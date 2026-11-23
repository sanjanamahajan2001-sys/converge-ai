/**
 * TypeScript types and DTO contracts for Organizer Portal (Phase 2 & Phase 3).
 */

export type OrganizerType = 'INDIVIDUAL' | 'COMPANY' | 'INSTITUTION' | 'COMMUNITY' | 'NON_PROFIT';

export type OrganizerVerificationStatus = 'UNVERIFIED' | 'PENDING_REVIEW' | 'VERIFIED' | 'SUSPENDED';

export type ConferenceFormat = 'IN_PERSON' | 'ONLINE' | 'HYBRID';

export type ConferenceStatus =
  | 'DRAFT'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'CHANGES_REQUESTED'
  | 'REJECTED'
  | 'PUBLISHED'
  | 'CANCELLED';

export interface OrganizerRegisterPayload {
  username: string;
  password: string;
  full_name: string;
  email: string;
  organizer_type: OrganizerType;
  representative_name: string;
  organization_name?: string;
  designation?: string;
  professional_email: string;
  contact_phone: string;
  website_url?: string;
  logo_url?: string;
  address_line1?: string;
  city: string;
  state_province?: string;
  postal_code?: string;
  country: string;
  bio: string;
  experience_years?: number;
  focus_areas: string[];
}

export interface OrganizerProfileUpdatePayload {
  organizer_type?: OrganizerType;
  representative_name?: string;
  organization_name?: string;
  designation?: string;
  professional_email?: string;
  contact_phone?: string;
  website_url?: string;
  logo_url?: string;
  address_line1?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
  bio?: string;
  experience_years?: number;
  focus_areas?: string[];
}

export interface OrganizerProfile {
  id: string;
  user_id: string;
  organizer_type: OrganizerType;
  representative_name: string;
  organization_name?: string | null;
  designation?: string | null;
  professional_email: string;
  contact_phone: string;
  website_url?: string | null;
  logo_url?: string | null;
  address_line1?: string | null;
  city: string;
  state_province?: string | null;
  postal_code?: string | null;
  country: string;
  bio: string;
  experience_years?: number | null;
  focus_areas: string[];
  verification_status: OrganizerVerificationStatus;
  created_at: string;
  updated_at: string;
  conferences_count: number;
}

export interface OrganizerConferenceCreatePayload {
  title: string;
  summary?: string;
  description?: string;
  category?: string;
  format: ConferenceFormat;
  venue_name: string;
  timezone?: string;
  start_date: string;
  end_date: string;
  start_time?: string;
  end_time?: string;
  registration_opens_at?: string;
  registration_closes_at?: string;
  capacity?: number;
  target_audience?: string;
  website_url?: string;
  banner_url?: string;
  meeting_url?: string;
  formatted_address?: string;
  location_lat?: number;
  location_lng?: number;
  place_id?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
}

export interface OrganizerConferenceUpdatePayload {
  title?: string;
  summary?: string;
  description?: string;
  category?: string;
  format?: ConferenceFormat;
  venue_name?: string;
  timezone?: string;
  start_date?: string;
  end_date?: string;
  start_time?: string;
  end_time?: string;
  registration_opens_at?: string;
  registration_closes_at?: string;
  capacity?: number;
  target_audience?: string;
  website_url?: string;
  banner_url?: string;
  meeting_url?: string;
  formatted_address?: string;
  location_lat?: number;
  location_lng?: number;
  place_id?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country?: string;
}

export interface OrganizerSession {
  id: string;
  conference_id: string;
  title: string;
  abstract?: string | null;
  speaker_names?: string | null;
  track_name?: string | null;
  hall_room: string;
  start_time: string;
  end_time: string;
  is_cancelled: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrganizerSessionCreatePayload {
  title: string;
  abstract?: string;
  speaker_names?: string;
  track_name?: string;
  hall_room: string;
  start_time: string;
  end_time: string;
}

export interface OrganizerSessionUpdatePayload {
  title?: string;
  abstract?: string;
  speaker_names?: string;
  track_name?: string;
  hall_room?: string;
  start_time?: string;
  end_time?: string;
  is_cancelled?: boolean;
}

export interface OrganizerConference {
  id: string;
  organizer_id?: string | null;
  title: string;
  summary?: string | null;
  description?: string | null;
  category?: string | null;
  format: ConferenceFormat;
  venue_name: string;
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
  formatted_address?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  place_id?: string | null;
  city?: string | null;
  state_province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  status: ConferenceStatus;
  review_feedback?: string | null;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
  sessions_count: number;
}

export interface OrganizerConferenceDetail extends OrganizerConference {
  sessions: OrganizerSession[];
}

export interface ConferenceSubmitResponse {
  status: ConferenceStatus;
  conference_id: string;
  message: string;
}
