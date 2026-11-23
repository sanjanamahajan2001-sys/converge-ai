"""Unit and integration tests for Administrative Oversight & Governance (Subphase 8)."""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models.conversation import Conversation, ConversationStatus
from app.db.models.proposal import (
    ApprovalAction,
    CommercialRole,
    Proposal,
    ProposalApproval,
    ProposalContactDisclosure,
    ProposalRevision,
    ProposalStatus,
    ProposalType,
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


def create_test_session(sync_engine, user_id: uuid.UUID) -> str:
    """Helper to create session token in DB."""
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    with Session(sync_engine) as session:
        user_session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
            last_accessed_at=datetime.now(timezone.utc),
            ip_address="127.0.0.1",
            user_agent="pytest-client",
        )
        session.add(user_session)
        session.commit()
    return raw_token


@pytest.fixture
def test_setup(sync_engine):
    """Seed test admin, 2 delegates, a conversation, and 2 proposals."""
    admin_id = uuid.uuid4()
    buyer_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    prop1_id = uuid.uuid4()
    prop2_id = uuid.uuid4()
    rev1_id = uuid.uuid4()
    rev2_id = uuid.uuid4()

    pwd_hash = hash_password("Secret123!")

    with Session(sync_engine) as session:
        # Cleanup any existing test data
        existing_user_ids = [
            u.id for u in session.query(User.id).filter(
                User.username.in_(["adm_prop_admin", "adm_prop_buyer", "adm_prop_supplier"])
            ).all()
        ]
        if existing_user_ids:
            session.query(ProposalContactDisclosure).delete()
            session.query(ProposalApproval).delete()
            session.query(ProposalRevision).delete()
            session.query(Proposal).delete()
            session.query(Conversation).filter(
                or_(
                    Conversation.initiator_id.in_(existing_user_ids),
                    Conversation.target_id.in_(existing_user_ids),
                )
            ).delete(synchronize_session=False)
            session.query(UserSession).filter(
                UserSession.user_id.in_(existing_user_ids)
            ).delete(synchronize_session=False)
            session.query(User).filter(
                User.id.in_(existing_user_ids)
            ).delete(synchronize_session=False)
            session.commit()

        # Seed Users
        admin = User(
            id=admin_id,
            username="adm_prop_admin",
            email="adm_prop_admin@converge.ai",
            password_hash=pwd_hash,
            full_name="Platform Overseer",
            is_active=True,
            is_admin=True,
        )
        buyer = User(
            id=buyer_id,
            username="adm_prop_buyer",
            email="adm_buyer@infra.com",
            password_hash=pwd_hash,
            phone_number="+91 98765 43210",
            full_name="Rajesh Verma",
            company_name="Verma EPC Infrastructure",
            is_active=True,
            is_admin=False,
        )
        supplier = User(
            id=supplier_id,
            username="adm_prop_supplier",
            email="adm_supplier@cement.com",
            password_hash=pwd_hash,
            phone_number="+91 91234 56789",
            full_name="Deepak Joshi",
            company_name="Deccan Cements Ltd",
            is_active=True,
            is_admin=False,
        )
        session.add_all([admin, buyer, supplier])
        session.commit()

        # Seed Conversation
        conv = Conversation(
            id=conv_id,
            initiator_id=buyer_id,
            target_id=supplier_id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.commit()

        # Seed Proposal 1: PENDING_REVIEW (Supply Contract)
        now = datetime.now(timezone.utc)
        prop1 = Proposal(
            id=prop1_id,
            conversation_id=conv_id,
            proposer_id=buyer_id,
            recipient_id=supplier_id,
            proposer_role=CommercialRole.BUYER,
            recipient_role=CommercialRole.SUPPLIER,
            proposal_type=ProposalType.SUPPLY_CONTRACT,
            status=ProposalStatus.PENDING_REVIEW,
            current_revision_number=1,
            expires_at=now + timedelta(days=7),
            created_at=now,
            updated_at=now,
        )
        session.add(prop1)

        rev1 = ProposalRevision(
            id=rev1_id,
            proposal_id=prop1_id,
            revision_number=1,
            author_id=buyer_id,
            title="Procurement Order: 1,000 MT Slag Cement",
            proposal_type=ProposalType.SUPPLY_CONTRACT,
            product_name="Ground Granulated Slag Cement",
            quantity=Decimal("1000"),
            unit="MT",
            unit_price=Decimal("4200.00"),
            currency="INR",
            total_value=Decimal("4200000.00"),
            payment_terms="20% Advance, 80% on Dispatch",
            delivery_location="Navi Mumbai Warehouse",
            incoterm="EXW",
            delivery_timeline_days=21,
            created_at=now,
        )
        session.add(rev1)

        app1 = ProposalApproval(
            id=uuid.uuid4(),
            proposal_id=prop1_id,
            revision_id=rev1_id,
            user_id=buyer_id,
            action=ApprovalAction.APPROVED,
            ip_address="192.168.1.100",
            created_at=now,
        )
        session.add(app1)

        # Seed Proposal 2: MUTUALLY_APPROVED
        prop2 = Proposal(
            id=prop2_id,
            conversation_id=conv_id,
            proposer_id=supplier_id,
            recipient_id=buyer_id,
            proposer_role=CommercialRole.SUPPLIER,
            recipient_role=CommercialRole.BUYER,
            proposal_type=ProposalType.SERVICE_MOU,
            status=ProposalStatus.MUTUALLY_APPROVED,
            current_revision_number=1,
            expires_at=now + timedelta(days=7),
            concluded_at=now,
            created_at=now - timedelta(days=1),
            updated_at=now,
        )
        session.add(prop2)

        rev2 = ProposalRevision(
            id=rev2_id,
            proposal_id=prop2_id,
            revision_number=1,
            author_id=supplier_id,
            title="Engineering Consultation Service Agreement",
            proposal_type=ProposalType.SERVICE_MOU,
            product_name="Structural Concrete Mix Design",
            quantity=Decimal("5"),
            unit="Sessions",
            unit_price=Decimal("50000.00"),
            currency="INR",
            total_value=Decimal("250000.00"),
            payment_terms="100% Post Completion",
            delivery_location="Pune Design Center",
            delivery_timeline_days=14,
            created_at=now - timedelta(days=1),
        )
        session.add(rev2)

        app2_1 = ProposalApproval(
            id=uuid.uuid4(),
            proposal_id=prop2_id,
            revision_id=rev2_id,
            user_id=supplier_id,
            action=ApprovalAction.APPROVED,
            ip_address="10.0.0.1",
            created_at=now - timedelta(days=1),
        )
        app2_2 = ProposalApproval(
            id=uuid.uuid4(),
            proposal_id=prop2_id,
            revision_id=rev2_id,
            user_id=buyer_id,
            action=ApprovalAction.APPROVED,
            ip_address="10.0.0.2",
            created_at=now,
        )
        session.add_all([app2_1, app2_2])

        # Disclosure record for prop2
        disclosure = ProposalContactDisclosure(
            id=uuid.uuid4(),
            proposal_id=prop2_id,
            user_id=supplier_id,
            disclosed_to_user_id=buyer_id,
            disclosed_credentials={
                "user_id": str(supplier_id),
                "full_name": "Deepak Joshi",
                "email": "adm_supplier@cement.com",
                "phone_number": "+91 91234 56789",
                "company_name": "Deccan Cements Ltd",
                "role": "SUPPLIER",
                "transaction_receipt_hash": "sha256:abc123def456auditreceipt",
            },
            disclosed_at=now,
        )
        session.add(disclosure)
        session.commit()

    admin_token = create_test_session(sync_engine, admin_id)
    buyer_token = create_test_session(sync_engine, buyer_id)

    yield {
        "admin_token": admin_token,
        "buyer_token": buyer_token,
        "admin_id": admin_id,
        "buyer_id": buyer_id,
        "supplier_id": supplier_id,
        "prop1_id": prop1_id,
        "prop2_id": prop2_id,
    }

    with Session(sync_engine) as session:
        session.query(ProposalContactDisclosure).delete()
        session.query(ProposalApproval).delete()
        session.query(ProposalRevision).delete()
        session.query(Proposal).delete()
        session.query(Conversation).filter(
            or_(
                Conversation.initiator_id.in_([admin_id, buyer_id, supplier_id]),
                Conversation.target_id.in_([admin_id, buyer_id, supplier_id]),
            )
        ).delete(synchronize_session=False)
        session.query(UserSession).filter(
            UserSession.user_id.in_([admin_id, buyer_id, supplier_id])
        ).delete(synchronize_session=False)
        session.query(User).filter(
            User.id.in_([admin_id, buyer_id, supplier_id])
        ).delete(synchronize_session=False)
        session.commit()


def test_admin_proposals_listing_and_counts(client, test_setup):
    """Admin retrieves full platform proposals queue with status counts."""
    cookies = {SESSION_COOKIE_NAME: test_setup["admin_token"]}
    resp = client.get("/converge-api/v1/admin/proposals", cookies=cookies, headers=CSRF_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "items" in data
    assert "status_counts" in data
    assert data["total"] >= 2
    assert data["status_counts"]["total"] >= 2
    assert data["status_counts"]["PENDING_REVIEW"] >= 1
    assert data["status_counts"]["MUTUALLY_APPROVED"] >= 1

    # Verify item attributes
    prop1 = next((p for p in data["items"] if p["id"] == str(test_setup["prop1_id"])), None)
    assert prop1 is not None
    assert prop1["proposer_name"] == "Rajesh Verma"
    assert prop1["recipient_name"] == "Deepak Joshi"
    assert prop1["status"] == "PENDING_REVIEW"
    assert prop1["total_revisions_count"] == 1
    assert prop1["approvals_count"] == 1


def test_admin_proposals_search_and_status_filtering(client, test_setup):
    """Admin filters proposals by status and searches across parties and product names."""
    cookies = {SESSION_COOKIE_NAME: test_setup["admin_token"]}

    # Filter by MUTUALLY_APPROVED
    resp = client.get("/converge-api/v1/admin/proposals?status=MUTUALLY_APPROVED", cookies=cookies, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["status"] == "MUTUALLY_APPROVED" for p in data["items"])
    assert any(p["id"] == str(test_setup["prop2_id"]) for p in data["items"])

    # Search by proposer name
    resp2 = client.get("/converge-api/v1/admin/proposals?search=Verma", cookies=cookies, headers=CSRF_HEADERS)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert any("Verma" in p["proposer_name"] or "Verma" in (p["proposer_company"] or "") for p in data2["items"])

    # Search by product name
    resp3 = client.get("/converge-api/v1/admin/proposals?search=Slag", cookies=cookies, headers=CSRF_HEADERS)
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert any(p["id"] == str(test_setup["prop1_id"]) for p in data3["items"])


def test_admin_proposal_forensic_detail_inspection(client, test_setup):
    """Admin inspects single proposal forensic audit sheet with IP addresses and disclosure receipts."""
    cookies = {SESSION_COOKIE_NAME: test_setup["admin_token"]}
    prop2_id = test_setup["prop2_id"]

    resp = client.get(f"/converge-api/v1/admin/proposals/{prop2_id}", cookies=cookies, headers=CSRF_HEADERS)
    assert resp.status_code == 200, resp.text
    detail = resp.json()

    assert detail["id"] == str(prop2_id)
    assert detail["status"] == "MUTUALLY_APPROVED"
    assert len(detail["approvals"]) == 2

    # Check non-repudiable audit: IP addresses captured
    ip_addresses = [a["ip_address"] for a in detail["approvals"]]
    assert "10.0.0.1" in ip_addresses
    assert "10.0.0.2" in ip_addresses

    # Check disclosed credentials receipt visible to admin
    assert detail["contacts_disclosed"] is True
    assert detail["disclosed_credentials"] is not None
    assert detail["disclosed_credentials"]["email"] == "adm_supplier@cement.com"
    assert detail["disclosed_credentials"]["phone_number"] == "+91 91234 56789"
    assert "sha256" in detail["disclosed_credentials"]["verification_receipt_hash"]


def test_admin_user_proposals_audit(client, test_setup):
    """Admin retrieves proposal portfolio for a specific attendee."""
    cookies = {SESSION_COOKIE_NAME: test_setup["admin_token"]}
    buyer_id = test_setup["buyer_id"]

    resp = client.get(f"/converge-api/v1/admin/users/{buyer_id}/proposals", cookies=cookies, headers=CSRF_HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Buyer is participant in both proposals
    assert data["total"] >= 2
    for p in data["items"]:
        assert p["proposer_id"] == str(buyer_id) or p["recipient_id"] == str(buyer_id)


def test_admin_proposals_security_gate_for_non_admin(client, test_setup):
    """Regular attendees are strictly denied access (403 Forbidden) to administrative governance endpoints."""
    regular_cookies = {SESSION_COOKIE_NAME: test_setup["buyer_token"]}

    resp = client.get("/converge-api/v1/admin/proposals", cookies=regular_cookies, headers=CSRF_HEADERS)
    assert resp.status_code == 403

    resp2 = client.get(f"/converge-api/v1/admin/proposals/{test_setup['prop1_id']}", cookies=regular_cookies, headers=CSRF_HEADERS)
    assert resp2.status_code == 403

    resp3 = client.get(f"/converge-api/v1/admin/users/{test_setup['buyer_id']}/proposals", cookies=regular_cookies, headers=CSRF_HEADERS)
    assert resp3.status_code == 403
