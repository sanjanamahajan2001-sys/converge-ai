"""Pydantic schemas for the Converge AI Admin Portal (Phase 2 & Phase 3)."""
from datetime import date, datetime, time
from decimal import Decimal
import enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AdminUserSummary(BaseModel):
    """Administrative detailed summary for a conference attendee user."""

    id: UUID
    username: str
    email: str
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    # Profile & Demographics
    has_profile: bool = False
    bio_summary: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    intent: Optional[str] = None
    availability: Optional[str] = None
    allow_agent_matching: Optional[bool] = None
    current_mood: Optional[str] = None

    # Interests, Hobbies & Keywords
    hobbies: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)

    # Conference Telemetry & Participation
    bookmarks_count: int = 0
    attendance_count: int = 0
    conversations_count: int = 0
    activity_events_count: int = 0

    # Commercial & Business Profile Telemetry
    has_business_profile: bool = False
    commercial_roles: List[str] = Field(default_factory=list)
    offerings_count: int = 0
    requirements_count: int = 0

    # Activity Timestamps
    last_active_at: Optional[datetime] = None


class AdminUserDirectoryStats(BaseModel):
    """Aggregate telemetry for the users directory header."""

    total_users: int
    active_users: int
    inactive_users: int
    with_profile: int
    active_today: int
    with_business_profile: int = 0


class AdminUsersListResponse(BaseModel):
    """Paginated response containing conference user summaries and directory stats."""

    items: List[AdminUserSummary]
    total: int
    page: int
    limit: int
    total_pages: int
    stats: AdminUserDirectoryStats


# ==========================================
# Phase 4: Comprehensive User Detail Schemas
# ==========================================

class AdminUserAccountDetail(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class AdminUserProfileDetail(BaseModel):
    has_profile: bool
    bio_summary: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    intent: Optional[str] = None
    availability: Optional[str] = None
    allow_agent_matching: Optional[bool] = None
    current_mood: Optional[str] = None
    hobbies: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)


