"""Tests for health liveness probe endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings


@pytest.fixture
def client():
    """Create test client using default test settings."""
    test_settings = Settings(ENVIRONMENT="test")
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_success(client: TestClient):
    """Verify GET /converge-api/v1/health returns HTTP 200 with expected schema."""
    response = client.get("/converge-api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "converge-ai"
    assert data["environment"] == "test"


def test_health_endpoint_method_not_allowed(client: TestClient):
    """Verify POST /converge-api/v1/health returns HTTP 405."""
    response = client.post("/converge-api/v1/health")
    assert response.status_code == 405
