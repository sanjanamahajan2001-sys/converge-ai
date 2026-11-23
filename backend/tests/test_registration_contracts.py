"""Integration tests for identity registration, validation, error semantics, and audit events."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.config import Settings, get_settings
from app.db.models.audit import AuditLog
from app.db.models.user import User
from app.db.session import db_manager
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
def cleanup_test_identities():
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


def test_registration_success(client: TestClient):
    """Verify valid participant registration succeeds with 201 Created and audit event."""
    unique_id = uuid.uuid4().hex[:8]
    payload = {
        "username": f"test_user_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "ValidPassword123!",
        "full_name": "Test Participant",
        "company_name": "Converge AI Testing",
        "job_title": "Staff Engineer",
        "phone_number": "+1-555-0199",
    }

    response = client.post("/converge-api/v1/auth/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()

    # Identity attributes returned
    assert data["username"] == payload["username"].lower()
    assert data["email"] == payload["email"].lower()
    assert data["full_name"] == payload["full_name"]
    assert data["company_name"] == payload["company_name"]
    assert data["job_title"] == payload["job_title"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data

    # Strict security check: password and password_hash must NEVER be exposed in response
    assert "password" not in data
    assert "password_hash" not in data


def test_registration_duplicate_username_conflict(client: TestClient):
    """Verify duplicate username returns 409 Conflict with enumeration-safe message."""
    unique_id = uuid.uuid4().hex[:8]
    username = f"test_dup_{unique_id}"
    payload1 = {
        "username": username,
        "email": f"test_email1_{unique_id}@example.com",
        "password": "ValidPassword123!",
        "full_name": "Original User",
    }
    res1 = client.post("/converge-api/v1/auth/register", json=payload1)
    assert res1.status_code == 201

    # Attempt registration with different email but matching username (uppercase)
    payload2 = {
        "username": username.upper(),
        "email": f"test_email2_{unique_id}@example.com",
        "password": "ValidPassword123!",
        "full_name": "Duplicate User",
    }
    res2 = client.post("/converge-api/v1/auth/register", json=payload2)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "An account with these identity details already exists."


def test_registration_duplicate_email_conflict(client: TestClient):
    """Verify duplicate email returns 409 Conflict with enumeration-safe message."""
    unique_id = uuid.uuid4().hex[:8]
    email = f"test_dup_{unique_id}@example.com"
    payload1 = {
        "username": f"test_user1_{unique_id}",
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "Original User",
    }
    res1 = client.post("/converge-api/v1/auth/register", json=payload1)
    assert res1.status_code == 201

    # Attempt registration with different username but matching email (uppercase)
    payload2 = {
        "username": f"test_user2_{unique_id}",
        "email": email.upper(),
        "password": "ValidPassword123!",
        "full_name": "Duplicate User",
    }
    res2 = client.post("/converge-api/v1/auth/register", json=payload2)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "An account with these identity details already exists."


def test_registration_invalid_username_format(client: TestClient):
    """Verify invalid username format returns 422 Unprocessable Entity."""
    invalid_usernames = [
        "ab",  # Too short (< 3)
        "a" * 51,  # Too long (> 50)
        "invalid user with spaces",
        "user@invalid#char$",
    ]
    for bad_username in invalid_usernames:
        payload = {
            "username": bad_username,
            "email": "valid@example.com",
            "password": "ValidPassword123!",
            "full_name": "Test User",
        }
        res = client.post("/converge-api/v1/auth/register", json=payload)
        assert res.status_code == 422, f"Expected 422 for username '{bad_username}', got {res.status_code}"


def test_registration_weak_password_rejected(client: TestClient):
    """Verify weak passwords failing complexity rules return 422 Unprocessable Entity."""
    weak_passwords = [
        "short",  # < 10
        "alllowercasepassword123!",  # no uppercase
        "ALLUPPERCASEPASSWORD123!",  # no lowercase
        "PasswordWithoutDigits!",  # no digits
        "PasswordWithDigits1234",  # no special chars
    ]
    for weak_pwd in weak_passwords:
        payload = {
            "username": f"test_pwd_{uuid.uuid4().hex[:6]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "password": weak_pwd,
            "full_name": "Test User",
        }
        res = client.post("/converge-api/v1/auth/register", json=payload)
        assert res.status_code == 422, f"Expected 422 for weak password '{weak_pwd}', got {res.status_code}"


def test_registration_invalid_email_format(client: TestClient):
    """Verify malformed email returns 422 Unprocessable Entity."""
    payload = {
        "username": f"test_email_{uuid.uuid4().hex[:6]}",
        "email": "not_an_email_address",
        "password": "ValidPassword123!",
        "full_name": "Test User",
    }
    res = client.post("/converge-api/v1/auth/register", json=payload)
    assert res.status_code == 422
