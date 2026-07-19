"""Analysis endpoints - placeholder, real implementation in section 6."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.db.base import get_db
from app.schemas import AnalysisConfirmIn, AnalysisOut, AnalysisRequestIn
from app.schemas.repositories import analysis_to_schema
from app.services import analysis_repo, connection_repo, experiment_repo
from app.services import multimodal as multimodal_service


router = APIRouter()


@router.post("/experiments/{experiment_id}/request", response_model=AnalysisOut)
def request_analysis(
    experiment_id: str,
    payload: AnalysisRequestIn,
    db: Session = Depends(get_db),
) -> AnalysisOut:
    experiment = experiment_repo.get_experiment(db, experiment_id)
    provider = connection_repo.get_active_provider(db)
    if provider is None:
        raise ValidationError(
            "No AI provider is configured. Open AI Provider first.",
            details={"experiment_id": experiment_id},
        )
    if not payload.artifact_ids:
        raise ValidationError("At least one candidate artifact is required")
    artifacts = [experiment_repo.get_artifact(db, aid) for aid in payload.artifact_ids]
    return analysis_to_schema(
        multimodal_service.request_analysis(
            db,
            experiment=experiment,
            provider=provider,
            artifacts=artifacts,
            goal_override=payload.goal_override,
            include_comparison_context=payload.include_comparison_context,
        )
    )


@router.post("/{analysis_id}/confirm", response_model=AnalysisOut)
def confirm_analysis(
    analysis_id: str,
    payload: AnalysisConfirmIn,
    db: Session = Depends(get_db),
) -> AnalysisOut:
    analysis = analysis_repo.get_analysis(db, analysis_id)
    return analysis_to_schema(
        multimodal_service.confirm_analysis(db, analysis, payload.model_dump())
    )


@router.get("/experiments/{experiment_id}", response_model=list[AnalysisOut])
def list_analyses(experiment_id: str, db: Session = Depends(get_db)) -> list[AnalysisOut]:
    return [
        analysis_to_schema(a)
        for a in analysis_repo.list_analyses_for_experiment(db, experiment_id)
    ]
