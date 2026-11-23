"""Create conference live states table and session type enums for temporal dynamic matching

Revision ID: 021_conf_temporal_states
Revises: 019_group_conversations
Create Date: 2026-11-03 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "021_conf_temporal_states"
down_revision: Union[str, None] = "019_group_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Enums in schema agenda
    session_type_enum = postgresql.ENUM(
        "KEYNOTE",
        "PANEL",
        "TECHNICAL_SESSION",
        "WORKSHOP",
        "TEA_BREAK",
        "LUNCH_BREAK",
        "NETWORKING_RECEPTION",
        "EXHIBITION_WALK",
        name="session_type",
        schema="agenda",
        create_type=False,
    )
    session_type_enum.create(bind, checkfirst=True)

    conf_live_state_enum = postgresql.ENUM(
        "IN_SESSION",
        "TEA_BREAK",
        "LUNCH_BREAK",
        "NETWORKING_RECEPTION",
        "FREE_TIME",
        name="conference_live_state",
        schema="agenda",
        create_type=False,
    )
    conf_live_state_enum.create(bind, checkfirst=True)

    break_type_enum = postgresql.ENUM(
        "TEA_COFFEE",
        "LUNCH",
        "CASUAL_NETWORKING",
        "EXHIBITION",
        "NONE",
        name="break_type",
        schema="agenda",
        create_type=False,
    )
    break_type_enum.create(bind, checkfirst=True)

    # 2. Add session_type column to agenda.sessions
    op.add_column(
        "sessions",
        sa.Column(
            "session_type",
            session_type_enum,
            server_default="TECHNICAL_SESSION",
            nullable=False,
        ),
        schema="agenda",
    )
    op.create_index(
        "idx_sessions_type",
        "sessions",
        ["session_type"],
        schema="agenda",
    )

    # 3. Create table agenda.conference_live_states
    op.create_table(
        "conference_live_states",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "active_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "current_state",
            conf_live_state_enum,
            server_default="IN_SESSION",
            nullable=False,
        ),
        sa.Column("custom_state_label", sa.String(length=150), nullable=True),
        sa.Column(
            "break_type",
            break_type_enum,
            server_default="NONE",
            nullable=False,
        ),
        sa.Column("designated_location", sa.String(length=150), nullable=True),
        sa.Column("announcement_banner", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "triggered_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("conference_id", name="uq_conference_live_state"),
        schema="agenda",
    )

    op.create_index(
        "ix_conf_live_state_conf_id",
        "conference_live_states",
        ["conference_id"],
        schema="agenda",
    )
    op.create_index(
        "ix_conf_live_state_active",
        "conference_live_states",
        ["is_active", "current_state"],
        schema="agenda",
    )

    # 4. Grants to converge_ai_app
    op.execute(f"GRANT USAGE ON TYPE agenda.session_type TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE agenda.conference_live_state TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE agenda.break_type TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON agenda.conference_live_states TO {RUNTIME_ROLE};")


def downgrade() -> None:
    op.drop_table("conference_live_states", schema="agenda")
    op.drop_index("idx_sessions_type", table_name="sessions", schema="agenda")
    op.drop_column("sessions", "session_type", schema="agenda")

    sa.Enum(name="break_type", schema="agenda").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="conference_live_state", schema="agenda").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="session_type", schema="agenda").drop(op.get_bind(), checkfirst=True)
