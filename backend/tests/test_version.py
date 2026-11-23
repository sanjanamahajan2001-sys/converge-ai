"""Tests for version endpoint."""

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


def test_version_endpoint_success(client: TestClient):
    """Verify GET /converge-api/v1/version returns HTTP 200 with matching version."""
    response = client.get("/converge-api/v1/version")
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "0.1.0"
    assert data["project_name"] == "Converge AI — Conference Agent Network"
    assert data["api_prefix"] == "/converge-api/v1"


def test_version_endpoint_method_not_allowed(client: TestClient):
    """Verify POST /converge-api/v1/version returns HTTP 405."""
    response = client.post("/converge-api/v1/version")
    assert response.status_code == 405
