"""Create conversation and persistent messaging foundation: core.conversations, core.messages (P5-WS2, GAP-06)

Revision ID: 008_persistent_messaging
Revises: 007_agenda_sessions
Create Date: 2026-10-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_persistent_messaging"
down_revision: Union[str, None] = "007_agenda_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. Create enum types in schema core
    sa.Enum(
        "INVITED",
        "ACTIVE",
        "COMPLETED",
        "CANCELLED",
        "EXPIRED",
        name="conversation_status",
        schema="core",
    ).create(op.get_bind(), checkfirst=True)

    sa.Enum(
        "PROPOSAL_GENERATED",
        "COMPLETED_WITHOUT_PROPOSAL",
        "CANCELLED",
        "EXPIRED",
        name="conversation_outcome",
        schema="core",
    ).create(op.get_bind(), checkfirst=True)

    sa.Enum(
        "PARTICIPANT",
        "AGENT",
        "SYSTEM",
        name="message_sender_type",
        schema="core",
    ).create(op.get_bind(), checkfirst=True)

    # 2. Create core.conversations table
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "initiator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "INVITED",
                "ACTIVE",
                "COMPLETED",
                "CANCELLED",
                "EXPIRED",
                name="conversation_status",
                schema="core",
                create_type=False,
            ),
            server_default="INVITED",
            nullable=False,
        ),
        sa.Column(
            "match_score",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column(
            "terminal_outcome",
            postgresql.ENUM(
                "PROPOSAL_GENERATED",
                "COMPLETED_WITHOUT_PROPOSAL",
                "CANCELLED",
                "EXPIRED",
                name="conversation_outcome",
                schema="core",
                create_type=False,
            ),
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
            nullable=False,
        ),
        sa.Column(
            "concluded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "initiator_id != target_id",
            name="ck_distinct_participants",
        ),
        sa.CheckConstraint(
            "((status IN ('COMPLETED', 'CANCELLED', 'EXPIRED') AND concluded_at IS NOT NULL AND terminal_outcome IS NOT NULL) OR "
            "(status IN ('INVITED', 'ACTIVE') AND concluded_at IS NULL AND terminal_outcome IS NULL))",
            name="ck_terminal_outcome_consistency",
        ),
        schema="core",
    )

    # Partial unique index for active pair concurrency (unordered functional index)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_conversation_pair 
        ON core.conversations (
            LEAST(initiator_id, target_id),
            GREATEST(initiator_id, target_id)
        )
        WHERE status IN ('INVITED', 'ACTIVE');
        """
    )

    op.create_index(
        "ix_conversations_initiator",
        "conversations",
        ["initiator_id"],
        schema="core",
    )
    op.create_index(
        "ix_conversations_target",
        "conversations",
        ["target_id"],
        schema="core",
    )
    op.create_index(
        "ix_conversations_status",
        "conversations",
        ["status"],
        schema="core",
    )

    # 3. Create core.messages table (Append-Only)
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sender_type",
            postgresql.ENUM(
                "PARTICIPANT",
                "AGENT",
                "SYSTEM",
                name="message_sender_type",
                schema="core",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "turn_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "turn_index >= 0",
            name="ck_turn_index_nonnegative",
        ),
        sa.CheckConstraint(
            "turn_index < 20",
            name="ck_turn_index_limit",
        ),
        sa.CheckConstraint(
            "length(trim(content)) >= 1 AND length(content) <= 4000",
            name="ck_content_length",
        ),
        sa.CheckConstraint(
            "((sender_type = 'SYSTEM' AND sender_id IS NULL) OR "
            "(sender_type IN ('PARTICIPANT', 'AGENT') AND sender_id IS NOT NULL))",
            name="ck_sender_presence",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "turn_index",
            name="uq_conversation_turn",
        ),
        schema="core",
    )

    op.create_index(
        "ix_messages_conversation_turn",
        "messages",
        ["conversation_id", "turn_index"],
        schema="core",
    )

    # 4. Explicit runtime least-privilege grants to converge_ai_app (GAP-02)
    op.execute(f"GRANT USAGE ON TYPE core.conversation_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE core.conversation_outcome TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE core.message_sender_type TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON core.conversations TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT ON core.messages TO {RUNTIME_ROLE};")


def downgrade() -> None:
    op.drop_table("messages", schema="core")
    op.drop_table("conversations", schema="core")
    
    sa.Enum(name="message_sender_type", schema="core").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="conversation_outcome", schema="core").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="conversation_status", schema="core").drop(op.get_bind(), checkfirst=True)
