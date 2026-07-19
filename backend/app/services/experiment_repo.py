"""Experiment + snapshot + artifact repositories."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models import (
    Artifact,
    Evaluation,
    Experiment,
    ExtractedMetadata,
    Snapshot,
)


def get_experiment(db: Session, experiment_id: str) -> Experiment:
    obj = db.get(Experiment, experiment_id)
    if obj is None:
        raise NotFoundError("Experiment not found", details={"id": experiment_id})
    return obj


def list_experiments(db: Session) -> list[Experiment]:
    return list(db.scalars(select(Experiment).order_by(Experiment.created_at.desc())))


def create_experiment(
    db: Session,
    *,
    name: str,
    goal: str,
    original_filename: str,
    original_extension: str,
    original_checksum: str,
    remote_workspace_path: str,
) -> Experiment:
    if not name.strip():
        raise ValidationError("Experiment name is required")
    if not original_checksum:
        raise ValidationError("Original image checksum is required")
    obj = Experiment(
        name=name.strip(),
        goal=goal or "",
        original_filename=original_filename,
        original_extension=original_extension,
        original_checksum=original_checksum,
        remote_workspace_path=remote_workspace_path,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_remote_workspace_path(remote_root: str, experiment_id: str) -> str:
    base = PurePosixPath(remote_root.rstrip("/"))
    return str(base / "experiments" / experiment_id)


# --- snapshots ---


def next_snapshot_number(db: Session, experiment_id: str) -> int:
    count = db.scalar(
        select(func.count(Snapshot.id)).where(Snapshot.experiment_id == experiment_id)
    )
    return (count or 0) + 1


def create_snapshot(
    db: Session,
    *,
    experiment_id: str,
    source_path: str,
    status: str = "success",
    ignored_count: int = 0,
    error_detail: str | None = None,
) -> Snapshot:
    number = next_snapshot_number(db, experiment_id)
    obj = Snapshot(
        experiment_id=experiment_id,
        number=number,
        status=status,
        source_path=source_path,
        ignored_count=ignored_count,
        error_detail=error_detail,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_snapshot(db: Session, snapshot_id: str) -> Snapshot:
    obj = db.get(Snapshot, snapshot_id)
    if obj is None:
        raise NotFoundError("Snapshot not found", details={"id": snapshot_id})
    return obj


def list_snapshots(db: Session, experiment_id: str) -> list[Snapshot]:
    return list(
        db.scalars(
            select(Snapshot)
            .where(Snapshot.experiment_id == experiment_id)
            .order_by(Snapshot.number.desc())
        )
    )


def mark_snapshot_finished(
    db: Session, snapshot: Snapshot, *, status: str, error_detail: str | None = None
) -> None:
    from datetime import datetime

    snapshot.status = status
    snapshot.error_detail = error_detail
    snapshot.finished_at = datetime.utcnow()
    db.commit()


# --- artifacts ---


def add_artifact(
    db: Session,
    *,
    snapshot_id: str,
    relative_path: str,
    kind: str,
    remote_path: str,
    local_path: str,
    checksum: str,
    size_bytes: int,
    transfer_status: str = "transferred",
    error_detail: str | None = None,
) -> Artifact:
    obj = Artifact(
        snapshot_id=snapshot_id,
        relative_path=relative_path,
        kind=kind,
        remote_path=remote_path,
        local_path=local_path,
        checksum=checksum,
        size_bytes=size_bytes,
        transfer_status=transfer_status,
        error_detail=error_detail,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_snapshot_artifacts(db: Session, snapshot_id: str) -> list[Artifact]:
    return list(
        db.scalars(select(Artifact).where(Artifact.snapshot_id == snapshot_id).order_by(Artifact.kind, Artifact.relative_path))
    )


def list_experiment_candidate_artifacts(db: Session, experiment_id: str) -> list[Artifact]:
    """Return all saved_image artifacts across the experiment's snapshots."""
    return list(
        db.scalars(
            select(Artifact)
            .join(Snapshot, Snapshot.id == Artifact.snapshot_id)
            .where(Snapshot.experiment_id == experiment_id)
            .where(Artifact.kind == "saved_image")
            .order_by(Snapshot.number.desc(), Artifact.relative_path)
        )
    )


def get_artifact(db: Session, artifact_id: str) -> Artifact:
    obj = db.get(Artifact, artifact_id)
    if obj is None:
        raise NotFoundError("Artifact not found", details={"id": artifact_id})
    return obj


def upsert_extracted_metadata(
    db: Session,
    *,
    artifact_id: str,
    field_name: str,
    field_value: str,
    is_unknown: bool,
    is_user_corrected: bool = False,
) -> ExtractedMetadata:
    existing = db.scalar(
        select(ExtractedMetadata)
        .where(ExtractedMetadata.artifact_id == artifact_id)
        .where(ExtractedMetadata.field_name == field_name)
    )
    if existing is None:
        obj = ExtractedMetadata(
            artifact_id=artifact_id,
            field_name=field_name,
            field_value=field_value,
            is_unknown=is_unknown,
            is_user_corrected=is_user_corrected,
        )
        db.add(obj)
    else:
        # Only user-driven corrections overwrite existing values.
        if is_user_corrected or not existing.is_user_corrected:
            existing.field_value = field_value
            existing.is_unknown = is_unknown
            if is_user_corrected:
                existing.is_user_corrected = True
        obj = existing
    db.commit()
    db.refresh(obj)
    return obj


def list_extracted_metadata(db: Session, artifact_id: str) -> list[ExtractedMetadata]:
    return list(
        db.scalars(
            select(ExtractedMetadata).where(ExtractedMetadata.artifact_id == artifact_id)
        )
    )


# --- evaluations ---


def get_evaluation_for_artifact(db: Session, artifact_id: str) -> Evaluation | None:
    return db.scalar(select(Evaluation).where(Evaluation.artifact_id == artifact_id))
