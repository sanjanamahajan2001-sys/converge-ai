/**
 * API client methods for Organizer Portal (Phase 2 & Phase 3).
 */
import { request } from '@/lib/api/client';
import {
  ConferenceSubmitResponse,
  OrganizerConference,
  OrganizerConferenceCreatePayload,
  OrganizerConferenceDetail,
  OrganizerConferenceUpdatePayload,
  OrganizerProfile,
  OrganizerProfileUpdatePayload,
  OrganizerRegisterPayload,
  OrganizerSession,
  OrganizerSessionCreatePayload,
  OrganizerSessionUpdatePayload,
} from '@/types/organizer';

/**
 * Register a new organizer account and profile, issuing session cookie.
 */
export async function registerOrganizer(payload: OrganizerRegisterPayload): Promise<OrganizerProfile> {
  return request<OrganizerProfile>('/organizer/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Retrieve current authenticated organizer's profile and event metrics.
 */
export async function getMyOrganizerProfile(): Promise<OrganizerProfile> {
  return request<OrganizerProfile>('/organizer/me', {
    method: 'GET',
  });
}

/**
 * Update current authenticated organizer's profile attributes.
 */
export async function updateMyOrganizerProfile(
  payload: OrganizerProfileUpdatePayload
): Promise<OrganizerProfile> {
  return request<OrganizerProfile>('/organizer/me', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

/**
 * List all conferences owned by the current organizer.
 */
export async function getOrganizerConferences(): Promise<OrganizerConference[]> {
  return request<OrganizerConference[]>('/organizer/conferences', {
    method: 'GET',
  });
}

/**
 * Create a new conference draft.
 */
export async function createOrganizerConference(
  payload: OrganizerConferenceCreatePayload
): Promise<OrganizerConference> {
  return request<OrganizerConference>('/organizer/conferences', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Get detailed conference data with all scheduled sessions.
 */
export async function getOrganizerConferenceDetail(
  conferenceId: string
): Promise<OrganizerConferenceDetail> {
  return request<OrganizerConferenceDetail>(`/organizer/conferences/${conferenceId}`, {
    method: 'GET',
  });
}

/**
 * Update a conference draft or edit after changes requested.
 */
export async function updateOrganizerConference(
  conferenceId: string,
  payload: OrganizerConferenceUpdatePayload
): Promise<OrganizerConference> {
  return request<OrganizerConference>(`/organizer/conferences/${conferenceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

/**
 * Submit conference draft for administrative review.
 */
export async function submitConferenceForReview(
  conferenceId: string
): Promise<ConferenceSubmitResponse> {
  return request<ConferenceSubmitResponse>(`/organizer/conferences/${conferenceId}/submit`, {
    method: 'POST',
  });
}

/**
 * Add an agenda session to conference.
 */
export async function createOrganizerSession(
  conferenceId: string,
  payload: OrganizerSessionCreatePayload
): Promise<OrganizerSession> {
  return request<OrganizerSession>(`/organizer/conferences/${conferenceId}/sessions`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Update an existing session.
 */
export async function updateOrganizerSession(
  conferenceId: string,
  sessionId: string,
  payload: OrganizerSessionUpdatePayload
): Promise<OrganizerSession> {
  return request<OrganizerSession>(`/organizer/conferences/${conferenceId}/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a session from agenda.
 */
export async function deleteOrganizerSession(
  conferenceId: string,
  sessionId: string
): Promise<{ detail: string }> {
  return request<{ detail: string }>(`/organizer/conferences/${conferenceId}/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

/**
 * Phase 5: Live Conference Control Plane API Methods
 */
export interface ConferenceLiveStateResponse {
  id?: string;
  conference_id: string;
  active_session_id?: string;
  current_state: string;
  custom_state_label?: string;
  break_type: string;
  designated_location?: string;
  announcement_banner?: string;
  active_day?: number;
  starts_at?: string;
  ends_at?: string;
  is_active: boolean;
  delay_minutes?: number;
  weather_override?: string;
  amenities_note?: string;
}

export interface ConferenceLiveStateUpdatePayload {
  current_state: string;
  custom_state_label?: string;
  break_type?: string;
  designated_location?: string;
  announcement_banner?: string;
  duration_minutes?: number;
  delay_minutes?: number;
  weather_override?: string;
  active_session_id?: string;
  amenities_note?: string;
  criticality?: 'NORMAL' | 'CRITICAL';
  active_day?: number;
}

export async function getConferenceLiveState(conferenceId: string): Promise<ConferenceLiveStateResponse> {
  return request<ConferenceLiveStateResponse>(`/organizer/conferences/${conferenceId}/live-state`, {
    method: 'GET',
  });
}

export async function setConferenceLiveState(
  conferenceId: string,
  payload: ConferenceLiveStateUpdatePayload
): Promise<ConferenceLiveStateResponse> {
  return request<ConferenceLiveStateResponse>(`/organizer/conferences/${conferenceId}/live-state`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function resetConferenceLiveState(conferenceId: string): Promise<{ detail: string }> {
  return request<{ detail: string }>(`/organizer/conferences/${conferenceId}/live-state`, {
    method: 'DELETE',
  });
}

export async function hostConferenceLounge(conferenceId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/organizer/conferences/${conferenceId}/lounge/host`, {
    method: 'POST',
  });
}

export async function resetConferenceLounge(conferenceId: string): Promise<{ detail: string }> {
  return request<{ detail: string }>(`/organizer/conferences/${conferenceId}/lounge/reset`, {
    method: 'POST',
  });
}

export async function closeConferenceLounge(conferenceId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/organizer/conferences/${conferenceId}/lounge/close`, {
    method: 'POST',
  });
}
