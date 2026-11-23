"""Pydantic schemas and Data Transfer Objects for Quote Requests and Email Dispatches (Quote Subphase 3)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.db.models.quote import (
    EmailDeliveryStatus,
    QuoteRequestStatus,
    QuoteUrgency,
    VendorMatchStatus,
)


class CustomerSummary(BaseModel):
    """Public customer delegate projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None


class VendorSummary(BaseModel):
    """Public vendor delegate projection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None


class QuoteRequestCreate(BaseModel):
    """Payload to initiate a new procurement ask / RFQ."""

    conversation_id: Optional[uuid.UUID] = None
    customer_agent_persona: Optional[str] = "Procurement AI Agent"
    title: str = Field(..., min_length=3, max_length=255)
    product_name: str = Field(..., min_length=2, max_length=200)
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    quantity_unit: Optional[str] = "MT"
    delivery_location: Optional[str] = None
    timeline_days: Optional[int] = Field(None, gt=0)
    target_price_indication: Optional[Decimal] = Field(None, gt=0)
    currency: str = Field(default="INR", max_length=10)
    is_budget_public: bool = False
    urgency: QuoteUrgency = QuoteUrgency.PLANNED
    technical_specifications: Dict[str, Any] = Field(default_factory=dict)
    inquiry_notes: Optional[str] = None
    target_vendor_ids: Optional[List[uuid.UUID]] = None


class QuoteVendorPanelItem(BaseModel):
    """Summary projection for an ask listed on a vendor's incoming quotes panel."""

    model_config = ConfigDict(from_attributes=True)

    match_id: Optional[uuid.UUID] = None
    quote_request_id: uuid.UUID
    title: str
    product_name: str
    product_code: Optional[str] = None
    quantity: Optional[Decimal] = None
    quantity_unit: Optional[str] = None
    delivery_location: Optional[str] = None
    timeline_days: Optional[int] = None
    urgency: QuoteUrgency
    status: VendorMatchStatus
    match_score: Decimal
    match_reasons: List[str] = Field(default_factory=list)
    viewed_at: Optional[datetime] = None
    created_at: datetime
    customer: CustomerSummary
    customer_agent_persona: Optional[str] = None

    # Quoting Activity Summary
    dispatches_count: int = 0
    latest_quote_reference: Optional[str] = None
    latest_quoted_value: Optional[Decimal] = None
    latest_quoted_currency: Optional[str] = None
    latest_dispatched_at: Optional[datetime] = None


class QuoteVendorPanelCounts(BaseModel):
    """Aggregate counts for vendor quotes panel status tabs."""

    all: int = 0
    new_inquiries: int = 0
    quoted: int = 0
    declined: int = 0


class QuoteVendorPanelResponse(BaseModel):
    """Paginated list of incoming asks with status metrics for vendor portal."""

    items: List[QuoteVendorPanelItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    counts: QuoteVendorPanelCounts


class QuoteEmailDispatchDetail(BaseModel):
    """Detailed audit record of an email quote transmission."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quote_reference_number: str
    unit_price: Decimal
    total_value: Decimal
    currency: str
    incoterm: str
    lead_time_days: int
    validity_days: int
    payment_terms: str
    commercial_notes: Optional[str] = None
    sender_email: str
    recipient_email: str
    delivery_status: EmailDeliveryStatus
    sent_at: datetime


class QuoteRequestDetail(BaseModel):
    """Full forensic specification of a customer ask."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: Optional[uuid.UUID] = None
    title: str
    product_name: str
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    quantity: Optional[Decimal] = None
    quantity_unit: Optional[str] = None
    delivery_location: Optional[str] = None
    timeline_days: Optional[int] = None
    target_price_indication: Optional[Decimal] = None
    currency: str
    is_budget_public: bool
    urgency: QuoteUrgency
    status: QuoteRequestStatus
    technical_specifications: Dict[str, Any]
    inquiry_notes: Optional[str] = None
    created_at: datetime
    customer: CustomerSummary
    customer_agent_persona: Optional[str] = None

    # Vendor-specific perspective (if caller is a matched vendor)
    vendor_match_status: Optional[VendorMatchStatus] = None
    match_score: Optional[Decimal] = None
    match_reasons: Optional[List[str]] = None
    dispatches: List[QuoteEmailDispatchDetail] = Field(default_factory=list)


class SendQuoteEmailRequest(BaseModel):
    """Commercial terms submitted by a vendor to dispatch a quote via email."""

    unit_price: Decimal = Field(..., gt=0, description="Offered price per unit")
    total_value: Optional[Decimal] = Field(
        None, gt=0, description="Optional total contract value; auto-calculated from quantity if omitted"
    )
    currency: str = Field(default="INR", max_length=10)
    incoterm: str = Field(default="EXW", max_length=30)
    lead_time_days: int = Field(default=14, gt=0)
    validity_days: int = Field(default=15, gt=0)
    payment_terms: str = Field(..., min_length=3, max_length=500)
    commercial_notes: Optional[str] = Field(None, max_length=2000)


class SendQuoteEmailResponse(BaseModel):
    """Confirmation payload returned after quote email dispatch."""

    dispatch_id: uuid.UUID
    quote_reference_number: str
    recipient_email: str
    sender_email: str
    total_value: Decimal
    currency: str
    delivery_status: EmailDeliveryStatus
    sent_at: datetime
    message: str


# --- Admin Governance Schemas ---

class AdminQuoteDispatchItem(BaseModel):
    """Detailed audit projection of a quote dispatch for admin governance."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quote_reference_number: str
    quote_request_id: uuid.UUID
    quote_vendor_match_id: uuid.UUID
    product_name: str
    product_code: Optional[str] = None
    quantity: Optional[Decimal] = None
    quantity_unit: Optional[str] = None
    unit_price: Decimal
    total_value: Decimal
    currency: str
    incoterm: str
    lead_time_days: int
    validity_days: int
    payment_terms: str
    commercial_notes: Optional[str] = None

    # Vendor (Seller)
    vendor_id: uuid.UUID
    vendor_name: str
    vendor_company: Optional[str] = None
    sender_email: str

    # Customer (Buyer)
    customer_id: uuid.UUID
    customer_name: str
    customer_company: Optional[str] = None
    recipient_email: str

    # Delivery & Audit
    email_subject: str
    delivery_status: EmailDeliveryStatus
    external_message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: datetime


class AdminQuoteMetrics(BaseModel):
    """Platform-wide aggregate metrics for commercial quotations."""

    total_dispatched: int = 0
    total_quoted_value: Decimal = Decimal("0.00")
    unique_vendors: int = 0
    unique_customers: int = 0
    sent_count: int = 0
    failed_count: int = 0
    delivery_rate_percent: Decimal = Decimal("100.00")


class AdminQuoteListResponse(BaseModel):
    """Paginated directory of all platform quote dispatches for administrators."""

    items: List[AdminQuoteDispatchItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    metrics: AdminQuoteMetrics


class AdminQuoteDetailResponse(AdminQuoteDispatchItem):
    """Full forensic audit detail of a single quotation transmission including rendered HTML."""

    email_body_html: str

