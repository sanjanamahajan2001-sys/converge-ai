/**
 * Participant profile, hobbies, topics, and catalog contract types.
 */

export type ParticipationIntent = 'NETWORKING' | 'CASUAL' | 'BOTH';

export type AvailabilityStatus = 'AVAILABLE' | 'IN_SESSION' | 'DO_NOT_DISTURB' | 'OFFLINE';

export interface ProfileResponse {
  user_id: string;
  company_name?: string | null;
  job_title?: string | null;
  intent: ParticipationIntent;
  bio_summary: string | null;
  availability: AvailabilityStatus;
  allow_agent_matching: boolean;
  allow_agent_dm_initiation?: boolean;
  contact_sharing_policy?: string;
  current_mood?: string | null;
  mood_updated_at?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  location?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  hobbies: string[];
  topics: string[];
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  company_name?: string | null;
  job_title?: string | null;
  intent?: ParticipationIntent;
  bio_summary?: string | null;
  availability?: AvailabilityStatus;
  allow_agent_matching?: boolean;
  allow_agent_dm_initiation?: boolean;
  contact_sharing_policy?: string;
  current_mood?: string | null;
  gender?: string | null;
  date_of_birth?: string | null;
  location?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  hobbies?: string[];
  topics?: string[];
}

export interface PublicProfileResponse {
  user_id: string;
  full_name: string;
  company_name: string | null;
  job_title: string | null;
  intent: ParticipationIntent;
  bio_summary: string | null;
  availability: AvailabilityStatus;
  gender?: string | null;
  date_of_birth?: string | null;
  location?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  hobbies: string[];
  topics: string[];
}