class AdminUserSessionItem(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AdminUserSessionsBlock(BaseModel):
    total_logins: int
    active_sessions_count: int
    recent_sessions: List[AdminUserSessionItem] = Field(default_factory=list)


class AdminBookmarkedSessionItem(BaseModel):
    session_id: UUID
    title: str
    track_name: Optional[str] = None
    hall_room: str
    speaker_names: Optional[str] = None
    start_time: datetime
    end_time: datetime
    created_at: datetime


class AdminAttendanceDecisionItem(BaseModel):
    session_id: UUID
    title: str
    decision: str
    hall_room: str
    start_time: datetime
    end_time: datetime


class AdminUserAgendaBlock(BaseModel):
    bookmarks_count: int
    bookmarks: List[AdminBookmarkedSessionItem] = Field(default_factory=list)
    attendance_decisions: List[AdminAttendanceDecisionItem] = Field(default_factory=list)


class AdminConversationHistoryItem(BaseModel):
    conversation_id: UUID
    partner_id: UUID
    partner_name: str
    partner_username: str
    role: str  # "INITIATOR" or "TARGET"
    status: str
    outcome: Optional[str] = None
    message_count: int
    created_at: datetime
    last_interaction_at: Optional[datetime] = None


class AdminUserConversationsBlock(BaseModel):
    total_count: int
    initiated_count: int
    participated_count: int
    history: List[AdminConversationHistoryItem] = Field(default_factory=list)


class AdminActivityItem(BaseModel):
    id: int
    event_type: str
    feature_name: str
    target_resource_id: Optional[str] = None
    created_at: datetime


class AdminUserActivityBlock(BaseModel):
    total_events: int
    recent_events: List[AdminActivityItem] = Field(default_factory=list)


class AdminOfferingDetail(BaseModel):
    id: UUID
    business_profile_id: UUID
    custom_product_title: str
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    specifications_text: Optional[str] = None
    declared_monthly_capacity: Optional[Decimal] = None
    declared_committed_volume: Optional[Decimal] = None
    capacity_unit: Optional[str] = None
    minimum_order_quantity: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    geographic_coverage: List[str] = Field(default_factory=list)
    offers_test_certificates: bool = False
    vendor_certifications: List[str] = Field(default_factory=list)
    open_to_distribution: bool = False
    target_distribution_regions: List[str] = Field(default_factory=list)
    distributor_tier_preferred: Optional[str] = None
    is_public_indicative: bool = False
    indicative_price_min: Optional[Decimal] = None
    indicative_price_max: Optional[Decimal] = None
    price_currency: str = "INR"
    pricing_basis: Optional[str] = None
    offers_delivered_pricing: bool = False
    quote_validity_days: int = 30
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class AdminRequirementDetail(BaseModel):
    id: UUID
    business_profile_id: UUID
    custom_requirement_title: str
    product_code: Optional[str] = None
    grade_code: Optional[str] = None
    service_code: Optional[str] = None
    required_quantity: Optional[Decimal] = None
    quantity_unit: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_country: Optional[str] = None
    target_timeline_days: Optional[int] = None
    target_budget_indication: Optional[Decimal] = None
    is_budget_public: bool = False
    urgency: str = "PLANNED"
    excluded_supplier_ids: List[str] = Field(default_factory=list)
    allow_substitutes: bool = False
    required_certifications: List[str] = Field(default_factory=list)
    is_feedstock_procurement: bool = False
    notes: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class AdminBusinessProfileDetail(BaseModel):
    id: UUID
    user_id: UUID
    is_buyer: bool = False
    is_supplier: bool = False
    is_vendor: bool = False
    is_distributor: bool = False
    is_partner: bool = False
    allow_business_matching: bool = False
    company_name: Optional[str] = None
    industry: Optional[str] = None
    business_website: Optional[str] = None
    hq_city: Optional[str] = None
    hq_country: Optional[str] = None
    company_bio: Optional[str] = None
    distributor_territories: List[str] = Field(default_factory=list)
    warehousing_capacity_sqft: Optional[Decimal] = None
    retail_dealer_count: Optional[int] = None
    partnership_types: List[str] = Field(default_factory=list)
    partnership_interests: List[str] = Field(default_factory=list)
    offerings: List[AdminOfferingDetail] = Field(default_factory=list)
    requirements: List[AdminRequirementDetail] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdminUserDetailResponse(BaseModel):
    account: AdminUserAccountDetail
    profile: AdminUserProfileDetail
    sessions: AdminUserSessionsBlock
    agenda: AdminUserAgendaBlock
    conversations: AdminUserConversationsBlock
    activity: AdminUserActivityBlock
    business_profile: Optional[AdminBusinessProfileDetail] = None


class AdminUpdateUserStatusRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = None


class AdminUpdateUserStatusResponse(BaseModel):
    status: str
    user_id: UUID
    is_active: bool
    revoked_sessions_count: int
    detail: str


# =============================================================================
# Organizer Directory & Verification Schemas (Phase 4)
# =============================================================================

class AdminOrganizerItem(BaseModel):
    """Summary item for the active organizers table."""
    id: UUID
    user_id: UUID
    username: str
    organizer_type: str
    representative_name: str
    organization_name: Optional[str] = None
    designation: Optional[str] = None
    professional_email: str
    contact_phone: str
    city: str
    state_province: Optional[str] = None
    country: str
    focus_areas: List[str] = Field(default_factory=list)
    verification_status: str
    conferences_count: int = 0
    created_at: datetime
    updated_at: datetime


class AdminOrganizersListStats(BaseModel):
    total_organizers: int
    verified_count: int
    pending_review_count: int
    total_conferences_managed: int


class AdminOrganizersListResponse(BaseModel):
    items: List[AdminOrganizerItem]
    total: int
    page: int
    limit: int
    total_pages: int
    stats: AdminOrganizersListStats


class AdminUpdateOrganizerVerificationRequest(BaseModel):
    verification_status: str
    reason: Optional[str] = None


class AdminUpdateOrganizerVerificationResponse(BaseModel):
    status: str
    organizer_id: UUID
    verification_status: str
    detail: str


# =============================================================================
# Conference Review Queue & Decision Schemas (Phase 4)
# =============================================================================

class AdminConferenceOrganizerSummary(BaseModel):
    id: UUID
    user_id: UUID
    username: str
    representative_name: str
    organization_name: Optional[str] = None
    organizer_type: Optional[str] = None
    designation: Optional[str] = None
    professional_email: str
    contact_phone: str
    website_url: Optional[str] = None
    address_line1: Optional[str] = None
    city: str
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    bio: Optional[str] = None
    experience_years: Optional[int] = None
    focus_areas: List[str] = Field(default_factory=list)
    verification_status: str


class AdminConferenceSessionItem(BaseModel):
    id: UUID
    conference_id: UUID
    title: str
    abstract: Optional[str] = None
    speaker_names: Optional[str] = None
    track_name: Optional[str] = None
    hall_room: str
    start_time: datetime
    end_time: datetime
    is_cancelled: bool
    created_at: datetime


class AdminConferenceReviewLogItem(BaseModel):
    id: int
    reviewer_id: Optional[UUID] = None
    reviewer_username: Optional[str] = None
    from_status: str
    to_status: str
    notes: Optional[str] = None
    created_at: datetime


class AdminConferenceQueueItem(BaseModel):
    """Conference item in the admin review queue."""
    id: UUID
    organizer_id: Optional[UUID] = None
    organizer: Optional[AdminConferenceOrganizerSummary] = None
    title: str
    summary: Optional[str] = None
    category: Optional[str] = None
    format: str
    venue_name: str
    timezone: str
    start_date: date
    end_date: date
    city: Optional[str] = None
    country: Optional[str] = None
    capacity: Optional[int] = None
    status: str
    sessions_count: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AdminConferenceQueueStats(BaseModel):
    total_in_review: int
    total_published: int
    total_draft: int
    total_changes_requested: int
    total_rejected: int


class AdminConferenceQueueResponse(BaseModel):
    items: List[AdminConferenceQueueItem]
    total: int
    page: int
    limit: int
    total_pages: int
    stats: AdminConferenceQueueStats


class AdminConferenceDetailResponse(BaseModel):
    """Comprehensive conference inspection payload for admin reviewer."""
    id: UUID
    organizer_id: Optional[UUID] = None
    organizer: Optional[AdminConferenceOrganizerSummary] = None
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    format: str
    venue_name: str
    timezone: str
    start_date: date
    end_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    registration_opens_at: Optional[datetime] = None
    registration_closes_at: Optional[datetime] = None
    capacity: Optional[int] = None
    target_audience: Optional[str] = None
    website_url: Optional[str] = None
    banner_url: Optional[str] = None
    meeting_url: Optional[str] = None
    formatted_address: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    place_id: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    status: str
    review_feedback: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sessions: List[AdminConferenceSessionItem] = Field(default_factory=list)
    review_logs: List[AdminConferenceReviewLogItem] = Field(default_factory=list)


class ConferenceDecisionAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    REJECT = "REJECT"


class AdminConferenceDecisionRequest(BaseModel):
    decision: ConferenceDecisionAction
    feedback: Optional[str] = None


class AdminConferenceDecisionResponse(BaseModel):
    status: str
    conference_id: UUID
    new_status: str
    detail: str


