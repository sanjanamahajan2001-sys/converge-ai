"""Integration tests for Phase 3 Multi-Dimensional Mode B Matching Engine."""
import uuid
from decimal import Decimal
from typing import Tuple
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    create_session,
    generate_session_token,
    hash_session_token,
)
from app.db.models import User, UserSession
from app.db.models.business import (
    BusinessOffering,
    BusinessProfile,
    BusinessRequirement,
)
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    assert "test" in TEST_DB_URL.lower(), f"Refusing to run tests against non-test DB: {TEST_DB_URL}"
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def sync_engine():
    engine = create_engine(TEST_MIGRATION_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_business_matching_db(sync_engine):
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.business_requirements;")
            conn.exec_driver_sql("DELETE FROM business.business_offerings;")
            conn.exec_driver_sql("DELETE FROM business.business_profiles;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users;")
            conn.commit()

    _clean()
    yield
    _clean()


def create_user_and_token(sync_engine, username: str, email: str) -> Tuple[User, str]:
    from datetime import datetime, timedelta, timezone

    with Session(sync_engine) as session:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password("ValidP@ssw0rd123!"),
            full_name=username.capitalize(),
            is_active=True,
        )
        session.add(user)
        session.flush()

        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token)
        now = datetime.now(timezone.utc)
        sess = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=24),
            last_accessed_at=now,
            ip_address="127.0.0.1",
            user_agent="pytest-agent",
        )
        session.add(sess)
        session.commit()
        session.refresh(user)
        return user, raw_token


from typing import Tuple


