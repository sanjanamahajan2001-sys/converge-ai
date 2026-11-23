/**
 * Conference Agenda, Session, and Participant Bookmark contract types (GAP-09, GAP-10).
 */

export interface ConferenceOrganizerPublic {
  id: string;
  representative_name: string;
  organization_name?: string | null;
  designation?: string | null;
  city: string;
  country: string;
  verification_status: string;
  website_url?: string | null;
}

export interface ConferenceResponse {
  id: string;
  organizer_id?: string | null;
  organizer?: ConferenceOrganizerPublic | null;
  title: string;
  summary?: string | null;
  description: string | null;
  category?: string | null;
  format?: string;
  venue_name: string;
  formatted_address?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  place_id?: string | null;
  city?: string | null;
  country?: string | null;
  timezone: string;
  start_date: string;
  end_date: string;
  start_time?: string | null;
  end_time?: string | null;
  registration_opens_at?: string | null;
  registration_closes_at?: string | null;
  capacity?: number | null;
  target_audience?: string | null;
  website_url?: string | null;
  banner_url?: string | null;
  meeting_url?: string | null;
  status?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SessionResponse {
  id: string;
  conference_id: string;
  title: string;
  abstract: string | null;
  speaker_names: string | null;
  track_name: string | null;
  hall_room: string;
  start_time: string;
  end_time: string;
  is_cancelled: boolean;
  created_at: string;
  updated_at: string;
}

export interface BookmarkResponse {
  user_id: string;
  session_id: string;
  created_at: string;
}

export interface BookmarkedSessionResponse {
  session_id: string;
  bookmarked_at: string;
  session: SessionResponse;
}

export interface SessionFilterParams {
  conference_id?: string;
  track_name?: string;
  hall_room?: string;
  date?: string;
  is_cancelled?: boolean;
  conference_is_active?: boolean;
  limit?: number;
  offset?: number;
}

export type SessionIntentDecisionState = 'ATTENDING' | 'DECLINED' | 'UNDECIDED';

export interface SessionIntentDecisionResponse {
  id: string;
  user_id: string;
  session_id: string;
  decision: SessionIntentDecisionState;
  source: string;
  created_at: string;
  updated_at: string;
  session?: SessionResponse;
}

export interface SessionRecommendationPrompt {
  session: SessionResponse;
  matched_reason: string;
  prompt_message: string;
  current_decision?: SessionIntentDecisionState | null;
}

