"""Experiment CRUD endpoints.

See spec: local-experiment-management.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.core.errors import NotFoundError, ValidationError
from app.db.base import get_db
from app.schemas import ExperimentDetail, ExperimentOut
from app.schemas.repositories import experiment_detail_schema, experiment_to_schema
from app.services import (
    analysis_repo,
    connection_repo,
    evaluation_repo,
    experiment_repo,
)
from app.services import artifacts as artifact_store_mod

router = APIRouter()


def _guess_extension(filename: str, content_type: str) -> str:
    if filename and "." in filename:
        return Path(filename).suffix.lstrip(".").lower()
    guess = mimetypes.guess_extension(content_type) if content_type else None
    return (guess or ".png").lstrip(".").lower()


@router.get("", response_model=list[ExperimentOut])
def list_experiments(db: Session = Depends(get_db)) -> list[ExperimentOut]:
    return [experiment_to_schema(e) for e in experiment_repo.list_experiments(db)]


@router.post("", response_model=ExperimentDetail)
def create_experiment(
    name: str = Form(...),
    goal: str = Form(""),
    original_image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExperimentDetail:
    if not original_image.filename:
        raise ValidationError("An original image is required to create an experiment")
    cfg = get_config()
    content = original_image.file.read()
    if not content:
        raise ValidationError("Original image is empty")
    ext = _guess_extension(original_image.filename, original_image.content_type or "")
    store = artifact_store_mod.ArtifactStore(cfg)
    checksum = artifact_store_mod.sha256_bytes(content)
    # Pre-create the experiment so we know the id, then store the original.
    connection = connection_repo.get_active_connection(db)
    if connection is None:
        # We still allow creating the experiment without a connection so users
        # can plan experiments offline. Sync will refuse until configured.
        remote_root = "<unconfigured>"
    else:
        remote_root = connection.remote_root
    # Reserve the experiment row with a temporary checksum placeholder to
    # obtain the id, then store the original using the id.
    experiment = experiment_repo.create_experiment(
        db,
        name=name,
        goal=goal,
        original_filename=original_image.filename,
        original_extension=ext,
        original_checksum=checksum,
        remote_workspace_path="pending",
    )
    # Store the original image now that we have an id.
    import io

    path, stored_checksum, _size = store.store_original_image(
        experiment.id, ext, io.BytesIO(content)
    )
    if stored_checksum != checksum:
        experiment.original_checksum = stored_checksum
        db.commit()
        db.refresh(experiment)
    remote_workspace_path = experiment_repo.make_remote_workspace_path(remote_root, experiment.id)
    experiment.remote_workspace_path = remote_workspace_path
    db.commit()
    db.refresh(experiment)
    return experiment_detail_schema(experiment)


@router.get("/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)) -> ExperimentDetail:
    experiment = experiment_repo.get_experiment(db, experiment_id)
    snapshots = experiment_repo.list_snapshots(db, experiment_id)
    evaluations = evaluation_repo.list_evaluations_for_experiment(db, experiment_id)
    analyses = analysis_repo.list_analyses_for_experiment(db, experiment_id)
    return experiment_detail_schema(
        experiment,
        snapshots=snapshots,
        evaluations=evaluations,
        analyses=analyses,
    )


@router.get("/{experiment_id}/original-image")
def get_original_image(experiment_id: str, db: Session = Depends(get_db)):
    experiment = experiment_repo.get_experiment(db, experiment_id)
    cfg = get_config()
    suffix = ("." + experiment.original_extension) if experiment.original_extension else ""
    path = cfg.artifacts_dir / experiment.id / f"original{suffix}"
    if not path.exists():
        raise NotFoundError("Original image is not available", details={"id": experiment_id})
    media_type = (
        f"image/{experiment.original_extension}"
        if experiment.original_extension
        else "application/octet-stream"
    )
    return FileResponse(path, media_type=media_type, filename=experiment.original_filename)


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str, db: Session = Depends(get_db)) -> dict:
    experiment = experiment_repo.get_experiment(db, experiment_id)
    cfg = get_config()
    store = artifact_store_mod.ArtifactStore(cfg)
    store.delete_experiment(experiment_id)
    db.delete(experiment)
    db.commit()
    return {"deleted": experiment_id}
