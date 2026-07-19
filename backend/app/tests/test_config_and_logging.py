"""Tests that secrets are never serialized into log payloads."""
from app.core.config import safe_join_for_log


def test_safe_join_for_log_redacts_common_secret_keys() -> None:
    out = safe_join_for_log(
        {
            "host": "1.2.3.4",
            "api_key": "sk-supersecret",
            "private_key": "-----BEGIN...",
            "password": "abc",
            "Authorization": "Bearer X",
            "message": "ok",
        }
    )
    assert out["host"] == "1.2.3.4"
    assert out["message"] == "ok"
    assert out["api_key"] == "***"
    assert out["private_key"] == "***"
    assert out["password"] == "***"
    assert out["Authorization"] == "***"


def test_app_config_load_creates_layout(tmp_path):
    from app.core.config import AppConfig

    cfg = AppConfig.load(tmp_path / "data")
    assert cfg.secrets_dir.exists()
    assert cfg.artifacts_dir.exists()
    assert cfg.db_url.startswith("sqlite:///")


def test_secrets_storage_writes_with_restrictive_permissions(tmp_path):
    from app.core.config import AppConfig
    from app.services.secrets import read_secret, write_secret

    cfg = AppConfig.load(tmp_path / "data")
    write_secret(cfg, "demo_key", "secret-data")
    mode = (cfg.secrets_dir / "demo_key").stat().st_mode & 0o777
    assert mode == 0o600
    assert read_secret(cfg, "demo_key") == b"secret-data"
