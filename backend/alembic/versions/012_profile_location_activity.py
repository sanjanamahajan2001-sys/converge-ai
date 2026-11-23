"""Add gender and date_of_birth to participant_profiles, message location support, and user activity events

Revision ID: 012_phase1_profile_location_activity
Revises: 011_session_intent_decisions
Create Date: 2026-10-28 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012_profile_loc_act"
down_revision: Union[str, None] = "011_session_intent_decisions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. User Profile Enhancements: gender and date_of_birth
    op.add_column(
        "participant_profiles",
        sa.Column("gender", sa.String(length=30), nullable=True),
        schema="core",
    )
    op.add_column(
        "participant_profiles",
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        schema="core",
    )

    # 2. Location Sharing in Messaging: message_type and location_payload
    op.add_column(
        "messages",
        sa.Column("message_type", sa.String(length=20), server_default="TEXT", nullable=False),
        schema="core",
    )
    op.add_column(
        "messages",
        sa.Column("location_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="core",
    )
    op.create_index(
        "idx_messages_type",
        "messages",
        ["message_type"],
        schema="core",
    )

    # 3. User Activity Events: analytics and interaction tracking
    op.create_table(
        "user_activity_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("feature_name", sa.String(length=100), nullable=False),
        sa.Column("target_resource_id", sa.String(length=100), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="core",
    )
    op.create_index(
        "idx_activity_user_created",
        "user_activity_events",
        ["user_id", "created_at"],
        schema="core",
    )
    op.create_index(
        "idx_activity_event_type",
        "user_activity_events",
        ["event_type", "created_at"],
        schema="core",
    )


def downgrade() -> None:
    # 3. Drop user_activity_events
    op.drop_index("idx_activity_event_type", table_name="user_activity_events", schema="core")
    op.drop_index("idx_activity_user_created", table_name="user_activity_events", schema="core")
    op.drop_table("user_activity_events", schema="core")

    # 2. Drop location message columns
    op.drop_index("idx_messages_type", table_name="messages", schema="core")
    op.drop_column("messages", "location_payload", schema="core")
    op.drop_column("messages", "message_type", schema="core")

    # 1. Drop profile columns
    op.drop_column("participant_profiles", "date_of_birth", schema="core")
    op.drop_column("participant_profiles", "gender", schema="core")
