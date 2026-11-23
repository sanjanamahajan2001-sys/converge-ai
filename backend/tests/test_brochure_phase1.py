"""Unit and integration tests for Company Digital Brochures & Asset Pipeline (Brochure Phase 1)."""
import io
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.core.session import (
    SESSION_COOKIE_NAME,
    generate_session_token,
    hash_session_token,
)
from app.db.models.brochure import (
    AdEventType,
    AdPlacementType,
    BrochureAd,
    BrochureAdAssignment,
    BrochurePage,
    CompanyBrochure,
)
from app.db.models.business import BusinessProfile
from app.db.models.session import UserSession
from app.db.models.user import User
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture(scope="module")
def app_instance():
    assert "test" in TEST_DB_URL.lower(), f"SAFETY GUARD: Non-test DB: {TEST_DB_URL}"
    test_settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL=TEST_DB_URL,
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="TestAdminSecret123!",
    )
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance, headers=CSRF_HEADERS) as c:
        yield c


@pytest.fixture(scope="module")
def sync_engine():
    sync_url = TEST_MIGRATION_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


def create_test_user(
    sync_engine,
    username: str,
    email: str,
    company: str,
    is_admin: bool = False,
) -> Tuple[User, str]:
    with SASession(sync_engine, expire_on_commit=False) as session:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hash_password("BrochureTestPass123!"),
            full_name=f"{company} Delegate",
            company_name=company,
            job_title="VP Marketing",
            is_active=True,
            is_admin=is_admin,
        )
        session.add(user)
        session.flush()

        bp = BusinessProfile(
            user_id=user.id,
            company_name=company,
            is_supplier=True,
            allow_business_matching=True,
        )
        session.add(bp)
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
        return user, raw_token


