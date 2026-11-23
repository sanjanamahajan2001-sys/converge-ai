"""Integration tests for Business Profile, Dynamic Roles, Offerings & Anti-Staleness APIs."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models import User, UserSession
from app.db.models.business import BusinessOffering, BusinessProfile, BusinessRequirement
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
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
def cleanup_test_db(sync_engine):
    def _clean():
        with sync_engine.connect() as conn:
            conn.exec_driver_sql("DELETE FROM business.business_offerings;")
            conn.exec_driver_sql("DELETE FROM business.business_requirements;")
            conn.exec_driver_sql("DELETE FROM business.business_profiles;")
            conn.exec_driver_sql("DELETE FROM core.user_sessions;")
            conn.exec_driver_sql("DELETE FROM core.users;")
            conn.commit()
    _clean()
    yield
    _clean()


@pytest.fixture
def create_test_user(sync_engine):
    def _create(username="test_biz_user1"):
        with Session(sync_engine) as session:
            user = User(
                id=uuid.uuid4(),
                email=f"{username}@example.com",
                username=username,
                password_hash=hash_password("ValidP@ssw0rd123!"),
                full_name=f"Full Name of {username}",
                company_name="Industrial Corp",
                job_title="Procurement Officer",
                is_active=True,
            )
            session.add(user)
            session.flush()

            raw_token = generate_session_token()
            token_hash = hash_session_token(raw_token)
            now = datetime.now(timezone.utc)
            user_session = UserSession(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=now + timedelta(hours=24),
                last_accessed_at=now,
            )
            session.add(user_session)
            session.commit()
            session.refresh(user)
            return user, raw_token
    return _create


CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


def test_business_profile_unauthenticated(client):
    """Verify 401 when unauthenticated."""
    resp = client.get("/converge-api/v1/business/profile/me")
    assert resp.status_code == 401


def test_business_profile_not_found_initially(client, create_test_user):
    """Verify 404 when user has not yet initialized a business profile."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.get("/converge-api/v1/business/profile/me")
    assert resp.status_code == 404


def test_business_profile_create_and_dynamic_roles(client, create_test_user):
    """Verify creating a business profile and toggling dynamic multi-roles."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    # 1. Create Buyer profile
    payload = {
        "is_buyer": True,
        "is_supplier": False,
        "is_vendor": False,
        "is_distributor": False,
        "is_partner": False,
        "allow_business_matching": True,
        "company_name": "Apex Builders",
        "industry": "Construction",
        "hq_city": "Pune",
        "hq_country": "India",
    }
    resp = client.put("/converge-api/v1/business/profile/me", json=payload, headers=CSRF_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_buyer"] is True
    assert data["is_supplier"] is False
    assert data["company_name"] == "Apex Builders"

    # 2. Dynamic Role Evolution: User expands business and enables Supplier role too
    payload["is_supplier"] = True
    resp2 = client.put("/converge-api/v1/business/profile/me", json=payload, headers=CSRF_HEADERS)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_buyer"] is True
    assert data2["is_supplier"] is True


def test_offering_creation_and_role_deactivation_lifecycle(client, create_test_user):
    """Verify catalog offerings, soft-deactivation when role pauses, and re-activation."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    # Set up Supplier profile
    client.put("/converge-api/v1/business/profile/me", json={
        "is_supplier": True,
        "allow_business_matching": True,
        "company_name": "Ultra Cement Works",
    }, headers=CSRF_HEADERS)

    # Create offering
    off_payload = {
        "custom_product_title": "OPC 53 Bulk Tankers",
        "product_code": "ORDINARY_PORTLAND_CEMENT",
        "grade_code": "OPC_53_IS_269",
        "declared_monthly_capacity": 5000,
        "declared_committed_volume": 1000,
        "capacity_unit": "METRIC_TONNE",
        "minimum_order_quantity": 200,
        "lead_time_days": 7,
        "geographic_coverage": ["Pune", "Mumbai", "Nashik"],
        "offers_test_certificates": True,
        "is_public_indicative": True,
        "indicative_price_min": 5200,
        "indicative_price_max": 5600,
        "price_currency": "INR",
        "pricing_basis": "EX_WORKS",
    }
    create_resp = client.post("/converge-api/v1/business/offerings", json=off_payload, headers=CSRF_HEADERS)
    assert create_resp.status_code == 201
    off_data = create_resp.json()
    off_id = off_data["id"]
    assert off_data["is_active"] is True
    assert off_data["is_capacity_stale"] is False
    assert off_data["reconfirmation_required"] is False

    # Deactivate supplier role
    client.put("/converge-api/v1/business/profile/me", json={
        "is_buyer": True,
        "is_supplier": False,
        "allow_business_matching": True,
    }, headers=CSRF_HEADERS)

    # Offering should be soft-deactivated
    get_resp = client.get("/converge-api/v1/business/profile/me")
    assert get_resp.status_code == 200
    offerings = get_resp.json()["offerings"]
    assert len(offerings) == 1
    assert offerings[0]["is_active"] is False

    # Re-activate supplier role
    client.put("/converge-api/v1/business/profile/me", json={
        "is_buyer": True,
        "is_supplier": True,
        "allow_business_matching": True,
    }, headers=CSRF_HEADERS)
    get_resp2 = client.get("/converge-api/v1/business/profile/me")
    assert get_resp2.json()["offerings"][0]["is_active"] is True


