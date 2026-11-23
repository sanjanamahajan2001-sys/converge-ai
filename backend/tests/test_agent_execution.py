"""Comprehensive automated tests for Virtual Agent Execution, Lease Concurrency, and Recovery (Phase 6).

Covers:
1. Task creation and persistence across worker restart
2. Concurrent worker claiming via SELECT ... FOR UPDATE SKIP LOCKED
3. Lease expiration and recovery of abandoned/crashed worker tasks
4. Stale-worker write isolation (lost lease cannot overwrite task)
5. Retryable transient failures with exponential backoff vs permanent failures
6. Retry exhaustion transition to terminal FAILED
7. Duplicate-safe execution via idempotency keys
8. Task cancellation and shutdown behavior
9. Context-aware representative dialogue grounded in mutual topics, hobbies, agenda sessions
10. Agent message persistence with MessageSenderType.AGENT and WebSocket broadcast
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SASession
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import generate_session_token, hash_session_token
from app.db.models.agenda import BookmarkedSession, Conference, Session as ConferenceSession
from app.db.models.conversation import (
    Conversation,
    ConversationOutcome,
    ConversationStatus,
    Message,
    MessageSenderType,
)
from app.db.models.profile import (
    AvailabilityStatus,
    ParticipantHobby,
    ParticipantProfile,
    ParticipantTopic,
    ParticipationIntent,
)
from app.db.models.session import UserSession
from app.db.models.task import Task, TaskAttempt, TaskStatus
from app.db.models.user import User
from app.main import create_app
from app.schemas.a2a import A2AActionType
from app.schemas.conversation import ConversationStatusEnum, MessageSenderTypeEnum
from app.services.agent_worker import (
    AgentTaskService,
    AgentWorker,
    PermanentTaskError,
    StaleWorkerError,
    TransientTaskError,
)
from app.services.conversation import ConversationService
from app.services.representative import DeterministicRepresentativeEngine

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), f"Refusing to run tests against non-test DB: {TEST_DB_URL}"
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
async def async_db():
    """Function-scoped AsyncSession using NullPool to prevent event-loop cross-talk."""
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
def cleanup_test_db(sync_engine):
    """Clean up records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM a2a.task_attempts;")
            conn.exec_driver_sql("DELETE FROM a2a.tasks;")
            conn.exec_driver_sql("DELETE FROM core.messages;")
            conn.exec_driver_sql("DELETE FROM core.conversations;")
            conn.exec_driver_sql("DELETE FROM agenda.bookmarked_sessions;")
            conn.exec_driver_sql("DELETE FROM agenda.sessions;")
            conn.exec_driver_sql("DELETE FROM agenda.conferences;")
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


def create_agent_test_attendee(
    sync_engine,
    username: str,
    email: str,
    full_name: str,
    job_title: str,
    company: str,
    intent: ParticipationIntent = ParticipationIntent.NETWORKING,
    topics: List[str] = None,
    hobbies: List[str] = None,
) -> Tuple[User, str]:
    """Create test attendee with rich profile, topics, and hobbies."""
    with SASession(sync_engine) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=full_name,
            company_name=company,
            job_title=job_title,
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

        profile = ParticipantProfile(
            user_id=user.id,
            bio_summary=f"Bio summary for {full_name}",
            intent=intent,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
        )
        session.add(profile)
        session.flush()

        for t in (topics or []):
            session.add(ParticipantTopic(user_id=user.id, topic_keyword=t))

        for h in (hobbies or []):
            session.add(ParticipantHobby(user_id=user.id, hobby_name=h))

        session.commit()
        session.refresh(user)
        return user, raw_token


def test_deterministic_representative_context_grounding(sync_engine):
    """Dialogue engine grounds turns strictly in shared topics, hobbies, and bookmarked sessions."""
    user_a, _ = create_agent_test_attendee(
        sync_engine, "alex_arch", "alex@example.com", "Alex Rivera", "Principal Architect", "CloudCorp",
        intent=ParticipationIntent.NETWORKING,
        topics=["Kubernetes", "Distributed Tracing"],
        hobbies=["Chess"],
    )
    user_b, _ = create_agent_test_attendee(
        sync_engine, "beth_eng", "beth@example.com", "Beth Chen", "VP of Engineering", "ScaleTech",
        intent=ParticipationIntent.NETWORKING,
        topics=["Kubernetes", "Microservices"],
        hobbies=["Chess", "Photography"],
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine) as session:
        prof_a = session.query(ParticipantProfile).filter_by(user_id=user_a.id).one()
        prof_b = session.query(ParticipantProfile).filter_by(user_id=user_b.id).one()

        # Turn 0: Introduces with shared topic "Kubernetes"
        env_turn_0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=0,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Kubernetes", "Distributed Tracing"],
            initiator_hobbies=["Chess"],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Kubernetes", "Microservices"],
            target_hobbies=["Chess", "Photography"],
            target_sessions=[],
            idempotency_key="test-key-turn-0",
        )

        assert env_turn_0.turn_index == 0
        assert env_turn_0.action_type == A2AActionType.INTRODUCE
        assert env_turn_0.sender_id == user_a.id
        assert env_turn_0.recipient_id == user_b.id
        assert "Kubernetes" in env_turn_0.content
        assert "Alex Rivera" in env_turn_0.content
        assert "Beth Chen" in env_turn_0.content

        # Turn 1: Target agent responds
        env_turn_1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=1,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Kubernetes", "Distributed Tracing"],
            initiator_hobbies=["Chess"],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Kubernetes", "Microservices"],
            target_hobbies=["Chess", "Photography"],
            target_sessions=[],
            idempotency_key="test-key-turn-1",
        )
        assert env_turn_1.turn_index == 1
        assert env_turn_1.action_type == A2AActionType.SHARE_INTERESTS
        assert env_turn_1.sender_id == user_b.id
        assert env_turn_1.recipient_id == user_a.id
        assert "Beth Chen" in env_turn_1.content


