"""Background Agent Worker & Task Execution Engine (Phase 6, GAP-03, GAP-06).

Implements durable PostgreSQL-backed task queue execution with:
- Row-level claiming via SELECT ... FOR UPDATE SKIP LOCKED
- Lease expiration and automatic worker recovery
- Stale-worker detection and write isolation
- Context-aware dialogue generation via DeterministicRepresentativeEngine
- Monotonic 20-turn conversation limit and WebSocket broadcast
- Bounded retries for transient errors and immediate terminal failure for permanent errors
"""

import asyncio
import os
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.conversations import manager
from app.core.audit import record_audit_event
from app.core.config import get_settings

settings = get_settings()
from app.db.models.agenda import BookmarkedSession, Session, SessionIntentDecision
from app.db.models.conversation import (
    Conversation,
    ConversationOutcome,
    ConversationStatus,
    Message,
    MessageSenderType,
)
from app.db.models.profile import ParticipantHobby, ParticipantProfile, ParticipantTopic
from app.db.models.task import Task, TaskAttempt, TaskStatus
from app.db.models.user import User
from app.db.session import db_manager
from app.schemas.a2a import A2AMessageEnvelope
from app.services.conversation import ConversationService, get_max_agent_turns
from app.services.representative import DeterministicRepresentativeEngine

logger = logging.getLogger(__name__)


class TaskExecutionError(Exception):
    """Base exception for task execution failures."""
    category: str = "GENERIC_ERROR"


class TransientTaskError(TaskExecutionError):
    """Temporary failure eligible for exponential retry backoff."""
    category: str = "TRANSIENT_FAILURE"


class PermanentTaskError(TaskExecutionError):
    """Unrecoverable failure that transitions task immediately to FAILED."""
    category: str = "PERMANENT_FAILURE"


class StaleWorkerError(TaskExecutionError):
    """Raised when a worker's lease expired and task was claimed by another worker."""
    category: str = "STALE_WORKER"


