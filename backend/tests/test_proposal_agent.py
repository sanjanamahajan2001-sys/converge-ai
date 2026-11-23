"""Unit and Integration Tests for AI Proposal Drafting Engine & Profile Autofill (Phase 7 - Subphase 4)."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import SESSION_COOKIE_NAME, generate_session_token, hash_session_token
from app.db.models.business import (
    BusinessOffering,
    BusinessProfile,
    BusinessRequirement,
    ConversationBusinessContext,
)
from app.db.models.conversation import Conversation, ConversationStatus, Message, MessageSenderType
from app.db.models.proposal import CommercialRole, ProposalType
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
    """Clean up test proposal and business records before and after each test."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.proposal_contact_disclosures;")
            conn.exec_driver_sql("DELETE FROM business.proposal_approvals;")
            conn.exec_driver_sql("DELETE FROM business.proposal_revisions;")
            conn.exec_driver_sql("DELETE FROM business.proposals;")
            conn.exec_driver_sql("DELETE FROM business.context_revisions;")
            conn.exec_driver_sql("DELETE FROM business.conversation_business_contexts;")
            conn.exec_driver_sql("DELETE FROM business.business_offerings;")
            conn.exec_driver_sql("DELETE FROM business.business_requirements;")
            conn.exec_driver_sql("DELETE FROM business.business_profiles;")
            conn.exec_driver_sql("DELETE FROM core.messages;")
            conn.exec_driver_sql("DELETE FROM core.conversations;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users WHERE username LIKE 'draft_test_%%';")
            conn.commit()

    _clean()
    yield
    _clean()


def create_test_user(
    sync_engine,
    username: str,
    email: str,
    full_name: str,
    phone_number: str,
    company_name: str,
    is_supplier: bool = False,
    is_buyer: bool = False,
    is_distributor: bool = False,
    is_partner: bool = False,
    hq_city: str = "Mumbai",
) -> tuple[User, str]:
    """Helper to create user, business profile, and active session."""
    if not any([is_supplier, is_buyer, is_distributor, is_partner]):
        is_buyer = True

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)

    with SASession(sync_engine, expire_on_commit=False) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=full_name,
            company_name=company_name,
            job_title="Director of Procurement" if is_buyer else "VP Commercial",
            phone_number=phone_number,
            is_active=True,
        )
        session.add(user)
        session.flush()

        profile = BusinessProfile(
            user_id=user.id,
            company_name=company_name,
            is_supplier=is_supplier,
            is_buyer=is_buyer,
            is_distributor=is_distributor,
            is_partner=is_partner,
            allow_business_matching=True,
            hq_city=hq_city,
        )
        session.add(profile)

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc).replace(year=2030),
            last_accessed_at=datetime.now(timezone.utc),
        )
        session.add(user_session)
        session.commit()

    return user, raw_token


