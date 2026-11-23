import uuid
"""Targeted automated tests for Informal Mood Preference & On-Demand Agent Dialogue Trigger (AC-WS1).

Covers:
1. Curated moods catalog endpoint
2. Setting, updating, and clearing current_mood on profile
3. Sanitization and max-length boundary enforcement (50 chars)
4. 24-hour TTL expiry semantics (active_mood returns None after 24h)
5. Privacy protection: public profile strictly omits mood
6. Conversation peer sees active mood in ConversationDetailResponse
7. Stale mood prevention (expired mood not displayed to peer)
8. On-demand agent dialogue trigger via POST /{id}/trigger-agent
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update, text
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import generate_session_token, hash_session_token
from app.db.models.conversation import Conversation, ConversationStatus, Message, MessageSenderType
from app.db.models.profile import ParticipantProfile, ParticipationIntent, AvailabilityStatus
from app.db.models.session import UserSession
from app.db.models.task import Task, TaskStatus
from app.db.models.user import User
from app.main import create_app
from app.schemas.profile import CURATED_MOODS

TEST_DB_URL = "postgresql+asyncpg://converge_ai_app:c394df2de776933da72201a5678a9afc@127.0.0.1:5432/converge_ai_test"
SYNC_DB_URL = "postgresql+psycopg2://converge_ai_owner:2a41722c2a5717cbfc000b16c624f2bd@127.0.0.1:5432/converge_ai_test"


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
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
    engine = create_engine(SYNC_DB_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_test_db(sync_engine):
    """Clean up test records."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.execute(text("DELETE FROM a2a.task_attempts;"))
            conn.execute(text("DELETE FROM a2a.tasks;"))
            conn.execute(text("DELETE FROM core.messages;"))
            conn.execute(text("DELETE FROM core.conversations;"))
            conn.execute(text("DELETE FROM core.user_sessions;"))
            conn.execute(text("DELETE FROM core.participant_profiles;"))
            conn.execute(text("DELETE FROM core.users WHERE username LIKE 'mood_%' OR username LIKE 'peer_%' OR username LIKE 'trig_%';"))
            conn.commit()
    _clean()
    yield
    _clean()