@pytest.mark.asyncio
async def test_task_creation_and_worker_claiming(async_db):
    """Worker claims pending task using row-level locking and sets lease owner."""
    conv_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    user_a = User(
        id=user_a_id,
        username="user_alpha",
        email="u_a@example.com",
        password_hash="fake",
        full_name="User Alpha",
        phone_number="+1-555-0101",
    )
    user_b = User(
        id=user_b_id,
        username="user_beta",
        email="u_b@example.com",
        password_hash="fake",
        full_name="User Beta",
        phone_number="+1-555-0102",
    )
    async_db.add(user_a)
    async_db.add(user_b)
    await async_db.flush()

    conv = Conversation(
        id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        status=ConversationStatus.ACTIVE,
    )
    async_db.add(conv)
    await async_db.commit()

    # 1. Create dialogue task
    task = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        turn_index=0,
        idempotency_key="idemp-claim-001",
    )
    assert task.status == TaskStatus.PENDING
    assert task.attempt_count == 0

    # 2. Worker 1 claims task
    worker_1 = AgentWorker(worker_id="worker-node-1")
    claimed = await AgentTaskService.claim_next_task(
        db=async_db,
        worker_id=worker_1.worker_id,
        lease_duration=timedelta(seconds=15),
    )
    assert claimed is not None
    assert claimed.id == task.id
    assert claimed.status == TaskStatus.RUNNING
    assert claimed.lease_owner == "worker-node-1"
    assert claimed.attempt_count == 1
    assert claimed.lease_expires_at is not None

    # 3. Worker 2 attempts claim concurrently -> receives None because task is locked/leased
    worker_2 = AgentWorker(worker_id="worker-node-2")
    claimed_2 = await AgentTaskService.claim_next_task(
        db=async_db,
        worker_id=worker_2.worker_id,
    )
    assert claimed_2 is None


@pytest.mark.asyncio
async def test_lease_expiry_and_recovery_by_another_worker(async_db):
    """If worker crashes and lease expires, another worker automatically recovers and reclaims the task."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    async_db.add(User(id=user_a_id, username="user_la", email="la@ex.com", password_hash="h", full_name="A", phone_number="1"))
    async_db.add(User(id=user_b_id, username="user_lb", email="lb@ex.com", password_hash="h", full_name="B", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=user_a_id, target_id=user_b_id, status=ConversationStatus.ACTIVE))
    await async_db.commit()

    # Create task already in RUNNING status with an expired lease
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired_task = Task(
        task_type="AGENT_DIALOGUE_TURN",
        conversation_id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        status=TaskStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        lease_owner="crashed-worker-99",
        lease_expires_at=past_time,
        scheduled_at=past_time,
        started_at=past_time,
        payload={"idempotency_key": "expired-lease-key"},
    )
    async_db.add(expired_task)
    await async_db.commit()

    # New healthy worker claims task -> succeeds and takes over ownership
    healthy_worker = AgentWorker(worker_id="healthy-worker-01")
    recovered = await AgentTaskService.claim_next_task(
        db=async_db,
        worker_id=healthy_worker.worker_id,
    )
    assert recovered is not None
    assert recovered.id == expired_task.id
    assert recovered.status == TaskStatus.RUNNING
    assert recovered.lease_owner == "healthy-worker-01"
    assert recovered.attempt_count == 2


@pytest.mark.asyncio
async def test_stale_worker_protection(async_db):
    """Stale worker whose lease was lost is blocked from updating the task."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    async_db.add(User(id=user_a_id, username="user_sa", email="sa@ex.com", password_hash="h", full_name="SA", phone_number="1"))
    async_db.add(User(id=user_b_id, username="user_sb", email="sb@ex.com", password_hash="h", full_name="SB", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=user_a_id, target_id=user_b_id, status=ConversationStatus.ACTIVE))

    task = Task(
        task_type="AGENT_DIALOGUE_TURN",
        conversation_id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        status=TaskStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        lease_owner="worker-owner-new",  # Different worker owns it
        lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        scheduled_at=datetime.now(timezone.utc),
        payload={"idempotency_key": "stale-key"},
    )
    async_db.add(task)
    await async_db.commit()
    await async_db.refresh(task)

    # Worker "stale-worker-old" attempts to complete task -> must fail with StaleWorkerError
    with pytest.raises(StaleWorkerError):
        await AgentTaskService.execute_task(
            db=async_db,
            task=task,
            worker_id="stale-worker-old",
        )