class AgentTaskService:
    """Service layer managing durable agent task claiming, execution, recovery, and audit logs."""

    @staticmethod
    async def create_agent_dialogue_task(
        db: AsyncSession,
        conversation_id: UUID,
        initiator_id: UUID,
        target_id: UUID,
        turn_index: int,
        idempotency_key: str,
        scheduled_delay_seconds: int = 0,
        commit: bool = True,
        payload_extra: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a durable background dialogue turn task in a2a.tasks with race-safe idempotency."""
        # 1. Idempotency & duplicate turn check
        # Check for any existing task with this idempotency key regardless of status
        existing_stmt = select(Task).where(
            Task.conversation_id == conversation_id,
            Task.payload["idempotency_key"].astext == idempotency_key,
        )
        existing = await db.scalar(existing_stmt)
        if existing:
            if existing.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.SUCCEEDED):
                logger.info("Replay detected: Task for key %s already exists (status=%s)", idempotency_key, existing.status)
                return existing
            elif existing.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                # Reset failed/cancelled task so it can be re-executed
                logger.info("Resetting %s task %s for retry", existing.status, existing.id)
                now = datetime.now(timezone.utc)
                existing.status = TaskStatus.PENDING
                existing.attempt_count = 0
                existing.lease_owner = None
                existing.lease_expires_at = None
                existing.error_category = None
                existing.error_detail = None
                existing.started_at = None
                existing.completed_at = None
                existing.scheduled_at = now + timedelta(seconds=scheduled_delay_seconds)
                if payload_extra:
                    p = dict(existing.payload or {})
                    p.update(payload_extra)
                    existing.payload = p
                if commit:
                    await db.commit()
                    await db.refresh(existing)
                else:
                    await db.flush()
                return existing

        now = datetime.now(timezone.utc)
        scheduled_at = now + timedelta(seconds=scheduled_delay_seconds)

        payload_dict = {
            "turn_index": turn_index,
            "idempotency_key": idempotency_key,
        }
        if payload_extra:
            payload_dict.update(payload_extra)

        task = Task(
            task_type="AGENT_DIALOGUE_TURN",
            conversation_id=conversation_id,
            initiator_id=initiator_id,
            target_id=target_id,
            status=TaskStatus.PENDING,
            attempt_count=0,
            max_attempts=3,
            scheduled_at=scheduled_at,
            payload=payload_dict,
        )
        try:
            db.add(task)
            if commit:
                await db.commit()
                await db.refresh(task)
            else:
                await db.flush()
            logger.info("Created agent dialogue task %s for conv %s turn %s", task.id, conversation_id, turn_index)
            return task
        except IntegrityError:
            # Handles duplicate submission race condition caught by uq_tasks_conversation_idempotency
            await db.rollback()
            existing_retry = await db.scalar(existing_stmt)
            if existing_retry:
                logger.info("Unique index collision caught: Reusing existing task %s", existing_retry.id)
                return existing_retry
            raise

    @staticmethod
    async def cancel_conversation_tasks(
        db: AsyncSession,
        conversation_id: UUID,
        reason: str = "Conversation cancelled or concluded",
    ) -> int:
        """Cancel all pending or retryable tasks for a conversation."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Task)
            .where(
                Task.conversation_id == conversation_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.RETRYABLE_FAILURE]),
            )
            .values(
                status=TaskStatus.CANCELLED,
                completed_at=now,
                error_category="CONVERSATION_INACTIVE",
                error_detail=reason,
                updated_at=now,
            )
        )
        res = await db.execute(stmt)
        return res.rowcount

    @staticmethod
    async def claim_next_task(
        db: AsyncSession,
        worker_id: str,
        lease_duration: timedelta = timedelta(seconds=30),
    ) -> Optional[Task]:
        """Claim the next ready task using PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)

        # Claim criteria:
        # 1. PENDING and scheduled_at <= now
        # 2. RUNNING but lease_expires_at < now (worker crashed / lease expired)
        # 3. RETRYABLE_FAILURE and scheduled_at <= now
        claimable_filter = or_(
            (Task.status == TaskStatus.PENDING) & (Task.scheduled_at <= now),
            (Task.status == TaskStatus.RUNNING) & (Task.lease_expires_at < now),
            (Task.status == TaskStatus.RETRYABLE_FAILURE) & (Task.scheduled_at <= now),
        )

        stmt = (
            select(Task)
            .where(claimable_filter)
            .order_by(Task.scheduled_at.asc(), Task.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        task = await db.scalar(stmt)
        if not task:
            return None

        # Transition to RUNNING and bind lease
        task.status = TaskStatus.RUNNING
        task.lease_owner = worker_id
        task.lease_expires_at = now + lease_duration
        task.started_at = now
        task.attempt_count += 1
        task.updated_at = now

        # Record execution attempt history
        attempt = TaskAttempt(
            task_id=task.id,
            attempt_number=task.attempt_count,
            worker_id=worker_id,
            started_at=now,
            status=TaskStatus.RUNNING,
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(task)

        logger.info("Worker %s successfully claimed task %s (attempt %s/%s)", worker_id, task.id, task.attempt_count, task.max_attempts)
        return task

    @staticmethod
    async def execute_task(
        db: AsyncSession,
        task: Task,
        worker_id: str,
        client_ip: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        """Execute task logic and persist results safely with lease validation."""
        start_time = datetime.now(timezone.utc)

        if task.lease_owner != worker_id:
            raise StaleWorkerError(
                f"Worker {worker_id} does not hold active lease on task {task.id} (lease_owner={task.lease_owner})"
            )

        if task.task_type != "AGENT_DIALOGUE_TURN":
            raise PermanentTaskError(f"Unsupported task_type: {task.task_type}")

        conv_id = task.conversation_id
        if not conv_id:
            raise PermanentTaskError("Task has no associated conversation_id")

        # 1. Fetch conversation with participants
        conv_stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.initiator),
                selectinload(Conversation.target),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conv_id)
        )
        conv = await db.scalar(conv_stmt)
        if not conv:
            raise PermanentTaskError(f"Conversation {conv_id} not found")

        # If conversation is not ACTIVE, terminate task without retry
        if conv.status != ConversationStatus.ACTIVE:
            raise PermanentTaskError(f"Conversation {conv_id} is in terminal or inactive state: {conv.status.value}")

        turn_count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conv_id)
        turn_index = await db.scalar(turn_count_stmt) or 0
        if turn_index >= 30:
            raise PermanentTaskError(f"Conversation {conv_id} reached 30-message turn limit")

        max_agent_turns = get_max_agent_turns()
        if turn_index >= max_agent_turns:
            logger.info("Task %s skipped: representative exchange complete (current turn=%s >= %s).", task.id, turn_index, max_agent_turns)
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            update_stmt = (
                update(Task)
                .where(Task.id == task.id, Task.lease_owner == worker_id)
                .values(
                    status=TaskStatus.SUCCEEDED,
                    completed_at=end_time,
                    result={"turn_index": turn_index, "action_type": "SKIPPED_REPRESENTATIVE_EXCHANGE_COMPLETE", "duration_ms": duration_ms},
                    lease_owner=None,
                    lease_expires_at=None,
                    updated_at=end_time,
                )
            )
            res = await db.execute(update_stmt)
            if res.rowcount == 0:
                raise StaleWorkerError(f"Worker {worker_id} lost lease on task {task.id}")
            attempt_update = (
                update(TaskAttempt)
                .where(TaskAttempt.task_id == task.id, TaskAttempt.attempt_number == task.attempt_count)
                .values(status=TaskStatus.SUCCEEDED, completed_at=end_time, duration_ms=duration_ms)
            )
            await db.execute(attempt_update)
            await db.commit()
            return {"turn_index": turn_index, "action_type": "SKIPPED_REPRESENTATIVE_EXCHANGE_COMPLETE"}

        # Idempotency check: if this task was meant for a turn that has already been satisfied
        expected_turn = task.payload.get("turn_index") if task.payload else None
        if expected_turn is not None and expected_turn < turn_index:
            logger.info("Task %s for turn %s is already satisfied (current turn=%s). Completing.", task.id, expected_turn, turn_index)
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            update_stmt = (
                update(Task)
                .where(Task.id == task.id, Task.lease_owner == worker_id)
                .values(
                    status=TaskStatus.SUCCEEDED,
                    completed_at=end_time,
                    result={"turn_index": expected_turn, "action_type": "SKIPPED_ALREADY_SATISFIED", "duration_ms": duration_ms},
                    lease_owner=None,
                    lease_expires_at=None,
                    updated_at=end_time,
                )
            )
            res = await db.execute(update_stmt)
            if res.rowcount == 0:
                raise StaleWorkerError(f"Worker {worker_id} lost lease on task {task.id}")
            attempt_update = (
                update(TaskAttempt)
                .where(TaskAttempt.task_id == task.id, TaskAttempt.attempt_number == task.attempt_count)
                .values(status=TaskStatus.SUCCEEDED, completed_at=end_time, duration_ms=duration_ms)
            )
            await db.execute(attempt_update)
            await db.commit()
            return {"turn_index": expected_turn, "action_type": "SKIPPED_ALREADY_SATISFIED"}

        # 2. Gather context for Initiator and Target
        initiator = conv.initiator
        target = conv.target

        # Initiator Profile & Collections
        init_prof_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == initiator.id)
        init_prof = (await db.execute(init_prof_stmt)).scalar_one()

        init_topics = (
            await db.scalars(
                select(ParticipantTopic.topic_keyword).where(ParticipantTopic.user_id == initiator.id)
            )
        ).all()
        init_hobbies = (
            await db.scalars(
                select(ParticipantHobby.hobby_name).where(ParticipantHobby.user_id == initiator.id)
            )
        ).all()
        init_bookmarks = (
            await db.scalars(
                select(Session.title)
                .join(BookmarkedSession, BookmarkedSession.session_id == Session.id)
                .where(
                    BookmarkedSession.user_id == initiator.id,
                    Session.is_cancelled == False,
                )
            )
        ).all()
        init_decisions_stmt = (
            select(Session.title, SessionIntentDecision.decision)
            .join(SessionIntentDecision, SessionIntentDecision.session_id == Session.id)
            .where(
                SessionIntentDecision.user_id == initiator.id,
                Session.is_cancelled == False,
            )
        )
        init_decisions_rows = (await db.execute(init_decisions_stmt)).all()
        init_decisions = {r[0]: r[1] for r in init_decisions_rows}
        init_attending = [r[0] for r in init_decisions_rows if r[1] == "ATTENDING"]

        # Target Profile & Collections
        target_prof_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == target.id)
        target_prof = (await db.execute(target_prof_stmt)).scalar_one()

        target_topics = (
            await db.scalars(
                select(ParticipantTopic.topic_keyword).where(ParticipantTopic.user_id == target.id)
            )
        ).all()
        target_hobbies = (
            await db.scalars(
                select(ParticipantHobby.hobby_name).where(ParticipantHobby.user_id == target.id)
            )
        ).all()
        target_bookmarks = (
            await db.scalars(
                select(Session.title)
                .join(BookmarkedSession, BookmarkedSession.session_id == Session.id)
                .where(
                    BookmarkedSession.user_id == target.id,
                    Session.is_cancelled == False,
                )
            )
        ).all()
        target_decisions_stmt = (
            select(Session.title, SessionIntentDecision.decision)
            .join(SessionIntentDecision, SessionIntentDecision.session_id == Session.id)
            .where(
                SessionIntentDecision.user_id == target.id,
                Session.is_cancelled == False,
            )
        )
        target_decisions_rows = (await db.execute(target_decisions_stmt)).all()
        target_decisions = {r[0]: r[1] for r in target_decisions_rows}
        target_attending = [r[0] for r in target_decisions_rows if r[1] == "ATTENDING"]

        # Check for commercial business context snapshot (Phase 4 & Phase 5)
        from app.db.models.business import ConversationBusinessContext, BusinessOffering, BusinessProfile

        ctx_stmt = select(ConversationBusinessContext).where(
            ConversationBusinessContext.conversation_id == conv.id
        )
        business_ctx = await db.scalar(ctx_stmt)

        target_offering = None
        init_biz_prof = None
        target_biz_prof = None

        if business_ctx:
            init_bp_stmt = select(BusinessProfile).where(BusinessProfile.user_id == initiator.id)
            init_biz_prof = await db.scalar(init_bp_stmt)

            target_bp_stmt = select(BusinessProfile).where(BusinessProfile.user_id == target.id)
            target_biz_prof = await db.scalar(target_bp_stmt)

            # Check which participant holds the catalog offering (Initiator or Target)
            offering_owner_prof = None
            if business_ctx.inquiry_type in ("SUPPLIER_PROSPECTING", "VENDOR_PITCH"):
                offering_owner_prof = init_biz_prof or target_biz_prof
            else:
                offering_owner_prof = target_biz_prof or init_biz_prof

            if offering_owner_prof:
                off_stmt = select(BusinessOffering).where(
                    BusinessOffering.business_profile_id == offering_owner_prof.id,
                    BusinessOffering.is_active == True,
                )
                offerings = (await db.scalars(off_stmt)).all()
                for off in offerings:
                    if business_ctx.product_code and off.product_code == business_ctx.product_code:
                        target_offering = off
                        break
                    if business_ctx.service_code and off.service_code == business_ctx.service_code:
                        target_offering = off
                        break
                    off_title = getattr(off, "custom_product_title", None) or getattr(off, "custom_offering_title", "")
                    if off_title and business_ctx.product_name:
                        if (
                            off_title.lower() in business_ctx.product_name.lower()
                            or business_ctx.product_name.lower() in off_title.lower()
                        ):
                            target_offering = off
                            break
                if not target_offering and offerings:
                    target_offering = offerings[0]

        # 3. Generate contextual dialogue turn
        idempotency_key = (
            task.payload.get("idempotency_key")
            if task.payload
            else f"agent-turn-{task.id}-{turn_index}"
        )

        # Fetch active temporal context (break state & recently ended talk momentum)
        from app.services.temporal_context import TemporalContextService
        temporal_ctx = await TemporalContextService.get_current_conference_state(db)

        envelope = DeterministicRepresentativeEngine.generate_dialogue_turn(
            conversation_id=conv.id,
            turn_index=turn_index,
            initiator=initiator,
            initiator_profile=init_prof,
            initiator_topics=list(init_topics),
            initiator_hobbies=list(init_hobbies),
            initiator_sessions=list(init_bookmarks),
            target=target,
            target_profile=target_prof,
            target_topics=list(target_topics),
            target_hobbies=list(target_hobbies),
            target_sessions=list(target_bookmarks),
            idempotency_key=idempotency_key,
            initiator_mood=init_prof.active_mood,
            target_mood=target_prof.active_mood,
            initiator_attending_sessions=list(init_attending),
            target_attending_sessions=list(target_attending),
            initiator_session_decisions=init_decisions,
            target_session_decisions=target_decisions,
            business_context=business_ctx,
            target_offering=target_offering,
            initiator_business_profile=init_biz_prof,
            target_business_profile=target_biz_prof,
            temporal_context=temporal_ctx,
            total_planned_turns=get_max_agent_turns(),
        )

        # 4. Append message to database via ConversationService as AGENT (commit=False for atomicity)
        msg_dto, conv_detail = await ConversationService.append_message(
            db=db,
            conversation_id=conv.id,
            sender_id=envelope.sender_id,
            content=envelope.content,
            client_ip=client_ip,
            sender_type=MessageSenderType.AGENT,
            commit=False,
        )

        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        result_data = {
            "message_id": str(msg_dto.id),
            "turn_index": msg_dto.turn_index,
            "sender_id": str(msg_dto.sender_id),
            "action_type": envelope.action_type.value,
            "duration_ms": duration_ms,
        }

        # 5. Check lease ownership before commit and update task status
        update_stmt = (
            update(Task)
            .where(Task.id == task.id, Task.lease_owner == worker_id)
            .values(
                status=TaskStatus.SUCCEEDED,
                completed_at=end_time,
                result=result_data,
                lease_owner=None,
                lease_expires_at=None,
                updated_at=end_time,
            )
        )
        res = await db.execute(update_stmt)
        if res.rowcount == 0:
            await db.rollback()
            raise StaleWorkerError(f"Worker {worker_id} lost lease on task {task.id}")

        # Update attempt record
        attempt_update = (
            update(TaskAttempt)
            .where(TaskAttempt.task_id == task.id, TaskAttempt.attempt_number == task.attempt_count)
            .values(
                status=TaskStatus.SUCCEEDED,
                completed_at=end_time,
                duration_ms=duration_ms,
            )
        )
        await db.execute(attempt_update)

        await record_audit_event(
            session=db,
            action_type="AGENT_TASK_SUCCEEDED",
            resource_type="TASK",
            resource_id=str(task.id),
            user_id=envelope.sender_id,
            ip_address=client_ip,
            payload=result_data,
        )

        # Autonomous turn chaining: enqueue next turn if autonomous flag is set and < max_agent_turns - 1 turns completed
        is_autonomous = bool(task.payload and task.payload.get("autonomous"))
        max_agent_turns = get_max_agent_turns()
        if is_autonomous and msg_dto.turn_index < (max_agent_turns - 1):
            next_turn = msg_dto.turn_index + 1
            next_key = f"agent-dialogue-{conv.id}-turn-{next_turn}"
            # Paced 6-second interval between turns for realistic live representative dialogue (0s in test mode)
            is_test_env = bool(os.getenv("PYTEST_CURRENT_TEST")) or settings.is_test()
            turn_delay = 0 if is_test_env else 6
            await AgentTaskService.create_agent_dialogue_task(
                db=db,
                conversation_id=conv.id,
                initiator_id=initiator.id,
                target_id=target.id,
                turn_index=next_turn,
                idempotency_key=next_key,
                scheduled_delay_seconds=turn_delay,
                commit=False,
                payload_extra={"autonomous": True},
            )
            logger.info("Enqueued next autonomous turn %s with %ss delay for conversation %s", next_turn, turn_delay, conv.id)

        # ATOMIC COMMIT: Message, Task SUCCEEDED, TaskAttempt SUCCEEDED, and next turn task (if any)
        await db.commit()
        logger.info("Task %s completed SUCCEEDED by worker %s in %sms", task.id, worker_id, duration_ms)

        # STRICT PERSIST-BEFORE-PUBLISH: Broadcast WebSocket event ONLY after database commit succeeds
        event_payload = {
            "event": "message:new",
            "data": {
                "id": str(msg_dto.id),
                "conversation_id": str(msg_dto.conversation_id),
                "sender_id": str(msg_dto.sender_id) if msg_dto.sender_id else None,
                "sender_type": msg_dto.sender_type.value,
                "turn_index": msg_dto.turn_index,
                "content": msg_dto.content,
                "created_at": msg_dto.created_at.isoformat(),
            },
            "conversation_status": conv_detail.status.value,
        }
        await manager.broadcast(conv.id, event_payload)

        return result_data

    @staticmethod
    async def handle_task_failure(
        db: AsyncSession,
        task_id: UUID,
        worker_id: str,
        exc: Exception,
    ) -> None:
        """Handle task execution failure with retry or permanent failure classification."""
        now = datetime.now(timezone.utc)
        error_msg = str(exc)

        # Re-fetch task
        task = await db.get(Task, task_id)
        if not task:
            return

        is_transient = isinstance(exc, TransientTaskError) or "deadlock" in error_msg.lower()
        can_retry = is_transient and (task.attempt_count < task.max_attempts)

        if can_retry:
            # Exponential backoff: 2, 4, 8 seconds
            backoff_sec = 2 ** task.attempt_count
            scheduled_at = now + timedelta(seconds=backoff_sec)
            new_status = TaskStatus.RETRYABLE_FAILURE
            error_cat = getattr(exc, "category", "TRANSIENT_FAILURE")
            logger.warning("Task %s failed transiently (%s). Retrying in %ss (attempt %s/%s)", task_id, error_msg, backoff_sec, task.attempt_count, task.max_attempts)
        else:
            scheduled_at = task.scheduled_at
            new_status = TaskStatus.FAILED
            error_cat = getattr(exc, "category", "PERMANENT_FAILURE")
            if task.attempt_count >= task.max_attempts and is_transient:
                error_cat = "RETRY_EXHAUSTED"
            logger.error("Task %s failed permanently: %s (status=%s)", task_id, error_msg, new_status.value)

        # Update task state
        task.status = new_status
        task.scheduled_at = scheduled_at
        task.lease_owner = None
        task.lease_expires_at = None
        task.error_category = error_cat
        task.error_detail = error_msg[:1000]
        task.updated_at = now
        if new_status == TaskStatus.FAILED:
            task.completed_at = now

        # Update attempt log
        attempt_update = (
            update(TaskAttempt)
            .where(TaskAttempt.task_id == task.id, TaskAttempt.attempt_number == task.attempt_count)
            .values(
                status=new_status,
                completed_at=now,
                error_category=error_cat,
                error_detail=error_msg[:1000],
            )
        )
        await db.execute(attempt_update)
        await db.commit()

    @staticmethod
    async def cancel_task(
        db: AsyncSession,
        task_id: UUID,
        reason: str = "User cancelled",
    ) -> bool:
        """Cancel a pending or retryable task."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Task)
            .where(Task.id == task_id, Task.status.in_([TaskStatus.PENDING, TaskStatus.RETRYABLE_FAILURE]))
            .values(
                status=TaskStatus.CANCELLED,
                completed_at=now,
                error_category="USER_CANCELLED",
                error_detail=reason,
                updated_at=now,
            )
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount > 0


