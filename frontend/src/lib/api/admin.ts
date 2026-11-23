import { request } from '@/lib/api/client';
import {
  UserIdentityResponse,
  UserLoginRequest,
  UserLoginResponse,
  UserLogoutResponse,
} from '@/types/auth';
import { AdminProposalListResponse, ProposalDetail } from '@/types/proposal';
import { AdminQuoteDetailResponse, AdminQuoteListResponse } from '@/types/quote';

export interface AdminOverviewStats {
  total_users: number;
  active_users: number;
  profile_completion_pct: number;
  active_users_today: number;
  total_conversations: number;
  admin_username: string;
  generated_at: string;
}

/**
 * Authenticate administrator credentials against dedicated admin gateway.
 * Strictly verifies is_admin status on backend (rejects regular attendees with 403).
 */
export async function adminLogin(credentials: UserLoginRequest): Promise<UserLoginResponse> {
  return request<UserLoginResponse>('/admin/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

/**
 * Retrieve verified administrator identity profile.
 */
export async function getAdminMe(): Promise<UserIdentityResponse> {
  return request<UserIdentityResponse>('/admin/auth/me', {
    method: 'GET',
  });
}

/**
 * Revoke administrator session and clear session cookie.
 */
export async function adminLogout(): Promise<UserLogoutResponse> {
  return request<UserLogoutResponse>('/admin/auth/logout', {
    method: 'POST',
  });
}

/**
 * Fetch platform-wide metrics for the administrative dashboard foundation.
 */
export async function getAdminOverview(): Promise<AdminOverviewStats> {
  return request<AdminOverviewStats>('/admin/overview', {
    method: 'GET',
  });
}

export interface AdminUserSummary {
  id: string;
  username: string;
  email: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  phone_number?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;

  has_profile: boolean;
  bio_summary?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  location?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  intent?: string | null;
  availability?: string | null;
  allow_agent_matching?: boolean | null;
  current_mood?: string | null;

  hobbies: string[];
  topics: string[];

  bookmarks_count: number;
  attendance_count: number;
  conversations_count: number;
  activity_events_count: number;
  has_business_profile?: boolean;
  commercial_roles?: string[];
  offerings_count?: number;
  requirements_count?: number;
  last_active_at?: string | null;
}

export interface AdminUserDirectoryStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  with_profile: number;
  active_today: number;
  with_business_profile?: number;
}

export interface AdminUsersListResponse {
  items: AdminUserSummary[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  stats: AdminUserDirectoryStats;
}

export interface AdminUsersQueryOptions {
  search?: string;
  status?: string;
  profile_status?: string;
  gender?: string;
  registration_period?: string;
  commercial_role?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

/**
 * Fetch paginated users directory with server-side filters and engagement metrics (Phase 3).
 */
export async function getAdminUsers(options?: AdminUsersQueryOptions): Promise<AdminUsersListResponse> {
  const params = new URLSearchParams();
  if (options?.search) params.set('search', options.search);
  if (options?.status && options.status !== 'all') params.set('status', options.status);
  if (options?.profile_status && options.profile_status !== 'all') params.set('profile_status', options.profile_status);
  if (options?.gender && options.gender !== 'all') params.set('gender', options.gender);
  if (options?.registration_period && options.registration_period !== 'all') params.set('registration_period', options.registration_period);
  if (options?.commercial_role && options.commercial_role !== 'all') params.set('commercial_role', options.commercial_role);
  if (options?.sort_by) params.set('sort_by', options.sort_by);
  if (options?.sort_order) params.set('sort_order', options.sort_order);
  if (options?.page) params.set('page', String(options.page));
  if (options?.limit) params.set('limit', String(options.limit));

  const qs = params.toString();
  return request<AdminUsersListResponse>(`/admin/users${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

// ==========================================
// Phase 4: Comprehensive User Detail Types & APIs
// ==========================================

export interface AdminUserAccountDetail {
  id: string;
  username: string;
  email: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  phone_number?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserProfileDetail {
  has_profile: boolean;
  bio_summary?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  location?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  intent?: string | null;
  availability?: string | null;
  allow_agent_matching?: boolean | null;
  current_mood?: string | null;
  hobbies: string[];
  topics: string[];
}

export interface AdminUserSessionItem {
  id: string;
  created_at: string;
  expires_at: string;
  last_accessed_at: string;
  revoked_at?: string | null;
  is_active: boolean;
  ip_address?: string | null;
  user_agent?: string | null;
}

export interface AdminUserSessionsBlock {
  total_logins: number;
  active_sessions_count: number;
  recent_sessions: AdminUserSessionItem[];
}

export interface AdminBookmarkedSessionItem {
  session_id: string;
  title: string;
  track_name?: string | null;
  hall_room: string;
  speaker_names?: string | null;
  start_time: string;
  end_time: string;
  created_at: string;
}

export interface AdminAttendanceDecisionItem {
  session_id: string;
  title: string;
  decision: string;
  hall_room: string;
  start_time: string;
  end_time: string;
}

export interface AdminUserAgendaBlock {
  bookmarks_count: number;
  bookmarks: AdminBookmarkedSessionItem[];
  attendance_decisions: AdminAttendanceDecisionItem[];
}

export interface AdminConversationHistoryItem {
  conversation_id: string;
  partner_id: string;
  partner_name: string;
  partner_username: string;
  role: 'INITIATOR' | 'TARGET';
  status: string;
  outcome?: string | null;
  message_count: number;
  created_at: string;
  last_interaction_at?: string | null;
}

export interface AdminUserConversationsBlock {
  total_count: number;
  initiated_count: number;
  participated_count: number;
  history: AdminConversationHistoryItem[];
}

export interface AdminActivityItem {
  id: number;
  event_type: string;
  feature_name: string;
  target_resource_id?: string | null;
  created_at: string;
}

export interface AdminUserActivityBlock {
  total_events: number;
  recent_events: AdminActivityItem[];
}

export interface AdminOfferingDetail {
  id: string;
  business_profile_id: string;
  custom_product_title: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  specifications_text?: string | null;
  declared_monthly_capacity?: number | null;
  declared_committed_volume?: number | null;
  capacity_unit?: string | null;
  minimum_order_quantity?: number | null;
  lead_time_days?: number | null;
  geographic_coverage: string[];
  offers_test_certificates: boolean;
  vendor_certifications: string[];
  open_to_distribution: boolean;
  target_distribution_regions: string[];
  distributor_tier_preferred?: string | null;
  is_public_indicative: boolean;
  indicative_price_min?: number | null;
  indicative_price_max?: number | null;
  price_currency: string;
  pricing_basis?: string | null;
  offers_delivered_pricing: boolean;
  quote_validity_days: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminRequirementDetail {
  id: string;
  business_profile_id: string;
  custom_requirement_title: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  required_quantity?: number | null;
  quantity_unit?: string | null;
  delivery_city?: string | null;
  delivery_country?: string | null;
  target_timeline_days?: number | null;
  target_budget_indication?: number | null;
  is_budget_public: boolean;
  urgency: string;
  excluded_supplier_ids: string[];
  allow_substitutes: boolean;
  required_certifications: string[];
  is_feedstock_procurement: boolean;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminBusinessProfileDetail {
  id: string;
  user_id: string;
  is_buyer: boolean;
  is_supplier: boolean;
  is_vendor: boolean;
  is_distributor: boolean;
  is_partner: boolean;
  allow_business_matching: boolean;
  company_name?: string | null;
  industry?: string | null;
  business_website?: string | null;
  hq_city?: string | null;
  hq_country?: string | null;
  company_bio?: string | null;
  distributor_territories: string[];
  warehousing_capacity_sqft?: number | null;
  retail_dealer_count?: number | null;
  partnership_types: string[];
  partnership_interests: string[];
  offerings: AdminOfferingDetail[];
  requirements: AdminRequirementDetail[];
  created_at: string;
  updated_at: string;
}

export interface AdminUserDetailResponse {
  account: AdminUserAccountDetail;
  profile: AdminUserProfileDetail;
  sessions: AdminUserSessionsBlock;
  agenda: AdminUserAgendaBlock;
  conversations: AdminUserConversationsBlock;
  activity: AdminUserActivityBlock;
  business_profile?: AdminBusinessProfileDetail | null;
}

export interface AdminUpdateUserStatusRequest {
  is_active: boolean;
  reason?: string;
}

export interface AdminUpdateUserStatusResponse {
  status: string;
  user_id: string;
  is_active: boolean;
  revoked_sessions_count: number;
  detail: string;
}

/**
 * Retrieve comprehensive attendee details, profile, sessions, agenda, and activity (Phase 4).
 */
export async function getAdminUserDetail(userId: string): Promise<AdminUserDetailResponse> {
  return request<AdminUserDetailResponse>(`/admin/users/${userId}`, {
    method: 'GET',
  });
}

/**
 * Administratively activate or suspend an account with instant session revocation (Phase 4).
 */
export async function updateAdminUserStatus(
  userId: string,
  payload: AdminUpdateUserStatusRequest
): Promise<AdminUpdateUserStatusResponse> {
  return request<AdminUpdateUserStatusResponse>(`/admin/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

// =============================================================================
// Phase 4: Admin Organizers & Conference Review Queue API Clients
// =============================================================================

export interface AdminOrganizerItem {
  id: string;
  user_id: string;
  username: string;
  organizer_type: string;
  representative_name: string;
  organization_name?: string | null;
  designation?: string | null;
  professional_email: string;
  contact_phone: string;
  city: string;
  state_province?: string | null;
  country: string;
  focus_areas: string[];
  verification_status: string;
  conferences_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminOrganizersListStats {
  total_organizers: number;
  verified_count: number;
  pending_review_count: number;
  total_conferences_managed: number;
}

export interface AdminOrganizersListResponse {
  items: AdminOrganizerItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  stats: AdminOrganizersListStats;
}

export interface AdminConferenceOrganizerSummary {
  id: string;
  user_id: string;
  username: string;
  representative_name: string;
  organization_name?: string | null;
  organizer_type?: string | null;
  designation?: string | null;
  professional_email: string;
  contact_phone: string;
  website_url?: string | null;
  address_line1?: string | null;
  city: string;
  state_province?: string | null;
  postal_code?: string | null;
  country: string;
  bio?: string | null;
  experience_years?: number | null;
  focus_areas?: string[];
  verification_status: string;
}

export interface AdminConferenceSessionItem {
  id: string;
  conference_id: string;
  title: string;
  abstract?: string | null;
  speaker_names?: string | null;
  track_name?: string | null;
  hall_room: string;
  start_time: string;
  end_time: string;
  is_cancelled: boolean;
  created_at: string;
}

export interface AdminConferenceReviewLogItem {
  id: number;
  reviewer_id?: string | null;
  reviewer_username?: string | null;
  from_status: string;
  to_status: string;
  notes?: string | null;
  created_at: string;
}

export interface AdminConferenceQueueItem {
  id: string;
  organizer_id?: string | null;
  organizer?: AdminConferenceOrganizerSummary | null;
  title: string;
  summary?: string | null;
  category?: string | null;
  format: string;
  venue_name: string;
  timezone: string;
  start_date: string;
  end_date: string;
  city?: string | null;
  country?: string | null;
  capacity?: number | null;
  status: string;
  sessions_count: number;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminConferenceQueueStats {
  total_in_review: number;
  total_published: number;
  total_draft: number;
  total_changes_requested: number;
  total_rejected: number;
}

export interface AdminConferenceQueueResponse {
  items: AdminConferenceQueueItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  stats: AdminConferenceQueueStats;
}

export interface AdminConferenceDetailResponse {
  id: string;
  organizer_id?: string | null;
  organizer?: AdminConferenceOrganizerSummary | null;
  title: string;
  summary?: string | null;
  description?: string | null;
  category?: string | null;
  format: string;
  venue_name: string;
  timezone: string;
  start_date: string;
  end_date: string;
  start_time?: string | null;
  end_time?: string | null;
  registration_opens_at?: string | null;
  registration_closes_at?: string | null;
  capacity?: number | null;
  target_audience?: string | null;
  website_url?: string | null;
  banner_url?: string | null;
  meeting_url?: string | null;
  formatted_address?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  place_id?: string | null;
  city?: string | null;
  state_province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  status: string;
  review_feedback?: string | null;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
  sessions: AdminConferenceSessionItem[];
  review_logs: AdminConferenceReviewLogItem[];
}

export interface AdminConferenceDecisionRequest {
  decision: 'APPROVE' | 'REQUEST_CHANGES' | 'REJECT';
  feedback?: string;
}

export interface AdminConferenceDecisionResponse {
  status: string;
  conference_id: string;
  new_status: string;
  detail: string;
}

/**
 * Retrieve paginated active organizers directory with verification stats.
 */
export async function getAdminOrganizers(params?: {
  search?: string;
  verification_status?: string;
  organizer_type?: string;
  page?: number;
  limit?: number;
}): Promise<AdminOrganizersListResponse> {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.verification_status && params.verification_status !== 'all') {
    query.set('verification_status', params.verification_status);
  }
  if (params?.organizer_type && params.organizer_type !== 'all') {
    query.set('organizer_type', params.organizer_type);
  }
  if (params?.page) query.set('page', params.page.toString());
  if (params?.limit) query.set('limit', params.limit.toString());

  const qs = query.toString();
  return request<AdminOrganizersListResponse>(`/admin/organizers${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Update organizer profile verification status (VERIFIED / SUSPENDED / PENDING_REVIEW).
 */
export async function updateAdminOrganizerVerification(
  organizerId: string,
  payload: { verification_status: string; reason?: string }
): Promise<{ status: string; organizer_id: string; verification_status: string; detail: string }> {
  return request(`/admin/organizers/${organizerId}/verification`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

/**
 * Retrieve paginated conference review queue with state breakdown stats.
 */
export async function getAdminConferences(params?: {
  search?: string;
  status_filter?: string;
  category?: string;
  format_filter?: string;
  page?: number;
  limit?: number;
}): Promise<AdminConferenceQueueResponse> {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.status_filter && params.status_filter !== 'all') {
    query.set('status_filter', params.status_filter);
  }
  if (params?.category && params.category !== 'all') {
    query.set('category', params.category);
  }
  if (params?.format_filter && params.format_filter !== 'all') {
    query.set('format_filter', params.format_filter);
  }
  if (params?.page) query.set('page', params.page.toString());
  if (params?.limit) query.set('limit', params.limit.toString());

  const qs = query.toString();
  return request<AdminConferenceQueueResponse>(`/admin/conferences${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Retrieve detailed conference submission, agenda sessions, and organizer footprint for review.
 */
export async function getAdminConferenceDetail(conferenceId: string): Promise<AdminConferenceDetailResponse> {
  return request<AdminConferenceDetailResponse>(`/admin/conferences/${conferenceId}`, {
    method: 'GET',
  });
}

/**
 * Submit administrative conference decision (APPROVE / REQUEST_CHANGES / REJECT) with feedback.
 */
export async function submitAdminConferenceDecision(
  conferenceId: string,
  payload: AdminConferenceDecisionRequest
): Promise<AdminConferenceDecisionResponse> {
  return request<AdminConferenceDecisionResponse>(`/admin/conferences/${conferenceId}/decision`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Retrieve paginated commercial proposals directory for administrative governance (Subphase 8).
 */
export async function getAdminProposals(params?: {
  status?: string;
  proposal_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<AdminProposalListResponse> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== 'all') query.append('status', params.status);
  if (params?.proposal_type && params.proposal_type !== 'all') query.append('proposal_type', params.proposal_type);
  if (params?.search && params.search.trim()) query.append('search', params.search.trim());
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const queryString = query.toString();
  return request<AdminProposalListResponse>(`/admin/proposals${queryString ? `?${queryString}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Retrieve full forensic inspection sheet for a single commercial proposal (Subphase 8).
 */
export async function getAdminProposalDetail(proposalId: string): Promise<ProposalDetail> {
  return request<ProposalDetail>(`/admin/proposals/${proposalId}`, {
    method: 'GET',
  });
}

/**
 * Retrieve all proposals where specified user is proposer or recipient (Subphase 8).
 */
export async function getAdminUserProposals(
  userId: string,
  params?: { page?: number; page_size?: number }
): Promise<AdminProposalListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const queryString = query.toString();
  return request<AdminProposalListResponse>(`/admin/users/${userId}/proposals${queryString ? `?${queryString}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Retrieve paginated commercial quotations directory with metrics for administrators.
 */
export async function getAdminQuotes(params?: {
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<AdminQuoteListResponse> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== 'all') query.append('status', params.status);
  if (params?.search && params.search.trim()) query.append('search', params.search.trim());
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const queryString = query.toString();
  return request<AdminQuoteListResponse>(`/admin/quotes${queryString ? `?${queryString}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Retrieve full forensic inspection sheet for a single quotation transmission.
 */
export async function getAdminQuoteDetail(quoteId: string): Promise<AdminQuoteDetailResponse> {
  return request<AdminQuoteDetailResponse>(`/admin/quotes/${quoteId}`, {
    method: 'GET',
  });
}

/**
 * Retrieve all quotes where specified user is vendor or customer.
 */
export async function getAdminUserQuotes(
  userId: string,
  params?: { page?: number; page_size?: number }
): Promise<AdminQuoteListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const queryString = query.toString();
  return request<AdminQuoteListResponse>(`/admin/users/${userId}/quotes${queryString ? `?${queryString}` : ''}`, {
    method: 'GET',
  });
}


