"""Participant Profile and Interest models in schema core."""
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.schemas.profile import AvailabilityStatus, ParticipationIntent

if TYPE_CHECKING:
    from app.db.models.user import User


class ParticipantProfile(Base):
    """Core Participant Profile entity representing conference networking preferences."""

    __tablename__ = "participant_profiles"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    intent: Mapped[ParticipationIntent] = mapped_column(
        SQLEnum(
            ParticipationIntent,
            name="participation_intent",
            schema="core",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ParticipationIntent.NETWORKING,
        server_default="NETWORKING",
    )
    bio_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    availability: Mapped[AvailabilityStatus] = mapped_column(
        SQLEnum(
            AvailabilityStatus,
            name="availability_status",
            schema="core",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AvailabilityStatus.AVAILABLE,
        server_default="AVAILABLE",
    )
    allow_agent_matching: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    allow_agent_dm_initiation: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    contact_sharing_policy: Mapped[str] = mapped_column(
        String(50),
        default="ASK_HUMAN_FIRST",
        server_default=text("'ASK_HUMAN_FIRST'"),
        nullable=False,
    )
    current_mood: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mood_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
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
    user: Mapped["User"] = relationship("User", back_populates="profile")

    @property
    def active_mood(self) -> Optional[str]:
        """Return self-declared mood if updated within the last 24 hours, else None."""
        if not self.current_mood or not self.mood_updated_at:
            return None
        now = datetime.now(timezone.utc)
        updated = self.mood_updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if (now - updated).total_seconds() > 86400:
            return None
        return self.current_mood

    @property
    def id(self) -> uuid.UUID:
        """Surrogate accessor matching user_id for uniform contract reference."""
        return self.user_id

    @property
    def hobbies(self) -> List[str]:
        """Convenience property extracting hobby names from related user."""
        if self.user and self.user.hobbies:
            return [h.hobby_name for h in self.user.hobbies]
        return []

    @property
    def topics(self) -> List[str]:
        """Convenience property extracting topic keywords from related user."""
        if self.user and self.user.topics:
            return [t.topic_keyword for t in self.user.topics]
        return []

    def __repr__(self) -> str:
        intent_val = self.intent.value if hasattr(self.intent, "value") else self.intent
        avail_val = self.availability.value if hasattr(self.availability, "value") else self.availability
        return (
            f"<ParticipantProfile user_id={self.user_id} "
            f"intent={intent_val} availability={avail_val} matching={self.allow_agent_matching}>"
        )


class ParticipantHobby(Base):
    """Curated or custom participant hobby/interest preference in schema core."""

    __tablename__ = "participant_hobbies"
    __table_args__ = (
        UniqueConstraint("user_id", "hobby_name", name="uq_user_hobby"),
        CheckConstraint("length(trim(hobby_name)) > 0", name="ck_hobby_name_not_empty"),
        Index("idx_hobbies_user_id", "user_id"),
        Index("idx_hobbies_normalized", func.lower("hobby_name")),
        Index("uq_hobbies_user_normalized", "user_id", func.lower("hobby_name"), unique=True),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    hobby_name: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="hobbies")

    def __repr__(self) -> str:
        return f"<ParticipantHobby id={self.id} user_id={self.user_id} hobby_name={self.hobby_name!r}>"


class ParticipantTopic(Base):
    """Participant technical focus or domain topic keyword in schema core."""

    __tablename__ = "participant_topics"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_keyword", name="uq_user_topic"),
        CheckConstraint("length(trim(topic_keyword)) > 0", name="ck_topic_keyword_not_empty"),
        Index("idx_topics_user_id", "user_id"),
        Index("idx_topics_normalized", func.lower("topic_keyword")),
        Index("uq_topics_user_normalized", "user_id", func.lower("topic_keyword"), unique=True),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_keyword: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="topics")

    def __repr__(self) -> str:
        return f"<ParticipantTopic id={self.id} user_id={self.user_id} topic_keyword={self.topic_keyword!r}>"