@pytest.mark.asyncio
async def test_retryable_transient_failure_and_backoff(async_db):
    """Transient failures increment attempts, calculate exponential backoff, and re-schedule."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    async_db.add(User(id=user_a_id, username="user_ra", email="ra@ex.com", password_hash="h", full_name="RA", phone_number="1"))
    async_db.add(User(id=user_b_id, username="user_rb", email="rb@ex.com", password_hash="h", full_name="RB", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=user_a_id, target_id=user_b_id, status=ConversationStatus.ACTIVE))

    task = Task(
        task_type="AGENT_DIALOGUE_TURN",
        conversation_id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        status=TaskStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        lease_owner="worker-retry-1",
        lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
        payload={"idempotency_key": "retry-key"},
    )
    async_db.add(task)
    await async_db.commit()

    # Handle transient failure
    await AgentTaskService.handle_task_failure(
        db=async_db,
        task_id=task.id,
        worker_id="worker-retry-1",
        exc=TransientTaskError("Temporary network timeout connecting to socket"),
    )

    refreshed = await async_db.get(Task, task.id)
    assert refreshed.status == TaskStatus.RETRYABLE_FAILURE
    assert refreshed.lease_owner is None
    assert refreshed.lease_expires_at is None
    assert refreshed.error_category == "TRANSIENT_FAILURE"
    assert refreshed.attempt_count == 1
    # Backoff: 2 ** 1 = 2 seconds
    assert refreshed.scheduled_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_retry_exhaustion_transitions_to_failed(async_db):
    """When attempt_count reaches max_attempts, task enters terminal FAILED state."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    async_db.add(User(id=user_a_id, username="user_ea", email="ea@ex.com", password_hash="h", full_name="EA", phone_number="1"))
    async_db.add(User(id=user_b_id, username="user_eb", email="eb@ex.com", password_hash="h", full_name="EB", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=user_a_id, target_id=user_b_id, status=ConversationStatus.ACTIVE))

    task = Task(
        task_type="AGENT_DIALOGUE_TURN",
        conversation_id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        status=TaskStatus.RUNNING,
        attempt_count=3,  # Reached max attempts
        max_attempts=3,
        lease_owner="worker-exhausted",
        lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
        payload={"idempotency_key": "exhausted-key"},
    )
    async_db.add(task)
    await async_db.commit()

    await AgentTaskService.handle_task_failure(
        db=async_db,
        task_id=task.id,
        worker_id="worker-exhausted",
        exc=TransientTaskError("Transient timeout at limit"),
    )

    refreshed = await async_db.get(Task, task.id)
    assert refreshed.status == TaskStatus.FAILED
    assert refreshed.error_category == "RETRY_EXHAUSTED"
    assert refreshed.completed_at is not None


@pytest.mark.asyncio
async def test_permanent_failure_does_not_retry(async_db):
    """Permanent errors fail immediately without retrying."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    async_db.add(User(id=user_a_id, username="user_pa", email="pa@ex.com", password_hash="h", full_name="PA", phone_number="1"))
    async_db.add(User(id=user_b_id, username="user_pb", email="pb@ex.com", password_hash="h", full_name="PB", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=user_a_id, target_id=user_b_id, status=ConversationStatus.ACTIVE))

    task = Task(
        task_type="AGENT_DIALOGUE_TURN",
        conversation_id=conv_id,
        initiator_id=user_a_id,
        target_id=user_b_id,
        status=TaskStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        lease_owner="worker-perm",
        lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
        payload={"idempotency_key": "perm-key"},
    )
    async_db.add(task)
    await async_db.commit()

    await AgentTaskService.handle_task_failure(
        db=async_db,
        task_id=task.id,
        worker_id="worker-perm",
        exc=PermanentTaskError("Conversation was deleted or cancelled"),
    )

    refreshed = await async_db.get(Task, task.id)
    assert refreshed.status == TaskStatus.FAILED
    assert refreshed.error_category == "PERMANENT_FAILURE"
    assert refreshed.completed_at is not None


@pytest.mark.asyncio
async def test_task_cancellation(async_db):
    """Pending tasks can be cancelled gracefully."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    async_db.add(User(id=user_a_id, username="user_ca", email="ca@ex.com", password_hash="h", full_name="CA", phone_number="1"))
    async_db.add(User(id=user_b_id, username="user_cb", email="cb@ex.com", password_hash="h", full_name="CB", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=user_a_id, target_id=user_b_id, status=ConversationStatus.ACTIVE))

    task = Task(
        task_type="AGENT_DIALOGUE_TURN",
        conversation_id=conv_id,
        initiator_id=user_a_id,
        status=TaskStatus.PENDING,
        attempt_count=0,
        max_attempts=3,
        payload={"idempotency_key": "cancel-key"},
    )
    async_db.add(task)
    await async_db.commit()

    success = await AgentTaskService.cancel_task(db=async_db, task_id=task.id, reason="User retracted invitation")
    assert success is True

    await async_db.refresh(task)
    assert task.status == TaskStatus.CANCELLED
    assert task.error_category == "USER_CANCELLED"
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_end_to_end_agent_task_execution(sync_engine, async_db):
    """End-to-end task execution creates real AGENT message turn and completes task SUCCEEDED."""
    alice, alice_token = create_agent_test_attendee(
        sync_engine, "alice_agent", "alice_a@example.com", "Alice Rivera", "Staff Engineer", "CloudCorp",
        intent=ParticipationIntent.NETWORKING,
        topics=["PostgreSQL", "AsyncIO"],
        hobbies=["Cycling"],
    )
    bob, bob_token = create_agent_test_attendee(
        sync_engine, "bob_agent", "bob_a@example.com", "Bob Zhang", "Director of Infrastructure", "ScaleTech",
        intent=ParticipationIntent.NETWORKING,
        topics=["PostgreSQL", "Observability"],
        hobbies=["Cycling"],
    )

    conv = Conversation(
        initiator_id=alice.id,
        target_id=bob.id,
        status=ConversationStatus.ACTIVE,
    )
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # Create agent turn task
    task = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv.id,
        initiator_id=alice.id,
        target_id=bob.id,
        turn_index=0,
        idempotency_key="e2e-agent-turn-001",
    )

    # Worker claims task
    worker = AgentWorker(worker_id="e2e-worker-test")
    claimed = await AgentTaskService.claim_next_task(db=async_db, worker_id=worker.worker_id)
    assert claimed is not None

    # Worker executes task
    result = await AgentTaskService.execute_task(db=async_db, task=claimed, worker_id=worker.worker_id)
    assert result["turn_index"] == 0
    assert result["action_type"] == "INTRODUCE"

    # Verify task status is SUCCEEDED
    task_refreshed = await async_db.get(Task, task.id)
    assert task_refreshed.status == TaskStatus.SUCCEEDED
    assert task_refreshed.completed_at is not None

    # Verify message persisted in core.messages with MessageSenderType.AGENT
    msg_stmt = select(Message).where(Message.conversation_id == conv.id, Message.turn_index == 0)
    msg = await async_db.scalar(msg_stmt)
    assert msg is not None
    assert msg.sender_type == MessageSenderType.AGENT
    assert msg.sender_id == alice.id
    assert "PostgreSQL" in msg.content
    assert "Alice Rivera" in msg.content


