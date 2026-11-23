"""Create tables, enums, constraints, and indexes for Quote Requests and Email Dispatch (Quote Subphase 2)

Revision ID: 028_quote_requests_email
Revises: 027_agent_dm_and_contact_policy
Create Date: 2026-11-06 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "028_quote_requests_email"
down_revision: Union[str, None] = "027_agent_dm_and_contact_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    bind = op.get_bind()

    # -------------------------------------------------------------------------
    # 1. Enums for Quotes in schema 'business'
    # -------------------------------------------------------------------------
    quote_request_status_enum = postgresql.ENUM(
        "OPEN",
        "MATCHED",
        "CLOSED",
        "CANCELLED",
        name="quote_request_status",
        schema="business",
        create_type=False,
    )
    quote_request_status_enum.create(bind, checkfirst=True)

    quote_urgency_enum = postgresql.ENUM(
        "IMMEDIATE",
        "PLANNED",
        "EXPLORATORY",
        name="quote_urgency",
        schema="business",
        create_type=False,
    )
    quote_urgency_enum.create(bind, checkfirst=True)

    vendor_match_status_enum = postgresql.ENUM(
        "PENDING_REVIEW",
        "QUOTED_VIA_EMAIL",
        "DECLINED",
        "EXPIRED",
        name="vendor_match_status",
        schema="business",
        create_type=False,
    )
    vendor_match_status_enum.create(bind, checkfirst=True)

    email_delivery_status_enum = postgresql.ENUM(
        "QUEUED",
        "SENT",
        "FAILED",
        name="email_delivery_status",
        schema="business",
        create_type=False,
    )
    email_delivery_status_enum.create(bind, checkfirst=True)

    # -------------------------------------------------------------------------
    # 2. Table: business.quote_requests
    # -------------------------------------------------------------------------
    op.create_table(
        "quote_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_agent_persona",
            sa.String(length=100),
            server_default="Procurement AI Agent",
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "product_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "grade_code",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "service_code",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=4),
            nullable=True,
        ),
        sa.Column(
            "quantity_unit",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "delivery_location",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "timeline_days",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "target_price_indication",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.Column(
            "currency",
            sa.String(length=10),
            server_default="INR",
            nullable=False,
        ),
        sa.Column(
            "is_budget_public",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "urgency",
            quote_urgency_enum,
            server_default="PLANNED",
            nullable=False,
        ),
        sa.Column(
            "technical_specifications",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "inquiry_notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "status",
            quote_request_status_enum,
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_price_indication IS NULL OR target_price_indication > 0",
            name="ck_quote_request_price_positive",
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_quote_request_quantity_positive",
        ),
        schema="business",
    )

    op.create_index(
        "ix_quote_requests_customer_id",
        "quote_requests",
        ["customer_id"],
        schema="business",
    )
    op.create_index(
        "ix_quote_requests_status",
        "quote_requests",
        ["status"],
        schema="business",
    )
    op.create_index(
        "ix_quote_requests_created_at",
        "quote_requests",
        ["created_at"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 3. Table: business.quote_vendor_matches
    # -------------------------------------------------------------------------
    op.create_table(
        "quote_vendor_matches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "quote_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.quote_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "match_score",
            sa.Numeric(precision=5, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "match_reasons",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            vendor_match_status_enum,
            server_default="PENDING_REVIEW",
            nullable=False,
        ),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "quote_request_id",
            "vendor_id",
            name="uq_quote_vendor_match",
        ),
        schema="business",
    )

    op.create_index(
        "ix_quote_vendor_matches_vendor_id",
        "quote_vendor_matches",
        ["vendor_id"],
        schema="business",
    )
    op.create_index(
        "ix_quote_vendor_matches_status",
        "quote_vendor_matches",
        ["status"],
        schema="business",
    )
    op.create_index(
        "ix_quote_vendor_matches_request",
        "quote_vendor_matches",
        ["quote_request_id"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 4. Table: business.quote_email_dispatches
    # -------------------------------------------------------------------------
    op.create_table(
        "quote_email_dispatches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "quote_vendor_match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.quote_vendor_matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "quote_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.quote_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sender_email",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "recipient_email",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "quote_reference_number",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            "total_value",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=10),
            server_default="INR",
            nullable=False,
        ),
        sa.Column(
            "incoterm",
            sa.String(length=30),
            server_default="EXW",
            nullable=False,
        ),
        sa.Column(
            "lead_time_days",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "validity_days",
            sa.Integer(),
            server_default="15",
            nullable=False,
        ),
        sa.Column(
            "payment_terms",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "commercial_notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "email_subject",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "email_body_html",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "delivery_status",
            email_delivery_status_enum,
            server_default="SENT",
            nullable=False,
        ),
        sa.Column(
            "external_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "unit_price > 0 AND total_value > 0",
            name="ck_quote_dispatch_positive_values",
        ),
        schema="business",
    )

    op.create_index(
        "ix_quote_email_dispatches_ref_no",
        "quote_email_dispatches",
        ["quote_reference_number"],
        schema="business",
    )
    op.create_index(
        "ix_quote_email_dispatches_match_id",
        "quote_email_dispatches",
        ["quote_vendor_match_id"],
        schema="business",
    )
    op.create_index(
        "ix_quote_email_dispatches_vendor_id",
        "quote_email_dispatches",
        ["vendor_id"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 5. Grants for Least-Privilege Role converge_ai_app
    # -------------------------------------------------------------------------
    op.execute(f"GRANT USAGE ON TYPE business.quote_request_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.quote_urgency TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.vendor_match_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.email_delivery_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.quote_requests TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.quote_vendor_matches TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.quote_email_dispatches TO {RUNTIME_ROLE};")


def downgrade() -> None:
    # Reverse drops in dependency order
    op.drop_table("quote_email_dispatches", schema="business")
    op.drop_table("quote_vendor_matches", schema="business")
    op.drop_table("quote_requests", schema="business")

    sa.Enum(name="email_delivery_status", schema="business").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="vendor_match_status", schema="business").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="quote_urgency", schema="business").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="quote_request_status", schema="business").drop(op.get_bind(), checkfirst=True)
