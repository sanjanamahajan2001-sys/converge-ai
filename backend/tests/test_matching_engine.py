"""Unit and database integration tests for the Centralized Matching Engine (P4-WS1, GAP-06)."""

import uuid
from datetime import datetime, timezone
from typing import List
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.models.agenda import BookmarkedSession, Conference, Session as ConfSession
from app.db.models.profile import AvailabilityStatus, ParticipantHobby, ParticipantProfile, ParticipantTopic, ParticipationIntent
from app.db.models.user import User
from app.schemas.matching import MatchFactorWeights
from app.services.matching import (
    MatchingEngine,
    ParticipantContext,
    extract_participant_context,
    find_candidate_matches,
)

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


# =============================================================================
# Unit Tests: Pure Mathematical Engine & In-Memory Policy Checks
# =============================================================================

def make_context(
    user_id: uuid.UUID = None,
    full_name: str = "Test Participant",
    is_active: bool = True,
    has_profile: bool = True,
    intent: ParticipationIntent = ParticipationIntent.NETWORKING,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
    allow_agent_matching: bool = True,
    topics: List[str] = None,
    hobbies: List[str] = None,
    bookmarked_sessions: List[uuid.UUID] = None,
) -> ParticipantContext:
    uid = user_id or uuid.uuid4()
    raw_topics = topics or []
    raw_hobbies = hobbies or []
    return ParticipantContext(
        user_id=uid,
        full_name=full_name,
        company_name="Test Corp",
        job_title="Engineer",
        is_active=is_active,
        has_profile=has_profile,
        intent=intent,
        availability=availability,
        allow_agent_matching=allow_agent_matching,
        bio_summary="Test bio",
        raw_topics=raw_topics,
        raw_hobbies=raw_hobbies,
        normalized_topics={t.lower().strip() for t in raw_topics},
        normalized_hobbies={h.lower().strip() for h in raw_hobbies},
        bookmarked_session_ids=set(bookmarked_sessions or []),
    )


