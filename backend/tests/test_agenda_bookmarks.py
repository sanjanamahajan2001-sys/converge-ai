"""Integration tests for Participant Session Bookmarks & Ownership (P3-WS3, GAP-05, GAP-10)."""

import uuid
from datetime import date as dt_date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    CSRF_EXPECTED_VALUE,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models.agenda import BookmarkedSession, Conference, Session
from app.db.models.audit import AuditLog
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Refusing to run integration tests against non-test DB: {TEST_DB_URL}"
    )
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    """Yield test client with initialized database engine."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous SQLAlchemy engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_agenda_tables(sync_engine):
    """Clean agenda and audit tables before and after each test."""
    with sync_engine.connect() as conn:
        conn.exec_driver_sql("DELETE FROM agenda.bookmarked_sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.conferences;")
        conn.exec_driver_sql("DELETE FROM core.audit_logs;")
        conn.commit()
    yield
    with sync_engine.connect() as conn:
        conn.exec_driver_sql("DELETE FROM agenda.bookmarked_sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.conferences;")
        conn.exec_driver_sql("DELETE FROM core.audit_logs;")
        conn.commit()


class SimpleUser:
    def __init__(self, uid: uuid.UUID, username: str):
        self.id = uid
        self.username = username


def create_test_user_and_session(sync_engine, username_prefix="user", is_active=True, is_expired=False, is_revoked=False):
    """Create disposable user and server-side session."""
    uid = uuid.uuid4()
    username = f"{username_prefix}_{uid.hex[:8]}"
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)

    with SASession(sync_engine) as session:
        user = User(
            id=uid,
            username=username,
            email=f"{username}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name=f"Test {username}",
            is_active=is_active,
        )
        session.add(user)
        session.flush()

        expires = now - timedelta(hours=1) if is_expired else now + timedelta(hours=24)
        revoked = now if is_revoked else None

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
            last_accessed_at=now,
            revoked_at=revoked,
            ip_address="127.0.0.1",
            user_agent="pytest-client",
        )
        session.add(user_session)
        session.commit()

    return SimpleUser(uid, username), raw_token


def create_conference_and_sessions(sync_engine, is_active=True, session_count=2):
    """Create a test conference with scheduled sessions."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title=f"Conference {uuid.uuid4().hex[:6]}",
            venue_name="Convention Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
            is_active=is_active,
        )
        session.add(conf)
        session.flush()

        sessions = []
        t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        for i in range(session_count):
            sess = Session(
                conference_id=conf.id,
                title=f"Session {i + 1} - Track A",
                abstract=f"Abstract for session {i + 1}",
                speaker_names="Dr. Alice Smith, Alan Turing",
                track_name="AI Track",
                hall_room=f"Hall {chr(65 + i)}",
                start_time=t0 + timedelta(hours=i),
                end_time=t0 + timedelta(hours=i, minutes=45),
                is_cancelled=False,
            )
            session.add(sess)
            sessions.append(sess)

        session.commit()
        conf_id = conf.id
        session_ids = [s.id for s in sessions]

    return conf_id, session_ids


# =============================================================================
# 1. Authentication, CSRF & Ownership Authorization
# =============================================================================


def test_anonymous_requests_rejected(client, sync_engine):
    """Anonymous POST, DELETE, and GET requests are strictly rejected with 401."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]

    # Anonymous POST
    res_post = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}")
    assert res_post.status_code == 401
    assert res_post.json()["detail"] == "Authentication required."

    # Anonymous DELETE
    res_del = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}")
    assert res_del.status_code == 401
    assert res_del.json()["detail"] == "Authentication required."

    # Anonymous GET
    res_get = client.get("/converge-api/v1/agenda/bookmarks/me")
    assert res_get.status_code == 401
    assert res_get.json()["detail"] == "Authentication required."


def test_invalid_expired_and_revoked_sessions_rejected(client, sync_engine):
    """Sessions that are invalid, expired, or revoked cannot access bookmark operations."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]

    # 1. Invalid token
    headers_invalid = {"Authorization": "Bearer invalid_nonexistent_token"}
    res = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers_invalid)
    assert res.status_code == 401

    # 2. Expired session
    _, token_expired = create_test_user_and_session(sync_engine, username_prefix="expired", is_expired=True)
    headers_exp = {"Authorization": f"Bearer {token_expired}"}
    res_exp = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers_exp)
    assert res_exp.status_code == 401

    # 3. Revoked session
    _, token_revoked = create_test_user_and_session(sync_engine, username_prefix="revoked", is_revoked=True)
    headers_rev = {"Authorization": f"Bearer {token_revoked}"}
    res_rev = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers_rev)
    assert res_rev.status_code == 401


