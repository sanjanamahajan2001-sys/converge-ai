"""Unit and integration tests for Organizer Registration, Profile Management, and Conference Lifecycle (Phase 2 & Phase 3)."""
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.session import CSRF_EXPECTED_VALUE, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    assert "test" in TEST_DB_URL.lower(), f"SAFETY GUARD: Non-test DB: {TEST_DB_URL}"
    test_settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DB_URL,
    )
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as c:
        yield c


def register_test_organizer(client: TestClient, prefix: str = "org"):
    unique_id = uuid.uuid4().hex[:8]
    payload = {
        "username": f"{prefix}_{unique_id}",
        "password": "OrganizerPass123!",
        "full_name": "Dr. Sarah Lin",
        "email": f"{prefix}_{unique_id}@materials-consortium.org",
        "organizer_type": "COMPANY",
        "representative_name": "Dr. Sarah Lin",
        "organization_name": "Green Cement Innovations Ltd",
        "designation": "Director of Industry Partnerships",
        "professional_email": f"sarah.lin@{unique_id}.org",
        "contact_phone": "+91 98201 44521",
        "city": "Mumbai",
        "state_province": "Maharashtra",
        "postal_code": "400093",
        "country": "India",
        "bio": "Leading international decarbonization symposiums and sustainable building materials summits.",
        "experience_years": 12,
        "focus_areas": ["Green Cement", "Decarbonization", "Sustainable Concrete"],
    }
    resp = client.post("/converge-api/v1/organizer/register", json=payload)
    assert resp.status_code == 201
    return resp.json(), resp.cookies


