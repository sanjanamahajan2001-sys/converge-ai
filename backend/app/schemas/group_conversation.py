"""Pydantic schemas and contracts for Thematic Networking Circles (Group Chat)."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.conversation import MessageSenderTypeEnum


class GroupStatusEnum(str, Enum):
    """Lifecycle state of a Thematic Networking Circle."""

    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GroupRoleEnum(str, Enum):
    """Role of a member within a group conversation."""

    HOST = "HOST"
    MEMBER = "MEMBER"


class GroupMemberSummary(BaseModel):
    """DTO summarizing a participant in a group conversation."""

    user_id: UUID
    username: str
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    role: GroupRoleEnum
    joined_at: datetime
    last_read_turn: int = 0

    model_config = ConfigDict(from_attributes=True)


class GroupMessageCreate(BaseModel):
    """Payload to post a human message to an active group conversation."""

    content: str = Field(..., min_length=1, max_length=4000, description="Message text (1-4000 chars)")
    message_type: Optional[str] = Field("TEXT", description="Message type: TEXT")

    model_config = ConfigDict(extra="forbid")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message content cannot be blank or whitespace-only.")
        return v


class GroupMessageResponse(BaseModel):
    """DTO representing an accepted, persisted group message turn."""

    id: UUID
    group_id: UUID
    sender_id: Optional[UUID] = None
    sender_username: Optional[str] = None
    sender_full_name: Optional[str] = None
    sender_type: MessageSenderTypeEnum
    turn_index: int
    content: str
    message_type: str = "TEXT"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupConversationCreate(BaseModel):
    """Payload to initiate a new Thematic Networking Circle."""

    title: str = Field(..., min_length=3, max_length=120, description="Circle title / focus theme")
    topic_context: str = Field(..., min_length=5, max_length=2000, description="Thematic context and discussion goal")
    member_ids: List[UUID] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2 to 5 peer participant UUIDs (resulting in 3 to 6 total participants including host)",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title_clean(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3:
            raise ValueError("Title must be at least 3 characters.")
        return stripped

    @field_validator("member_ids")
    @classmethod
    def validate_unique_members(cls, v: List[UUID]) -> List[UUID]:
        if len(v) != len(set(v)):
            raise ValueError("member_ids must not contain duplicate participants.")
        return v


class GroupConversationResponse(BaseModel):
    """DTO summary of a group conversation for list/sidebar views."""

    id: UUID
    title: str
    topic_context: str
    host_id: UUID
    host_name: Optional[str] = None
    status: GroupStatusEnum
    max_turns: int
    current_turn: int
    ai_turns_budget: int = 10
    created_at: datetime
    updated_at: datetime
    concluded_at: Optional[datetime] = None
    members_count: int = 0
    members: List[GroupMemberSummary] = []
    last_message: Optional[GroupMessageResponse] = None

    model_config = ConfigDict(from_attributes=True)


class GroupConversationDetailResponse(GroupConversationResponse):
    """Detailed group record including chronological message turns."""

    messages: List[GroupMessageResponse] = []


class GroupActionRequest(BaseModel):
    """Payload for transitioning group conversation lifecycle state."""

    action: str = Field(..., description="Action to perform: LEAVE, CANCEL, CONCLUDE")

    model_config = ConfigDict(extra="forbid")
