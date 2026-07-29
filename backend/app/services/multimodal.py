"""Multimodal analysis service.

Implements spec:
- Trigger analysis explicitly (6.3). Synchronization never calls the model.
- Store editable AI analysis (6.4).
- Confirm analysis selectively (6.5 backend).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import AppConfig
from app.core.errors import ProviderError, ValidationError
from app.core.logging import get_logger
from app.models import Analysis, Artifact
from app.providers import AnalysisContext, get_provider
from app.services import analysis_repo, experiment_repo

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Experiment, Provider


def request_analysis(
    db: Session,
    *,
    experiment: Experiment,
    provider: Provider,
    artifacts: list[Artifact],
    goal_override: str | None,
    include_comparison_context: bool,
) -> Analysis:
    log = get_logger("multimodal.request")
    if not artifacts:
        raise ValidationError("At least one artifact is required")
    cfg = AppConfig.load()
    provider_adapter = get_provider(provider.kind)
    # Build request context - never include secrets.
    metadata_summary: dict[str, str] = {}
    for artifact in artifacts:
        for m in artifact.extracted_metadata:
            value = "<unknown>" if m.is_unknown else m.field_value
            metadata_summary.setdefault(m.field_name, value)
    workflow_json = None
    for artifact in artifacts:
        if artifact.kind == "workflow_json":
            try:
                workflow_json = Path(artifact.local_path).read_text(encoding="utf-8")
            except Exception:
                pass
            break

    confirmed_evaluations = []
    if include_comparison_context:
        for artifact in artifacts:
            ev = experiment_repo.get_evaluation_for_artifact(db, artifact.id)
            if ev:
                confirmed_evaluations.append(
                    {
                        "status": ev.status,
                        "overall_score": ev.overall_score,
                        "notes": ev.notes,
                    }
                )

    context = AnalysisContext(
        goal=goal_override or experiment.goal,
        artifact_local_paths=[a.local_path for a in artifacts if a.local_path],
        workflow_json=workflow_json,
        metadata_summary=metadata_summary,
        confirmed_evaluations=confirmed_evaluations,
        include_comparison_context=include_comparison_context,
    )

    analysis = analysis_repo.create_pending_analysis(
        db,
        experiment_id=experiment.id,
        provider_id=provider.id,
        provider_kind=provider.kind,
        provider_model=provider.model,
        request_context={
            "goal": context.goal,
            "artifact_ids": [a.id for a in artifacts],
            "metadata_summary": metadata_summary,
            "include_comparison_context": include_comparison_context,
        },
        artifact_ids=[a.id for a in artifacts],
    )
    try:
        result = provider_adapter.analyze(
            cfg,
            provider.api_key_ref,
            provider.base_url,
            provider.model,
            context,
        )
    except ProviderError as exc:
        log.info("multimodal.provider_failed", analysis_id=analysis.id, code=exc.code)
        return analysis_repo.record_analysis_failure(db, analysis, detail=exc.message)
    except Exception as exc:  # pragma: no cover - defensive
        log.info("multimodal.unexpected_error", analysis_id=analysis.id, error=str(exc))
        return analysis_repo.record_analysis_failure(db, analysis, detail=str(exc))
    return analysis_repo.record_analysis_success(
        db,
        analysis,
        raw_response=result.raw_response,
        suggestions=result.suggestions,
    )


def confirm_analysis(db: Session, analysis: Analysis, payload: dict) -> Analysis:
    """Apply user confirm/reject. Spec: distinguish confirmed user decisions
    from unconfirmed model output."""
    rejected_fields = list(payload.get("rejected_fields") or [])
    # If the user only rejected fields, store the rejection but don't flip the
    # is_confirmed flag unless they actually accept something.
    if rejected_fields and not payload.get("status") and payload.get("notes", "") == "":
        return analysis_repo.reject_fields(db, analysis, fields=rejected_fields)
    return analysis_repo.confirm_analysis(
        db,
        analysis,
        overall_score=payload.get("overall_score"),
        status=payload.get("status"),
        notes=payload.get("notes", "") or "",
        rejected_fields=rejected_fields,
    )
