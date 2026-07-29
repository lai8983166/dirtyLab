"""Evaluation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import EvaluationIn, EvaluationOut
from app.schemas.repositories import evaluation_to_schema
from app.services import evaluation_repo, experiment_repo

router = APIRouter()


@router.put("/artifacts/{artifact_id}", response_model=EvaluationOut)
def upsert_evaluation(
    artifact_id: str,
    payload: EvaluationIn,
    db: Session = Depends(get_db),
) -> EvaluationOut:
    experiment_repo.get_artifact(db, artifact_id)  # validates existence
    obj = evaluation_repo.upsert_evaluation(
        db,
        artifact_id=artifact_id,
        status=payload.status,
        overall_score=payload.overall_score,
        notes=payload.notes,
        is_complete=payload.is_complete,
        provenance=payload.provenance,
        dimension_scores=[d.model_dump() for d in payload.dimension_scores],
        tags=[t.model_dump() for t in payload.tags],
    )
    return evaluation_to_schema(obj)


@router.get("/artifacts/{artifact_id}", response_model=EvaluationOut | None)
def get_evaluation(artifact_id: str, db: Session = Depends(get_db)) -> EvaluationOut | None:
    obj = evaluation_repo.get_evaluation_for_artifact(db, artifact_id)
    return evaluation_to_schema(obj) if obj else None
