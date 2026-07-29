"""End-to-end local workflow test (Task 7.1).

Walks through the complete flow without a real network:
1. Configure an AutoDL connection (with a real generated key).
2. Create an experiment with an original image.
3. Sync a snapshot using the SFTP double.
4. Compare candidates and save a failure evaluation.
5. Request AI analysis (with the provider mocked) and confirm an edit.

This proves the layered implementation composes into the documented user flow.
"""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import AppConfig
from app.providers import AnalysisResult
from app.tests._fixtures import PNG_1x1_RED as PNG
from app.tests.sftp_fixture import install_fake_sftp


def test_end_to_end_local_workflow(client: TestClient, tmp_data_dir: Path, monkeypatch) -> None:
    # 1. Configure AutoDL connection with a real generated ed25519 key.
    from app.tests._keys import generate_ed25519_openssh_text

    private_key = generate_ed25519_openssh_text()
    r = client.put(
        "/api/connections",
        json={
            "host": "127.0.0.1",
            "port": 2222,
            "username": "root",
            "private_key": private_key,
            "remote_root": "/root/ComfyUI",
        },
    )
    assert r.status_code == 200, r.text

    # 2. Create an experiment.
    r = client.post(
        "/api/experiments",
        data={"name": "e2e", "goal": "remove background cleanly"},
        files={"original_image": ("o.png", io.BytesIO(PNG), "image/png")},
    )
    assert r.status_code == 200, r.text
    experiment = r.json()
    experiment_id = experiment["id"]
    workspace = experiment["remote_workspace_path"]

    # 3. Sync a snapshot using the in-process SFTP fixture.
    install_fake_sftp(
        monkeypatch,
        {
            f"{workspace}/output/c1.png": PNG,
            f"{workspace}/output/.preview.tmp": PNG,  # should be ignored
        },
    )
    r = client.post(f"/api/sync/experiments/{experiment_id}")
    assert r.status_code == 200, r.text
    sync_result = r.json()
    assert sync_result["snapshot"]["status"] == "success"
    assert len(sync_result["snapshot"]["artifacts"]) == 1
    assert sync_result["ignored_count"] >= 1
    candidate = sync_result["snapshot"]["artifacts"][0]
    candidate_id = candidate["id"]

    # 4. Compare candidate + save a failure evaluation.
    r = client.put(
        f"/api/evaluations/artifacts/{candidate_id}",
        json={
            "status": "failure",
            "overall_score": 3,
            "notes": "hair is wrong color",
            "is_complete": True,
            "provenance": "human",
            "dimension_scores": [
                {"key": "overall_alignment", "label": "Overall alignment with goal", "score": 2}
            ],
            "tags": [{"key": "color_cast", "label": "Wrong color / lighting"}],
        },
    )
    assert r.status_code == 200, r.text
    evaluation = r.json()
    assert evaluation["status"] == "failure"
    assert evaluation["overall_score"] == 3

    # 5. Configure provider, request analysis (mocked), confirm edited.
    cfg = AppConfig.load(tmp_data_dir)
    cfg.secrets_dir.mkdir(exist_ok=True)
    (cfg.secrets_dir / "provider_api_key").write_text("sk-test", encoding="utf-8")
    r = client.put(
        "/api/providers",
        json={
            "kind": "openai_compatible",
            "base_url": "https://example.invalid/v1",
            "model": "gpt-4o",
            "api_key": "sk-test",
        },
    )
    assert r.status_code == 200, r.text

    fake = AnalysisResult(
        raw_response={"id": "fake"},
        suggestions={
            "failure_causes": ["wrong palette"],
            "quality_scores": {"overall_alignment": 2},
            "overall_score": 3,
            "status": "failure",
            "next_steps": ["try different sampler"],
        },
    )
    with patch("app.services.multimodal.get_provider") as mocked:
        mocked.return_value = type(
            "A", (), {"kind": "openai_compatible", "analyze": lambda self, *a, **k: fake}
        )()
        r = client.post(
            f"/api/analyses/experiments/{experiment_id}/request",
            json={
                "artifact_ids": [candidate_id],
                "include_comparison_context": True,
            },
        )
    assert r.status_code == 200, r.text
    analysis = r.json()
    assert analysis["status"] == "success"
    assert analysis["is_confirmed"] is False
    analysis_id = analysis["id"]

    r = client.post(
        f"/api/analyses/{analysis_id}/confirm",
        json={
            "overall_score": 4,
            "status": "failure",
            "notes": "edited from AI suggestion",
            "rejected_fields": ["failure_causes.0"],
        },
    )
    assert r.status_code == 200, r.text
    confirmed = r.json()
    assert confirmed["is_confirmed"] is True
    assert confirmed["confirmed_overall_score"] == 4


def test_sync_does_not_trigger_provider_calls(
    client: TestClient, tmp_data_dir: Path, monkeypatch
) -> None:
    """Spec scenario: synchronization does not call AI."""
    from app.tests._keys import generate_ed25519_openssh_text

    private_key = generate_ed25519_openssh_text()
    client.put(
        "/api/connections",
        json={
            "host": "127.0.0.1",
            "port": 2222,
            "username": "root",
            "private_key": private_key,
            "remote_root": "/root/ComfyUI",
        },
    )
    r = client.post(
        "/api/experiments",
        data={"name": "t", "goal": ""},
        files={"original_image": ("o.png", io.BytesIO(PNG), "image/png")},
    )
    experiment_id = r.json()["id"]
    workspace = r.json()["remote_workspace_path"]
    install_fake_sftp(monkeypatch, {f"{workspace}/output/c1.png": PNG})

    called = {"n": 0}

    def spy(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("Provider should not be called during sync")

    with patch("app.services.multimodal.get_provider") as mocked:
        mocked.side_effect = spy
        client.post(f"/api/sync/experiments/{experiment_id}")
    assert called["n"] == 0
