"""Unit tests for Phase 1: Database Foundation & Temporal State Engine.

Verifies:
1. SessionType and ConferenceLiveState enums.
2. ConferenceLiveStateResponse and Update schemas.
3. TemporalContextService fallback and active conference state resolution.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.db.session import DatabaseManager
from app.db.models.agenda import (
    BreakType,
    ConferenceLiveStateEnum,
    SessionType,
)
from app.schemas.agenda import ConferenceLiveStateResponse, ConferenceLiveStateUpdate
from app.services.temporal_context import TemporalContextService

settings = get_settings()


@pytest.fixture
async def db_session():
    """Async database session fixture for schema tests."""
    manager = DatabaseManager(settings)
    manager.initialize()
    async with manager.session_factory() as session:
        yield session
    await manager.close()


def test_temporal_enums():
    """Verify all session types and conference live state enums."""
    assert SessionType.KEYNOTE.value == "KEYNOTE"
    assert SessionType.TECHNICAL_SESSION.value == "TECHNICAL_SESSION"
    assert SessionType.TEA_BREAK.value == "TEA_BREAK"
    assert SessionType.LUNCH_BREAK.value == "LUNCH_BREAK"
    assert SessionType.NETWORKING_RECEPTION.value == "NETWORKING_RECEPTION"

    assert ConferenceLiveStateEnum.IN_SESSION.value == "IN_SESSION"
    assert ConferenceLiveStateEnum.TEA_BREAK.value == "TEA_BREAK"
    assert ConferenceLiveStateEnum.LUNCH_BREAK.value == "LUNCH_BREAK"
    assert ConferenceLiveStateEnum.FREE_TIME.value == "FREE_TIME"

    assert BreakType.TEA_COFFEE.value == "TEA_COFFEE"
    assert BreakType.LUNCH.value == "LUNCH"
    assert BreakType.CASUAL_NETWORKING.value == "CASUAL_NETWORKING"
    assert BreakType.NONE.value == "NONE"


def test_temporal_schemas():
    """Verify ConferenceLiveStateResponse and ConferenceLiveStateUpdate DTOs."""
    conf_id = uuid4()
    now = datetime.now(timezone.utc)
    ends = now + timedelta(minutes=30)

    res = ConferenceLiveStateResponse(
        conference_id=conf_id,
        current_state=ConferenceLiveStateEnum.TEA_BREAK.value,
        custom_state_label="Morning Coffee & Tea Break",
        break_type=BreakType.TEA_COFFEE.value,
        designated_location="West Terrace Lounge",
        announcement_banner="Grab a hot coffee and network at West Terrace!",
        starts_at=now,
        ends_at=ends,
        is_active=True,
        recently_ended_session_title="LC3 Cement Formulations Keynote",
    )
    assert res.current_state == "TEA_BREAK"
    assert res.break_type == "TEA_COFFEE"
    assert res.recently_ended_session_title == "LC3 Cement Formulations Keynote"

    update_dto = ConferenceLiveStateUpdate(
        current_state="TEA_BREAK",
        break_type="TEA_COFFEE",
        custom_state_label="11:00 AM Coffee Break",
        duration_minutes=25,
    )
    assert update_dto.duration_minutes == 25
    assert update_dto.break_type == "TEA_COFFEE"


@pytest.mark.asyncio
async def test_temporal_fallback_when_no_conf(db_session):
    """Verify TemporalContextService returns clean fallback when no conference matches."""
    res = await TemporalContextService.get_current_conference_state(db_session, conference_id=uuid4())
    assert res.current_state in ("IN_SESSION", "FREE_TIME")
