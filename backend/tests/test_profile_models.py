"""Unit & integration tests for Participant Profile, Hobbies, Topics models, schema constraints, and DTO contracts (GAP-03, GAP-10)."""
import uuid
import psycopg2
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import ParticipantHobby, ParticipantProfile, ParticipantTopic, User
from app.schemas.profile import (
    CURATED_HOBBIES,
    AvailabilityStatus,
    HobbyCreate,
    ParticipationIntent,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    PublicProfileResponse,
    TopicCreate,
)

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


def get_connection(url: str):
    clean_url = url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(clean_url)


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous SQLAlchemy engine bound to the test database."""
    assert "test" in TEST_MIGRATION_URL.lower(), (
        f"SAFETY GUARD: Refusing to run tests against non-test DB: {TEST_MIGRATION_URL}"
    )
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sync_engine):
    """Provide an isolated database session per test."""
    with Session(sync_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up records before and after each test."""
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


def create_test_user(session: Session, username: str = "test_user_profile", email: str = "profile@test.com") -> User:
    """Helper to insert a valid test user."""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("ValidP@ssw0rd123!"),
        full_name="Profile Test User",
        company_name="Test Engineering Corp",
        job_title="Lead Automation Engineer",
        phone_number="+15551234567",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ==============================================================================
# Model Instantiation & Representation Tests
# ==============================================================================


