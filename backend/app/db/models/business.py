"""Business profile, taxonomy, catalog offerings and connection context models in schema business."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.user import User


class ProductTaxonomy(Base):
    """Tier 2 ProductCategory in 4-tier taxonomy."""

    __tablename__ = "product_taxonomies"
    __table_args__ = {"schema": "business"}

    category_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    sector_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(150), nullable=False)
    standard_units: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    canonical_products: Mapped[List["CanonicalProduct"]] = relationship(
        "CanonicalProduct", back_populates="taxonomy", cascade="all, delete-orphan"
    )


class CanonicalProduct(Base):
    """Tier 3 Canonical non-interchangeable product."""

    __tablename__ = "canonical_products"
    __table_args__ = {"schema": "business"}

    product_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    category_code: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("business.product_taxonomies.category_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    canonical_name: Mapped[str] = mapped_column(String(150), nullable=False)
    substitute_product_codes: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    taxonomy: Mapped["ProductTaxonomy"] = relationship(
        "ProductTaxonomy", back_populates="canonical_products"
    )
    grades: Mapped[List["ProductGrade"]] = relationship(
        "ProductGrade", back_populates="canonical_product", cascade="all, delete-orphan"
    )


class ProductGrade(Base):
    """Tier 4 Product grade and governing standard."""

    __tablename__ = "product_grades"
    __table_args__ = {"schema": "business"}

    grade_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    product_code: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("business.canonical_products.product_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    grade_name: Mapped[str] = mapped_column(String(150), nullable=False)
    governing_standard: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    aliases: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    canonical_product: Mapped["CanonicalProduct"] = relationship(
        "CanonicalProduct", back_populates="grades"
    )


class ServiceTaxonomy(Base):
    """Service categories for vendors and service providers."""

    __tablename__ = "service_taxonomies"
    __table_args__ = {"schema": "business"}

    service_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    category_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class BusinessProfile(Base):
    """Commercial profile supporting dynamic multi-role participation."""

    __tablename__ = "business_profiles"
    __table_args__ = (
        CheckConstraint(
            "(allow_business_matching = FALSE) OR "
            "(is_buyer OR is_supplier OR is_vendor OR is_distributor OR is_partner)",
            name="ck_at_least_one_role",
        ),
        CheckConstraint(
            "warehousing_capacity_sqft IS NULL OR warehousing_capacity_sqft >= 0",
            name="ck_warehousing_capacity_positive",
        ),
        CheckConstraint(
            "retail_dealer_count IS NULL OR retail_dealer_count >= 0",
            name="ck_retail_dealer_count_positive",
        ),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Dynamic Role Flags
    is_buyer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_supplier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_vendor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_distributor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_partner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Global Commercial Consent (Strictly Opt-In)
    allow_business_matching: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Company Metadata
    company_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hq_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hq_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Distributor Specific Fields
    distributor_territories: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    warehousing_capacity_sqft: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    retail_dealer_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Partnership Specific Fields
    partnership_types: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    partnership_interests: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    offerings: Mapped[List["BusinessOffering"]] = relationship(
        "BusinessOffering", back_populates="business_profile", cascade="all, delete-orphan"
    )
    requirements: Mapped[List["BusinessRequirement"]] = relationship(
        "BusinessRequirement", back_populates="business_profile", cascade="all, delete-orphan"
    )


class BusinessOffering(Base):
    """Supplier and Vendor Catalog Offerings."""

    __tablename__ = "business_offerings"
    __table_args__ = (
        CheckConstraint(
            "declared_monthly_capacity IS NULL OR declared_monthly_capacity >= 0",
            name="ck_declared_monthly_capacity_positive",
        ),
        CheckConstraint(
            "declared_committed_volume IS NULL OR declared_committed_volume >= 0",
            name="ck_declared_committed_volume_positive",
        ),
        CheckConstraint(
            "minimum_order_quantity IS NULL OR minimum_order_quantity > 0",
            name="ck_moq_positive",
        ),
        CheckConstraint(
            "lead_time_days IS NULL OR lead_time_days >= 0",
            name="ck_lead_time_positive",
        ),
        CheckConstraint(
            "indicative_price_min IS NULL OR indicative_price_min > 0",
            name="ck_indicative_price_min_positive",
        ),
        CheckConstraint(
            "indicative_price_max IS NULL OR indicative_price_min IS NULL OR indicative_price_max >= indicative_price_min",
            name="ck_indicative_price_max_ge_min",
        ),
        CheckConstraint(
            "quote_validity_days > 0 AND quote_validity_days <= 365",
            name="ck_quote_validity_range",
        ),
        CheckConstraint(
            "pricing_basis IS NULL OR pricing_basis IN ('EX_WORKS', 'FOR_DELIVERED', 'FOB', 'CIF', 'FAS', 'DAP')",
            name="ck_pricing_basis_valid",
        ),
        CheckConstraint(
            "price_currency IN ('INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD')",
            name="ck_price_currency_valid",
        ),
        CheckConstraint(
            "(declared_committed_volume IS NULL OR declared_monthly_capacity IS NULL OR declared_committed_volume <= declared_monthly_capacity) AND "
            "(minimum_order_quantity IS NULL OR declared_monthly_capacity IS NULL OR minimum_order_quantity <= declared_monthly_capacity)",
            name="ck_offering_capacity_consistency",
        ),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    business_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.business_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("business.canonical_products.product_code", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    grade_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("business.product_grades.grade_code", ondelete="SET NULL"),
        nullable=True,
    )
    service_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("business.service_taxonomies.service_code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    custom_product_title: Mapped[str] = mapped_column(String(200), nullable=False)
    specifications_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Capacity
    declared_monthly_capacity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    declared_committed_volume: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    capacity_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    minimum_order_quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    geographic_coverage: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )

    # Certifications
    offers_test_certificates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vendor_certifications: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )

    # Distribution Parameters
    open_to_distribution: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_distribution_regions: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    distributor_tier_preferred: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Commercial Pricing Safeguards
    is_public_indicative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    indicative_price_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    indicative_price_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    price_currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    pricing_basis: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    offers_delivered_pricing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quote_validity_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Freshness Tracking
    price_last_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    capacity_last_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    business_profile: Mapped["BusinessProfile"] = relationship(
        "BusinessProfile", back_populates="offerings"
    )


class BusinessRequirement(Base):
    """Buyer and Procurement Active Requirements."""

    __tablename__ = "business_requirements"
    __table_args__ = (
        CheckConstraint(
            "required_quantity IS NULL OR required_quantity > 0",
            name="ck_required_quantity_positive",
        ),
        CheckConstraint(
            "target_timeline_days IS NULL OR target_timeline_days > 0",
            name="ck_target_timeline_positive",
        ),
        CheckConstraint(
            "target_budget_indication IS NULL OR target_budget_indication > 0",
            name="ck_target_budget_positive",
        ),
        CheckConstraint(
            "urgency IN ('IMMEDIATE', 'PLANNED', 'EXPLORATORY')",
            name="ck_urgency_valid",
        ),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    business_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.business_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("business.canonical_products.product_code", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    grade_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("business.product_grades.grade_code", ondelete="SET NULL"),
        nullable=True,
    )
    service_code: Mapped[Optional[str]] = mapped_column(
        String(80),
        ForeignKey("business.service_taxonomies.service_code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    custom_requirement_title: Mapped[str] = mapped_column(
        String(200), nullable=False, server_default=""
    )

    required_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    delivery_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delivery_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_timeline_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Strict Privacy
    target_budget_indication: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    is_budget_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    urgency: Mapped[str] = mapped_column(String(30), default="PLANNED", nullable=False)

    # Exclusions & Special Parameters
    excluded_supplier_ids: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    allow_substitutes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_certifications: Mapped[List[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    is_feedstock_procurement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    business_profile: Mapped["BusinessProfile"] = relationship(
        "BusinessProfile", back_populates="requirements"
    )


class ConversationBusinessContext(Base):
    """Frozen connection business context snapshot tied to conversation."""

    __tablename__ = "conversation_business_contexts"
    __table_args__ = (
        CheckConstraint(
            "inquiry_type IN ('RFQ_PRODUCT', 'RFI_SERVICE', 'SUPPLIER_PROSPECTING', "
            "'VENDOR_PITCH', 'ALTERNATIVE_SOURCING', 'SOURCING_PARTNERSHIP', "
            "'DISTRIBUTION_EXPANSION', 'DISTRIBUTOR_APPLICATION', 'EXPLORATORY_COLLABORATION')",
            name="ck_inquiry_type_valid",
        ),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    inquiry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    grade_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    service_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    delivery_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timeline_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_price_indication: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    urgency: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    inquiry_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    revisions: Mapped[List["ContextRevision"]] = relationship(
        "ContextRevision", back_populates="context", cascade="all, delete-orphan"
    )


class ContextRevision(Base):
    """Subsequent authorized human revisions to business context."""

    __tablename__ = "context_revisions"
    __table_args__ = {"schema": "business"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.conversation_business_contexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revised_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    change_diff: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    context: Mapped["ConversationBusinessContext"] = relationship(
        "ConversationBusinessContext", back_populates="revisions"
    )
