"""Expand message turn limit from 20 to 30

Revision ID: 023_msg_limit_30
Revises: 022_conf_chatrooms
Create Date: 2026-11-03 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "023_msg_limit_30"
down_revision: Union[str, None] = "022_conf_chatrooms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_turn_index_limit", "messages", schema="core", type_="check")
    op.create_check_constraint(
        "ck_turn_index_limit",
        "messages",
        "turn_index < 30",
        schema="core",
    )


def downgrade() -> None:
    op.drop_constraint("ck_turn_index_limit", "messages", schema="core", type_="check")
    op.create_check_constraint(
        "ck_turn_index_limit",
        "messages",
        "turn_index < 20",
        schema="core",
    )
