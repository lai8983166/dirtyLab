"""Evaluation repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models import (
    Artifact,
    Evaluation,
    EvaluationDimensionScore,
    EvaluationTag,
    Snapshot,
)
from app.services.template_repo import get_active_template


VALID_STATUSES = {"success", "partial_success", "failure"}
VALID_PROVENANCE = {"human", "ai_confirmed", "ai_edited"}


def get_evaluation(db: Session, evaluation_id: str) -> Evaluation:
    obj = db.get(Evaluation, evaluation_id)
    if obj is None:
        raise NotFoundError("Evaluation not found", details={"id": evaluation_id})
    return obj


def upsert_evaluation(
    db: Session,
    *,
    artifact_id: str,
    status: str,
    overall_score: int | None,
    notes: str,
    is_complete: bool,
    provenance: str = "human",
    dimension_scores: list[dict] | None = None,
    tags: list[dict] | None = None,
) -> Evaluation:
    if status not in VALID_STATUSES:
        raise ValidationError(
            f"Invalid status {status}",
            details={"allowed": sorted(VALID_STATUSES)},
        )
    if provenance not in VALID_PROVENANCE:
        raise ValidationError(
            f"Invalid provenance {provenance}",
            details={"allowed": sorted(VALID_PROVENANCE)},
        )
    if overall_score is not None and not (1 <= overall_score <= 10):
        raise ValidationError("Overall score must be between 1 and 10")

    template = get_active_template(db)
    existing = db.scalar(select(Evaluation).where(Evaluation.artifact_id == artifact_id))
    if existing is None:
        obj = Evaluation(
            artifact_id=artifact_id,
            status=status,
            overall_score=overall_score,
            notes=notes or "",
            is_complete=is_complete,
            provenance=provenance,
            template_version=template.version,
        )
        db.add(obj)
    else:
        existing.status = status
        existing.overall_score = overall_score
        existing.notes = notes or ""
        existing.is_complete = is_complete
        existing.provenance = provenance
        # template_version stays pinned to the version at first save so
        # historical labels remain valid even if the template changes later.
        obj = existing

    # Wipe + reinsert dimension/tag scores for simplicity.
    if existing is not None:
        for child in list(existing.dimension_scores):
            db.delete(child)
        for child in list(existing.tags):
            db.delete(child)
    db.flush()

    for d in dimension_scores or []:
        score = d.get("score")
        if score is not None and not (1 <= int(score) <= 10):
            raise ValidationError(f"Dimension score out of range: {score}")
        db.add(
            EvaluationDimensionScore(
                evaluation_id=obj.id,
                dimension_key=d["key"],
                dimension_label=d["label"],
                score=int(score) if score is not None else None,
            )
        )
    for t in tags or []:
        db.add(
            EvaluationTag(
                evaluation_id=obj.id,
                tag_key=t["key"],
                tag_label=t["label"],
            )
        )
    db.commit()
    db.refresh(obj)
    return obj


def list_evaluations_for_experiment(db: Session, experiment_id: str) -> list[Evaluation]:
    return list(
        db.scalars(
            select(Evaluation)
            .join(Artifact, Artifact.id == Evaluation.artifact_id)
            .join(Snapshot, Snapshot.id == Artifact.snapshot_id)
            .where(Snapshot.experiment_id == experiment_id)
            .order_by(Evaluation.updated_at.desc())
        )
    )
