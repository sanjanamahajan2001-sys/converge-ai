"""Comprehensive End-to-End Demonstration and Acceptance Test (AC-WS5).

Verifies the complete real application lifecycle:
1. Two attendees with distinct profiles, active informal moods, topics, and bookmarks.
2. Attendee 1 sends invitation to Attendee 2.
3. Attendee 2 accepts invitation with trigger_agent=True.
4. Autonomous virtual representative dialogue runs for 5 turns (turns 0-4) with
   mood grounding and mutual context without hallucination.
5. Turns alternate strictly between representatives on behalf of attendees.
6. Representatives speak in third person.
7. Sequence concludes at turn 4, leaving conversation ACTIVE.
8. Human attendees seamlessly continue chatting manually (interleaved messaging).
9. All messages persist reliably with appropriate sender_type and turn_index.
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SASession

from app.core.config import get_settings
from app.db.models.agenda import BookmarkedSession, Conference, Session as ConferenceSession
from app.db.models.conversation import (
    Conversation,
    ConversationStatus,
    Message,
    MessageSenderType,
)
from app.db.models.profile import (
    AvailabilityStatus,
    ParticipantHobby,
    ParticipantProfile,
    ParticipantTopic,
    ParticipationIntent,
)
from app.db.models.task import Task, TaskStatus
from app.db.models.user import User
from app.schemas.conversation import MessageSenderTypeEnum
from app.services.agent_worker import AgentTaskService
from app.services.conversation import ConversationService
from tests.test_agent_execution import (
    app_instance,
    async_db,
    cleanup_test_db,
    client,
    create_agent_test_attendee,
    sync_engine,
)


@pytest.mark.asyncio
async def test_full_agent_chat_enhancement_lifecycle(sync_engine, async_db):
    """Demonstrates full autonomous virtual representative workflow followed by human attendee chat."""
    now = datetime.now(timezone.utc)

    # 1. Create Conference and Shared Agenda Session
    with SASession(sync_engine) as session:
        conf = Conference(
            title="Autonomous Agent Summit 2026",
            venue_name="Moscone Center",
            start_date=now.date(),
            end_date=now.date(),
            timezone="UTC",
        )
        session.add(conf)
        session.flush()

        sess = ConferenceSession(
            conference_id=conf.id,
            title="Next-Gen Autonomous Agent Orchestration",
            hall_room="Main Hall A",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        session.add(sess)
        session.commit()
        session_id = sess.id

    # 2. Seed Attendee 1 (Elena Vance) with active mood "Ready to network"
    user_elena, _ = create_agent_test_attendee(
        sync_engine,
        username="elena_vance",
        email="elena@example.com",
        full_name="Dr. Elena Vance",
        job_title="Lead AI Architect",
        company="Cyberdyne Research",
        intent=ParticipationIntent.BOTH,
        topics=["Agent Swarms", "Multi-Agent Consensus"],
        hobbies=["Rock Climbing"],
    )

    # 3. Seed Attendee 2 (Marcus Sterling) with active mood "Open to casual conversation"
    user_marcus, _ = create_agent_test_attendee(
        sync_engine,
        username="marcus_sterling",
        email="marcus@example.com",
        full_name="Marcus Sterling",
        job_title="VP of Engineering",
        company="OmniCorp Systems",
        intent=ParticipationIntent.CASUAL,
        topics=["Multi-Agent Consensus", "Cloud Infrastructure"],
        hobbies=["Photography"],
    )

    # 4. Attach Moods and Bookmark Shared Session
    with SASession(sync_engine) as session:
        prof_elena = session.query(ParticipantProfile).filter_by(user_id=user_elena.id).one()
        prof_elena.current_mood = "Ready to network"
        prof_elena.mood_updated_at = now

        prof_marcus = session.query(ParticipantProfile).filter_by(user_id=user_marcus.id).one()
        prof_marcus.current_mood = "Open to casual conversation"
        prof_marcus.mood_updated_at = now

        b1 = BookmarkedSession(user_id=user_elena.id, session_id=session_id)
        b2 = BookmarkedSession(user_id=user_marcus.id, session_id=session_id)
        session.add_all([b1, b2])
        session.commit()

    # 5. Elena initiates conversation with Marcus
    conv = Conversation(
        initiator_id=user_elena.id,
        target_id=user_marcus.id,
        status=ConversationStatus.INVITED,
    )
    async_db.add(conv)
    await async_db.commit()
    await async_db.refresh(conv)

    assert conv.status == ConversationStatus.INVITED

    # 6. Marcus accepts conversation with trigger_agent=True
    updated_detail = await ConversationService.update_conversation_status(
        db=async_db,
        conversation_id=conv.id,
        current_user_id=user_marcus.id,
        client_ip="127.0.0.1",
        action="ACCEPT",
        trigger_agent=True,
    )
    assert updated_detail.status.value == "ACTIVE"
    assert updated_detail.other_participant_mood == "Ready to network"

    # 7. Worker processes the 5-turn representative dialogue sequence (turns 0-4)
    for expected_turn in range(5):
        claimed_task = await AgentTaskService.claim_next_task(
            db=async_db,
            worker_id=f"demo-worker-{expected_turn}",
        )
        assert claimed_task is not None, f"Expected task for turn {expected_turn} to be claimed"
        assert claimed_task.payload["turn_index"] == expected_turn

        result = await AgentTaskService.execute_task(
            db=async_db,
            task=claimed_task,
            worker_id=f"demo-worker-{expected_turn}",
        )
        assert result["turn_index"] == expected_turn

    # 8. Verify all 5 turns exist and are correctly attributed as AGENT
    messages = (
        await async_db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.turn_index.asc())
        )
    ).all()
    assert len(messages) == 5
    assert all(m.sender_type == MessageSenderType.AGENT for m in messages)

    # Turn 0: Elena's representative speaks on behalf of Elena
    assert messages[0].sender_id == user_elena.id
    assert "Dr. Elena Vance" in messages[0].content
    assert "Ready to network" in messages[0].content
    assert "Multi-Agent Consensus" in messages[0].content

    # Turn 1: Marcus's representative speaks on behalf of Marcus
    assert messages[1].sender_id == user_marcus.id
    assert "Marcus Sterling" in messages[1].content
    assert "Open to casual conversation" in messages[1].content
    assert "Multi-Agent Consensus" in messages[1].content

    # Turn 2: Elena's representative proposes coffee meetup (grounded in Marcus's casual mood & intent)
    assert messages[2].sender_id == user_elena.id
    assert "coffee" in messages[2].content.lower()

    # Turn 3: Marcus's representative acknowledges possibility conditionally
    assert messages[3].sender_id == user_marcus.id
    assert "welcome possibility" in messages[3].content or "coordinate directly" in messages[3].content
    assert "productive plan" not in messages[3].content
    assert "That works nicely for" not in messages[3].content

    # Turn 4: Elena's representative concludes dialogue with handoff to attendees
    assert messages[4].sender_id == user_elena.id
    assert "leave this conversation open" in messages[4].content
    assert "Dr. Elena Vance" in messages[4].content

    # 9. Verify no further agent task is scheduled (sequence stops at turn 4)
    next_task = await AgentTaskService.claim_next_task(async_db, worker_id="check-worker")
    assert next_task is None

    # 10. Conversation remains ACTIVE for attendee direct messaging
    await async_db.refresh(conv)
    assert conv.status == ConversationStatus.ACTIVE

    # 11. Elena sends a direct attendee message (Turn 5)
    human_msg_5, _ = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv.id,
        sender_id=user_elena.id,
        content="Hi Marcus! Looking forward to grabbing coffee near the lounge as our agents coordinated.",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert human_msg_5.turn_index == 5
    assert human_msg_5.sender_type == MessageSenderTypeEnum.PARTICIPANT

    # 12. Marcus sends a direct attendee message (Turn 6)
    human_msg_6, final_detail = await ConversationService.append_message(
        db=async_db,
        conversation_id=conv.id,
        sender_id=user_marcus.id,
        content="Sounds great Elena, see you there right after the keynote!",
        client_ip="127.0.0.1",
        sender_type=MessageSenderType.PARTICIPANT,
    )
    assert human_msg_6.turn_index == 6
    assert human_msg_6.sender_type == MessageSenderTypeEnum.PARTICIPANT
    assert final_detail.status.value == "ACTIVE"
    assert final_detail.message_count == 7
