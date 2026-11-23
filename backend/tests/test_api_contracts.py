"""Comprehensive OpenAPI contract and response schema verification tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings


@pytest.fixture
def client():
    """Create test client with test settings."""
    settings = Settings(ENVIRONMENT="test")
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def test_openapi_contract_paths(client: TestClient):
    """Verify OpenAPI schema registers exactly the verified Phase 1 endpoints."""
    resp = client.get("/converge-api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    paths = schema["paths"]
    expected_paths = {
        "/converge-api/v1/health",
        "/converge-api/v1/health/ready",
        "/converge-api/v1/version",
        "/converge-api/v1/auth/register",
        "/converge-api/v1/auth/login",
        "/converge-api/v1/auth/logout",
        "/converge-api/v1/auth/me",
        "/converge-api/v1/auth/rotate",
        "/converge-api/v1/profile/me",
        "/converge-api/v1/profile/catalog/hobbies",
        "/converge-api/v1/profile/catalog/moods",
        "/converge-api/v1/profile/{id}",
        "/converge-api/v1/agenda/conferences",
        "/converge-api/v1/agenda/sessions",
        "/converge-api/v1/agenda/sessions/{id}",
        "/converge-api/v1/agenda/bookmarks/me",
        "/converge-api/v1/agenda/bookmarks/{session_id}",
        "/converge-api/v1/agenda/recommendations/me",
        "/converge-api/v1/agenda/sessions/{session_id}/intent",
        "/converge-api/v1/agenda/intent/me",
        "/converge-api/v1/matching/candidates",
        "/converge-api/v1/conversations",
        "/converge-api/v1/conversations/{conversation_id}",
        "/converge-api/v1/conversations/{conversation_id}/accept",
        "/converge-api/v1/conversations/{conversation_id}/trigger-agent",
        "/converge-api/v1/conversations/{conversation_id}/cancel",
        "/converge-api/v1/conversations/{conversation_id}/conclude",
        "/converge-api/v1/conversations/{conversation_id}/messages",
        "/converge-api/v1/analytics/events",
        "/converge-api/v1/analytics/my-summary",
        "/converge-api/v1/analytics/users/{target_user_id}/summary",
        "/converge-api/v1/analytics/overview",
        "/converge-api/v1/admin/auth/login",
        "/converge-api/v1/admin/auth/me",
        "/converge-api/v1/admin/auth/logout",
        "/converge-api/v1/admin/overview",
        "/converge-api/v1/admin/users",
        "/converge-api/v1/admin/users/{user_id}",
        "/converge-api/v1/admin/users/{user_id}/status",
        "/converge-api/v1/admin/organizers",
        "/converge-api/v1/admin/organizers/{organizer_id}/verification",
        "/converge-api/v1/admin/conferences",
        "/converge-api/v1/admin/conferences/{conference_id}",
        "/converge-api/v1/admin/conferences/{conference_id}/decision",
        "/converge-api/v1/organizer/register",
        "/converge-api/v1/organizer/me",
        "/converge-api/v1/organizer/conferences",
        "/converge-api/v1/organizer/conferences/{conference_id}",
        "/converge-api/v1/organizer/conferences/{conference_id}/submit",
        "/converge-api/v1/organizer/conferences/{conference_id}/sessions",
        "/converge-api/v1/organizer/conferences/{conference_id}/sessions/{session_id}",
        "/converge-api/v1/events/stream",
        "/converge-api/v1/events/health",
        "/converge-api/v1/business/profile/me",
        "/converge-api/v1/business/offerings",
        "/converge-api/v1/business/offerings/{offering_id}",
        "/converge-api/v1/business/offerings/{offering_id}/confirm",
        "/converge-api/v1/business/requirements",
        "/converge-api/v1/business/requirements/{requirement_id}",
        "/converge-api/v1/business/taxonomies/products",
        "/converge-api/v1/business/taxonomies/services",
        "/converge-api/v1/business/matching/my-requirements",
        "/converge-api/v1/business/matching/my-offerings",
        "/converge-api/v1/business/matching/parse-query",
        "/converge-api/v1/business/matching/search",
        "/converge-api/v1/conversations/{conversation_id}/business-context",
        "/converge-api/v1/chatrooms/active",
        "/converge-api/v1/chatrooms/{chatroom_id}/ambient-tick",
        "/converge-api/v1/chatrooms/{chatroom_id}/leave",
        "/converge-api/v1/chatrooms/{chatroom_id}/messages",
        "/converge-api/v1/groups/circles",
        "/converge-api/v1/groups/circles/{group_id}",
        "/converge-api/v1/groups/circles/{group_id}/close",
        "/converge-api/v1/groups/circles/{group_id}/leave",
        "/converge-api/v1/groups/circles/{group_id}/messages",
        "/converge-api/v1/organizer/conferences/{conference_id}/live-state",
        "/converge-api/v1/organizer/conferences/{conference_id}/lounge/close",
        "/converge-api/v1/organizer/conferences/{conference_id}/lounge/host",
        "/converge-api/v1/organizer/conferences/{conference_id}/lounge/reset",
    }
    assert set(paths.keys()) == expected_paths, f"Unexpected paths in OpenAPI: {set(paths.keys())}"


def test_health_contract_schema(client: TestClient):
    """Verify /health endpoint matches contract schema."""
    resp = client.get("/converge-api/v1/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "healthy"
    assert data["service"] == "converge-ai"
    assert data["environment"] == "test"
    assert set(data.keys()) == {"status", "service", "environment"}


def test_readiness_contract_schema(client: TestClient):
    """Verify /health/ready endpoint matches readiness schema."""
    resp = client.get("/converge-api/v1/health/ready")
    # In test mode without DATABASE_URL, returns 503 unconfigured
    assert resp.status_code in (200, 503)
    data = resp.json()

    assert "status" in data
    assert data["status"] in ("ready", "not_ready")
    assert "database" in data
    assert data["database"] in ("connected", "unconfigured", "disconnected")
    assert set(data.keys()) == {"status", "database"}


def test_version_contract_schema(client: TestClient):
    """Verify /version endpoint matches version schema."""
    resp = client.get("/converge-api/v1/version")
    assert resp.status_code == 200
    data = resp.json()

    assert "version" in data
    assert "project_name" in data
    assert "api_prefix" in data
    assert data["api_prefix"] == "/converge-api/v1"
    assert set(data.keys()) == {"version", "project_name", "api_prefix"}


def test_no_sensitive_data_in_openapi(client: TestClient):
    """Verify that OpenAPI schema string contains no database passwords or credentials."""
    resp = client.get("/converge-api/v1/openapi.json")
    assert resp.status_code == 200
    raw_schema = resp.text.lower()

    # Standard security keyword checks (no hashes or database connection strings)
    forbidden_terms = [
        "password_hash",
        "secret_key",
        "jwt_secret",
        "postgresql://",
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
    ]
    for term in forbidden_terms:
        assert term not in raw_schema, f"Potential credential leak in OpenAPI: '{term}'"

    # Dynamically verify actual configured database credentials from environment are never in OpenAPI
    from app.core.config import get_settings
    current_settings = get_settings()
    for url in (current_settings.DATABASE_URL, current_settings.MIGRATION_DATABASE_URL):
        if url and "@" in url:
            # Extract user:pass portion
            credentials = url.split("://")[1].split("@")[0]
            if ":" in credentials:
                secret_part = credentials.split(":")[1]
                if secret_part:
                    assert secret_part.lower() not in raw_schema, "Configured DB password found in OpenAPI schema!"