def test_offering_reconfirmation_endpoint(client, create_test_user, sync_engine):
    """Verify 1-click re-confirmation endpoint resets freshness timestamps."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    client.put("/converge-api/v1/business/profile/me", json={
        "is_supplier": True,
        "allow_business_matching": True,
    }, headers=CSRF_HEADERS)

    create_resp = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "PPC Bags",
        "product_code": "PORTLAND_POZZOLANA_CEMENT",
        "declared_monthly_capacity": 3000,
        "capacity_unit": "METRIC_TONNE",
    }, headers=CSRF_HEADERS)
    off_id = create_resp.json()["id"]

    # Manually backdate capacity_last_confirmed_at to 100 days ago to simulate stale data
    stale_date = datetime.now(timezone.utc) - timedelta(days=100)
    with sync_engine.connect() as conn:
        conn.exec_driver_sql(
            f"UPDATE business.business_offerings SET capacity_last_confirmed_at = '{stale_date.isoformat()}' "
            f"WHERE id = '{off_id}';"
        )
        conn.commit()

    # Check profile - offering should be stale & reconfirmation required
    prof_resp = client.get("/converge-api/v1/business/profile/me")
    off = prof_resp.json()["offerings"][0]
    assert off["is_capacity_stale"] is True
    assert off["reconfirmation_required"] is True

    # Call re-confirmation endpoint
    confirm_resp = client.post(f"/converge-api/v1/business/offerings/{off_id}/confirm", headers=CSRF_HEADERS)
    assert confirm_resp.status_code == 200
    confirmed_off = confirm_resp.json()
    assert confirmed_off["is_capacity_stale"] is False
    assert confirmed_off["reconfirmation_required"] is False


def test_idor_protection_on_offerings(client, create_test_user):
    """Verify that User B cannot edit or delete User A's catalog offering."""
    user_a, token_a = create_test_user("test_biz_usera")
    user_b, token_b = create_test_user("test_biz_userb")

    # User A creates offering
    client.cookies.set(SESSION_COOKIE_NAME, token_a)
    client.put("/converge-api/v1/business/profile/me", json={"is_supplier": True, "allow_business_matching": True}, headers=CSRF_HEADERS)
    create_resp = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "Private Catalog Item",
        "declared_monthly_capacity": 100,
    }, headers=CSRF_HEADERS)
    off_id = create_resp.json()["id"]

    # User B initializes own profile
    client.cookies.set(SESSION_COOKIE_NAME, token_b)
    client.put("/converge-api/v1/business/profile/me", json={"is_supplier": True, "allow_business_matching": True}, headers=CSRF_HEADERS)

    # User B attempts to update User A's offering -> 404 IDOR rejection
    attack_resp = client.put(f"/converge-api/v1/business/offerings/{off_id}", json={
        "custom_product_title": "Hacked Title"
    }, headers=CSRF_HEADERS)
    assert attack_resp.status_code == 404

    # User B attempts to delete User A's offering -> 404 IDOR rejection
    del_resp = client.delete(f"/converge-api/v1/business/offerings/{off_id}", headers=CSRF_HEADERS)
    assert del_resp.status_code == 404


