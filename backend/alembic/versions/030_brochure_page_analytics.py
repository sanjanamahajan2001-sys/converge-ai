"""Add brochures.brochure_page_read_events for time-series magazine and page read analytics.

Revision ID: 030_brochure_page_analytics
Revises: 029_company_brochures_ads
Create Date: 2026-11-12 12:25:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "030_brochure_page_analytics"
down_revision: Union[str, None] = "029_company_brochures_ads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    op.create_table(
        "brochure_page_read_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("brochure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column(
            "event_kind",
            sa.String(length=16),
            server_default=sa.text("'PAGE_READ'"),
            nullable=False,
        ),
        sa.Column("session_key", sa.String(length=64), nullable=True),
        sa.Column("view_mode", sa.String(length=20), nullable=True),
        sa.Column("viewer_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["brochure_id"],
            ["brochures.company_brochures.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["brochures.brochure_pages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="brochures",
    )

    op.create_index(
        op.f("ix_brochures_brochure_page_read_events_brochure_id"),
        "brochure_page_read_events",
        ["brochure_id"],
        unique=False,
        schema="brochures",
    )
    op.create_index(
        op.f("ix_brochures_brochure_page_read_events_page_id"),
        "brochure_page_read_events",
        ["page_id"],
        unique=False,
        schema="brochures",
    )
    op.create_index(
        op.f("ix_brochures_brochure_page_read_events_session_key"),
        "brochure_page_read_events",
        ["session_key"],
        unique=False,
        schema="brochures",
    )
    op.create_index(
        "ix_brochure_page_read_events_brochure_created",
        "brochure_page_read_events",
        ["brochure_id", "created_at"],
        unique=False,
        schema="brochures",
    )
    op.create_index(
        "ix_brochure_page_read_events_brochure_kind_page",
        "brochure_page_read_events",
        ["brochure_id", "event_kind", "page_number"],
        unique=False,
        schema="brochures",
    )
    op.create_index(
        "ix_brochure_page_read_events_created_at",
        "brochure_page_read_events",
        ["created_at"],
        unique=False,
        schema="brochures",
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA brochures TO {RUNTIME_ROLE};")


def downgrade() -> None:
    op.drop_index("ix_brochure_page_read_events_created_at", table_name="brochure_page_read_events", schema="brochures")
    op.drop_index("ix_brochure_page_read_events_brochure_kind_page", table_name="brochure_page_read_events", schema="brochures")
    op.drop_index("ix_brochure_page_read_events_brochure_created", table_name="brochure_page_read_events", schema="brochures")
    op.drop_index(op.f("ix_brochures_brochure_page_read_events_session_key"), table_name="brochure_page_read_events", schema="brochures")
    op.drop_index(op.f("ix_brochures_brochure_page_read_events_page_id"), table_name="brochure_page_read_events", schema="brochures")
    op.drop_index(op.f("ix_brochures_brochure_page_read_events_brochure_id"), table_name="brochure_page_read_events", schema="brochures")
    op.drop_table("brochure_page_read_events", schema="brochures")
