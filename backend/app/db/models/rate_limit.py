"""Rate limiting model for authentication endpoints in schema core."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginRateLimit(Base):
    """Tracks failed login attempts per hashed client IP in schema core."""

    __tablename__ = "login_rate_limits"
    __table_args__ = (
        Index("idx_rate_limits_locked_until", "locked_until"),
        {"schema": "core"},
    )

    ip_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<LoginRateLimit ip_hash={self.ip_hash[:8]}... attempts={self.attempt_count} locked_until={self.locked_until}>"
