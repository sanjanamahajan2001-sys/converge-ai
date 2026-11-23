"""Business matching and profiles schema, taxonomy, catalog and context snapshots

Revision ID: 016_business_matching_profiles
Revises: 015_organizer_conferences
Create Date: 2026-10-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars for standard alembic_version table).
revision: str = "016_business_matching_profiles"
down_revision: Union[str, None] = "015_organizer_conferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"
OWNER_ROLE = "converge_ai_owner"


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 0. Ensure schema business exists and configure runtime grants
    # -------------------------------------------------------------------------
    op.execute(f"CREATE SCHEMA IF NOT EXISTS business AUTHORIZATION {OWNER_ROLE};")
    op.execute(f"GRANT USAGE ON SCHEMA business TO {RUNTIME_ROLE};")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA business "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA business "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {RUNTIME_ROLE};"
    )

    # -------------------------------------------------------------------------
    # 1. Product & Service Taxonomies
    # -------------------------------------------------------------------------
    op.create_table(
        "product_taxonomies",
        sa.Column("category_code", sa.String(length=80), primary_key=True),
        sa.Column("sector_code", sa.String(length=80), nullable=False),
        sa.Column("canonical_name", sa.String(length=150), nullable=False),
        sa.Column(
            "standard_units",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_product_taxonomies_sector",
        "product_taxonomies",
        ["sector_code"],
        schema="business",
    )

    op.create_table(
        "canonical_products",
        sa.Column("product_code", sa.String(length=80), primary_key=True),
        sa.Column(
            "category_code",
            sa.String(length=80),
            sa.ForeignKey("business.product_taxonomies.category_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("canonical_name", sa.String(length=150), nullable=False),
        sa.Column(
            "substitute_product_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_canonical_products_category",
        "canonical_products",
        ["category_code"],
        schema="business",
    )

    op.create_table(
        "product_grades",
        sa.Column("grade_code", sa.String(length=80), primary_key=True),
        sa.Column(
            "product_code",
            sa.String(length=80),
            sa.ForeignKey("business.canonical_products.product_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("grade_name", sa.String(length=150), nullable=False),
        sa.Column("governing_standard", sa.String(length=100), nullable=True),
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_product_grades_product",
        "product_grades",
        ["product_code"],
        schema="business",
    )

    op.create_table(
        "service_taxonomies",
        sa.Column("service_code", sa.String(length=80), primary_key=True),
        sa.Column("category_code", sa.String(length=80), nullable=False),
        sa.Column("canonical_name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_service_taxonomies_category",
        "service_taxonomies",
        ["category_code"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 2. Business Profiles
    # -------------------------------------------------------------------------
    op.create_table(
        "business_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("is_buyer", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_supplier", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_vendor", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_distributor", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_partner", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("allow_business_matching", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("company_name", sa.String(length=150), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("business_website", sa.String(length=255), nullable=True),
        sa.Column("hq_city", sa.String(length=100), nullable=True),
        sa.Column("hq_country", sa.String(length=100), nullable=True),
        sa.Column("company_bio", sa.Text(), nullable=True),
        sa.Column(
            "distributor_territories",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("warehousing_capacity_sqft", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("retail_dealer_count", sa.Integer(), nullable=True),
        sa.Column(
            "partnership_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "partnership_interests",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(allow_business_matching = FALSE) OR (is_buyer OR is_supplier OR is_vendor OR is_distributor OR is_partner)",
            name="ck_at_least_one_role",
        ),
        sa.CheckConstraint(
            "warehousing_capacity_sqft IS NULL OR warehousing_capacity_sqft >= 0",
            name="ck_warehousing_capacity_positive",
        ),
        sa.CheckConstraint(
            "retail_dealer_count IS NULL OR retail_dealer_count >= 0",
            name="ck_retail_dealer_count_positive",
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_profiles_user_id",
        "business_profiles",
        ["user_id"],
        schema="business",
    )
    op.create_index(
        "ix_business_profiles_matching_status",
        "business_profiles",
        ["allow_business_matching", "is_supplier", "is_buyer", "is_vendor"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 3. Business Offerings (Supplier / Vendor Catalog)
    # -------------------------------------------------------------------------
    op.create_table(
        "business_offerings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "business_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.business_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.String(length=80),
            sa.ForeignKey("business.canonical_products.product_code", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "grade_code",
            sa.String(length=80),
            sa.ForeignKey("business.product_grades.grade_code", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "service_code",
            sa.String(length=80),
            sa.ForeignKey("business.service_taxonomies.service_code", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("custom_product_title", sa.String(length=200), nullable=False),
        sa.Column("specifications_text", sa.Text(), nullable=True),
        sa.Column("declared_monthly_capacity", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("declared_committed_volume", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("capacity_unit", sa.String(length=30), nullable=True),
        sa.Column("minimum_order_quantity", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column(
            "geographic_coverage",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("offers_test_certificates", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "vendor_certifications",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("open_to_distribution", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "target_distribution_regions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("distributor_tier_preferred", sa.String(length=50), nullable=True),
        sa.Column("is_public_indicative", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("indicative_price_min", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("indicative_price_max", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("price_currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("pricing_basis", sa.String(length=30), nullable=True),
        sa.Column("offers_delivered_pricing", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("quote_validity_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("price_last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capacity_last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "declared_monthly_capacity IS NULL OR declared_monthly_capacity >= 0",
            name="ck_declared_monthly_capacity_positive",
        ),
        sa.CheckConstraint(
            "declared_committed_volume IS NULL OR declared_committed_volume >= 0",
            name="ck_declared_committed_volume_positive",
        ),
        sa.CheckConstraint(
            "minimum_order_quantity IS NULL OR minimum_order_quantity > 0",
            name="ck_moq_positive",
        ),
        sa.CheckConstraint(
            "lead_time_days IS NULL OR lead_time_days >= 0",
            name="ck_lead_time_positive",
        ),
        sa.CheckConstraint(
            "indicative_price_min IS NULL OR indicative_price_min > 0",
            name="ck_indicative_price_min_positive",
        ),
        sa.CheckConstraint(
            "indicative_price_max IS NULL OR indicative_price_min IS NULL OR indicative_price_max >= indicative_price_min",
            name="ck_indicative_price_max_ge_min",
        ),
        sa.CheckConstraint(
            "quote_validity_days > 0 AND quote_validity_days <= 365",
            name="ck_quote_validity_range",
        ),
        sa.CheckConstraint(
            "pricing_basis IS NULL OR pricing_basis IN ('EX_WORKS', 'FOR_DELIVERED', 'FOB', 'CIF', 'FAS', 'DAP')",
            name="ck_pricing_basis_valid",
        ),
        sa.CheckConstraint(
            "price_currency IN ('INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD')",
            name="ck_price_currency_valid",
        ),
        sa.CheckConstraint(
            "(declared_committed_volume IS NULL OR declared_monthly_capacity IS NULL OR declared_committed_volume <= declared_monthly_capacity) AND "
            "(minimum_order_quantity IS NULL OR declared_monthly_capacity IS NULL OR minimum_order_quantity <= declared_monthly_capacity)",
            name="ck_offering_capacity_consistency",
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_offerings_profile",
        "business_offerings",
        ["business_profile_id"],
        schema="business",
    )
    op.create_index(
        "ix_business_offerings_product",
        "business_offerings",
        ["product_code"],
        schema="business",
    )
    op.create_index(
        "ix_business_offerings_service",
        "business_offerings",
        ["service_code"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 4. Business Requirements (Buyer / Procurement Needs)
    # -------------------------------------------------------------------------
    op.create_table(
        "business_requirements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "business_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.business_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.String(length=80),
            sa.ForeignKey("business.canonical_products.product_code", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "grade_code",
            sa.String(length=80),
            sa.ForeignKey("business.product_grades.grade_code", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "service_code",
            sa.String(length=80),
            sa.ForeignKey("business.service_taxonomies.service_code", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("required_quantity", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("quantity_unit", sa.String(length=30), nullable=True),
        sa.Column("delivery_city", sa.String(length=100), nullable=True),
        sa.Column("delivery_country", sa.String(length=100), nullable=True),
        sa.Column("target_timeline_days", sa.Integer(), nullable=True),
        sa.Column("target_budget_indication", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("is_budget_public", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("urgency", sa.String(length=30), server_default="PLANNED", nullable=False),
        sa.Column(
            "excluded_supplier_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("allow_substitutes", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "required_certifications",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_feedstock_procurement", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "required_quantity IS NULL OR required_quantity > 0",
            name="ck_required_quantity_positive",
        ),
        sa.CheckConstraint(
            "target_timeline_days IS NULL OR target_timeline_days > 0",
            name="ck_target_timeline_positive",
        ),
        sa.CheckConstraint(
            "target_budget_indication IS NULL OR target_budget_indication > 0",
            name="ck_target_budget_positive",
        ),
        sa.CheckConstraint(
            "urgency IN ('IMMEDIATE', 'PLANNED', 'EXPLORATORY')",
            name="ck_urgency_valid",
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_requirements_profile",
        "business_requirements",
        ["business_profile_id"],
        schema="business",
    )
    op.create_index(
        "ix_business_requirements_product",
        "business_requirements",
        ["product_code"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 5. Connection Context Snapshots & Revisions
    # -------------------------------------------------------------------------
    op.create_table(
        "conversation_business_contexts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.conversations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("inquiry_type", sa.String(length=50), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("product_code", sa.String(length=80), nullable=True),
        sa.Column("grade_code", sa.String(length=80), nullable=True),
        sa.Column("service_code", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("delivery_location", sa.String(length=255), nullable=True),
        sa.Column("timeline_days", sa.Integer(), nullable=True),
        sa.Column("target_price_indication", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("urgency", sa.String(length=30), nullable=True),
        sa.Column("inquiry_notes", sa.Text(), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "inquiry_type IN ('RFQ_PRODUCT', 'RFI_SERVICE', 'SUPPLIER_PROSPECTING', "
            "'VENDOR_PITCH', 'ALTERNATIVE_SOURCING', 'SOURCING_PARTNERSHIP', "
            "'DISTRIBUTION_EXPANSION', 'DISTRIBUTOR_APPLICATION', 'EXPLORATORY_COLLABORATION')",
            name="ck_inquiry_type_valid",
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_contexts_conversation",
        "conversation_business_contexts",
        ["conversation_id"],
        schema="business",
    )

    op.create_table(
        "context_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "context_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.conversation_business_contexts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "revised_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "change_diff",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="business",
    )
    op.create_index(
        "ix_business_revisions_context",
        "context_revisions",
        ["context_id"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 6. Seed Standard Industrial Taxonomy Data
    # -------------------------------------------------------------------------
    op.execute("""
        INSERT INTO business.product_taxonomies (category_code, sector_code, canonical_name, standard_units)
        VALUES 
            ('BINDERS_AND_CEMENTITIOUS', 'HEAVY_CONSTRUCTION_MATERIALS', 'Binders & Cementitious Materials', '["METRIC_TONNE", "BAG_50KG", "KILOGRAM", "QUINTAL"]'::jsonb),
            ('STRUCTURAL_METALS', 'HEAVY_CONSTRUCTION_MATERIALS', 'Structural Metals & Rebar', '["METRIC_TONNE", "KILOGRAM"]'::jsonb),
            ('AGGREGATES_AND_SAND', 'HEAVY_CONSTRUCTION_MATERIALS', 'Aggregates & M-Sand', '["METRIC_TONNE", "CUBIC_METER"]'::jsonb)
        ON CONFLICT (category_code) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO business.canonical_products (product_code, category_code, canonical_name, substitute_product_codes)
        VALUES 
            ('PORTLAND_POZZOLANA_CEMENT', 'BINDERS_AND_CEMENTITIOUS', 'Portland Pozzolana Cement (PPC)', '["CALCINED_CLAY_LC3", "PORTLAND_SLAG_CEMENT"]'::jsonb),
            ('ORDINARY_PORTLAND_CEMENT', 'BINDERS_AND_CEMENTITIOUS', 'Ordinary Portland Cement (OPC)', '["PORTLAND_POZZOLANA_CEMENT"]'::jsonb),
            ('CALCINED_CLAY_LC3', 'BINDERS_AND_CEMENTITIOUS', 'Limestone Calcined Clay Cement (LC3)', '["PORTLAND_POZZOLANA_CEMENT"]'::jsonb),
            ('CEMENT_CLINKER', 'BINDERS_AND_CEMENTITIOUS', 'Cement Clinker Intermediate', '[]'::jsonb)
        ON CONFLICT (product_code) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO business.product_grades (grade_code, product_code, grade_name, governing_standard, aliases)
        VALUES 
            ('OPC_53_IS_269', 'ORDINARY_PORTLAND_CEMENT', 'OPC 53 Grade', 'IS 269:2015', '["53 grade", "opc53", "53-grade"]'::jsonb),
            ('OPC_43_IS_269', 'ORDINARY_PORTLAND_CEMENT', 'OPC 43 Grade', 'IS 269:2015', '["43 grade", "opc43"]'::jsonb),
            ('LC3_50_STANDARD', 'CALCINED_CLAY_LC3', 'LC3-50 Low Carbon Blend', 'IS 18189:2023', '["lc3", "lc3-50", "low carbon cement"]'::jsonb)
        ON CONFLICT (grade_code) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO business.service_taxonomies (service_code, category_code, canonical_name, description)
        VALUES 
            ('CONSTRUCTION_LOGISTICS', 'LOGISTICS', 'Bulk Construction Material Transport & Fleet', 'Heavy bulk tanker and flatbed transportation for industrial construction materials.'),
            ('MATERIAL_TESTING_NABL', 'TESTING', 'Third-Party NABL Accredited Material Laboratory Testing', 'Compressive strength, setting time, and chemical analysis certification for cement and concrete.'),
            ('EQUIPMENT_RENTAL', 'PLANT_SERVICES', 'Heavy Construction Equipment & Crane Rental', 'Mobile crane, concrete batching plant, and earthmoving machinery leasing with certified crew.'),
            ('PLANT_MAINTENANCE', 'INDUSTRIAL_MAINTENANCE', 'Preventive Plant & Kiln Maintenance Services', 'Industrial machinery refractory lining, conveyor maintenance, and mechanical inspection services.')
        ON CONFLICT (service_code) DO NOTHING;
    """)

    # -------------------------------------------------------------------------
    # 7. Explicit runtime DML grants to converge_ai_app
    # -------------------------------------------------------------------------
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA business TO {RUNTIME_ROLE};"
    )


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # Reverse dependency drops of newly created tables
    # -------------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS business.context_revisions;")
    op.execute("DROP TABLE IF EXISTS business.conversation_business_contexts;")
    op.execute("DROP TABLE IF EXISTS business.business_requirements;")
    op.execute("DROP TABLE IF EXISTS business.business_offerings;")
    op.execute("DROP TABLE IF EXISTS business.business_profiles;")
    op.execute("DROP TABLE IF EXISTS business.service_taxonomies;")
    op.execute("DROP TABLE IF EXISTS business.product_grades;")
    op.execute("DROP TABLE IF EXISTS business.canonical_products;")
    op.execute("DROP TABLE IF EXISTS business.product_taxonomies;")

    # -------------------------------------------------------------------------
    # Drop schema ONLY IF empty (preserves schema if foreign/unowned tables exist)
    # -------------------------------------------------------------------------
    op.execute("""
        DO $$
        DECLARE
            remaining_tables INT;
        BEGIN
            SELECT count(*) INTO remaining_tables 
            FROM information_schema.tables 
            WHERE table_schema = 'business';
            
            IF remaining_tables = 0 THEN
                EXECUTE 'DROP SCHEMA IF EXISTS business;';
            ELSE
                RAISE NOTICE 'Schema business contains % unowned objects; preserving schema.', remaining_tables;
            END IF;
        END $$;
    """)
