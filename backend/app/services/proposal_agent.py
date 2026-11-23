"""AI Proposal Drafting Engine & Business Profile Autofill (Phase 7 - Subphase 4).

Generates grounded commercial proposal drafts from:
1. Connection Business Context Snapshots (`ConversationBusinessContext`).
2. Persisted Participant `BusinessProfile` Offerings and Requirements.
3. Chronological Conversation Dialogue Turns.
4. Strict Taxonomy Standards and Normalization.
"""

from decimal import Decimal
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.business import (
    BusinessOffering,
    BusinessProfile,
    BusinessRequirement,
    ConversationBusinessContext,
)
from app.db.models.conversation import Conversation, Message
from app.db.models.proposal import CommercialRole, ProposalType
from app.db.models.user import User
from app.schemas.proposal import (
    ProposalDraftPrefillRequest,
    ProposalDraftPrefillResponse,
    ProposalRevisionCreate,
)
from app.services.business_profile import BusinessProfileService

logger = logging.getLogger("converge.services.proposal_agent")


class ProposalAgentService:
    """Intelligent drafting service converting bilateral negotiations into structured proposals."""

    @staticmethod
    async def generate_draft_prefill(
        db: AsyncSession,
        current_user: User,
        payload: ProposalDraftPrefillRequest,
    ) -> ProposalDraftPrefillResponse:
        """Analyze dialogue context and user profiles to generate a pre-populated proposal draft."""
        if payload.recipient_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot generate a proposal draft to yourself.",
            )

        # 1. Fetch Conversation and verify participant authorization
        conv_stmt = (
            select(Conversation)
            .where(Conversation.id == payload.conversation_id)
            .options(
                selectinload(Conversation.initiator),
                selectinload(Conversation.target),
                selectinload(Conversation.messages),
            )
        )
        conv_res = await db.execute(conv_stmt)
        conversation = conv_res.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced conversation not found.",
            )

        if current_user.id not in (conversation.initiator_id, conversation.target_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an authorized participant in this dialogue.",
            )

        if payload.recipient_id not in (conversation.initiator_id, conversation.target_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target recipient is not the other participant in this dialogue.",
            )

        # 2. Fetch Business Profiles for both parties
        proposer_profile = await BusinessProfileService.get_profile_with_catalog(db, current_user.id)
        recipient_profile = await BusinessProfileService.get_profile_with_catalog(db, payload.recipient_id)

        # 3. Fetch ConversationBusinessContext (Frozen brief)
        ctx_stmt = (
            select(ConversationBusinessContext)
            .where(ConversationBusinessContext.conversation_id == conversation.id)
            .options(selectinload(ConversationBusinessContext.revisions))
        )
        ctx_res = await db.execute(ctx_stmt)
        biz_ctx = ctx_res.scalar_one_or_none()

        # 4. Resolve Roles & Base Proposal Type
        inquiry_type = biz_ctx.inquiry_type if biz_ctx else None
        proposer_role, recipient_role = BusinessProfileService.resolve_bilateral_roles(
            proposer_profile=proposer_profile,
            recipient_profile=recipient_profile,
            inquiry_type=inquiry_type,
        )
        prop_type = BusinessProfileService.resolve_proposal_type(inquiry_type, proposer_role)

        # 5. Extract Commercial Terms through Grounding Hierarchy
        (
            product_name,
            product_code,
            grade_code,
            service_code,
            quantity,
            unit,
            unit_price,
            currency,
            delivery_location,
            delivery_timeline_days,
            payment_terms,
            incoterm,
            governing_standards,
            special_conditions,
            notes,
            grounding_source,
            confidence_score,
        ) = await ProposalAgentService._extract_commercial_parameters(
            db=db,
            biz_ctx=biz_ctx,
            proposer_profile=proposer_profile,
            recipient_profile=recipient_profile,
            proposer_role=proposer_role,
            messages=conversation.messages,
            current_user=current_user,
            recipient=conversation.target if conversation.initiator_id == current_user.id else conversation.initiator,
        )

        # 6. Generate Title and Revision Summary
        clean_qty = f"{float(quantity):g}"
        clean_unit = "MT" if unit in ("METRIC_TONNE", "METRIC_TON") else unit.replace("_", " ")
        title = f"{prop_type.value.replace('_', ' ').title()}: {clean_qty} {clean_unit} {product_name}"
        if len(title) > 150:
            title = title[:147] + "..."

        source_label = grounding_source.lower().replace("_", " ")
        revision_summary = f"Pre-populated proposal draft grounded via {source_label}."

        suggested_rev = ProposalRevisionCreate(
            title=title,
            proposal_type=prop_type,
            product_name=product_name,
            product_code=product_code,
            grade_code=grade_code,
            service_code=service_code,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            currency=currency,
            total_value=quantity * unit_price if unit_price is not None else None,
            payment_terms=payment_terms,
            delivery_location=delivery_location,
            incoterm=incoterm,
            delivery_timeline_days=delivery_timeline_days,
            governing_standards=governing_standards,
            special_conditions=special_conditions,
            notes=notes,
            revision_summary=revision_summary,
        )

        return ProposalDraftPrefillResponse(
            conversation_id=conversation.id,
            recipient_id=payload.recipient_id,
            proposer_role=proposer_role,
            recipient_role=recipient_role,
            suggested_revision=suggested_rev,
            grounding_source=grounding_source,
            confidence_score=confidence_score,
        )

    @staticmethod
    async def _extract_commercial_parameters(
        db: AsyncSession,
        biz_ctx: Optional[ConversationBusinessContext],
        proposer_profile: Optional[BusinessProfile],
        recipient_profile: Optional[BusinessProfile],
        proposer_role: CommercialRole,
        messages: List[Message],
        current_user: User,
        recipient: User,
    ) -> Tuple[
        str,  # product_name
        Optional[str],  # product_code
        Optional[str],  # grade_code
        Optional[str],  # service_code
        Decimal,  # quantity
        str,  # unit
        Optional[Decimal],  # unit_price
        str,  # currency
        str,  # delivery_location
        int,  # delivery_timeline_days
        str,  # payment_terms
        str,  # incoterm
        List[str],  # governing_standards
        Optional[str],  # special_conditions
        Optional[str],  # notes
        str,  # grounding_source
        float,  # confidence_score
    ]:
        """Hierarchical parameter extraction: Brief -> Catalog Offerings -> Dialogue Synthesis -> Defaults."""
        # ---------------------------------------------------------
        # Case A: Grounded via ConversationBusinessContext Snapshot
        # ---------------------------------------------------------
        if biz_ctx and biz_ctx.product_name:
            gov_standards = []
            if biz_ctx.grade_code:
                std = await BusinessProfileService.get_governing_standard_for_grade(db, biz_ctx.grade_code)
                if std:
                    gov_standards.append(std)
                elif "_" in biz_ctx.grade_code:
                    gov_standards.append(biz_ctx.grade_code.replace("_", " "))

            qty = Decimal(str(biz_ctx.quantity)) if biz_ctx.quantity and biz_ctx.quantity > 0 else Decimal("100")
            unit_val = biz_ctx.unit or "MT"
            price = Decimal(str(biz_ctx.target_price_indication)) if biz_ctx.target_price_indication else None

            # Fallback price from offering if missing in brief
            if price is None and proposer_profile and proposer_profile.offerings:
                for off in proposer_profile.offerings:
                    if off.is_active and (off.indicative_price_min or off.indicative_price_max):
                        price = off.indicative_price_min or off.indicative_price_max
                        break

            loc = biz_ctx.delivery_location or (
                proposer_profile.hq_city if proposer_profile and proposer_profile.hq_city else "Bhiwandi Central Warehousing, Maharashtra"
            )
            timeline = biz_ctx.timeline_days if biz_ctx.timeline_days and biz_ctx.timeline_days > 0 else 30
            incoterm_val = "DDP" if proposer_role == CommercialRole.SUPPLIER else "EXW"

            return (
                biz_ctx.product_name,
                biz_ctx.product_code,
                biz_ctx.grade_code,
                biz_ctx.service_code,
                qty,
                unit_val,
                price if price is not None else Decimal("3200"),
                "INR",
                loc,
                timeline,
                "20% Advance against Proforma, 80% upon delivery & inspection",
                incoterm_val,
                gov_standards,
                biz_ctx.inquiry_notes or "Quality certificate required with each shipment.",
                f"Generated from commercial context brief {biz_ctx.inquiry_type}.",
                "CONTEXT_BRIEF",
                0.95,
            )

        # ---------------------------------------------------------
        # Case B: Grounded via Catalog Offerings / Requirements
        # ---------------------------------------------------------
        # If proposer is supplier/vendor, look at their active offerings
        offering: Optional[BusinessOffering] = None
        if proposer_profile and proposer_profile.offerings:
            active_offs = [o for o in proposer_profile.offerings if o.is_active]
            if active_offs:
                offering = active_offs[0]

        # If recipient has requirements, see if we can match
        if not offering and recipient_profile and recipient_profile.requirements:
            active_reqs = [r for r in recipient_profile.requirements if r.is_active]
            if active_reqs:
                req = active_reqs[0]
                # Synthesize from requirement
                qty = req.required_monthly_volume or Decimal("200")
                unit_val = req.volume_unit or "MT"
                loc = req.target_delivery_city or "Mumbai Logistics Hub"
                timeline = req.max_acceptable_lead_time_days or 21
                return (
                    req.custom_requirement_title,
                    req.product_code,
                    req.grade_code,
                    req.service_code,
                    Decimal(str(qty)),
                    unit_val,
                    Decimal("3500"),
                    "INR",
                    loc,
                    timeline,
                    "30% Advance, 70% against Bill of Lading",
                    "DDP",
                    [],
                    "Material must comply with procurement specifications.",
                    "Drafted from buyer's active procurement requirements.",
                    "CATALOG_OFFERING",
                    0.85,
                )

        if offering:
            gov_standards = []
            if offering.grade_code:
                std = await BusinessProfileService.get_governing_standard_for_grade(db, offering.grade_code)
                if std:
                    gov_standards.append(std)

            qty = offering.minimum_order_quantity or Decimal("100")
            unit_val = offering.capacity_unit or "MT"
            price = offering.indicative_price_min or offering.indicative_price_max or Decimal("3000")
            curr = offering.price_currency or "INR"
            loc = offering.geographic_coverage[0] if offering.geographic_coverage else "Ex-Works Facility"
            timeline = offering.lead_time_days or 21
            incoterm_val = offering.pricing_basis or "EXW"

            return (
                offering.custom_product_title,
                offering.product_code,
                offering.grade_code,
                offering.service_code,
                Decimal(str(qty)),
                unit_val,
                Decimal(str(price)),
                curr,
                loc,
                timeline,
                "25% Advance, 75% against Dispatch Notice",
                incoterm_val,
                gov_standards,
                offering.specifications_text,
                "Auto-filled from verified catalog offering specifications.",
                "CATALOG_OFFERING",
                0.85,
            )

        # ---------------------------------------------------------
        # Case C: Grounded via Dialogue Messages Synthesis
        # ---------------------------------------------------------
        if messages:
            extracted = ProposalAgentService._extract_from_dialogue_turns(messages)
            if extracted:
                return (
                    extracted["product_name"],
                    None,
                    None,
                    None,
                    extracted["quantity"],
                    extracted["unit"],
                    extracted["unit_price"],
                    "INR",
                    extracted["delivery_location"],
                    extracted["timeline_days"],
                    extracted["payment_terms"],
                    "DDP",
                    [],
                    None,
                    "Synthesized from mutual dialogue message history.",
                    "DIALOGUE_SYNTHESIS",
                    0.75,
                )

        # ---------------------------------------------------------
        # Case D: Sensible Profile-Default Fallback
        # ---------------------------------------------------------
        proposer_co = current_user.company_name or "Commercial Partner"
        fallback_product = f"{proposer_co} Commercial Supply"
        loc = (proposer_profile.hq_city if proposer_profile and proposer_profile.hq_city else "Pune, Maharashtra")

        return (
            fallback_product,
            None,
            None,
            None,
            Decimal("100"),
            "Units",
            Decimal("2500"),
            "INR",
            loc,
            30,
            "50% Advance, 50% upon Delivery",
            "EXW",
            [],
            None,
            "Standard bilateral terms template.",
            "PROFILE_DEFAULT",
            0.60,
        )

    @staticmethod
    def _extract_from_dialogue_turns(messages: List[Message]) -> Optional[Dict[str, Any]]:
        """Parse chat history for mentioned quantity, price, unit, and terms."""
        combined_text = " \n ".join([m.content for m in messages if m.content])
        if not combined_text.strip():
            return None

        # Extract quantity and unit
        qty_match = re.search(r"(\d+(?:\.\d+)?)\s*(MT|Tons?|Tonnes?|KG|Bags?|Units?|Truckloads?)", combined_text, re.IGNORECASE)
        qty = Decimal(qty_match.group(1)) if qty_match else Decimal("250")
        unit = qty_match.group(2).upper() if qty_match else "MT"
        if "TON" in unit:
            unit = "MT"

        # Extract price
        price_match = re.search(r"(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*(?:\.\d+)?)", combined_text, re.IGNORECASE)
        if not price_match:
            price_match = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:INR|per\s+MT|per\s+ton)", combined_text, re.IGNORECASE)
        
        price = Decimal(price_match.group(1).replace(",", "")) if price_match else Decimal("3400")

        # Extract location
        loc_match = re.search(r"(?:delivery\s+(?:to|at)|site:?|destination:?)\s+([A-Za-z\s]{3,35})(?:\.|\,|\n|within|by|$)", combined_text, re.IGNORECASE)
        loc = loc_match.group(1).strip() if loc_match else "Consignee Designated Site"

        # Extract timeline
        time_match = re.search(r"(\d+)\s*(?:calendar\s*)?(?:days?|weeks?)", combined_text, re.IGNORECASE)
        timeline = int(time_match.group(1)) if time_match else 21
        if "week" in (time_match.group(0).lower() if time_match else ""):
            timeline = timeline * 7

        # Extract commodity name
        product_name = "Commercial Grade Commodity"
        for kw in ["Portland Slag Cement", "Ready Mix Concrete", "Fly Ash", "OPC 53", "PPC Cement", "Granulated Blast Furnace Slag", "Aggregate 20mm"]:
            if kw.lower() in combined_text.lower():
                product_name = kw
                break

        return {
            "product_name": product_name,
            "quantity": qty,
            "unit": unit,
            "unit_price": price,
            "delivery_location": loc,
            "timeline_days": min(max(timeline, 1), 365),
            "payment_terms": "30% Advance, 70% against delivery & inspection",
        }
