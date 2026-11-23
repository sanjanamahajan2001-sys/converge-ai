"""Add location, location_lat, and location_lng to participant_profiles

Revision ID: 013_profile_location
Revises: 012_profile_loc_act
Create Date: 2026-10-28 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "013_profile_location"
down_revision: Union[str, None] = "012_profile_loc_act"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participant_profiles",
        sa.Column("location", sa.String(length=255), nullable=True),
        schema="core",
    )
    op.add_column(
        "participant_profiles",
        sa.Column("location_lat", sa.Float(), nullable=True),
        schema="core",
    )
    op.add_column(
        "participant_profiles",
        sa.Column("location_lng", sa.Float(), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("participant_profiles", "location_lng", schema="core")
    op.drop_column("participant_profiles", "location_lat", schema="core")
    op.drop_column("participant_profiles", "location", schema="core")
