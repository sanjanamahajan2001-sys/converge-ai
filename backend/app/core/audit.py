"""Security Audit Logging & PII Scrubbing Foundation (GAP-10).

Ensures that core.audit_logs records security-relevant events while strictly
prohibiting plain credentials, emails, phone numbers, and personal data
from event_payload.
"""
import hashlib
import re
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

# GAP-10 Mandated payload allowlist
ALLOWED_PAYLOAD_KEYS = {
    "action",
    "timestamp",
    "ip_hash",
    "resource_type",
    "resource_id",
    "status",
    "reason",
    "details",
    "user_agent_hash",
}

# Strict blacklist for sensitive fields that must never appear in payloads
FORBIDDEN_KEY_PATTERNS = re.compile(
    r"(password|hash|secret|token|credential|email|phone|cookie|session_id|authorization)",
    re.IGNORECASE,
)

# PII Pattern matchers (email and international phone)
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def hash_ip(ip_address: Optional[str]) -> Optional[str]:
    """Hash an IP address using SHA-256 for anonymized security telemetry."""
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.strip().encode("utf-8")).hexdigest()[:16]


def sanitize_audit_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize and scrub audit payload against GAP-10 PII allowlist and privacy rules.

    Strips forbidden keys, redacts email/phone patterns, and enforces allowed keys.
    """
    if not payload:
        return {}

    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        # Check against forbidden key name patterns
        if FORBIDDEN_KEY_PATTERNS.search(key):
            continue

        # Check against allowed key allowlist
        if key not in ALLOWED_PAYLOAD_KEYS:
            continue

        # Check string values for embedded email/phone PII
        if isinstance(value, str):
            if key == "resource_id" or UUID_PATTERN.match(value.strip()):
                sanitized[key] = value.strip()
            else:
                clean_val = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
                clean_val = PHONE_PATTERN.sub("[REDACTED_PHONE]", clean_val)
                sanitized[key] = clean_val
        elif isinstance(value, (int, float, bool)) or value is None:
            sanitized[key] = value
        elif isinstance(value, dict):
            # Recurse for nested dictionaries
            clean_dict = sanitize_audit_payload(value)
            if clean_dict:
                sanitized[key] = clean_dict

    return sanitized


async def record_audit_event(
    session: AsyncSession,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor_username: str = "anonymous",
    user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    """Create and stage a sanitized audit event in the database session.

    Import of AuditLog is deferred to avoid circular import issues.
    """
    from app.db.models.audit import AuditLog

    clean_payload = sanitize_audit_payload(payload)
    if ip_address and "ip_hash" not in clean_payload:
        clean_payload["ip_hash"] = hash_ip(ip_address)

    audit_entry = AuditLog(
        user_id=user_id,
        actor_username=actor_username[:50],
        action_type=action_type[:80],
        resource_type=resource_type[:80],
        resource_id=resource_id[:100] if resource_id else None,
        ip_address=ip_address,
        event_payload=clean_payload,
    )
    session.add(audit_entry)
    return audit_entry
