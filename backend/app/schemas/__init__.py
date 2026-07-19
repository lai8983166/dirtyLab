"""Pydantic schemas for the API surface."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ----- generic -----


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    artifacts_dir: str
    version: str = "0.1.0"


# ----- connection -----


class ConnectionIn(BaseModel):
    host: str
    port: int = 22
    username: str
    private_key: str  # raw key bytes (text) - stored as a local secret
    remote_root: str
    comfyui_input_path: str = "input"
    comfyui_output_prefix: str = "ComfyUI_"


class ConnectionOut(BaseModel):
    id: str
    host: str
    port: int
    username: str
    private_key_ref: str
    remote_root: str
    comfyui_input_path: str
    comfyui_output_prefix: str
    last_test_status: str | None
    last_test_at: datetime | None
    last_test_detail: str | None


class ConnectionTestResult(BaseModel):
    ok: bool
    stage: str  # ssh_access | remote_root | comfyui_input | comfyui_output
    detail: str | None
    resolved_paths: dict[str, str] | None = None


# ----- provider -----


class ProviderIn(BaseModel):
    kind: str = "openai_compatible"
    base_url: str
    model: str
    api_key: str


class ProviderOut(BaseModel):
    id: str
    kind: str
    label: str
    base_url: str
    model: str
    api_key_ref: str


# ----- experiment -----


class ExperimentOut(BaseModel):
    id: str
    name: str
    goal: str
    original_filename: str
    original_extension: str
    original_checksum: str
    remote_workspace_path: str
    status: str
    created_at: datetime
    updated_at: datetime


class ExperimentCreate(BaseModel):
    name: str
    goal: str = ""


class ExperimentDetail(ExperimentOut):
    snapshots: list["SnapshotOut"] = Field(default_factory=list)
    evaluations: list["EvaluationOut"] = Field(default_factory=list)
    analyses: list["AnalysisOut"] = Field(default_factory=list)


# ----- snapshot / artifact -----


class ExtractedMetadataOut(BaseModel):
    field_name: str
    field_value: str
    is_unknown: bool
    is_user_corrected: bool


class ArtifactOut(BaseModel):
    id: str
    snapshot_id: str
    relative_path: str
    kind: str
    checksum: str
    size_bytes: int
    transfer_status: str
    error_detail: str | None
    extracted_metadata: list[ExtractedMetadataOut] = Field(default_factory=list)


class SnapshotOut(BaseModel):
    id: str
    experiment_id: str
    number: int
    status: str
    source_path: str
    ignored_count: int
    error_detail: str | None
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime
    artifacts: list[ArtifactOut] = Field(default_factory=list)


class SyncResultOut(BaseModel):
    snapshot: SnapshotOut
    partial_failures: list[dict[str, Any]] = Field(default_factory=list)
    ignored_count: int
    retryable: bool


class MetadataCorrectionIn(BaseModel):
    field_name: str
    field_value: str
    is_unknown: bool = False


# ----- scoring template -----


class DimensionIn(BaseModel):
    key: str
    label: str
    order: int = 0
    disabled: bool = False


class TagIn(BaseModel):
    key: str
    label: str
    order: int = 0
    disabled: bool = False


class TemplateIn(BaseModel):
    dimensions: list[DimensionIn]
    tags: list[TagIn] = Field(default_factory=list)


class DimensionOut(BaseModel):
    id: str
    key: str
    label: str
    order_index: int
    is_disabled: bool


class TagOut(BaseModel):
    id: str
    key: str
    label: str
    order_index: int
    is_disabled: bool


class TemplateOut(BaseModel):
    id: str
    version: int
    is_active: bool
    created_at: datetime
    dimensions: list[DimensionOut]
    tags: list[TagOut]


# ----- evaluation -----


class DimensionScoreIn(BaseModel):
    key: str
    label: str
    score: int | None = Field(default=None, ge=1, le=10)


class EvaluationTagIn(BaseModel):
    key: str
    label: str


class EvaluationIn(BaseModel):
    status: Literal["success", "partial_success", "failure"]
    overall_score: int | None = Field(default=None, ge=1, le=10)
    notes: str = ""
    is_complete: bool = True
    provenance: Literal["human", "ai_confirmed", "ai_edited"] = "human"
    dimension_scores: list[DimensionScoreIn] = Field(default_factory=list)
    tags: list[EvaluationTagIn] = Field(default_factory=list)


class EvaluationOut(BaseModel):
    id: str
    artifact_id: str
    status: str
    overall_score: int | None
    notes: str
    is_complete: bool
    provenance: str
    template_version: int
    dimension_scores: list[dict[str, Any]]
    tags: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


# ----- analysis -----


class AnalysisRequestIn(BaseModel):
    artifact_ids: list[str]
    goal_override: str | None = None
    include_comparison_context: bool = False


class AnalysisOut(BaseModel):
    id: str
    experiment_id: str
    provider_kind: str
    provider_model: str
    status: str
    error_detail: str | None
    suggestions: dict[str, Any]
    is_confirmed: bool
    is_rejected: bool
    confirmed_overall_score: int | None
    confirmed_status: str | None
    confirmed_notes: str
    requested_at: datetime
    completed_at: datetime | None
    confirmed_at: datetime | None


class AnalysisConfirmIn(BaseModel):
    overall_score: int | None = Field(default=None, ge=1, le=10)
    status: Literal["success", "partial_success", "failure"] | None = None
    notes: str = ""
    rejected_fields: list[str] = Field(default_factory=list)


ExperimentDetail.model_rebuild()
