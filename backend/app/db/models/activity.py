"""User Activity Event database model for privacy-conscious analytics in schema core."""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserActivityEvent(Base):
    """User activity event entity tracking feature clicks, visits, and interactions."""

    __tablename__ = "user_activity_events"
    __table_args__ = (
        Index("idx_activity_user_created", "user_id", text("created_at DESC")),
        Index("idx_activity_event_type", "event_type", text("created_at DESC")),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
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
            f"<UserActivityEvent id={self.id} user={self.user_id} "
            f"event={self.event_type!r} feature={self.feature_name!r}>"
        )
