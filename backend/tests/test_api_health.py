"""
Tests for the health check and core FastAPI application setup.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_health_check():
    """GET /health should return 200 with status=healthy."""
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_docs_available():
    """OpenAPI docs should be available at /docs."""
    with TestClient(app) as client:
        resp = client.get("/docs")
    assert resp.status_code == 200


def test_openapi_schema():
    """OpenAPI JSON schema should be available and contain expected paths."""
    with TestClient(app) as client:
        resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    # Verify core route groups exist
    paths = schema["paths"]
    path_keys = list(paths.keys())
    assert any("/signals" in p for p in path_keys), "Signal routes missing from schema"
    assert any("/auth" in p for p in path_keys), "Auth routes missing from schema"


def test_forgot_password():
    """POST /api/v1/auth/forgot-password should return 200."""
    with TestClient(app) as client:
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "test@geotrade.ai"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