def test_self_match_is_strictly_excluded():
    """Verify that a participant cannot match with themselves."""
    engine = MatchingEngine()
    p1 = make_context(user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"))
    
    is_eligible, reason = engine.check_eligibility(p1, p1)
    assert not is_eligible
    assert reason == "Self-match excluded"
    assert engine.evaluate_pair(p1, p1) is None


def test_consent_disabled_candidate_is_excluded_gap06():
    """Verify that a candidate with allow_agent_matching = False is excluded (GAP-06)."""
    engine = MatchingEngine()
    req = make_context(allow_agent_matching=True)
    cand = make_context(allow_agent_matching=False)

    is_eligible, reason = engine.check_eligibility(req, cand)
    assert not is_eligible
    assert "Candidate has not opted into autonomous agent matching" in reason
    assert engine.evaluate_pair(req, cand) is None


def test_consent_disabled_requester_is_excluded_gap06():
    """Verify that a requester with allow_agent_matching = False is excluded."""
    engine = MatchingEngine()
    req = make_context(allow_agent_matching=False)
    cand = make_context(allow_agent_matching=True)

    is_eligible, reason = engine.check_eligibility(req, cand)
    assert not is_eligible
    assert "Requester has not opted into autonomous agent matching" in reason
    assert engine.evaluate_pair(req, cand) is None


def test_uninitialized_or_missing_profile_is_excluded():
    """Verify that participants without an initialized profile cannot be matched."""
    engine = MatchingEngine()
    req = make_context()
    cand_no_profile = make_context(has_profile=False, intent=None)

    is_eligible, reason = engine.check_eligibility(req, cand_no_profile)
    assert not is_eligible
    assert "Candidate profile is not initialized" in reason
    assert engine.evaluate_pair(req, cand_no_profile) is None


def test_inactive_account_is_excluded():
    """Verify that deactivated accounts are excluded from matching."""
    engine = MatchingEngine()
    req = make_context(is_active=True)
    cand_inactive = make_context(is_active=False)

    is_eligible, reason = engine.check_eligibility(req, cand_inactive)
    assert not is_eligible
    assert "Candidate account is deactivated" in reason
    assert engine.evaluate_pair(req, cand_inactive) is None


def test_availability_boundaries():
    """Verify that DO_NOT_DISTURB and OFFLINE participants are excluded, while IN_SESSION is allowed."""
    engine = MatchingEngine()
    req = make_context(availability=AvailabilityStatus.AVAILABLE)

    # In session is allowed
    cand_in_session = make_context(availability=AvailabilityStatus.IN_SESSION)
    is_eligible, _ = engine.check_eligibility(req, cand_in_session)
    assert is_eligible

    # DND is excluded
    cand_dnd = make_context(availability=AvailabilityStatus.DO_NOT_DISTURB)
    is_eligible, reason = engine.check_eligibility(req, cand_dnd)
    assert not is_eligible
    assert "DO_NOT_DISTURB" in reason

    # OFFLINE is excluded
    cand_offline = make_context(availability=AvailabilityStatus.OFFLINE)
    is_eligible, reason = engine.check_eligibility(req, cand_offline)
    assert not is_eligible
    assert "OFFLINE" in reason


def test_intent_similarity_matrix():
    """Verify intent alignment calculations: exact = 1.0, both = 0.8, disjoint = 0.0."""
    calc = MatchingEngine.calculate_intent_similarity

    # Exact matches
    assert calc(ParticipationIntent.NETWORKING, ParticipationIntent.NETWORKING) == 1.0
    assert calc(ParticipationIntent.CASUAL, ParticipationIntent.CASUAL) == 1.0
    assert calc(ParticipationIntent.BOTH, ParticipationIntent.BOTH) == 1.0

    # Versatile matches
    assert calc(ParticipationIntent.NETWORKING, ParticipationIntent.BOTH) == 0.8
    assert calc(ParticipationIntent.BOTH, ParticipationIntent.CASUAL) == 0.8

    # Disjoint matches
    assert calc(ParticipationIntent.NETWORKING, ParticipationIntent.CASUAL) == 0.0
    assert calc(ParticipationIntent.CASUAL, ParticipationIntent.NETWORKING) == 0.0


def test_four_factor_scoring_with_all_dimensions_active():
    """Verify exact 4-factor scoring with known overlapping dimensions."""
    s1 = uuid.uuid4()
    s2 = uuid.uuid4()
    s3 = uuid.uuid4()

    req = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Kiln Decarbonization", "CCUS", "Alternative Fuels"],
        hobbies=["Tea / Coffee", "Technical Deep-dives"],
        bookmarked_sessions=[s1, s2],
    )
    cand = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Kiln Decarbonization", "CCUS", "Robotics"],
        hobbies=["Tea / Coffee", "Exhibition Walking Tours"],
        bookmarked_sessions=[s2, s3],
    )

    engine = MatchingEngine(
        MatchFactorWeights(
            intent_weight=0.25,
            topics_weight=0.35,
            agenda_weight=0.25,
            hobbies_weight=0.15,
        )
    )
    res = engine.evaluate_pair(req, cand)
    assert res is not None

    # Intent: exact match -> 1.0
    assert res.score_breakdown.intent.raw_similarity == 1.0
    assert res.score_breakdown.intent.effective_weight == 0.25

    # Topics: Intersection={kiln, ccus} (2), Union={kiln, ccus, alternative fuels, robotics} (4) -> 2/4 = 0.5
    assert res.score_breakdown.topics.raw_similarity == 0.5
    assert res.score_breakdown.topics.effective_weight == 0.35

    # Agenda: Intersection={s2} (1), Union={s1, s2, s3} (3) -> 1/3 ≈ 0.3333
    assert res.score_breakdown.agenda.raw_similarity == 0.3333
    assert res.score_breakdown.agenda.effective_weight == 0.25

    # Hobbies: Intersection={tea/coffee} (1), Union={tea/coffee, deep-dives, exhibition} (3) -> 1/3 ≈ 0.3333
    assert res.score_breakdown.hobbies.raw_similarity == 0.3333
    assert res.score_breakdown.hobbies.effective_weight == 0.15

    # Expected composite:
    # 0.25 * 1.0 + 0.35 * 0.5 + 0.25 * (1/3) + 0.15 * (1/3) = 0.25 + 0.175 + 0.083325 + 0.05 = 0.5583
    assert res.composite_score == 0.5583
    assert "Kiln Decarbonization" in res.common_topics
    assert "CCUS" in res.common_topics
    assert "Tea / Coffee" in res.common_hobbies
    assert res.common_sessions_count == 1


