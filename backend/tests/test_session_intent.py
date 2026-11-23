"""Integration & Unit tests for Attendee Session Decisions & Persistent Agent Memory (AC-WS8)."""

import uuid
from datetime import date as dt_date, datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
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
from app.db.models.agenda import (
    BookmarkedSession,
    Conference,
    Session,
    SessionIntentDecision,
    SessionIntentDecisionState,
)
from app.db.models.audit import AuditLog
from app.db.models.profile import (
    AvailabilityStatus,
    ParticipantHobby,
    ParticipantProfile,
    ParticipantTopic,
    ParticipationIntent,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.db.models.conversation import Conversation, ConversationStatus, Message, MessageSenderType
from app.schemas.conversation import MessageSenderTypeEnum
from app.db.models.task import Task, TaskStatus
from app.services.agent_worker import AgentTaskService
from app.services.conversation import ConversationService
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app
from app.services.representative import DeterministicRepresentativeEngine

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
    """Yield test client with initialized database engine."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous SQLAlchemy engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
async def async_db():
    """Function-scoped AsyncSession using NullPool for async worker execution."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_tables(sync_engine):
    """Clean intent, agenda, conversation, and profile tables before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM a2a.task_attempts;")
            conn.exec_driver_sql("DELETE FROM a2a.tasks;")
            conn.exec_driver_sql("DELETE FROM core.messages;")
            conn.exec_driver_sql("DELETE FROM core.conversations;")
            conn.exec_driver_sql("DELETE FROM agenda.session_intent_decisions;")
            conn.exec_driver_sql("DELETE FROM agenda.bookmarked_sessions;")
            conn.exec_driver_sql("DELETE FROM agenda.sessions;")
            conn.exec_driver_sql("DELETE FROM agenda.conferences;")
            conn.exec_driver_sql("DELETE FROM core.participant_topics;")
            conn.exec_driver_sql("DELETE FROM core.participant_hobbies;")
            conn.exec_driver_sql("DELETE FROM core.participant_profiles;")
            conn.exec_driver_sql("DELETE FROM core.audit_logs;")
            conn.commit()
    _clean()
    yield
    _clean()


class UserHolder:
    def __init__(self, uid: uuid.UUID, username: str):
        self.id = uid
        self.username = username


def create_test_user_and_session(sync_engine, username_prefix="attendee"):
    """Create a test user, profile, and session token."""
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
            full_name=f"Full {username}",
            company_name="Acme Corp",
            job_title="Materials Engineer",
            is_active=True,
        )
        session.add(user)
        session.flush()

        profile = ParticipantProfile(
            user_id=user.id,
            intent=ParticipationIntent.NETWORKING,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
            current_mood="Conference-focused",
            mood_updated_at=now,
        )
        session.add(profile)

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=24),
            last_accessed_at=now,
            ip_address="127.0.0.1",
            user_agent="pytest-client",
        )
        session.add(user_session)
        session.commit()

    return UserHolder(uid, username), None, raw_token


def create_conference_and_session(sync_engine, title="Cement & Concrete Materials", is_cancelled=False):
    """Create conference and scheduled session."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Materials Summit 2026",
            venue_name="Hall 1",
            timezone="UTC",
            start_date=now.date(),
            end_date=(now + timedelta(days=2)).date(),
            is_active=True,
        )
        session.add(conf)
        session.flush()

        sess = Session(
            conference_id=conf.id,
            title=title,
            abstract="In-depth analysis of high-performance cement formulation.",
            track_name="Civil Engineering",
            hall_room="Auditorium B",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            is_cancelled=is_cancelled,
        )
        session.add(sess)
        session.commit()
        session.refresh(sess)
        sess_id = sess.id
    return conf, sess_id


# =============================================================================
# 1. Decision Persistence & Semantics Tests (Workspace 2 & 3)
# =============================================================================


def test_record_session_intent_attending(client, sync_engine):
    """Attendee explicitly opts in with Yes / ATTENDING."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine)

    res = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING", "source": "REPRESENTATIVE_PROMPT"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "ATTENDING"
    assert data["session_id"] == str(sess_id)
    assert data["user_id"] == str(user.id)

    # Verify PostgreSQL persistence
    with SASession(sync_engine) as session:
        record = session.scalar(
            select(SessionIntentDecision).where(
                SessionIntentDecision.user_id == user.id,
                SessionIntentDecision.session_id == sess_id,
            )
        )
        assert record is not None
        assert record.decision == "ATTENDING"

        # Verify audit event
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action_type == "agenda.session_intent_decision",
                AuditLog.user_id == user.id,
            )
        )
        assert audit is not None
        assert audit.event_payload["details"] == "ATTENDING"


def test_record_session_intent_declined_and_undecided(client, sync_engine):
    """Attendee explicitly selects No / DECLINED or Decide later / UNDECIDED."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine)

    # 1. No / DECLINED
    res1 = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "DECLINED", "source": "REPRESENTATIVE_PROMPT"},
    )
    assert res1.status_code == 200
    assert res1.json()["decision"] == "DECLINED"

    # 2. Decide later / UNDECIDED
    res2 = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "UNDECIDED", "source": "REPRESENTATIVE_PROMPT"},
    )
    assert res2.status_code == 200
    assert res2.json()["decision"] == "UNDECIDED"


def test_update_and_reverse_decision_idempotency(client, sync_engine):
    """Updating decision multiple times is idempotent and modifies the existing record."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine)

    # Initial ATTENDING
    client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING"},
    )

    # Reverse to DECLINED
    client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "DECLINED"},
    )

    with SASession(sync_engine) as session:
        records = session.scalars(
            select(SessionIntentDecision).where(
                SessionIntentDecision.user_id == user.id,
                SessionIntentDecision.session_id == sess_id,
            )
        ).all()
        assert len(records) == 1
        assert records[0].decision == "DECLINED"


def test_cancelled_session_rejects_intent(client, sync_engine):
    """Cannot record attendance intent on a cancelled session."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine, is_cancelled=True)

    res = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING"},
    )
    assert res.status_code == 400
    assert "cancelled" in res.json()["detail"].lower()


# =============================================================================
# 2. Recommendation Discovery & Prompt Generation (Workspace 2)
# =============================================================================


