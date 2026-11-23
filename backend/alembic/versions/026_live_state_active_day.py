"""Add active_day to conference_live_states

Revision ID: 026_live_state_active_day
Revises: 025_commercial_proposals
Create Date: 2026-11-04 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "026_live_state_active_day"
down_revision: Union[str, None] = "025_commercial_proposals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conference_live_states",
        sa.Column("active_day", sa.Integer(), nullable=True),
        schema="agenda",
    )


def downgrade() -> None:
    op.drop_column("conference_live_states", "active_day", schema="agenda")
