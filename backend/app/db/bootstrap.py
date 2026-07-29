"""Schema bootstrap + first-run seeding.

This is the migration strategy for v1: ``create_all`` builds the initial
schema, and the seed function ensures exactly one connection slot, one active
scoring template with default dimensions/tags, and a starting provider slot
remain available. Future schema changes will be handled by Alembic migrations
under ``backend/alembic``; this module stamps the baseline.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Base,
    FailureTag,
    Provider,
    QualityDimension,
    ScoringTemplate,
)

DEFAULT_DIMENSIONS = [
    ("overall_alignment", "Overall alignment with goal"),
    ("artifact_quality", "Artifact / detail quality"),
    ("coherence", "Coherence / anatomical plausibility"),
    ("style_match", "Style match"),
    ("prompt_adherence", "Prompt adherence"),
]

DEFAULT_TAGS = [
    ("wrong_subject", "Wrong subject"),
    ("extra_limbs", "Extra / missing limbs"),
    ("blurred", "Blurred / low detail"),
    ("color_cast", "Wrong color / lighting"),
    ("composition", "Bad composition"),
    ("artifacts", "Compression / model artifacts"),
    ("oversmoothed", "Over-smoothed / plastic"),
    ("other", "Other"),
]


def create_schema(engine) -> None:
    Base.metadata.create_all(engine)


def ensure_seed_data(db: Session) -> None:
    """Make sure there is exactly one active scoring template with the default
    dimensions/tags. Existing templates are left untouched."""
    active_template = db.scalar(
        select(ScoringTemplate).where(ScoringTemplate.is_active.is_(True))
    )
    if active_template is None:
        template = ScoringTemplate(version=1, is_active=True)
        db.add(template)
        db.flush()
        for idx, (key, label) in enumerate(DEFAULT_DIMENSIONS):
            db.add(
                QualityDimension(
                    template_id=template.id,
                    key=key,
                    label=label,
                    order_index=idx,
                )
            )
        for idx, (key, label) in enumerate(DEFAULT_TAGS):
            db.add(
                FailureTag(
                    template_id=template.id,
                    key=key,
                    label=label,
                    order_index=idx,
                )
            )
    # Provider slot is optional; do not auto-create.
    # Connection slot is enforced as unique by the API (at most one active row).
    _ = db.scalar(select(Provider).where(Provider.is_active.is_(True)))
    db.commit()
