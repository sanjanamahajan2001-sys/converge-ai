"""Server-side user session database model in schema core (GAP-05)."""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class UserSession(Base):
    """Server-side session entity in schema core.

    Stores one-way SHA-256 cryptographic digests of bearer session tokens to prevent
    credential exposure even if the database table is read.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("idx_sessions_token_hash", "token_hash", unique=True),
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_expires_at", "expires_at"),
        Index("idx_sessions_revoked_at", "revoked_at"),
        {"schema": "core"},
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
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<UserSession id={self.id} user_id={self.user_id} "
            f"revoked={'yes' if self.revoked_at else 'no'} expires={self.expires_at}>"
        )
