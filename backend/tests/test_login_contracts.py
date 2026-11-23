"""Integration tests for participant login, credential verification, and error semantics."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.models.user import User
from app.main import create_app
from tests.test_migrations import get_connection, TEST_MIGRATION_URL

app_settings = get_settings()
TEST_DB_URL = app_settings.TEST_DATABASE_URL or app_settings.DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Aborting test! Refusing to run integration tests against non-test DB: {TEST_DB_URL}"
    )
    settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(settings)
    yield app


@pytest.fixture
def client(app_instance):
    """Yield test client with initialized database engine."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up synthetic test records before and after each test."""
    def _clean():
        conn = get_connection(TEST_MIGRATION_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DELETE FROM core.participant_topics;")
            cur.execute("DELETE FROM core.participant_hobbies;")
            cur.execute("DELETE FROM core.participant_profiles;")
            cur.execute("DELETE FROM core.user_sessions;")
            cur.execute("DELETE FROM core.login_rate_limits;")
            cur.execute("DELETE FROM core.audit_logs;")
            cur.execute("DELETE FROM core.users;")
        conn.close()

    _clean()
    yield
    _clean()


@pytest.fixture
def seed_active_user(client: TestClient):
    """Register and seed an active test user for login verification."""
    unique = uuid.uuid4().hex[:8]
    username = f"user_{unique}"
    email = f"user_{unique}@example.com"
    password = "ValidPassword123!"

    resp = client.post(
        "/converge-api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Test Participant",
        },
    )
    assert resp.status_code == 201
    return {
        "id": resp.json()["id"],
        "username": username,
        "email": email,
        "password": password,
    }


def test_login_success_with_username(client: TestClient, seed_active_user):
    """Verify login succeeds using exact username and establishes session cookie."""
    user = seed_active_user
    payload = {
        "identifier": user["username"],
        "password": user["password"],
    }
    resp = client.post("/converge-api/v1/auth/login", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["status"] == "authenticated"
    assert data["username"] == user["username"].lower()
    assert data["user_id"] == user["id"]
    assert data["email"] == user["email"].lower()
    assert "expires_at" in data

    # Verify session cookie is set
    assert "set-cookie" in resp.headers
    cookie_header = resp.headers["set-cookie"]
    assert "converge_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/" in cookie_header
    assert "SameSite=lax" in cookie_header


def test_login_success_case_insensitive_username(client: TestClient, seed_active_user):
    """Verify login succeeds when username has mixed uppercase characters."""
    user = seed_active_user
    payload = {
        "identifier": user["username"].upper(),
        "password": user["password"],
    }
    resp = client.post("/converge-api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "authenticated"
    assert resp.json()["username"] == user["username"].lower()


def test_login_success_with_email(client: TestClient, seed_active_user):
    """Verify login succeeds using registered email address (case-insensitive)."""
    user = seed_active_user
    payload = {
        "identifier": user["email"].upper(),
        "password": user["password"],
    }
    resp = client.post("/converge-api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "authenticated"
    assert resp.json()["user_id"] == user["id"]


def test_login_invalid_password_returns_generic_401(client: TestClient, seed_active_user):
    """Verify wrong password returns 401 with generic message."""
    user = seed_active_user
    payload = {
        "identifier": user["username"],
        "password": "WrongPassword999!",
    }
    resp = client.post("/converge-api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials."


def test_login_nonexistent_user_returns_generic_401(client: TestClient):
    """Verify nonexistent user returns identical 401 message (no user enumeration)."""
    payload = {
        "identifier": f"nonexistent_{uuid.uuid4().hex[:8]}",
        "password": "SomePassword123!",
    }
    resp = client.post("/converge-api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials."


def test_login_deactivated_user_returns_generic_401(client: TestClient, seed_active_user):
    """Verify inactive account returns generic 401 without leaking account existence."""
    user = seed_active_user

    # Deactivate account directly in database
    conn = get_connection(TEST_MIGRATION_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("UPDATE core.users SET is_active = false WHERE id = %s;", (user["id"],))
    conn.close()

    payload = {
        "identifier": user["username"],
        "password": user["password"],
    }
    resp = client.post("/converge-api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials."


def test_login_audit_events_recorded_and_scrubbed(client: TestClient, seed_active_user):
    """Verify login success and failure emit audit log entries adhering to GAP-10."""
    user = seed_active_user

    # 1. Failed login
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": user["username"], "password": "BadPassword123!"},
    )

    # 2. Successful login
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": user["username"], "password": user["password"]},
    )

    # Inspect audit logs
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT action_type, actor_username, event_payload FROM core.audit_logs ORDER BY id ASC;"
        )
        logs = cur.fetchall()
    conn.close()

    # Should contain registration, LOGIN_FAILED, and LOGIN_SUCCESS
    actions = [row[0] for row in logs]
    assert "LOGIN_FAILED" in actions
    assert "LOGIN_SUCCESS" in actions

    for action, actor, payload in logs:
        payload_str = str(payload).lower()
        assert "password" not in payload_str
        assert "badpassword" not in payload_str
        assert "validpassword" not in payload_str
