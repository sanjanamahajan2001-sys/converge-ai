"""Unit and integration tests for Admin Authentication and Dashboard Foundation (Phase 2)."""
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.session import (
    CSRF_EXPECTED_VALUE,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models import User, UserSession
from app.db.models.business import BusinessOffering, BusinessProfile, BusinessRequirement
from app.db.models.agenda import Conference, ConferenceFormat, ConferenceStatus, Session as DbConferenceSession
from app.db.models.organizer import OrganizerProfile, OrganizerType, OrganizerVerificationStatus
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    assert "test" in TEST_DB_URL.lower(), f"SAFETY GUARD: Non-test DB: {TEST_DB_URL}"
    test_settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DB_URL,
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="TestAdminSecret123!",
    )
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def test_users(sync_engine):
    """Seed test admin and regular non-admin user."""
    admin_id = uuid.uuid4()
    regular_id = uuid.uuid4()

    admin_pwd_hash = bcrypt.hashpw(b"TestAdminSecret123!", bcrypt.gensalt(12)).decode("utf-8")
    regular_pwd_hash = bcrypt.hashpw(b"RegularPass123!", bcrypt.gensalt(12)).decode("utf-8")

    with Session(sync_engine) as session:
        # Cleanup
        session.query(UserSession).filter(
            UserSession.user_id.in_([admin_id, regular_id])
        ).delete(synchronize_session=False)
        session.query(User).filter(
            User.username.in_(["admin_test_user", "regular_test_user"])
        ).delete(synchronize_session=False)
        session.commit()

        admin_user = User(
            id=admin_id,
            username="admin_test_user",
            email="admin_test@converge.ai",
            password_hash=admin_pwd_hash,
            full_name="Admin Test",
            is_active=True,
            is_admin=True,
        )
        regular_user = User(
            id=regular_id,
            username="regular_test_user",
            email="regular_test@converge.ai",
            password_hash=regular_pwd_hash,
            full_name="Regular Attendee",
            is_active=True,
            is_admin=False,
        )
        session.add(admin_user)
        session.add(regular_user)
        session.commit()

    yield {"admin_id": admin_id, "regular_id": regular_id}

    with Session(sync_engine) as session:
        session.query(UserSession).filter(
            UserSession.user_id.in_([admin_id, regular_id])
        ).delete(synchronize_session=False)
        session.query(User).filter(
            User.username.in_(["admin_test_user", "regular_test_user"])
        ).delete(synchronize_session=False)
        session.commit()


def create_test_session(sync_engine, user_id: uuid.UUID) -> str:
    """Helper to create session token in DB."""
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)
    with Session(sync_engine) as session:
        db_sess = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            last_accessed_at=now,
            expires_at=now + timedelta(hours=24),
            revoked_at=None,
        )
        session.add(db_sess)
        session.commit()
    return raw_token