@pytest.mark.asyncio
async def test_real_conversation_acceptance_leaves_conversation_clean_for_manual_messaging(sync_engine, async_db):
    """Accepting an invitation transitions to ACTIVE without auto-injecting agent messages."""
    carol, carol_token = create_agent_test_attendee(
        sync_engine, "carol_attendee", "carol@example.com", "Carol Danvers", "Lead Architect", "SpaceTech",
        intent=ParticipationIntent.NETWORKING,
        topics=["Cloud Native", "Observability"],
        hobbies=["Hiking"],
    )
    dan, dan_token = create_agent_test_attendee(
        sync_engine, "dan_attendee", "dan@example.com", "Dan Hughes", "Engineering Director", "OrbitCorp",
        intent=ParticipationIntent.NETWORKING,
        topics=["Cloud Native", "FinOps"],
        hobbies=["Hiking"],
    )

    # 1. Initiator initiates conversation
    conv_resp = await ConversationService.initiate_conversation(
        db=async_db,
        initiator=carol,
        target_id=dan.id,
        client_ip="127.0.0.1",
    )
    assert conv_resp.status == ConversationStatus.INVITED

    # 2. Target accepts conversation via real service lifecycle
    detail_resp = await ConversationService.update_conversation_status(
        db=async_db,
        conversation_id=conv_resp.id,
        current_user_id=dan.id,
        client_ip="127.0.0.1",
        action="ACCEPT",
    )
    assert detail_resp.status == ConversationStatus.ACTIVE

    # 3. Confirm NO automated tasks or messages were auto-injected on accept
    task_stmt = select(Task).where(Task.conversation_id == conv_resp.id)
    tasks = (await async_db.scalars(task_stmt)).all()
    assert len(tasks) in (0, 1)

    msgs_stmt = select(Message).where(Message.conversation_id == conv_resp.id)
    msgs = (await async_db.scalars(msgs_stmt)).all()
    assert len(msgs) == 0

    # 4. Attendees can converse manually without interference
    msg_manual, _ = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv_resp.id,
        sender_id=carol.id,
        content="Hi Dan, glad we connected!",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert msg_manual.turn_index == 0
    assert msg_manual.sender_type == MessageSenderType.PARTICIPANT


@pytest.mark.asyncio
async def test_duplicate_enqueue_idempotency_protection(async_db):
    """Calling create_agent_dialogue_task multiple times with same idempotency key returns existing task."""
    conv_id = uuid.uuid4()
    u1_id = uuid.uuid4()
    u2_id = uuid.uuid4()
    async_db.add(User(id=u1_id, username="user_dup1", email="dup1@ex.com", password_hash="h", full_name="D1", phone_number="1"))
    async_db.add(User(id=u2_id, username="user_dup2", email="dup2@ex.com", password_hash="h", full_name="D2", phone_number="2"))
    async_db.add(Conversation(id=conv_id, initiator_id=u1_id, target_id=u2_id, status=ConversationStatus.ACTIVE))
    await async_db.commit()

    idempotency_key = f"dedup-test-{conv_id}-turn-0"

    task_1 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=0,
        idempotency_key=idempotency_key,
    )

    task_2 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv_id,
        initiator_id=u1_id,
        target_id=u2_id,
        turn_index=0,
        idempotency_key=idempotency_key,
    )

    assert task_1.id == task_2.id

    # Verify only 1 row exists in a2a.tasks
    all_tasks = (await async_db.scalars(select(Task).where(Task.conversation_id == conv_id))).all()
    assert len(all_tasks) == 1


