"""Unit test suite for Conference Chatroom and Ambient Lounge Service (Temporal Phase 4)."""

from uuid import uuid4
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models.chatroom import (
    ChatroomMessage,
    ChatroomMessageKind,
    ChatroomSenderType,
    ConferenceChatroom,
)
from app.db.models.user import User
from app.db.session import DatabaseManager
from app.services.ambient_lounge_service import AmbientLoungeService

settings = get_settings()


@pytest.fixture
async def db_session():
    """Async database session fixture."""
    manager = DatabaseManager(settings)
    manager.initialize()
    async with manager.session_factory() as session:
        yield session
    await manager.close()


@pytest.mark.asyncio
async def test_get_or_create_lounge_and_welcome(db_session):
    """Verify default lounge retrieval and initial welcome message."""
    lounge = await AmbientLoungeService.get_or_create_default_lounge(db_session)
    assert lounge is not None
    assert lounge.slug.startswith("lounge-") or lounge.slug == "networking-lounge"
    assert lounge.is_active is True

    # Verify messages exist
    msgs = await AmbientLoungeService.get_recent_messages(db_session, lounge.id)
    assert len(msgs) >= 1
    assert msgs[0].turn_index == 0


@pytest.mark.asyncio
async def test_conference_scoped_lounges(db_session):
    """Verify distinct conferences receive separate isolated networking lounges."""
    from datetime import date
    from app.db.models.agenda import Conference

    # Create two test conferences
    c1_id = uuid4()
    c2_id = uuid4()

    conf1 = Conference(
        id=c1_id,
        title="Western Cement Logistics Conclave",
        venue_name="Pune Exhibition Ground",
        city="Pune",
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 21),
        timezone="Asia/Kolkata",
        is_active=True,
    )
    conf2 = Conference(
        id=c2_id,
        title="National Decarbonization Forum",
        venue_name="Jio World Convention Centre",
        city="Mumbai",
        start_date=date(2026, 11, 25),
        end_date=date(2026, 11, 26),
        timezone="Asia/Kolkata",
        is_active=True,
    )
    db_session.add_all([conf1, conf2])
    await db_session.commit()

    # Create lounges for each conference
    lounge1 = await AmbientLoungeService.get_or_create_default_lounge(db_session, conference_id=c1_id)
    lounge2 = await AmbientLoungeService.get_or_create_default_lounge(db_session, conference_id=c2_id)

    assert lounge1.id != lounge2.id
    assert lounge1.conference_id == c1_id
    assert lounge2.conference_id == c2_id
    assert lounge1.slug == f"lounge-{c1_id.hex[:8]}"
    assert lounge2.slug == f"lounge-{c2_id.hex[:8]}"
    assert "Western Cement Logistics Conclave" in lounge1.name
    assert "National Decarbonization Forum" in lounge2.name

    # Verify organizer broadcast goes only to that conference's lounge
    await AmbientLoungeService.broadcast_organizer_announcement(
        db_session,
        conference_id=c1_id,
        announcement_text="☕ Coffee break active at Concourse A!",
    )
    msgs1 = await AmbientLoungeService.get_recent_messages(db_session, lounge1.id)
    msgs2 = await AmbientLoungeService.get_recent_messages(db_session, lounge2.id)

    assert any("Coffee break active at Concourse A!" in m.content for m in msgs1)
    assert not any("Coffee break active at Concourse A!" in m.content for m in msgs2)


@pytest.mark.asyncio
async def test_user_join_and_post_message(db_session):
    """Verify user joins the lounge, receives welcome banner, and posts a chat message."""
    # Create test user
    uid = uuid4()
    test_user = User(
        id=uid,
        email=f"loungetest_{uid.hex[:6]}@example.com",
        username=f"user_{uid.hex[:6]}",
        password_hash="pbkdf2_sha256$260000$test$test",
        full_name="Rajesh Gupta",
        company_name="Apex Logistics",
        job_title="VP Fleet",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()

    lounge = await AmbientLoungeService.get_or_create_default_lounge(db_session)

    # 1. Join lounge
    presence, welcome_msg = await AmbientLoungeService.join_lounge(db_session, lounge.id, test_user)
    assert presence.is_online is True
    assert welcome_msg is not None
    assert "Rajesh Gupta" in welcome_msg.content

    # 2. Post human message
    chat_msg = await AmbientLoungeService.post_user_message(
        db_session,
        lounge.id,
        test_user,
        "Hello everyone! Looking forward to the afternoon supply chain talks."
    )
    assert chat_msg.sender_type == ChatroomSenderType.USER.value
    assert chat_msg.sender_name == "Rajesh Gupta"
    assert chat_msg.content == "Hello everyone! Looking forward to the afternoon supply chain talks."
    assert chat_msg.turn_index > 0

    # 3. Test ambient tick generation
    generated, reason, amb_msg = await AmbientLoungeService.generate_ambient_tick(
        db_session, lounge.id, force=True
    )
    assert generated is True
    assert amb_msg is not None
    assert amb_msg.turn_index > chat_msg.turn_index

    # 4. Leave lounge
    await AmbientLoungeService.leave_lounge(db_session, lounge.id, test_user.id)
    online_count = await AmbientLoungeService.get_online_presence_count(db_session, lounge.id)
    assert online_count >= 1