def test_csrf_protection_on_state_changing_cookie_requests(client, sync_engine):
    """State-changing requests using cookie authentication require CSRF header."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    _, raw_token = create_test_user_and_session(sync_engine, username_prefix="csrf_user")

    client.cookies.set(SESSION_COOKIE_NAME, raw_token)

    # 1. POST without CSRF header -> 403 Forbidden
    res_no_csrf = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}")
    assert res_no_csrf.status_code == 403
    assert "CSRF verification failed" in res_no_csrf.json()["detail"]

    # 2. POST with custom anti-CSRF header -> 201 Created
    headers = {CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE}
    res_with_csrf = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_with_csrf.status_code == 201

    # 3. DELETE without CSRF header -> 403 Forbidden
    res_del_no_csrf = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}")
    assert res_del_no_csrf.status_code == 403

    # 4. DELETE with custom anti-CSRF header -> 204 No Content
    res_del_with_csrf = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_del_with_csrf.status_code == 204


def test_idor_isolation_between_participants(client, sync_engine):
    """A participant cannot view, delete, or mutate another participant's bookmarks."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]

    user_a, token_a = create_test_user_and_session(sync_engine, username_prefix="user_a")
    user_b, token_b = create_test_user_and_session(sync_engine, username_prefix="user_b")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A bookmarks session
    res_a_post = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers_a)
    assert res_a_post.status_code == 201

    # User B lists bookmarks -> User B's list is EMPTY (does not see User A's bookmark)
    res_b_list = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers_b)
    assert res_b_list.status_code == 200
    assert len(res_b_list.json()) == 0

    # User B attempts to DELETE session -> returns 204 (idempotent no-op for User B)
    res_b_del = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers_b)
    assert res_b_del.status_code == 204

    # User A lists bookmarks -> User A's bookmark is still intact
    res_a_list = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers_a)
    assert res_a_list.status_code == 200
    assert len(res_a_list.json()) == 1
    assert res_a_list.json()[0]["session_id"] == str(sess_id)


def test_forged_user_id_in_payload_or_params_is_ignored(client, sync_engine):
    """Caller-supplied user_id cannot override identity derived from server-side session."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]

    real_user, token = create_test_user_and_session(sync_engine, username_prefix="real_user")
    victim_user, _ = create_test_user_and_session(sync_engine, username_prefix="victim_user")

    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to supply a forged user_id query parameter
    res = client.post(
        f"/converge-api/v1/agenda/bookmarks/{sess_id}?user_id={victim_user.id}",
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    # Authority strictly binds to real authenticated user
    assert data["user_id"] == str(real_user.id)
    assert data["user_id"] != str(victim_user.id)


# =============================================================================
# 2. Bookmark Creation, Deletion & Idempotency
# =============================================================================


def test_bookmark_creation_success_and_response_dto(client, sync_engine):
    """Verify successful bookmark creation returns BookmarkResponse."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    user, token = create_test_user_and_session(sync_engine, username_prefix="create_bm")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["user_id"] == str(user.id)
    assert data["session_id"] == str(sess_id)
    assert "created_at" in data

    # Verify persisted in database
    with SASession(sync_engine) as session:
        bm = session.get(BookmarkedSession, (user.id, sess_id))
        assert bm is not None


def test_duplicate_bookmark_returns_409_conflict(client, sync_engine):
    """Creating a duplicate bookmark returns 409 Conflict."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    _, token = create_test_user_and_session(sync_engine, username_prefix="dup_bm")
    headers = {"Authorization": f"Bearer {token}"}

    # First attempt: 201 Created
    res1 = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res1.status_code == 201

    # Second attempt: 409 Conflict
    res2 = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Session already bookmarked."


def test_concurrent_duplicate_race_rolls_back_cleanly(client, sync_engine):
    """Simulate a race condition where a concurrent insert occurs, triggering
    IntegrityError on flush, confirming clean rollback and healthy subsequent queries."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    user, token = create_test_user_and_session(sync_engine, username_prefix="race_clean")
    headers = {"Authorization": f"Bearer {token}"}

    # Pre-insert bookmark into database to simulate concurrent transaction committing first
    with sync_engine.connect() as conn:
        conn.exec_driver_sql(
            "INSERT INTO agenda.bookmarked_sessions (user_id, session_id) VALUES (%s, %s);",
            (user.id, sess_id),
        )
        conn.commit()

    # Calling POST endpoint encounters duplicate and returns 409 Conflict
    res_conflict = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_conflict.status_code == 409
    assert res_conflict.json()["detail"] == "Session already bookmarked."

    # Verify session is clean and subsequent query executes without transaction error
    res_followup = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers)
    assert res_followup.status_code == 200
    assert len(res_followup.json()) == 1
    assert res_followup.json()[0]["session_id"] == str(sess_id)


