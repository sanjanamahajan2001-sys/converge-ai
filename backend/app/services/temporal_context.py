"""Temporal context service for resolving real-time conference breaks and session momentum."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agenda import (
    Conference,
    ConferenceLiveState,
    ConferenceLiveStateEnum,
    BreakType,
    Session,
    SessionType,
)
from app.schemas.agenda import ConferenceLiveStateResponse, ConferenceLiveStateUpdate


class TemporalContextService:
    """Evaluates real-time conference schedule clock, manual break overrides, and session momentum."""

    @staticmethod
    async def get_active_conference(db: AsyncSession, conference_id: Optional[UUID] = None) -> Optional[Conference]:
        """Fetch the target or primary published conference."""
        if conference_id:
            stmt = select(Conference).where(Conference.id == conference_id)
            return await db.scalar(stmt)
        # Fetch the first active published conference
        stmt = (
            select(Conference)
            .where(Conference.is_active == True)
            .order_by(Conference.created_at.desc())
            .limit(1)
        )
        return await db.scalar(stmt)

    @classmethod
    async def get_current_conference_state(
        cls,
        db: AsyncSession,
        conference_id: Optional[UUID] = None,
        reference_time: Optional[datetime] = None,
    ) -> ConferenceLiveStateResponse:
        """Resolve the active temporal state: manual break override -> schedule clock -> default fallback."""
        now = reference_time or datetime.now(timezone.utc)
        conf = await cls.get_active_conference(db, conference_id)
        if not conf:
            # Fallback when no conference is configured
            return ConferenceLiveStateResponse(
                conference_id=conference_id or UUID("00000000-0000-0000-0000-000000000000"),
                current_state=ConferenceLiveStateEnum.IN_SESSION.value,
                break_type=BreakType.NONE.value,
                is_active=False,
            )

        # Calculate default conference day number (GAP-DayControl)
        calculated_day = 1
        if conf and conf.start_date:
            try:
                s_date = conf.start_date.date() if hasattr(conf.start_date, "date") else conf.start_date
                diff = (now.date() - s_date).days + 1
                calculated_day = max(1, min(diff, 2)) if diff > 0 else 1
            except Exception:
                calculated_day = 1

        # Check for recently concluded talk within last 45 minutes (momentum factor)
        forty_five_mins_ago = now - timedelta(minutes=45)
        recent_sess_stmt = select(Session).where(
            Session.conference_id == conf.id,
            Session.is_cancelled == False,
            Session.end_time <= now,
            Session.end_time >= forty_five_mins_ago,
        ).order_by(Session.end_time.desc()).limit(1)

        recent_sess = await db.scalar(recent_sess_stmt)
        recent_id = recent_sess.id if recent_sess else None
        recent_title = recent_sess.title if recent_sess else None

        # 1. Check for manual live override in agenda.conference_live_states
        state_stmt = select(ConferenceLiveState).where(
            ConferenceLiveState.conference_id == conf.id,
            ConferenceLiveState.is_active == True,
        )
        live_state = await db.scalar(state_stmt)

        if live_state:
            # Check if scheduled override has expired
            if live_state.ends_at and now > live_state.ends_at:
                live_state.is_active = False
                await db.commit()
                live_state = None
            else:
                effective_day = live_state.active_day or calculated_day
                return ConferenceLiveStateResponse(
                    id=live_state.id,
                    conference_id=conf.id,
                    active_session_id=live_state.active_session_id,
                    current_state=live_state.current_state,
                    custom_state_label=live_state.custom_state_label,
                    break_type=live_state.break_type,
                    designated_location=live_state.designated_location,
                    announcement_banner=live_state.announcement_banner,
                    active_day=effective_day,
                    starts_at=live_state.starts_at,
                    ends_at=live_state.ends_at,
                    is_active=True,
                    recently_ended_session_id=recent_id,
                    recently_ended_session_title=recent_title,
                )

        # 2. Check scheduled agenda.sessions for active break or talk
        active_sess_stmt = select(Session).where(
            Session.conference_id == conf.id,
            Session.is_cancelled == False,
            Session.start_time <= now,
            Session.end_time >= now,
        ).order_by(Session.start_time.asc()).limit(1)

        active_sess = await db.scalar(active_sess_stmt)

        if active_sess:
            sess_type = active_sess.session_type
            if sess_type == SessionType.TEA_BREAK.value:
                return ConferenceLiveStateResponse(
                    conference_id=conf.id,
                    active_session_id=active_sess.id,
                    current_state=ConferenceLiveStateEnum.TEA_BREAK.value,
                    custom_state_label=active_sess.title,
                    break_type=BreakType.TEA_COFFEE.value,
                    designated_location=active_sess.hall_room,
                    announcement_banner=f"Morning Tea & Refreshment Break is now active at {active_sess.hall_room}!",
                    starts_at=active_sess.start_time,
                    ends_at=active_sess.end_time,
                    is_active=True,
                    recently_ended_session_id=recent_id,
                    recently_ended_session_title=recent_title,
                    active_day=calculated_day,
                )
            elif sess_type == SessionType.LUNCH_BREAK.value:
                return ConferenceLiveStateResponse(
                    conference_id=conf.id,
                    active_session_id=active_sess.id,
                    current_state=ConferenceLiveStateEnum.LUNCH_BREAK.value,
                    custom_state_label=active_sess.title,
                    break_type=BreakType.LUNCH.value,
                    designated_location=active_sess.hall_room,
                    announcement_banner="Conference Lunch & Networking Break is now active!",
                    starts_at=active_sess.start_time,
                    ends_at=active_sess.end_time,
                    is_active=True,
                    recently_ended_session_id=recent_id,
                    recently_ended_session_title=recent_title,
                    active_day=calculated_day,
                )
            else:
                return ConferenceLiveStateResponse(
                    conference_id=conf.id,
                    active_session_id=active_sess.id,
                    current_state=ConferenceLiveStateEnum.IN_SESSION.value,
                    custom_state_label=active_sess.title,
                    break_type=BreakType.NONE.value,
                    designated_location=active_sess.hall_room,
                    starts_at=active_sess.start_time,
                    ends_at=active_sess.end_time,
                    is_active=True,
                    recently_ended_session_id=recent_id,
                    recently_ended_session_title=recent_title,
                    active_day=calculated_day,
                )

        # 4. Default state when between sessions or during free time
        return ConferenceLiveStateResponse(
            conference_id=conf.id,
            current_state=ConferenceLiveStateEnum.FREE_TIME.value,
            custom_state_label="Open Networking & Exhibition Hours",
            break_type=BreakType.CASUAL_NETWORKING.value,
            designated_location="Central Foyer & Exhibition Floor",
            is_active=True,
            recently_ended_session_id=recent_id,
            recently_ended_session_title=recent_title,
            active_day=calculated_day,
        )

    @classmethod
    async def set_conference_live_state(
        cls,
        db: AsyncSession,
        conference_id: UUID,
        payload: ConferenceLiveStateUpdate,
        triggered_by_user_id: Optional[UUID] = None,
    ) -> ConferenceLiveStateResponse:
        """Create or update the live temporal state override for a conference."""
        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(minutes=payload.duration_minutes)

        stmt = select(ConferenceLiveState).where(ConferenceLiveState.conference_id == conference_id)
        live_state = await db.scalar(stmt)

        # Announcement banner handling:
        # - If explicitly passed: empty string or "__CLEAR__" clears banner, otherwise use string directly
        # - If None: synthesize default banner from state/delays/weather
        if payload.announcement_banner is not None:
            cleaned_banner = payload.announcement_banner.strip()
            announcement = None if cleaned_banner in ("", "__CLEAR__") else cleaned_banner
        else:
            parts = []
            if payload.custom_state_label:
                parts.append(payload.custom_state_label)
            elif payload.current_state in ("TEA_BREAK", "LUNCH_BREAK"):
                parts.append(f"{payload.current_state.replace('_', ' ').title()} is underway")
            elif payload.current_state == "IN_SESSION":
                parts.append("Sessions are underway")
            elif payload.current_state == "GENERAL_ANNOUNCEMENT":
                parts.append("Live Summit Bulletin")
            else:
                parts.append(payload.current_state.replace("_", " ").title())

            if payload.designated_location:
                parts.append(f"at {payload.designated_location}")
            if payload.delay_minutes:
                parts.append(f"(Schedule +{payload.delay_minutes}m delay)")
            if payload.weather_override:
                parts.append(f"[{payload.weather_override}]")
            announcement = " • ".join(parts) if parts else None

        # Map GENERAL_ANNOUNCEMENT to valid database enum FREE_TIME
        db_state = payload.current_state
        custom_label = payload.custom_state_label
        if db_state == "GENERAL_ANNOUNCEMENT":
            db_state = ConferenceLiveStateEnum.FREE_TIME.value
            if not custom_label:
                custom_label = "Floor Announcement"

        # Determine criticality: check explicit flag or auto-infer from weather/danger terms
        criticality = (getattr(payload, "criticality", None) or "NORMAL").upper()
        text_check = f"{payload.announcement_banner or ''} {payload.weather_override or ''}".lower()
        if any(w in text_check for w in ["thunder", "storm", "lightning", "heavy rain", "emergency", "danger", "warning", "hazard", "evacuat"]):
            criticality = "CRITICAL"

        if criticality == "CRITICAL" and announcement:
            if not announcement.startswith("🚨"):
                announcement = f"🚨 [CRITICAL ALERT] {announcement}"

        if not live_state:
            live_state = ConferenceLiveState(
                conference_id=conference_id,
                active_session_id=payload.active_session_id,
                current_state=db_state,
                custom_state_label=custom_label,
                break_type=payload.break_type or BreakType.NONE.value,
                designated_location=payload.designated_location,
                announcement_banner=announcement,
                active_day=payload.active_day if (payload.active_day and payload.active_day > 0) else None,
                starts_at=now,
                ends_at=ends_at,
                is_active=True,
                triggered_by_user_id=triggered_by_user_id,
            )
            db.add(live_state)
        else:
            live_state.active_session_id = payload.active_session_id
            live_state.current_state = db_state
            live_state.custom_state_label = custom_label
            live_state.break_type = payload.break_type or BreakType.NONE.value
            live_state.designated_location = payload.designated_location
            live_state.announcement_banner = announcement
            if payload.active_day is not None:
                live_state.active_day = payload.active_day if payload.active_day > 0 else None
            live_state.starts_at = now
            live_state.ends_at = ends_at
            live_state.is_active = True
            live_state.triggered_by_user_id = triggered_by_user_id

        await db.commit()
        await db.refresh(live_state)

        return ConferenceLiveStateResponse(
            id=live_state.id,
            conference_id=conference_id,
            active_session_id=live_state.active_session_id,
            current_state=live_state.current_state,
            custom_state_label=live_state.custom_state_label,
            break_type=live_state.break_type,
            announcement_criticality=criticality,
            designated_location=live_state.designated_location,
            announcement_banner=live_state.announcement_banner,
            active_day=live_state.active_day,
            starts_at=live_state.starts_at,
            ends_at=live_state.ends_at,
            is_active=True,
            delay_minutes=payload.delay_minutes,
            weather_override=payload.weather_override,
        )
