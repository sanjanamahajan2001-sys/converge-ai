"""Group Conversation domain models for Thematic Networking Circles."""
import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
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
from app.db.models.conversation import MessageSenderType


class GroupStatus(str, enum.Enum):
    """Lifecycle status of a Thematic Networking Circle."""

    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GroupRole(str, enum.Enum):
    """Role of a member within a group conversation."""

    HOST = "HOST"
    MEMBER = "MEMBER"


class GroupConversation(Base):
    """Domain entity governing multi-participant Thematic Networking Circles."""

    __tablename__ = "group_conversations"
    __table_args__ = (
        CheckConstraint(
            "max_turns >= 20 AND max_turns <= 50",
            name="ck_group_max_turns_range",
        ),
        CheckConstraint(
            "current_turn >= 0 AND current_turn <= max_turns",
            name="ck_group_current_turn_range",
        ),
        CheckConstraint(
            "length(trim(title)) >= 3 AND length(title) <= 120",
            name="ck_group_title_length",
        ),
        Index("ix_group_conversations_host", "host_id"),
        Index("ix_group_conversations_status", "status"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    topic_context: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[GroupStatus] = mapped_column(
        Enum(GroupStatus, name="group_status", schema="core"),
        default=GroupStatus.ACTIVE,
        server_default="ACTIVE",
        nullable=False,
    )
    max_turns: Mapped[int] = mapped_column(
        Integer,
        default=25,
        server_default="25",
        nullable=False,
    )
    current_turn: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
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
    concluded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    host: Mapped["User"] = relationship(
        "User",
        foreign_keys=[host_id],
        lazy="selectin",
    )
    members: Mapped[List["GroupMember"]] = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="GroupMember.joined_at",
        lazy="selectin",
    )
    messages: Mapped[List["GroupMessage"]] = relationship(
        "GroupMessage",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="GroupMessage.turn_index",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<GroupConversation id={self.id} title={self.title!r} host_id={self.host_id} status={self.status}>"


class GroupMember(Base):
    """Participant membership within a Thematic Networking Circle."""

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member_user"),
        Index("ix_group_members_user", "user_id"),
        Index("ix_group_members_group", "group_id"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.group_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[GroupRole] = mapped_column(
        Enum(GroupRole, name="group_role", schema="core"),
        default=GroupRole.MEMBER,
        server_default="MEMBER",
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_read_turn: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    # Relationships
    group: Mapped["GroupConversation"] = relationship(
        "GroupConversation",
        back_populates="members",
        lazy="selectin",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<GroupMember id={self.id} group_id={self.group_id} user_id={self.user_id} role={self.role}>"


class GroupMessage(Base):
    """Chronological, append-only message turn within a Group Conversation."""

    __tablename__ = "group_messages"
    __table_args__ = (
        CheckConstraint("turn_index >= 0", name="ck_group_msg_turn_index_nonnegative"),
        CheckConstraint(
            "length(trim(content)) >= 1 AND length(content) <= 4000",
            name="ck_group_msg_content_length",
        ),
        CheckConstraint(
            "((sender_type = 'SYSTEM' AND sender_id IS NULL) OR "
            "(sender_type IN ('PARTICIPANT', 'AGENT') AND sender_id IS NOT NULL))",
            name="ck_group_msg_sender_presence",
        ),
        UniqueConstraint("group_id", "turn_index", name="uq_group_msg_turn"),
        Index("ix_group_messages_group_turn", "group_id", "turn_index"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.group_conversations.id", ondelete="CASCADE"),
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    group: Mapped["GroupConversation"] = relationship(
        "GroupConversation",
        back_populates="messages",
        lazy="selectin",
    )
    sender: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[sender_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<GroupMessage id={self.id} group_id={self.group_id} turn={self.turn_index} sender={self.sender_id}>"
