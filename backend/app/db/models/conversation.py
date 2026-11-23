"""Conversation and Message models in schema core (P5-WS2, GAP-06)."""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class ConversationStatus(str, enum.Enum):
    """Canonical lifecycle states for participant conversations."""

    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ConversationOutcome(str, enum.Enum):
    """Terminal outcomes governing pair cooldown periods (GAP-06)."""

    PROPOSAL_GENERATED = "PROPOSAL_GENERATED"
    COMPLETED_WITHOUT_PROPOSAL = "COMPLETED_WITHOUT_PROPOSAL"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class MessageSenderType(str, enum.Enum):
    """Origin of a conversation message."""

    PARTICIPANT = "PARTICIPANT"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class Conversation(Base):
    """Authoritative domain entity governing one-to-one participant dialogue."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("initiator_id != target_id", name="ck_distinct_participants"),
        CheckConstraint(
            "((status IN ('COMPLETED', 'CANCELLED', 'EXPIRED') AND concluded_at IS NOT NULL AND terminal_outcome IS NOT NULL) OR "
            "(status IN ('INVITED', 'ACTIVE') AND concluded_at IS NULL AND terminal_outcome IS NULL))",
            name="ck_terminal_outcome_consistency",
        ),
        Index(
            "uq_active_conversation_pair",
            func.least(column("initiator_id"), column("target_id")),
            func.greatest(column("initiator_id"), column("target_id")),
            unique=True,
            postgresql_where=text("status IN ('INVITED', 'ACTIVE')"),
        ),
        Index("ix_conversations_initiator", "initiator_id"),
        Index("ix_conversations_target", "target_id"),
        Index("ix_conversations_status", "status"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status", schema="core"),
        default=ConversationStatus.INVITED,
        server_default="INVITED",
        nullable=False,
    )
    match_score: Mapped[Optional[float]] = mapped_column(
        Numeric(precision=5, scale=4),
        nullable=True,
    )
    terminal_outcome: Mapped[Optional[ConversationOutcome]] = mapped_column(
        Enum(ConversationOutcome, name="conversation_outcome", schema="core"),
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
    concluded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    initiator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[initiator_id],
        lazy="selectin",
    )
    target: Mapped["User"] = relationship(
        "User",
        foreign_keys=[target_id],
        lazy="selectin",
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.turn_index",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} initiator={self.initiator_id} target={self.target_id} status={self.status}>"


class Message(Base):
    """Chronological, append-only message turn within a conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("turn_index >= 0", name="ck_turn_index_nonnegative"),
        CheckConstraint("turn_index < 30", name="ck_turn_index_limit"),
        CheckConstraint("length(trim(content)) >= 1 AND length(content) <= 4000", name="ck_content_length"),
        CheckConstraint(
            "((sender_type = 'SYSTEM' AND sender_id IS NULL) OR "
            "(sender_type IN ('PARTICIPANT', 'AGENT') AND sender_id IS NOT NULL))",
            name="ck_sender_presence",
        ),
        UniqueConstraint("conversation_id", "turn_index", name="uq_conversation_turn"),
        Index("ix_messages_conversation_turn", "conversation_id", "turn_index"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_type: Mapped[MessageSenderType] = mapped_column(
        Enum(MessageSenderType, name="message_sender_type", schema="core"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        default="TEXT",
        server_default="TEXT",
        nullable=False,
    )
    location_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    sender: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[sender_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} conv={self.conversation_id} turn={self.turn_index} sender={self.sender_type}>"
