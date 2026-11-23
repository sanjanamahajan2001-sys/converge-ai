"""Organizer Portal API routes (Phase 2 & Phase 3).

Provides endpoints for:
- Organizer registration & instant session authentication
- Organizer profile retrieval and updates
- Conference draft creation, editing, and listing
- Agenda session schedule builder (create, edit, delete sessions)
- Conference submission for administrative review
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.config import get_settings
from app.core.dependencies import get_client_ip, get_current_user
from app.core.security import hash_password
from app.core.session import create_session, set_session_cookie
from app.db.models.activity import UserActivityEvent
from app.db.models.agenda import (
    Conference,
    ConferenceFormat,
    ConferenceLiveState,
    ConferenceReviewLog,
    ConferenceStatus,
    Session,
)
from app.db.models.chatroom import (
    ChatroomMessage,
    ChatroomMessageKind,
    ChatroomPresence,
    ChatroomSenderType,
)
from app.db.models.organizer import OrganizerProfile, OrganizerType, OrganizerVerificationStatus
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.agenda import ConferenceLiveStateResponse, ConferenceLiveStateUpdate
from app.schemas.auth import ErrorResponse
from app.services.ambient_lounge_service import AmbientLoungeService
from app.services.temporal_context import TemporalContextService
from app.schemas.organizer import (
    ConferenceSubmitResponse,
    OrganizerConferenceCreate,
    OrganizerConferenceDetailResponse,
    OrganizerConferenceResponse,
    OrganizerConferenceUpdate,
    OrganizerProfileResponse,
    OrganizerProfileUpdate,
    OrganizerRegisterRequest,
    OrganizerSessionCreate,
    OrganizerSessionResponse,
    OrganizerSessionUpdate,
)

router = APIRouter(prefix="/organizer", tags=["Organizer Portal"])


async def require_organizer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerProfile:
    """Dependency verifying the caller has an active registered Organizer profile."""
    stmt = select(OrganizerProfile).where(OrganizerProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. An Organizer account is required to perform this action.",
        )
    return profile


# =============================================================================
# 1. Organizer Registration & Authentication
# =============================================================================


@router.post(
    "/register",
    response_model=OrganizerProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Organizer Account and Profile",
    description="Registers an event organizer, initializes an organization profile, and issues an authenticated session.",
    responses={
        status.HTTP_201_CREATED: {"description": "Organizer registered and session cookie attached."},
        status.HTTP_409_CONFLICT: {"description": "Username or email already in use.", "model": ErrorResponse},
    },
)
async def register_organizer(
    payload: OrganizerRegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerProfileResponse:
    """Create a new user account with attached organizer profile and issue session cookie."""
    client_ip = get_client_ip(request)

    # 1. Uniqueness check for username & email
    clean_username = payload.username.strip()
    clean_email = payload.email.strip().lower()
    clean_prof_email = payload.professional_email.strip().lower()

    existing_user_stmt = select(User).where(
        or_(
            func.lower(User.username) == clean_username.lower(),
            func.lower(User.email) == clean_email,
        )
    )
    existing_user = (await db.execute(existing_user_stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username or account email already exists.",
        )

    # 2. Hash password and insert User identity
    pwd_hash = hash_password(payload.password)
    user = User(
        username=clean_username,
        email=clean_email,
        password_hash=pwd_hash,
        full_name=payload.full_name.strip(),
        company_name=payload.organization_name.strip() if payload.organization_name else None,
        job_title=payload.designation.strip() if payload.designation else None,
        phone_number=payload.contact_phone.strip(),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered.",
        )

    # 3. Create Organizer Profile
    org_profile = OrganizerProfile(
        user_id=user.id,
        organizer_type=payload.organizer_type.value,
        representative_name=payload.representative_name.strip(),
        organization_name=payload.organization_name.strip() if payload.organization_name else None,
        designation=payload.designation.strip() if payload.designation else None,
        professional_email=clean_prof_email,
        contact_phone=payload.contact_phone.strip(),
        website_url=payload.website_url.strip() if payload.website_url else None,
        logo_url=payload.logo_url.strip() if payload.logo_url else None,
        address_line1=payload.address_line1.strip() if payload.address_line1 else None,
        city=payload.city.strip(),
        state_province=payload.state_province.strip() if payload.state_province else None,
        postal_code=payload.postal_code.strip() if payload.postal_code else None,
        country=payload.country.strip(),
        bio=payload.bio.strip(),
        experience_years=payload.experience_years,
        focus_areas=payload.focus_areas,
        verification_status=OrganizerVerificationStatus.VERIFIED.value,
    )
    db.add(org_profile)
    await db.flush()

    # 4. Create Session and attach cookie
    settings = get_settings()
    is_secure = settings.is_production() or request.url.scheme == "https"
    db_session, raw_token = await create_session(
        session=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    set_session_cookie(response=response, raw_token=raw_token, secure=is_secure)

    await record_audit_event(
        session=db,
        action_type="ORGANIZER_REGISTERED",
        resource_type="ORGANIZER_PROFILE",
        resource_id=str(org_profile.id),
        actor_username=user.username,
        user_id=user.id,
        ip_address=client_ip,
        payload={"organization_name": org_profile.organization_name, "type": org_profile.organizer_type},
    )
    db.add(
        UserActivityEvent(
            user_id=user.id,
            event_type="LOGIN_SUCCESS",
            feature_name="ORGANIZER_PORTAL",
            details={"action": "organizer_registered"},
        )
    )
    await db.commit()
    await db.refresh(org_profile)

    return OrganizerProfileResponse(
        id=org_profile.id,
        user_id=org_profile.user_id,
        organizer_type=org_profile.organizer_type,
        representative_name=org_profile.representative_name,
        organization_name=org_profile.organization_name,
        designation=org_profile.designation,
        professional_email=org_profile.professional_email,
        contact_phone=org_profile.contact_phone,
        website_url=org_profile.website_url,
        logo_url=org_profile.logo_url,
        address_line1=org_profile.address_line1,
        city=org_profile.city,
        state_province=org_profile.state_province,
        postal_code=org_profile.postal_code,
        country=org_profile.country,
        bio=org_profile.bio,
        experience_years=org_profile.experience_years,
        focus_areas=org_profile.focus_areas or [],
        verification_status=org_profile.verification_status,
        created_at=org_profile.created_at,
        updated_at=org_profile.updated_at,
        conferences_count=0,
    )


# =============================================================================
# 2. Organizer Profile Management
# =============================================================================


@router.get(
    "/me",
    response_model=OrganizerProfileResponse,
    summary="Get My Organizer Profile",
    description="Returns authenticated organizer's profile and active conferences summary.",
)
async def get_my_organizer_profile(
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerProfileResponse:
    """Fetch current organizer profile."""
    conf_count_stmt = select(func.count(Conference.id)).where(Conference.organizer_id == current_user.id)
    conf_count = (await db.execute(conf_count_stmt)).scalar() or 0

    return OrganizerProfileResponse(
        id=org_profile.id,
        user_id=org_profile.user_id,
        organizer_type=org_profile.organizer_type,
        representative_name=org_profile.representative_name,
        organization_name=org_profile.organization_name,
        designation=org_profile.designation,
        professional_email=org_profile.professional_email,
        contact_phone=org_profile.contact_phone,
        website_url=org_profile.website_url,
        logo_url=org_profile.logo_url,
        address_line1=org_profile.address_line1,
        city=org_profile.city,
        state_province=org_profile.state_province,
        postal_code=org_profile.postal_code,
        country=org_profile.country,
        bio=org_profile.bio,
        experience_years=org_profile.experience_years,
        focus_areas=org_profile.focus_areas or [],
        verification_status=org_profile.verification_status,
        created_at=org_profile.created_at,
        updated_at=org_profile.updated_at,
        conferences_count=conf_count,
    )


@router.put(
    "/me",
    response_model=OrganizerProfileResponse,
    summary="Update My Organizer Profile",
    description="Updates organizer identity, organization background, and expertise attributes.",
)
async def update_my_organizer_profile(
    payload: OrganizerProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerProfileResponse:
    """Update caller's organizer profile."""
    client_ip = get_client_ip(request)
    stmt = select(OrganizerProfile).where(OrganizerProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizer profile not found for this account.",
        )

    # Partial update fields
    if payload.organizer_type is not None:
        profile.organizer_type = payload.organizer_type.value
    if payload.representative_name is not None:
        profile.representative_name = payload.representative_name.strip()
    if payload.organization_name is not None:
        profile.organization_name = payload.organization_name.strip() if payload.organization_name else None
    if payload.designation is not None:
        profile.designation = payload.designation.strip() if payload.designation else None
    if payload.professional_email is not None:
        profile.professional_email = payload.professional_email.strip().lower()
    if payload.contact_phone is not None:
        profile.contact_phone = payload.contact_phone.strip()
    if payload.website_url is not None:
        profile.website_url = payload.website_url.strip() if payload.website_url else None
    if payload.logo_url is not None:
        profile.logo_url = payload.logo_url.strip() if payload.logo_url else None
    if payload.address_line1 is not None:
        profile.address_line1 = payload.address_line1.strip() if payload.address_line1 else None
    if payload.city is not None:
        profile.city = payload.city.strip()
    if payload.state_province is not None:
        profile.state_province = payload.state_province.strip() if payload.state_province else None
    if payload.postal_code is not None:
        profile.postal_code = payload.postal_code.strip() if payload.postal_code else None
    if payload.country is not None:
        profile.country = payload.country.strip()
    if payload.bio is not None:
        profile.bio = payload.bio.strip()
    if payload.experience_years is not None:
        profile.experience_years = payload.experience_years
    if payload.focus_areas is not None:
        profile.focus_areas = payload.focus_areas

    profile.updated_at = datetime.now(timezone.utc)

    # Sync User table top-level fields for consistency
    if payload.organization_name is not None:
        current_user.company_name = payload.organization_name.strip() if payload.organization_name else None
    if payload.designation is not None:
        current_user.job_title = payload.designation.strip() if payload.designation else None
    if payload.contact_phone is not None:
        current_user.phone_number = payload.contact_phone.strip()

    await record_audit_event(
        session=db,
        action_type="ORGANIZER_PROFILE_UPDATED",
        resource_type="ORGANIZER_PROFILE",
        resource_id=str(profile.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"status": "SUCCESS"},
    )
    db.add(
        UserActivityEvent(
            user_id=current_user.id,
            event_type="FEATURE_CLICK",
            feature_name="ORGANIZER_PROFILE_UPDATE",
            target_resource_id=str(profile.id),
            details={"action": "update"},
        )
    )
    await db.commit()
    await db.refresh(profile)

    conf_count_stmt = select(func.count(Conference.id)).where(Conference.organizer_id == current_user.id)
    conf_count = (await db.execute(conf_count_stmt)).scalar() or 0

    return OrganizerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        organizer_type=profile.organizer_type,
        representative_name=profile.representative_name,
        organization_name=profile.organization_name,
        designation=profile.designation,
        professional_email=profile.professional_email,
        contact_phone=profile.contact_phone,
        website_url=profile.website_url,
        logo_url=profile.logo_url,
        address_line1=profile.address_line1,
        city=profile.city,
        state_province=profile.state_province,
        postal_code=profile.postal_code,
        country=profile.country,
        bio=profile.bio,
        experience_years=profile.experience_years,
        focus_areas=profile.focus_areas or [],
        verification_status=profile.verification_status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        conferences_count=conf_count,
    )


