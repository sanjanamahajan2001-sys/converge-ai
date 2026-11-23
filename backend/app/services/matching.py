"""Deterministic matching engine and participant candidate eligibility service (P4-WS1, GAP-06).

Implements the canonical 4-factor scoring model with dynamic re-weighting,
stable tie-breaking, strict consent checks, and zero PII disclosure.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SASession, selectinload

from app.db.models.agenda import BookmarkedSession
from app.db.models.profile import AvailabilityStatus, ParticipantHobby, ParticipantProfile, ParticipantTopic, ParticipationIntent
from app.db.models.user import User
from app.schemas.matching import (
    CandidateMatchResponse,
    FactorScoreDetail,
    MatchEvaluationResult,
    MatchFactorWeights,
    MatchScoreBreakdown,
)


@dataclass
class ParticipantContext:
    """In-memory representation of a participant for pure, deterministic matching evaluation."""

    user_id: UUID
    full_name: str
    company_name: Optional[str]
    job_title: Optional[str]
    is_active: bool
    has_profile: bool
    intent: Optional[ParticipationIntent]
    availability: Optional[AvailabilityStatus]
    allow_agent_matching: bool
    bio_summary: Optional[str] = None
    raw_topics: List[str] = field(default_factory=list)
    raw_hobbies: List[str] = field(default_factory=list)
    normalized_topics: Set[str] = field(default_factory=set)
    normalized_hobbies: Set[str] = field(default_factory=set)
    bookmarked_session_ids: Set[UUID] = field(default_factory=set)


class MatchingEngine:
    """Core mathematical and policy engine for participant eligibility, scoring, and ranking."""

    def __init__(self, default_weights: Optional[MatchFactorWeights] = None):
        self.weights = default_weights or MatchFactorWeights()

    # -------------------------------------------------------------------------
    # 1. Hard Eligibility Gates (Pre-filtering)
    # -------------------------------------------------------------------------
    @staticmethod
    def check_eligibility(
        requester: ParticipantContext, candidate: ParticipantContext
    ) -> Tuple[bool, Optional[str]]:
        """Verify hard constraints before calculating compatibility scores.

        Rules:
        1. Self-match is strictly excluded.
        2. Both requester and candidate accounts must be active (is_active = True).
        3. Both requester and candidate must have an initialized profile.
        4. Explicit consent (allow_agent_matching = True) is mandatory for both (GAP-06).
        5. Neither participant can be in DO_NOT_DISTURB or OFFLINE availability mode.
        """
        # Rule 1: Self-match exclusion
        if requester.user_id == candidate.user_id:
            return False, "Self-match excluded"

        # Rule 2: Account active status
        if not requester.is_active:
            return False, "Requester account is deactivated"
        if not candidate.is_active:
            return False, "Candidate account is deactivated"

        # Rule 3: Profile initialization
        if not requester.has_profile or requester.intent is None:
            return False, "Requester profile is not initialized"
        if not candidate.has_profile or candidate.intent is None:
            return False, "Candidate profile is not initialized"

        # Rule 4: Explicit consent (GAP-06)
        if not requester.allow_agent_matching:
            return False, "Requester has not opted into autonomous agent matching"
        if not candidate.allow_agent_matching:
            return False, "Candidate has not opted into autonomous agent matching"

        # Rule 5: Availability boundaries
        ineligible_statuses = {AvailabilityStatus.DO_NOT_DISTURB, AvailabilityStatus.OFFLINE}
        if requester.availability in ineligible_statuses:
            return False, "Requester is in DO_NOT_DISTURB or OFFLINE status"
        if candidate.availability in ineligible_statuses:
            return False, "Candidate is in DO_NOT_DISTURB or OFFLINE status"

        return True, None

    # -------------------------------------------------------------------------
    # 2. Factor Similarity Metrics
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_intent_similarity(
        intent_a: ParticipationIntent, intent_b: ParticipationIntent
    ) -> float:
        """Evaluate networking intent alignment.

        - Exact match (NETWORKING vs NETWORKING, CASUAL vs CASUAL, BOTH vs BOTH): 1.0
        - Either is open to BOTH: 0.8 (compatible dialogue)
        - Disjoint (NETWORKING vs CASUAL): 0.0
        """
        if intent_a == intent_b:
            return 1.0
        if intent_a == ParticipationIntent.BOTH or intent_b == ParticipationIntent.BOTH:
            return 0.8
        return 0.0

    @staticmethod
    def calculate_jaccard_similarity(
        set_a: Set, set_b: Set
    ) -> Tuple[float, bool]:
        """Compute Jaccard similarity index: |A ∩ B| / |A ∪ B|.

        Distinguishes between:
        - No available data: If either participant has 0 items (len(A) == 0 or len(B) == 0),
          meaningful comparison is impossible -> returns (0.0, False) to trigger dynamic re-weighting.
        - Available data with zero similarity: Both participants declared items, but have 0 overlap ->
          returns (0.0, True), actively evaluating the dimension as 0.0 similarity.
        """
        if len(set_a) == 0 or len(set_b) == 0:
            return 0.0, False
        union_len = len(set_a | set_b)
        intersection_len = len(set_a & set_b)
        return round(intersection_len / union_len, 4), True

    # -------------------------------------------------------------------------
    # 3. Dynamic Re-weighting & Composite Evaluation
    # -------------------------------------------------------------------------
    def evaluate_pair(
        self,
        requester: ParticipantContext,
        candidate: ParticipantContext,
        weights: Optional[MatchFactorWeights] = None,
        temporal_context: Optional[Any] = None,
    ) -> Optional[CandidateMatchResponse]:
        """Evaluate candidate against requester, applying dynamic re-weighting and temporal boost (Phase 2)."""
        is_eligible, _ = self.check_eligibility(requester, candidate)
        if not is_eligible:
            return None

        w = weights or self.weights

        # 1. Intent Factor (always active since profile requires intent)
        intent_sim = self.calculate_intent_similarity(requester.intent, candidate.intent)
        intent_active = True

        # 2. Topics Factor
        topics_sim, topics_active = self.calculate_jaccard_similarity(
            requester.normalized_topics, candidate.normalized_topics
        )

        # 3. Agenda Factor (Bookmarked sessions overlap)
        agenda_sim, agenda_active = self.calculate_jaccard_similarity(
            requester.bookmarked_session_ids, candidate.bookmarked_session_ids
        )

        # 4. Hobbies Factor
        hobbies_sim, hobbies_active = self.calculate_jaccard_similarity(
            requester.normalized_hobbies, candidate.normalized_hobbies
        )

        # Compute sum of active baseline weights
        active_weights_sum = 0.0
        if intent_active:
            active_weights_sum += w.intent_weight
        if topics_active:
            active_weights_sum += w.topics_weight
        if agenda_active:
            active_weights_sum += w.agenda_weight
        if hobbies_active:
            active_weights_sum += w.hobbies_weight

        # Normalization & Dynamic Re-weighting (TST-007)
        if active_weights_sum > 0.0:
            eff_intent_w = round(w.intent_weight / active_weights_sum, 4) if intent_active else 0.0
            eff_topics_w = round(w.topics_weight / active_weights_sum, 4) if topics_active else 0.0
            eff_agenda_w = round(w.agenda_weight / active_weights_sum, 4) if agenda_active else 0.0
            eff_hobbies_w = round(w.hobbies_weight / active_weights_sum, 4) if hobbies_active else 0.0

            composite = (
                (eff_intent_w * intent_sim)
                + (eff_topics_w * topics_sim)
                + (eff_agenda_w * agenda_sim)
                + (eff_hobbies_w * hobbies_sim)
            )
            composite_score = round(min(max(composite, 0.0), 1.0), 4)
        else:
            eff_intent_w = eff_topics_w = eff_agenda_w = eff_hobbies_w = 0.0
            composite_score = 0.0

        # Construct explainable breakdown
        breakdown = MatchScoreBreakdown(
            intent=FactorScoreDetail(
                raw_similarity=intent_sim,
                baseline_weight=w.intent_weight,
                effective_weight=eff_intent_w,
                is_active=intent_active,
            ),
            topics=FactorScoreDetail(
                raw_similarity=topics_sim,
                baseline_weight=w.topics_weight,
                effective_weight=eff_topics_w,
                is_active=topics_active,
            ),
            agenda=FactorScoreDetail(
                raw_similarity=agenda_sim,
                baseline_weight=w.agenda_weight,
                effective_weight=eff_agenda_w,
                is_active=agenda_active,
            ),
            hobbies=FactorScoreDetail(
                raw_similarity=hobbies_sim,
                baseline_weight=w.hobbies_weight,
                effective_weight=eff_hobbies_w,
                is_active=hobbies_active,
            ),
            composite_score=composite_score,
        )

        # Common overlaps (preserving display capitalization)
        common_topics_normalized = requester.normalized_topics & candidate.normalized_topics
        common_topics = sorted(
            [t for t in candidate.raw_topics if t.lower().strip() in common_topics_normalized]
        )

        common_hobbies_normalized = requester.normalized_hobbies & candidate.normalized_hobbies
        common_hobbies = sorted(
            [h for h in candidate.raw_hobbies if h.lower().strip() in common_hobbies_normalized]
        )

        common_sessions = requester.bookmarked_session_ids & candidate.bookmarked_session_ids

        # Explainability Rationale
        reasons = []
        if intent_sim >= 0.8:
            reasons.append(f"Aligned intent ({requester.intent.value} & {candidate.intent.value})")
        if common_topics:
            reasons.append(f"{len(common_topics)} shared topic(s): {', '.join(common_topics[:3])}")
        if common_sessions:
            reasons.append(f"{len(common_sessions)} mutually bookmarked conference session(s)")
        if common_hobbies:
            reasons.append(f"{len(common_hobbies)} common interest(s): {', '.join(common_hobbies[:2])}")

        # Temporal Context Boost (Phase 2: Tea/Coffee break + Session talk momentum)
        temporal_boost = 0.0
        temporal_reasons = []

        if temporal_context and getattr(temporal_context, "is_active", False):
            curr_state = getattr(temporal_context, "current_state", None)
            break_type = getattr(temporal_context, "break_type", None)

            # 1. Break Synergy Boost (+15%): Active Tea Break & Shared Tea/Coffee hobby
            if curr_state == "TEA_BREAK" or break_type == "TEA_COFFEE":
                tea_hobbies = {"tea / coffee", "tea", "coffee", "casual conversations"}
                has_req_tea = any(h in tea_hobbies for h in requester.normalized_hobbies)
                has_cand_tea = any(h in tea_hobbies for h in candidate.normalized_hobbies)

                if has_req_tea and has_cand_tea:
                    temporal_boost += 0.15
                    temporal_reasons.append("☕ Tea Break Synergy • Both enjoy Tea / Coffee")
                elif has_cand_tea or has_req_tea:
                    temporal_boost += 0.08
                    temporal_reasons.append("☕ Tea Break Synergy • Open for a coffee/tea sync")
            elif curr_state == "LUNCH_BREAK" or break_type == "LUNCH":
                temporal_boost += 0.10
                temporal_reasons.append("🍽️ Lunch Break Networking • Free for lunch discussion")

            # 2. Session Talk Momentum (+15%): Both attended / bookmarked recent session
            recent_sess_id = getattr(temporal_context, "recently_ended_session_id", None)
            recent_title = getattr(temporal_context, "recently_ended_session_title", None)
            if recent_sess_id:
                if recent_sess_id in requester.bookmarked_session_ids and recent_sess_id in candidate.bookmarked_session_ids:
                    temporal_boost += 0.15
                    temporal_reasons.append(f"🎙️ Talk Synergy • Both attended '{recent_title}'")

        # Apply boost to composite score (capped at 1.0)
        final_composite_score = round(min(max(composite_score + temporal_boost, 0.0), 1.0), 4)

        if temporal_reasons:
            reasons = temporal_reasons + reasons

        if not reasons:
            reasons.append("General attendee compatibility")

        # Project strictly sanitized candidate card (zero PII)
        return CandidateMatchResponse(
            candidate_id=candidate.user_id,
            full_name=candidate.full_name,
            company_name=candidate.company_name,
            job_title=candidate.job_title,
            intent=candidate.intent,
            availability=candidate.availability,
            bio_summary=candidate.bio_summary,
            topics=candidate.raw_topics,
            hobbies=candidate.raw_hobbies,
            composite_score=final_composite_score,
            score_breakdown=breakdown,
            common_topics=common_topics,
            common_hobbies=common_hobbies,
            common_sessions_count=len(common_sessions),
            match_reasons=reasons,
            temporal_boost=round(temporal_boost, 4),
            temporal_reason=" • ".join(temporal_reasons) if temporal_reasons else None,
        )

    # -------------------------------------------------------------------------
    # 4. Deterministic Ranking & Stable Tie-Breaking
    # -------------------------------------------------------------------------
    @staticmethod
    def rank_candidates(
        candidates: List[CandidateMatchResponse],
        threshold: float = 0.0,
    ) -> List[CandidateMatchResponse]:
        """Rank candidates with stable, reproducible tie-breaking.

        Tie-breaking hierarchy:
        1. Composite score descending (-score)
        2. Shared topics count descending (-len(common_topics))
        3. Shared sessions count descending (-common_sessions_count)
        4. Shared hobbies count descending (-len(common_hobbies))
        5. Candidate UUID string ascending (str(candidate_id)) -> guaranteed deterministic tie-breaker.
        """
        # Filter by threshold if requested
        filtered = [c for c in candidates if c.composite_score >= threshold]

        def sort_key(c: CandidateMatchResponse):
            return (
                -c.composite_score,
                -len(c.common_topics),
                -c.common_sessions_count,
                -len(c.common_hobbies),
                str(c.candidate_id),
            )

        return sorted(filtered, key=sort_key)


# =============================================================================
# Database Retrieval & Pipeline Helper
# =============================================================================

def extract_participant_context(user: User) -> ParticipantContext:
    """Extract ParticipantContext from SQLAlchemy User entity."""
    profile: Optional[ParticipantProfile] = user.profile
    has_profile = profile is not None

    raw_topics = [t.topic_keyword for t in user.topics] if user.topics else []
    raw_hobbies = [h.hobby_name for h in user.hobbies] if user.hobbies else []
    normalized_topics = {t.lower().strip() for t in raw_topics}
    normalized_hobbies = {h.lower().strip() for h in raw_hobbies}
    bookmarked_session_ids = {b.session_id for b in user.bookmarks} if user.bookmarks else set()

    return ParticipantContext(
        user_id=user.id,
        full_name=user.full_name,
        company_name=user.company_name,
        job_title=user.job_title,
        is_active=user.is_active,
        has_profile=has_profile,
        intent=profile.intent if has_profile else None,
        availability=profile.availability if has_profile else None,
        allow_agent_matching=profile.allow_agent_matching if has_profile else False,
        bio_summary=profile.bio_summary if has_profile else None,
        raw_topics=raw_topics,
        raw_hobbies=raw_hobbies,
        normalized_topics=normalized_topics,
        normalized_hobbies=normalized_hobbies,
        bookmarked_session_ids=bookmarked_session_ids,
    )


def find_candidate_matches(
    db: SASession,
    requester_id: UUID,
    weights: Optional[MatchFactorWeights] = None,
    filter_by_threshold: bool = True,
) -> MatchEvaluationResult:
    """Find and rank all eligible candidate matches for a participant from the database.

    Guarantees:
    - Pure read-only queries with zero mutations.
    - Full eager loading to prevent N+1 queries.
    - Zero exposure of private participant information.
    - Deterministic output ordering across multiple invocations.
    """
    engine = MatchingEngine(weights)
    cfg = weights or engine.weights

    # 1. Fetch requester with full relations
    requester_stmt = (
        select(User)
        .where(User.id == requester_id)
        .options(
            selectinload(User.profile),
            selectinload(User.topics),
            selectinload(User.hobbies),
            selectinload(User.bookmarks),
        )
    )
    requester_user = db.execute(requester_stmt).scalar_one_or_none()

    if not requester_user:
        return MatchEvaluationResult(
            requester_id=requester_id,
            candidates=[],
            total_evaluated=0,
            eligible_count=0,
            matched_count=0,
        )

    requester_ctx = extract_participant_context(requester_user)

    # If requester himself does not satisfy basic eligibility (e.g. inactive or consent=False),
    # return clean empty result (reasons remain private).
    if not requester_ctx.is_active or not requester_ctx.allow_agent_matching:
        return MatchEvaluationResult(
            requester_id=requester_id,
            candidates=[],
            total_evaluated=0,
            eligible_count=0,
            matched_count=0,
        )

    # 2. Fetch all other active users with profiles
    candidates_stmt = (
        select(User)
        .where(User.id != requester_id)
        .where(User.is_active == True)
        .options(
            selectinload(User.profile),
            selectinload(User.topics),
            selectinload(User.hobbies),
            selectinload(User.bookmarks),
        )
    )
    candidate_users = db.execute(candidates_stmt).scalars().all()

    evaluated_candidates: List[CandidateMatchResponse] = []
    eligible_count = 0

    for u in candidate_users:
        candidate_ctx = extract_participant_context(u)
        match_card = engine.evaluate_pair(requester_ctx, candidate_ctx, cfg)
        if match_card is not None:
            eligible_count += 1
            evaluated_candidates.append(match_card)

    # 3. Deterministically rank candidates
    threshold = cfg.match_threshold if filter_by_threshold else 0.0
    ranked = engine.rank_candidates(evaluated_candidates, threshold=threshold)

    return MatchEvaluationResult(
        requester_id=requester_id,
        candidates=ranked,
        total_evaluated=len(candidate_users),
        eligible_count=eligible_count,
        matched_count=len(ranked),
    )


async def find_candidate_matches_async(
    db: AsyncSession,
    requester_id: UUID,
    weights: Optional[MatchFactorWeights] = None,
    filter_by_threshold: bool = True,
    custom_threshold: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
) -> MatchEvaluationResult:
    """Find and rank all eligible candidate matches asynchronously from the database.

    Guarantees:
    - Pure read-only queries with zero mutations.
    - Full eager loading to prevent N+1 queries.
    - Zero exposure of private participant information.
    - Deterministic output ordering across multiple invocations.
    - Pagination support (limit and offset).
    """
    engine = MatchingEngine(weights)
    cfg = weights or engine.weights

    # 1. Fetch requester with full relations
    requester_stmt = (
        select(User)
        .where(User.id == requester_id)
        .options(
            selectinload(User.profile),
            selectinload(User.topics),
            selectinload(User.hobbies),
            selectinload(User.bookmarks),
        )
    )
    req_res = await db.execute(requester_stmt)
    requester_user = req_res.scalar_one_or_none()

    if not requester_user:
        return MatchEvaluationResult(
            requester_id=requester_id,
            candidates=[],
            total_evaluated=0,
            eligible_count=0,
            matched_count=0,
            limit=limit,
            offset=offset,
        )

    requester_ctx = extract_participant_context(requester_user)

    # If requester himself does not satisfy basic eligibility (e.g. inactive or consent=False),
    # return clean empty result (reasons remain private).
    if not requester_ctx.is_active or not requester_ctx.allow_agent_matching:
        return MatchEvaluationResult(
            requester_id=requester_id,
            candidates=[],
            total_evaluated=0,
            eligible_count=0,
            matched_count=0,
            limit=limit,
            offset=offset,
        )

    # 2. Fetch all other active users with profiles
    candidates_stmt = (
        select(User)
        .where(User.id != requester_id)
        .where(User.is_active == True)
        .options(
            selectinload(User.profile),
            selectinload(User.topics),
            selectinload(User.hobbies),
            selectinload(User.bookmarks),
        )
    )
    cand_res = await db.execute(candidates_stmt)
    candidate_users = cand_res.scalars().all()

    # Fetch active temporal context (break state & recently ended talk momentum)
    from app.services.temporal_context import TemporalContextService
    temporal_ctx = await TemporalContextService.get_current_conference_state(db)

    evaluated_candidates: List[CandidateMatchResponse] = []
    eligible_count = 0

    for u in candidate_users:
        candidate_ctx = extract_participant_context(u)
        match_card = engine.evaluate_pair(requester_ctx, candidate_ctx, cfg, temporal_context=temporal_ctx)
        if match_card is not None:
            eligible_count += 1
            evaluated_candidates.append(match_card)

    # 3. Deterministically rank candidates
    if not filter_by_threshold:
        threshold = 0.0
    elif custom_threshold is not None:
        threshold = custom_threshold
    else:
        threshold = cfg.match_threshold

    ranked = engine.rank_candidates(evaluated_candidates, threshold=threshold)
    total_matched = len(ranked)
    paged = ranked[offset : offset + limit]

    return MatchEvaluationResult(
        requester_id=requester_id,
        candidates=paged,
        total_evaluated=len(candidate_users),
        eligible_count=eligible_count,
        matched_count=total_matched,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# 5. Quota & Cooldown Lifecycle Policy (GAP-06)
# =============================================================================

@dataclass
class CooldownPolicy:
    """Canonical cooldown duration policy for participant pairs (GAP-06)."""

    proposal_generated_hours: int = 72
    completed_without_proposal_hours: int = 48
    cancelled_or_expired_hours: int = 24
    transient_failure_hours: int = 1
    max_active_tasks_per_participant: int = 3


class QuotaAndCooldownService:
    """Contract and dependency placeholder for active task quota and pair cooldown enforcement.

    Status: DEFERRED / BLOCKED on conversation & task lifecycle persistence (GAP-06).
    Once the canonical A2A task schema is migrated, this service integrates with database queries:
    1. Active task count: count(tasks) WHERE requester_id = :id AND status IN ('SUBMITTED', 'QUEUED', 'WORKING', 'PROPOSAL_GENERATING')
    2. Pair cooldown: max(completed_at) WHERE ((initiator_id = :a AND target_id = :b) OR (initiator_id = :b AND target_id = :a))
    """

    def __init__(self, policy: Optional[CooldownPolicy] = None):
        self.policy = policy or CooldownPolicy()

    def is_quota_exceeded(self, active_task_count: int) -> bool:
        """Check if participant reached maximum concurrent conversation tasks (3)."""
        return active_task_count >= self.policy.max_active_tasks_per_participant

    def evaluate_pair_cooldown(
        self,
        last_interaction_outcome: Optional[str],
        last_interaction_time: Optional[datetime],
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[timedelta]]:
        """Evaluate whether a pair cooldown is active given the last interaction outcome.

        Returns (is_in_cooldown, remaining_timedelta).
        """
        if not last_interaction_outcome or not last_interaction_time:
            return False, None

        now = current_time or datetime.now(timezone.utc)
        cooldown_hours = {
            "PROPOSAL_GENERATED": self.policy.proposal_generated_hours,
            "COMPLETED_WITHOUT_PROPOSAL": self.policy.completed_without_proposal_hours,
            "CANCELLED": self.policy.cancelled_or_expired_hours,
            "EXPIRED": self.policy.cancelled_or_expired_hours,
            "TRANSIENT_FAILURE": self.policy.transient_failure_hours,
        }.get(last_interaction_outcome, 0)

        cooldown_delta = timedelta(hours=cooldown_hours)
        if now < (last_interaction_time + cooldown_delta):
            remaining = (last_interaction_time + cooldown_delta) - now
            return True, remaining
        return False, None

