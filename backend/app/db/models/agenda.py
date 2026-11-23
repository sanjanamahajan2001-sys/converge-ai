"""Agenda and Conference domain models in schema agenda (GAP-09, GAP-10)."""

import enum
import uuid
from datetime import date, datetime, time
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class ConferenceFormat(str, enum.Enum):
    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"


class ConferenceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class SessionType(str, enum.Enum):
    """Category of scheduled conference session or agenda break."""

    KEYNOTE = "KEYNOTE"
    PANEL = "PANEL"
    TECHNICAL_SESSION = "TECHNICAL_SESSION"
    WORKSHOP = "WORKSHOP"
    TEA_BREAK = "TEA_BREAK"
    LUNCH_BREAK = "LUNCH_BREAK"
    NETWORKING_RECEPTION = "NETWORKING_RECEPTION"
    EXHIBITION_WALK = "EXHIBITION_WALK"


class ConferenceLiveStateEnum(str, enum.Enum):
    """Real-time active state of the conference venue."""

    IN_SESSION = "IN_SESSION"
    TEA_BREAK = "TEA_BREAK"
    LUNCH_BREAK = "LUNCH_BREAK"
    NETWORKING_RECEPTION = "NETWORKING_RECEPTION"
    FREE_TIME = "FREE_TIME"


class BreakType(str, enum.Enum):
    """Specific refreshment or networking break classification."""

    TEA_COFFEE = "TEA_COFFEE"
    LUNCH = "LUNCH"
    CASUAL_NETWORKING = "CASUAL_NETWORKING"
    EXHIBITION = "EXHIBITION"
    NONE = "NONE"