# =============================================================================
# 3. Conference Management (Phase 3)
# =============================================================================


@router.get(
    "/conferences",
    response_model=List[OrganizerConferenceResponse],
    summary="List Organizer Conferences",
    description="Retrieves all conferences owned and managed by the authenticated organizer.",
)
async def list_organizer_conferences(
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> List[OrganizerConferenceResponse]:
    """List conferences owned by caller."""
    stmt = (
        select(
            Conference,
            func.count(Session.id).label("sessions_count"),
        )
        .outerjoin(Session, Session.conference_id == Conference.id)
        .where(Conference.organizer_id == current_user.id)
        .group_by(Conference.id)
        .order_by(Conference.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    conferences = []
    for conf, sess_cnt in rows:
        conferences.append(
            OrganizerConferenceResponse(
                id=conf.id,
                organizer_id=conf.organizer_id,
                title=conf.title,
                summary=conf.summary,
                description=conf.description,
                category=conf.category,
                format=conf.format,
                venue_name=conf.venue_name,
                timezone=conf.timezone,
                start_date=conf.start_date,
                end_date=conf.end_date,
                start_time=conf.start_time,
                end_time=conf.end_time,
                registration_opens_at=conf.registration_opens_at,
                registration_closes_at=conf.registration_closes_at,
                capacity=conf.capacity,
                target_audience=conf.target_audience,
                website_url=conf.website_url,
                banner_url=conf.banner_url,
                meeting_url=conf.meeting_url,
                formatted_address=conf.formatted_address,
                location_lat=conf.location_lat,
                location_lng=conf.location_lng,
                place_id=conf.place_id,
                city=conf.city,
                state_province=None,
                postal_code=None,
                country=conf.country,
                status=conf.status,
                review_feedback=conf.review_feedback,
                published_at=conf.published_at,
                created_at=conf.created_at,
                updated_at=conf.updated_at,
                sessions_count=sess_cnt or 0,
            )
        )
    return conferences


@router.post(
    "/conferences",
    response_model=OrganizerConferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Conference Draft",
    description="Creates a new conference draft in DRAFT status.",
)
async def create_organizer_conference(
    payload: OrganizerConferenceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerConferenceResponse:
    """Create a new conference draft."""
    client_ip = get_client_ip(request)

    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conference end_date cannot be earlier than start_date.",
        )

    venue = payload.venue_name.strip()
    if payload.format == ConferenceFormat.ONLINE.value and not venue:
        venue = "Virtual Event Platform"

    conference = Conference(
        organizer_id=current_user.id,
        title=payload.title.strip(),
        summary=payload.summary.strip() if payload.summary else None,
        description=payload.description.strip() if payload.description else None,
        category=payload.category.strip() if payload.category else None,
        format=payload.format.value,
        venue_name=venue,
        timezone=payload.timezone.strip() if payload.timezone else "Asia/Kolkata",
        start_date=payload.start_date,
        end_date=payload.end_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        registration_opens_at=payload.registration_opens_at,
        registration_closes_at=payload.registration_closes_at,
        capacity=payload.capacity,
        target_audience=payload.target_audience.strip() if payload.target_audience else None,
        website_url=payload.website_url.strip() if payload.website_url else None,
        banner_url=payload.banner_url.strip() if payload.banner_url else None,
        meeting_url=payload.meeting_url.strip() if payload.meeting_url else None,
        formatted_address=payload.formatted_address.strip() if payload.formatted_address else None,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
        place_id=payload.place_id.strip() if payload.place_id else None,
        city=payload.city.strip() if payload.city else None,
        country=payload.country.strip() if payload.country else None,
        status=ConferenceStatus.DRAFT.value,
        is_active=True,
    )
    db.add(conference)
    await db.flush()

    # Create initial review log
    review_log = ConferenceReviewLog(
        conference_id=conference.id,
        reviewer_id=None,
        from_status="NONE",
        to_status=ConferenceStatus.DRAFT.value,
        notes="Conference draft created by organizer.",
    )
    db.add(review_log)

    await record_audit_event(
        session=db,
        action_type="CONFERENCE_CREATED",
        resource_type="CONFERENCE",
        resource_id=str(conference.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"title": conference.title, "format": conference.format},
    )
    await db.commit()
    await db.refresh(conference)

    # Phase 6: Real-time event for conference creation
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:created",
        {
            "conference_id": str(conference.id),
            "title": conference.title,
            "status": conference.status,
            "category": conference.category,
        },
    )

    return OrganizerConferenceResponse(
        id=conference.id,
        organizer_id=conference.organizer_id,
        title=conference.title,
        summary=conference.summary,
        description=conference.description,
        category=conference.category,
        format=conference.format,
        venue_name=conference.venue_name,
        timezone=conference.timezone,
        start_date=conference.start_date,
        end_date=conference.end_date,
        start_time=conference.start_time,
        end_time=conference.end_time,
        registration_opens_at=conference.registration_opens_at,
        registration_closes_at=conference.registration_closes_at,
        capacity=conference.capacity,
        target_audience=conference.target_audience,
        website_url=conference.website_url,
        banner_url=conference.banner_url,
        meeting_url=conference.meeting_url,
        formatted_address=conference.formatted_address,
        location_lat=conference.location_lat,
        location_lng=conference.location_lng,
        place_id=conference.place_id,
        city=conference.city,
        state_province=None,
        postal_code=None,
        country=conference.country,
        status=conference.status,
        review_feedback=conference.review_feedback,
        published_at=conference.published_at,
        created_at=conference.created_at,
        updated_at=conference.updated_at,
        sessions_count=0,
    )


@router.get(
    "/conferences/{conference_id}",
    response_model=OrganizerConferenceDetailResponse,
    summary="Get Conference Details & Agenda",
    description="Fetches full conference metadata and scheduled sessions for the organizer.",
)
async def get_organizer_conference_detail(
    conference_id: UUID,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerConferenceDetailResponse:
    """Fetch conference detail and session schedule."""
    stmt = select(Conference).where(Conference.id == conference_id)
    result = await db.execute(stmt)
    conference = result.scalar_one_or_none()

    if not conference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    # Ownership check
    if conference.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view or manage this conference.",
        )

    # Fetch sessions
    sessions_stmt = select(Session).where(Session.conference_id == conference.id).order_by(Session.start_time.asc())
    sessions_res = await db.execute(sessions_stmt)
    sessions = sessions_res.scalars().all()

    session_dtos = [
        OrganizerSessionResponse(
            id=s.id,
            conference_id=s.conference_id,
            title=s.title,
            abstract=s.abstract,
            speaker_names=s.speaker_names,
            track_name=s.track_name,
            hall_room=s.hall_room,
            start_time=s.start_time,
            end_time=s.end_time,
            is_cancelled=s.is_cancelled,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]

    return OrganizerConferenceDetailResponse(
        id=conference.id,
        organizer_id=conference.organizer_id,
        title=conference.title,
        summary=conference.summary,
        description=conference.description,
        category=conference.category,
        format=conference.format,
        venue_name=conference.venue_name,
        timezone=conference.timezone,
        start_date=conference.start_date,
        end_date=conference.end_date,
        start_time=conference.start_time,
        end_time=conference.end_time,
        registration_opens_at=conference.registration_opens_at,
        registration_closes_at=conference.registration_closes_at,
        capacity=conference.capacity,
        target_audience=conference.target_audience,
        website_url=conference.website_url,
        banner_url=conference.banner_url,
        meeting_url=conference.meeting_url,
        formatted_address=conference.formatted_address,
        location_lat=conference.location_lat,
        location_lng=conference.location_lng,
        place_id=conference.place_id,
        city=conference.city,
        state_province=None,
        postal_code=None,
        country=conference.country,
        status=conference.status,
        review_feedback=conference.review_feedback,
        published_at=conference.published_at,
        created_at=conference.created_at,
        updated_at=conference.updated_at,
        sessions_count=len(session_dtos),
        sessions=session_dtos,
    )


@router.put(
    "/conferences/{conference_id}",
    response_model=OrganizerConferenceResponse,
    summary="Update Conference Draft",
    description="Updates conference properties when in editable states (DRAFT or CHANGES_REQUESTED).",
)
async def update_organizer_conference(
    conference_id: UUID,
    payload: OrganizerConferenceUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerConferenceResponse:
    """Update conference metadata."""
    client_ip = get_client_ip(request)

    stmt = select(Conference).where(Conference.id == conference_id)
    conference = (await db.execute(stmt)).scalar_one_or_none()
    if not conference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    # Ownership check
    if conference.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this conference.",
        )

    # State validation
    if conference.status not in (ConferenceStatus.DRAFT.value, ConferenceStatus.CHANGES_REQUESTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conference cannot be modified while in status '{conference.status}'.",
        )

    if payload.title is not None:
        conference.title = payload.title.strip()
    if payload.summary is not None:
        conference.summary = payload.summary.strip() if payload.summary else None
    if payload.description is not None:
        conference.description = payload.description.strip() if payload.description else None
    if payload.category is not None:
        conference.category = payload.category.strip() if payload.category else None
    if payload.format is not None:
        conference.format = payload.format.value
    if payload.venue_name is not None:
        conference.venue_name = payload.venue_name.strip()
    if payload.timezone is not None:
        conference.timezone = payload.timezone.strip()
    if payload.start_date is not None:
        conference.start_date = payload.start_date
    if payload.end_date is not None:
        conference.end_date = payload.end_date
    if payload.start_time is not None:
        conference.start_time = payload.start_time
    if payload.end_time is not None:
        conference.end_time = payload.end_time
    if payload.registration_opens_at is not None:
        conference.registration_opens_at = payload.registration_opens_at
    if payload.registration_closes_at is not None:
        conference.registration_closes_at = payload.registration_closes_at
    if payload.capacity is not None:
        conference.capacity = payload.capacity
    if payload.target_audience is not None:
        conference.target_audience = payload.target_audience.strip() if payload.target_audience else None
    if payload.website_url is not None:
        conference.website_url = payload.website_url.strip() if payload.website_url else None
    if payload.banner_url is not None:
        conference.banner_url = payload.banner_url.strip() if payload.banner_url else None
    if payload.meeting_url is not None:
        conference.meeting_url = payload.meeting_url.strip() if payload.meeting_url else None
    if payload.formatted_address is not None:
        conference.formatted_address = payload.formatted_address.strip() if payload.formatted_address else None
    elif payload.state_province or payload.postal_code:
        conference.formatted_address = (
            f"{conference.venue_name}, {payload.city or conference.city or ''}, {payload.state_province or ''} {payload.postal_code or ''}, {payload.country or conference.country or 'India'}"
        ).strip().rstrip(',')
    if payload.location_lat is not None:
        conference.location_lat = payload.location_lat
    if payload.location_lng is not None:
        conference.location_lng = payload.location_lng
    if payload.place_id is not None:
        conference.place_id = payload.place_id.strip() if payload.place_id else None
    if payload.city is not None:
        conference.city = payload.city.strip() if payload.city else None
    if payload.country is not None:
        conference.country = payload.country.strip() if payload.country else None

    if conference.end_date < conference.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conference end_date cannot be earlier than start_date.",
        )

    conference.updated_at = datetime.now(timezone.utc)

    await record_audit_event(
        session=db,
        action_type="CONFERENCE_UPDATED",
        resource_type="CONFERENCE",
        resource_id=str(conference.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"status": "SUCCESS"},
    )
    await db.commit()
    await db.refresh(conference)

    # Phase 6: Real-time event for conference update
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:updated",
        {
            "conference_id": str(conference.id),
            "title": conference.title,
            "status": conference.status,
            "category": conference.category,
        },
    )

    sess_count_stmt = select(func.count(Session.id)).where(Session.conference_id == conference.id)
    sess_count = (await db.execute(sess_count_stmt)).scalar() or 0

    return OrganizerConferenceResponse(
        id=conference.id,
        organizer_id=conference.organizer_id,
        title=conference.title,
        summary=conference.summary,
        description=conference.description,
        category=conference.category,
        format=conference.format,
        venue_name=conference.venue_name,
        timezone=conference.timezone,
        start_date=conference.start_date,
        end_date=conference.end_date,
        start_time=conference.start_time,
        end_time=conference.end_time,
        registration_opens_at=conference.registration_opens_at,
        registration_closes_at=conference.registration_closes_at,
        capacity=conference.capacity,
        target_audience=conference.target_audience,
        website_url=conference.website_url,
        banner_url=conference.banner_url,
        meeting_url=conference.meeting_url,
        formatted_address=conference.formatted_address,
        location_lat=conference.location_lat,
        location_lng=conference.location_lng,
        place_id=conference.place_id,
        city=conference.city,
        state_province=None,
        postal_code=None,
        country=conference.country,
        status=conference.status,
        review_feedback=conference.review_feedback,
        published_at=conference.published_at,
        created_at=conference.created_at,
        updated_at=conference.updated_at,
        sessions_count=sess_count,
    )


@router.post(
    "/conferences/{conference_id}/submit",
    response_model=ConferenceSubmitResponse,
    summary="Submit Conference for Administrative Review",
    description="Transitions a conference from DRAFT or CHANGES_REQUESTED to IN_REVIEW.",
)
async def submit_conference_for_review(
    conference_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> ConferenceSubmitResponse:
    """Submit conference for admin approval."""
    client_ip = get_client_ip(request)

    stmt = select(Conference).where(Conference.id == conference_id)
    conference = (await db.execute(stmt)).scalar_one_or_none()
    if not conference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    # Ownership check
    if conference.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to submit this conference.",
        )

    if conference.status not in (ConferenceStatus.DRAFT.value, ConferenceStatus.CHANGES_REQUESTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit conference currently in status '{conference.status}'.",
        )

    # Mandatory Session requirement check
    sess_count_stmt = select(func.count(Session.id)).where(Session.conference_id == conference.id)
    sess_count = (await db.execute(sess_count_stmt)).scalar() or 0
    if sess_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please schedule at least one agenda session before submitting for review.",
        )

    from_status = conference.status
    conference.status = ConferenceStatus.IN_REVIEW.value
    conference.updated_at = datetime.now(timezone.utc)

    # Add audit review log
    review_log = ConferenceReviewLog(
        conference_id=conference.id,
        reviewer_id=None,
        from_status=from_status,
        to_status=ConferenceStatus.IN_REVIEW.value,
        notes="Conference submitted by organizer for administrative review and publication approval.",
    )
    db.add(review_log)

    await record_audit_event(
        session=db,
        action_type="CONFERENCE_SUBMITTED_FOR_REVIEW",
        resource_type="CONFERENCE",
        resource_id=str(conference.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"from_status": from_status, "to_status": conference.status, "sessions_count": sess_count},
    )
    await db.commit()

    # Phase 6: Real-time broadcast for conference submission to admin queue
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:submitted",
        {
            "conference_id": str(conference.id),
            "title": conference.title,
            "organizer_name": org_profile.organization_name or org_profile.representative_name,
            "status": ConferenceStatus.IN_REVIEW.value,
            "sessions_count": sess_count,
        },
    )

    return ConferenceSubmitResponse(
        status=ConferenceStatus.IN_REVIEW.value,
        conference_id=conference.id,
        message="Conference submitted successfully. It is now awaiting administrative review.",
    )


