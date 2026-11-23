"""Tests for Phase 4: Context-Aware Connection Requests & Recipient Preview UI (GAP-06 / Phase 4)."""

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Tuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession
from starlette.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
from app.db.models.conversation import Conversation, ConversationStatus
from app.db.models.profile import AvailabilityStatus, ParticipantProfile, ParticipationIntent
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Refusing to run tests against non-test DB: {TEST_DB_URL}"
    )
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    """Yield test client."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous SQLAlchemy engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_test_db(sync_engine):
    """Clean up records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.conversation_business_contexts;")
            conn.exec_driver_sql("DELETE FROM core.messages;")
            conn.exec_driver_sql("DELETE FROM core.conversations;")
            conn.exec_driver_sql("DELETE FROM core.participant_profiles;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.audit_logs;")
            conn.exec_driver_sql("DELETE FROM core.users;")
            conn.commit()

    _clean()
    yield
    _clean()


def create_test_participant(
    sync_engine,
    username: str,
    email: str,
    has_profile: bool = True,
) -> Tuple[User, str]:
    """Create a participant with active session and initialized profile."""
    with SASession(sync_engine) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=f"Full Name of {username}",
            company_name="Innovate Corp",
            job_title="Software Architect",
            phone_number="+1-555-0100",
            is_active=True,
        )
        session.add(user)
        session.flush()

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        now = datetime.now(timezone.utc)

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=24),
            last_accessed_at=now,
        )
        session.add(user_session)

        if has_profile:
            profile = ParticipantProfile(
                user_id=user.id,
                bio_summary=f"Bio for {username}",
                intent=ParticipationIntent.NETWORKING,
                availability=AvailabilityStatus.AVAILABLE,
                allow_agent_matching=True,
            )
            session.add(profile)

        session.commit()
        session.refresh(user)
        return user, raw_token


