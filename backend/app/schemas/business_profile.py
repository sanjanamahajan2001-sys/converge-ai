"""Pydantic schemas for business profiles, offerings, requirements, and taxonomies."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Taxonomy DTOs
# ---------------------------------------------------------------------------
class ProductGradeDTO(BaseModel):
    grade_code: str
    product_code: str
    grade_name: str
    governing_standard: Optional[str] = None
    aliases: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class CanonicalProductDTO(BaseModel):
    product_code: str
    category_code: str
    canonical_name: str
    substitute_product_codes: List[str] = []
    grades: List[ProductGradeDTO] = []

    model_config = ConfigDict(from_attributes=True)


class ProductTaxonomyDTO(BaseModel):
    category_code: str
    sector_code: str
    canonical_name: str
    standard_units: List[str] = []
    canonical_products: List[CanonicalProductDTO] = []

    model_config = ConfigDict(from_attributes=True)


class ServiceTaxonomyDTO(BaseModel):
    service_code: str
    category_code: str
    canonical_name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Business Offering DTOs (Supplier & Vendor Catalog)
# ---------------------------------------------------------------------------
class BusinessOfferingBase(BaseModel):
    custom_product_title: str = Field(..., min_length=2, max_length=200)
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    specifications_text: Optional[str] = None

    declared_monthly_capacity: Optional[Decimal] = Field(None, ge=0)
    declared_committed_volume: Optional[Decimal] = Field(None, ge=0)
    capacity_unit: Optional[str] = None
    minimum_order_quantity: Optional[Decimal] = Field(None, gt=0)
    lead_time_days: Optional[int] = Field(None, ge=0)
    geographic_coverage: List[str] = []

    offers_test_certificates: bool = False
    vendor_certifications: List[str] = []

    open_to_distribution: bool = False
    target_distribution_regions: List[str] = []
    distributor_tier_preferred: Optional[str] = None

    is_public_indicative: bool = False
    indicative_price_min: Optional[Decimal] = Field(None, gt=0)
    indicative_price_max: Optional[Decimal] = None
    price_currency: str = Field("INR", pattern="^(INR|USD|EUR|GBP|AED|SGD)$")
    pricing_basis: Optional[str] = Field(None, pattern="^(EX_WORKS|FOR_DELIVERED|FOB|CIF|FAS|DAP)$")
    offers_delivered_pricing: bool = False
    quote_validity_days: int = Field(30, ge=1, le=365)

    @model_validator(mode="after")
    def validate_capacity_and_pricing(self) -> "BusinessOfferingBase":
        if self.declared_monthly_capacity is not None and self.declared_committed_volume is not None:
            if self.declared_committed_volume > self.declared_monthly_capacity:
                raise ValueError("declared_committed_volume cannot exceed declared_monthly_capacity")
        if self.declared_monthly_capacity is not None and self.minimum_order_quantity is not None:
            if self.minimum_order_quantity > self.declared_monthly_capacity:
                raise ValueError("minimum_order_quantity cannot exceed declared_monthly_capacity")
        if self.indicative_price_min is not None and self.indicative_price_max is not None:
            if self.indicative_price_max < self.indicative_price_min:
                raise ValueError("indicative_price_max must be greater than or equal to indicative_price_min")
        return self


class BusinessOfferingCreate(BusinessOfferingBase):
    pass


class BusinessOfferingUpdate(BaseModel):
    custom_product_title: Optional[str] = Field(None, min_length=2, max_length=200)
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    specifications_text: Optional[str] = None

    declared_monthly_capacity: Optional[Decimal] = Field(None, ge=0)
    declared_committed_volume: Optional[Decimal] = Field(None, ge=0)
    capacity_unit: Optional[str] = None
    minimum_order_quantity: Optional[Decimal] = Field(None, gt=0)
    lead_time_days: Optional[int] = Field(None, ge=0)
    geographic_coverage: Optional[List[str]] = None

    offers_test_certificates: Optional[bool] = None
    vendor_certifications: Optional[List[str]] = None

    open_to_distribution: Optional[bool] = None
    target_distribution_regions: Optional[List[str]] = None
    distributor_tier_preferred: Optional[str] = None

    is_public_indicative: Optional[bool] = None
    indicative_price_min: Optional[Decimal] = Field(None, gt=0)
    indicative_price_max: Optional[Decimal] = None
    price_currency: Optional[str] = Field(None, pattern="^(INR|USD|EUR|GBP|AED|SGD)$")
    pricing_basis: Optional[str] = Field(None, pattern="^(EX_WORKS|FOR_DELIVERED|FOB|CIF|FAS|DAP)$")
    offers_delivered_pricing: Optional[bool] = None
    quote_validity_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = None


class BusinessOfferingResponse(BusinessOfferingBase):
    id: uuid.UUID
    business_profile_id: uuid.UUID
    is_active: bool
    price_last_confirmed_at: Optional[datetime] = None
    capacity_last_confirmed_at: Optional[datetime] = None
    is_capacity_stale: bool = False
    is_price_stale: bool = False
    reconfirmation_required: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Business Requirement DTOs (Buyer & Procurement Needs)
# ---------------------------------------------------------------------------
class BusinessRequirementBase(BaseModel):
    custom_requirement_title: Optional[str] = Field(None, min_length=2, max_length=200)
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    required_quantity: Optional[Decimal] = Field(None, gt=0)
    quantity_unit: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_country: Optional[str] = None
    target_timeline_days: Optional[int] = Field(None, gt=0)

    # Privacy by default
    target_budget_indication: Optional[Decimal] = Field(None, gt=0)
    is_budget_public: bool = False

    urgency: str = Field("PLANNED", pattern="^(IMMEDIATE|PLANNED|EXPLORATORY)$")
    excluded_supplier_ids: List[str] = []
    allow_substitutes: bool = False
    required_certifications: List[str] = []
    is_feedstock_procurement: bool = False
    notes: Optional[str] = None


class BusinessRequirementCreate(BusinessRequirementBase):
    pass


class BusinessRequirementUpdate(BaseModel):
    custom_requirement_title: Optional[str] = Field(None, min_length=2, max_length=200)
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    required_quantity: Optional[Decimal] = Field(None, gt=0)
    quantity_unit: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_country: Optional[str] = None
    target_timeline_days: Optional[int] = Field(None, gt=0)
    target_budget_indication: Optional[Decimal] = Field(None, gt=0)
    is_budget_public: Optional[bool] = None
    urgency: Optional[str] = Field(None, pattern="^(IMMEDIATE|PLANNED|EXPLORATORY)$")
    excluded_supplier_ids: Optional[List[str]] = None
    allow_substitutes: Optional[bool] = None
    required_certifications: Optional[List[str]] = None
    is_feedstock_procurement: Optional[bool] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class BusinessRequirementResponse(BusinessRequirementBase):
    id: uuid.UUID
    business_profile_id: uuid.UUID
    custom_requirement_title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Commercial Profile DTOs (Multi-Role Management)
# ---------------------------------------------------------------------------
class BusinessProfileUpdate(BaseModel):
    is_buyer: bool = False
    is_supplier: bool = False
    is_vendor: bool = False
    is_distributor: bool = False
    is_partner: bool = False
    allow_business_matching: bool = False

    company_name: Optional[str] = Field(None, max_length=150)
    industry: Optional[str] = Field(None, max_length=100)
    business_website: Optional[str] = Field(None, max_length=255)
    hq_city: Optional[str] = Field(None, max_length=100)
    hq_country: Optional[str] = Field(None, max_length=100)
    company_bio: Optional[str] = None

    distributor_territories: List[str] = []
    warehousing_capacity_sqft: Optional[Decimal] = Field(None, ge=0)
    retail_dealer_count: Optional[int] = Field(None, ge=0)

    partnership_types: List[str] = []
    partnership_interests: List[str] = []

    @model_validator(mode="after")
    def validate_opt_in_roles(self) -> "BusinessProfileUpdate":
        if self.allow_business_matching:
            if not (self.is_buyer or self.is_supplier or self.is_vendor or self.is_distributor or self.is_partner):
                raise ValueError("At least one business role must be selected to enable business matching")
        return self


class BusinessProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    is_buyer: bool
    is_supplier: bool
    is_vendor: bool
    is_distributor: bool
    is_partner: bool
    allow_business_matching: bool

    company_name: Optional[str] = None
    industry: Optional[str] = None
    business_website: Optional[str] = None
    hq_city: Optional[str] = None
    hq_country: Optional[str] = None
    company_bio: Optional[str] = None

    distributor_territories: List[str] = []
    warehousing_capacity_sqft: Optional[Decimal] = None
    retail_dealer_count: Optional[int] = None

    partnership_types: List[str] = []
    partnership_interests: List[str] = []

    offerings: List[BusinessOfferingResponse] = []
    requirements: List[BusinessRequirementResponse] = []

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
