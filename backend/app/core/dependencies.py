"""Reusable FastAPI authentication dependencies for session validation (GAP-05)."""
import ipaddress
from typing import Optional
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.session import (
    SESSION_COOKIE_NAME,
    UserSession,
    validate_session,
    verify_csrf_header,
)
from app.db.models.user import User
from app.db.session import get_db_session


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


def extract_session_token(request: Request) -> Optional[str]:
    """Extract raw session token from HttpOnly cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()
        if bearer_token:
            return bearer_token

    return None


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> UserSession:
    """Validate active server-side session from database state.

    Enforces token validity, revocation check, expiration, idle timeout, and user status.
    """
    token = extract_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    # If authenticated via cookie on state-changing method, verify CSRF protection header
    if request.cookies.get(SESSION_COOKIE_NAME):
        verify_csrf_header(request)

    return await validate_session(session=db, raw_token=token)


async def get_current_user(
    current_session: UserSession = Depends(get_current_session),
) -> User:
    """Extract active authenticated user from validated session."""
    return current_session.user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce administrative privilege check on protected admin APIs (Phase 2)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privilege required.",
        )
    return current_user
