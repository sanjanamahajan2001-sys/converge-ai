"""Unit tests for Quote Domain Models, Constraints, and DB Persistence (Quote Subphase 2)."""

import uuid
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SASession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models.quote import (
    EmailDeliveryStatus,
    QuoteEmailDispatch,
    QuoteRequest,
    QuoteRequestStatus,
    QuoteUrgency,
    QuoteVendorMatch,
    VendorMatchStatus,
)
from app.db.models.user import User

settings = get_settings()
engine = create_engine(
    settings.MIGRATION_DATABASE_URL or "postgresql://converge_ai_owner:2a41722c2a5717cbfc000b16c624f2bd@127.0.0.1:5432/converge_ai_db"
)


@pytest.fixture
def db_session():
    """Isolated session for model testing."""
    session = SASession(bind=engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def create_test_user(session: SASession, prefix: str) -> User:
    """Helper to provision test users."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"{prefix}_{uid}",
        email=f"{prefix}_{uid}@example.com",
        full_name=f"Test {prefix.capitalize()}",
        company_name=f"{prefix.capitalize()} Corp",
        password_hash=hash_password("Secret123!"),
    )
    session.add(user)
    session.flush()
    return user


def test_quote_enums():
    """Verify enum members and values."""
    assert QuoteRequestStatus.OPEN.value == "OPEN"
    assert QuoteRequestStatus.MATCHED.value == "MATCHED"
    assert QuoteRequestStatus.CLOSED.value == "CLOSED"
    assert QuoteRequestStatus.CANCELLED.value == "CANCELLED"

    assert QuoteUrgency.IMMEDIATE.value == "IMMEDIATE"
    assert QuoteUrgency.PLANNED.value == "PLANNED"
    assert QuoteUrgency.EXPLORATORY.value == "EXPLORATORY"

    assert VendorMatchStatus.PENDING_REVIEW.value == "PENDING_REVIEW"
    assert VendorMatchStatus.QUOTED_VIA_EMAIL.value == "QUOTED_VIA_EMAIL"
    assert VendorMatchStatus.DECLINED.value == "DECLINED"
    assert VendorMatchStatus.EXPIRED.value == "EXPIRED"

    assert EmailDeliveryStatus.QUEUED.value == "QUEUED"
    assert EmailDeliveryStatus.SENT.value == "SENT"
    assert EmailDeliveryStatus.FAILED.value == "FAILED"


def test_quote_models_persistence_and_relationships(db_session: SASession):
    """Verify persisting a QuoteRequest, QuoteVendorMatch, and QuoteEmailDispatch."""
    customer = create_test_user(db_session, "buyer")
    vendor = create_test_user(db_session, "supplier")

    # 1. Create Ask
    ask = QuoteRequest(
        customer_id=customer.id,
        customer_agent_persona="Procurement AI Agent",
        title="Procurement: 1000 MT Calcined Clay LC3",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="CALCINED_CLAY_LC3",
        quantity=Decimal("1000.0000"),
        quantity_unit="MT",
        delivery_location="Pune Industrial Yard, Maharashtra",
        timeline_days=21,
        target_price_indication=Decimal("3200.00"),
        currency="INR",
        is_budget_public=False,
        urgency=QuoteUrgency.PLANNED,
        technical_specifications={
            "standard": "IS 18189:2023",
            "purity_percentage": 95.5,
            "packaging": "50kg HDPE bags",
        },
        inquiry_notes="Required for green highway infrastructure project.",
        status=QuoteRequestStatus.OPEN,
    )
    db_session.add(ask)
    db_session.flush()

    assert ask.id is not None
    assert ask.created_at is not None

    # 2. Create Vendor Match
    match = QuoteVendorMatch(
        quote_request_id=ask.id,
        vendor_id=vendor.id,
        match_score=Decimal("94.50"),
        match_reasons=["Supplier produces LC3 in Pune region", "Meets IS 18189"],
        status=VendorMatchStatus.PENDING_REVIEW,
    )
    db_session.add(match)
    db_session.flush()

    assert match.id is not None
    assert len(ask.matches) == 1
    assert ask.matches[0].vendor_id == vendor.id

    # 3. Create Email Dispatch Record
    dispatch = QuoteEmailDispatch(
        quote_vendor_match_id=match.id,
        quote_request_id=ask.id,
        vendor_id=vendor.id,
        sender_email="sanjana.mahajan@sofueled.com",
        recipient_email=customer.email,
        quote_reference_number="QUO-2026-TEST01",
        unit_price=Decimal("3450.00"),
        total_value=Decimal("3450000.00"),
        currency="INR",
        incoterm="EXW",
        lead_time_days=18,
        validity_days=15,
        payment_terms="20% Advance, 80% upon delivery",
        commercial_notes="Quality certificate included per batch.",
        email_subject="Commercial Quotation: 1000 MT LC3 [QUO-2026-TEST01]",
        email_body_html="<p>Commercial offer details</p>",
        delivery_status=EmailDeliveryStatus.SENT,
        external_message_id="msg-123456",
    )
    db_session.add(dispatch)
    db_session.flush()

    # Query back from DB
    queried_ask = db_session.query(QuoteRequest).filter_by(id=ask.id).first()
    assert queried_ask is not None
    assert queried_ask.customer.id == customer.id
    assert len(queried_ask.matches) == 1
    assert len(queried_ask.matches[0].dispatches) == 1

    queried_dispatch = queried_ask.matches[0].dispatches[0]
    assert queried_dispatch.quote_reference_number == "QUO-2026-TEST01"
    assert queried_dispatch.total_value == Decimal("3450000.00")
    assert queried_dispatch.sender_email == "sanjana.mahajan@sofueled.com"


def test_quote_vendor_match_unique_constraint(db_session: SASession):
    """Verify that a vendor cannot be matched twice to the same ask."""
    customer = create_test_user(db_session, "buyer")
    vendor = create_test_user(db_session, "supplier")

    ask = QuoteRequest(
        customer_id=customer.id,
        title="Procurement of Fly Ash",
        product_name="Fly Ash Class F",
        status=QuoteRequestStatus.OPEN,
    )
    db_session.add(ask)
    db_session.flush()

    match1 = QuoteVendorMatch(
        quote_request_id=ask.id,
        vendor_id=vendor.id,
        match_score=Decimal("88.00"),
    )
    db_session.add(match1)
    db_session.flush()

    # Second match with identical pair must violate unique constraint
    match2 = QuoteVendorMatch(
        quote_request_id=ask.id,
        vendor_id=vendor.id,
        match_score=Decimal("90.00"),
    )
    db_session.add(match2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_quote_request_cascade_delete(db_session: SASession):
    """Verify that deleting a QuoteRequest cascades to its matches and dispatches."""
    customer = create_test_user(db_session, "buyer")
    vendor = create_test_user(db_session, "supplier")

    ask = QuoteRequest(
        customer_id=customer.id,
        title="Procurement to be deleted",
        product_name="Ground Granulated Blast-furnace Slag",
        status=QuoteRequestStatus.OPEN,
    )
    db_session.add(ask)
    db_session.flush()

    match = QuoteVendorMatch(
        quote_request_id=ask.id,
        vendor_id=vendor.id,
        match_score=Decimal("85.00"),
    )
    db_session.add(match)
    db_session.flush()

    dispatch = QuoteEmailDispatch(
        quote_vendor_match_id=match.id,
        quote_request_id=ask.id,
        vendor_id=vendor.id,
        sender_email="sanjana.mahajan@sofueled.com",
        recipient_email=customer.email,
        quote_reference_number="QUO-DEL-001",
        unit_price=Decimal("2000.00"),
        total_value=Decimal("200000.00"),
        currency="INR",
        incoterm="EXW",
        lead_time_days=10,
        validity_days=15,
        payment_terms="Net 30",
        email_subject="Test",
        email_body_html="<p>Test</p>",
        delivery_status=EmailDeliveryStatus.SENT,
    )
    db_session.add(dispatch)
    db_session.flush()

    ask_id = ask.id
    match_id = match.id
    dispatch_id = dispatch.id

    # Delete ask
    db_session.delete(ask)
    db_session.flush()

    assert db_session.query(QuoteRequest).filter_by(id=ask_id).first() is None
    assert db_session.query(QuoteVendorMatch).filter_by(id=match_id).first() is None
    assert db_session.query(QuoteEmailDispatch).filter_by(id=dispatch_id).first() is None
