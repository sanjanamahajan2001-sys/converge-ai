"""Unit and Integration Tests for Dual-Sided Approval Engine, Revision Diff & Contact Security (Phase 7 - Subphase 5)."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
from app.db.models.proposal import ApprovalAction, CommercialRole, Proposal, ProposalApproval, ProposalRevision, ProposalStatus, ProposalType
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
    """Yield test client with default CSRF header."""
    with TestClient(app_instance, headers={"X-Requested-With": "XMLHttpRequest"}) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    """Create synchronous SQLAlchemy engine for test fixture setup."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_test_db(sync_engine):
    """Clean up test proposal records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.proposal_contact_disclosures;")
            conn.exec_driver_sql("DELETE FROM business.proposal_approvals;")
            conn.exec_driver_sql("DELETE FROM business.proposal_revisions;")
            conn.exec_driver_sql("DELETE FROM business.proposals;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users WHERE username LIKE 'appr_test_%%';")
            conn.commit()

    _clean()
    yield
    _clean()


def create_test_user(
    sync_engine,
    username: str,
    email: str,
    full_name: str,
    phone_number: str = "+919876543210",
    company_name: str = "Test Corp",
) -> tuple[User, str]:
    """Helper to create user and active session."""
    with SASession(sync_engine, expire_on_commit=False) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=full_name,
            company_name=company_name,
            job_title="Director of Procurement",
            phone_number=phone_number,
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


def test_dual_approval_and_cryptographic_receipt_generation(client, sync_engine):
    """Verify dual-sided consensus generates non-repudiable SHA-256 verification hash and unlocks contact info."""
    user_proposer, token_proposer = create_test_user(
        sync_engine, "appr_test_prop", "prop@infra.com", "Prakash Proposer", "+919876543211", "Proposer Cement"
    )
    user_recipient, token_recipient = create_test_user(
        sync_engine, "appr_test_recip", "recip@build.com", "Ramesh Recipient", "+919123456781", "Recipient Infra"
    )

    # 1. Proposer creates Proposal Revision 1
    client.cookies.set(SESSION_COOKIE_NAME, token_proposer)
    create_payload = {
        "recipient_id": str(user_recipient.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "validity_days": 10,
        "revision": {
            "title": "Supply Agreement: 600 MT Slag Cement",
            "proposal_type": "SUPPLY_CONTRACT",
            "product_name": "Portland Slag Cement (PSC)",
            "product_code": "CEMENT_PSC",
            "grade_code": "IS_455",
            "quantity": 600.0,
            "unit": "MT",
            "unit_price": 3150.0,
            "currency": "INR",
            "payment_terms": "20% Advance, 80% against delivery",
            "delivery_location": "Bhiwandi Central Warehousing, Maharashtra",
            "incoterm": "DDP",
            "delivery_timeline_days": 15,
            "governing_standards": ["IS 455"],
            "special_conditions": "Moisture-proof packing.",
        },
    }

    res = client.post("/converge-api/v1/proposals", json=create_payload)
    assert res.status_code == 201, res.text
    prop_data = res.json()
    prop_id = prop_data["id"]

    assert prop_data["status"] == "PENDING_REVIEW"
    assert prop_data["contacts_disclosed"] is False
    assert prop_data["disclosed_credentials"] is None

    # Verify contact credentials endpoint returns 403 before mutual approval
    res_contacts_blocked = client.get(f"/converge-api/v1/proposals/{prop_id}/contacts")
    assert res_contacts_blocked.status_code == 403

    # 2. Proposer attempts duplicate approval on V1 -> 409 Conflict
    res_dup = client.post(f"/converge-api/v1/proposals/{prop_id}/approve", json={"notes": "Duplicate"})
    assert res_dup.status_code == 409
    assert "already approved" in res_dup.json()["detail"].lower()

    # 3. Recipient approves V1 -> Mutual Consensus Achieved!
    client.cookies.set(SESSION_COOKIE_NAME, token_recipient)
    res_approve = client.post(f"/converge-api/v1/proposals/{prop_id}/approve", json={"notes": "Formally accepted terms."})
    assert res_approve.status_code == 200, res_approve.text
    approved_data = res_approve.json()

    assert approved_data["status"] == "MUTUALLY_APPROVED"
    assert approved_data["contacts_disclosed"] is True
    assert approved_data["disclosed_credentials"] is not None

    creds = approved_data["disclosed_credentials"]
    assert creds["user_id"] == str(user_proposer.id)
    assert creds["full_name"] == "Prakash Proposer"
    assert creds["email"] == "prop@infra.com"
    assert creds["phone_number"] == "+919876543211"
    assert creds["verification_receipt_hash"] is not None
    assert len(creds["verification_receipt_hash"]) == 64  # Valid SHA-256

    # 4. Recipient directly calls unlocked contacts endpoint
    res_contacts = client.get(f"/converge-api/v1/proposals/{prop_id}/contacts")
    assert res_contacts.status_code == 200
    assert res_contacts.json()["email"] == "prop@infra.com"

    # 5. Proposer inspects unlocked contact details for recipient
    client.cookies.set(SESSION_COOKIE_NAME, token_proposer)
    res_prop_view = client.get(f"/converge-api/v1/proposals/{prop_id}")
    assert res_prop_view.status_code == 200
    prop_creds = res_prop_view.json()["disclosed_credentials"]
    assert prop_creds["user_id"] == str(user_recipient.id)
    assert prop_creds["full_name"] == "Ramesh Recipient"
    assert prop_creds["email"] == "recip@build.com"


def test_revision_diff_calculation(client, sync_engine):
    """Verify field-by-field delta calculation between baseline V1 and counterproposal V2."""
    user_a, token_a = create_test_user(
        sync_engine, "appr_test_diff_a", "diff_a@test.com", "Anand Author", "+919876543212", "Anand Corp"
    )
    user_b, token_b = create_test_user(
        sync_engine, "appr_test_diff_b", "diff_b@test.com", "Bhavin Buyer", "+919123456782", "Bhavin Infra"
    )

    # 1. Author submits V1
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    payload_v1 = {
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "validity_days": 14,
        "revision": {
            "title": "Supply Offer: 500 MT Slag Cement",
            "proposal_type": "SUPPLY_CONTRACT",
            "product_name": "Portland Slag Cement (PSC)",
            "product_code": "CEMENT_PSC",
            "grade_code": "IS_455",
            "quantity": 500.0,
            "unit": "MT",
            "unit_price": 3400.0,
            "currency": "INR",
            "payment_terms": "20% Advance, 80% against delivery",
            "delivery_location": "Bhiwandi Central Warehousing",
            "incoterm": "EXW",
            "delivery_timeline_days": 30,
            "governing_standards": ["IS 455"],
            "special_conditions": "Standard shrink wrap.",
        },
    }
    res_v1 = client.post("/converge-api/v1/proposals", json=payload_v1)
    assert res_v1.status_code == 201
    prop_id = res_v1.json()["id"]

    # 2. Buyer counters with V2
    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    counter_payload = {
        "revision_summary": "Increased volume to 750 MT with volume discount to Rs 3250 and expedited 21 days lead time.",
        "revision": {
            "title": "Supply Offer: 750 MT Slag Cement (Discounted)",
            "proposal_type": "SUPPLY_CONTRACT",
            "product_name": "Portland Slag Cement (PSC)",
            "product_code": "CEMENT_PSC",
            "grade_code": "IS_455",
            "quantity": 750.0,
            "unit": "MT",
            "unit_price": 3250.0,
            "currency": "INR",
            "payment_terms": "15% Advance, 85% against delivery",
            "delivery_location": "Thane Logistics Park",
            "incoterm": "DDP",
            "delivery_timeline_days": 21,
            "governing_standards": ["IS 455"],
            "special_conditions": "Heavy duty palletized packing.",
        },
    }
    res_v2 = client.post(f"/converge-api/v1/proposals/{prop_id}/counter", json=counter_payload)
    assert res_v2.status_code == 200

    # 3. Request diff between V1 and V2
    res_diff = client.get(f"/converge-api/v1/proposals/{prop_id}/diff?from_rev=1&to_rev=2")
    assert res_diff.status_code == 200, res_diff.text
    diff = res_diff.json()

    assert diff["proposal_id"] == prop_id
    assert diff["from_revision_number"] == 1
    assert diff["to_revision_number"] == 2
    assert diff["has_quantity_change"] is True
    assert diff["has_price_change"] is True
    assert diff["has_timeline_change"] is True
    assert diff["has_delivery_change"] is True

    # Inspect individual field changes
    changes_map = {c["field"]: c for c in diff["changes"]}

    # Quantity changed from 500 to 750 (+250)
    qty_change = changes_map["quantity"]
    assert float(qty_change["old_value"]) == 500.0
    assert float(qty_change["new_value"]) == 750.0
    assert float(qty_change["numeric_delta"]) == 250.0
    assert "+250 MT" in qty_change["formatted_change"]

    # Unit price changed from 3400 to 3250 (-150)
    price_change = changes_map["unit_price"]
    assert float(price_change["old_value"]) == 3400.0
    assert float(price_change["new_value"]) == 3250.0
    assert float(price_change["numeric_delta"]) == -150.0
    assert "-₹ 150" in price_change["formatted_change"]

    # Timeline changed from 30 to 21 (-9)
    time_change = changes_map["delivery_timeline_days"]
    assert time_change["old_value"] == 30
    assert time_change["new_value"] == 21
    assert float(time_change["numeric_delta"]) == -9.0
    assert "-9 Days" in time_change["formatted_change"]

    # Delivery location changed
    assert changes_map["delivery_location"]["old_value"] == "Bhiwandi Central Warehousing"
    assert changes_map["delivery_location"]["new_value"] == "Thane Logistics Park"

    # Incoterm changed from EXW to DDP
    assert changes_map["incoterm"]["old_value"] == "EXW"
    assert changes_map["incoterm"]["new_value"] == "DDP"


def test_diff_idor_and_nonexistent_revision_boundaries(client, sync_engine):
    """Verify diff endpoint enforces participant boundary and valid revision numbers."""
    user_a, token_a = create_test_user(sync_engine, "appr_test_idor_a", "id_a@test.com", "Party A")
    user_b, _ = create_test_user(sync_engine, "appr_test_idor_b", "id_b@test.com", "Party B")
    user_c, token_c = create_test_user(sync_engine, "appr_test_idor_c", "id_c@test.com", "Intruder C")

    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    res_v1 = client.post("/converge-api/v1/proposals", json={
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "validity_days": 7,
        "revision": {
            "title": "Supply Agreement",
            "proposal_type": "SUPPLY_CONTRACT",
            "product_name": "Cement",
            "quantity": 100.0,
            "unit": "MT",
            "unit_price": 3000.0,
            "payment_terms": "Advance",
            "delivery_location": "Pune",
        },
    })
    prop_id = res_v1.json()["id"]

    # 1. Non-participant (User C) -> 404 Not Found
    client.cookies.set(SESSION_COOKIE_NAME, token_c)
    res_intruder = client.get(f"/converge-api/v1/proposals/{prop_id}/diff?from_rev=1&to_rev=2")
    assert res_intruder.status_code == 404

    # 2. Invalid revision number -> 404 Not Found
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    res_invalid_rev = client.get(f"/converge-api/v1/proposals/{prop_id}/diff?from_rev=1&to_rev=99")
    assert res_invalid_rev.status_code == 404
    assert "target revision v99 not found" in res_invalid_rev.json()["detail"].lower()
