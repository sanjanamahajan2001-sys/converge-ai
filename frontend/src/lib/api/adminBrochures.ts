/**
 * API client module for Administrative Sponsored Ad Management & Brochure Targeting (Phase 4).
 */

import { request, ApiClientError } from './client';
import {
  AdminBrochureAdAssignRequest,
  AdminBrochureAdDetail,
  AdminBrochureAdsListResponse,
  AdminBrochureAnalyticsOverview,
  AdminCompanyBrochureOption,
  AnalyticsPeriod,
  BrochureAdCreatePayload,
  BrochureAdUpdatePayload,
} from '@/types/brochure';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/converge-api/v1';

export const adminBrochureApi = {
  /**
   * List all sponsored ads with impression/click telemetry and brochure assignment status.
   */
  listAds: async (): Promise<AdminBrochureAdsListResponse> => {
    return request<AdminBrochureAdsListResponse>('/admin/brochures/ads');
  },

  /**
   * Create a new sponsored ad campaign with creative assets and initial brochure assignments.
   */
  createAd: async (payload: BrochureAdCreatePayload): Promise<AdminBrochureAdDetail> => {
    return request<AdminBrochureAdDetail>('/admin/brochures/ads', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Update an existing sponsored ad campaign.
   */
  updateAd: async (
    adId: string,
    payload: BrochureAdUpdatePayload
  ): Promise<AdminBrochureAdDetail> => {
    return request<AdminBrochureAdDetail>(`/admin/brochures/ads/${adId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Delete an ad campaign.
   */
  deleteAd: async (adId: string): Promise<{ success: boolean; deleted_ad_id: string }> => {
    return request<{ success: boolean; deleted_ad_id: string }>(
      `/admin/brochures/ads/${adId}`,
      {
        method: 'DELETE',
      }
    );
  },

  /**
   * Update targeting matrix: map ad to specific company brochures or global conference-wide.
   */
  assignTargets: async (
    adId: string,
    payload: AdminBrochureAdAssignRequest
  ): Promise<{ success: boolean; ad_id: string; is_global: boolean; targets_count: number }> => {
    return request<{ success: boolean; ad_id: string; is_global: boolean; targets_count: number }>(
      `/admin/brochures/ads/${adId}/assign`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * Upload creative banner image directly to disk storage.
   */
  uploadCreative: async (file: File): Promise<{ creative_image_url: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE}/admin/brochures/ads/upload-creative`;
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    if (!res.ok) {
      let detail = `Upload error (${res.status})`;
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {}
      throw new ApiClientError(res.status, detail);
    }
    return res.json();
  },

  /**
   * List all company brochures available for ad targeting checklist.
   */
  listCompanyBrochures: async (): Promise<AdminCompanyBrochureOption[]> => {
    return request<AdminCompanyBrochureOption[]>('/admin/brochures/companies');
  },

  /**
   * Persist global summit flipbook sound & animation presets.
   */
  updateViewerSettings: async (payload: {
    sound_preset: string;
    animation_preset: string;
  }): Promise<{ sound_preset: string; animation_preset: string }> => {
    return request<{ sound_preset: string; animation_preset: string }>(
      '/admin/brochures/viewer-settings',
      {
        method: 'PUT',
        body: JSON.stringify(payload),
      }
    );
  },

  /**
   * Fetch portfolio-wide and per-magazine page read analytics over a time window.
   */
  getBrochureAnalytics: async (
    period: AnalyticsPeriod = '7d'
  ): Promise<AdminBrochureAnalyticsOverview> => {
    return request<AdminBrochureAnalyticsOverview>(
      `/admin/brochures/analytics?period=${encodeURIComponent(period)}`
    );
  },
};
