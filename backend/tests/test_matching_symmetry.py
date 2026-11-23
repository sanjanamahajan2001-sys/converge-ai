"""Targeted test suite verifying strict mathematical symmetry of the matching engine.

Proves:
1. Intent similarity is strictly symmetric across all 9 possible (Intent A, Intent B) pairs.
2. Jaccard similarity is strictly symmetric across all combinations of sets (empty, disjoint, subsets, overlapping, identical).
3. Dynamic reweighting and composite scores are strictly symmetric:
   evaluate_pair(A, B).composite_score == evaluate_pair(B, A).composite_score
   for arbitrary combinations of intents, topics, hobbies, and bookmarked sessions.
"""

import itertools
from uuid import uuid4
import pytest
from app.db.models.profile import AvailabilityStatus, ParticipationIntent
from app.schemas.matching import MatchFactorWeights
from app.services.matching import MatchingEngine, ParticipantContext


def make_context(
    name: str = "Test User",
    intent: ParticipationIntent = ParticipationIntent.NETWORKING,
    topics: list[str] = None,
    hobbies: list[str] = None,
    bookmarks: list = None,
    allow_matching: bool = True,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
) -> ParticipantContext:
    raw_topics = topics or []
    raw_hobbies = hobbies or []
    norm_topics = {t.lower().strip() for t in raw_topics}
    norm_hobbies = {h.lower().strip() for h in raw_hobbies}
    bms = set(bookmarks or [])

    return ParticipantContext(
        user_id=uuid4(),
        full_name=name,
        company_name="TestCorp",
        job_title="Engineer",
        is_active=True,
        has_profile=True,
        intent=intent,
        availability=availability,
        allow_agent_matching=allow_matching,
        bio_summary="A test bio.",
        raw_topics=raw_topics,
        raw_hobbies=raw_hobbies,
        normalized_topics=norm_topics,
        normalized_hobbies=norm_hobbies,
        bookmarked_session_ids=bms,
    )


