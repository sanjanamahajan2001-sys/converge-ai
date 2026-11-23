"""Add amenities_note to conference_live_states

Revision ID: 024_live_state_amenities
Revises: 023_msg_limit_30
Create Date: 2026-11-03 20:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "024_live_state_amenities"
down_revision: Union[str, None] = "023_msg_limit_30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conference_live_states",
        sa.Column("amenities_note", sa.String(length=255), nullable=True),
        schema="agenda",
    )


def downgrade() -> None:
    op.drop_column("conference_live_states", "amenities_note", schema="agenda")
