"""Automated Test Suite for Grounded Commercial Representative RFQ & Dialogue Branching (Phase 5).

Verifies:
1. RFQ_PRODUCT 5-turn complete deterministic exchange (Use Case 1: Material Procurement).
2. RFI_SERVICE 5-turn complete deterministic exchange (Use Case 2: Vendor / Service Procurement).
3. ALTERNATIVE_SOURCING dialogue branching (Secondary supplier / dual-sourcing qualification).
4. DISTRIBUTION_EXPANSION dialogue branching (Territorial dealerships & channel sales).
5. Strict anti-hallucination pricing guard: withholds pricing if > 60 days stale.
6. Strict anti-hallucination pricing guard: withholds pricing if is_public_indicative is False.
7. Strict anti-hallucination allocation guard: flags unrecorded commitments transparently.
8. Zero regression on Mode A networking dialogue when business_context is None.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
import pytest

from app.db.models.profile import ParticipantProfile
from app.db.models.user import User
from app.schemas.a2a import A2AActionType
from app.services.representative import DeterministicRepresentativeEngine


@pytest.fixture
def test_participants():
    """Create dummy initiator and target users and profiles."""
    user_initiator = User(
        id=uuid.uuid4(),
        username="sanjana_buyer",
        email="sanjana@buyer.com",
        full_name="Mahajan Sanjana",
        company_name="Infrastructure EPC Group",
        job_title="Head of Procurement",
        password_hash="dummy",
        phone_number="+91-9876543210",
    )
    prof_initiator = ParticipantProfile(
        user_id=user_initiator.id,
        bio_summary="Procurement director for major infrastructure highways and airports.",
    )

    user_target = User(
        id=uuid.uuid4(),
        username="maahi_vendor",
        email="maahi@decarb.com",
        full_name="Maahi Sharma",
        company_name="Maahi Decarb Materials Pvt Ltd",
        job_title="Commercial Director",
        password_hash="dummy",
        phone_number="+91-9876543211",
    )
    prof_target = ParticipantProfile(
        user_id=user_target.id,
        bio_summary="Green cement manufacturer and specialized logistics fleet operator.",
    )

    return user_initiator, prof_initiator, user_target, prof_target


def test_rfq_product_5_turn_complete_dialogue(test_participants):
    """Use Case 1: Material Procurement (LC3 Cement) executes grounded 5-turn dialogue."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Business context: 1,000 MT LC3 to Pune in 42 days
    business_ctx = SimpleNamespace(
        inquiry_type="RFQ_PRODUCT",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="CALCINED_CLAY_LC3",
        quantity=Decimal("1000"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=42,
        inquiry_notes="NABL batch test reports required with each delivery rake.",
        urgency="PLANNED",
    )

    # Target offering: 2,500 MT/mo capacity, fresh pricing ₹4,900 - ₹5,100 Ex-Works
    target_offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("2500"),
        declared_committed_volume=Decimal("1500"),
        capacity_unit="METRIC_TONNE",
        lead_time_days=5,
        geographic_coverage=["Pune", "Mumbai", "Nashik"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4900"),
        indicative_price_max=Decimal("5100"),
        price_currency="INR",
        pricing_basis="EX_WORKS",
        price_last_confirmed_at=now - timedelta(days=5),  # Fresh (< 60 days)
        offers_test_certificates=True,
        vendor_certifications=["BIS", "ISO 9001", "NABL"],
    )

    init_bp = SimpleNamespace(company_name="Infrastructure EPC Group")
    target_bp = SimpleNamespace(company_name="Maahi Decarb Materials Pvt Ltd")

    # Turn 0: Initiator Agent (speaks for Buyer)
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfq-turn-0",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t0.turn_index == 0
    assert t0.sender_id == user_init.id
    assert t0.action_type == A2AActionType.INTRODUCE
    assert "Limestone Calcined Clay Cement (LC3)" in t0.content
    assert "1,000 METRIC TONNE" in t0.content
    assert "Pune" in t0.content
    assert "42 days" in t0.content
    assert "NABL batch test reports required" in t0.content
    assert t0.metadata["is_commercial"] is True
    assert t0.metadata["inquiry_type"] == "RFQ_PRODUCT"

    # Turn 1: Target Agent (speaks for Supplier)
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfq-turn-1",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t1.turn_index == 1
    assert t1.sender_id == user_target.id
    assert t1.action_type == A2AActionType.SHARE_INTERESTS
    assert "2,500 METRIC TONNE / month" in t1.content
    assert "5 days" in t1.content
    assert "₹4,900 - ₹5,100 / METRIC TONNE (Ex Works)" in t1.content
    assert "1,000 METRIC TONNE / month uncommitted run-rate allocation" in t1.content
    assert t1.metadata["pricing_quoted"] is True

    # Turn 2: Initiator Agent (inquiries about packaging, test certs, terms)
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=2,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfq-turn-2",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t2.turn_index == 2
    assert t2.sender_id == user_init.id
    assert t2.action_type == A2AActionType.INQUIRE
    assert "test certificate availability" in t2.content
    assert "Ex-Works or delivered to site" in t2.content

    # Turn 3: Target Agent (confirms MTC, NABL, dispatch terms)
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=3,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfq-turn-3",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t3.turn_index == 3
    assert t3.sender_id == user_target.id
    assert t3.action_type == A2AActionType.PROPOSE_COLLABORATION
    assert "manufacturer test certificates (MTC)" in t3.content
    assert "BIS, ISO 9001, NABL" in t3.content
    assert "Ex-Works" in t3.content

    # Turn 4: Representative Conclusion & Handoff to human attendees
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfq-turn-4",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t4.turn_index == 4
    assert t4.action_type == A2AActionType.CONCLUDE_DIALOGUE
    assert "Commercial RFQ dialogue complete" in t4.content
    assert "hand over this channel directly" in t4.content
    assert "finalize commercial contract terms" in t4.content


def test_rfi_service_5_turn_complete_dialogue(test_participants):
    """Use Case 2: Vendor / Service Procurement (Pneumatic Bulker Haulage) executes service branch."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Business context: 25 TRUCKLOAD Bulk Haulage to Pune in 15 days
    business_ctx = SimpleNamespace(
        inquiry_type="RFI_SERVICE",
        product_name="Bulk Pneumatic Bulker Haulage Fleet",
        product_code=None,
        service_code="CONSTR_LOGISTICS",
        quantity=Decimal("25"),
        unit="TRUCKLOAD",
        delivery_location="Pune",
        timeline_days=15,
        inquiry_notes="Dedicated GPS tracking and unloader compatibility required.",
        urgency="IMMEDIATE",
    )

    # Target offering: 50 TRUCKLOAD capacity, mobilization 3 days
    target_offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("50"),
        declared_committed_volume=None,
        capacity_unit="TRUCKLOAD",
        lead_time_days=3,
        geographic_coverage=["Pune", "Mumbai", "Thane"],
        is_public_indicative=True,
        indicative_price_min=Decimal("45000"),
        indicative_price_max=Decimal("52000"),
        price_currency="INR",
        pricing_basis="PER_TRIP",
        price_last_confirmed_at=now - timedelta(days=10),
        offers_test_certificates=False,
        vendor_certifications=["ISO 9001", "GPS Fleet Monitored"],
    )

    init_bp = SimpleNamespace(company_name="Infrastructure EPC Group")
    target_bp = SimpleNamespace(company_name="Western Logistics & Heavy Haulage Fleet")

    # Turn 0: Inquires on service fleet mobilization
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfi-turn-0",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t0.turn_index == 0
    assert "industrial service requirement" in t0.content
    assert "Bulk Pneumatic Bulker Haulage Fleet" in t0.content
    assert "25 TRUCKLOAD" in t0.content
    assert "15 days" in t0.content

    # Turn 1: Confirms fleet capacity and mobilization readiness
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfi-turn-1",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t1.turn_index == 1
    assert "50 TRUCKLOAD / month" in t1.content
    assert "3 days" in t1.content
    assert "₹45,000 - ₹52,000 / TRUCKLOAD (Per Trip)" in t1.content
    assert "ISO 9001, GPS Fleet Monitored" in t1.content

    # Turn 4: Concludes service alignment and hands over to SOW
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="rfi-turn-4",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t4.turn_index == 4
    assert "Industrial service alignment complete" in t4.content
    assert "Statement of Work (SOW)" in t4.content


def test_anti_hallucination_withholds_stale_pricing(test_participants):
    """Strict Rule: Indicative pricing > 60 days old is withheld and marked for reconfirmation."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="RFQ_PRODUCT",
        product_name="Ordinary Portland Cement 53 Grade",
        quantity=Decimal("500"),
        unit="METRIC_TONNE",
        delivery_location="Mumbai",
        timeline_days=30,
        inquiry_notes=None,
    )

    # Price was confirmed 75 days ago (> 60 days threshold)
    stale_offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("1000"),
        capacity_unit="METRIC_TONNE",
        lead_time_days=4,
        geographic_coverage=["Mumbai"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4100"),
        indicative_price_max=Decimal("4300"),
        price_currency="INR",
        pricing_basis="EX_WORKS",
        price_last_confirmed_at=now - timedelta(days=75),
        offers_test_certificates=True,
        vendor_certifications=[],
    )

    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="stale-price-turn-1",
        business_context=business_ctx,
        target_offering=stale_offering,
    )

    # Must NOT quote the old 4,100 price!
    assert "₹4,100" not in t1.content
    assert "4100" not in t1.content
    assert "Indicative pricing is subject to re-confirmation (last verified over 60 days ago)" in t1.content
    assert t1.metadata["pricing_quoted"] is False


