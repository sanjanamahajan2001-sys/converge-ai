"""Participant Profile API endpoints with strict ownership and IDOR defense (GAP-03, GAP-05, GAP-10)."""
import re
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.dependencies import get_client_ip, get_current_user
from app.db.models.activity import UserActivityEvent
from app.db.models.profile import ParticipantHobby, ParticipantProfile, ParticipantTopic
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import ErrorResponse
from app.schemas.profile import (
    CURATED_HOBBIES,
    CURATED_MOODS,
    AvailabilityStatus,
    ParticipationIntent,
    ProfileResponse,
    ProfileUpdate,
    PublicProfileResponse,
)

router = APIRouter(prefix="/profile", tags=["Participant Profiles"])


def parse_dob_string(dob_str: Optional[str]) -> Optional[date]:
    """Parse date of birth string in DD-MM-YYYY or YYYY-MM-DD format into date object."""
    if not dob_str:
        return None
    clean = dob_str.strip()
    if not clean:
        return None
    try:
        if re.match(r"^\d{2}-\d{2}-\d{4}$", clean):
            d, m, y = map(int, clean.split("-"))
            return date(y, m, d)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
            y, m, d = map(int, clean.split("-"))
            return date(y, m, d)
        return date.fromisoformat(clean)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date of birth format. Expected DD-MM-YYYY: {exc}",
        )


@router.get(
    "/catalog/moods",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="Retrieve Curated Reference Moods Catalog",
    description="Returns curated starter conversation preferences for attendees.",
)
async def get_curated_moods_catalog() -> List[str]:
    """Return curated conference mood preferences."""
    return CURATED_MOODS


@router.get(
    "/catalog/hobbies",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="Retrieve Curated Reference Hobbies Catalog",
    description="Returns the curated conference starter themes and social preferences (DOC-REQ-001 §2.1).",
)
async def get_curated_hobbies_catalog() -> List[str]:
    """Return the curated conference hobbies reference list."""
    return CURATED_HOBBIES


