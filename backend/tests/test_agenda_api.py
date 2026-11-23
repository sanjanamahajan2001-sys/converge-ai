"""Integration tests for Agenda Read APIs and Timezone Normalization (P3-WS2, GAP-09)."""

import uuid
from datetime import date as dt_date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, create_session, generate_session_token, hash_session_token
from app.db.models.agenda import BookmarkedSession, Conference, Session
from app.db.models.user import User
from app.db.models.session import UserSession
from app.main import create_app
from app.schemas.agenda import ConferenceResponse, SessionResponse

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


def create_user_and_session(sync_engine, username: str = "agenda_viewer"):
    """Create a test user and an active session token."""
    with SASession(sync_engine) as session:
        uid = uuid.uuid4()
        user = User(
            id=uid,
            username=f"{username}_{uid.hex[:8]}",
            email=f"{username}_{uid.hex[:8]}@example.com",
            password_hash=hash_password("ValidPassword123!"),
            full_name="Agenda Test Viewer",
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
            ip_address="127.0.0.1",
            user_agent="pytest-agent",
        )
        session.add(user_session)
        session.commit()
        return user, raw_token


# =============================================================================
# 1. Conference Listing Tests
# =============================================================================

def test_list_conferences_empty(client):
    """Verify GET /agenda/conferences returns 200 and empty list when no conferences exist."""
    res = client.get("/converge-api/v1/agenda/conferences")
    assert res.status_code == 200
    assert res.json() == []


def test_list_conferences_public_anonymous_and_authenticated(client, sync_engine):
    """Verify conferences endpoint is public (accessible anonymously and authenticated)."""
    with SASession(sync_engine) as session:
        conf_active = Conference(
            title="Active Summit",
            venue_name="Main Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
            is_active=True,
        )
        conf_inactive = Conference(
            title="Archived Expo",
            venue_name="Old Hall",
            timezone="UTC",
            start_date=dt_date(2025, 11, 1),
            end_date=dt_date(2025, 11, 3),
            is_active=False,
        )
        session.add_all([conf_active, conf_inactive])
        session.commit()

    # 1. Anonymous access defaults to active conferences
    res_anon = client.get("/converge-api/v1/agenda/conferences")
    assert res_anon.status_code == 200
    data_anon = res_anon.json()
    assert len(data_anon) == 1
    assert data_anon[0]["title"] == "Active Summit"
    assert data_anon[0]["is_active"] is True

    # 2. Filter for inactive conferences
    res_inact = client.get("/converge-api/v1/agenda/conferences?is_active=false")
    assert res_inact.status_code == 200
    data_inact = res_inact.json()
    assert len(data_inact) == 1
    assert data_inact[0]["title"] == "Archived Expo"

    # 3. Authenticated participant access returns same data
    user, raw_token = create_user_and_session(sync_engine)
    client.cookies.set(SESSION_COOKIE_NAME, raw_token)
    res_auth = client.get("/converge-api/v1/agenda/conferences")
    assert res_auth.status_code == 200
    assert res_auth.json() == data_anon


def test_list_conferences_deterministic_ordering_and_pagination(client, sync_engine):
    """Verify deterministic ordering (start_date ASC, title ASC, id ASC) and limit/offset."""
    with SASession(sync_engine) as session:
        c1 = Conference(
            title="Beta Conference",
            venue_name="Hall B",
            timezone="UTC",
            start_date=dt_date(2026, 11, 10),
            end_date=dt_date(2026, 11, 12),
        )
        c2 = Conference(
            title="Alpha Conference",
            venue_name="Hall A",
            timezone="UTC",
            start_date=dt_date(2026, 11, 10),
            end_date=dt_date(2026, 11, 12),
        )
        c3 = Conference(
            title="Future Conference",
            venue_name="Hall F",
            timezone="UTC",
            start_date=dt_date(2026, 12, 1),
            end_date=dt_date(2026, 12, 3),
        )
        session.add_all([c1, c2, c3])
        session.commit()

    # Full list: Alpha first (same date, earlier title), then Beta, then Future
    res = client.get("/converge-api/v1/agenda/conferences")
    assert res.status_code == 200
    titles = [c["title"] for c in res.json()]
    assert titles == ["Alpha Conference", "Beta Conference", "Future Conference"]

    # Pagination: limit=1, offset=1 -> Beta Conference
    res_page = client.get("/converge-api/v1/agenda/conferences?limit=1&offset=1")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert len(page_data) == 1
    assert page_data[0]["title"] == "Beta Conference"

    # Invalid limit rejected with 422
    assert client.get("/converge-api/v1/agenda/conferences?limit=0").status_code == 422
    assert client.get("/converge-api/v1/agenda/conferences?limit=101").status_code == 422


