import { request } from './client';
import {
  AmbientTickResult,
  ChatroomDetail,
  ChatroomMessage,
} from '@/types/chatroom';

export const chatroomApi = {
  getActiveLounge: (conferenceId?: string) => {
    const query = conferenceId ? `?conference_id=${encodeURIComponent(conferenceId)}` : '';
    return request<ChatroomDetail>(`/chatrooms/active${query}`);
  },

  getRecentMessages: (chatroomId: string, limit: number = 50) =>
    request<ChatroomMessage[]>(`/chatrooms/${chatroomId}/messages?limit=${limit}`),

  postMessage: (chatroomId: string, content: string) =>
    request<ChatroomMessage>(`/chatrooms/${chatroomId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  pollAmbientTick: (chatroomId: string, force: boolean = false) =>
    request<AmbientTickResult>(`/chatrooms/${chatroomId}/ambient-tick?force=${force}`, {
      method: 'POST',
    }),

  leaveLounge: (chatroomId: string) =>
    request<{ status: string }>(`/chatrooms/${chatroomId}/leave`, {
      method: 'POST',
    }),

  getOnlineUsers: (chatroomId: string) =>
    request<
      Array<{
        id: string;
        full_name: string;
        company_name: string;
        job_title?: string;
        is_me: boolean;
        allow_agent_dm_initiation?: boolean;
      }>
    >(`/chatrooms/${chatroomId}/online-users`),
};
