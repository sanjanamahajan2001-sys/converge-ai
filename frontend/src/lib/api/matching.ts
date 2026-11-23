import { request } from '@/lib/api/client';
import { CandidateMatchFilterParams, MatchEvaluationResult } from '@/types/matching';

/**
 * Discover candidate participant matches using canonical 4-factor scoring.
 * Identity is derived strictly from the active server-side session.
 */
export async function getCandidateMatches(
  params?: CandidateMatchFilterParams
): Promise<MatchEvaluationResult> {
  const query = new URLSearchParams();
  if (params?.filter_by_threshold !== undefined) {
    query.set('filter_by_threshold', String(params.filter_by_threshold));
  }
  if (params?.threshold !== undefined) {
    query.set('threshold', String(params.threshold));
  }
  if (params?.limit !== undefined) {
    query.set('limit', String(params.limit));
  }
  if (params?.offset !== undefined) {
    query.set('offset', String(params.offset));
  }

  const qs = query.toString();
  return request<MatchEvaluationResult>(`/matching/candidates${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}
