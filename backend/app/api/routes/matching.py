"""Authenticated Participant Candidate Matching API routes (P4-WS2, GAP-06)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.dependencies import get_client_ip, get_current_user
from app.db.models.profile import AvailabilityStatus, ParticipantProfile
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import ErrorResponse
from app.schemas.matching import MatchEvaluationResult
from app.services.matching import find_candidate_matches_async

router = APIRouter(prefix="/matching", tags=["Participant Matching"])


@router.get(
    "/candidates",
    response_model=MatchEvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Discover Candidate Participant Matches",
    description=(
        "Evaluates and returns deterministically ranked participant match recommendations "
        "using canonical 4-factor scoring and dynamic re-weighting. Derives requester identity "
        "strictly from the validated session cookie/token (IDOR immune). "
        "Requires initialized profile, explicit opt-in consent (GAP-06), and non-DND availability."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Deterministically ranked candidate recommendations.",
            "model": MatchEvaluationResult,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication required or invalid/expired session.",
            "model": ErrorResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Requester lacks matching consent or is in DO_NOT_DISTURB / OFFLINE mode.",
            "model": ErrorResponse,
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Requester profile has not been initialized.",
            "model": ErrorResponse,
        },
    },
)
async def get_match_candidates(
    request: Request,
    filter_by_threshold: bool = Query(
        default=True,
        description="When true, filters candidates by threshold (default 0.65). When false, returns all eligible candidates without minimum score cutoff.",
    ),
    threshold: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Custom minimum composite score cutoff in [0.0, 1.0]. Overrides the default 0.65 threshold if provided.",
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Max candidates to return per page."),
    offset: int = Query(default=0, ge=0, description="Number of candidates to skip."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MatchEvaluationResult:
    """Evaluate, rank, and return eligible match candidates for the authenticated user."""
    # 1. Fetch requester's own profile to check hard eligibility prerequisites
    profile_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == current_user.id)
    profile_res = await db.execute(profile_stmt)
    profile = profile_res.scalar_one_or_none()

    if profile is None or profile.intent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant profile not found. Please initialize your profile via PUT /profile/me before searching for matches.",
        )

    # 2. Check explicit matching consent (GAP-06)
    if not profile.allow_agent_matching:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autonomous agent matching consent is not granted. Explicit opt-in (allow_agent_matching=True) is required to discover candidates (GAP-06).",
        )

    # 3. Check availability status boundaries
    ineligible_statuses = {AvailabilityStatus.DO_NOT_DISTURB, AvailabilityStatus.OFFLINE}
    if profile.availability in ineligible_statuses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Candidate discovery is paused while your availability is set to {profile.availability.value}.",
        )

    # 4. Execute deterministic matching query pipeline
    result = await find_candidate_matches_async(
        db=db,
        requester_id=current_user.id,
        filter_by_threshold=filter_by_threshold,
        custom_threshold=threshold,
        limit=limit,
        offset=offset,
    )

    # 5. Record sanitized security audit event (GAP-10)
    await record_audit_event(
        session=db,
        action_type="matching.candidates.discover",
        resource_type="matching.evaluation",
        resource_id=str(current_user.id),
        actor_username=current_user.username,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        payload={
            "action": "candidates_discovered",
            "status": "success",
            "details": f"evaluated={result.total_evaluated},matched={result.matched_count},returned={len(result.candidates)}",
        },
    )
    await db.commit()

    return result
