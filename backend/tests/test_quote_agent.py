"""Unit & integration tests for AI Agent Dialogue Ask Synthesis & Broadcast (Quote Subphase 4)."""

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
from app.db.models.business import ConversationBusinessContext
from app.db.models.conversation import Conversation, ConversationStatus, Message, MessageSenderType
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
def cleanup_agent_quotes(sync_engine):
    """Clean up records created during agent tests."""
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.quote_email_dispatches;")
            conn.exec_driver_sql("DELETE FROM business.quote_vendor_matches;")
            conn.exec_driver_sql("DELETE FROM business.quote_requests;")
            conn.exec_driver_sql("DELETE FROM business.conversation_business_contexts;")
            conn.exec_driver_sql("DELETE FROM core.messages;")
            conn.exec_driver_sql("DELETE FROM core.conversations;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users WHERE username LIKE 'quote_agent_%%';")
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
    """Create delegate user with active session."""
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


def test_prefill_ask_from_conversation_business_context(client, sync_engine):
    """Verify prefilling an ask directly from a frozen ConversationBusinessContext."""
    customer, token_c = create_test_user(
        sync_engine, "quote_agent_c1", "cust1@infra.com", "Sanjana Mahajan", "InfraTech EPC"
    )
    supplier, token_s = create_test_user(
        sync_engine, "quote_agent_s1", "supp1@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    conv_id = None
    with SASession(sync_engine) as session:
        conv = Conversation(
            initiator_id=customer.id,
            target_id=supplier.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()

        ctx = ConversationBusinessContext(
            conversation_id=conv.id,
            inquiry_type="RFQ_PRODUCT",
            product_name="Limestone Calcined Clay Cement (LC3)",
            product_code="CALCINED_CLAY_LC3",
            grade_code="GRADE_A",
            quantity=Decimal("1500.0000"),
            unit="MT",
            delivery_location="Pune Industrial Yard, Maharashtra",
            timeline_days=25,
            target_price_indication=Decimal("3400.00"),
            urgency="IMMEDIATE",
            inquiry_notes="Required for sustainable expressway pavement.",
            snapshot_hash="hash123456",
        )
        session.add(ctx)
        session.commit()
        conv_id = str(conv.id)

    client.cookies.set(SESSION_COOKIE_NAME, token_c)
    res = client.get(f"/converge-api/v1/quotes/asks/prefill-from-conversation/{conv_id}")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["product_name"] == "Limestone Calcined Clay Cement (LC3)"
    assert data["product_code"] == "CALCINED_CLAY_LC3"
    assert float(data["quantity"]) == 1500.0
    assert data["quantity_unit"] == "MT"
    assert data["delivery_location"] == "Pune Industrial Yard, Maharashtra"
    assert data["timeline_days"] == 25
    assert data["urgency"] == "IMMEDIATE"


def test_prefill_ask_from_dialogue_fallback(client, sync_engine):
    """Verify synthesizing an ask from dialogue turn messages when no frozen brief exists."""
    customer, token_c = create_test_user(
        sync_engine, "quote_agent_c2", "cust2@infra.com", "Sanjana Mahajan", "InfraTech EPC"
    )
    supplier, token_s = create_test_user(
        sync_engine, "quote_agent_s2", "supp2@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    conv_id = None
    with SASession(sync_engine) as session:
        conv = Conversation(
            initiator_id=customer.id,
            target_id=supplier.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()

        msg = Message(
            conversation_id=conv.id,
            sender_id=customer.id,
            sender_type=MessageSenderType.PARTICIPANT,
            turn_index=0,
            content="We need 800 MT of Low-Carbon Clinker delivered to Mumbai Port.",
        )
        session.add(msg)
        session.commit()
        conv_id = str(conv.id)

    client.cookies.set(SESSION_COOKIE_NAME, token_c)
    res = client.get(f"/converge-api/v1/quotes/asks/prefill-from-conversation/{conv_id}")
    assert res.status_code == 200, res.text
    data = res.json()

    assert "Clinker" in data["product_name"]
    assert float(data["quantity"]) == 800.0


def test_broadcast_ask_from_conversation_end_to_end(client, sync_engine):
    """Verify 1-click broadcast from conversation matching vendors and publishing events."""
    customer, token_c = create_test_user(
        sync_engine, "quote_agent_c3", "cust3@infra.com", "Sanjana Mahajan", "InfraTech EPC"
    )
    supplier, token_s = create_test_user(
        sync_engine, "quote_agent_s3", "supp3@deccan.com", "Maahi Sharma", "Deccan Cement"
    )

    conv_id = None
    with SASession(sync_engine) as session:
        conv = Conversation(
            initiator_id=customer.id,
            target_id=supplier.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.flush()

        ctx = ConversationBusinessContext(
            conversation_id=conv.id,
            inquiry_type="RFQ_PRODUCT",
            product_name="Limestone Calcined Clay Cement (LC3)",
            quantity=Decimal("1000.0000"),
            unit="MT",
            delivery_location="Pune Industrial Yard",
            timeline_days=21,
            urgency="PLANNED",
            snapshot_hash="hash987654",
        )
        session.add(ctx)
        session.commit()
        conv_id = str(conv.id)

    client.cookies.set(SESSION_COOKIE_NAME, token_c)
    res = client.post(f"/converge-api/v1/quotes/asks/broadcast-from-conversation/{conv_id}")
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["product_name"] == "Limestone Calcined Clay Cement (LC3)"
    assert data["status"] == "MATCHED"

    # Verify DB records
    with SASession(sync_engine) as session:
        ask = session.query(QuoteRequest).filter_by(id=uuid.UUID(data["id"])).first()
        assert ask is not None
        assert len(ask.matches) > 0


def test_prefill_and_broadcast_idor_security(client, sync_engine):
    """Verify unauthorized third party cannot prefill or broadcast from an un-involved conversation."""
    customer, token_c = create_test_user(
        sync_engine, "quote_agent_c4", "cust4@infra.com", "Sanjana Mahajan", "InfraTech EPC"
    )
    supplier, token_s = create_test_user(
        sync_engine, "quote_agent_s4", "supp4@deccan.com", "Maahi Sharma", "Deccan Cement"
    )
    intruder, token_i = create_test_user(
        sync_engine, "quote_agent_intruder", "intruder@hack.com", "Intruder Attendee", "Spy Corp"
    )

    conv_id = None
    with SASession(sync_engine) as session:
        conv = Conversation(
            initiator_id=customer.id,
            target_id=supplier.id,
            status=ConversationStatus.ACTIVE,
        )
        session.add(conv)
        session.commit()
        conv_id = str(conv.id)

    client.cookies.set(SESSION_COOKIE_NAME, token_i)
    res_prefill = client.get(f"/converge-api/v1/quotes/asks/prefill-from-conversation/{conv_id}")
    assert res_prefill.status_code == 404

    res_broadcast = client.post(f"/converge-api/v1/quotes/asks/broadcast-from-conversation/{conv_id}")
    assert res_broadcast.status_code == 404
