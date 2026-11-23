"""AI Agent Integration & Automated Ask Broadcast Engine (Quote Subphase 4).

Extracts and synthesizes procurement specifications from:
1. Frozen Conversation Business Context (`ConversationBusinessContext`).
2. Participant Business Profiles & Requirements.
3. Bilateral Dialogue Messages & Inquiry Notes.
4. Real-time Event Broker for multi-vendor notification.
"""

from decimal import Decimal
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import event_broker
from app.db.models.business import BusinessProfile, BusinessRequirement, ConversationBusinessContext
from app.db.models.conversation import Conversation, Message
from app.db.models.quote import QuoteUrgency
from app.db.models.user import User
from app.schemas.quote import QuoteRequestCreate, QuoteRequestDetail
from app.services.quote import QuoteService

logger = logging.getLogger("converge.services.quote_agent")


class QuoteAgentService:
    """Service synthesizing procurement asks from conversations and broadcasting to vendors."""

    @staticmethod
    async def generate_ask_prefill(
        db: AsyncSession,
        current_user: User,
        conversation_id: UUID,
    ) -> QuoteRequestCreate:
        """Analyze conversation context and synthesize a prefilled procurement ask."""
        # 1. Verify conversation existence and participant membership
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv_res = await db.execute(conv_stmt)
        conversation = conv_res.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced conversation not found",
            )

        if current_user.id not in (conversation.initiator_id, conversation.target_id) and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access denied to conversation context",
            )

        # 2. Check for frozen Connection Business Context
        ctx_stmt = select(ConversationBusinessContext).where(
            ConversationBusinessContext.conversation_id == conversation_id
        )
        ctx_res = await db.execute(ctx_stmt)
        ctx = ctx_res.scalar_one_or_none()

        if ctx:
            urgency_mapped = QuoteUrgency.PLANNED
            if ctx.urgency:
                clean_u = ctx.urgency.upper()
                if clean_u in ("IMMEDIATE", "HIGH", "CRITICAL"):
                    urgency_mapped = QuoteUrgency.IMMEDIATE
                elif clean_u in ("EXPLORATORY", "LOW"):
                    urgency_mapped = QuoteUrgency.EXPLORATORY

            qty_str = f"{int(ctx.quantity):,}" if ctx.quantity and ctx.quantity == int(ctx.quantity) else str(ctx.quantity or "")
            title = f"Procurement Inquiry: {qty_str} {ctx.unit or 'MT'} {ctx.product_name}".strip()

            return QuoteRequestCreate(
                conversation_id=conversation_id,
                customer_agent_persona="Procurement AI Agent",
                title=title,
                product_name=ctx.product_name,
                product_code=ctx.product_code,
                grade_code=ctx.grade_code,
                service_code=ctx.service_code,
                quantity=ctx.quantity,
                quantity_unit=ctx.unit or "MT",
                delivery_location=ctx.delivery_location,
                timeline_days=ctx.timeline_days,
                target_price_indication=ctx.target_price_indication,
                currency="INR",
                is_budget_public=False,
                urgency=urgency_mapped,
                technical_specifications={},
                inquiry_notes=ctx.inquiry_notes or "Auto-extracted from grounded negotiation brief.",
            )

        # 3. Fallback: Inspect buyer profile requirements
        req_stmt = (
            select(BusinessRequirement)
            .join(BusinessProfile, BusinessRequirement.business_profile_id == BusinessProfile.id)
            .where(BusinessProfile.user_id == current_user.id, BusinessRequirement.is_active == True)  # noqa: E712
            .limit(1)
        )
        req_res = await db.execute(req_stmt)
        req = req_res.scalar_one_or_none()

        if req:
            prod_name = req.custom_requirement_title or "Industrial Raw Materials"
            return QuoteRequestCreate(
                conversation_id=conversation_id,
                customer_agent_persona="Procurement AI Agent",
                title=f"Procurement: {req.required_quantity or ''} {req.quantity_unit or 'MT'} {prod_name}".strip(),
                product_name=prod_name,
                product_code=req.product_code,
                grade_code=req.grade_code,
                service_code=req.service_code,
                quantity=req.required_quantity,
                quantity_unit=req.quantity_unit or "MT",
                delivery_location=f"{req.delivery_city or ''}, {req.delivery_country or ''}".strip(", "),
                timeline_days=req.target_timeline_days or 30,
                target_price_indication=req.target_budget_indication,
                currency="INR",
                is_budget_public=req.is_budget_public,
                urgency=QuoteUrgency.PLANNED,
                technical_specifications={"certifications": req.required_certifications or []},
                inquiry_notes=req.notes or "Extracted from attendee procurement profile.",
            )

        # 4. Fallback: Parse dialogue messages for material keywords
        msg_stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.turn_index.asc())
        )
        msg_res = await db.execute(msg_stmt)
        messages = msg_res.scalars().all()

        combined_text = " ".join([m.content for m in messages if m.content])
        product_name = "Limestone Calcined Clay Cement (LC3)"
        if "clinker" in combined_text.lower():
            product_name = "Low-Carbon Clinker"
        elif "fly ash" in combined_text.lower():
            product_name = "Class F Fly Ash"
        elif "slag" in combined_text.lower():
            product_name = "Ground Granulated Blast-Furnace Slag (GGBS)"

        # Search for quantity
        qty = Decimal("1000")
        qty_match = re.search(r"(\d+)\s*(?:MT|metric tons?|tonnes?|tons?)", combined_text, re.IGNORECASE)
        if qty_match:
            try:
                qty = Decimal(qty_match.group(1))
            except Exception:
                pass

        return QuoteRequestCreate(
            conversation_id=conversation_id,
            customer_agent_persona="Procurement AI Agent",
            title=f"Procurement Inquiry: {int(qty):,} MT {product_name}",
            product_name=product_name,
            quantity=qty,
            quantity_unit="MT",
            delivery_location="Pune Industrial Yard, Maharashtra",
            timeline_days=21,
            currency="INR",
            urgency=QuoteUrgency.PLANNED,
            technical_specifications={},
            inquiry_notes="Synthesized from dialogue representative negotiation.",
        )

    @staticmethod
    async def broadcast_ask_from_conversation(
        db: AsyncSession,
        current_user: User,
        conversation_id: UUID,
        payload_override: Optional[QuoteRequestCreate] = None,
    ) -> QuoteRequestDetail:
        """Synthesize and broadcast an ask to matched vendors in a single operation."""
        # 1. Synthesize if not explicitly supplied
        payload = payload_override or await QuoteAgentService.generate_ask_prefill(
            db, current_user, conversation_id
        )

        # 2. Determine target customer (prefer buyer participant in bilateral conversation)
        target_customer = current_user
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await db.execute(conv_stmt)).scalar_one_or_none()
        if conv:
            bp_stmt = select(BusinessProfile).where(
                BusinessProfile.user_id.in_([conv.initiator_id, conv.target_id])
            )
            profiles = (await db.execute(bp_stmt)).scalars().all()
            buyer_id = None
            for bp in profiles:
                if bp.is_buyer:
                    buyer_id = bp.user_id
                    break
            if not buyer_id:
                buyer_id = conv.initiator_id

            if buyer_id != current_user.id:
                target_cust_res = await db.execute(select(User).where(User.id == buyer_id))
                found_cust = target_cust_res.scalar_one_or_none()
                if found_cust:
                    target_customer = found_cust

        # 3. Delegate to QuoteService to create ask and match vendors
        ask_detail = await QuoteService.create_quote_request(db, target_customer, payload)

        # 4. Publish real-time event to matched suppliers via SSE/WebSocket
        try:
            event_payload = {
                "quote_request_id": str(ask_detail.id),
                "title": ask_detail.title,
                "product_name": ask_detail.product_name,
                "quantity": float(ask_detail.quantity) if ask_detail.quantity else None,
                "unit": ask_detail.quantity_unit,
                "delivery_location": ask_detail.delivery_location,
                "customer_name": target_customer.full_name,
                "customer_company": target_customer.company_name,
                "customer_agent_persona": ask_detail.customer_agent_persona,
                "conversation_id": str(conversation_id),
                "created_at": ask_detail.created_at.isoformat(),
            }
            await event_broker.publish("quote:matched", event_payload)
            logger.info("Published real-time SSE event 'quote:matched' for ask %s", ask_detail.id)
        except Exception as ex:
            logger.warning("Failed to publish real-time SSE event for ask %s: %s", ask_detail.id, ex)

        return ask_detail
