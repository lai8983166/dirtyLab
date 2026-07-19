"""Synchronization service.

Implements the spec for ``autodl-comfyui-sync``:

- Allowlist + temporary-file exclusion (Requirement 4.1 in tasks).
- SFTP directory inspection with stable-file checks (4.2).
- Per-file checksums and incremental download (4.2).
- Per-file transfer status (4.2).
- Immutable snapshot for success/partial/empty (4.3).
- Best-effort metadata extraction (4.4).
"""
from __future__ import annotations

import io
import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import paramiko

from app.core.config import AppConfig
from app.core.logging import get_logger
from app.schemas import SyncResultOut
from app.schemas.repositories import snapshot_to_schema
from app.services import artifacts as artifact_store_mod
from app.services import experiment_repo
from app.services import metadata as metadata_service
from app.services.connection_test import _ssh_client

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Connection, Experiment


# Remote artifact allowlist (Task 4.1)
ALLOWED_KINDS_BY_DIR = {
    "input": "input",
    "inputs": "input",
    "masks": "mask",
    "output": "saved_image",
    "outputs": "saved_image",
    "workflows": "workflow_json",
}
ALLOWED_EXTENSIONS = {
    "input": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
    "mask": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
    "saved_image": {".png", ".jpg", ".jpeg", ".webp", ".bmp"},
    "workflow_json": {".json"},
    "metadata": {".json", ".txt", ".log"},
}
EXCLUDE_PATTERNS = {
    "*.tmp",
    "*.temp",
    "*.bak",
    "*~",
    "*.cache",
    "*.partial",
    "Thumbs.db",
    ".DS_Store",
}


@dataclass
class _RemoteFile:
    path: str  # absolute remote path
    relative_path: str  # relative to remote workspace
    kind: str
    size: int
    mtime: float


def run_sync(db: "Session", experiment: "Experiment", connection: "Connection") -> SyncResultOut:
    log = get_logger("sync")
    cfg = AppConfig.load()

    # Stage 1: SSH connect.
    try:
        client = _ssh_client(cfg, connection)
    except (socket.timeout, TimeoutError) as exc:
        log.info("sync.timeout", experiment_id=experiment.id)
        return _failure_snapshot(
            db,
            experiment,
            source_path=experiment.remote_workspace_path,
            detail=f"Timed out reaching AutoDL: {exc}",
        )
    except paramiko.AuthenticationException as exc:
        log.info("sync.auth_failed", experiment_id=experiment.id)
        return _failure_snapshot(
            db,
            experiment,
            source_path=experiment.remote_workspace_path,
            detail=f"Authentication failed: {exc}",
        )
    except FileNotFoundError as exc:
        log.info("sync.missing_key", experiment_id=experiment.id)
        return _failure_snapshot(
            db,
            experiment,
            source_path=experiment.remote_workspace_path,
            detail=f"Missing private key: {exc}",
        )

    try:
        sftp = client.open_sftp()
        try:
            files, ignored = _list_workspace(sftp, experiment.remote_workspace_path)
            if not files:
                return _empty_snapshot(
                    db,
                    experiment,
                    source_path=experiment.remote_workspace_path,
                    ignored_count=ignored,
                )

            snapshot = experiment_repo.create_snapshot(
                db,
                experiment_id=experiment.id,
                source_path=experiment.remote_workspace_path,
                status="partial",  # updated below
                ignored_count=ignored,
            )
            store = artifact_store_mod.ArtifactStore(cfg)

            partial_failures: list[dict[str, str]] = []
            transferred: list[tuple[str, str, str, int]] = []
            unstable_files = False

            for f in files:
                try:
                    data, checksum = _download_stable(sftp, f, cfg)
                except _UnstableFile:
                    partial_failures.append({"path": f.relative_path, "reason": "unstable"})
                    unstable_files = True
                    artifact = experiment_repo.add_artifact(
                        db,
                        snapshot_id=snapshot.id,
                        relative_path=f.relative_path,
                        kind=f.kind,
                        remote_path=f.path,
                        local_path="",
                        checksum="",
                        size_bytes=f.size,
                        transfer_status="unstable",
                        error_detail="file kept changing during transfer",
                    )
                    continue
                except Exception as exc:
                    partial_failures.append({"path": f.relative_path, "reason": str(exc)})
                    experiment_repo.add_artifact(
                        db,
                        snapshot_id=snapshot.id,
                        relative_path=f.relative_path,
                        kind=f.kind,
                        remote_path=f.path,
                        local_path="",
                        checksum="",
                        size_bytes=f.size,
                        transfer_status="failed",
                        error_detail=str(exc),
                    )
                    continue
                # Write to disk via the artifact store so paths stay local.
                target, stored_checksum, size = store.write_artifact(
                    experiment.id,
                    snapshot.id,
                    f.kind,
                    f.relative_path,
                    io.BytesIO(data),
                )
                if stored_checksum != checksum:
                    partial_failures.append(
                        {"path": f.relative_path, "reason": "checksum mismatch after write"}
                    )
                artifact = experiment_repo.add_artifact(
                    db,
                    snapshot_id=snapshot.id,
                    relative_path=f.relative_path,
                    kind=f.kind,
                    remote_path=f.path,
                    local_path=str(target),
                    checksum=stored_checksum,
                    size_bytes=size,
                    transfer_status="transferred",
                )
                transferred.append((artifact.id, f.kind, str(target), size))
                # Best-effort metadata extraction.
                try:
                    metadata_service.extract_and_store(db, artifact, target, kind=f.kind)
                except Exception as exc:  # pragma: no cover - best-effort
                    log.info("sync.metadata_failed", artifact_id=artifact.id, error=str(exc))

            status = "success" if not partial_failures else "partial"
            experiment_repo.mark_snapshot_finished(
                db, snapshot, status=status, error_detail=None
            )
            db.refresh(snapshot)
            return SyncResultOut(
                snapshot=snapshot_to_schema(snapshot),
                partial_failures=partial_failures,
                ignored_count=ignored,
                retryable=unstable_files or bool(partial_failures),
            )
        finally:
            sftp.close()
    finally:
        client.close()