@router.get(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Authenticated Participant's Own Profile",
    description=(
        "Retrieves the active authenticated user's own profile, interests, and availability. "
        "Identity is derived strictly from the verified server-side session (IDOR immune)."
    ),
    responses={
        status.HTTP_200_OK: {"description": "Own profile retrieved successfully.", "model": ProfileResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required or session invalid.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Participant profile not yet initialized.", "model": ErrorResponse},
    },
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    """Resolve and return authenticated user's own profile."""
    # 1. Query own profile strictly by authenticated user ID
    result = await db.execute(
        select(ParticipantProfile).where(ParticipantProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant profile not found. Please initialize your profile via PUT /profile/me.",
        )

    # 2. Query hobbies and topics
    h_res = await db.execute(
        select(ParticipantHobby.hobby_name)
        .where(ParticipantHobby.user_id == current_user.id)
        .order_by(ParticipantHobby.id)
    )
    hobbies = list(h_res.scalars().all())

    t_res = await db.execute(
        select(ParticipantTopic.topic_keyword)
        .where(ParticipantTopic.user_id == current_user.id)
        .order_by(ParticipantTopic.id)
    )
    topics = list(t_res.scalars().all())

    return ProfileResponse(
        user_id=profile.user_id,
        company_name=current_user.company_name,
        job_title=current_user.job_title,
        intent=profile.intent,
        bio_summary=profile.bio_summary,
        availability=profile.availability,
        allow_agent_matching=profile.allow_agent_matching,
        allow_agent_dm_initiation=getattr(profile, "allow_agent_dm_initiation", True),
        contact_sharing_policy=getattr(profile, "contact_sharing_policy", "ASK_HUMAN_FIRST"),
        current_mood=profile.active_mood,
        mood_updated_at=profile.mood_updated_at,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth.strftime("%d-%m-%Y") if profile.date_of_birth else None,
        location=profile.location,
        location_lat=profile.location_lat,
        location_lng=profile.location_lng,
        hobbies=hobbies,
        topics=topics,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update or Initialize Authenticated Participant's Profile",
    description=(
        "Updates or initializes the authenticated user's profile and synchronizes interests. "
        "Enforces partial updates, atomic tag synchronization, mass assignment defense, "
        "and explicit matching consent verification."
    ),
    responses={
        status.HTTP_200_OK: {"description": "Profile updated successfully.", "model": ProfileResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid input or constraint violation.", "model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "CSRF verification failed.", "model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Payload validation error."},
    },
)
async def update_my_profile(
    request: Request,
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProfileResponse:
    """Atomically update or initialize the caller's own profile."""
    # 1. Fetch existing profile for the authenticated caller
    result = await db.execute(
        select(ParticipantProfile).where(ParticipantProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    is_initialization = profile is None

    # 2. Initialize or update fields
    if profile is None:
        clean_mood = payload.current_mood.strip() if payload.current_mood else None
        clean_gender = payload.gender.strip() if payload.gender else None
        clean_location = payload.location.strip() if payload.location else None
        dob = parse_dob_string(payload.date_of_birth)
        profile = ParticipantProfile(
            user_id=current_user.id,
            intent=payload.intent if payload.intent is not None else ParticipationIntent.NETWORKING,
            bio_summary=payload.bio_summary if payload.bio_summary else None,
            availability=payload.availability if payload.availability is not None else AvailabilityStatus.AVAILABLE,
            allow_agent_matching=payload.allow_agent_matching if payload.allow_agent_matching is not None else False,
            allow_agent_dm_initiation=payload.allow_agent_dm_initiation if payload.allow_agent_dm_initiation is not None else True,
            contact_sharing_policy=payload.contact_sharing_policy if payload.contact_sharing_policy else "ASK_HUMAN_FIRST",
            current_mood=clean_mood if clean_mood else None,
            mood_updated_at=datetime.now(timezone.utc) if clean_mood else None,
            gender=clean_gender if clean_gender else None,
            date_of_birth=dob,
            location=clean_location if clean_location else None,
            location_lat=payload.location_lat,
            location_lng=payload.location_lng,
        )
        db.add(profile)
    else:
        # Partial update semantics: only update fields explicitly passed
        if payload.intent is not None:
            profile.intent = payload.intent
        if payload.bio_summary is not None:
            profile.bio_summary = payload.bio_summary if payload.bio_summary else None
        if payload.availability is not None:
            profile.availability = payload.availability
        if payload.allow_agent_matching is not None:
            profile.allow_agent_matching = payload.allow_agent_matching
        if payload.allow_agent_dm_initiation is not None:
            profile.allow_agent_dm_initiation = payload.allow_agent_dm_initiation
        if payload.contact_sharing_policy is not None:
            profile.contact_sharing_policy = payload.contact_sharing_policy
        if "current_mood" in payload.model_fields_set:
            clean_mood = payload.current_mood.strip() if payload.current_mood else None
            profile.current_mood = clean_mood if clean_mood else None
            profile.mood_updated_at = datetime.now(timezone.utc) if clean_mood else None
        if "gender" in payload.model_fields_set:
            clean_gender = payload.gender.strip() if payload.gender else None
            profile.gender = clean_gender if clean_gender else None
        if "date_of_birth" in payload.model_fields_set:
            profile.date_of_birth = parse_dob_string(payload.date_of_birth)
        if "location" in payload.model_fields_set:
            clean_location = payload.location.strip() if payload.location else None
            profile.location = clean_location if clean_location else None
        if "location_lat" in payload.model_fields_set:
            profile.location_lat = payload.location_lat
        if "location_lng" in payload.model_fields_set:
            profile.location_lng = payload.location_lng

    # Update user identity fields (company_name, job_title) if passed
    if "company_name" in payload.model_fields_set:
        clean_company = payload.company_name.strip() if payload.company_name else None
        current_user.company_name = clean_company if clean_company else None
    if "job_title" in payload.model_fields_set:
        clean_title = payload.job_title.strip() if payload.job_title else None
        current_user.job_title = clean_title if clean_title else None

    # 3. Synchronize hobbies atomically if provided
    if payload.hobbies is not None:
        await db.execute(
            delete(ParticipantHobby).where(ParticipantHobby.user_id == current_user.id)
        )
        for h_name in payload.hobbies:
            db.add(ParticipantHobby(user_id=current_user.id, hobby_name=h_name))

    # 4. Synchronize topics atomically if provided
    if payload.topics is not None:
        await db.execute(
            delete(ParticipantTopic).where(ParticipantTopic.user_id == current_user.id)
        )
        for t_keyword in payload.topics:
            db.add(ParticipantTopic(user_id=current_user.id, topic_keyword=t_keyword))

    # 5. Flush to enforce constraint checking within the transaction
    await db.flush()

    # 6. Retrieve synchronized tags
    h_res = await db.execute(
        select(ParticipantHobby.hobby_name)
        .where(ParticipantHobby.user_id == current_user.id)
        .order_by(ParticipantHobby.id)
    )
    hobbies = list(h_res.scalars().all())

    t_res = await db.execute(
        select(ParticipantTopic.topic_keyword)
        .where(ParticipantTopic.user_id == current_user.id)
        .order_by(ParticipantTopic.id)
    )
    topics = list(t_res.scalars().all())

    # 7. Record security audit event with scrubbed whitelisted payload
    client_ip = get_client_ip(request)
    await record_audit_event(
        session=db,
        action_type="PROFILE_INITIALIZED" if is_initialization else "PROFILE_UPDATED",
        resource_type="PROFILE",
        resource_id=str(current_user.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={
            "status": "SUCCESS",
            "details": f"intent={profile.intent.value};matching={profile.allow_agent_matching};hobbies={len(hobbies)};topics={len(topics)}",
        },
    )

    db.add(
        UserActivityEvent(
            user_id=current_user.id,
            event_type="FEATURE_CLICK",
            feature_name="PROFILE_UPDATE",
            target_resource_id=str(current_user.id),
            details={
                "action": "initialize" if is_initialization else "update",
                "hobbies_count": len(hobbies),
                "topics_count": len(topics),
            },
        )
    )

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse(
        user_id=profile.user_id,
        company_name=current_user.company_name,
        job_title=current_user.job_title,
        intent=profile.intent,
        bio_summary=profile.bio_summary,
        availability=profile.availability,
        allow_agent_matching=profile.allow_agent_matching,
        allow_agent_dm_initiation=getattr(profile, "allow_agent_dm_initiation", True),
        contact_sharing_policy=getattr(profile, "contact_sharing_policy", "ASK_HUMAN_FIRST"),
        current_mood=profile.active_mood,
        mood_updated_at=profile.mood_updated_at,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth.strftime("%d-%m-%Y") if profile.date_of_birth else None,
        location=profile.location,
        location_lat=profile.location_lat,
        location_lng=profile.location_lng,
        hobbies=hobbies,
        topics=topics,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/{id}",
    response_model=PublicProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Public Participant Profile",
    description=(
        "Retrieves the public profile projection for a conference participant by their user ID. "
        "Requires authenticated session. Private contact details (email, phone, credentials) "
        "and internal metadata are strictly excluded (GAP-03, GAP-10)."
    ),
    responses={
        status.HTTP_200_OK: {"description": "Public profile retrieved.", "model": PublicProfileResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Participant profile not found.", "model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Malformed UUID parameter."},
    },
)
async def get_public_profile(
    id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PublicProfileResponse:
    """Retrieve sanitized public profile projection for an active participant."""
    # 1. Query target active user
    user_res = await db.execute(
        select(User).where(User.id == id, User.is_active == True)
    )
    target_user = user_res.scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant profile not found.",
        )

    # 2. Query target profile
    prof_res = await db.execute(
        select(ParticipantProfile).where(ParticipantProfile.user_id == id)
    )
    target_profile = prof_res.scalar_one_or_none()

    if target_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant profile not found.",
        )

    # 3. Query target hobbies and topics
    h_res = await db.execute(
        select(ParticipantHobby.hobby_name)
        .where(ParticipantHobby.user_id == id)
        .order_by(ParticipantHobby.id)
    )
    hobbies = list(h_res.scalars().all())

    t_res = await db.execute(
        select(ParticipantTopic.topic_keyword)
        .where(ParticipantTopic.user_id == id)
        .order_by(ParticipantTopic.id)
    )
    topics = list(t_res.scalars().all())

    # 4. Record audit event for profile viewing
    client_ip = get_client_ip(request)
    await record_audit_event(
        session=db,
        action_type="PROFILE_VIEWED",
        resource_type="PROFILE",
        resource_id=str(id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=client_ip,
        payload={"status": "SUCCESS"},
    )
    await db.commit()

    # 5. Return explicit allowlist projection — zero private fields
    return PublicProfileResponse(
        user_id=target_user.id,
        full_name=target_user.full_name,
        company_name=target_user.company_name,
        job_title=target_user.job_title,
        intent=target_profile.intent,
        bio_summary=target_profile.bio_summary,
        availability=target_profile.availability,
        gender=target_profile.gender,
        date_of_birth=target_profile.date_of_birth.strftime("%d-%m-%Y") if target_profile.date_of_birth else None,
        location=target_profile.location,
        hobbies=hobbies,
        topics=topics,
    )