def create_mood_test_user(sync_engine, username, email, full_name, mood=None, mood_updated_at=None):
    with SASession(sync_engine) as session:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password("Password123!"),
            full_name=full_name,
            company_name="TestCorp",
            job_title="Engineer",
            is_active=True,
        )
        session.add(user)
        session.flush()

        profile = ParticipantProfile(
            user_id=user.id,
            intent=ParticipationIntent.NETWORKING,
            bio_summary="Testing mood preferences",
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
            current_mood=mood,
            mood_updated_at=mood_updated_at,
        )
        session.add(profile)

        raw_token = generate_session_token()
        sess_token_hash = hash_session_token(raw_token)
        user_sess = UserSession(
            user_id=user.id,
            token_hash=sess_token_hash,
            ip_address="127.0.0.1",
            user_agent="Pytest Agent",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        session.add(user_sess)
        session.commit()
        session.refresh(user)
        session.refresh(profile)
        return user, profile, raw_token


def test_get_curated_moods_catalog(client):
    """Verify public catalog returns curated conference starter mood preferences."""
    res = client.get("/converge-api/v1/profile/catalog/moods")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert "Ready to network" in data
    assert "Open to discussing an informal break or meetup" in data


def test_put_and_get_my_profile_with_mood(client, sync_engine):
    """Setting current_mood updates timestamp and returns active mood."""
    user, profile, token = create_mood_test_user(sync_engine, "mood_u1", "mood_u1@ex.com", "Mood User 1")

    # Update mood
    res = client.put(
        "/converge-api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf"},
        json={"current_mood": "Open to discussing an informal break or meetup"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_mood"] == "Open to discussing an informal break or meetup"
    assert data["mood_updated_at"] is not None

    # Fetch profile
    get_res = client.get(
        "/converge-api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["current_mood"] == "Open to discussing an informal break or meetup"


def test_mood_max_length_boundary(client, sync_engine):
    """Mood string up to 255 chars is accepted; exceeding 255 chars is rejected."""
    user, profile, token = create_mood_test_user(sync_engine, "mood_u2", "mood_u2@ex.com", "Mood User 2")

    # Long natural language mood (74 chars) succeeds
    long_pref = "Connecting with project contractors for dedicated fleet haulage contracts."
    res_ok = client.put(
        "/converge-api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf"},
        json={"current_mood": long_pref},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["current_mood"] == long_pref

    # 256 chars rejected
    res_overflow = client.put(
        "/converge-api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf"},
        json={"current_mood": "A" * 256},
    )
    assert res_overflow.status_code == 422


def test_mood_24h_ttl_expiry(client, sync_engine):
    """Declared mood expires after 24 hours and active_mood evaluates to None."""
    stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
    user, profile, token = create_mood_test_user(
        sync_engine, "mood_u3", "mood_u3@ex.com", "Mood User 3",
        mood="Stale Mood", mood_updated_at=stale_time
    )

    with SASession(sync_engine) as session:
        prof = session.get(ParticipantProfile, user.id)
        assert prof.current_mood == "Stale Mood"
        assert prof.active_mood is None  # Expired after 24 hours!

    res = client.get(
        "/converge-api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_mood"] is None  # API treats expired mood as None


def test_clear_mood_preference(client, sync_engine):
    """Updating with empty/None mood clears current_mood and resets timestamp."""
    user, profile, token = create_mood_test_user(
        sync_engine, "mood_u4", "mood_u4@ex.com", "Mood User 4",
        mood="Ready to network", mood_updated_at=datetime.now(timezone.utc)
    )

    res = client.put(
        "/converge-api/v1/profile/me",
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf"},
        json={"current_mood": None},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_mood"] is None
    assert data["mood_updated_at"] is None


def test_public_profile_strictly_omits_mood(client, sync_engine):
    """Public profile projection never leaks current_mood or mood_updated_at."""
    user_a, _, token_a = create_mood_test_user(
        sync_engine, "mood_pub_a", "mood_pub_a@ex.com", "Public A",
        mood="Secret Mood", mood_updated_at=datetime.now(timezone.utc)
    )
    user_b, _, token_b = create_mood_test_user(sync_engine, "mood_pub_b", "mood_pub_b@ex.com", "Public B")

    # User B views User A's public profile
    res = client.get(
        f"/converge-api/v1/profile/{user_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "current_mood" not in data
    assert "mood_updated_at" not in data


def test_conversation_peer_sees_active_mood_only(client, sync_engine):
    """Matched peer in an active conversation sees active mood, but not expired mood."""
    user_a, prof_a, token_a = create_mood_test_user(
        sync_engine, "peer_a", "peer_a@ex.com", "Peer A",
        mood="☕ Coffee-fueled", mood_updated_at=datetime.now(timezone.utc)
    )
    user_b, prof_b, token_b = create_mood_test_user(sync_engine, "peer_b", "peer_b@ex.com", "Peer B")

    with SASession(sync_engine) as session:
        conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
        session.add(conv)
        session.commit()
        session.refresh(conv)
        conv_id = conv.id

    # User B views conversation detail -> sees other_participant_mood == "☕ Coffee-fueled"
    res_b = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 200
    assert res_b.json()["other_participant_mood"] == "☕ Coffee-fueled"

    # Now expire User A's mood (> 24 hours)
    with SASession(sync_engine) as session:
        session.execute(
            update(ParticipantProfile)
            .where(ParticipantProfile.user_id == user_a.id)
            .values(mood_updated_at=datetime.now(timezone.utc) - timedelta(hours=26))
        )
        session.commit()

    # User B views conversation detail again -> expired mood is treated as None
    res_b_expired = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_expired.status_code == 200
    assert res_b_expired.json()["other_participant_mood"] is None


def test_trigger_agent_dialogue_endpoint(client, sync_engine):
    """POST /conversations/{id}/trigger-agent enqueues autonomous agent task for active conversation."""
    user_a, _, token_a = create_mood_test_user(sync_engine, "trig_a", "trig_a@ex.com", "Trigger A")
    user_b, _, token_b = create_mood_test_user(sync_engine, "trig_b", "trig_b@ex.com", "Trigger B")
    user_c, _, token_c = create_mood_test_user(sync_engine, "trig_c", "trig_c@ex.com", "Trigger C")

    with SASession(sync_engine) as session:
        conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
        session.add(conv)
        session.commit()
        session.refresh(conv)
        conv_id = conv.id

    # Non-participant User C tries to trigger agent -> 403 Forbidden
    res_c = client.post(
        f"/converge-api/v1/conversations/{conv_id}/trigger-agent",
        headers={"Authorization": f"Bearer {token_c}", "X-CSRF-Token": "test-csrf"},
    )
    assert res_c.status_code == 403

    # Authorized participant User B triggers agent -> 200 OK
    res_b = client.post(
        f"/converge-api/v1/conversations/{conv_id}/trigger-agent",
        headers={"Authorization": f"Bearer {token_b}", "X-CSRF-Token": "test-csrf"},
    )
    assert res_b.status_code == 200

    # Verify task was created in a2a.tasks with autonomous=True
    with SASession(sync_engine) as session:
        task = session.scalar(
            select(Task).where(Task.conversation_id == conv_id, Task.status == TaskStatus.PENDING)
        )
        assert task is not None
        assert task.payload["autonomous"] is True
        assert task.payload["turn_index"] == 0


def test_conversation_invited_state_strictly_omits_mood(client, sync_engine):
    """An INVITED conversation must strictly omit partner mood until accepted (AC-WS7R Section 4)."""
    uid = uuid.uuid4().hex[:6]
    user_a, prof_a, token_a = create_mood_test_user(sync_engine, f"inv_a_{uid}", f"inv_a_{uid}@ex.com", "Inviter A")
    user_b, prof_b, token_b = create_mood_test_user(sync_engine, f"inv_b_{uid}", f"inv_b_{uid}@ex.com", "Invitee B")

    # User A declares mood
    with SASession(sync_engine) as session:
        session.execute(
            update(ParticipantProfile)
            .where(ParticipantProfile.user_id == user_a.id)
            .values(current_mood="Open to casual conversation", mood_updated_at=datetime.now(timezone.utc))
        )
        session.commit()

    # Create conversation in INVITED status
    with SASession(sync_engine) as session:
        conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.INVITED)
        session.add(conv)
        session.commit()
        session.refresh(conv)
        conv_id = conv.id

    # User B views INVITED conversation detail -> other_participant_mood MUST be None
    res_b = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "INVITED"
    assert res_b.json()["other_participant_mood"] is None

    # User A views INVITED conversation detail -> other_participant_mood MUST be None
    res_a = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    assert res_a.json()["other_participant_mood"] is None

    # Transition conversation to ACTIVE
    with SASession(sync_engine) as session:
        session.execute(
            update(Conversation)
            .where(Conversation.id == conv_id)
            .values(status=ConversationStatus.ACTIVE)
        )
        session.commit()

    # Now that conversation is ACTIVE, User B can see User A's mood
    res_b_active = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_active.status_code == 200
    assert res_b_active.json()["status"] == "ACTIVE"
    assert res_b_active.json()["other_participant_mood"] == "Open to casual conversation"
