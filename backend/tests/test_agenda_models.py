"""Unit and integration tests for Conference Agenda domain models, constraints, and contracts (P3-WS1)."""

import uuid
from datetime import date as dt_date, datetime, timedelta, timezone
import pytest
import psycopg2
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.models.agenda import BookmarkedSession, Conference, Session
from app.db.models.user import User
from app.schemas.agenda import (
    BookmarkResponse,
    ConferenceCreate,
    ConferenceResponse,
    ConferenceUpdate,
    SessionCreate,
    SessionFilter,
    SessionResponse,
    SessionUpdate,
)

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


def get_connection(url: str):
    """Create raw psycopg2 connection."""
    clean_url = url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(clean_url)


@pytest.fixture(scope="module")
def sync_engine():
    """Create synchronous SQLAlchemy engine connected to test database."""
    assert "test" in TEST_MIGRATION_URL.lower(), (
        f"SAFETY GUARD: Refusing to run tests against non-test DB: {TEST_MIGRATION_URL}"
    )
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sync_engine):
    """Provide isolated transactional session for testing."""
    with SASession(sync_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up agenda and user records before and after each test."""
    def _clean():
        conn = get_connection(TEST_MIGRATION_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DELETE FROM agenda.bookmarked_sessions;")
            cur.execute("DELETE FROM agenda.sessions;")
            cur.execute("DELETE FROM agenda.conferences;")
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


def create_test_user(db_session: SASession, username: str = "agenda_tester") -> User:
    """Helper to create a test participant in isolated DB."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        username=f"{username}_{uid.hex[:8]}",
        email=f"{username}_{uid.hex[:8]}@example.com",
        password_hash=hash_password("ValidPassword123!"),
        full_name="Agenda Test User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# =============================================================================
# 1. Conference Model Tests
# =============================================================================

def test_conference_creation_and_repr(db_session: SASession):
    """Verify Conference creation with valid attributes and truthful representation."""
    conf = Conference(
        title="Converge AI Summit 2026",
        description="Annual conference on autonomous agent networks.",
        venue_name="Grand Hyatt Convention Center",
        timezone="Asia/Kolkata",
        start_date=dt_date(2026, 11, 10),
        end_date=dt_date(2026, 11, 12),
        is_active=True,
    )
    db_session.add(conf)
    db_session.commit()
    db_session.refresh(conf)

    assert conf.id is not None
    assert conf.title == "Converge AI Summit 2026"
    assert conf.timezone == "Asia/Kolkata"
    assert "Converge AI Summit 2026" in repr(conf)
    assert "Asia/Kolkata" in repr(conf)


def test_conference_date_ordering_constraint(db_session: SASession):
    """Verify check constraint rejects end_date preceding start_date."""
    conf = Conference(
        title="Invalid Date Summit",
        venue_name="Main Hall",
        timezone="UTC",
        start_date=dt_date(2026, 11, 15),
        end_date=dt_date(2026, 11, 10),  # Precedes start_date
    )
    db_session.add(conf)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    assert "ck_conference_dates" in str(exc_info.value).lower()


def test_conference_nonempty_constraints(db_session: SASession):
    """Verify check constraints reject empty or whitespace-only conference fields."""
    # Empty title
    conf = Conference(
        title="   ",
        venue_name="Valid Venue",
        timezone="UTC",
        start_date=dt_date(2026, 11, 10),
        end_date=dt_date(2026, 11, 12),
    )
    db_session.add(conf)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Empty venue
    conf = Conference(
        title="Valid Title",
        venue_name="   ",
        timezone="UTC",
        start_date=dt_date(2026, 11, 10),
        end_date=dt_date(2026, 11, 12),
    )
    db_session.add(conf)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Empty timezone
    conf = Conference(
        title="Valid Title",
        venue_name="Valid Venue",
        timezone="   ",
        start_date=dt_date(2026, 11, 10),
        end_date=dt_date(2026, 11, 12),
    )
    db_session.add(conf)
    with pytest.raises(IntegrityError):
        db_session.commit()


# =============================================================================
# 2. Session Model & Constraint Tests (GAP-09)
# =============================================================================

def test_session_creation_and_repr(db_session: SASession):
    """Verify Session creation with valid attributes, FK association, and repr."""
    conf = Conference(
        title="AI Engineering Expo",
        venue_name="Expo Center",
        timezone="UTC",
        start_date=dt_date(2026, 12, 1),
        end_date=dt_date(2026, 12, 2),
    )
    db_session.add(conf)
    db_session.commit()

    start_dt = datetime(2026, 12, 1, 9, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
    sess = Session(
        conference_id=conf.id,
        title="Opening Keynote: Agentic Protocols",
        abstract="Deep dive into A2A communication standards.",
        speaker_names="Dr. Alice Smith, Bob Jones",
        track_name="Keynotes",
        hall_room="Auditorium A",
        start_time=start_dt,
        end_time=end_dt,
        import_batch_id="batch-20261201-01",
    )
    db_session.add(sess)
    db_session.commit()
    db_session.refresh(sess)

    assert sess.id is not None
    assert sess.conference_id == conf.id
    assert sess.title == "Opening Keynote: Agentic Protocols"
    assert sess.is_cancelled is False
    assert "Opening Keynote" in repr(sess)
    assert "Auditorium A" in repr(sess)


def test_session_time_ordering_constraint(db_session: SASession):
    """Verify check constraint ck_session_times rejects end_time <= start_time."""
    conf = Conference(
        title="Time Check Summit",
        venue_name="Hall B",
        timezone="UTC",
        start_date=dt_date(2026, 12, 1),
        end_date=dt_date(2026, 12, 2),
    )
    db_session.add(conf)
    db_session.commit()

    now = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
    # end_time equals start_time
    sess = Session(
        conference_id=conf.id,
        title="Zero Duration Session",
        hall_room="Room 101",
        start_time=now,
        end_time=now,
    )
    db_session.add(sess)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    assert "ck_session_times" in str(exc_info.value).lower()
    db_session.rollback()

    # end_time before start_time
    sess_rev = Session(
        conference_id=conf.id,
        title="Backwards Session",
        hall_room="Room 101",
        start_time=now,
        end_time=now - timedelta(minutes=30),
    )
    db_session.add(sess_rev)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    assert "ck_session_times" in str(exc_info.value).lower()


def test_session_room_conflict_defense_gap09(db_session: SASession):
    """Verify GAP-09: two sessions cannot occupy the same room at the same start time."""
    conf = Conference(
        title="Conflict Check Summit",
        venue_name="Tech Hall",
        timezone="UTC",
        start_date=dt_date(2026, 12, 1),
        end_date=dt_date(2026, 12, 2),
    )
    db_session.add(conf)
    db_session.commit()

    start_dt = datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc)
    sess1 = Session(
        conference_id=conf.id,
        title="First Scheduled Session",
        hall_room="Track Hall 1",
        start_time=start_dt,
        end_time=start_dt + timedelta(hours=1),
    )
    db_session.add(sess1)
    db_session.commit()

    # Same conference, same room, same start_time -> must be rejected
    sess2 = Session(
        conference_id=conf.id,
        title="Conflicting Session",
        hall_room="Track Hall 1",
        start_time=start_dt,
        end_time=start_dt + timedelta(hours=1, minutes=30),
    )
    db_session.add(sess2)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    assert "uq_session_room_starttime" in str(exc_info.value).lower()
    db_session.rollback()

    # Same start_time in DIFFERENT room -> must succeed
    sess_diff_room = Session(
        conference_id=conf.id,
        title="Concurrent Session in Other Room",
        hall_room="Track Hall 2",
        start_time=start_dt,
        end_time=start_dt + timedelta(hours=1),
    )
    db_session.add(sess_diff_room)
    db_session.commit()
    assert sess_diff_room.id is not None


# =============================================================================
# 3. Relationships & Cascade Deletion Tests (GAP-10)
# =============================================================================

def test_conference_cascade_deletes_sessions(db_session: SASession):
    """Verify deleting a conference cascades and removes all scheduled sessions."""
    conf = Conference(
        title="Temporary Summit",
        venue_name="Temp Venue",
        timezone="UTC",
        start_date=dt_date(2026, 12, 1),
        end_date=dt_date(2026, 12, 2),
    )
    db_session.add(conf)
    db_session.commit()

    start_dt = datetime(2026, 12, 1, 14, 0, tzinfo=timezone.utc)
    sess = Session(
        conference_id=conf.id,
        title="Ephemeral Session",
        hall_room="Room E",
        start_time=start_dt,
        end_time=start_dt + timedelta(hours=1),
    )
    db_session.add(sess)
    db_session.commit()
    sess_id = sess.id

    # Delete conference
    db_session.delete(conf)
    db_session.commit()

    # Verify session was cascaded
    found_sess = db_session.get(Session, sess_id)
    assert found_sess is None


def test_bookmark_creation_and_cascade_on_session_delete(sync_engine):
    """Verify bookmarked sessions link user and session, and cascade on session deletion."""
    with SASession(sync_engine) as session1:
        user = create_test_user(session1, "bookmarker_1")
        conf = Conference(
            title="Bookmark Summit",
            venue_name="Center Hall",
            timezone="UTC",
            start_date=dt_date(2026, 12, 1),
            end_date=dt_date(2026, 12, 2),
        )
        session1.add(conf)
        session1.commit()

        start_dt = datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc)
        sess = Session(
            conference_id=conf.id,
            title="Highly Anticipated Talk",
            hall_room="Main Hall",
            start_time=start_dt,
            end_time=start_dt + timedelta(minutes=45),
        )
        session1.add(sess)
        session1.commit()

        # Create bookmark
        bm = BookmarkedSession(user_id=user.id, session_id=sess.id)
        session1.add(bm)
        session1.commit()

        user_id = user.id
        sess_id = sess.id

    # Separate session for duplicate bookmark attempt -> PK violation
    with SASession(sync_engine) as session2:
        bm_dup = BookmarkedSession(user_id=user_id, session_id=sess_id)
        session2.add(bm_dup)
        with pytest.raises(IntegrityError):
            session2.commit()

    # Separate session: Delete session -> bookmark cascades
    with SASession(sync_engine) as session3:
        sess_to_delete = session3.get(Session, sess_id)
        session3.delete(sess_to_delete)
        session3.commit()

        found_bm = session3.get(BookmarkedSession, (user_id, sess_id))
        assert found_bm is None


