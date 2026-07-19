from fastapi.testclient import TestClient


def test_health_endpoint_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert "artifacts_dir" in body


def test_app_error_handler_returns_structured_payload(client: TestClient) -> None:
    # Hitting a missing artifact should produce a 404 with code/message/details.
    response = client.get("/api/artifacts/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "id" in body["details"]
