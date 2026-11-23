import { AvailabilityStatus, ParticipationIntent } from './profile';

export interface FactorScoreDetail {
  raw_similarity: number;
  baseline_weight: number;
  effective_weight: number;
  is_active: boolean;
}

export interface MatchScoreBreakdown {
  intent: FactorScoreDetail;
  topics: FactorScoreDetail;
  agenda: FactorScoreDetail;
  hobbies: FactorScoreDetail;
  composite_score: number;
}

export interface CandidateMatchResponse {
  candidate_id: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  intent: ParticipationIntent;
  availability: AvailabilityStatus;
  bio_summary?: string | null;
  topics: string[];
  hobbies: string[];
  composite_score: number;
  score_breakdown: MatchScoreBreakdown;
  common_topics: string[];
  common_hobbies: string[];
  common_sessions_count: number;
  match_reasons: string[];
  temporal_boost?: number;
  temporal_reason?: string | null;
}

export interface MatchEvaluationResult {
  requester_id: string;
  candidates: CandidateMatchResponse[];
  total_evaluated: number;
  eligible_count: number;
  matched_count: number;
  limit: number;
  offset: number;
}

export interface CandidateMatchFilterParams {
  filter_by_threshold?: boolean;
  threshold?: number;
  limit?: number;
  offset?: number;
}
