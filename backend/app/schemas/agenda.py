"""Pydantic validation DTOs and contracts for Conference Agenda and Sessions (GAP-09, GAP-10)."""

from datetime import date as dt_date, datetime, time as dt_time
import enum
from typing import List, Optional
from uuid import UUID
import zoneinfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConferenceBase(BaseModel):
    """Base schema for Conference data."""

    title: str = Field(..., min_length=1, max_length=200, description="Conference title")
    description: Optional[str] = Field(None, max_length=2000, description="Overview / description")
    venue_name: str = Field(..., min_length=1, max_length=200, description="Venue or convention center name")
    timezone: str = Field(default="UTC", min_length=1, max_length=50, description="IANA timezone name")
    start_date: dt_date = Field(..., description="Conference starting date")
    end_date: dt_date = Field(..., description="Conference ending date")
    is_active: bool = Field(default=True, description="Whether conference is currently active")

    @field_validator("title", "venue_name", mode="before")
    @classmethod
    def strip_and_validate_nonempty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Field must be a non-empty string.")
        return v.strip()

    @field_validator("timezone", mode="before")
    @classmethod
    def validate_iana_timezone(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Timezone must be a non-empty string.")
        cleaned = v.strip()
        try:
            zoneinfo.ZoneInfo(cleaned)
        except Exception:
            raise ValueError(f"Invalid IANA timezone identifier: {cleaned!r}")
        return cleaned

    @model_validator(mode="after")
    def validate_date_ordering(self) -> "ConferenceBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date.")
        return self


class ConferenceCreate(ConferenceBase):
    """Request DTO to create a conference."""

    model_config = ConfigDict(extra="forbid")


