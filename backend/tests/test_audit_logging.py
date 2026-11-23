"""Tests for GAP-10 security audit logging and PII payload scrubbing."""
from app.core.audit import hash_ip, sanitize_audit_payload


def test_hash_ip():
    """Verify IP address is consistently hashed for privacy."""
    assert hash_ip(None) is None
    assert hash_ip("") is None
    h1 = hash_ip("192.168.1.100")
    h2 = hash_ip("192.168.1.100")
    assert h1 == h2
    assert len(h1) == 16


def test_sanitize_payload_strips_forbidden_keys():
    """Verify passwords, tokens, secrets, and raw PII keys are stripped from payload."""
    dirty_payload = {
        "status": "SUCCESS",
        "action": "REGISTRATION",
        "password": "PlainTextPassword123!",
        "password_hash": "$2b$12$somehash",
        "token": "secret_jwt_token",
        "email": "user@example.com",
        "phone_number": "+1234567890",
        "session_id": "sess_12345",
    }
    clean = sanitize_audit_payload(dirty_payload)
    assert "password" not in clean
    assert "password_hash" not in clean
    assert "token" not in clean
    assert "email" not in clean
    assert "phone_number" not in clean
    assert "session_id" not in clean
    assert clean["status"] == "SUCCESS"
    assert clean["action"] == "REGISTRATION"


def test_sanitize_payload_redacts_embedded_pii_in_strings():
    """Verify email and phone patterns embedded in allowed string fields are redacted."""
    payload_with_pii = {
        "details": "User attempted registration with email john.doe@example.com and phone +1-555-123-4567",
        "reason": "Contact support at help@company.org",
        "status": "FAILED",
    }
    clean = sanitize_audit_payload(payload_with_pii)
    assert "john.doe@example.com" not in clean["details"]
    assert "[REDACTED_EMAIL]" in clean["details"]
    assert "[REDACTED_PHONE]" in clean["details"]
    assert "help@company.org" not in clean["reason"]
    assert "[REDACTED_EMAIL]" in clean["reason"]


def test_sanitize_payload_allows_whitelisted_metadata():
    """Verify safe technical metadata is preserved."""
    safe_payload = {
        "action": "USER_REGISTERED",
        "timestamp": "2026-10-23T14:00:00Z",
        "resource_type": "USER",
        "resource_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "SUCCESS",
        "reason": "VALIDATION_PASSED",
    }
    clean = sanitize_audit_payload(safe_payload)
    assert clean == safe_payload


def test_sanitize_payload_empty_and_none():
    """Verify empty or None payloads return empty dictionary."""
    assert sanitize_audit_payload(None) == {}
    assert sanitize_audit_payload({}) == {}
