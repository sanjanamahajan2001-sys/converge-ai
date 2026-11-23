"""Create core identity and audit tables: core.users and core.audit_logs

Revision ID: 002_core_identity
Revises: 001_initial_schemas
Create Date: 2026-10-23 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_core_identity"
down_revision: Union[str, None] = "001_initial_schemas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create core.users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("company_name", sa.String(length=150), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("phone_number", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "username ~* '^[a-zA-Z0-9_-]{3,50}$'",
            name="ck_users_username_format",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        schema="core",
    )

    # 2. Case-insensitive unique indexes on username and email
    op.create_index(
        "uq_users_username_lower",
        "users",
        [sa.text("lower(username)")],
        unique=True,
        schema="core",
    )
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        schema="core",
    )

    # 3. Create core.audit_logs table (GAP-10)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=False),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column(
            "event_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core.users.id"],
            name="fk_audit_logs_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        schema="core",
    )

    # 4. Audit log indexes
    op.create_index(
        "idx_audit_created",
        "audit_logs",
        [sa.text("created_at DESC")],
        unique=False,
        schema="core",
    )
    op.create_index(
        "idx_audit_action",
        "audit_logs",
        ["action_type"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    # Reverse order teardown
    op.drop_index("idx_audit_action", table_name="audit_logs", schema="core")
    op.drop_index("idx_audit_created", table_name="audit_logs", schema="core")
    op.drop_table("audit_logs", schema="core")

    op.drop_index("uq_users_email_lower", table_name="users", schema="core")
    op.drop_index("uq_users_username_lower", table_name="users", schema="core")
    op.drop_table("users", schema="core")
