"""Conference Chatroom domain models in schema agenda for the Common Open Lounge."""

import enum
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.agenda import Conference


class ChatroomSenderType(str, enum.Enum):
    USER = "USER"
    REPRESENTATIVE = "REPRESENTATIVE"
    HOST = "HOST"
    SYSTEM = "SYSTEM"


class ChatroomMessageKind(str, enum.Enum):
    CHAT = "CHAT"
    WELCOME = "WELCOME"
    TRAFFIC_ALERT = "TRAFFIC_ALERT"
    WEATHER_UPDATE = "WEATHER_UPDATE"
    TEA_ANNOUNCEMENT = "TEA_ANNOUNCEMENT"
    SESSION_BUZZ = "SESSION_BUZZ"


class ConferenceChatroom(Base):
    """Domain model for open public conference networking lounges."""

    __tablename__ = "conference_chatrooms"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_conference_chatrooms_slug"),
        CheckConstraint("length(trim(name)) >= 3", name="ck_chatroom_name_length"),
        Index("idx_chatrooms_conference", "conference_id"),
        Index("idx_chatrooms_active", "is_active"),
        {"schema": "agenda"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    conference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="The Networking Lounge",
    )
    slug: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="networking-lounge",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default="Open public lounge for all delegates to hang out, share thoughts, and stay updated during breaks.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    ambient_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        default=20,
        server_default="20",
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
    conference: Mapped[Optional["Conference"]] = relationship(
        "Conference",
        foreign_keys=[conference_id],
        lazy="selectin",
    )
    messages: Mapped[List["ChatroomMessage"]] = relationship(
        "ChatroomMessage",
        back_populates="chatroom",
        cascade="all, delete-orphan",
        order_by="ChatroomMessage.turn_index",
        lazy="selectin",
    )
    presences: Mapped[List["ChatroomPresence"]] = relationship(
        "ChatroomPresence",
        back_populates="chatroom",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChatroomMessage(Base):
    """Chronological message within a public conference chatroom."""

    __tablename__ = "chatroom_messages"
    __table_args__ = (
        CheckConstraint("turn_index >= 0", name="ck_chatroom_msg_turn_index"),
        CheckConstraint("length(trim(content)) >= 1 AND length(content) <= 4000", name="ck_chatroom_msg_content_len"),
        Index("idx_chatroom_messages_room_turn", "chatroom_id", "turn_index"),
        Index("idx_chatroom_messages_created", "created_at"),
        {"schema": "agenda"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    chatroom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.conference_chatrooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ChatroomSenderType.USER.value,
    )
    sender_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    message_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ChatroomMessageKind.CHAT.value,
    )
    turn_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    chatroom: Mapped["ConferenceChatroom"] = relationship(
        "ConferenceChatroom",
        back_populates="messages",
        lazy="selectin",
    )
    sender: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[sender_id],
        lazy="selectin",
    )


class ChatroomPresence(Base):
    """Presence and active membership in the conference chatroom."""

    __tablename__ = "chatroom_presences"
    __table_args__ = (
        UniqueConstraint("chatroom_id", "user_id", name="uq_chatroom_presence_user"),
        Index("idx_chatroom_presences_room_user", "chatroom_id", "user_id"),
        {"schema": "agenda"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    chatroom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agenda.conference_chatrooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Relationships
    chatroom: Mapped["ConferenceChatroom"] = relationship(
        "ConferenceChatroom",
        back_populates="presences",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )
