"""Tests for Proposal Domain Models, Table Schemas, Constraints, and Foreign Key Cascades (Phase 7 - Subphase 2)."""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SASession
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import hash_password
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
from app.db.models.user import User
from app.schemas.proposal import (
    ProposalStatus as SchemaProposalStatus,
    CommercialRole as SchemaCommercialRole,
    ProposalType as SchemaProposalType,
    ApprovalAction as SchemaApprovalAction,
)

settings = get_settings()
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def sync_engine():
    """Create a synchronous SQLAlchemy engine for test fixture setup."""
    assert "test" in TEST_MIGRATION_URL.lower() or "5432" in TEST_MIGRATION_URL, (
        f"SAFETY GUARD: Invalid DB URL: {TEST_MIGRATION_URL}"
    )
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


def test_proposal_enum_parity():
    """Verify exact parity between DB model Enums and Pydantic Schema Enums."""
    assert set(e.value for e in ProposalStatus) == set(e.value for e in SchemaProposalStatus)
    assert set(e.value for e in CommercialRole) == set(e.value for e in SchemaCommercialRole)
    assert set(e.value for e in ProposalType) == set(e.value for e in SchemaProposalType)
    assert set(e.value for e in ApprovalAction) == set(e.value for e in SchemaApprovalAction)


def test_proposal_models_table_definitions():
    """Verify table names, schemas, and essential mapped columns."""
    assert Proposal.__tablename__ == "proposals"
    assert Proposal.__table_args__[-1]["schema"] == "business"

    assert ProposalRevision.__tablename__ == "proposal_revisions"
    assert ProposalRevision.__table_args__[-1]["schema"] == "business"

    assert ProposalApproval.__tablename__ == "proposal_approvals"
    assert ProposalApproval.__table_args__[-1]["schema"] == "business"

    assert ProposalContactDisclosure.__tablename__ == "proposal_contact_disclosures"
    assert ProposalContactDisclosure.__table_args__[-1]["schema"] == "business"


