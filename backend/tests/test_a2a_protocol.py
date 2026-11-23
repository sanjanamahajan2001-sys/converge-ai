"""Tests for Versioned Agent-to-Agent (A2A) Protocol Contracts and Message Envelopes (Phase 5)."""

import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.a2a import (
    A2A_PROTOCOL_VERSION,
    A2AActionType,
    A2AExecutionBoundary,
    A2AHandshakeRequest,
    A2AHandshakeResponse,
    A2AMessageEnvelope,
    A2ATurnBudget,
)
from app.schemas.conversation import (
    ConversationOutcomeEnum,
    ConversationStatusEnum,
    MessageSenderTypeEnum,
)


def test_a2a_protocol_version():
    """Verify canonical semantic version of the A2A protocol."""
    assert A2A_PROTOCOL_VERSION == "1.0.0"


def test_a2a_turn_budget_contract():
    """Turn budget must strictly enforce bounds between 0 and 30."""
    budget = A2ATurnBudget(current_turn_count=5, remaining_turns=25)
    assert budget.max_turns == 30
    assert budget.current_turn_count == 5
    assert budget.remaining_turns == 25

    # Boundary violation: current turns > 30
    with pytest.raises(ValidationError):
        A2ATurnBudget(current_turn_count=31, remaining_turns=0)

    # Negative turns rejected
    with pytest.raises(ValidationError):
        A2ATurnBudget(current_turn_count=-1, remaining_turns=30)


def test_a2a_message_envelope_valid():
    """Construct and serialize valid A2AMessageEnvelope."""
    conv_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    recipient_id = uuid.uuid4()

    env = A2AMessageEnvelope(
        conversation_id=conv_id,
        sender_type=MessageSenderTypeEnum.AGENT,
        sender_id=sender_id,
        recipient_id=recipient_id,
        turn_index=0,
        action_type=A2AActionType.INTRODUCE,
        content="Hello, I represent Attendee A and noticed mutual interest in Distributed Systems.",
        idempotency_key="agent-turn-intro-12345",
        metadata={"model": "gpt-4o", "confidence": 0.92},
    )

    assert env.protocol_version == "1.0.0"
    assert env.turn_index == 0
    assert env.action_type == A2AActionType.INTRODUCE
    assert env.sender_type == MessageSenderTypeEnum.AGENT
    assert env.sender_id == sender_id
    assert env.recipient_id == recipient_id

    # Test serialization round-trip
    dumped = env.model_dump(mode="json")
    assert dumped["protocol_version"] == "1.0.0"
    assert dumped["turn_index"] == 0
    assert dumped["idempotency_key"] == "agent-turn-intro-12345"

    reconstructed = A2AMessageEnvelope.model_validate(dumped)
    assert reconstructed.message_id == env.message_id


def test_a2a_envelope_sender_presence_validation():
    """SYSTEM messages must not have sender_id; AGENT and PARTICIPANT must have sender_id."""
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # SYSTEM message with sender_id must fail
    with pytest.raises(ValidationError) as exc:
        A2AMessageEnvelope(
            conversation_id=conv_id,
            sender_type=MessageSenderTypeEnum.SYSTEM,
            sender_id=user_id,
            recipient_id=user_id,
            turn_index=0,
            action_type=A2AActionType.CONCLUDE_DIALOGUE,
            content="Dialogue concluded by system timeout.",
            idempotency_key="sys-timeout-12345",
        )
    assert "SYSTEM messages must not have a sender_id" in str(exc.value)

    # AGENT message without sender_id must fail
    with pytest.raises(ValidationError) as exc:
        A2AMessageEnvelope(
            conversation_id=conv_id,
            sender_type=MessageSenderTypeEnum.AGENT,
            sender_id=None,
            recipient_id=user_id,
            turn_index=0,
            action_type=A2AActionType.INQUIRE,
            content="Agent inquiry.",
            idempotency_key="agent-inquire-12345",
        )
    assert "AGENT messages must include a valid sender_id" in str(exc.value)


def test_a2a_envelope_turn_limit():
    """Turn index must strictly be < 30 (0..29)."""
    conv_id = uuid.uuid4()
    sender_id = uuid.uuid4()

    # Turn index 30 must fail
    with pytest.raises(ValidationError):
        A2AMessageEnvelope(
            conversation_id=conv_id,
            sender_type=MessageSenderTypeEnum.PARTICIPANT,
            sender_id=sender_id,
            recipient_id=uuid.uuid4(),
            turn_index=30,
            action_type=A2AActionType.CONCLUDE_DIALOGUE,
            content="Attempting turn 30.",
            idempotency_key="turn-30-key-12345",
        )


def test_a2a_envelope_content_length_and_whitespace():
    """Content must be 1-4000 characters and non-whitespace."""
    conv_id = uuid.uuid4()
    sender_id = uuid.uuid4()

    with pytest.raises(ValidationError):
        A2AMessageEnvelope(
            conversation_id=conv_id,
            sender_type=MessageSenderTypeEnum.AGENT,
            sender_id=sender_id,
            recipient_id=uuid.uuid4(),
            turn_index=1,
            action_type=A2AActionType.SHARE_INTERESTS,
            content="   ",
            idempotency_key="whitespace-key-12345",
        )


def test_a2a_handshake_request_and_response():
    """A2AHandshakeRequest and A2AHandshakeResponse contract validation."""
    conv_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    target_id = uuid.uuid4()

    req = A2AHandshakeRequest(
        conversation_id=conv_id,
        initiator_agent_id=agent_id,
        target_participant_id=target_id,
        initial_action=A2AActionType.INTRODUCE,
        idempotency_key="handshake-idemp-001",
        declared_interests=["Kubernetes", "AI Agents"],
    )
    assert req.initial_action == A2AActionType.INTRODUCE
    assert len(req.declared_interests) == 2

    resp = A2AHandshakeResponse(
        conversation_id=conv_id,
        status=ConversationStatusEnum.ACTIVE,
        turn_budget=A2ATurnBudget(current_turn_count=1, remaining_turns=19),
        next_expected_sender_id=target_id,
    )
    assert resp.status == ConversationStatusEnum.ACTIVE
    assert resp.turn_budget.remaining_turns == 19
