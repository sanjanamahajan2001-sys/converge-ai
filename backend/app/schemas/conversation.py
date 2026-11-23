"""Pydantic schemas and contracts for Conversation and Persistent Messaging (P5-WS2, GAP-06)."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationStatusEnum(str, Enum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ConversationOutcomeEnum(str, Enum):
    PROPOSAL_GENERATED = "PROPOSAL_GENERATED"
    COMPLETED_WITHOUT_PROPOSAL = "COMPLETED_WITHOUT_PROPOSAL"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class MessageSenderTypeEnum(str, Enum):
    PARTICIPANT = "PARTICIPANT"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class ConversationBusinessContextCreate(BaseModel):
    """Payload to attach an initial commercial business context snapshot."""

    inquiry_type: str = Field(
        "RFQ_PRODUCT",
        description="RFQ_PRODUCT, RFI_SERVICE, ALTERNATIVE_SOURCING, DISTRIBUTION_EXPANSION, etc.",
    )
    product_name: str = Field(..., min_length=2, max_length=200)
    product_code: Optional[str] = Field(None, max_length=80)
    grade_code: Optional[str] = Field(None, max_length=80)
    service_code: Optional[str] = Field(None, max_length=80)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=30)
    delivery_location: Optional[str] = Field(None, max_length=255)
    timeline_days: Optional[int] = Field(None, gt=0)
    target_price_indication: Optional[float] = Field(
        None, description="Disclosed target budget indication (Only saved if is_budget_public == True)"
    )
    is_budget_public: bool = Field(
        False, description="Whether buyer explicitly chose to include target budget in RFQ brief"
    )
    urgency: Optional[str] = Field("PLANNED", max_length=30)
    inquiry_notes: Optional[str] = Field(None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class ConversationBusinessContextResponse(BaseModel):
    """DTO representing verified point-in-time commercial business context snapshot."""

    id: UUID
    conversation_id: UUID
    version: int
    inquiry_type: str
    product_name: str
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    delivery_location: Optional[str] = None
    timeline_days: Optional[int] = None
    target_price_indication: Optional[float] = None
    urgency: Optional[str] = None
    inquiry_notes: Optional[str] = None
    snapshot_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Payload to initiate a 1-to-1 conversation with another participant."""

    target_id: UUID = Field(..., description="Target participant UUID to invite")
    business_context: Optional[ConversationBusinessContextCreate] = None
    auto_start: Optional[bool] = Field(default=False, description="Whether to start conversation directly in ACTIVE state")

    model_config = ConfigDict(extra="forbid")


class LocationPayload(BaseModel):
    """Structured location payload for WhatsApp-style location sharing."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to +180)")
    name: Optional[str] = Field(None, max_length=200, description="Optional name of the venue or point of interest")
    address: Optional[str] = Field(None, max_length=500, description="Optional street or landmark address")

    model_config = ConfigDict(extra="forbid")


class MessageCreate(BaseModel):
    """Payload to append a new message turn to an active conversation."""

    content: str = Field(..., min_length=1, max_length=4000, description="Message text body (1-4000 chars)")
    message_type: Optional[str] = Field("TEXT", description="Message type: TEXT or LOCATION")
    location: Optional[LocationPayload] = Field(None, description="Optional location payload if message_type is LOCATION")
    location_payload: Optional[LocationPayload] = Field(None, description="Optional alias for location payload")

    model_config = ConfigDict(extra="forbid")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content cannot be blank or whitespace-only.")
        return v


class MessageResponse(BaseModel):
    """DTO representing an accepted, persisted message turn."""

    id: UUID
    conversation_id: UUID
    sender_id: Optional[UUID]
    sender_type: MessageSenderTypeEnum
    turn_index: int
    content: str
    message_type: str = "TEXT"
    location_payload: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """DTO summary of a conversation for list/card views."""

    id: UUID
    initiator_id: UUID
    target_id: UUID
    status: ConversationStatusEnum
    match_score: Optional[float] = None
    terminal_outcome: Optional[ConversationOutcomeEnum] = None
    created_at: datetime
    updated_at: datetime
    concluded_at: Optional[datetime] = None
    other_participant_id: Optional[UUID] = None
    other_participant_name: Optional[str] = None
    last_message: Optional[MessageResponse] = None
    message_count: int = 0
    has_business_context: bool = False
    business_inquiry_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation record including chronological messages."""

    messages: List[MessageResponse] = []
    other_participant_mood: Optional[str] = None
    business_context: Optional[ConversationBusinessContextResponse] = None


class ConversationActionRequest(BaseModel):
    """Payload for transitioning conversation lifecycle state."""

    action: str = Field(..., description="Action to perform: ACCEPT, REJECT, CANCEL, CONCLUDE")
    outcome: Optional[ConversationOutcomeEnum] = Field(
        None, description="Terminal outcome when concluding: PROPOSAL_GENERATED or COMPLETED_WITHOUT_PROPOSAL"
    )
    trigger_agent: Optional[bool] = Field(
        None, description="Optional override to trigger autonomous agent dialogue upon ACCEPT"
    )

    model_config = ConfigDict(extra="forbid")