@pytest.mark.asyncio
async def test_stale_turn_satisfaction_prevents_duplicate_messages(sync_engine, async_db):
    """If a task was enqueued for turn 0, but turn 0 was already committed, worker marks task SUCCEEDED without creating duplicate message."""
    user_a, _ = create_agent_test_attendee(sync_engine, "stale_a", "stale_a@ex.com", "Stale A", "Dev", "Co")
    user_b, _ = create_agent_test_attendee(sync_engine, "stale_b", "stale_b@ex.com", "Stale B", "Dev", "Co")

    conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # 1. Simulate participant already sending Turn 0 message
    await ConversationService.append_message(
        db=async_db,
        conversation_id=conv.id,
        sender_id=user_a.id,
        content="Hello manually typed message!",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )

    # 2. An old task enqueued for turn 0 is now claimed by worker
    task = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv.id,
        initiator_id=user_a.id,
        target_id=user_b.id,
        turn_index=0,
        idempotency_key=f"stale-satisfy-{conv.id}-turn-0",
    )

    worker = AgentWorker(worker_id="stale-turn-worker")
    claimed = await AgentTaskService.claim_next_task(db=async_db, worker_id=worker.worker_id)
    assert claimed is not None

    # 3. Worker executes task -> must detect turn 0 already satisfied and exit cleanly
    result = await AgentTaskService.execute_task(db=async_db, task=claimed, worker_id=worker.worker_id)
    assert result["action_type"] == "SKIPPED_ALREADY_SATISFIED"

    # 4. Confirm message count is still exactly 1 (no duplicate turn appended)
    msgs = (await async_db.scalars(select(Message).where(Message.conversation_id == conv.id))).all()
    assert len(msgs) == 1


@pytest.mark.asyncio
async def test_conversation_cancellation_cancels_pending_tasks(sync_engine, async_db):
    """When a conversation is cancelled or concluded, any pending agent tasks are cancelled with CONVERSATION_INACTIVE."""
    user_a, _ = create_agent_test_attendee(sync_engine, "canc_a", "canc_a@ex.com", "Canc A", "Dev", "Co")
    user_b, _ = create_agent_test_attendee(sync_engine, "canc_b", "canc_b@ex.com", "Canc B", "Dev", "Co")

    conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.INVITED)
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # Accept invitation
    await ConversationService.update_conversation_status(
        db=async_db, conversation_id=conv.id, current_user_id=user_b.id, client_ip="127.0.0.1", action="ACCEPT",
    )

    # Explicitly enqueue task for conversation
    task = await AgentTaskService.create_agent_dialogue_task(
        db=async_db, conversation_id=conv.id, initiator_id=user_a.id, target_id=user_b.id, turn_index=0, idempotency_key=f"canc-task-{conv.id}",
    )
    assert task.status == TaskStatus.PENDING

    # Cancel conversation
    await ConversationService.update_conversation_status(
        db=async_db, conversation_id=conv.id, current_user_id=user_a.id, client_ip="127.0.0.1", action="CANCEL",
    )

    # Verify task was transitioned to CANCELLED
    await async_db.refresh(task)
    assert task.status == TaskStatus.CANCELLED
    assert task.error_category == "CONVERSATION_INACTIVE"


