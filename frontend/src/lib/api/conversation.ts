import { request } from './client';
import {
  Conversation,
  ConversationBusinessContextCreate,
  ConversationBusinessContextResponse,
  ConversationDetail,
  ConversationOutcome,
  LocationPayload,
  Message,
} from '@/types/conversation';

export const conversationApi = {
  listConversations: () => request<Conversation[]>('/conversations'),

  getConversation: (conversationId: string) =>
    request<ConversationDetail>(`/conversations/${conversationId}`),

  getBusinessContext: (conversationId: string) =>
    request<ConversationBusinessContextResponse>(`/conversations/${conversationId}/business-context`),

  initiateConversation: (
    targetId: string,
    businessContext?: ConversationBusinessContextCreate | null,
    autoStart: boolean = false
  ) =>
    request<ConversationDetail>('/conversations', {
      method: 'POST',
      body: JSON.stringify({
        target_id: targetId,
        business_context: businessContext || undefined,
        auto_start: autoStart,
      }),
    }),

  sendMessage: (
    conversationId: string,
    content: string,
    messageType: string = 'TEXT',
    locationPayload?: LocationPayload | null
  ) =>
    request<Message>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        message_type: messageType,
        location: locationPayload || undefined,
        location_payload: locationPayload || undefined,
      }),
    }),

  acceptConversation: (conversationId: string, triggerAgent: boolean = false) => {
    const url = triggerAgent
      ? `/conversations/${conversationId}/accept?trigger_agent=true`
      : `/conversations/${conversationId}/accept`;
    return request<ConversationDetail>(url, {
      method: 'POST',
    });
  },

  triggerAgentDialogue: (conversationId: string) =>
    request<ConversationDetail>(`/conversations/${conversationId}/trigger-agent`, {
      method: 'POST',
    }),

  cancelConversation: (conversationId: string) =>
    request<ConversationDetail>(`/conversations/${conversationId}/cancel`, {
      method: 'POST',
    }),

  concludeConversation: (conversationId: string, outcome?: ConversationOutcome) =>
    request<ConversationDetail>(`/conversations/${conversationId}/conclude`, {
      method: 'POST',
      body: JSON.stringify({
        action: 'CONCLUDE',
        outcome: outcome || 'COMPLETED_WITHOUT_PROPOSAL',
      }),
    }),
};

export function getConversationWebSocketUrl(conversationId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/converge-api/v1/conversations/ws/${conversationId}`;
}