def test_draft_prefill_from_conversation_business_context(client, sync_engine):
    """Verify AI proposal draft is accurately extracted from ConversationBusinessContext snapshot."""
    user_supplier, token_supplier = create_test_user(
        sync_engine, "draft_test_supplier", "sup@alpha.com", "Sanjay Supplier", "+919876543210", "Alpha Cement Ltd", is_supplier=True
    )
    user_buyer, token_buyer = create_test_user(
        sync_engine, "draft_test_buyer", "buy@beta.com", "Bipin Buyer", "+919123456789", "Beta Infra Corp", is_buyer=True
    )

    # Create conversation and business context snapshot
    conv_id = uuid.uuid4()
    with SASession(sync_engine, expire_on_commit=False) as session:
        conv = Conversation(
            id=conv_id,
            initiator_id=user_buyer.id,
            target_id=user_supplier.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()

        biz_ctx = ConversationBusinessContext(
            conversation_id=conv_id,
            version=1,
            inquiry_type="RFQ_PRODUCT",
            product_name="Portland Slag Cement (PSC)",
            product_code="CEMENT_PSC",
            grade_code="IS_455",
            quantity=Decimal("750.0000"),
            unit="MT",
            delivery_location="Bhiwandi Central Warehousing, Maharashtra",
            timeline_days=18,
            target_price_indication=Decimal("3350.00"),
            inquiry_notes="50kg tamper-proof HDPE bags required.",
            snapshot_hash="dummy_hash_001",
        )
        session.add(biz_ctx)
        session.commit()

    # Call /proposals/draft as supplier
    client.cookies.set(SESSION_COOKIE_NAME, token_supplier)
    payload = {
        "conversation_id": str(conv_id),
        "recipient_id": str(user_buyer.id),
    }

    res = client.post("/converge-api/v1/proposals/draft", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["conversation_id"] == str(conv_id)
    assert data["recipient_id"] == str(user_buyer.id)
    assert data["proposer_role"] == "SUPPLIER"
    assert data["recipient_role"] == "BUYER"
    assert data["grounding_source"] == "CONTEXT_BRIEF"
    assert data["confidence_score"] >= 0.90

    rev = data["suggested_revision"]
    assert rev["product_name"] == "Portland Slag Cement (PSC)"
    assert float(rev["quantity"]) == 750.0
    assert rev["unit"] == "MT"
    assert float(rev["unit_price"]) == 3350.0
    assert float(rev["total_value"]) == 750.0 * 3350.0
    assert rev["delivery_location"] == "Bhiwandi Central Warehousing, Maharashtra"
    assert rev["delivery_timeline_days"] == 18
    assert "IS 455" in rev["governing_standards"]
    assert "50kg tamper-proof" in rev["special_conditions"]
    assert rev["proposal_type"] == "SUPPLY_CONTRACT"


def test_draft_prefill_from_catalog_offering_when_no_context(client, sync_engine):
    """Verify AI proposal draft falls back to active catalog offerings when frozen brief is absent."""
    user_supplier, token_supplier = create_test_user(
        sync_engine, "draft_test_off_sup", "off_sup@alpha.com", "Sunil Supplier", "+919876543211", "UltraPozz Tech", is_supplier=True
    )
    user_buyer, _ = create_test_user(
        sync_engine, "draft_test_off_buy", "off_buy@beta.com", "Bharat Buyer", "+919123456781", "MegaBuild Construction", is_buyer=True
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine, expire_on_commit=False) as session:
        conv = Conversation(
            id=conv_id,
            initiator_id=user_supplier.id,
            target_id=user_buyer.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)

        # Add active catalog offering to supplier's profile
        prof = session.query(BusinessProfile).filter_by(user_id=user_supplier.id).first()
        offering = BusinessOffering(
            business_profile_id=prof.id,
            custom_product_title="Processed Micro-Silica Slurry",
            minimum_order_quantity=Decimal("150.0000"),
            capacity_unit="MT",
            indicative_price_min=Decimal("4800.00"),
            indicative_price_max=Decimal("5200.00"),
            price_currency="INR",
            pricing_basis="FOR_DELIVERED",
            lead_time_days=14,
            geographic_coverage=["Navi Mumbai Industrial Area"],
            specifications_text="SiO2 content > 92%, bulk tanker delivery.",
        )
        session.add(offering)
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, token_supplier)
    payload = {
        "conversation_id": str(conv_id),
        "recipient_id": str(user_buyer.id),
    }

    res = client.post("/converge-api/v1/proposals/draft", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["grounding_source"] == "CATALOG_OFFERING"
    assert data["confidence_score"] >= 0.80

    rev = data["suggested_revision"]
    assert rev["product_name"] == "Processed Micro-Silica Slurry"
    assert float(rev["quantity"]) == 150.0
    assert rev["unit"] == "MT"
    assert float(rev["unit_price"]) == 4800.0
    assert rev["delivery_location"] == "Navi Mumbai Industrial Area"
    assert rev["delivery_timeline_days"] == 14
    assert rev["incoterm"] == "FOR_DELIVERED"
    assert "SiO2 content > 92%" in rev["special_conditions"]


def test_draft_prefill_from_dialogue_turns_synthesis(client, sync_engine):
    """Verify AI proposal draft extracts volume, price, and location from conversational messages."""
    user_a, token_a = create_test_user(
        sync_engine, "draft_test_chat_a", "chata@test.com", "Anil Aggarwal", "+919876543212", "Delta Infrastructure"
    )
    user_b, _ = create_test_user(
        sync_engine, "draft_test_chat_b", "chatb@test.com", "Bablu Builder", "+919123456782", "Apex Projects"
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine, expire_on_commit=False) as session:
        conv = Conversation(
            id=conv_id,
            initiator_id=user_a.id,
            target_id=user_b.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()

        # Add message turns with negotiated commercial terms
        msg1 = Message(
            conversation_id=conv_id,
            sender_id=user_a.id,
            sender_type=MessageSenderType.PARTICIPANT,
            turn_index=1,
            content="Can you supply 400 MT of Ready Mix Concrete for our project?",
        )
        msg2 = Message(
            conversation_id=conv_id,
            sender_id=user_b.id,
            sender_type=MessageSenderType.PARTICIPANT,
            turn_index=2,
            content="Yes, we can offer Rs 3850 per MT with delivery to Thane Industrial Park within 12 days.",
        )
        session.add_all([msg1, msg2])
        session.commit()

    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    payload = {
        "conversation_id": str(conv_id),
        "recipient_id": str(user_b.id),
    }

    res = client.post("/converge-api/v1/proposals/draft", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["grounding_source"] == "DIALOGUE_SYNTHESIS"
    assert data["confidence_score"] >= 0.70

    rev = data["suggested_revision"]
    assert rev["product_name"] == "Ready Mix Concrete"
    assert float(rev["quantity"]) == 400.0
    assert rev["unit"] == "MT"
    assert float(rev["unit_price"]) == 3850.0
    assert "Thane Industrial Park" in rev["delivery_location"]
    assert rev["delivery_timeline_days"] == 12


def test_draft_prefill_idor_and_security_boundaries(client, sync_engine):
    """Verify non-participants and invalid participants are strictly blocked."""
    user_a, token_a = create_test_user(
        sync_engine, "draft_test_sec_a", "sec_a@test.com", "User A", "+919876543213", "Company A"
    )
    user_b, _ = create_test_user(
        sync_engine, "draft_test_sec_b", "sec_b@test.com", "User B", "+919123456783", "Company B"
    )
    user_c, token_c = create_test_user(
        sync_engine, "draft_test_sec_c", "sec_c@test.com", "Intruder C", "+919123456784", "Company C"
    )

    conv_id = uuid.uuid4()
    with SASession(sync_engine, expire_on_commit=False) as session:
        conv = Conversation(
            id=conv_id,
            initiator_id=user_a.id,
            target_id=user_b.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.commit()

    # 1. Non-participant (User C) tries to draft from A & B's conversation -> 403 Forbidden
    client.cookies.set(SESSION_COOKIE_NAME, token_c)
    res = client.post("/converge-api/v1/proposals/draft", json={
        "conversation_id": str(conv_id),
        "recipient_id": str(user_b.id),
    })
    assert res.status_code == 403

    # 2. User A tries to draft to themselves -> 400 Bad Request
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    res = client.post("/converge-api/v1/proposals/draft", json={
        "conversation_id": str(conv_id),
        "recipient_id": str(user_a.id),
    })
    assert res.status_code == 400

    # 3. Non-existent conversation -> 404 Not Found
    res = client.post("/converge-api/v1/proposals/draft", json={
        "conversation_id": str(uuid.uuid4()),
        "recipient_id": str(user_b.id),
    })
    assert res.status_code == 404
