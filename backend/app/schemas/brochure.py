"""Pydantic v2 schemas for company digital brochures, pages, and sponsored ads."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.db.models.brochure import AdEventType, AdPlacementType


class BrochurePageItem(BaseModel):
    """Single page representation in a digital brochure."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brochure_id: uuid.UUID
    page_number: int
    image_url: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    aspect_ratio: float = 0.707
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime


class BrochureAdItem(BaseModel):
    """Sponsored ad creative representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sponsor_name: str
    title: str
    placement_type: AdPlacementType
    creative_image_url: str
    destination_url: str
    tagline: Optional[str] = None
    is_active: bool = True


class CompanyBrochureDetail(BaseModel):
    """Comprehensive company brochure model with full page sequence."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_profile_id: uuid.UUID
    owner_user_id: uuid.UUID
    company_name: str
    title: str
    description: Optional[str] = None
    slug: str
    is_published: bool
    view_count: int
    total_pages: int = 0
    pages: List[BrochurePageItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BrochureDirectoryItem(BaseModel):
    """Public discovery summary for exhibitor catalogs directory."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_profile_id: uuid.UUID
    owner_user_id: uuid.UUID
    company_name: str
    title: str
    description: Optional[str] = None
    slug: str
    total_pages: int = 0
    cover_image_url: Optional[str] = None
    cover_thumbnail_url: Optional[str] = None
    view_count: int = 0
    created_at: datetime


class CompanyBrochureUpdate(BaseModel):
    """Payload to update brochure metadata."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    slug: Optional[str] = Field(None, max_length=120)
    is_published: Optional[bool] = None


class BrochurePageReorderRequest(BaseModel):
    """Ordered list of page IDs to resequence a brochure."""
    page_ids: List[uuid.UUID]


class BrochurePublicView(BaseModel):
    """Publicly visible flipbook payload with resolved ads."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    title: str
    description: Optional[str] = None
    slug: str
    total_pages: int
    pages: List[BrochurePageItem]
    top_banner_ad: Optional[BrochureAdItem] = None
    pre_roll_ad: Optional[BrochureAdItem] = None


class BrochureAdCreate(BaseModel):
    """Admin payload to create a new sponsored ad campaign."""
    sponsor_name: str = Field(..., max_length=150)
    title: str = Field(..., max_length=200)
    placement_type: AdPlacementType
    creative_image_url: str
    destination_url: str
    tagline: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    brochure_ids: Optional[List[uuid.UUID]] = None


class BrochureAdUpdate(BaseModel):
    """Admin payload to edit an existing ad campaign."""
    sponsor_name: Optional[str] = Field(None, max_length=150)
    title: Optional[str] = Field(None, max_length=200)
    placement_type: Optional[AdPlacementType] = None
    creative_image_url: Optional[str] = None
    destination_url: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    brochure_ids: Optional[List[uuid.UUID]] = None


class BrochureAdEventCreate(BaseModel):
    """Telemetry payload logging an impression or click."""
    event_type: AdEventType


class AdminBrochureCompanyTarget(BaseModel):
    """Target company brochure summary for ad mapping."""
    model_config = ConfigDict(from_attributes=True)

    brochure_id: uuid.UUID
    company_name: str
    title: str
    slug: str


class AdminBrochureAdDetail(BaseModel):
    """Admin-facing ad model with performance metrics and assigned companies."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sponsor_name: str
    title: str
    placement_type: AdPlacementType
    creative_image_url: str
    destination_url: str
    tagline: Optional[str] = None
    is_active: bool = True
    is_global: bool = True
    assigned_brochure_ids: List[uuid.UUID] = Field(default_factory=list)
    assigned_brochures: List[AdminBrochureCompanyTarget] = Field(default_factory=list)
    impression_count: int = 0
    click_count: int = 0
    ctr: float = 0.0
    created_at: datetime
    updated_at: datetime


class AdminBrochureAdsListResponse(BaseModel):
    """Paginated or complete list of sponsored ads with portfolio metrics."""
    items: List[AdminBrochureAdDetail]
    total_active_ads: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    average_ctr: float = 0.0


class AdminBrochureAdAssignRequest(BaseModel):
    """Payload to target an ad to specific brochures or mark as global."""
    is_global: bool = False
    brochure_ids: List[uuid.UUID] = Field(default_factory=list)


class AdminCompanyBrochureOption(BaseModel):
    """Selectable company brochure entity for ad targeting checklist."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    title: str
    slug: str
    total_pages: int = 0
    is_published: bool = True


class FlipbookViewerSettings(BaseModel):
    """Global summit flipbook acoustics and page-turn animation configuration."""
    sound_preset: str = "PAPER_RUSTLE"
    animation_preset: str = "BOOK_CURL_3D"


class FlipbookViewerSettingsUpdate(BaseModel):
    """Payload to update summit flipbook acoustics and animation defaults."""
    sound_preset: str
    animation_preset: str


class BrochurePageReadEventCreate(BaseModel):
    """Telemetry payload recorded when a reader views one or more brochure pages."""
    page_numbers: List[int] = Field(..., min_length=1, max_length=4)
    session_key: Optional[str] = Field(None, max_length=64)
    view_mode: Optional[str] = Field(None, max_length=20)


class ReadTimeSeriesPoint(BaseModel):
    """Single chronological bucket for magazine opens and page reads."""
    bucket: str
    label: str
    opens: int = 0
    page_reads: int = 0


class BrochurePageAnalyticsItem(BaseModel):
    """Per-page engagement breakdown for a brochure."""
    page_id: Optional[uuid.UUID] = None
    page_number: int
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    read_count: int = 0
    total_read_count: int = 0
    unique_readers: int = 0
    share_pct: float = 0.0
    last_read_at: Optional[datetime] = None


class BrochureAnalyticsDetail(BaseModel):
    """Detailed magazine & page read analytics for a single company brochure."""
    brochure_id: uuid.UUID
    company_name: str
    title: str
    slug: str
    is_published: bool
    total_pages: int = 0
    period: str = "7d"
    total_views_all_time: int = 0
    period_views: int = 0
    total_page_reads_all_time: int = 0
    period_page_reads: int = 0
    unique_sessions: int = 0
    avg_pages_per_session: float = 0.0
    top_page_number: Optional[int] = None
    last_activity_at: Optional[datetime] = None
    cover_thumbnail_url: Optional[str] = None
    time_series: List[ReadTimeSeriesPoint] = Field(default_factory=list)
    pages: List[BrochurePageAnalyticsItem] = Field(default_factory=list)


class AdminBrochureAnalyticsOverview(BaseModel):
    """Admin-wide analytics across all available magazines with combined and per-magazine drilldowns."""
    period: str = "7d"
    generated_at: datetime
    total_magazines: int = 0
    published_magazines: int = 0
    total_views_all_time: int = 0
    period_views: int = 0
    total_page_reads_all_time: int = 0
    period_page_reads: int = 0
    unique_sessions: int = 0
    combined_time_series: List[ReadTimeSeriesPoint] = Field(default_factory=list)
    magazines: List[BrochureAnalyticsDetail] = Field(default_factory=list)



