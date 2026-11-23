"""Create agenda domain foundation: agenda.conferences, agenda.sessions, agenda.bookmarked_sessions (GAP-09, GAP-10)

Revision ID: 007_agenda_sessions
Revises: 006_profile_matching_unique
Create Date: 2026-10-26 07:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_agenda_sessions"
down_revision: Union[str, None] = "006_profile_matching_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. Create agenda.conferences table (GAP-09 timezone & event foundation)
    op.create_table(
        "conferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("venue_name", sa.String(200), nullable=False),
        sa.Column(
            "timezone",
            sa.String(50),
            server_default="UTC",
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
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
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_conference_dates",
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_conference_title_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(venue_name)) > 0",
            name="ck_conference_venue_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(timezone)) > 0",
            name="ck_conference_timezone_nonempty",
        ),
        schema="agenda",
    )

    # 2. Create agenda.sessions table (GAP-09 room conflict constraint & provenance)
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "conference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agenda.conferences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("speaker_names", sa.String(255), nullable=True),
        sa.Column("track_name", sa.String(100), nullable=True),
        sa.Column("hall_room", sa.String(100), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("import_batch_id", sa.String(100), nullable=True),
        sa.Column(
            "is_cancelled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
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
        sa.CheckConstraint(
            "end_time > start_time",
            name="ck_session_times",
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_session_title_nonempty",
        ),
        sa.CheckConstraint(
            "length(trim(hall_room)) > 0",
            name="ck_session_hall_nonempty",
        ),
        sa.UniqueConstraint(
            "conference_id",
            "hall_room",
            "start_time",
            name="uq_session_room_starttime",
        ),
        schema="agenda",
    )

    # Indexes on agenda.sessions
    op.create_index(
        "idx_sessions_conference_id",
        "sessions",
        ["conference_id"],
        schema="agenda",
    )
    op.create_index(
        "idx_sessions_timerange",
        "sessions",
        ["start_time", "end_time"],
        schema="agenda",
    )
    op.create_index(
        "idx_sessions_track",
        "sessions",
        ["track_name"],
        schema="agenda",
    )
    op.create_index(
        "idx_sessions_import_batch",
        "sessions",
        ["import_batch_id"],
        schema="agenda",
    )

    # 3. Create agenda.bookmarked_sessions table (GAP-10 cascade on user/session deletion)
    op.create_table(
        "bookmarked_sessions",
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
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "session_id", name="pk_bookmarked_sessions"),
        schema="agenda",
    )

    # 4. Explicit runtime DML grants to converge_ai_app (GAP-02)
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA agenda TO {RUNTIME_ROLE};"
    )


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table("bookmarked_sessions", schema="agenda")
    op.drop_table("sessions", schema="agenda")
    op.drop_table("conferences", schema="agenda")