class TestMatchingEngineSymmetry:
    """Comprehensive symmetry verification."""

    @pytest.mark.parametrize(
        "intent_a,intent_b",
        list(itertools.product(list(ParticipationIntent), list(ParticipationIntent))),
    )
    def test_intent_similarity_is_symmetric(self, intent_a, intent_b):
        """Verify sim(A, B) == sim(B, A) across all 3x3=9 intent combinations."""
        sim_ab = MatchingEngine.calculate_intent_similarity(intent_a, intent_b)
        sim_ba = MatchingEngine.calculate_intent_similarity(intent_b, intent_a)
        assert sim_ab == sim_ba, f"Intent asymmetry for ({intent_a}, {intent_b}): {sim_ab} != {sim_ba}"

    @pytest.mark.parametrize(
        "set_a,set_b",
        [
            (set(), set()),
            ({"ai"}, set()),
            (set(), {"ai"}),
            ({"ai"}, {"cloud"}),
            ({"ai", "cloud"}, {"ai"}),
            ({"ai", "cloud"}, {"ai", "cloud"}),
            ({"ai", "cloud", "devops"}, {"cloud", "security"}),
            ({"python", "rust", "go", "k8s"}, {"rust", "typescript", "k8s", "c++"}),
        ],
    )
    def test_jaccard_similarity_is_symmetric(self, set_a, set_b):
        """Verify Jaccard similarity and active flags are strictly commutative."""
        sim_ab, active_ab = MatchingEngine.calculate_jaccard_similarity(set_a, set_b)
        sim_ba, active_ba = MatchingEngine.calculate_jaccard_similarity(set_b, set_a)
        assert sim_ab == sim_ba, f"Similarity mismatch: {sim_ab} != {sim_ba}"
        assert active_ab == active_ba, f"Active flag mismatch: {active_ab} != {active_ba}"

    def test_composite_score_symmetry_across_intent_matrix(self):
        """Verify evaluate_pair(A, B).composite_score == evaluate_pair(B, A).composite_score

        Tests across all 9 intent pairs with fixed topics and hobbies.
        """
        engine = MatchingEngine()
        all_intents = list(ParticipationIntent)

        for intent_a, intent_b in itertools.product(all_intents, all_intents):
            user_a = make_context("User A", intent=intent_a, topics=["Python", "FastAPI"], hobbies=["Chess"])
            user_b = make_context("User B", intent=intent_b, topics=["FastAPI", "React"], hobbies=["Chess", "Running"])

            card_ab = engine.evaluate_pair(user_a, user_b)
            card_ba = engine.evaluate_pair(user_b, user_a)

            assert card_ab is not None
            assert card_ba is not None
            assert card_ab.composite_score == card_ba.composite_score, (
                f"Symmetry failed for ({intent_a}, {intent_b}): {card_ab.composite_score} != {card_ba.composite_score}"
            )
            # Factor-level symmetry
            assert card_ab.score_breakdown.intent.raw_similarity == card_ba.score_breakdown.intent.raw_similarity
            assert card_ab.score_breakdown.topics.raw_similarity == card_ba.score_breakdown.topics.raw_similarity
            assert card_ab.score_breakdown.hobbies.raw_similarity == card_ba.score_breakdown.hobbies.raw_similarity
            assert card_ab.score_breakdown.agenda.raw_similarity == card_ba.score_breakdown.agenda.raw_similarity

    def test_composite_score_symmetry_with_missing_and_varied_dimensions(self):
        """Exhaustively verify symmetry when 0, 1, 2, or 3 dimensions are empty/missing."""
        engine = MatchingEngine()
        s1, s2, s3 = uuid4(), uuid4(), uuid4()

        test_topic_scenarios = [
            ([], []),
            (["AI"], []),
            ([], ["AI"]),
            (["AI"], ["Cloud"]),
            (["AI", "ML"], ["AI", "Security"]),
        ]

        test_hobby_scenarios = [
            ([], []),
            (["Reading"], []),
            ([], ["Reading"]),
            (["Reading"], ["Gaming"]),
            (["Reading", "Coffee"], ["Coffee", "Cycling"]),
        ]

        test_agenda_scenarios = [
            ([], []),
            ([s1], []),
            ([], [s1]),
            ([s1], [s2]),
            ([s1, s2], [s2, s3]),
        ]

        # Test combinations across scenario pairs
        for topics_a, topics_b in test_topic_scenarios:
            for hobbies_a, hobbies_b in test_hobby_scenarios:
                for bms_a, bms_b in test_agenda_scenarios:
                    user_a = make_context(
                        "User A",
                        intent=ParticipationIntent.NETWORKING,
                        topics=topics_a,
                        hobbies=hobbies_a,
                        bookmarks=bms_a,
                    )
                    user_b = make_context(
                        "User B",
                        intent=ParticipationIntent.BOTH,
                        topics=topics_b,
                        hobbies=hobbies_b,
                        bookmarks=bms_b,
                    )

                    card_ab = engine.evaluate_pair(user_a, user_b)
                    card_ba = engine.evaluate_pair(user_b, user_a)

                    assert card_ab is not None
                    assert card_ba is not None
                    assert card_ab.composite_score == card_ba.composite_score, (
                        f"Composite score asymmetry: {card_ab.composite_score} != {card_ba.composite_score}\n"
                        f"A: topics={topics_a}, hobbies={hobbies_a}, bms={len(bms_a)}\n"
                        f"B: topics={topics_b}, hobbies={hobbies_b}, bms={len(bms_b)}"
                    )
                    assert card_ab.score_breakdown.composite_score == card_ba.score_breakdown.composite_score
                    assert card_ab.score_breakdown.intent.effective_weight == card_ba.score_breakdown.intent.effective_weight
                    assert card_ab.score_breakdown.topics.effective_weight == card_ba.score_breakdown.topics.effective_weight
                    assert card_ab.score_breakdown.agenda.effective_weight == card_ba.score_breakdown.agenda.effective_weight
                    assert card_ab.score_breakdown.hobbies.effective_weight == card_ba.score_breakdown.hobbies.effective_weight

    def test_eligibility_gate_symmetry(self):
        """Hard eligibility checks must be symmetric for active consent and availability."""
        # 1. Missing consent on either side makes pair ineligible in both directions
        a_no_consent = make_context("A", allow_matching=False)
        b_with_consent = make_context("B", allow_matching=True)

        elig_ab, reason_ab = MatchingEngine.check_eligibility(a_no_consent, b_with_consent)
        elig_ba, reason_ba = MatchingEngine.check_eligibility(b_with_consent, a_no_consent)
        assert elig_ab is False
        assert elig_ba is False

        # 2. DND status on either side makes pair ineligible in both directions
        a_dnd = make_context("A", availability=AvailabilityStatus.DO_NOT_DISTURB)
        b_avail = make_context("B", availability=AvailabilityStatus.AVAILABLE)

        elig_ab, _ = MatchingEngine.check_eligibility(a_dnd, b_avail)
        elig_ba, _ = MatchingEngine.check_eligibility(b_avail, a_dnd)
        assert elig_ab is False
        assert elig_ba is False