def test_requirement_creation_and_budget_privacy(client, create_test_user):
    """Verify buyer requirement creation and target budget handling."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    client.put("/converge-api/v1/business/profile/me", json={
        "is_buyer": True,
        "allow_business_matching": True,
    }, headers=CSRF_HEADERS)

    req_payload = {
        "product_code": "ORDINARY_PORTLAND_CEMENT",
        "grade_code": "OPC_53_IS_269",
        "required_quantity": 1000,
        "quantity_unit": "METRIC_TONNE",
        "delivery_city": "Pune",
        "target_timeline_days": 45,
        "target_budget_indication": 5300,
        "is_budget_public": False,
        "urgency": "PLANNED",
    }
    create_resp = client.post("/converge-api/v1/business/requirements", json=req_payload, headers=CSRF_HEADERS)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert float(data["required_quantity"]) == 1000.0
    assert data["delivery_city"] == "Pune"
    assert float(data["target_budget_indication"]) == 5300.0
    assert data["is_budget_public"] is False


def test_taxonomy_discovery_endpoints(client):
    """Verify taxonomy endpoints return seeded product and service hierarchies."""
    resp_prod = client.get("/converge-api/v1/business/taxonomies/products")
    assert resp_prod.status_code == 200
    data_prod = resp_prod.json()
    assert len(data_prod) >= 2
    categories = [p["category_code"] for p in data_prod]
    assert "BINDERS_AND_CEMENTITIOUS" in categories

    resp_svc = client.get("/converge-api/v1/business/taxonomies/services")
    assert resp_svc.status_code == 200
    data_svc = resp_svc.json()
    assert len(data_svc) >= 4
    service_codes = [s["service_code"] for s in data_svc]
    assert "CONSTRUCTION_LOGISTICS" in service_codes
    assert "MATERIAL_TESTING_NABL" in service_codes


def test_custom_product_and_service_offerings(client, create_test_user):
    """Verify suppliers and vendors can publish custom offerings with or without taxonomy references."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    # Enable both Supplier and Vendor roles
    client.put("/converge-api/v1/business/profile/me", json={
        "is_supplier": True,
        "is_vendor": True,
        "allow_business_matching": True,
        "company_name": "Apex Engineering & Logistics",
    }, headers=CSRF_HEADERS)

    # 1. Custom physical product offering (no canonical product code)
    custom_prod_resp = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "Fe 550D High-Strength TMT Rebars 16mm",
        "specifications_text": "IS 1786:2008 certified, primary steel billet route, 12m standard lengths",
        "declared_monthly_capacity": 1500,
        "capacity_unit": "METRIC_TONNE",
        "minimum_order_quantity": 40,
        "lead_time_days": 5,
        "geographic_coverage": ["Gujarat", "Maharashtra"],
        "offers_test_certificates": True,
    }, headers=CSRF_HEADERS)
    assert custom_prod_resp.status_code == 201
    prod_data = custom_prod_resp.json()
    assert prod_data["custom_product_title"] == "Fe 550D High-Strength TMT Rebars 16mm"
    assert prod_data["product_code"] is None
    assert float(prod_data["declared_monthly_capacity"]) == 1500.0

    # 2. Service offering with service taxonomy reference and custom transport capacity unit
    custom_srv_resp = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "Bulk Pneumatic Bulker Haulage (35-Ton)",
        "service_code": "CONSTRUCTION_LOGISTICS",
        "specifications_text": "Dedicated pneumatic fleet for dry fly ash and bulk cement transport",
        "declared_monthly_capacity": 120,
        "capacity_unit": "TRUCKLOAD",
        "lead_time_days": 2,
        "geographic_coverage": ["Western Maharashtra", "Goa"],
    }, headers=CSRF_HEADERS)
    assert custom_srv_resp.status_code == 201
    srv_data = custom_srv_resp.json()
    assert srv_data["custom_product_title"] == "Bulk Pneumatic Bulker Haulage (35-Ton)"
    assert srv_data["service_code"] == "CONSTRUCTION_LOGISTICS"
    assert srv_data["capacity_unit"] == "TRUCKLOAD"
    assert float(srv_data["declared_monthly_capacity"]) == 120.0


