"""Add is_admin column to users table for administrative access control

Revision ID: 014_admin_role
Revises: 013_profile_location
Create Date: 2026-10-28 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "014_admin_role"
down_revision: Union[str, None] = "013_profile_location"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_admin boolean column with default false
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="core",
    )
    # 2. Create index on is_admin for administrative queries
    op.create_index(
        "ix_core_users_is_admin",
        "users",
        ["is_admin"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    op.drop_index("ix_core_users_is_admin", table_name="users", schema="core")
    op.drop_column("users", "is_admin", schema="core")