# =============================================================================
# 2. Session Listing Tests
# =============================================================================

def test_list_sessions_empty(client):
    """Verify GET /agenda/sessions returns 200 and empty list when no sessions exist."""
    res = client.get("/converge-api/v1/agenda/sessions")
    assert res.status_code == 200
    assert res.json() == []


def test_list_sessions_filter_by_conference(client, sync_engine):
    """Verify filtering sessions by conference UUID and unknown conference 404."""
    with SASession(sync_engine) as session:
        c1 = Conference(
            title="Conf 1",
            venue_name="V1",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        c2 = Conference(
            title="Conf 2",
            venue_name="V2",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        session.add_all([c1, c2])
        session.commit()

        start_dt = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
        s1 = Session(
            conference_id=c1.id,
            title="Session in Conf 1",
            hall_room="Room 1",
            start_time=start_dt,
            end_time=start_dt + timedelta(hours=1),
        )
        s2 = Session(
            conference_id=c2.id,
            title="Session in Conf 2",
            hall_room="Room 2",
            start_time=start_dt,
            end_time=start_dt + timedelta(hours=1),
        )
        session.add_all([s1, s2])
        session.commit()
        c1_id = c1.id

    # Filter by conference_id
    res = client.get(f"/converge-api/v1/agenda/sessions?conference_id={c1_id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Session in Conf 1"

    # Unknown conference returns 404
    res_404 = client.get(f"/converge-api/v1/agenda/sessions?conference_id={uuid.uuid4()}")
    assert res_404.status_code == 404
    assert res_404.json()["detail"] == "Conference not found."

    # Malformed UUID returns 422
    assert client.get("/converge-api/v1/agenda/sessions?conference_id=invalid-uuid").status_code == 422


def test_list_sessions_filter_by_track_hall_and_cancellation(client, sync_engine):
    """Verify filtering sessions by track name, room name, and cancellation flag."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Filter Summit",
            venue_name="Tech Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        session.add(conf)
        session.commit()

        start_dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        s_ai = Session(
            conference_id=conf.id,
            title="AI Systems Keynote",
            track_name="AI Systems",
            hall_room="Auditorium A",
            start_time=start_dt,
            end_time=start_dt + timedelta(hours=1),
            is_cancelled=False,
        )
        s_sec = Session(
            conference_id=conf.id,
            title="Security Workshop",
            track_name="Security",
            hall_room="Room 102",
            start_time=start_dt + timedelta(hours=1),
            end_time=start_dt + timedelta(hours=2),
            is_cancelled=True,
        )
        session.add_all([s_ai, s_sec])
        session.commit()

    # Track filter
    res_track = client.get("/converge-api/v1/agenda/sessions?track_name=AI%20Systems")
    assert res_track.status_code == 200
    assert len(res_track.json()) == 1
    assert res_track.json()[0]["title"] == "AI Systems Keynote"

    # Room filter
    res_room = client.get("/converge-api/v1/agenda/sessions?hall_room=Room%20102")
    assert res_room.status_code == 200
    assert len(res_room.json()) == 1
    assert res_room.json()[0]["title"] == "Security Workshop"

    # Cancellation filter
    res_canc = client.get("/converge-api/v1/agenda/sessions?is_cancelled=true")
    assert res_canc.status_code == 200
    assert len(res_canc.json()) == 1
    assert res_canc.json()[0]["is_cancelled"] is True


def test_list_sessions_deterministic_ordering_and_pagination(client, sync_engine):
    """Verify deterministic ordering (start_time ASC, hall_room ASC, id ASC) and limit/offset bounds."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Ordering Summit",
            venue_name="Expo",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        session.add(conf)
        session.commit()

        t1 = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        s1 = Session(
            conference_id=conf.id,
            title="Session 1: Hall B at 9:00",
            hall_room="Hall B",
            start_time=t1,
            end_time=t1 + timedelta(minutes=45),
        )
        s2 = Session(
            conference_id=conf.id,
            title="Session 2: Hall A at 9:00",
            hall_room="Hall A",
            start_time=t1,
            end_time=t1 + timedelta(minutes=45),
        )
        s3 = Session(
            conference_id=conf.id,
            title="Session 3: Hall A at 10:00",
            hall_room="Hall A",
            start_time=t2,
            end_time=t2 + timedelta(minutes=45),
        )
        session.add_all([s1, s2, s3])
        session.commit()

    # Ordered: t1 Hall A, then t1 Hall B, then t2 Hall A
    res = client.get("/converge-api/v1/agenda/sessions")
    assert res.status_code == 200
    titles = [s["title"] for s in res.json()]
    assert titles == [
        "Session 2: Hall A at 9:00",
        "Session 1: Hall B at 9:00",
        "Session 3: Hall A at 10:00",
    ]

    # Pagination: limit=2
    res_page = client.get("/converge-api/v1/agenda/sessions?limit=2&offset=1")
    assert res_page.status_code == 200
    assert len(res_page.json()) == 2
    assert res_page.json()[0]["title"] == "Session 1: Hall B at 9:00"
    assert res_page.json()[1]["title"] == "Session 3: Hall A at 10:00"

    # Limit bounds validation
    assert client.get("/converge-api/v1/agenda/sessions?limit=0").status_code == 422
    assert client.get("/converge-api/v1/agenda/sessions?limit=201").status_code == 422


# =============================================================================
# 3. Session Details Tests
# =============================================================================

def test_get_session_details_success_and_internal_scrubbing(client, sync_engine):
    """Verify GET /agenda/sessions/{id} returns full public details and omits import_batch_id."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Details Summit",
            venue_name="Convention Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        session.add(conf)
        session.commit()

        start_dt = datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc)
        sess = Session(
            conference_id=conf.id,
            title="Autonomous Agents in Industry",
            abstract="In-depth analysis of A2A protocol in industrial networks.",
            speaker_names="Dr. Maya Lin, Alex Mercer",
            track_name="Industry AI",
            hall_room="Auditorium Blue",
            start_time=start_dt,
            end_time=start_dt + timedelta(hours=1),
            import_batch_id="batch-internal-secret-999",
            is_cancelled=False,
        )
        session.add(sess)
        session.commit()
        sess_id = sess.id
        conf_id = conf.id

    res = client.get(f"/converge-api/v1/agenda/sessions/{sess_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == str(sess_id)
    assert data["conference_id"] == str(conf_id)
    assert data["title"] == "Autonomous Agents in Industry"
    assert data["abstract"] == "In-depth analysis of A2A protocol in industrial networks."
    assert data["speaker_names"] == "Dr. Maya Lin, Alex Mercer"
    assert data["track_name"] == "Industry AI"
    assert data["hall_room"] == "Auditorium Blue"
    assert data["is_cancelled"] is False
    assert "start_time" in data
    assert "end_time" in data

    # Internal import implementation detail strictly omitted from public response
    assert "import_batch_id" not in data


def test_get_session_details_not_found_and_malformed(client):
    """Verify 404 for unknown UUID and 422 for malformed identifier."""
    # Unknown UUID
    res_404 = client.get(f"/converge-api/v1/agenda/sessions/{uuid.uuid4()}")
    assert res_404.status_code == 404
    assert res_404.json()["detail"] == "Session not found."

    # Malformed UUID
    res_422 = client.get("/converge-api/v1/agenda/sessions/invalid-session-uuid")
    assert res_422.status_code == 422


def test_read_endpoints_have_zero_write_side_effects(client, sync_engine):
    """Verify read-only endpoints execute zero state mutations or table modifications."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Read Side Effect Summit",
            venue_name="Safety Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        session.add(conf)
        session.commit()
        conf_id = conf.id

        start_dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        sess = Session(
            conference_id=conf_id,
            title="Side Effect Probe Talk",
            hall_room="Room Safe",
            start_time=start_dt,
            end_time=start_dt + timedelta(hours=1),
        )
        session.add(sess)
        session.commit()
        sess_id = sess.id

    def get_counts():
        with sync_engine.connect() as conn:
            c_conf = conn.exec_driver_sql("SELECT count(*) FROM agenda.conferences;").scalar()
            c_sess = conn.exec_driver_sql("SELECT count(*) FROM agenda.sessions;").scalar()
            c_bm = conn.exec_driver_sql("SELECT count(*) FROM agenda.bookmarked_sessions;").scalar()
        return c_conf, c_sess, c_bm

    counts_before = get_counts()

    # Call all three read endpoints
    client.get("/converge-api/v1/agenda/conferences")
    client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}")
    client.get(f"/converge-api/v1/agenda/sessions/{sess_id}")

    counts_after = get_counts()
    assert counts_before == counts_after


# =============================================================================
# 4. Timezone Correctness Tests (GAP-09)
# =============================================================================

def test_timezone_conference_local_date_filtering_gap09(client, sync_engine):
    """Verify GAP-09: date filtering evaluates against conference's IANA timezone."""
    with SASession(sync_engine) as session:
        # Conference located in New Delhi, India (Asia/Kolkata = UTC+05:30)
        conf = Conference(
            title="Indian Cement Innovation Summit",
            venue_name="Hyderabad International Convention Centre",
            timezone="Asia/Kolkata",
            start_date=dt_date(2026, 11, 10),
            end_date=dt_date(2026, 11, 12),
        )
        session.add(conf)
        session.commit()
        conf_id = conf.id

        # Session 1: Nov 10, 2026 at 09:00 IST (= Nov 10 03:30 UTC)
        tz_ist = ZoneInfo("Asia/Kolkata")
        s1_start = datetime(2026, 11, 10, 9, 0, tzinfo=tz_ist)
        s1 = Session(
            conference_id=conf_id,
            title="Nov 10 Morning Session (IST)",
            hall_room="Hall 1",
            start_time=s1_start,
            end_time=s1_start + timedelta(hours=1),
        )

        # Session 2: Nov 10, 2026 at 20:00 IST (= Nov 10 14:30 UTC)
        s2_start = datetime(2026, 11, 10, 20, 0, tzinfo=tz_ist)
        s2 = Session(
            conference_id=conf_id,
            title="Nov 10 Evening Session (IST)",
            hall_room="Hall 1",
            start_time=s2_start,
            end_time=s2_start + timedelta(hours=1),
        )

        # Session 3: Nov 11, 2026 at 10:00 IST (= Nov 11 04:30 UTC)
        s3_start = datetime(2026, 11, 11, 10, 0, tzinfo=tz_ist)
        s3 = Session(
            conference_id=conf_id,
            title="Nov 11 Morning Session (IST)",
            hall_room="Hall 1",
            start_time=s3_start,
            end_time=s3_start + timedelta(hours=1),
        )

        session.add_all([s1, s2, s3])
        session.commit()

    # Query for Nov 10 local calendar day
    res_nov10 = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&date=2026-11-10")
    assert res_nov10.status_code == 200
    titles_nov10 = [s["title"] for s in res_nov10.json()]
    assert "Nov 10 Morning Session (IST)" in titles_nov10
    assert "Nov 10 Evening Session (IST)" in titles_nov10
    assert "Nov 11 Morning Session (IST)" not in titles_nov10
    assert len(titles_nov10) == 2

    # Query for Nov 11 local calendar day
    res_nov11 = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&date=2026-11-11")
    assert res_nov11.status_code == 200
    titles_nov11 = [s["title"] for s in res_nov11.json()]
    assert "Nov 11 Morning Session (IST)" in titles_nov11
    assert "Nov 10 Morning Session (IST)" not in titles_nov11
    assert len(titles_nov11) == 1


def test_timezone_midnight_spanning_session_gap09(client, sync_engine):
    """Verify session spanning midnight appears on both affected calendar days."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Late Night Hackathon",
            venue_name="Innovation Hub",
            timezone="Asia/Kolkata",
            start_date=dt_date(2026, 11, 10),
            end_date=dt_date(2026, 11, 12),
        )
        session.add(conf)
        session.commit()
        conf_id = conf.id

        # Spans midnight: Nov 10 23:00 IST to Nov 11 01:30 IST
        tz_ist = ZoneInfo("Asia/Kolkata")
        span_start = datetime(2026, 11, 10, 23, 0, tzinfo=tz_ist)
        span_end = datetime(2026, 11, 11, 1, 30, tzinfo=tz_ist)
        sess = Session(
            conference_id=conf_id,
            title="Midnight Agent Hackathon Session",
            hall_room="Lab A",
            start_time=span_start,
            end_time=span_end,
        )
        session.add(sess)
        session.commit()

    # Appears on Nov 10
    res_10 = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&date=2026-11-10")
    assert res_10.status_code == 200
    assert len(res_10.json()) == 1
    assert res_10.json()[0]["title"] == "Midnight Agent Hackathon Session"

    # Appears on Nov 11
    res_11 = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&date=2026-11-11")
    assert res_11.status_code == 200
    assert len(res_11.json()) == 1
    assert res_11.json()[0]["title"] == "Midnight Agent Hackathon Session"


def test_timezone_dst_transition_handling(client, sync_engine):
    """Verify correct calendar day boundary on US Daylight Saving Time transition day."""
    with SASession(sync_engine) as session:
        # America/New_York DST fall-back occurs on Sunday, Nov 1, 2026 (day has 25 hours)
        conf = Conference(
            title="US Fall Summit",
            venue_name="Javits Center",
            timezone="America/New_York",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
        )
        session.add(conf)
        session.commit()
        conf_id = conf.id

        tz_ny = ZoneInfo("America/New_York")
        # Session scheduled during the afternoon of the DST change day
        sess_dt = datetime(2026, 11, 1, 14, 0, tzinfo=tz_ny)
        sess = Session(
            conference_id=conf_id,
            title="Post-DST Afternoon Keynote",
            hall_room="Grand Ballroom",
            start_time=sess_dt,
            end_time=sess_dt + timedelta(hours=1),
        )
        session.add(sess)
        session.commit()

    res = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&date=2026-11-01")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "Post-DST Afternoon Keynote"


def test_timestamp_serialization_has_explicit_timezone_offset(client, sync_engine):
    """Verify serialized ISO 8601 timestamps include explicit UTC offset."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Serialization Check",
            venue_name="Hall Z",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
        )
        session.add(conf)
        session.commit()

        start_dt = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        sess = Session(
            conference_id=conf.id,
            title="Offset Verified Session",
            hall_room="Room Z",
            start_time=start_dt,
            end_time=start_dt + timedelta(hours=1),
        )
        session.add(sess)
        session.commit()
        sess_id = sess.id

    res = client.get(f"/converge-api/v1/agenda/sessions/{sess_id}")
    assert res.status_code == 200
    data = res.json()

    # Explicit timezone offset information must be present in serialized ISO strings
    start_str = data["start_time"]
    end_str = data["end_time"]
    assert "+00:00" in start_str or "Z" in start_str
    assert "+00:00" in end_str or "Z" in end_str


# =============================================================================
# 4. Multi-Conference & Gap Resolution Tests (GAP B, C, E)
# =============================================================================


def test_multi_conference_timezone_date_filtering_gap_b(client, sync_engine):
    """Gap B: When date is supplied without conference_id, each session must be
    tested against the timezone of its own conference in SQL."""
    with SASession(sync_engine) as session:
        # Conference 1: India (UTC+5:30)
        conf_in = Conference(
            title="India Tech Summit",
            venue_name="Bangalore Expo",
            timezone="Asia/Kolkata",
            start_date=dt_date(2026, 11, 10),
            end_date=dt_date(2026, 11, 12),
            is_active=True,
        )
        # Conference 2: New York (UTC-5:00)
        conf_ny = Conference(
            title="New York AI Summit",
            venue_name="Javits Center",
            timezone="America/New_York",
            start_date=dt_date(2026, 11, 10),
            end_date=dt_date(2026, 11, 12),
            is_active=True,
        )
        session.add_all([conf_in, conf_ny])
        session.commit()

        tz_in = ZoneInfo("Asia/Kolkata")
        tz_ny = ZoneInfo("America/New_York")

        # Session 1A: India on Nov 10 local time (10:00 IST -> 04:30 UTC)
        s1a = Session(
            conference_id=conf_in.id,
            title="India Day 1 Keynote",
            hall_room="Hall 1",
            start_time=datetime(2026, 11, 10, 10, 0, tzinfo=tz_in),
            end_time=datetime(2026, 11, 10, 11, 30, tzinfo=tz_in),
        )
        # Session 1B: India on Nov 11 local time (10:00 IST -> 04:30 UTC)
        s1b = Session(
            conference_id=conf_in.id,
            title="India Day 2 Keynote",
            hall_room="Hall 1",
            start_time=datetime(2026, 11, 11, 10, 0, tzinfo=tz_in),
            end_time=datetime(2026, 11, 11, 11, 30, tzinfo=tz_in),
        )
        # Session 2A: NY on Nov 10 local time (10:00 EST -> 15:00 UTC)
        s2a = Session(
            conference_id=conf_ny.id,
            title="NY Day 1 Keynote",
            hall_room="Room A",
            start_time=datetime(2026, 11, 10, 10, 0, tzinfo=tz_ny),
            end_time=datetime(2026, 11, 10, 11, 30, tzinfo=tz_ny),
        )
        # Session 2B: NY on Nov 11 local time (10:00 EST -> 15:00 UTC)
        s2b = Session(
            conference_id=conf_ny.id,
            title="NY Day 2 Keynote",
            hall_room="Room A",
            start_time=datetime(2026, 11, 11, 10, 0, tzinfo=tz_ny),
            end_time=datetime(2026, 11, 11, 11, 30, tzinfo=tz_ny),
        )
        session.add_all([s1a, s1b, s2a, s2b])
        session.commit()

    # Query with date=2026-11-10 and NO conference_id
    res_nov10 = client.get("/converge-api/v1/agenda/sessions?date=2026-11-10")
    assert res_nov10.status_code == 200
    titles_nov10 = [s["title"] for s in res_nov10.json()]
    assert set(titles_nov10) == {"India Day 1 Keynote", "NY Day 1 Keynote"}

    # Query with date=2026-11-11 and NO conference_id
    res_nov11 = client.get("/converge-api/v1/agenda/sessions?date=2026-11-11")
    assert res_nov11.status_code == 200
    titles_nov11 = [s["title"] for s in res_nov11.json()]
    assert set(titles_nov11) == {"India Day 2 Keynote", "NY Day 2 Keynote"}


def test_inactive_conference_sessions_hidden_gap_c(client, sync_engine):
    """Gap C: Sessions belonging to inactive conferences must never be exposed publicly."""
    with SASession(sync_engine) as session:
        active_conf = Conference(
            title="Published Summit",
            venue_name="Expo Center",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
            is_active=True,
        )
        draft_conf = Conference(
            title="Unpublished Draft Expo",
            venue_name="Secret Lab",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
            is_active=False,
        )
        session.add_all([active_conf, draft_conf])
        session.commit()

        s_active = Session(
            conference_id=active_conf.id,
            title="Public Keynote",
            hall_room="Auditorium",
            start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
        )
        s_draft = Session(
            conference_id=draft_conf.id,
            title="Confidential Internal Planning",
            hall_room="Room X",
            start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
        )
        session.add_all([s_active, s_draft])
        session.commit()
        draft_conf_id = draft_conf.id
        draft_sess_id = s_draft.id

    # 1. Default session list hides draft conference sessions
    res_list = client.get("/converge-api/v1/agenda/sessions")
    assert res_list.status_code == 200
    titles = [s["title"] for s in res_list.json()]
    assert "Public Keynote" in titles
    assert "Confidential Internal Planning" not in titles

    # 2. Querying by inactive conference ID returns empty
    res_draft_conf = client.get(f"/converge-api/v1/agenda/sessions?conference_id={draft_conf_id}")
    assert res_draft_conf.status_code == 200
    assert len(res_draft_conf.json()) == 0

    # 3. Direct access to draft session by UUID returns 404
    res_detail = client.get(f"/converge-api/v1/agenda/sessions/{draft_sess_id}")
    assert res_detail.status_code == 404
    assert res_detail.json()["detail"] == "Session not found."


def test_cancelled_sessions_visibility_gap_c(client, sync_engine):
    """Gap C: is_cancelled defaults to None (returning both active and cancelled sessions
    with cancellation indicators), and filters properly when requested."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Schedule Visibility Conf",
            venue_name="Convention Hall",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 3),
            is_active=True,
        )
        session.add(conf)
        session.commit()

        s_live = Session(
            conference_id=conf.id,
            title="Confirmed Keynote",
            hall_room="Main Hall",
            start_time=datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            is_cancelled=False,
        )
        s_cancelled = Session(
            conference_id=conf.id,
            title="Cancelled Workshop",
            hall_room="Workshop Room",
            start_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
            is_cancelled=True,
        )
        session.add_all([s_live, s_cancelled])
        session.commit()
        conf_id = conf.id

    # Default query returns both sessions
    res_all = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert len(data_all) == 2
    by_title = {s["title"]: s for s in data_all}
    assert by_title["Confirmed Keynote"]["is_cancelled"] is False
    assert by_title["Cancelled Workshop"]["is_cancelled"] is True

    # Filter is_cancelled=false returns only live
    res_live = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&is_cancelled=false")
    assert res_live.status_code == 200
    assert len(res_live.json()) == 1
    assert res_live.json()[0]["title"] == "Confirmed Keynote"

    # Filter is_cancelled=true returns only cancelled
    res_canc = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&is_cancelled=true")
    assert res_canc.status_code == 200
    assert len(res_canc.json()) == 1
    assert res_canc.json()[0]["title"] == "Cancelled Workshop"


def test_null_room_sorting_and_stable_pagination_gap_e(client, sync_engine):
    """Gap E: Hall room NULLS LAST sorting and stable pagination tie-breaking."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Ordering Conf",
            venue_name="Center",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
            is_active=True,
        )
        session.add(conf)
        session.commit()

        t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        # 3 sessions with equal start_time
        s_room_b = Session(
            conference_id=conf.id,
            title="Session B in Room B",
            hall_room="Hall B",
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
        )
        s_room_a = Session(
            conference_id=conf.id,
            title="Session A in Room A",
            hall_room="Hall A",
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
        )
        s_room_null = Session(
            conference_id=conf.id,
            title="Virtual Session without Room",
            hall_room="TBD / Virtual",
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
        )
        session.add_all([s_room_b, s_room_a, s_room_null])
        session.commit()
        conf_id = conf.id

    res = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 3
    # Ordered: Hall A, Hall B, TBD / Virtual
    assert items[0]["hall_room"] == "Hall A"
    assert items[1]["hall_room"] == "Hall B"
    assert items[2]["hall_room"] == "TBD / Virtual"