def test_parse_query_api_endpoint(client, sync_engine):
    """Test the POST /business/matching/parse-query endpoint."""
    user, token = create_user_and_token(sync_engine, "buyer_nlp", "buyer_nlp@example.com")

    resp = client.post(
        "/converge-api/v1/business/matching/parse-query",
        json={"query": "Need 1000 MT LC3-50 cement in Pune within 45 days"},
        cookies={SESSION_COOKIE_NAME: token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_product_code"] == "CALCINED_CLAY_LC3"
    assert data["matched_grade_code"] == "LC3_50_STANDARD"
    assert data["quantity"] == 1000.0
    assert data["quantity_unit"] == "METRIC_TONNE"
    assert data["destination_city"] == "Pune"
    assert data["target_timeline_days"] == 45
    assert data["inquiry_type"] == "RFQ_PRODUCT"


def test_matching_requires_commercial_opt_in_consent(client, sync_engine):
    """Caller without commercial opt-in consent is strictly forbidden (403)."""
    user, token = create_user_and_token(sync_engine, "no_optin_user", "no_optin@example.com")

    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"query": "Need 500 MT OPC 53 in Mumbai"},
        cookies={SESSION_COOKIE_NAME: token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 403
    assert "opt-in consent" in resp.json()["detail"].lower()


def test_multi_dimensional_matching_ranking_and_run_rate(client, sync_engine):
    """Verify 5-dimensional candidate scoring and capacity run-rate normalization."""
    # 1. Setup Buyer with commercial profile & opt-in
    buyer, buyer_token = create_user_and_token(sync_engine, "sanjana_buyer", "sanjana@infratech.com")
    # 2. Setup Supplier 1 (Deccan Green Cement: LC3-50, 5000 MT/mo capacity, delivers to Pune)
    supp1, _ = create_user_and_token(sync_engine, "maahi_supp", "maahi@deccancement.com")
    # 3. Setup Supplier 2 (Small local supplier: LC3-50, only 300 MT/mo capacity - capacity constrained!)
    supp2, _ = create_user_and_token(sync_engine, "small_supp", "small@cement.com")
    # 4. Setup Supplier 3 (Out of coverage: LC3-50, 10000 MT/mo capacity, but only delivers to Delhi/NCR)
    supp3, _ = create_user_and_token(sync_engine, "delhi_supp", "delhi@cement.com")

    with Session(sync_engine) as session:
        # Buyer profile
        buyer_prof = BusinessProfile(
            user_id=buyer.id,
            is_buyer=True,
            allow_business_matching=True,
            company_name="InfraTech EPC Solutions Ltd",
            hq_city="Mumbai",
        )
        session.add(buyer_prof)

        # Supplier 1 Profile & Offering (Optimal match: 5000 MT/mo > 666 MT run rate, Pune covered, fresh)
        supp1_prof = BusinessProfile(
            user_id=supp1.id,
            is_supplier=True,
            allow_business_matching=True,
            company_name="Deccan Green Cement & Binders Ltd",
            hq_city="Pune",
        )
        session.add(supp1_prof)
        session.flush()

        off1 = BusinessOffering(
            business_profile_id=supp1_prof.id,
            custom_product_title="LC3-50 Low Carbon Cement",
            product_code="CALCINED_CLAY_LC3",
            grade_code="LC3_50_STANDARD",
            declared_monthly_capacity=Decimal("5000"),
            capacity_unit="METRIC_TONNE",
            lead_time_days=7,
            geographic_coverage=["Pune", "Mumbai"],
            offers_test_certificates=True,
            is_public_indicative=True,
            indicative_price_min=Decimal("5200"),
            indicative_price_max=Decimal("5500"),
            pricing_basis="EX_WORKS",
            is_active=True,
        )
        session.add(off1)

        # Supplier 2 Profile & Offering (Capacity constrained: 300 MT/mo < 666 MT run rate)
        supp2_prof = BusinessProfile(
            user_id=supp2.id,
            is_supplier=True,
            allow_business_matching=True,
            company_name="Small Mills Ltd",
            hq_city="Pune",
        )
        session.add(supp2_prof)
        session.flush()

        off2 = BusinessOffering(
            business_profile_id=supp2_prof.id,
            custom_product_title="LC3-50 Cement",
            product_code="CALCINED_CLAY_LC3",
            grade_code="LC3_50_STANDARD",
            declared_monthly_capacity=Decimal("300"),
            capacity_unit="METRIC_TONNE",
            lead_time_days=5,
            geographic_coverage=["Pune"],
            is_active=True,
        )
        session.add(off2)

        # Supplier 3 Profile & Offering (Out of coverage: Pune not covered)
        supp3_prof = BusinessProfile(
            user_id=supp3.id,
            is_supplier=True,
            allow_business_matching=True,
            company_name="Northern Binders Ltd",
            hq_city="Delhi",
        )
        session.add(supp3_prof)
        session.flush()

        off3 = BusinessOffering(
            business_profile_id=supp3_prof.id,
            custom_product_title="LC3-50 Cement",
            product_code="CALCINED_CLAY_LC3",
            grade_code="LC3_50_STANDARD",
            declared_monthly_capacity=Decimal("10000"),
            capacity_unit="METRIC_TONNE",
            lead_time_days=3,
            geographic_coverage=["Delhi", "Noida", "Gurugram"],
            is_active=True,
        )
        session.add(off3)
        session.commit()

    # Buyer searches for 1000 MT LC3 in Pune within 45 days
    # Required Run Rate = 1000 * (30 / 45) = 666.67 MT/month
    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={
            "query": "Need 1000 MT LC3 cement in Pune within 45 days",
        },
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.json()

    candidates = data["candidates"]
    # Supplier 3 must be excluded (Pune out of delivery coverage)
    supp_companies = [c["supplier_company_name"] for c in candidates]
    assert "Northern Binders Ltd" not in supp_companies
    assert "Deccan Green Cement & Binders Ltd" in supp_companies

    # Supplier 1 must rank highest because capacity (5000 MT) easily meets run rate (666.67 MT)
    top_cand = candidates[0]
    assert top_cand["supplier_company_name"] == "Deccan Green Cement & Binders Ltd"
    assert top_cand["score_breakdown"]["product_relevance"] == 1.0  # Exact grade match
    assert top_cand["score_breakdown"]["capacity_feasibility"] == 1.0  # Run rate feasible
    assert top_cand["score_breakdown"]["delivery_feasibility"] == 1.0  # Pune covered & lead time <= 45d
    assert top_cand["composite_score"] >= 85.0
    assert "📜 Mill Certs" in top_cand["confidence_badges"]
    assert "₹5,200 – ₹5,500 / METRIC_TONNE (Ex Works)" in top_cand["indicative_price_display"]

    # If Supplier 2 is present, its capacity_feasibility score must be penalized (< 1.0)
    supp2_cand = next((c for c in candidates if c["supplier_company_name"] == "Small Mills Ltd"), None)
    if supp2_cand:
        assert supp2_cand["score_breakdown"]["capacity_feasibility"] < 1.0
        assert top_cand["composite_score"] > supp2_cand["composite_score"]


def test_incumbent_supplier_exclusion_filter(client, sync_engine):
    """Verify strict exclusion of incumbent suppliers specified in requirement."""
    buyer, buyer_token = create_user_and_token(sync_engine, "excl_buyer", "excl_buyer@example.com")
    supp, _ = create_user_and_token(sync_engine, "incumbent_supp", "incumbent@example.com")

    with Session(sync_engine) as session:
        buyer_prof = BusinessProfile(
            user_id=buyer.id,
            is_buyer=True,
            allow_business_matching=True,
            company_name="Buyer Corp",
        )
        session.add(buyer_prof)
        session.flush()

        supp_prof = BusinessProfile(
            user_id=supp.id,
            is_supplier=True,
            allow_business_matching=True,
            company_name="Incumbent Supplier Corp",
        )
        session.add(supp_prof)
        session.flush()

        # Offering
        off = BusinessOffering(
            business_profile_id=supp_prof.id,
            custom_product_title="OPC 53 Cement",
            product_code="ORDINARY_PORTLAND_CEMENT",
            grade_code="OPC_53_IS_269",
            declared_monthly_capacity=Decimal("10000"),
            capacity_unit="METRIC_TONNE",
            is_active=True,
        )
        session.add(off)

        # Buyer requirement that specifically excludes incumbent supplier!
        req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="Dual Sourcing OPC 53",
            product_code="ORDINARY_PORTLAND_CEMENT",
            grade_code="OPC_53_IS_269",
            required_quantity=Decimal("1000"),
            quantity_unit="METRIC_TONNE",
            excluded_supplier_ids=[str(supp_prof.id)],  # Incumbent excluded!
            is_active=True,
        )
        session.add(req)
        session.commit()
        req_id = req.id

    # Search with requirement_id
    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    candidates = resp.json()["candidates"]
    # Incumbent supplier MUST be excluded completely
    assert len(candidates) == 0


def test_budget_privacy_enforced(client, sync_engine):
    """Verify buyer target budget is strictly hidden from search candidate objects."""
    buyer, buyer_token = create_user_and_token(sync_engine, "priv_buyer", "priv_buyer@example.com")
    supp, _ = create_user_and_token(sync_engine, "pub_supp", "pub_supp@example.com")

    with Session(sync_engine) as session:
        buyer_prof = BusinessProfile(
            user_id=buyer.id,
            is_buyer=True,
            allow_business_matching=True,
        )
        session.add(buyer_prof)
        session.flush()

        supp_prof = BusinessProfile(
            user_id=supp.id,
            is_supplier=True,
            allow_business_matching=True,
            company_name="Public Supplier Ltd",
        )
        session.add(supp_prof)
        session.flush()

        off = BusinessOffering(
            business_profile_id=supp_prof.id,
            custom_product_title="Portland Pozzolana Cement PPC",
            product_code="PORTLAND_POZZOLANA_CEMENT",
            declared_monthly_capacity=Decimal("2000"),
            capacity_unit="METRIC_TONNE",
            is_active=True,
        )
        session.add(off)

        # Buyer requirement with private target budget
        req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="PPC Bulk Sourcing",
            product_code="PORTLAND_POZZOLANA_CEMENT",
            required_quantity=Decimal("500"),
            quantity_unit="METRIC_TONNE",
            target_budget_indication=Decimal("4800"),  # Private budget!
            is_budget_public=False,
            is_active=True,
        )
        session.add(req)
        session.commit()
        req_id = req.id

    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["candidates"]) == 1

    # Candidate object contains zero buyer budget fields
    cand = data["candidates"][0]
    assert "target_budget" not in cand
    assert "budget" not in cand
    assert "target_budget_indication" not in cand



