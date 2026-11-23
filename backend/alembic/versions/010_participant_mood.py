"""Add current_mood and mood_updated_at to core.participant_profiles (AC-WS1, GAP-03)

Revision ID: 010_participant_mood
Revises: 009_a2a_task_execution
Create Date: 2026-10-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "010_participant_mood"
down_revision: Union[str, None] = "009_a2a_task_execution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add current_mood and mood_updated_at columns to core.participant_profiles
    op.add_column(
        "participant_profiles",
        sa.Column("current_mood", sa.String(50), nullable=True),
        schema="core",
    )
    op.add_column(
        "participant_profiles",
        sa.Column("mood_updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="core",
    )

    # 2. Add check constraint to ensure mood is not merely whitespace
    op.create_check_constraint(
        "ck_participant_mood_not_empty",
        "participant_profiles",
        "current_mood IS NULL OR length(trim(current_mood)) > 0",
        schema="core",
    )


def downgrade() -> None:
    op.drop_constraint("ck_participant_mood_not_empty", "participant_profiles", schema="core", type_="check")
    op.drop_column("participant_profiles", "mood_updated_at", schema="core")
    op.drop_column("participant_profiles", "current_mood", schema="core")
