"""Domain models for Quote Requests (The Ask), Multi-Vendor Matches, and Email Dispatches (Quote Subphase 2).

Enforces:
1. Vendor Isolation: Matched vendors can only inspect and quote on asks explicitly broadcast to them.
2. Complete Specifications: Commodity, volume, Incoterm, delivery location, and compliance standards stored per ask.
3. Immutable Email Dispatch Audit Trail: Captures exact quote parameters, reference number, recipient email,
   HTML body, and delivery status dispatched from sanjana.mahajan@sofueled.com.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.user import User


class QuoteRequestStatus(str, enum.Enum):
    """Lifecycle states for a Customer Ask / RFQ."""

    OPEN = "OPEN"
    MATCHED = "MATCHED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class QuoteUrgency(str, enum.Enum):
    """Urgency level specified by the customer / customer agent."""

    IMMEDIATE = "IMMEDIATE"
    PLANNED = "PLANNED"
    EXPLORATORY = "EXPLORATORY"


class VendorMatchStatus(str, enum.Enum):
    """Status of an individual vendor's match for an ask."""

    PENDING_REVIEW = "PENDING_REVIEW"
    QUOTED_VIA_EMAIL = "QUOTED_VIA_EMAIL"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class EmailDeliveryStatus(str, enum.Enum):
    """Delivery status of the quotation email."""

    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class QuoteRequest(Base):
    """Customer-initiated Procurement Ask / RFQ with technical specifications."""

    __tablename__ = "quote_requests"
    __table_args__ = (
        CheckConstraint(
            "target_price_indication IS NULL OR target_price_indication > 0",
            name="ck_quote_request_price_positive",
        ),
        CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_quote_request_quantity_positive",
        ),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Ownership & Source Context
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_agent_persona: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default="Procurement AI Agent",
    )

    # Core Specifications of the Ask
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    grade_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    service_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    quantity_unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    delivery_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timeline_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    target_price_indication: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    is_budget_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    urgency: Mapped[QuoteUrgency] = mapped_column(
        Enum(
            QuoteUrgency,
            name="quote_urgency",
            schema="business",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=QuoteUrgency.PLANNED,
        nullable=False,
        index=True,
    )

    technical_specifications: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    inquiry_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[QuoteRequestStatus] = mapped_column(
        Enum(
            QuoteRequestStatus,
            name="quote_request_status",
            schema="business",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=QuoteRequestStatus.OPEN,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id])
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation", foreign_keys=[conversation_id]
    )
    matches: Mapped[List["QuoteVendorMatch"]] = relationship(
        "QuoteVendorMatch",
        back_populates="quote_request",
        cascade="all, delete-orphan",
        order_by="desc(QuoteVendorMatch.match_score)",
    )


class QuoteVendorMatch(Base):
    """Mapping between a customer's ask and a matched supplier vendor."""

    __tablename__ = "quote_vendor_matches"
    __table_args__ = (
        UniqueConstraint("quote_request_id", "vendor_id", name="uq_quote_vendor_match"),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    quote_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.quote_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    match_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    match_reasons: Mapped[List[str]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    status: Mapped[VendorMatchStatus] = mapped_column(
        Enum(
            VendorMatchStatus,
            name="vendor_match_status",
            schema="business",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=VendorMatchStatus.PENDING_REVIEW,
        nullable=False,
        index=True,
    )

    viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # Relationships
    quote_request: Mapped["QuoteRequest"] = relationship("QuoteRequest", back_populates="matches")
    vendor: Mapped["User"] = relationship("User", foreign_keys=[vendor_id])
    dispatches: Mapped[List["QuoteEmailDispatch"]] = relationship(
        "QuoteEmailDispatch",
        back_populates="quote_vendor_match",
        cascade="all, delete-orphan",
        order_by="desc(QuoteEmailDispatch.sent_at)",
    )


class QuoteEmailDispatch(Base):
    """Immutable audit record of a quotation email dispatched to a customer."""

    __tablename__ = "quote_email_dispatches"
    __table_args__ = (
        CheckConstraint(
            "unit_price > 0 AND total_value > 0",
            name="ck_quote_dispatch_positive_values",
        ),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    quote_vendor_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.quote_vendor_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.quote_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Email Addresses & Attribution
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    quote_reference_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Quoted Commercial Consideration
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    incoterm: Mapped[str] = mapped_column(String(30), default="EXW", nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    payment_terms: Mapped[str] = mapped_column(Text, nullable=False)
    commercial_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Email Artifacts & Delivery Status
    email_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_body_html: Mapped[str] = mapped_column(Text, nullable=False)

    delivery_status: Mapped[EmailDeliveryStatus] = mapped_column(
        Enum(
            EmailDeliveryStatus,
            name="email_delivery_status",
            schema="business",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=EmailDeliveryStatus.SENT,
        nullable=False,
        index=True,
    )
    external_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    quote_vendor_match: Mapped["QuoteVendorMatch"] = relationship(
        "QuoteVendorMatch", back_populates="dispatches"
    )
    quote_request: Mapped["QuoteRequest"] = relationship("QuoteRequest")
    vendor: Mapped["User"] = relationship("User", foreign_keys=[vendor_id])
