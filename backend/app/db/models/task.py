"""Task and TaskAttempt domain models in schema a2a (Phase 6, GAP-03, GAP-06)."""

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
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.user import User


class TaskStatus(str, enum.Enum):
    """Lifecycle states for background agent tasks."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(Base):
    """Durable background agent execution task in schema a2a."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts",
            name="ck_task_attempt_count_bounds",
        ),
        CheckConstraint(
            "max_attempts >= 1 AND max_attempts <= 10",
            name="ck_task_max_attempts_bounds",
        ),
        CheckConstraint(
            "((status = 'RUNNING' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR (status != 'RUNNING'))",
            name="ck_task_lease_consistency",
        ),
        CheckConstraint(
            "((status IN ('SUCCEEDED', 'FAILED', 'CANCELLED') AND completed_at IS NOT NULL) OR (status NOT IN ('SUCCEEDED', 'FAILED', 'CANCELLED')))",
            name="ck_task_terminal_consistency",
        ),
        Index("ix_tasks_claim_queue", "status", "scheduled_at"),
        Index("ix_tasks_conversation_id", "conversation_id"),
        Index("ix_tasks_initiator_id", "initiator_id"),
        Index("ix_tasks_lease_expiry", "status", "lease_expires_at"),
        {"schema": "a2a"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    task_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.conversations.id", ondelete="CASCADE"),
        nullable=True,
    )
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", schema="a2a"),
        default=TaskStatus.PENDING,
        server_default="PENDING",
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3",
        nullable=False,
    )
    lease_owner: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_category: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    error_detail: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
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
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation",
        lazy="selectin",
    )
    initiator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[initiator_id],
        lazy="selectin",
    )
    target: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[target_id],
        lazy="selectin",
    )
    attempts: Mapped[List["TaskAttempt"]] = relationship(
        "TaskAttempt",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskAttempt.attempt_number",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} type={self.task_type} status={self.status} attempts={self.attempt_count}>"


class TaskAttempt(Base):
    """Individual execution attempt history log for a background agent task."""

    __tablename__ = "task_attempts"
    __table_args__ = (
        UniqueConstraint("task_id", "attempt_number", name="uq_task_attempt_number"),
        Index("ix_task_attempts_task_id", "task_id"),
        {"schema": "a2a"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("a2a.tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    worker_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", schema="a2a"),
        nullable=False,
    )
    error_category: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    error_detail: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="attempts",
    )

    def __repr__(self) -> str:
        return f"<TaskAttempt task={self.task_id} attempt={self.attempt_number} status={self.status}>"