def test_proposal_repr_security_isolation():
    """Ensure __repr__ strings never disclose sensitive phone numbers, emails, or credentials."""
    dummy_id = uuid.uuid4()
    p = Proposal(
        id=dummy_id,
        proposer_id=uuid.uuid4(),
        recipient_id=uuid.uuid4(),
        proposer_role=CommercialRole.SUPPLIER,
        recipient_role=CommercialRole.BUYER,
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        status=ProposalStatus.PENDING_REVIEW,
        current_revision_number=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    repr_str = repr(p)
    assert str(dummy_id) in repr_str
    assert "SUPPLY_CONTRACT" in repr_str
    assert "PENDING_REVIEW" in repr_str
    assert "email" not in repr_str
    assert "phone" not in repr_str

    disclosure = ProposalContactDisclosure(
        id=dummy_id,
        proposal_id=dummy_id,
        user_id=uuid.uuid4(),
        disclosed_to_user_id=uuid.uuid4(),
        disclosed_credentials={"phone_number": "+919876543210", "email": "classified@corp.com"},
    )
    disclosure_repr = repr(disclosure)
    assert "+919876543210" not in disclosure_repr
    assert "classified@corp.com" not in disclosure_repr


def test_proposal_lifecycle_db_persistence_and_relationships(sync_engine):
    """Verify inserting and querying a complete Proposal with Revision, Approval, and Contact Disclosure."""
    with SASession(sync_engine) as session:
        # 1. Create two test delegates
        uid1 = uuid.uuid4()
        uid2 = uuid.uuid4()
        user_a = User(
            id=uid1,
            username=f"prop_user_a_{uid1.hex[:8]}",
            email=f"prop_a_{uid1.hex[:8]}@example.com",
            password_hash=hash_password("Secr3tP@ss!"),
            full_name="Alice Proposer",
            company_name="Alpha Clinker Ltd",
            phone_number="+919900011122",
        )
        user_b = User(
            id=uid2,
            username=f"prop_user_b_{uid2.hex[:8]}",
            email=f"prop_b_{uid2.hex[:8]}@example.com",
            password_hash=hash_password("Secr3tP@ss!"),
            full_name="Bob Buyer",
            company_name="Beta Construction Ltd",
            phone_number="+919900033344",
        )
        session.add_all([user_a, user_b])
        session.commit()

        # 2. Create proposal
        prop_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        proposal = Proposal(
            id=prop_id,
            proposer_id=user_a.id,
            recipient_id=user_b.id,
            proposer_role=CommercialRole.SUPPLIER,
            recipient_role=CommercialRole.BUYER,
            proposal_type=ProposalType.SUPPLY_CONTRACT,
            status=ProposalStatus.PENDING_REVIEW,
            current_revision_number=1,
            expires_at=now + timedelta(days=7),
        )
        session.add(proposal)
        session.commit()

        # 3. Create Revision V1
        rev_id = uuid.uuid4()
        revision_v1 = ProposalRevision(
            id=rev_id,
            proposal_id=proposal.id,
            revision_number=1,
            author_id=user_a.id,
            title="Supply of 500 MT Portland Pozzolana Cement",
            proposal_type=ProposalType.SUPPLY_CONTRACT,
            product_name="Portland Pozzolana Cement (PPC)",
            product_code="CEMENT_PPC",
            grade_code="IS_1489_PART_1",
            quantity=Decimal("500.0000"),
            unit="MT",
            unit_price=Decimal("3450.00"),
            currency="INR",
            total_value=Decimal("1725000.00"),
            payment_terms="30% Advance, 70% against BL/Delivery",
            delivery_location="Navi Mumbai Port Logistics Park",
            incoterm="DDP",
            delivery_timeline_days=21,
            governing_standards=["IS 1489 Part 1", "ASTM C595"],
            special_conditions="Moisture-proof poly-lined 50kg bags.",
            notes="Ready for dispatch within 5 days of advance confirmation.",
            revision_summary="Initial commercial contract offer",
        )
        session.add(revision_v1)
        session.commit()

        # 4. Create Author Approval for V1
        appr_id = uuid.uuid4()
        approval_a = ProposalApproval(
            id=appr_id,
            proposal_id=proposal.id,
            revision_id=revision_v1.id,
            user_id=user_a.id,
            action=ApprovalAction.APPROVED,
            notes="Author endorsement on initial submission.",
            ip_address="127.0.0.1",
        )
        session.add(approval_a)
        session.commit()

        # 5. Verify relationships navigation
        refreshed_p = session.get(Proposal, prop_id)
        assert refreshed_p is not None
        assert refreshed_p.proposer.id == user_a.id
        assert refreshed_p.recipient.id == user_b.id
        assert len(refreshed_p.revisions) == 1
        assert refreshed_p.revisions[0].id == rev_id
        assert refreshed_p.revisions[0].title == "Supply of 500 MT Portland Pozzolana Cement"
        assert refreshed_p.revisions[0].total_value == Decimal("1725000.00")
        assert len(refreshed_p.approvals) == 1
        assert refreshed_p.approvals[0].user_id == user_a.id
        assert refreshed_p.approvals[0].action == ApprovalAction.APPROVED

        # 6. Test mutual approval transition and contact disclosure record
        approval_b = ProposalApproval(
            id=uuid.uuid4(),
            proposal_id=proposal.id,
            revision_id=revision_v1.id,
            user_id=user_b.id,
            action=ApprovalAction.APPROVED,
            notes="Terms accepted without modifications.",
            ip_address="127.0.0.1",
        )
        refreshed_p.status = ProposalStatus.MUTUALLY_APPROVED
        refreshed_p.concluded_at = datetime.now(timezone.utc)

        disclosure = ProposalContactDisclosure(
            id=uuid.uuid4(),
            proposal_id=proposal.id,
            user_id=user_a.id,
            disclosed_to_user_id=user_b.id,
            disclosed_credentials={
                "full_name": user_a.full_name,
                "email": user_a.email,
                "phone_number": user_a.phone_number,
                "company_name": user_a.company_name,
            },
        )
        session.add_all([approval_b, disclosure])
        session.commit()

        refreshed_p2 = session.get(Proposal, prop_id)
        assert refreshed_p2.status == ProposalStatus.MUTUALLY_APPROVED
        assert len(refreshed_p2.approvals) == 2
        assert len(refreshed_p2.contact_disclosures) == 1
        assert refreshed_p2.contact_disclosures[0].disclosed_to_user_id == user_b.id
        assert refreshed_p2.contact_disclosures[0].disclosed_credentials["phone_number"] == "+919900011122"

        # Cleanup test entities
        session.delete(refreshed_p2)
        session.delete(user_a)
        session.delete(user_b)
        session.commit()


def test_proposal_distinct_parties_constraint(sync_engine):
    """Verify database check constraint ck_proposals_distinct_parties prevents self-proposals."""
    with SASession(sync_engine) as session:
        uid = uuid.uuid4()
        user = User(
            id=uid,
            username=f"self_prop_{uid.hex[:8]}",
            email=f"self_{uid.hex[:8]}@example.com",
            password_hash=hash_password("Secr3tP@ss!"),
            full_name="Self Proposer",
        )
        session.add(user)
        session.commit()

        invalid_proposal = Proposal(
            proposer_id=user.id,
            recipient_id=user.id,  # Invalid: proposer == recipient
            proposer_role=CommercialRole.BUYER,
            recipient_role=CommercialRole.SUPPLIER,
            proposal_type=ProposalType.PROCUREMENT_ORDER,
            status=ProposalStatus.PENDING_REVIEW,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(invalid_proposal)
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "ck_proposals_distinct_parties" in str(exc_info.value)
        session.rollback()

        session.delete(user)
        session.commit()
