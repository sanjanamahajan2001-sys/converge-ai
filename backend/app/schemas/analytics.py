"""Pydantic v2 schemas for User Activity, Sessions, and Analytics Tracking."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActivityEventCreate(BaseModel):
    """Payload to record a user activity, feature click, or agent visit."""

    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Category of event (e.g. FEATURE_CLICK, AGENT_VISIT, PAGE_VIEW)",
    )
    feature_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the feature, component, or agent interacting with",
    )
    target_resource_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional ID of target entity (e.g. partner ID, session ID)",
    )
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Non-sensitive metadata dictionary",
    )

    @field_validator("details")
    @classmethod
    def sanitize_metadata(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Strip sensitive credentials, passwords, or tokens for privacy."""
        if not v:
            return {}
        forbidden_keys = {"password", "token", "secret", "authorization", "cookie", "lat", "lng"}
        return {k: str(val)[:200] for k, val in v.items() if k.lower() not in forbidden_keys}


class ActivityEventResponse(BaseModel):
    """Persisted activity event schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: uuid.UUID
    event_type: str
    feature_name: str
    target_resource_id: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """User session history record."""

    session_id: uuid.UUID
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime
    is_active: bool
    user_agent: Optional[str] = None


class ConversationHistoryDetail(BaseModel):
    """Participant conversation record with whom and when."""

    conversation_id: uuid.UUID
    partner_id: uuid.UUID
    partner_name: str
    partner_username: str
    role: str
    status: str
    turn_count: int
    created_at: datetime
    concluded_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None


class UserActivitySummaryResponse(BaseModel):
    """Comprehensive user activity, logins, and conversation analytics summary."""

    user_id: uuid.UUID
    total_logins: int
    active_sessions: int
    recent_sessions: List[SessionDetailResponse]
    total_conversations: int
    conversations_initiated: int
    conversations_participated: int
    conversation_history: List[ConversationHistoryDetail]
    total_activity_events: int
    feature_clicks_count: int
    agent_visits_count: int
    recent_activity_events: List[ActivityEventResponse]
