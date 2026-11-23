"""Brochure and interactive digital flipbook models in schema brochures."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.business import BusinessProfile
    from app.db.models.user import User


class AdPlacementType(str, enum.Enum):
    """Supported ad slot placements in digital flipbook viewer."""
    BANNER_TOP = "BANNER_TOP"
    PRE_ROLL = "PRE_ROLL"


class AdEventType(str, enum.Enum):
    """Impression and engagement telemetry events for brochure ads."""
    IMPRESSION = "IMPRESSION"
    CLICK = "CLICK"


class CompanyBrochure(Base):
    """Company digital catalog / brochure entity."""

    __tablename__ = "company_brochures"
    __table_args__ = {"schema": "brochures"}

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
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(
        String(200),
        default="Company Catalog & Brochure",
        server_default=text("'Company Catalog & Brochure'"),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)

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
    pages: Mapped[List["BrochurePage"]] = relationship(
        "BrochurePage",
        back_populates="brochure",
        cascade="all, delete-orphan",
        order_by="BrochurePage.page_number",
    )
    ad_assignments: Mapped[List["BrochureAdAssignment"]] = relationship(
        "BrochureAdAssignment",
        back_populates="brochure",
        cascade="all, delete-orphan",
    )
    read_events: Mapped[List["BrochurePageReadEvent"]] = relationship(
        "BrochurePageReadEvent",
        back_populates="brochure",
        cascade="all, delete-orphan",
    )


class BrochurePage(Base):
    """Individual high-resolution page inside a digital flipbook brochure."""

    __tablename__ = "brochure_pages"
    __table_args__ = (
        UniqueConstraint("brochure_id", "page_number", name="uq_brochure_page_number"),
        {"schema": "brochures"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    brochure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.company_brochures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    aspect_ratio: Mapped[Decimal] = mapped_column(
        Numeric(5, 3),
        default=Decimal("0.707"),
        server_default=text("0.707"),
        nullable=False,
    )
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    brochure: Mapped["CompanyBrochure"] = relationship("CompanyBrochure", back_populates="pages")


class BrochureAd(Base):
    """Administrative sponsored ad campaign."""

    __tablename__ = "brochure_ads"
    __table_args__ = {"schema": "brochures"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    sponsor_name: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    placement_type: Mapped[AdPlacementType] = mapped_column(
        Enum(AdPlacementType, schema="brochures", name="ad_placement_type", native_enum=True),
        nullable=False,
    )
    creative_image_url: Mapped[str] = mapped_column(Text, nullable=False)
    destination_url: Mapped[str] = mapped_column(Text, nullable=False)
    tagline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    assignments: Mapped[List["BrochureAdAssignment"]] = relationship(
        "BrochureAdAssignment",
        back_populates="ad",
        cascade="all, delete-orphan",
    )
    events: Mapped[List["BrochureAdEvent"]] = relationship(
        "BrochureAdEvent",
        back_populates="ad",
        cascade="all, delete-orphan",
    )


class BrochureAdAssignment(Base):
    """Targeting matrix mapping sponsored ads to specific brochures (or NULL for global conference)."""

    __tablename__ = "brochure_ad_assignments"
    __table_args__ = (
        UniqueConstraint("ad_id", "brochure_id", name="uq_ad_brochure_assignment"),
        {"schema": "brochures"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.brochure_ads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brochure_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.company_brochures.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=10, server_default=text("10"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ad: Mapped["BrochureAd"] = relationship("BrochureAd", back_populates="assignments")
    brochure: Mapped[Optional["CompanyBrochure"]] = relationship("CompanyBrochure", back_populates="ad_assignments")


class BrochureAdEvent(Base):
    """Telemetry records for impression and click engagement."""

    __tablename__ = "brochure_ad_events"
    __table_args__ = {"schema": "brochures"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.brochure_ads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brochure_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.company_brochures.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[AdEventType] = mapped_column(
        Enum(AdEventType, schema="brochures", name="ad_event_type", native_enum=True),
        nullable=False,
    )
    viewer_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ad: Mapped["BrochureAd"] = relationship("BrochureAd", back_populates="events")


class BrochurePageReadEvent(Base):
    """Time-series telemetry records for magazine opens and individual page reads."""

    __tablename__ = "brochure_page_read_events"
    __table_args__ = (
        Index("ix_brochure_page_read_events_brochure_created", "brochure_id", "created_at"),
        Index("ix_brochure_page_read_events_brochure_kind_page", "brochure_id", "event_kind", "page_number"),
        Index("ix_brochure_page_read_events_created_at", "created_at"),
        {"schema": "brochures"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    brochure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.company_brochures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brochures.brochure_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_kind: Mapped[str] = mapped_column(
        String(16),
        default="PAGE_READ",
        server_default=text("'PAGE_READ'"),
        nullable=False,
    )
    session_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    view_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    viewer_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    brochure: Mapped["CompanyBrochure"] = relationship("CompanyBrochure", back_populates="read_events")
