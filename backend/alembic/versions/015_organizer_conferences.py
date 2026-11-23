"""Organizer profiles, conference lifecycle, format, location and review logs

Revision ID: 015_organizer_and_conference_lifecycle
Revises: 014_admin_role
Create Date: 2026-10-28 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015_organizer_conferences"
down_revision: Union[str, None] = "014_admin_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Create table core.organizer_profiles
    # -------------------------------------------------------------------------
    op.create_table(
        "organizer_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organizer_type", sa.String(length=50), server_default="COMPANY", nullable=False),
        sa.Column("representative_name", sa.String(length=120), nullable=False),
        sa.Column("organization_name", sa.String(length=150), nullable=True),
        sa.Column("designation", sa.String(length=100), nullable=True),
        sa.Column("professional_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=50), nullable=False),
        sa.Column("website_url", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=255), nullable=True),
        sa.Column("address_line1", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state_province", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("focus_areas", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("verification_status", sa.String(length=30), server_default="VERIFIED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_core_organizer_user_id"),
        schema="core",
    )
    op.create_index(
        "ix_core_organizer_user_id",
        "organizer_profiles",
        ["user_id"],
        unique=True,
        schema="core",
    )
    op.create_index(
        "ix_core_organizer_verification",
        "organizer_profiles",
        ["verification_status"],
        unique=False,
        schema="core",
    )

    # -------------------------------------------------------------------------
    # 2. Add columns to agenda.conferences
    # -------------------------------------------------------------------------
    op.add_column("conferences", sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=True), schema="agenda")
    op.create_foreign_key(
        "fk_conferences_organizer_id",
        "conferences",
        "users",
        ["organizer_id"],
        ["id"],
        source_schema="agenda",
        referent_schema="core",
        ondelete="SET NULL",
    )
    op.add_column("conferences", sa.Column("summary", sa.String(length=300), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("category", sa.String(length=100), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("format", sa.String(length=20), server_default="IN_PERSON", nullable=False), schema="agenda")
    op.add_column("conferences", sa.Column("start_time", sa.Time(), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("end_time", sa.Time(), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("registration_opens_at", sa.DateTime(timezone=True), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("registration_closes_at", sa.DateTime(timezone=True), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("capacity", sa.Integer(), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("target_audience", sa.String(length=255), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("website_url", sa.String(length=255), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("banner_url", sa.String(length=255), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("meeting_url", sa.String(length=255), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("formatted_address", sa.String(length=255), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("location_lat", sa.Float(), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("location_lng", sa.Float(), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("place_id", sa.String(length=100), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("city", sa.String(length=100), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("country", sa.String(length=100), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("status", sa.String(length=30), server_default="PUBLISHED", nullable=False), schema="agenda")
    op.add_column("conferences", sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True), schema="agenda")
    op.create_foreign_key(
        "fk_conferences_reviewed_by",
        "conferences",
        "users",
        ["reviewed_by"],
        ["id"],
        source_schema="agenda",
        referent_schema="core",
        ondelete="SET NULL",
    )
    op.add_column("conferences", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("review_feedback", sa.Text(), nullable=True), schema="agenda")
    op.add_column("conferences", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True), schema="agenda")

    op.create_index("idx_conferences_organizer_id", "conferences", ["organizer_id"], unique=False, schema="agenda")
    op.create_index("idx_conferences_status", "conferences", ["status"], unique=False, schema="agenda")
    op.create_index("idx_conferences_dates", "conferences", ["start_date", "end_date"], unique=False, schema="agenda")

    # -------------------------------------------------------------------------
    # 3. Create table agenda.conference_review_logs
    # -------------------------------------------------------------------------
    op.create_table(
        "conference_review_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("conference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_status", sa.String(length=30), nullable=False),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conference_id"], ["agenda.conferences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["core.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="agenda",
    )
    op.create_index(
        "idx_review_logs_conference_created",
        "conference_review_logs",
        ["conference_id", sa.text("created_at DESC")],
        unique=False,
        schema="agenda",
    )


def downgrade() -> None:
    # 1. Drop conference_review_logs
    op.drop_index("idx_review_logs_conference_created", table_name="conference_review_logs", schema="agenda")
    op.drop_table("conference_review_logs", schema="agenda")

    # 2. Drop columns from agenda.conferences
    op.drop_index("idx_conferences_dates", table_name="conferences", schema="agenda")
    op.drop_index("idx_conferences_status", table_name="conferences", schema="agenda")
    op.drop_index("idx_conferences_organizer_id", table_name="conferences", schema="agenda")

    op.drop_constraint("fk_conferences_reviewed_by", "conferences", schema="agenda", type_="foreignkey")
    op.drop_constraint("fk_conferences_organizer_id", "conferences", schema="agenda", type_="foreignkey")

    for col in [
        "published_at",
        "review_feedback",
        "reviewed_at",
        "reviewed_by",
        "status",
        "country",
        "city",
        "place_id",
        "location_lng",
        "location_lat",
        "formatted_address",
        "meeting_url",
        "banner_url",
        "website_url",
        "target_audience",
        "capacity",
        "registration_closes_at",
        "registration_opens_at",
        "end_time",
        "start_time",
        "format",
        "category",
        "summary",
        "organizer_id",
    ]:
        op.drop_column("conferences", col, schema="agenda")

    # 3. Drop core.organizer_profiles
    op.drop_index("ix_core_organizer_verification", table_name="organizer_profiles", schema="core")
    op.drop_index("ix_core_organizer_user_id", table_name="organizer_profiles", schema="core")
    op.drop_table("organizer_profiles", schema="core")
