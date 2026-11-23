"""Create login rate limiting table: core.login_rate_limits

Revision ID: 003_login_rate_limits
Revises: 002_core_identity
Create Date: 2026-10-23 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_login_rate_limits"
down_revision: Union[str, None] = "002_core_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. Create core.login_rate_limits table
    op.create_table(
        "login_rate_limits",
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "first_failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("ip_hash", name="pk_login_rate_limits"),
        schema="core",
    )

    # 2. Index on locked_until for quick lock check/cleanup
    op.create_index(
        "idx_rate_limits_locked_until",
        "login_rate_limits",
        ["locked_until"],
        unique=False,
        schema="core",
    )

    # 3. Explicit permissions grant for runtime role
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE core.login_rate_limits TO {RUNTIME_ROLE};"
    )


def downgrade() -> None:
    op.drop_index("idx_rate_limits_locked_until", table_name="login_rate_limits", schema="core")
    op.drop_table("login_rate_limits", schema="core")