def test_anti_hallucination_withholds_private_pricing(test_participants):
    """Strict Rule: Indicative pricing is withheld if is_public_indicative is False."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="RFQ_PRODUCT",
        product_name="Portland Pozzolana Cement (PPC)",
        quantity=Decimal("2000"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=60,
        inquiry_notes=None,
    )

    private_offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("5000"),
        capacity_unit="METRIC_TONNE",
        lead_time_days=7,
        geographic_coverage=["Pune"],
        is_public_indicative=False,  # Private pricing
        indicative_price_min=Decimal("3800"),
        price_currency="INR",
        pricing_basis="EX_WORKS",
        price_last_confirmed_at=now - timedelta(days=5),
        offers_test_certificates=True,
        vendor_certifications=[],
    )

    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="private-price-turn-1",
        business_context=business_ctx,
        target_offering=private_offering,
    )

    assert "3800" not in t1.content
    assert "₹3,800" not in t1.content
    assert "Indicative commercial pricing is available upon direct commercial request with our sales desk" in t1.content
    assert t1.metadata["pricing_quoted"] is False


def test_anti_hallucination_unrecorded_commitments(test_participants):
    """Strict Rule: If committed volume is not declared, representative never guesses or assumes 100% availability."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="RFQ_PRODUCT",
        product_name="Fly Ash Grade 1",
        quantity=Decimal("300"),
        unit="METRIC_TONNE",
        delivery_location="Nashik",
        timeline_days=20,
        inquiry_notes=None,
    )

    offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("1200"),
        declared_committed_volume=None,  # Unrecorded
        capacity_unit="METRIC_TONNE",
        lead_time_days=4,
        geographic_coverage=["Nashik"],
        is_public_indicative=False,
        price_last_confirmed_at=None,
        offers_test_certificates=False,
        vendor_certifications=[],
    )

    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="unrec-commit-turn-1",
        business_context=business_ctx,
        target_offering=offering,
    )

    assert "Uncommitted allocation is unrecorded and will be verified directly by our dispatch team." in t1.content