class ConferenceUpdate(BaseModel):
    """Request DTO to update conference properties."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    venue_name: Optional[str] = Field(None, min_length=1, max_length=200)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "venue_name", mode="before")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not isinstance(v, str) or not v.strip():
                raise ValueError("Field must be a non-empty string.")
            return v.strip()
        return v

    @field_validator("timezone", mode="before")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            try:
                zoneinfo.ZoneInfo(cleaned)
            except Exception:
                raise ValueError(f"Invalid IANA timezone identifier: {cleaned!r}")
            return cleaned
        return v


class ConferenceOrganizerPublicResponse(BaseModel):
    """Sanitized public organizer profile for attendee inspection."""

    id: UUID
    representative_name: str
    organization_name: Optional[str] = None
    designation: Optional[str] = None
    city: str
    country: str
    verification_status: str
    website_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConferenceResponse(BaseModel):
    """Public read model for conference entity with full event and organizer footprint."""

    id: UUID
    organizer_id: Optional[UUID] = None
    organizer: Optional[ConferenceOrganizerPublicResponse] = None
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    format: str = "IN_PERSON"
    venue_name: str
    formatted_address: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    place_id: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: str
    start_date: dt_date
    end_date: dt_date
    start_time: Optional[dt_time] = None
    end_time: Optional[dt_time] = None
    registration_opens_at: Optional[datetime] = None
    registration_closes_at: Optional[datetime] = None
    capacity: Optional[int] = None
    target_audience: Optional[str] = None
    website_url: Optional[str] = None
    banner_url: Optional[str] = None
    meeting_url: Optional[str] = None
    status: str = "PUBLISHED"
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionBase(BaseModel):
    """Base schema for Conference Session data."""

    title: str = Field(..., min_length=1, max_length=255, description="Session title")
    abstract: Optional[str] = Field(None, max_length=5000, description="Session abstract / summary")
    speaker_names: Optional[str] = Field(None, max_length=255, description="Comma-separated public speaker names")
    track_name: Optional[str] = Field(None, max_length=100, description="Track or category")
    hall_room: str = Field(..., min_length=1, max_length=100, description="Designated hall or room")
    start_time: datetime = Field(..., description="Scheduled start timestamp (timezone-aware)")
    end_time: datetime = Field(..., description="Scheduled end timestamp (timezone-aware)")
    import_batch_id: Optional[str] = Field(None, max_length=100, description="Provenance import batch ID")
    is_cancelled: bool = Field(default=False, description="Cancellation status")

    @field_validator("title", "hall_room", mode="before")
    @classmethod
    def strip_and_validate_nonempty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Field must be a non-empty string.")
        return v.strip()

    @field_validator("track_name", mode="before")
    @classmethod
    def strip_optional_track(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("speaker_names", mode="before")
    @classmethod
    def validate_and_strip_speaker_names(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            if "@" in stripped:
                raise ValueError("Speaker names must not contain email addresses.")
            return stripped
        return v

    @model_validator(mode="after")
    def validate_session_times(self) -> "SessionBase":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must strictly follow start_time.")
        return self


class SessionCreate(SessionBase):
    """Request DTO to create a session."""

    conference_id: UUID

    model_config = ConfigDict(extra="forbid")


class SessionUpdate(BaseModel):
    """Request DTO to partially update session details."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    abstract: Optional[str] = Field(None, max_length=5000)
    speaker_names: Optional[str] = Field(None, max_length=255)
    track_name: Optional[str] = Field(None, max_length=100)
    hall_room: Optional[str] = Field(None, min_length=1, max_length=100)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    import_batch_id: Optional[str] = Field(None, max_length=100)
    is_cancelled: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("speaker_names", mode="before")
    @classmethod
    def validate_update_speakers(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            if "@" in stripped:
                raise ValueError("Speaker names must not contain email addresses.")
            return stripped
        return v


class SessionResponse(BaseModel):
    """Public read model for conference session. Internal import details excluded."""

    id: UUID
    conference_id: UUID
    title: str
    abstract: Optional[str] = None
    speaker_names: Optional[str] = None
    track_name: Optional[str] = None
    hall_room: str
    session_type: Optional[str] = "TECHNICAL_SESSION"
    start_time: datetime
    end_time: datetime
    is_cancelled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionFilter(BaseModel):
    """Query parameter contract for filtering agenda sessions."""

    conference_id: Optional[UUID] = None
    track_name: Optional[str] = None
    hall_room: Optional[str] = None
    date: Optional[dt_date] = None
    is_cancelled: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class BookmarkResponse(BaseModel):
    """Read contract for participant session bookmark creation."""

    user_id: UUID
    session_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookmarkedSessionResponse(BaseModel):
    """Read contract for a participant's bookmarked session including session details (P3-WS3)."""

    session_id: UUID
    bookmarked_at: datetime
    session: SessionResponse

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Session Intent & Attendee Consent Schemas (AC-WS8)
# =============================================================================


class SessionIntentDecisionState(str, enum.Enum):
    ATTENDING = "ATTENDING"
    DECLINED = "DECLINED"
    UNDECIDED = "UNDECIDED"


class SessionIntentDecisionCreate(BaseModel):
    """Request DTO to record or update attendance decision (AC-WS8)."""

    decision: SessionIntentDecisionState = Field(
        ...,
        description="Attendee attendance decision: ATTENDING, DECLINED, or UNDECIDED",
    )
    source: Optional[str] = Field(
        default="REPRESENTATIVE_PROMPT",
        max_length=50,
        description="Decision source / trigger mechanism",
    )

    model_config = ConfigDict(extra="forbid")


class SessionIntentDecisionResponse(BaseModel):
    """Read contract for participant session intent decision."""

    id: UUID
    user_id: UUID
    session_id: UUID
    decision: str
    source: str
    created_at: datetime
    updated_at: datetime
    session: Optional[SessionResponse] = None

    model_config = ConfigDict(from_attributes=True)


class SessionRecommendationPrompt(BaseModel):
    """Attendee session recommendation prompt matching interests/hobbies (AC-WS8, Manager Requirement)."""

    session: SessionResponse
    matched_reason: str = Field(..., description="Explanation of topic/hobby alignment, e.g. 'Matched interest in cement'")
    prompt_message: str = Field(..., description="Personalized prompt message presented to the attendee")
    current_decision: Optional[str] = Field(None, description="Current recorded intent decision: ATTENDING, DECLINED, or UNDECIDED")

    model_config = ConfigDict(from_attributes=True)


class ConferenceLiveStateResponse(BaseModel):
    """Read contract for real-time conference temporal and physical networking state."""

    id: Optional[UUID] = None
    conference_id: UUID
    active_session_id: Optional[UUID] = None
    current_state: str = Field(default="IN_SESSION", description="IN_SESSION, TEA_BREAK, LUNCH_BREAK, NETWORKING_RECEPTION, FREE_TIME")
    custom_state_label: Optional[str] = None
    break_type: str = Field(default="NONE", description="TEA_COFFEE, LUNCH, CASUAL_NETWORKING, EXHIBITION, NONE")
    designated_location: Optional[str] = None
    announcement_banner: Optional[str] = None
    announcement_criticality: Optional[str] = Field(default="NORMAL")
    active_day: Optional[int] = Field(default=None, description="Active conference day number")
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = True
    recently_ended_session_id: Optional[UUID] = None
    recently_ended_session_title: Optional[str] = None
    delay_minutes: Optional[int] = Field(default=None, description="Active session delay in minutes")
    weather_override: Optional[str] = Field(default=None, description="Indoor or weather guidance note")
    amenities_note: Optional[str] = Field(default=None, description="Venue amenities, charging stations, and logistics note")

    model_config = ConfigDict(from_attributes=True)


class ConferenceLiveStateUpdate(BaseModel):
    """Payload to trigger or schedule a live conference state or break."""

    current_state: str = Field(..., description="IN_SESSION, TEA_BREAK, LUNCH_BREAK, NETWORKING_RECEPTION, FREE_TIME")
    custom_state_label: Optional[str] = None
    break_type: str = Field(default="NONE", description="TEA_COFFEE, LUNCH, CASUAL_NETWORKING, EXHIBITION, NONE")
    designated_location: Optional[str] = None
    announcement_banner: Optional[str] = None
    criticality: Optional[str] = Field(default="NORMAL", description="NORMAL or CRITICAL")
    duration_minutes: int = Field(default=30, ge=5, le=180)
    delay_minutes: Optional[int] = Field(default=None, ge=0, le=120, description="Optional delay in minutes to broadcast")
    weather_override: Optional[str] = Field(default=None, description="Optional weather/indoor override note")
    amenities_note: Optional[str] = Field(default=None, description="Optional venue amenities and charging stations note")
    active_day: Optional[int] = Field(default=None, ge=0, le=10, description="Optional active day number override (1 or 2, 0 or null resets to auto)")
    active_session_id: Optional[UUID] = None