def test_initiate_conversation_with_business_context_private_budget(client, sync_engine):
    """Test initiating an RFQ conversation with private target budget masks price and computes snapshot hash."""
    buyer, buyer_token = create_test_participant(sync_engine, "buyer_priv", "buyer_priv@example.com")
    supplier, _ = create_test_participant(sync_engine, "supp_priv", "supp_priv@example.com")

    req_payload = {
        "target_id": str(supplier.id),
        "business_context": {
            "inquiry_type": "RFQ_PRODUCT",
            "product_name": "Limestone Calcined Clay Cement (LC3)",
            "product_code": "MAT-CEMENT-LC3",
            "grade_code": "LC3-50",
            "quantity": 1000.0,
            "unit": "METRIC_TONNE",
            "delivery_location": "Pune",
            "timeline_days": 45,
            "target_price_indication": 5400.0,
            "is_budget_public": False,  # Private budget
            "urgency": "PLANNED",
            "inquiry_notes": "Bulk supply needed for ongoing flyover project.",
        },
    }

    resp = client.post(
        "/converge-api/v1/conversations",
        json=req_payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["status"] == "INVITED"
    assert data["has_business_context"] is True
    assert data["business_inquiry_type"] == "RFQ_PRODUCT"

    biz_ctx = data.get("business_context")
    assert biz_ctx is not None
    assert biz_ctx["product_name"] == "Limestone Calcined Clay Cement (LC3)"
    assert biz_ctx["quantity"] == 1000.0
    assert biz_ctx["unit"] == "METRIC_TONNE"
    assert biz_ctx["delivery_location"] == "Pune"
    assert biz_ctx["timeline_days"] == 45
    # Strict privacy check: budget was private, so target_price_indication must be None!
    assert biz_ctx["target_price_indication"] is None

    # Verify SHA-256 integrity hash matches canonical formulation with masked budget
    expected_canonical = "RFQ_PRODUCT|Limestone Calcined Clay Cement (LC3)|MAT-CEMENT-LC3|LC3-50||1000.0|METRIC_TONNE|Pune|45||PLANNED"
    expected_hash = hashlib.sha256(expected_canonical.encode("utf-8")).hexdigest()
    assert biz_ctx["snapshot_hash"] == expected_hash


def test_initiate_conversation_with_business_context_public_budget(client, sync_engine):
    """Test initiating an RFQ conversation with public target budget stores the price in snapshot."""
    buyer, buyer_token = create_test_participant(sync_engine, "buyer_pub", "buyer_pub@example.com")
    vendor, _ = create_test_participant(sync_engine, "vendor_pub", "vendor_pub@example.com")

    req_payload = {
        "target_id": str(vendor.id),
        "business_context": {
            "inquiry_type": "RFI_SERVICE",
            "product_name": "Bulk Pneumatic Bulker Fleet",
            "quantity": 25.0,
            "unit": "TRUCKLOAD",
            "delivery_location": "Mumbai to Pune",
            "timeline_days": 15,
            "target_price_indication": 22000.0,
            "is_budget_public": True,  # Disclose budget
            "urgency": "IMMEDIATE",
            "inquiry_notes": "Dedicated 35-ton bulkers required.",
        },
    }

    resp = client.post(
        "/converge-api/v1/conversations",
        json=req_payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    biz_ctx = data.get("business_context")
    assert biz_ctx is not None
    assert biz_ctx["product_name"] == "Bulk Pneumatic Bulker Fleet"
    assert biz_ctx["target_price_indication"] == 22000.0

    expected_canonical = "RFI_SERVICE|Bulk Pneumatic Bulker Fleet||||25.0|TRUCKLOAD|Mumbai to Pune|15|22000.0|IMMEDIATE"
    expected_hash = hashlib.sha256(expected_canonical.encode("utf-8")).hexdigest()
    assert biz_ctx["snapshot_hash"] == expected_hash


def test_recipient_and_idor_access_to_business_context(client, sync_engine):
    """Test that recipient can view the commercial context, but 3rd-party non-participant is 403 Forbidden."""
    buyer, buyer_token = create_test_participant(sync_engine, "buyer_idor", "buyer_idor@example.com")
    supplier, supplier_token = create_test_participant(sync_engine, "supp_idor", "supp_idor@example.com")
    outsider, outsider_token = create_test_participant(sync_engine, "out_idor", "out_idor@example.com")

    req_payload = {
        "target_id": str(supplier.id),
        "business_context": {
            "inquiry_type": "RFQ_PRODUCT",
            "product_name": "Ordinary Portland Cement (OPC 53)",
            "quantity": 500.0,
            "unit": "METRIC_TONNE",
            "delivery_location": "Nashik",
            "timeline_days": 30,
            "is_budget_public": False,
        },
    }

    init_resp = client.post(
        "/converge-api/v1/conversations",
        json=req_payload,
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert init_resp.status_code == 201
    conv_id = init_resp.json()["id"]

    # 1. Recipient (supplier) retrieves conversation detail: sees business_context
    supp_conv_resp = client.get(
        f"/converge-api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert supp_conv_resp.status_code == 200
    supp_data = supp_conv_resp.json()
    assert supp_data["business_context"] is not None
    assert supp_data["business_context"]["product_name"] == "Ordinary Portland Cement (OPC 53)"
    assert supp_data["has_business_context"] is True

    # 2. Recipient calls explicit endpoint GET /conversations/{id}/business-context
    ctx_resp = client.get(
        f"/converge-api/v1/conversations/{conv_id}/business-context",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert ctx_resp.status_code == 200
    assert ctx_resp.json()["product_name"] == "Ordinary Portland Cement (OPC 53)"

    # 3. Third-party outsider attempts to access GET /conversations/{id}/business-context: 403 Forbidden!
    outsider_ctx_resp = client.get(
        f"/converge-api/v1/conversations/{conv_id}/business-context",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert outsider_ctx_resp.status_code == 403
    assert "Access denied" in outsider_ctx_resp.json()["detail"]
