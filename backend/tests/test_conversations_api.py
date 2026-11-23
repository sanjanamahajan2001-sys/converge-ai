"""Contract, lifecycle, concurrency, quota, and real-time delivery tests for Conversations API (P5-WS2, GAP-06)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
from app.db.models.conversation import Conversation, ConversationOutcome, ConversationStatus, Message
from app.db.models.profile import AvailabilityStatus, ParticipantProfile, ParticipationIntent
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
        f"SAFETY GUARD: Refusing to run tests against non-test DB: {TEST_DB_URL}"
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
    """Create a synchronous SQLAlchemy engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_test_db(sync_engine):
    """Clean up records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM core.messages;")
            conn.exec_driver_sql("DELETE FROM core.conversations;")
            conn.exec_driver_sql("DELETE FROM core.participant_topics;")
            conn.exec_driver_sql("DELETE FROM core.participant_hobbies;")
            conn.exec_driver_sql("DELETE FROM core.participant_profiles;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.login_rate_limits;")
            conn.exec_driver_sql("DELETE FROM core.audit_logs;")
            conn.exec_driver_sql("DELETE FROM core.users;")
            conn.commit()

    _clean()
    yield
    _clean()


def create_test_participant(
    sync_engine,
    username: str,
    email: str,
    has_profile: bool = True,
) -> Tuple[User, str]:
    """Create a participant with active session and initialized profile."""
    with SASession(sync_engine) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=f"Full Name of {username}",
            company_name="Innovate Corp",
            job_title="Software Architect",
            phone_number="+1-555-0100",
            is_active=True,
        )
        session.add(user)
        session.flush()

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        now = datetime.now(timezone.utc)

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=24),
            last_accessed_at=now,
        )
        session.add(user_session)

        if has_profile:
            profile = ParticipantProfile(
                user_id=user.id,
                bio_summary=f"Bio for {username}",
                intent=ParticipationIntent.NETWORKING,
                availability=AvailabilityStatus.AVAILABLE,
                allow_agent_matching=True,
            )
            session.add(profile)

        session.commit()
        session.refresh(user)
        return user, raw_token


def test_unauthenticated_requests_rejected(client):
    """Anonymous requests must return 401 Unauthorized."""
    res = client.get("/converge-api/v1/conversations")
    assert res.status_code == 401

    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(uuid.uuid4())},
    )
    assert res.status_code == 401


def test_csrf_protection_on_post(client, sync_engine):
    """State-changing requests with cookie authentication must provide CSRF header."""
    user, token = create_test_participant(sync_engine, "csrf_user", "csrf@example.com")
    target, _ = create_test_participant(sync_engine, "csrf_target", "csrftarget@example.com")

    # Missing CSRF header
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(target.id)},
        cookies={SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 403

    # With CSRF header
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(target.id)},
        cookies={SESSION_COOKIE_NAME: token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert res.status_code == 201


def test_cannot_initiate_with_self(client, sync_engine):
    """Participant cannot start a conversation with themselves."""
    user, token = create_test_participant(sync_engine, "self_user", "self@example.com")

    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(user.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "yourself" in res.json()["detail"].lower()


def test_initiate_with_nonexistent_or_uninitialized_target(client, sync_engine):
    """Target participant must exist and have initialized profile."""
    user, token = create_test_participant(sync_engine, "user_a", "usera@example.com")
    fake_id = uuid.uuid4()

    # Nonexistent user
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(fake_id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404

    # User without profile
    no_prof_user, _ = create_test_participant(sync_engine, "no_prof", "noprof@example.com", has_profile=False)
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(no_prof_user.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert "profile" in res.json()["detail"].lower()


def test_conversation_lifecycle_and_turn_limit(client, sync_engine):
    """Full lifecycle: Invite -> Accept -> 20 Message turns -> Auto Completion -> Post-completion rejection."""
    alice, alice_token = create_test_participant(sync_engine, "alice_msg", "alice_msg@example.com")
    bob, bob_token = create_test_participant(sync_engine, "bob_msg", "bob_msg@example.com")

    alice_hdr = {"Authorization": f"Bearer {alice_token}"}
    bob_hdr = {"Authorization": f"Bearer {bob_token}"}

    # 1. Alice invites Bob
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(bob.id)},
        headers=alice_hdr,
    )
    assert res.status_code == 201
    conv_id = res.json()["id"]
    assert res.json()["status"] == "INVITED"

    # 2. Cannot send messages while in INVITED status
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/messages",
        json={"content": "Early message"},
        headers=alice_hdr,
    )
    assert res.status_code == 400

    # 3. Alice (initiator) cannot accept the invitation
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/accept",
        headers=alice_hdr,
    )
    assert res.status_code == 403

    # 4. Bob accepts the invitation
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/accept",
        headers=bob_hdr,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"

    # 5. Send message turns 0 through 28
    for turn in range(29):
        sender_hdr = alice_hdr if turn % 2 == 0 else bob_hdr
        res = client.post(
            f"/converge-api/v1/conversations/{conv_id}/messages",
            json={"content": f"Turn message index {turn}"},
            headers=sender_hdr,
        )
        assert res.status_code == 201, f"Failed turn {turn}: {res.text}"
        data = res.json()
        assert data["turn_index"] == turn

    # Verify conversation is still ACTIVE before turn 29
    res = client.get(f"/converge-api/v1/conversations/{conv_id}", headers=alice_hdr)
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"
    assert len(res.json()["messages"]) == 29

    # 6. Send message turn 29 (the 30th message) -> triggers atomic auto-completion!
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/messages",
        json={"content": "Final 30th message"},
        headers=bob_hdr,
    )
    assert res.status_code == 201
    assert res.json()["turn_index"] == 29

    # 7. Check that conversation is now atomically COMPLETED
    res = client.get(f"/converge-api/v1/conversations/{conv_id}", headers=alice_hdr)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["terminal_outcome"] == "COMPLETED_WITHOUT_PROPOSAL"
    assert data["concluded_at"] is not None

    # 8. Attempting turn 30 must return 409 Conflict
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/messages",
        json={"content": "Extra 31st message rejected"},
        headers=alice_hdr,
    )
    assert res.status_code == 409


def test_idor_protection(client, sync_engine):
    """User C cannot view or send messages to User A & User B conversation."""
    alice, alice_token = create_test_participant(sync_engine, "alice_idor", "alice_idor@example.com")
    bob, bob_token = create_test_participant(sync_engine, "bob_idor", "bob_idor@example.com")
    charlie, charlie_token = create_test_participant(sync_engine, "charlie_idor", "charlie_idor@example.com")

    # Alice invites Bob
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(bob.id)},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    conv_id = res.json()["id"]

    # Charlie attempts to view conversation details
    res = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {charlie_token}"},
    )
    assert res.status_code == 403

    # Charlie attempts to send message
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/messages",
        json={"content": "Intruder message"},
        headers={"Authorization": f"Bearer {charlie_token}"},
    )
    assert res.status_code == 403


def test_unique_active_pair_reverse_direction(client, sync_engine):
    """Reverse-direction invitation between active pair must be rejected with 409 Conflict."""
    alice, alice_token = create_test_participant(sync_engine, "alice_dup", "alicedup@example.com")
    bob, bob_token = create_test_participant(sync_engine, "bob_dup", "bobdup@example.com")

    # Alice invites Bob
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(bob.id)},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res.status_code == 201

    # Bob attempts to invite Alice while previous is active/invited
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(alice.id)},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"].lower()


def test_max_active_quota_enforcement(client, sync_engine):
    """Participant cannot have more than 3 active/invited conversations concurrently."""
    alice, alice_token = create_test_participant(sync_engine, "alice_quota", "alicequota@example.com")
    peers = [
        create_test_participant(sync_engine, f"peer_{i}", f"peer_{i}@example.com")[0]
        for i in range(4)
    ]

    alice_hdr = {"Authorization": f"Bearer {alice_token}"}

    # Alice creates 3 conversations (reaching quota limit)
    for i in range(3):
        res = client.post(
            "/converge-api/v1/conversations",
            json={"target_id": str(peers[i].id)},
            headers=alice_hdr,
        )
        assert res.status_code == 201

    # 4th conversation creation attempt must return 429
    res = client.post(
        "/converge-api/v1/conversations",
        json={"target_id": str(peers[3].id)},
        headers=alice_hdr,
    )
    assert res.status_code == 429
    assert "quota" in res.json()["detail"].lower()


def test_cooldown_enforcement(client, sync_engine):
    """Pair in cooldown cannot start a new conversation until cooldown window elapses."""
    alice, alice_token = create_test_participant(sync_engine, "alice_cd", "alicecd@example.com")
    bob, bob_token = create_test_participant(sync_engine, "bob_cd", "bobcd@example.com")

    alice_hdr = {"Authorization": f"Bearer {alice_token}"}
    bob_hdr = {"Authorization": f"Bearer {bob_token}"}

    # 1. Alice invites Bob and Bob accepts
    res = client.post("/converge-api/v1/conversations", json={"target_id": str(bob.id)}, headers=alice_hdr)
    conv_id = res.json()["id"]
    client.post(f"/converge-api/v1/conversations/{conv_id}/accept", headers=bob_hdr)

    # 2. Conclude with COMPLETED_WITHOUT_PROPOSAL (triggers 48h cooldown)
    res = client.post(
        f"/converge-api/v1/conversations/{conv_id}/conclude",
        json={"action": "CONCLUDE", "outcome": "COMPLETED_WITHOUT_PROPOSAL"},
        headers=alice_hdr,
    )
    assert res.status_code == 200

    # 3. Alice attempts to initiate a new conversation immediately -> rejected with 403
    res = client.post("/converge-api/v1/conversations", json={"target_id": str(bob.id)}, headers=alice_hdr)
    assert res.status_code == 403
    assert "cooldown" in res.json()["detail"].lower()


def test_real_time_websocket_message_delivery(client, sync_engine):
    """User A sends a message via REST; User B receives it instantly on WebSocket without refreshing."""
    alice, alice_token = create_test_participant(sync_engine, "alice_ws", "alicews@example.com")
    bob, bob_token = create_test_participant(sync_engine, "bob_ws", "bobws@example.com")

    alice_hdr = {"Authorization": f"Bearer {alice_token}"}
    bob_hdr = {"Authorization": f"Bearer {bob_token}"}

    # 1. Alice creates conversation and Bob accepts
    res = client.post("/converge-api/v1/conversations", json={"target_id": str(bob.id)}, headers=alice_hdr)
    conv_id = res.json()["id"]
    client.post(f"/converge-api/v1/conversations/{conv_id}/accept", headers=bob_hdr)

    # 2. Bob connects to the WebSocket stream
    with client.websocket_connect(f"/converge-api/v1/conversations/ws/{conv_id}?token={bob_token}") as ws:
        # Ping check
        ws.send_text("ping")
        assert ws.receive_text() == "pong"

        # 3. Alice sends a message via REST
        res = client.post(
            f"/converge-api/v1/conversations/{conv_id}/messages",
            json={"content": "Instant delivery message from Alice!"},
            headers=alice_hdr,
        )
        assert res.status_code == 201

        # 4. Bob receives the event instantly on WebSocket without reloading
        event = ws.receive_json()
        assert event["event"] == "message:new"
        assert event["data"]["content"] == "Instant delivery message from Alice!"
        assert event["data"]["turn_index"] == 0
        assert event["data"]["sender_id"] == str(alice.id)


def test_cannot_initiate_without_consent_or_when_unavailable(client, sync_engine):
    """Cannot initiate conversation if target has disabled matching consent or is DND/OFFLINE."""
    alice, alice_token = create_test_participant(sync_engine, "alice_consent", "alice_c@example.com")
    bob, _ = create_test_participant(sync_engine, "bob_noconsent", "bob_noconsent@example.com")
    charlie, _ = create_test_participant(sync_engine, "charlie_dnd", "charlie_dnd@example.com")

    # Set Bob consent to False and Charlie availability to DO_NOT_DISTURB
    with SASession(sync_engine) as session:
        bob_prof = session.query(ParticipantProfile).filter_by(user_id=bob.id).one()
        bob_prof.allow_agent_matching = False
        charlie_prof = session.query(ParticipantProfile).filter_by(user_id=charlie.id).one()
        charlie_prof.availability = AvailabilityStatus.DO_NOT_DISTURB
        session.commit()

    alice_hdr = {"Authorization": f"Bearer {alice_token}"}

    # Initiating with Bob (no consent) -> 403 Forbidden
    res = client.post("/converge-api/v1/conversations", json={"target_id": str(bob.id)}, headers=alice_hdr)
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()

    # Initiating with Charlie (DND) -> 403 Forbidden
    res = client.post("/converge-api/v1/conversations", json={"target_id": str(charlie.id)}, headers=alice_hdr)
    assert res.status_code == 403
    assert "unavailable" in res.json()["detail"].lower()
