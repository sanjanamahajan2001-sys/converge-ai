"""Core Proposal Domain Service (Phase 7 - Subphase 3).

Enforces:
1. Strict Dual-Sided Approval: Both parties must approve the exact same revision.
2. Zero Contact Leakage Invariant: Contact credentials never queried or projected before mutual approval.
3. Concurrency Safety: Atomic row-level locking (SELECT ... FOR UPDATE) on state transitions.
4. Non-Repudiable Attribution & Audit: Proposer, Revision Author, and Approver permanently logged.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, or_, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import event_broker
from app.db.models.conversation import Conversation
from app.db.models.proposal import (
    ApprovalAction,
    CommercialRole,
    Proposal,
    ProposalApproval,
    ProposalContactDisclosure,
    ProposalRevision,
    ProposalStatus,
    ProposalType,
)
from app.db.models.user import User
from app.schemas.proposal import (
    AdminProposalListItem,
    AdminProposalListResponse,
    CounterProposalRequest,
    DisclosedContactCredentials,
    ProposalApprovalRecord,
    ProposalApprovalRequest,
    ProposalCreateRequest,
    ProposalDetailResponse,
    ProposalListItem,
    ProposalPartySummary,
    ProposalRejectionRequest,
    ProposalRevisionResponse,
)

logger = logging.getLogger("converge.services.proposal")


class ProposalService:
    """Domain service managing the complete commercial proposal lifecycle."""

    @staticmethod
    async def create_proposal(
        db: AsyncSession,
        current_user: User,
        payload: ProposalCreateRequest,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Create and submit a formal proposal (Revision 1) to a matched peer."""
        if payload.recipient_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot initiate a commercial proposal to yourself.",
            )

        # Verify recipient existence
        recip_stmt = select(User).where(User.id == payload.recipient_id, User.is_active == True)
        recip_res = await db.execute(recip_stmt)
        recipient = recip_res.scalar_one_or_none()
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target recipient attendee profile not found.",
            )

        # Check for active proposals between this bilateral pair
        active_check_stmt = select(Proposal.id).where(
            or_(
                and_(Proposal.proposer_id == current_user.id, Proposal.recipient_id == recipient.id),
                and_(Proposal.proposer_id == recipient.id, Proposal.recipient_id == current_user.id),
            ),
            Proposal.status.in_([
                ProposalStatus.DRAFT,
                ProposalStatus.PENDING_REVIEW,
                ProposalStatus.REVISED,
            ]),
        )
        active_res = await db.execute(active_check_stmt)
        if active_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active proposal is already in negotiation between you and this delegate. Complete, counter, or withdraw the existing proposal before drafting a new one.",
            )

        # If conversation_id is provided, verify participants
        if payload.conversation_id:
            conv_stmt = select(Conversation).where(Conversation.id == payload.conversation_id)
            conv_res = await db.execute(conv_stmt)
            conversation = conv_res.scalar_one_or_none()
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced conversation not found.",
                )
            if current_user.id not in (conversation.initiator_id, conversation.target_id) or \
               recipient.id not in (conversation.initiator_id, conversation.target_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Delegates are not active participants in the referenced dialogue.",
                )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=payload.validity_days)

        # 1. Instantiate Proposal
        proposal = Proposal(
            conversation_id=payload.conversation_id,
            proposer_id=current_user.id,
            recipient_id=recipient.id,
            proposer_role=payload.proposer_role,
            recipient_role=payload.recipient_role,
            proposal_type=payload.revision.proposal_type,
            status=ProposalStatus.PENDING_REVIEW,
            current_revision_number=1,
            expires_at=expires_at,
        )
        db.add(proposal)
        await db.flush()

        # 2. Instantiate Revision 1
        rev_data = payload.revision
        total_val = rev_data.total_value
        if total_val is None and rev_data.unit_price is not None:
            total_val = rev_data.quantity * rev_data.unit_price

        revision_v1 = ProposalRevision(
            proposal=proposal,
            revision_number=1,
            author_id=current_user.id,
            title=rev_data.title,
            proposal_type=rev_data.proposal_type,
            product_name=rev_data.product_name,
            product_code=rev_data.product_code,
            grade_code=rev_data.grade_code,
            service_code=rev_data.service_code,
            quantity=rev_data.quantity,
            unit=rev_data.unit,
            unit_price=rev_data.unit_price,
            currency=rev_data.currency or "INR",
            total_value=total_val,
            payment_terms=rev_data.payment_terms,
            delivery_location=rev_data.delivery_location,
            incoterm=rev_data.incoterm or "EXW",
            delivery_timeline_days=rev_data.delivery_timeline_days,
            governing_standards=rev_data.governing_standards or [],
            special_conditions=rev_data.special_conditions,
            notes=rev_data.notes,
            revision_summary=rev_data.revision_summary or "Initial proposal submission (Revision V1)",
        )
        db.add(revision_v1)
        await db.flush()

        # 3. Author Auto-Approval for V1
        author_approval = ProposalApproval(
            proposal=proposal,
            revision=revision_v1,
            user_id=current_user.id,
            action=ApprovalAction.APPROVED,
            notes="Author endorsement on initial submission.",
            ip_address=client_ip,
        )
        db.add(author_approval)
        prop_id = proposal.id
        await db.commit()

        # Broadcast SSE event
        event_data = {
            "proposal_id": str(prop_id),
            "conversation_id": str(proposal.conversation_id) if proposal.conversation_id else None,
            "proposer_id": str(current_user.id),
            "recipient_id": str(recipient.id),
            "title": revision_v1.title,
            "product_name": revision_v1.product_name,
            "quantity": float(revision_v1.quantity) if revision_v1.quantity is not None else None,
            "unit": revision_v1.unit,
            "total_value": float(revision_v1.total_value) if revision_v1.total_value is not None else None,
            "currency": revision_v1.currency,
            "status": proposal.status.value,
            "revision_number": 1,
            "actor_id": str(current_user.id),
            "action": "CREATED",
        }
        try:
            await event_broker.publish("proposal:created", event_data)
        except Exception as e:
            logger.warning("Failed to publish proposal:created event: %s", e)

        if proposal.conversation_id:
            try:
                from app.api.routes.conversations import broadcast_conversation_event
                await broadcast_conversation_event(proposal.conversation_id, {
                    "event": "proposal:created",
                    "data": event_data,
                })
            except Exception as e:
                logger.debug("Failed to broadcast proposal:created to conversation: %s", e)

        return await ProposalService.get_proposal(db, prop_id, current_user)

    @staticmethod
    async def list_proposals(
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[ProposalStatus] = None,
        tab: Optional[str] = None,
        conversation_id: Optional[UUID] = None,
    ) -> List[ProposalListItem]:
        """List proposals for the authenticated user with status and tab filters."""
        stmt = (
            select(Proposal)
            .where(
                or_(
                    Proposal.proposer_id == current_user.id,
                    Proposal.recipient_id == current_user.id,
                )
            )
            .options(
                selectinload(Proposal.revisions),
                selectinload(Proposal.proposer),
                selectinload(Proposal.recipient),
            )
            .order_by(Proposal.updated_at.desc())
        )

        if status_filter:
            stmt = stmt.where(Proposal.status == status_filter)

        if conversation_id:
            stmt = stmt.where(Proposal.conversation_id == conversation_id)

        res = await db.execute(stmt)
        proposals = res.scalars().all()

        now = datetime.now(timezone.utc)
        items: List[ProposalListItem] = []

        for p in proposals:
            # Check expiration dynamically
            if p.status in (ProposalStatus.PENDING_REVIEW, ProposalStatus.REVISED) and p.expires_at < now:
                p.status = ProposalStatus.EXPIRED

            user_is_proposer = (p.proposer_id == current_user.id)
            
            # Action required logic:
            # 1. PENDING_REVIEW: Recipient needs to review
            # 2. REVISED: Counterparty to the last revision needs to review
            latest_rev = max(p.revisions, key=lambda r: r.revision_number) if p.revisions else None
            requires_action = False
            if p.status == ProposalStatus.PENDING_REVIEW:
                requires_action = not user_is_proposer
            elif p.status == ProposalStatus.REVISED and latest_rev:
                requires_action = (latest_rev.author_id != current_user.id)

            # Filter by tab if requested
            if tab == "action_required" and not requires_action:
                continue
            elif tab == "approved" and p.status != ProposalStatus.MUTUALLY_APPROVED:
                continue
            elif tab == "archive" and p.status not in (ProposalStatus.REJECTED, ProposalStatus.WITHDRAWN, ProposalStatus.EXPIRED):
                continue

            active_rev = latest_rev or p.revisions[0]

            item = ProposalListItem(
                id=p.id,
                conversation_id=p.conversation_id,
                proposer_id=p.proposer_id,
                proposer_name=p.proposer.full_name,
                proposer_company=p.proposer.company_name,
                proposer_role=p.proposer_role,
                recipient_id=p.recipient_id,
                recipient_name=p.recipient.full_name,
                recipient_company=p.recipient.company_name,
                recipient_role=p.recipient_role,
                proposal_type=p.proposal_type,
                status=p.status,
                current_revision_number=p.current_revision_number,
                current_title=active_rev.title,
                product_name=active_rev.product_name,
                quantity=active_rev.quantity,
                unit=active_rev.unit,
                total_value=active_rev.total_value,
                currency=active_rev.currency,
                expires_at=p.expires_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
                concluded_at=p.concluded_at,
                user_is_proposer=user_is_proposer,
                requires_user_action=requires_action,
                contacts_disclosed=(p.status == ProposalStatus.MUTUALLY_APPROVED),
            )
            items.append(item)

        return items

    @staticmethod
    async def get_proposal(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        is_admin: bool = False,
    ) -> ProposalDetailResponse:
        """Fetch complete proposal detail sheet with revisions, approvals, and gated contacts."""
        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(
                selectinload(Proposal.revisions).selectinload(ProposalRevision.author),
                selectinload(Proposal.approvals).selectinload(ProposalApproval.user),
                selectinload(Proposal.contact_disclosures),
                selectinload(Proposal.proposer),
                selectinload(Proposal.recipient),
            )
        )
        res = await db.execute(stmt)
        proposal = res.scalar_one_or_none()

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found.",
            )

        # IDOR Boundary Check
        if not is_admin and current_user.id not in (proposal.proposer_id, proposal.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found.",
            )

        # Check expiration dynamically
        now = datetime.now(timezone.utc)
        if proposal.status in (ProposalStatus.PENDING_REVIEW, ProposalStatus.REVISED) and proposal.expires_at < now:
            proposal.status = ProposalStatus.EXPIRED
            await db.commit()

        # Sort revisions by revision_number ascending
        sorted_revisions = sorted(proposal.revisions, key=lambda r: r.revision_number)
        active_rev = next(
            (r for r in sorted_revisions if r.revision_number == proposal.current_revision_number),
            sorted_revisions[-1] if sorted_revisions else None,
        )

        if not active_rev:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Proposal has no valid active revision attached.",
            )

        user_is_proposer = (proposal.proposer_id == current_user.id)
        requires_action = False
        if proposal.status == ProposalStatus.PENDING_REVIEW:
            requires_action = not user_is_proposer
        elif proposal.status == ProposalStatus.REVISED and active_rev:
            requires_action = (active_rev.author_id != current_user.id)

        # Build revision responses
        rev_responses: List[ProposalRevisionResponse] = [
            ProposalRevisionResponse(
                id=r.id,
                proposal_id=r.proposal_id,
                revision_number=r.revision_number,
                author_id=r.author_id,
                author_name=r.author.full_name if r.author else None,
                author_company=r.author.company_name if r.author else None,
                title=r.title,
                proposal_type=r.proposal_type,
                product_name=r.product_name,
                product_code=r.product_code,
                grade_code=r.grade_code,
                service_code=r.service_code,
                quantity=r.quantity,
                unit=r.unit,
                unit_price=r.unit_price,
                currency=r.currency,
                total_value=r.total_value,
                payment_terms=r.payment_terms,
                delivery_location=r.delivery_location,
                incoterm=r.incoterm,
                delivery_timeline_days=r.delivery_timeline_days,
                governing_standards=r.governing_standards,
                special_conditions=r.special_conditions,
                notes=r.notes,
                revision_summary=r.revision_summary,
                created_at=r.created_at,
            )
            for r in sorted_revisions
        ]

        active_rev_response = next(
            (r for r in rev_responses if r.revision_number == active_rev.revision_number),
            rev_responses[-1],
        )

        # Build approval records
        sorted_approvals = sorted(proposal.approvals, key=lambda a: a.created_at)
        approval_records: List[ProposalApprovalRecord] = []
        rejection_reason: Optional[str] = None

        for a in sorted_approvals:
            # find revision number for this approval
            rev_num = next((r.revision_number for r in sorted_revisions if r.id == a.revision_id), 1)
            approval_records.append(
                ProposalApprovalRecord(
                    id=a.id,
                    proposal_id=a.proposal_id,
                    revision_id=a.revision_id,
                    revision_number=rev_num,
                    user_id=a.user_id,
                    user_name=a.user.full_name if a.user else None,
                    action=a.action,
                    notes=a.notes,
                    ip_address=a.ip_address,
                    created_at=a.created_at,
                )
            )
            if a.action == ApprovalAction.REJECTED and a.notes:
                rejection_reason = a.notes

        # Contact disclosure extraction: Strictly guarded
        disclosed_credentials: Optional[DisclosedContactCredentials] = None
        contacts_disclosed = False

        if proposal.status == ProposalStatus.MUTUALLY_APPROVED:
            contacts_disclosed = True
            # Find disclosure where disclosed_to_user_id == current_user.id (or first disclosure for platform admin)
            disclosure = next(
                (d for d in proposal.contact_disclosures if d.disclosed_to_user_id == current_user.id),
                None,
            )
            if not disclosure and is_admin and proposal.contact_disclosures:
                disclosure = proposal.contact_disclosures[0]

            if disclosure and disclosure.disclosed_credentials:
                creds = disclosure.disclosed_credentials
                disclosed_credentials = DisclosedContactCredentials(
                    user_id=disclosure.user_id,
                    full_name=creds.get("full_name", ""),
                    company_name=creds.get("company_name"),
                    designation=creds.get("designation"),
                    email=creds.get("email", ""),
                    phone_number=creds.get("phone_number", ""),
                    hq_city=creds.get("hq_city"),
                    corporate_website=creds.get("corporate_website"),
                    tax_id_or_registration=creds.get("tax_id_or_registration"),
                    verification_receipt_hash=creds.get("verification_receipt_hash") or creds.get("transaction_receipt_hash"),
                    disclosed_at=disclosure.disclosed_at,
                )

        return ProposalDetailResponse(
            id=proposal.id,
            conversation_id=proposal.conversation_id,
            proposer=ProposalPartySummary(
                user_id=proposal.proposer_id,
                full_name=proposal.proposer.full_name,
                company_name=proposal.proposer.company_name,
                designation=proposal.proposer.job_title,
                role=proposal.proposer_role,
            ),
            recipient=ProposalPartySummary(
                user_id=proposal.recipient_id,
                full_name=proposal.recipient.full_name,
                company_name=proposal.recipient.company_name,
                designation=proposal.recipient.job_title,
                role=proposal.recipient_role,
            ),
            proposal_type=proposal.proposal_type,
            status=proposal.status,
            current_revision_number=proposal.current_revision_number,
            active_revision=active_rev_response,
            revisions=rev_responses,
            approvals=approval_records,
            expires_at=proposal.expires_at,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            concluded_at=proposal.concluded_at,
            user_is_proposer=user_is_proposer,
            requires_user_action=requires_action,
            contacts_disclosed=contacts_disclosed,
            disclosed_credentials=disclosed_credentials,
            rejection_reason=rejection_reason,
        )

    @staticmethod
    async def approve_proposal(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        payload: ProposalApprovalRequest,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Approve the active proposal revision under pessimistic row-level lock."""
        from app.services.proposal_approval import ProposalApprovalService

        return await ProposalApprovalService.approve_proposal_with_lock(
            db, proposal_id, current_user, payload, client_ip
        )

    @staticmethod
    async def counter_proposal(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        payload: CounterProposalRequest,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Submit a counterproposal revision (Vk+1) with modified parameters."""
        from app.services.proposal_approval import ProposalApprovalService

        return await ProposalApprovalService.submit_counter_proposal(
            db, proposal_id, current_user, payload, client_ip
        )

    @staticmethod
    async def reject_proposal(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        payload: ProposalRejectionRequest,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Reject a pending proposal with mandatory reason."""
        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(selectinload(Proposal.revisions))
            .with_for_update()
        )
        res = await db.execute(stmt)
        proposal = res.scalar_one_or_none()

        if not proposal or current_user.id not in (proposal.proposer_id, proposal.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found.",
            )

        if proposal.status not in (ProposalStatus.PENDING_REVIEW, ProposalStatus.REVISED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot decline proposal in {proposal.status.value} status.",
            )

        active_rev = next(
            (r for r in proposal.revisions if r.revision_number == proposal.current_revision_number),
            proposal.revisions[-1] if proposal.revisions else None,
        )
        if not active_rev:
            raise HTTPException(status_code=500, detail="No active revision record.")

        now = datetime.now(timezone.utc)
        proposal.status = ProposalStatus.REJECTED
        proposal.concluded_at = now

        rejection_approval = ProposalApproval(
            proposal=proposal,
            revision=active_rev,
            user_id=current_user.id,
            action=ApprovalAction.REJECTED,
            notes=payload.reason,
            ip_address=client_ip,
        )
        db.add(rejection_approval)
        prop_id = proposal.id
        status_val = proposal.status
        await db.commit()

        # Publish SSE and conversation room event
        event_data = {
            "proposal_id": str(prop_id),
            "conversation_id": str(proposal.conversation_id) if proposal.conversation_id else None,
            "status": status_val.value,
            "actor_id": str(current_user.id),
            "reason": payload.reason,
            "title": active_rev.title if active_rev else "Commercial Agreement",
            "action": "REJECTED",
        }
        try:
            await event_broker.publish("proposal:rejected", event_data)
        except Exception as e:
            logger.warning("Failed to publish SSE event: %s", e)

        if proposal.conversation_id:
            try:
                from app.api.routes.conversations import broadcast_conversation_event
                await broadcast_conversation_event(proposal.conversation_id, {
                    "event": "proposal:rejected",
                    "data": event_data,
                })
            except Exception as e:
                logger.debug("Failed to broadcast proposal:rejected to conversation: %s", e)

        return await ProposalService.get_proposal(db, prop_id, current_user)

    @staticmethod
    async def withdraw_proposal(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Withdraw an authored proposal revision before counterparty decision."""
        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(selectinload(Proposal.revisions))
            .with_for_update()
        )
        res = await db.execute(stmt)
        proposal = res.scalar_one_or_none()

        if not proposal or current_user.id not in (proposal.proposer_id, proposal.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found.",
            )

        if proposal.status not in (ProposalStatus.PENDING_REVIEW, ProposalStatus.REVISED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot withdraw proposal in {proposal.status.value} status.",
            )

        active_rev = next(
            (r for r in proposal.revisions if r.revision_number == proposal.current_revision_number),
            None,
        )
        if not active_rev:
            raise HTTPException(status_code=500, detail="Active revision record missing.")

        if active_rev.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only withdraw a proposal revision that you personally authored.",
            )

        now = datetime.now(timezone.utc)
        proposal.status = ProposalStatus.WITHDRAWN
        proposal.concluded_at = now

        withdrawal = ProposalApproval(
            proposal=proposal,
            revision=active_rev,
            user_id=current_user.id,
            action=ApprovalAction.WITHDRAWN,
            notes="Withdrawn by author before counterparty acceptance.",
            ip_address=client_ip,
        )
        db.add(withdrawal)
        prop_id = proposal.id
        status_val = proposal.status
        await db.commit()

        # Publish SSE and conversation room event
        event_data = {
            "proposal_id": str(prop_id),
            "conversation_id": str(proposal.conversation_id) if proposal.conversation_id else None,
            "status": status_val.value,
            "actor_id": str(current_user.id),
            "title": active_rev.title if active_rev else "Commercial Agreement",
            "action": "WITHDRAWN",
        }
        try:
            await event_broker.publish("proposal:withdrawn", event_data)
        except Exception as e:
            logger.warning("Failed to publish SSE event: %s", e)

        if proposal.conversation_id:
            try:
                from app.api.routes.conversations import broadcast_conversation_event
                await broadcast_conversation_event(proposal.conversation_id, {
                    "event": "proposal:withdrawn",
                    "data": event_data,
                })
            except Exception as e:
                logger.debug("Failed to broadcast proposal:withdrawn to conversation: %s", e)

        return await ProposalService.get_proposal(db, prop_id, current_user)

    @staticmethod
    async def get_unlocked_contacts(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
    ) -> DisclosedContactCredentials:
        """Retrieve verified mutual contact coordinates strictly after mutual approval."""
        detail = await ProposalService.get_proposal(db, proposal_id, current_user)
        if detail.status != ProposalStatus.MUTUALLY_APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contact details are strictly locked until mutual dual-sided approval is committed.",
            )
        if not detail.disclosed_credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No disclosed contact credentials found for your account on this agreement.",
            )
        return detail.disclosed_credentials

    @staticmethod
    async def list_admin_proposals(
        db: AsyncSession,
        status: Optional[ProposalStatus] = None,
        proposal_type: Optional[ProposalType] = None,
        search: Optional[str] = None,
        user_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminProposalListResponse:
        """Administrative directory of platform commercial proposals with status counts, search, and pagination."""
        import math

        base_query = (
            select(Proposal)
            .options(
                selectinload(Proposal.revisions).selectinload(ProposalRevision.author),
                selectinload(Proposal.proposer),
                selectinload(Proposal.recipient),
                selectinload(Proposal.approvals),
            )
        )

        # Filters
        if status:
            base_query = base_query.where(Proposal.status == status)
        if proposal_type:
            base_query = base_query.where(Proposal.proposal_type == proposal_type)
        if user_id:
            base_query = base_query.where(
                or_(
                    Proposal.proposer_id == user_id,
                    Proposal.recipient_id == user_id,
                )
            )

        if search and search.strip():
            term = f"%{search.strip()}%"
            base_query = base_query.where(
                or_(
                    Proposal.proposer.has(
                        or_(User.full_name.ilike(term), User.company_name.ilike(term), User.email.ilike(term))
                    ),
                    Proposal.recipient.has(
                        or_(User.full_name.ilike(term), User.company_name.ilike(term), User.email.ilike(term))
                    ),
                    Proposal.revisions.any(
                        or_(ProposalRevision.title.ilike(term), ProposalRevision.product_name.ilike(term))
                    ),
                )
            )

        # Status counts calculation (platform-wide or scoped by user_id)
        count_stmt = select(Proposal.status, func.count(Proposal.id)).group_by(Proposal.status)
        if user_id:
            count_stmt = count_stmt.where(
                or_(
                    Proposal.proposer_id == user_id,
                    Proposal.recipient_id == user_id,
                )
            )
        count_res = await db.execute(count_stmt)
        status_counts: Dict[str, int] = {s.value: 0 for s in ProposalStatus}
        total_all = 0
        for st, c in count_res.all():
            val = st.value if hasattr(st, "value") else str(st)
            status_counts[val] = c
            total_all += c
        status_counts["total"] = total_all

        # Total count for the filtered query
        total_stmt = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(total_stmt)
        total = total_res.scalar_one() or 0

        # Pagination & Ordering
        offset = (page - 1) * page_size
        paginated_query = (
            base_query
            .order_by(Proposal.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await db.execute(paginated_query)
        proposals = res.scalars().all()

        items: List[AdminProposalListItem] = []
        now = datetime.now(timezone.utc)
        for p in proposals:
            # Check dynamic expiration
            if p.status in (ProposalStatus.PENDING_REVIEW, ProposalStatus.REVISED) and p.expires_at < now:
                p.status = ProposalStatus.EXPIRED

            sorted_revs = sorted(p.revisions, key=lambda r: r.revision_number) if p.revisions else []
            latest_rev = next(
                (r for r in sorted_revs if r.revision_number == p.current_revision_number),
                sorted_revs[-1] if sorted_revs else None,
            )

            title = latest_rev.title if latest_rev else "Untitled Proposal"
            product_name = latest_rev.product_name if latest_rev else "Custom Goods/Services"
            total_value = latest_rev.total_value if latest_rev else None
            currency = latest_rev.currency if latest_rev else "INR"

            items.append(
                AdminProposalListItem(
                    id=p.id,
                    conversation_id=p.conversation_id,
                    proposer_id=p.proposer_id,
                    proposer_name=p.proposer.full_name if p.proposer else "Unknown Proposer",
                    proposer_company=p.proposer.company_name if p.proposer else None,
                    proposer_role=p.proposer_role,
                    recipient_id=p.recipient_id,
                    recipient_name=p.recipient.full_name if p.recipient else "Unknown Recipient",
                    recipient_company=p.recipient.company_name if p.recipient else None,
                    recipient_role=p.recipient_role,
                    proposal_type=p.proposal_type,
                    status=p.status,
                    current_revision_number=p.current_revision_number,
                    total_revisions_count=len(p.revisions),
                    current_title=title,
                    product_name=product_name,
                    total_value=total_value,
                    currency=currency,
                    expires_at=p.expires_at,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    concluded_at=p.concluded_at,
                    approvals_count=len(p.approvals),
                )
            )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return AdminProposalListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            status_counts=status_counts,
        )
