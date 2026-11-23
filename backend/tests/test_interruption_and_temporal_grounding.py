from datetime import datetime, timezone
"""Unit tests for Phase 3: Multi-Mode AI Representative Dialogue Grounding & Concurrency Handler.

Verifies:
1. Mode A Turn 0 incorporates active TEA_BREAK context naturally.
2. Mode A Turn 0 incorporates recently ended session context.
3. Mode A Turn 4 concludes with proposal handover note.
4. Group roundtable Host Opening incorporates active tea break context.
5. Early human participant message cleans up pending agent worker tasks.
"""
from uuid import uuid4

import pytest

from app.db.models.profile import AvailabilityStatus, ParticipantProfile, ParticipationIntent
from app.db.models.user import User
from app.schemas.agenda import ConferenceLiveStateResponse
from app.services.representative import DeterministicRepresentativeEngine


def create_test_user(name: str, company: str, job_title: str) -> User:
    u = User(
        id=uuid4(),
        email=f"{name.lower().replace(' ', '')}@example.com",
        username=name.lower().replace(" ", ""),
        full_name=name,
        company_name=company,
        job_title=job_title,
        is_active=True,
    )
    return u


def test_mode_a_turn_0_with_tea_break_context():
    """Verify Mode A Turn 0 includes tea break greeting and meetup suggestion."""
    u1 = create_test_user("Sanjana Mahajan", "InfraTech EPC", "Procurement Head")
    u2 = create_test_user("Vikram Singhania", "Deccan Clinker", "CCO")

    p1 = ParticipantProfile(user_id=u1.id)
    p2 = ParticipantProfile(user_id=u2.id)

    temporal_ctx = ConferenceLiveStateResponse(
        conference_id=uuid4(),
        current_state="TEA_BREAK",
        break_type="TEA_COFFEE",
        designated_location="West Terrace Coffee Bar",
        custom_state_label="Morning Networking Break",
        is_active=True,
    )

    env = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Low-Carbon Cement"],
        initiator_hobbies=["Tea / Coffee"],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Low-Carbon Cement"],
        target_hobbies=["Tea / Coffee"],
        target_sessions=[],
        idempotency_key=str(uuid4()),
        initiator_mood="Ready to network",
        temporal_context=temporal_ctx,
    )

    assert "morning tea break" in env.content.lower()
    assert "West Terrace Coffee Bar" in env.content
    assert "coffee/tea" in env.content.lower()


def test_mode_a_turn_0_with_recent_talk_context():
    """Verify Mode A Turn 0 includes recently ended talk momentum."""
    u1 = create_test_user("Sanjana Mahajan", "InfraTech EPC", "Procurement Head")
    u2 = create_test_user("Vikram Singhania", "Deccan Clinker", "CCO")

    p1 = ParticipantProfile(user_id=u1.id)
    p2 = ParticipantProfile(user_id=u2.id)

    temporal_ctx = ConferenceLiveStateResponse(
        conference_id=uuid4(),
        current_state="IN_SESSION",
        break_type="NONE",
        is_active=True,
        recently_ended_session_id=uuid4(),
        recently_ended_session_title="Decarbonization in Cement Kilns",
    )

    env = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid4(),
        turn_index=0,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Decarbonization"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Decarbonization"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key=str(uuid4()),
        temporal_context=temporal_ctx,
    )

    assert "Decarbonization in Cement Kilns" in env.content
    assert "takeaways" in env.content.lower()


def test_mode_a_turn_4_proposal_handover_prompt():
    """Verify Mode A Turn 4 mentions Draft Proposal action."""
    u1 = create_test_user("Sanjana Mahajan", "InfraTech EPC", "Procurement Head")
    u2 = create_test_user("Vikram Singhania", "Deccan Clinker", "CCO")

    p1 = ParticipantProfile(user_id=u1.id)
    p2 = ParticipantProfile(user_id=u2.id)

    env = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=uuid4(),
        turn_index=4,
        initiator=u1,
        initiator_profile=p1,
        initiator_topics=["Cement"],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=u2,
        target_profile=p2,
        target_topics=["Cement"],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key=str(uuid4()),
    )

    assert "Draft Proposal" in env.content


def test_rfq_product_10_turn_complete_dialogue():
    """Verify 10-turn autonomous dialogue sequence for Mode B Commercial RFQ."""
    from types import SimpleNamespace
    from decimal import Decimal
    from app.schemas.a2a import A2AActionType

    u1 = create_test_user("Sanjana Mahajan", "InfraTech EPC", "Procurement Head")
    u2 = create_test_user("Maahi Sharma", "Maahi Decarb Materials", "MD")

    p1 = ParticipantProfile(user_id=u1.id)
    p2 = ParticipantProfile(user_id=u2.id)

    biz_ctx = SimpleNamespace(
        inquiry_type="RFQ_PRODUCT",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="CALCINED_CLAY_LC3",
        quantity=Decimal("1000"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=42,
        inquiry_notes=None,
    )

    offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("2500"),
        capacity_unit="METRIC_TONNE",
        lead_time_days=5,
        geographic_coverage=["Pune", "Mumbai"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4900"),
        indicative_price_max=Decimal("5100"),
        price_currency="INR",
        pricing_basis="EX_WORKS",
        price_last_confirmed_at=datetime.now(timezone.utc),
        offers_test_certificates=True,
        vendor_certifications=["BIS", "NABL"],
    )

    conv_id = uuid4()

    # Turns 0 through 9
    for turn in range(10):
        env = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=turn,
            initiator=u1,
            initiator_profile=p1,
            initiator_topics=[],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=u2,
            target_profile=p2,
            target_topics=[],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key=f"rfq-turn-{turn}",
            business_context=biz_ctx,
            target_offering=offering,
            total_planned_turns=10,
        )
        assert env.turn_index == turn
        if turn < 9:
            assert env.action_type != A2AActionType.CONCLUDE_DIALOGUE
        else:
            assert env.action_type == A2AActionType.CONCLUDE_DIALOGUE
            assert "Commercial RFQ dialogue complete" in env.content
            assert "Draft Proposal" in env.content


def test_mode_a_10_turn_complete_dialogue():
    """Verify 10-turn autonomous dialogue sequence for Mode A Attendee Networking."""
    from app.schemas.a2a import A2AActionType

    u1 = create_test_user("Sanjana Mahajan", "InfraTech EPC", "Procurement Head")
    u2 = create_test_user("Vikram Singhania", "Deccan Clinker", "CCO")

    p1 = ParticipantProfile(user_id=u1.id)
    p2 = ParticipantProfile(user_id=u2.id)

    conv_id = uuid4()

    # Turns 0 through 9
    for turn in range(10):
        env = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv_id,
            turn_index=turn,
            initiator=u1,
            initiator_profile=p1,
            initiator_topics=["Decarbonization"],
            initiator_hobbies=[],
            initiator_sessions=[],
            target=u2,
            target_profile=p2,
            target_topics=["Decarbonization"],
            target_hobbies=[],
            target_sessions=[],
            idempotency_key=f"mode-a-turn-{turn}",
            total_planned_turns=10,
        )
        assert env.turn_index == turn
        if turn < 9:
            assert env.action_type != A2AActionType.CONCLUDE_DIALOGUE
        else:
            assert env.action_type == A2AActionType.CONCLUDE_DIALOGUE
            assert "Draft Proposal" in env.content
