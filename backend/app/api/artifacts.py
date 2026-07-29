"""Artifact serving + metadata correction."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.base import get_db
from app.schemas import ArtifactOut, MetadataCorrectionIn
from app.schemas.repositories import artifact_to_schema
from app.services import experiment_repo

router = APIRouter()


@router.get("/{artifact_id}", response_model=ArtifactOut)
def get_artifact(artifact_id: str, db: Session = Depends(get_db)) -> ArtifactOut:
    obj = experiment_repo.get_artifact(db, artifact_id)
    return artifact_to_schema(obj)


@router.get("/{artifact_id}/file")
def download_artifact(artifact_id: str, db: Session = Depends(get_db)):
    obj = experiment_repo.get_artifact(db, artifact_id)
    path = Path(obj.local_path)
    if not path.exists():
        raise NotFoundError("Artifact file is missing on disk", details={"id": artifact_id})
    media = mimetypes.guess_type(obj.relative_path)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=path.name)


@router.put("/{artifact_id}/metadata", response_model=ArtifactOut)
def correct_metadata(
    artifact_id: str,
    payload: MetadataCorrectionIn,
    db: Session = Depends(get_db),
) -> ArtifactOut:
    obj = experiment_repo.get_artifact(db, artifact_id)
    experiment_repo.upsert_extracted_metadata(
        db,
        artifact_id=obj.id,
        field_name=payload.field_name,
        field_value=payload.field_value,
        is_unknown=payload.is_unknown,
        is_user_corrected=True,
    )
    db.refresh(obj)
    return artifact_to_schema(obj)
