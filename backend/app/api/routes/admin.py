"""Dedicated Administration Portal APIs (Phase 2).

Provides administrative authentication, session control, access authorization,
and platform metrics exclusively for verified administrators.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import and_, asc, cast, desc, func, or_, select, String, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_event
from app.core.dependencies import get_client_ip, get_current_session, require_admin
from app.core.security import verify_dummy_password, verify_password
from app.core.session import (
    UserSession,
    clear_session_cookie,
    create_session,
    revoke_session,
    set_session_cookie,
)
from app.db.models.activity import UserActivityEvent
from app.db.models.agenda import (
    BookmarkedSession,
    Conference,
    ConferenceReviewLog,
    ConferenceStatus,
    Session as DbConferenceSession,
    SessionIntentDecision,
)
from app.db.models.business import BusinessProfile
from app.db.models.conversation import Conversation
from app.db.models.organizer import OrganizerProfile, OrganizerVerificationStatus
from app.db.models.profile import ParticipantProfile
from app.db.models.session import UserSession as DbUserSession
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminActivityItem,
    AdminAttendanceDecisionItem,
    AdminBookmarkedSessionItem,
    AdminBusinessProfileDetail,
    AdminConferenceDecisionRequest,
    AdminConferenceDecisionResponse,
    AdminConferenceDetailResponse,
    AdminConferenceOrganizerSummary,
    AdminConferenceQueueItem,
    AdminConferenceQueueResponse,
    AdminConferenceQueueStats,
    AdminConferenceReviewLogItem,
    AdminConferenceSessionItem,
    AdminConversationHistoryItem,
    AdminOfferingDetail,
    AdminOrganizerItem,
    AdminOrganizersListResponse,
    AdminOrganizersListStats,
    AdminRequirementDetail,
    AdminUpdateOrganizerVerificationRequest,
    AdminUpdateOrganizerVerificationResponse,
    AdminUpdateUserStatusRequest,
    AdminUpdateUserStatusResponse,
    AdminUserAccountDetail,
    AdminUserActivityBlock,
    AdminUserAgendaBlock,
    AdminUserConversationsBlock,
    AdminUserDetailResponse,
    AdminUserDirectoryStats,
    AdminUserProfileDetail,
    AdminUserSessionItem,
    AdminUserSessionsBlock,
    AdminUsersListResponse,
    AdminUserSummary,
    ConferenceDecisionAction,
)
from app.schemas.auth import (
    UserIdentityResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserLogoutResponse,
)
from app.db.models.proposal import ProposalStatus, ProposalType
from app.db.models.quote import EmailDeliveryStatus
from app.schemas.proposal import AdminProposalListResponse, ProposalDetailResponse
from app.schemas.quote import AdminQuoteDetailResponse, AdminQuoteListResponse
from app.services.proposal import ProposalService
from app.services.quote import QuoteService
from app.services.brochure import BrochureService
from app.schemas.brochure import (
    AdminBrochureAdAssignRequest,
    AdminBrochureAdDetail,
    AdminBrochureAdsListResponse,
    AdminBrochureAnalyticsOverview,
    AdminCompanyBrochureOption,
    BrochureAdCreate,
    BrochureAdUpdate,
    FlipbookViewerSettings,
    FlipbookViewerSettingsUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/auth/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Dedicated Login",
    description="Authenticate an administrator with username/email and password, strictly verifying administrative authorization.",
)
async def admin_login(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> UserLoginResponse:
    """Verify administrator credentials, reject non-admins with 403, and issue an administrative session."""
    client_ip = get_client_ip(request)
    identifier_clean = payload.identifier.strip().lower()

    # 1. Query user by username or email
    stmt = select(User).where(
        or_(
            func.lower(User.username) == identifier_clean,
            func.lower(User.email) == identifier_clean,
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # 2. Timing attack mitigation: verify credentials in constant time
    if not user:
        verify_dummy_password(payload.password)
        await record_audit_event(
            session=db,
            action_type="ADMIN_LOGIN_FAILURE_UNKNOWN_USER",
            resource_type="core.users",
            actor_username=identifier_clean,
            ip_address=client_ip,
            payload={"reason": "User not found"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials.",
        )

    # 3. Verify bcrypt password hash
    if not verify_password(payload.password, user.password_hash):
        await record_audit_event(
            session=db,
            user_id=user.id,
            action_type="ADMIN_LOGIN_FAILURE_PASSWORD",
            resource_type="core.users",
            resource_id=str(user.id),
            actor_username=user.username,
            ip_address=client_ip,
            payload={"reason": "Password mismatch"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials.",
        )

    # 4. Enforce active account status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive or disabled.",
        )

    # 5. STRICT ADMINISTRATIVE ROLE VERIFICATION
    # Regular users attempting to login through the admin gateway are rejected with 403 Forbidden
    if not user.is_admin:
        await record_audit_event(
            session=db,
            user_id=user.id,
            action_type="ADMIN_ACCESS_DENIED_NON_ADMIN",
            resource_type="core.users",
            resource_id=str(user.id),
            actor_username=user.username,
            ip_address=client_ip,
            payload={"details": "Non-admin attempted admin login"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have administrative privileges.",
        )

    # 6. Issue server-side session and set HttpOnly session cookie
    user_agent = request.headers.get("user-agent")
    session_record, raw_token = await create_session(
        session=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    settings = getattr(request.app.state, "settings", None)
    is_secure = settings.is_production() if settings else False
    set_session_cookie(response=response, raw_token=raw_token, secure=is_secure)

    # 7. Record successful administrative login audit trail
    await record_audit_event(
        session=db,
        user_id=user.id,
        action_type="ADMIN_LOGIN_SUCCESS",
        resource_type="core.user_sessions",
        resource_id=str(session_record.id),
        actor_username=user.username,
        ip_address=client_ip,
        payload={"details": "Administrative login successful"},
    )
    await db.commit()

    return UserLoginResponse(
        status="authenticated",
        user_id=user.id,
        username=user.username,
        email=user.email,
        expires_at=session_record.expires_at,
    )


@router.get(
    "/auth/me",
    response_model=UserIdentityResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Current Identity",
    description="Verify and retrieve the currently authenticated administrator profile.",
)
async def admin_get_me(
    current_admin: User = Depends(require_admin),
) -> UserIdentityResponse:
    """Return verified administrator identity attributes."""
    return UserIdentityResponse(
        id=current_admin.id,
        username=current_admin.username,
        email=current_admin.email,
        full_name=current_admin.full_name,
        company_name=current_admin.company_name,
        job_title=current_admin.job_title,
        is_active=current_admin.is_active,
        is_admin=current_admin.is_admin,
    )


@router.post(
    "/auth/logout",
    response_model=UserLogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
    description="Revoke the active administrative session and clear the session cookie.",
)
async def admin_logout(
    request: Request,
    response: Response,
    current_session: UserSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db_session),
) -> UserLogoutResponse:
    """Revoke active administrator session."""
    client_ip = get_client_ip(request)
    current_session.revoked_at = datetime.now(timezone.utc)
    await record_audit_event(
        session=db,
        user_id=current_session.user_id,
        action_type="ADMIN_LOGOUT",
        resource_type="core.user_sessions",
        resource_id=str(current_session.id),
        actor_username=current_session.user.username if current_session.user else "admin",
        ip_address=client_ip,
    )
    await db.commit()

    settings = getattr(request.app.state, "settings", None)
    is_secure = settings.is_production() if settings else False
    clear_session_cookie(response=response, secure=is_secure)

    return UserLogoutResponse(
        status="logged_out",
        detail="Administrative session revoked successfully.",
    )


@router.get(
    "/overview",
    status_code=status.HTTP_200_OK,
    summary="Admin Dashboard Overview Metrics",
    description="Retrieve aggregated statistics for the admin dashboard foundation (users, active sessions, conversations).",
)
async def get_admin_overview(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Provide dashboard metrics for the administrator."""
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)

    # 1. Total users
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    # 2. Active users (is_active = True)
    active_users_res = await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    active_users = active_users_res.scalar() or 0

    # 3. Completed profiles count
    completed_profiles_res = await db.execute(
        select(func.count(ParticipantProfile.user_id)).where(
            or_(
                ParticipantProfile.bio_summary.isnot(None),
                ParticipantProfile.location.isnot(None),
                ParticipantProfile.gender.isnot(None),
            )
        )
    )
    completed_profiles = completed_profiles_res.scalar() or 0
    profile_completion_pct = round((completed_profiles / total_users * 100), 1) if total_users > 0 else 0.0

    # 4. Active sessions today (last_accessed_at in last 24h and not revoked)
    active_today_res = await db.execute(
        select(func.count(func.distinct(DbUserSession.user_id))).where(
            DbUserSession.last_accessed_at >= one_day_ago,
            DbUserSession.revoked_at.is_(None),
        )
    )
    active_today = active_today_res.scalar() or 0

    # 5. Total conversations
    total_convs_res = await db.execute(select(func.count(Conversation.id)))
    total_conversations = total_convs_res.scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "profile_completion_pct": profile_completion_pct,
        "active_users_today": active_today,
        "total_conversations": total_conversations,
        "admin_username": current_admin.username,
        "generated_at": now.isoformat(),
    }


