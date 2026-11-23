"""FastAPI router for the Common Open Conference Lounge & Continuous Chatroom."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.models.chatroom import ChatroomPresence, ConferenceChatroom
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import ErrorResponse
from app.schemas.chatroom import (
    AmbientTickResponse,
    ChatroomContextResponse,
    ChatroomDetailResponse,
    ChatroomMessageResponse,
    ChatroomPostMessageRequest,
)
from app.services.ambient_lounge_service import AmbientLoungeService
from app.services.temporal_context import TemporalContextService
from app.services.traffic_service import TrafficService
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatrooms", tags=["Common Conference Lounge"])


@router.get(
    "/active",
    response_model=ChatroomDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get or Join Active Conference Networking Lounge",
    responses={
        status.HTTP_200_OK: {"description": "Active lounge details and recent chat stream.", "model": ChatroomDetailResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
    },
)
async def get_active_lounge(
    conference_id: Optional[UUID] = Query(None, description="Optional specific conference ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChatroomDetailResponse:
    """Retrieve active lounge, record presence, and return live environmental context."""
    lounge = await AmbientLoungeService.get_or_create_default_lounge(db, conference_id)
    await AmbientLoungeService.join_lounge(db, lounge.id, current_user)

    # Environmental & Temporal Context
    target_conf = await TemporalContextService.get_active_conference(db, lounge.conference_id)
    city = target_conf.city if target_conf and target_conf.city else "Pune"
    venue = target_conf.venue_name if target_conf and target_conf.venue_name else "Pune International Exhibition Centre"

    temp_state = await TemporalContextService.get_current_conference_state(db, lounge.conference_id)
    weather = await WeatherService.get_weather_summary(city=city)
    traffic = await TrafficService.get_traffic_summary(destination=f"{venue}, {city}")

    recent_msgs = await AmbientLoungeService.get_recent_messages(db, lounge.id, limit=50)
    online_count = await AmbientLoungeService.get_online_presence_count(db, lounge.id)

    announcement_text = temp_state.announcement_banner if temp_state else None
    announcement_criticality = "NORMAL"
    if announcement_text:
        text_lower = announcement_text.lower()
        if (
            getattr(temp_state, "announcement_criticality", None) == "CRITICAL"
            or any(w in text_lower for w in ["critical", "urgent", "thunder", "storm", "lightning", "heavy rain", "emergency", "warning", "hazard"])
        ):
            announcement_criticality = "CRITICAL"

    context = ChatroomContextResponse(
        weather=weather,
        traffic=traffic,
        active_break=temp_state.current_state if temp_state else None,
        break_location=temp_state.designated_location if temp_state else None,
        general_announcement=announcement_text,
        announcement_criticality=announcement_criticality,
        active_day=getattr(temp_state, "active_day", None) if temp_state else None,
    )

    return ChatroomDetailResponse(
        id=lounge.id,
        conference_id=lounge.conference_id,
        name=lounge.name,
        slug=lounge.slug,
        description=lounge.description,
        is_active=lounge.is_active,
        ambient_interval_seconds=lounge.ambient_interval_seconds,
        online_count=online_count,
        context=context,
        recent_messages=[ChatroomMessageResponse.model_validate(m) for m in recent_msgs],
    )


@router.get(
    "/{chatroom_id}/messages",
    response_model=List[ChatroomMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch Recent Messages",
)
async def get_messages(
    chatroom_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[ChatroomMessageResponse]:
    """Fetch chronological message stream from the chatroom."""
    msgs = await AmbientLoungeService.get_recent_messages(db, chatroom_id, limit=limit)
    return [ChatroomMessageResponse.model_validate(m) for m in msgs]


@router.post(
    "/{chatroom_id}/messages",
    response_model=ChatroomMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post Human Attendee Message",
)
async def post_message(
    chatroom_id: UUID,
    payload: ChatroomPostMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ChatroomMessageResponse:
    """Post an attendee's human chat message into the stream."""
    lounge = await db.get(ConferenceChatroom, chatroom_id)
    if not lounge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatroom not found.")
    if not lounge.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The networking lounge is currently closed by the organizer.",
        )
    msg = await AmbientLoungeService.post_user_message(db, chatroom_id, current_user, payload.content)
    return ChatroomMessageResponse.model_validate(msg)


@router.post(
    "/{chatroom_id}/ambient-tick",
    response_model=AmbientTickResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger or Poll Periodic Ambient Message",
)
async def poll_ambient_tick(
    chatroom_id: UUID,
    force: bool = Query(False, description="Force message generation bypassing interval timer"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AmbientTickResponse:
    """Evaluate interval timer and generate ambient conversational message if due."""
    generated, reason, msg = await AmbientLoungeService.generate_ambient_tick(db, chatroom_id, force=force)
    return AmbientTickResponse(
        message_generated=generated,
        reason=reason,
        message=ChatroomMessageResponse.model_validate(msg) if msg else None,
    )


@router.post(
    "/{chatroom_id}/leave",
    status_code=status.HTTP_200_OK,
    summary="Leave Chatroom",
)
async def leave_chatroom(
    chatroom_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Set presence status to offline."""
    await AmbientLoungeService.leave_lounge(db, chatroom_id, current_user.id)
    return {"status": "left"}


@router.get(
    "/{chatroom_id}/online-users",
    status_code=status.HTTP_200_OK,
    summary="List Currently Online Delegates in Lounge",
)
async def get_online_users(
    chatroom_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve list of active delegates currently present in the networking lounge."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    pres_query = (
        select(User)
        .options(selectinload(User.profile))
        .join(ChatroomPresence, ChatroomPresence.user_id == User.id)
        .where(
            ChatroomPresence.chatroom_id == chatroom_id,
            ChatroomPresence.is_online == True,
            ChatroomPresence.last_seen_at >= cutoff,
            User.is_active == True,
        )
        .order_by(User.full_name)
    )
    res = await db.execute(pres_query)
    online_users = list(res.scalars().all())

    # If few users are recorded in presence, supplement with active conference delegates
    if len(online_users) < 3:
        seen_ids = {u.id for u in online_users}
        supp_query = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.is_active == True, User.id.not_in(seen_ids))
            .limit(6 - len(online_users))
        )
        supp_res = await db.execute(supp_query)
        online_users.extend(supp_res.scalars().all())

    return [
        {
            "id": str(u.id),
            "full_name": u.full_name or u.username,
            "company_name": u.company_name or "Conference Delegate",
            "job_title": getattr(u, "job_title", None) or "Delegate",
            "is_me": u.id == current_user.id,
            "allow_agent_dm_initiation": getattr(u.profile, "allow_agent_dm_initiation", True) if getattr(u, "profile", None) else True,
        }
        for u in online_users
    ]