def test_incompatible_service_disqualification_crane_vs_pneumatic_haulage(client, sync_engine):
    """Negative Test: Crane rental alone CANNOT qualify for bulk pneumatic haulage inquiry."""
    buyer, buyer_token = create_user_and_token(sync_engine, "haulage_buyer", "haulage_buyer@test.com")
    crane_supp, _ = create_user_and_token(sync_engine, "crane_vendor", "crane_vendor@test.com")

    with Session(sync_engine) as session:
        buyer_prof = BusinessProfile(
            user_id=buyer.id,
            is_buyer=True,
            allow_business_matching=True,
            company_name="Sanjana Infrastructure Developers",
            hq_city="Pune",
        )
        session.add(buyer_prof)

        vendor_prof = BusinessProfile(
            user_id=crane_supp.id,
            is_vendor=True,
            allow_business_matching=True,
            company_name="Western Logistics Crane Fleet",
            hq_city="Navi Mumbai",
        )
        session.add(vendor_prof)
        session.flush()

        # The incompatible offering: Crane Rental
        crane_offering = BusinessOffering(
            business_profile_id=vendor_prof.id,
            custom_product_title="50-Ton Crawler Crane Rental",
            specifications_text="Mobile Hydraulic Crane Rental with crew",
            declared_monthly_capacity=Decimal("50"),
            capacity_unit="TRUCKLOAD",
            geographic_coverage=["Pune", "Mumbai", "Nashik"],
            lead_time_days=3,
            is_active=True,
        )
        session.add(crane_offering)

        # Buyer requirement specifically for Bulk Pneumatic Haulage
        req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="Bulk Pneumatic Haulage Fleet (Mumbai to Pune)",
            required_quantity=Decimal("25"),
            quantity_unit="TRUCKLOAD",
            delivery_city="Pune",
            target_timeline_days=15,
            is_active=True,
        )
        session.add(req)
        session.commit()
        req_id = req.id

    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    candidates = resp.json()["candidates"]
    # Crane rental MUST NOT qualify for bulk pneumatic haulage!
    assert len(candidates) == 0, f"Expected 0 candidates, but received: {[c['offering_title'] for c in candidates]}"


