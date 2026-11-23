import { request } from './client';
import {
  GroupConversation,
  GroupConversationDetail,
  GroupConversationCreate,
  GroupMessage,
  GroupMessageCreate,
} from '@/types/groupConversation';

export const groupConversationApi = {
  listCircles: () => request<GroupConversation[]>('/groups/circles'),

  getCircle: (circleId: string) =>
    request<GroupConversationDetail>(`/groups/circles/${circleId}`),

  createCircle: (payload: GroupConversationCreate) =>
    request<GroupConversationDetail>('/groups/circles', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  sendMessage: (circleId: string, content: string, messageType: string = 'TEXT') =>
    request<GroupMessage>(`/groups/circles/${circleId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        message_type: messageType,
      } as GroupMessageCreate),
    }),

  leaveCircle: (circleId: string) =>
    request<GroupConversation>(`/groups/circles/${circleId}/leave`, {
      method: 'POST',
    }),

  closeCircle: (circleId: string) =>
    request<GroupConversation>(`/groups/circles/${circleId}/close`, {
      method: 'POST',
    }),

  deleteCircle: (circleId: string) =>
    request<void>(`/groups/circles/${circleId}`, {
      method: 'DELETE',
    }),
};
