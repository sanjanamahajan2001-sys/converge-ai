"""Pydantic schemas for the Common Open Conference Lounge & Chatroom."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatroomMessageResponse(BaseModel):
    """Schema for individual message in the conference chatroom."""

    id: uuid.UUID
    chatroom_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_type: str
    sender_name: str
    content: str
    message_kind: str
    turn_index: int
    metadata_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatroomPostMessageRequest(BaseModel):
    """Payload when human attendee or representative sends a chat message."""

    content: str = Field(..., min_length=1, max_length=4000, description="Chatroom message content")


class ChatroomPresenceResponse(BaseModel):
    """Active delegate presence in the open lounge."""

    user_id: uuid.UUID
    full_name: str
    organization: Optional[str] = None
    is_online: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatroomContextResponse(BaseModel):
    """Live environmental & floor context for the lounge."""

    weather: Dict[str, Any]
    traffic: Dict[str, Any]
    active_break: Optional[str] = None
    break_location: Optional[str] = None
    general_announcement: Optional[str] = None
    announcement_criticality: Optional[str] = "NORMAL"
    active_day: Optional[int] = None


class ChatroomDetailResponse(BaseModel):
    """Complete public lounge state with online presence, live context, and recent chat stream."""

    id: uuid.UUID
    conference_id: Optional[uuid.UUID] = None
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    ambient_interval_seconds: int
    online_count: int
    context: ChatroomContextResponse
    recent_messages: List[ChatroomMessageResponse]

    model_config = ConfigDict(from_attributes=True)


class AmbientTickResponse(BaseModel):
    """Response returned when evaluating continuous interval ambient dialogue."""

    message_generated: bool
    reason: Optional[str] = None
    message: Optional[ChatroomMessageResponse] = None
