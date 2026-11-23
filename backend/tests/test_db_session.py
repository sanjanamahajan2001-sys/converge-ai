"""Tests for SQLAlchemy async engine and session lifecycle."""

import pytest
from app.core.config import Settings, get_settings
from app.db.session import DatabaseManager, create_engine_from_settings, get_db, db_manager
from sqlalchemy import text

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL


def test_engine_creation_none_when_unconfigured():
    """Verify engine is None if DATABASE_URL is not set."""
    cfg = Settings(DATABASE_URL=None)
    engine = create_engine_from_settings(cfg)
    assert engine is None


def test_engine_creation_configured():
    """Verify engine is created with pool settings when DATABASE_URL is set."""
    cfg = Settings(DATABASE_URL=TEST_DB_URL)
    engine = create_engine_from_settings(cfg)
    assert engine is not None
    assert engine.pool.size() == cfg.DB_POOL_SIZE


@pytest.mark.asyncio
async def test_database_manager_lifecycle():
    """Verify DatabaseManager initializes and disposes cleanly."""
    cfg = Settings(DATABASE_URL=TEST_DB_URL)
    manager = DatabaseManager(cfg)
    manager.initialize()

    assert manager.engine is not None
    assert manager.session_factory is not None

    is_connected = await manager.check_connectivity(timeout_seconds=2.0)
    assert is_connected is True

    await manager.close()
    assert manager.engine is None
    assert manager.session_factory is None


@pytest.mark.asyncio
async def test_database_manager_broken_connection():
    """Verify check_connectivity fails safely without crashing on unreachable host."""
    cfg = Settings(DATABASE_URL="postgresql+asyncpg://invalid:invalid@127.0.0.1:54329/invalid_db")
    manager = DatabaseManager(cfg)
    manager.initialize()

    is_connected = await manager.check_connectivity(timeout_seconds=0.5)
    assert is_connected is False

    await manager.close()


@pytest.mark.asyncio
async def test_get_db_raises_when_uninitialized():
    """Verify get_db dependency raises RuntimeError when session_factory is uninitialized."""
    original_factory = db_manager.session_factory
    db_manager.session_factory = None
    try:
        gen = get_db()
        with pytest.raises(RuntimeError, match="Database session factory is not initialized"):
            await anext(gen)
    finally:
        db_manager.session_factory = original_factory


@pytest.mark.asyncio
async def test_get_db_session_lifecycle():
    """Verify get_db dependency yields a valid session and queries cleanly."""
    cfg = Settings(DATABASE_URL=TEST_DB_URL)
    db_manager._settings = cfg
    db_manager.initialize()

    gen = get_db()
    session = await anext(gen)
    assert session is not None

    res = await session.execute(text("SELECT 1"))
    assert res.scalar() == 1

    try:
        await anext(gen)
    except StopAsyncIteration:
        pass
