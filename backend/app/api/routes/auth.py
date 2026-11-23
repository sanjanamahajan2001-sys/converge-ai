"""Authentication & Registration API endpoints."""
import ipaddress
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.config import get_settings
from app.core.dependencies import extract_session_token, get_current_session, get_current_user
from app.core.rate_limit import (
    check_login_rate_limit,
    record_failed_login,
    reset_login_rate_limit,
)
from app.core.security import hash_password, verify_dummy_password, verify_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    UserSession,
    clear_session_cookie,
    create_session,
    revoke_session,
    rotate_session,
    set_session_cookie,
    verify_csrf_header,
)
from app.db.models.organizer import OrganizerProfile
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import (
    ErrorResponse,
    SessionRotateResponse,
    UserIdentityResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserLogoutResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_ip(request: Request) -> str:
    """Safely extract valid IPv4 or IPv6 client IP.

    Trusts X-Forwarded-For ONLY when request comes from an explicitly configured trusted proxy (GAP-05).
    """
    settings = getattr(request.app.state, "settings", None) or get_settings()
    trusted_proxies = set(settings.TRUSTED_PROXIES)
    peer_ip = request.client.host if request.client else None

    # Direct peer must be in trusted proxies or running under test client
    is_trusted_peer = (
        peer_ip in trusted_proxies
        or peer_ip == "testclient"
        or (settings.is_test() and peer_ip is None)
    )

    raw_ip = None
    if is_trusted_peer and "x-forwarded-for" in request.headers:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if ips:
            raw_ip = ips[0]
    elif peer_ip and peer_ip != "testclient":
        raw_ip = peer_ip

    if raw_ip:
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip
        except ValueError:
            pass

    return peer_ip if peer_ip and peer_ip != "testclient" else "127.0.0.1"


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Participant Identity",
    description=(
        "Registers a new conference participant identity with validated credentials. "
        "Enforces case-insensitive username and email uniqueness, password complexity, "
        "and security audit logging with strict PII scrubbing (GAP-10)."
    ),
    responses={
        status.HTTP_201_CREATED: {
            "description": "User successfully registered.",
            "model": UserRegisterResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "Account conflict (enumeration-safe).",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error in request payload.",
        },
    },
)
async def register_user(
    payload: UserRegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> UserRegisterResponse:
    """Handle new participant registration."""
    client_ip = get_client_ip(request)

    # 1. Check for duplicate username or email (case-insensitive)
    stmt = select(User).where(
        or_(
            func.lower(User.username) == payload.username.lower(),
            func.lower(User.email) == payload.email.lower(),
        )
    )
    result = await session.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        # Record security audit event without logging plain password or specific conflict
        await record_audit_event(
            session=session,
            action_type="REGISTRATION_FAILED_CONFLICT",
            resource_type="USER",
            actor_username=payload.username,
            ip_address=client_ip,
            payload={
                "status": "CONFLICT",
                "reason": "DUPLICATE_IDENTITY_DETECTED",
            },
        )
        await session.commit()

        # Enumeration-safe conflict response
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with these identity details already exists.",
        )

    # 2. Hash password with bcrypt work factor 12
    password_hash = hash_password(payload.password)

    # 3. Instantiate and persist new User entity
    new_user = User(
        username=payload.username,
        email=payload.email,
        password_hash=password_hash,
        full_name=payload.full_name,
        company_name=payload.company_name,
        job_title=payload.job_title,
        phone_number=payload.phone_number,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()  # Populates new_user.id

    # 4. Record successful registration audit event (GAP-10 scrubbed)
    await record_audit_event(
        session=session,
        action_type="USER_REGISTERED",
        resource_type="USER",
        resource_id=str(new_user.id),
        actor_username=new_user.username,
        user_id=new_user.id,
        ip_address=client_ip,
        payload={
            "status": "SUCCESS",
            "action": "REGISTRATION",
            "resource_id": str(new_user.id),
        },
    )
    await session.commit()
    await session.refresh(new_user)

    return UserRegisterResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Participant Credentials",
    description=(
        "Verifies participant credentials using either username or email. "
        "Enforces timing-attack resistance via dummy work for nonexistent users, "
        "generic 401 error semantics without enumeration leaks, failed-attempt "
        "throttling (5 attempts per 15 minutes per IP), and security audit logging. "
        "Returns a verified contract without session tokens (session lifecycle belongs to P2-WS3)."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Credentials verified successfully.",
            "model": UserLoginResponse,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid credentials or inactive account.",
            "model": ErrorResponse,
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "description": "Too many failed sign-in attempts.",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Malformed request payload.",
        },
    },
)
async def login_user(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> UserLoginResponse:
    """Verify participant credentials and issue a secure server-side authenticated session."""
    client_ip = get_client_ip(request)

    # 1. Throttling preflight check
    try:
        await check_login_rate_limit(session, client_ip)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            await record_audit_event(
                session=session,
                action_type="LOGIN_THROTTLED",
                resource_type="AUTH",
                actor_username=payload.identifier[:50],
                ip_address=client_ip,
                payload={
                    "status": "THROTTLED",
                    "reason": "LOCKED_OUT_PREFLIGHT",
                },
            )
            await session.commit()
        raise exc

    # 2. Case-insensitive lookup by username or email
    clean_identifier = payload.identifier.strip()
    stmt = select(User).where(
        or_(
            func.lower(User.username) == clean_identifier.lower(),
            func.lower(User.email) == clean_identifier.lower(),
        )
    )
    result = await session.execute(stmt)
    user = result.scalars().first()

    # 3. Nonexistent user branch (with constant-time dummy verification)
    if not user:
        verify_dummy_password(payload.password)
        is_locked = await record_failed_login(session, client_ip)
        if is_locked:
            await record_audit_event(
                session=session,
                action_type="LOGIN_THROTTLED",
                resource_type="AUTH",
                actor_username=clean_identifier[:50],
                ip_address=client_ip,
                payload={"status": "THROTTLED", "reason": "MAX_ATTEMPTS_EXCEEDED"},
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Please try again later.",
                headers={"Retry-After": "900"},
            )

        await record_audit_event(
            session=session,
            action_type="LOGIN_FAILED",
            resource_type="AUTH",
            actor_username=clean_identifier[:50],
            ip_address=client_ip,
            payload={"status": "FAILED", "reason": "INVALID_CREDENTIALS"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # 4. Existing user: verify password
    password_valid = verify_password(payload.password, user.password_hash)

    if not password_valid:
        is_locked = await record_failed_login(session, client_ip)
        if is_locked:
            await record_audit_event(
                session=session,
                action_type="LOGIN_THROTTLED",
                resource_type="AUTH",
                actor_username=user.username,
                user_id=user.id,
                ip_address=client_ip,
                payload={"status": "THROTTLED", "reason": "MAX_ATTEMPTS_EXCEEDED"},
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Please try again later.",
                headers={"Retry-After": "900"},
            )

        await record_audit_event(
            session=session,
            action_type="LOGIN_FAILED",
            resource_type="AUTH",
            actor_username=user.username,
            user_id=user.id,
            ip_address=client_ip,
            payload={"status": "FAILED", "reason": "INVALID_CREDENTIALS"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # 5. Check account active status
    if not user.is_active:
        is_locked = await record_failed_login(session, client_ip)
        if is_locked:
            await record_audit_event(
                session=session,
                action_type="LOGIN_THROTTLED",
                resource_type="AUTH",
                actor_username=user.username,
                user_id=user.id,
                ip_address=client_ip,
                payload={"status": "THROTTLED", "reason": "MAX_ATTEMPTS_EXCEEDED"},
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Please try again later.",
                headers={"Retry-After": "900"},
            )

        await record_audit_event(
            session=session,
            action_type="LOGIN_FAILED",
            resource_type="AUTH",
            actor_username=user.username,
            user_id=user.id,
            ip_address=client_ip,
            payload={"status": "FAILED", "reason": "ACCOUNT_INACTIVE"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # 6. Authentication verified: reset throttling, issue server-side session, set cookie
    await reset_login_rate_limit(session, client_ip)

    # Determine secure cookie flag
    settings = getattr(request.app.state, "settings", None) or get_settings()
    is_secure = settings.is_production() or request.url.scheme == "https"

    # Create server-side session (invalidates any existing sessions for this user)
    db_session, raw_token = await create_session(
        session=session,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    # Attach HttpOnly session cookie
    set_session_cookie(response=response, raw_token=raw_token, secure=is_secure)

    # Record login success & session creation audit events (GAP-10 scrubbed)
    await record_audit_event(
        session=session,
        action_type="LOGIN_SUCCESS",
        resource_type="USER",
        resource_id=str(user.id),
        actor_username=user.username,
        user_id=user.id,
        ip_address=client_ip,
        payload={"status": "SUCCESS", "action": "CREDENTIALS_VERIFIED"},
    )
    await record_audit_event(
        session=session,
        action_type="SESSION_ISSUED",
        resource_type="SESSION",
        resource_id=str(db_session.id),
        actor_username=user.username,
        user_id=user.id,
        ip_address=client_ip,
        payload={"status": "ACTIVE", "expires_at": db_session.expires_at.isoformat()},
    )
    await session.commit()

    return UserLoginResponse(
        status="authenticated",
        user_id=user.id,
        username=user.username,
        email=user.email,
        expires_at=db_session.expires_at,
    )


@router.post(
    "/logout",
    response_model=UserLogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Active Session (Logout)",
    description=(
        "Revokes the active session server-side and clears the browser session cookie. "
        "Enforces anti-CSRF custom header validation for cookie-authenticated requests (GAP-05)."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Session revoked and cleared successfully.",
            "model": UserLogoutResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "CSRF validation failed.",
            "model": ErrorResponse,
        },
    },
)
async def logout_user(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> UserLogoutResponse:
    """Revoke active session and clear cookie."""
    client_ip = get_client_ip(request)
    raw_token = extract_session_token(request)

    # Enforce CSRF header check on cookie-authenticated logout
    if request.cookies.get(SESSION_COOKIE_NAME):
        verify_csrf_header(request)

    revoked_session = None
    if raw_token:
        revoked_session = await revoke_session(session=session, raw_token=raw_token)

    settings = getattr(request.app.state, "settings", None) or get_settings()
    is_secure = settings.is_production() or request.url.scheme == "https"
    clear_session_cookie(response=response, secure=is_secure)

    if revoked_session:
        await record_audit_event(
            session=session,
            action_type="SESSION_REVOKED",
            resource_type="SESSION",
            resource_id=str(revoked_session.id),
            actor_username="authenticated",
            user_id=revoked_session.user_id,
            ip_address=client_ip,
            payload={"status": "REVOKED", "action": "LOGOUT"},
        )
        await session.commit()

    return UserLogoutResponse(
        status="logged_out",
        detail="Session revoked successfully.",
    )


@router.get(
    "/me",
    response_model=UserIdentityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated Participant",
    description="Validates active server-side session and returns participant public identity.",
    responses={
        status.HTTP_200_OK: {
            "description": "Active session validated.",
            "model": UserIdentityResponse,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing, expired, or revoked session.",
            "model": ErrorResponse,
        },
    },
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserIdentityResponse:
    """Return validated current user identity with organizer status."""
    stmt = select(OrganizerProfile.id).where(OrganizerProfile.user_id == current_user.id)
    is_org = (await db.execute(stmt)).scalar_one_or_none() is not None

    return UserIdentityResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        company_name=current_user.company_name,
        job_title=current_user.job_title,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        is_organizer=is_org,
    )


@router.post(
    "/rotate",
    response_model=SessionRotateResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate Session Credential",
    description="Invalidates current session token and issues a fresh session credential (GAP-05).",
    responses={
        status.HTTP_200_OK: {
            "description": "Session successfully rotated.",
            "model": SessionRotateResponse,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Session invalid or expired.",
            "model": ErrorResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "CSRF validation failed.",
            "model": ErrorResponse,
        },
    },
)
async def rotate_current_session(
    request: Request,
    response: Response,
    current_session: UserSession = Depends(get_current_session),
    session: AsyncSession = Depends(get_db_session),
) -> SessionRotateResponse:
    """Rotate session token and update cookie."""
    client_ip = get_client_ip(request)
    raw_token = extract_session_token(request)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    new_session, new_raw_token = await rotate_session(
        session=session,
        raw_token=raw_token,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    settings = getattr(request.app.state, "settings", None) or get_settings()
    is_secure = settings.is_production() or request.url.scheme == "https"
    set_session_cookie(response=response, raw_token=new_raw_token, secure=is_secure)

    await record_audit_event(
        session=session,
        action_type="SESSION_ROTATED",
        resource_type="SESSION",
        resource_id=str(new_session.id),
        actor_username=current_session.user.username,
        user_id=current_session.user.id,
        ip_address=client_ip,
        payload={"status": "ROTATED", "expires_at": new_session.expires_at.isoformat()},
    )
    await session.commit()

    return SessionRotateResponse(
        status="session_rotated",
        expires_at=new_session.expires_at,
    )