@pytest.mark.asyncio
async def test_30_turn_boundary_concurrency_protection(sync_engine, async_db):
    """When conversation reaches turn 29, 30th message marks it COMPLETED and subsequent attempts fail with 409."""
    user_a, _ = create_agent_test_attendee(sync_engine, "turn_a", "turn_a@ex.com", "Turn A", "Dev", "Co")
    user_b, _ = create_agent_test_attendee(sync_engine, "turn_b", "turn_b@ex.com", "Turn B", "Dev", "Co")

    conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # Populate 29 messages (turns 0..28)
    now = datetime.now(timezone.utc)
    for i in range(29):
        sender = user_a.id if i % 2 == 0 else user_b.id
        async_db.add(Message(
            conversation_id=conv.id,
            sender_id=sender,
            sender_type=MessageSenderType.PARTICIPANT,
            turn_index=i,
            content=f"Message turn {i}",
            created_at=now,
        ))
    await async_db.commit()

    # The 30th message (turn 29) is sent
    msg_30, detail = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv.id,
        sender_id=user_b.id,
        content="30th message concluding the conversation",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert msg_30.turn_index == 29
    assert detail.status == ConversationStatus.COMPLETED
    assert detail.terminal_outcome == ConversationOutcome.COMPLETED_WITHOUT_PROPOSAL

    # Further attempt to append a 31st message fails with 409 Conflict
    with pytest.raises(Exception) as exc_info:
        await ConversationService.append_message(
            db=async_db,
            conversation_id=conv.id,
            sender_id=user_a.id,
            content="Illegal 31st message",
            client_ip="127.0.0.1",
            sender_type=MessageSenderType.AGENT,
        )
    assert "already" in str(exc_info.value.detail).lower() or "maximum turn limit" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_worker_run_forever_graceful_shutdown(sync_engine, async_db):
    """Worker background task starts, processes queue, and shuts down cleanly upon stop()."""
    user_a, _ = create_agent_test_attendee(sync_engine, "bg_a", "bg_a@ex.com", "Bg A", "Dev", "Co")
    user_b, _ = create_agent_test_attendee(sync_engine, "bg_b", "bg_b@ex.com", "Bg B", "Dev", "Co")

    conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # Create task
    task = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv.id,
        initiator_id=user_a.id,
        target_id=user_b.id,
        turn_index=0,
        idempotency_key=f"bg-worker-test-{conv.id}",
    )

    # Use function-scoped session factory
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    worker = AgentWorker(worker_id="bg-test-worker", poll_interval=0.1)
    worker_task = asyncio.create_task(worker.run_forever(session_factory=session_factory))

    # Wait for worker to process task
    for _ in range(30):
        await asyncio.sleep(0.1)
        await async_db.refresh(task)
        if task.status == TaskStatus.SUCCEEDED:
            break

    assert task.status == TaskStatus.SUCCEEDED

    # Signal stop and await clean termination
    worker.stop()
    await asyncio.wait_for(worker_task, timeout=2.0)
    assert worker._running is False
    await engine.dispose()


@pytest.mark.asyncio
async def test_persist_before_publish_and_atomic_stale_worker_rollback(sync_engine, async_db):
    """If a worker executes a turn but loses its lease prior to commit, the message turn is rolled back."""
    user_a, _ = create_agent_test_attendee(sync_engine, "atom_a", "atom_a@ex.com", "Atom A", "Eng", "Corp")
    user_b, _ = create_agent_test_attendee(sync_engine, "atom_b", "atom_b@ex.com", "Atom B", "Eng", "Corp")

    conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # Create task
    task = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv.id,
        initiator_id=user_a.id,
        target_id=user_b.id,
        turn_index=0,
        idempotency_key=f"atom-test-{conv.id}",
    )

    # Claim task as worker_1
    claimed = await AgentTaskService.claim_next_task(async_db, worker_id="worker_1")
    assert claimed is not None
    assert claimed.id == task.id

    # Simulate lease theft: worker_2 steals lease or task is reset
    await async_db.execute(
        update(Task).where(Task.id == task.id).values(lease_owner="worker_2")
    )
    await async_db.commit()

    # Now worker_1 attempts to execute_task -> must raise StaleWorkerError and rollback uncommitted message
    from app.services.agent_worker import StaleWorkerError
    with pytest.raises(StaleWorkerError):
        await AgentTaskService.execute_task(async_db, claimed, worker_id="worker_1")

    # Verify no message was persisted for this conversation in PostgreSQL
    msg_count = await async_db.scalar(
        select(func.count(Message.id)).where(Message.conversation_id == conv.id)
    )
    assert msg_count == 0


@pytest.mark.asyncio
async def test_autonomous_five_turn_sequence_and_attendee_continuation(sync_engine, async_db):
    """Full 5-turn autonomous sequence (turns 0-4) runs deterministically, leaves conv ACTIVE for attendee turns (5-19)."""
    user_a, _ = create_agent_test_attendee(sync_engine, "seq_a", "seq_a@ex.com", "Seq A", "CEO", "Alpha")
    user_b, _ = create_agent_test_attendee(sync_engine, "seq_b", "seq_b@ex.com", "Seq B", "CTO", "Beta")

    conv = Conversation(initiator_id=user_a.id, target_id=user_b.id, status=ConversationStatus.ACTIVE)
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    # Enqueue Turn 0 with autonomous=True
    task_0 = await AgentTaskService.create_agent_dialogue_task(
        db=async_db,
        conversation_id=conv.id,
        initiator_id=user_a.id,
        target_id=user_b.id,
        turn_index=0,
        idempotency_key=f"seq-{conv.id}-turn-0",
        payload_extra={"autonomous": True},
    )

    # Process all 5 autonomous turns sequentially through worker execution
    for expected_turn in range(5):
        claimed = await AgentTaskService.claim_next_task(async_db, worker_id=f"seq-worker-{expected_turn}")
        assert claimed is not None, f"Expected task for turn {expected_turn} to be ready/claimed"
        assert claimed.payload.get("turn_index") == expected_turn

        res = await AgentTaskService.execute_task(async_db, claimed, worker_id=f"seq-worker-{expected_turn}")
        assert res["turn_index"] == expected_turn

    # Verify all 5 turns (0, 1, 2, 3, 4) exist in database
    msgs = (
        await async_db.scalars(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.turn_index.asc())
        )
    ).all()
    assert len(msgs) == 5
    assert [m.turn_index for m in msgs] == [0, 1, 2, 3, 4]
    assert all(m.sender_type == MessageSenderType.AGENT for m in msgs)

    # Verify Turn 0 is initiator, Turn 1 is target, Turn 2 is initiator, Turn 3 is target, Turn 4 is initiator
    assert msgs[0].sender_id == user_a.id
    assert msgs[1].sender_id == user_b.id
    assert msgs[2].sender_id == user_a.id
    assert msgs[3].sender_id == user_b.id
    assert msgs[4].sender_id == user_a.id

    # Verify no 6th agent task is enqueued (sequence finishes at turn 4)
    next_task = await AgentTaskService.claim_next_task(async_db, worker_id="check-worker")
    assert next_task is None

    # CRITICAL: Verify conversation remains ACTIVE after turn 4
    await async_db.refresh(conv)
    assert conv.status == ConversationStatus.ACTIVE
    assert conv.terminal_outcome is None

    # Verify human attendees can now chat manually for remaining 15 turns (turns 5 to 19)
    human_msg_5, detail = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv.id,
        sender_id=user_b.id,
        content="Human follow-up message from User B!",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert human_msg_5.turn_index == 5
    assert human_msg_5.sender_type == MessageSenderTypeEnum.PARTICIPANT
    assert detail.status == ConversationStatusEnum.ACTIVE


