"""SQLAlchemy asynchronous engine, session factory, and lifecycle management."""

import asyncio
from typing import AsyncIterator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from app.core.config import Settings, get_settings


def create_engine_from_settings(settings: Settings) -> Optional[AsyncEngine]:
    """Create async SQLAlchemy engine if DATABASE_URL is configured."""
    if not settings.DATABASE_URL:
        return None

    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        echo=settings.DB_ECHO,
        future=True,
    )


class DatabaseManager:
    """Manages application database engine and session factory lifecycle."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize engine and session factory if DATABASE_URL is available."""
        if self._initialized:
            return

        if self._settings.DATABASE_URL:
            self.engine = create_engine_from_settings(self._settings)
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
                class_=AsyncSession,
            )
        self._initialized = True

    async def close(self) -> None:
        """Dispose database engine cleanly on application shutdown."""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
        self._initialized = False

    async def check_connectivity(self, timeout_seconds: float = 2.0) -> bool:
        """Execute bounded SELECT 1 ping to check database connectivity."""
        if self.engine is None:
            return False

        try:
            async with asyncio.timeout(timeout_seconds):
                async with self.engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    scalar = result.scalar()
                    return scalar == 1
        except Exception:
            return False


# Global manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an isolated AsyncSession per request."""
    if not db_manager.session_factory:
        raise RuntimeError(
            "Database session factory is not initialized. "
            "Ensure DATABASE_URL is configured."
        )

    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for explicit domain naming
get_db_session = get_db