@router.get(
    "/users",
    response_model=AdminUsersListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Users Directory",
    description="Retrieve paginated conference users with server-side search, multi-attribute filtering, and engagement telemetry.",
)
async def list_admin_users(
    search: Optional[str] = Query(None, description="Search by username, email, full name, company, or ID"),
    status: Optional[str] = Query("all", description="Filter by account status: all, active, inactive, admin"),
    profile_status: Optional[str] = Query("all", description="Filter by profile: all, with_profile, incomplete"),
    gender: Optional[str] = Query("all", description="Filter by gender: all, male, female, non_binary, etc."),
    registration_period: Optional[str] = Query("all", description="Filter by registration timeframe: all, today, week, month"),
    commercial_role: Optional[str] = Query("all", description="Filter by commercial role: all, any, buyer, supplier, vendor, distributor, partner"),
    sort_by: str = Query("created_at", description="Sort field: created_at, username, full_name"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUsersListResponse:
    """Server-side searchable, filterable, and paginated conference user directory for administrators."""
    now = datetime.now(timezone.utc)
    conditions = []

    # 1. Search filter
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(User.username).like(term),
                func.lower(User.email).like(term),
                func.lower(User.full_name).like(term),
                func.lower(User.company_name).like(term),
                cast(User.id, String).ilike(term),
            )
        )

    # 2. Account Status filter
    if status == "active":
        conditions.append(User.is_active.is_(True))
    elif status == "inactive":
        conditions.append(User.is_active.is_(False))
    elif status == "admin":
        conditions.append(User.is_admin.is_(True))

    # 3. Registration period filter
    if registration_period == "today":
        conditions.append(User.created_at >= (now - timedelta(days=1)))
    elif registration_period == "week":
        conditions.append(User.created_at >= (now - timedelta(days=7)))
    elif registration_period == "month":
        conditions.append(User.created_at >= (now - timedelta(days=30)))

    # 4. Profile completion & Gender filters
    if profile_status == "with_profile":
        conditions.append(ParticipantProfile.user_id.isnot(None))
    elif profile_status == "incomplete":
        conditions.append(ParticipantProfile.user_id.is_(None))

    if gender and gender.lower() != "all":
        conditions.append(func.lower(ParticipantProfile.gender) == gender.strip().lower())

    # 5. Commercial Role filter
    if commercial_role and commercial_role.lower() != "all":
        crole = commercial_role.strip().lower()
        if crole == "any":
            conditions.append(BusinessProfile.id.isnot(None))
        elif crole == "buyer":
            conditions.append(and_(BusinessProfile.id.isnot(None), BusinessProfile.is_buyer.is_(True)))
        elif crole == "supplier":
            conditions.append(and_(BusinessProfile.id.isnot(None), BusinessProfile.is_supplier.is_(True)))
        elif crole == "vendor":
            conditions.append(and_(BusinessProfile.id.isnot(None), BusinessProfile.is_vendor.is_(True)))
        elif crole == "distributor":
            conditions.append(and_(BusinessProfile.id.isnot(None), BusinessProfile.is_distributor.is_(True)))
        elif crole == "partner":
            conditions.append(and_(BusinessProfile.id.isnot(None), BusinessProfile.is_partner.is_(True)))

    # Total matching users count
    count_stmt = (
        select(func.count(func.distinct(User.id)))
        .outerjoin(ParticipantProfile, User.id == ParticipantProfile.user_id)
        .outerjoin(BusinessProfile, User.id == BusinessProfile.user_id)
    )
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Summary statistics for users directory header
    tot_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    act_users = (await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))).scalar() or 0
    inact_users = tot_users - act_users
    prof_users = (await db.execute(select(func.count(ParticipantProfile.user_id)))).scalar() or 0
    today_active = (await db.execute(
        select(func.count(func.distinct(DbUserSession.user_id))).where(
            DbUserSession.last_accessed_at >= (now - timedelta(days=1)),
            DbUserSession.revoked_at.is_(None),
        )
    )).scalar() or 0
    biz_users = (await db.execute(select(func.count(BusinessProfile.id)))).scalar() or 0

    directory_stats = AdminUserDirectoryStats(
        total_users=tot_users,
        active_users=act_users,
        inactive_users=inact_users,
        with_profile=prof_users,
        active_today=today_active,
        with_business_profile=biz_users,
    )

    # Sort column selection
    sort_col = User.created_at
    if sort_by == "username":
        sort_col = func.lower(User.username)
    elif sort_by == "full_name":
        sort_col = func.lower(User.full_name)

    order_expr = desc(sort_col) if sort_order.lower() == "desc" else asc(sort_col)

    # Pagination calculation
    offset = (page - 1) * limit
    total_pages = max(1, (total + limit - 1) // limit)

    # Query users page
    user_stmt = (
        select(User)
        .outerjoin(ParticipantProfile, User.id == ParticipantProfile.user_id)
        .outerjoin(BusinessProfile, User.id == BusinessProfile.user_id)
        .options(
            selectinload(User.profile),
            selectinload(User.hobbies),
            selectinload(User.topics),
        )
    )
    if conditions:
        user_stmt = user_stmt.where(and_(*conditions))

    user_stmt = user_stmt.order_by(order_expr).offset(offset).limit(limit)
    users_page = (await db.execute(user_stmt)).scalars().all()
    user_ids = [u.id for u in users_page]

    # Batch queries for conference engagement telemetry
    bookmarks_map: Dict[UUID, int] = {}
    attendance_map: Dict[UUID, int] = {}
    conversations_map: Dict[UUID, int] = {}
    activity_map: Dict[UUID, int] = {}
    last_active_map: Dict[UUID, datetime] = {}
    business_profiles_map: Dict[UUID, BusinessProfile] = {}

    if user_ids:
        # Bookmarks
        bm_res = await db.execute(
            select(BookmarkedSession.user_id, func.count(BookmarkedSession.session_id))
            .where(BookmarkedSession.user_id.in_(user_ids))
            .group_by(BookmarkedSession.user_id)
        )
        for uid, count in bm_res.all():
            bookmarks_map[uid] = count

        # Attendance Intent Decisions
        att_res = await db.execute(
            select(SessionIntentDecision.user_id, func.count(SessionIntentDecision.id))
            .where(SessionIntentDecision.user_id.in_(user_ids))
            .group_by(SessionIntentDecision.user_id)
        )
        for uid, count in att_res.all():
            attendance_map[uid] = count

        # Conversations (both initiator and target)
        conv_init_res = await db.execute(
            select(Conversation.initiator_id, func.count(Conversation.id))
            .where(Conversation.initiator_id.in_(user_ids))
            .group_by(Conversation.initiator_id)
        )
        for uid, count in conv_init_res.all():
            conversations_map[uid] = conversations_map.get(uid, 0) + count

        conv_target_res = await db.execute(
            select(Conversation.target_id, func.count(Conversation.id))
            .where(Conversation.target_id.in_(user_ids))
            .group_by(Conversation.target_id)
        )
        for uid, count in conv_target_res.all():
            conversations_map[uid] = conversations_map.get(uid, 0) + count

        # Activity events count
        act_res = await db.execute(
            select(UserActivityEvent.user_id, func.count(UserActivityEvent.id))
            .where(UserActivityEvent.user_id.in_(user_ids))
            .group_by(UserActivityEvent.user_id)
        )
        for uid, count in act_res.all():
            activity_map[uid] = count

        # Last active session timestamp
        session_res = await db.execute(
            select(DbUserSession.user_id, func.max(DbUserSession.last_accessed_at))
            .where(DbUserSession.user_id.in_(user_ids))
            .group_by(DbUserSession.user_id)
        )
        for uid, dt in session_res.all():
            last_active_map[uid] = dt

        # Business Profiles batch query
        bp_stmt = (
            select(BusinessProfile)
            .where(BusinessProfile.user_id.in_(user_ids))
            .options(
                selectinload(BusinessProfile.offerings),
                selectinload(BusinessProfile.requirements),
            )
        )
        bp_res = await db.execute(bp_stmt)
        for bp in bp_res.scalars().all():
            business_profiles_map[bp.user_id] = bp

    # Construct user summaries
    items: List[AdminUserSummary] = []
    for u in users_page:
        prof = u.profile
        intent_str = None
        if prof and prof.intent:
            intent_str = prof.intent.value if hasattr(prof.intent, "value") else str(prof.intent)

        avail_str = None
        if prof and prof.availability:
            avail_str = prof.availability.value if hasattr(prof.availability, "value") else str(prof.availability)

        last_act = last_active_map.get(u.id) or u.updated_at or u.created_at

        bp = business_profiles_map.get(u.id)
        commercial_roles = []
        if bp:
            if bp.is_buyer:
                commercial_roles.append("BUYER")
            if bp.is_supplier:
                commercial_roles.append("SUPPLIER")
            if bp.is_vendor:
                commercial_roles.append("VENDOR")
            if bp.is_distributor:
                commercial_roles.append("DISTRIBUTOR")
            if bp.is_partner:
                commercial_roles.append("PARTNER")

        items.append(
            AdminUserSummary(
                id=u.id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                company_name=u.company_name,
                job_title=u.job_title,
                phone_number=u.phone_number,
                is_active=u.is_active,
                is_admin=u.is_admin,
                created_at=u.created_at,
                updated_at=u.updated_at,
                has_profile=prof is not None,
                bio_summary=prof.bio_summary if prof else None,
                gender=prof.gender if prof else None,
                date_of_birth=prof.date_of_birth if prof else None,
                location=prof.location if prof else None,
                location_lat=prof.location_lat if prof else None,
                location_lng=prof.location_lng if prof else None,
                intent=intent_str,
                availability=avail_str,
                allow_agent_matching=prof.allow_agent_matching if prof else None,
                current_mood=prof.active_mood if prof else None,
                hobbies=[h.hobby_name for h in u.hobbies] if u.hobbies else [],
                topics=[t.topic_keyword for t in u.topics] if u.topics else [],
                bookmarks_count=bookmarks_map.get(u.id, 0),
                attendance_count=attendance_map.get(u.id, 0),
                conversations_count=conversations_map.get(u.id, 0),
                activity_events_count=activity_map.get(u.id, 0),
                has_business_profile=bp is not None,
                commercial_roles=commercial_roles,
                offerings_count=len(bp.offerings) if bp and bp.offerings else 0,
                requirements_count=len(bp.requirements) if bp and bp.requirements else 0,
                last_active_at=last_act,
            )
        )

    return AdminUsersListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        stats=directory_stats,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Comprehensive User Detail View",
    description="Retrieve full attendee footprint including account, profile, sessions, agenda bookmarks, conversations, and activity telemetry.",
)
async def get_admin_user_detail(
    user_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUserDetailResponse:
    """Retrieve full comprehensive user details for administrators (Phase 4)."""
    # 1. Fetch user with profile, hobbies, and topics
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.profile),
            selectinload(User.hobbies),
            selectinload(User.topics),
        )
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' was not found.",
        )

    prof = user.profile
    intent_str = None
    if prof and prof.intent:
        intent_str = prof.intent.value if hasattr(prof.intent, "value") else str(prof.intent)

    avail_str = None
    if prof and prof.availability:
        avail_str = prof.availability.value if hasattr(prof.availability, "value") else str(prof.availability)

    account_detail = AdminUserAccountDetail(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        job_title=user.job_title,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

    profile_detail = AdminUserProfileDetail(
        has_profile=prof is not None,
        bio_summary=prof.bio_summary if prof else None,
        gender=prof.gender if prof else None,
        date_of_birth=prof.date_of_birth if prof else None,
        location=prof.location if prof else None,
        location_lat=prof.location_lat if prof else None,
        location_lng=prof.location_lng if prof else None,
        intent=intent_str,
        availability=avail_str,
        allow_agent_matching=prof.allow_agent_matching if prof else None,
        current_mood=prof.active_mood if prof else None,
        hobbies=[h.hobby_name for h in user.hobbies] if user.hobbies else [],
        topics=[t.topic_keyword for t in user.topics] if user.topics else [],
    )

    # 2. Query user login sessions
    now = datetime.now(timezone.utc)
    sessions_stmt = (
        select(DbUserSession)
        .where(DbUserSession.user_id == user_id)
        .order_by(desc(DbUserSession.created_at))
        .limit(25)
    )
    sessions_res = await db.execute(sessions_stmt)
    all_sessions = sessions_res.scalars().all()

    session_items = [
        AdminUserSessionItem(
            id=s.id,
            created_at=s.created_at,
            expires_at=s.expires_at,
            last_accessed_at=s.last_accessed_at,
            revoked_at=s.revoked_at,
            is_active=s.revoked_at is None and s.expires_at > now,
            ip_address=str(s.ip_address) if s.ip_address else None,
            user_agent=s.user_agent,
        )
        for s in all_sessions
    ]
    tot_logins_res = await db.execute(
        select(func.count(DbUserSession.id)).where(DbUserSession.user_id == user_id)
    )
    tot_logins = tot_logins_res.scalar() or len(all_sessions)
    act_sessions = sum(1 for s in session_items if s.is_active)

    sessions_block = AdminUserSessionsBlock(
        total_logins=tot_logins,
        active_sessions_count=act_sessions,
        recent_sessions=session_items,
    )

    # 3. Query agenda bookmarks and attendance intent decisions
    bm_stmt = (
        select(BookmarkedSession, DbConferenceSession)
        .join(DbConferenceSession, BookmarkedSession.session_id == DbConferenceSession.id)
        .where(BookmarkedSession.user_id == user_id)
        .order_by(desc(BookmarkedSession.created_at))
    )
    bm_res = await db.execute(bm_stmt)
    bookmarks_list = [
        AdminBookmarkedSessionItem(
            session_id=sess.id,
            title=sess.title,
            track_name=sess.track_name,
            hall_room=sess.hall_room,
            speaker_names=sess.speaker_names,
            start_time=sess.start_time,
            end_time=sess.end_time,
            created_at=bm.created_at,
        )
        for bm, sess in bm_res.all()
    ]

    dec_stmt = (
        select(SessionIntentDecision, DbConferenceSession)
        .join(DbConferenceSession, SessionIntentDecision.session_id == DbConferenceSession.id)
        .where(SessionIntentDecision.user_id == user_id)
        .order_by(desc(SessionIntentDecision.created_at))
    )
    dec_res = await db.execute(dec_stmt)
    decisions_list = [
        AdminAttendanceDecisionItem(
            session_id=sess.id,
            title=sess.title,
            decision=dec.decision.value if hasattr(dec.decision, "value") else str(dec.decision),
            hall_room=sess.hall_room,
            start_time=sess.start_time,
            end_time=sess.end_time,
        )
        for dec, sess in dec_res.all()
    ]

    agenda_block = AdminUserAgendaBlock(
        bookmarks_count=len(bookmarks_list),
        bookmarks=bookmarks_list,
        attendance_decisions=decisions_list,
    )

    # 4. Query conversations (both initiator and target)
    conv_stmt = (
        select(Conversation)
        .where(or_(Conversation.initiator_id == user_id, Conversation.target_id == user_id))
        .options(
            selectinload(Conversation.initiator),
            selectinload(Conversation.target),
            selectinload(Conversation.messages),
        )
        .order_by(desc(Conversation.created_at))
    )
    conv_res = await db.execute(conv_stmt)
    conversations = conv_res.scalars().all()

    conv_items = []
    initiated_count = 0
    participated_count = 0

    for c in conversations:
        is_initiator = c.initiator_id == user_id
        if is_initiator:
            initiated_count += 1
            partner = c.target
            role = "INITIATOR"
        else:
            participated_count += 1
            partner = c.initiator
            role = "TARGET"

        partner_name = partner.full_name if partner else "Unknown Participant"
        partner_username = partner.username if partner else "unknown"

        last_msg_at = c.concluded_at or c.updated_at or c.created_at
        if c.messages:
            last_msg_at = max(m.created_at for m in c.messages)

        status_str = c.status.value if hasattr(c.status, "value") else str(c.status)
        outcome_str = (
            c.terminal_outcome.value
            if c.terminal_outcome and hasattr(c.terminal_outcome, "value")
            else (str(c.terminal_outcome) if c.terminal_outcome else None)
        )

        conv_items.append(
            AdminConversationHistoryItem(
                conversation_id=c.id,
                partner_id=partner.id if partner else user_id,
                partner_name=partner_name,
                partner_username=partner_username,
                role=role,
                status=status_str,
                outcome=outcome_str,
                message_count=len(c.messages) if c.messages else 0,
                created_at=c.created_at,
                last_interaction_at=last_msg_at,
            )
        )

    conversations_block = AdminUserConversationsBlock(
        total_count=len(conversations),
        initiated_count=initiated_count,
        participated_count=participated_count,
        history=conv_items,
    )

    # 5. Query user activity events
    act_stmt = (
        select(UserActivityEvent)
        .where(UserActivityEvent.user_id == user_id)
        .order_by(desc(UserActivityEvent.created_at))
        .limit(30)
    )
    act_res = await db.execute(act_stmt)
    activity_events = act_res.scalars().all()

    tot_events_res = await db.execute(
        select(func.count(UserActivityEvent.id)).where(UserActivityEvent.user_id == user_id)
    )
    tot_events = tot_events_res.scalar() or len(activity_events)

    act_items = [
        AdminActivityItem(
            id=ev.id,
            event_type=ev.event_type,
            feature_name=ev.feature_name,
            target_resource_id=ev.target_resource_id,
            created_at=ev.created_at,
        )
        for ev in activity_events
    ]
    activity_block = AdminUserActivityBlock(
        total_events=tot_events,
        recent_events=act_items,
    )

    # 6. Query business profile with offerings and requirements
    bp_stmt = (
        select(BusinessProfile)
        .where(BusinessProfile.user_id == user_id)
        .options(
            selectinload(BusinessProfile.offerings),
            selectinload(BusinessProfile.requirements),
        )
    )
    bp_res = await db.execute(bp_stmt)
    bp = bp_res.scalar_one_or_none()

    business_profile_detail = None
    if bp:
        offering_items = [
            AdminOfferingDetail(
                id=o.id,
                business_profile_id=o.business_profile_id,
                custom_product_title=o.custom_product_title,
                product_code=o.product_code,
                grade_code=o.grade_code,
                service_code=o.service_code,
                specifications_text=o.specifications_text,
                declared_monthly_capacity=o.declared_monthly_capacity,
                declared_committed_volume=o.declared_committed_volume,
                capacity_unit=o.capacity_unit,
                minimum_order_quantity=o.minimum_order_quantity,
                lead_time_days=o.lead_time_days,
                geographic_coverage=o.geographic_coverage or [],
                offers_test_certificates=o.offers_test_certificates,
                vendor_certifications=o.vendor_certifications or [],
                open_to_distribution=o.open_to_distribution,
                target_distribution_regions=o.target_distribution_regions or [],
                distributor_tier_preferred=o.distributor_tier_preferred,
                is_public_indicative=o.is_public_indicative,
                indicative_price_min=o.indicative_price_min,
                indicative_price_max=o.indicative_price_max,
                price_currency=o.price_currency or "INR",
                pricing_basis=o.pricing_basis,
                offers_delivered_pricing=o.offers_delivered_pricing,
                quote_validity_days=o.quote_validity_days or 30,
                is_active=o.is_active,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in bp.offerings
        ]
        requirement_items = [
            AdminRequirementDetail(
                id=r.id,
                business_profile_id=r.business_profile_id,
                custom_requirement_title=r.custom_requirement_title,
                product_code=r.product_code,
                grade_code=r.grade_code,
                service_code=r.service_code,
                required_quantity=r.required_quantity,
                quantity_unit=r.quantity_unit,
                delivery_city=r.delivery_city,
                delivery_country=r.delivery_country,
                target_timeline_days=r.target_timeline_days,
                target_budget_indication=r.target_budget_indication,
                is_budget_public=r.is_budget_public,
                urgency=r.urgency,
                excluded_supplier_ids=r.excluded_supplier_ids or [],
                allow_substitutes=r.allow_substitutes,
                required_certifications=r.required_certifications or [],
                is_feedstock_procurement=r.is_feedstock_procurement,
                notes=r.notes,
                is_active=r.is_active,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in bp.requirements
        ]
        business_profile_detail = AdminBusinessProfileDetail(
            id=bp.id,
            user_id=bp.user_id,
            is_buyer=bp.is_buyer,
            is_supplier=bp.is_supplier,
            is_vendor=bp.is_vendor,
            is_distributor=bp.is_distributor,
            is_partner=bp.is_partner,
            allow_business_matching=bp.allow_business_matching,
            company_name=bp.company_name,
            industry=bp.industry,
            business_website=bp.business_website,
            hq_city=bp.hq_city,
            hq_country=bp.hq_country,
            company_bio=bp.company_bio,
            distributor_territories=bp.distributor_territories or [],
            warehousing_capacity_sqft=bp.warehousing_capacity_sqft,
            retail_dealer_count=bp.retail_dealer_count,
            partnership_types=bp.partnership_types or [],
            partnership_interests=bp.partnership_interests or [],
            offerings=offering_items,
            requirements=requirement_items,
            created_at=bp.created_at,
            updated_at=bp.updated_at,
        )

    return AdminUserDetailResponse(
        account=account_detail,
        profile=profile_detail,
        sessions=sessions_block,
        agenda=agenda_block,
        conversations=conversations_block,
        activity=activity_block,
        business_profile=business_profile_detail,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUpdateUserStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Update User Account Status",
    description="Activate or deactivate/suspend a conference attendee account. Deactivation immediately revokes all active sessions.",
)
async def update_admin_user_status(
    user_id: UUID,
    payload: AdminUpdateUserStatusRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUpdateUserStatusResponse:
    """Administratively activate or suspend an account with instant session revocation (Phase 4)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' was not found.",
        )

    # Prevent admin from deactivating own administrator account
    if user.id == current_admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own administrator account.",
        )

    old_status = user.is_active
    user.is_active = payload.is_active

    revoked_count = 0
    now = datetime.now(timezone.utc)

    if not payload.is_active:
        # Revoke all active bearer sessions for this attendee in core.user_sessions
        rev_stmt = (
            update(DbUserSession)
            .where(
                DbUserSession.user_id == user_id,
                DbUserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        res = await db.execute(rev_stmt)
        revoked_count = res.rowcount

    # Audit security event
    client_ip = get_client_ip(request)
    action = "ADMIN_USER_ACTIVATE" if payload.is_active else "ADMIN_USER_DEACTIVATE"
    await record_audit_event(
        session=db,
        user_id=current_admin.id,
        action_type=action,
        resource_type="core.users",
        resource_id=str(user_id),
        actor_username=current_admin.username,
        ip_address=client_ip,
    )
    await db.commit()

    detail_msg = f"User @{user.username} has been {'activated' if payload.is_active else 'suspended'}."
    if revoked_count > 0:
        detail_msg += f" {revoked_count} active session(s) revoked immediately."

    return AdminUpdateUserStatusResponse(
        status="success",
        user_id=user_id,
        is_active=payload.is_active,
        revoked_sessions_count=revoked_count,
        detail=detail_msg,
    )


# =============================================================================
# Organizer Directory & Verification Endpoints (Phase 4)
# =============================================================================

@router.get(
    "/organizers",
    response_model=AdminOrganizersListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Organizers Directory",
    description="Retrieve paginated directory of registered organizers with verification states and conference counts.",
)
async def list_admin_organizers(
    search: Optional[str] = Query(default=None, description="Search representative, organization, or email."),
    verification_status: Optional[str] = Query(default=None, description="Filter by verification status."),
    organizer_type: Optional[str] = Query(default=None, description="Filter by organizer type."),
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page."),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminOrganizersListResponse:
    """Retrieve organizers directory with server-side filters and summary stats."""
    # 1. Base query joining User to fetch account username
    query = (
        select(OrganizerProfile, User.username)
        .join(User, OrganizerProfile.user_id == User.id)
    )

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(OrganizerProfile.representative_name).like(term),
                func.lower(func.coalesce(OrganizerProfile.organization_name, "")).like(term),
                func.lower(OrganizerProfile.professional_email).like(term),
                func.lower(User.username).like(term),
            )
        )

    if verification_status and verification_status != "all":
        query = query.where(OrganizerProfile.verification_status == verification_status)

    if organizer_type and organizer_type != "all":
        query = query.where(OrganizerProfile.organizer_type == organizer_type)

    # Count total matching
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order by newest first
    offset = (page - 1) * limit
    paged_stmt = query.order_by(OrganizerProfile.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(paged_stmt)).all()

    # Pre-fetch conference counts for these organizers
    user_ids = [row[0].user_id for row in rows]
    conf_counts_map: Dict[UUID, int] = {}
    if user_ids:
        cc_stmt = (
            select(Conference.organizer_id, func.count(Conference.id))
            .where(Conference.organizer_id.in_(user_ids))
            .group_by(Conference.organizer_id)
        )
        cc_res = await db.execute(cc_stmt)
        for org_uid, cnt in cc_res.all():
            if org_uid:
                conf_counts_map[org_uid] = cnt

    items = [
        AdminOrganizerItem(
            id=prof.id,
            user_id=prof.user_id,
            username=uname,
            organizer_type=prof.organizer_type,
            representative_name=prof.representative_name,
            organization_name=prof.organization_name,
            designation=prof.designation,
            professional_email=prof.professional_email,
            contact_phone=prof.contact_phone,
            city=prof.city,
            state_province=prof.state_province,
            country=prof.country,
            focus_areas=prof.focus_areas or [],
            verification_status=prof.verification_status,
            conferences_count=conf_counts_map.get(prof.user_id, 0),
            created_at=prof.created_at,
            updated_at=prof.updated_at,
        )
        for prof, uname in rows
    ]

    # Global stats for organizers header
    tot_orgs_res = await db.execute(select(func.count(OrganizerProfile.id)))
    total_orgs = tot_orgs_res.scalar() or 0

    verif_res = await db.execute(
        select(func.count(OrganizerProfile.id)).where(
            OrganizerProfile.verification_status == OrganizerVerificationStatus.VERIFIED.value
        )
    )
    verified_cnt = verif_res.scalar() or 0

    pend_res = await db.execute(
        select(func.count(OrganizerProfile.id)).where(
            OrganizerProfile.verification_status == OrganizerVerificationStatus.PENDING_REVIEW.value
        )
    )
    pend_cnt = pend_res.scalar() or 0

    tot_conf_res = await db.execute(select(func.count(Conference.id)))
    tot_confs = tot_conf_res.scalar() or 0

    total_pages = max(1, (total + limit - 1) // limit)

    return AdminOrganizersListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        stats=AdminOrganizersListStats(
            total_organizers=total_orgs,
            verified_count=verified_cnt,
            pending_review_count=pend_cnt,
            total_conferences_managed=tot_confs,
        ),
    )


@router.patch(
    "/organizers/{organizer_id}/verification",
    response_model=AdminUpdateOrganizerVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Organizer Verification Status",
    description="Verify or suspend an organizer profile with administrative audit logging.",
)
async def update_organizer_verification(
    organizer_id: UUID,
    payload: AdminUpdateOrganizerVerificationRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminUpdateOrganizerVerificationResponse:
    """Update verification status of an organizer profile."""
    profile = await db.get(OrganizerProfile, organizer_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organizer profile '{organizer_id}' was not found.",
        )

    valid_statuses = [s.value for s in OrganizerVerificationStatus]
    if payload.verification_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification status. Must be one of: {valid_statuses}",
        )

    old_status = profile.verification_status
    profile.verification_status = payload.verification_status
    profile.updated_at = datetime.now(timezone.utc)

    client_ip = get_client_ip(request)
    await record_audit_event(
        session=db,
        user_id=current_admin.id,
        action_type="ADMIN_ORGANIZER_VERIFICATION_UPDATE",
        resource_type="core.organizer_profiles",
        resource_id=str(organizer_id),
        actor_username=current_admin.username,
        ip_address=client_ip,
        payload={"from_status": old_status, "to_status": profile.verification_status, "reason": payload.reason},
    )
    await db.commit()

    # Phase 6: Real-time broadcast for organizer verification updates
    from app.core.events import event_broker
    await event_broker.publish(
        "organizer:verified",
        {
            "organizer_id": str(organizer_id),
            "user_id": str(profile.user_id),
            "verification_status": profile.verification_status,
        },
    )

    return AdminUpdateOrganizerVerificationResponse(
        status="success",
        organizer_id=organizer_id,
        verification_status=profile.verification_status,
        detail=f"Organizer verification status updated to '{profile.verification_status}'.",
    )


# =============================================================================
# Conference Review Queue & Decision Endpoints (Phase 4)
# =============================================================================

@router.get(
    "/conferences",
    response_model=AdminConferenceQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Conferences Review Queue",
    description="List all conferences submitted for review or in any lifecycle status with full organizer metadata.",
)
async def list_admin_conferences(
    search: Optional[str] = Query(default=None, description="Search conference title, venue, category, or organizer."),
    status_filter: Optional[str] = Query(default=None, description="Filter by conference status (default shows all or in-review)."),
    category: Optional[str] = Query(default=None, description="Filter by conference category."),
    format_filter: Optional[str] = Query(default=None, description="Filter by format: IN_PERSON, HYBRID, ONLINE."),
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page."),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminConferenceQueueResponse:
    """Retrieve conference submissions across approval lifecycle."""
    query = (
        select(Conference, OrganizerProfile, User.username)
        .outerjoin(OrganizerProfile, Conference.organizer_id == OrganizerProfile.user_id)
        .outerjoin(User, Conference.organizer_id == User.id)
    )

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Conference.title).like(term),
                func.lower(Conference.venue_name).like(term),
                func.lower(func.coalesce(Conference.category, "")).like(term),
                func.lower(func.coalesce(OrganizerProfile.organization_name, "")).like(term),
                func.lower(func.coalesce(OrganizerProfile.representative_name, "")).like(term),
            )
        )

    if status_filter and status_filter != "all":
        query = query.where(Conference.status == status_filter)

    if category and category != "all":
        query = query.where(Conference.category == category)

    if format_filter and format_filter != "all":
        query = query.where(Conference.format == format_filter)

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    # Sort priority: IN_REVIEW first, then updated_at desc
    paged_stmt = (
        query.order_by(
            (Conference.status == ConferenceStatus.IN_REVIEW.value).desc(),
            Conference.updated_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(paged_stmt)).all()

    # Pre-fetch session counts
    conf_ids = [row[0].id for row in rows]
    session_counts_map: Dict[UUID, int] = {}
    if conf_ids:
        sc_stmt = (
            select(DbConferenceSession.conference_id, func.count(DbConferenceSession.id))
            .where(DbConferenceSession.conference_id.in_(conf_ids))
            .group_by(DbConferenceSession.conference_id)
        )
        sc_res = await db.execute(sc_stmt)
        for cid, cnt in sc_res.all():
            session_counts_map[cid] = cnt

    items: List[AdminConferenceQueueItem] = []
    for conf, org_prof, uname in rows:
        org_summary = None
        if org_prof and uname:
            org_summary = AdminConferenceOrganizerSummary(
                id=org_prof.id,
                user_id=org_prof.user_id,
                username=uname,
                representative_name=org_prof.representative_name,
                organization_name=org_prof.organization_name,
                designation=org_prof.designation,
                professional_email=org_prof.professional_email,
                contact_phone=org_prof.contact_phone,
                city=org_prof.city,
                country=org_prof.country,
                verification_status=org_prof.verification_status,
            )

        items.append(
            AdminConferenceQueueItem(
                id=conf.id,
                organizer_id=conf.organizer_id,
                organizer=org_summary,
                title=conf.title,
                summary=conf.summary,
                category=conf.category,
                format=conf.format,
                venue_name=conf.venue_name,
                timezone=conf.timezone,
                start_date=conf.start_date,
                end_date=conf.end_date,
                city=conf.city,
                country=conf.country,
                capacity=conf.capacity,
                status=conf.status,
                sessions_count=session_counts_map.get(conf.id, 0),
                published_at=conf.published_at,
                created_at=conf.created_at,
                updated_at=conf.updated_at,
            )
        )

    # Queue telemetry stats
    in_rev_res = await db.execute(
        select(func.count(Conference.id)).where(Conference.status == ConferenceStatus.IN_REVIEW.value)
    )
    total_in_rev = in_rev_res.scalar() or 0

    pub_res = await db.execute(
        select(func.count(Conference.id)).where(Conference.status == ConferenceStatus.PUBLISHED.value)
    )
    total_pub = pub_res.scalar() or 0

    draft_res = await db.execute(
        select(func.count(Conference.id)).where(Conference.status == ConferenceStatus.DRAFT.value)
    )
    total_draft = draft_res.scalar() or 0

    chg_res = await db.execute(
        select(func.count(Conference.id)).where(Conference.status == ConferenceStatus.CHANGES_REQUESTED.value)
    )
    total_chg = chg_res.scalar() or 0

    rej_res = await db.execute(
        select(func.count(Conference.id)).where(Conference.status == ConferenceStatus.REJECTED.value)
    )
    total_rej = rej_res.scalar() or 0

    total_pages = max(1, (total + limit - 1) // limit)

    return AdminConferenceQueueResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        stats=AdminConferenceQueueStats(
            total_in_review=total_in_rev,
            total_published=total_pub,
            total_draft=total_draft,
            total_changes_requested=total_chg,
            total_rejected=total_rej,
        ),
    )


@router.get(
    "/conferences/{conference_id}",
    response_model=AdminConferenceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Conference Detail View",
    description="Retrieve comprehensive conference record, full agenda sessions schedule, organizer footprint, and audit review history.",
)
async def get_admin_conference_detail(
    conference_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminConferenceDetailResponse:
    """Detailed inspection of a conference submission for admin review."""
    conf = await db.get(Conference, conference_id)
    if not conf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conference '{conference_id}' was not found.",
        )

    # 1. Organizer summary
    org_summary = None
    if conf.organizer_id:
        prof_stmt = select(OrganizerProfile, User.username).join(User, OrganizerProfile.user_id == User.id).where(OrganizerProfile.user_id == conf.organizer_id)
        prof_res = (await db.execute(prof_stmt)).first()
        if prof_res:
            prof, uname = prof_res
            org_summary = AdminConferenceOrganizerSummary(
                id=prof.id,
                user_id=prof.user_id,
                username=uname,
                representative_name=prof.representative_name,
                organization_name=prof.organization_name,
                organizer_type=prof.organizer_type,
                designation=prof.designation,
                professional_email=prof.professional_email,
                contact_phone=prof.contact_phone,
                website_url=prof.website_url,
                address_line1=prof.address_line1,
                city=prof.city,
                state_province=prof.state_province,
                postal_code=prof.postal_code,
                country=prof.country,
                bio=prof.bio,
                experience_years=prof.experience_years,
                focus_areas=prof.focus_areas or [],
                verification_status=prof.verification_status,
            )

    # 2. Sessions schedule
    sess_stmt = (
        select(DbConferenceSession)
        .where(DbConferenceSession.conference_id == conf.id)
        .order_by(DbConferenceSession.start_time.asc())
    )
    sess_res = await db.execute(sess_stmt)
    sessions = [
        AdminConferenceSessionItem(
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
        )
        for s in sess_res.scalars().all()
    ]

    # 3. Review audit logs
    log_stmt = (
        select(ConferenceReviewLog, User.username)
        .outerjoin(User, ConferenceReviewLog.reviewer_id == User.id)
        .where(ConferenceReviewLog.conference_id == conf.id)
        .order_by(ConferenceReviewLog.created_at.desc())
    )
    log_res = await db.execute(log_stmt)
    review_logs = [
        AdminConferenceReviewLogItem(
            id=l.id,
            reviewer_id=l.reviewer_id,
            reviewer_username=uname,
            from_status=l.from_status,
            to_status=l.to_status,
            notes=l.notes,
            created_at=l.created_at,
        )
        for l, uname in log_res.all()
    ]

    return AdminConferenceDetailResponse(
        id=conf.id,
        organizer_id=conf.organizer_id,
        organizer=org_summary,
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
        sessions=sessions,
        review_logs=review_logs,
    )


@router.post(
    "/conferences/{conference_id}/decision",
    response_model=AdminConferenceDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Conference Review Decision",
    description="Admin decision workflow: APPROVE (sets PUBLISHED and published_at), REQUEST_CHANGES (unblocks organizer with notes), or REJECT.",
)
async def submit_conference_decision(
    conference_id: UUID,
    payload: AdminConferenceDecisionRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminConferenceDecisionResponse:
    """Execute administrative decision on a submitted conference."""
    conf = await db.get(Conference, conference_id)
    if not conf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conference '{conference_id}' was not found.",
        )

    # Decisions require feedback for REQUEST_CHANGES and REJECT
    if payload.decision in (ConferenceDecisionAction.REQUEST_CHANGES, ConferenceDecisionAction.REJECT):
        if not payload.feedback or not payload.feedback.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback notes are required when requesting changes or rejecting a conference.",
            )

    from_status = conf.status
    now = datetime.now(timezone.utc)

    if payload.decision == ConferenceDecisionAction.APPROVE:
        to_status = ConferenceStatus.PUBLISHED.value
        conf.status = to_status
        conf.is_active = True
        conf.published_at = now
        conf.reviewed_by = current_admin.id
        conf.reviewed_at = now
        conf.review_feedback = payload.feedback.strip() if payload.feedback else None
        detail_msg = f"Conference '{conf.title}' has been APPROVED and PUBLISHED to the public agenda."

    elif payload.decision == ConferenceDecisionAction.REQUEST_CHANGES:
        to_status = ConferenceStatus.CHANGES_REQUESTED.value
        conf.status = to_status
        conf.reviewed_by = current_admin.id
        conf.reviewed_at = now
        conf.review_feedback = payload.feedback.strip() if payload.feedback else None
        detail_msg = f"Conference '{conf.title}' marked as CHANGES_REQUESTED. Organizer notified with revision feedback."

    elif payload.decision == ConferenceDecisionAction.REJECT:
        to_status = ConferenceStatus.REJECTED.value
        conf.status = to_status
        conf.reviewed_by = current_admin.id
        conf.reviewed_at = now
        conf.review_feedback = payload.feedback.strip() if payload.feedback else None
        detail_msg = f"Conference '{conf.title}' has been REJECTED."

    conf.updated_at = now

    # Write immutable review audit log
    log = ConferenceReviewLog(
        conference_id=conf.id,
        reviewer_id=current_admin.id,
        from_status=from_status,
        to_status=to_status,
        notes=payload.feedback.strip() if payload.feedback else f"Administrative decision: {payload.decision.value}",
    )
    db.add(log)

    client_ip = get_client_ip(request)
    await record_audit_event(
        session=db,
        user_id=current_admin.id,
        action_type=f"ADMIN_CONFERENCE_DECISION_{payload.decision.value}",
        resource_type="agenda.conferences",
        resource_id=str(conf.id),
        actor_username=current_admin.username,
        ip_address=client_ip,
        payload={
            "from_status": from_status,
            "to_status": to_status,
            "feedback": payload.feedback,
        },
    )
    await db.commit()

    # Phase 6: Real-time broadcast for conference decision and publication
    from app.core.events import event_broker
    await event_broker.publish(
        "conference:decision",
        {
            "conference_id": str(conf.id),
            "title": conf.title,
            "decision": payload.decision.value,
            "status": to_status,
            "feedback": payload.feedback,
        },
    )
    if to_status == ConferenceStatus.PUBLISHED.value:
        await event_broker.publish(
            "conference:approved",
            {
                "conference_id": str(conf.id),
                "title": conf.title,
                "status": to_status,
                "published_at": now.isoformat(),
            },
        )
    elif to_status == ConferenceStatus.CHANGES_REQUESTED.value:
        await event_broker.publish(
            "conference:changes_requested",
            {
                "conference_id": str(conf.id),
                "title": conf.title,
                "status": to_status,
                "feedback": payload.feedback,
            },
        )
    elif to_status == ConferenceStatus.REJECTED.value:
        await event_broker.publish(
            "conference:rejected",
            {
                "conference_id": str(conf.id),
                "title": conf.title,
                "status": to_status,
                "feedback": payload.feedback,
            },
        )

    return AdminConferenceDecisionResponse(
        status="success",
        conference_id=conf.id,
        new_status=to_status,
        detail=detail_msg,
    )


# --- Subphase 8: Administrative Oversight & Governance (Proposals Queue) ---

@router.get(
    "/proposals",
    response_model=AdminProposalListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Commercial Proposals Directory",
    description="Retrieve paginated platform commercial proposals with status counts, type filtering, and search.",
)
async def list_admin_proposals(
    status_filter: Optional[ProposalStatus] = Query(default=None, alias="status", description="Filter by proposal lifecycle status"),
    proposal_type: Optional[ProposalType] = Query(default=None, description="Filter by contract category"),
    search: Optional[str] = Query(default=None, description="Search counterparty names, company names, or product scopes"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminProposalListResponse:
    """Retrieve platform proposals directory for administrative governance."""
    return await ProposalService.list_admin_proposals(
        db=db,
        status=status_filter,
        proposal_type=proposal_type,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Proposal Forensic Inspection",
    description="Retrieve full forensic inspection sheet for a proposal including revision ledger, approval trail with IP addresses, and contact disclosure receipts.",
)
async def get_admin_proposal_detail(
    proposal_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Forensic inspection of a single proposal for administrative governance."""
    return await ProposalService.get_proposal(
        db=db,
        proposal_id=proposal_id,
        current_user=current_admin,
        is_admin=True,
    )


@router.get(
    "/users/{user_id}/proposals",
    response_model=AdminProposalListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin User Proposals Audit List",
    description="Retrieve all commercial proposals where the specified user is either the proposer or recipient.",
)
async def list_admin_user_proposals(
    user_id: UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminProposalListResponse:
    """Retrieve delegate-specific proposal portfolio for administrator audit."""
    return await ProposalService.list_admin_proposals(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


# --- Administrative Oversight & Governance (Commercial Quotes & RFQs) ---

@router.get(
    "/quotes",
    response_model=AdminQuoteListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Commercial Quotes Directory",
    description="Retrieve paginated platform commercial quotations with metrics, delivery status filtering, and multi-field search.",
)
async def list_admin_quotes(
    status_filter: Optional[EmailDeliveryStatus] = Query(default=None, alias="status", description="Filter by email delivery status (SENT, FAILED)"),
    search: Optional[str] = Query(default=None, description="Search quote reference, product name, email, counterparty names, or company names"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminQuoteListResponse:
    """Retrieve platform commercial quotes directory for administrative governance."""
    return await QuoteService.list_admin_quotes(
        db=db,
        status=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/quotes/{quote_id}",
    response_model=AdminQuoteDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Quote Forensic Inspection",
    description="Retrieve full forensic inspection sheet for a quote dispatch including exact HTML email body delivered.",
)
async def get_admin_quote_detail(
    quote_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminQuoteDetailResponse:
    """Forensic inspection of a single quote transmission for administrative governance."""
    return await QuoteService.get_admin_quote_detail(
        db=db,
        quote_id=quote_id,
    )


@router.get(
    "/users/{user_id}/quotes",
    response_model=AdminQuoteListResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin User Quotes Audit List",
    description="Retrieve all commercial quotations where the specified user is either the vendor or customer.",
)
async def list_admin_user_quotes(
    user_id: UUID,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminQuoteListResponse:
    """Retrieve delegate-specific quote portfolio for administrator audit."""
    return await QuoteService.list_admin_quotes(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Admin Sponsored Ad Management & Brochure Monetization Engine (Phase 4)
# ============================================================================

@router.get(
    "/brochures/ads",
    response_model=AdminBrochureAdsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Sponsored Ad Campaigns",
    description="Retrieve all sponsor ads, placement types, telemetry metrics, and targeted brochures.",
)
async def list_admin_brochure_ads(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminBrochureAdsListResponse:
    """List administrative sponsored ad campaigns and analytics."""
    return await BrochureService.list_admin_ads(db)


@router.post(
    "/brochures/ads",
    response_model=AdminBrochureAdDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create Sponsored Ad Campaign",
    description="Create a new sponsored ad campaign with creative assets, placement slot, and target brochures.",
)
async def create_admin_brochure_ad(
    payload: BrochureAdCreate,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminBrochureAdDetail:
    """Create a sponsored ad campaign."""
    ad = await BrochureService.create_admin_ad(db, payload)
    res = await BrochureService.list_admin_ads(db)
    for item in res.items:
        if item.id == ad.id:
            return item
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ad creation failed")


@router.put(
    "/brochures/ads/{ad_id}",
    response_model=AdminBrochureAdDetail,
    status_code=status.HTTP_200_OK,
    summary="Update Sponsored Ad Campaign",
    description="Update sponsor ad creative, placement, URLs, or target brochures.",
)
async def update_admin_brochure_ad(
    ad_id: UUID,
    payload: BrochureAdUpdate,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminBrochureAdDetail:
    """Update existing sponsor ad campaign."""
    updated = await BrochureService.update_admin_ad(db, ad_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    res = await BrochureService.list_admin_ads(db)
    for item in res.items:
        if item.id == ad_id:
            return item
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch updated ad")


@router.post(
    "/brochures/ads/{ad_id}/assign",
    status_code=status.HTTP_200_OK,
    summary="Assign Ad Targeting Matrix",
    description="Assign ad to specific company brochures or configure as global conference-wide fallback.",
)
async def assign_admin_brochure_ad_targets(
    ad_id: UUID,
    payload: AdminBrochureAdAssignRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Update targeting matrix for an ad campaign."""
    success = await BrochureService.assign_ad_targets(
        session=db,
        ad_id=ad_id,
        is_global=payload.is_global,
        brochure_ids=payload.brochure_ids,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    return {"success": True, "ad_id": str(ad_id), "is_global": payload.is_global, "targets_count": len(payload.brochure_ids)}


@router.delete(
    "/brochures/ads/{ad_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Sponsored Ad Campaign",
)
async def delete_admin_brochure_ad(
    ad_id: UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Permanently delete an ad campaign."""
    deleted = await BrochureService.delete_admin_ad(db, ad_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    return {"success": True, "deleted_ad_id": str(ad_id)}


@router.post(
    "/brochures/ads/upload-creative",
    status_code=status.HTTP_201_CREATED,
    summary="Upload Sponsor Creative Asset",
)
async def upload_admin_ad_creative(
    file: UploadFile = File(...),
    current_admin: User = Depends(require_admin),
) -> dict:
    """Upload sponsor creative banner image (JPG, PNG, WebP) directly to media storage."""
    allowed = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type and file.content_type.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{file.content_type}'. Allowed: JPG, PNG, WebP.",
        )
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file upload.")
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset exceeds 25MB limit.")

    creative_url = BrochureService.save_ad_creative(file_bytes, file.filename or "ad_creative.jpg")
    return {"creative_image_url": creative_url}


@router.get(
    "/brochures/companies",
    response_model=List[AdminCompanyBrochureOption],
    status_code=status.HTTP_200_OK,
    summary="List Company Brochures for Ad Targeting",
)
async def list_admin_company_brochures(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> List[AdminCompanyBrochureOption]:
    """List available company brochures for ad targeting checklist."""
    return await BrochureService.list_company_brochures_for_admin(db)


@router.get(
    "/brochures/analytics",
    response_model=AdminBrochureAnalyticsOverview,
    status_code=status.HTTP_200_OK,
    summary="Portfolio & Per-Magazine Brochure Page Read Analytics",
)
async def get_admin_brochures_analytics(
    period: str = "7d",
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> AdminBrochureAnalyticsOverview:
    """Return combined and magazine-by-magazine read counts, time series, and page breakdowns."""
    return await BrochureService.get_admin_brochure_analytics(db, period=period)


@router.put(
    "/brochures/viewer-settings",
    response_model=FlipbookViewerSettings,
    status_code=status.HTTP_200_OK,
    summary="Update Summit Flipbook Sound & Animation Defaults",
)
async def update_admin_viewer_settings(
    payload: FlipbookViewerSettingsUpdate,
    current_admin: User = Depends(require_admin),
) -> FlipbookViewerSettings:
    """Persist global summit flipbook acoustics and page-turn animation defaults."""
    try:
        updated = BrochureService.update_viewer_settings(
            sound_preset=payload.sound_preset,
            animation_preset=payload.animation_preset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return FlipbookViewerSettings(**updated)





