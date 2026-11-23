"""Pydantic schemas and contracts for Organizer profile, registration, and conference management (Phase 2 & Phase 3)."""
from datetime import date as dt_date, datetime, time as dt_time
import enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrganizerTypeEnum(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"
    INSTITUTION = "INSTITUTION"
    COMMUNITY = "COMMUNITY"
    NON_PROFIT = "NON_PROFIT"


class OrganizerVerificationStatusEnum(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"


class OrganizerRegisterRequest(BaseModel):
    """Payload for registering a new organizer account and profile."""

    model_config = ConfigDict(extra="forbid")

    # Account credentials
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr

    # Identity
    organizer_type: OrganizerTypeEnum = Field(default=OrganizerTypeEnum.COMPANY)
    representative_name: str = Field(..., min_length=2, max_length=120)
    organization_name: Optional[str] = Field(None, max_length=150)
    designation: Optional[str] = Field(None, max_length=100)
    professional_email: EmailStr
    contact_phone: str = Field(..., min_length=5, max_length=50)
    website_url: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=255)

    # Address
    address_line1: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)

    # Bio & Focus
    bio: str = Field(..., min_length=10, max_length=2000)
    experience_years: Optional[int] = Field(None, ge=0, le=100)
    focus_areas: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("username", "representative_name", "city", "country", "bio", mode="before")
    @classmethod
    def strip_required_strings(cls, v: str) -> str:
        if isinstance(v, str):
            clean = v.strip()
            if not clean:
                raise ValueError("Field cannot be empty or blank.")
            return clean
        return v


class OrganizerProfileUpdate(BaseModel):
    """Payload for updating an existing organizer profile."""

    model_config = ConfigDict(extra="forbid")

    organizer_type: Optional[OrganizerTypeEnum] = None
    representative_name: Optional[str] = Field(None, min_length=2, max_length=120)
    organization_name: Optional[str] = Field(None, max_length=150)
    designation: Optional[str] = Field(None, max_length=100)
    professional_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, min_length=5, max_length=50)
    website_url: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, min_length=10, max_length=2000)
    experience_years: Optional[int] = Field(None, ge=0, le=100)
    focus_areas: Optional[List[str]] = Field(None, max_length=20)


class OrganizerProfileResponse(BaseModel):
    """Response DTO for Organizer profile attributes."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    organizer_type: str
    representative_name: str
    organization_name: Optional[str] = None
    designation: Optional[str] = None
    professional_email: str
    contact_phone: str
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    address_line1: Optional[str] = None
    city: str
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    bio: str
    experience_years: Optional[int] = None
    focus_areas: List[str]
    verification_status: str
    created_at: datetime
    updated_at: datetime
    conferences_count: int = 0


# =============================================================================
# Conference & Agenda Lifecycle Schemas (Phase 3)
# =============================================================================


class ConferenceFormatEnum(str, enum.Enum):
    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"


class ConferenceStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class OrganizerConferenceCreate(BaseModel):
    """Payload to create a new conference draft."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=3, max_length=200)
    summary: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, max_length=100)
    format: ConferenceFormatEnum = Field(default=ConferenceFormatEnum.IN_PERSON)
    venue_name: str = Field(..., min_length=1, max_length=200)
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=50)
    start_date: dt_date
    end_date: dt_date
    start_time: Optional[dt_time] = None
    end_time: Optional[dt_time] = None
    registration_opens_at: Optional[datetime] = None
    registration_closes_at: Optional[datetime] = None
    capacity: Optional[int] = Field(None, ge=1, le=500000)
    target_audience: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=255)
    banner_url: Optional[str] = Field(None, max_length=255)
    meeting_url: Optional[str] = Field(None, max_length=255)

    # Location
    formatted_address: Optional[str] = Field(None, max_length=255)
    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    place_id: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator("title", "venue_name", mode="before")
    @classmethod
    def strip_required_strings(cls, v: str) -> str:
        if isinstance(v, str):
            clean = v.strip()
            if not clean:
                raise ValueError("Field must not be blank.")
            return clean
        return v


class OrganizerConferenceUpdate(BaseModel):
    """Payload to update an editable conference draft."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    summary: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, max_length=100)
    format: Optional[ConferenceFormatEnum] = None
    venue_name: Optional[str] = Field(None, min_length=1, max_length=200)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    start_time: Optional[dt_time] = None
    end_time: Optional[dt_time] = None
    registration_opens_at: Optional[datetime] = None
    registration_closes_at: Optional[datetime] = None
    capacity: Optional[int] = Field(None, ge=1, le=500000)
    target_audience: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=255)
    banner_url: Optional[str] = Field(None, max_length=255)
    meeting_url: Optional[str] = Field(None, max_length=255)

    formatted_address: Optional[str] = Field(None, max_length=255)
    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0)
    place_id: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)


class OrganizerSessionCreate(BaseModel):
    """Payload to add a session to conference agenda."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    abstract: Optional[str] = Field(None, max_length=5000)
    speaker_names: Optional[str] = Field(None, max_length=255)
    track_name: Optional[str] = Field(None, max_length=100)
    hall_room: str = Field(..., min_length=1, max_length=100)
    start_time: datetime
    end_time: datetime

    @field_validator("title", "hall_room", mode="before")
    @classmethod
    def strip_required_strings(cls, v: str) -> str:
        if isinstance(v, str):
            clean = v.strip()
            if not clean:
                raise ValueError("Field must not be blank.")
            return clean
        return v


class OrganizerSessionUpdate(BaseModel):
    """Payload to update an existing session."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    abstract: Optional[str] = Field(None, max_length=5000)
    speaker_names: Optional[str] = Field(None, max_length=255)
    track_name: Optional[str] = Field(None, max_length=100)
    hall_room: Optional[str] = Field(None, min_length=1, max_length=100)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_cancelled: Optional[bool] = None


class OrganizerSessionResponse(BaseModel):
    """Response model for a conference session."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conference_id: UUID
    title: str
    abstract: Optional[str] = None
    speaker_names: Optional[str] = None
    track_name: Optional[str] = None
    hall_room: str
    start_time: datetime
    end_time: datetime
    is_cancelled: bool = False
    created_at: datetime
    updated_at: datetime


class OrganizerConferenceResponse(BaseModel):
    """Summary response for an organizer conference."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organizer_id: Optional[UUID] = None
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    format: str
    venue_name: str
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
    formatted_address: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    place_id: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    status: str
    review_feedback: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sessions_count: int = 0


class OrganizerConferenceDetailResponse(OrganizerConferenceResponse):
    """Detailed response with all sessions attached."""

    sessions: List[OrganizerSessionResponse] = Field(default_factory=list)


class ConferenceSubmitResponse(BaseModel):
    """Response after submitting conference for review."""

    status: str
    conference_id: UUID
    message: str