def _list_workspace(
    sftp: paramiko.SFTPClient, remote_workspace: str
) -> tuple[list[_RemoteFile], int]:
    """Walk the remote workspace and split into allowlisted files + ignored count."""
    files: list[_RemoteFile] = []
    ignored = 0
    workspace = remote_workspace.rstrip("/")
    try:
        entries = sftp.listdir_attr(workspace)
    except FileNotFoundError:
        return [], 0
    for entry in entries:
        top = entry.filename
        kind = ALLOWED_KINDS_BY_DIR.get(top.lower())
        full = f"{workspace}/{top}"
        if kind is None:
            ignored += 1
            continue
        try:
            for sub in sftp.listdir_attr(full):
                if _is_excluded(sub.filename):
                    ignored += 1
                    continue
                ext = PurePosixPath(sub.filename).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS.get(kind, set()):
                    ignored += 1
                    continue
                files.append(
                    _RemoteFile(
                        path=f"{full}/{sub.filename}",
                        relative_path=f"{top}/{sub.filename}",
                        kind=kind,
                        size=sub.st_size or 0,
                        mtime=sub.st_mtime or 0.0,
                    )
                )
        except FileNotFoundError:
            ignored += 1
        except PermissionError:
            ignored += 1
    return files, ignored


def _is_excluded(name: str) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(name, pat) for pat in EXCLUDE_PATTERNS)


class _UnstableFile(Exception):
    pass


def _download_stable(
    sftp: paramiko.SFTPClient, f: "_RemoteFile", cfg: AppConfig
) -> tuple[bytes, str]:
    """Read the file size multiple times; if it keeps changing, raise."""
    import hashlib

    last_size = -1
    stable = False
    for _ in range(max(1, cfg.sync_stability_retries)):
        try:
            stat = sftp.stat(f.path)
        except FileNotFoundError as exc:
            raise _UnstableFile() from exc
        if stat.st_size != last_size and last_size != -1:
            time.sleep(cfg.sync_stability_wait_seconds)
            last_size = stat.st_size
            continue
        if last_size == -1:
            last_size = stat.st_size
            time.sleep(cfg.sync_stability_wait_seconds)
            continue
        stable = True
        break
    if not stable:
        # One final stat: if it matches, allow the transfer.
        try:
            stat = sftp.stat(f.path)
            if stat.st_size == last_size:
                stable = True
        except FileNotFoundError as exc:  # pragma: no cover
            raise _UnstableFile() from exc
    if not stable:
        raise _UnstableFile()
    buf = io.BytesIO()
    sftp.getfo(f.path, buf)
    data = buf.getvalue()
    return data, hashlib.sha256(data).hexdigest()


def _failure_snapshot(
    db: "Session", experiment: "Experiment", *, source_path: str, detail: str
) -> SyncResultOut:
    snapshot = experiment_repo.create_snapshot(
        db,
        experiment_id=experiment.id,
        source_path=source_path,
        status="failed",
        ignored_count=0,
        error_detail=detail,
    )
    experiment_repo.mark_snapshot_finished(db, snapshot, status="failed", error_detail=detail)
    db.refresh(snapshot)
    return SyncResultOut(
        snapshot=snapshot_to_schema(snapshot),
        partial_failures=[],
        ignored_count=0,
        retryable=True,
    )


def _empty_snapshot(
    db: "Session", experiment: "Experiment", *, source_path: str, ignored_count: int
) -> SyncResultOut:
    snapshot = experiment_repo.create_snapshot(
        db,
        experiment_id=experiment.id,
        source_path=source_path,
        status="empty",
        ignored_count=ignored_count,
    )
    experiment_repo.mark_snapshot_finished(db, snapshot, status="empty")
    db.refresh(snapshot)
    return SyncResultOut(
        snapshot=snapshot_to_schema(snapshot),
        partial_failures=[],
        ignored_count=ignored_count,
        retryable=False,
    )