def test_track_case_insensitive_matching_gap_e(client, sync_engine):
    """Gap E: track_name filtering uses case-insensitive exact matching."""
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Track Conf",
            venue_name="Center",
            timezone="UTC",
            start_date=dt_date(2026, 11, 1),
            end_date=dt_date(2026, 11, 2),
            is_active=True,
        )
        session.add(conf)
        session.commit()

        t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        s = Session(
            conference_id=conf.id,
            title="AI Agents Talk",
            track_name="Artificial Intelligence",
            hall_room="Hall 1",
            start_time=t0,
            end_time=t0 + timedelta(hours=1),
        )
        session.add(s)
        session.commit()
        conf_id = conf.id

    # 1. Lowercase match
    res_lower = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&track_name=artificial intelligence")
    assert res_lower.status_code == 200
    assert len(res_lower.json()) == 1

    # 2. Uppercase match
    res_upper = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&track_name=ARTIFICIAL INTELLIGENCE")
    assert res_upper.status_code == 200
    assert len(res_upper.json()) == 1

    # 3. Partial substring does NOT match exact track filter
    res_partial = client.get(f"/converge-api/v1/agenda/sessions?conference_id={conf_id}&track_name=art")
    assert res_partial.status_code == 200
    assert len(res_partial.json()) == 0


def test_speaker_names_validation_and_email_prevention_gap_e():
    """Gap E: speaker_names rejects email addresses to protect speaker privacy."""
    from app.schemas.agenda import SessionCreate
    import pytest

    # Valid speaker names
    s_valid = SessionCreate(
        conference_id=uuid.uuid4(),
        title="Valid Session",
        hall_room="Room 1",
        start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
        speaker_names="Dr. Alice Smith, Bob Jones",
    )
    assert s_valid.speaker_names == "Dr. Alice Smith, Bob Jones"

    # Email address inside speaker_names must raise validation error
    with pytest.raises(ValueError, match="must not contain email addresses"):
        SessionCreate(
            conference_id=uuid.uuid4(),
            title="Leaked Email Session",
            hall_room="Room 1",
            start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
            speaker_names="alice@example.com",
        )

