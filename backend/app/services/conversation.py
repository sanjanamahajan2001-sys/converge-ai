"""Domain services and state machine for Conversation & Persistent Messaging (P5-WS2, GAP-06)."""

import enum
import os
import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import record_audit_event
from app.core.config import get_settings
from app.db.models.activity import UserActivityEvent
from app.db.models.business import ConversationBusinessContext
from app.db.models.conversation import (
    Conversation,
    ConversationOutcome,
    ConversationStatus,
    Message,
    MessageSenderType,
)
from app.db.models.profile import AvailabilityStatus, ParticipantProfile
from app.db.models.user import User
from app.schemas.conversation import (
    ConversationActionRequest,
    ConversationBusinessContextCreate,
    ConversationBusinessContextResponse,
    ConversationDetailResponse,
    ConversationOutcomeEnum,
    ConversationResponse,
    ConversationStatusEnum,
    MessageResponse,
    MessageSenderTypeEnum,
)
from app.services.matching import QuotaAndCooldownService

logger = logging.getLogger(__name__)
quota_service = QuotaAndCooldownService()


def _format_conversation_response(
    conv: Conversation,
    current_user_id: UUID,
    biz_ctx: Optional[ConversationBusinessContext] = None,
) -> ConversationResponse:
    """Format a Conversation model into a user-specific ConversationResponse DTO."""
    other_user = conv.target if conv.initiator_id == current_user_id else conv.initiator
    other_name = other_user.full_name if other_user else None
    other_id = other_user.id if other_user else None

    last_msg = None
    msg_count = len(conv.messages) if conv.messages else 0
    if conv.messages:
        sorted_msgs = sorted(conv.messages, key=lambda m: m.turn_index)
        latest = sorted_msgs[-1]
        last_msg = MessageResponse(
            id=latest.id,
            conversation_id=latest.conversation_id,
            sender_id=latest.sender_id,
            sender_type=MessageSenderTypeEnum(latest.sender_type.value),
            turn_index=latest.turn_index,
            content=latest.content,
            message_type=getattr(latest, "message_type", "TEXT") or "TEXT",
            location_payload=getattr(latest, "location_payload", None),
            created_at=latest.created_at,
        )

    return ConversationResponse(
        id=conv.id,
        initiator_id=conv.initiator_id,
        target_id=conv.target_id,
        status=ConversationStatusEnum(conv.status.value),
        match_score=float(conv.match_score) if conv.match_score is not None else None,
        terminal_outcome=ConversationOutcomeEnum(conv.terminal_outcome.value) if conv.terminal_outcome else None,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        concluded_at=conv.concluded_at,
        other_participant_id=other_id,
        other_participant_name=other_name,
        last_message=last_msg,
        message_count=msg_count,
        has_business_context=biz_ctx is not None,
        business_inquiry_type=biz_ctx.inquiry_type if biz_ctx else None,
    )



def get_max_agent_turns() -> int:
    env_val = os.getenv("MAX_AGENT_TURNS")
    if env_val:
        return int(env_val)
    if bool(os.getenv("PYTEST_CURRENT_TEST")):
        return 5
    settings = get_settings()
    if settings.is_test():
        return 5
    return 10