def test_buyer_requirement_dynamic_title_and_service_procurement(client, create_test_user):
    """Verify buyer can specify arbitrary custom requirements and service procurements."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    client.put("/converge-api/v1/business/profile/me", json={
        "is_buyer": True,
        "allow_business_matching": True,
    }, headers=CSRF_HEADERS)

    # 1. Custom requirement with explicit title
    req_resp = client.post("/converge-api/v1/business/requirements", json={
        "custom_requirement_title": "500 kVA Silent Containerized Diesel Generator Rental",
        "required_quantity": 2,
        "quantity_unit": "UNIT",
        "delivery_city": "Navi Mumbai",
        "target_timeline_days": 14,
        "urgency": "IMMEDIATE",
        "notes": "Includes backup operator and periodic maintenance SLA",
    }, headers=CSRF_HEADERS)
    assert req_resp.status_code == 201
    req_data = req_resp.json()
    assert req_data["custom_requirement_title"] == "500 kVA Silent Containerized Diesel Generator Rental"
    assert req_data["product_code"] is None
    assert float(req_data["required_quantity"]) == 2.0
    req_id = req_data["id"]

    # 2. Update requirement and verify persistence
    upd_resp = client.put(f"/converge-api/v1/business/requirements/{req_id}", json={
        "custom_requirement_title": "750 kVA Silent Diesel Generator Rental",
        "required_quantity": 3,
    }, headers=CSRF_HEADERS)
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["custom_requirement_title"] == "750 kVA Silent Diesel Generator Rental"
    assert float(upd_data["required_quantity"]) == 3.0

    # 3. Requirement with canonical product code auto-populates title if title omitted
    canon_resp = client.post("/converge-api/v1/business/requirements", json={
        "product_code": "PORTLAND_POZZOLANA_CEMENT",
        "required_quantity": 500,
        "quantity_unit": "METRIC_TONNE",
    }, headers=CSRF_HEADERS)
    assert canon_resp.status_code == 201
    assert "Portland Pozzolana Cement" in canon_resp.json()["custom_requirement_title"]


def test_rejection_of_invalid_references_and_units(client, create_test_user):
    """Verify rejection of non-existent canonical codes, invalid units, and empty requirement titles."""
    user, token = create_test_user()
    client.cookies.set(SESSION_COOKIE_NAME, token)

    client.put("/converge-api/v1/business/profile/me", json={
        "is_buyer": True,
        "is_supplier": True,
        "allow_business_matching": True,
    }, headers=CSRF_HEADERS)

    # 1. Non-existent product code in offering
    bad_prod_off = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "Fake Product",
        "product_code": "NON_EXISTENT_PRODUCT_CODE",
    }, headers=CSRF_HEADERS)
    assert bad_prod_off.status_code == 400
    assert "Unrecognized canonical product code" in bad_prod_off.json()["detail"]

    # 2. Non-existent service code in offering
    bad_srv_off = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "Fake Service",
        "service_code": "NON_EXISTENT_SERVICE_CODE",
    }, headers=CSRF_HEADERS)
    assert bad_srv_off.status_code == 400
    assert "Unrecognized service code" in bad_srv_off.json()["detail"]

    # 3. Invalid capacity unit
    bad_unit_off = client.post("/converge-api/v1/business/offerings", json={
        "custom_product_title": "Test Offering",
        "capacity_unit": "INVALID_ALIEN_UNIT",
    }, headers=CSRF_HEADERS)
    assert bad_unit_off.status_code == 400
    assert "Unsupported or unrecognized capacity unit" in bad_unit_off.json()["detail"]

    # 4. Invalid quantity unit in requirement
    bad_unit_req = client.post("/converge-api/v1/business/requirements", json={
        "custom_requirement_title": "Valid Title",
        "quantity_unit": "INVALID_MAGIC_UNIT",
    }, headers=CSRF_HEADERS)
    assert bad_unit_req.status_code == 400
    assert "Unsupported or unrecognized quantity unit" in bad_unit_req.json()["detail"]

    # 5. Missing title AND missing canonical references in requirement
    empty_req = client.post("/converge-api/v1/business/requirements", json={
        "required_quantity": 100,
    }, headers=CSRF_HEADERS)
    assert empty_req.status_code == 400
    assert "A custom requirement title or a valid product/service selection is required" in empty_req.json()["detail"]