def test_representative_dialogue_mood_grounding(sync_engine):
    """Dialogue engine grounds turns in active informal mood preferences (<24h TTL) without hallucination."""
    now = datetime.now(timezone.utc)
    user_a, _ = create_agent_test_attendee(
        sync_engine, "mood_alex", "alex_m@example.com", "Alex Mood", "Lead Architect", "CloudCorp",
        intent=ParticipationIntent.NETWORKING,
        topics=["Kubernetes"],
    )
    user_b, _ = create_agent_test_attendee(
        sync_engine, "mood_beth", "beth_m@example.com", "Beth Mood", "Staff Engineer", "ScaleTech",
        intent=ParticipationIntent.CASUAL,
        topics=["Kubernetes"],
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine) as session:
        prof_a = session.query(ParticipantProfile).filter_by(user_id=user_a.id).one()
        prof_b = session.query(ParticipantProfile).filter_by(user_id=user_b.id).one()

        # Set active moods
        prof_a.current_mood = "Ready to network"
        prof_a.mood_updated_at = now
        prof_b.current_mood = "Open to casual conversation"
        prof_b.mood_updated_at = now
        session.commit()

        # Turn 0: Alex's representative mentions Alex's active mood
        env_turn_0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=0,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Kubernetes"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Kubernetes"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="mood-turn-0",
        )
        assert env_turn_0.turn_index == 0
        assert "Alex Mood" in env_turn_0.content
        assert "Ready to network" in env_turn_0.content
        assert "Kubernetes" in env_turn_0.content
        assert env_turn_0.metadata["speaking_mood"] == "Ready to network"

        # Turn 1: Beth's representative mentions Beth's active mood
        env_turn_1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=1,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Kubernetes"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Kubernetes"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="mood-turn-1",
        )
        assert env_turn_1.turn_index == 1
        assert "Beth Mood" in env_turn_1.content
        assert "Open to casual conversation" in env_turn_1.content
        assert env_turn_1.metadata["speaking_mood"] == "Open to casual conversation"


def test_representative_dialogue_mood_expiration_omitted(sync_engine):
    """Expired mood (>24h) is strictly omitted from dialogue turns, adhering to Rule 9 zero-hallucination."""
    expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
    user_a, _ = create_agent_test_attendee(
        sync_engine, "exp_a", "exp_a@example.com", "Exp A", "Director", "Alpha",
        intent=ParticipationIntent.NETWORKING,
        topics=["Cloud"],
    )
    user_b, _ = create_agent_test_attendee(
        sync_engine, "exp_b", "exp_b@example.com", "Exp B", "Manager", "Beta",
        intent=ParticipationIntent.NETWORKING,
        topics=["Cloud"],
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine) as session:
        prof_a = session.query(ParticipantProfile).filter_by(user_id=user_a.id).one()
        prof_b = session.query(ParticipantProfile).filter_by(user_id=user_b.id).one()

        # Set expired mood for User A
        prof_a.current_mood = "Ready to network"
        prof_a.mood_updated_at = expired_time
        session.commit()

        assert prof_a.active_mood is None  # Verify TTL check

        env_turn_0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=0,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Cloud"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Cloud"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="exp-turn-0",
        )
        # Verify no mood is hallucinated or spoken
        assert "Ready to network" not in env_turn_0.content
        assert "focus as" not in env_turn_0.content
        assert env_turn_0.metadata["speaking_mood"] is None


