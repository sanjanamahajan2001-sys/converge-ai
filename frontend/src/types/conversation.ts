export type ConversationStatus = 'INVITED' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED';

export type ConversationOutcome =
  | 'PROPOSAL_GENERATED'
  | 'COMPLETED_WITHOUT_PROPOSAL'
  | 'CANCELLED'
  | 'EXPIRED';

export type MessageSenderType = 'PARTICIPANT' | 'AGENT' | 'SYSTEM';

export interface LocationPayload {
  latitude: number;
  longitude: number;
  name?: string | null;
  address?: string | null;
  map_url?: string | null;
}

export interface ConversationBusinessContextCreate {
  inquiry_type: string;
  product_name: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  quantity?: number | null;
  unit?: string | null;
  delivery_location?: string | null;
  timeline_days?: number | null;
  target_price_indication?: number | null;
  is_budget_public: boolean;
  urgency?: string | null;
  inquiry_notes?: string | null;
}

export interface ConversationBusinessContextResponse {
  id: string;
  conversation_id: string;
  version: number;
  inquiry_type: string;
  product_name: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  quantity?: number | null;
  unit?: string | null;
  delivery_location?: string | null;
  timeline_days?: number | null;
  target_price_indication?: number | null;
  urgency?: string | null;
  inquiry_notes?: string | null;
  snapshot_hash: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string | null;
  sender_type: MessageSenderType;
  turn_index: number;
  content: string;
  message_type?: string;
  location_payload?: LocationPayload | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  initiator_id: string;
  target_id: string;
  status: ConversationStatus;
  match_score: number | null;
  terminal_outcome: ConversationOutcome | null;
  created_at: string;
  updated_at: string;
  concluded_at: string | null;
  other_participant_id: string | null;
  other_participant_name: string | null;
  other_participant_mood?: string | null;
  last_message?: Message | null;
  message_count: number;
  has_business_context?: boolean;
  business_inquiry_type?: string | null;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  business_context?: ConversationBusinessContextResponse | null;
}
