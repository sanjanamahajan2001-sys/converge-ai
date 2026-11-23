"""Tests verifying Phase 3: The Virtual Roundtable AI Facilitator Engine (N+1 Protocol)."""

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
from app.db.models import ParticipantProfile, ParticipantTopic, User, UserSession
from app.db.models.conversation import MessageSenderType
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


def _create_rich_delegate(sync_db, username_prefix: str, topic_name: str, company: str, title: str):
    uid = uuid.uuid4()
    username = f"{username_prefix}_{uid.hex[:8]}"
    email = f"{username}@example.com"
    pwd_hash = bcrypt.hashpw(b"Secret123!", bcrypt.gensalt()).decode("utf-8")

    user = User(
        id=uid,
        username=username,
        email=email,
        password_hash=pwd_hash,
        full_name=f"Delegate {username_prefix.capitalize()}",
        company_name=company,
        job_title=title,
        is_active=True,
    )
    sync_db.add(user)
    sync_db.flush()

    profile = ParticipantProfile(
        user_id=user.id,
        bio_summary=f"Specialist in {topic_name} and industrial project delivery.",
        current_mood=f"Eager to collaborate on {topic_name}",
    )
    sync_db.add(profile)
    sync_db.flush()

    topic = ParticipantTopic(
        user_id=user.id,
        topic_keyword=topic_name,
    )
    sync_db.add(topic)

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


def test_roundtable_ai_n_plus_one_protocol_3_members(client, sync_db):
    """Test 3-participant circle generates exactly 4 AI turns (Host Opening + 2 Delegate Briefs + Host Synthesis)."""
    host, host_token = _create_rich_delegate(sync_db, "host_rt3", "Decarbonization Policy", "InfraTech EPC", "VP Procurement")
    peer1, _ = _create_rich_delegate(sync_db, "peer1_rt3", "Calcined Clay LC3", "Maahi Decarb", "Technical Director")
    peer2, _ = _create_rich_delegate(sync_db, "peer2_rt3", "Clinker Substitution", "Deccan Clinker", "CCO")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)

    create_resp = client.post(
        "/converge-api/v1/groups/circles",
        json={
            "title": "Low-Carbon Cement Standards Working Group",
            "topic_context": "Accelerating adoption of LC3-50 across Western Maharashtra infrastructure projects.",
            "member_ids": [str(peer1.id), str(peer2.id)],
        },
        headers=CSRF_HEADERS,
    )
    assert create_resp.status_code == 201, create_resp.text
    data = create_resp.json()
    group_id = data["id"]
    messages = data["messages"]

    # 1. Verify Message Counts: Turn 0 (System) + Turns 1..10 (AI Roundtable) = 11 total
    assert len(messages) == 11
    assert data["current_turn"] == 11
    assert data["max_turns"] == 35

    # Turn 0: System Kickoff
    assert messages[0]["turn_index"] == 0
    assert messages[0]["sender_type"] == MessageSenderType.SYSTEM.value

    # Turn 1: Host AI Opening (Welcoming peer1 & peer2 by name, topic preview)
    assert messages[1]["turn_index"] == 1
    assert messages[1]["sender_type"] == MessageSenderType.AGENT.value
    assert messages[1]["sender_id"] == str(host.id)
    assert "InfraTech EPC" in messages[1]["content"]
    assert "Maahi Decarb" in messages[1]["content"] or "Deccan Clinker" in messages[1]["content"]

    # Turn 2: Peer1 AI Brief
    assert messages[2]["turn_index"] == 2
    assert messages[2]["sender_type"] == MessageSenderType.AGENT.value
    assert messages[2]["sender_id"] == str(peer1.id)
    assert "Maahi Decarb" in messages[2]["content"]
    assert "Calcined Clay LC3" in messages[2]["content"]

    # Turn 3: Peer2 AI Brief
    assert messages[3]["turn_index"] == 3
    assert messages[3]["sender_type"] == MessageSenderType.AGENT.value
    assert messages[3]["sender_id"] == str(peer2.id)
    assert "Deccan Clinker" in messages[3]["content"]
    assert "Clinker Substitution" in messages[3]["content"]

    # Turn 10: Host AI Synthesis & Floor Handover
    assert messages[10]["turn_index"] == 10
    assert messages[10]["sender_type"] == MessageSenderType.AGENT.value
    assert messages[10]["sender_id"] == str(host.id)
    assert "Virtual Representative introductions complete" in messages[10]["content"]
    assert "officially open for direct human discussion" in messages[10]["content"]


