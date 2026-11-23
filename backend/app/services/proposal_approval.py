r"""Dual-Sided Approval Engine, Revision Diff & Secure Contact Disclosure (Phase 7 - Subphase 5).

Enforces:
1. Pessimistic Row-Level Locking (SELECT ... FOR UPDATE) preventing race conditions on concurrent approvals.
2. Non-Repudiable Cryptographic Verification Receipt Hash (SHA-256).
3. Immutable Bilateral Contact Disclosure Ledger upon exact dual consensus on the active revision.
4. Structured Revision Diff Computation ($V_{from} \leftrightarrow V_{to}$) across all commercial parameters.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
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
)
from app.db.models.user import User
from app.schemas.proposal import (
    CounterProposalRequest,
    ProposalApprovalRequest,
    ProposalDetailResponse,
    ProposalDiffFieldChange,
    ProposalRevisionDiffResponse,
)

logger = logging.getLogger("converge.services.proposal_approval")


class ProposalApprovalService:
    """Authoritative engine governing revision approvals, counters, diffing, and mutual disclosure."""

    @staticmethod
    async def approve_proposal_with_lock(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        payload: ProposalApprovalRequest,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Approve the active proposal revision under pessimistic row-level lock."""
        from app.services.proposal import ProposalService

        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(
                selectinload(Proposal.revisions),
                selectinload(Proposal.approvals),
                selectinload(Proposal.proposer),
                selectinload(Proposal.recipient),
            )
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
                detail=f"Cannot approve proposal in {proposal.status.value} state.",
            )

        now = datetime.now(timezone.utc)
        if proposal.expires_at < now:
            proposal.status = ProposalStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This proposal has expired and can no longer be approved.",
            )

        active_rev = next(
            (r for r in proposal.revisions if r.revision_number == proposal.current_revision_number),
            None,
        )
        if not active_rev:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Active revision record not found.",
            )

        # Check if already approved by current user
        already_approved = any(
            a.revision_id == active_rev.id and a.user_id == current_user.id and a.action == ApprovalAction.APPROVED
            for a in proposal.approvals
        )
        if already_approved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already approved the active revision of this proposal.",
            )

        # Record approval
        approval = ProposalApproval(
            proposal=proposal,
            revision=active_rev,
            user_id=current_user.id,
            action=ApprovalAction.APPROVED,
            notes=payload.notes or "Proposal revision approved.",
            ip_address=client_ip,
        )
        db.add(approval)
        await db.flush()

        # Count distinct approved users on active revision
        approved_user_ids = {
            a.user_id
            for a in proposal.approvals
            if a.revision_id == active_rev.id and a.action == ApprovalAction.APPROVED
        }
        approved_user_ids.add(current_user.id)

        # If both participants have approved active revision: MUTUAL APPROVAL!
        if len(approved_user_ids) >= 2:
            proposal.status = ProposalStatus.MUTUALLY_APPROVED
            proposal.concluded_at = now

            # Generate Cryptographic Verification Hash
            receipt_hash = ProposalApprovalService.generate_cryptographic_receipt(
                proposal=proposal, revision=active_rev, timestamp=now
            )

            # Snapshot credentials for User A and B
            user_a = proposal.proposer
            user_b = proposal.recipient

            creds_a = {
                "user_id": str(user_a.id),
                "full_name": user_a.full_name,
                "company_name": user_a.company_name,
                "designation": user_a.job_title,
                "email": user_a.email,
                "phone_number": user_a.phone_number or "Verified through Converge AI",
                "verification_receipt_hash": receipt_hash,
            }
            creds_b = {
                "user_id": str(user_b.id),
                "full_name": user_b.full_name,
                "company_name": user_b.company_name,
                "designation": user_b.job_title,
                "email": user_b.email,
                "phone_number": user_b.phone_number or "Verified through Converge AI",
                "verification_receipt_hash": receipt_hash,
            }

            # Disclose A to B and B to A
            disc_a_to_b = ProposalContactDisclosure(
                proposal=proposal,
                user_id=user_a.id,
                disclosed_to_user_id=user_b.id,
                disclosed_credentials=creds_a,
                disclosed_at=now,
            )
            disc_b_to_a = ProposalContactDisclosure(
                proposal=proposal,
                user_id=user_b.id,
                disclosed_to_user_id=user_a.id,
                disclosed_credentials=creds_b,
                disclosed_at=now,
            )
            db.add_all([disc_a_to_b, disc_b_to_a])

            # Update linked conversation terminal outcome if tied to chat
            if proposal.conversation_id:
                conv_update_stmt = (
                    update(Conversation)
                    .where(Conversation.id == proposal.conversation_id)
                    .values(
                        status="COMPLETED",
                        concluded_at=now,
                        terminal_outcome="PROPOSAL_GENERATED",
                    )
                )
                await db.execute(conv_update_stmt)

        prop_id = proposal.id
        status_val = proposal.status
        await db.commit()

        # Publish SSE and in-conversation WebSocket events
        event_name = "proposal:approved" if status_val == ProposalStatus.MUTUALLY_APPROVED else "proposal:reviewed"
        event_data = {
            "proposal_id": str(prop_id),
            "conversation_id": str(proposal.conversation_id) if proposal.conversation_id else None,
            "status": status_val.value,
            "action": "APPROVED",
            "actor_id": str(current_user.id),
            "title": active_rev.title if active_rev else "Commercial Agreement",
            "revision_number": active_rev.revision_number if active_rev else proposal.current_revision_number,
        }
        try:
            await event_broker.publish(event_name, event_data)
        except Exception as e:
            logger.warning("Failed to publish SSE event: %s", e)

        if proposal.conversation_id:
            try:
                from app.api.routes.conversations import broadcast_conversation_event
                await broadcast_conversation_event(proposal.conversation_id, {
                    "event": event_name,
                    "data": event_data,
                })
            except Exception as e:
                logger.debug("Failed to broadcast %s to conversation: %s", event_name, e)

        return await ProposalService.get_proposal(db, prop_id, current_user)

    @staticmethod
    async def submit_counter_proposal(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        payload: CounterProposalRequest,
        client_ip: Optional[str] = None,
    ) -> ProposalDetailResponse:
        """Submit a counterproposal revision (Vk+1) with modified parameters under row lock."""
        from app.services.proposal import ProposalService

        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(
                selectinload(Proposal.revisions),
                selectinload(Proposal.approvals),
            )
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
                detail=f"Cannot counter a proposal in {proposal.status.value} status.",
            )

        now = datetime.now(timezone.utc)
        if proposal.expires_at < now:
            proposal.status = ProposalStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This proposal has expired.",
            )

        new_rev_number = proposal.current_revision_number + 1
        proposal.current_revision_number = new_rev_number
        proposal.status = ProposalStatus.REVISED
        proposal.expires_at = now + timedelta(days=7)  # Renew validity window

        rev_data = payload.revision
        total_val = rev_data.total_value
        if total_val is None and rev_data.unit_price is not None:
            total_val = rev_data.quantity * rev_data.unit_price

        counter_revision = ProposalRevision(
            proposal=proposal,
            revision_number=new_rev_number,
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
            revision_summary=payload.revision_summary,
        )
        db.add(counter_revision)
        await db.flush()

        # Author auto-approval on new revision
        author_approval = ProposalApproval(
            proposal=proposal,
            revision=counter_revision,
            user_id=current_user.id,
            action=ApprovalAction.APPROVED,
            notes=f"Counterproposal Revision V{new_rev_number} submitted.",
            ip_address=client_ip,
        )
        db.add(author_approval)
        prop_id = proposal.id
        status_val = proposal.status
        await db.commit()

        # Publish SSE and in-conversation WebSocket events
        event_data = {
            "proposal_id": str(prop_id),
            "conversation_id": str(proposal.conversation_id) if proposal.conversation_id else None,
            "status": status_val.value,
            "revision_number": new_rev_number,
            "actor_id": str(current_user.id),
            "title": counter_revision.title,
            "product_name": counter_revision.product_name,
            "quantity": float(counter_revision.quantity) if counter_revision.quantity is not None else None,
            "unit": counter_revision.unit,
            "total_value": float(counter_revision.total_value) if counter_revision.total_value is not None else None,
            "currency": counter_revision.currency,
            "action": "COUNTERED",
        }
        try:
            await event_broker.publish("proposal:countered", event_data)
        except Exception as e:
            logger.warning("Failed to publish SSE event: %s", e)

        if proposal.conversation_id:
            try:
                from app.api.routes.conversations import broadcast_conversation_event
                await broadcast_conversation_event(proposal.conversation_id, {
                    "event": "proposal:countered",
                    "data": event_data,
                })
            except Exception as e:
                logger.debug("Failed to broadcast proposal:countered to conversation: %s", e)

        return await ProposalService.get_proposal(db, prop_id, current_user)

    @staticmethod
    def generate_cryptographic_receipt(
        proposal: Proposal,
        revision: ProposalRevision,
        timestamp: datetime,
    ) -> str:
        """Calculate tamper-evident SHA-256 hash identifying the mutual consensus record."""
        hash_input = (
            f"{proposal.id}:{revision.id}:{proposal.proposer_id}:"
            f"{proposal.recipient_id}:{revision.revision_number}:{timestamp.isoformat()}"
        )
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    @staticmethod
    async def compute_revision_diff(
        db: AsyncSession,
        proposal_id: UUID,
        current_user: User,
        from_rev_num: int,
        to_rev_num: Optional[int] = None,
        is_admin: bool = False,
    ) -> ProposalRevisionDiffResponse:
        """Compare two revisions parameter-by-parameter and yield structured diff."""
        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(
                selectinload(Proposal.revisions).selectinload(ProposalRevision.author),
            )
        )
        res = await db.execute(stmt)
        proposal = res.scalar_one_or_none()

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found.",
            )

        if not is_admin and current_user.id not in (proposal.proposer_id, proposal.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found.",
            )

        target_to_num = to_rev_num if to_rev_num is not None else proposal.current_revision_number

        rev_from = next((r for r in proposal.revisions if r.revision_number == from_rev_num), None)
        rev_to = next((r for r in proposal.revisions if r.revision_number == target_to_num), None)

        if not rev_from:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Baseline revision V{from_rev_num} not found.",
            )
        if not rev_to:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target revision V{target_to_num} not found.",
            )

        changes: List[ProposalDiffFieldChange] = []
        has_price_change = False
        has_quantity_change = False
        has_timeline_change = False
        has_delivery_change = False

        # Helper to register field diff
        def check_field(
            field: str,
            label: str,
            val_a: Any,
            val_b: Any,
            is_numeric: bool = False,
            unit_suffix: str = "",
            currency_prefix: str = "",
        ):
            nonlocal has_price_change, has_quantity_change, has_timeline_change, has_delivery_change

            if val_a == val_b:
                return

            num_delta: Optional[Decimal] = None
            fmt_change: Optional[str] = None

            if is_numeric and val_a is not None and val_b is not None:
                d_a = Decimal(str(val_a))
                d_b = Decimal(str(val_b))
                num_delta = d_b - d_a
                sign = "+" if num_delta >= 0 else "-"
                abs_clean = f"{abs(float(num_delta)):g}"
                if currency_prefix:
                    fmt_change = f"{sign}{currency_prefix} {abs_clean}"
                elif unit_suffix:
                    fmt_change = f"{sign}{abs_clean} {unit_suffix}"
                else:
                    fmt_change = f"{sign}{abs_clean}"

            if field in ("unit_price", "total_value"):
                has_price_change = True
            elif field == "quantity":
                has_quantity_change = True
            elif field == "delivery_timeline_days":
                has_timeline_change = True
            elif field in ("delivery_location", "incoterm"):
                has_delivery_change = True

            change_type = "MODIFIED"
            if val_a is None and val_b is not None:
                change_type = "ADDED"
            elif val_a is not None and val_b is None:
                change_type = "REMOVED"

            changes.append(
                ProposalDiffFieldChange(
                    field=field,
                    field_label=label,
                    old_value=val_a,
                    new_value=val_b,
                    change_type=change_type,
                    numeric_delta=num_delta,
                    formatted_change=fmt_change,
                )
            )

        # 1. Product Name & Grade
        check_field("product_name", "Product / Commodity", rev_from.product_name, rev_to.product_name)
        check_field("grade_code", "Material Grade", rev_from.grade_code, rev_to.grade_code)

        # 2. Quantity & Unit
        check_field(
            "quantity",
            "Quantity",
            rev_from.quantity,
            rev_to.quantity,
            is_numeric=True,
            unit_suffix=rev_to.unit or "Units",
        )
        check_field("unit", "Unit of Measure", rev_from.unit, rev_to.unit)

        # 3. Pricing
        curr_symbol = "₹" if (rev_to.currency or rev_from.currency) == "INR" else (rev_to.currency or "$")
        check_field(
            "unit_price",
            "Unit Commercial Price",
            rev_from.unit_price,
            rev_to.unit_price,
            is_numeric=True,
            currency_prefix=curr_symbol,
        )
        check_field(
            "total_value",
            "Total Contract Value",
            rev_from.total_value,
            rev_to.total_value,
            is_numeric=True,
            currency_prefix=curr_symbol,
        )
        check_field("currency", "Currency", rev_from.currency, rev_to.currency)

        # 4. Delivery & Terms
        check_field("payment_terms", "Payment Terms", rev_from.payment_terms, rev_to.payment_terms)
        check_field("delivery_location", "Delivery Destination", rev_from.delivery_location, rev_to.delivery_location)
        check_field("incoterm", "Applicable Incoterm", rev_from.incoterm, rev_to.incoterm)
        check_field(
            "delivery_timeline_days",
            "Delivery Lead Time",
            rev_from.delivery_timeline_days,
            rev_to.delivery_timeline_days,
            is_numeric=True,
            unit_suffix="Days",
        )

        # 5. Standards & Covenants
        check_field(
            "governing_standards",
            "Governing Standards",
            rev_from.governing_standards or [],
            rev_to.governing_standards or [],
        )
        check_field("special_conditions", "Special Conditions", rev_from.special_conditions, rev_to.special_conditions)
        check_field("notes", "Notes", rev_from.notes, rev_to.notes)

        return ProposalRevisionDiffResponse(
            proposal_id=proposal.id,
            from_revision_number=rev_from.revision_number,
            to_revision_number=rev_to.revision_number,
            from_author_name=rev_from.author.full_name if rev_from.author else None,
            to_author_name=rev_to.author.full_name if rev_to.author else None,
            from_created_at=rev_from.created_at,
            to_created_at=rev_to.created_at,
            changes=changes,
            has_price_change=has_price_change,
            has_quantity_change=has_quantity_change,
            has_timeline_change=has_timeline_change,
            has_delivery_change=has_delivery_change,
        )