# =============================================================================
# 4. Agenda Session Management (Phase 3)
# =============================================================================


@router.post(
    "/conferences/{conference_id}/sessions",
    response_model=OrganizerSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Session to Conference Agenda",
    description="Schedules a new agenda session within the conference timeline.",
)
async def create_organizer_session(
    conference_id: UUID,
    payload: OrganizerSessionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerSessionResponse:
    """Add a session to conference."""
    client_ip = get_client_ip(request)

    stmt = select(Conference).where(Conference.id == conference_id)
    conference = (await db.execute(stmt)).scalar_one_or_none()
    if not conference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    if conference.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage sessions for this conference.",
        )

    if conference.status not in (ConferenceStatus.DRAFT.value, ConferenceStatus.CHANGES_REQUESTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sessions cannot be added while conference is in '{conference.status}'.",
        )

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session end_time must be later than start_time.",
        )

    session = Session(
        conference_id=conference.id,
        title=payload.title.strip(),
        abstract=payload.abstract.strip() if payload.abstract else None,
        speaker_names=payload.speaker_names.strip() if payload.speaker_names else None,
        track_name=payload.track_name.strip() if payload.track_name else None,
        hall_room=payload.hall_room.strip(),
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_cancelled=False,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    await record_audit_event(
        session=db,
        action_type="SESSION_CREATED",
        resource_type="SESSION",
        resource_id=str(session.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"title": session.title, "conference_id": str(conference.id)},
    )

    # Phase 6: Real-time event for session creation
    from app.core.events import event_broker
    await event_broker.publish(
        "session:created",
        {
            "conference_id": str(conference.id),
            "session_id": str(session.id),
            "title": session.title,
        },
    )

    return OrganizerSessionResponse(
        id=session.id,
        conference_id=session.conference_id,
        title=session.title,
        abstract=session.abstract,
        speaker_names=session.speaker_names,
        track_name=session.track_name,
        hall_room=session.hall_room,
        start_time=session.start_time,
        end_time=session.end_time,
        is_cancelled=session.is_cancelled,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.put(
    "/conferences/{conference_id}/sessions/{session_id}",
    response_model=OrganizerSessionResponse,
    summary="Update Agenda Session",
    description="Updates session title, time, hall/room, or speaker details.",
)
async def update_organizer_session(
    conference_id: UUID,
    session_id: UUID,
    payload: OrganizerSessionUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> OrganizerSessionResponse:
    """Update a session."""
    client_ip = get_client_ip(request)

    conf_stmt = select(Conference).where(Conference.id == conference_id)
    conference = (await db.execute(conf_stmt)).scalar_one_or_none()
    if not conference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    if conference.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify sessions for this conference.",
        )

    if conference.status not in (ConferenceStatus.DRAFT.value, ConferenceStatus.CHANGES_REQUESTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sessions cannot be modified while conference is in '{conference.status}'.",
        )

    sess_stmt = select(Session).where(Session.id == session_id, Session.conference_id == conference_id)
    session = (await db.execute(sess_stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found for this conference.",
        )

    if payload.title is not None:
        session.title = payload.title.strip()
    if payload.abstract is not None:
        session.abstract = payload.abstract.strip() if payload.abstract else None
    if payload.speaker_names is not None:
        session.speaker_names = payload.speaker_names.strip() if payload.speaker_names else None
    if payload.track_name is not None:
        session.track_name = payload.track_name.strip() if payload.track_name else None
    if payload.hall_room is not None:
        session.hall_room = payload.hall_room.strip()
    if payload.start_time is not None:
        session.start_time = payload.start_time
    if payload.end_time is not None:
        session.end_time = payload.end_time
    if payload.is_cancelled is not None:
        session.is_cancelled = payload.is_cancelled

    if session.end_time <= session.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session end_time must be later than start_time.",
        )

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)

    await record_audit_event(
        session=db,
        action_type="SESSION_UPDATED",
        resource_type="SESSION",
        resource_id=str(session.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"title": session.title},
    )

    # Phase 6: Real-time event for session update
    from app.core.events import event_broker
    await event_broker.publish(
        "session:updated",
        {
            "conference_id": str(conference_id),
            "session_id": str(session.id),
            "title": session.title,
        },
    )

    return OrganizerSessionResponse(
        id=session.id,
        conference_id=session.conference_id,
        title=session.title,
        abstract=session.abstract,
        speaker_names=session.speaker_names,
        track_name=session.track_name,
        hall_room=session.hall_room,
        start_time=session.start_time,
        end_time=session.end_time,
        is_cancelled=session.is_cancelled,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete(
    "/conferences/{conference_id}/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Agenda Session",
    description="Deletes a session from the conference agenda.",
)
async def delete_organizer_session(
    conference_id: UUID,
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a session."""
    client_ip = get_client_ip(request)

    conf_stmt = select(Conference).where(Conference.id == conference_id)
    conference = (await db.execute(conf_stmt)).scalar_one_or_none()
    if not conference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    if conference.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete sessions from this conference.",
        )

    if conference.status not in (ConferenceStatus.DRAFT.value, ConferenceStatus.CHANGES_REQUESTED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sessions cannot be deleted while conference is in '{conference.status}'.",
        )

    sess_stmt = select(Session).where(Session.id == session_id, Session.conference_id == conference_id)
    session = (await db.execute(sess_stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found for this conference.",
        )

    await db.delete(session)
    await db.commit()

    # Phase 6: Real-time event for session deletion
    from app.core.events import event_broker
    await event_broker.publish(
        "session:deleted",
        {
            "conference_id": str(conference_id),
            "session_id": str(session_id),
        },
    )

    await record_audit_event(
        session=db,
        action_type="SESSION_DELETED",
        resource_type="SESSION",
        resource_id=str(session_id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"conference_id": str(conference_id)},
    )

    return {"detail": "Session deleted successfully."}


# =============================================================================
# 5. Live Conference Control Plane (Temporal Phase 5)
# =============================================================================

@router.get(
    "/conferences/{conference_id}/live-state",
    response_model=ConferenceLiveStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Conference Live Temporal & Break State",
)
async def get_conference_live_state(
    conference_id: UUID,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> ConferenceLiveStateResponse:
    """Retrieve the real-time live temporal state, break status, and active announcements."""
    conf = await TemporalContextService.get_active_conference(db, conference_id)
    if not conf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    if conf.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view live control plane for this conference.",
        )

    return await TemporalContextService.get_current_conference_state(db, conference_id)


@router.post(
    "/conferences/{conference_id}/live-state",
    response_model=ConferenceLiveStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Set Conference Live Break, Schedule Delay, or Weather Override",
)
async def set_conference_live_state(
    conference_id: UUID,
    payload: ConferenceLiveStateUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> ConferenceLiveStateResponse:
    """Trigger a real-time break, delay, or environmental override and broadcast to the lounge."""
    client_ip = get_client_ip(request)

    conf = await TemporalContextService.get_active_conference(db, conference_id)
    if not conf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    if conf.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to control live state for this conference.",
        )

    # 1. Update live temporal state
    live_resp = await TemporalContextService.set_conference_live_state(
        db,
        conference_id=conference_id,
        payload=payload,
        triggered_by_user_id=current_user.id,
    )

    # 2. Automatically broadcast announcement to that conference's networking lounge
    announcement_text = live_resp.announcement_banner
    if not announcement_text:
        loc = payload.designated_location or "the main concourse"
        state_label = payload.custom_state_label or payload.current_state.replace("_", " ").title()
        if payload.current_state in ("TEA_BREAK", "LUNCH_BREAK"):
            announcement_text = f"📢 Organizer Announcement: {state_label} is now active at {loc}! Duration: {payload.duration_minutes} mins."
        elif payload.current_state == "IN_SESSION":
            announcement_text = f"🔔 Organizer Announcement: Sessions are resuming in {loc}. Delegates are requested to take their seats."
        else:
            announcement_text = f"📢 Organizer Announcement: {state_label} at {loc}."

    await AmbientLoungeService.broadcast_organizer_announcement(
        db=db,
        conference_id=conference_id,
        announcement_text=announcement_text,
    )

    # 3. Publish real-time event to SSE/WS subscribers
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:live_state_updated",
        {
            "conference_id": str(conference_id),
            "current_state": live_resp.current_state,
            "break_type": live_resp.break_type,
            "designated_location": live_resp.designated_location,
            "announcement_banner": announcement_text,
        },
    )

    await record_audit_event(
        session=db,
        action_type="CONFERENCE_LIVE_STATE_OVERRIDE",
        resource_type="CONFERENCE",
        resource_id=str(conference_id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={
            "current_state": payload.current_state,
            "break_type": payload.break_type,
            "duration_minutes": payload.duration_minutes,
            "delay_minutes": payload.delay_minutes,
            "weather_override": payload.weather_override,
        },
    )

    return live_resp


@router.delete(
    "/conferences/{conference_id}/live-state",
    status_code=status.HTTP_200_OK,
    summary="Reset Live Break Override to Normal Schedule",
)
async def reset_conference_live_state(
    conference_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Clear active live override and resume automatic schedule-based state."""
    client_ip = get_client_ip(request)

    conf = await TemporalContextService.get_active_conference(db, conference_id)
    if not conf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conference not found.",
        )

    if conf.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to control live state for this conference.",
        )

    stmt = select(ConferenceLiveState).where(ConferenceLiveState.conference_id == conference_id)
    live_state = await db.scalar(stmt)
    if live_state:
        live_state.is_active = False
        await db.commit()

        # Announce resumption of normal schedule in lounge
        await AmbientLoungeService.broadcast_organizer_announcement(
            db=db,
            conference_id=conference_id,
            announcement_text="🔔 Organizer Announcement: Live override concluded. Returning to regular scheduled sessions.",
        )

    await record_audit_event(
        session=db,
        action_type="CONFERENCE_LIVE_STATE_RESET",
        resource_type="CONFERENCE",
        resource_id=str(conference_id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"conference_id": str(conference_id)},
    )

    return {"detail": "Live conference state reset to schedule clock."}


@router.post(
    "/conferences/{conference_id}/lounge/host",
    status_code=status.HTTP_200_OK,
    summary="Host Live Networking Lounge with Kick-off Intro",
)
async def host_conference_lounge(
    conference_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Officially host the live networking lounge, broadcast kickoff announcement and intro prompt."""
    conf = await TemporalContextService.get_active_conference(db, conference_id)
    if not conf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conference not found.")

    if conf.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    lounge = await AmbientLoungeService.get_or_create_default_lounge(db, conference_id=conference_id)
    lounge.is_active = True
    await db.commit()

    # 1. Official Organizer Kickoff Announcement
    kickoff_text = (
        f"🎉 Welcome everyone! The Live Networking Lounge for {conf.title} at {conf.venue_name} is officially open! "
        f"Delegates are warmly invited to hang out, share session reflections, and connect with peers across the floor."
    )
    await AmbientLoungeService.broadcast_organizer_announcement(
        db=db,
        conference_id=conference_id,
        announcement_text=kickoff_text,
    )

    # 2. Immediate Kickoff Intro Question from Lounge Host
    next_turn = await AmbientLoungeService._get_next_turn_index(db, lounge.id)
    intro_msg = ChatroomMessage(
        chatroom_id=lounge.id,
        sender_id=None,
        sender_type=ChatroomSenderType.HOST.value,
        sender_name="Virtual Lounge Host",
        content="☕ Welcome delegates! To kick off our live networking: Which keynote track or session on the agenda are you looking forward to most today? Say hi below!",
        message_kind=ChatroomMessageKind.CHAT.value,
        turn_index=next_turn,
    )
    db.add(intro_msg)
    await db.commit()

    # 3. Broadcast SSE/WS event
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:lounge_hosted",
        {
            "conference_id": str(conference_id),
            "chatroom_id": str(lounge.id),
            "name": lounge.name,
        },
    )

    return {
        "status": "hosted",
        "conference_id": str(conference_id),
        "chatroom_id": str(lounge.id),
        "message": "Live Networking Lounge officially hosted with kickoff intro!",
    }


@router.post(
    "/conferences/{conference_id}/lounge/close",
    status_code=status.HTTP_200_OK,
    summary="Close Conference Networking Lounge",
)
async def close_conference_lounge(
    conference_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Close the live networking lounge, pausing ambient messages and member chats."""
    conf = await TemporalContextService.get_active_conference(db, conference_id)
    if not conf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conference not found.")

    if conf.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    lounge = await AmbientLoungeService.get_or_create_default_lounge(db, conference_id=conference_id)
    lounge.is_active = False

    # 1. Official Organizer Closing Notice
    next_turn = await AmbientLoungeService._get_next_turn_index(db, lounge.id)
    closing_msg = ChatroomMessage(
        chatroom_id=lounge.id,
        sender_id=None,
        sender_type=ChatroomSenderType.HOST.value,
        sender_name="Organizer Live Broadcast",
        content=(
            f"🛑 Lounge Notice: The Live Networking Lounge for {conf.title} has concluded for now. "
            f"Thank you delegates for engaging! Ambient messages and attendee chats are paused until the next live track."
        ),
        message_kind=ChatroomMessageKind.TEA_ANNOUNCEMENT.value,
        turn_index=next_turn,
    )
    db.add(closing_msg)
    await db.commit()

    # 2. Broadcast SSE/WS event
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:lounge_closed",
        {
            "conference_id": str(conference_id),
            "chatroom_id": str(lounge.id),
            "name": lounge.name,
        },
    )

    return {
        "status": "closed",
        "conference_id": str(conference_id),
        "chatroom_id": str(lounge.id),
        "message": "Live Networking Lounge closed successfully.",
    }


@router.post(
    "/conferences/{conference_id}/lounge/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset Conference Lounge Chat History",
)
async def reset_conference_lounge(
    conference_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    org_profile: OrganizerProfile = Depends(require_organizer),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Clear chat messages and presences for this conference lounge, re-initializing turn 0."""
    conf = await TemporalContextService.get_active_conference(db, conference_id)
    if not conf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conference not found.")

    if conf.organizer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    lounge = await AmbientLoungeService.get_or_create_default_lounge(db, conference_id=conference_id)

    # Delete messages and presences for this lounge
    await db.execute(delete(ChatroomMessage).where(ChatroomMessage.chatroom_id == lounge.id))
    await db.execute(delete(ChatroomPresence).where(ChatroomPresence.chatroom_id == lounge.id))

    # Re-create clean turn 0
    welcome_msg = ChatroomMessage(
        chatroom_id=lounge.id,
        sender_id=None,
        sender_type=ChatroomSenderType.HOST.value,
        sender_name="Virtual Lounge Host",
        content=(
            f"🎉 Welcome to the {lounge.name}! "
            f"This is an open town square for all delegates attending {conf.title} at {conf.venue_name} to chat, "
            f"share session takeaways, connect on mutual initiatives, and stay posted on break announcements."
        ),
        message_kind=ChatroomMessageKind.WELCOME.value,
        turn_index=0,
    )
    db.add(welcome_msg)
    await db.commit()

    return {"detail": "Lounge history cleared and reset to Turn 0."}
