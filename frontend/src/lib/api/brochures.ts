/**
 * API client module for Company Digital Brochures & Flipbooks (Phase 1 & 2).
 */

import { request, ApiClientError } from './client';
import {
  AnalyticsPeriod,
  BrochureAnalyticsDetail,
  BrochureDirectoryItem,
  BrochurePageItem,
  BrochurePublicView,
  CompanyBrochureDetail,
  CompanyBrochureUpdate,
} from '@/types/brochure';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/converge-api/v1';

export const brochureApi = {
  /**
   * Fetch or auto-provision the authenticated user's company brochure studio details.
   */
  getMyBrochure: async (): Promise<CompanyBrochureDetail> => {
    return request<CompanyBrochureDetail>('/brochures/my-brochure');
  },

  /**
   * Update brochure title, description, custom slug, or publish state.
   */
  updateMyBrochure: async (payload: CompanyBrochureUpdate): Promise<CompanyBrochureDetail> => {
    return request<CompanyBrochureDetail>('/brochures/my-brochure', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Upload an image page (JPEG, PNG, WebP) to append to the brochure.
   */
  uploadPage: async (file: File, title?: string): Promise<BrochurePageItem> => {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    const url = `${API_BASE}/brochures/my-brochure/upload-page`;
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
   * Reorder brochure pages by submitting the exact array of Page UUIDs.
   */
  reorderPages: async (pageIds: string[]): Promise<BrochurePageItem[]> => {
    return request<BrochurePageItem[]>('/brochures/my-brochure/reorder', {
      method: 'POST',
      body: JSON.stringify({ page_ids: pageIds }),
    });
  },

  /**
   * Delete an existing page from the brochure.
   */
  deletePage: async (pageId: string): Promise<{ success: boolean; deleted_page_id: string }> => {
    return request<{ success: boolean; deleted_page_id: string }>(
      `/brochures/my-brochure/pages/${pageId}`,
      {
        method: 'DELETE',
      }
    );
  },

  /**
   * Public flipbook data endpoint resolving pages and dynamic sponsor ads.
   */
  getPublicBrochure: async (slug: string): Promise<BrochurePublicView> => {
    return request<BrochurePublicView>(`/brochures/public/${slug}`);
  },

  /**
   * Public directory of all published exhibitor company brochures.
   */
  getDirectory: async (search?: string): Promise<BrochureDirectoryItem[]> => {
    const qs = search ? `?search=${encodeURIComponent(search)}` : '';
    return request<BrochureDirectoryItem[]>(`/brochures/directory${qs}`);
  },

  /**
   * Log ad impression or click telemetry.
   */
  trackAdEvent: async (
    adId: string,
    eventType: 'IMPRESSION' | 'CLICK',
    brochureId?: string
  ): Promise<{ success: boolean }> => {
    const qs = brochureId ? `?brochure_id=${encodeURIComponent(brochureId)}` : '';
    return request<{ success: boolean }>(`/brochures/ads/${adId}/track${qs}`, {
      method: 'POST',
      body: JSON.stringify({ event_type: eventType }),
    });
  },

  /**
   * Fetch global summit flipbook acoustics & page-turn animation defaults.
   */
  getViewerSettings: async (): Promise<{ sound_preset: string; animation_preset: string }> => {
    return request<{ sound_preset: string; animation_preset: string }>('/brochures/viewer-settings');
  },

  /**
   * Record page-level read telemetry while reading a public flipbook.
   */
  trackPageReads: async (
    slug: string,
    pageNumbers: number[],
    sessionKey?: string,
    viewMode?: string
  ): Promise<{ success: boolean; recorded_pages: number[] }> => {
    return request<{ success: boolean; recorded_pages: number[] }>(
      `/brochures/public/${encodeURIComponent(slug)}/page-read`,
      {
        method: 'POST',
        body: JSON.stringify({
          page_numbers: pageNumbers,
          session_key: sessionKey,
          view_mode: viewMode,
        }),
      }
    );
  },

  /**
   * Fetch detailed time-series and per-page read analytics for the owner's brochure.
   */
  getMyBrochureAnalytics: async (period: AnalyticsPeriod = '7d'): Promise<BrochureAnalyticsDetail> => {
    return request<BrochureAnalyticsDetail>(
      `/brochures/my-brochure/analytics?period=${encodeURIComponent(period)}`
    );
  },
};
