"""Tests for login failed-attempt throttling, lockouts, and IP isolation."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
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
def test_user(client: TestClient):
    """Create a verified test user."""
    uname = f"throttle_user_{uuid.uuid4().hex[:6]}"
    password = "ValidPassword123!"
    client.post(
        "/converge-api/v1/auth/register",
        json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": password,
            "full_name": "Throttle Test User",
        },
    )
    return {"username": uname, "password": password}


def test_throttling_triggers_on_fifth_failed_attempt(client: TestClient, test_user):
    """Verify that 5 failed login attempts from an IP triggers HTTP 429 lockout."""
    target_ip = "192.168.100.42"
    headers = {"X-Forwarded-For": target_ip}

    # Attempts 1 through 4 should fail with 401
    for attempt in range(1, 5):
        resp = client.post(
            "/converge-api/v1/auth/login",
            json={"identifier": test_user["username"], "password": "BadPassword123!"},
            headers=headers,
        )
        assert resp.status_code == 401, f"Attempt {attempt} expected 401, got {resp.status_code}"
        assert resp.json()["detail"] == "Invalid credentials."

    # 5th attempt must trigger 429 Too Many Requests
    resp5 = client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": test_user["username"], "password": "BadPassword123!"},
        headers=headers,
    )
    assert resp5.status_code == 429, f"Attempt 5 expected 429, got {resp5.status_code}"
    assert "Too many failed sign-in attempts" in resp5.json()["detail"]
    assert "retry-after" in resp5.headers
    assert int(resp5.headers["retry-after"]) > 0


def test_locked_out_ip_preflight_blocks_even_valid_credentials(client: TestClient, test_user):
    """Verify that an IP locked out by failed attempts is rejected before checking valid credentials."""
    target_ip = "192.168.100.43"
    headers = {"X-Forwarded-For": target_ip}

    # Trigger lockout with 5 failed attempts
    for _ in range(5):
        client.post(
            "/converge-api/v1/auth/login",
            json={"identifier": test_user["username"], "password": "WrongPassword!"},
            headers=headers,
        )

    # 6th attempt with CORRECT password must still be rejected with 429
    resp_valid = client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": test_user["username"], "password": test_user["password"]},
        headers=headers,
    )
    assert resp_valid.status_code == 429
    assert "Too many failed sign-in attempts" in resp_valid.json()["detail"]


def test_successful_login_resets_rate_limit(client: TestClient, test_user):
    """Verify that a successful login resets the failed attempt counter."""
    target_ip = "192.168.100.44"
    headers = {"X-Forwarded-For": target_ip}

    # 3 failed attempts
    for _ in range(3):
        res = client.post(
            "/converge-api/v1/auth/login",
            json={"identifier": test_user["username"], "password": "BadPassword1!"},
            headers=headers,
        )
        assert res.status_code == 401

    # Verify rate limit record exists in DB
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT attempt_count FROM core.login_rate_limits;")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 3
    conn.close()

    # Successful login
    success_resp = client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": test_user["username"], "password": test_user["password"]},
        headers=headers,
    )
    assert success_resp.status_code == 200

    # Rate limit record should now be deleted/cleared
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM core.login_rate_limits;")
        count = cur.fetchone()[0]
        assert count == 0
    conn.close()


def test_ip_isolation_for_throttling(client: TestClient, test_user):
    """Verify that lockouts on one IP do not impact login requests from another IP."""
    attacker_ip = "192.168.100.50"
    legitimate_ip = "192.168.100.51"

    # Attacker triggers lockout on attacker_ip
    for _ in range(5):
        client.post(
            "/converge-api/v1/auth/login",
            json={"identifier": test_user["username"], "password": "AttackerWrongPassword!"},
            headers={"X-Forwarded-For": attacker_ip},
        )

    # Legitimate user from different IP can log in successfully
    legit_resp = client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": test_user["username"], "password": test_user["password"]},
        headers={"X-Forwarded-For": legitimate_ip},
    )
    assert legit_resp.status_code == 200
    assert legit_resp.json()["status"] == "authenticated"
