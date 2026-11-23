"""Tests for health liveness and readiness probe endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings, get_settings

app_settings = get_settings()
TEST_DB_URL = app_settings.TEST_DATABASE_URL or app_settings.DATABASE_URL


def test_liveness_probe_always_healthy():
    """Verify liveness probe returns HTTP 200 regardless of database state."""
    settings = Settings(ENVIRONMENT="test", DATABASE_URL=None)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/converge-api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "converge-ai"


def test_readiness_probe_unconfigured():
    """Verify readiness returns HTTP 503 when DATABASE_URL is not set."""
    settings = Settings(ENVIRONMENT="test", DATABASE_URL=None)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/converge-api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "unconfigured"


def test_readiness_probe_connected():
    """Verify readiness returns HTTP 200 when database connectivity is healthy."""
    settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/converge-api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


def test_readiness_probe_disconnected_on_bad_host():
    """Verify readiness returns HTTP 503 when database is unreachable."""
    bad_url = "postgresql+asyncpg://converge_ai_app:wrong@127.0.0.1:54329/converge_ai_test"
    settings = Settings(ENVIRONMENT="test", DATABASE_URL=bad_url)
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/converge-api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"
