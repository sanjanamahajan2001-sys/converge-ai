"""Integration tests for User Activity and Interaction Tracking APIs (Phase 2)."""
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    CSRF_EXPECTED_VALUE,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models import Conversation, Message, User, UserActivityEvent, UserSession
from app.db.models.conversation import ConversationStatus, MessageSenderType
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to test DB."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Refusing to run integration tests against non-test DB: {TEST_DB_URL}"
    )
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    """Yield test client."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def test_user(sync_engine):
    """Seed test user and session."""
    user_id = uuid.uuid4()
    unique_suffix = user_id.hex[:6]
    token = generate_session_token()
    token_hash = hash_session_token(token)

    with Session(sync_engine) as session:
        user = User(
            id=user_id,
            username=f"analyst_{unique_suffix}",
            email=f"analyst_{unique_suffix}@conference.org",
            password_hash=hash_password("AnalystPass!123"),
            full_name="Analytics Tester",
            is_active=True,
        )
        session.add(user)
        session.flush()

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_agent="Pytest-Test-Agent",
        )
        session.add(user_session)
        session.commit()

    yield {
        "user_id": user_id,
        "token": token,
        "username": f"analyst_{unique_suffix}",
    }

    # Cleanup
    with Session(sync_engine) as session:
        session.execute(text(f"DELETE FROM core.user_activity_events WHERE user_id = '{user_id}'"))
        session.execute(text(f"DELETE FROM core.user_sessions WHERE user_id = '{user_id}'"))
        session.execute(text(f"DELETE FROM core.messages WHERE sender_id = '{user_id}'"))
        session.execute(text(f"DELETE FROM core.conversations WHERE initiator_id = '{user_id}' OR target_id = '{user_id}'"))
        session.execute(text(f"DELETE FROM core.users WHERE id = '{user_id}'"))
        session.commit()


def test_record_activity_event_unauthenticated(client):
    """Unauthenticated calls to /analytics/events must return 401."""
    res = client.post(
        "/converge-api/v1/analytics/events",
        json={"event_type": "FEATURE_CLICK", "feature_name": "AGENDA_EXPLORE"},
    )
    assert res.status_code == 401


def test_record_activity_event_and_privacy_sanitization(client, test_user):
    """Record an activity event and verify sensitive credentials are sanitized."""
    client.cookies.set(SESSION_COOKIE_NAME, test_user["token"])

    payload = {
        "event_type": "FEATURE_CLICK",
        "feature_name": "AGENDA_SESSION_FILTER",
        "target_resource_id": "session_tea_01",
        "details": {
            "component": "SessionList",
            "tag": "Networking",
            "password": "SuperSecretPassword123!",
            "token": "bearer-sensitive-token",
        },
    }
    headers = {CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE}
    res = client.post("/converge-api/v1/analytics/events", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["event_type"] == "FEATURE_CLICK"
    assert data["feature_name"] == "AGENDA_SESSION_FILTER"
    assert data["target_resource_id"] == "session_tea_01"
    # Privacy check: sensitive keys must have been scrubbed
    assert "password" not in data["details"]
    assert "token" not in data["details"]
    assert data["details"]["component"] == "SessionList"


def test_record_agent_visit_event(client, test_user):
    """Record AGENT_VISIT event."""
    client.cookies.set(SESSION_COOKIE_NAME, test_user["token"])

    payload = {
        "event_type": "AGENT_VISIT",
        "feature_name": "MATCHING_VIRTUAL_REPRESENTATIVE",
        "target_resource_id": "candidate_456",
        "details": {"action": "view_profile"},
    }
    headers = {CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE}
    res = client.post("/converge-api/v1/analytics/events", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["event_type"] == "AGENT_VISIT"
    assert data["feature_name"] == "MATCHING_VIRTUAL_REPRESENTATIVE"


def test_get_my_activity_summary(client, test_user, sync_engine):
    """Verify get_my_activity_summary calculates logins, conversation history, and events."""
    client.cookies.set(SESSION_COOKIE_NAME, test_user["token"])

    # Create partner and a conversation with messages
    partner_id = uuid.uuid4()
    conv_id = None
    with Session(sync_engine) as session:
        partner = User(
            id=partner_id,
            username=f"partner_{partner_id.hex[:6]}",
            email=f"partner_{partner_id.hex[:6]}@conf.org",
            password_hash=hash_password("StrongPass123!"),
            full_name="Partner Person",
            is_active=True,
        )
        session.add(partner)
        session.flush()

        conv = Conversation(
            initiator_id=test_user["user_id"],
            target_id=partner.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()
        conv_id = conv.id

        msg = Message(
            conversation_id=conv.id,
            sender_id=test_user["user_id"],
            sender_type=MessageSenderType.PARTICIPANT,
            turn_index=0,
            content="Hello partner!",
        )
        session.add(msg)
        session.commit()

    # Query summary
    res = client.get("/converge-api/v1/analytics/my-summary")
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == str(test_user["user_id"])
    assert data["total_logins"] >= 1
    assert data["active_sessions"] >= 1
    assert data["total_conversations"] >= 1
    assert data["conversations_initiated"] >= 1

    # Check conversation history
    history = data["conversation_history"]
    assert len(history) >= 1
    partner_item = next((h for h in history if h["partner_id"] == str(partner_id)), None)
    assert partner_item is not None
    assert partner_item["partner_name"] == "Partner Person"
    assert partner_item["role"] == "INITIATOR"
    assert partner_item["turn_count"] >= 1

    # Clean up partner
    with Session(sync_engine) as session:
        session.execute(text(f"DELETE FROM core.messages WHERE conversation_id = '{conv_id}'"))
        session.execute(text(f"DELETE FROM core.conversations WHERE id = '{conv_id}'"))
        session.execute(text(f"DELETE FROM core.users WHERE id = '{partner_id}'"))
        session.commit()


def test_get_analytics_overview(client, test_user):
    """Verify overview returns platform aggregate metrics."""
    client.cookies.set(SESSION_COOKIE_NAME, test_user["token"])

    res = client.get("/converge-api/v1/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_users" in data
    assert "total_logins" in data
    assert "active_sessions" in data
    assert "total_conversations" in data
    assert "total_activity_events" in data
    assert isinstance(data["top_features"], list)
    assert isinstance(data["top_agents"], list)


def test_get_user_activity_summary_by_id(client, test_user):
    """Verify summary by ID works and handles 404 for nonexistent user."""
    client.cookies.set(SESSION_COOKIE_NAME, test_user["token"])

    res = client.get(f"/converge-api/v1/analytics/users/{test_user['user_id']}/summary")
    assert res.status_code == 200
    assert res.json()["user_id"] == str(test_user["user_id"])

    # Nonexistent user ID
    fake_id = uuid.uuid4()
    res404 = client.get(f"/converge-api/v1/analytics/users/{fake_id}/summary")
    assert res404.status_code == 404
