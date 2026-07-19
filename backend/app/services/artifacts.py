"""Filesystem helpers for artifacts.

The repository layer stores absolute paths in the DB, but all paths live under
``data/artifacts/<experiment_id>/`` and never outside. ``ArtifactStore`` is the
only component that writes binary files for snapshots/inputs so we can keep the
layout consistent and verify nothing escapes the experiment directory.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import IO

from app.core.config import AppConfig
from app.core.errors import ValidationError


def sha256_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ArtifactStore:
    """Filesystem-backed store. Never writes outside ``data/artifacts``."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.root = config.artifacts_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_experiment_dirs(self, experiment_id: str) -> Path:
        base = self.root / experiment_id
        (base / "snapshots").mkdir(parents=True, exist_ok=True)
        (base / "analyses").mkdir(parents=True, exist_ok=True)
        return base

    def ensure_snapshot_dirs(self, experiment_id: str, snapshot_id: str) -> Path:
        base = self.ensure_experiment_dirs(experiment_id) / "snapshots" / snapshot_id
        for sub in ("inputs", "masks", "outputs", "workflows", "metadata"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        return base

    def store_original_image(
        self, experiment_id: str, extension: str, stream: IO[bytes]
    ) -> tuple[Path, str, int]:
        self.ensure_experiment_dirs(experiment_id)
        suffix = ("." + extension.lstrip(".")) if extension else ""
        path = self.root / experiment_id / f"original{suffix}"
        size = self._copy(stream, path)
        checksum = sha256_file(path)
        return path, checksum, size

    def write_artifact(
        self,
        experiment_id: str,
        snapshot_id: str,
        kind: str,
        relative_path: str,
        stream: IO[bytes],
    ) -> tuple[Path, str, int]:
        base = self.ensure_snapshot_dirs(experiment_id, snapshot_id)
        # Map artifact kinds to on-disk subdirectories; reject anything outside.
        kind_dirs = {
            "input": "inputs",
            "original_image": "inputs",
            "mask": "masks",
            "saved_image": "outputs",
            "workflow_json": "workflows",
            "metadata": "metadata",
        }
        subdir = kind_dirs.get(kind)
        if subdir is None:
            raise ValidationError(f"Unsupported artifact kind: {kind}")
        # Sanitize relative_path so it stays inside the snapshot dir.
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValidationError(f"Unsafe relative path: {relative_path}")
        target = base / subdir / rel.name
        target.parent.mkdir(parents=True, exist_ok=True)
        size = self._copy(stream, target)
        checksum = sha256_file(target)
        return target, checksum, size

    def import_local_file(
        self,
        experiment_id: str,
        snapshot_id: str,
        kind: str,
        relative_path: str,
        source: Path,
    ) -> tuple[Path, str, int]:
        with source.open("rb") as fh:
            return self.write_artifact(
                experiment_id, experiment_id, kind, relative_path, fh
            ) if False else self.write_artifact(
                experiment_id, snapshot_id, kind, relative_path, fh
            )

    def delete_experiment(self, experiment_id: str) -> None:
        target = self.root / experiment_id
        if target.exists():
            shutil.rmtree(target)

    def _copy(self, stream: IO[bytes], target: Path) -> int:
        size = 0
        with target.open("wb") as out:
            while True:
                buf = stream.read(65536)
                if not buf:
                    break
                out.write(buf)
                size += len(buf)
        return size
