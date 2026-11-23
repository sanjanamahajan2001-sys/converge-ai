"""Audit log database model in schema core."""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """Immutable security audit log record in schema core (GAP-10)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_created", text("created_at DESC")),
        Index("idx_audit_action", "action_type"),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_username: Mapped[str] = mapped_column(String(50), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    event_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action_type!r} "
            f"actor={self.actor_username!r} resource={self.resource_type!r}:{self.resource_id!r}>"
        )
