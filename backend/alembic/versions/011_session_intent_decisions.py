"""Add session_intent_decisions to agenda schema (AC-WS8, Manager Consent & Memory Requirement)

Revision ID: 011_session_intent_decisions
Revises: 010_participant_mood
Create Date: 2026-10-27 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "011_session_intent_decisions"
down_revision: Union[str, None] = "010_participant_mood"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create agenda.session_intent_decisions table
    op.create_table(
        "session_intent_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'UNDECIDED'"),
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'REPRESENTATIVE_PROMPT'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "session_id", name="uq_session_intent_user_session"),
        sa.CheckConstraint(
            "decision IN ('ATTENDING', 'DECLINED', 'UNDECIDED')",
            name="ck_session_intent_decision_state",
        ),
        schema="agenda",
    )

    # 2. Indexes for high-throughput lookup during representative dialogue generation
    op.create_index(
        "ix_session_intent_decisions_user_id",
        "session_intent_decisions",
        ["user_id"],
        schema="agenda",
    )
    op.create_index(
        "ix_session_intent_decisions_session_id",
        "session_intent_decisions",
        ["session_id"],
        schema="agenda",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_intent_decisions_session_id",
        table_name="session_intent_decisions",
        schema="agenda",
    )
    op.drop_index(
        "ix_session_intent_decisions_user_id",
        table_name="session_intent_decisions",
        schema="agenda",
    )
    op.drop_table("session_intent_decisions", schema="agenda")
