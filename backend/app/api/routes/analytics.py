"""User Activity and Interaction Tracking API endpoints (Phase 2 & AC requirements).

Provides privacy-conscious tracking for:
- User logins with timestamps and session details.
- User activity and interaction tracking (feature clicks, agent visits).
- Total number of conversations initiated and participated in.
- Detailed conversation history (whom the user interacted with, when, message count).
- Structured queries for user summaries and analytics dashboards.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.db.session import get_db_session
from app.db.models.activity import UserActivityEvent
from app.db.models.conversation import Conversation, Message
from app.db.models.session import UserSession
from app.db.models.user import User
from app.schemas.analytics import (
    ActivityEventCreate,
    ActivityEventResponse,
    ConversationHistoryDetail,
    SessionDetailResponse,
    UserActivitySummaryResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/events",
    response_model=ActivityEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record User Interaction Event",
    description="Logs a privacy-conscious feature click, agent visit, or interaction event.",
)
async def record_activity_event(
    payload: ActivityEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ActivityEventResponse:
    """Record an interaction event for the authenticated user."""
    event = UserActivityEvent(
        user_id=current_user.id,
        event_type=payload.event_type.strip().upper(),
        feature_name=payload.feature_name.strip(),
        target_resource_id=payload.target_resource_id.strip() if payload.target_resource_id else None,
        details=payload.details or {},
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return ActivityEventResponse(
        id=event.id,
        user_id=event.user_id,
        event_type=event.event_type,
        feature_name=event.feature_name,
        target_resource_id=event.target_resource_id,
        details=event.details or {},
        created_at=event.created_at,
    )


async def _build_user_summary(user_id: uuid.UUID, db: AsyncSession) -> UserActivitySummaryResponse:
    """Helper to assemble full activity, login, and conversation history metrics."""
    now = datetime.now(timezone.utc)

    # 1. Query Sessions & Logins
    sessions_stmt = (
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .order_by(desc(UserSession.created_at))
    )
    sessions_result = await db.execute(sessions_stmt)
    all_sessions = sessions_result.scalars().all()

    total_logins = len(all_sessions)
    active_sessions = sum(
        1 for s in all_sessions if s.revoked_at is None and s.expires_at > now
    )

    recent_sessions: List[SessionDetailResponse] = [
        SessionDetailResponse(
            session_id=s.id,
            created_at=s.created_at,
            last_accessed_at=s.last_accessed_at,
            expires_at=s.expires_at,
            is_active=(s.revoked_at is None and s.expires_at > now),
            user_agent=s.user_agent,
        )
        for s in all_sessions[:10]
    ]

    # 2. Query Conversations & Participation
    conv_stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.initiator),
            selectinload(Conversation.target),
            selectinload(Conversation.messages),
        )
        .where(
            or_(
                Conversation.initiator_id == user_id,
                Conversation.target_id == user_id,
            )
        )
        .order_by(desc(Conversation.created_at))
    )
    conv_result = await db.execute(conv_stmt)
    conversations = conv_result.scalars().all()

    conversations_initiated = 0
    conversations_participated = 0
    history: List[ConversationHistoryDetail] = []

    for c in conversations:
        is_initiator = c.initiator_id == user_id
        if is_initiator:
            conversations_initiated += 1
            partner = c.target
            role = "INITIATOR"
        else:
            conversations_participated += 1
            partner = c.initiator
            role = "TARGET"

        partner_name = partner.full_name if partner and partner.full_name else (partner.username if partner else "Unknown")
        partner_username = partner.username if partner else "unknown"

        msgs = c.messages or []
        turn_count = len(msgs)
        last_msg_at = msgs[-1].created_at if msgs else None

        history.append(
            ConversationHistoryDetail(
                conversation_id=c.id,
                partner_id=partner.id if partner else uuid.uuid4(),
                partner_name=partner_name,
                partner_username=partner_username,
                role=role,
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                turn_count=turn_count,
                created_at=c.created_at,
                concluded_at=c.concluded_at,
                last_message_at=last_msg_at,
            )
        )

    total_conversations = conversations_initiated + conversations_participated

    # 3. Query Activity Events
    events_stmt = (
        select(UserActivityEvent)
        .where(UserActivityEvent.user_id == user_id)
        .order_by(desc(UserActivityEvent.created_at))
    )
    events_result = await db.execute(events_stmt)
    all_events = events_result.scalars().all()

    total_activity_events = len(all_events)
    feature_clicks_count = sum(1 for e in all_events if e.event_type == "FEATURE_CLICK")
    agent_visits_count = sum(1 for e in all_events if e.event_type == "AGENT_VISIT")

    recent_events: List[ActivityEventResponse] = [
        ActivityEventResponse(
            id=e.id,
            user_id=e.user_id,
            event_type=e.event_type,
            feature_name=e.feature_name,
            target_resource_id=e.target_resource_id,
            details=e.details or {},
            created_at=e.created_at,
        )
        for e in all_events[:20]
    ]

    return UserActivitySummaryResponse(
        user_id=user_id,
        total_logins=total_logins,
        active_sessions=active_sessions,
        recent_sessions=recent_sessions,
        total_conversations=total_conversations,
        conversations_initiated=conversations_initiated,
        conversations_participated=conversations_participated,
        conversation_history=history,
        total_activity_events=total_activity_events,
        feature_clicks_count=feature_clicks_count,
        agent_visits_count=agent_visits_count,
        recent_activity_events=recent_events,
    )


@router.get(
    "/my-summary",
    response_model=UserActivitySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Caller Activity & Session Summary",
    description="Returns aggregate login counts, active sessions, conversation history, and interaction metrics.",
)
async def get_my_activity_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserActivitySummaryResponse:
    """Get the caller's complete activity metrics."""
    return await _build_user_summary(current_user.id, db)