def test_bookmark_cascade_on_user_delete_gap10(db_session: SASession):
    """Verify GAP-10: deleting a user cascades and purges their session bookmarks."""
    user = create_test_user(db_session, "bookmarker_2")
    conf = Conference(
        title="User Cascade Summit",
        venue_name="Hall C",
        timezone="UTC",
        start_date=dt_date(2026, 12, 1),
        end_date=dt_date(2026, 12, 2),
    )
    db_session.add(conf)
    db_session.commit()

    start_dt = datetime(2026, 12, 1, 16, 0, tzinfo=timezone.utc)
    sess = Session(
        conference_id=conf.id,
        title="Track Session",
        hall_room="Room 303",
        start_time=start_dt,
        end_time=start_dt + timedelta(hours=1),
    )
    db_session.add(sess)
    db_session.commit()

    bm = BookmarkedSession(user_id=user.id, session_id=sess.id)
    db_session.add(bm)
    db_session.commit()

    # Delete user -> bookmark purged
    db_session.delete(user)
    db_session.commit()

    found_bm = db_session.get(BookmarkedSession, (user.id, sess.id))
    assert found_bm is None

    # The session itself must remain intact
    found_sess = db_session.get(Session, sess.id)
    assert found_sess is not None


# =============================================================================
# 4. Runtime Application Role Table Privileges (GAP-02)
# =============================================================================

