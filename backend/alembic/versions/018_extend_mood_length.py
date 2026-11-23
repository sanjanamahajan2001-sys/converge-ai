"""Extend current_mood max length to 255 characters

Revision ID: 018_extend_mood_length
Revises: 017_dynamic_product_entry
Create Date: 2026-10-29 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "018_extend_mood_length"
down_revision: Union[str, None] = "017_dynamic_product_entry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Expand current_mood VARCHAR from 50 to 255 in core.participant_profiles
    op.alter_column(
        "participant_profiles",
        "current_mood",
        type_=sa.String(length=255),
        existing_type=sa.String(length=50),
        schema="core",
    )


def downgrade() -> None:
    # 1. Truncate any values exceeding 50 chars before shrinking to prevent failure
    op.execute(
        "UPDATE core.participant_profiles SET current_mood = SUBSTRING(current_mood FROM 1 FOR 50) WHERE length(current_mood) > 50;"
    )
    # 2. Revert column type to VARCHAR(50)
    op.alter_column(
        "participant_profiles",
        "current_mood",
        type_=sa.String(length=50),
        existing_type=sa.String(length=255),
        schema="core",
    )
