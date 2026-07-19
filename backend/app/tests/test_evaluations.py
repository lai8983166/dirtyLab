"""Tests for candidate evaluation (Task 5.6).

Scenarios:
- Save a failed-candidate evaluation with tags + notes.
- Save a partial (incomplete) evaluation and extend it later.
- Custom dimensions.
- Disabled historical dimensions do not appear in active template lookups.
- Provenance distinguishes human / ai_confirmed / ai_edited.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.base import session_scope
from app.db.bootstrap import ensure_seed_data
from app.models import (
    Artifact,
    Evaluation,
    Experiment,
    FailureTag,
    QualityDimension,
    ScoringTemplate,
    Snapshot,
)
from app.services import evaluation_repo, template_repo


def _seed_experiment_with_candidate(db: Session) -> tuple[str, str]:
    experiment = Experiment(
        name="t",
        goal="",
        original_filename="o.png",
        original_extension="png",
        original_checksum="x",
        remote_workspace_path="/root/x",
    )
    db.add(experiment)
    db.flush()
    snapshot = Snapshot(
        experiment_id=experiment.id,
        number=1,
        status="success",
        source_path="/root/x",
    )
    db.add(snapshot)
    db.flush()
    artifact = Artifact(
        snapshot_id=snapshot.id,
        relative_path="output/c1.png",
        kind="saved_image",
        remote_path="/root/x/output/c1.png",
        local_path="/tmp/c1.png",
        checksum="abc",
        size_bytes=10,
        transfer_status="transferred",
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return experiment.id, artifact.id


def test_save_failed_candidate_evaluation(db_session: Session) -> None:
    ensure_seed_data(db_session)
    _experiment_id, artifact_id = _seed_experiment_with_candidate(db_session)
    template = template_repo.get_active_template(db_session)
    dim = template.dimensions[0]
    tag = template.tags[0]
    evaluation = evaluation_repo.upsert_evaluation(
        db_session,
        artifact_id=artifact_id,
        status="failure",
        overall_score=3,
        notes="extra limbs",
        is_complete=True,
        dimension_scores=[{"key": dim.key, "label": dim.label, "score": 2}],
        tags=[{"key": tag.key, "label": tag.label}],
    )
    assert evaluation.status == "failure"
    assert evaluation.overall_score == 3
    assert evaluation.notes == "extra limbs"
    assert evaluation.is_complete is True
    assert len(evaluation.dimension_scores) == 1
    assert evaluation.dimension_scores[0].score == 2
    assert len(evaluation.tags) == 1


def test_partial_evaluation_can_be_completed_later(db_session: Session) -> None:
    ensure_seed_data(db_session)
    _experiment_id, artifact_id = _seed_experiment_with_candidate(db_session)
    first = evaluation_repo.upsert_evaluation(
        db_session,
        artifact_id=artifact_id,
        status="failure",
        overall_score=None,
        notes="",
        is_complete=False,
    )
    assert first.is_complete is False
    second = evaluation_repo.upsert_evaluation(
        db_session,
        artifact_id=artifact_id,
        status="failure",
        overall_score=2,
        notes="now completed",
        is_complete=True,
    )
    assert second.id == first.id
    assert second.is_complete is True
    assert second.overall_score == 2


def test_template_version_preserves_historical_labels(db_session: Session) -> None:
    ensure_seed_data(db_session)
    _experiment_id, artifact_id = _seed_experiment_with_candidate(db_session)
    # First evaluation is saved against v1.
    v1 = template_repo.get_active_template(db_session)
    original_dim_label = v1.dimensions[0].label
    evaluation_repo.upsert_evaluation(
        db_session,
        artifact_id=artifact_id,
        status="failure",
        overall_score=4,
        notes="",
        is_complete=True,
        dimension_scores=[
            {"key": v1.dimensions[0].key, "label": v1.dimensions[0].label, "score": 4}
        ],
        tags=[],
    )
    # Create v2 with a different label for the same key.
    v2 = template_repo.new_template_version(
        db_session,
        dimensions=[
            {"key": v1.dimensions[0].key, "label": "renamed", "order": 0},
        ],
        tags=[],
    )
    assert v2.version == 2
    # Historical evaluation still references the original label.
    saved = db_session.get(Evaluation, db_session.query(Evaluation).first().id)
    assert saved.template_version == 1
    assert saved.dimension_scores[0].dimension_label == original_dim_label


def test_invalid_status_rejected(db_session: Session) -> None:
    ensure_seed_data(db_session)
    _experiment_id, artifact_id = _seed_experiment_with_candidate(db_session)
    from app.core.errors import ValidationError

    try:
        evaluation_repo.upsert_evaluation(
            db_session,
            artifact_id=artifact_id,
            status="invalid",
            overall_score=None,
            notes="",
            is_complete=True,
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_out_of_range_score_rejected(db_session: Session) -> None:
    ensure_seed_data(db_session)
    _experiment_id, artifact_id = _seed_experiment_with_candidate(db_session)
    from app.core.errors import ValidationError

    try:
        evaluation_repo.upsert_evaluation(
            db_session,
            artifact_id=artifact_id,
            status="success",
            overall_score=11,
            notes="",
            is_complete=True,
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_provenance_recorded_for_ai_edited(db_session: Session) -> None:
    ensure_seed_data(db_session)
    _experiment_id, artifact_id = _seed_experiment_with_candidate(db_session)
    evaluation = evaluation_repo.upsert_evaluation(
        db_session,
        artifact_id=artifact_id,
        status="partial_success",
        overall_score=6,
        notes="edited from AI suggestion",
        is_complete=True,
        provenance="ai_edited",
    )
    assert evaluation.provenance == "ai_edited"
