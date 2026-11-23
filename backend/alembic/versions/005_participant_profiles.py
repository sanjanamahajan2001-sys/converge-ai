"""Create participant profiles and interest tables: core.participant_profiles, core.participant_hobbies, core.participant_topics (GAP-03, GAP-10)

Revision ID: 005_participant_profiles
Revises: 004_user_sessions
Create Date: 2026-10-23 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_participant_profiles"
down_revision: Union[str, None] = "004_user_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. Create enum types in schema core
    sa.Enum(
        "NETWORKING",
        "CASUAL",
        "BOTH",
        name="participation_intent",
        schema="core",
    ).create(op.get_bind(), checkfirst=True)

    sa.Enum(
        "AVAILABLE",
        "IN_SESSION",
        "DO_NOT_DISTURB",
        "OFFLINE",
        name="availability_status",
        schema="core",
    ).create(op.get_bind(), checkfirst=True)

    # 2. Create core.participant_profiles table
    op.create_table(
        "participant_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "intent",
            postgresql.ENUM(
                "NETWORKING",
                "CASUAL",
                "BOTH",
                name="participation_intent",
                schema="core",
                create_type=False,
            ),
            server_default="NETWORKING",
            nullable=False,
        ),
        sa.Column("bio_summary", sa.String(length=500), nullable=True),
        sa.Column(
            "availability",
            postgresql.ENUM(
                "AVAILABLE",
                "IN_SESSION",
                "DO_NOT_DISTURB",
                "OFFLINE",
                name="availability_status",
                schema="core",
                create_type=False,
            ),
            server_default="AVAILABLE",
            nullable=False,
        ),
        sa.Column(
            "allow_agent_matching",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core.users.id"],
            name="fk_participant_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_participant_profiles"),
        schema="core",
    )

    # 3. Create core.participant_hobbies table
    op.create_table(
        "participant_hobbies",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("hobby_name", sa.String(length=60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(hobby_name)) > 0",
            name="ck_hobby_name_not_empty",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core.users.id"],
            name="fk_participant_hobbies_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_participant_hobbies"),
        sa.UniqueConstraint("user_id", "hobby_name", name="uq_user_hobby"),
        schema="core",
    )
    op.create_index(
        "idx_hobbies_user_id",
        "participant_hobbies",
        ["user_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "idx_hobbies_normalized",
        "participant_hobbies",
        [sa.text("lower(hobby_name)")],
        unique=False,
        schema="core",
    )

    # 4. Create core.participant_topics table
    op.create_table(
        "participant_topics",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("topic_keyword", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(topic_keyword)) > 0",
            name="ck_topic_keyword_not_empty",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core.users.id"],
            name="fk_participant_topics_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_participant_topics"),
        sa.UniqueConstraint("user_id", "topic_keyword", name="uq_user_topic"),
        schema="core",
    )
    op.create_index(
        "idx_topics_user_id",
        "participant_topics",
        ["user_id"],
        unique=False,
        schema="core",
    )
    op.create_index(
        "idx_topics_normalized",
        "participant_topics",
        [sa.text("lower(topic_keyword)")],
        unique=False,
        schema="core",
    )

    # 5. Role permissions for runtime user
    op.execute(
        f"GRANT USAGE ON TYPE core.participation_intent TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"GRANT USAGE ON TYPE core.availability_status TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE core.participant_profiles TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE core.participant_hobbies TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE core.participant_topics TO {RUNTIME_ROLE};"
    )
    op.execute(
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO {RUNTIME_ROLE};"
    )


def downgrade() -> None:
    # 1. Drop topic indexes & table
    op.drop_index("idx_topics_normalized", table_name="participant_topics", schema="core", if_exists=True)
    op.drop_index("idx_topics_user_id", table_name="participant_topics", schema="core", if_exists=True)
    op.drop_table("participant_topics", schema="core")

    # 2. Drop hobby indexes & table
    op.drop_index("idx_hobbies_normalized", table_name="participant_hobbies", schema="core", if_exists=True)
    op.drop_index("idx_hobbies_user_id", table_name="participant_hobbies", schema="core", if_exists=True)
    op.drop_table("participant_hobbies", schema="core")

    # 3. Drop participant_profiles table
    op.drop_table("participant_profiles", schema="core")

    # 4. Drop enum types
    sa.Enum(name="availability_status", schema="core").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="participation_intent", schema="core").drop(op.get_bind(), checkfirst=True)
