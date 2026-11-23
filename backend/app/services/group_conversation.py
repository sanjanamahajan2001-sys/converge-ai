"""Group Conversation domain service governing multi-party circle lifecycle and turns."""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Set
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.conversation import MessageSenderType
from app.db.models.group_conversation import (
    GroupConversation,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupStatus,
)
from app.db.models.user import User
from app.schemas.group_conversation import (
    GroupConversationCreate,
    GroupConversationDetailResponse,
    GroupConversationResponse,
    GroupMemberSummary,
    GroupMessageCreate,
    GroupMessageResponse,
    GroupRoleEnum,
    GroupStatusEnum,
)

logger = logging.getLogger(__name__)

# Constants
MAX_ACTIVE_CIRCLES_PER_USER = 3
MIN_PEERS = 2
MAX_PEERS = 5


class GroupConversationService:
    """Encapsulates group conversation lifecycle, quota, dynamic limits, and messages."""

    @staticmethod
    def calculate_max_turns(total_participants: int) -> int:
        """Calculate dynamic participant-scaled max turns: 30 + 5 * (N - 2), clamped [35, 50]."""
        base = 30 + 5 * (total_participants - 2)
        return max(35, min(50, base))

    @classmethod
    async def create_circle(
        cls,
        db: AsyncSession,
        host_id: UUID,
        payload: GroupConversationCreate,
    ) -> GroupConversationDetailResponse:
        """Validate participants, check quotas, enforce limits, and persist a new circle."""
        # 1. Ensure host is not included in peer member_ids
        if host_id in payload.member_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host cannot be listed in peer member_ids.",
            )

        # 2. Check peer count bounds (2 to 4 peers -> 3 to 5 total participants)
        peer_count = len(payload.member_ids)
        if peer_count < MIN_PEERS or peer_count > MAX_PEERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Thematic Circles require between {MIN_PEERS} and {MAX_PEERS} invited peers (3 to 6 total members).",
            )

        # 3. Check active circle quota for host
        host_active_count = await cls._count_active_circles_for_user(db, host_id)
        if host_active_count >= MAX_ACTIVE_CIRCLES_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"You have reached the maximum quota of {MAX_ACTIVE_CIRCLES_PER_USER} active networking circles.",
            )

        # 4. Verify all peer users exist and are active
        all_user_ids = [host_id] + payload.member_ids
        user_stmt = select(User).where(User.id.in_(all_user_ids))
        res = await db.execute(user_stmt)
        found_users = {u.id: u for u in res.scalars().all()}

        if len(found_users) != len(all_user_ids):
            missing = set(all_user_ids) - set(found_users.keys())
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"One or more selected participants could not be found: {list(missing)}",
            )

        for uid, u in found_users.items():
            if not u.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Participant {u.username} is currently deactivated.",
                )

        # 5. Check duplicate active circle with the exact same set of participants
        has_dup = await cls._check_duplicate_active_circle(db, set(all_user_ids))
        if has_dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active Networking Circle with this exact combination of delegates already exists.",
            )

        # 6. Calculate dynamic max turns: 20 + 5 * (N - 2)
        total_members = len(all_user_ids)
        max_turns = cls.calculate_max_turns(total_members)

        # 7. Persist Group Conversation
        group = GroupConversation(
            title=payload.title.strip(),
            topic_context=payload.topic_context.strip(),
            host_id=host_id,
            status=GroupStatus.ACTIVE,
            max_turns=max_turns,
            current_turn=0,
        )
        db.add(group)
        await db.flush()

        # 8. Persist Group Members (Host as HOST, peers as MEMBER)
        members: List[GroupMember] = []
        host_member = GroupMember(
            group_id=group.id,
            user_id=host_id,
            role=GroupRole.HOST,
        )
        members.append(host_member)

        for peer_id in payload.member_ids:
            m = GroupMember(
                group_id=group.id,
                user_id=peer_id,
                role=GroupRole.MEMBER,
            )
            members.append(m)

        db.add_all(members)

        # 9. Initial System Kickoff Message
        system_msg = GroupMessage(
            group_id=group.id,
            sender_id=None,
            sender_type=MessageSenderType.SYSTEM,
            turn_index=0,
            content=f"Thematic Networking Circle '{group.title}' initiated with {total_members} delegates. Discussion limit: {max_turns} turns.",
            message_type="SYSTEM",
        )
        db.add(system_msg)
        group.current_turn = 1

        circle_id = group.id
        await db.commit()

        # 10. Trigger Grounded (N+1) Virtual Roundtable AI Representative Introductions
        try:
            from app.services.group_roundtable_agent import VirtualRoundtableEngine
            await VirtualRoundtableEngine.execute_full_roundtable(db, circle_id)
        except Exception as e:
            logger.error("Failed to execute Virtual Roundtable AI introductions for circle %s: %s", circle_id, e)

        return await cls.get_circle_detail(db, circle_id, host_id)

    @classmethod
    async def get_user_circles(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> List[GroupConversationResponse]:
        """Fetch all networking circles the user belongs to, ordered by updated_at desc."""
        stmt = (
            select(GroupConversation)
            .join(GroupMember, GroupMember.group_id == GroupConversation.id)
            .options(
                selectinload(GroupConversation.host),
                selectinload(GroupConversation.members).selectinload(GroupMember.user),
                selectinload(GroupConversation.messages),
            )
            .where(GroupMember.user_id == user_id)
            .order_by(GroupConversation.updated_at.desc())
        )
        res = await db.execute(stmt)
        groups = res.scalars().all()
        return [cls._format_group_summary(g) for g in groups]

    @classmethod
    async def get_circle_detail(
        cls,
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupConversationDetailResponse:
        """Fetch full group conversation record with member authorization check."""
        stmt = (
            select(GroupConversation)
            .options(
                selectinload(GroupConversation.host),
                selectinload(GroupConversation.members).selectinload(GroupMember.user),
                selectinload(GroupConversation.messages).selectinload(GroupMessage.sender),
            )
            .where(GroupConversation.id == group_id)
            .execution_options(populate_existing=True)
        )
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Networking Circle not found.",
            )

        member_ids = {m.user_id for m in group.members}
        if user_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this Networking Circle.",
            )

        return cls._format_group_detail(group)

    @classmethod
    async def post_message(
        cls,
        db: AsyncSession,
        group_id: UUID,
        sender_id: UUID,
        payload: GroupMessageCreate,
    ) -> GroupMessageResponse:
        """Append a human message turn, enforcing member authorization, active state, and turn limits."""
        stmt = (
            select(GroupConversation)
            .options(
                selectinload(GroupConversation.members),
                selectinload(GroupConversation.messages),
            )
            .where(GroupConversation.id == group_id)
        )
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Networking Circle not found.",
            )

        # 1. Authorization check
        member = next((m for m in group.members if m.user_id == sender_id), None)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this Networking Circle.",
            )

        # 2. Status check
        if group.status != GroupStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot post to circle in status '{group.status.value}'.",
            )

        # 3. AI Introduction Lockout Check: Enforce 10-turn AI representative discussion completion before human chat
        total_ai_turns = 10
        if group.current_turn <= total_ai_turns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI Representatives are currently discussing parameters (Turn {group.current_turn} of {total_ai_turns}). Human messaging opens after alignment completes.",
            )

        # 4. Max turn limit check
        if group.current_turn >= group.max_turns:
            group.status = GroupStatus.COMPLETED
            group.concluded_at = datetime.now(timezone.utc)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conversation limit reached ({group.max_turns}/{group.max_turns} turns). Circle is concluded.",
            )

        # 4. Create and persist message
        next_turn = group.current_turn
        msg = GroupMessage(
            group_id=group.id,
            sender_id=sender_id,
            sender_type=MessageSenderType.PARTICIPANT,
            turn_index=next_turn,
            content=payload.content.strip(),
            message_type=payload.message_type or "TEXT",
        )
        db.add(msg)

        group.current_turn = next_turn + 1
        group.updated_at = datetime.now(timezone.utc)

        # 5. Check if limit reached after this turn
        if group.current_turn >= group.max_turns:
            group.status = GroupStatus.COMPLETED
            group.concluded_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(msg)

        # Query sender info for clean response
        sender = (await db.execute(select(User).where(User.id == sender_id))).scalar_one()

        return GroupMessageResponse(
            id=msg.id,
            group_id=msg.group_id,
            sender_id=msg.sender_id,
            sender_username=sender.username,
            sender_full_name=sender.full_name,
            sender_type=msg.sender_type,
            turn_index=msg.turn_index,
            content=msg.content,
            message_type=msg.message_type,
            created_at=msg.created_at,
        )

    @classmethod
    async def get_circle_summary_by_id(
        cls,
        db: AsyncSession,
        group_id: UUID,
    ) -> GroupConversationResponse:
        """Fetch fresh group record for summary serialization."""
        stmt = (
            select(GroupConversation)
            .options(
                selectinload(GroupConversation.host),
                selectinload(GroupConversation.members).selectinload(GroupMember.user),
                selectinload(GroupConversation.messages),
            )
            .where(GroupConversation.id == group_id)
        )
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")
        return cls._format_group_summary(group)

    @classmethod
    async def leave_circle(
        cls,
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupConversationResponse:
        """Process member voluntary exit from a circle."""
        stmt = (
            select(GroupConversation)
            .options(
                selectinload(GroupConversation.members).selectinload(GroupMember.user),
                selectinload(GroupConversation.messages),
                selectinload(GroupConversation.host),
            )
            .where(GroupConversation.id == group_id)
        )
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()

        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")

        member = next((m for m in group.members if m.user_id == user_id), None)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this circle.")

        leaving_user = member.user

        # Remove member
        await db.delete(member)
        await db.commit()

        # Reload members count
        remaining_members = [m for m in group.members if m.user_id != user_id]

        # Post system message
        sys_msg = GroupMessage(
            group_id=group.id,
            sender_id=None,
            sender_type=MessageSenderType.SYSTEM,
            turn_index=group.current_turn,
            content=f"{leaving_user.full_name} left the Networking Circle.",
            message_type="SYSTEM",
        )
        db.add(sys_msg)
        group.current_turn += 1

        # If less than 2 members remain or host left, conclude circle
        if len(remaining_members) < 2 or user_id == group.host_id:
            group.status = GroupStatus.COMPLETED
            group.concluded_at = datetime.now(timezone.utc)

        await db.commit()
        db.expire_all()

        # Re-query fresh group summary with eager relationships loaded
        return await cls.get_circle_summary_by_id(db, group_id)

    @classmethod
    async def close_circle(
        cls,
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupConversationResponse:
        """Process host explicit closing/conclusion of a circle."""
        stmt = (
            select(GroupConversation)
            .options(
                selectinload(GroupConversation.members).selectinload(GroupMember.user),
                selectinload(GroupConversation.messages),
                selectinload(GroupConversation.host),
            )
            .where(GroupConversation.id == group_id)
        )
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()

        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")

        if group.host_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the circle host can close this circle.")

        if group.status != GroupStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Circle cannot be closed because its status is already {group.status.value}."
            )

        group.status = GroupStatus.COMPLETED
        group.concluded_at = datetime.now(timezone.utc)

        host_name = group.host.full_name if group.host else "Host"
        sys_msg = GroupMessage(
            group_id=group.id,
            sender_id=None,
            sender_type=MessageSenderType.SYSTEM,
            turn_index=group.current_turn,
            content=f"Host {host_name} has concluded the Thematic Networking Circle.",
            message_type="SYSTEM",
        )
        db.add(sys_msg)
        group.current_turn += 1

        await db.commit()
        db.expire_all()

        return await cls.get_circle_summary_by_id(db, group_id)

    @classmethod
    async def delete_circle(
        cls,
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> None:
        """Process host permanent deletion/disbandment of a circle."""
        stmt = select(GroupConversation).where(GroupConversation.id == group_id)
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()

        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found.")

        if group.host_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the circle host can delete this circle.")

        await db.delete(group)
        await db.commit()

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    @staticmethod
    async def _count_active_circles_for_user(db: AsyncSession, user_id: UUID) -> int:
        stmt = (
            select(func.count(GroupConversation.id))
            .join(GroupMember, GroupMember.group_id == GroupConversation.id)
            .where(
                GroupMember.user_id == user_id,
                GroupConversation.status == GroupStatus.ACTIVE,
            )
        )
        res = await db.execute(stmt)
        return res.scalar() or 0

    @staticmethod
    async def _check_duplicate_active_circle(db: AsyncSession, user_ids: Set[UUID]) -> bool:
        """Check if any active circle has the exact identical set of participant user_ids."""
        # Find all active circles
        stmt = (
            select(GroupConversation.id)
            .where(GroupConversation.status == GroupStatus.ACTIVE)
        )
        res = await db.execute(stmt)
        active_ids = res.scalars().all()

        for gid in active_ids:
            m_stmt = select(GroupMember.user_id).where(GroupMember.group_id == gid)
            m_res = await db.execute(m_stmt)
            existing_set = set(m_res.scalars().all())
            if existing_set == user_ids:
                return True
        return False

    @classmethod
    def _format_group_summary(cls, g: GroupConversation) -> GroupConversationResponse:
        members = [
            GroupMemberSummary(
                user_id=m.user_id,
                username=m.user.username if m.user else "user",
                full_name=m.user.full_name if m.user else "User",
                company_name=m.user.company_name if m.user else None,
                job_title=m.user.job_title if m.user else None,
                role=GroupRoleEnum(m.role.value),
                joined_at=m.joined_at,
                last_read_turn=m.last_read_turn,
            )
            for m in g.members
        ]

        last_msg = None
        if g.messages:
            lm = g.messages[-1]
            last_msg = GroupMessageResponse(
                id=lm.id,
                group_id=lm.group_id,
                sender_id=lm.sender_id,
                sender_type=lm.sender_type,
                turn_index=lm.turn_index,
                content=lm.content,
                message_type=lm.message_type,
                created_at=lm.created_at,
            )

        return GroupConversationResponse(
            id=g.id,
            title=g.title,
            topic_context=g.topic_context,
            host_id=g.host_id,
            host_name=g.host.full_name if g.host else None,
            status=GroupStatusEnum(g.status.value),
            max_turns=g.max_turns,
            current_turn=g.current_turn,
            ai_turns_budget=10,
            created_at=g.created_at,
            updated_at=g.updated_at,
            concluded_at=g.concluded_at,
            members_count=len(members),
            members=members,
            last_message=last_msg,
        )

    @classmethod
    def _format_group_detail(cls, g: GroupConversation) -> GroupConversationDetailResponse:
        summary = cls._format_group_summary(g)
        user_map = {m.user_id: m.user for m in g.members if m.user}
        if g.host:
            user_map[g.host_id] = g.host

        messages = []
        for m in (g.messages or []):
            sender_user = user_map.get(m.sender_id) if m.sender_id else None
            messages.append(
                GroupMessageResponse(
                    id=m.id,
                    group_id=m.group_id,
                    sender_id=m.sender_id,
                    sender_username=sender_user.username if sender_user else None,
                    sender_full_name=sender_user.full_name if sender_user else None,
                    sender_type=m.sender_type,
                    turn_index=m.turn_index,
                    content=m.content,
                    message_type=m.message_type,
                    created_at=m.created_at,
                )
            )

        return GroupConversationDetailResponse(
            **summary.model_dump(),
            messages=messages,
        )
