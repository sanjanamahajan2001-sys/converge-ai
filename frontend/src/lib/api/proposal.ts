import { request } from './client';
import {
  CounterProposalRequest,
  DisclosedContactCredentials,
  ProposalApprovalRequest,
  ProposalCreateRequest,
  ProposalDetail,
  ProposalDraftPrefillRequest,
  ProposalDraftPrefillResponse,
  ProposalListItem,
  ProposalRejectionRequest,
  ProposalRevisionDiffResponse,
  ProposalStatus,
} from '@/types/proposal';

export const proposalApi = {
  /**
   * List all proposals sent or received by authenticated user with optional status or tab filters.
   */
  listProposals: async (params?: {
    status?: ProposalStatus;
    tab?: 'action_required' | 'approved' | 'archive' | string;
    conversation_id?: string;
  }): Promise<ProposalListItem[]> => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.tab) query.append('tab', params.tab);
    if (params?.conversation_id) query.append('conversation_id', params.conversation_id);
    const qs = query.toString();
    return request<ProposalListItem[]>(`/proposals${qs ? `?${qs}` : ''}`);
  },

  /**
   * Fetch complete proposal sheet with revisions, approvals trail, and gated contact details.
   */
  getProposal: async (proposalId: string): Promise<ProposalDetail> => {
    return request<ProposalDetail>(`/proposals/${proposalId}`);
  },

  /**
   * Initiate and submit a formal proposal (Revision 1).
   */
  createProposal: async (payload: ProposalCreateRequest): Promise<ProposalDetail> => {
    return request<ProposalDetail>('/proposals', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Approve the active revision. Unlocks contact credentials if both parties have approved.
   */
  approveProposal: async (
    proposalId: string,
    payload?: ProposalApprovalRequest
  ): Promise<ProposalDetail> => {
    return request<ProposalDetail>(`/proposals/${proposalId}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  /**
   * Counter with a new revision (Vk+1).
   */
  counterProposal: async (
    proposalId: string,
    payload: CounterProposalRequest
  ): Promise<ProposalDetail> => {
    return request<ProposalDetail>(`/proposals/${proposalId}/counter`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Formally decline / reject a proposal with mandatory reason.
   */
  rejectProposal: async (
    proposalId: string,
    payload: ProposalRejectionRequest
  ): Promise<ProposalDetail> => {
    return request<ProposalDetail>(`/proposals/${proposalId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Withdraw an authored proposal before counterparty accepts.
   */
  withdrawProposal: async (proposalId: string): Promise<ProposalDetail> => {
    return request<ProposalDetail>(`/proposals/${proposalId}/withdraw`, {
      method: 'POST',
    });
  },

  /**
   * Fetch unlocked contact credentials for mutually approved agreement.
   */
  getUnlockedContacts: async (proposalId: string): Promise<DisclosedContactCredentials> => {
    return request<DisclosedContactCredentials>(`/proposals/${proposalId}/contacts`);
  },

  /**
   * AI/Auto-prefill proposal draft parameters from conversation context.
   */
  getProposalDraftPrefill: async (
    payload: ProposalDraftPrefillRequest
  ): Promise<ProposalDraftPrefillResponse> => {
    return request<ProposalDraftPrefillResponse>('/proposals/draft', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Calculate structured commercial parameter diff between revisions.
   */
  getProposalRevisionDiff: async (
    proposalId: string,
    fromRev: number = 1,
    toRev?: number
  ): Promise<ProposalRevisionDiffResponse> => {
    const query = new URLSearchParams({ from_rev: fromRev.toString() });
    if (toRev !== undefined) {
      query.append('to_rev', toRev.toString());
    }
    return request<ProposalRevisionDiffResponse>(`/proposals/${proposalId}/diff?${query.toString()}`);
  },
};
