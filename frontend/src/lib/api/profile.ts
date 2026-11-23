import { request } from '@/lib/api/client';
import { ProfileResponse, ProfileUpdate, PublicProfileResponse } from '@/types/profile';

/**
 * Retrieve the current authenticated participant's complete profile.
 * Returns 404 if profile is uninitialized.
 */
export async function getMyProfile(): Promise<ProfileResponse> {
  return request<ProfileResponse>('/profile/me', {
    method: 'GET',
  });
}

/**
 * Upsert or partially update the current participant's profile.
 * Sends strictly approved ProfileUpdate properties to prevent mass assignment rejection.
 */
export async function updateMyProfile(payload: ProfileUpdate): Promise<ProfileResponse> {
  return request<ProfileResponse>('/profile/me', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

/**
 * Retrieve a public profile projection of a conference participant by their user ID.
 * Returns 404 if user does not exist, is deactivated, or uninitialized.
 */
export async function getPublicProfile(id: string): Promise<PublicProfileResponse> {
  return request<PublicProfileResponse>(`/profile/${encodeURIComponent(id)}`, {
    method: 'GET',
  });
}

/**
 * Retrieve the curated reference catalog of conference hobbies and preferences.
 */
export async function getHobbiesCatalog(): Promise<string[]> {
  return request<string[]>('/profile/catalog/hobbies', {
    method: 'GET',
  });
}

/**
 * Retrieve the curated reference catalog of conference informal moods.
 */
export async function getMoodsCatalog(): Promise<string[]> {
  return request<string[]>('/profile/catalog/moods', {
    method: 'GET',
  });
}
