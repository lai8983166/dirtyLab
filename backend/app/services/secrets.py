"""Local-only secret storage.

Secrets are stored as plain files under ``data/secrets``. The database only
records the filename (``*_ref`` columns), never the secret material. This
module is the single point that reads/writes secret files so permissions and
redaction stay consistent.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.core.config import AppConfig
from app.core.errors import NotFoundError


def write_secret(config: AppConfig, ref: str, content: bytes | str) -> None:
    """Write ``content`` to ``secrets/<ref>`` with mode 0600."""
    path = _resolve(config, ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content
    # Write atomically with restrictive permissions.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def read_secret(config: AppConfig, ref: str) -> bytes:
    path = _resolve(config, ref)
    if not path.exists():
        raise NotFoundError(
            f"Secret file '{ref}' is not present",
            details={"ref": ref},
        )
    return path.read_bytes()


def delete_secret(config: AppConfig, ref: str) -> None:
    path = _resolve(config, ref)
    if path.exists():
        path.unlink()


def _resolve(config: AppConfig, ref: str) -> Path:
    # Defense in depth: never allow path traversal out of secrets dir.
    base = config.secrets_dir.resolve()
    candidate = (base / ref).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError(f"Invalid secret reference: {ref}")
    if Path(ref).name != ref or "/" in ref or "\\" in ref:
        raise ValueError(f"Invalid secret reference: {ref}")
    return candidate