class ConversationService:
    """Encapsulates conversation lifecycle, atomic quota checking, cooldowns, and message turns."""

    @staticmethod
    async def get_participant_conversations(
        db: AsyncSession,
        user_id: UUID,
    ) -> List[ConversationResponse]:
        """Fetch all conversations for the authenticated user, ordered by latest activity."""
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.initiator),
                selectinload(Conversation.target),
                selectinload(Conversation.messages),
            )
            .where(
                or_(
                    Conversation.initiator_id == user_id,
                    Conversation.target_id == user_id,
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        conv_ids = [c.id for c in conversations]
        biz_map: Dict[UUID, ConversationBusinessContext] = {}
        if conv_ids:
            biz_stmt = select(ConversationBusinessContext).where(
                ConversationBusinessContext.conversation_id.in_(conv_ids)
            )
            biz_res = await db.execute(biz_stmt)
            for b in biz_res.scalars().all():
                biz_map[b.conversation_id] = b

        return [_format_conversation_response(c, user_id, biz_map.get(c.id)) for c in conversations]

    @staticmethod
    async def get_conversation_by_id(
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
    ) -> ConversationDetailResponse:
        """Fetch a single conversation by ID, enforcing IDOR participant isolation."""
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.initiator),
                selectinload(Conversation.target),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conversation_id)
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        if conv.initiator_id != user_id and conv.target_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a participant in this conversation.",
            )

        # Query commercial business context snapshot if present
        ctx_stmt = select(ConversationBusinessContext).where(
            ConversationBusinessContext.conversation_id == conversation_id
        )
        ctx_res = await db.execute(ctx_stmt)
        biz_ctx = ctx_res.scalar_one_or_none()
        biz_ctx_resp = None
        if biz_ctx:
            biz_ctx_resp = ConversationBusinessContextResponse.model_validate(biz_ctx)

        base_resp = _format_conversation_response(conv, user_id, biz_ctx)
        messages_resp = [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                sender_id=m.sender_id,
                sender_type=MessageSenderTypeEnum(m.sender_type.value),
                turn_index=m.turn_index,
                content=m.content,
                message_type=getattr(m, "message_type", "TEXT") or "TEXT",
                location_payload=getattr(m, "location_payload", None),
                created_at=m.created_at,
            )
            for m in sorted(conv.messages, key=lambda x: x.turn_index)
        ]

        other_id = conv.target_id if conv.initiator_id == user_id else conv.initiator_id
        other_mood = None
        # Privacy policy: mood preference is only shared with accepted conversation partners (ACTIVE or COMPLETED)
        if conv.status in (ConversationStatus.ACTIVE, ConversationStatus.COMPLETED):
            prof_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == other_id)
            other_prof = (await db.execute(prof_stmt)).scalar_one_or_none()
            other_mood = other_prof.active_mood if other_prof else None

        return ConversationDetailResponse(
            **base_resp.model_dump(),
            messages=messages_resp,
            other_participant_mood=other_mood,
            business_context=biz_ctx_resp,
        )

    @staticmethod
    async def get_conversation_business_context(
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Optional[ConversationBusinessContextResponse]:
        """Fetch commercial business context snapshot with participant IDOR authorization."""
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await db.execute(conv_stmt)).scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        if conv.initiator_id != user_id and conv.target_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a participant in this conversation.",
            )
        ctx_stmt = select(ConversationBusinessContext).where(
            ConversationBusinessContext.conversation_id == conversation_id
        )
        ctx = (await db.execute(ctx_stmt)).scalar_one_or_none()
        if not ctx:
            return None
        return ConversationBusinessContextResponse.model_validate(ctx)

    @staticmethod
    async def initiate_conversation(
        db: AsyncSession,
        initiator: User,
        target_id: UUID,
        client_ip: str,
        business_context: Optional[ConversationBusinessContextCreate] = None,
        auto_start: bool = False,
    ) -> ConversationDetailResponse:
        """Create a new 1-to-1 conversation with deterministic locking, quota, and cooldown enforcement."""
        if initiator.id == target_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot initiate a conversation with yourself.",
            )

        # 1. Deterministic participant row locking (order by ID to prevent deadlocks)
        ordered_ids = sorted([initiator.id, target_id])
        lock_stmt = (
            select(User.id)
            .where(User.id.in_(ordered_ids))
            .order_by(User.id)
            .with_for_update()
        )
        lock_res = await db.execute(lock_stmt)
        locked_user_ids = lock_res.scalars().all()

        if len(locked_user_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target participant does not exist.",
            )

        # 2. Verify target profile exists and is eligible
        target_profile_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == target_id)
        target_profile_res = await db.execute(target_profile_stmt)
        target_profile = target_profile_res.scalar_one_or_none()
        if not target_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target participant profile has not been initialized.",
            )

        if not target_profile.allow_agent_matching:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Target participant has not consented to agent networking matching.",
            )

        if auto_start and not getattr(target_profile, "allow_agent_dm_initiation", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Target participant has disabled AI Representative 1-on-1 DM initiation in their profile settings.",
            )

        if target_profile.availability in (AvailabilityStatus.DO_NOT_DISTURB, AvailabilityStatus.OFFLINE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Target participant is currently unavailable ({target_profile.availability.value}).",
            )

        # Verify initiator profile exists and is eligible
        initiator_profile_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == initiator.id)
        initiator_profile_res = await db.execute(initiator_profile_stmt)
        initiator_profile = initiator_profile_res.scalar_one_or_none()
        if not initiator_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Your participant profile has not been initialized. Please complete onboarding first.",
            )

        if not initiator_profile.allow_agent_matching:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have disabled networking matching consent in your profile.",
            )

        if auto_start and not getattr(initiator_profile, "allow_agent_dm_initiation", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have disabled AI Representative 1-on-1 DM initiation in your profile settings.",
            )

        if initiator_profile.availability in (AvailabilityStatus.DO_NOT_DISTURB, AvailabilityStatus.OFFLINE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot initiate conversations while your status is {initiator_profile.availability.value}.",
            )

        # 3. Check for existing active or invited conversation between this pair
        active_pair_stmt = select(Conversation).where(
            or_(
                (Conversation.initiator_id == initiator.id) & (Conversation.target_id == target_id),
                (Conversation.initiator_id == target_id) & (Conversation.target_id == initiator.id),
            ),
            Conversation.status.in_([ConversationStatus.INVITED, ConversationStatus.ACTIVE]),
        )
        active_pair_res = await db.execute(active_pair_stmt)
        existing_conv = active_pair_res.scalar_one_or_none()
        if existing_conv:
            if auto_start:
                if existing_conv.status == ConversationStatus.INVITED:
                    existing_conv.status = ConversationStatus.ACTIVE
                    await db.flush()
                return await ConversationService.get_conversation_detail(db, existing_conv.id, initiator.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active or pending conversation already exists with this participant.",
            )

        # 4. Check pair cooldown from last concluded conversation
        last_concluded_stmt = (
            select(Conversation)
            .where(
                or_(
                    (Conversation.initiator_id == initiator.id) & (Conversation.target_id == target_id),
                    (Conversation.initiator_id == target_id) & (Conversation.target_id == initiator.id),
                ),
                Conversation.status.in_([
                    ConversationStatus.COMPLETED,
                    ConversationStatus.CANCELLED,
                    ConversationStatus.EXPIRED,
                ]),
            )
            .order_by(Conversation.concluded_at.desc())
            .limit(1)
        )
        last_conv = await db.scalar(last_concluded_stmt)
        if last_conv and last_conv.terminal_outcome and last_conv.concluded_at:
            in_cooldown, remaining = quota_service.evaluate_pair_cooldown(
                last_interaction_outcome=last_conv.terminal_outcome.value,
                last_interaction_time=last_conv.concluded_at,
            )
            if in_cooldown and remaining:
                hours = remaining.total_seconds() / 3600.0
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot initiate conversation: Pair is in cooldown for another {hours:.1f} hours.",
                )

        # 5. Check active conversation quota for initiator (max 3)
        initiator_active_stmt = select(func.count(Conversation.id)).where(
            or_(
                Conversation.initiator_id == initiator.id,
                Conversation.target_id == initiator.id,
            ),
            Conversation.status.in_([ConversationStatus.INVITED, ConversationStatus.ACTIVE]),
        )
        initiator_active_count = await db.scalar(initiator_active_stmt) or 0
        if quota_service.is_quota_exceeded(initiator_active_count):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You have reached your maximum concurrent active conversation quota (3). Conclude or cancel an existing conversation first.",
            )

        # 6. Check active conversation quota for target (max 3)
        target_active_stmt = select(func.count(Conversation.id)).where(
            or_(
                Conversation.initiator_id == target_id,
                Conversation.target_id == target_id,
            ),
            Conversation.status.in_([ConversationStatus.INVITED, ConversationStatus.ACTIVE]),
        )
        target_active_count = await db.scalar(target_active_stmt) or 0
        if quota_service.is_quota_exceeded(target_active_count):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Target participant has reached their maximum concurrent active conversation quota.",
            )

        # 7. Create conversation in ACTIVE state if auto_start, otherwise INVITED
        new_conv = Conversation(
            initiator_id=initiator.id,
            target_id=target_id,
            status=ConversationStatus.ACTIVE if auto_start else ConversationStatus.INVITED,
        )
        db.add(new_conv)
        await db.flush()

        if auto_start:
            greeting = f"Hello {initiator.full_name}! Connected directly from the Networking Lounge. Let's discuss collaboration and initiatives here."
            pm = Message(
                conversation_id=new_conv.id,
                sender_id=target_id,
                sender_type=MessageSenderType.AGENT,
                content=greeting,
                turn_index=0,
            )
            db.add(pm)
            await db.flush()

        # 8. Attach immutable Commercial Business Context Snapshot if provided (Phase 4 / GAP-06)
        if business_context:
            # Enforce Buyer Budget Privacy: target price indication is ONLY disclosed if explicitly opted in
            disclosed_price = (
                business_context.target_price_indication
                if business_context.is_budget_public
                else None
            )
            canonical = (
                f"{business_context.inquiry_type}|{business_context.product_name}|"
                f"{business_context.product_code or ''}|{business_context.grade_code or ''}|{business_context.service_code or ''}|"
                f"{business_context.quantity or ''}|{business_context.unit or ''}|{business_context.delivery_location or ''}|"
                f"{business_context.timeline_days or ''}|{disclosed_price or ''}|{business_context.urgency or ''}"
            )
            snapshot_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

            new_ctx = ConversationBusinessContext(
                conversation_id=new_conv.id,
                version=1,
                inquiry_type=business_context.inquiry_type,
                product_name=business_context.product_name,
                product_code=business_context.product_code,
                grade_code=business_context.grade_code,
                service_code=business_context.service_code,
                quantity=Decimal(str(business_context.quantity)) if business_context.quantity is not None else None,
                unit=business_context.unit,
                delivery_location=business_context.delivery_location,
                timeline_days=business_context.timeline_days,
                target_price_indication=Decimal(str(disclosed_price)) if disclosed_price is not None else None,
                urgency=business_context.urgency,
                inquiry_notes=business_context.inquiry_notes,
                snapshot_hash=snapshot_hash,
            )
            db.add(new_ctx)
            await db.flush()

        await record_audit_event(
            session=db,
            action_type="CONVERSATION_INITIATED",
            resource_type="CONVERSATION",
            resource_id=str(new_conv.id),
            user_id=initiator.id,
            actor_username=initiator.username,
            ip_address=client_ip,
            payload={
                "target_id": str(target_id),
                "status": "INVITED",
                "has_business_context": business_context is not None,
                "inquiry_type": business_context.inquiry_type if business_context else None,
            },
        )
        db.add(
            UserActivityEvent(
                user_id=initiator.id,
                event_type="FEATURE_CLICK",
                feature_name="START_CONVERSATION",
                target_resource_id=str(target_id),
                details={
                    "conversation_id": str(new_conv.id),
                    "status": "INVITED",
                    "has_business_context": business_context is not None,
                },
            )
        )
        await db.commit()

        # Reload with relations
        return await ConversationService.get_conversation_by_id(db, new_conv.id, initiator.id)

    @staticmethod
    async def update_conversation_status(
        db: AsyncSession,
        conversation_id: UUID,
        current_user_id: UUID,
        client_ip: str,
        action: str,
        outcome: Optional[ConversationOutcomeEnum] = None,
        trigger_agent: Optional[bool] = None,
    ) -> ConversationDetailResponse:
        """Perform validated state transitions (ACCEPT, REJECT, CANCEL, CONCLUDE)."""
        # Lock conversation row
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.initiator),
                selectinload(Conversation.target),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )
        conv = await db.scalar(stmt)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        if conv.initiator_id != current_user_id and conv.target_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a participant in this conversation.",
            )

        now = datetime.now(timezone.utc)
        action_upper = action.upper()

        if action_upper == "ACCEPT":
            if conv.status != ConversationStatus.INVITED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot accept conversation in '{conv.status.value}' status.",
                )
            if conv.initiator_id == current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The initiator cannot accept their own invitation. Only the target participant may accept.",
                )
            conv.status = ConversationStatus.ACTIVE
            conv.updated_at = now

            # Unconditionally launch autonomous agent representative dialogue upon acceptance
            from app.services.agent_worker import AgentTaskService
            await AgentTaskService.create_agent_dialogue_task(
                db=db,
                conversation_id=conv.id,
                initiator_id=conv.initiator_id,
                target_id=conv.target_id,
                turn_index=0,
                idempotency_key=f"agent-dialogue-{conv.id}-turn-0",
                scheduled_delay_seconds=0,
                commit=False,
                payload_extra={"autonomous": True},
            )

            await record_audit_event(
                session=db,
                action_type="CONVERSATION_ACCEPTED",
                resource_type="CONVERSATION",
                resource_id=str(conv.id),
                user_id=current_user_id,
                ip_address=client_ip,
                payload={"initiator_id": str(conv.initiator_id)},
            )

        elif action_upper in ("REJECT", "CANCEL"):
            if conv.status not in (ConversationStatus.INVITED, ConversationStatus.ACTIVE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel/reject conversation in '{conv.status.value}' status.",
                )
            conv.status = ConversationStatus.CANCELLED
            conv.terminal_outcome = ConversationOutcome.CANCELLED
            conv.concluded_at = now
            conv.updated_at = now

            from app.services.agent_worker import AgentTaskService
            await AgentTaskService.cancel_conversation_tasks(
                db=db,
                conversation_id=conv.id,
                reason=f"Conversation transitioned to {conv.status.value}",
            )

            await record_audit_event(
                session=db,
                action_type="CONVERSATION_CANCELLED",
                resource_type="CONVERSATION",
                resource_id=str(conv.id),
                user_id=current_user_id,
                ip_address=client_ip,
                payload={"action": action_upper},
            )

        elif action_upper == "CONCLUDE":
            if conv.status != ConversationStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot conclude conversation in '{conv.status.value}' status. Must be ACTIVE.",
                )
            terminal_outcome = (
                ConversationOutcome(outcome.value)
                if outcome
                else ConversationOutcome.COMPLETED_WITHOUT_PROPOSAL
            )
            conv.status = ConversationStatus.COMPLETED
            conv.terminal_outcome = terminal_outcome
            conv.concluded_at = now
            conv.updated_at = now

            from app.services.agent_worker import AgentTaskService
            await AgentTaskService.cancel_conversation_tasks(
                db=db,
                conversation_id=conv.id,
                reason="Conversation concluded",
            )

            await record_audit_event(
                session=db,
                action_type="CONVERSATION_CONCLUDED",
                resource_type="CONVERSATION",
                resource_id=str(conv.id),
                user_id=current_user_id,
                ip_address=client_ip,
                payload={"outcome": terminal_outcome.value},
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown conversation action '{action}'. Allowed: ACCEPT, REJECT, CANCEL, CONCLUDE.",
            )

        db.add(
            UserActivityEvent(
                user_id=current_user_id,
                event_type="FEATURE_CLICK",
                feature_name=f"CONVERSATION_{action_upper}",
                target_resource_id=str(conv.id),
                details={"action": action_upper},
            )
        )
        await db.commit()
        return await ConversationService.get_conversation_by_id(db, conv.id, current_user_id)

    @staticmethod
    async def trigger_agent_dialogue(
        db: AsyncSession,
        conversation_id: UUID,
        current_user_id: UUID,
        client_ip: str,
    ) -> ConversationDetailResponse:
        """Trigger autonomous virtual representative dialogue for an active conversation."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )
        conv = await db.scalar(stmt)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        if conv.initiator_id != current_user_id and conv.target_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a participant in this conversation.",
            )

        if conv.status != ConversationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot trigger agent dialogue for conversation in '{conv.status.value}' status. Must be ACTIVE.",
            )

        count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        current_turn = await db.scalar(count_stmt) or 0
        max_agent_turns = get_max_agent_turns()
        if current_turn >= max_agent_turns:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Representative exchange complete ({max_agent_turns} turns). Manual chat is active.",
            )
        if current_turn >= 30:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation has reached the maximum turn limit of 30 messages.",
            )

        from app.services.agent_worker import AgentTaskService
        await AgentTaskService.create_agent_dialogue_task(
            db=db,
            conversation_id=conv.id,
            initiator_id=conv.initiator_id,
            target_id=conv.target_id,
            turn_index=current_turn,
            idempotency_key=f"agent-dialogue-{conv.id}-turn-{current_turn}",
            scheduled_delay_seconds=0,
            commit=True,
            payload_extra={"autonomous": True},
        )

        await record_audit_event(
            session=db,
            action_type="AGENT_DIALOGUE_TRIGGERED",
            resource_type="CONVERSATION",
            resource_id=str(conv.id),
            user_id=current_user_id,
            ip_address=client_ip,
            payload={"turn_index": current_turn},
        )

        return await ConversationService.get_conversation_by_id(db, conv.id, current_user_id)

    @staticmethod
    async def append_message(
        db: AsyncSession,
        conversation_id: UUID,
        sender_id: UUID,
        content: str,
        client_ip: str,
        sender_type: MessageSenderType = MessageSenderType.PARTICIPANT,
        commit: bool = True,
        message_type: str = "TEXT",
        location_payload: Optional[dict] = None,
    ) -> Tuple[MessageResponse, ConversationDetailResponse]:
        """Atomically append a message turn, enforcing 20-turn limit and terminal conclusion on turn 19."""
        # 1. Lock conversation row
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.initiator),
                selectinload(Conversation.target),
                selectinload(Conversation.messages),
            )
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )
        conv = await db.scalar(stmt)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        if conv.initiator_id != sender_id and conv.target_id != sender_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a participant in this conversation.",
            )

        if conv.status == ConversationStatus.INVITED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation invitation has not been accepted yet. Messages cannot be sent while INVITED.",
            )

        if conv.status in (ConversationStatus.COMPLETED, ConversationStatus.CANCELLED, ConversationStatus.EXPIRED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot send message: Conversation is already {conv.status.value}.",
            )

        # 2. Determine current turn count
        count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        current_turn = await db.scalar(count_stmt) or 0

        max_agent_turns = get_max_agent_turns()
        if sender_type == MessageSenderType.AGENT and current_turn >= max_agent_turns:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Representative exchange complete ({max_agent_turns} turns). Only human attendee messages are permitted.",
            )

        if current_turn >= 30:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation has reached the maximum turn limit of 30 messages.",
            )

        now = datetime.now(timezone.utc)
        new_msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_type=sender_type,
            turn_index=current_turn,
            content=content,
            message_type=message_type,
            location_payload=location_payload,
            created_at=now,
        )
        db.add(new_msg)
        if conv.messages is not None and new_msg not in conv.messages:
            conv.messages.append(new_msg)

        # 3. If this is the 30th message (index 29), automatically complete conversation atomically
        if current_turn == 29:
            conv.status = ConversationStatus.COMPLETED
            conv.terminal_outcome = ConversationOutcome.COMPLETED_WITHOUT_PROPOSAL
            conv.concluded_at = now
            logger.info("Conversation %s reached 30-message limit, marked COMPLETED.", conv.id)

        conv.updated_at = now
        await db.flush()

        await record_audit_event(
            session=db,
            action_type="MESSAGE_SENT",
            resource_type="MESSAGE",
            resource_id=str(new_msg.id),
            user_id=sender_id,
            ip_address=client_ip,
            payload={"conversation_id": str(conversation_id), "turn_index": current_turn},
        )

        if sender_type == MessageSenderType.PARTICIPANT:
            db.add(
                UserActivityEvent(
                    user_id=sender_id,
                    event_type="FEATURE_CLICK",
                    feature_name="SEND_MESSAGE",
                    target_resource_id=str(conversation_id),
                    details={"turn_index": current_turn, "message_type": message_type},
                )
            )

            # Graceful Human Interruption Handler (Phase 3): If attendee types while automated representative
            # turns are active (< 5), cleanly cancel remaining pending agent tasks and hand over directly.
            if current_turn < get_max_agent_turns():
                from app.services.agent_worker import AgentTaskService
                await AgentTaskService.cancel_conversation_tasks(
                    db=db,
                    conversation_id=conversation_id,
                    reason=f"Human participant {sender_id} took over dialogue on turn {current_turn}. Handing over directly.",
                )
                logger.info(
                    "Human participant %s took over dialogue early on turn %d in conv %s. Cancelled pending agent tasks.",
                    sender_id,
                    current_turn,
                    conversation_id,
                )

        if commit:
            await db.commit()

        msg_dto = MessageResponse(
            id=new_msg.id,
            conversation_id=new_msg.conversation_id,
            sender_id=new_msg.sender_id,
            sender_type=MessageSenderTypeEnum(new_msg.sender_type.value),
            turn_index=new_msg.turn_index,
            content=new_msg.content,
            message_type=getattr(new_msg, "message_type", "TEXT") or "TEXT",
            location_payload=getattr(new_msg, "location_payload", None),
            created_at=new_msg.created_at,
        )

        conv_detail = await ConversationService.get_conversation_by_id(db, conversation_id, sender_id)
        return msg_dto, conv_detail