def test_alternative_sourcing_dialogue(test_participants):
    """ALTERNATIVE_SOURCING inquiry type branches to benchmarking and trial testing runs."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="ALTERNATIVE_SOURCING",
        product_name="Low-Carbon Composite Cement",
        quantity=Decimal("500"),
        unit="METRIC_TONNE",
        delivery_location="Kolhapur",
        timeline_days=45,
        inquiry_notes="Secondary supplier qualification to hedge primary plant outage.",
    )

    offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("3000"),
        capacity_unit="METRIC_TONNE",
        lead_time_days=6,
        geographic_coverage=["Kolhapur", "Pune"],
        is_public_indicative=False,
        price_last_confirmed_at=None,
        offers_test_certificates=True,
        vendor_certifications=["GreenPro", "IS 16415"],
    )

    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="alt-turn-0",
        business_context=business_ctx,
        target_offering=offering,
    )
    assert "strategic benchmarking and secondary supplier qualification" in t0.content

    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="alt-turn-4",
        business_context=business_ctx,
        target_offering=offering,
    )
    assert "Alternative sourcing qualification dialogue complete" in t4.content
    assert "sample trial protocols established" in t4.content


def test_mode_a_dialogue_fallback_when_no_business_context(test_participants):
    """When business_context is None, dialogue seamlessly executes Mode A networking dialogue."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()

    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=["Decarbonization", "Precast Concrete"],
        initiator_hobbies=["Cricket"],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=["Decarbonization", "Fly Ash"],
        target_hobbies=["Cricket", "Chess"],
        target_sessions=[],
        idempotency_key="mode-a-turn-0",
        business_context=None,  # No commercial brief
    )

    # Standard Mode A greetings
    assert "Decarbonization" in t0.content
    assert t0.metadata.get("is_commercial") is not True
    assert t0.metadata["engine"] == "deterministic_v2"


