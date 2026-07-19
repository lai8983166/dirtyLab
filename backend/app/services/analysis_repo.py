"""AI analysis repository."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Analysis, AnalysisCandidate, Artifact, Snapshot


def get_analysis(db: Session, analysis_id: str) -> Analysis:
    obj = db.get(Analysis, analysis_id)
    if obj is None:
        raise NotFoundError("Analysis not found", details={"id": analysis_id})
    return obj


def list_analyses_for_experiment(db: Session, experiment_id: str) -> list[Analysis]:
    return list(
        db.scalars(
            select(Analysis)
            .where(Analysis.experiment_id == experiment_id)
            .order_by(Analysis.requested_at.desc())
        )
    )


def create_pending_analysis(
    db: Session,
    *,
    experiment_id: str,
    provider_id: str,
    provider_kind: str,
    provider_model: str,
    request_context: dict,
    artifact_ids: list[str],
) -> Analysis:
    obj = Analysis(
        experiment_id=experiment_id,
        provider_id=provider_id,
        provider_kind=provider_kind,
        provider_model=provider_model,
        request_context=json.dumps(request_context),
        status="pending",
    )
    db.add(obj)
    db.flush()
    for aid in artifact_ids:
        db.add(AnalysisCandidate(analysis_id=obj.id, artifact_id=aid))
    db.commit()
    db.refresh(obj)
    return obj


def record_analysis_success(
    db: Session,
    analysis: Analysis,
    *,
    raw_response: dict,
    suggestions: dict,
) -> Analysis:
    analysis.status = "success"
    analysis.raw_response = json.dumps(raw_response)
    analysis.suggestions = json.dumps(suggestions)
    analysis.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(analysis)
    return analysis


def record_analysis_failure(db: Session, analysis: Analysis, *, detail: str) -> Analysis:
    analysis.status = "failed"
    analysis.error_detail = detail
    analysis.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(analysis)
    return analysis


def confirm_analysis(
    db: Session,
    analysis: Analysis,
    *,
    overall_score: int | None,
    status: str | None,
    notes: str,
    rejected_fields: list[str] | None = None,
) -> Analysis:
    analysis.confirmed_overall_score = overall_score
    analysis.confirmed_status = status
    analysis.confirmed_notes = notes
    analysis.is_confirmed = True
    analysis.is_rejected = False
    analysis.confirmed_at = datetime.utcnow()
    analysis.rejected_fields = json.dumps(rejected_fields or [])
    db.commit()
    db.refresh(analysis)
    return analysis


def reject_fields(
    db: Session, analysis: Analysis, *, fields: list[str]
) -> Analysis:
    analysis.rejected_fields = json.dumps(fields)
    analysis.is_rejected = True
    analysis.is_confirmed = False
    db.commit()
    db.refresh(analysis)
    return analysis


def get_suggestions(analysis: Analysis) -> dict:
    if not analysis.suggestions:
        return {}
    return json.loads(analysis.suggestions)


def get_request_context(analysis: Analysis) -> dict:
    if not analysis.request_context:
        return {}
    return json.loads(analysis.request_context)
