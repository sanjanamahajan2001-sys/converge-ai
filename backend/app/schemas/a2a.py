"""Versioned Agent-to-Agent (A2A) Protocol Contracts and Message Envelopes (Phase 5 Foundation).

Defines the server-authoritative protocol contracts governing automated agent dialogue turns,
handshake negotiation, turn budgeting, and idempotency boundaries. Used by Phase 5 runtime
contracts and Phase 6 background task worker orchestration.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.conversation import (
    ConversationOutcomeEnum,
    ConversationStatusEnum,
    MessageSenderTypeEnum,
)

A2A_PROTOCOL_VERSION: str = "1.0.0"


class A2AActionType(str, Enum):
    """Canonical A2A turn actions exchanged between participant agents."""

    INTRODUCE = "INTRODUCE"
    INQUIRE = "INQUIRE"
    SHARE_INTERESTS = "SHARE_INTERESTS"
    PROPOSE_COLLABORATION = "PROPOSE_COLLABORATION"
    CONCLUDE_DIALOGUE = "CONCLUDE_DIALOGUE"


class A2ATurnBudget(BaseModel):
    """Server-authoritative turn budget governing 1-to-1 dialogue."""

    max_turns: int = Field(default=30, description="Hard ceiling of total dialogue messages (0..29)")
    current_turn_count: int = Field(..., ge=0, le=30, description="Current accepted message turns in conversation")
    remaining_turns: int = Field(..., ge=0, le=30, description="Available turn budget remaining")

    model_config = ConfigDict(extra="forbid")


class A2AExecutionBoundary(BaseModel):
    """Execution sandbox and rate-boundary constraints governing agent turns."""

    max_turns_per_dialogue: int = Field(default=30, description="Absolute ceiling on total turns per dialogue")
    max_tokens_per_turn: int = Field(default=2000, description="Token consumption ceiling per message turn")
    allowed_actions: List[A2AActionType] = Field(
        default_factory=lambda: list(A2AActionType),
        description="Allowed structured turn actions for agents",
    )
    require_idempotency: bool = Field(default=True, description="Strict requirement for idempotency keys")

    model_config = ConfigDict(extra="forbid")


class A2AMessageEnvelope(BaseModel):
    """Canonical versioned envelope for agent-to-agent messages and handshakes."""

    protocol_version: str = Field(default=A2A_PROTOCOL_VERSION, description="A2A protocol semantic version")
    message_id: UUID = Field(default_factory=uuid4, description="Unique message turn identifier")
    conversation_id: UUID = Field(..., description="Target conversation UUID")
    sender_type: MessageSenderTypeEnum = Field(..., description="PARTICIPANT, AGENT, or SYSTEM")
    sender_id: Optional[UUID] = Field(None, description="UUID of sender (required for PARTICIPANT and AGENT, null for SYSTEM)")
    recipient_id: UUID = Field(..., description="Target attendee user UUID")
    turn_index: int = Field(..., ge=0, lt=30, description="Monotonic 0-based turn index (0..29)")
    action_type: A2AActionType = Field(..., description="Structured intent category")
    content: str = Field(..., min_length=1, max_length=4000, description="Message text payload (1-4000 chars)")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Client/agent supplied idempotency key to prevent replay turns")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured protocol metadata (model name, score breakdown, context)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of envelope generation")

    model_config = ConfigDict(extra="forbid")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Envelope content cannot be empty or whitespace only.")
        return v

    @field_validator("sender_id")
    @classmethod
    def validate_sender_presence(cls, v: Optional[UUID], info) -> Optional[UUID]:
        sender_type = info.data.get("sender_type")
        if sender_type == MessageSenderTypeEnum.SYSTEM and v is not None:
            raise ValueError("SYSTEM messages must not have a sender_id.")
        if sender_type in (MessageSenderTypeEnum.PARTICIPANT, MessageSenderTypeEnum.AGENT) and v is None:
            raise ValueError(f"{sender_type.value} messages must include a valid sender_id.")
        return v


class A2AHandshakeRequest(BaseModel):
    """Payload to initiate an automated agent-to-agent handshake dialogue."""

    conversation_id: UUID
    initiator_agent_id: UUID
    target_participant_id: UUID
    initial_action: A2AActionType = A2AActionType.INTRODUCE
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    declared_interests: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class A2AHandshakeResponse(BaseModel):
    """Result envelope of an A2A handshake evaluation."""

    conversation_id: UUID
    status: ConversationStatusEnum
    turn_budget: A2ATurnBudget
    envelope: Optional[A2AMessageEnvelope] = None
    next_expected_sender_id: Optional[UUID] = None
    terminal_outcome: Optional[ConversationOutcomeEnum] = None

    model_config = ConfigDict(extra="forbid")