def test_runtime_role_table_permissions_on_agenda():
    """Verify runtime role converge_ai_app can perform DML on agenda tables."""
    conn = psycopg2.connect(TEST_DB_URL.replace("postgresql+asyncpg://", "postgresql://"))
    with conn.cursor() as cur:
        # 1. Insert conference
        cur.execute("""
            INSERT INTO agenda.conferences (title, venue_name, timezone, start_date, end_date)
            VALUES ('App Role Conf', 'Venue App', 'UTC', '2026-12-01', '2026-12-02')
            RETURNING id;
        """)
        conf_id = cur.fetchone()[0]

        # 2. Select conference
        cur.execute("SELECT title, timezone FROM agenda.conferences WHERE id = %s;", (conf_id,))
        row = cur.fetchone()
        assert row[0] == "App Role Conf"
        assert row[1] == "UTC"

        # 3. Insert session
        cur.execute("""
            INSERT INTO agenda.sessions (conference_id, title, hall_room, start_time, end_time)
            VALUES (%s, 'App Role Session', 'Hall 1', '2026-12-01 10:00:00+00', '2026-12-01 11:00:00+00')
            RETURNING id;
        """, (conf_id,))
        sess_id = cur.fetchone()[0]

        # 4. Update session
        cur.execute(
            "UPDATE agenda.sessions SET title = 'Updated Title' WHERE id = %s;",
            (sess_id,),
        )
        assert cur.rowcount == 1

        # 5. Delete session and conference
        cur.execute("DELETE FROM agenda.sessions WHERE id = %s;", (sess_id,))
        assert cur.rowcount == 1
        cur.execute("DELETE FROM agenda.conferences WHERE id = %s;", (conf_id,))
        assert cur.rowcount == 1

    conn.rollback()
    conn.close()


