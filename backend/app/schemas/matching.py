"""Pydantic schemas and contracts for the Centralized Matching Engine (P4-WS1, GAP-06)."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.profile import AvailabilityStatus, ParticipationIntent


class MatchFactorWeights(BaseModel):
    """Configurable weights for the 4-factor matching algorithm (Canonical Specification)."""

    intent_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for networking intent alignment (25%)"
    )
    topics_weight: float = Field(
        default=0.35, ge=0.0, le=1.0, description="Weight for technical topics overlap (35%)"
    )
    agenda_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for bookmarked sessions overlap (25%)"
    )
    hobbies_weight: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Weight for informal hobbies/interests overlap (15%)"
    )
    match_threshold: float = Field(
        default=0.65, ge=0.0, le=1.0, description="Minimum composite score threshold for recommendations"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("intent_weight", "topics_weight", "agenda_weight", "hobbies_weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Factor weights must be between 0.0 and 1.0 inclusive.")
        return round(v, 4)


class FactorScoreDetail(BaseModel):
    """Detailed calculation metrics for a single matching dimension."""

    raw_similarity: float = Field(..., ge=0.0, le=1.0, description="Raw similarity score in [0.0, 1.0]")
    baseline_weight: float = Field(..., ge=0.0, le=1.0, description="Standard baseline weight")
    effective_weight: float = Field(..., ge=0.0, le=1.0, description="Normalized weight after dynamic re-weighting")
    is_active: bool = Field(..., description="Whether this factor was active for the pair evaluation")


class MatchScoreBreakdown(BaseModel):
    """Explainable 4-factor score breakdown for a candidate recommendation."""

    intent: FactorScoreDetail
    topics: FactorScoreDetail
    agenda: FactorScoreDetail
    hobbies: FactorScoreDetail
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Final weighted composite score in [0.0, 1.0]")


class CandidateMatchResponse(BaseModel):
    """Safe, PII-scrubbed projection of an eligible candidate participant.

    Guarantees that private fields (email, phone_number, private credentials, user_sessions)
    are strictly excluded from the match result (GAP-03, GAP-10).
    """

    candidate_id: UUID = Field(..., description="Unique participant UUID")
    full_name: str = Field(..., description="Participant display name")
    company_name: Optional[str] = Field(None, description="Company or institution")
    job_title: Optional[str] = Field(None, description="Professional title")
    intent: ParticipationIntent = Field(..., description="Declared participation intent")
    availability: AvailabilityStatus = Field(..., description="Current availability status")
    bio_summary: Optional[str] = Field(None, description="Public bio summary")
    topics: List[str] = Field(default_factory=list, description="Declared technical topics")
    hobbies: List[str] = Field(default_factory=list, description="Selected hobbies / interests")

    # Match evaluation & explainability
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Normalized compatibility score")
    score_breakdown: MatchScoreBreakdown = Field(..., description="Detailed 4-factor score components")
    common_topics: List[str] = Field(default_factory=list, description="Shared topic keywords")
    common_hobbies: List[str] = Field(default_factory=list, description="Shared hobbies / interests")
    common_sessions_count: int = Field(default=0, ge=0, description="Count of mutually bookmarked sessions")
    match_reasons: List[str] = Field(default_factory=list, description="Human-readable match rationale")
    temporal_boost: float = Field(default=0.0, description="Bonus score applied from active conference break or talk momentum")
    temporal_reason: Optional[str] = Field(None, description="Active temporal context e.g. Tea Break Match or Recent Talk Synergy")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MatchEvaluationResult(BaseModel):
    """Result envelope of the deterministic matching engine evaluation."""

    requester_id: UUID = Field(..., description="Participant requesting matches")
    candidates: List[CandidateMatchResponse] = Field(
        default_factory=list, description="Deterministically sorted candidate recommendations"
    )
    total_evaluated: int = Field(default=0, ge=0, description="Total active participants evaluated")
    eligible_count: int = Field(default=0, ge=0, description="Number of participants satisfying hard eligibility")
    matched_count: int = Field(default=0, ge=0, description="Number of candidates meeting score threshold")
    limit: int = Field(default=50, ge=1, le=100, description="Pagination page size limit")
    offset: int = Field(default=0, ge=0, description="Pagination offset count")
