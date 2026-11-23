"""Contract, authorization, privacy, and integration tests for Candidate Matching API (P4-WS2, GAP-06)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import generate_session_token, hash_session_token
from app.db.models.agenda import BookmarkedSession, Conference, Session as ConfSession
from app.db.models.audit import AuditLog
from app.db.models.profile import (
    AvailabilityStatus,
    ParticipantHobby,
    ParticipantProfile,
    ParticipantTopic,
    ParticipationIntent,
)
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app
from app.services.matching import CooldownPolicy, QuotaAndCooldownService

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
def cleanup_test_db(sync_engine):
    """Clean up records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
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


def create_user_and_session(
    sync_engine,
    username: str = "alice_dev",
    email: str = "alice@example.com",
    is_active: bool = True,
    is_expired: bool = False,
    is_revoked: bool = False,
):
    """Create a test user and an active session token in the database."""
    with SASession(sync_engine) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=f"Full Name of {username}",
            company_name="Alcon Industrial Corp",
            job_title="Automation Specialist",
            phone_number="+1-555-0199",
            is_active=is_active,
        )
        session.add(user)
        session.flush()

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now - timedelta(hours=1) if is_expired else now + timedelta(hours=24)
        revoked_at = now if is_revoked else None

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            last_accessed_at=now,
            revoked_at=revoked_at,
        )
        session.add(user_session)
        session.commit()
        session.refresh(user)

        return user, raw_token


def setup_participant_profile(
    sync_engine,
    user_id: uuid.UUID,
    intent: ParticipationIntent = ParticipationIntent.NETWORKING,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    allow_agent_matching: bool = True,
    topics: Optional[List[str]] = None,
    hobbies: Optional[List[str]] = None,
):
    """Attach initialized profile, topics, and hobbies to a user."""
    with SASession(sync_engine) as session:
        profile = ParticipantProfile(
            user_id=user_id,
            intent=intent,
            availability=availability,
            allow_agent_matching=allow_agent_matching,
            bio_summary="Participant bio for matching test.",
        )
        session.add(profile)
        for t in topics or []:
            session.add(ParticipantTopic(user_id=user_id, topic_keyword=t))
        for h in hobbies or []:
            session.add(ParticipantHobby(user_id=user_id, hobby_name=h))
        session.commit()


# =============================================================================
# 1. Authentication & Security Boundary Tests
# =============================================================================

def test_unauthenticated_request_returns_401(client):
    """Verify anonymous discovery requests return 401 Unauthorized."""
    resp = client.get("/converge-api/v1/matching/candidates")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_expired_or_revoked_session_returns_401(client, sync_engine):
    """Verify expired or revoked session tokens return 401 Unauthorized."""
    # Expired session
    _, expired_token = create_user_and_session(
        sync_engine, username="exp_user", email="exp@example.com", is_expired=True
    )
    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401

    # Revoked session
    _, revoked_token = create_user_and_session(
        sync_engine, username="rev_user", email="rev@example.com", is_revoked=True
    )
    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {revoked_token}"},
    )
    assert resp.status_code == 401


def test_uninitialized_profile_returns_404(client, sync_engine):
    """Verify authenticated user without an initialized profile receives 404."""
    user, token = create_user_and_session(sync_engine, username="no_prof", email="no_prof@example.com")
    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert "Participant profile not found" in resp.json()["detail"]


def test_requester_without_consent_returns_403(client, sync_engine):
    """Verify requester with allow_agent_matching=False receives 403 Forbidden (GAP-06)."""
    user, token = create_user_and_session(sync_engine, username="no_consent", email="no_c@example.com")
    setup_participant_profile(sync_engine, user.id, allow_agent_matching=False)

    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Autonomous agent matching consent is not granted" in resp.json()["detail"]


def test_requester_in_dnd_or_offline_returns_403(client, sync_engine):
    """Verify requester in DO_NOT_DISTURB or OFFLINE status receives 403 Forbidden."""
    user, token = create_user_and_session(sync_engine, username="dnd_user", email="dnd@example.com")
    setup_participant_profile(sync_engine, user.id, availability=AvailabilityStatus.DO_NOT_DISTURB)

    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "DO_NOT_DISTURB" in resp.json()["detail"]

    # Test OFFLINE
    user2, token2 = create_user_and_session(sync_engine, username="off_user", email="off@example.com")
    setup_participant_profile(sync_engine, user2.id, availability=AvailabilityStatus.OFFLINE)

    resp2 = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp2.status_code == 403
    assert "OFFLINE" in resp2.json()["detail"]


