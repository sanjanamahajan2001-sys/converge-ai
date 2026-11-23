"""Comprehensive integration tests for server-side sessions, revocation, rotation, CSRF, and cookies (GAP-05)."""
import time
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.security import verify_dummy_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.main import create_app
from tests.test_migrations import get_connection, TEST_MIGRATION_URL

app_settings = get_settings()
TEST_DB_URL = app_settings.TEST_DATABASE_URL or app_settings.DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Aborting test! Refusing to run tests against non-test DB: {TEST_DB_URL}"
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
def active_user(client: TestClient):
    """Create an active registered user."""
    uname = f"sess_user_{uuid.uuid4().hex[:6]}"
    email = f"{uname}@example.com"
    pwd = "ValidPassword123!"

    resp = client.post(
        "/converge-api/v1/auth/register",
        json={
            "username": uname,
            "email": email,
            "password": pwd,
            "full_name": "Session Test Participant",
        },
    )
    assert resp.status_code == 201
    return {
        "id": resp.json()["id"],
        "username": uname,
        "email": email,
        "password": pwd,
    }


def test_token_entropy_and_digest_storage():
    """Verify session token randomness and that only SHA-256 digests are stored in DB."""
    tokens = {generate_session_token() for _ in range(100)}
    assert len(tokens) == 100, "Collision detected in session tokens!"

    # Verify entropy: urlsafe token generated from 32 bytes produces 43 characters
    for token in tokens:
        assert len(token) >= 43
        digest = hash_session_token(token)
        assert len(digest) == 64
        # SHA-256 digest is hex
        assert all(c in "0123456789abcdef" for c in digest)


def test_dummy_bcrypt_hash_validity_and_timing():
    """Verify dummy bcrypt hash is mathematically valid and takes expected computation time (~100-250ms)."""
    t0 = time.time()
    result = verify_dummy_password("SomeTestPassword123!")
    t1 = time.time()
    elapsed = t1 - t0

    assert result is False
    assert elapsed > 0.08, f"Dummy verification completed too quickly ({elapsed:.4f}s), indicating fake or bypassed work!"


def test_successful_login_issues_cookie_and_persists_session_digest(client: TestClient, active_user):
    """Verify valid login sets HttpOnly cookie and persists token digest in core.user_sessions."""
    login_resp = client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["status"] == "authenticated"
    assert data["username"] == active_user["username"].lower()
    assert "expires_at" in data

    # 1. Cookie headers verification
    assert "set-cookie" in login_resp.headers
    cookie = login_resp.headers["set-cookie"]
    assert f"{SESSION_COOKIE_NAME}=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/" in cookie
    assert "SameSite=lax" in cookie

    # Extract raw token from cookie
    raw_token = login_resp.cookies.get(SESSION_COOKIE_NAME)
    assert raw_token is not None

    # 2. Database verification: verify only token_hash is stored, NEVER raw_token
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT token_hash, user_id, revoked_at FROM core.user_sessions;")
        rows = cur.fetchall()
        assert len(rows) == 1
        stored_hash, db_user_id, revoked_at = rows[0]
        assert stored_hash == hash_session_token(raw_token)
        assert stored_hash != raw_token
        assert str(db_user_id) == active_user["id"]
        assert revoked_at is None
    conn.close()


def test_invalid_credentials_do_not_issue_session(client: TestClient, active_user):
    """Verify invalid password does not create a session in database."""
    resp = client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": "WrongPassword999!"},
    )
    assert resp.status_code == 401
    assert "set-cookie" not in resp.headers

    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM core.user_sessions;")
        count = cur.fetchone()[0]
        assert count == 0
    conn.close()


