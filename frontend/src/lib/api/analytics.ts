import { request } from '@/lib/api/client';
import {
  ActivityEventPayload,
  ActivityEventResponse,
  UserActivitySummary,
} from '@/types/analytics';

/**
 * Record a user interaction, feature click, or agent visit.
 */
export async function recordActivityEvent(payload: ActivityEventPayload): Promise<ActivityEventResponse> {
  return request<ActivityEventResponse>('/analytics/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch caller's complete activity metrics, login sessions, and conversation history.
 */
export async function getMyActivitySummary(): Promise<UserActivitySummary> {
  return request<UserActivitySummary>('/analytics/my-summary', {
    method: 'GET',
  });
}

/**
 * Fire-and-forget helper to track feature clicks from frontend components.
 */
export function trackFeatureClick(
  featureName: string,
  targetResourceId?: string,
  details: Record<string, any> = {}
): void {
  recordActivityEvent({
    event_type: 'FEATURE_CLICK',
    feature_name: featureName,
    target_resource_id: targetResourceId,
    details: details,
  }).catch((err) => {
    // Non-blocking, silence debug error
    console.debug('Failed to track feature click:', err);
  });
}
