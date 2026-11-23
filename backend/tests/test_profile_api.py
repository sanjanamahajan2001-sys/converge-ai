"""Integration tests for Participant Profile APIs, IDOR defense, privacy projection, and CSRF protection (P2-WS5)."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    create_session,
    generate_session_token,
    hash_session_token,
)
from app.db.models import AuditLog, ParticipantHobby, ParticipantProfile, ParticipantTopic, User, UserSession
from app.main import create_app
from app.schemas.profile import (
    CURATED_HOBBIES,
    AvailabilityStatus,
    ParticipationIntent,
)

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


def create_user_and_session(sync_engine, username: str = "alice_dev", email: str = "alice@example.com", is_active: bool = True):
    """Create a test user and an active session token in the database."""
    with Session(sync_engine) as session:
        user = User(
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
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=24),
            last_accessed_at=now,
        )
        session.add(user_session)
        session.commit()
        session.refresh(user)

        return user, raw_token


# ==============================================================================
# 1. Own-Profile Retrieval (GET /profile/me)
# ==============================================================================


def test_get_my_profile_unauthenticated_rejected(client):
    """Verify GET /profile/me fails with 401 when unauthenticated."""
    resp = client.get("/converge-api/v1/profile/me")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_get_my_profile_not_found_when_uninitialized(client, sync_engine):
    """Verify GET /profile/me returns 404 without side effects when profile not yet initialized."""
    user, raw_token = create_user_and_session(sync_engine, "bob_new", "bob@example.com")

    resp = client.get(
        "/converge-api/v1/profile/me",
        cookies={SESSION_COOKIE_NAME: raw_token},
    )
    assert resp.status_code == 404
    assert "Participant profile not found" in resp.json()["detail"]

    # Verify no row was created by the GET request (no side effects)
    with Session(sync_engine) as session:
        prof = session.execute(
            select(ParticipantProfile).where(ParticipantProfile.user_id == user.id)
        ).scalar_one_or_none()
        assert prof is None


def test_get_my_profile_success(client, sync_engine):
    """Verify GET /profile/me successfully returns authenticated user's own profile and interests."""
    user, raw_token = create_user_and_session(sync_engine, "carol_profile", "carol@example.com")

    # Seed profile, hobbies, and topics
    with Session(sync_engine) as session:
        prof = ParticipantProfile(
            user_id=user.id,
            intent=ParticipationIntent.NETWORKING,
            bio_summary="Focusing on calcined clay decarbonization.",
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
        )
        h1 = ParticipantHobby(user_id=user.id, hobby_name="Tea / Coffee")
        h2 = ParticipantHobby(user_id=user.id, hobby_name="Technical Deep-dives")
        t1 = ParticipantTopic(user_id=user.id, topic_keyword="Calcined Clay")
        session.add_all([prof, h1, h2, t1])
        session.commit()

    resp = client.get(
        "/converge-api/v1/profile/me",
        cookies={SESSION_COOKIE_NAME: raw_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(user.id)
    assert data["intent"] == "NETWORKING"
    assert data["availability"] == "AVAILABLE"
    assert data["allow_agent_matching"] is True
    assert data["bio_summary"] == "Focusing on calcined clay decarbonization."
    assert "Tea / Coffee" in data["hobbies"]
    assert "Technical Deep-dives" in data["hobbies"]
    assert "Calcined Clay" in data["topics"]


# ==============================================================================
# 2. Profile Initialization & Update (PUT /profile/me)
# ==============================================================================


def test_put_my_profile_requires_csrf_with_cookie(client, sync_engine):
    """Verify PUT /profile/me rejects state-changing requests missing CSRF custom headers."""
    user, raw_token = create_user_and_session(sync_engine, "csrf_user", "csrf@example.com")

    # Attempt PUT with session cookie but without X-Requested-With or X-CSRF-Token
    resp = client.put(
        "/converge-api/v1/profile/me",
        json={"bio_summary": "Attempting CSRF update"},
        cookies={SESSION_COOKIE_NAME: raw_token},
    )
    assert resp.status_code == 403
    assert "CSRF verification failed" in resp.json()["detail"]


def test_put_my_profile_initialization_with_consent(client, sync_engine):
    """Verify PUT /profile/me creates new profile and honors explicit matching consent."""
    user, raw_token = create_user_and_session(sync_engine, "init_user", "init@example.com")

    headers = {"X-Requested-With": "XMLHttpRequest"}
    payload = {
        "intent": "BOTH",
        "bio_summary": "Lead pyroprocessing engineer.",
        "availability": "AVAILABLE",
        "allow_agent_matching": True,
        "hobbies": ["Tea / Coffee", "Equipment & Exhibition Walking Tours"],
        "topics": ["Kiln Automation", "Alternative Fuels"],
    }

    resp = client.put(
        "/converge-api/v1/profile/me",
        json=payload,
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(user.id)
    assert data["intent"] == "BOTH"
    assert data["bio_summary"] == "Lead pyroprocessing engineer."
    assert data["allow_agent_matching"] is True
    assert len(data["hobbies"]) == 2
    assert len(data["topics"]) == 2

    # Verify audit event emitted
    with Session(sync_engine) as session:
        audit = session.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action_type == "PROFILE_INITIALIZED",
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.event_payload["status"] == "SUCCESS"
        assert "matching=True" in audit.event_payload["details"]


def test_put_my_profile_default_consent_is_false(client, sync_engine):
    """Verify matching consent defaults to False unless explicitly granted (opt-in requirement)."""
    user, raw_token = create_user_and_session(sync_engine, "no_consent_user", "noconsent@example.com")

    headers = {"X-Requested-With": "XMLHttpRequest"}
    # Payload omitting allow_agent_matching
    payload = {
        "intent": "CASUAL",
        "bio_summary": "Attending casually.",
        "availability": "AVAILABLE",
    }

    resp = client.put(
        "/converge-api/v1/profile/me",
        json=payload,
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["allow_agent_matching"] is False


def test_put_my_profile_partial_update(client, sync_engine):
    """Verify PUT /profile/me supports partial updates without wiping omitted fields."""
    user, raw_token = create_user_and_session(sync_engine, "partial_user", "partial@example.com")

    headers = {"X-Requested-With": "XMLHttpRequest"}
    # 1. Initialize full profile
    client.put(
        "/converge-api/v1/profile/me",
        json={
            "intent": "NETWORKING",
            "bio_summary": "Original bio.",
            "availability": "AVAILABLE",
            "allow_agent_matching": True,
            "hobbies": ["Tea / Coffee"],
            "topics": ["Calcined Clay"],
        },
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )

    # 2. Update only availability and bio
    resp = client.put(
        "/converge-api/v1/profile/me",
        json={"availability": "IN_SESSION", "bio_summary": "Updated bio."},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["availability"] == "IN_SESSION"
    assert data["bio_summary"] == "Updated bio."
    # Omitted fields remain preserved
    assert data["intent"] == "NETWORKING"
    assert data["allow_agent_matching"] is True
    assert data["hobbies"] == ["Tea / Coffee"]
    assert data["topics"] == ["Calcined Clay"]


def test_put_my_profile_update_job_title_and_company(client, sync_engine):
    """Verify updating job_title and company_name synchronizes to user and appears in responses."""
    user, raw_token = create_user_and_session(sync_engine, "title_user", "title@example.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    resp = client.put(
        "/converge-api/v1/profile/me",
        json={
            "intent": "NETWORKING",
            "job_title": "Head of Fleet Operations",
            "company_name": "Western Heavy Logistics Ltd",
        },
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_title"] == "Head of Fleet Operations"
    assert data["company_name"] == "Western Heavy Logistics Ltd"

    # Verify GET /profile/me returns these fields
    get_resp = client.get(
        "/converge-api/v1/profile/me",
        cookies={SESSION_COOKIE_NAME: raw_token},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["job_title"] == "Head of Fleet Operations"
    assert get_resp.json()["company_name"] == "Western Heavy Logistics Ltd"


def test_put_my_profile_atomic_tag_replacement(client, sync_engine):
    """Verify updating hobbies/topics atomically replaces the caller's collections."""
    user, raw_token = create_user_and_session(sync_engine, "tags_user", "tags@example.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    # Initial tags
    client.put(
        "/converge-api/v1/profile/me",
        json={"hobbies": ["Tea / Coffee"], "topics": ["Kiln Automation"]},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )

    # Replace tags
    resp = client.put(
        "/converge-api/v1/profile/me",
        json={
            "hobbies": ["Technical Deep-dives", "Casual Conversations"],
            "topics": ["Alternative Fuels", "Hydrogen Co-firing"],
        },
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["hobbies"]) == {"Technical Deep-dives", "Casual Conversations"}
    assert set(data["topics"]) == {"Alternative Fuels", "Hydrogen Co-firing"}

    # Verify old tags were completely removed from database
    with Session(sync_engine) as session:
        h_names = session.execute(
            select(ParticipantHobby.hobby_name).where(ParticipantHobby.user_id == user.id)
        ).scalars().all()
        assert "Tea / Coffee" not in h_names


def test_put_my_profile_case_insensitive_tag_deduplication(client, sync_engine):
    """Verify duplicate tags under case/whitespace variations are deduplicated."""
    user, raw_token = create_user_and_session(sync_engine, "case_user", "case@example.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    resp = client.put(
        "/converge-api/v1/profile/me",
        json={
            "hobbies": ["Tea / Coffee", "  tea / coffee  ", "TEA / COFFEE", "Technical Deep-dives  "],
            "topics": ["Kiln Automation", " kiln automation ", "KILN AUTOMATION"],
        },
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["hobbies"] == ["Tea / Coffee", "Technical Deep-dives"]
    assert data["topics"] == ["Kiln Automation"]


# ==============================================================================
# 3. IDOR Defenses & Mass-Assignment Protection
# ==============================================================================


def test_put_my_profile_mass_assignment_forbidden(client, sync_engine):
    """Verify client cannot inject user_id, email, password_hash, or other ownership fields."""
    user, raw_token = create_user_and_session(sync_engine, "victim_user", "victim@example.com")
    fake_uuid = str(uuid.uuid4())
    headers = {"X-Requested-With": "XMLHttpRequest"}

    # Payload injecting extra/forbidden fields
    payload = {
        "user_id": fake_uuid,
        "email": "hacked@example.com",
        "password_hash": "forged_hash",
        "is_active": False,
        "bio_summary": "Attempting mass assignment.",
    }

    resp = client.put(
        "/converge-api/v1/profile/me",
        json=payload,
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    # Extra fields are strictly forbidden
    assert resp.status_code == 422


def test_idor_cross_user_isolation(client, sync_engine):
    """Verify User A cannot alter User B's profile or tags via any endpoint."""
    user_a, token_a = create_user_and_session(sync_engine, "user_a", "a@example.com")
    user_b, token_b = create_user_and_session(sync_engine, "user_b", "b@example.com")

    headers_a = {"X-Requested-With": "XMLHttpRequest"}
    headers_b = {"X-Requested-With": "XMLHttpRequest"}

    # Initialize User B profile
    client.put(
        "/converge-api/v1/profile/me",
        json={
            "bio_summary": "User B original bio.",
            "intent": "NETWORKING",
            "hobbies": ["Tea / Coffee"],
            "topics": ["Topic B"],
        },
        cookies={SESSION_COOKIE_NAME: token_b},
        headers=headers_b,
    )

    # User A updates their own profile
    client.put(
        "/converge-api/v1/profile/me",
        json={
            "bio_summary": "User A bio.",
            "intent": "CASUAL",
            "hobbies": ["Technical Deep-dives"],
            "topics": ["Topic A"],
        },
        cookies={SESSION_COOKIE_NAME: token_a},
        headers=headers_a,
    )

    # Verify User B profile and tags were not modified
    with Session(sync_engine) as session:
        prof_b = session.execute(
            select(ParticipantProfile).where(ParticipantProfile.user_id == user_b.id)
        ).scalar_one()
        assert prof_b.bio_summary == "User B original bio."
        assert prof_b.intent == ParticipationIntent.NETWORKING

        hobbies_b = session.execute(
            select(ParticipantHobby.hobby_name).where(ParticipantHobby.user_id == user_b.id)
        ).scalars().all()
        assert hobbies_b == ["Tea / Coffee"]


# ==============================================================================
# 4. Public Profile Projection & Privacy Boundary (GET /profile/{id})
# ==============================================================================


def test_get_public_profile_requires_authentication(client, sync_engine):
    """Verify GET /profile/{id} rejects unauthenticated callers with 401."""
    user, _ = create_user_and_session(sync_engine, "target_user", "target@example.com")
    resp = client.get(f"/converge-api/v1/profile/{user.id}")
    assert resp.status_code == 401


def test_get_public_profile_success_and_scrubs_private_fields(client, sync_engine):
    """Verify GET /profile/{id} returns public fields while strictly omitting private contact info (GAP-03, GAP-10)."""
    target_user, _ = create_user_and_session(sync_engine, "target_att", "target@alcon.com")
    viewer_user, viewer_token = create_user_and_session(sync_engine, "viewer_att", "viewer@alcon.com")

    # Seed target's profile
    with Session(sync_engine) as session:
        prof = ParticipantProfile(
            user_id=target_user.id,
            intent=ParticipationIntent.NETWORKING,
            bio_summary="Target attendee public bio.",
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
        )
        h = ParticipantHobby(user_id=target_user.id, hobby_name="Tea / Coffee")
        t = ParticipantTopic(user_id=target_user.id, topic_keyword="Kiln Automation")
        session.add_all([prof, h, t])
        session.commit()

    resp = client.get(
        f"/converge-api/v1/profile/{target_user.id}",
        cookies={SESSION_COOKIE_NAME: viewer_token},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Allowed public fields
    assert data["user_id"] == str(target_user.id)
    assert data["full_name"] == target_user.full_name
    assert data["company_name"] == target_user.company_name
    assert data["job_title"] == target_user.job_title
    assert data["intent"] == "NETWORKING"
    assert data["bio_summary"] == "Target attendee public bio."
    assert data["availability"] == "AVAILABLE"
    assert data["hobbies"] == ["Tea / Coffee"]
    assert data["topics"] == ["Kiln Automation"]

    # Prohibited private fields MUST NOT BE PRESENT
    assert "email" not in data
    assert "phone_number" not in data
    assert "password_hash" not in data
    assert "is_active" not in data
    assert "allow_agent_matching" not in data
    assert "created_at" not in data
    assert "updated_at" not in data


def test_get_public_profile_not_found_uniform_response(client, sync_engine):
    """Verify non-existent or deactivated user returns uniform 404 (enumeration defense)."""
    _, viewer_token = create_user_and_session(sync_engine, "viewer", "viewer@test.com")
    random_uuid = str(uuid.uuid4())

    resp = client.get(
        f"/converge-api/v1/profile/{random_uuid}",
        cookies={SESSION_COOKIE_NAME: viewer_token},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Participant profile not found."


def test_get_public_profile_malformed_uuid_rejected(client, sync_engine):
    """Verify malformed non-UUID parameter returns 422 Unprocessable Entity."""
    _, viewer_token = create_user_and_session(sync_engine, "viewer2", "viewer2@test.com")

    resp = client.get(
        "/converge-api/v1/profile/not-a-valid-uuid",
        cookies={SESSION_COOKIE_NAME: viewer_token},
    )
    assert resp.status_code == 422


# ==============================================================================
# 5. Reference Curated Hobbies Catalog (GET /profile/catalog/hobbies)
# ==============================================================================


def test_get_curated_hobbies_catalog(client):
    """Verify GET /profile/catalog/hobbies returns the curated reference themes."""
    resp = client.get("/converge-api/v1/profile/catalog/hobbies")
    assert resp.status_code == 200
    hobbies = resp.json()
    assert isinstance(hobbies, list)
    assert len(hobbies) == len(CURATED_HOBBIES)
    assert "Tea / Coffee" in hobbies


# ==============================================================================
# 6. Additional Security & Validation Edge Cases (Section 8)
# ==============================================================================


def test_profile_api_expired_session_rejected(client, sync_engine):
    """Verify expired session token is rejected with 401 Unauthorized."""
    user, raw_token = create_user_and_session(sync_engine, "expired_u", "expired@test.com")
    from datetime import datetime, timedelta, timezone

    # Force expiration in database
    with Session(sync_engine) as session:
        session_obj = session.execute(
            select(UserSession).where(UserSession.user_id == user.id)
        ).scalar_one()
        session_obj.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
        session.commit()

    resp = client.get(
        "/converge-api/v1/profile/me",
        cookies={SESSION_COOKIE_NAME: raw_token},
    )
    assert resp.status_code == 401
    assert "Session expired." in resp.json()["detail"]


def test_profile_api_revoked_session_rejected(client, sync_engine):
    """Verify revoked session token is rejected with 401 Unauthorized."""
    user, raw_token = create_user_and_session(sync_engine, "revoked_u", "revoked@test.com")
    from datetime import datetime, timezone

    # Force revocation in database
    with Session(sync_engine) as session:
        session_obj = session.execute(
            select(UserSession).where(UserSession.user_id == user.id)
        ).scalar_one()
        session_obj.revoked_at = datetime.now(timezone.utc)
        session.commit()

    resp = client.get(
        "/converge-api/v1/profile/me",
        cookies={SESSION_COOKIE_NAME: raw_token},
    )
    assert resp.status_code == 401
    assert "Session has been revoked" in resp.json()["detail"]


def test_put_my_profile_bio_too_long_rejected(client, sync_engine):
    """Verify bio exceeding 500 characters is rejected with 422 Unprocessable Entity."""
    user, raw_token = create_user_and_session(sync_engine, "longbio_u", "longbio@test.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    resp = client.put(
        "/converge-api/v1/profile/me",
        json={"bio_summary": "A" * 501},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 422


def test_put_my_profile_invalid_enums_rejected(client, sync_engine):
    """Verify invalid intent or availability enum values return 422."""
    user, raw_token = create_user_and_session(sync_engine, "badenum_u", "badenum@test.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    # Bad intent
    resp1 = client.put(
        "/converge-api/v1/profile/me",
        json={"intent": "INVALID_INTENT"},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp1.status_code == 422

    # Bad availability
    resp2 = client.put(
        "/converge-api/v1/profile/me",
        json={"availability": "VACATION"},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp2.status_code == 422


def test_put_my_profile_collection_limits_rejected(client, sync_engine):
    """Verify hobbies or topics exceeding 20 items return 422."""
    user, raw_token = create_user_and_session(sync_engine, "limits_u", "limits@test.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    resp1 = client.put(
        "/converge-api/v1/profile/me",
        json={"hobbies": [f"hobby_{i}" for i in range(25)]},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp1.status_code == 422

    resp2 = client.put(
        "/converge-api/v1/profile/me",
        json={"topics": [f"topic_{i}" for i in range(25)]},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp2.status_code == 422


def test_put_my_profile_clear_bio(client, sync_engine):
    """Verify passing empty string clears bio to None."""
    user, raw_token = create_user_and_session(sync_engine, "clearbio_u", "clearbio@test.com")
    headers = {"X-Requested-With": "XMLHttpRequest"}

    # Initial bio
    client.put(
        "/converge-api/v1/profile/me",
        json={"bio_summary": "Existing bio."},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )

    # Clear bio
    resp = client.put(
        "/converge-api/v1/profile/me",
        json={"bio_summary": ""},
        cookies={SESSION_COOKIE_NAME: raw_token},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["bio_summary"] is None


def test_full_lifecycle_security_gate(client):
    """End-to-End Security Gate Integration Verification (P2-WS7).
    
    Verifies full lifecycle from registration through login, session validation,
    profile initialization with explicit consent false, public profile projection
    scrubbing, and logout revocation.
    """
    # 1. Health & readiness probes
    res = client.get("/converge-api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res = client.get("/converge-api/v1/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert res.json()["database"] == "connected"

    # 2. Registration with full fields
    unique_username = "gate_test_user_7"
    unique_email = "gate_test_user_7@example.com"
    reg_payload = {
        "username": unique_username,
        "email": unique_email,
        "password": "SecurePassword123!",
        "full_name": "Gate Test Participant",
        "company_name": "Converge Security Labs",
        "job_title": "Security Lead",
        "phone_number": "+91 98765 43210",
    }
    res = client.post("/converge-api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    reg_data = res.json()
    assert reg_data["username"] == unique_username
    assert reg_data["email"] == unique_email
    assert reg_data["full_name"] == "Gate Test Participant"
    assert reg_data["company_name"] == "Converge Security Labs"
    assert reg_data["job_title"] == "Security Lead"
    assert "password_hash" not in reg_data

    # 3. Login & Cookie Issuance
    login_payload = {
        "identifier": unique_username,
        "password": "SecurePassword123!",
    }
    res = client.post("/converge-api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    assert SESSION_COOKIE_NAME in client.cookies

    # 4. Session Validation via /auth/me
    res = client.get("/converge-api/v1/auth/me")
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["username"] == unique_username
    assert user_data["full_name"] == "Gate Test Participant"
    assert user_data["company_name"] == "Converge Security Labs"
    assert user_data["job_title"] == "Security Lead"
    user_id = user_data["id"]

    # 5. Initialize Profile with matching consent explicitly FALSE
    prof_payload = {
        "intent": "NETWORKING",
        "bio_summary": "Automated security gate test bio",
        "availability": "AVAILABLE",
        "allow_agent_matching": False,
        "hobbies": ["Technical Deep-dives", "Tea / Coffee"],
        "topics": ["Decarbonization", "Zero Knowledge"],
    }
    headers = {"X-Requested-With": "XMLHttpRequest"}
    res = client.put("/converge-api/v1/profile/me", json=prof_payload, headers=headers)
    assert res.status_code == 200
    prof_data = res.json()
    assert prof_data["allow_agent_matching"] is False
    assert prof_data["bio_summary"] == "Automated security gate test bio"
    assert len(prof_data["hobbies"]) == 2
    assert len(prof_data["topics"]) == 2

    # 6. Public Profile Projection Security Gate
    res = client.get(f"/converge-api/v1/profile/{user_id}")
    assert res.status_code == 200
    pub_data = res.json()
    assert "email" not in pub_data
    assert "phone_number" not in pub_data
    assert "allow_agent_matching" not in pub_data
    assert "username" not in pub_data
    assert pub_data["full_name"] == "Gate Test Participant"
    assert pub_data["company_name"] == "Converge Security Labs"
    assert pub_data["job_title"] == "Security Lead"
    assert set(pub_data["topics"]) == {"Decarbonization", "Zero Knowledge"}

    # 7. Session Revocation / Logout
    res = client.post("/converge-api/v1/auth/logout", headers=headers)
    assert res.status_code == 200

    # 8. Post-logout /auth/me must return 401
    res = client.get("/converge-api/v1/auth/me")
    assert res.status_code == 401

    # 9. Post-logout /profile/me must return 401
    res = client.get("/converge-api/v1/profile/me")
    assert res.status_code == 401


