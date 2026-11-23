"""Failed-attempt rate limiting and lockouts for authentication endpoints."""
import hashlib
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.rate_limit import LoginRateLimit

# Rate limiting policy: 5 failed attempts per 15-minute window
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
WINDOW_MINUTES = 15


def hash_client_ip(client_ip: str) -> str:
    """Return SHA-256 hash of client IP to prevent storing raw IP PII in rate limit records."""
    return hashlib.sha256(client_ip.strip().encode("utf-8")).hexdigest()


async def check_login_rate_limit(session: AsyncSession, client_ip: str) -> None:
    """Check if the client IP is currently throttled / locked out.

    Raises HTTPException 429 Too Many Requests with Retry-After header if locked out.
    """
    ip_h = hash_client_ip(client_ip)
    stmt = select(LoginRateLimit).where(LoginRateLimit.ip_hash == ip_h)
    result = await session.execute(stmt)
    record = result.scalars().first()

    if not record:
        return

    now = datetime.now(timezone.utc)

    # 1. Active lockout check
    if record.locked_until:
        if record.locked_until > now:
            remaining_seconds = math.ceil((record.locked_until - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Please try again later.",
                headers={"Retry-After": str(max(1, remaining_seconds))},
            )
        else:
            # Lockout expired, clean up record
            await session.delete(record)
            await session.commit()
            return

    # 2. Window expiration check
    if record.last_failed_at and (record.last_failed_at < now - timedelta(minutes=WINDOW_MINUTES)):
        await session.delete(record)
        await session.commit()


async def record_failed_login(session: AsyncSession, client_ip: str) -> bool:
    """Record a failed login attempt and apply lockout if threshold exceeded.

    Returns True if the attempt caused the client to become locked out.
    """
    ip_h = hash_client_ip(client_ip)
    now = datetime.now(timezone.utc)

    stmt = select(LoginRateLimit).where(LoginRateLimit.ip_hash == ip_h)
    result = await session.execute(stmt)
    record = result.scalars().first()

    is_locked = False

    if record:
        # Check if previous window expired
        if record.last_failed_at < (now - timedelta(minutes=WINDOW_MINUTES)) and (
            record.locked_until is None or record.locked_until <= now
        ):
            record.attempt_count = 1
            record.first_failed_at = now
            record.last_failed_at = now
            record.locked_until = None
        else:
            record.attempt_count += 1
            record.last_failed_at = now
            if record.attempt_count >= MAX_FAILED_ATTEMPTS:
                record.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                is_locked = True
    else:
        new_record = LoginRateLimit(
            ip_hash=ip_h,
            attempt_count=1,
            first_failed_at=now,
            last_failed_at=now,
            locked_until=None,
        )
        session.add(new_record)

    await session.commit()
    return is_locked


async def reset_login_rate_limit(session: AsyncSession, client_ip: str) -> None:
    """Reset failed login attempt counter upon successful authentication."""
    ip_h = hash_client_ip(client_ip)
    stmt = select(LoginRateLimit).where(LoginRateLimit.ip_hash == ip_h)
    result = await session.execute(stmt)
    record = result.scalars().first()

    if record:
        await session.delete(record)
        await session.commit()
