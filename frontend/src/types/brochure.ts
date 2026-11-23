/**
 * TypeScript interfaces for Company Digital Brochure and Flipbook System (Phase 1 & 2).
 */

export type AdPlacementType = 'BANNER_TOP' | 'PRE_ROLL';
export type AdEventType = 'IMPRESSION' | 'CLICK';

export interface BrochurePageItem {
  id: string;
  brochure_id: string;
  page_number: number;
  image_url: string;
  thumbnail_url?: string | null;
  title?: string | null;
  aspect_ratio: number;
  width?: number | null;
  height?: number | null;
  file_size_bytes?: number | null;
  created_at: string;
}

export interface BrochureAdItem {
  id: string;
  sponsor_name: string;
  title: string;
  placement_type: AdPlacementType;
  creative_image_url: string;
  destination_url: string;
  tagline?: string | null;
  is_active: boolean;
}

export interface CompanyBrochureDetail {
  id: string;
  business_profile_id: string;
  owner_user_id: string;
  company_name: string;
  title: string;
  description?: string | null;
  slug: string;
  is_published: boolean;
  view_count: number;
  total_pages: number;
  pages: BrochurePageItem[];
  created_at: string;
  updated_at: string;
}

export interface CompanyBrochureUpdate {
  title?: string;
  description?: string;
  slug?: string;
  is_published?: boolean;
}

export interface BrochurePublicView {
  id: string;
  company_name: string;
  title: string;
  description?: string | null;
  slug: string;
  total_pages: number;
  pages: BrochurePageItem[];
  top_banner_ad?: BrochureAdItem | null;
  pre_roll_ad?: BrochureAdItem | null;
}

export interface BrochureDirectoryItem {
  id: string;
  business_profile_id: string;
  owner_user_id: string;
  company_name: string;
  title: string;
  description?: string | null;
  slug: string;
  total_pages: number;
  cover_image_url?: string | null;
  cover_thumbnail_url?: string | null;
  view_count: number;
  created_at: string;
}

export interface AdminBrochureCompanyTarget {
  brochure_id: string;
  company_name: string;
  title: string;
  slug: string;
}

export interface AdminBrochureAdDetail {
  id: string;
  sponsor_name: string;
  title: string;
  placement_type: AdPlacementType;
  creative_image_url: string;
  destination_url: string;
  tagline?: string | null;
  is_active: boolean;
  is_global: boolean;
  assigned_brochure_ids: string[];
  assigned_brochures: AdminBrochureCompanyTarget[];
  impression_count: number;
  click_count: number;
  ctr: number;
  created_at: string;
  updated_at: string;
}

export interface AdminBrochureAdsListResponse {
  items: AdminBrochureAdDetail[];
  total_active_ads: number;
  total_impressions: number;
  total_clicks: number;
  average_ctr: number;
}

export interface AdminBrochureAdAssignRequest {
  is_global: boolean;
  brochure_ids: string[];
}

export interface AdminCompanyBrochureOption {
  id: string;
  company_name: string;
  title: string;
  slug: string;
  total_pages: number;
  is_published: boolean;
}

export interface BrochureAdCreatePayload {
  sponsor_name: string;
  title: string;
  placement_type: AdPlacementType;
  creative_image_url: string;
  destination_url: string;
  tagline?: string;
  is_active?: boolean;
  brochure_ids?: string[];
}

export interface BrochureAdUpdatePayload {
  sponsor_name?: string;
  title?: string;
  placement_type?: AdPlacementType;
  creative_image_url?: string;
  destination_url?: string;
  tagline?: string;
  is_active?: boolean;
  brochure_ids?: string[];
}

export type AnalyticsPeriod = '24h' | '7d' | '30d' | 'all';

export interface ReadTimeSeriesPoint {
  bucket: string;
  label: string;
  opens: number;
  page_reads: number;
}

export interface BrochurePageAnalyticsItem {
  page_id?: string | null;
  page_number: number;
  title?: string | null;
  thumbnail_url?: string | null;
  image_url?: string | null;
  read_count: number;
  total_read_count: number;
  unique_readers: number;
  share_pct: number;
  last_read_at?: string | null;
}

export interface BrochureAnalyticsDetail {
  brochure_id: string;
  company_name: string;
  title: string;
  slug: string;
  is_published: boolean;
  total_pages: number;
  period: AnalyticsPeriod | string;
  total_views_all_time: number;
  period_views: number;
  total_page_reads_all_time: number;
  period_page_reads: number;
  unique_sessions: number;
  avg_pages_per_session: number;
  top_page_number?: number | null;
  last_activity_at?: string | null;
  cover_thumbnail_url?: string | null;
  time_series: ReadTimeSeriesPoint[];
  pages: BrochurePageAnalyticsItem[];
}

export interface AdminBrochureAnalyticsOverview {
  period: AnalyticsPeriod | string;
  generated_at: string;
  total_magazines: number;
  published_magazines: number;
  total_views_all_time: number;
  period_views: number;
  total_page_reads_all_time: number;
  period_page_reads: number;
  unique_sessions: number;
  combined_time_series: ReadTimeSeriesPoint[];
  magazines: BrochureAnalyticsDetail[];
}

