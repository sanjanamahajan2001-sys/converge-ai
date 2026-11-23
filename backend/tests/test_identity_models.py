"""Tests for Core User and AuditLog SQLAlchemy models."""
import uuid
import pytest
from app.db.models.audit import AuditLog
from app.db.models.user import User


def test_user_repr_does_not_leak_secrets():
    """Verify User __repr__ strictly excludes password_hash, email, or phone numbers."""
    u = User(
        id=uuid.uuid4(),
        username="test_user",
        email="test@example.com",
        password_hash="$2b$12$securehash12345678901234567890123456789012345678901234",
        full_name="Test User",
        phone_number="+1-555-0100",
        is_active=True,
    )
    repr_str = repr(u)
    assert "test_user" in repr_str
    assert "password_hash" not in repr_str
    assert "$2b$12$" not in repr_str
    assert "test@example.com" not in repr_str
    assert "+1-555-0100" not in repr_str


def test_audit_log_repr():
    """Verify AuditLog __repr__ formats action and resource safely."""
    audit = AuditLog(
        id=1,
        actor_username="test_user",
        action_type="USER_REGISTERED",
        resource_type="USER",
        resource_id="12345",
        event_payload={"status": "SUCCESS"},
    )
    repr_str = repr(audit)
    assert "USER_REGISTERED" in repr_str
    assert "test_user" in repr_str
    assert "resource='USER':'12345'" in repr_str
