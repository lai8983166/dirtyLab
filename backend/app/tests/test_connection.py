"""Connection tests.

We can't exercise real SSH in unit tests, so we cover the in-process paths:
- Validation rejects an empty / malformed key (missing-key scenario).
- The DB upsert keeps at most one active connection.
- The test endpoint returns a structured failure when no key material is
  configured (this exercises the FileNotFound path of check_connection).
"""
from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import AppConfig
from app.db.base import session_scope
from app.models import Connection
from app.services import connection_repo, secrets
from app.services.connection_test import check_connection
from app.services.ssh_keys import validate_private_key


def _seed_connection(
    data_dir: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 2222,
    username: str = "root",
    remote_root: str = "/root/ComfyUI",
) -> Connection:
    """Seed a connection in the DB and return a detached instance with all
    scalar attributes pre-loaded so callers can read fields after the session
    is closed."""
    cfg = AppConfig.load(data_dir)
    from app.db.base import init_engine
    from app.db.bootstrap import create_schema, ensure_seed_data

    engine = init_engine(cfg)
    create_schema(engine)
    with session_scope() as db:
        ensure_seed_data(db)
        # Leave the key file intentionally missing for the "unavailable" test.
        obj = connection_repo.upsert_connection(
            db,
            host=host,
            port=port,
            username=username,
            private_key_ref="autodl_private_key",
            remote_root=remote_root,
        )
        db.refresh(obj)
        # Force-load all scalar columns then detach so the test can read them
        # outside the session.
        _ = (obj.host, obj.port, obj.username, obj.private_key_ref, obj.remote_root,
             obj.comfyui_input_path, obj.comfyui_output_prefix)
        from sqlalchemy.orm import make_transient

        db.expunge(obj)
        make_transient(obj)
        return obj


def test_validate_private_key_rejects_empty() -> None:
    res = validate_private_key("")
    assert not res.ok
    assert "empty" in res.detail.lower()


def test_validate_private_key_rejects_garbage() -> None:
    res = validate_private_key("not a key at all")
    assert not res.ok
    assert "could not be parsed" in res.detail.lower()


def test_validate_private_key_accepts_generated_ed25519(tmp_path: Path) -> None:
    from app.tests._keys import generate_ed25519_openssh_text

    key = generate_ed25519_openssh_text()
    res = validate_private_key(key)
    assert res.ok
    assert res.key_type is not None


def test_only_one_active_connection_persisted(db_session) -> None:
    first = connection_repo.upsert_connection(
        db_session,
        host="1.1.1.1",
        port=22,
        username="root",
        private_key_ref="autodl_private_key",
        remote_root="/root/ComfyUI",
    )
    second = connection_repo.upsert_connection(
        db_session,
        host="2.2.2.2",
        port=22,
        username="root",
        private_key_ref="autodl_private_key",
        remote_root="/root/ComfyUI",
    )
    assert first.id == second.id
    active = db_session.query(Connection).filter_by(is_active=True).all()
    assert len(active) == 1
    assert active[0].host == "2.2.2.2"


def test_connection_test_reports_missing_key(tmp_data_dir: Path) -> None:
    conn = _seed_connection(tmp_data_dir)
    cfg = AppConfig.load(tmp_data_dir)
    # Key file is missing on purpose.
    result = check_connection(cfg, conn)
    assert not result.ok
    assert result.stage == "ssh_access"
    assert "missing" in (result.detail or "").lower() or "private key" in (result.detail or "").lower()


def test_connection_test_reports_no_config(client: TestClient) -> None:
    response = client.post("/api/connections/test")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["stage"] == "ssh_access"
    assert "No connection" in body["detail"]


def test_save_connection_endpoint_stores_key_as_secret(client: TestClient, tmp_data_dir: Path) -> None:
    key_text = paramiko_key()
    response = client.put(
        "/api/connections",
        json={
            "host": "127.0.0.1",
            "port": 22,
            "username": "root",
            "private_key": key_text,
            "remote_root": "/root/ComfyUI",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["host"] == "127.0.0.1"
    assert body["private_key_ref"] == "autodl_private_key"
    # Key material is on disk in the secrets dir.
    cfg = AppConfig.load(tmp_data_dir)
    secret_path = cfg.secrets_dir / "autodl_private_key"
    assert secret_path.exists()
    mode = secret_path.stat().st_mode & 0o777
    assert mode == 0o600
    # And the API never echoes the key back.
    assert "BEGIN" not in response.text


# --- helpers ---


def paramiko_key() -> str:
    """Generate an ed25519 key in-process; the test environment may not have
    ssh-keygen and paramiko 5+ removed ``Ed25519Key.generate``."""
    from app.tests._keys import generate_ed25519_openssh_text

    return generate_ed25519_openssh_text()
