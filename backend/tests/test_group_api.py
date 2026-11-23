"""Integration tests for Group Phase 2: Thematic Networking Circles REST APIs."""

import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.session import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models import User, UserSession
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL
CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


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
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture
def sync_db():
    engine = create_engine(TEST_MIGRATION_URL)
    with Session(engine) as session:
        yield session
        session.rollback()
        session.execute(text("DELETE FROM core.group_conversations;"))
        session.commit()


def _create_authenticated_user(sync_db, username_prefix: str):
    uid = uuid.uuid4()
    username = f"{username_prefix}_{uid.hex[:8]}"
    email = f"{username}@test.com"
    pwd_hash = bcrypt.hashpw(b"Secret123!", bcrypt.gensalt()).decode("utf-8")

    user = User(
        id=uid,
        username=username,
        email=email,
        password_hash=pwd_hash,
        full_name=f"Test {username_prefix.capitalize()}",
        company_name=f"{username_prefix.capitalize()} Industries Ltd",
        job_title="Director of Operations",
        is_active=True,
    )
    sync_db.add(user)
    sync_db.flush()

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    sync_db.add(session)
    sync_db.commit()

    return user, raw_token


def test_create_and_list_networking_circles(client, sync_db):
    """Verify circle creation with 2 invited peers (3 total) and listing user's circles."""
    host, host_token = _create_authenticated_user(sync_db, "host")
    peer1, _ = _create_authenticated_user(sync_db, "peer1")
    peer2, peer2_token = _create_authenticated_user(sync_db, "peer2")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)

    # 1. Create Circle
    payload = {
        "title": "Decarbonization Standards Working Group",
        "topic_context": "Reviewing standard benchmarks for LC3 cement and clinker reduction targets.",
        "member_ids": [str(peer1.id), str(peer2.id)],
    }
    resp = client.post("/converge-api/v1/groups/circles", json=payload, headers=CSRF_HEADERS)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    group_id = data["id"]
    assert data["title"] == "Decarbonization Standards Working Group"
    assert data["status"] == "ACTIVE"
    assert data["max_turns"] == 35  # 30 + 5 * (3 - 2) = 35
    assert data["members_count"] == 3
    # 10 AI Turns Protocol across 3 rounds: Turn 0 (System) + Turns 1..10 (AI Roundtable) = 11
    assert len(data["messages"]) == 11
    assert data["messages"][0]["turn_index"] == 0
    assert data["messages"][1]["turn_index"] == 1
    assert data["messages"][-1]["turn_index"] == 10

    # 2. List Circles for Host
    list_resp = client.get("/converge-api/v1/groups/circles")
    assert list_resp.status_code == 200
    host_circles = list_resp.json()
    assert any(c["id"] == group_id for c in host_circles)

    # 3. List Circles for Peer2
    client.cookies.set(SESSION_COOKIE_NAME, peer2_token)
    p2_resp = client.get("/converge-api/v1/groups/circles")
    assert p2_resp.status_code == 200
    peer_circles = p2_resp.json()
    assert any(c["id"] == group_id for c in peer_circles)


def test_post_message_and_idor_protection(client, sync_db):
    """Verify that only authorized members can post and outsiders receive 403 Forbidden."""
    host, host_token = _create_authenticated_user(sync_db, "host2")
    peer1, peer1_token = _create_authenticated_user(sync_db, "peer1_2")
    peer2, _ = _create_authenticated_user(sync_db, "peer2_2")
    outsider, outsider_token = _create_authenticated_user(sync_db, "outsider")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)
    create_resp = client.post(
        "/converge-api/v1/groups/circles",
        json={
            "title": "Industrial Logistics Roundtable",
            "topic_context": "Pneumatic bulker fleet coordination across western corridors.",
            "member_ids": [str(peer1.id), str(peer2.id)],
        },
        headers=CSRF_HEADERS,
    )
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # 1. Circle was created with 3 members: Turn 0 (System) + Turns 1..10 (AI Roundtable) = 11 turns
    # Peer1 posts first human message -> should be turn_index 11
    client.cookies.set(SESSION_COOKIE_NAME, peer1_token)
    msg_resp = client.post(
        f"/converge-api/v1/groups/circles/{group_id}/messages",
        json={"content": "Hello everyone, glad to join this logistics working group."},
        headers=CSRF_HEADERS,
    )
    assert msg_resp.status_code == 201
    msg_data = msg_resp.json()
    assert msg_data["turn_index"] == 11
    assert msg_data["content"] == "Hello everyone, glad to join this logistics working group."
    assert msg_data["sender_username"] == peer1.username

    # 2. Outsider attempts to get details -> 403
    client.cookies.set(SESSION_COOKIE_NAME, outsider_token)
    detail_resp = client.get(f"/converge-api/v1/groups/circles/{group_id}")
    assert detail_resp.status_code == 403

    # 3. Outsider attempts to post -> 403
    post_resp = client.post(
        f"/converge-api/v1/groups/circles/{group_id}/messages",
        json={"content": "Let me in!"},
        headers=CSRF_HEADERS,
    )
    assert post_resp.status_code == 403


