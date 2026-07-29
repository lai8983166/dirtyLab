"""Sync service tests using the in-process SFTP double."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.core.config import AppConfig
from app.db.base import init_engine, session_scope
from app.db.bootstrap import create_schema, ensure_seed_data
from app.services import connection_repo, experiment_repo
from app.services import sync as sync_service
from app.tests._fixtures import PNG_1x1_RED as PNG
from app.tests.sftp_fixture import install_fake_sftp


@pytest.fixture
def seeded(tmp_data_dir: Path):
    """Return (cfg, experiment_id). Tests open their own session to fetch
    fresh ORM objects, so nothing detaches."""
    cfg = AppConfig.load(tmp_data_dir)
    engine = init_engine(cfg)
    create_schema(engine)
    with session_scope() as db:
        ensure_seed_data(db)
        connection_repo.upsert_connection(
            db,
            host="h",
            port=22,
            username="u",
            private_key_ref="autodl_private_key",
            remote_root="/root/ComfyUI",
        )
        from app.models import Experiment
        from app.services.artifacts import sha256_bytes

        experiment = Experiment(
            name="x",
            goal="",
            original_filename="orig.png",
            original_extension="png",
            original_checksum=sha256_bytes(PNG),
            remote_workspace_path="/root/ComfyUI/experiments/abc",
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)
        # Write the original image locally so the experiment detail view works.
        from app.services.artifacts import ArtifactStore

        store = ArtifactStore(cfg)
        store.ensure_experiment_dirs(experiment.id)
        (cfg.artifacts_dir / experiment.id / "original.png").write_bytes(PNG)
        experiment_id = experiment.id
    return cfg, experiment_id


def test_sync_new_files(seeded, monkeypatch) -> None:
    cfg, experiment_id = seeded
    workspace = "/root/ComfyUI/experiments/abc"
    install_fake_sftp(
        monkeypatch,
        {
            f"{workspace}/output/c1.png": PNG,
            f"{workspace}/output/c2.png": PNG,
        },
    )
    with session_scope() as db:
        exp = experiment_repo.get_experiment(db, experiment_id)
        conn = connection_repo.get_active_connection(db)
        result = sync_service.run_sync(db, exp, conn)
        assert result.snapshot.status == "success"
        assert len(result.snapshot.artifacts) == 2
        assert result.ignored_count == 0
        assert result.partial_failures == []


def test_sync_ignores_temporary_files(seeded, monkeypatch) -> None:
    cfg, experiment_id = seeded
    workspace = "/root/ComfyUI/experiments/abc"
    install_fake_sftp(
        monkeypatch,
        {
            f"{workspace}/output/c1.png": PNG,
            f"{workspace}/output/preview.tmp": PNG,  # excluded by pattern
            f"{workspace}/cache/x.cache": b"noise",  # excluded (unknown dir)
        },
    )
    with session_scope() as db:
        exp = experiment_repo.get_experiment(db, experiment_id)
        conn = connection_repo.get_active_connection(db)
        result = sync_service.run_sync(db, exp, conn)
        assert len(result.snapshot.artifacts) == 1
        assert result.ignored_count >= 2


def test_sync_partial_failure(seeded, monkeypatch) -> None:
    cfg, experiment_id = seeded
    workspace = "/root/ComfyUI/experiments/abc"
    from app.tests.sftp_fixture import FakeSFTP, FakeSSHClient

    files = {
        f"{workspace}/output/c1.png": PNG,
        f"{workspace}/output/c2.png": PNG,
    }
    fake = FakeSFTP(files)
    original_getfo = fake.getfo

    def flaky_getfo(path: str, stream: io.BytesIO) -> None:
        if path.endswith("c2.png"):
            raise OSError("simulated network drop")
        original_getfo(path, stream)

    fake.getfo = flaky_getfo
    monkeypatch.setattr(
        "app.services.sync._ssh_client", lambda _c, _x: FakeSSHClient(fake)
    )
    with session_scope() as db:
        exp = experiment_repo.get_experiment(db, experiment_id)
        conn = connection_repo.get_active_connection(db)
        result = sync_service.run_sync(db, exp, conn)
        assert result.snapshot.status == "partial"
        assert len(result.partial_failures) == 1
        assert result.retryable


def test_sync_creates_new_snapshot_each_run(seeded, monkeypatch) -> None:
    cfg, experiment_id = seeded
    workspace = "/root/ComfyUI/experiments/abc"
    install_fake_sftp(
        monkeypatch,
        {f"{workspace}/output/c1.png": PNG},
    )
    with session_scope() as db:
        exp = experiment_repo.get_experiment(db, experiment_id)
        conn = connection_repo.get_active_connection(db)
        first = sync_service.run_sync(db, exp, conn)
        second = sync_service.run_sync(db, exp, conn)
        assert first.snapshot.id != second.snapshot.id
        assert first.snapshot.number == 1
        assert second.snapshot.number == 2


def test_sync_empty_workspace(seeded, monkeypatch) -> None:
    cfg, experiment_id = seeded
    # No files registered at all -> listdir(workspace) raises FileNotFoundError
    # -> sync returns empty.
    install_fake_sftp(monkeypatch, {})
    with session_scope() as db:
        exp = experiment_repo.get_experiment(db, experiment_id)
        conn = connection_repo.get_active_connection(db)
        result = sync_service.run_sync(db, exp, conn)
        assert result.snapshot.status == "empty"