def test_sourcing_partnership_5_turn_dialogue(test_participants):
    """Use Case 6: Supplier looking for sourcing partners (Cement Clinker Feedstock)."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="SOURCING_PARTNERSHIP",
        product_name="Cement Clinker Intermediate",
        product_code=None,
        service_code=None,
        quantity=Decimal("2000"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=30,
        urgency="PLANNED",
        target_price=None,
        is_budget_public=False,
        inquiry_notes=None,
    )

    target_offering = SimpleNamespace(
        custom_product_title="High-Grade Cement Clinker & Mineral Feedstock",
        declared_monthly_capacity=Decimal("5000"),
        declared_committed_volume=Decimal("50"),
        capacity_unit="METRIC_TONNE",
        minimum_order_quantity=Decimal("500"),
        lead_time_days=7,
        geographic_coverage=["Pune", "Mumbai", "Nagpur"],
        is_public_indicative=True,
        indicative_price_min=Decimal("3200"),
        indicative_price_max=Decimal("3399"),
        pricing_basis="EX_WORKS",
        price_currency="INR",
        price_last_confirmed_at=now,
        offers_test_certificates=True,
        vendor_certifications=["IS 16415", "ISO 9001:2015", "NABL Lab Certified"],
        service_code=None,
    )

    init_bp = SimpleNamespace(company_name="Maahi Decarb Materials Pvt Ltd")
    target_bp = SimpleNamespace(company_name="Deccan Clinker & Mineral Feedstocks Ltd")

    # Turn 0 (Maahi rep)
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="source-t0",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t0.turn_index == 0
    assert "strategic feedstock and raw material sourcing partnerships" in t0.content
    assert "2,000 METRIC TONNE" in t0.content

    # Turn 1 (Vikram rep)
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="source-t1",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t1.turn_index == 1
    assert "5,000 METRIC TONNE / month" in t1.content
    assert "IS 16415" in t1.content
    assert "ISO 9001:2015" in t1.content
    assert "₹3,200 - ₹3,399" in t1.content

    # Turn 2 (Maahi rep)
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=2,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="source-t2",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t2.turn_index == 2
    assert "minimum order commitments (MOQ)" in t2.content
    assert "(MTC / lab tests)" not in t2.content

    # Turn 3 (Vikram rep)
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=3,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="source-t3",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t3.turn_index == 3
    assert "500 METRIC TONNE" in t3.content
    assert "Ex Works" in t3.content
    assert "dedicated dispatch SLAs" in t3.content

    # Turn 4 (Maahi rep)
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="source-t4",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t4.turn_index == 4
    assert "Strategic sourcing partnership dialogue complete" in t4.content
    assert "Master Supply Agreement (MSA)" in t4.content


def test_distributor_application_5_turn_dialogue(test_participants):
    """Use Case 7: Distributor looking for Manufacturer to source & distribute."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="DISTRIBUTOR_APPLICATION",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="LC3_50_STANDARD",
        service_code=None,
        quantity=Decimal("1500"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=30,
        urgency="PLANNED",
        target_price=None,
        is_budget_public=False,
        inquiry_notes=None,
    )

    target_offering = SimpleNamespace(
        custom_product_title="Limestone Calcined Clay Cement (LC3)",
        declared_monthly_capacity=Decimal("2500"),
        declared_committed_volume=Decimal("0"),
        capacity_unit="METRIC_TONNE",
        minimum_order_quantity=Decimal("100"),
        lead_time_days=5,
        geographic_coverage=["Pune", "Mumbai", "Nashik"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4900"),
        indicative_price_max=Decimal("5100"),
        pricing_basis="EX_WORKS",
        price_currency="INR",
        price_last_confirmed_at=now,
        offers_test_certificates=True,
        vendor_certifications=["IS 16415", "GreenPro Certified"],
        service_code=None,
    )

    init_bp = SimpleNamespace(
        company_name="Apex Building Materials & Regional Distribution Ltd",
        is_distributor=True,
        distributor_territories=["Pune", "Satara", "Solapur", "Kolhapur"],
        warehousing_capacity_sqft=Decimal("60000"),
        retail_dealer_count=220,
    )
    target_bp = SimpleNamespace(company_name="Maahi Decarb Materials Pvt Ltd", is_distributor=False)

    # Turn 0 (Rohit Distributor rep)
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="distributor-t0",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t0.turn_index == 0
    assert "authorized distributorship / stockist rights" in t0.content
    assert "Pune, Satara, Solapur, Kolhapur" in t0.content

    # Turn 1 (Maahi Manufacturer rep)
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="distributor-t1",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t1.turn_index == 1
    assert "2,500 METRIC TONNE / month" in t1.content
    assert "₹4,900 - ₹5,100" in t1.content

    # Turn 2 (Rohit Distributor rep)
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=2,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="distributor-t2",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t2.turn_index == 2
    assert "60,000 sq ft" in t2.content
    assert "220 active" in t2.content
    assert "territorial exclusivity provisions" in t2.content

    # Turn 3 (Maahi Manufacturer rep)
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=3,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="distributor-t3",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t3.turn_index == 3
    assert "quarterly volume off-take tiers" in t3.content

    # Turn 4 (Rohit Distributor rep)
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="distributor-t4",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t4.turn_index == 4
    assert "Authorized distributorship evaluation dialogue complete" in t4.content
    assert "Regional Distributorship Agreement" in t4.content


def test_distribution_expansion_5_turn_dialogue(test_participants):
    """Use Case 8: Manufacturer looking for regional distributor / channel partner."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="DISTRIBUTION_EXPANSION",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="LC3_50_STANDARD",
        service_code=None,
        quantity=Decimal("1500"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=30,
        urgency="PLANNED",
        target_price=None,
        is_budget_public=False,
        inquiry_notes=None,
    )

    target_offering = SimpleNamespace(
        custom_product_title="Limestone Calcined Clay Cement (LC3)",
        declared_monthly_capacity=Decimal("2500"),
        declared_committed_volume=Decimal("0"),
        capacity_unit="METRIC_TONNE",
        minimum_order_quantity=Decimal("100"),
        lead_time_days=5,
        geographic_coverage=["Pune", "Mumbai", "Nashik"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4900"),
        indicative_price_max=Decimal("5100"),
        pricing_basis="EX_WORKS",
        price_currency="INR",
        price_last_confirmed_at=now,
        offers_test_certificates=True,
        vendor_certifications=["IS 16415"],
        service_code=None,
    )

    init_bp = SimpleNamespace(company_name="Maahi Decarb Materials Pvt Ltd", is_distributor=False)
    target_bp = SimpleNamespace(
        company_name="Apex Building Materials & Regional Distribution Ltd",
        is_distributor=True,
        distributor_territories=["Pune", "Satara", "Solapur", "Kolhapur"],
        warehousing_capacity_sqft=Decimal("60000"),
        retail_dealer_count=220,
    )

    # Turn 0 (Maahi Manufacturer rep)
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="expansion-t0",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t0.turn_index == 0
    assert "regional distribution expansion for Limestone Calcined Clay Cement (LC3)" in t0.content
    assert "Pune, Satara, Solapur, Kolhapur" in t0.content

    # Turn 1 (Rohit Distributor rep)
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="expansion-t1",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t1.turn_index == 1
    assert "60,000 sq ft" in t1.content
    assert "220 active" in t1.content

    # Turn 2 (Maahi Manufacturer rep)
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=2,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="expansion-t2",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t2.turn_index == 2
    assert "territorial exclusivity provisions" in t2.content

    # Turn 3 (Rohit Distributor rep)
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=3,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="expansion-t3",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t3.turn_index == 3
    assert "quarterly volume commitments" in t3.content

    # Turn 4 (Maahi Manufacturer rep)
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="expansion-t4",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t4.turn_index == 4
    assert "Channel distribution introductory dialogue complete" in t4.content


def test_exploratory_collaboration_5_turn_dialogue(test_participants):
    """Use Case 9: Buyer and supplier exploring a potential business relationship."""
    user_init, prof_init, user_target, prof_target = test_participants
    conv_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    business_ctx = SimpleNamespace(
        inquiry_type="EXPLORATORY_COLLABORATION",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="LC3_50_STANDARD",
        service_code=None,
        quantity=Decimal("1000"),
        unit="METRIC_TONNE",
        delivery_location="Pune",
        timeline_days=60,
        urgency="EXPLORATORY",
        target_price=None,
        is_budget_public=False,
        inquiry_notes="Exploring sustainable cement blends for upcoming infrastructure pipeline",
    )

    target_offering = SimpleNamespace(
        custom_product_title="Limestone Calcined Clay Cement (LC3)",
        declared_monthly_capacity=Decimal("2500"),
        declared_committed_volume=Decimal("0"),
        capacity_unit="METRIC_TONNE",
        minimum_order_quantity=Decimal("100"),
        lead_time_days=5,
        geographic_coverage=["Pune", "Mumbai", "Nashik"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4900"),
        indicative_price_max=Decimal("5100"),
        pricing_basis="EX_WORKS",
        price_currency="INR",
        price_last_confirmed_at=now,
        offers_test_certificates=True,
        vendor_certifications=["IS 16415"],
        service_code=None,
    )

    init_bp = SimpleNamespace(company_name="InfraTech EPC Solutions Ltd", is_distributor=False)
    target_bp = SimpleNamespace(company_name="Maahi Decarb Materials Pvt Ltd", is_distributor=False)

    # Turn 0 (Sanjana Buyer rep)
    t0 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=0,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="explore-t0",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t0.turn_index == 0
    assert "exploring a potential business relationship" in t0.content
    assert "Limestone Calcined Clay Cement (LC3)" in t0.content

    # Turn 1 (Maahi Supplier rep)
    t1 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=1,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="explore-t1",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t1.turn_index == 1
    assert "2,500 METRIC TONNE / month" in t1.content
    assert "₹4,900 - ₹5,100" in t1.content

    # Turn 2 (Sanjana Buyer rep)
    t2 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=2,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="explore-t2",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t2.turn_index == 2
    assert "partnership structures, pilot trial protocols" in t2.content

    # Turn 3 (Maahi Supplier rep)
    t3 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=3,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="explore-t3",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t3.turn_index == 3
    assert "preliminary technical data exchange, trial batch testing" in t3.content

    # Turn 4 (Sanjana Buyer rep)
    t4 = DeterministicRepresentativeEngine.generate_dialogue_turn(
        conversation_id=conv_id,
        turn_index=4,
        initiator=user_init,
        initiator_profile=prof_init,
        initiator_topics=[],
        initiator_hobbies=[],
        initiator_sessions=[],
        target=user_target,
        target_profile=prof_target,
        target_topics=[],
        target_hobbies=[],
        target_sessions=[],
        idempotency_key="explore-t4",
        business_context=business_ctx,
        target_offering=target_offering,
        initiator_business_profile=init_bp,
        target_business_profile=target_bp,
    )
    assert t4.turn_index == 4
    assert "Preliminary business relationship dialogue complete" in t4.content


def test_all_9_use_cases_10_turn_dialogue(test_participants):
    """Verify all 9 commercial discovery use cases execute complete 10-turn dialogue without failure."""
    user_init, prof_init, user_target, prof_target = test_participants
    now = datetime.now(timezone.utc)
    conv_id = uuid.uuid4()

    use_case_inquiries = [
        "RFQ_PRODUCT",
        "RFI_SERVICE",
        "SUPPLIER_PROSPECTING",
        "VENDOR_PITCH",
        "ALTERNATIVE_SOURCING",
        "SOURCING_PARTNERSHIP",
        "DISTRIBUTOR_APPLICATION",
        "DISTRIBUTION_EXPANSION",
        "EXPLORATORY_COLLABORATION",
    ]

    target_offering = SimpleNamespace(
        declared_monthly_capacity=Decimal("2500"),
        capacity_unit="METRIC_TONNE",
        lead_time_days=5,
        geographic_coverage=["Pune", "Mumbai", "Nashik"],
        is_public_indicative=True,
        indicative_price_min=Decimal("4900"),
        indicative_price_max=Decimal("5100"),
        price_currency="INR",
        pricing_basis="EX_WORKS",
        price_last_confirmed_at=now,
        offers_test_certificates=True,
        vendor_certifications=["BIS", "ISO 9001", "NABL"],
    )

    init_bp = SimpleNamespace(company_name="InfraTech EPC Solutions Ltd", is_distributor=True, warehousing_capacity_sqft=60000, retail_dealer_count=220, distributor_territories=["Pune", "Satara"])
    target_bp = SimpleNamespace(company_name="Maahi Decarb Materials Pvt Ltd", is_distributor=True, warehousing_capacity_sqft=60000, retail_dealer_count=220, distributor_territories=["Western Maharashtra"])

    for inq in use_case_inquiries:
        bctx = SimpleNamespace(
            inquiry_type=inq,
            product_name="Limestone Calcined Clay Cement (LC3)",
            product_code="CALCINED_CLAY_LC3",
            quantity=Decimal("1000"),
            unit="METRIC_TONNE",
            delivery_location="Pune",
            timeline_days=30,
            inquiry_notes="10-turn dynamic test",
        )

        for turn in range(10):
            env = DeterministicRepresentativeEngine.generate_dialogue_turn(
                conversation_id=conv_id,
                turn_index=turn,
                initiator=user_init,
                initiator_profile=prof_init,
                initiator_topics=[],
                initiator_hobbies=[],
                initiator_sessions=[],
                target=user_target,
                target_profile=prof_target,
                target_topics=[],
                target_hobbies=[],
                target_sessions=[],
                idempotency_key=f"dynamic-{inq.lower()[:5]}-turn-{turn}",
                business_context=bctx,
                target_offering=target_offering,
                initiator_business_profile=init_bp,
                target_business_profile=target_bp,
                total_planned_turns=10,
            )
            assert env.turn_index == turn
            if turn < 9:
                assert env.action_type != A2AActionType.CONCLUDE_DIALOGUE, f"Case {inq} turn {turn} concluded early!"
            else:
                assert env.action_type == A2AActionType.CONCLUDE_DIALOGUE, f"Case {inq} turn 9 did not conclude!"
                assert "Draft Proposal" in env.content, f"Case {inq} turn 9 missing Draft Proposal prompt!"
