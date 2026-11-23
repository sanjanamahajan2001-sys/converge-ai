"""Organizer Profile database model in schema core."""
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.agenda import Conference
    from app.db.models.user import User


class OrganizerType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"
    INSTITUTION = "INSTITUTION"
    COMMUNITY = "COMMUNITY"
    NON_PROFIT = "NON_PROFIT"


class OrganizerVerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"


class OrganizerProfile(Base):
    """Organizer Profile entity in schema core."""

    __tablename__ = "organizer_profiles"
    __table_args__ = (
        Index("ix_core_organizer_user_id", "user_id", unique=True),
        Index("ix_core_organizer_verification", "verification_status"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    organizer_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OrganizerType.COMPANY.value,
        server_default=OrganizerType.COMPANY.value,
    )
    representative_name: Mapped[str] = mapped_column(String(120), nullable=False)
    organization_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    professional_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Address details
    address_line1: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state_province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Profile & Expertise
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    focus_areas: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    # Verification / Account Status
    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=OrganizerVerificationStatus.VERIFIED.value,
        server_default=OrganizerVerificationStatus.VERIFIED.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="organizer_profile")
    conferences: Mapped[List["Conference"]] = relationship(
        "Conference",
        foreign_keys="Conference.organizer_id",
        primaryjoin="OrganizerProfile.user_id==Conference.organizer_id",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<OrganizerProfile id={self.id} user_id={self.user_id} org={self.organization_name!r}>"
