"""Administrative account bootstrap and credential synchronization (Phase 2)."""

import bcrypt
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.db.models.user import User

logger = logging.getLogger(__name__)


async def ensure_admin_user(db: AsyncSession) -> None:
    """Ensure administrator user exists with credentials matching ADMIN_PASSWORD from .env."""
    settings = get_settings()
    if not settings.ADMIN_PASSWORD:
        return

    admin_username = settings.ADMIN_USERNAME.strip()
    admin_pwd = settings.ADMIN_PASSWORD.strip()

    stmt = select(User).where(User.username == admin_username)
    result = await db.execute(stmt)
    admin_user = result.scalar_one_or_none()

    # Generate bcrypt hash directly (work factor 12) to support alphanumeric env passwords
    password_hash = bcrypt.hashpw(
        admin_pwd.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    if not admin_user:
        admin_user = User(
            username=admin_username,
            email=f"{admin_username}@converge.ai",
            full_name="Converge Administrator",
            password_hash=password_hash,
            is_active=True,
            is_admin=True,
        )
        db.add(admin_user)
        await db.commit()
        logger.info("Provisioned new administrative user '%s'", admin_username)
    else:
        # Keep password & admin flag synchronized with environment
        admin_user.is_admin = True
        admin_user.password_hash = password_hash
        admin_user.is_active = True
        await db.commit()
        logger.info("Synchronized administrative credentials for '%s'", admin_username)


if __name__ == "__main__":
    import asyncio
    from app.db.session import db_manager

    async def _cli_main():
        db_manager.initialize()
        async with db_manager.session_factory() as session:
            await ensure_admin_user(session)
        await db_manager.close()
        print("Admin user synchronization finished successfully.")

    asyncio.run(_cli_main())
