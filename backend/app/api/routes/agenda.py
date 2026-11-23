"""Public read-only Agenda and authenticated Participant Bookmark API routes (GAP-05, GAP-09, GAP-10)."""

from datetime import date as dt_date, datetime, time, timedelta
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.dependencies import get_client_ip, get_current_user
from app.db.models.activity import UserActivityEvent
from app.db.models.agenda import BookmarkedSession, Conference, Session, SessionIntentDecision
from app.db.models.organizer import OrganizerProfile
from app.db.models.profile import ParticipantHobby, ParticipantTopic
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.agenda import (
    BookmarkResponse,
    BookmarkedSessionResponse,
    ConferenceOrganizerPublicResponse,
    ConferenceResponse,
    SessionIntentDecisionCreate,
    SessionIntentDecisionResponse,
    SessionRecommendationPrompt,
    SessionResponse,
)
from app.schemas.auth import ErrorResponse

router = APIRouter(prefix="/agenda", tags=["Conference Agenda"])


# =============================================================================
# 1. Conference Directory (Public Read-Only)
# =============================================================================


@router.get(
    "/conferences",
    response_model=List[ConferenceResponse],
    status_code=status.HTTP_200_OK,
    summary="List Conferences",
    description="Retrieve published conferences. Public read-only access (P3-WS2).",
    responses={
        status.HTTP_200_OK: {
            "description": "List of conferences matching filters.",
            "model": List[ConferenceResponse],
        }
    },
)
async def list_conferences(
    is_active: Optional[bool] = Query(
        default=True,
        description="Filter by active status. Default true.",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by conference category.",
    ),
    format: Optional[str] = Query(
        default=None,
        description="Filter by conference format (IN_PERSON, HYBRID, ONLINE).",
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Max items to return."),
    offset: int = Query(default=0, ge=0, description="Items to skip."),
    db: AsyncSession = Depends(get_db_session),
) -> List[ConferenceResponse]:
    """Return published conferences ordered deterministically by start_date, title, id."""
    query = select(Conference).where(Conference.status == "PUBLISHED")
    if is_active is not None:
        query = query.where(Conference.is_active == is_active)
    if category and category.lower() != "all":
        query = query.where(func.lower(Conference.category) == category.lower())
    if format and format.upper() != "ALL":
        query = query.where(Conference.format == format.upper())

    query = query.order_by(
        Conference.start_date.asc(),
        Conference.title.asc(),
        Conference.id.asc(),
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    conferences = result.scalars().all()

    # Batch load organizer profiles for conferences that have organizer_id
    org_user_ids = [c.organizer_id for c in conferences if c.organizer_id]
    org_map = {}
    if org_user_ids:
        prof_res = await db.execute(
            select(OrganizerProfile).where(OrganizerProfile.user_id.in_(org_user_ids))
        )
        for prof in prof_res.scalars().all():
            org_map[prof.user_id] = ConferenceOrganizerPublicResponse(
                id=prof.id,
                representative_name=prof.representative_name,
                organization_name=prof.organization_name,
                designation=prof.designation,
                city=prof.city,
                country=prof.country,
                verification_status=prof.verification_status,
                website_url=prof.website_url,
            )

    items = []
    for c in conferences:
        c_dict = {
            "id": c.id,
            "organizer_id": c.organizer_id,
            "organizer": org_map.get(c.organizer_id),
            "title": c.title,
            "summary": c.summary,
            "description": c.description,
            "category": c.category,
            "format": c.format,
            "venue_name": c.venue_name,
            "formatted_address": c.formatted_address,
            "location_lat": c.location_lat,
            "location_lng": c.location_lng,
            "place_id": c.place_id,
            "city": c.city,
            "country": c.country,
            "timezone": c.timezone,
            "start_date": c.start_date,
            "end_date": c.end_date,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "registration_opens_at": c.registration_opens_at,
            "registration_closes_at": c.registration_closes_at,
            "capacity": c.capacity,
            "target_audience": c.target_audience,
            "website_url": c.website_url,
            "banner_url": c.banner_url,
            "meeting_url": c.meeting_url,
            "status": c.status,
            "is_active": c.is_active,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        items.append(ConferenceResponse(**c_dict))

    return items


# =============================================================================
# 2. Participant Bookmarks (Authenticated, GAP-05, GAP-10)
# =============================================================================


@router.get(
    "/bookmarks/me",
    response_model=List[BookmarkedSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Bookmarked Sessions",
    description="Retrieve all sessions bookmarked by the currently authenticated participant (P3-WS3).",
    responses={
        status.HTTP_200_OK: {
            "description": "List of bookmarked sessions.",
            "model": List[BookmarkedSessionResponse],
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication required.",
            "model": ErrorResponse,
        },
    },
)
async def list_my_bookmarks(
    limit: int = Query(default=100, ge=1, le=200, description="Max items to return."),
    offset: int = Query(default=0, ge=0, description="Items to skip."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[BookmarkedSessionResponse]:
    """Return only bookmarked sessions belonging to the authenticated participant with deterministic ordering."""
    query = (
        select(BookmarkedSession, Session)
        .join(Session, BookmarkedSession.session_id == Session.id)
        .join(Conference, Session.conference_id == Conference.id)
        .where(
            BookmarkedSession.user_id == current_user.id,
            Conference.is_active == True,
        )
        .order_by(
            Session.start_time.asc(),
            Session.hall_room.asc().nulls_last(),
            Session.title.asc(),
            Session.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        BookmarkedSessionResponse(
            session_id=bm.session_id,
            bookmarked_at=bm.created_at,
            session=SessionResponse.model_validate(sess),
        )
        for bm, sess in rows
    ]


@router.post(
    "/bookmarks/{session_id}",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark Session",
    description="Bookmark a conference session for the authenticated participant (P3-WS3).",
    responses={
        status.HTTP_201_CREATED: {
            "description": "Session bookmarked successfully.",
            "model": BookmarkResponse,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication required.",
            "model": ErrorResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "CSRF verification failed.",
            "model": ErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Session not found.",
            "model": ErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "Session already bookmarked.",
            "model": ErrorResponse,
        },
    },
)
async def create_bookmark(
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BookmarkResponse:
    """Create a bookmark for the current participant. Enforces session existence, uniqueness, and audit."""
    # 1. Verify target session exists and belongs to an active conference
    sess_res = await db.execute(
        select(Session)
        .join(Conference, Session.conference_id == Conference.id)
        .where(Session.id == session_id, Conference.is_active == True)
    )
    target_session = sess_res.scalar_one_or_none()
    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    # 2. Check for duplicate bookmark prior to insertion
    bm_res = await db.execute(
        select(BookmarkedSession).where(
            BookmarkedSession.user_id == current_user.id,
            BookmarkedSession.session_id == session_id,
        )
    )
    existing_bm = bm_res.scalar_one_or_none()
    if existing_bm:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session already bookmarked.",
        )

    # 3. Insert new bookmark with concurrency safety
    new_bm = BookmarkedSession(
        user_id=current_user.id,
        session_id=session_id,
    )
    db.add(new_bm)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session already bookmarked.",
        )

    # 4. Record sanitized audit event
    await record_audit_event(
        session=db,
        action_type="agenda.bookmark.create",
        resource_type="agenda.session",
        resource_id=str(session_id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        payload={"action": "bookmark_created", "status": "success"},
    )
    # Record user activity event for analytics
    db.add(
        UserActivityEvent(
            user_id=current_user.id,
            event_type="FEATURE_CLICK",
            feature_name="AGENDA_BOOKMARK",
            target_resource_id=str(session_id),
            details={"action": "add", "session_title": target_session.title},
        )
    )
    await db.commit()
    await db.refresh(new_bm)

    return BookmarkResponse(
        user_id=new_bm.user_id,
        session_id=new_bm.session_id,
        created_at=new_bm.created_at,
    )


@router.delete(
    "/bookmarks/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Bookmark",
    description="Remove a conference session bookmark for the authenticated participant (P3-WS3). Idempotent.",
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Bookmark removed or was not present.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication required.",
            "model": ErrorResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "CSRF verification failed.",
            "model": ErrorResponse,
        },
    },
)
async def delete_bookmark(
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Idempotently delete the bookmark for the authenticated participant."""
    bm_res = await db.execute(
        select(BookmarkedSession).where(
            BookmarkedSession.user_id == current_user.id,
            BookmarkedSession.session_id == session_id,
        )
    )
    existing_bm = bm_res.scalar_one_or_none()
    if existing_bm:
        await db.delete(existing_bm)
        await record_audit_event(
            session=db,
            action_type="agenda.bookmark.delete",
            resource_type="agenda.session",
            resource_id=str(session_id),
            actor_username=current_user.username,
            user_id=current_user.id,
            ip_address=get_client_ip(request),
            payload={"action": "bookmark_deleted", "status": "success"},
        )
        # Record user activity event for analytics
        db.add(
            UserActivityEvent(
                user_id=current_user.id,
                event_type="FEATURE_CLICK",
                feature_name="AGENDA_BOOKMARK",
                target_resource_id=str(session_id),
                details={"action": "remove"},
            )
        )
        await db.commit()

    return None


# =============================================================================
# 3. Session Directory & Details (Public Read-Only)
# =============================================================================


@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Conference Sessions",
    description="Retrieve scheduled sessions matching query filters. Public read-only access (P3-WS2, GAP-09).",
    responses={
        status.HTTP_200_OK: {
            "description": "List of scheduled sessions matching filters.",
            "model": List[SessionResponse],
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Specified conference does not exist.",
            "model": ErrorResponse,
        },
    },
)
async def list_sessions(
    conference_id: Optional[UUID] = Query(
        default=None,
        description="Filter sessions by conference UUID.",
    ),
    track_name: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Filter by exact track category name (case-insensitive).",
    ),
    hall_room: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Filter by designated hall or room.",
    ),
    date: Optional[dt_date] = Query(
        default=None,
        description="Filter by calendar date evaluated in each session's parent conference timezone.",
    ),
    is_cancelled: Optional[bool] = Query(
        default=None,
        description="Filter by cancellation status. Default None includes both active and cancelled sessions.",
    ),
    conference_is_active: Optional[bool] = Query(
        default=True,
        description="Filter sessions by active status of their parent conference. Default true.",
    ),
    limit: int = Query(default=100, ge=1, le=200, description="Max items to return."),
    offset: int = Query(default=0, ge=0, description="Items to skip."),
    db: AsyncSession = Depends(get_db_session),
) -> List[SessionResponse]:
    """Query scheduled sessions with deterministic ordering and multi-conference timezone-aware date intervals."""
    # Always join parent Conference to enforce conference active status, published lifecycle, and evaluate timezone
    query = (
        select(Session)
        .join(Conference, Session.conference_id == Conference.id)
        .where(Conference.status == "PUBLISHED")
    )

    if conference_is_active is not None:
        query = query.where(Conference.is_active == conference_is_active)

    if conference_id is not None:
        # Verify conference exists
        conf_res = await db.execute(select(Conference).where(Conference.id == conference_id))
        conf = conf_res.scalar_one_or_none()
        if not conf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conference not found.",
            )
        if conference_is_active is not None and conf.is_active != conference_is_active:
            # Conference exists but does not match active status filter
            return []
        query = query.where(Session.conference_id == conference_id)

    if track_name is not None and track_name.strip():
        query = query.where(func.lower(Session.track_name) == track_name.strip().lower())

    if hall_room is not None and hall_room.strip():
        query = query.where(Session.hall_room == hall_room.strip())

    if is_cancelled is not None:
        query = query.where(Session.is_cancelled == is_cancelled)

    if date is not None:
        # Timezone-aware date interval in parent conference timezone (GAP-09)
        local_start = datetime.combine(date, time.min)
        local_end = datetime.combine(date + timedelta(days=1), time.min)

        # In PostgreSQL:
        # Session.start_time AT TIME ZONE Conference.timezone < local_end
        # AND Session.end_time AT TIME ZONE Conference.timezone > local_start
        local_session_start = Session.start_time.op("AT TIME ZONE")(Conference.timezone)
        local_session_end = Session.end_time.op("AT TIME ZONE")(Conference.timezone)

        query = query.where(
            local_session_start < local_end,
            local_session_end > local_start,
        )

    # Deterministic total ordering: start_time, hall_room (NULLS LAST), title, id
    query = query.order_by(
        Session.start_time.asc(),
        Session.hall_room.asc().nulls_last(),
        Session.title.asc(),
        Session.id.asc(),
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/sessions/{id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Session Details",
    description="Retrieve details of a single scheduled session. Public read-only access (P3-WS2).",
    responses={
        status.HTTP_200_OK: {
            "description": "Session details retrieved.",
            "model": SessionResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Session not found.",
            "model": ErrorResponse,
        },
    },
)
async def get_session_details(
    id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    """Retrieve single session details by UUID. Rejects sessions of inactive conferences."""
    res = await db.execute(
        select(Session)
        .join(Conference, Session.conference_id == Conference.id)
        .where(Session.id == id, Conference.is_active == True)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return SessionResponse.model_validate(sess)


# =============================================================================
# 4. Session Intent & Attendee Decisions (AC-WS8, Manager Requirement)
# =============================================================================


@router.get(
    "/recommendations/me",
    response_model=List[SessionRecommendationPrompt],
    status_code=status.HTTP_200_OK,
    summary="List Recommended Sessions for Authenticated Participant",
    description="Discovers active sessions aligning with attendee topics/hobbies with personalized attendance prompts (AC-WS8).",
)
async def list_recommended_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[SessionRecommendationPrompt]:
    """Identify relevant sessions based on attendee's actual interests, hobbies, and uncancelled agenda."""
    # 1. Fetch attendee topics and hobbies
    topics_res = await db.scalars(
        select(ParticipantTopic.topic_keyword).where(ParticipantTopic.user_id == current_user.id)
    )
    user_topics = [t.strip() for t in topics_res.all() if t and t.strip()]

    hobbies_res = await db.scalars(
        select(ParticipantHobby.hobby_name).where(ParticipantHobby.user_id == current_user.id)
    )
    user_hobbies = [h.strip() for h in hobbies_res.all() if h and h.strip()]

    # 2. Fetch existing session intent decisions and bookmarks
    decisions_res = await db.execute(
        select(SessionIntentDecision).where(SessionIntentDecision.user_id == current_user.id)
    )
    decisions_map = {d.session_id: d.decision for d in decisions_res.scalars().all()}

    bookmarks_res = await db.scalars(
        select(BookmarkedSession.session_id).where(BookmarkedSession.user_id == current_user.id)
    )
    bookmarked_ids = set(bookmarks_res.all())

    # 3. Fetch active uncancelled sessions
    sessions_query = (
        select(Session)
        .join(Conference, Session.conference_id == Conference.id)
        .where(
            Session.is_cancelled == False,
            Conference.is_active == True,
        )
        .order_by(
            Session.start_time.asc(),
            Session.title.asc(),
            Session.id.asc(),
        )
    )
    all_sessions = (await db.scalars(sessions_query)).all()

    # 4. Match sessions against attendee interests/hobbies, bookmarks, or featured sessions
    recommendations: List[SessionRecommendationPrompt] = []
    recommended_session_ids = set()
    keywords = [(kw, "topic") for kw in user_topics] + [(kw, "hobby") for kw in user_hobbies]

    # Priority 1: Match against declared topic and hobby keywords (exact and tokenized)
    for sess in all_sessions:
        matched_kw: Optional[str] = None
        matched_kind: Optional[str] = None
        searchable_text = f"{sess.title} {sess.abstract or ''} {sess.track_name or ''}".lower()

        for kw, kind in keywords:
            # 1. Full string match
            if kw.lower() in searchable_text:
                matched_kw = kw
                matched_kind = kind
                break

            # 2. Tokenized match (e.g. "Tea / Coffee" -> "tea", "coffee"; "Sustainability & Decarbonization Policy" -> "sustainability", "decarbonization")
            tokens = [t.strip().lower() for t in re.split(r"[/,&-]", kw) if len(t.strip()) >= 3]
            for token in tokens:
                if token in searchable_text:
                    matched_kw = kw
                    matched_kind = kind
                    break

            if matched_kw:
                break

        if matched_kw:
            time_formatted = sess.start_time.strftime("%I:%M %p").lstrip("0")
            reason_text = f"Matched {matched_kind} in '{matched_kw}'"
            prompt_text = (
                f"You're interested in {matched_kw}. I found a relevant session: "
                f"'{sess.title}' at {time_formatted}. Would you like to attend?"
            )
            recommendations.append(
                SessionRecommendationPrompt(
                    session=SessionResponse.model_validate(sess),
                    matched_reason=reason_text,
                    prompt_message=prompt_text,
                    current_decision=decisions_map.get(sess.id),
                )
            )
            recommended_session_ids.add(sess.id)

    # Priority 2: Attendee's bookmarked sessions
    for sess in all_sessions:
        if sess.id in bookmarked_ids and sess.id not in recommended_session_ids:
            time_formatted = sess.start_time.strftime("%I:%M %p").lstrip("0")
            reason_text = "Saved in your conference bookmarks"
            prompt_text = (
                f"You saved '{sess.title}' to your schedule (scheduled at {time_formatted}). "
                f"Would you like to confirm your attendance?"
            )
            recommendations.append(
                SessionRecommendationPrompt(
                    session=SessionResponse.model_validate(sess),
                    matched_reason=reason_text,
                    prompt_message=prompt_text,
                    current_decision=decisions_map.get(sess.id),
                )
            )
            recommended_session_ids.add(sess.id)

    # Priority 3: If no matches, surface featured active conference sessions
    if not recommendations:
        for sess in all_sessions[:2]:
            time_formatted = sess.start_time.strftime("%I:%M %p").lstrip("0")
            reason_text = f"Featured session in {sess.track_name or 'General'}"
            prompt_text = (
                f"Here is a key session on today's agenda: '{sess.title}' at {time_formatted}. "
                f"Would you like to attend?"
            )
            recommendations.append(
                SessionRecommendationPrompt(
                    session=SessionResponse.model_validate(sess),
                    matched_reason=reason_text,
                    prompt_message=prompt_text,
                    current_decision=decisions_map.get(sess.id),
                )
            )

    return recommendations


@router.post(
    "/sessions/{session_id}/intent",
    response_model=SessionIntentDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Session Attendance Intent Decision",
    description="Explicitly record or update attendance decision: ATTENDING, DECLINED, or UNDECIDED (AC-WS8).",
)
async def record_session_intent_decision(
    session_id: UUID,
    payload: SessionIntentDecisionCreate,
    current_user: User = Depends(get_current_user),
    client_ip: str = Depends(get_client_ip),
    db: AsyncSession = Depends(get_db_session),
) -> SessionIntentDecisionResponse:
    """Record attendee's explicit consent/intent decision for a conference session."""
    # 1. Verify session exists and is part of an active conference
    sess_res = await db.execute(
        select(Session)
        .join(Conference, Session.conference_id == Conference.id)
        .where(Session.id == session_id, Conference.is_active == True)
    )
    sess = sess_res.scalar_one_or_none()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    if sess.is_cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record attendance decision on a cancelled session.",
        )

    # 2. Upsert decision idempotently
    existing_res = await db.execute(
        select(SessionIntentDecision).where(
            SessionIntentDecision.user_id == current_user.id,
            SessionIntentDecision.session_id == session_id,
        )
    )
    decision_record = existing_res.scalar_one_or_none()
    if decision_record:
        decision_record.decision = payload.decision.value
        decision_record.source = payload.source
        decision_record.updated_at = func.now()
    else:
        decision_record = SessionIntentDecision(
            user_id=current_user.id,
            session_id=session_id,
            decision=payload.decision.value,
            source=payload.source,
        )
        db.add(decision_record)

    await db.flush()

    # 3. Record audit trail
    await record_audit_event(
        session=db,
        action_type="agenda.session_intent_decision",
        resource_type="agenda.session",
        resource_id=str(session_id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"action": "session_intent_decision", "status": "success", "details": payload.decision.value},
    )
    # Record user activity event for analytics
    db.add(
        UserActivityEvent(
            user_id=current_user.id,
            event_type="FEATURE_CLICK",
            feature_name="SESSION_INTENT",
            target_resource_id=str(session_id),
            details={"decision": payload.decision.value, "session_title": sess.title},
        )
    )
    await db.commit()
    await db.refresh(decision_record)

    return SessionIntentDecisionResponse(
        id=decision_record.id,
        user_id=decision_record.user_id,
        session_id=decision_record.session_id,
        decision=decision_record.decision,
        source=decision_record.source,
        created_at=decision_record.created_at,
        updated_at=decision_record.updated_at,
        session=SessionResponse.model_validate(sess),
    )


@router.get(
    "/intent/me",
    response_model=List[SessionIntentDecisionResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Session Intent Decisions",
    description="Retrieve all attendance decisions recorded by the authenticated participant (AC-WS8).",
)
async def list_my_session_intent_decisions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[SessionIntentDecisionResponse]:
    """Retrieve participant's recorded decisions ordered chronologically by session start time."""
    query = (
        select(SessionIntentDecision, Session)
        .join(Session, SessionIntentDecision.session_id == Session.id)
        .where(SessionIntentDecision.user_id == current_user.id)
        .order_by(Session.start_time.asc(), Session.id.asc())
    )
    res = await db.execute(query)
    rows = res.all()
    return [
        SessionIntentDecisionResponse(
            id=d.id,
            user_id=d.user_id,
            session_id=d.session_id,
            decision=d.decision,
            source=d.source,
            created_at=d.created_at,
            updated_at=d.updated_at,
            session=SessionResponse.model_validate(sess),
        )
        for d, sess in rows
    ]

