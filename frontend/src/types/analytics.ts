/**
 * Types for User Activity, Sessions, and Engagement Tracking.
 */

export interface ActivityEventPayload {
  event_type: 'FEATURE_CLICK' | 'AGENT_VISIT' | 'PAGE_VIEW' | string;
  feature_name: string;
  target_resource_id?: string | null;
  details?: Record<string, unknown>;
}

export interface ActivityEventResponse {
  id: number;
  user_id: string;
  event_type: string;
  feature_name: string;
  target_resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SessionDetail {
  session_id: string;
  created_at: string;
  last_accessed_at: string;
  expires_at: string;
  is_active: boolean;
  user_agent: string | null;
}

export interface ConversationHistoryItem {
  conversation_id: string;
  partner_id: string;
  partner_name: string;
  partner_username: string;
  role: 'INITIATOR' | 'TARGET';
  status: string;
  turn_count: number;
  created_at: string;
  concluded_at: string | null;
  last_message_at: string | null;
}

export interface UserActivitySummary {
  user_id: string;
  total_logins: number;
  active_sessions: number;
  recent_sessions: SessionDetail[];
  total_conversations: number;
  conversations_initiated: number;
  conversations_participated: number;
  conversation_history: ConversationHistoryItem[];
  total_activity_events: number;
  feature_clicks_count: number;
  agent_visits_count: number;
  recent_activity_events: ActivityEventResponse[];
}
