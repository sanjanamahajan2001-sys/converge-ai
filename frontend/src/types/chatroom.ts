/**
 * TypeScript domain contracts for the Common Open Conference Lounge & Chatroom.
 */

export type ChatroomSenderType = 'USER' | 'REPRESENTATIVE' | 'HOST' | 'SYSTEM';

export type ChatroomMessageKind =
  | 'CHAT'
  | 'WELCOME'
  | 'TRAFFIC_ALERT'
  | 'WEATHER_UPDATE'
  | 'TEA_ANNOUNCEMENT'
  | 'SESSION_BUZZ';

export interface ChatroomMessage {
  id: string;
  chatroom_id: string;
  sender_id: string | null;
  sender_type: ChatroomSenderType;
  sender_name: string;
  content: string;
  message_kind: ChatroomMessageKind;
  turn_index: number;
  metadata_json: string | null;
  created_at: string;
}

export interface ChatroomWeatherContext {
  city?: string;
  temperature_c?: number;
  humidity_pct?: number;
  precipitation_mm?: number;
  condition?: string;
  summary?: string;
  is_live?: boolean;
  is_rainy?: boolean;
}

export interface ChatroomTrafficContext {
  origin?: string;
  destination?: string;
  distance_km?: number;
  duration_mins?: number;
  delay_mins?: number;
  congestion_level?: 'NORMAL' | 'MODERATE' | 'HEAVY' | 'UNKNOWN';
  summary?: string;
  is_live?: boolean;
}

export interface ChatroomContext {
  weather: ChatroomWeatherContext;
  traffic: ChatroomTrafficContext;
  active_break?: string | null;
  break_location?: string | null;
  general_announcement?: string | null;
  announcement_criticality?: 'NORMAL' | 'CRITICAL' | null;
  active_day?: number | null;
}

export interface ChatroomDetail {
  id: string;
  conference_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  ambient_interval_seconds: number;
  online_count: number;
  context: ChatroomContext;
  recent_messages: ChatroomMessage[];
}

export interface AmbientTickResult {
  message_generated: boolean;
  reason: string | null;
  message: ChatroomMessage | null;
}
