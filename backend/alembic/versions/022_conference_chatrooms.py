"""Create conference chatroom tables for open public lounge

Revision ID: 022_conf_chatrooms
Revises: 021_conf_temporal_states
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "022_conf_chatrooms"
down_revision: Union[str, None] = "021_conf_temporal_states"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. agenda.conference_chatrooms
    op.create_table(
        "conference_chatrooms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "conference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=120), nullable=False, server_default="The Networking Lounge"),
        sa.Column("slug", sa.String(length=64), nullable=False, server_default="networking-lounge"),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            server_default="Open public lounge for all delegates to hang out, share thoughts, and stay updated during breaks.",
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ambient_interval_seconds", sa.Integer(), server_default=sa.text("20"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_conference_chatrooms_slug"),
        sa.CheckConstraint("length(trim(name)) >= 3", name="ck_chatroom_name_length"),
        schema="agenda",
    )
    op.create_index(
        "idx_chatrooms_conference",
        "conference_chatrooms",
        ["conference_id"],
        schema="agenda",
    )
    op.create_index(
        "idx_chatrooms_active",
        "conference_chatrooms",
        ["is_active"],
        schema="agenda",
    )

    # 2. agenda.chatroom_messages
    op.create_table(
        "chatroom_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "chatroom_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.conference_chatrooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sender_type", sa.String(length=32), nullable=False, server_default="USER"),
        sa.Column("sender_name", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_kind", sa.String(length=32), nullable=False, server_default="CHAT"),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("turn_index >= 0", name="ck_chatroom_msg_turn_index"),
        sa.CheckConstraint("length(trim(content)) >= 1 AND length(content) <= 4000", name="ck_chatroom_msg_content_len"),
        schema="agenda",
    )
    op.create_index(
        "idx_chatroom_messages_room_turn",
        "chatroom_messages",
        ["chatroom_id", "turn_index"],
        schema="agenda",
    )
    op.create_index(
        "idx_chatroom_messages_created",
        "chatroom_messages",
        ["created_at"],
        schema="agenda",
    )

    # 3. agenda.chatroom_presences
    op.create_table(
        "chatroom_presences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "chatroom_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.conference_chatrooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_online", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chatroom_id", "user_id", name="uq_chatroom_presence_user"),
        schema="agenda",
    )
    op.create_index(
        "idx_chatroom_presences_room_user",
        "chatroom_presences",
        ["chatroom_id", "user_id"],
        schema="agenda",
    )

    # 4. Grants to converge_ai_app
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
        f"agenda.conference_chatrooms, agenda.chatroom_messages, agenda.chatroom_presences "
        f"TO {RUNTIME_ROLE};"
    )

    # 5. Seed default Networking Lounge
    op.execute(
        """
        INSERT INTO agenda.conference_chatrooms (
            id, name, slug, description, is_active, ambient_interval_seconds
        ) VALUES (
            gen_random_uuid(),
            'The Networking Lounge',
            'networking-lounge',
            'Open public lounge for all delegates to hang out, share thoughts, and stay updated during breaks.',
            true,
            20
        ) ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("chatroom_presences", schema="agenda")
    op.drop_table("chatroom_messages", schema="agenda")
    op.drop_table("conference_chatrooms", schema="agenda")
