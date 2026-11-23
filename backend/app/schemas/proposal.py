"""Pydantic schemas and data contracts for Proposal Generation & Dual-Sided Approval.

Enforces zero contact leakage invariant:
Protected contact credentials (email, phone, direct tax/registration) are
strictly omitted from serialization unless the proposal status is MUTUALLY_APPROVED.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProposalStatus(str, Enum):
    """Proposal lifecycle states."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    MUTUALLY_APPROVED = "MUTUALLY_APPROVED"
    REJECTED = "REJECTED"
    REVISED = "REVISED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class CommercialRole(str, Enum):
    """Commercial role of a party in a bilateral transaction."""

    BUYER = "BUYER"
    SUPPLIER = "SUPPLIER"
    VENDOR = "VENDOR"
    DISTRIBUTOR = "DISTRIBUTOR"
    PARTNER = "PARTNER"


class ProposalType(str, Enum):
    """Structured proposal categories."""

    SUPPLY_CONTRACT = "SUPPLY_CONTRACT"
    PROCUREMENT_ORDER = "PROCUREMENT_ORDER"
    DISTRIBUTION_AGREEMENT = "DISTRIBUTION_AGREEMENT"
    SERVICE_MOU = "SERVICE_MOU"
    STRATEGIC_PARTNERSHIP = "STRATEGIC_PARTNERSHIP"


class ApprovalAction(str, Enum):
    """Action recorded in proposal approval history."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class ProposalPartySummary(BaseModel):
    """Public party identification on a proposal."""

    user_id: UUID
    full_name: str
    company_name: Optional[str] = None
    designation: Optional[str] = None
    role: CommercialRole

    model_config = ConfigDict(from_attributes=True)


class DisclosedContactCredentials(BaseModel):
    """Protected contact details only revealed after valid dual-sided approval."""

    user_id: UUID
    full_name: str
    company_name: Optional[str] = None
    designation: Optional[str] = None
    email: str
    phone_number: str
    hq_city: Optional[str] = None
    corporate_website: Optional[str] = None
    tax_id_or_registration: Optional[str] = None
    verification_receipt_hash: Optional[str] = None
    disclosed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalRevisionBase(BaseModel):
    """Core commercial parameters common across creation, update, and projection."""

    title: str = Field(..., min_length=3, max_length=150, description="Proposal headline or commercial contract title.")
    proposal_type: ProposalType = Field(default=ProposalType.SUPPLY_CONTRACT, description="Type of commercial agreement.")
    product_name: str = Field(..., min_length=2, max_length=150, description="Core commodity, product, or scope of services.")
    product_code: Optional[str] = Field(default=None, max_length=60, description="Standardized taxonomy product code.")
    grade_code: Optional[str] = Field(default=None, max_length=60, description="Material grade or specification code.")
    service_code: Optional[str] = Field(default=None, max_length=60, description="Taxonomy service code if applicable.")
    quantity: Decimal = Field(..., gt=0, description="Quantity or volume.")
    unit: str = Field(..., min_length=1, max_length=30, description="Unit of measurement (MT, KG, Liters, Units).")
    unit_price: Optional[Decimal] = Field(default=None, ge=0, description="Unit commercial price.")
    currency: str = Field(default="INR", min_length=3, max_length=10, description="3-letter currency code (e.g. INR, USD).")
    total_value: Optional[Decimal] = Field(default=None, ge=0, description="Calculated or agreed total value.")
    payment_terms: str = Field(..., min_length=3, max_length=255, description="Agreed payment terms (e.g. 30% Advance, 70% against BL).")
    delivery_location: str = Field(..., min_length=2, max_length=150, description="Delivery city, destination port, or site address.")
    incoterm: Optional[str] = Field(default="EXW", max_length=20, description="Applicable Incoterm (e.g. EXW, FOB, CIF, DDP).")
    delivery_timeline_days: int = Field(default=30, ge=1, le=730, description="Lead time in calendar days.")
    governing_standards: Optional[List[str]] = Field(default_factory=list, description="Regulatory, IS, or ASTM standards.")
    special_conditions: Optional[str] = Field(default=None, max_length=2000, description="Testing requirements, penalty clauses, or special covenants.")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Internal or counterparty context notes.")
    revision_summary: Optional[str] = Field(default=None, max_length=300, description="Summary of changes relative to prior version.")

    @model_validator(mode="after")
    def calculate_total_value_if_missing(self) -> "ProposalRevisionBase":
        """Compute total_value automatically from unit_price and quantity if not explicitly provided."""
        if self.total_value is None and self.unit_price is not None:
            self.total_value = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        return self


class ProposalRevisionCreate(ProposalRevisionBase):
    """Payload to create a new revision (either V1 or subsequent counterproposal)."""

    pass


class ProposalRevisionResponse(ProposalRevisionBase):
    """Complete revision projection returned from API."""

    id: UUID
    proposal_id: UUID
    revision_number: int
    author_id: UUID
    author_name: Optional[str] = None
    author_company: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalApprovalRecord(BaseModel):
    """Audit entry recording a party's action on a revision."""

    id: UUID
    proposal_id: UUID
    revision_id: UUID
    revision_number: int
    user_id: UUID
    user_name: Optional[str] = None
    action: ApprovalAction
    notes: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalCreateRequest(BaseModel):
    """Request payload to initiate a new formal proposal (Revision 1)."""

    conversation_id: Optional[UUID] = Field(default=None, description="Linked bilateral conversation if initiated from chat.")
    recipient_id: UUID = Field(..., description="Target counterparty delegate user UUID.")
    proposer_role: CommercialRole = Field(..., description="Role of the initiator (e.g. BUYER or SUPPLIER).")
    recipient_role: CommercialRole = Field(..., description="Complementary role of recipient.")
    validity_days: int = Field(default=7, ge=1, le=60, description="Validity period in calendar days.")
    revision: ProposalRevisionCreate = Field(..., description="Parameters for Revision V1.")