def test_duplicate_active_circle_rejection(client, sync_db):
    """Verify that creating a duplicate active circle with the identical members returns 409 Conflict."""
    host, host_token = _create_authenticated_user(sync_db, "host3")
    peer1, _ = _create_authenticated_user(sync_db, "peer1_3")
    peer2, _ = _create_authenticated_user(sync_db, "peer2_3")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)
    payload = {
        "title": "Duplicate Check Group",
        "topic_context": "Testing conflict prevention.",
        "member_ids": [str(peer1.id), str(peer2.id)],
    }
    r1 = client.post("/converge-api/v1/groups/circles", json=payload, headers=CSRF_HEADERS)
    assert r1.status_code == 201

    # Second creation with identical set
    r2 = client.post("/converge-api/v1/groups/circles", json=payload, headers=CSRF_HEADERS)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


def test_leave_circle(client, sync_db):
    """Verify member voluntary exit and system announcement turn."""
    host, host_token = _create_authenticated_user(sync_db, "host4")
    peer1, peer1_token = _create_authenticated_user(sync_db, "peer1_4")
    peer2, _ = _create_authenticated_user(sync_db, "peer2_4")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)
    create_resp = client.post(
        "/converge-api/v1/groups/circles",
        json={
            "title": "Temporary Discussion Circle",
            "topic_context": "Testing member exit flow.",
            "member_ids": [str(peer1.id), str(peer2.id)],
        },
        headers=CSRF_HEADERS,
    )
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # Peer1 leaves
    client.cookies.set(SESSION_COOKIE_NAME, peer1_token)
    leave_resp = client.post(f"/converge-api/v1/groups/circles/{group_id}/leave", headers=CSRF_HEADERS)
    assert leave_resp.status_code == 200
    assert leave_resp.json()["members_count"] == 2


def test_host_close_and_delete_circle(client, sync_db):
    """Verify Option 1: Host can close and delete circles, while non-hosts receive 403 Forbidden."""
    host, host_token = _create_authenticated_user(sync_db, "host_opt1")
    peer1, peer1_token = _create_authenticated_user(sync_db, "peer1_opt1")
    peer2, _ = _create_authenticated_user(sync_db, "peer2_opt1")

    # Host creates circle
    client.cookies.set(SESSION_COOKIE_NAME, host_token)
    create_resp = client.post(
        "/converge-api/v1/groups/circles",
        json={
            "title": "Circle to Close and Delete",
            "topic_context": "Testing host lifecycle management.",
            "member_ids": [str(peer1.id), str(peer2.id)],
        },
        headers=CSRF_HEADERS,
    )
    assert create_resp.status_code == 201
    group_id = create_resp.json()["id"]

    # 1. Non-host attempts to close -> 403 Forbidden
    client.cookies.set(SESSION_COOKIE_NAME, peer1_token)
    forbidden_close = client.post(f"/converge-api/v1/groups/circles/{group_id}/close", headers=CSRF_HEADERS)
    assert forbidden_close.status_code == 403
    assert "Only the circle host can close" in forbidden_close.json()["detail"]

    # 2. Non-host attempts to delete -> 403 Forbidden
    forbidden_delete = client.delete(f"/converge-api/v1/groups/circles/{group_id}", headers=CSRF_HEADERS)
    assert forbidden_delete.status_code == 403
    assert "Only the circle host can delete" in forbidden_delete.json()["detail"]

    # 3. Host closes circle -> 200 OK, status COMPLETED
    client.cookies.set(SESSION_COOKIE_NAME, host_token)
    close_resp = client.post(f"/converge-api/v1/groups/circles/{group_id}/close", headers=CSRF_HEADERS)
    assert close_resp.status_code == 200
    close_data = close_resp.json()
    assert close_data["status"] == "COMPLETED"
    assert close_data["concluded_at"] is not None

    # Closing again returns 400 Bad Request
    reclose_resp = client.post(f"/converge-api/v1/groups/circles/{group_id}/close", headers=CSRF_HEADERS)
    assert reclose_resp.status_code == 400

    # 4. Host deletes circle -> 204 No Content
    delete_resp = client.delete(f"/converge-api/v1/groups/circles/{group_id}", headers=CSRF_HEADERS)
    assert delete_resp.status_code == 204

    # 5. Accessing deleted circle returns 404 Not Found
    get_resp = client.get(f"/converge-api/v1/groups/circles/{group_id}")
    assert get_resp.status_code == 404
