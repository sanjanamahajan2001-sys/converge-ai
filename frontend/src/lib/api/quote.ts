/**
 * API client module for Quotes & Multi-Vendor RFQ System (Quote Subphase 5).
 */

import { request } from './client';
import {
  QuoteRequestCreate,
  QuoteRequestDetail,
  QuoteVendorPanelResponse,
  SendQuoteEmailRequest,
  SendQuoteEmailResponse,
} from '@/types/quote';

export const quoteApi = {
  /**
   * Fetch paginated asks distributed to the authenticated vendor with status tabs & search.
   */
  listVendorQuotesPanel: async (params?: {
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<QuoteVendorPanelResponse> => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    const qs = query.toString();
    return request<QuoteVendorPanelResponse>(`/quotes/vendor-panel${qs ? `?${qs}` : ''}`);
  },

  /**
   * Fetch paginated asks broadcasted by the authenticated buyer delegate.
   */
  listBuyerAsksPanel: async (params?: {
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<QuoteVendorPanelResponse> => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    const qs = query.toString();
    return request<QuoteVendorPanelResponse>(`/quotes/buyer-panel${qs ? `?${qs}` : ''}`);
  },

  /**
   * Fetch full forensic specifications and dispatch history for an ask.
   */
  getQuoteDetail: async (quoteRequestId: string): Promise<QuoteRequestDetail> => {
    return request<QuoteRequestDetail>(`/quotes/${quoteRequestId}`);
  },

  /**
   * Submit commercial terms and dispatch a branded quotation via email.
   */
  sendQuoteEmail: async (
    matchId: string,
    payload: SendQuoteEmailRequest
  ): Promise<SendQuoteEmailResponse> => {
    return request<SendQuoteEmailResponse>(`/quotes/matches/${matchId}/send-email`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Decline an incoming procurement inquiry.
   */
  declineQuote: async (matchId: string): Promise<{ status: string; match_id: string }> => {
    return request<{ status: string; match_id: string }>(`/quotes/matches/${matchId}/decline`, {
      method: 'POST',
    });
  },

  /**
   * Prefill ask specifications from an active dialogue brief.
   */
  prefillAskFromConversation: async (
    conversationId: string
  ): Promise<QuoteRequestCreate> => {
    return request<QuoteRequestCreate>(
      `/quotes/asks/prefill-from-conversation/${conversationId}`
    );
  },

  /**
   * Broadcast an ask synthesized from conversation to qualified vendors.
   */
  broadcastAskFromConversation: async (
    conversationId: string,
    payloadOverride?: QuoteRequestCreate
  ): Promise<QuoteRequestDetail> => {
    return request<QuoteRequestDetail>(
      `/quotes/asks/broadcast-from-conversation/${conversationId}`,
      {
        method: 'POST',
        body: payloadOverride ? JSON.stringify(payloadOverride) : undefined,
      }
    );
  },

  /**
   * Directly create a procurement ask.
   */
  createQuoteRequest: async (
    payload: QuoteRequestCreate
  ): Promise<QuoteRequestDetail> => {
    return request<QuoteRequestDetail>('/quotes/asks', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Send commercial quotation via email directly from a 1-on-1 conversation.
   */
  sendDirectQuoteFromConversation: async (
    conversationId: string,
    payload: SendQuoteEmailRequest
  ): Promise<SendQuoteEmailResponse> => {
    return request<SendQuoteEmailResponse>(
      `/quotes/conversations/${conversationId}/direct-quote`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },
};