def test_dynamic_reweighting_missing_agenda_tst007():
    """Verify that when neither participant has bookmarks, agenda weight is redistributed (TST-007)."""
    req = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Kiln Decarbonization", "CCUS"],
        hobbies=["Tea / Coffee"],
        bookmarked_sessions=[],
    )
    cand = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Kiln Decarbonization", "CCUS"],
        hobbies=["Tea / Coffee"],
        bookmarked_sessions=[],
    )

    engine = MatchingEngine(
        MatchFactorWeights(
            intent_weight=0.25,
            topics_weight=0.35,
            agenda_weight=0.25,
            hobbies_weight=0.15,
        )
    )
    res = engine.evaluate_pair(req, cand)
    assert res is not None

    # Agenda factor is inactive
    assert not res.score_breakdown.agenda.is_active
    assert res.score_breakdown.agenda.effective_weight == 0.0

    # Active baseline weights sum: 0.25 + 0.35 + 0.15 = 0.75
    # Effective weights:
    # intent: 0.25 / 0.75 = 0.3333
    # topics: 0.35 / 0.75 = 0.4667
    # hobbies: 0.15 / 0.75 = 0.2000
    assert res.score_breakdown.intent.effective_weight == 0.3333
    assert res.score_breakdown.topics.effective_weight == 0.4667
    assert res.score_breakdown.hobbies.effective_weight == 0.2000

    # All active dimensions are 1.0 -> composite score must be 1.0!
    assert res.composite_score == 1.0


def test_dynamic_reweighting_distinction_no_data_vs_zero_similarity():
    """Verify distinction between 'no data' (re-weighted) and 'zero similarity' (penalized)."""
    engine = MatchingEngine(
        MatchFactorWeights(
            intent_weight=0.25,
            topics_weight=0.35,
            agenda_weight=0.25,
            hobbies_weight=0.15,
        )
    )

    # Case 1: Both participants have topics, but 0 overlap -> zero similarity, ACTIVE factor (penalizes score)
    req1 = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Decarbonization", "Hydrogen"],
        hobbies=[],
        bookmarked_sessions=[],
    )
    cand1 = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Tax Law", "Corporate Finance"],
        hobbies=[],
        bookmarked_sessions=[],
    )
    res1 = engine.evaluate_pair(req1, cand1)
    assert res1 is not None
    # Hobbies and agenda have no data -> inactive
    assert not res1.score_breakdown.hobbies.is_active
    assert not res1.score_breakdown.agenda.is_active
    # Topics has data for both, so it is ACTIVE with similarity 0.0
    assert res1.score_breakdown.topics.is_active
    assert res1.score_breakdown.topics.raw_similarity == 0.0
    # Active weights: intent (0.25), topics (0.35) -> total active = 0.60
    # effective_weight(intent) = 0.25 / 0.60 = 0.4167
    # effective_weight(topics) = 0.35 / 0.60 = 0.5833
    # Composite score = 0.4167 * 1.0 + 0.5833 * 0.0 = 0.4167 (penalized by topics mismatch!)
    assert res1.composite_score == 0.4167

    # Case 2: One participant has 0 topics -> no data, INACTIVE factor (re-weighted, does not penalize)
    req2 = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=["Decarbonization", "Hydrogen"],
        hobbies=[],
        bookmarked_sessions=[],
    )
    cand2 = make_context(
        intent=ParticipationIntent.NETWORKING,
        topics=[],  # Missing topics
        hobbies=[],
        bookmarked_sessions=[],
    )
    res2 = engine.evaluate_pair(req2, cand2)
    assert res2 is not None
    # Topics has no data for candidate -> INACTIVE
    assert not res2.score_breakdown.topics.is_active
    assert not res2.score_breakdown.hobbies.is_active
    assert not res2.score_breakdown.agenda.is_active
    # Only intent is active -> effective weight = 1.0
    assert res2.score_breakdown.intent.is_active
    assert res2.score_breakdown.intent.effective_weight == 1.0
    # Composite score = 1.0 * 1.0 = 1.0 (not penalized!)
    assert res2.composite_score == 1.0


