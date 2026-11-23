"""Tests for route composition and API prefix structure."""

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


def test_no_duplicated_prefix(client: TestClient):
    """Verify that duplicated prefix does not exist."""
    response = client.get("/converge-api/v1/converge-api/v1/health")
    assert response.status_code == 404


def test_unknown_route_returns_404(client: TestClient):
    """Verify unknown route returns standard HTTP 404."""
    response = client.get("/converge-api/v1/nonexistent-route")
    assert response.status_code == 404


def test_openapi_available_in_test_environment(client: TestClient):
    """Verify OpenAPI JSON schema is accessible in non-production environments."""
    response = client.get("/converge-api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "Converge AI — Conference Agent Network"
    assert "/converge-api/v1/health" in data["paths"]
    assert "/converge-api/v1/version" in data["paths"]


def test_docs_hidden_in_production():
    """Verify documentation routes are disabled in production environment."""
    prod_settings = Settings(ENVIRONMENT="production")
    app = create_app(prod_settings)
    with TestClient(app) as prod_client:
        docs_resp = prod_client.get("/converge-api/v1/docs")
        assert docs_resp.status_code == 404

        openapi_resp = prod_client.get("/converge-api/v1/openapi.json")
        assert openapi_resp.status_code == 404
