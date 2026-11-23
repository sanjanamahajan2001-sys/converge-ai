"""Contract, lifecycle, concurrency, IDOR, and contact disclosure tests for Proposal API (Phase 7 - Subphase 3)."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
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


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Refusing to run tests against non-test DB: {TEST_DB_URL}"
    )
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


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
def cleanup_proposals(sync_engine):
    """Clean up proposal and session test records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.proposal_contact_disclosures;")
            conn.exec_driver_sql("DELETE FROM business.proposal_approvals;")
            conn.exec_driver_sql("DELETE FROM business.proposal_revisions;")
            conn.exec_driver_sql("DELETE FROM business.proposals;")
            conn.exec_driver_sql(
                "DELETE FROM core.conversations WHERE initiator_id IN (SELECT id FROM core.users WHERE username LIKE 'prop_test_%%') OR target_id IN (SELECT id FROM core.users WHERE username LIKE 'prop_test_%%');"
            )
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users WHERE username LIKE 'prop_test_%%';")
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
) -> Tuple[User, str]:
    """Create a delegate user with active session."""
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


def test_create_proposal_success_and_contact_privacy_gating(client, sync_engine):
    """Verify proposal creation, computed total value, auto-approval, and zero contact leakage."""
    user_a, token_a = create_test_user(
        sync_engine, "prop_test_alice", "alice@alphacement.com", "Alice Agarwal", "+919876543210", "Alpha Cement"
    )
    user_b, token_b = create_test_user(
        sync_engine, "prop_test_bob", "bob@betainfra.com", "Bob Banerjee", "+919123456789", "Beta Infra"
    )

    client.cookies.set(SESSION_COOKIE_NAME, token_a)

    payload = {
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "validity_days": 7,
        "revision": {
            "title": "Supply Offer: 500 MT Slag Cement",
            "proposal_type": "SUPPLY_CONTRACT",
            "product_name": "Portland Slag Cement (PSC)",
            "product_code": "CEMENT_PSC",
            "grade_code": "IS_455",
            "quantity": 500.0,
            "unit": "MT",
            "unit_price": 3200.0,
            "currency": "INR",
            "payment_terms": "20% Advance, 80% against Delivery",
            "delivery_location": "Bhiwandi Central Warehousing, Maharashtra",
            "incoterm": "DDP",
            "delivery_timeline_days": 15,
            "governing_standards": ["IS 455"],
            "special_conditions": "Palletized shrink-wrapped delivery.",
            "notes": "Bulk discount included.",
        },
    }

    res = client.post("/converge-api/v1/proposals", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["status"] == "PENDING_REVIEW"
    assert data["current_revision_number"] == 1
    assert data["proposer"]["user_id"] == str(user_a.id)
    assert data["recipient"]["user_id"] == str(user_b.id)
    assert data["user_is_proposer"] is True
    assert data["requires_user_action"] is False

    # Check computed total value: 500 * 3200 = 1600000.00
    active_rev = data["active_revision"]
    assert active_rev["title"] == "Supply Offer: 500 MT Slag Cement"
    assert float(active_rev["total_value"]) == 1600000.0
    assert active_rev["author_id"] == str(user_a.id)

    # Check author auto-approval
    assert len(data["approvals"]) == 1
    assert data["approvals"][0]["user_id"] == str(user_a.id)
    assert data["approvals"][0]["action"] == "APPROVED"

    # ZERO CONTACT LEAKAGE: Status is PENDING_REVIEW, contact coordinates must be omitted
    assert data["contacts_disclosed"] is False
    assert data["disclosed_credentials"] is None

    # Recipient fetches the proposal
    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    res_b = client.get(f"/converge-api/v1/proposals/{data['id']}")
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["user_is_proposer"] is False
    assert data_b["requires_user_action"] is True
    assert data_b["contacts_disclosed"] is False
    assert data_b["disclosed_credentials"] is None


def test_create_proposal_self_and_duplicate_conflict(client, sync_engine):
    """Ensure delegate cannot propose to self and cannot create duplicate active proposals."""
    user_a, token_a = create_test_user(
        sync_engine, "prop_test_alice2", "alice2@alpha.com", "Alice Agarwal"
    )
    user_b, token_b = create_test_user(
        sync_engine, "prop_test_bob2", "bob2@beta.com", "Bob Banerjee"
    )

    client.cookies.set(SESSION_COOKIE_NAME, token_a)

    # 1. Propose to self
    self_payload = {
        "recipient_id": str(user_a.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "validity_days": 7,
        "revision": {
            "title": "Self deal",
            "product_name": "Cement",
            "quantity": 10.0,
            "unit": "MT",
            "payment_terms": "Advance",
            "delivery_location": "Mumbai",
        },
    }
    res_self = client.post("/converge-api/v1/proposals", json=self_payload)
    assert res_self.status_code == 400
    assert "yourself" in res_self.json()["detail"].lower()

    # 2. First valid proposal
    valid_payload = {
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "validity_days": 7,
        "revision": {
            "title": "Deal 1",
            "product_name": "Cement",
            "quantity": 100.0,
            "unit": "MT",
            "payment_terms": "100% Advance",
            "delivery_location": "Delhi",
        },
    }
    res1 = client.post("/converge-api/v1/proposals", json=valid_payload)
    assert res1.status_code == 201

    # 3. Duplicate active proposal between same pair
    res2 = client.post("/converge-api/v1/proposals", json=valid_payload)
    assert res2.status_code == 409
    assert "active proposal is already in negotiation" in res2.json()["detail"]


def test_proposals_listing_and_idor_protection(client, sync_engine):
    """Verify proposals directory filtering and strict IDOR boundary protection."""
    user_a, token_a = create_test_user(sync_engine, "prop_test_a3", "a3@corp.com", "User A")
    user_b, token_b = create_test_user(sync_engine, "prop_test_b3", "b3@corp.com", "User B")
    user_c, token_c = create_test_user(sync_engine, "prop_test_c3", "c3@corp.com", "User C")

    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    payload = {
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "revision": {
            "title": "Private Deal",
            "product_name": "Fly Ash",
            "quantity": 250.0,
            "unit": "MT",
            "payment_terms": "Immediate",
            "delivery_location": "Pune",
        },
    }
    create_res = client.post("/converge-api/v1/proposals", json=payload)
    assert create_res.status_code == 201
    prop_id = create_res.json()["id"]

    # User A lists proposals
    list_a = client.get("/converge-api/v1/proposals").json()
    assert len(list_a) == 1
    assert list_a[0]["id"] == prop_id

    # User C (outsider) lists proposals -> empty
    client.cookies.set(SESSION_COOKIE_NAME, token_c)
    list_c = client.get("/converge-api/v1/proposals").json()
    assert len(list_c) == 0

    # User C attempts IDOR access to User A & B's proposal
    res_idor = client.get(f"/converge-api/v1/proposals/{prop_id}")
    assert res_idor.status_code == 404
    assert res_idor.json()["detail"] == "Proposal not found."


def test_full_counterproposal_and_mutual_approval_lifecycle(client, sync_engine):
    """Verify Counterproposal (V1 -> V2) and Dual-Sided Approval triggering mutual contact unlock."""
    user_a, token_a = create_test_user(
        sync_engine, "prop_test_a4", "alice4@trade.com", "Alice Trade", "+919800000001", "Alice Industries"
    )
    user_b, token_b = create_test_user(
        sync_engine, "prop_test_b4", "bob4@build.com", "Bob Build", "+919800000002", "Bob Builders"
    )

    # 1. Alice creates Proposal V1: 100 MT @ ₹4000
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    create_res = client.post("/converge-api/v1/proposals", json={
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "revision": {
            "title": "100 MT Ready Mix Concrete",
            "product_name": "RMC M30 Grade",
            "quantity": 100.0,
            "unit": "CUM",
            "unit_price": 4000.0,
            "payment_terms": "50% Advance, 50% on Delivery",
            "delivery_location": "Bandra Kurla Complex, Mumbai",
            "delivery_timeline_days": 10,
        },
    })
    assert create_res.status_code == 201
    prop_id = create_res.json()["id"]

    # 2. Bob counters with V2: 150 MT @ ₹3700
    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    counter_payload = {
        "revision_summary": "Volume increased to 150 CUM with discounted rate of ₹3700.",
        "revision": {
            "title": "150 MT Ready Mix Concrete (Counter)",
            "proposal_type": "SUPPLY_CONTRACT",
            "product_name": "RMC M30 Grade",
            "quantity": 150.0,
            "unit": "CUM",
            "unit_price": 3700.0,
            "payment_terms": "30% Advance, 70% against Site Batch Slip",
            "delivery_location": "Bandra Kurla Complex, Mumbai",
            "delivery_timeline_days": 12,
        },
    }
    counter_res = client.post(f"/converge-api/v1/proposals/{prop_id}/counter", json=counter_payload)
    assert counter_res.status_code == 200
    counter_data = counter_res.json()

    assert counter_data["status"] == "REVISED"
    assert counter_data["current_revision_number"] == 2
    assert len(counter_data["revisions"]) == 2
    assert counter_data["active_revision"]["revision_number"] == 2
    assert float(counter_data["active_revision"]["total_value"]) == 555000.0
    assert counter_data["active_revision"]["author_id"] == str(user_b.id)
    assert counter_data["contacts_disclosed"] is False

    # 3. Contacts still locked before Alice approves V2
    contacts_locked_res = client.get(f"/converge-api/v1/proposals/{prop_id}/contacts")
    assert contacts_locked_res.status_code == 403

    # 4. Alice approves V2 -> triggers MUTUAL APPROVAL!
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    approve_res = client.post(f"/converge-api/v1/proposals/{prop_id}/approve", json={"notes": "Agreed to ₹3700/CUM."})
    assert approve_res.status_code == 200
    final_data = approve_res.json()

    assert final_data["status"] == "MUTUALLY_APPROVED"
    assert final_data["concluded_at"] is not None
    assert final_data["contacts_disclosed"] is True

    # Alice sees Bob's verified contact credentials
    alice_view_creds = final_data["disclosed_credentials"]
    assert alice_view_creds is not None
    assert alice_view_creds["full_name"] == "Bob Build"
    assert alice_view_creds["email"] == "bob4@build.com"
    assert alice_view_creds["phone_number"] == "+919800000002"

    # Bob sees Alice's verified contact credentials
    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    bob_contacts_res = client.get(f"/converge-api/v1/proposals/{prop_id}/contacts")
    assert bob_contacts_res.status_code == 200
    bob_view_creds = bob_contacts_res.json()
    assert bob_view_creds["full_name"] == "Alice Trade"
    assert bob_view_creds["email"] == "alice4@trade.com"
    assert bob_view_creds["phone_number"] == "+919800000001"


def test_reject_and_withdraw_endpoints(client, sync_engine):
    """Verify proposal rejection and author withdrawal behaviors."""
    user_a, token_a = create_test_user(sync_engine, "prop_test_a5", "a5@test.com", "Alice Five")
    user_b, token_b = create_test_user(sync_engine, "prop_test_b5", "b5@test.com", "Bob Five")

    # 1. Alice creates proposal, Bob rejects
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    p1 = client.post("/converge-api/v1/proposals", json={
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "revision": {"title": "Deal to Reject", "product_name": "Sand", "quantity": 10.0, "unit": "TONS", "payment_terms": "Cash", "delivery_location": "Goa"},
    }).json()

    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    reject_res = client.post(f"/converge-api/v1/proposals/{p1['id']}/reject", json={"reason": "Material specs do not match project needs."})
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"
    assert reject_res.json()["rejection_reason"] == "Material specs do not match project needs."

    # 2. Alice creates second proposal and withdraws before Bob acts
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    p2 = client.post("/converge-api/v1/proposals", json={
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "revision": {"title": "Deal to Withdraw", "product_name": "Aggregates", "quantity": 20.0, "unit": "TONS", "payment_terms": "Cash", "delivery_location": "Pune"},
    }).json()

    # Bob cannot withdraw Alice's offer (403)
    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    bob_withdraw = client.post(f"/converge-api/v1/proposals/{p2['id']}/withdraw")
    assert bob_withdraw.status_code == 403

    # Alice withdraws her own offer (200)
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    alice_withdraw = client.post(f"/converge-api/v1/proposals/{p2['id']}/withdraw")
    assert alice_withdraw.status_code == 200
    assert alice_withdraw.json()["status"] == "WITHDRAWN"


def test_proposal_conversation_filtering_and_realtime_events(client, sync_engine):
    """Verify proposal listing filtered by conversation_id (Subphase 7)."""
    user_a, token_a = create_test_user(sync_engine, "prop_test_a6", "a6@test.com", "Alice Six")
    user_b, token_b = create_test_user(sync_engine, "prop_test_b6", "b6@test.com", "Bob Six")
    user_c, token_c = create_test_user(sync_engine, "prop_test_c6", "c6@test.com", "Charlie Six")

    with SASession(sync_engine) as session:
        c1 = Conversation(
            initiator_id=user_a.id,
            target_id=user_b.id,
            status=ConversationStatus.ACTIVE,
            match_score=0.9,
        )
        c2 = Conversation(
            initiator_id=user_a.id,
            target_id=user_c.id,
            status=ConversationStatus.ACTIVE,
            match_score=0.85,
        )
        session.add_all([c1, c2])
        session.commit()
        session.refresh(c1)
        session.refresh(c2)
        target_conv_id = str(c1.id)
        other_conv_id = str(c2.id)

    client.cookies.set(SESSION_COOKIE_NAME, token_a)

    # 1. Proposal with target_conv_id
    p1_res = client.post("/converge-api/v1/proposals", json={
        "conversation_id": target_conv_id,
        "recipient_id": str(user_b.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "revision": {
            "title": "Target Conversation Deal",
            "product_name": "Bitumen VG-30",
            "quantity": 100.0,
            "unit": "MT",
            "payment_terms": "100% LC",
            "delivery_location": "JNPT Port",
        },
    })
    assert p1_res.status_code == 201

    # 2. Proposal with other_conv_id
    p2_res = client.post("/converge-api/v1/proposals", json={
        "conversation_id": other_conv_id,
        "recipient_id": str(user_c.id),
        "proposer_role": "SUPPLIER",
        "recipient_role": "BUYER",
        "revision": {
            "title": "Other Conversation Deal",
            "product_name": "Crushed Stone",
            "quantity": 500.0,
            "unit": "MT",
            "payment_terms": "Cash on Delivery",
            "delivery_location": "Nagpur",
        },
    })
    assert p2_res.status_code == 201

    # Filter by target_conv_id
    res_target = client.get(f"/converge-api/v1/proposals?conversation_id={target_conv_id}")
    assert res_target.status_code == 200
    items_target = res_target.json()
    assert len(items_target) == 1
    assert items_target[0]["product_name"] == "Bitumen VG-30"
    assert items_target[0]["conversation_id"] == target_conv_id

    # Filter by non-existent conversation_id
    empty_conv = str(uuid.uuid4())
    res_empty = client.get(f"/converge-api/v1/proposals?conversation_id={empty_conv}")
    assert res_empty.status_code == 200
    assert len(res_empty.json()) == 0
