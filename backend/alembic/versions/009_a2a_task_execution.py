"""Create A2A task persistence foundation: a2a.tasks, a2a.task_attempts (Phase 6, GAP-03, GAP-06)

Revision ID: 009_a2a_task_execution
Revises: 008_persistent_messaging
Create Date: 2026-10-26 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009_a2a_task_execution"
down_revision: Union[str, None] = "008_persistent_messaging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUNTIME_ROLE = "converge_ai_app"


def upgrade() -> None:
    # 1. Create task_status enum in schema a2a
    sa.Enum(
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "RETRYABLE_FAILURE",
        "FAILED",
        "CANCELLED",
        name="task_status",
        schema="a2a",
    ).create(op.get_bind(), checkfirst=True)

    # 2. Create a2a.tasks table
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "task_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.conversations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "initiator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "RUNNING",
                "SUCCEEDED",
                "RETRYABLE_FAILURE",
                "FAILED",
                "CANCELLED",
                name="task_status",
                schema="a2a",
                create_type=False,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
        sa.Column(
            "lease_owner",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "error_category",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "error_detail",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
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
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts",
            name="ck_task_attempt_count_bounds",
        ),
        sa.CheckConstraint(
            "max_attempts >= 1 AND max_attempts <= 10",
            name="ck_task_max_attempts_bounds",
        ),
        sa.CheckConstraint(
            "((status = 'RUNNING' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR (status != 'RUNNING'))",
            name="ck_task_lease_consistency",
        ),
        sa.CheckConstraint(
            "((status IN ('SUCCEEDED', 'FAILED', 'CANCELLED') AND completed_at IS NOT NULL) OR (status NOT IN ('SUCCEEDED', 'FAILED', 'CANCELLED')))",
            name="ck_task_terminal_consistency",
        ),
        schema="a2a",
    )

    # Queue index for worker claiming: pending or expired running or retryable
    op.create_index(
        "ix_tasks_claim_queue",
        "tasks",
        ["status", "scheduled_at"],
        schema="a2a",
    )
    op.create_index(
        "ix_tasks_conversation_id",
        "tasks",
        ["conversation_id"],
        schema="a2a",
    )
    op.create_index(
        "ix_tasks_initiator_id",
        "tasks",
        ["initiator_id"],
        schema="a2a",
    )
    op.create_index(
        "ix_tasks_lease_expiry",
        "tasks",
        ["status", "lease_expires_at"],
        schema="a2a",
    )
    # Unique partial index for task enqueue idempotency per conversation and idempotency key
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tasks_conversation_idempotency
        ON a2a.tasks (conversation_id, (payload->>'idempotency_key'))
        WHERE conversation_id IS NOT NULL AND (payload->>'idempotency_key') IS NOT NULL;
        """
    )

    # 3. Create a2a.task_attempts table (Execution Audit Trail)
    op.create_table(
        "task_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("a2a.tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "worker_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "RUNNING",
                "SUCCEEDED",
                "RETRYABLE_FAILURE",
                "FAILED",
                "CANCELLED",
                name="task_status",
                schema="a2a",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "error_category",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "error_detail",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "task_id",
            "attempt_number",
            name="uq_task_attempt_number",
        ),
        schema="a2a",
    )

    op.create_index(
        "ix_task_attempts_task_id",
        "task_attempts",
        ["task_id"],
        schema="a2a",
    )

    # 4. Explicit runtime least-privilege grants to converge_ai_app (GAP-02)
    op.execute(f"GRANT USAGE ON TYPE a2a.task_status TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON a2a.tasks TO {RUNTIME_ROLE};")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON a2a.task_attempts TO {RUNTIME_ROLE};")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS a2a.uq_tasks_conversation_idempotency;")
    op.drop_table("task_attempts", schema="a2a")
    op.drop_table("tasks", schema="a2a")
    sa.Enum(name="task_status", schema="a2a").drop(op.get_bind(), checkfirst=True)