def test_valid_matches_for_haulage_and_crane_rental_independently(client, sync_engine):
    """Positive Test: Haulage requirement matches haulage offering; Crane requirement matches crane offering."""
    buyer, buyer_token = create_user_and_token(sync_engine, "dual_buyer", "dual_buyer@test.com")
    crane_vendor, _ = create_user_and_token(sync_engine, "crane_co", "crane_co@test.com")
    haulage_vendor, _ = create_user_and_token(sync_engine, "haulage_co", "haulage_co@test.com")

    with Session(sync_engine) as session:
        buyer_prof = BusinessProfile(user_id=buyer.id, is_buyer=True, allow_business_matching=True)
        session.add(buyer_prof)

        c_prof = BusinessProfile(user_id=crane_vendor.id, is_vendor=True, allow_business_matching=True, company_name="Apex Cranes")
        h_prof = BusinessProfile(user_id=haulage_vendor.id, is_vendor=True, allow_business_matching=True, company_name="Express Bulkers")
        session.add_all([c_prof, h_prof])
        session.flush()

        crane_off = BusinessOffering(
            business_profile_id=c_prof.id,
            custom_product_title="50-Ton Crawler Crane Rental",
            declared_monthly_capacity=Decimal("20"),
            capacity_unit="UNITS",
            geographic_coverage=["Pune"],
            is_active=True,
        )
        haulage_off = BusinessOffering(
            business_profile_id=h_prof.id,
            custom_product_title="Bulk Pneumatic Bulker Haulage Fleet",
            declared_monthly_capacity=Decimal("100"),
            capacity_unit="TRUCKLOAD",
            geographic_coverage=["Pune"],
            is_active=True,
        )
        session.add_all([crane_off, haulage_off])

        # Haulage Requirement
        haulage_req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="Bulk Pneumatic Haulage Fleet (Mumbai to Pune)",
            delivery_city="Pune",
            is_active=True,
        )
        # Crane Requirement
        crane_req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="Mobile Hydraulic Crane Rental for Plant Erection",
            delivery_city="Pune",
            is_active=True,
        )
        session.add_all([haulage_req, crane_req])
        session.commit()
        h_req_id = haulage_req.id
        c_req_id = crane_req.id

    # 1. Haulage Search: Only haulage offering matches!
    h_resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(h_req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert h_resp.status_code == 200
    h_cands = h_resp.json()["candidates"]
    assert len(h_cands) == 1
    assert h_cands[0]["offering_title"] == "Bulk Pneumatic Bulker Haulage Fleet"

    # 2. Crane Search: Only crane offering matches!
    c_resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(c_req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert c_resp.status_code == 200
    c_cands = c_resp.json()["candidates"]
    assert len(c_cands) == 1
    assert c_cands[0]["offering_title"] == "50-Ton Crawler Crane Rental"


def test_unrecorded_commitment_and_incompatible_dimensions(client, sync_engine):
    """Verify unrecorded commitment gives 0.0 confidence (never 50%), and incompatible units fail feasibility."""
    buyer, buyer_token = create_user_and_token(sync_engine, "bound_buyer", "bound_buyer@test.com")
    supp, _ = create_user_and_token(sync_engine, "bound_supp", "bound_supp@test.com")

    with Session(sync_engine) as session:
        buyer_prof = BusinessProfile(user_id=buyer.id, is_buyer=True, allow_business_matching=True)
        session.add(buyer_prof)
        supp_prof = BusinessProfile(user_id=supp.id, is_supplier=True, allow_business_matching=True, company_name="Incompat Supp")
        session.add(supp_prof)
        session.flush()

        # Offering with declared capacity in HOURS (time dimension) and UNRECORDED committed volume
        off = BusinessOffering(
            business_profile_id=supp_prof.id,
            custom_product_title="Calcined Clay LC3 Special",
            product_code="CALCINED_CLAY_LC3",
            grade_code="LC3_50_STANDARD",
            declared_monthly_capacity=Decimal("500"),
            capacity_unit="HOURS",  # Incompatible with mass!
            declared_committed_volume=None,  # Unrecorded commitment!
            geographic_coverage=["Pune"],
            is_active=True,
        )
        session.add(off)

        # Requirement with mass dimension (METRIC_TONNE)
        req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="LC3 Sourcing",
            product_code="CALCINED_CLAY_LC3",
            grade_code="LC3_50_STANDARD",
            required_quantity=Decimal("100"),
            quantity_unit="METRIC_TONNE",
            delivery_city="Pune",
            target_timeline_days=30,
            is_active=True,
        )
        session.add(req)
        session.commit()
        req_id = req.id

    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    candidates = resp.json()["candidates"]
    assert len(candidates) == 1
    cand = candidates[0]

    # Incompatible unit dimensions must result in S_cap = 0.0
    assert cand["score_breakdown"]["capacity_feasibility"] == 0.0
    assert any("Incompatible Dimensions" in b for b in cand["confidence_badges"])

    # Unrecorded commitment must result in C_com = 0.0 (strictly 0.0, NOT 0.50)
    assert cand["score_breakdown"]["commitment_confidence"] == 0.0
    assert "⚠️ Uncommitted Allocation Unverified" in cand["confidence_badges"]


def test_cross_category_physical_product_vs_service_disqualification(client, sync_engine):
    """Physical material requirement cannot match service offering, and vice versa."""
    buyer, buyer_token = create_user_and_token(sync_engine, "cat_buyer", "cat_buyer@test.com")
    service_vendor, _ = create_user_and_token(sync_engine, "log_vendor", "log_vendor@test.com")

    with Session(sync_engine) as session:
        buyer_prof = BusinessProfile(user_id=buyer.id, is_buyer=True, allow_business_matching=True)
        session.add(buyer_prof)
        vendor_prof = BusinessProfile(user_id=service_vendor.id, is_vendor=True, allow_business_matching=True)
        session.add(vendor_prof)
        session.flush()

        # Service Offering: Construction Logistics
        log_off = BusinessOffering(
            business_profile_id=vendor_prof.id,
            custom_product_title="Construction Logistics Fleet",
            service_code="CONSTRUCTION_LOGISTICS",
            product_code=None,
            declared_monthly_capacity=Decimal("200"),
            capacity_unit="TRUCKLOAD",
            geographic_coverage=["Pune"],
            is_active=True,
        )
        session.add(log_off)

        # Buyer Requirement for Physical Cement
        cement_req = BusinessRequirement(
            business_profile_id=buyer_prof.id,
            custom_requirement_title="OPC 53 Cement Procurement",
            product_code="ORDINARY_PORTLAND_CEMENT",
            grade_code="OPC_53_IS_269",
            service_code=None,
            delivery_city="Pune",
            is_active=True,
        )
        session.add(cement_req)
        session.commit()
        req_id = cement_req.id

    resp = client.post(
        "/converge-api/v1/business/matching/search",
        json={"requirement_id": str(req_id)},
        cookies={SESSION_COOKIE_NAME: buyer_token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    # Physical product requirement MUST NOT match service offering
    assert len(resp.json()["candidates"]) == 0