def test_roundtable_ai_n_plus_one_protocol_4_members(client, sync_db):
    """Test 4-participant circle generates 10 AI turns across 3 rounds."""
    host, host_token = _create_rich_delegate(sync_db, "host_rt4", "Green Supply Chain", "Apex Infra", "Head of Sourcing")
    peer1, _ = _create_rich_delegate(sync_db, "peer1_rt4", "LC3 Cement", "Pro Cement Ltd", "Quality Head")
    peer2, _ = _create_rich_delegate(sync_db, "peer2_rt4", "Bulker Logistics", "Speed Haulage", "Fleet Director")
    peer3, _ = _create_rich_delegate(sync_db, "peer3_rt4", "Pozzolanic Materials", "Mineral Corp", "Sales Head")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)

    create_resp = client.post(
        "/converge-api/v1/groups/circles",
        json={
            "title": "Corridor Haulage & Sourcing Syndicate",
            "topic_context": "Integrated bulk supply and pneumatic transport logistics for metro projects.",
            "member_ids": [str(peer1.id), str(peer2.id), str(peer3.id)],
        },
        headers=CSRF_HEADERS,
    )
    assert create_resp.status_code == 201, create_resp.text
    data = create_resp.json()
    messages = data["messages"]

    # 4 participants -> total AI turns = 10. Total with System kickoff = 11 turns (0..10)
    assert len(messages) == 11
    assert data["max_turns"] == 40  # 30 + 5 * (4 - 2) = 40
    assert data["current_turn"] == 11

    # Verify final turn is Turn 10 Host Synthesis
    last_ai_turn = messages[10]
    assert last_ai_turn["turn_index"] == 10
    assert last_ai_turn["sender_id"] == str(host.id)
    assert "Virtual Representative introductions complete" in last_ai_turn["content"]


def test_roundtable_ai_n_plus_one_protocol_5_members(client, sync_db):
    """Test 5-participant circle generates 10 AI turns across 3 rounds."""
    host, host_token = _create_rich_delegate(sync_db, "host_rt5", "Decarbonization", "InfraTech EPC", "Managing Director")
    peer1, _ = _create_rich_delegate(sync_db, "peer1_rt5", "LC3 Cement", "Deccan Clinker", "CCO")
    peer2, _ = _create_rich_delegate(sync_db, "peer2_rt5", "Supply Chain", "Apex Materials", "Distribution Head")
    peer3, _ = _create_rich_delegate(sync_db, "peer3_rt5", "Green Pozzolans", "GreenBind Tech", "Tech Director")
    peer4, _ = _create_rich_delegate(sync_db, "peer4_rt5", "Ready-Mix", "Sahyadri Concrete", "Plant Head")

    client.cookies.set(SESSION_COOKIE_NAME, host_token)

    create_resp = client.post(
        "/converge-api/v1/groups/circles",
        json={
            "title": "Western Corridor Decarbonization Working Group",
            "topic_context": "Collaborative exploration and operational synchronization around LC3 formulations.",
            "member_ids": [str(peer1.id), str(peer2.id), str(peer3.id), str(peer4.id)],
        },
        headers=CSRF_HEADERS,
    )
    assert create_resp.status_code == 201, create_resp.text
    data = create_resp.json()
    messages = data["messages"]

    # 5 participants -> total AI turns = 10. Total with System kickoff = 11 turns (0..10)
    assert len(messages) == 11
    assert data["max_turns"] == 45  # 30 + 5 * (5 - 2) = 45
    assert data["current_turn"] == 11

    # Turn 1: Host Opening
    assert "to engage in: Collaborative exploration and operational synchronization around LC3 formulations." in messages[1]["content"]

    # Turn 10: Host Synthesis
    last_ai_turn = messages[10]
    assert last_ai_turn["turn_index"] == 10
    assert last_ai_turn["sender_id"] == str(host.id)
    assert "Virtual Representative introductions complete" in last_ai_turn["content"]
    assert "among Host_rt5, Peer1_rt5, Peer2_rt5, Peer3_rt5, and Peer4_rt5!" in last_ai_turn["content"]