def test_deterministic_reproducibility():
    """Verify that identical inputs produce identical ordered results across 100 iterations."""
    engine = MatchingEngine()
    req = make_context(
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        topics=["Automation", "Sensors"],
    )

    c1 = make_context(
        user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        full_name="Candidate B",
        topics=["Automation", "Sensors"],
    )
    c2 = make_context(
        user_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        full_name="Candidate C",
        topics=["Automation"],
    )

    evaluated_1 = [engine.evaluate_pair(req, c1), engine.evaluate_pair(req, c2)]
    ranked_1 = engine.rank_candidates(evaluated_1)

    for _ in range(100):
        evaluated_n = [engine.evaluate_pair(req, c1), engine.evaluate_pair(req, c2)]
        ranked_n = engine.rank_candidates(evaluated_n)
        assert [c.candidate_id for c in ranked_n] == [c.candidate_id for c in ranked_1]
        assert [c.composite_score for c in ranked_n] == [c.composite_score for c in ranked_1]


def test_stable_tie_breaking_order():
    """Verify stable tie-breaking when two candidates have identical scores."""
    engine = MatchingEngine()
    req = make_context(topics=["A"])

    # Two candidates with identical scores and topic counts, different UUIDs
    uid_lower = uuid.UUID("10000000-0000-0000-0000-000000000000")
    uid_higher = uuid.UUID("20000000-0000-0000-0000-000000000000")

    c_higher = make_context(user_id=uid_higher, full_name="Higher UUID", topics=["A"])
    c_lower = make_context(user_id=uid_lower, full_name="Lower UUID", topics=["A"])

    # Pass in reverse order
    ranked = engine.rank_candidates([
        engine.evaluate_pair(req, c_higher),
        engine.evaluate_pair(req, c_lower),
    ])

    # Lower UUID must win the tie-break deterministically
    assert ranked[0].candidate_id == uid_lower
    assert ranked[1].candidate_id == uid_higher


def test_zero_pii_in_candidate_projection():
    """Verify that private credentials and contact info are absent from CandidateMatchResponse."""
    engine = MatchingEngine()
    req = make_context()
    cand = make_context()

    res = engine.evaluate_pair(req, cand)
    dumped = res.model_dump()

    # Assert forbidden fields are strictly absent
    assert "email" not in dumped
    assert "phone_number" not in dumped
    assert "password_hash" not in dumped
    assert "session_token" not in dumped
    assert "allow_agent_matching" not in dumped
    assert "is_active" not in dumped


# =============================================================================
# Database Integration Tests: Real Persistence with SQLAlchemy
# =============================================================================

@pytest.fixture(scope="module")
def sync_engine():
    """Create synchronous engine for database integration tests."""
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(sync_engine):
    """Clean tables before each database test."""
    with sync_engine.connect() as conn:
        conn.exec_driver_sql("DELETE FROM agenda.bookmarked_sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.conferences;")
        conn.exec_driver_sql("DELETE FROM core.participant_topics;")
        conn.exec_driver_sql("DELETE FROM core.participant_hobbies;")
        conn.exec_driver_sql("DELETE FROM core.participant_profiles;")
        conn.exec_driver_sql("DELETE FROM core.user_sessions;")
        conn.exec_driver_sql("DELETE FROM core.audit_logs;")
        conn.exec_driver_sql("DELETE FROM core.users;")
        conn.commit()
    yield
    with sync_engine.connect() as conn:
        conn.exec_driver_sql("DELETE FROM agenda.bookmarked_sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.sessions;")
        conn.exec_driver_sql("DELETE FROM agenda.conferences;")
        conn.exec_driver_sql("DELETE FROM core.participant_topics;")
        conn.exec_driver_sql("DELETE FROM core.participant_hobbies;")
        conn.exec_driver_sql("DELETE FROM core.participant_profiles;")
        conn.exec_driver_sql("DELETE FROM core.user_sessions;")
        conn.exec_driver_sql("DELETE FROM core.audit_logs;")
        conn.exec_driver_sql("DELETE FROM core.users;")
        conn.commit()