def test_recommendation_discovery_matches_topic_and_generates_prompt(client, sync_engine):
    """Representative identifies relevant session from attendee topic and formats prompt."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine, title="Cement & Advanced Concrete Formulation")

    # Add topic "cement"
    with SASession(sync_engine) as session:
        session.add(ParticipantTopic(user_id=user.id, topic_keyword="cement"))
        session.commit()

    res = client.get(
        "/converge-api/v1/agenda/recommendations/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    prompt_item = next(p for p in data if p["session"]["id"] == str(sess_id))
    assert "cement" in prompt_item["prompt_message"].lower()
    assert "Would you like to attend?" in prompt_item["prompt_message"]
    assert prompt_item["current_decision"] is None

    # Now attendee clicks Yes / ATTENDING
    client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING"},
    )

    # Re-query recommendations -> current_decision reflects ATTENDING
    res2 = client.get(
        "/converge-api/v1/agenda/recommendations/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    prompt_item2 = next(p for p in res2.json() if p["session"]["id"] == str(sess_id))
    assert prompt_item2["current_decision"] == "ATTENDING"


def test_bookmark_vs_intent_independence(client, sync_engine):
    """Bookmarking a session does not imply attendance intent and vice-versa."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine)

    # 1. Bookmark session
    res_bm = client.post(
        f"/converge-api/v1/agenda/bookmarks/{sess_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_bm.status_code == 201

    # Verify no intent decision exists
    with SASession(sync_engine) as session:
        intent = session.scalar(
            select(SessionIntentDecision).where(
                SessionIntentDecision.user_id == user.id,
                SessionIntentDecision.session_id == sess_id,
            )
        )
        assert intent is None


# =============================================================================
# 3. Representative Dialogue Grounding & Phrasing (Workspace 4 & 5)
# =============================================================================


def test_representative_dialogue_mutual_attendance():
    """When both attendees opted into the same session, dialogue reflects mutual attendance."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps Lead", company_name="TechNova")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")

    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="AI Engineer", company_name="Sofueled")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")

    # Turn 0: Initiator Agent speaking
    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["multi-agent"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["multi-agent"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-0",
        initiator_attending_sessions=["Autonomous Multi-Agent Networks"],
        target_attending_sessions=["Autonomous Multi-Agent Networks"],
    )
    assert "mutual interest in attending 'Autonomous Multi-Agent Networks'" in turn0.content

    # Turn 1: Target Agent speaking
    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["multi-agent"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["multi-agent"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-1",
        initiator_attending_sessions=["Autonomous Multi-Agent Networks"],
        target_attending_sessions=["Autonomous Multi-Agent Networks"],
    )
    assert "Looking forward to 'Autonomous Multi-Agent Networks' as well!" in turn1.content

    # Turn 2: Proposal
    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["multi-agent"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["multi-agent"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-2",
        initiator_attending_sessions=["Autonomous Multi-Agent Networks"],
        target_attending_sessions=["Autonomous Multi-Agent Networks"],
    )
    assert "Since both attendees are planning to attend 'Autonomous Multi-Agent Networks'" in turn2.content


def test_representative_dialogue_one_sided_attendance():
    """When only initiator opted in, representative discloses intent and inquires without presuming."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps Lead", company_name="TechNova")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")

    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="AI Engineer", company_name="Sofueled")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")

    # Turn 0: Initiator Agent speaking
    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["multi-agent"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["multi-agent"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-0",
        initiator_attending_sessions=["Autonomous Multi-Agent Networks"],
        target_attending_sessions=[],
    )
    assert "Sanjana Mahajan has decided to attend 'Autonomous Multi-Agent Networks' on the conference agenda. Has Maahi Sharma considered attending that session?" in turn0.content

    # Turn 1: Target Agent speaking
    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["multi-agent"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["multi-agent"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-1",
        initiator_attending_sessions=["Autonomous Multi-Agent Networks"],
        target_attending_sessions=[],
    )
    assert "Maahi Sharma has not finalized attendance for 'Autonomous Multi-Agent Networks' yet, but is keeping an eye on it." in turn1.content


def test_list_my_session_intent_decisions(client, sync_engine):
    """GET /agenda/intent/me returns all recorded intent decisions for the caller."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id1 = create_conference_and_session(sync_engine, title="Keynote: Distributed AI")
    _, sess_id2 = create_conference_and_session(sync_engine, title="Workshop: High Performance Cement")

    # Record two decisions
    client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id1}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING"},
    )
    client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id2}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "DECLINED"},
    )

    res = client.get(
        "/converge-api/v1/agenda/intent/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    decisions = {i["session_id"]: i["decision"] for i in items}
    assert decisions[str(sess_id1)] == "ATTENDING"
    assert decisions[str(sess_id2)] == "DECLINED"


def test_recommendation_discovery_matches_hobby(client, sync_engine):
    """Session recommendation matches attendee hobbies."""
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine, title="Morning Chess & Strategy Tournament")

    # Add hobby "chess"
    with SASession(sync_engine) as session:
        session.add(ParticipantHobby(user_id=user.id, hobby_name="chess"))
        session.commit()

    res = client.get(
        "/converge-api/v1/agenda/recommendations/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    matched = [p for p in res.json() if p["session"]["id"] == str(sess_id)]
    assert len(matched) == 1
    assert "chess" in matched[0]["prompt_message"].lower()


def test_unauthenticated_request_rejected(client, sync_engine):
    """Unauthenticated requests to intent endpoints are rejected with 401."""
    _, sess_id = create_conference_and_session(sync_engine)

    res1 = client.get("/converge-api/v1/agenda/recommendations/me")
    assert res1.status_code == 401

    res2 = client.get("/converge-api/v1/agenda/intent/me")
    assert res2.status_code == 401

    res3 = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        json={"decision": "ATTENDING"},
    )
    assert res3.status_code == 401


def test_representative_dialogue_mood_adaptation_with_attendance():
    """Turn 2 collaboration proposal adapts tone according to informal mood when attending shared session."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    # Low-key mood
    turn2_low_key = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["cement"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["cement"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-2-lk",
        initiator_mood="Prefer low-key interaction",
        initiator_attending_sessions=["Cement Innovations"],
        target_attending_sessions=["Cement Innovations"],
    )
    assert "appreciates low-key interaction" in turn2_low_key.content
    assert "brief asynchronous exchange or comparing notes" in turn2_low_key.content

    # Casual mood
    turn2_casual = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["cement"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["cement"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-turn-2-cas",
        initiator_mood="Open to casual conversation",
        initiator_attending_sessions=["Cement Innovations"],
        target_attending_sessions=["Cement Innovations"],
    )
    assert "grabbing coffee or catching up briefly" in turn2_casual.content


# =============================================================================
# 4. Comprehensive Decision Matrix Scenarios 1-10 (AC-WS10)
# =============================================================================


def test_decision_matrix_scenario_1_mutual_attending():
    """Scenario 1: Both attendees explicitly selected ATTENDING for the same active session."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")

    sess_title = "Autonomous Multi-Agent Networks"

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["agent-networks"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["agent-networks"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s1-t0",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[sess_title],
    )
    assert f"mutual interest in attending '{sess_title}' on the conference agenda" in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["agent-networks"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["agent-networks"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s1-t1",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[sess_title],
    )
    assert f"Looking forward to '{sess_title}' as well!" in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["agent-networks"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["agent-networks"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s1-t2",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[sess_title],
    )
    assert f"Since both attendees are planning to attend '{sess_title}'" in turn2.content


def test_decision_matrix_scenario_2_only_initiator_attending():
    """Scenario 2: Only the initiator selected ATTENDING; target has no decision."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Cloud Native Scaling"

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["cloud"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["cloud"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s2-t0",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
    )
    assert f"Alice Initiator has decided to attend '{sess_title}' on the conference agenda. Has Bob Target considered attending that session?" in turn0.content
    assert "mutual interest in attending" not in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["cloud"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["cloud"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s2-t1",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
    )
    assert f"Bob Target has not finalized attendance for '{sess_title}' yet, but is keeping an eye on it." in turn1.content
    assert "Looking forward to" not in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["cloud"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["cloud"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s2-t2",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
    )
    assert "Since both attendees are planning to attend" not in turn2.content
    assert "brief 10-minute touchpoint" in turn2.content


def test_decision_matrix_scenario_3_only_target_attending():
    """Scenario 3: Only the target selected ATTENDING."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Distributed Storage"

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["storage"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["storage"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s3-t0",
        initiator_attending_sessions=[],
        target_attending_sessions=[sess_title],
    )
    # Turn 0 does not claim initiator is attending or mutual attendance
    assert "Alice Initiator has decided to attend" not in turn0.content
    assert "mutual interest in attending" not in turn0.content
    assert "We noticed mutual interest in storage" in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["storage"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["storage"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s3-t1",
        initiator_attending_sessions=[],
        target_attending_sessions=[sess_title],
    )
    # Turn 1 states target decided to attend and inquires
    assert f"Bob Target has decided to attend '{sess_title}' on the conference agenda. Has Alice Initiator considered attending that session?" in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["storage"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["storage"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s3-t2",
        initiator_attending_sessions=[],
        target_attending_sessions=[sess_title],
    )
    assert "Since both attendees are planning to attend" not in turn2.content


def test_decision_matrix_scenario_4_initiator_attending_target_undecided():
    """Scenario 4: Initiator is ATTENDING; target is UNDECIDED."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Observability Systems"

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["observability"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["observability"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s4-t0",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "UNDECIDED"},
    )
    assert f"Alice Initiator has decided to attend '{sess_title}' on the conference agenda. Has Bob Target considered attending that session?" in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["observability"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["observability"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s4-t1",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "UNDECIDED"},
    )
    assert f"Bob Target has not finalized attendance for '{sess_title}' yet, but is keeping an eye on it." in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["observability"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["observability"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s4-t2",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "UNDECIDED"},
    )
    assert "Since both attendees are planning to attend" not in turn2.content


def test_decision_matrix_scenario_5_initiator_attending_target_declined():
    """Scenario 5: Initiator is ATTENDING; target is DECLINED."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Advanced Kubernetes"

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["k8s"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["k8s"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s5-t0",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "DECLINED"},
    )
    assert f"Alice Initiator has decided to attend '{sess_title}' on the conference agenda." in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["k8s"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["k8s"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s5-t1",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "DECLINED"},
    )
    # Target representative honestly states declined decision
    assert f"Bob Target has declined attending '{sess_title}' due to other priorities" in turn1.content
    assert "Looking forward to" not in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["k8s"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["k8s"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s5-t2",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "DECLINED"},
    )
    assert "Since both attendees are planning to attend" not in turn2.content


def test_decision_matrix_scenario_6_neither_has_explicit_decision_with_bookmarks():
    """Scenario 6: Neither attendee has an explicit attendance decision; both have bookmarked sessions."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Keynote: Future of AI"

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[sess_title],
        target=u2,
        target_profile=p2,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[sess_title],
        idempotency_key="dm-s6-t0",
        initiator_attending_sessions=[],
        target_attending_sessions=[],
    )
    # Strictly described as bookmarked on agenda, NOT mutual attendance
    assert f"We noticed we both have '{sess_title}' bookmarked on our agenda." in turn0.content
    assert "mutual interest in attending" not in turn0.content
    assert "planning to attend" not in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[sess_title],
        target=u2,
        target_profile=p2,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[sess_title],
        idempotency_key="dm-s6-t1",
        initiator_attending_sessions=[],
        target_attending_sessions=[],
    )
    assert f"I noticed '{sess_title}' on the schedule as well." in turn1.content
    assert "Looking forward to" not in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[sess_title],
        target=u2,
        target_profile=p2,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[sess_title],
        idempotency_key="dm-s6-t2",
        initiator_attending_sessions=[],
        target_attending_sessions=[],
    )
    assert "Since both attendees are planning to attend" not in turn2.content


def test_decision_matrix_scenario_7_undecided_to_attending_transition():
    """Scenario 7: Attendee changes from UNDECIDED to ATTENDING.

    Prior turns are preserved, subsequent turn generation reflects mutual attendance.
    """
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Edge Computing Forum"

    # Step A: Initially Target is UNDECIDED
    turn0_initial = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["edge"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["edge"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s7-t0",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "UNDECIDED"},
    )
    assert "Has Bob Target considered attending that session?" in turn0_initial.content

    turn1_initial = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["edge"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["edge"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s7-t1",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "UNDECIDED"},
    )
    assert "has not finalized attendance" in turn1_initial.content

    # Step B: Target updates decision to ATTENDING
    # Turn 2 is now generated with both in ATTENDING state
    turn2_after_update = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["edge"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["edge"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s7-t2",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[sess_title],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "ATTENDING"},
    )
    # Historical turn 0 & 1 remain untouched, but turn 2 now respects the new decision
    assert f"Since both attendees are planning to attend '{sess_title}'" in turn2_after_update.content


def test_decision_matrix_scenario_8_attending_to_declined_transition():
    """Scenario 8: Attendee changes from ATTENDING to DECLINED.

    Subsequent generated messages cease claiming mutual attendance.
    """
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    sess_title = "Robotics & Automation"

    # Step A: Initially both ATTENDING
    turn0_initial = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["robotics"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["robotics"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s8-t0",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[sess_title],
    )
    assert f"mutual interest in attending '{sess_title}'" in turn0_initial.content

    # Step B: Target changes to DECLINED
    turn2_after_decline = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["robotics"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["robotics"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s8-t2",
        initiator_attending_sessions=[sess_title],
        target_attending_sessions=[],
        initiator_session_decisions={sess_title: "ATTENDING"},
        target_session_decisions={sess_title: "DECLINED"},
    )
    # Subsequent turn 2 MUST NOT claim mutual attendance
    assert "Since both attendees are planning to attend" not in turn2_after_decline.content
    assert "brief 10-minute touchpoint" in turn2_after_decline.content


def test_decision_matrix_scenario_9_cancelled_session_rejected_from_dialogue(client, sync_engine):
    """Scenario 9: A session is cancelled after an attendance decision was saved.

    Cancelled sessions are filtered out and cannot be represented as valid upcoming plans.
    """
    user, _, token = create_test_user_and_session(sync_engine)
    _, sess_id = create_conference_and_session(sync_engine, title="Pre-Cancellation Keynote", is_cancelled=False)

    # Save attendance intent
    res = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING", "source": "REPRESENTATIVE_PROMPT"},
    )
    assert res.status_code == 200

    # Cancel the session in the database
    with SASession(sync_engine) as session:
        sess = session.get(Session, sess_id)
        sess.is_cancelled = True
        session.commit()

    # Querying recommendations excludes cancelled session
    rec_res = client.get(
        "/converge-api/v1/agenda/recommendations/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rec_res.status_code == 200
    for prompt in rec_res.json():
        assert prompt["session_id"] != str(sess_id)

    # Submitting intent on cancelled session returns 400
    res_retry = client.post(
        f"/converge-api/v1/agenda/sessions/{sess_id}/intent",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "ATTENDING", "source": "REPRESENTATIVE_PROMPT"},
    )
    assert res_retry.status_code == 400
    assert "cancelled" in res_retry.json()["detail"].lower()


def test_decision_matrix_scenario_10_no_relevant_session_shared():
    """Scenario 10: No relevant session is shared by the attendees."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="DevOps Lead", company_name="TechCorp")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="AI Researcher", company_name="DataLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Cybersecurity"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Cybersecurity"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s10-t0",
        initiator_attending_sessions=[],
        target_attending_sessions=[],
    )
    assert "We noticed mutual interest in Cybersecurity and would love to exchange perspectives" in turn0.content
    assert "attending" not in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Cybersecurity"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Cybersecurity"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s10-t1",
        initiator_attending_sessions=[],
        target_attending_sessions=[],
    )
    assert "currently focusing on Cybersecurity" in turn1.content
    assert "Looking forward to" not in turn1.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Cybersecurity"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Cybersecurity"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="dm-s10-t2",
        initiator_attending_sessions=[],
        target_attending_sessions=[],
    )
    assert "Since both attendees are planning to attend" not in turn2.content
    assert "explore potential collaboration on Cybersecurity" in turn2.content


# =============================================================================
# 5. Mood Variation & Regression Tests (AC-WS10 Section 4)
# =============================================================================


def test_mood_conference_focused_conversational_style():
    """Verify Conference-focused mood guides professional focus style without emotional claims."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps", company_name="Sofueled")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="Engineer", company_name="Tech")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["AI"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["AI"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-cf-t0",
        initiator_mood="Conference-focused",
    )
    assert "noted their current focus as 'Conference-focused'." in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["AI"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["AI"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-cf-t1",
        target_mood="Conference-focused",
    )
    assert "current focus is 'Conference-focused'" in turn1.content


def test_mood_ready_to_network_conversational_style():
    """Verify Ready to network mood weaves proactive networking phrasing into turns."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps", company_name="Sofueled")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="Engineer", company_name="Tech")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Scaling"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Scaling"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-rn-t0",
        initiator_mood="Ready to network",
    )
    assert "noted their current focus as 'Ready to network'." in turn0.content

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Scaling"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Scaling"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-rn-t2",
        initiator_mood="Ready to network",
    )
    assert "is ready to network and would welcome a brief 10-minute conversation" in turn2.content


def test_mood_prefer_low_key_conversational_style():
    """Verify Prefer low-key interaction guides asynchronous and low-pressure proposals."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps", company_name="Sofueled")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="Engineer", company_name="Tech")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Telemetry"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Telemetry"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-lk-t2",
        initiator_mood="Prefer low-key interaction",
    )
    assert "appreciates low-key interaction" in turn2.content
    assert "brief asynchronous exchange or comparing notes" in turn2.content

    turn3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=3,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Telemetry"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Telemetry"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-lk-t3",
        target_mood="Prefer low-key interaction",
    )
    assert "That could be an option" in turn3.content
    assert "follow up asynchronously" in turn3.content


def test_mood_open_to_informal_break_conversational_style():
    """Verify Open to discussing an informal break or meetup weaves casual coffee proposal."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps", company_name="Sofueled")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="Engineer", company_name="Tech")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)

    turn2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Architecture"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Architecture"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-ib-t2",
        initiator_mood="Open to discussing an informal break or meetup",
    )
    assert "grabbing a coffee or catching up informally between conference sessions" in turn2.content


def test_mood_expired_and_missing_strictly_omits_mood_claims():
    """Verify expired (>24h TTL) and missing (None) moods strictly omit mood phrasing."""
    now = datetime.now(timezone.utc)
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps", company_name="Sofueled")
    # Expired mood (updated 25 hours ago)
    p1 = ParticipantProfile(
        user_id=u1.id,
        intent=ParticipationIntent.NETWORKING,
        current_mood="Conference-focused",
        mood_updated_at=now - timedelta(hours=25),
    )
    assert p1.active_mood is None

    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="Engineer", company_name="Tech")
    # Missing mood
    p2 = ParticipantProfile(
        user_id=u2.id,
        intent=ParticipationIntent.NETWORKING,
        current_mood=None,
        mood_updated_at=None,
    )
    assert p2.active_mood is None

    turn0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Linux"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Linux"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-exp-t0",
    )
    assert "noted their current focus as" not in turn0.content

    turn1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Linux"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Linux"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="mood-exp-t1",
    )
    assert "current focus is" not in turn1.content


# =============================================================================
# 5b. Dialogue Quality Refinements: 3 Patterns, Mixed Moods & Factual Grounding (AC-WS10)
# =============================================================================


def test_dialogue_refinement_conference_focused_complete_exchange():
    """Verify Conference-focused mood prioritizes session and topics, avoiding coffee and generic team questions."""
    u1 = User(id=uuid.uuid4(), full_name="Sanjana Mahajan", username="sanjana", job_title="DevOps Lead", company_name="TechNova")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")
    u2 = User(id=uuid.uuid4(), full_name="Maahi Sharma", username="maahi", job_title="AI Engineer", company_name="Sofueled")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING, current_mood="Conference-focused")
    sess = "Autonomous Multi-Agent Networks"

    # Turn 0 (Initiator): Leads with verified shared session and topics
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Agent Consensus"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Agent Consensus"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-cf-turn-0",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Conference-focused",
    )
    assert f"mutual interest in attending '{sess}'" in t0.content
    assert "'Conference-focused'" in t0.content

    # Turn 1 (Target): Responds to session and topic, NO generic team questions
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=1,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Agent Consensus"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Agent Consensus"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-cf-turn-1",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        target_mood="Conference-focused",
    )
    assert f"Looking forward to '{sess}' as well!" in t1.content
    assert "current focus is 'Conference-focused'" in t1.content
    assert "team approaching" not in t1.content
    assert "particular aspects of Agent Consensus you are hoping to explore" in t1.content

    # Turn 2 (Initiator): Prioritizes session and topic discussion, NO coffee
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Agent Consensus"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Agent Consensus"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-cf-turn-2",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Conference-focused",
        target_mood="Conference-focused",
    )
    assert f"Since both attendees are planning to attend '{sess}'" in t2.content
    assert "discussing key takeaways or session themes on Agent Consensus" in t2.content
    assert "coffee" not in t2.content.lower()

    # Turn 3 (Target): Constructive acknowledgment without human commitment
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=3,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Agent Consensus"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Agent Consensus"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-cf-turn-3",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Conference-focused",
        target_mood="Conference-focused",
    )
    assert "That could be an option" in t3.content
    assert "can decide whether to connect or share perspectives around the session" in t3.content
    assert "We will coordinate" not in t3.content
    assert "productive plan" not in t3.content

    # Turn 4 (Initiator): Clear hand-off to human attendees
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=4,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Agent Consensus"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Agent Consensus"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-cf-turn-4",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Conference-focused",
        target_mood="Conference-focused",
    )
    assert "leave this conversation open" in t4.content
    assert "can coordinate directly" in t4.content


def test_dialogue_refinement_low_key_complete_exchange():
    """Verify Prefer low-key interaction favors comparing notes and asynchronous interaction, avoiding coffee."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="Engineer", company_name="Alpha")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="Researcher", company_name="Beta")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)
    sess = "Deep Learning Systems"

    # Turn 2: Proposes comparing notes / async exchange, strictly NO coffee
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["PyTorch"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["PyTorch"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-lk-turn-2",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Prefer low-key interaction",
        target_mood="Prefer low-key interaction",
    )
    assert "appreciates low-key interaction" in t2.content
    assert "brief asynchronous exchange or comparing notes on PyTorch" in t2.content
    assert "coffee" not in t2.content.lower()

    # Turn 3: Acknowledges thoughtfully without committing attendee
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=3,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["PyTorch"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["PyTorch"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-lk-turn-3",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Prefer low-key interaction",
        target_mood="Prefer low-key interaction",
    )
    assert "That could be an option" in t3.content
    assert "can decide whether to follow up asynchronously or compare notes directly" in t3.content


def test_dialogue_refinement_open_to_break_complete_exchange():
    """Verify Open to discussing an informal break or meetup proposes casual catchup/coffee when mutually aligned."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="Engineer", company_name="Alpha")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="Researcher", company_name="Beta")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)
    sess = "Networking Roundtable"

    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Networking"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Networking"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-ib-turn-2",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Open to discussing an informal break or meetup",
        target_mood="Open to discussing an informal break or meetup",
    )
    assert "open to grabbing coffee or catching up briefly before or after the session" in t2.content

    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=3,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Networking"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Networking"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-ib-turn-3",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Open to discussing an informal break or meetup",
        target_mood="Open to discussing an informal break or meetup",
    )
    assert "That could be an option" in t3.content
    assert "can decide whether to reach out or coordinate directly between sessions" in t3.content


def test_dialogue_refinement_mixed_moods_respects_both_preferences():
    """Verify that when attendees have different preferences, suggestion respects both without dictating."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="Engineer", company_name="Alpha")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="Researcher", company_name="Beta")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)
    sess = "AI Innovation"

    # Case 1: Attendee A is Low-Key, Attendee B is Open to informal break
    # Low-key MUST be respected: NO coffee, favor comparing notes/async!
    t2_low_key_mixed = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["AI"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["AI"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-mix-lk-t2",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Prefer low-key interaction",
        target_mood="Open to discussing an informal break or meetup",
    )
    assert "appreciates low-key interaction" in t2_low_key_mixed.content
    assert "coffee" not in t2_low_key_mixed.content.lower()

    # Case 2: Attendee A is Conference-Focused, Attendee B is Open to informal break
    # Conference-focused MUST be respected: prioritize session themes, NO coffee!
    t2_cf_mixed = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid.uuid4(),
        turn_index=2,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["AI"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["AI"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="idemp-mix-cf-t2",
        initiator_attending_sessions=[sess],
        target_attending_sessions=[sess],
        initiator_mood="Conference-focused",
        target_mood="Open to discussing an informal break or meetup",
    )
    assert "discussing key takeaways or session themes on AI" in t2_cf_mixed.content
    assert "coffee" not in t2_cf_mixed.content.lower()


# =============================================================================
# 6. End-to-End Worker Database Decision Matrix Execution (AC-WS10 Section 3)
# =============================================================================


@pytest.mark.asyncio
async def test_worker_attendance_decision_matrix_db_execution(async_db, sync_engine):
    """Verify background agent worker reads real PostgreSQL decision records at execution time.

    Tests full database lifecycle:
    1. User A is ATTENDING session S1 in DB; User B is DECLINED session S1 in DB.
    2. Worker claims and executes Turn 0 -> Alice states intent, asks Bob.
    3. Worker claims and executes Turn 1 -> Bob honestly states declined decision.
    4. Bob updates decision in DB to ATTENDING.
    5. Worker claims and executes Turn 2 -> Now detects mutual attendance from DB and reflects it.
    6. All turns persisted in core.messages with monotonic turn indexes.
    """
    now = datetime.now(timezone.utc)
    u1_id = uuid.uuid4()
    u2_id = uuid.uuid4()

    with SASession(sync_engine) as session:
        # Create users
        user_a = User(
            id=u1_id,
            username=f"worker_alice_{u1_id.hex[:6]}",
            email=f"alice_{u1_id.hex[:6]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Alice DevOps",
            company_name="CloudHQ",
            job_title="Lead Architect",
            is_active=True,
        )
        user_b = User(
            id=u2_id,
            username=f"worker_bob_{u2_id.hex[:6]}",
            email=f"bob_{u2_id.hex[:6]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Bob Data",
            company_name="DataCorp",
            job_title="Data Engineer",
            is_active=True,
        )
        session.add(user_a)
        session.add(user_b)
        session.flush()

        # Profiles
        prof_a = ParticipantProfile(
            user_id=u1_id,
            intent=ParticipationIntent.NETWORKING,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
            current_mood="Conference-focused",
            mood_updated_at=now,
        )
        prof_b = ParticipantProfile(
            user_id=u2_id,
            intent=ParticipationIntent.NETWORKING,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
            current_mood="Conference-focused",
            mood_updated_at=now,
        )
        session.add(prof_a)
        session.add(prof_b)

        # Topics
        session.add(ParticipantTopic(user_id=u1_id, topic_keyword="DistributedSystems"))
        session.add(ParticipantTopic(user_id=u2_id, topic_keyword="DistributedSystems"))

        # Conference & Session
        conf = Conference(
            title="Systems Conf 2026",
            venue_name="Convention Center",
            timezone="UTC",
            start_date=now.date(),
            end_date=(now + timedelta(days=1)).date(),
            is_active=True,
        )
        session.add(conf)
        session.flush()

        sess = Session(
            conference_id=conf.id,
            title="Distributed Systems Workshop",
            abstract="Hands-on distributed consistency architectures.",
            hall_room="Room 101",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            is_cancelled=False,
        )
        session.add(sess)
        session.flush()
        sess_id = sess.id

        # Persist Initial Decisions in DB:
        # Alice is ATTENDING
        dec_a = SessionIntentDecision(
            user_id=u1_id,
            session_id=sess_id,
            decision="ATTENDING",
            source="REPRESENTATIVE_PROMPT",
        )
        # Bob is DECLINED
        dec_b = SessionIntentDecision(
            user_id=u2_id,
            session_id=sess_id,
            decision="DECLINED",
            source="REPRESENTATIVE_PROMPT",
        )
        session.add(dec_a)
        session.add(dec_b)

        # Conversation
        conv = Conversation(
            initiator_id=u1_id,
            target_id=u2_id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.commit()
        conv_id = conv.id

    # Turn 0 Execution via Worker
    task0 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=0,
        idempotency_key="worker-e2e-turn-0",
    )
    claimed0 = await AgentTaskService.claim_next_task(db=async_db, worker_id="test-worker-1")
    assert claimed0 is not None
    await AgentTaskService.execute_task(db=async_db, task=claimed0, worker_id="test-worker-1")

    # Verify Turn 0 message in DB
    msg0_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 0)
    msg0 = (await async_db.execute(msg0_stmt)).scalar_one()
    assert "Alice DevOps has decided to attend 'Distributed Systems Workshop'" in msg0.content
    assert "Has Bob Data considered attending that session?" in msg0.content
    assert "mutual interest in attending" not in msg0.content

    # Turn 1 Execution via Worker
    task1 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=1,
        idempotency_key="worker-e2e-turn-1",
    )
    claimed1 = await AgentTaskService.claim_next_task(db=async_db, worker_id="test-worker-1")
    assert claimed1 is not None
    await AgentTaskService.execute_task(db=async_db, task=claimed1, worker_id="test-worker-1")

    # Verify Turn 1 message in DB: Bob honestly acknowledges declined decision
    msg1_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 1)
    msg1 = (await async_db.execute(msg1_stmt)).scalar_one()
    assert "Bob Data has declined attending 'Distributed Systems Workshop' due to other priorities" in msg1.content
    assert "Looking forward to" not in msg1.content

    # Bob changes his decision in PostgreSQL from DECLINED to ATTENDING
    with SASession(sync_engine) as session:
        bob_dec = session.query(SessionIntentDecision).filter_by(user_id=u2_id, session_id=sess_id).one()
        bob_dec.decision = "ATTENDING"
        session.commit()

    # Turn 2 Execution via Worker
    task2 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=2,
        idempotency_key="worker-e2e-turn-2",
    )
    claimed2 = await AgentTaskService.claim_next_task(db=async_db, worker_id="test-worker-1")
    assert claimed2 is not None
    await AgentTaskService.execute_task(db=async_db, task=claimed2, worker_id="test-worker-1")

    # Verify Turn 2 message in DB: Worker dynamically queried updated decisions and now reflects mutual attendance!
    msg2_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 2)
    msg2 = (await async_db.execute(msg2_stmt)).scalar_one()
    assert "Since both attendees are planning to attend 'Distributed Systems Workshop'" in msg2.content

    # Verify historical Turn 0 and Turn 1 messages remain completely intact (not rewritten)
    msg0_rechecked = (await async_db.execute(msg0_stmt)).scalar_one()
    assert "Has Bob Data considered attending that session?" in msg0_rechecked.content
    msg1_rechecked = (await async_db.execute(msg1_stmt)).scalar_one()
    assert "has declined attending 'Distributed Systems Workshop'" in msg1_rechecked.content


# =============================================================================
# 7. Comprehensive 36-Pair Cartesian Mood Matrix & Consent Audit (AC-WS12)
# =============================================================================


def test_full_cartesian_mood_matrix_all_36_pairs():
    """Verify complete 36-pair Cartesian product of all 5 defined moods + None in both directions (AC-WS12)."""
    u1 = User(id=uuid.uuid4(), full_name="Alice Initiator", username="alice", job_title="Tech Lead", company_name="Acme")
    p1 = ParticipantProfile(user_id=u1.id, intent=ParticipationIntent.NETWORKING)
    u2 = User(id=uuid.uuid4(), full_name="Bob Target", username="bob", job_title="Staff Researcher", company_name="BetaLab")
    p2 = ParticipantProfile(user_id=u2.id, intent=ParticipationIntent.NETWORKING)
    sess = "Next-Gen AI Systems"
    cid = uuid.uuid4()

    all_moods = [
        None,
        "Ready to network",
        "Open to casual conversation",
        "Conference-focused",
        "Open to discussing an informal break or meetup",
        "Prefer low-key interaction",
    ]

    for i, m1 in enumerate(all_moods):
        for j, m2 in enumerate(all_moods):
            pair_key = f"cart-{i}-{j}"
            # Turn 2: Initiator Virtual Representative speaks
            t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
                conversation_id=cid,
                turn_index=2,
                initiator=u1,
                initiator_profile=p1,
                initiator_topics=["AI Systems"],
                initiator_hobbies=[],
                initiator_sessions=[],
                target=u2,
                target_profile=p2,
                target_topics=["AI Systems"],
                target_hobbies=[],
                target_sessions=[],
                idempotency_key=f"t2-{pair_key}",
                initiator_attending_sessions=[sess],
                target_attending_sessions=[sess],
                initiator_mood=m1,
                target_mood=m2,
            )

            # Turn 3: Target Virtual Representative acknowledges (non-presumptuous)
            t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
                conversation_id=cid,
                turn_index=3,
                initiator=u1,
                initiator_profile=p1,
                initiator_topics=["AI Systems"],
                initiator_hobbies=[],
                initiator_sessions=[],
                target=u2,
                target_profile=p2,
                target_topics=["AI Systems"],
                target_hobbies=[],
                target_sessions=[],
                idempotency_key=f"t3-{pair_key}",
                initiator_attending_sessions=[sess],
                target_attending_sessions=[sess],
                initiator_mood=m1,
                target_mood=m2,
            )

            # Invariant: Turn 3 strictly begins with non-presumptuous acknowledgment
            assert "That could be an option. Bob Target can decide whether to" in t3.content, f"Turn 3 violated non-presumptuous standard for pair ({m1}, {m2}): {t3.content}"
            assert "That sounds like a" not in t3.content
            assert "We will coordinate" not in t3.content
            assert "We are planning to" not in t3.content

            # Hierarchy Verification:
            # 1. Low-key presence ALWAYS takes precedence
            if "Prefer low-key interaction" in (m1, m2):
                assert "coffee" not in t2.content.lower(), f"Low-key violated by coffee for pair ({m1}, {m2})"
                assert "brief asynchronous exchange or comparing notes" in t2.content
                assert "follow up asynchronously or compare notes directly" in t3.content
                if m1 == "Prefer low-key interaction":
                    assert "Alice Initiator appreciates low-key interaction." in t2.content
                else:
                    assert "given Bob Target's preference for low-key interaction, would they be open" in t2.content

            # 2. Conference-focused presence (without low-key) ALWAYS takes precedence over casual/networking
            elif "Conference-focused" in (m1, m2):
                assert "coffee" not in t2.content.lower(), f"Conference-focused violated by coffee for pair ({m1}, {m2})"
                assert "discussing key takeaways or session themes on AI Systems" in t2.content
                assert "connect or share perspectives around the session" in t3.content

            # 3. Casual / Break meetup presence (without low-key, without conference-focused)
            elif any(m in ("Open to casual conversation", "Open to discussing an informal break or meetup") for m in (m1, m2)):
                assert "grabbing coffee or catching up briefly before or after the session" in t2.content
                assert "reach out or coordinate directly between sessions" in t3.content

            # 4. Ready to network presence (without low-key, conference-focused, casual)
            elif "Ready to network" in (m1, m2):
                assert "exchange ideas on AI Systems" in t2.content
                assert "reach out or coordinate directly between sessions" in t3.content
                if m1 == "Ready to network":
                    assert "Alice Initiator is eager to network" in t2.content
                else:
                    assert "noting Bob Target's interest in networking, Alice Initiator would welcome" in t2.content

            # 5. Missing / Expired moods on both (None, None)
            else:
                assert "explore collaboration on AI Systems" in t2.content
                assert "reach out or coordinate directly between sessions" in t3.content


# =============================================================================
# 8. Representative Sequence Invariants & Maximum 5 Turns (AC-WS12)
# =============================================================================


@pytest.mark.asyncio
async def test_representative_sequence_five_turn_maximum_guard(async_db, sync_engine):
    """Enforce invariant: Exactly 5 representative turns maximum; worker skips turn_index >= 5; API rejects turn 5."""
    now = datetime.now(timezone.utc)
    u1_id = uuid.uuid4()
    u2_id = uuid.uuid4()

    with SASession(sync_engine) as session:
        user_a = User(
            id=u1_id,
            username=f"seq_a_{u1_id.hex[:6]}",
            email=f"seq_a_{u1_id.hex[:6]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Seq User A",
            is_active=True,
        )
        user_b = User(
            id=u2_id,
            username=f"seq_b_{u2_id.hex[:6]}",
            email=f"seq_b_{u2_id.hex[:6]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Seq User B",
            is_active=True,
        )
        session.add(user_a)
        session.add(user_b)
        session.flush()

        session.add(ParticipantProfile(user_id=u1_id, intent=ParticipationIntent.NETWORKING))
        session.add(ParticipantProfile(user_id=u2_id, intent=ParticipationIntent.NETWORKING))

        conv = Conversation(initiator_id=u1_id, target_id=u2_id, status=ConversationStatus.ACTIVE)
        session.add(conv)
        session.commit()
        conv_id = conv.id

    # 1. Execute 5 representative turns (0 through 4)
    for turn in range(5):
        task = await AgentTaskService.create_agent_dialogue_task(
            db=async_db,
            conversation_id=conv_id,
            initiator_id=u1_id,
            target_id=u2_id,
            turn_index=turn,
            idempotency_key=f"seq-turn-{turn}",
        )
        claimed = await AgentTaskService.claim_next_task(db=async_db, worker_id="test-worker-seq")
        assert claimed is not None
        await AgentTaskService.execute_task(db=async_db, task=claimed, worker_id="test-worker-seq")

    # Verify exactly 5 messages in DB
    msg_stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.turn_index)
    messages = (await async_db.execute(msg_stmt)).scalars().all()
    assert len(messages) == 5
    for idx, msg in enumerate(messages):
        assert msg.turn_index == idx
        assert msg.sender_type == MessageSenderType.AGENT

    # Alternating identities:
    assert messages[0].sender_id == u1_id  # Turn 0: Initiator Agent
    assert messages[1].sender_id == u2_id  # Turn 1: Target Agent
    assert messages[2].sender_id == u1_id  # Turn 2: Initiator Agent
    assert messages[3].sender_id == u2_id  # Turn 3: Target Agent
    assert messages[4].sender_id == u1_id  # Turn 4: Initiator Agent

    # 2. Triggering agent dialogue via API when 5 turns already exist MUST raise HTTP 409
    with pytest.raises(HTTPException) as exc_info:
        await ConversationService.trigger_agent_dialogue(
            db=async_db,
            conversation_id=conv_id,
            current_user_id=u1_id,
            client_ip="127.0.0.1",
        )
    assert exc_info.value.status_code == 409
    assert "Representative exchange complete" in exc_info.value.detail

    # 3. Attempting to append an AGENT message when 5 turns exist MUST raise HTTP 409
    with pytest.raises(HTTPException) as exc_append:
        await ConversationService.append_message(
            db=async_db,
            conversation_id=conv_id,
            sender_id=u2_id,
            content="Attempted 6th agent turn",
            client_ip="127.0.0.1",
            sender_type=MessageSenderType.AGENT,
        )
    assert exc_append.value.status_code == 409
    assert "Only human attendee messages are permitted" in exc_append.value.detail

    # 4. Attempting to execute an agent task for turn_index=5 MUST be skipped by worker with 0 new messages
    task_6 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=5,
        idempotency_key="seq-turn-5-extra",
    )
    claimed_6 = await AgentTaskService.claim_next_task(db=async_db, worker_id="test-worker-seq")
    assert claimed_6 is not None
    res = await AgentTaskService.execute_task(db=async_db, task=claimed_6, worker_id="test-worker-seq")
    assert res["action_type"] == "SKIPPED_REPRESENTATIVE_EXCHANGE_COMPLETE"

    # Messages count remains strictly 5
    messages_after = (await async_db.execute(msg_stmt)).scalars().all()
    assert len(messages_after) == 5

    # 5. Human attendees CAN send messages seamlessly (Turns 5 and 6)
    human_msg_1, _ = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv_id,
        sender_id=u1_id,
        content="Hi Bob! Let's connect after the session.",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert human_msg_1.turn_index == 5
    assert human_msg_1.sender_type == MessageSenderTypeEnum.PARTICIPANT

    human_msg_2, _ = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv_id,
        sender_id=u2_id,
        content="Sounds great Alice, see you there!",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert human_msg_2.turn_index == 6
    assert human_msg_2.sender_type == MessageSenderTypeEnum.PARTICIPANT


# =============================================================================
# 9. Attendance Decision Freshness & Dynamic Transition Tests (AC-WS12)
# =============================================================================


@pytest.mark.asyncio
async def test_attendance_decision_freshness_lifecycle(async_db, sync_engine):
    """Verify worker queries live database at turn execution time: ATTENDING -> DECLINED -> UNDECIDED -> ATTENDING -> Cancelled."""
    now = datetime.now(timezone.utc)
    u1_id = uuid.uuid4()
    u2_id = uuid.uuid4()

    with SASession(sync_engine) as session:
        user_a = User(
            id=u1_id,
            username=f"fresh_a_{u1_id.hex[:6]}",
            email=f"fresh_a_{u1_id.hex[:6]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Fresh Alice",
            is_active=True,
        )
        user_b = User(
            id=u2_id,
            username=f"fresh_b_{u2_id.hex[:6]}",
            email=f"fresh_b_{u2_id.hex[:6]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Fresh Bob",
            is_active=True,
        )
        session.add(user_a)
        session.add(user_b)
        session.flush()

        session.add(ParticipantProfile(user_id=u1_id, intent=ParticipationIntent.NETWORKING))
        session.add(ParticipantProfile(user_id=u2_id, intent=ParticipationIntent.NETWORKING))
        session.add(ParticipantTopic(user_id=u1_id, topic_keyword="Rust"))
        session.add(ParticipantTopic(user_id=u2_id, topic_keyword="Rust"))

        conf = Conference(
            title="Rust Conf 2026",
            venue_name="Hall A",
            timezone="UTC",
            start_date=now.date(),
            end_date=(now + timedelta(days=1)).date(),
            is_active=True,
        )
        session.add(conf)
        session.flush()

        sess = Session(
            conference_id=conf.id,
            title="Rust Systems Architecture",
            abstract="Async runtime internals in Rust.",
            hall_room="Room 404",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            is_cancelled=False,
        )
        session.add(sess)
        session.flush()
        sess_id = sess.id

        # Initial state: Alice is ATTENDING, Bob is ATTENDING
        session.add(SessionIntentDecision(user_id=u1_id, session_id=sess_id, decision="ATTENDING"))
        session.add(SessionIntentDecision(user_id=u2_id, session_id=sess_id, decision="ATTENDING"))

        conv = Conversation(initiator_id=u1_id, target_id=u2_id, status=ConversationStatus.ACTIVE)
        session.add(conv)
        session.commit()
        conv_id = conv.id

    # Turn 0: Worker executes -> Both attending in DB, so states mutual attendance
    await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=0,
        idempotency_key="fresh-turn-0",
    )
    c0 = await AgentTaskService.claim_next_task(db=async_db, worker_id="fresh-worker")
    await AgentTaskService.execute_task(db=async_db, task=c0, worker_id="fresh-worker")

    msg0_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 0)
    msg0 = (await async_db.execute(msg0_stmt)).scalar_one()
    assert "mutual interest in attending 'Rust Systems Architecture'" in msg0.content

    # State Transition 1: Bob changes decision in PostgreSQL to DECLINED
    with SASession(sync_engine) as session:
        b_dec = session.query(SessionIntentDecision).filter_by(user_id=u2_id, session_id=sess_id).one()
        b_dec.decision = "DECLINED"
        session.commit()

    # Turn 1: Worker executes -> Bob's representative queries live DB and honestly states declined
    await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=1,
        idempotency_key="fresh-turn-1",
    )
    c1 = await AgentTaskService.claim_next_task(db=async_db, worker_id="fresh-worker")
    await AgentTaskService.execute_task(db=async_db, task=c1, worker_id="fresh-worker")

    msg1_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 1)
    msg1 = (await async_db.execute(msg1_stmt)).scalar_one()
    assert "Fresh Bob has declined attending 'Rust Systems Architecture'" in msg1.content

    # Historical Turn 0 message remains strictly intact
    msg0_rechecked = (await async_db.execute(msg0_stmt)).scalar_one()
    assert "mutual interest in attending 'Rust Systems Architecture'" in msg0_rechecked.content

    # State Transition 2: Bob changes decision in PostgreSQL from DECLINED to UNDECIDED
    with SASession(sync_engine) as session:
        b_dec = session.query(SessionIntentDecision).filter_by(user_id=u2_id, session_id=sess_id).one()
        b_dec.decision = "UNDECIDED"
        session.commit()

    # Turn 2: Worker executes -> Bob is undecided, so Alice's representative CANNOT claim mutual attendance
    await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=2,
        idempotency_key="fresh-turn-2",
    )
    c2 = await AgentTaskService.claim_next_task(db=async_db, worker_id="fresh-worker")
    await AgentTaskService.execute_task(db=async_db, task=c2, worker_id="fresh-worker")

    msg2_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 2)
    msg2 = (await async_db.execute(msg2_stmt)).scalar_one()
    assert "Since both attendees are planning to attend" not in msg2.content

    # State Transition 3: Session is CANCELLED in DB
    with SASession(sync_engine) as session:
        s_obj = session.query(Session).filter_by(id=sess_id).one()
        s_obj.is_cancelled = True
        session.commit()

    # Turn 3: Worker executes -> Cancelled session is excluded from active consideration
    await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=3,
        idempotency_key="fresh-turn-3",
    )
    c3 = await AgentTaskService.claim_next_task(db=async_db, worker_id="fresh-worker")
    await AgentTaskService.execute_task(db=async_db, task=c3, worker_id="fresh-worker")

    msg3_stmt = select(Message).where(Message.conversation_id == conv_id, Message.turn_index == 3)
    msg3 = (await async_db.execute(msg3_stmt)).scalar_one()
    assert "Rust Systems Architecture" not in msg3.content