def test_organizer_register_success(client: TestClient):
    """Verify organizer registration creates user, profile, and issues authenticated session cookie."""
    data, cookies = register_test_organizer(client, "org_reg")
    assert data["representative_name"] == "Dr. Sarah Lin"
    assert data["organization_name"] == "Green Cement Innovations Ltd"
    assert data["city"] == "Mumbai"
    assert data["country"] == "India"
    assert data["verification_status"] == "VERIFIED"

    me_resp = client.get("/converge-api/v1/organizer/me", cookies=cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == data["id"]


def test_organizer_register_duplicate_username(client: TestClient):
    """Verify duplicate registration is rejected with 409 Conflict."""
    unique_id = uuid.uuid4().hex[:8]
    payload = {
        "username": f"org_dup_{unique_id}",
        "password": "OrganizerPass123!",
        "full_name": "Alex Mercer",
        "email": f"alex_{unique_id}@techsummit.io",
        "organizer_type": "INSTITUTION",
        "representative_name": "Alex Mercer",
        "organization_name": "Agentic AI Foundation",
        "professional_email": f"alex@{unique_id}.io",
        "contact_phone": "+91 80 4115 8899",
        "city": "Bengaluru",
        "country": "India",
        "bio": "Curating technical deep-dives on multi-agent consensus protocols and decentralized AI architecture.",
        "focus_areas": ["Autonomous Agents", "Distributed Systems"],
    }

    resp1 = client.post("/converge-api/v1/organizer/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/converge-api/v1/organizer/register", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


def test_organizer_update_profile(client: TestClient):
    """Verify an authenticated organizer can update organization and expertise details."""
    _, cookies = register_test_organizer(client, "org_upd")

    update_payload = {
        "organization_name": "Pan-European HealthTech Collective",
        "designation": "Executive Director",
        "city": "Munich",
        "experience_years": 8,
        "focus_areas": ["Robotics", "MedTech", "AI Diagnostics"],
    }
    upd_resp = client.put(
        "/converge-api/v1/organizer/me",
        json=update_payload,
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["organization_name"] == "Pan-European HealthTech Collective"
    assert upd_data["city"] == "Munich"
    assert upd_data["experience_years"] == 8
    assert "AI Diagnostics" in upd_data["focus_areas"]


def test_organizer_conference_create_and_list(client: TestClient):
    """Verify organizer can create a conference draft and list their own conferences."""
    _, cookies = register_test_organizer(client, "org_conf")

    conf_payload = {
        "title": "National Green Cement & Decarbonization Conclave 2026",
        "summary": "India's premier symposium on low-carbon cements and calcined clay.",
        "description": "Comprehensive summit uniting cement producers, regulators, and civil engineers.",
        "category": "Sustainable Materials",
        "format": "IN_PERSON",
        "venue_name": "Jio World Convention Centre, Pavilion Hall 1",
        "timezone": "Asia/Kolkata",
        "start_date": "2026-11-15",
        "end_date": "2026-11-17",
        "city": "Mumbai",
        "state_province": "Maharashtra",
        "postal_code": "400051",
        "country": "India",
        "formatted_address": "G Block BKC, Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra 400051",
        "location_lat": 19.0657,
        "location_lng": 72.8687,
        "capacity": 1500,
    }

    create_resp = client.post(
        "/converge-api/v1/organizer/conferences",
        json=conf_payload,
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert create_resp.status_code == 201, create_resp.text
    conf_data = create_resp.json()
    assert conf_data["title"] == conf_payload["title"]
    assert conf_data["status"] == "DRAFT"
    assert conf_data["city"] == "Mumbai"
    assert conf_data["sessions_count"] == 0
    conf_id = conf_data["id"]

    # List conferences
    list_resp = client.get("/converge-api/v1/organizer/conferences", cookies=cookies)
    assert list_resp.status_code == 200
    confs = list_resp.json()
    assert any(c["id"] == conf_id for c in confs)


def test_organizer_session_management_and_submission(client: TestClient):
    """Verify organizer can add sessions and submit conference for review once scheduled."""
    _, cookies = register_test_organizer(client, "org_sub")

    # 1. Create conference
    conf_resp = client.post(
        "/converge-api/v1/organizer/conferences",
        json={
            "title": "Autonomous Agents & Swarm Intelligence Summit",
            "venue_name": "KTPO Convention Centre, Whitefield",
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
            "city": "Bengaluru",
            "country": "India",
            "format": "IN_PERSON",
        },
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert conf_resp.status_code == 201
    conf_id = conf_resp.json()["id"]

    # 2. Attempt to submit with 0 sessions -> should fail with 400
    sub_fail = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/submit",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert sub_fail.status_code == 400
    assert "at least one agenda session" in sub_fail.json()["detail"].lower()

    # 3. Add a session to agenda
    now = datetime.now(timezone.utc)
    sess_payload = {
        "title": "Keynote: Multi-Agent Orchestration & Enterprise Reasoning",
        "abstract": "Architectural breakdown of autonomous agent network matchmaking.",
        "speaker_names": "Dr. Elena Rostova, VP AI Research",
        "track_name": "Keynote",
        "hall_room": "Auditorium A",
        "start_time": (now + timedelta(days=35)).isoformat(),
        "end_time": (now + timedelta(days=35, hours=1)).isoformat(),
    }
    sess_resp = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/sessions",
        json=sess_payload,
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert sess_resp.status_code == 201
    sess_id = sess_resp.json()["id"]
    assert sess_resp.json()["title"] == sess_payload["title"]

    # 4. Fetch conference detail -> should contain session
    detail_resp = client.get(f"/converge-api/v1/organizer/conferences/{conf_id}", cookies=cookies)
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["sessions"]) == 1

    # 5. Submit conference for review -> should succeed now
    sub_ok = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/submit",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert sub_ok.status_code == 200
    assert sub_ok.json()["status"] == "IN_REVIEW"

    # 6. Editing while IN_REVIEW should be blocked
    block_resp = client.put(
        f"/converge-api/v1/organizer/conferences/{conf_id}",
        json={"title": "Unauthorized Title Change"},
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert block_resp.status_code == 400
    assert "in_review" in block_resp.json()["detail"].lower()


def test_organizer_live_conference_control_plane(client: TestClient):
    """Verify Phase 5 Organizer Live Conference Control Plane endpoints and auto-announcements."""
    org_data, cookies = register_test_organizer(client, prefix="org_live")

    # 1. Create a conference
    now = datetime.now(timezone.utc)
    conf_payload = {
        "title": "Decarbonization Live Summit",
        "format": "IN_PERSON",
        "start_date": (now + timedelta(days=10)).date().isoformat(),
        "end_date": (now + timedelta(days=12)).date().isoformat(),
        "venue_name": "Pune Tech Grounds",
        "city": "Pune",
        "timezone": "Asia/Kolkata",
    }
    create_resp = client.post(
        "/converge-api/v1/organizer/conferences",
        json=conf_payload,
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert create_resp.status_code == 201
    conf_id = create_resp.json()["id"]

    # 2. Get initial live state
    get_state_resp = client.get(
        f"/converge-api/v1/organizer/conferences/{conf_id}/live-state",
        cookies=cookies,
    )
    assert get_state_resp.status_code == 200
    assert get_state_resp.json()["conference_id"] == conf_id

    # 3. Trigger live break with session delay and weather override
    override_payload = {
        "current_state": "TEA_BREAK",
        "break_type": "TEA_COFFEE",
        "designated_location": "Central Concourse & Hall A Foyer",
        "duration_minutes": 25,
        "delay_minutes": 15,
        "weather_override": "Rain showers: Lawn tables moved indoors to Central Concourse",
    }
    post_state_resp = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/live-state",
        json=override_payload,
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert post_state_resp.status_code == 200
    live_data = post_state_resp.json()
    assert live_data["current_state"] == "TEA_BREAK"
    assert live_data["break_type"] == "TEA_COFFEE"
    assert live_data["designated_location"] == "Central Concourse & Hall A Foyer"
    assert live_data["delay_minutes"] == 15
    assert "Central Concourse" in live_data["announcement_banner"]
    assert live_data["is_active"] is True

    # 4. Check conference chatroom received the broadcast
    active_lounge_resp = client.get(
        f"/converge-api/v1/chatrooms/active?conference_id={conf_id}",
        cookies=cookies,
    )
    assert active_lounge_resp.status_code == 200
    lounge_data = active_lounge_resp.json()
    assert lounge_data["conference_id"] == conf_id
    recent_msgs = lounge_data["recent_messages"]
    assert any("Central Concourse" in m["content"] for m in recent_msgs)

    # 5. Reset live state override
    del_resp = client.delete(
        f"/converge-api/v1/organizer/conferences/{conf_id}/live-state",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert del_resp.status_code == 200
    assert "reset" in del_resp.json()["detail"].lower()

    # 6. Host Live Lounge Kick-off Ceremony
    host_resp = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/lounge/host",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert host_resp.status_code == 200
    assert host_resp.json()["status"] == "hosted"

    # Verify kickoff broadcast and host intro question exist in stream
    lounge_after_host = client.get(
        f"/converge-api/v1/chatrooms/active?conference_id={conf_id}",
        cookies=cookies,
    )
    msgs = lounge_after_host.json()["recent_messages"]
    assert any("The Live Networking Lounge for Decarbonization Live Summit" in m["content"] for m in msgs)
    assert any("Which keynote track or session" in m["content"] for m in msgs)

    # 7. Reset Lounge History
    reset_resp = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/lounge/reset",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert reset_resp.status_code == 200
    assert "reset to turn 0" in reset_resp.json()["detail"].lower()

    lounge_after_reset = client.get(
        f"/converge-api/v1/chatrooms/active?conference_id={conf_id}",
        cookies=cookies,
    )
    reset_msgs = lounge_after_reset.json()["recent_messages"]
    assert any(m["turn_index"] == 0 for m in reset_msgs)
    assert any("Welcome to the Decarbonization Live Summit" in m["content"] for m in reset_msgs)

    # 8. Close Lounge Ceremony & Verify Inactivity
    close_resp = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/lounge/close",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"

    lounge_after_close = client.get(
        f"/converge-api/v1/chatrooms/active?conference_id={conf_id}",
        cookies=cookies,
    )
    assert lounge_after_close.status_code == 200
    lounge_close_data = lounge_after_close.json()
    assert lounge_close_data["is_active"] is False
    assert any("🛑 Lounge Notice:" in m["content"] for m in lounge_close_data["recent_messages"])

    # Attempting to post message when lounge is closed must be blocked (HTTP 400)
    blocked_post = client.post(
        f"/converge-api/v1/chatrooms/{lounge_close_data['id']}/messages",
        json={"content": "Are we still open?"},
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert blocked_post.status_code == 400
    assert "currently closed" in blocked_post.json()["detail"].lower()

    # 9. Re-open / Re-host Lounge and verify message posting resumes
    reopen_resp = client.post(
        f"/converge-api/v1/organizer/conferences/{conf_id}/lounge/host",
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "hosted"

    allowed_post = client.post(
        f"/converge-api/v1/chatrooms/{lounge_close_data['id']}/messages",
        json={"content": "Glad the lounge is open again!"},
        cookies=cookies,
        headers={CSRF_HEADER_NAME: CSRF_EXPECTED_VALUE},
    )
    assert allowed_post.status_code == 201
