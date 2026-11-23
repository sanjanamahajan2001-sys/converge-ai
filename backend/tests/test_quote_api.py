"""Integration and security tests for Quote Requests, Vendor Panel, and Email Dispatch APIs (Quote Subphase 3)."""

from decimal import Decimal
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
from app.db.models.quote import (
    QuoteEmailDispatch,
    QuoteRequest,
    QuoteRequestStatus,
    QuoteUrgency,
    QuoteVendorMatch,
    VendorMatchStatus,
)
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app
from app.services.email import ConsoleEmailService, get_email_service

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    test_settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DB_URL,
        EMAIL_BACKEND="console",
    )
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    """Yield test client with default CSRF header configured."""
    with TestClient(app_instance, headers=CSRF_HEADERS) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous SQLAlchemy engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_quotes(sync_engine):
    """Clean up quote records and test users before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.quote_email_dispatches;")
            conn.exec_driver_sql("DELETE FROM business.quote_vendor_matches;")
            conn.exec_driver_sql("DELETE FROM business.quote_requests;")
            conn.exec_driver_sql("DELETE FROM core.messages WHERE conversation_id IN (SELECT id FROM core.conversations WHERE initiator_id IN (SELECT id FROM core.users WHERE username LIKE 'quote_test_%%'));")
            conn.exec_driver_sql("DELETE FROM business.conversation_business_contexts WHERE conversation_id IN (SELECT id FROM core.conversations WHERE initiator_id IN (SELECT id FROM core.users WHERE username LIKE 'quote_test_%%'));")
            conn.exec_driver_sql("DELETE FROM core.conversations WHERE initiator_id IN (SELECT id FROM core.users WHERE username LIKE 'quote_test_%%') OR target_id IN (SELECT id FROM core.users WHERE username LIKE 'quote_test_%%');")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users WHERE username LIKE 'quote_test_%%';")
            conn.commit()

    _clean()
    yield
    _clean()


def create_test_user(
    sync_engine,
    username: str,
    email: str,
    full_name: str,
    company_name: str = "Test Corp",
) -> Tuple[User, str]:
    """Create an attendee user with an active session token."""
    with SASession(sync_engine, expire_on_commit=False) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=full_name,
            company_name=company_name,
            job_title="Procurement Director",
            phone_number="+919876543210",
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
        session.commit()
        return user, raw_token


def test_create_quote_request_and_vendor_matching(client, sync_engine):
    """Verify customer ask creation and automated distribution to matching vendors."""
    customer, token_c = create_test_user(
        sync_engine, "quote_test_cust", "cust@infratech.com", "Sanjana Mahajan", "InfraTech EPC"
    )
    vendor, token_v = create_test_user(
        sync_engine, "quote_test_vend", "vend@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    client.cookies.set(SESSION_COOKIE_NAME, token_c)

    payload = {
        "title": "Procurement of 1000 MT Limestone Calcined Clay Cement (LC3)",
        "product_name": "Limestone Calcined Clay Cement (LC3)",
        "product_code": "CALCINED_CLAY_LC3",
        "quantity": 1000.0,
        "quantity_unit": "MT",
        "delivery_location": "Pune Industrial Yard, Maharashtra",
        "timeline_days": 21,
        "urgency": "PLANNED",
        "technical_specifications": {"standard": "IS 18189:2023"},
        "inquiry_notes": "Required for green highway project",
        "target_vendor_ids": [str(vendor.id)],
    }

    res = client.post("/converge-api/v1/quotes/asks", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["title"] == payload["title"]
    assert data["product_name"] == payload["product_name"]
    assert float(data["quantity"]) == 1000.0
    assert data["customer"]["full_name"] == "Sanjana Mahajan"

    # Verify vendor match was created in DB
    with SASession(sync_engine) as session:
        matches = session.query(QuoteVendorMatch).filter_by(vendor_id=vendor.id).all()
        assert len(matches) == 1
        assert matches[0].status == VendorMatchStatus.PENDING_REVIEW
        assert matches[0].match_score == Decimal("95.00")


def test_vendor_quotes_panel_listing_and_counts(client, sync_engine):
    """Verify vendor panel listing, customer summary, and tab count aggregations."""
    customer, token_c = create_test_user(
        sync_engine, "quote_test_c1", "cust1@infra.com", "Sanjana Mahajan", "InfraTech"
    )
    vendor, token_v = create_test_user(
        sync_engine, "quote_test_v1", "vend1@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    # Provision an ask with match for vendor
    with SASession(sync_engine) as session:
        ask = QuoteRequest(
            customer_id=customer.id,
            title="Strategic Ask: LC3 Cement",
            product_name="Limestone Calcined Clay Cement (LC3)",
            quantity=Decimal("500"),
            quantity_unit="MT",
            delivery_location="Mumbai Port",
            urgency=QuoteUrgency.IMMEDIATE,
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            quote_request_id=ask.id,
            vendor_id=vendor.id,
            match_score=Decimal("94.00"),
            match_reasons=["Supplier verified for LC3"],
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, token_v)
    res = client.get("/converge-api/v1/quotes/vendor-panel")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total"] == 1
    assert data["counts"]["all"] == 1
    assert data["counts"]["new_inquiries"] == 1
    assert data["counts"]["quoted"] == 0
    assert data["counts"]["declined"] == 0

    item = data["items"][0]
    assert item["title"] == "Strategic Ask: LC3 Cement"
    assert item["customer"]["full_name"] == "Sanjana Mahajan"
    assert item["customer"]["company_name"] == "InfraTech"
    assert item["status"] == "PENDING_REVIEW"
    assert float(item["match_score"]) == 94.0


def test_quote_request_detail_and_idor_security(client, sync_engine):
    """Verify ask detail access and strict IDOR boundary for unmatched third parties."""
    customer, token_c = create_test_user(
        sync_engine, "quote_test_c2", "cust2@infra.com", "Sanjana Mahajan", "InfraTech"
    )
    matched_vendor, token_v = create_test_user(
        sync_engine, "quote_test_v2", "vend2@deccan.com", "Maahi Sharma", "Deccan Cement"
    )
    unmatched_delegate, token_other = create_test_user(
        sync_engine, "quote_test_other", "other@random.com", "Other Delegate", "Random Corp"
    )

    ask_id = None
    with SASession(sync_engine) as session:
        ask = QuoteRequest(
            customer_id=customer.id,
            title="Confidential Ask",
            product_name="Special Grade Clinker",
            quantity=Decimal("2000"),
            quantity_unit="MT",
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            quote_request_id=ask.id,
            vendor_id=matched_vendor.id,
            match_score=Decimal("90.00"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()
        ask_id = str(ask.id)

    # 1. Matched vendor can view details
    client.cookies.set(SESSION_COOKIE_NAME, token_v)
    res_v = client.get(f"/converge-api/v1/quotes/{ask_id}")
    assert res_v.status_code == 200
    assert res_v.json()["product_name"] == "Special Grade Clinker"
    assert res_v.json()["vendor_match_status"] == "PENDING_REVIEW"

    # 2. Unmatched third party gets 404 (IDOR barrier)
    client.cookies.set(SESSION_COOKIE_NAME, token_other)
    res_other = client.get(f"/converge-api/v1/quotes/{ask_id}")
    assert res_other.status_code == 404


def test_send_quote_via_email(client, sync_engine):
    """Verify vendor submitting quotation terms triggers email dispatch and records audit log."""
    customer, token_c = create_test_user(
        sync_engine, "quote_test_c3", "customer3@infratech.com", "Sanjana Mahajan", "InfraTech"
    )
    vendor, token_v = create_test_user(
        sync_engine, "quote_test_v3", "vendor3@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    match_id = None
    with SASession(sync_engine) as session:
        ask = QuoteRequest(
            customer_id=customer.id,
            title="Supply of 1000 MT Calcined Clay",
            product_name="Limestone Calcined Clay Cement (LC3)",
            quantity=Decimal("1000"),
            quantity_unit="MT",
            delivery_location="Pune Industrial Yard",
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            quote_request_id=ask.id,
            vendor_id=vendor.id,
            match_score=Decimal("95.00"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()
        match_id = str(match.id)

    # Ensure console email service is active
    console_svc = get_email_service("console")
    if isinstance(console_svc, ConsoleEmailService):
        console_svc.clear()

    client.cookies.set(SESSION_COOKIE_NAME, token_v)

    quote_payload = {
        "unit_price": 3500.0,
        "total_value": 3500000.0,
        "currency": "INR",
        "incoterm": "EXW",
        "lead_time_days": 18,
        "validity_days": 14,
        "payment_terms": "20% Advance, 80% Delivery against Proforma",
        "commercial_notes": "Third-party lab quality certificate included per 50 MT batch.",
    }

    res = client.post(f"/converge-api/v1/quotes/matches/{match_id}/send-email", json=quote_payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["delivery_status"] == "SENT"
    assert data["recipient_email"] == "customer3@infratech.com"
    assert "QUO-" in data["quote_reference_number"]
    assert float(data["total_value"]) == 3500000.0

    # Verify match status updated to QUOTED_VIA_EMAIL
    with SASession(sync_engine) as session:
        updated_match = session.query(QuoteVendorMatch).filter_by(id=uuid.UUID(match_id)).first()
        assert updated_match.status == VendorMatchStatus.QUOTED_VIA_EMAIL
        assert len(updated_match.dispatches) == 1
        assert updated_match.dispatches[0].quote_reference_number == data["quote_reference_number"]


def test_decline_quote_request(client, sync_engine):
    """Verify vendor declining an ask updates match status to DECLINED."""
    customer, token_c = create_test_user(
        sync_engine, "quote_test_c4", "cust4@infra.com", "Sanjana Mahajan", "InfraTech"
    )
    vendor, token_v = create_test_user(
        sync_engine, "quote_test_v4", "vend4@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    match_id = None
    with SASession(sync_engine) as session:
        ask = QuoteRequest(
            customer_id=customer.id,
            title="Declined Inquiry",
            product_name="White Portland Cement",
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            quote_request_id=ask.id,
            vendor_id=vendor.id,
            match_score=Decimal("80.00"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()
        match_id = str(match.id)

    client.cookies.set(SESSION_COOKIE_NAME, token_v)
    res = client.post(f"/converge-api/v1/quotes/matches/{match_id}/decline")
    assert res.status_code == 200
    assert res.json()["status"] == "declined"

    with SASession(sync_engine) as session:
        updated_match = session.query(QuoteVendorMatch).filter_by(id=uuid.UUID(match_id)).first()
        assert updated_match.status == VendorMatchStatus.DECLINED


def test_send_direct_quote_from_conversation(client, sync_engine):
    """Verify vendor can directly dispatch a quotation from an active 1-on-1 conversation."""
    customer, token_c = create_test_user(
        sync_engine, "quote_test_cdir", "cust_dir@infra.com", "Sanjana Mahajan", "InfraTech"
    )
    vendor, token_v = create_test_user(
        sync_engine, "quote_test_vdir", "vend_dir@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    conv_id = None
    with SASession(sync_engine, expire_on_commit=False) as session:
        from app.db.models.conversation import Conversation, ConversationStatus
        conv = Conversation(
            initiator_id=customer.id,
            target_id=vendor.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()
        conv_id = str(conv.id)

        from app.db.models.business import ConversationBusinessContext
        ctx = ConversationBusinessContext(
            conversation_id=conv.id,
            version=1,
            inquiry_type="RFQ_PRODUCT",
            product_name="Limestone Calcined Clay Cement (LC3)",
            quantity=Decimal("1000.00"),
            unit="MT",
            delivery_location="Pune Industrial Yard",
            timeline_days=18,
            target_price_indication=Decimal("3500.00"),
            urgency="IMMEDIATE",
            inquiry_notes="Testing direct quote from bilateral conversation.",
            snapshot_hash="dir_quote_sha256",
        )
        session.add(ctx)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, token_v)

    quote_payload = {
        "unit_price": 3500.0,
        "total_value": 3500000.0,
        "currency": "INR",
        "incoterm": "EXW",
        "lead_time_days": 18,
        "validity_days": 14,
        "payment_terms": "20% Advance, 80% Delivery against Proforma",
        "commercial_notes": "Third-party lab quality certificate included.",
    }

    res = client.post(
        f"/converge-api/v1/quotes/conversations/{conv_id}/direct-quote",
        json=quote_payload,
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["delivery_status"] == "SENT"
    assert data["recipient_email"] == "cust_dir@infra.com"
    assert "QUO-" in data["quote_reference_number"]
    assert float(data["total_value"]) == 3500000.0

    # Verify that in-chat message was recorded
    with SASession(sync_engine) as session:
        from app.db.models.conversation import Message
        msgs = session.query(Message).filter_by(conversation_id=uuid.UUID(conv_id)).all()
        assert len(msgs) == 1
        assert "Official Commercial Quotation Dispatched via Email" in msgs[0].content
        assert data["quote_reference_number"] in msgs[0].content
