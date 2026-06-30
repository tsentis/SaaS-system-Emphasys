"""Smoke tests for the health endpoint (no database required)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_root() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Emphasys EPIP"
