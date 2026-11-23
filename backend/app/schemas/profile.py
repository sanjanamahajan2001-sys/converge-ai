"""Participant Profile, Hobbies, and Topics Data Transfer Objects (DTOs)."""
import re
from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ParticipationIntent(str, Enum):
    """Conference networking intent options."""

    NETWORKING = "NETWORKING"
    CASUAL = "CASUAL"
    BOTH = "BOTH"


class AvailabilityStatus(str, Enum):
    """Real-time conference availability toggle."""

    AVAILABLE = "AVAILABLE"
    IN_SESSION = "IN_SESSION"
    DO_NOT_DISTURB = "DO_NOT_DISTURB"
    OFFLINE = "OFFLINE"


# Curated starter catalog of conference hobbies and preferences (DOC-REQ-001 §2.1)
# Curated starter conversation preferences (Informal Mood - AC-WS1)
CURATED_MOODS: List[str] = [
    "Ready to network",
    "Open to casual conversation",
    "Conference-focused",
    "Open to discussing an informal break or meetup",
    "Prefer low-key interaction",
]

CURATED_HOBBIES: List[str] = [
    "Tea / Coffee",
    "Casual Conversations",
    "Technical Deep-dives",
    "Sustainability & Decarbonization Policy",
    "Equipment & Exhibition Walking Tours",
]


class HobbyCreate(BaseModel):
    """DTO for adding a participant hobby/interest."""

    hobby_name: str = Field(
        ...,
        min_length=1,
        max_length=60,
        description="Name of the hobby or interest preference.",
        examples=["Tea / Coffee"],
    )

    @field_validator("hobby_name")
    @classmethod
    def sanitize_hobby(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Hobby name cannot be empty or whitespace.")
        return clean


class HobbyRead(BaseModel):
    """DTO for reading a participant hobby record."""

    id: int
    user_id: UUID
    hobby_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicCreate(BaseModel):
    """DTO for adding a participant technical focus keyword."""

    topic_keyword: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Technical focus or domain topic keyword.",
        examples=["Kiln Automation"],
    )

    @field_validator("topic_keyword")
    @classmethod
    def sanitize_topic(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Topic keyword cannot be empty or whitespace.")
        return clean


class TopicRead(BaseModel):
    """DTO for reading a participant topic record."""

    id: int
    user_id: UUID
    topic_keyword: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileCreate(BaseModel):
    """Payload to create or initialize a participant profile."""

    model_config = ConfigDict(extra="forbid")

    intent: ParticipationIntent = Field(
        default=ParticipationIntent.NETWORKING,
        description="Primary intent at the conference.",
    )
    bio_summary: Optional[str] = Field(
        None,
        max_length=500,
        description="Brief professional summary (max 500 characters).",
        examples=["Process engineer focusing on cement decarbonization."],
    )
    availability: AvailabilityStatus = Field(
        default=AvailabilityStatus.AVAILABLE,
        description="Current availability status.",
    )
    allow_agent_matching: bool = Field(
        default=False,
        description="Explicit opt-in required for autonomous agent matching (GAP-06).",
    )
    allow_agent_dm_initiation: bool = Field(
        default=True,
        description="Allow AI representative to initiate 1-on-1 DMs from lounge.",
    )
    contact_sharing_policy: str = Field(
        default="ASK_HUMAN_FIRST",
        description="Contact sharing policy: ASK_HUMAN_FIRST | AUTO_SHARE_ON_RFQ | NEVER_SHARE",
    )
    company_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Organization or company name.",
    )
    job_title: Optional[str] = Field(
        None,
        max_length=120,
        description="Professional position or job title.",
    )
    current_mood: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional self-declared informal conversation preference (max 255 chars).",
    )
    gender: Optional[str] = Field(
        None,
        max_length=30,
        description="Optional gender identifier (e.g. Female, Male, Non-binary, Prefer not to say).",
    )
    date_of_birth: Optional[str] = Field(
        None,
        description="Date of birth in DD-MM-YYYY format (or ISO YYYY-MM-DD).",
    )
    location: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional location (city, venue, or address).",
    )
    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional latitude coordinate.")
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional longitude coordinate.")
    hobbies: Optional[List[str]] = Field(
        default_factory=list,
        description="List of participant hobbies or social preferences.",
    )
    topics: Optional[List[str]] = Field(
        default_factory=list,
        description="List of technical keywords or focus areas.",
    )

    @field_validator("current_mood")
    @classmethod
    def sanitize_mood(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        if len(clean) > 255:
            raise ValueError("Mood preference cannot exceed 255 characters.")
        return clean

    @field_validator("bio_summary")
    @classmethod
    def clean_bio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        return clean if clean else ""

    @field_validator("hobbies")
    @classmethod
    def validate_hobbies(cls, items: Optional[List[str]]) -> List[str]:
        if not items:
            return []
        if len(items) > 20:
            raise ValueError("Maximum 20 hobbies permitted per participant.")
        deduped: List[str] = []
        seen = set()
        for item in items:
            clean = item.strip()
            if not clean:
                continue
            if len(clean) > 60:
                raise ValueError(f"Hobby '{clean[:20]}...' exceeds 60 characters.")
            lower_clean = clean.lower()
            if lower_clean not in seen:
                seen.add(lower_clean)
                deduped.append(clean)
        return deduped

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, items: Optional[List[str]]) -> List[str]:
        if not items:
            return []
        if len(items) > 20:
            raise ValueError("Maximum 20 topics permitted per participant.")
        deduped: List[str] = []
        seen = set()
        for item in items:
            clean = item.strip()
            if not clean:
                continue
            if len(clean) > 80:
                raise ValueError(f"Topic '{clean[:20]}...' exceeds 80 characters.")
            lower_clean = clean.lower()
            if lower_clean not in seen:
                seen.add(lower_clean)
                deduped.append(clean)
        return deduped


