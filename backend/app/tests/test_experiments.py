"""Tests for experiment lifecycle.

Scenarios:
- Reject missing original image.
- Reject empty original image.
- Unique workspace path per experiment.
- Reopen an existing experiment.
- Local data is accessible without a connection (offline scenario).
"""
from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.tests._fixtures import PNG_1x1_RED


def _png(name: str = "original.png") -> tuple[bytes, str]:
    return PNG_1x1_RED, name


def test_create_experiment_rejects_missing_original_image(client: TestClient) -> None:
    response = client.post(
        "/api/experiments",
        data={"name": "no-image", "goal": ""},
    )
    assert response.status_code == 422  # missing file


def test_create_experiment_rejects_empty_image(client: TestClient) -> None:
    response = client.post(
        "/api/experiments",
        data={"name": "empty", "goal": ""},
        files={"original_image": ("empty.png", io.BytesIO(b""), "image/png")},
    )
    assert response.status_code in (400, 422)
    body = response.json()
    assert "empty" in body["message"].lower()


def test_create_experiment_assigns_unique_workspace(client: TestClient) -> None:
    img, name = _png()
    r1 = client.post(
        "/api/experiments",
        data={"name": "first", "goal": "fix hair"},
        files={"original_image": (name, io.BytesIO(img), "image/png")},
    )
    assert r1.status_code == 200, r1.text
    img, name = _png()
    r2 = client.post(
        "/api/experiments",
        data={"name": "second", "goal": ""},
        files={"original_image": (name, io.BytesIO(img), "image/png")},
    )
    assert r2.status_code == 200
    assert r1.json()["id"] != r2.json()["id"]
    assert r1.json()["remote_workspace_path"] != r2.json()["remote_workspace_path"]
    assert r1.json()["remote_workspace_path"].endswith(r1.json()["id"])


def test_reopen_experiment_shows_status(client: TestClient) -> None:
    img, name = _png()
    created = client.post(
        "/api/experiments",
        data={"name": "x", "goal": ""},
        files={"original_image": (name, io.BytesIO(img), "image/png")},
    ).json()
    reopened = client.get(f"/api/experiments/{created['id']}").json()
    assert reopened["id"] == created["id"]
    assert reopened["status"] == "created"
    assert reopened["snapshots"] == []
    assert reopened["evaluations"] == []
    assert reopened["analyses"] == []


def test_offline_access_without_connection(client: TestClient) -> None:
    img, name = _png()
    created = client.post(
        "/api/experiments",
        data={"name": "offline", "goal": ""},
        files={"original_image": (name, io.BytesIO(img), "image/png")},
    ).json()
    # Without a connection configured, the experiment is still readable and the
    # original image is still served locally.
    detail = client.get(f"/api/experiments/{created['id']}").json()
    assert detail["remote_workspace_path"].startswith("<")
    response = client.get(f"/api/experiments/{created['id']}/original-image")
    assert response.status_code == 200
    assert response.content == PNG_1x1_RED


def test_list_experiments(client: TestClient) -> None:
    img, name = _png()
    client.post(
        "/api/experiments",
        data={"name": "a", "goal": ""},
        files={"original_image": (name, io.BytesIO(img), "image/png")},
    )
    body = client.get("/api/experiments").json()
    assert len(body) >= 1
    assert body[0]["name"] in {"a"}