def test_bookmark_deletion_success_and_idempotency(client, sync_engine):
    """Deleting a bookmark succeeds with 204; repeating delete is idempotent (returns 204)."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    user, token = create_test_user_and_session(sync_engine, username_prefix="del_bm")
    headers = {"Authorization": f"Bearer {token}"}

    # Create bookmark
    client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)

    # First delete: 204 No Content
    res_del1 = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_del1.status_code == 204

    # Verify removed from database
    with SASession(sync_engine) as session:
        bm = session.get(BookmarkedSession, (user.id, sess_id))
        assert bm is None

    # Second delete (already removed): 204 No Content (idempotent)
    res_del2 = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_del2.status_code == 204


def test_nonexistent_and_malformed_session_id(client, sync_engine):
    """Malformed UUID returns 422; nonexistent session UUID returns 404."""
    _, token = create_test_user_and_session(sync_engine, username_prefix="err_bm")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Malformed UUID
    res_malformed = client.post("/converge-api/v1/agenda/bookmarks/not-a-uuid", headers=headers)
    assert res_malformed.status_code == 422

    # 2. Nonexistent UUID
    random_uuid = uuid.uuid4()
    res_nonexistent = client.post(f"/converge-api/v1/agenda/bookmarks/{random_uuid}", headers=headers)
    assert res_nonexistent.status_code == 404
    assert res_nonexistent.json()["detail"] == "Session not found."


def test_inactive_conference_sessions_cannot_be_bookmarked(client, sync_engine):
    """Sessions belonging to inactive/unpublished conferences return 404 Not Found."""
    _, session_ids = create_conference_and_sessions(sync_engine, is_active=False)
    sess_id = session_ids[0]
    _, token = create_test_user_and_session(sync_engine, username_prefix="inactive_bm")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Session not found."


def test_cancelled_session_bookmark_behavior(client, sync_engine):
    """Published sessions that are cancelled can be bookmarked and retain cancellation status."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Cancelled Test Conf",
            venue_name="Hall X",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
            is_active=True,
        )
        session.add(conf)
        session.flush()

        sess = Session(
            conference_id=conf.id,
            title="Cancelled Session To Bookmark",
            hall_room="Hall C",
            start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
            is_cancelled=True,
        )
        session.add(sess)
        session.commit()
        sess_id = sess.id

    _, token = create_test_user_and_session(sync_engine, username_prefix="canc_bm")
    headers = {"Authorization": f"Bearer {token}"}

    res_post = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_post.status_code == 201

    res_list = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert items[0]["session"]["is_cancelled"] is True


# =============================================================================
# 3. Bookmark Listing & Privacy
# =============================================================================


def test_list_my_bookmarks_empty(client, sync_engine):
    """Participant with no bookmarks receives an empty array."""
    _, token = create_test_user_and_session(sync_engine, username_prefix="empty_bms")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_my_bookmarks_deterministic_ordering_and_pagination(client, sync_engine):
    """Bookmarks are returned ordered chronologically by session start_time and support pagination."""
    _, session_ids = create_conference_and_sessions(sync_engine, session_count=3)
    user, token = create_test_user_and_session(sync_engine, username_prefix="order_bms")
    headers = {"Authorization": f"Bearer {token}"}

    # Bookmark in reverse order
    client.post(f"/converge-api/v1/agenda/bookmarks/{session_ids[2]}", headers=headers)
    client.post(f"/converge-api/v1/agenda/bookmarks/{session_ids[0]}", headers=headers)
    client.post(f"/converge-api/v1/agenda/bookmarks/{session_ids[1]}", headers=headers)

    # List all: must be ordered chronologically (Session 1, Session 2, Session 3)
    res_all = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers)
    assert res_all.status_code == 200
    items = res_all.json()
    assert len(items) == 3
    assert items[0]["session"]["title"] == "Session 1 - Track A"
    assert items[1]["session"]["title"] == "Session 2 - Track A"
    assert items[2]["session"]["title"] == "Session 3 - Track A"

    # Pagination: limit=1, offset=0
    res_page1 = client.get("/converge-api/v1/agenda/bookmarks/me?limit=1&offset=0", headers=headers)
    assert res_page1.status_code == 200
    assert len(res_page1.json()) == 1
    assert res_page1.json()[0]["session"]["title"] == "Session 1 - Track A"

    # Pagination: limit=1, offset=1
    res_page2 = client.get("/converge-api/v1/agenda/bookmarks/me?limit=1&offset=1", headers=headers)
    assert res_page2.status_code == 200
    assert len(res_page2.json()) == 1
    assert res_page2.json()[0]["session"]["title"] == "Session 2 - Track A"


