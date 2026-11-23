"""Tests verifying Phase 1: Group Conversation Database Schema & Migration 019."""
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.models.conversation import MessageSenderType
from app.db.models.group_conversation import (
    GroupConversation,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupStatus,
)
from app.db.models.user import User
from app.db.session import DatabaseManager

settings = get_settings()


@pytest.fixture
async def db_session():
    """Async database session fixture for schema tests."""
    manager = DatabaseManager(settings)
    manager.initialize()
    async with manager.session_factory() as session:
        yield session
    await manager.close()


@pytest.mark.asyncio
async def test_group_tables_exist(db_session):
    """Verify that all 3 group tables exist in schema core."""
    res = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'core' AND table_name LIKE 'group_%' "
            "ORDER BY table_name;"
        )
    )
    tables = [r[0] for r in res.fetchall()]
    assert "group_conversations" in tables
    assert "group_members" in tables
    assert "group_messages" in tables


@pytest.mark.asyncio
async def test_group_conversation_creation_and_membership(db_session):
    """Verify that a group conversation with multiple members can be created and queried cleanly."""
    user_stmt = select(User).limit(3)
    res = await db_session.execute(user_stmt)
    users = res.scalars().all()
    assert len(users) >= 2, "Test requires at least 2 users in db"

    host = users[0]
    peer = users[1]

    # Create Group Conversation
    group = GroupConversation(
        title="Decarbonization Working Group",
        topic_context="Exploring low-carbon clinker alternatives and regional supply chain synergies",
        host_id=host.id,
        status=GroupStatus.ACTIVE,
        max_turns=25,
        current_turn=0,
    )
    db_session.add(group)
    await db_session.flush()

    assert group.id is not None
    assert group.status == GroupStatus.ACTIVE

    # Add Members
    member_host = GroupMember(
        group_id=group.id,
        user_id=host.id,
        role=GroupRole.HOST,
    )
    member_peer = GroupMember(
        group_id=group.id,
        user_id=peer.id,
        role=GroupRole.MEMBER,
    )
    db_session.add_all([member_host, member_peer])
    await db_session.flush()

    # Add AI Intro message
    msg = GroupMessage(
        group_id=group.id,
        sender_id=host.id,
        sender_type=MessageSenderType.AGENT,
        turn_index=0,
        content="Welcome to the Decarbonization Working Group circle.",
        message_type="TEXT",
    )
    db_session.add(msg)
    await db_session.flush()

    # Query back
    stmt = select(GroupConversation).where(GroupConversation.id == group.id)
    retrieved = (await db_session.execute(stmt)).scalar_one()

    assert retrieved.title == "Decarbonization Working Group"
    assert len(retrieved.members) == 2
    assert len(retrieved.messages) == 1
    assert retrieved.messages[0].turn_index == 0

    # Cleanup test record
    await db_session.delete(group)
    await db_session.commit()


@pytest.mark.asyncio
async def test_group_conversation_unique_member_constraint(db_session):
    """Verify that a user cannot be added twice to the exact same group conversation."""
    user_stmt = select(User).limit(1)
    user = (await db_session.execute(user_stmt)).scalars().first()
    assert user is not None

    group = GroupConversation(
        title="Circular Economy Roundtable",
        topic_context="Testing unique member constraint",
        host_id=user.id,
        status=GroupStatus.ACTIVE,
        max_turns=30,
    )
    db_session.add(group)
    await db_session.flush()

    m1 = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.HOST)
    db_session.add(m1)
    await db_session.flush()

    # Adding the same user to the same group should violate uq_group_member_user
    m2 = GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.MEMBER)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_group_conversation_max_turns_constraint(db_session):
    """Verify that max_turns is constrained within the allowed range (20 to 50)."""
    user_stmt = select(User).limit(1)
    user = (await db_session.execute(user_stmt)).scalars().first()
    assert user is not None

    # Invalid max_turns < 20
    group_invalid = GroupConversation(
        title="Invalid Limits Circle",
        topic_context="Testing range constraint",
        host_id=user.id,
        status=GroupStatus.ACTIVE,
        max_turns=10,  # Below allowed 20
    )
    db_session.add(group_invalid)
    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()