def test_session_validation_via_me_endpoint(client: TestClient, active_user):
    """Verify GET /auth/me successfully authenticates via session cookie."""
    # 1. Unauthenticated request returns 401
    unauth_resp = client.get("/converge-api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # 2. Log in to establish session
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )

    # 3. Authenticated request with cookie returns user identity
    me_resp = client.get("/converge-api/v1/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == active_user["id"]
    assert me_data["username"] == active_user["username"].lower()
    assert me_data["email"] == active_user["email"].lower()
    assert me_data["is_active"] is True


def test_logout_revokes_session_and_clears_cookie(client: TestClient, active_user):
    """Verify POST /auth/logout revokes session in DB and prevents subsequent access."""
    # Log in
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )
    raw_token = client.cookies.get(SESSION_COOKIE_NAME)
    assert raw_token is not None

    # Call logout with CSRF header
    logout_resp = client.post(
        "/converge-api/v1/auth/logout",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "logged_out"

    # Verify cookie is cleared in response
    assert f'{SESSION_COOKIE_NAME}=""' in logout_resp.headers.get("set-cookie", "") or (
        logout_resp.cookies.get(SESSION_COOKIE_NAME) is None
    )

    # Verify session is marked revoked in database
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT revoked_at FROM core.user_sessions WHERE token_hash = %s;", (hash_session_token(raw_token),))
        row = cur.fetchone()
        assert row is not None
        assert row[0] is not None
    conn.close()

    # Replay attempt: sending the revoked token must return 401
    client.cookies.set(SESSION_COOKIE_NAME, raw_token)
    replay_resp = client.get("/converge-api/v1/auth/me")
    assert replay_resp.status_code == 401
    assert "revoked" in replay_resp.json()["detail"].lower()


def test_session_rotation(client: TestClient, active_user):
    """Verify POST /auth/rotate invalidates prior token and issues a fresh one."""
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )
    old_token = client.cookies.get(SESSION_COOKIE_NAME)

    # Rotate session
    rotate_resp = client.post(
        "/converge-api/v1/auth/rotate",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert rotate_resp.status_code == 200
    assert rotate_resp.json()["status"] == "session_rotated"
    new_token = client.cookies.get(SESSION_COOKIE_NAME)
    assert new_token is not None
    assert new_token != old_token

    # Verify database state: old token is revoked, new token is active
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT token_hash, revoked_at FROM core.user_sessions;")
        records = cur.fetchall()
        assert len(records) == 2
        for h, revoked in records:
            if h == hash_session_token(old_token):
                assert revoked is not None
            elif h == hash_session_token(new_token):
                assert revoked is None
    conn.close()

    # Old token replay fails
    client.cookies.set(SESSION_COOKIE_NAME, old_token)
    old_resp = client.get("/converge-api/v1/auth/me")
    assert old_resp.status_code == 401

    # New token works
    client.cookies.set(SESSION_COOKIE_NAME, new_token)
    new_resp = client.get("/converge-api/v1/auth/me")
    assert new_resp.status_code == 200


def test_session_expiry_rejection(client: TestClient, active_user):
    """Verify absolutely expired session is rejected with 401."""
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )
    token = client.cookies.get(SESSION_COOKIE_NAME)

    # Force expiration in database
    conn = get_connection(TEST_MIGRATION_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        past = datetime.now(timezone.utc) - timedelta(hours=25)
        cur.execute("UPDATE core.user_sessions SET expires_at = %s WHERE token_hash = %s;", (past, hash_session_token(token)))
    conn.close()

    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.get("/converge-api/v1/auth/me")
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_session_idle_timeout_rejection(client: TestClient, active_user):
    """Verify idle expired session (>60m inactivity) is rejected with 401."""
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )
    token = client.cookies.get(SESSION_COOKIE_NAME)

    # Force idle timeout in database (last accessed 70 minutes ago)
    conn = get_connection(TEST_MIGRATION_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        idle_past = datetime.now(timezone.utc) - timedelta(minutes=70)
        cur.execute("UPDATE core.user_sessions SET last_accessed_at = %s WHERE token_hash = %s;", (idle_past, hash_session_token(token)))
    conn.close()

    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.get("/converge-api/v1/auth/me")
    assert resp.status_code == 401
    assert "inactivity" in resp.json()["detail"].lower()


def test_csrf_protection_on_state_changing_requests(client: TestClient, active_user):
    """Verify state-changing POST with cookie requires X-Requested-With header."""
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )

    # State-changing logout WITHOUT CSRF header should return 403 Forbidden
    resp_no_csrf = client.post("/converge-api/v1/auth/logout")
    assert resp_no_csrf.status_code == 403
    assert "csrf" in resp_no_csrf.json()["detail"].lower()

    # With X-Requested-With: XMLHttpRequest, succeeds
    resp_with_csrf = client.post(
        "/converge-api/v1/auth/logout",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp_with_csrf.status_code == 200


def test_session_audit_events_recorded_without_raw_secrets(client: TestClient, active_user):
    """Verify SESSION_ISSUED, SESSION_REVOKED, SESSION_ROTATED are recorded and clean of secrets."""
    # 1. Login (issues session)
    client.post(
        "/converge-api/v1/auth/login",
        json={"identifier": active_user["username"], "password": active_user["password"]},
    )
    token = client.cookies.get(SESSION_COOKIE_NAME)

    # 2. Rotate
    client.post("/converge-api/v1/auth/rotate", headers={"X-Requested-With": "XMLHttpRequest"})

    # 3. Logout
    client.post("/converge-api/v1/auth/logout", headers={"X-Requested-With": "XMLHttpRequest"})

    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT action_type, event_payload FROM core.audit_logs;")
        logs = cur.fetchall()
    conn.close()

    actions = [row[0] for row in logs]
    assert "SESSION_ISSUED" in actions
    assert "SESSION_ROTATED" in actions
    assert "SESSION_REVOKED" in actions

    for action, payload in logs:
        p_str = str(payload).lower()
        # GAP-10: zero raw tokens, passwords, or cookies
        assert "password" not in p_str
        assert token.lower() not in p_str


def test_trusted_proxy_forwarded_for_defense(client: TestClient, active_user):
    """Verify X-Forwarded-For is respected only when client is trusted proxy."""
    from app.api.routes.auth import get_client_ip
    from unittest.mock import MagicMock

    # 1. Trusted proxy request (e.g. peer IP is 127.0.0.1)
    req_trusted = MagicMock()
    req_trusted.client.host = "127.0.0.1"
    req_trusted.headers = {"x-forwarded-for": "203.0.113.10"}
    req_trusted.app.state.settings = Settings(ENVIRONMENT="production", TRUSTED_PROXIES=["127.0.0.1"])
    assert get_client_ip(req_trusted) == "203.0.113.10"

    # 2. Untrusted direct client request (e.g. peer IP is 198.51.100.5)
    req_untrusted = MagicMock()
    req_untrusted.client.host = "198.51.100.5"
    req_untrusted.headers = {"x-forwarded-for": "1.2.3.4"}
    req_untrusted.app.state.settings = Settings(ENVIRONMENT="production", TRUSTED_PROXIES=["127.0.0.1"])
    # Untrusted request MUST ignore spoofed X-Forwarded-For and return actual peer IP!
    assert get_client_ip(req_untrusted) == "198.51.100.5"