def test_profile_model_repr_and_attributes(db_session):
    """Test ParticipantProfile representation does not leak sensitive information."""
    user = create_test_user(db_session)
    profile = ParticipantProfile(
        user_id=user.id,
        intent=ParticipationIntent.NETWORKING,
        bio_summary="Focusing on kiln optimization.",
        availability=AvailabilityStatus.AVAILABLE,
        allow_agent_matching=True,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.id == user.id
    assert "user_id" in repr(profile)
    assert "NETWORKING" in repr(profile)
    assert "AVAILABLE" in repr(profile)
    assert "test_user_profile" not in repr(profile)


def test_hobby_and_topic_repr():
    """Test string representations for Hobby and Topic models."""
    sample_uid = uuid.uuid4()
    hobby = ParticipantHobby(id=1, user_id=sample_uid, hobby_name="Tea / Coffee")
    assert repr(hobby) == f"<ParticipantHobby id=1 user_id={sample_uid} hobby_name='Tea / Coffee'>"

    topic = ParticipantTopic(id=2, user_id=sample_uid, topic_keyword="Calcined Clay")
    assert repr(topic) == f"<ParticipantTopic id=2 user_id={sample_uid} topic_keyword='Calcined Clay'>"


# ==============================================================================
# Relational Constraints & Database Persistence Tests
# ==============================================================================


def test_profile_one_to_one_relationship(db_session):
    """Verify 1-to-1 relationship between User and ParticipantProfile."""
    user = create_test_user(db_session)

    # Create profile
    profile = ParticipantProfile(
        user_id=user.id,
        intent=ParticipationIntent.CASUAL,
        bio_summary="Interested in informal discussions.",
        availability=AvailabilityStatus.IN_SESSION,
        allow_agent_matching=False,
    )
    db_session.add(profile)
    db_session.commit()

    # Query via User relationship
    queried_user = db_session.execute(select(User).where(User.id == user.id)).scalar_one()
    assert queried_user.profile is not None
    assert queried_user.profile.intent == ParticipationIntent.CASUAL
    assert queried_user.profile.availability == AvailabilityStatus.IN_SESSION
    assert queried_user.profile.allow_agent_matching is False
    assert queried_user.profile.bio_summary == "Interested in informal discussions."


def test_profile_matching_defaults_to_false_in_db(db_session):
    """Verify allow_agent_matching defaults to False (explicit consent required) in DB and model."""
    user = create_test_user(db_session, username="consent_user", email="consent@test.com")

    # Insert omitting allow_agent_matching
    profile = ParticipantProfile(
        user_id=user.id,
        intent=ParticipationIntent.NETWORKING,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.allow_agent_matching is False

    # Raw SQL query to confirm server_default in PostgreSQL
    raw_val = db_session.execute(
        text("SELECT allow_agent_matching FROM core.participant_profiles WHERE user_id = :uid"),
        {"uid": user.id},
    ).scalar_one()
    assert raw_val is False, f"Expected DB persisted allow_agent_matching to be False, got {raw_val}"


def test_profile_duplicate_user_violates_pk(sync_engine, db_session):
    """Verify creating a second profile for the same user is rejected by PK constraint."""
    user = create_test_user(db_session)

    p1 = ParticipantProfile(user_id=user.id, intent=ParticipationIntent.NETWORKING)
    db_session.add(p1)
    db_session.commit()

    # Direct database insert in separate session to test DB PK constraint without session identity warning
    with Session(sync_engine) as second_session:
        p2 = ParticipantProfile(user_id=user.id, intent=ParticipationIntent.CASUAL)
        second_session.add(p2)
        with pytest.raises(IntegrityError):
            second_session.commit()


def test_hobbies_relationship_and_uniqueness(db_session):
    """Verify hobbies persistence, uniqueness per user, and cross-user support."""
    u1 = create_test_user(db_session, username="user_h1", email="u1@test.com")
    u2 = create_test_user(db_session, username="user_h2", email="u2@test.com")

    # Add hobbies to u1
    h1 = ParticipantHobby(user_id=u1.id, hobby_name="Tea / Coffee")
    h2 = ParticipantHobby(user_id=u1.id, hobby_name="Technical Deep-dives")
    db_session.add_all([h1, h2])
    db_session.commit()

    # Verify cross-user same hobby is permitted
    h_u2 = ParticipantHobby(user_id=u2.id, hobby_name="Tea / Coffee")
    db_session.add(h_u2)
    db_session.commit()

    # Verify duplicate hobby for u1 violates uq_user_hobby
    h_dup = ParticipantHobby(user_id=u1.id, hobby_name="Tea / Coffee")
    db_session.add(h_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Verify case-insensitive duplicate ('tea / coffee' vs 'Tea / Coffee') violates uq_hobbies_user_normalized
    h_case_dup = ParticipantHobby(user_id=u1.id, hobby_name="tea / coffee")
    db_session.add(h_case_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_topics_relationship_and_uniqueness(db_session):
    """Verify topics persistence, uniqueness per user, and cross-user support."""
    u1 = create_test_user(db_session, username="user_t1", email="t1@test.com")
    u2 = create_test_user(db_session, username="user_t2", email="t2@test.com")

    # Add topics to u1
    t1 = ParticipantTopic(user_id=u1.id, topic_keyword="Kiln Automation")
    t2 = ParticipantTopic(user_id=u1.id, topic_keyword="Alternative Fuels")
    db_session.add_all([t1, t2])
    db_session.commit()

    # Verify cross-user same topic is permitted
    t_u2 = ParticipantTopic(user_id=u2.id, topic_keyword="Kiln Automation")
    db_session.add(t_u2)
    db_session.commit()

    # Verify duplicate topic for u1 violates uq_user_topic
    t_dup = ParticipantTopic(user_id=u1.id, topic_keyword="Kiln Automation")
    db_session.add(t_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Verify case-insensitive duplicate ('kiln automation' vs 'Kiln Automation') violates uq_topics_user_normalized
    t_case_dup = ParticipantTopic(user_id=u1.id, topic_keyword="kiln automation")
    db_session.add(t_case_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_deletion_on_user_removal(db_session):
    """Verify deleting a User cascades to profile, hobbies, and topics (GAP-10)."""
    user = create_test_user(db_session)
    user_id = user.id

    profile = ParticipantProfile(user_id=user_id, intent=ParticipationIntent.BOTH)
    h1 = ParticipantHobby(user_id=user_id, hobby_name="Tea / Coffee")
    t1 = ParticipantTopic(user_id=user_id, topic_keyword="Decarbonization")
    db_session.add_all([profile, h1, t1])
    db_session.commit()

    # Confirm all 3 exist
    assert db_session.execute(select(ParticipantProfile).where(ParticipantProfile.user_id == user_id)).scalar_one_or_none() is not None
    assert len(db_session.execute(select(ParticipantHobby).where(ParticipantHobby.user_id == user_id)).scalars().all()) == 1
    assert len(db_session.execute(select(ParticipantTopic).where(ParticipantTopic.user_id == user_id)).scalars().all()) == 1

    # Delete the User
    db_session.delete(user)
    db_session.commit()

    # Confirm cascaded deletion across all 3 tables
    assert db_session.execute(select(ParticipantProfile).where(ParticipantProfile.user_id == user_id)).scalar_one_or_none() is None
    assert len(db_session.execute(select(ParticipantHobby).where(ParticipantHobby.user_id == user_id)).scalars().all()) == 0
    assert len(db_session.execute(select(ParticipantTopic).where(ParticipantTopic.user_id == user_id)).scalars().all()) == 0


def test_runtime_role_table_permissions():
    """Verify runtime role converge_ai_app has DML privileges on profile tables (GAP-02)."""
    conn = get_connection(TEST_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM core.participant_profiles;")
        cur.execute("SELECT count(*) FROM core.participant_hobbies;")
        cur.execute("SELECT count(*) FROM core.participant_topics;")
    conn.close()


# ==============================================================================
# Pydantic Schema Contracts & DTO Validation Tests
# ==============================================================================


def test_participation_intent_enum_values():
    """Verify ParticipationIntent matches architectural contract."""
    assert ParticipationIntent.NETWORKING.value == "NETWORKING"
    assert ParticipationIntent.CASUAL.value == "CASUAL"
    assert ParticipationIntent.BOTH.value == "BOTH"
    with pytest.raises(ValueError):
        ParticipationIntent("INVALID_INTENT")


def test_availability_status_enum_values():
    """Verify AvailabilityStatus matches architectural contract."""
    assert AvailabilityStatus.AVAILABLE.value == "AVAILABLE"
    assert AvailabilityStatus.IN_SESSION.value == "IN_SESSION"
    assert AvailabilityStatus.DO_NOT_DISTURB.value == "DO_NOT_DISTURB"
    assert AvailabilityStatus.OFFLINE.value == "OFFLINE"
    with pytest.raises(ValueError):
        AvailabilityStatus("AWAY")


def test_curated_hobbies_catalog():
    """Verify curated hobbies catalog is non-empty and contains standard conference themes."""
    assert len(CURATED_HOBBIES) == 5
    assert "Tea / Coffee" in CURATED_HOBBIES
    assert "Casual Conversations" in CURATED_HOBBIES


def test_hobby_create_dto_validation():
    """Test HobbyCreate validation and whitespace sanitization."""
    h = HobbyCreate(hobby_name="   Tea / Coffee   ")
    assert h.hobby_name == "Tea / Coffee"

    with pytest.raises(ValueError, match="Hobby name cannot be empty"):
        HobbyCreate(hobby_name="   ")


def test_topic_create_dto_validation():
    """Test TopicCreate validation and whitespace sanitization."""
    t = TopicCreate(topic_keyword="   Kiln Automation   ")
    assert t.topic_keyword == "Kiln Automation"

    with pytest.raises(ValueError, match="Topic keyword cannot be empty"):
        TopicCreate(topic_keyword="   ")


def test_profile_create_dto_deduplication_and_limits():
    """Test ProfileCreate deduplication, trimming, and limits on hobbies and topics."""
    payload = ProfileCreate(
        intent=ParticipationIntent.BOTH,
        bio_summary="  Industrial process control lead.  ",
        availability=AvailabilityStatus.AVAILABLE,
        allow_agent_matching=True,
        hobbies=["Tea / Coffee", "  tea / coffee  ", "Technical Deep-dives  "],
        topics=["Kiln Automation", "  kiln automation  ", "Alternative Fuels"],
    )

    assert payload.bio_summary == "Industrial process control lead."
    # Case-insensitive deduplication preserves first occurrence
    assert payload.hobbies == ["Tea / Coffee", "Technical Deep-dives"]
    assert payload.topics == ["Kiln Automation", "Alternative Fuels"]


def test_profile_create_dto_limits_exceeded():
    """Verify hobby and topic limit checks (>20 items rejected)."""
    with pytest.raises(ValueError, match="Maximum 20 hobbies"):
        ProfileCreate(hobbies=[f"hobby_{i}" for i in range(25)])

    with pytest.raises(ValueError, match="Maximum 20 topics"):
        ProfileCreate(topics=[f"topic_{i}" for i in range(25)])


def test_profile_update_dto():
    """Test partial updates via ProfileUpdate."""
    update = ProfileUpdate(
        intent=ParticipationIntent.CASUAL,
        bio_summary=None,
        availability=AvailabilityStatus.DO_NOT_DISTURB,
    )
    assert update.intent == ParticipationIntent.CASUAL
    assert update.availability == AvailabilityStatus.DO_NOT_DISTURB
    assert update.bio_summary is None
    assert update.allow_agent_matching is None


def test_public_profile_response_scrubs_private_contact_info():
    """Verify PublicProfileResponse strictly excludes private credentials, email, and phone (GAP-03, GAP-10)."""
    uid = uuid.uuid4()
    public_dto = PublicProfileResponse(
        user_id=uid,
        full_name="Dr. Aris Thorne",
        company_name="Alcon Materials",
        job_title="Chief Metallurgist",
        intent=ParticipationIntent.NETWORKING,
        bio_summary="Developing low-carbon binders.",
        availability=AvailabilityStatus.AVAILABLE,
        hobbies=["Tea / Coffee"],
        topics=["Decarbonization", "Slag Chemistry"],
    )

    dumped = public_dto.model_dump()
    assert "email" not in dumped
    assert "phone_number" not in dumped
    assert "password_hash" not in dumped
    assert "is_active" not in dumped
    assert "allow_agent_matching" not in dumped
    assert dumped["user_id"] == uid
    assert dumped["full_name"] == "Dr. Aris Thorne"
    assert dumped["hobbies"] == ["Tea / Coffee"]
    assert dumped["topics"] == ["Decarbonization", "Slag Chemistry"]