def test_bookmark_response_dto_excludes_private_and_internal_data(client, sync_engine):
    """Response DTO contains only public session info, scrubbing internal batch ID and user credentials."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Privacy Check Conf",
            venue_name="Privacy Center",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
            is_active=True,
        )
        session.add(conf)
        session.flush()

        sess = Session(
            conference_id=conf.id,
            title="Privacy Protected Session",
            hall_room="Room P",
            start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
            import_batch_id="internal_batch_secret_123",
        )
        session.add(sess)
        session.commit()
        sess_id = sess.id

    _, token = create_test_user_and_session(sync_engine, username_prefix="privacy_bms")
    headers = {"Authorization": f"Bearer {token}"}
    client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)

    res = client.get("/converge-api/v1/agenda/bookmarks/me", headers=headers)
    assert res.status_code == 200
    item = res.json()[0]

    # Verify session details exist
    assert item["session_id"] == str(sess_id)
    assert "bookmarked_at" in item
    assert "session" in item

    # Verify internal and sensitive fields are scrubbed
    raw_json = res.text
    assert "import_batch_id" not in raw_json
    assert "internal_batch_secret_123" not in raw_json
    assert "password_hash" not in raw_json
    assert "email" not in raw_json


# =============================================================================
# 4. Integrity, Cascades & Audit Logging
# =============================================================================


def test_user_deletion_cascades_to_bookmarks_gap10(client, sync_engine):
    """GAP-10: Deleting a participant user immediately cascades and purges their bookmarks."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    user, token = create_test_user_and_session(sync_engine, username_prefix="cascade_u")
    headers = {"Authorization": f"Bearer {token}"}

    # Bookmark session
    client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)

    # Verify bookmark exists in DB
    with SASession(sync_engine) as session:
        bm = session.get(BookmarkedSession, (user.id, sess_id))
        assert bm is not None

        # Delete user
        u = session.get(User, user.id)
        session.delete(u)
        session.commit()

    # Verify bookmark is purged
    with SASession(sync_engine) as session:
        bm_after = session.get(BookmarkedSession, (user.id, sess_id))
        assert bm_after is None


def test_session_deletion_cascades_to_bookmarks(client, sync_engine):
    """Deleting a conference session immediately cascades and purges all bookmarks for it."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    user, token = create_test_user_and_session(sync_engine, username_prefix="cascade_s")
    headers = {"Authorization": f"Bearer {token}"}

    # Bookmark session
    client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)

    # Delete session from DB
    with SASession(sync_engine) as session:
        s = session.get(Session, sess_id)
        session.delete(s)
        session.commit()

    # Verify bookmark is purged
    with SASession(sync_engine) as session:
        bm_after = session.get(BookmarkedSession, (user.id, sess_id))
        assert bm_after is None


def test_audit_events_recorded_and_sanitized(client, sync_engine):
    """Creating and deleting bookmarks logs sanitized audit records in core.audit_logs."""
    _, session_ids = create_conference_and_sessions(sync_engine)
    sess_id = session_ids[0]
    user, token = create_test_user_and_session(sync_engine, username_prefix="audit_u")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create bookmark
    res_create = client.post(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_create.status_code == 201

    # 2. Delete bookmark
    res_del = client.delete(f"/converge-api/v1/agenda/bookmarks/{sess_id}", headers=headers)
    assert res_del.status_code == 204

    # 3. Check audit log entries
    with SASession(sync_engine) as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.asc())
        ).scalars().all()

        assert len(logs) == 2
        log_create, log_delete = logs[0], logs[1]

        assert log_create.action_type == "agenda.bookmark.create"
        assert log_create.resource_type == "agenda.session"
        assert log_create.resource_id == str(sess_id)
        assert log_create.actor_username == user.username
        assert "ip_hash" in log_create.event_payload

        assert log_delete.action_type == "agenda.bookmark.delete"
        assert log_delete.resource_type == "agenda.session"
        assert log_delete.resource_id == str(sess_id)
        assert log_delete.actor_username == user.username
        assert "ip_hash" in log_delete.event_payload

        # Ensure no secrets or tokens in audit logs
        for l in logs:
            payload_str = str(l.event_payload).lower()
            assert "token" not in payload_str
            assert "password" not in payload_str
            assert "secret" not in payload_str