def test_requester_in_session_succeeds_200(client, sync_engine):
    """Verify requester attending a session (IN_SESSION) succeeds with 200 OK (Domain Rationale)."""
    user, token = create_user_and_session(sync_engine, username="session_user", email="sess@example.com")
    setup_participant_profile(sync_engine, user.id, availability=AvailabilityStatus.IN_SESSION)

    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["requester_id"] == str(user.id)
    assert data["candidates"] == []


# =============================================================================
# 2. Hard Eligibility & Candidate Filtering
# =============================================================================

def test_self_match_is_strictly_excluded(client, sync_engine):
    """Verify requester cannot match with themselves."""
    user, token = create_user_and_session(sync_engine, username="self_user", email="self@example.com")
    setup_participant_profile(
        sync_engine,
        user.id,
        topics=["Automation", "Sensors"],
        hobbies=["Tea / Coffee"],
    )

    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for c in data["candidates"]:
        assert c["candidate_id"] != str(user.id)


def test_candidate_without_consent_excluded(client, sync_engine):
    """Verify candidates with allow_agent_matching=False are never returned."""
    req, req_token = create_user_and_session(sync_engine, username="req_user", email="req@example.com")
    setup_participant_profile(
        sync_engine, req.id, topics=["Decarbonization"], hobbies=["Tea / Coffee"]
    )

    # Candidate has identical topics but consent=False
    cand, _ = create_user_and_session(sync_engine, username="cand_no_consent", email="c1@example.com")
    setup_participant_profile(
        sync_engine,
        cand.id,
        allow_agent_matching=False,
        topics=["Decarbonization"],
        hobbies=["Tea / Coffee"],
    )

    resp = client.get(
        "/converge-api/v1/matching/candidates?filter_by_threshold=false",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    candidate_ids = [c["candidate_id"] for c in data["candidates"]]
    assert str(cand.id) not in candidate_ids


def test_inactive_and_dnd_candidates_excluded(client, sync_engine):
    """Verify inactive and DND/OFFLINE candidates are excluded from discovery."""
    req, req_token = create_user_and_session(sync_engine, username="req_avail", email="req_a@example.com")
    setup_participant_profile(sync_engine, req.id, topics=["AI", "Robotics"])

    # Deactivated candidate
    inact, _ = create_user_and_session(sync_engine, username="cand_inact", email="inact@example.com", is_active=False)
    setup_participant_profile(sync_engine, inact.id, topics=["AI", "Robotics"])

    # DND candidate
    dnd, _ = create_user_and_session(sync_engine, username="cand_dnd", email="dnd_cand@example.com")
    setup_participant_profile(sync_engine, dnd.id, availability=AvailabilityStatus.DO_NOT_DISTURB, topics=["AI", "Robotics"])

    # Offline candidate
    off, _ = create_user_and_session(sync_engine, username="cand_off", email="off_cand@example.com")
    setup_participant_profile(sync_engine, off.id, availability=AvailabilityStatus.OFFLINE, topics=["AI", "Robotics"])

    resp = client.get(
        "/converge-api/v1/matching/candidates?filter_by_threshold=false",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    candidate_ids = [c["candidate_id"] for c in data["candidates"]]
    assert str(inact.id) not in candidate_ids
    assert str(dnd.id) not in candidate_ids
    assert str(off.id) not in candidate_ids


# =============================================================================
# 3. Threshold Filtering vs. Ranking Separation
# =============================================================================

def test_threshold_filter_separation(client, sync_engine):
    """Verify filter_by_threshold=True filters < 0.65 while False returns all ranked candidates."""
    req, req_token = create_user_and_session(sync_engine, username="alice", email="alice@example.com")
    setup_participant_profile(
        sync_engine,
        req.id,
        intent=ParticipationIntent.NETWORKING,
        topics=["Kiln Decarbonization", "CCUS"],
        hobbies=["Tea / Coffee"],
    )

    # Bob: High match (aligned intent, overlapping topics and hobbies) -> score > 0.65
    bob, _ = create_user_and_session(sync_engine, username="bob", email="bob@example.com")
    setup_participant_profile(
        sync_engine,
        bob.id,
        intent=ParticipationIntent.NETWORKING,
        topics=["Kiln Decarbonization", "CCUS"],
        hobbies=["Tea / Coffee"],
    )

    # Charlie: Low match (disjoint intent: NETWORKING vs CASUAL) -> score ~ 0.35 (due to topics/hobbies)
    charlie, _ = create_user_and_session(sync_engine, username="charlie", email="charlie@example.com")
    setup_participant_profile(
        sync_engine,
        charlie.id,
        intent=ParticipationIntent.CASUAL,  # Disjoint
        topics=["Robotics"],               # Disjoint
        hobbies=["Tea / Coffee"],          # Single hobby match
    )

    # 1. With filter_by_threshold=True (default): only Bob should be returned
    resp1 = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["matched_count"] == 1
    assert len(data1["candidates"]) == 1
    assert data1["candidates"][0]["candidate_id"] == str(bob.id)
    assert data1["candidates"][0]["composite_score"] >= 0.65

    # 2. With filter_by_threshold=False: both Bob and Charlie returned, Bob ranked first
    resp2 = client.get(
        "/converge-api/v1/matching/candidates?filter_by_threshold=false",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["matched_count"] == 2
    assert len(data2["candidates"]) == 2
    assert data2["candidates"][0]["candidate_id"] == str(bob.id)
    assert data2["candidates"][1]["candidate_id"] == str(charlie.id)
    assert data2["candidates"][0]["composite_score"] > data2["candidates"][1]["composite_score"]


def test_custom_threshold_query_param(client, sync_engine):
    """Verify custom threshold query parameter filters accurately."""
    req, req_token = create_user_and_session(sync_engine, username="user_thresh", email="ut@example.com")
    setup_participant_profile(sync_engine, req.id, topics=["AI", "ML"])

    cand1, _ = create_user_and_session(sync_engine, username="cand1", email="c1@example.com")
    setup_participant_profile(sync_engine, cand1.id, topics=["AI", "ML"])

    cand2, _ = create_user_and_session(sync_engine, username="cand2", email="c2@example.com")
    setup_participant_profile(sync_engine, cand2.id, topics=["AI", "Robotics"])

    # High threshold 0.95 -> only cand1
    resp = client.get(
        "/converge-api/v1/matching/candidates?threshold=0.95",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["candidate_id"] == str(cand1.id)


# =============================================================================
# 4. Deterministic Ordering & Pagination
# =============================================================================

def test_deterministic_ranking_across_repeated_requests(client, sync_engine):
    """Verify identical database inputs produce identical candidate ordering across 5 requests."""
    req, req_token = create_user_and_session(sync_engine, username="req_det", email="rdet@example.com")
    setup_participant_profile(sync_engine, req.id, topics=["Python", "Cloud"])

    for i in range(4):
        u, _ = create_user_and_session(sync_engine, username=f"cand_det_{i}", email=f"cd_{i}@example.com")
        setup_participant_profile(sync_engine, u.id, topics=["Python"])

    first_run_order = None
    for _ in range(5):
        resp = client.get(
            "/converge-api/v1/matching/candidates?filter_by_threshold=false",
            headers={"Authorization": f"Bearer {req_token}"},
        )
        assert resp.status_code == 200
        ids = [c["candidate_id"] for c in resp.json()["candidates"]]
        if first_run_order is None:
            first_run_order = ids
        else:
            assert ids == first_run_order


def test_pagination_limit_and_offset(client, sync_engine):
    """Verify pagination limit and offset parameters operate correctly."""
    req, req_token = create_user_and_session(sync_engine, username="req_page", email="rpage@example.com")
    setup_participant_profile(sync_engine, req.id, topics=["Engineering"])

    for i in range(3):
        u, _ = create_user_and_session(sync_engine, username=f"cand_p_{i}", email=f"cp_{i}@example.com")
        setup_participant_profile(sync_engine, u.id, topics=["Engineering"])

    # Page 1: limit=2, offset=0
    r1 = client.get(
        "/converge-api/v1/matching/candidates?filter_by_threshold=false&limit=2&offset=0",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["candidates"]) == 2
    assert d1["matched_count"] == 3
    assert d1["limit"] == 2
    assert d1["offset"] == 0

    # Page 2: limit=2, offset=2
    r2 = client.get(
        "/converge-api/v1/matching/candidates?filter_by_threshold=false&limit=2&offset=2",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert len(d2["candidates"]) == 1
    assert d2["offset"] == 2


# =============================================================================
# 5. Zero PII Projection & Privacy Defense
# =============================================================================

def test_zero_pii_in_response_projection(client, sync_engine):
    """Verify candidate cards contain zero sensitive fields (email, phone, hash, audit)."""
    req, req_token = create_user_and_session(sync_engine, username="req_pii", email="req_pii@example.com")
    setup_participant_profile(sync_engine, req.id, topics=["Privacy"])

    cand, _ = create_user_and_session(sync_engine, username="cand_pii", email="sensitive@secret.com")
    setup_participant_profile(sync_engine, cand.id, topics=["Privacy"])

    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp.status_code == 200
    raw_text = resp.text

    # Private fields must not appear anywhere in the serialized response
    assert "sensitive@secret.com" not in raw_text
    assert "password_hash" not in raw_text
    assert "phone_number" not in raw_text
    assert "+1-555-0199" not in raw_text
    assert "allow_agent_matching" not in raw_text


def test_invalid_query_parameters_validation(client, sync_engine):
    """Verify out-of-bounds parameters return 422 Unprocessable Entity."""
    req, req_token = create_user_and_session(sync_engine, username="req_val", email="rv@example.com")
    setup_participant_profile(sync_engine, req.id)

    # limit > 100
    r1 = client.get(
        "/converge-api/v1/matching/candidates?limit=101",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r1.status_code == 422

    # threshold > 1.0
    r2 = client.get(
        "/converge-api/v1/matching/candidates?threshold=1.5",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert r2.status_code == 422


def test_audit_event_recorded_on_discovery(client, sync_engine):
    """Verify candidate discovery writes sanitized audit event to core.audit_logs."""
    req, req_token = create_user_and_session(sync_engine, username="audit_user", email="au@example.com")
    setup_participant_profile(sync_engine, req.id, topics=["Auditing"])

    resp = client.get(
        "/converge-api/v1/matching/candidates",
        headers={"Authorization": f"Bearer {req_token}"},
    )
    assert resp.status_code == 200

    with SASession(sync_engine) as session:
        log = session.execute(
            select(AuditLog).where(
                AuditLog.action_type == "matching.candidates.discover",
                AuditLog.user_id == req.id,
            )
        ).scalar_one_or_none()
        assert log is not None
        assert log.actor_username == "audit_user"
        assert log.resource_type == "matching.evaluation"
        assert "candidates_discovered" in str(log.event_payload)


# =============================================================================
# 6. Quota & Cooldown Policy Unit Tests (GAP-06)
# =============================================================================

def test_quota_and_cooldown_lifecycle_policy():
    """Verify mathematical and rule evaluation in QuotaAndCooldownService."""
    service = QuotaAndCooldownService(CooldownPolicy())

    # 1. Quota checks (max 3 concurrent active tasks)
    assert not service.is_quota_exceeded(active_task_count=0)
    assert not service.is_quota_exceeded(active_task_count=2)
    assert service.is_quota_exceeded(active_task_count=3)
    assert service.is_quota_exceeded(active_task_count=5)

    now = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)

    # 2. Cooldown for PROPOSAL_GENERATED (72 hours)
    recent_proposal = now - timedelta(hours=71)
    is_cool, rem = service.evaluate_pair_cooldown("PROPOSAL_GENERATED", recent_proposal, now)
    assert is_cool
    assert rem.total_seconds() == 3600  # 1 hour remaining

    old_proposal = now - timedelta(hours=73)
    is_cool, rem = service.evaluate_pair_cooldown("PROPOSAL_GENERATED", old_proposal, now)
    assert not is_cool

    # 3. Cooldown for COMPLETED_WITHOUT_PROPOSAL (48 hours)
    recent_completed = now - timedelta(hours=40)
    is_cool, rem = service.evaluate_pair_cooldown("COMPLETED_WITHOUT_PROPOSAL", recent_completed, now)
    assert is_cool

    old_completed = now - timedelta(hours=49)
    is_cool, rem = service.evaluate_pair_cooldown("COMPLETED_WITHOUT_PROPOSAL", old_completed, now)
    assert not is_cool

    # 4. Cooldown for CANCELLED or EXPIRED (24 hours)
    recent_cancelled = now - timedelta(hours=20)
    is_cool, rem = service.evaluate_pair_cooldown("CANCELLED", recent_cancelled, now)
    assert is_cool

    # 5. Cooldown for TRANSIENT_FAILURE (1 hour)
    recent_fail = now - timedelta(minutes=30)
    is_cool, rem = service.evaluate_pair_cooldown("TRANSIENT_FAILURE", recent_fail, now)
    assert is_cool

    old_fail = now - timedelta(minutes=61)
    is_cool, rem = service.evaluate_pair_cooldown("TRANSIENT_FAILURE", old_fail, now)
    assert not is_cool
