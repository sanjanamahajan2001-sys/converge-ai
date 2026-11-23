import { request } from '@/lib/api/client';
import {
  BookmarkResponse,
  BookmarkedSessionResponse,
  ConferenceResponse,
  SessionFilterParams,
  SessionIntentDecisionResponse,
  SessionIntentDecisionState,
  SessionRecommendationPrompt,
  SessionResponse,
} from '@/types/agenda';

/**
 * Retrieve published conferences with optional active status filter and pagination.
 */
export async function getConferences(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<ConferenceResponse[]> {
  const query = new URLSearchParams();
  if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));

  const qs = query.toString();
  return request<ConferenceResponse[]>(`/agenda/conferences${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Retrieve scheduled conference sessions matching query filters.
 */
export async function getSessions(params?: SessionFilterParams): Promise<SessionResponse[]> {
  const query = new URLSearchParams();
  if (params?.conference_id) query.set('conference_id', params.conference_id);
  if (params?.track_name) query.set('track_name', params.track_name);
  if (params?.hall_room) query.set('hall_room', params.hall_room);
  if (params?.date) query.set('date', params.date);
  if (params?.is_cancelled !== undefined) query.set('is_cancelled', String(params.is_cancelled));
  if (params?.conference_is_active !== undefined)
    query.set('conference_is_active', String(params.conference_is_active));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));

  const qs = query.toString();
  return request<SessionResponse[]>(`/agenda/sessions${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Retrieve details for an individual session by UUID.
 */
export async function getSessionDetails(id: string): Promise<SessionResponse> {
  return request<SessionResponse>(`/agenda/sessions/${encodeURIComponent(id)}`, {
    method: 'GET',
  });
}

/**
 * Retrieve all sessions bookmarked by the currently authenticated participant.
 */
export async function getMyBookmarks(params?: {
  limit?: number;
  offset?: number;
}): Promise<BookmarkedSessionResponse[]> {
  const query = new URLSearchParams();
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.offset !== undefined) query.set('offset', String(params.offset));

  const qs = query.toString();
  return request<BookmarkedSessionResponse[]>(`/agenda/bookmarks/me${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Bookmark a conference session for the authenticated participant.
 */
export async function createBookmark(sessionId: string): Promise<BookmarkResponse> {
  return request<BookmarkResponse>(`/agenda/bookmarks/${encodeURIComponent(sessionId)}`, {
    method: 'POST',
  });
}

/**
 * Remove a conference session bookmark for the authenticated participant (idempotent).
 */
export async function deleteBookmark(sessionId: string): Promise<void> {
  return request<void>(`/agenda/bookmarks/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
}

/**
 * Retrieve recommended sessions for the authenticated attendee with agent prompt (AC-WS8).
 */
export async function getRecommendedSessions(): Promise<SessionRecommendationPrompt[]> {
  return request<SessionRecommendationPrompt[]>('/agenda/recommendations/me', {
    method: 'GET',
  });
}

/**
 * Explicitly record or update attendance decision: ATTENDING, DECLINED, or UNDECIDED (AC-WS8).
 */
export async function recordSessionIntent(
  sessionId: string,
  decision: SessionIntentDecisionState,
  source = 'REPRESENTATIVE_PROMPT'
): Promise<SessionIntentDecisionResponse> {
  return request<SessionIntentDecisionResponse>(
    `/agenda/sessions/${encodeURIComponent(sessionId)}/intent`,
    {
      method: 'POST',
      body: JSON.stringify({ decision, source }),
    }
  );
}

/**
 * Retrieve all session intent decisions recorded by the authenticated participant (AC-WS8).
 */
export async function getMySessionIntents(): Promise<SessionIntentDecisionResponse[]> {
  return request<SessionIntentDecisionResponse[]>('/agenda/intent/me', {
    method: 'GET',
  });
}

