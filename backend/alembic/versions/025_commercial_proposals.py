"""Create tables, enums, constraints, and indexes for Commercial Proposals & Dual-Sided Approval (Phase 7 - Subphase 2)

Revision ID: 025_commercial_proposals
Revises: 024_live_state_amenities
Create Date: 2026-11-04 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "025_commercial_proposals"
down_revision: Union[str, None] = "024_live_state_amenities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    bind = op.get_bind()

    # -------------------------------------------------------------------------
    # 1. Enums for Commercial Proposals in schema 'business'
    # -------------------------------------------------------------------------
    proposal_status_enum = postgresql.ENUM(
        "DRAFT",
        "PENDING_REVIEW",
        "MUTUALLY_APPROVED",
        "REJECTED",
        "REVISED",
        "WITHDRAWN",
        "EXPIRED",
        name="proposal_status",
        schema="business",
        create_type=False,
    )
    proposal_status_enum.create(bind, checkfirst=True)

    proposal_role_enum = postgresql.ENUM(
        "BUYER",
        "SUPPLIER",
        "VENDOR",
        "DISTRIBUTOR",
        "PARTNER",
        name="proposal_commercial_role",
        schema="business",
        create_type=False,
    )
    proposal_role_enum.create(bind, checkfirst=True)

    proposal_type_enum = postgresql.ENUM(
        "SUPPLY_CONTRACT",
        "PROCUREMENT_ORDER",
        "DISTRIBUTION_AGREEMENT",
        "SERVICE_MOU",
        "STRATEGIC_PARTNERSHIP",
        name="proposal_type",
        schema="business",
        create_type=False,
    )
    proposal_type_enum.create(bind, checkfirst=True)

    proposal_approval_action_enum = postgresql.ENUM(
        "APPROVED",
        "REJECTED",
        "WITHDRAWN",
        name="proposal_approval_action",
        schema="business",
        create_type=False,
    )
    proposal_approval_action_enum.create(bind, checkfirst=True)

    # -------------------------------------------------------------------------
    # 2. Table: business.proposals
    # -------------------------------------------------------------------------
    op.create_table(
        "proposals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "proposer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "proposer_role",
            proposal_role_enum,
            nullable=False,
        ),
        sa.Column(
            "recipient_role",
            proposal_role_enum,
            nullable=False,
        ),
        sa.Column(
            "proposal_type",
            proposal_type_enum,
            server_default="SUPPLY_CONTRACT",
            nullable=False,
        ),
        sa.Column(
            "status",
            proposal_status_enum,
            server_default="PENDING_REVIEW",
            nullable=False,
        ),
        sa.Column(
            "current_revision_number",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "concluded_at",
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "proposer_id != recipient_id",
            name="ck_proposals_distinct_parties",
        ),
        sa.CheckConstraint(
            "current_revision_number >= 1",
            name="ck_proposals_min_revision",
        ),
        schema="business",
    )

    op.create_index(
        "ix_proposals_proposer",
        "proposals",
        ["proposer_id"],
        schema="business",
    )
    op.create_index(
        "ix_proposals_recipient",
        "proposals",
        ["recipient_id"],
        schema="business",
    )
    op.create_index(
        "ix_proposals_conversation",
        "proposals",
        ["conversation_id"],
        schema="business",
    )
    op.create_index(
        "ix_proposals_status",
        "proposals",
        ["status"],
        schema="business",
    )
    op.create_index(
        "ix_proposals_created_at",
        "proposals",
        ["created_at"],
        schema="business",
    )
    op.create_index(
        "uq_active_proposal_pair",
        "proposals",
        ["proposer_id", "recipient_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('DRAFT', 'PENDING_REVIEW', 'REVISED')"),
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 3. Table: business.proposal_revisions
    # -------------------------------------------------------------------------
    op.create_table(
        "proposal_revisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "proposal_type",
            proposal_type_enum,
            nullable=False,
        ),
        sa.Column(
            "product_name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.String(length=60),
            nullable=True,
        ),
        sa.Column(
            "grade_code",
            sa.String(length=60),
            nullable=True,
        ),
        sa.Column(
            "service_code",
            sa.String(length=60),
            nullable=True,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=4),
            nullable=False,
        ),
        sa.Column(
            "unit",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "unit_price",
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
            "total_value",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.Column(
            "payment_terms",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "delivery_location",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "incoterm",
            sa.String(length=20),
            server_default="EXW",
            nullable=True,
        ),
        sa.Column(
            "delivery_timeline_days",
            sa.Integer(),
            server_default="30",
            nullable=False,
        ),
        sa.Column(
            "governing_standards",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "special_conditions",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "revision_summary",
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "revision_number",
            name="uq_proposal_revision_number",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_rev_min_revision_number",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_rev_quantity_positive",
        ),
        sa.CheckConstraint(
            "delivery_timeline_days >= 1 AND delivery_timeline_days <= 730",
            name="ck_rev_delivery_timeline_range",
        ),
        schema="business",
    )

    op.create_index(
        "ix_proposal_revisions_proposal",
        "proposal_revisions",
        ["proposal_id"],
        schema="business",
    )
    op.create_index(
        "ix_proposal_revisions_author",
        "proposal_revisions",
        ["author_id"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 4. Table: business.proposal_approvals
    # -------------------------------------------------------------------------
    op.create_table(
        "proposal_approvals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.proposal_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "action",
            proposal_approval_action_enum,
            nullable=False,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "revision_id",
            "user_id",
            "action",
            name="uq_proposal_approval_decision",
        ),
        schema="business",
    )

    op.create_index(
        "ix_proposal_approvals_proposal",
        "proposal_approvals",
        ["proposal_id"],
        schema="business",
    )
    op.create_index(
        "ix_proposal_approvals_revision",
        "proposal_approvals",
        ["revision_id"],
        schema="business",
    )
    op.create_index(
        "ix_proposal_approvals_user",
        "proposal_approvals",
        ["user_id"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 5. Table: business.proposal_contact_disclosures
    # -------------------------------------------------------------------------
    op.create_table(
        "proposal_contact_disclosures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business.proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "disclosed_to_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "disclosed_credentials",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "disclosed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "user_id",
            "disclosed_to_user_id",
            name="uq_proposal_contact_disclosure_pair",
        ),
        schema="business",
    )

    op.create_index(
        "ix_contact_disclosures_proposal",
        "proposal_contact_disclosures",
        ["proposal_id"],
        schema="business",
    )
    op.create_index(
        "ix_contact_disclosures_user",
        "proposal_contact_disclosures",
        ["user_id"],
        schema="business",
    )
    op.create_index(
        "ix_contact_disclosures_recipient",
        "proposal_contact_disclosures",
        ["disclosed_to_user_id"],
        schema="business",
    )

    # -------------------------------------------------------------------------
    # 6. Runtime Grants for least-privilege role converge_ai_app
    # -------------------------------------------------------------------------
    op.execute(f"GRANT USAGE ON SCHEMA business TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.proposal_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.proposal_commercial_role TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.proposal_type TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE business.proposal_approval_action TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.proposals TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.proposal_revisions TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.proposal_approvals TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON business.proposal_contact_disclosures TO {RUNTIME_ROLE};")


def downgrade() -> None:
    # Reverse drops in dependency order
    op.drop_table("proposal_contact_disclosures", schema="business")
    op.drop_table("proposal_approvals", schema="business")
    op.drop_table("proposal_revisions", schema="business")
    op.drop_table("proposals", schema="business")

    sa.Enum(name="proposal_approval_action", schema="business").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="proposal_type", schema="business").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="proposal_commercial_role", schema="business").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="proposal_status", schema="business").drop(op.get_bind(), checkfirst=True)
