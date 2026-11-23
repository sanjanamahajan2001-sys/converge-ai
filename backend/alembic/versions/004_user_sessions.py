"""Create user sessions table: core.user_sessions (GAP-05)

Revision ID: 004_user_sessions
Revises: 003_login_rate_limits
Create Date: 2026-10-23 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_user_sessions"
down_revision: Union[str, None] = "003_login_rate_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. Create core.user_sessions table
    op.create_table(
        "user_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core.users.id"],
            name="fk_user_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        schema="core",
    )

    # 2. Indexes on user_sessions
    op.create_index(
        "idx_sessions_token_hash",
        "user_sessions",
        ["token_hash"],
        unique=True,
        schema="core",
    )
    op.create_index(
        "idx_sessions_user_id",
        "user_sessions",
        ["user_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "idx_sessions_expires_at",
        "user_sessions",
        ["expires_at"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "idx_sessions_revoked_at",
        "user_sessions",
        ["revoked_at"],
        unique=False,
        schema="core",
    )

    # 3. Explicit permissions grant for runtime role
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE core.user_sessions TO {RUNTIME_ROLE};"
    )


def downgrade() -> None:
    op.drop_index("idx_sessions_revoked_at", table_name="user_sessions", schema="core")
    op.drop_index("idx_sessions_expires_at", table_name="user_sessions", schema="core")
    op.drop_index("idx_sessions_user_id", table_name="user_sessions", schema="core")
    op.drop_index("idx_sessions_token_hash", table_name="user_sessions", schema="core")
    op.drop_table("user_sessions", schema="core")
