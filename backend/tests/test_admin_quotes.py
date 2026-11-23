"""Unit and integration tests for Administrative Commercial Quotes & RFQ Oversight."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models.quote import (
    EmailDeliveryStatus,
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

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture(scope="module")
def app_instance():
    assert "test" in TEST_DB_URL.lower(), f"SAFETY GUARD: Non-test DB: {TEST_DB_URL}"
    test_settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DB_URL,
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="TestAdminSecret123!",
    )
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def admin_client(client, sync_engine):
    token = generate_session_token()
    token_hash = hash_session_token(token)

    with Session(sync_engine) as session:
        admin_user = session.query(User).filter(User.username == "adm_quote_admin").first()
        if not admin_user:
            admin_user = User(
                username="adm_quote_admin",
                email="admin_quotes@conference.org",
                password_hash=hash_password("AdminPass123!"),
                full_name="Admin Director",
                is_admin=True,
                is_active=True,
            )
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)

        user_session = UserSession(
            user_id=admin_user.id,
            token_hash=token_hash,
            ip_address="127.0.0.1",
            user_agent="PyTestAdminClient/1.0",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            last_accessed_at=datetime.now(timezone.utc),
        )
        session.add(user_session)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, token)
    yield client
    client.cookies.clear()


@pytest.fixture
def non_admin_client(client, sync_engine):
    token = generate_session_token()
    token_hash = hash_session_token(token)

    with Session(sync_engine) as session:
        regular_user = session.query(User).filter(User.username == "adm_quote_regular").first()
        if not regular_user:
            regular_user = User(
                username="adm_quote_regular",
                email="delegate@test.com",
                password_hash=hash_password("RegularPass123!"),
                full_name="Delegate One",
                is_admin=False,
                is_active=True,
            )
            session.add(regular_user)
            session.commit()
            session.refresh(regular_user)

        user_session = UserSession(
            user_id=regular_user.id,
            token_hash=token_hash,
            ip_address="127.0.0.1",
            user_agent="PyTestRegularClient/1.0",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            last_accessed_at=datetime.now(timezone.utc),
        )
        session.add(user_session)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, token)
    yield client
    client.cookies.clear()


@pytest.fixture
def quote_fixtures(sync_engine):
    with Session(sync_engine) as session:
        # Create vendor and customer
        buyer = session.query(User).filter(User.username == "adm_quote_buyer").first()
        if not buyer:
            buyer = User(
                username="adm_quote_buyer",
                email="buyer@infrastructure.org",
                password_hash=hash_password("RegularPass123!"),
                full_name="Rajesh Iyer",
                company_name="Infra Build Ltd",
                is_admin=False,
                is_active=True,
            )
            session.add(buyer)

        seller = session.query(User).filter(User.username == "adm_quote_seller").first()
        if not seller:
            seller = User(
                username="adm_quote_seller",
                email="sales@deccanmaterials.com",
                password_hash=hash_password("RegularPass123!"),
                full_name="Sunil Gavaskar",
                company_name="Deccan Calcined Materials",
                is_admin=False,
                is_active=True,
            )
            session.add(seller)
        session.commit()
        session.refresh(buyer)
        session.refresh(seller)

        # Create QuoteRequest
        req = QuoteRequest(
            customer_id=buyer.id,
            title="Procurement Ask: 500 MT LC3 for Pune Terminal",
            product_name="Limestone Calcined Clay Cement (LC3)",
            product_code="LC3_CEM_500",
            quantity=Decimal("500.00"),
            quantity_unit="MT",
            delivery_location="Pune Yard",
            timeline_days=20,
            currency="INR",
            urgency=QuoteUrgency.IMMEDIATE,
            status=QuoteRequestStatus.OPEN,
        )
        session.add(req)
        session.commit()
        session.refresh(req)

        # Match
        match = QuoteVendorMatch(
            quote_request_id=req.id,
            vendor_id=seller.id,
            match_score=Decimal("94.50"),
            match_reasons=["High grade LC3 capability", "Pune logistics"],
            status=VendorMatchStatus.QUOTED_VIA_EMAIL,
        )
        session.add(match)
        session.commit()
        session.refresh(match)

        # Dispatch
        disp = QuoteEmailDispatch(
            quote_vendor_match_id=match.id,
            quote_request_id=req.id,
            vendor_id=seller.id,
            sender_email=seller.email,
            recipient_email=buyer.email,
            quote_reference_number="QUO-TEST-ADM-001",
            unit_price=Decimal("4200.00"),
            total_value=Decimal("2100000.00"),
            currency="INR",
            incoterm="EXW",
            lead_time_days=18,
            validity_days=14,
            payment_terms="20% Advance, 80% on Delivery",
            commercial_notes="Certified test certificate included per 50 MT batch",
            email_subject="Formal Quotation: LC3 Cement (500 MT)",
            email_body_html="<html><body><h1>Commercial Quote</h1></body></html>",
            delivery_status=EmailDeliveryStatus.SENT,
        )
        session.add(disp)
        session.commit()
        session.refresh(disp)

        yield {
            "buyer": buyer,
            "seller": seller,
            "request": req,
            "match": match,
            "dispatch": disp,
        }

        # Cleanup
        session.delete(disp)
        session.delete(match)
        session.delete(req)
        session.commit()


def test_admin_quotes_security_non_admin_forbidden(non_admin_client):
    """Verify non-admin users receive 403 Forbidden."""
    resp = non_admin_client.get("/converge-api/v1/admin/quotes", headers=CSRF_HEADERS)
    assert resp.status_code == 403


def test_admin_quotes_listing_and_metrics(admin_client, quote_fixtures):
    """Verify admin quotes directory lists dispatches and calculates metrics."""
    resp = admin_client.get("/converge-api/v1/admin/quotes", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "metrics" in data
    assert data["total"] >= 1

    # Check metrics
    metrics = data["metrics"]
    assert metrics["total_dispatched"] >= 1
    assert float(metrics["total_quoted_value"]) >= 2100000.00
    assert metrics["unique_vendors"] >= 1
    assert metrics["unique_customers"] >= 1
    assert metrics["sent_count"] >= 1

    # Check item fields
    item = next((i for i in data["items"] if i["quote_reference_number"] == "QUO-TEST-ADM-001"), None)
    assert item is not None
    assert item["product_name"] == "Limestone Calcined Clay Cement (LC3)"
    assert float(item["unit_price"]) == 4200.00
    assert float(item["total_value"]) == 2100000.00
    assert item["vendor_name"] == "Sunil Gavaskar"
    assert item["customer_name"] == "Rajesh Iyer"
    assert item["delivery_status"] == "SENT"


def test_admin_quotes_search_and_filter(admin_client, quote_fixtures):
    """Verify admin quotes search by reference number, commodity, and status filter."""
    # Search by reference
    resp = admin_client.get("/converge-api/v1/admin/quotes?search=QUO-TEST-ADM-001", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["quote_reference_number"] == "QUO-TEST-ADM-001"

    # Search by non-existent term
    resp = admin_client.get("/converge-api/v1/admin/quotes?search=NONEXISTENT_COMMODITY_999", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0

    # Filter by status
    resp = admin_client.get("/converge-api/v1/admin/quotes?status=SENT", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    assert any(i["quote_reference_number"] == "QUO-TEST-ADM-001" for i in resp.json()["items"])


def test_admin_quote_detail_inspection(admin_client, quote_fixtures):
    """Verify forensic inspector detail endpoint retrieves HTML email body."""
    disp_id = quote_fixtures["dispatch"].id
    resp = admin_client.get(f"/converge-api/v1/admin/quotes/{disp_id}", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(disp_id)
    assert data["quote_reference_number"] == "QUO-TEST-ADM-001"
    assert "email_body_html" in data
    assert "<html><body><h1>Commercial Quote</h1></body></html>" in data["email_body_html"]


def test_admin_user_quotes_portfolio(admin_client, quote_fixtures):
    """Verify admin user quotes endpoint retrieves quotes for specific delegate."""
    seller_id = quote_fixtures["seller"].id
    resp = admin_client.get(f"/converge-api/v1/admin/users/{seller_id}/quotes", headers=CSRF_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["vendor_id"] == str(seller_id)
