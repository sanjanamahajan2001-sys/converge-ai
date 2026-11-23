"""Unit tests for Subphase 1: Proposal Data Contracts, Schemas & Validation.

Verifies:
1. Enum integrity (ProposalStatus, CommercialRole, ProposalType, ApprovalAction).
2. Computed total_value logic on ProposalRevisionBase.
3. Strict zero-leakage contact redaction invariant on ProposalDetailResponse.
4. Validation constraints on create, counter, approval, and rejection payloads.
5. Administrative governance schemas.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.proposal import (
    AdminProposalFilter,
    AdminProposalListItem,
    AdminProposalListResponse,
    ApprovalAction,
    CommercialRole,
    CounterProposalRequest,
    DisclosedContactCredentials,
    ProposalApprovalRecord,
    ProposalApprovalRequest,
    ProposalCreateRequest,
    ProposalDetailResponse,
    ProposalDraftPrefillRequest,
    ProposalDraftPrefillResponse,
    ProposalListItem,
    ProposalPartySummary,
    ProposalRejectionRequest,
    ProposalRevisionBase,
    ProposalRevisionCreate,
    ProposalRevisionResponse,
    ProposalStatus,
    ProposalType,
)


def test_proposal_enums():
    """Verify all lifecycle, commercial role, and agreement enums."""
    assert ProposalStatus.DRAFT.value == "DRAFT"
    assert ProposalStatus.PENDING_REVIEW.value == "PENDING_REVIEW"
    assert ProposalStatus.MUTUALLY_APPROVED.value == "MUTUALLY_APPROVED"
    assert ProposalStatus.REJECTED.value == "REJECTED"
    assert ProposalStatus.REVISED.value == "REVISED"
    assert ProposalStatus.WITHDRAWN.value == "WITHDRAWN"
    assert ProposalStatus.EXPIRED.value == "EXPIRED"

    assert CommercialRole.BUYER.value == "BUYER"
    assert CommercialRole.SUPPLIER.value == "SUPPLIER"
    assert CommercialRole.VENDOR.value == "VENDOR"
    assert CommercialRole.DISTRIBUTOR.value == "DISTRIBUTOR"
    assert CommercialRole.PARTNER.value == "PARTNER"

    assert ProposalType.SUPPLY_CONTRACT.value == "SUPPLY_CONTRACT"
    assert ProposalType.PROCUREMENT_ORDER.value == "PROCUREMENT_ORDER"
    assert ProposalType.DISTRIBUTION_AGREEMENT.value == "DISTRIBUTION_AGREEMENT"
    assert ProposalType.SERVICE_MOU.value == "SERVICE_MOU"
    assert ProposalType.STRATEGIC_PARTNERSHIP.value == "STRATEGIC_PARTNERSHIP"

    assert ApprovalAction.APPROVED.value == "APPROVED"
    assert ApprovalAction.REJECTED.value == "REJECTED"
    assert ApprovalAction.WITHDRAWN.value == "WITHDRAWN"


def test_proposal_revision_computed_total_value():
    """Verify automatic calculation of total_value when unit_price and quantity are given."""
    rev = ProposalRevisionCreate(
        title="500 MT GGBS Supply Contract",
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        product_name="Ground Granulated Blast Furnace Slag",
        quantity=Decimal("500"),
        unit="MT",
        unit_price=Decimal("4200.50"),
        payment_terms="30% Advance, 70% against BL",
        delivery_location="Pune, Maharashtra",
        incoterm="FOB",
        delivery_timeline_days=21,
    )
    # 500 * 4200.50 = 2100250.00
    assert rev.total_value == Decimal("2100250.00")
    assert rev.currency == "INR"


def test_proposal_revision_explicit_total_value_preserved():
    """Verify explicit total_value is not overridden if provided."""
    rev = ProposalRevisionCreate(
        title="Custom Lump-Sum Engineering Contract",
        proposal_type=ProposalType.SERVICE_MOU,
        product_name="Kiln Thermal Efficiency Audit",
        quantity=Decimal("1"),
        unit="Service",
        unit_price=Decimal("100000"),
        total_value=Decimal("95000"),  # negotiated lump-sum discount
        payment_terms="100% on completion",
        delivery_location="Nagpur Plant",
    )
    assert rev.total_value == Decimal("95000")


def test_proposal_revision_validation_failures():
    """Verify validation boundaries: quantity <= 0, empty title, invalid days."""
    # Negative quantity
    with pytest.raises(ValidationError):
        ProposalRevisionCreate(
            title="Invalid",
            product_name="Clinker",
            quantity=Decimal("-10"),
            unit="MT",
            payment_terms="Immediate",
            delivery_location="Mumbai",
        )

    # Title too short
    with pytest.raises(ValidationError):
        ProposalRevisionCreate(
            title="A",
            product_name="Clinker",
            quantity=Decimal("10"),
            unit="MT",
            payment_terms="Immediate",
            delivery_location="Mumbai",
        )

    # Delivery timeline out of range (> 730 days)
    with pytest.raises(ValidationError):
        ProposalRevisionCreate(
            title="Valid Title",
            product_name="Clinker",
            quantity=Decimal("10"),
            unit="MT",
            payment_terms="Immediate",
            delivery_location="Mumbai",
            delivery_timeline_days=1000,
        )


def test_contact_redaction_invariant_non_approved_status():
    """CRITICAL SECURITY TEST:
    Verify ProposalDetailResponse strictly wipes out contacts_disclosed and
    disclosed_credentials whenever status is NOT MUTUALLY_APPROVED.
    """
    proposer_id = uuid4()
    recipient_id = uuid4()
    proposal_id = uuid4()
    revision_id = uuid4()
    now = datetime.now(timezone.utc)

    # Attempt to inject disclosed credentials on a PENDING_REVIEW proposal
    fake_credentials = DisclosedContactCredentials(
        user_id=recipient_id,
        full_name="Vikram Singhania",
        company_name="Deccan Clinker",
        email="vikram@deccanclinker.com",
        phone_number="+91 98765 43210",
        disclosed_at=now,
    )

    active_rev = ProposalRevisionResponse(
        id=revision_id,
        proposal_id=proposal_id,
        revision_number=1,
        author_id=proposer_id,
        title="500 MT Supply",
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        product_name="Clinker",
        quantity=Decimal("500"),
        unit="MT",
        payment_terms="Advance",
        delivery_location="Surat",
        delivery_timeline_days=30,
        created_at=now,
    )

    # Status is PENDING_REVIEW -> MUST REDACT
    detail = ProposalDetailResponse(
        id=proposal_id,
        proposer=ProposalPartySummary(
            user_id=proposer_id,
            full_name="Mahajan Sanjana",
            role=CommercialRole.BUYER,
        ),
        recipient=ProposalPartySummary(
            user_id=recipient_id,
            full_name="Vikram Singhania",
            role=CommercialRole.SUPPLIER,
        ),
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        status=ProposalStatus.PENDING_REVIEW,
        current_revision_number=1,
        active_revision=active_rev,
        revisions=[active_rev],
        approvals=[],
        expires_at=now,
        created_at=now,
        updated_at=now,
        contacts_disclosed=True,  # Attempting to pass True
        disclosed_credentials=fake_credentials,  # Attempting to pass leaked credentials
    )

    # INVARIANT CHECK: Forced to False and None
    assert detail.contacts_disclosed is False
    assert detail.disclosed_credentials is None

    # Status is REVISED -> MUST REDACT
    detail_revised = detail.model_copy(update={"status": ProposalStatus.REVISED, "contacts_disclosed": True, "disclosed_credentials": fake_credentials})
    # Re-validate via constructor
    detail_revised_validated = ProposalDetailResponse.model_validate(detail_revised.model_dump())
    assert detail_revised_validated.contacts_disclosed is False
    assert detail_revised_validated.disclosed_credentials is None

    # Status is REJECTED -> MUST REDACT
    detail_rejected = ProposalDetailResponse.model_validate(detail.model_copy(update={"status": ProposalStatus.REJECTED}).model_dump())
    assert detail_rejected.contacts_disclosed is False
    assert detail_rejected.disclosed_credentials is None


def test_contact_disclosure_permitted_on_mutually_approved():
    """Verify ProposalDetailResponse preserves disclosed credentials when status IS MUTUALLY_APPROVED."""
    proposer_id = uuid4()
    recipient_id = uuid4()
    proposal_id = uuid4()
    revision_id = uuid4()
    now = datetime.now(timezone.utc)

    valid_credentials = DisclosedContactCredentials(
        user_id=recipient_id,
        full_name="Vikram Singhania",
        company_name="Deccan Clinker & Mineral Feedstocks Ltd",
        email="vikram@deccanclinker.com",
        phone_number="+91 98765 43210",
        hq_city="Hyderabad",
        corporate_website="https://deccanclinker.com",
        disclosed_at=now,
    )

    active_rev = ProposalRevisionResponse(
        id=revision_id,
        proposal_id=proposal_id,
        revision_number=1,
        author_id=proposer_id,
        title="500 MT Supply",
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        product_name="Clinker",
        quantity=Decimal("500"),
        unit="MT",
        payment_terms="Advance",
        delivery_location="Surat",
        delivery_timeline_days=30,
        created_at=now,
    )

    detail_approved = ProposalDetailResponse(
        id=proposal_id,
        proposer=ProposalPartySummary(
            user_id=proposer_id,
            full_name="Mahajan Sanjana",
            role=CommercialRole.BUYER,
        ),
        recipient=ProposalPartySummary(
            user_id=recipient_id,
            full_name="Vikram Singhania",
            role=CommercialRole.SUPPLIER,
        ),
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        status=ProposalStatus.MUTUALLY_APPROVED,
        current_revision_number=1,
        active_revision=active_rev,
        revisions=[active_rev],
        approvals=[],
        expires_at=now,
        created_at=now,
        updated_at=now,
        concluded_at=now,
        contacts_disclosed=True,
        disclosed_credentials=valid_credentials,
    )

    # Preserved when MUTUALLY_APPROVED
    assert detail_approved.contacts_disclosed is True
    assert detail_approved.disclosed_credentials is not None
    assert detail_approved.disclosed_credentials.email == "vikram@deccanclinker.com"
    assert detail_approved.disclosed_credentials.phone_number == "+91 98765 43210"


def test_proposal_lifecycle_request_payloads():
    """Verify Create, Counter, Approve, and Reject payload validation."""
    recipient_id = uuid4()
    rev_create = ProposalRevisionCreate(
        title="Bulk Pozzolana Clinker Supply",
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        product_name="Pozzolana Clinker",
        quantity=Decimal("1200"),
        unit="MT",
        unit_price=Decimal("3800"),
        payment_terms="100% LC at sight",
        delivery_location="JNPT Port, Navi Mumbai",
    )

    # 1. ProposalCreateRequest
    create_req = ProposalCreateRequest(
        recipient_id=recipient_id,
        proposer_role=CommercialRole.SUPPLIER,
        recipient_role=CommercialRole.BUYER,
        validity_days=14,
        revision=rev_create,
    )
    assert create_req.validity_days == 14
    assert create_req.revision.total_value == Decimal("4560000.00")

    # 2. CounterProposalRequest
    counter_req = CounterProposalRequest(
        revision_summary="Adjusted delivery location to JNPT Port and revised unit price to 3750/MT.",
        revision=rev_create.model_copy(update={"unit_price": Decimal("3750")}),
    )
    assert "Adjusted delivery" in counter_req.revision_summary

    # Summary too short (< 5 chars)
    with pytest.raises(ValidationError):
        CounterProposalRequest(
            revision_summary="No",
            revision=rev_create,
        )

    # 3. ProposalApprovalRequest
    appr_req = ProposalApprovalRequest(notes="Approved on behalf of InfraTech EPC procurement committee.")
    assert appr_req.notes is not None

    # 4. ProposalRejectionRequest
    rej_req = ProposalRejectionRequest(reason="Price exceeds regional allocation benchmark by 12%.")
    assert "exceeds" in rej_req.reason

    # Rejection reason too short (< 5 chars)
    with pytest.raises(ValidationError):
        ProposalRejectionRequest(reason="No")


def test_admin_proposal_governance_schemas():
    """Verify Admin filtering and paginated collection DTOs."""
    filter_dto = AdminProposalFilter(
        status=ProposalStatus.PENDING_REVIEW,
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        search="Deccan",
        page=2,
        page_size=25,
    )
    assert filter_dto.page == 2
    assert filter_dto.page_size == 25

    now = datetime.now(timezone.utc)
    item = AdminProposalListItem(
        id=uuid4(),
        proposer_id=uuid4(),
        proposer_name="Mahajan Sanjana",
        proposer_company="InfraTech EPC",
        proposer_role=CommercialRole.BUYER,
        recipient_id=uuid4(),
        recipient_name="Vikram Singhania",
        recipient_company="Deccan Clinker",
        recipient_role=CommercialRole.SUPPLIER,
        proposal_type=ProposalType.SUPPLY_CONTRACT,
        status=ProposalStatus.MUTUALLY_APPROVED,
        current_revision_number=2,
        total_revisions_count=2,
        current_title="500 MT Supply",
        product_name="Clinker",
        total_value=Decimal("2100000"),
        currency="INR",
        expires_at=now,
        created_at=now,
        updated_at=now,
        approvals_count=2,
    )

    res = AdminProposalListResponse(
        items=[item],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
        status_counts={"MUTUALLY_APPROVED": 1, "PENDING_REVIEW": 0},
    )
    assert res.total == 1
    assert len(res.items) == 1
    assert res.status_counts["MUTUALLY_APPROVED"] == 1
