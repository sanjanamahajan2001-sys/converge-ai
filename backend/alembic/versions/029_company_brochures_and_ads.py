"""Create schema brochures, company digital brochures, pages, and sponsored ad tables (Brochure Phase 1)

Revision ID: 029_company_brochures_ads
Revises: 028_quote_requests_email
Create Date: 2026-11-09 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "029_company_brochures_ads"
down_revision: Union[str, None] = "028_quote_requests_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"
OWNER_ROLE = "converge_ai_owner"


def upgrade() -> None:
    bind = op.get_bind()

    # -------------------------------------------------------------------------
    # 0. Ensure schema brochures exists and configure runtime grants
    # -------------------------------------------------------------------------
    op.execute(f"CREATE SCHEMA IF NOT EXISTS brochures AUTHORIZATION {OWNER_ROLE};")
    op.execute(f"GRANT USAGE ON SCHEMA brochures TO {RUNTIME_ROLE};")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA brochures "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA brochures "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {RUNTIME_ROLE};"
    )

    # -------------------------------------------------------------------------
    # 1. Enums in schema brochures
    # -------------------------------------------------------------------------
    ad_placement_type_enum = postgresql.ENUM(
        "BANNER_TOP",
        "PRE_ROLL",
        name="ad_placement_type",
        schema="brochures",
        create_type=False,
    )
    ad_placement_type_enum.create(bind, checkfirst=True)

    ad_event_type_enum = postgresql.ENUM(
        "IMPRESSION",
        "CLICK",
        name="ad_event_type",
        schema="brochures",
        create_type=False,
    )
    ad_event_type_enum.create(bind, checkfirst=True)

    # -------------------------------------------------------------------------
    # 2. brochures.company_brochures
    # -------------------------------------------------------------------------
    op.create_table(
        "company_brochures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "business_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.business_profiles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("company_name", sa.String(150), nullable=False),
        sa.Column(
            "title",
            sa.String(200),
            nullable=False,
            server_default=sa.text("'Company Catalog & Brochure'"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="brochures",
    )

    # -------------------------------------------------------------------------
    # 3. brochures.brochure_pages
    # -------------------------------------------------------------------------
    op.create_table(
        "brochure_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "brochure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brochures.company_brochures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(150), nullable=True),
        sa.Column("aspect_ratio", sa.Numeric(5, 3), nullable=False, server_default=sa.text("0.707")),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("brochure_id", "page_number", name="uq_brochure_page_number"),
        schema="brochures",
    )

    # -------------------------------------------------------------------------
    # 4. brochures.brochure_ads
    # -------------------------------------------------------------------------
    op.create_table(
        "brochure_ads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sponsor_name", sa.String(150), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("placement_type", ad_placement_type_enum, nullable=False),
        sa.Column("creative_image_url", sa.Text(), nullable=False),
        sa.Column("destination_url", sa.Text(), nullable=False),
        sa.Column("tagline", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="brochures",
    )

    # -------------------------------------------------------------------------
    # 5. brochures.brochure_ad_assignments
    # -------------------------------------------------------------------------
    op.create_table(
        "brochure_ad_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brochures.brochure_ads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "brochure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brochures.company_brochures.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("ad_id", "brochure_id", name="uq_ad_brochure_assignment"),
        schema="brochures",
    )

    # -------------------------------------------------------------------------
    # 6. brochures.brochure_ad_events
    # -------------------------------------------------------------------------
    op.create_table(
        "brochure_ad_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brochures.brochure_ads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "brochure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brochures.company_brochures.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("event_type", ad_event_type_enum, nullable=False),
        sa.Column("viewer_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="brochures",
    )

    # Explicit grant on newly created tables to runtime application role
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA brochures TO {RUNTIME_ROLE};")


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_table("brochure_ad_events", schema="brochures")
    op.drop_table("brochure_ad_assignments", schema="brochures")
    op.drop_table("brochure_ads", schema="brochures")
    op.drop_table("brochure_pages", schema="brochures")
    op.drop_table("company_brochures", schema="brochures")

    ad_event_type_enum = postgresql.ENUM(
        "IMPRESSION",
        "CLICK",
        name="ad_event_type",
        schema="brochures",
    )
    ad_event_type_enum.drop(bind, checkfirst=True)

    ad_placement_type_enum = postgresql.ENUM(
        "BANNER_TOP",
        "PRE_ROLL",
        name="ad_placement_type",
        schema="brochures",
    )
    ad_placement_type_enum.drop(bind, checkfirst=True)

    op.execute(
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA brochures "
        f"REVOKE USAGE, SELECT ON SEQUENCES FROM {RUNTIME_ROLE};"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA brochures "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {RUNTIME_ROLE};"
    )
    op.execute(f"REVOKE USAGE ON SCHEMA brochures FROM {RUNTIME_ROLE};")
    op.execute("DROP SCHEMA IF EXISTS brochures CASCADE;")
