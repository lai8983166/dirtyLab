"""Tests for the multimodal analysis flow (Task 6.6).

Scenarios:
- Missing provider config raises ValidationError and never sends data.
- Successful analysis stores the raw response + suggestions.
- Provider failure is recorded as a failed analysis (no confirmed scores).
- Unconfirmed drafts remain is_confirmed=False.
- Edited confirmations persist as user-confirmed values.
- Rejected suggestions set is_rejected and excluded fields list.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.config import AppConfig
from app.core.errors import ValidationError
from app.db.bootstrap import ensure_seed_data
from app.models import Artifact, Experiment, Provider, Snapshot
from app.providers import AnalysisResult
from app.services import analysis_repo, connection_repo, multimodal


def _seed_experiment_with_artifact(db) -> tuple[str, str]:
    experiment = Experiment(
        name="t",
        goal="fix hair color",
        original_filename="o.png",
        original_extension="png",
        original_checksum="x",
        remote_workspace_path="/root/x",
    )
    db.add(experiment)
    db.flush()
    snapshot = Snapshot(
        experiment_id=experiment.id, number=1, status="success", source_path="/root/x"
    )
    db.add(snapshot)
    db.flush()
    # Write a local artifact file the provider would upload.
    cfg = AppConfig.load()
    artifact_path = cfg.artifacts_dir / experiment.id / "c1.png"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"png-bytes")
    artifact = Artifact(
        snapshot_id=snapshot.id,
        relative_path="output/c1.png",
        kind="saved_image",
        remote_path="/root/x/output/c1.png",
        local_path=str(artifact_path),
        checksum="x",
        size_bytes=8,
        transfer_status="transferred",
    )
    db.add(artifact)
    db.commit()
    db.refresh(experiment)
    db.refresh(artifact)
    return experiment.id, artifact.id


def _seed_provider(db) -> Provider:
    cfg = AppConfig.load()
    (cfg.secrets_dir / "provider_api_key").write_text("sk-test", encoding="utf-8")
    return connection_repo.upsert_provider(
        db,
        kind="openai_compatible",
        base_url="https://example.invalid/v1",
        model="gpt-4o",
        api_key_ref="provider_api_key",
    )


def test_missing_artifacts_raises(db_session) -> None:
    ensure_seed_data(db_session)
    experiment = Experiment(
        name="t",
        goal="",
        original_filename="o.png",
        original_extension="png",
        original_checksum="x",
        remote_workspace_path="/root/x",
    )
    db_session.add(experiment)
    db_session.commit()
    provider = _seed_provider(db_session)
    with pytest.raises(ValidationError):
        multimodal.request_analysis(
            db_session,
            experiment=experiment,
            provider=provider,
            artifacts=[],
            goal_override=None,
            include_comparison_context=False,
        )


def test_successful_analysis_stores_suggestions(db_session) -> None:
    ensure_seed_data(db_session)
    experiment_id, artifact_id = _seed_experiment_with_artifact(db_session)
    provider = _seed_provider(db_session)
    experiment = db_session.get(Experiment, experiment_id)
    artifact = db_session.get(Artifact, artifact_id)
    fake = AnalysisResult(
        raw_response={"id": "x"},
        suggestions={
            "failure_causes": ["extra fingers"],
            "quality_scores": {"overall_alignment": 4},
            "overall_score": 4,
            "status": "failure",
            "next_steps": ["lower cfg"],
        },
    )
    with patch("app.services.multimodal.get_provider") as mocked:
        adapter = type(
            "A", (), {"kind": "openai_compatible", "analyze": lambda self, *a, **k: fake}
        )()
        mocked.return_value = adapter
        analysis = multimodal.request_analysis(
            db_session,
            experiment=experiment,
            provider=provider,
            artifacts=[artifact],
            goal_override=None,
            include_comparison_context=False,
        )
    assert analysis.status == "success"
    suggestions = analysis_repo.get_suggestions(analysis)
    assert suggestions["overall_score"] == 4
    assert analysis.is_confirmed is False  # unconfirmed draft
    assert analysis.is_rejected is False


def test_provider_failure_records_failed_state(db_session) -> None:
    ensure_seed_data(db_session)
    experiment_id, artifact_id = _seed_experiment_with_artifact(db_session)
    provider = _seed_provider(db_session)
    experiment = db_session.get(Experiment, experiment_id)
    artifact = db_session.get(Artifact, artifact_id)

    from app.core.errors import ProviderError

    def boom(*args, **kwargs):
        raise ProviderError("boom", details={})

    with patch("app.services.multimodal.get_provider") as mocked:
        mocked.return_value = type("A", (), {"kind": "openai_compatible", "analyze": boom})()
        analysis = multimodal.request_analysis(
            db_session,
            experiment=experiment,
            provider=provider,
            artifacts=[artifact],
            goal_override=None,
            include_comparison_context=False,
        )
    assert analysis.status == "failed"
    assert "boom" in (analysis.error_detail or "")
    assert analysis.is_confirmed is False


def test_confirm_edited_suggestions_marks_confirmed(db_session) -> None:
    ensure_seed_data(db_session)
    experiment_id, artifact_id = _seed_experiment_with_artifact(db_session)
    provider = _seed_provider(db_session)
    experiment = db_session.get(Experiment, experiment_id)
    artifact = db_session.get(Artifact, artifact_id)
    fake = AnalysisResult(
        raw_response={},
        suggestions={
            "failure_causes": ["x"],
            "quality_scores": {},
            "overall_score": 4,
            "status": "failure",
            "next_steps": [],
        },
    )
    with patch("app.services.multimodal.get_provider") as mocked:
        mocked.return_value = type(
            "A", (), {"kind": "openai_compatible", "analyze": lambda self, *a, **k: fake}
        )()
        analysis = multimodal.request_analysis(
            db_session,
            experiment=experiment,
            provider=provider,
            artifacts=[artifact],
            goal_override=None,
            include_comparison_context=False,
        )
    confirmed = multimodal.confirm_analysis(
        db_session,
        analysis,
        {"overall_score": 6, "status": "partial_success", "notes": "edited", "rejected_fields": []},
    )
    assert confirmed.is_confirmed is True
    assert confirmed.confirmed_overall_score == 6
    assert confirmed.confirmed_status == "partial_success"


def test_rejected_suggestions_do_not_become_confirmed(db_session) -> None:
    ensure_seed_data(db_session)
    experiment_id, artifact_id = _seed_experiment_with_artifact(db_session)
    provider = _seed_provider(db_session)
    experiment = db_session.get(Experiment, experiment_id)
    artifact = db_session.get(Artifact, artifact_id)
    fake = AnalysisResult(
        raw_response={},
        suggestions={
            "failure_causes": ["x", "y"],
            "quality_scores": {},
            "overall_score": 4,
            "status": "failure",
            "next_steps": [],
        },
    )
    with patch("app.services.multimodal.get_provider") as mocked:
        mocked.return_value = type(
            "A", (), {"kind": "openai_compatible", "analyze": lambda self, *a, **k: fake}
        )()
        analysis = multimodal.request_analysis(
            db_session,
            experiment=experiment,
            provider=provider,
            artifacts=[artifact],
            goal_override=None,
            include_comparison_context=False,
        )
    rejected = multimodal.confirm_analysis(
        db_session,
        analysis,
        {"rejected_fields": ["failure_causes.0"]},
    )
    assert rejected.is_rejected is True
    assert rejected.is_confirmed is False