# =============================================================================
# 5. Pydantic DTO Contract Validation Tests
# =============================================================================

def test_conference_dto_validation():
    """Verify ConferenceCreate DTO enforces IANA timezones and date bounds."""
    # Valid DTO
    dto = ConferenceCreate(
        title="Valid Summit",
        venue_name="Valid Hall",
        timezone="America/New_York",
        start_date=dt_date(2026, 11, 1),
        end_date=dt_date(2026, 11, 3),
    )
    assert dto.timezone == "America/New_York"

    # Invalid IANA timezone
    with pytest.raises(ValueError, match="Invalid IANA timezone identifier"):
        ConferenceCreate(
            title="Bad Timezone Summit",
            venue_name="Hall",
            timezone="Fake/Timezone_Not_Real",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
        )

    # Invalid date order
    with pytest.raises(ValueError, match="end_date must be greater than or equal to start_date"):
        ConferenceCreate(
            title="Inverted Date Summit",
            venue_name="Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 5),
            end_date=dt_date(2026, 11, 1),
        )

    # Empty string rejection
    with pytest.raises(ValueError, match="Field must be a non-empty string"):
        ConferenceCreate(
            title="   ",
            venue_name="Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
        )

    # Extra fields forbidden
    with pytest.raises(ValueError):
        ConferenceCreate(
            title="Extra Field Summit",
            venue_name="Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
            unauthorized_field="malicious",
        )


def test_session_dto_validation():
    """Verify SessionCreate DTO enforces time ordering and non-empty fields."""
    conf_id = uuid.uuid4()
    start_dt = datetime(2026, 12, 1, 9, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)

    # Valid DTO
    dto = SessionCreate(
        conference_id=conf_id,
        title="Agent Architectures",
        hall_room="Hall Alpha",
        start_time=start_dt,
        end_time=end_dt,
        track_name="Core AI",
    )
    assert dto.title == "Agent Architectures"

    # Invalid time ordering: end_time <= start_time
    with pytest.raises(ValueError, match="end_time must strictly follow start_time"):
        SessionCreate(
            conference_id=conf_id,
            title="Zero Duration",
            hall_room="Hall Alpha",
            start_time=start_dt,
            end_time=start_dt,
        )

    # Empty string rejection
    with pytest.raises(ValueError, match="Field must be a non-empty string"):
        SessionCreate(
            conference_id=conf_id,
            title="Valid Title",
            hall_room="   ",
            start_time=start_dt,
            end_time=end_dt,
        )

    # Extra fields forbidden
    with pytest.raises(ValueError):
        SessionCreate(
            conference_id=conf_id,
            title="Extra Field Session",
            hall_room="Hall Alpha",
            start_time=start_dt,
            end_time=end_dt,
            injected_role="admin",
        )


def test_session_filter_dto():
    """Verify SessionFilter DTO accepts valid query filters and forbids extra attributes."""
    conf_id = uuid.uuid4()
    flt = SessionFilter(
        conference_id=conf_id,
        track_name="AI Systems",
        hall_room="Room 1",
        date=dt_date(2026, 12, 1),
        is_cancelled=False,
    )
    assert flt.track_name == "AI Systems"

    # Extra filter parameters rejected
    with pytest.raises(ValueError):
        SessionFilter(unrecognized_filter="exploit")


def test_dto_serialization_from_orm():
    """Verify ConferenceResponse and SessionResponse serialize cleanly from ORM entities."""
    conf_id = uuid.uuid4()
    sess_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    conf_obj = Conference(
        id=conf_id,
        title="Serialization Summit",
        venue_name="Grand Hall",
        timezone="Europe/London",
        start_date=dt_date(2026, 11, 1),
        end_date=dt_date(2026, 11, 3),
        is_active=True,
        format="IN_PERSON",
        status="PUBLISHED",
        created_at=now,
        updated_at=now,
    )
    conf_resp = ConferenceResponse.model_validate(conf_obj)
    assert conf_resp.id == conf_id
    assert conf_resp.timezone == "Europe/London"

    sess_obj = Session(
        id=sess_id,
        conference_id=conf_id,
        title="Serialization Session",
        hall_room="Room A",
        start_time=now,
        end_time=now + timedelta(hours=1),
        is_cancelled=False,
        created_at=now,
        updated_at=now,
    )
    sess_resp = SessionResponse.model_validate(sess_obj)
    assert sess_resp.id == sess_id
    assert sess_resp.conference_id == conf_id
    assert sess_resp.title == "Serialization Session"
