"""Pydantic schemas for Phase 3 Business Requirement Matching and Query Parser."""
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdown(BaseModel):
    """Decomposed scoring across the 5 independent evaluation dimensions."""

    product_relevance: float = Field(..., ge=0.0, le=1.0, description="Product / service taxonomy match score (0.0 to 1.0).")
    capacity_feasibility: float = Field(..., ge=0.0, le=1.0, description="Run-rate normalized capacity feasibility (0.0 to 1.0).")
    commitment_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in uncommitted allocation (0.0 to 1.0).")
    delivery_feasibility: float = Field(..., ge=0.0, le=1.0, description="Location coverage and lead time feasibility (0.0 to 1.0).")
    verification_confidence: float = Field(..., ge=0.0, le=1.0, description="Freshness and anti-staleness rating (0.0 to 1.0).")


class ParsedBusinessRequirement(BaseModel):
    """Structured requirement extracted from natural language or saved requirement."""

    raw_query: str
    item_name: Optional[str] = None
    matched_product_code: Optional[str] = None
    matched_grade_code: Optional[str] = None
    matched_service_code: Optional[str] = None
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    destination_city: Optional[str] = None
    target_timeline_days: Optional[int] = None
    inquiry_type: str = "RFQ_PRODUCT"
    confidence: float = 1.0


class QueryParseRequest(BaseModel):
    """Payload to parse an unstructured procurement requirement inquiry."""

    query: str = Field(..., min_length=2, max_length=500, description="Natural language inquiry string.")


class BusinessMatchSearchRequest(BaseModel):
    """Request payload for Mode B commercial requirement matching."""

    requirement_id: Optional[UUID] = Field(None, description="Optional ID of saved buyer requirement to match against.")
    query: Optional[str] = Field(None, max_length=500, description="Optional freeform query string.")
    item_name: Optional[str] = Field(None, max_length=200)
    product_code: Optional[str] = Field(None, max_length=80)
    grade_code: Optional[str] = Field(None, max_length=80)
    service_code: Optional[str] = Field(None, max_length=80)
    quantity: Optional[float] = Field(None, gt=0)
    quantity_unit: Optional[str] = Field(None, max_length=30)
    delivery_city: Optional[str] = Field(None, max_length=100)
    target_timeline_days: Optional[int] = Field(None, gt=0)
    allow_substitutes: bool = Field(False, description="Whether to include substitute materials in matching.")
    search_type: str = Field("SUPPLIERS", description="Search target: 'SUPPLIERS' (Buyer seeking vendors/suppliers) or 'BUYERS' (Supplier/vendor seeking buyers).")
    limit: int = Field(20, ge=1, le=50)
    offset: int = Field(0, ge=0)


class BusinessMatchCandidate(BaseModel):
    """Ranked supplier or vendor offering candidate for commercial RFQ."""

    offering_id: Optional[UUID] = None
    requirement_id: Optional[UUID] = None
    candidate_type: str = "OFFERING"  # "OFFERING" or "REQUIREMENT"
    business_profile_id: UUID
    supplier_user_id: UUID
    supplier_company_name: Optional[str] = None
    supplier_industry: Optional[str] = None
    supplier_hq_city: Optional[str] = None
    supplier_role: str = "SUPPLIER" # BUYER, SUPPLIER, VENDOR, DISTRIBUTOR, PARTNER
    offering_title: str
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    composite_score: float = Field(..., description="Overall match percentage 0 to 100.")
    score_breakdown: ScoreBreakdown
    declared_monthly_capacity: Optional[float] = None
    capacity_unit: Optional[str] = None
    uncommitted_monthly_capacity: Optional[float] = None
    lead_time_days: Optional[int] = None
    geographic_coverage: List[str] = Field(default_factory=list)
    offers_test_certificates: bool = False
    confidence_badges: List[str] = Field(default_factory=list)
    indicative_price_display: Optional[str] = None
    pricing_basis: Optional[str] = None
    price_currency: str = "INR"
    destination_city: Optional[str] = None
    target_timeline_days: Optional[int] = None
    required_quantity: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BusinessMatchSearchResponse(BaseModel):
    """Response containing ranked commercial candidates and parsed inquiry context."""

    total_candidates: int
    query_summary: Optional[ParsedBusinessRequirement] = None
    candidates: List[BusinessMatchCandidate]
