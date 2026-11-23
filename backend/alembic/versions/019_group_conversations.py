"""Create group conversation, member, and message tables for Thematic Networking Circles

Revision ID: 019_group_conversations
Revises: 018_extend_mood_length
Create Date: 2026-11-02 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "019_group_conversations"
down_revision: Union[str, None] = "018_extend_mood_length"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Enums for Group Conversations & Members
    group_status_enum = postgresql.ENUM(
        "INVITED", "ACTIVE", "COMPLETED", "CANCELLED",
        name="group_status",
        schema="core",
        create_type=False,
    )
    group_status_enum.create(bind, checkfirst=True)

    group_role_enum = postgresql.ENUM(
        "HOST", "MEMBER",
        name="group_role",
        schema="core",
        create_type=False,
    )
    group_role_enum.create(bind, checkfirst=True)

    # 2. Table: core.group_conversations
    op.create_table(
        "group_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("topic_context", sa.Text(), nullable=False),
        sa.Column(
            "host_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            group_status_enum,
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("max_turns", sa.Integer(), server_default="25", nullable=False),
        sa.Column("current_turn", sa.Integer(), server_default="0", nullable=False),
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
        sa.Column("concluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "max_turns >= 20 AND max_turns <= 50",
            name="ck_group_max_turns_range",
        ),
        sa.CheckConstraint(
            "current_turn >= 0 AND current_turn <= max_turns",
            name="ck_group_current_turn_range",
        ),
        sa.CheckConstraint(
            "length(trim(title)) >= 3 AND length(title) <= 120",
            name="ck_group_title_length",
        ),
        schema="core",
    )

    op.create_index(
        "ix_group_conversations_host",
        "group_conversations",
        ["host_id"],
        schema="core",
    )
    op.create_index(
        "ix_group_conversations_status",
        "group_conversations",
        ["status"],
        schema="core",
    )

    # 3. Table: core.group_members
    op.create_table(
        "group_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.group_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            group_role_enum,
            server_default="MEMBER",
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_read_turn", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member_user"),
        schema="core",
    )

    op.create_index(
        "ix_group_members_user",
        "group_members",
        ["user_id"],
        schema="core",
    )
    op.create_index(
        "ix_group_members_group",
        "group_members",
        ["group_id"],
        schema="core",
    )

    # 4. Table: core.group_messages
    op.create_table(
        "group_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.group_conversations.id", ondelete="CASCADE"),
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
                "PARTICIPANT", "AGENT", "SYSTEM",
                name="message_sender_type",
                schema="core",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=20), server_default="TEXT", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("turn_index >= 0", name="ck_group_msg_turn_index_nonnegative"),
        sa.CheckConstraint(
            "length(trim(content)) >= 1 AND length(content) <= 4000",
            name="ck_group_msg_content_length",
        ),
        sa.CheckConstraint(
            "((sender_type = 'SYSTEM' AND sender_id IS NULL) OR "
            "(sender_type IN ('PARTICIPANT', 'AGENT') AND sender_id IS NOT NULL))",
            name="ck_group_msg_sender_presence",
        ),
        sa.UniqueConstraint("group_id", "turn_index", name="uq_group_msg_turn"),
        schema="core",
    )

    op.create_index(
        "ix_group_messages_group_turn",
        "group_messages",
        ["group_id", "turn_index"],
        schema="core",
    )

    # 5. Explicit runtime least-privilege grants to converge_ai_app
    op.execute(f"GRANT USAGE ON TYPE core.group_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT USAGE ON TYPE core.group_role TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON core.group_conversations TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON core.group_members TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON core.group_messages TO {RUNTIME_ROLE};")


def downgrade() -> None:
    op.drop_table("group_messages", schema="core")
    op.drop_table("group_members", schema="core")
    op.drop_table("group_conversations", schema="core")

    sa.Enum(name="group_role", schema="core").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="group_status", schema="core").drop(op.get_bind(), checkfirst=True)
