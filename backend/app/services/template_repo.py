"""Scoring template repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models import FailureTag, QualityDimension, ScoringTemplate


def get_active_template(db: Session) -> ScoringTemplate:
    obj = db.scalar(select(ScoringTemplate).where(ScoringTemplate.is_active.is_(True)))
    if obj is None:
        raise NotFoundError("No active scoring template")
    return obj


def list_templates(db: Session) -> list[ScoringTemplate]:
    return list(
        db.scalars(select(ScoringTemplate).order_by(ScoringTemplate.version.desc()))
    )


def get_template(db: Session, template_id: str) -> ScoringTemplate:
    obj = db.get(ScoringTemplate, template_id)
    if obj is None:
        raise NotFoundError("Template not found", details={"id": template_id})
    return obj


def new_template_version(
    db: Session,
    *,
    dimensions: list[dict],
    tags: list[dict],
) -> ScoringTemplate:
    """Create a new versioned template. Previous active template is marked
    inactive; its dimensions/tags remain so historical evaluations keep their
    label references."""
    previous = db.scalar(select(ScoringTemplate).where(ScoringTemplate.is_active.is_(True)))
    next_version = (previous.version + 1) if previous else 1
    if previous:
        previous.is_active = False
    template = ScoringTemplate(version=next_version, is_active=True)
    db.add(template)
    db.flush()
    if not dimensions:
        raise ValidationError("At least one quality dimension is required")
    for idx, d in enumerate(dimensions):
        db.add(
            QualityDimension(
                template_id=template.id,
                key=d["key"],
                label=d["label"],
                order_index=d.get("order", idx),
                is_disabled=bool(d.get("disabled", False)),
            )
        )
    for idx, t in enumerate(tags):
        db.add(
            FailureTag(
                template_id=template.id,
                key=t["key"],
                label=t["label"],
                order_index=t.get("order", idx),
                is_disabled=bool(t.get("disabled", False)),
            )
        )
    db.commit()
    db.refresh(template)
    return template


def update_dimension(
    db: Session,
    *,
    dimension_id: str,
    label: str | None = None,
    order_index: int | None = None,
    is_disabled: bool | None = None,
) -> QualityDimension:
    obj = db.get(QualityDimension, dimension_id)
    if obj is None:
        raise NotFoundError("Dimension not found", details={"id": dimension_id})
    if not obj.template.is_active:
        raise ValidationError("Cannot edit a dimension in an inactive (historical) template")
    if label is not None:
        obj.label = label
    if order_index is not None:
        obj.order_index = order_index
    if is_disabled is not None:
        obj.is_disabled = is_disabled
    db.commit()
    db.refresh(obj)
    return obj


def update_tag(
    db: Session,
    *,
    tag_id: str,
    label: str | None = None,
    order_index: int | None = None,
    is_disabled: bool | None = None,
) -> FailureTag:
    obj = db.get(FailureTag, tag_id)
    if obj is None:
        raise NotFoundError("Tag not found", details={"id": tag_id})
    if not obj.template.is_active:
        raise ValidationError("Cannot edit a tag in an inactive (historical) template")
    if label is not None:
        obj.label = label
    if order_index is not None:
        obj.order_index = order_index
    if is_disabled is not None:
        obj.is_disabled = is_disabled
    db.commit()
    db.refresh(obj)
    return obj