class CounterProposalRequest(BaseModel):
    """Request payload to counter a pending proposal by introducing Revision k+1."""

    revision_summary: str = Field(..., min_length=5, max_length=300, description="Clear summary explaining counter-offered modifications.")
    revision: ProposalRevisionCreate = Field(..., description="Modified commercial terms.")


class ProposalApprovalRequest(BaseModel):
    """Request payload to approve the active proposal revision."""

    notes: Optional[str] = Field(default=None, max_length=500, description="Optional acceptance or endorsement note.")


class ProposalRejectionRequest(BaseModel):
    """Request payload to formally reject a proposal."""

    reason: str = Field(..., min_length=5, max_length=500, description="Mandatory reason for rejection.")


class ProposalDraftPrefillRequest(BaseModel):
    """Request payload to pre-populate a proposal draft from active dialogue context."""

    conversation_id: UUID = Field(..., description="Conversation UUID to extract commercial brief and turns from.")
    recipient_id: UUID = Field(..., description="Counterparty delegate user UUID.")


class ProposalDraftPrefillResponse(BaseModel):
    """Pre-populated proposal draft generated via dynamic business profile and context analysis."""

    conversation_id: UUID
    recipient_id: UUID
    proposer_role: CommercialRole
    recipient_role: CommercialRole
    suggested_revision: ProposalRevisionCreate
    grounding_source: str = Field(..., description="Brief source e.g. CONTEXT_BRIEF, CATALOG_OFFERING, or LLM_SYNTHESIS.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class ProposalListItem(BaseModel):
    """Summary item displayed in user's Proposals Hub (/proposals)."""

    id: UUID
    conversation_id: Optional[UUID] = None
    proposer_id: UUID
    proposer_name: str
    proposer_company: Optional[str] = None
    proposer_role: CommercialRole
    recipient_id: UUID
    recipient_name: str
    recipient_company: Optional[str] = None
    recipient_role: CommercialRole
    proposal_type: ProposalType
    status: ProposalStatus
    current_revision_number: int
    current_title: str
    product_name: str
    quantity: Decimal
    unit: str
    total_value: Optional[Decimal] = None
    currency: str = "INR"
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    concluded_at: Optional[datetime] = None
    user_is_proposer: bool = False
    requires_user_action: bool = False
    contacts_disclosed: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProposalDetailResponse(BaseModel):
    """Full proposal sheet with revisions, approvals, and strictly gated contact credentials."""

    id: UUID
    conversation_id: Optional[UUID] = None
    proposer: ProposalPartySummary
    recipient: ProposalPartySummary
    proposal_type: ProposalType
    status: ProposalStatus
    current_revision_number: int
    active_revision: ProposalRevisionResponse
    revisions: List[ProposalRevisionResponse] = Field(default_factory=list)
    approvals: List[ProposalApprovalRecord] = Field(default_factory=list)
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    concluded_at: Optional[datetime] = None
    user_is_proposer: bool = False
    requires_user_action: bool = False
    contacts_disclosed: bool = False
    disclosed_credentials: Optional[DisclosedContactCredentials] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def enforce_contact_redaction_invariant(self) -> "ProposalDetailResponse":
        """Strict Privacy Gate: Ensure contact information is never leaked if status != MUTUALLY_APPROVED."""
        if self.status != ProposalStatus.MUTUALLY_APPROVED:
            self.contacts_disclosed = False
            self.disclosed_credentials = None
        return self


# --- Admin DTOs & Governance ---

class AdminProposalFilter(BaseModel):
    """Filter parameters for Admin Proposals Directory."""

    status: Optional[ProposalStatus] = None
    proposal_type: Optional[ProposalType] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AdminProposalListItem(BaseModel):
    """Administrative overview row for platform governance."""

    id: UUID
    conversation_id: Optional[UUID] = None
    proposer_id: UUID
    proposer_name: str
    proposer_company: Optional[str] = None
    proposer_role: CommercialRole
    recipient_id: UUID
    recipient_name: str
    recipient_company: Optional[str] = None
    recipient_role: CommercialRole
    proposal_type: ProposalType
    status: ProposalStatus
    current_revision_number: int
    total_revisions_count: int
    current_title: str
    product_name: str
    total_value: Optional[Decimal] = None
    currency: str = "INR"
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    concluded_at: Optional[datetime] = None
    approvals_count: int

    model_config = ConfigDict(from_attributes=True)


class AdminProposalListResponse(BaseModel):
    """Paginated collection for Admin Proposals Queue."""

    items: List[AdminProposalListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    status_counts: Dict[str, int]


class ProposalDiffFieldChange(BaseModel):
    """Detailed diff for a single commercial contract parameter between two revisions."""

    field: str = Field(..., description="Parameter attribute name (e.g. quantity, unit_price).")
    field_label: str = Field(..., description="Human-readable label (e.g. Quantity, Unit Price).")
    old_value: Any = Field(default=None, description="Value in baseline revision.")
    new_value: Any = Field(default=None, description="Value in compared revision.")
    change_type: str = Field(..., description="MODIFIED, ADDED, REMOVED, or UNCHANGED.")
    numeric_delta: Optional[Decimal] = Field(default=None, description="Numerical delta (new - old) if applicable.")
    formatted_change: Optional[str] = Field(default=None, description="Human summary e.g. '+250 MT' or '-₹ 150'.")


class ProposalRevisionDiffResponse(BaseModel):
    """Structured diff comparison between two proposal revisions (Phase 7 - Subphase 5)."""

    proposal_id: UUID
    from_revision_number: int
    to_revision_number: int
    from_author_name: Optional[str] = None
    to_author_name: Optional[str] = None
    from_created_at: Optional[datetime] = None
    to_created_at: Optional[datetime] = None
    changes: List[ProposalDiffFieldChange]
    has_price_change: bool = False
    has_quantity_change: bool = False
    has_timeline_change: bool = False
    has_delivery_change: bool = False