@router.get(
    "/users/{target_user_id}/summary",
    response_model=UserActivitySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Activity Summary by ID",
    description="Enables querying analytics for a specific participant (for administrative dashboards).",
)
async def get_user_activity_summary(
    target_user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserActivitySummaryResponse:
    """Query user activity metrics by target user ID."""
    # Ensure target user exists
    user_stmt = select(User).where(User.id == target_user_id)
    result = await db.execute(user_stmt)
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {target_user_id} was not found.",
        )

    return await _build_user_summary(target_user_id, db)


@router.get(
    "/overview",
    status_code=status.HTTP_200_OK,
    summary="Global Analytics Overview",
    description="Aggregates platform-wide engagement, conversations, and interaction distribution.",
)
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Retrieve platform-wide engagement and tracking statistics."""
    now = datetime.now(timezone.utc)

    # Total registered users
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    # Total logins & active sessions
    total_sessions_res = await db.execute(select(func.count(UserSession.id)))
    total_logins = total_sessions_res.scalar() or 0

    active_sessions_res = await db.execute(
        select(func.count(UserSession.id)).where(
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    active_sessions = active_sessions_res.scalar() or 0

    # Total conversations
    total_convs_res = await db.execute(select(func.count(Conversation.id)))
    total_conversations = total_convs_res.scalar() or 0

    # Total activity events
    total_events_res = await db.execute(select(func.count(UserActivityEvent.id)))
    total_events = total_events_res.scalar() or 0

    # Top feature clicks
    top_features_stmt = (
        select(
            UserActivityEvent.feature_name,
            func.count(UserActivityEvent.id).label("count"),
        )
        .where(UserActivityEvent.event_type == "FEATURE_CLICK")
        .group_by(UserActivityEvent.feature_name)
        .order_by(desc("count"))
        .limit(10)
    )
    top_features_res = await db.execute(top_features_stmt)
    top_features = [{"feature": row[0], "count": row[1]} for row in top_features_res.all()]

    # Top agents visited
    top_agents_stmt = (
        select(
            UserActivityEvent.feature_name,
            func.count(UserActivityEvent.id).label("count"),
        )
        .where(UserActivityEvent.event_type == "AGENT_VISIT")
        .group_by(UserActivityEvent.feature_name)
        .order_by(desc("count"))
        .limit(10)
    )
    top_agents_res = await db.execute(top_agents_stmt)
    top_agents = [{"agent": row[0], "count": row[1]} for row in top_agents_res.all()]

    return {
        "total_users": total_users,
        "total_logins": total_logins,
        "active_sessions": active_sessions,
        "total_conversations": total_conversations,
        "total_activity_events": total_events,
        "top_features": top_features,
        "top_agents": top_agents,
    }
