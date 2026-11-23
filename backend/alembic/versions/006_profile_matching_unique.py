"""Profile matching consent explicit default (false) and case-insensitive unique indexes (GAP-03, GAP-10)

Revision ID: 006_profile_matching_unique
Revises: 005_participant_profiles
Create Date: 2026-10-23 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_profile_matching_unique"
down_revision: Union[str, None] = "005_participant_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enforce explicit consent default (FALSE) on core.participant_profiles.allow_agent_matching
    op.alter_column(
        "participant_profiles",
        "allow_agent_matching",
        server_default=sa.text("false"),
        schema="core",
    )

    # 2. Add case-insensitive functional unique index on participant_hobbies (user_id, lower(hobby_name))
    op.create_index(
        "uq_hobbies_user_normalized",
        "participant_hobbies",
        ["user_id", sa.text("lower(hobby_name)")],
        unique=True,
        schema="core",
    )

    # 3. Add case-insensitive functional unique index on participant_topics (user_id, lower(topic_keyword))
    op.create_index(
        "uq_topics_user_normalized",
        "participant_topics",
        ["user_id", sa.text("lower(topic_keyword)")],
        unique=True,
        schema="core",
    )


def downgrade() -> None:
    # 1. Drop functional unique indexes
    op.drop_index(
        "uq_topics_user_normalized",
        table_name="participant_topics",
        schema="core",
        if_exists=True,
    )
    op.drop_index(
        "uq_hobbies_user_normalized",
        table_name="participant_hobbies",
        schema="core",
        if_exists=True,
    )

    # 2. Revert server_default to true
    op.alter_column(
        "participant_profiles",
        "allow_agent_matching",
        server_default=sa.text("true"),
        schema="core",
    )