def generate_test_image_bytes(width=800, height=1200, color="blue") -> bytes:
    """Generate in-memory JPEG bytes for upload testing."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_get_or_create_my_brochure(client, sync_engine):
    """Verify authenticated user gets auto-provisioned company brochure."""
    unique_suffix = uuid.uuid4().hex[:6]
    user, token = create_test_user(
        sync_engine,
        f"brochure_user_{unique_suffix}",
        f"user_{unique_suffix}@materials.com",
        f"Materials Corp {unique_suffix}",
    )

    res = client.get(
        "/converge-api/v1/brochures/my-brochure",
        cookies={SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["company_name"] == f"Materials Corp {unique_suffix}"
    assert data["total_pages"] == 0
    assert data["is_published"] is True
    assert "slug" in data


def test_update_brochure_metadata(client, sync_engine):
    """Verify updating title, description and slug."""
    unique_suffix = uuid.uuid4().hex[:6]
    user, token = create_test_user(
        sync_engine,
        f"updater_{unique_suffix}",
        f"updater_{unique_suffix}@corp.com",
        f"Apex Corp {unique_suffix}",
    )

    update_payload = {
        "title": "Apex Corp 2026 Sustainable Product Catalog",
        "description": "Comprehensive portfolio of green cement and decarbonized clinker.",
        "slug": f"apex-catalog-{unique_suffix}",
    }
    res = client.put(
        "/converge-api/v1/brochures/my-brochure",
        json=update_payload,
        cookies={SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Apex Corp 2026 Sustainable Product Catalog"
    assert data["slug"] == f"apex-catalog-{unique_suffix}"


def test_upload_and_reorder_brochure_pages(client, sync_engine):
    """Verify uploading multiple pages, dimension calculation, and reordering."""
    unique_suffix = uuid.uuid4().hex[:6]
    user, token = create_test_user(
        sync_engine,
        f"uploader_{unique_suffix}",
        f"uploader_{unique_suffix}@test.com",
        f"Publishing Test {unique_suffix}",
    )
    cookies = {SESSION_COOKIE_NAME: token}

    # 1. Upload Page 1
    img1 = generate_test_image_bytes(800, 1200, "red")
    res1 = client.post(
        "/converge-api/v1/brochures/my-brochure/upload-page",
        files={"file": ("cover.jpg", img1, "image/jpeg")},
        data={"title": "Front Cover"},
        cookies=cookies,
    )
    assert res1.status_code == 201
    page1_data = res1.json()
    assert page1_data["page_number"] == 1
    assert page1_data["width"] == 800
    assert page1_data["height"] == 1200
    assert "thumbnail_url" in page1_data
    page1_id = page1_data["id"]

    # 2. Upload Page 2
    img2 = generate_test_image_bytes(800, 1200, "green")
    res2 = client.post(
        "/converge-api/v1/brochures/my-brochure/upload-page",
        files={"file": ("specs.jpg", img2, "image/jpeg")},
        data={"title": "Technical Specs"},
        cookies=cookies,
    )
    assert res2.status_code == 201
    page2_data = res2.json()
    assert page2_data["page_number"] == 2
    page2_id = page2_data["id"]

    # 3. Check brochure detail contains 2 pages
    detail_res = client.get("/converge-api/v1/brochures/my-brochure", cookies=cookies)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["total_pages"] == 2

    # 4. Reorder: swap Page 2 to Page 1
    reorder_res = client.post(
        "/converge-api/v1/brochures/my-brochure/reorder",
        json={"page_ids": [page2_id, page1_id]},
        cookies=cookies,
    )
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()
    assert reordered[0]["id"] == page2_id
    assert reordered[0]["page_number"] == 1
    assert reordered[1]["id"] == page1_id
    assert reordered[1]["page_number"] == 2

    # 5. Delete page 1 (which is page2_id)
    del_res = client.delete(f"/converge-api/v1/brochures/my-brochure/pages/{page2_id}", cookies=cookies)
    assert del_res.status_code == 200

    # 6. Verify remaining page re-sequenced to 1
    after_del = client.get("/converge-api/v1/brochures/my-brochure", cookies=cookies).json()
    assert after_del["total_pages"] == 1
    assert after_del["pages"][0]["id"] == page1_id
    assert after_del["pages"][0]["page_number"] == 1


def test_public_flipbook_and_ad_resolution(client, sync_engine):
    """Verify public flipbook payload resolves top banner and pre-roll ads."""
    unique_suffix = uuid.uuid4().hex[:6]
    user, token = create_test_user(
        sync_engine,
        f"public_user_{unique_suffix}",
        f"pub_{unique_suffix}@view.com",
        f"Global Cement {unique_suffix}",
    )
    cookies = {SESSION_COOKIE_NAME: token}

    # Upload a page so brochure has content
    img = generate_test_image_bytes(800, 1131, "navy")
    client.post(
        "/converge-api/v1/brochures/my-brochure/upload-page",
        files={"file": ("page1.jpg", img, "image/jpeg")},
        cookies=cookies,
    )
    brochure_data = client.get("/converge-api/v1/brochures/my-brochure", cookies=cookies).json()
    brochure_id = uuid.UUID(brochure_data["id"])
    slug = brochure_data["slug"]

    # Provision sponsored ads directly in test DB
    with SASession(sync_engine) as session:
        banner_ad = BrochureAd(
            sponsor_name="CleanTech Infra",
            title="Official Decarbonization Partner",
            placement_type=AdPlacementType.BANNER_TOP,
            creative_image_url="/converge-api/v1/uploads/ads/cleantech_banner.jpg",
            destination_url="https://cleantech.example.com",
            tagline="Accelerate Net-Zero Cement Production",
            is_active=True,
        )
        pre_roll_ad = BrochureAd(
            sponsor_name="Global Summit Title Sponsor",
            title="Welcome to Converge 2026",
            placement_type=AdPlacementType.PRE_ROLL,
            creative_image_url="/converge-api/v1/uploads/ads/summit_preroll.jpg",
            destination_url="https://summit.example.com",
            is_active=True,
        )
        session.add_all([banner_ad, pre_roll_ad])
        session.flush()

        assign1 = BrochureAdAssignment(ad_id=banner_ad.id, brochure_id=brochure_id, priority=20)
        assign2 = BrochureAdAssignment(ad_id=pre_roll_ad.id, brochure_id=None, priority=10)
        session.add_all([assign1, assign2])
        session.commit()
        banner_ad_id = banner_ad.id

    # Unauthenticated public fetch (no session cookies)
    pub_res = client.get(f"/converge-api/v1/brochures/public/{slug}")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["company_name"] == f"Global Cement {unique_suffix}"
    assert pub_data["total_pages"] == 1
    assert pub_data["top_banner_ad"]["sponsor_name"] == "CleanTech Infra"
    assert pub_data["pre_roll_ad"]["sponsor_name"] == "Global Summit Title Sponsor"

    # Test ad telemetry tracking
    track_res = client.post(
        f"/converge-api/v1/brochures/ads/{banner_ad_id}/track?brochure_id={brochure_id}",
        json={"event_type": "IMPRESSION"},
    )
    assert track_res.status_code == 200
    assert track_res.json()["success"] is True

    # Test Phase 6: Public Directory Discovery
    dir_res = client.get("/converge-api/v1/brochures/directory")
    assert dir_res.status_code == 200
    dir_items = dir_res.json()
    assert isinstance(dir_items, list)
    matching = [b for b in dir_items if b["slug"] == slug]
    assert len(matching) == 1
    assert matching[0]["company_name"] == f"Global Cement {unique_suffix}"
    assert matching[0]["total_pages"] == 1
    assert matching[0]["cover_image_url"] is not None

    # Test Directory Search filter
    search_res = client.get(f"/converge-api/v1/brochures/directory?search={unique_suffix}")
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1


def test_brochure_page_read_analytics_and_admin_overview(client, sync_engine):
    """Verify page-read telemetry, time-series buckets, owner analytics, and admin multi-magazine view."""
    unique_suffix = uuid.uuid4().hex[:6]
    user, token = create_test_user(
        sync_engine,
        username=f"analytics_owner_{unique_suffix}",
        email=f"analytics_{unique_suffix}@converge.test",
        company=f"Apex Green Industries {unique_suffix}",
    )
    cookies = {SESSION_COOKIE_NAME: token}

    # Upload 3 pages to create a 3-page magazine
    for idx in range(1, 4):
        img_bytes = generate_test_image_bytes(800, 1200, color=(20 * idx, 100, 180))
        up_res = client.post(
            "/converge-api/v1/brochures/my-brochure/upload-page",
            cookies=cookies,
            files={"file": (f"page_{idx}.jpg", img_bytes, "image/jpeg")},
            data={"title": f"Section {idx}"},
        )
        assert up_res.status_code == 201

    brochure_res = client.get("/converge-api/v1/brochures/my-brochure", cookies=cookies)
    assert brochure_res.status_code == 200
    slug = brochure_res.json()["slug"]

    # Record a public magazine open + two reader sessions flipping across pages
    open_res = client.get(f"/converge-api/v1/brochures/public/{slug}")
    assert open_res.status_code == 200

    r1 = client.post(
        f"/converge-api/v1/brochures/public/{slug}/page-read",
        json={"page_numbers": [1], "session_key": "sess-alpha", "view_mode": "single"},
    )
    assert r1.status_code == 200
    assert r1.json()["recorded_pages"] == [1]

    r2 = client.post(
        f"/converge-api/v1/brochures/public/{slug}/page-read",
        json={"page_numbers": [2, 3], "session_key": "sess-alpha", "view_mode": "spread"},
    )
    assert r2.status_code == 200
    assert r2.json()["recorded_pages"] == [2, 3]

    r3 = client.post(
        f"/converge-api/v1/brochures/public/{slug}/page-read",
        json={"page_numbers": [2], "session_key": "sess-beta", "view_mode": "single"},
    )
    assert r3.status_code == 200
    assert r3.json()["recorded_pages"] == [2]

    # Verify owner analytics for 24h and 7d periods
    owner_analytics_res = client.get(
        "/converge-api/v1/brochures/my-brochure/analytics?period=24h",
        cookies=cookies,
    )
    assert owner_analytics_res.status_code == 200
    owner_data = owner_analytics_res.json()
    assert owner_data["period"] == "24h"
    assert owner_data["total_views_all_time"] >= 1
    assert owner_data["period_views"] >= 1
    assert owner_data["period_page_reads"] == 4
    assert owner_data["unique_sessions"] == 2
    assert owner_data["top_page_number"] == 2
    assert len(owner_data["time_series"]) == 24
    assert len(owner_data["pages"]) == 3

    page_map = {p["page_number"]: p for p in owner_data["pages"]}
    assert page_map[1]["read_count"] == 1
    assert page_map[2]["read_count"] == 2
    assert page_map[2]["unique_readers"] == 2
    assert page_map[3]["read_count"] == 1

    # Non-admin must be rejected from admin analytics
    forbidden_res = client.get("/converge-api/v1/admin/brochures/analytics", cookies=cookies)
    assert forbidden_res.status_code in (401, 403)

    # Create admin session and verify multi-magazine analytics overview
    _, admin_token = create_test_user(
        sync_engine,
        username=f"analytics_admin_{unique_suffix}",
        email=f"admin_{unique_suffix}@converge.test",
        company="Converge Admin",
        is_admin=True,
    )

    admin_res = client.get(
        "/converge-api/v1/admin/brochures/analytics?period=7d",
        cookies={SESSION_COOKIE_NAME: admin_token},
    )
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["period"] == "7d"
    assert len(admin_data["combined_time_series"]) == 7
    assert admin_data["total_magazines"] >= 1
    matching_mags = [m for m in admin_data["magazines"] if m["slug"] == slug]
    assert len(matching_mags) == 1
    assert matching_mags[0]["period_page_reads"] == 4
    assert matching_mags[0]["top_page_number"] == 2

