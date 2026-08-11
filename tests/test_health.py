"""Tests for application startup and the /health endpoint."""

from fastapi.testclient import TestClient


def test_app_imports() -> None:
    from app.main import app as fastapi_app

    assert fastapi_app is not None


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client: TestClient) -> None:
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body