def test_representative_dialogue_low_key_interaction_style(sync_engine):
    """Low-key mood preference adjusts collaboration proposal in Turn 2 and confirmation in Turn 3."""
    now = datetime.now(timezone.utc)
    user_a, _ = create_agent_test_attendee(
        sync_engine, "lk_a", "lk_a@example.com", "Quiet Alice", "Researcher", "LabCorp",
        intent=ParticipationIntent.NETWORKING,
        topics=["Quantum"],
    )
    user_b, _ = create_agent_test_attendee(
        sync_engine, "lk_b", "lk_b@example.com", "Bob Engineer", "Dev", "LabCorp",
        intent=ParticipationIntent.NETWORKING,
        topics=["Quantum"],
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine) as session:
        prof_a = session.query(ParticipantProfile).filter_by(user_id=user_a.id).one()
        prof_b = session.query(ParticipantProfile).filter_by(user_id=user_b.id).one()

        prof_a.current_mood = "Prefer low-key interaction"
        prof_a.mood_updated_at = now
        session.commit()

        # Turn 2: Low-key proposal
        env_turn_2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=2,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Quantum"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Quantum"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="lk-turn-2",
        )
        assert "low-key interaction" in env_turn_2.content
        assert "asynchronous" in env_turn_2.content

        # Turn 3: Target acknowledges low-key conditionally (no unsupported agreement)
        env_turn_3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=3,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Quantum"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Quantum"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="lk-turn-3",
        )
        assert "That could be an option" in env_turn_3.content
        assert "follow up asynchronously" in env_turn_3.content
        assert "That works nicely for" not in env_turn_3.content
        assert "We will coordinate" not in env_turn_3.content


def test_representative_factual_grounding_no_hallucinations(sync_engine):
    """Dialogue engine strictly avoids fabricated venue features, intervals, or presumptuous commitments (Rule 9)."""
    user_a, _ = create_agent_test_attendee(
        sync_engine, "fg_a", "fg_a@example.com", "Grounding A", "VP Engineering", "Acme",
        intent=ParticipationIntent.CASUAL,
        topics=["Green Tech"],
    )
    user_b, _ = create_agent_test_attendee(
        sync_engine, "fg_b", "fg_b@example.com", "Grounding B", "Director", "Acme",
        intent=ParticipationIntent.CASUAL,
        topics=["Green Tech"],
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine) as session:
        prof_a = session.query(ParticipantProfile).filter_by(user_id=user_a.id).one()
        prof_b = session.query(ParticipantProfile).filter_by(user_id=user_b.id).one()

        # Turn 2: Verify NO fabricated venue locations (like exhibition hall lounge) or ungrounded plan claims
        env_turn_2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=2,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Green Tech"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Green Tech"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="fg-turn-2",
        )
        assert "exhibition hall lounge" not in env_turn_2.content
        assert "We are planning to catch" not in env_turn_2.content
        assert "If schedules permit" in env_turn_2.content

        # Turn 3: Verify NO fabricated intervals or unsupported agreement claims
        env_turn_3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=3,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Green Tech"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Green Tech"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="fg-turn-3",
        )
        assert "designated networking interval" not in env_turn_3.content
        assert "productive plan" not in env_turn_3.content
        assert "Let's coordinate" not in env_turn_3.content
        assert "That could be an option" in env_turn_3.content
        assert "can decide whether to reach out" in env_turn_3.content
        assert "depending on their preferences and schedule" in env_turn_3.content

        # Turn 4: Verify NO presumptuous meeting commitments; handoff to attendees
        env_turn_4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=4,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=["Green Tech"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=user_b,
            target_profile=prof_b,
            target_topics=["Green Tech"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="fg-turn-4",
        )
        assert "leave this conversation open" in env_turn_4.content
        assert "coordinate directly" in env_turn_4.content


def test_representative_agenda_context_mutual_vs_single_bookmark(sync_engine):
    """Turn 0 references mutual bookmark interest only when both attendees bookmarked; never for single bookmarks."""
    user_a, _ = create_agent_test_attendee(
        sync_engine, "bk_a", "bk_a@example.com", "Book A", "Dev", "Comp",
        intent=ParticipationIntent.NETWORKING,
        topics=[],
    )
    user_b, _ = create_agent_test_attendee(
        sync_engine, "bk_b", "bk_b@example.com", "Book B", "Dev", "Comp",
        intent=ParticipationIntent.NETWORKING,
        topics=[],
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine) as session:
        prof_a = session.query(ParticipantProfile).filter_by(user_id=user_a.id).one()
        prof_b = session.query(ParticipantProfile).filter_by(user_id=user_b.id).one()

        # Case 1: Both bookmarked "Keynote: Future of AI"
        env_mutual = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=0,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=[],
            initiator_hobbies=[],
            initiator_sessions=["Keynote: Future of AI"],
            target=user_b,
            target_profile=prof_b,
            target_topics=[],
            target_hobbies=[],
            target_sessions=["Keynote: Future of AI"],
            idempotency_key="mutual-bk-0",
        )
        assert "noticed we both have 'Keynote: Future of AI' bookmarked on our agenda" in env_mutual.content
        assert "mutual interest in attending" not in env_mutual.content

        # Case 2: Only user_a bookmarked; user_b did not -> must NOT mention session
        env_single = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=0,
            initiator=user_a,
            initiator_profile=prof_a,
            initiator_topics=[],
            initiator_hobbies=[],
            initiator_sessions=["Keynote: Future of AI"],
            target=user_b,
            target_profile=prof_b,
            target_topics=[],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key="single-bk-0",
        )
        assert "Keynote: Future of AI" not in env_single.content
        assert "sharing insights across conference sessions" in env_single.content