class Conference(Base):
    """Conference/Event entity with timezone, venue, format, and lifecycle tracking (GAP-09, Phase 1 Organizer)."""

    __tablename__ = "conferences"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_conference_dates"),
        CheckConstraint("length(trim(title)) > 0", name="ck_conference_title_nonempty"),
        CheckConstraint("length(trim(venue_name)) > 0", name="ck_conference_venue_nonempty"),
        CheckConstraint("length(trim(timezone)) > 0", name="ck_conference_timezone_nonempty"),
        Index("idx_conferences_organizer_id", "organizer_id"),
        Index("idx_conferences_status", "status"),
        Index("idx_conferences_dates", "start_date", "end_date"),
        {"schema": "agenda"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    organizer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ConferenceFormat.IN_PERSON.value,
        server_default=ConferenceFormat.IN_PERSON.value,
    )
    venue_name: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        server_default="UTC",
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    registration_opens_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_closes_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meeting_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Location Details
    formatted_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    place_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Approval & Publication Lifecycle
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ConferenceStatus.PUBLISHED.value,
        server_default=ConferenceStatus.PUBLISHED.value,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
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
    organizer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[organizer_id],
        back_populates="organized_conferences",
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by],
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="conference",
        cascade="all, delete-orphan",
        order_by="Session.start_time",
    )
    review_logs: Mapped[List["ConferenceReviewLog"]] = relationship(
        "ConferenceReviewLog",
        back_populates="conference",
        cascade="all, delete-orphan",
        order_by="ConferenceReviewLog.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Conference id={self.id} title={self.title!r} timezone={self.timezone!r} active={self.is_active}>"


class Session(Base):
    """Conference session scheduled within a conference venue (GAP-09)."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_session_times"),
        CheckConstraint("length(trim(title)) > 0", name="ck_session_title_nonempty"),
        CheckConstraint("length(trim(hall_room)) > 0", name="ck_session_hall_nonempty"),
        UniqueConstraint(
            "conference_id",
            "hall_room",
            "start_time",
            name="uq_session_room_starttime",
        ),
        Index("idx_sessions_conference_id", "conference_id"),
        Index("idx_sessions_timerange", "start_time", "end_time"),
        Index("idx_sessions_track", "track_name"),
        Index("idx_sessions_type", "session_type"),
        Index("idx_sessions_import_batch", "import_batch_id"),
        {"schema": "agenda"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    conference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_type: Mapped[str] = mapped_column(
        PG_ENUM(
            "KEYNOTE",
            "TECHNICAL_SESSION",
            "PANEL_DISCUSSION",
            "WORKSHOP",
            "TEA_BREAK",
            "LUNCH_BREAK",
            "NETWORKING_RECEPTION",
            name="session_type",
            schema="agenda",
            create_type=False,
            values_callable=lambda x: [e.value for e in x] if hasattr(x, '__members__') else x,
        ),
        default=SessionType.TECHNICAL_SESSION.value,
        server_default=SessionType.TECHNICAL_SESSION.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    speaker_names: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    track_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hall_room: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    import_batch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
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
    conference: Mapped["Conference"] = relationship("Conference", back_populates="sessions")
    bookmarks: Mapped[List["BookmarkedSession"]] = relationship(
        "BookmarkedSession",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    intent_decisions: Mapped[List["SessionIntentDecision"]] = relationship(
        "SessionIntentDecision",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Session id={self.id} title={self.title!r} hall={self.hall_room!r} "
            f"start={self.start_time.isoformat()} cancelled={self.is_cancelled}>"
        )


class BookmarkedSession(Base):
    """Participant session bookmark linkage (GAP-10 cascade on deletion)."""

    __tablename__ = "bookmarked_sessions"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "session_id", name="pk_bookmarked_sessions"),
        {"schema": "agenda"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    session: Mapped["Session"] = relationship("Session", back_populates="bookmarks")

    def __repr__(self) -> str:
        return f"<BookmarkedSession user_id={self.user_id} session_id={self.session_id}>"


class SessionIntentDecisionState(str, enum.Enum):
    ATTENDING = "ATTENDING"
    DECLINED = "DECLINED"
    UNDECIDED = "UNDECIDED"


class SessionIntentDecision(Base):
    """Participant explicit session attendance decision (AC-WS8, Manager Consent & Memory Requirement)."""

    __tablename__ = "session_intent_decisions"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_session_intent_user_session"),
        CheckConstraint("decision IN ('ATTENDING', 'DECLINED', 'UNDECIDED')", name="ck_session_intent_decision_state"),
        {"schema": "agenda"},
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
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionIntentDecisionState.UNDECIDED.value,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REPRESENTATIVE_PROMPT",
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
    user: Mapped["User"] = relationship("User", back_populates="session_decisions")
    session: Mapped["Session"] = relationship("Session", back_populates="intent_decisions")

    def __repr__(self) -> str:
        return f"<SessionIntentDecision user_id={self.user_id} session_id={self.session_id} decision={self.decision}>"


class ConferenceReviewLog(Base):
    """Immutable audit trail for conference submission, review, approval and rejection events."""

    __tablename__ = "conference_review_logs"
    __table_args__ = (
        Index("idx_review_logs_conference_created", "conference_id", text("created_at DESC")),
        {"schema": "agenda"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    from_status: Mapped[str] = mapped_column(String(30), nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conference: Mapped["Conference"] = relationship("Conference", back_populates="review_logs")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self) -> str:
        return f"<ConferenceReviewLog id={self.id} conf={self.conference_id} {self.from_status}->{self.to_status}>"


class ConferenceLiveState(Base):
    """Conference real-time temporal and physical state tracker (Phase 1 Temporal Matching)."""

    __tablename__ = "conference_live_states"
    __table_args__ = (
        UniqueConstraint("conference_id", name="uq_conference_live_state"),
        Index("ix_conf_live_state_conf_id", "conference_id"),
        Index("ix_conf_live_state_active", "is_active", "current_state"),
        {"schema": "agenda"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    conference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    active_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_state: Mapped[str] = mapped_column(
        PG_ENUM(
            "IN_SESSION",
            "TEA_BREAK",
            "LUNCH_BREAK",
            "NETWORKING_RECEPTION",
            "FREE_TIME",
            name="conference_live_state",
            schema="agenda",
            create_type=False,
        ),
        default=ConferenceLiveStateEnum.IN_SESSION.value,
        server_default=ConferenceLiveStateEnum.IN_SESSION.value,
        nullable=False,
    )
    custom_state_label: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    break_type: Mapped[str] = mapped_column(
        PG_ENUM(
            "TEA_COFFEE",
            "LUNCH",
            "CASUAL_NETWORKING",
            "EXHIBITION",
            "NONE",
            name="break_type",
            schema="agenda",
            create_type=False,
        ),
        default=BreakType.NONE.value,
        server_default=BreakType.NONE.value,
        nullable=False,
    )
    designated_location: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    announcement_banner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amenities_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    triggered_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
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
    conference: Mapped["Conference"] = relationship("Conference")
    active_session: Mapped[Optional["Session"]] = relationship("Session", foreign_keys=[active_session_id])
    triggered_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[triggered_by_user_id])

    def __repr__(self) -> str:
        return f"<ConferenceLiveState conf={self.conference_id} state={self.current_state} break={self.break_type} active={self.is_active}>"