def test_find_candidate_matches_from_database(sync_engine):
    """Verify candidate matching query against real persisted PostgreSQL records."""
    with SASession(sync_engine) as session:
        # Create Requester (Alice)
        alice = User(
            id=uuid.uuid4(),
            username="alice_match",
            email="alice.match@example.com",
            password_hash=hash_password("Password123!"),
            full_name="Alice Martin",
            company_name="Alcon Corp",
            is_active=True,
        )
        session.add(alice)
        session.flush()

        alice_profile = ParticipantProfile(
            user_id=alice.id,
            intent=ParticipationIntent.NETWORKING,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
            bio_summary="Alice bio",
        )
        session.add(alice_profile)
        session.add(ParticipantTopic(user_id=alice.id, topic_keyword="Kiln Decarbonization"))
        session.add(ParticipantTopic(user_id=alice.id, topic_keyword="CCUS"))
        session.add(ParticipantHobby(user_id=alice.id, hobby_name="Tea / Coffee"))

        # Create Candidate 1 (Bob - Eligible, high match)
        bob = User(
            id=uuid.uuid4(),
            username="bob_match",
            email="bob.match@example.com",
            password_hash=hash_password("Password123!"),
            full_name="Bob Vance",
            company_name="Vance Refractories",
            is_active=True,
        )
        session.add(bob)
        session.flush()

        bob_profile = ParticipantProfile(
            user_id=bob.id,
            intent=ParticipationIntent.NETWORKING,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=True,
            bio_summary="Bob bio",
        )
        session.add(bob_profile)
        session.add(ParticipantTopic(user_id=bob.id, topic_keyword="Kiln Decarbonization"))
        session.add(ParticipantHobby(user_id=bob.id, hobby_name="Tea / Coffee"))

        # Create Candidate 2 (Charlie - Consent Disabled -> must be excluded)
        charlie = User(
            id=uuid.uuid4(),
            username="charlie_match",
            email="charlie.match@example.com",
            password_hash=hash_password("Password123!"),
            full_name="Charlie NoConsent",
            is_active=True,
        )
        session.add(charlie)
        session.flush()

        charlie_profile = ParticipantProfile(
            user_id=charlie.id,
            intent=ParticipationIntent.NETWORKING,
            availability=AvailabilityStatus.AVAILABLE,
            allow_agent_matching=False,  # NO CONSENT
        )
        session.add(charlie_profile)

        # Create Candidate 3 (Dave - Deactivated -> must be excluded)
        dave = User(
            id=uuid.uuid4(),
            username="dave_match",
            email="dave.match@example.com",
            password_hash=hash_password("Password123!"),
            full_name="Dave Inactive",
            is_active=False,  # INACTIVE
        )
        session.add(dave)
        session.flush()

        session.commit()

        # Run matching for Alice
        result = find_candidate_matches(session, alice.id, filter_by_threshold=False)

        assert result.requester_id == alice.id
        # Evaluated all active candidates (Bob & Charlie; Dave is inactive so excluded by query)
        assert result.total_evaluated == 2
        # Only Bob satisfies consent
        assert result.eligible_count == 1
        assert len(result.candidates) == 1
        assert result.candidates[0].candidate_id == bob.id
        assert result.candidates[0].full_name == "Bob Vance"
        assert "Kiln Decarbonization" in result.candidates[0].common_topics
        assert "Tea / Coffee" in result.candidates[0].common_hobbies


def test_empty_candidate_pool_returns_clean_result(sync_engine):
    """Verify that when 0 eligible candidates exist, empty result is returned gracefully."""
    with SASession(sync_engine) as session:
        solo_user = User(
            id=uuid.uuid4(),
            username="solo_user",
            email="solo@example.com",
            password_hash=hash_password("Password123!"),
            full_name="Solo User",
            is_active=True,
        )
        session.add(solo_user)
        session.flush()

        session.add(
            ParticipantProfile(
                user_id=solo_user.id,
                intent=ParticipationIntent.NETWORKING,
                availability=AvailabilityStatus.AVAILABLE,
                allow_agent_matching=True,
            )
        )
        session.commit()

        result = find_candidate_matches(session, solo_user.id)
        assert result.requester_id == solo_user.id
        assert result.candidates == []
        assert result.total_evaluated == 0
        assert result.eligible_count == 0
        assert result.matched_count == 0