def test_admin_login_success(client, test_users):
    """Admin credentials successfully authenticate and receive session."""
    resp = client.post(
        "/converge-api/v1/admin/auth/login",
        json={"identifier": "admin_test_user", "password": "TestAdminSecret123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "authenticated"
    assert data["username"] == "admin_test_user"
    assert SESSION_COOKIE_NAME in resp.cookies


def test_admin_login_rejects_regular_user_with_403(client, test_users):
    """Regular attendees attempting to login at admin endpoint are strictly rejected with 403 Forbidden."""
    resp = client.post(
        "/converge-api/v1/admin/auth/login",
        json={"identifier": "regular_test_user", "password": "RegularPass123!"},
    )
    assert resp.status_code == 403
    assert "administrative privileges" in resp.json()["detail"].lower()


def test_admin_login_invalid_password(client, test_users):
    """Invalid password returns 401."""
    resp = client.post(
        "/converge-api/v1/admin/auth/login",
        json={"identifier": "admin_test_user", "password": "WrongPassword999!"},
    )
    assert resp.status_code == 401


def test_admin_get_me_authorized(client, sync_engine, test_users):
    """Admin calling /admin/auth/me receives admin profile."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    resp = client.get("/converge-api/v1/admin/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin_test_user"
    assert data["is_admin"] is True


def test_admin_get_me_rejected_for_regular_user(client, sync_engine, test_users):
    """Regular user session calling /admin/auth/me receives 403 Forbidden."""
    token = create_test_session(sync_engine, test_users["regular_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    resp = client.get("/converge-api/v1/admin/auth/me")
    assert resp.status_code == 403
    assert "Administrative privilege required" in resp.json()["detail"]


def test_admin_overview_metrics(client, sync_engine, test_users):
    """Admin can fetch platform overview metrics."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    resp = client.get("/converge-api/v1/admin/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_users" in data
    assert "profile_completion_pct" in data
    assert "active_users_today" in data
    assert "total_conversations" in data


def test_admin_overview_unauthenticated_rejected(client):
    """Unauthenticated access to /admin/overview receives 401."""
    client.cookies.clear()
    resp = client.get("/converge-api/v1/admin/overview")
    assert resp.status_code == 401


def test_admin_logout_revokes_session(client, sync_engine, test_users):
    """Admin logout revokes session and clears cookie."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    resp = client.post(
        "/converge-api/v1/admin/auth/logout",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out"

    # Subsequent request with old token should fail
    resp2 = client.get("/converge-api/v1/admin/auth/me")
    assert resp2.status_code == 401


def test_admin_users_list_authorized(client, sync_engine, test_users):
    """Admin can fetch paginated users list with directory statistics."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    resp = client.get("/converge-api/v1/admin/users?page=1&limit=10")
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data
    assert "stats" in data

    assert data["page"] == 1
    assert data["limit"] == 10
    assert data["total"] >= 2
    assert "total_users" in data["stats"]
    assert "active_users" in data["stats"]

    # Verify user summary items schema
    item = next((u for u in data["items"] if u["id"] == str(test_users["admin_id"])), None)
    assert item is not None
    assert item["username"] == "admin_test_user"
    assert item["is_admin"] is True
    assert "bookmarks_count" in item
    assert "attendance_count" in item
    assert "conversations_count" in item


def test_admin_users_list_forbidden_for_regular_user(client, sync_engine, test_users):
    """Non-admin user receives 403 Forbidden when accessing users directory."""
    token = create_test_session(sync_engine, test_users["regular_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    resp = client.get("/converge-api/v1/admin/users")
    assert resp.status_code == 403
    assert "Administrative privilege required" in resp.json()["detail"]


def test_admin_users_search_and_filters(client, sync_engine, test_users):
    """Search query matches username and filters by status."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    # Search by unique username
    resp = client.get("/converge-api/v1/admin/users?search=regular_test_user")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "regular_test_user"

    # Filter by admin status
    resp_admin = client.get("/converge-api/v1/admin/users?status=admin")
    assert resp_admin.status_code == 200
    admin_items = resp_admin.json()["items"]
    assert all(item["is_admin"] is True for item in admin_items)


def test_admin_get_user_detail_success(client, sync_engine, test_users):
    """Admin can fetch comprehensive user footprint (Phase 4)."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    target_id = test_users["regular_id"]
    resp = client.get(f"/converge-api/v1/admin/users/{target_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert "account" in data
    assert data["account"]["id"] == str(target_id)
    assert data["account"]["username"] == "regular_test_user"
    assert data["account"]["email"] == "regular_test@converge.ai"

    assert "profile" in data
    assert "sessions" in data
    assert "agenda" in data
    assert "conversations" in data
    assert "activity" in data
    assert "business_profile" in data
    assert data["business_profile"] is None


def test_admin_get_user_detail_with_business_profile(client, sync_engine, test_users):
    """Admin receives rich business profile, catalog offerings, and procurement requirements."""
    admin_token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, admin_token)

    commercial_user_id = uuid.uuid4()
    rand_suffix = uuid.uuid4().hex[:6]
    bp_id = uuid.uuid4()
    offering_id = uuid.uuid4()
    req_id = uuid.uuid4()

    with Session(sync_engine) as session:
        u = User(
            id=commercial_user_id,
            username=f"decarb_user_{rand_suffix}",
            email=f"decarb_{rand_suffix}@materials.com",
            password_hash=bcrypt.hashpw(b"SecretPass123!", bcrypt.gensalt(12)).decode("utf-8"),
            full_name="Decarb Producer",
            company_name="Green Materials Ltd",
            is_active=True,
            is_admin=False,
        )
        bp = BusinessProfile(
            id=bp_id,
            user_id=commercial_user_id,
            is_supplier=True,
            is_buyer=True,
            allow_business_matching=True,
            company_name="Green Materials Ltd",
            industry="Green Building Materials",
            hq_city="Pune",
            hq_country="India",
        )
        offering = BusinessOffering(
            id=offering_id,
            business_profile_id=bp_id,
            custom_product_title="Limestone Calcined Clay Cement (LC3)",
            product_code=None,
            capacity_unit="METRIC TONNE",
            declared_monthly_capacity=2500,
            lead_time_days=7,
            geographic_coverage=["Pune", "Mumbai"],
            offers_test_certificates=True,
            indicative_price_min=4900,
            indicative_price_max=5100,
            price_currency="INR",
            pricing_basis="EX_WORKS",
            is_active=True,
        )
        req = BusinessRequirement(
            id=req_id,
            business_profile_id=bp_id,
            custom_requirement_title="Raw Calcined Clay Feedstock",
            required_quantity=500,
            quantity_unit="METRIC TONNE",
            delivery_city="Pune",
            target_timeline_days=30,
            is_active=True,
        )
        session.add(u)
        session.flush()
        session.add(bp)
        session.flush()
        session.add(offering)
        session.add(req)
        session.commit()

    resp = client.get(f"/converge-api/v1/admin/users/{commercial_user_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["business_profile"] is not None
    bp_data = data["business_profile"]
    assert bp_data["company_name"] == "Green Materials Ltd"
    assert bp_data["is_supplier"] is True
    assert bp_data["is_buyer"] is True
    assert len(bp_data["offerings"]) == 1
    assert bp_data["offerings"][0]["custom_product_title"] == "Limestone Calcined Clay Cement (LC3)"
    assert bp_data["offerings"][0]["lead_time_days"] == 7
    assert len(bp_data["requirements"]) == 1
    assert bp_data["requirements"][0]["custom_requirement_title"] == "Raw Calcined Clay Feedstock"

    # Also verify directory summary attributes
    dir_resp = client.get(f"/converge-api/v1/admin/users?search=decarb_user_{rand_suffix}")
    assert dir_resp.status_code == 200
    dir_items = dir_resp.json()["items"]
    assert len(dir_items) == 1
    assert dir_items[0]["has_business_profile"] is True
    assert "SUPPLIER" in dir_items[0]["commercial_roles"]
    assert "BUYER" in dir_items[0]["commercial_roles"]
    assert dir_items[0]["offerings_count"] == 1
    assert dir_items[0]["requirements_count"] == 1


def test_admin_get_user_detail_not_found(client, sync_engine, test_users):
    """Admin receives 404 for nonexistent user ID."""
    token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, token)

    fake_id = uuid.uuid4()
    resp = client.get(f"/converge-api/v1/admin/users/{fake_id}")
    assert resp.status_code == 404


def test_admin_update_user_status_deactivate_and_revoke_sessions(client, sync_engine, test_users):
    """Admin deactivates attendee, revoking active sessions immediately."""
    admin_token = create_test_session(sync_engine, test_users["admin_id"])
    regular_token = create_test_session(sync_engine, test_users["regular_id"])

    # 1. Verify regular user is initially active
    client.cookies.set(SESSION_COOKIE_NAME, regular_token)
    me_resp = client.get("/converge-api/v1/auth/me")
    assert me_resp.status_code == 200

    # 2. Admin deactivates regular user
    client.cookies.set(SESSION_COOKIE_NAME, admin_token)
    patch_resp = client.patch(
        f"/converge-api/v1/admin/users/{test_users['regular_id']}/status",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"is_active": False, "reason": "Violation of community standards"},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["is_active"] is False
    assert patch_data["revoked_sessions_count"] >= 1

    # 3. Regular user's existing session token should now be rejected with 401
    client.cookies.set(SESSION_COOKIE_NAME, regular_token)
    me_after = client.get("/converge-api/v1/auth/me")
    assert me_after.status_code == 401

    # 4. Reactivate user for future tests
    client.cookies.set(SESSION_COOKIE_NAME, admin_token)
    reactivate_resp = client.patch(
        f"/converge-api/v1/admin/users/{test_users['regular_id']}/status",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"is_active": True, "reason": "Account restored"},
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["is_active"] is True


def test_admin_update_user_status_prevent_self_deactivation(client, sync_engine, test_users):
    """Admin cannot deactivate own administrative account."""
    admin_token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, admin_token)

    patch_resp = client.patch(
        f"/converge-api/v1/admin/users/{test_users['admin_id']}/status",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"is_active": False, "reason": "Testing self deactivation"},
    )
    assert patch_resp.status_code == 400
    assert "Cannot deactivate your own administrator account" in patch_resp.json()["detail"]


# =============================================================================
# Phase 4 Tests: Admin Organizers Directory & Conference Review Queue
# =============================================================================

def test_admin_organizers_list_and_verification(client, sync_engine, test_users):
    """Admin can query organizers directory, filter by verification status, and update verification."""
    admin_token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, admin_token)

    # Seed an organizer profile
    org_user_id = uuid.uuid4()
    rand_suffix = uuid.uuid4().hex[:6]
    with Session(sync_engine) as session:
        u = User(
            id=org_user_id,
            username=f"ultratech_{rand_suffix}",
            email=f"test_org_{rand_suffix}@ultratech.com",
            password_hash=bcrypt.hashpw(b"Pass123!", bcrypt.gensalt(12)).decode("utf-8"),
            full_name="Dr. Rajesh Sharma",
            is_active=True,
            is_admin=False,
        )
        session.add(u)
        prof = OrganizerProfile(
            user_id=org_user_id,
            organizer_type=OrganizerType.COMPANY.value,
            representative_name="Dr. Rajesh Sharma",
            organization_name="UltraTech Cement Ltd",
            designation="Chief Sustainability Officer",
            professional_email="rajesh@ultratech.com",
            contact_phone="+91 98200 12345",
            city="Mumbai",
            state_province="Maharashtra",
            country="India",
            bio="Pioneering calcined clay cements and low carbon binders.",
            focus_areas=["Green Cement", "Decarbonization"],
            verification_status=OrganizerVerificationStatus.PENDING_REVIEW.value,
        )
        session.add(prof)
        session.commit()
        prof_id = prof.id

    # 1. Admin gets list
    resp = client.get("/converge-api/v1/admin/organizers?search=UltraTech")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    found = [item for item in data["items"] if item["id"] == str(prof_id)]
    assert len(found) == 1
    assert found[0]["representative_name"] == "Dr. Rajesh Sharma"
    assert found[0]["verification_status"] == "PENDING_REVIEW"

    # 2. Admin verifies organizer
    patch_res = client.patch(
        f"/converge-api/v1/admin/organizers/{prof_id}/verification",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"verification_status": "VERIFIED", "reason": "Verified corporate registration"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["verification_status"] == "VERIFIED"

    # 3. Verify status updated
    resp_verified = client.get(f"/converge-api/v1/admin/organizers?verification_status=VERIFIED")
    assert resp_verified.status_code == 200
    item_v = [item for item in resp_verified.json()["items"] if item["id"] == str(prof_id)]
    assert len(item_v) == 1


def test_admin_conference_review_and_approval_workflow(client, sync_engine, test_users):
    """Admin can list review queue, inspect full details & sessions, request changes, and approve conference."""
    admin_token = create_test_session(sync_engine, test_users["admin_id"])
    client.cookies.set(SESSION_COOKIE_NAME, admin_token)

    # Seed an organizer and a conference in IN_REVIEW
    conf_id = uuid.uuid4()
    org_user_id = uuid.uuid4()
    rand_suffix = uuid.uuid4().hex[:6]
    with Session(sync_engine) as session:
        u = User(
            id=org_user_id,
            username=f"aiims_{rand_suffix}",
            email=f"aiims_{rand_suffix}@aiims.edu",
            password_hash=bcrypt.hashpw(b"Pass123!", bcrypt.gensalt(12)).decode("utf-8"),
            full_name="Prof. Dr. Arun Mukherjee",
            is_active=True,
            is_admin=False,
        )
        session.add(u)
        prof = OrganizerProfile(
            user_id=org_user_id,
            organizer_type=OrganizerType.INSTITUTION.value,
            representative_name="Prof. Dr. Arun Mukherjee",
            organization_name="AIIMS New Delhi",
            professional_email="arun.mukherjee@aiims.edu",
            contact_phone="+91 98100 54321",
            city="New Delhi",
            state_province="Delhi",
            country="India",
            bio="Leading robotics in urology and surgical oncology.",
            focus_areas=["Robotic Surgery", "Healthcare"],
            verification_status=OrganizerVerificationStatus.VERIFIED.value,
        )
        session.add(prof)

        conf = Conference(
            id=conf_id,
            organizer_id=org_user_id,
            title="National Robotic Surgery Congress 2027",
            summary="Surgical robotics telecast and console workshops.",
            description="Deep dive clinical symposium for laparoscopic surgeons.",
            category="Healthcare & MedTech",
            format=ConferenceFormat.IN_PERSON.value,
            venue_name="AIIMS JLN Auditorium",
            timezone="Asia/Kolkata",
            start_date=datetime.now(timezone.utc).date() + timedelta(days=30),
            end_date=datetime.now(timezone.utc).date() + timedelta(days=32),
            city="New Delhi",
            country="India",
            capacity=800,
            status=ConferenceStatus.IN_REVIEW.value,
            is_active=False,
        )
        session.add(conf)

        sess = DbConferenceSession(
            conference_id=conf_id,
            title="Keynote: Multi-Port Robotic Radical Prostatectomy",
            abstract="Live OT HD feed demonstrating nerve-sparing robotic resection.",
            speaker_names="Prof. Dr. Arun Mukherjee",
            track_name="Live Surgery",
            hall_room="Main Auditorium",
            start_time=datetime.now(timezone.utc) + timedelta(days=30, hours=9),
            end_time=datetime.now(timezone.utc) + timedelta(days=30, hours=11),
            is_cancelled=False,
        )
        session.add(sess)
        session.commit()

    # 1. Admin queries conferences queue
    resp = client.get("/converge-api/v1/admin/conferences?status_filter=IN_REVIEW")
    assert resp.status_code == 200
    q_data = resp.json()
    assert q_data["total"] >= 1
    found_conf = [c for c in q_data["items"] if c["id"] == str(conf_id)]
    assert len(found_conf) == 1
    assert found_conf[0]["title"] == "National Robotic Surgery Congress 2027"
    assert found_conf[0]["sessions_count"] == 1
    assert found_conf[0]["organizer"]["organization_name"] == "AIIMS New Delhi"

    # 2. Admin inspects detailed conference view with sessions & organizer
    detail_res = client.get(f"/converge-api/v1/admin/conferences/{conf_id}")
    assert detail_res.status_code == 200
    d_data = detail_res.json()
    assert d_data["title"] == "National Robotic Surgery Congress 2027"
    assert len(d_data["sessions"]) == 1
    assert d_data["sessions"][0]["title"] == "Keynote: Multi-Port Robotic Radical Prostatectomy"
    assert d_data["organizer"]["professional_email"] == "arun.mukherjee@aiims.edu"

    # 3. Admin requests changes (reject without feedback fails with 400)
    fail_dec = client.post(
        f"/converge-api/v1/admin/conferences/{conf_id}/decision",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"decision": "REQUEST_CHANGES", "feedback": ""},
    )
    assert fail_dec.status_code == 400

    # Request changes with feedback
    chg_dec = client.post(
        f"/converge-api/v1/admin/conferences/{conf_id}/decision",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"decision": "REQUEST_CHANGES", "feedback": "Please add more details to the workshop session agenda."},
    )
    assert chg_dec.status_code == 200
    assert chg_dec.json()["new_status"] == "CHANGES_REQUESTED"

    # 4. Admin Approves conference
    appr_dec = client.post(
        f"/converge-api/v1/admin/conferences/{conf_id}/decision",
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
        json={"decision": "APPROVE", "feedback": "Approved for publication."},
    )
    assert appr_dec.status_code == 200
    assert appr_dec.json()["new_status"] == "PUBLISHED"

    # 5. Verify it now appears on public agenda
    pub_res = client.get("/converge-api/v1/agenda/conferences")
    assert pub_res.status_code == 200
    pub_titles = [c["title"] for c in pub_res.json()]
    assert "National Robotic Surgery Congress 2027" in pub_titles



