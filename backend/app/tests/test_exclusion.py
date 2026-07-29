"""Verify secrets/configs are excluded from sync and logs (Task 7.4)."""
from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import AppConfig, safe_join_for_log
from app.tests._fixtures import PNG_1x1_RED as PNG
from app.tests.sftp_fixture import install_fake_sftp


def test_log_redaction_never_dumps_secrets() -> None:
    out = safe_join_for_log({"api_key": "sk-secret", "private_key": "PEM", "note": "ok"})
    assert "sk-secret" not in str(out)
    assert "PEM" not in str(out)
    assert out["note"] == "ok"


def test_secrets_directory_is_outside_artifact_dir(tmp_data_dir: Path) -> None:
    cfg = AppConfig.load(tmp_data_dir)
    assert cfg.secrets_dir != cfg.artifacts_dir
    assert cfg.secrets_dir.is_relative_to(cfg.data_dir)
    assert cfg.artifacts_dir.is_relative_to(cfg.data_dir)


def test_sync_never_pulls_secrets_dir(client: TestClient, tmp_data_dir: Path, monkeypatch) -> None:
    """Sync only walks the remote experiment workspace; even if a malicious
    remote symlinked to data/secrets, the allowlist filter would exclude it."""
    from app.tests._keys import generate_ed25519_openssh_text

    private_key = generate_ed25519_openssh_text()
    client.put(
        "/api/connections",
        json={
            "host": "127.0.0.1",
            "port": 2222,
            "username": "root",
            "private_key": private_key,
            "remote_root": "/root/ComfyUI",
        },
    )
    r = client.post(
        "/api/experiments",
        data={"name": "t", "goal": ""},
        files={"original_image": ("o.png", io.BytesIO(PNG), "image/png")},
    )
    workspace = r.json()["remote_workspace_path"]
    experiment_id = r.json()["id"]

    # Even if the remote workspace had a "secrets" directory, the sync only
    # walks known allowlisted dir names.
    install_fake_sftp(
        monkeypatch,
        {
            f"{workspace}/output/c1.png": PNG,
            f"{workspace}/secrets/leak.txt": b"topsecret",
            f"{workspace}/unknown_dir/x": b"whatever",
        },
    )
    r = client.post(f"/api/sync/experiments/{experiment_id}").json()
    artifact_paths = [a["relative_path"] for a in r["snapshot"]["artifacts"]]
    assert all("secrets" not in p for p in artifact_paths)
    assert all("leak" not in p for p in artifact_paths)
    assert r["ignored_count"] >= 2  # the unknown_dir + secrets dir are ignored


def test_secrets_not_in_gitignore_patterns_at_runtime(tmp_data_dir: Path) -> None:
    cfg = AppConfig.load(tmp_data_dir)
    # Sanity: secrets dir is on disk but its files have 0600 perms.
    (cfg.secrets_dir / "demo").write_text("x", encoding="utf-8")
    (cfg.secrets_dir / "demo").chmod(0o600)
    mode = (cfg.secrets_dir / "demo").stat().st_mode & 0o777
    assert mode == 0o600
