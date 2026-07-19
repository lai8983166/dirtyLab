"""Pydantic mappers from ORM models to API schemas."""
from __future__ import annotations

from app.models import (
    Analysis,
    Artifact,
    Connection,
    Evaluation,
    Experiment,
    Provider,
    ScoringTemplate,
    Snapshot,
)
from app.schemas import (
    AnalysisOut,
    ArtifactOut,
    ConnectionOut,
    DimensionOut,
    EvaluationOut,
    ExperimentDetail,
    ExperimentOut,
    ExtractedMetadataOut,
    ProviderOut,
    SnapshotOut,
    TagOut,
    TemplateOut,
)


def connection_to_schema(obj: Connection) -> ConnectionOut:
    return ConnectionOut(
        id=obj.id,
        host=obj.host,
        port=obj.port,
        username=obj.username,
        private_key_ref=obj.private_key_ref,
        remote_root=obj.remote_root,
        comfyui_input_path=obj.comfyui_input_path,
        comfyui_output_prefix=obj.comfyui_output_prefix,
        last_test_status=obj.last_test_status,
        last_test_at=obj.last_test_at,
        last_test_detail=obj.last_test_detail,
    )


def provider_to_schema(obj: Provider) -> ProviderOut:
    return ProviderOut(
        id=obj.id,
        kind=obj.kind,
        label=obj.label,
        base_url=obj.base_url,
        model=obj.model,
        api_key_ref=obj.api_key_ref,
    )


def experiment_to_schema(obj: Experiment) -> ExperimentOut:
    return ExperimentOut(
        id=obj.id,
        name=obj.name,
        goal=obj.goal,
        original_filename=obj.original_filename,
        original_extension=obj.original_extension,
        original_checksum=obj.original_checksum,
        remote_workspace_path=obj.remote_workspace_path,
        status=obj.status,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def artifact_to_schema(obj: Artifact) -> ArtifactOut:
    return ArtifactOut(
        id=obj.id,
        snapshot_id=obj.snapshot_id,
        relative_path=obj.relative_path,
        kind=obj.kind,
        checksum=obj.checksum,
        size_bytes=obj.size_bytes,
        transfer_status=obj.transfer_status,
        error_detail=obj.error_detail,
        extracted_metadata=[
            ExtractedMetadataOut(
                field_name=m.field_name,
                field_value=m.field_value,
                is_unknown=m.is_unknown,
                is_user_corrected=m.is_user_corrected,
            )
            for m in obj.extracted_metadata
        ],
    )


def snapshot_to_schema(obj: Snapshot, *, include_artifacts: bool = True) -> SnapshotOut:
    return SnapshotOut(
        id=obj.id,
        experiment_id=obj.experiment_id,
        number=obj.number,
        status=obj.status,
        source_path=obj.source_path,
        ignored_count=obj.ignored_count,
        error_detail=obj.error_detail,
        started_at=obj.started_at,
        finished_at=obj.finished_at,
        created_at=obj.created_at,
        artifacts=[artifact_to_schema(a) for a in obj.artifacts] if include_artifacts else [],
    )


def evaluation_to_schema(obj: Evaluation) -> EvaluationOut:
    return EvaluationOut(
        id=obj.id,
        artifact_id=obj.artifact_id,
        status=obj.status,
        overall_score=obj.overall_score,
        notes=obj.notes,
        is_complete=obj.is_complete,
        provenance=obj.provenance,
        template_version=obj.template_version,
        dimension_scores=[
            {"key": s.dimension_key, "label": s.dimension_label, "score": s.score}
            for s in obj.dimension_scores
        ],
        tags=[{"key": t.tag_key, "label": t.tag_label} for t in obj.tags],
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def template_to_schema(obj: ScoringTemplate) -> TemplateOut:
    return TemplateOut(
        id=obj.id,
        version=obj.version,
        is_active=obj.is_active,
        created_at=obj.created_at,
        dimensions=[
            DimensionOut(
                id=d.id,
                key=d.key,
                label=d.label,
                order_index=d.order_index,
                is_disabled=d.is_disabled,
            )
            for d in obj.dimensions
        ],
        tags=[
            TagOut(
                id=t.id,
                key=t.key,
                label=t.label,
                order_index=t.order_index,
                is_disabled=t.is_disabled,
            )
            for t in obj.tags
        ],
    )


def analysis_to_schema(obj: Analysis) -> AnalysisOut:
    import json

    return AnalysisOut(
        id=obj.id,
        experiment_id=obj.experiment_id,
        provider_kind=obj.provider_kind,
        provider_model=obj.provider_model,
        status=obj.status,
        error_detail=obj.error_detail,
        suggestions=json.loads(obj.suggestions) if obj.suggestions else {},
        is_confirmed=obj.is_confirmed,
        is_rejected=obj.is_rejected,
        confirmed_overall_score=obj.confirmed_overall_score,
        confirmed_status=obj.confirmed_status,
        confirmed_notes=obj.confirmed_notes or "",
        requested_at=obj.requested_at,
        completed_at=obj.completed_at,
        confirmed_at=obj.confirmed_at,
    )


def experiment_detail_schema(
    experiment: Experiment,
    *,
    snapshots: list[Snapshot] | None = None,
    evaluations: list[Evaluation] | None = None,
    analyses: list[Analysis] | None = None,
) -> ExperimentDetail:
    return ExperimentDetail(
        **experiment_to_schema(experiment).model_dump(),
        snapshots=[snapshot_to_schema(s) for s in (snapshots or [])],
        evaluations=[evaluation_to_schema(e) for e in (evaluations or [])],
        analyses=[analysis_to_schema(a) for a in (analyses or [])],
    )
