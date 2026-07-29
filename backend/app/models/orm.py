"""SQLAlchemy ORM models.

Layout mirrors the data model in
``openspec/changes/build-comfyui-experiment-platform/design.md``:

- ``Connection``: one AutoDL SSH connection.
- ``Provider``: one multimodal API provider config.
- ``Experiment``: long-lived container with one original image + goal.
- ``Snapshot``: immutable result of one sync.
- ``Artifact``: file recorded in a snapshot (image, mask, workflow, metadata).
- ``ScoringTemplate`` + ``QualityDimension`` + ``FailureTag``: evaluation template
  with versioned rows; disabled historical dimensions retain their label.
- ``Evaluation``: per-candidate human evaluation with status, overall score,
  dimension scores, tags, notes, and provenance.
- ``EvaluationDimensionScore``: per-dimension score referencing a template row.
- ``EvaluationTag``: per-evaluation tag reference.
- ``Analysis``: AI provider draft + confirmation state, linked to candidate(s).
- ``AnalysisCandidate``: many-to-many between analysis and artifact candidates.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String, default="default")
    host: Mapped[str] = mapped_column(String, nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String, nullable=False)
    private_key_ref: Mapped[str] = mapped_column(
        String, nullable=False
    )  # path inside secrets dir, NOT the key material
    remote_root: Mapped[str] = mapped_column(String, nullable=False)
    comfyui_input_path: Mapped[str] = mapped_column(
        String, default="input"
    )
    comfyui_output_prefix: Mapped[str] = mapped_column(
        String, default="ComfyUI_"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_test_status: Mapped[str | None] = mapped_column(String, nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String, default="openai_compatible")
    label: Mapped[str] = mapped_column(String, default="default")
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    api_key_ref: Mapped[str] = mapped_column(
        String, nullable=False
    )  # filename inside secrets dir
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    original_extension: Mapped[str] = mapped_column(String, nullable=False)
    original_checksum: Mapped[str] = mapped_column(String, nullable=False)
    remote_workspace_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    snapshots: Mapped[list[Snapshot]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan", order_by="Snapshot.created_at"
    )


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # success|partial|failed|empty
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ignored_count: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    experiment: Mapped[Experiment] = relationship(back_populates="snapshots")
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), index=True)
    relative_path: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    # original_image | mask | saved_image | workflow_json | metadata | input
    remote_path: Mapped[str] = mapped_column(String, nullable=False)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    transfer_status: Mapped[str] = mapped_column(String, default="transferred")
    # transferred | failed | pending | unstable
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    snapshot: Mapped[Snapshot] = relationship(back_populates="artifacts")
    extracted_metadata: Mapped[list[ExtractedMetadata]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )


class ExtractedMetadata(Base):
    """Best-effort extracted values from a workflow JSON or image file.

    Each row stores one field with an explicit ``unknown`` flag so the UI never
    has to guess whether a value was actually recovered.
    """

    __tablename__ = "extracted_metadata"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_unknown: Mapped[bool] = mapped_column(Boolean, default=True)
    is_user_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    artifact: Mapped[Artifact] = relationship(back_populates="extracted_metadata")


class ScoringTemplate(Base):
    """Versioned template of dimensions + tags used by new evaluations."""

    __tablename__ = "scoring_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    dimensions: Mapped[list[QualityDimension]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="QualityDimension.order_index",
    )
    tags: Mapped[list[FailureTag]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="FailureTag.order_index",
    )


class QualityDimension(Base):
    __tablename__ = "quality_dimensions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(ForeignKey("scoring_templates.id"), index=True)
    key: Mapped[str] = mapped_column(String, nullable=False)  # stable key
    label: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    template: Mapped[ScoringTemplate] = relationship(back_populates="dimensions")


class FailureTag(Base):
    __tablename__ = "failure_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(ForeignKey("scoring_templates.id"), index=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    template: Mapped[ScoringTemplate] = relationship(back_populates="tags")


class Evaluation(Base):
    """Per-candidate (per-artifact) human evaluation.

    ``provenance`` is one of ``human``, ``ai_confirmed``, ``ai_edited``. The
    ``is_complete`` flag covers the spec's partial-evaluation scenario.
    """

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    # success | partial_success | failure
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    provenance: Mapped[str] = mapped_column(String, default="human")
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    dimension_scores: Mapped[list[EvaluationDimensionScore]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    tags: Mapped[list[EvaluationTag]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationDimensionScore(Base):
    __tablename__ = "evaluation_dimension_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"), index=True)
    dimension_label: Mapped[str] = mapped_column(String, nullable=False)  # snapshot label
    dimension_key: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    evaluation: Mapped[Evaluation] = relationship(back_populates="dimension_scores")


class EvaluationTag(Base):
    __tablename__ = "evaluation_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"), index=True)
    tag_label: Mapped[str] = mapped_column(String, nullable=False)
    tag_key: Mapped[str] = mapped_column(String, nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="tags")


class Analysis(Base):
    """Editable AI analysis draft + confirmation state."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    provider_kind: Mapped[str] = mapped_column(String, nullable=False)
    provider_model: Mapped[str] = mapped_column(String, nullable=False)
    request_context: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    raw_response: Mapped[str] = mapped_column(Text, default="")  # JSON, no secrets
    status: Mapped[str] = mapped_column(String, default="pending")
    # pending | success | failed
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # suggestions stored as JSON (failure_causes, scores, next_steps)
    suggestions: Mapped[str] = mapped_column(Text, default="{}")
    confirmed_overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_status: Mapped[str | None] = mapped_column(String, nullable=True)
    confirmed_notes: Mapped[str] = mapped_column(Text, default="")
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    rejected_fields: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    candidates: Mapped[list[AnalysisCandidate]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class AnalysisCandidate(Base):
    __tablename__ = "analysis_candidates"
    __table_args__ = (UniqueConstraint("analysis_id", "artifact_id", name="uq_analysis_artifact"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)

    analysis: Mapped[Analysis] = relationship(back_populates="candidates")
