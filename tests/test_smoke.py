"""Smoke test — verifies the app module imports and FastAPI is configured."""

from fastapi import FastAPI


def test_app_is_fastapi_instance():
    from src.app import app

    assert isinstance(app, FastAPI)


def test_health_endpoint_exists():
    from fastapi.testclient import TestClient
    from src.app import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