class ProfileUpdate(BaseModel):
    """Payload to update an existing participant profile."""

    model_config = ConfigDict(extra="forbid")

    intent: Optional[ParticipationIntent] = None
    bio_summary: Optional[str] = Field(None, max_length=500)
    availability: Optional[AvailabilityStatus] = None
    allow_agent_matching: Optional[bool] = None
    allow_agent_dm_initiation: Optional[bool] = None
    contact_sharing_policy: Optional[str] = None
    company_name: Optional[str] = Field(None, max_length=150)
    job_title: Optional[str] = Field(None, max_length=120)
    current_mood: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=30)
    date_of_birth: Optional[str] = Field(None, description="Date of birth in DD-MM-YYYY format (or ISO YYYY-MM-DD)")
    location: Optional[str] = Field(None, max_length=255, description="Optional location (city, venue, or address).")
    location_lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional latitude coordinate.")
    location_lng: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional longitude coordinate.")
    hobbies: Optional[List[str]] = None
    topics: Optional[List[str]] = None

    @field_validator("current_mood")
    @classmethod
    def sanitize_mood(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        if len(clean) > 255:
            raise ValueError("Mood preference cannot exceed 255 characters.")
        return clean

    @field_validator("bio_summary")
    @classmethod
    def clean_bio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        return clean if clean else ""

    @field_validator("hobbies")
    @classmethod
    def validate_hobbies(cls, items: Optional[List[str]]) -> Optional[List[str]]:
        if items is None:
            return None
        if len(items) > 20:
            raise ValueError("Maximum 20 hobbies permitted per participant.")
        deduped: List[str] = []
        seen = set()
        for item in items:
            clean = item.strip()
            if not clean:
                continue
            if len(clean) > 60:
                raise ValueError(f"Hobby '{clean[:20]}...' exceeds 60 characters.")
            lower_clean = clean.lower()
            if lower_clean not in seen:
                seen.add(lower_clean)
                deduped.append(clean)
        return deduped

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, items: Optional[List[str]]) -> Optional[List[str]]:
        if items is None:
            return None
        if len(items) > 20:
            raise ValueError("Maximum 20 topics permitted per participant.")
        deduped: List[str] = []
        seen = set()
        for item in items:
            clean = item.strip()
            if not clean:
                continue
            if len(clean) > 80:
                raise ValueError(f"Topic '{clean[:20]}...' exceeds 80 characters.")
            lower_clean = clean.lower()
            if lower_clean not in seen:
                seen.add(lower_clean)
                deduped.append(clean)
        return deduped


class ProfileResponse(BaseModel):
    """Detailed profile response for the authenticated owner."""

    user_id: UUID
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    intent: ParticipationIntent
    bio_summary: Optional[str] = None
    availability: AvailabilityStatus
    allow_agent_matching: bool
    allow_agent_dm_initiation: bool = True
    contact_sharing_policy: str = "ASK_HUMAN_FIRST"
    current_mood: Optional[str] = None
    mood_updated_at: Optional[datetime] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    hobbies: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("date_of_birth")
    def serialize_dob(self, v: Optional[date | str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, date):
            return v.strftime("%d-%m-%Y")
        if isinstance(v, str):
            clean = v.strip()
            # If already DD-MM-YYYY, return as is
            if re.match(r"^\d{2}-\d{2}-\d{4}$", clean):
                return clean
            # If YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
                parts = clean.split("-")
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return clean
        return str(v)


class PublicProfileResponse(BaseModel):
    """Sanitized public profile response for other conference participants.
    
    Guarantees private contact details (email, phone, credentials) are strictly omitted (GAP-03, GAP-10).
    """

    user_id: UUID
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    intent: ParticipationIntent
    bio_summary: Optional[str] = None
    availability: AvailabilityStatus
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    hobbies: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("date_of_birth")
    def serialize_dob(self, v: Optional[date | str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, date):
            return v.strftime("%d-%m-%Y")
        if isinstance(v, str):
            clean = v.strip()
            if re.match(r"^\d{2}-\d{2}-\d{4}$", clean):
                return clean
            if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
                parts = clean.split("-")
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return clean
        return str(v)
