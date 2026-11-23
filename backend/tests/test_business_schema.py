"""Tests for business schema creation, constraints, and taxonomy seed data."""
import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import DatabaseManager

settings = get_settings()


@pytest.fixture
async def db_session():
    """Async database session fixture for schema tests."""
    manager = DatabaseManager(settings)
    manager.initialize()
    async with manager.session_factory() as session:
        yield session
    await manager.close()


@pytest.mark.asyncio
async def test_business_schema_tables_exist(db_session):
    """Verify that all 9 tables exist in schema business."""
    res = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'business' ORDER BY table_name;"
        )
    )
    tables = [r[0] for r in res.fetchall()]
    expected = [
        "business_offerings",
        "business_profiles",
        "business_requirements",
        "canonical_products",
        "context_revisions",
        "conversation_business_contexts",
        "product_grades",
        "product_taxonomies",
        "service_taxonomies",
    ]
    for exp in expected:
        assert exp in tables, f"Expected table '{exp}' in schema 'business', found: {tables}"


@pytest.mark.asyncio
async def test_seeded_taxonomies_present(db_session):
    """Verify core product and service taxonomies are correctly seeded."""
    res_tax = await db_session.execute(
        text("SELECT category_code, canonical_name FROM business.product_taxonomies ORDER BY category_code;")
    )
    categories = {r[0]: r[1] for r in res_tax.fetchall()}
    assert "BINDERS_AND_CEMENTITIOUS" in categories
    assert "STRUCTURAL_METALS" in categories

    res_prod = await db_session.execute(
        text("SELECT product_code, canonical_name FROM business.canonical_products ORDER BY product_code;")
    )
    products = {r[0]: r[1] for r in res_prod.fetchall()}
    assert "PORTLAND_POZZOLANA_CEMENT" in products
    assert "ORDINARY_PORTLAND_CEMENT" in products
    assert "CALCINED_CLAY_LC3" in products

    res_grades = await db_session.execute(
        text("SELECT grade_code, grade_name FROM business.product_grades ORDER BY grade_code;")
    )
    grades = {r[0]: r[1] for r in res_grades.fetchall()}
    assert "OPC_53_IS_269" in grades
    assert "LC3_50_STANDARD" in grades

    res_svc = await db_session.execute(
        text("SELECT service_code, canonical_name FROM business.service_taxonomies ORDER BY service_code;")
    )
    services = {r[0]: r[1] for r in res_svc.fetchall()}
    assert "CONSTRUCTION_LOGISTICS" in services
    assert "MATERIAL_TESTING_NABL" in services
    assert "EQUIPMENT_RENTAL" in services
    assert "PLANT_MAINTENANCE" in services
