"""Unit tests for Phase 2: Temporal Matching Algorithm & Scoring Boost.

Verifies:
1. Candidate evaluation without temporal context produces standard composite score.
2. Active TEA_BREAK grants +0.15 boost when both users enjoy Tea/Coffee.
3. Recently ended session momentum grants +0.15 boost when both attended.
4. Combined boosts are capped cleanly at 1.0.
5. Temporal reasons are prepended to match_reasons.
"""
from uuid import uuid4
from app.db.models.profile import AvailabilityStatus, ParticipationIntent
from app.schemas.agenda import ConferenceLiveStateResponse
from app.services.matching import MatchingEngine, ParticipantContext


def create_mock_context(
    name: str,
    hobbies: list[str],
    topics: list[str],
    sessions: set,
) -> ParticipantContext:
    """Helper to create test participant context."""
    return ParticipantContext(
        user_id=uuid4(),
        full_name=name,
        company_name=f"{name} Corp",
        job_title="Engineer",
        is_active=True,
        has_profile=True,
        intent=ParticipationIntent.NETWORKING,
        availability=AvailabilityStatus.AVAILABLE,
        allow_agent_matching=True,
        raw_topics=topics,
        normalized_topics={t.lower().strip() for t in topics},
        raw_hobbies=hobbies,
        normalized_hobbies={h.lower().strip() for h in hobbies},
        bookmarked_session_ids=sessions,
    )


def test_matching_without_temporal_context():
    """Verify standard evaluation when temporal_context is None."""
    engine = MatchingEngine()
    req = create_mock_context("Sanjana", ["Reading"], ["Cement", "Decarbonization"], set())
    cand = create_mock_context("Vikram", ["Reading"], ["Cement"], set())

    match = engine.evaluate_pair(req, cand, temporal_context=None)
    assert match is not None
    assert match.temporal_boost == 0.0
    assert match.temporal_reason is None
    # No tea break reason
    assert not any("Tea Break" in r for r in match.match_reasons)


def test_matching_tea_break_boost():
    """Verify +0.15 boost during TEA_BREAK when both users share Tea / Coffee hobby."""
    engine = MatchingEngine()
    req = create_mock_context("Sanjana", ["Tea / Coffee", "Cycling"], ["Cement"], set())
    cand = create_mock_context("Vikram", ["Tea / Coffee", "Running"], ["Cement"], set())

    # 1. Base score without break
    base_match = engine.evaluate_pair(req, cand, temporal_context=None)
    base_score = base_match.composite_score

    # 2. Score during active TEA_BREAK
    temporal_ctx = ConferenceLiveStateResponse(
        conference_id=uuid4(),
        current_state="TEA_BREAK",
        break_type="TEA_COFFEE",
        designated_location="West Terrace Lounge",
        is_active=True,
    )

    boosted_match = engine.evaluate_pair(req, cand, temporal_context=temporal_ctx)
    assert boosted_match is not None
    assert boosted_match.temporal_boost == 0.15
    assert boosted_match.composite_score == round(min(base_score + 0.15, 1.0), 4)
    assert "☕ Tea Break Synergy • Both enjoy Tea / Coffee" in boosted_match.match_reasons[0]


def test_matching_session_talk_momentum_boost():
    """Verify +0.15 boost when both users attended a recently ended talk."""
    engine = MatchingEngine()
    shared_session_id = uuid4()
    req = create_mock_context("Sanjana", ["Cycling"], ["Cement"], {shared_session_id})
    cand = create_mock_context("Vikram", ["Running"], ["Cement"], {shared_session_id})

    base_match = engine.evaluate_pair(req, cand, temporal_context=None)
    base_score = base_match.composite_score

    temporal_ctx = ConferenceLiveStateResponse(
        conference_id=uuid4(),
        current_state="IN_SESSION",
        break_type="NONE",
        is_active=True,
        recently_ended_session_id=shared_session_id,
        recently_ended_session_title="LC3 Cement Formulations Keynote",
    )

    boosted_match = engine.evaluate_pair(req, cand, temporal_context=temporal_ctx)
    assert boosted_match is not None
    assert boosted_match.temporal_boost == 0.15
    assert boosted_match.composite_score == round(min(base_score + 0.15, 1.0), 4)
    assert "🎙️ Talk Synergy • Both attended 'LC3 Cement Formulations Keynote'" in boosted_match.match_reasons[0]


def test_matching_combined_boost_capping():
    """Verify combined tea break + session momentum boosts are capped at 1.0."""
    engine = MatchingEngine()
    shared_session_id = uuid4()
    # High overlapping profiles
    req = create_mock_context("Sanjana", ["Tea / Coffee"], ["Cement", "LC3", "Kiln"], {shared_session_id})
    cand = create_mock_context("Vikram", ["Tea / Coffee"], ["Cement", "LC3", "Kiln"], {shared_session_id})

    temporal_ctx = ConferenceLiveStateResponse(
        conference_id=uuid4(),
        current_state="TEA_BREAK",
        break_type="TEA_COFFEE",
        is_active=True,
        recently_ended_session_id=shared_session_id,
        recently_ended_session_title="LC3 Keynote",
    )

    match = engine.evaluate_pair(req, cand, temporal_context=temporal_ctx)
    assert match is not None
    # 0.15 + 0.15 = 0.30 boost
    assert match.temporal_boost == 0.30
    assert match.composite_score <= 1.0
    assert len(match.match_reasons) >= 2
