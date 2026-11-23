"""Add allow_agent_dm_initiation and contact_sharing_policy to participant_profiles

Revision ID: 027_agent_dm_and_contact_policy
Revises: 026_live_state_active_day
Create Date: 2026-11-04 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "027_agent_dm_and_contact_policy"
down_revision: Union[str, None] = "026_live_state_active_day"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participant_profiles",
        sa.Column("allow_agent_dm_initiation", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        schema="core",
    )
    op.add_column(
        "participant_profiles",
        sa.Column("contact_sharing_policy", sa.String(50), server_default=sa.text("'ASK_HUMAN_FIRST'"), nullable=False),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("participant_profiles", "contact_sharing_policy", schema="core")
    op.drop_column("participant_profiles", "allow_agent_dm_initiation", schema="core")