class AgentWorker:
    """Runnable worker process loop for executing background tasks with recovery and shutdown control."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        lease_duration: timedelta = timedelta(seconds=30),
        poll_interval: float = 1.0,
    ):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.lease_duration = lease_duration
        self.poll_interval = poll_interval
        self._running = False

    async def run_once(self, db: AsyncSession) -> bool:
        """Attempt to claim and process a single task. Returns True if task processed, False if idle."""
        task = await AgentTaskService.claim_next_task(
            db=db,
            worker_id=self.worker_id,
            lease_duration=self.lease_duration,
        )
        if not task:
            return False

        try:
            await AgentTaskService.execute_task(
                db=db,
                task=task,
                worker_id=self.worker_id,
            )
            return True
        except Exception as exc:
            await AgentTaskService.handle_task_failure(
                db=db,
                task_id=task.id,
                worker_id=self.worker_id,
                exc=exc,
            )
            return True

    def stop(self) -> None:
        """Signal worker to stop gracefully."""
        self._running = False

    async def run_forever(self, session_factory=None) -> None:
        """Continuously poll queue and process tasks with backoff on idle/error and graceful shutdown."""
        self._running = True
        logger.info("AgentWorker [%s] started background polling (poll_interval=%ss)", self.worker_id, self.poll_interval)
        if session_factory is None:
            session_factory = db_manager.session_factory

        while self._running:
            try:
                async with session_factory() as db:
                    processed = await self.run_once(db)
                    if not processed:
                        await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("AgentWorker [%s] received cancellation signal", self.worker_id)
                self._running = False
                break
            except Exception as exc:
                logger.warning("AgentWorker [%s] unexpected error in polling loop: %s", self.worker_id, exc)
                await asyncio.sleep(min(self.poll_interval * 2, 5.0))

        logger.info("AgentWorker [%s] stopped cleanly", self.worker_id)


async def _run_worker_cli() -> None:
    """CLI entry point for running a dedicated worker process."""
    from app.core.config import get_settings
    settings = get_settings()
    db_manager._settings = settings
    db_manager.initialize()
    worker = AgentWorker(poll_interval=settings.AGENT_WORKER_POLL_INTERVAL)
    try:
        await worker.run_forever()
    except (KeyboardInterrupt, SystemExit):
        worker.stop()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(_run_worker_cli())
