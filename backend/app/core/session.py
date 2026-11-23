"""Server-side session management, verification, rotation, and revocation (GAP-05)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.session import UserSession
from app.db.models.user import User

SESSION_COOKIE_NAME = "converge_session"
SESSION_LIFETIME_HOURS = 24
SESSION_IDLE_TIMEOUT_MINUTES = 60
CSRF_HEADER_NAME = "x-requested-with"
CSRF_EXPECTED_VALUE = "xmlhttprequest"


def generate_session_token() -> str:
    """Generate a high-entropy cryptographically secure session token (256 bits)."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Calculate SHA-256 one-way cryptographic digest of bearer token.

    Only the digest is stored in the database to prevent credential compromise
    in the event of database access.
    """
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


async def create_session(
    session: AsyncSession,
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[UserSession, str]:
    """Create a new server-side session, revoking any prior active sessions for this user (GAP-05).

    Returns a tuple of (UserSession record, raw_bearer_token).
    """
    now = datetime.now(timezone.utc)

    # 1. Session fixation defense: invalidate existing active sessions for this user
    stmt_revoke = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > now,
    )
    existing_sessions = (await session.execute(stmt_revoke)).scalars().all()
    for s in existing_sessions:
        s.revoked_at = now

    # 2. Generate bearer secret and compute one-way storage hash
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    expires_at = now + timedelta(hours=SESSION_LIFETIME_HOURS)

    # 3. Persist session entity
    db_session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        created_at=now,
        last_accessed_at=now,
        expires_at=expires_at,
        revoked_at=None,
        ip_address=ip_address,
        user_agent=user_agent[:255] if user_agent else None,
    )
    session.add(db_session)
    await session.flush()
    return db_session, raw_token


async def validate_session(
    session: AsyncSession,
    raw_token: Optional[str],
) -> UserSession:
    """Validate a bearer session token against server-side database state.

    Enforces:
    - Token existence
    - Revocation status
    - Absolute expiry (24h)
    - Idle inactivity timeout (60m)
    - Active user account status
    """
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)

    stmt = (
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(UserSession.token_hash == token_hash)
    )
    result = await session.execute(stmt)
    session_record = result.scalars().first()

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session credential.",
        )

    # Check revocation (replay detection)
    if session_record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked.",
        )

    # Check absolute expiration
    if session_record.expires_at <= now:
        session_record.revoked_at = now
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired.",
        )

    # Check idle inactivity timeout
    if session_record.last_accessed_at < (now - timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES)):
        session_record.revoked_at = now
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to inactivity.",
        )

    # Verify user existence and active status
    if not session_record.user or not session_record.user.is_active:
        session_record.revoked_at = now
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
        )

    # Update last_accessed_at on valid request
    session_record.last_accessed_at = now
    await session.commit()

    return session_record


async def revoke_session(
    session: AsyncSession,
    raw_token: Optional[str],
) -> Optional[UserSession]:
    """Revoke an active session server-side immediately upon logout (GAP-05)."""
    if not raw_token:
        return None

    token_hash = hash_session_token(raw_token)
    stmt = select(UserSession).where(UserSession.token_hash == token_hash)
    result = await session.execute(stmt)
    session_record = result.scalars().first()

    if session_record and session_record.revoked_at is None:
        session_record.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        return session_record

    return None


async def rotate_session(
    session: AsyncSession,
    raw_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[UserSession, str]:
    """Rotate an existing session, invalidating the old token and generating a fresh one (GAP-05)."""
    old_session = await validate_session(session, raw_token)
    now = datetime.now(timezone.utc)

    # Invalidate prior credential
    old_session.revoked_at = now

    # Issue fresh credential for the same authenticated user
    new_raw_token = generate_session_token()
    new_token_hash = hash_session_token(new_raw_token)
    expires_at = now + timedelta(hours=SESSION_LIFETIME_HOURS)

    new_session = UserSession(
        user_id=old_session.user_id,
        token_hash=new_token_hash,
        created_at=now,
        last_accessed_at=now,
        expires_at=expires_at,
        revoked_at=None,
        ip_address=ip_address,
        user_agent=user_agent[:255] if user_agent else None,
    )
    session.add(new_session)
    await session.commit()

    return new_session, new_raw_token


def set_session_cookie(
    response: Response,
    raw_token: str,
    secure: bool = False,
) -> None:
    """Attach HttpOnly, Lax, Path=/ session cookie to response."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_LIFETIME_HOURS * 3600,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(
    response: Response,
    secure: bool = False,
) -> None:
    """Clear session cookie from client browser."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def verify_csrf_header(request: Request) -> None:
    """Verify anti-CSRF custom header on state-changing cookie-authenticated requests."""
    if request.method.upper() in {"POST", "PUT", "DELETE", "PATCH"}:
        header_val = request.headers.get(CSRF_HEADER_NAME, "").lower()
        custom_token = request.headers.get("x-csrf-token", "")
        if header_val != CSRF_EXPECTED_VALUE and not custom_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF verification failed: missing required custom header.",
            )
