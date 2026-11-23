export type GroupRole = 'HOST' | 'MEMBER';
export type GroupStatus = 'ACTIVE' | 'COMPLETED';
export type GroupMessageSenderType = 'PARTICIPANT' | 'AGENT' | 'SYSTEM';

export interface GroupMemberSummary {
  user_id: string;
  username: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  role: GroupRole;
  joined_at: string;
  last_read_turn: number;
}

export interface GroupMessage {
  id: string;
  group_id: string;
  sender_id?: string | null;
  sender_username?: string | null;
  sender_full_name?: string | null;
  sender_type: GroupMessageSenderType;
  turn_index: number;
  content: string;
  message_type?: string | null;
  created_at: string;
}

export interface GroupConversation {
  id: string;
  title: string;
  topic_context: string;
  host_id: string;
  host_name?: string | null;
  status: GroupStatus;
  max_turns: number;
  current_turn: number;
  ai_turns_budget?: number;
  created_at: string;
  updated_at: string;
  concluded_at?: string | null;
  members_count: number;
  members: GroupMemberSummary[];
  last_message?: GroupMessage | null;
}

export interface GroupConversationDetail extends GroupConversation {
  messages: GroupMessage[];
}

export interface GroupConversationCreate {
  title: string;
  topic_context: string;
  member_ids: string[];
}

export interface GroupMessageCreate {
  content: string;
  message_type?: string;
}
