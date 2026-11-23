"""User identity database model in schema core."""
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.agenda import BookmarkedSession, Conference, SessionIntentDecision
    from app.db.models.organizer import OrganizerProfile
    from app.db.models.profile import ParticipantHobby, ParticipantProfile, ParticipantTopic


class User(Base):
    """Core User entity representing an authenticated participant identity."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "username ~* '^[a-zA-Z0-9_-]{3,50}$'",
            name="ck_users_username_format",
        ),
        Index("uq_users_username_lower", func.lower("username"), unique=True),
        Index("uq_users_email_lower", func.lower("email"), unique=True),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=func.false(),
        nullable=False,
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
    profile: Mapped[Optional["ParticipantProfile"]] = relationship(
        "ParticipantProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    hobbies: Mapped[List["ParticipantHobby"]] = relationship(
        "ParticipantHobby",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    topics: Mapped[List["ParticipantTopic"]] = relationship(
        "ParticipantTopic",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    bookmarks: Mapped[List["BookmarkedSession"]] = relationship(
        "BookmarkedSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    session_decisions: Mapped[List["SessionIntentDecision"]] = relationship(
        "SessionIntentDecision",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    organizer_profile: Mapped[Optional["OrganizerProfile"]] = relationship(
        "OrganizerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    organized_conferences: Mapped[List["Conference"]] = relationship(
        "Conference",
        back_populates="organizer",
        foreign_keys="Conference.organizer_id",
    )

    def __repr__(self) -> str:
        # Strictly exclude password_hash and contact details from representation
        return f"<User id={self.id} username={self.username!r} is_active={self.is_active}>"
