"""Application configuration loaded from environment + local settings file.

All paths are resolved under a single ``data_dir`` (default ``./data``). This
directory is local-only and MUST be excluded from synchronization and version
control. See ``.gitignore``.

Layout::

    data/
      config.json          # non-secret app config overrides
      secrets/             # never logged, never synced
        autodl_private_key # the SSH key configured by the user
        provider_api_key   # the multimodal provider API key (raw)
      dirtylab.db          # SQLite database
      artifacts/
        <experiment_id>/
          original.<ext>
          snapshots/
            <snapshot_id>/
              inputs/ masks/ outputs/ workflows/ metadata/
          analyses/        # cached provider payloads (no secrets)

Configuration precedence (highest first):
1. Environment variables (``DIRTYLAB_*``).
2. ``data/config.json`` (created on first run).
3. Built-in defaults below.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path(os.environ.get("DIRTYLAB_DATA_DIR", "./data")).resolve()


@dataclass
class AppConfig:
    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)
    db_url: str = ""  # filled at runtime
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["http://127.0.0.1:5173"])
    artifact_allowlist_extra: list[str] = field(default_factory=list)
    artifact_exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "*.tmp",
            "*.temp",
            "*.bak",
            "*.cache",
            "*~",
            ".DS_Store",
            "Thumbs.db",
        ]
    )
    sync_stability_retries: int = 3
    sync_stability_wait_seconds: float = 0.75
    sync_chunk_size: int = 65536
    http_timeout_seconds: float = 60.0

    @classmethod
    def load(cls, data_dir: Path | None = None) -> AppConfig:
        root = (data_dir or DEFAULT_DATA_DIR).resolve()
        root.mkdir(parents=True, exist_ok=True)
        (root / "secrets").mkdir(exist_ok=True)
        (root / "artifacts").mkdir(exist_ok=True)

        cfg = cls(data_dir=root)
        cfg.db_url = f"sqlite:///{(root / 'dirtylab.db').as_posix()}"

        config_file = root / "config.json"
        if config_file.exists():
            try:
                raw = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                raw = {}
            for key, value in raw.items():
                if key == "data_dir":
                    continue
                if hasattr(cfg, key):
                    setattr(cfg, key, value)

        # Environment overrides
        if v := os.environ.get("DIRTYLAB_LOG_LEVEL"):
            cfg.log_level = v
        if v := os.environ.get("DIRTYLAB_DB_URL"):
            cfg.db_url = v

        return cfg

    def save(self) -> None:
        payload = asdict(self)
        payload["data_dir"] = str(self.data_dir)
        (self.data_dir / "config.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    # --- path helpers ---
    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "dirtylab.db"

    def experiment_dir(self, experiment_id: str) -> Path:
        return self.artifacts_dir / experiment_id

    def snapshot_dir(self, experiment_id: str, snapshot_id: str) -> Path:
        return self.experiment_dir(experiment_id) / "snapshots" / snapshot_id

    def original_image_path(self, experiment_id: str, suffix: str) -> Path:
        return self.experiment_dir(experiment_id) / f"original{suffix}"


# A process-wide singleton set by the FastAPI startup event.
_CONFIG: AppConfig | None = None


def get_config() -> AppConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = AppConfig.load()
    return _CONFIG


def set_config(cfg: AppConfig) -> None:
    global _CONFIG
    _CONFIG = cfg


def redact_for_log(value: Any) -> str:
    """Used by logging helpers - never log raw secrets."""
    if value is None:
        return "<none>"
    s = str(value)
    if len(s) <= 4:
        return "***"
    return s[:2] + "***" + s[-2:]


def safe_join_for_log(d: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``d`` with common secret keys redacted."""
    secret_keys = {
        "api_key",
        "key",
        "private_key",
        "password",
        "token",
        "secret",
        "authorization",
    }
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k.lower() in secret_keys or any(s in k.lower() for s in secret_keys):
            out[k] = "***"
        else:
            out[k] = v
    return out
