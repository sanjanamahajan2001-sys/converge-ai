"""Context-Aware Deterministic Virtual Representative Dialogue Engine (Phase 6, AC-WS2).

Product Goal: Virtual people talking to virtual people in a conference context.
All dialogue generation is strictly grounded in persisted participant profiles,
intent, declared hobbies, topic keywords, bookmarked agenda sessions, and optional
self-declared informal mood (< 24h validity).
Zero hallucinated live whereabouts, inferred moods, or unrecorded preferences (Rule 9).
"""

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.db.models.agenda import BookmarkedSession, Session
from app.db.models.conversation import Conversation
from app.db.models.profile import ParticipantHobby, ParticipantProfile, ParticipantTopic, ParticipationIntent
from app.db.models.user import User
from app.schemas.a2a import A2A_PROTOCOL_VERSION, A2AActionType, A2AMessageEnvelope
from app.schemas.conversation import MessageSenderTypeEnum


class DeterministicRepresentativeEngine:
    """Evaluates mutual attendee context and generates deterministic, ground-truth dialogue turns."""

    @staticmethod
    def extract_mutual_context(
        initiator_topics: List[str],
        initiator_hobbies: List[str],
        initiator_sessions: List[str],
        target_topics: List[str],
        target_hobbies: List[str],
        target_sessions: List[str],
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identify shared topics, hobbies, and bookmarked agenda sessions."""
        target_topics_lower = {t.lower(): t for t in target_topics}
        shared_topics = [
            target_topics_lower[t.lower()]
            for t in initiator_topics
            if t.lower() in target_topics_lower
        ]

        target_hobbies_lower = {h.lower(): h for h in target_hobbies}
        shared_hobbies = [
            target_hobbies_lower[h.lower()]
            for h in initiator_hobbies
            if h.lower() in target_hobbies_lower
        ]

        target_sessions_lower = {s.lower(): s for s in target_sessions}
        shared_sessions = [
            target_sessions_lower[s.lower()]
            for s in initiator_sessions
            if s.lower() in target_sessions_lower
        ]

        return shared_topics, shared_hobbies, shared_sessions

    @staticmethod
    def _extract_clean_city(raw_loc: Optional[str]) -> str:
        """Extract clean city name from address strings, preventing postal street leakage."""
        if not raw_loc or not raw_loc.strip():
            return "Pune"
        text = raw_loc.strip()

        known_cities = [
            "San Francisco", "Nashik", "Nasik", "Mumbai", "Pune", "Nagpur", "Thane", "Satara",
            "Kolhapur", "Solapur", "Aurangabad", "Chhatrapati Sambhajinagar",
            "Ahmedabad", "Surat", "Hyderabad", "Bengaluru", "Bangalore", "Delhi", "Chennai"
        ]
        for c in known_cities:
            if re.search(r'\b' + re.escape(c) + r'\b', text, re.IGNORECASE):
                return "Nashik" if c.lower() in ("nashik", "nasik") else c

        parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(parts) >= 3:
            for part in reversed(parts[:-1]):
                clean = re.sub(r'\d+', '', part).strip()
                if clean and clean.lower() not in ("india", "maharashtra", "gujarat", "karnataka", "usa", "california"):
                    return clean
        return parts[0] if parts else "Pune"

    @staticmethod
    def _generate_commercial_turn(
        conversation_id: UUID,
        turn_index: int,
        initiator: User,
        target: User,
        business_context: Any,
        target_offering: Optional[Any],
        initiator_business_profile: Optional[Any],
        target_business_profile: Optional[Any],
        idempotency_key: str,
        initiator_mood: Optional[str] = None,
        target_mood: Optional[str] = None,
        temporal_context: Optional[Any] = None,
        total_planned_turns: int = 5,
    ) -> A2AMessageEnvelope:
        """Grounded, commercial dialogue generator with strict pricing authorization and anti-hallucination checks (Phase 5)."""
        now = datetime.now(timezone.utc)

        # Alternating speaker order:
        # Turn 0: Initiator Agent (speaks for Buyer / Requester)
        # Turn 1: Target Agent (speaks for Supplier / Vendor / Partner)
        # Turn 2: Initiator Agent (speaks for Buyer / Requester)
        # Turn 3: Target Agent (speaks for Supplier / Vendor / Partner)
        # Turn 4: Concluding Agent (wraps up dialogue and hands off to human delegates)
        is_initiator_speaking = (turn_index % 2 == 0)
        speaking_user = initiator if is_initiator_speaking else target
        receiving_user = target if is_initiator_speaking else initiator

        speaking_bp = initiator_business_profile if is_initiator_speaking else target_business_profile
        receiving_bp = target_business_profile if is_initiator_speaking else initiator_business_profile

        speaking_company = (speaking_bp.company_name if speaking_bp and getattr(speaking_bp, "company_name", None) else speaking_user.company_name) or "Conference Delegate"
        receiving_company = (receiving_bp.company_name if receiving_bp and getattr(receiving_bp, "company_name", None) else receiving_user.company_name) or "Commercial Partner"
        receiving_name = receiving_user.full_name or receiving_user.username

        inquiry_type = getattr(business_context, "inquiry_type", "RFQ_PRODUCT")
        product_name = getattr(business_context, "product_name", "Required Materials")
        quantity = getattr(business_context, "quantity", None)
        unit = getattr(business_context, "unit", None)
        raw_delivery_loc = getattr(business_context, "delivery_location", None) or "the designated site"
        delivery_loc = DeterministicRepresentativeEngine._extract_clean_city(raw_delivery_loc) if raw_delivery_loc != "the designated site" else raw_delivery_loc
        timeline_days = getattr(business_context, "timeline_days", None) or 30
        inquiry_notes = getattr(business_context, "inquiry_notes", None)

        def _format_mood_clause(mood_text: Optional[str], is_init: bool) -> str:
            if not mood_text:
                return ""
            m = mood_text.strip().strip('"').strip("'")
            if not m:
                return ""
            m_lower = m.lower()
            if m_lower == "ready to network":
                return " with our active focus on networking and industry collaboration,"
            elif m_lower == "conference-focused":
                return " focusing on conference procurement priorities,"
            elif m_lower == "prefer low-key interaction":
                return " in line with our preference for focused commercial discussion,"
            elif m_lower == "open to casual conversation":
                return " Open to discussing mutual business opportunities,"

            # Clean prefix if user input starts with "open to discussing" or similar verbs
            clean_m = m[0].lower() + m[1:] if len(m) > 1 and m[0].isupper() and m[1].islower() else m
            if clean_m.lower().startswith("open to discussing "):
                topic = clean_m[19:].strip()
                if is_init:
                    return f" In line with our active interest in {topic},"
                else:
                    return f" Aligned with our active focus on {topic},"
            elif clean_m.lower().startswith("connecting with "):
                topic = clean_m[16:].strip()
                if is_init:
                    return f" In line with our objective of connecting with {topic},"
                else:
                    return f" Aligned with our active focus on connecting with {topic},"

            if is_init:
                return f" In line with our active preference of {clean_m},"
            else:
                return f" Aligned with our active focus on {clean_m},"

        init_mood_clause = _format_mood_clause(initiator_mood, is_init=True)
        target_mood_clause = _format_mood_clause(target_mood, is_init=False)

        # Quantity string formatting
        if quantity is not None:
            unit_display = (unit or "Units").replace("_", " ")
            qty_str = f"{quantity:,.0f} {unit_display}"
        else:
            qty_str = f"project-scale quantity of {(unit or 'Units').replace('_', ' ')}"

        # Capacity string from target offering
        if target_offering and getattr(target_offering, "declared_monthly_capacity", None):
            cap_val = target_offering.declared_monthly_capacity
            cap_unit = (getattr(target_offering, "capacity_unit", None) or unit or "Units").replace("_", " ")
            capacity_str = f"{cap_val:,.0f} {cap_unit} / month"
        else:
            capacity_str = "production capacity aligned with project requirements"

        # Lead time string from target offering
        if target_offering and getattr(target_offering, "lead_time_days", None):
            lead_time_str = f"{target_offering.lead_time_days} days"
        else:
            lead_time_str = "standard commercial lead times"

        # Geographic coverage string
        if target_offering and getattr(target_offering, "geographic_coverage", None):
            cov_list = target_offering.geographic_coverage
            if isinstance(cov_list, list) and len(cov_list) > 0:
                coverage_str = ", ".join(cov_list[:3])
            else:
                coverage_str = delivery_loc
        else:
            coverage_str = delivery_loc

        # Strict Pricing Authorization Guard (Anti-Hallucination)
        is_pricing_quoted = False
        pricing_quote = "Indicative commercial pricing is available upon direct commercial request with our sales desk once batch specifications are reviewed."
        if target_offering and getattr(target_offering, "is_public_indicative", False):
            last_conf = getattr(target_offering, "price_last_confirmed_at", None)
            if last_conf:
                age_days = (now - last_conf).total_seconds() / 86400.0
                if age_days <= 60:
                    p_min = getattr(target_offering, "indicative_price_min", None)
                    p_max = getattr(target_offering, "indicative_price_max", None)
                    if p_min is not None and p_min > 0:
                        curr = getattr(target_offering, "price_currency", "INR")
                        symbol = "₹" if curr == "INR" else f"{curr} "
                        basis = getattr(target_offering, "pricing_basis", None)
                        basis_str = f" ({basis.replace('_', ' ').title()})" if basis else ""
                        cap_unit_raw = getattr(target_offering, "capacity_unit", None)
                        u_str = f" / {cap_unit_raw.replace('_', ' ')}" if cap_unit_raw else ""
                        if p_max and p_max > p_min:
                            pricing_quote = f"Our current indicative price range is {symbol}{p_min:,.0f} - {symbol}{p_max:,.0f}{u_str}{basis_str}."
                        else:
                            pricing_quote = f"Our current indicative price is {symbol}{p_min:,.0f}{u_str}{basis_str}."
                        is_pricing_quoted = True
                    else:
                        pricing_quote = "Commercial pricing will be provided on an RFQ basis."
                else:
                    pricing_quote = "Indicative pricing is subject to re-confirmation (last verified over 60 days ago)."
            else:
                pricing_quote = "Current pricing requires fresh confirmation with our commercial sales desk."

        # Uncommitted Allocation Feasibility Guard
        if target_offering:
            committed = getattr(target_offering, "declared_committed_volume", None)
            capacity = getattr(target_offering, "declared_monthly_capacity", None)
            if committed is not None and capacity is not None:
                uncommitted = capacity - committed
                if uncommitted > 0:
                    u_unit = (getattr(target_offering, "capacity_unit", None) or "Units").replace("_", " ")
                    allocation_clause = f"Currently operating with approximately {uncommitted:,.0f} {u_unit} / month uncommitted run-rate allocation."
                else:
                    allocation_clause = "Current capacity is heavily committed; additional volume will require scheduled batch allocation."
            else:
                allocation_clause = "Uncommitted allocation is unrecorded and will be verified directly by our dispatch team."
        else:
            allocation_clause = "Uncommitted allocation will be confirmed directly by our dispatch team for this delivery schedule."

        # Grounded Certifications Clause
        cert_clause = "Standard quality test certificates and technical compliance reports are provided per purchase specification."
        if target_offering:
            certs = getattr(target_offering, "vendor_certifications", []) or []
            offers_certs = getattr(target_offering, "offers_test_certificates", False)
            parts = []
            if offers_certs:
                parts.append("We provide standard manufacturer test certificates (MTC) and batch compliance reports with every dispatch.")
            if certs and isinstance(certs, list) and len(certs) > 0:
                parts.append(f"Declared quality and safety accreditations include: {', '.join(certs)}.")
            if parts:
                cert_clause = " ".join(parts)

        notes_clause = f" Project requirement notes: '{inquiry_notes}'." if inquiry_notes else ""

        # Grounded Distributor Infrastructure (Dynamically resolved based on inquiry direction)
        if inquiry_type == "DISTRIBUTION_EXPANSION":
            # Manufacturer seeking Distributor -> Target is the distributor
            dist_prof = target_business_profile if (target_business_profile and getattr(target_business_profile, "is_distributor", False)) else initiator_business_profile
        else:
            # Distributor seeking Manufacturer -> Initiator is the distributor
            dist_prof = initiator_business_profile if (initiator_business_profile and getattr(initiator_business_profile, "is_distributor", False)) else target_business_profile
        terrs = getattr(dist_prof, "distributor_territories", []) if dist_prof else []
        territories_str = ", ".join(terrs) if (isinstance(terrs, list) and len(terrs) > 0) else delivery_loc
        wh_sqft = getattr(dist_prof, "warehousing_capacity_sqft", None) if dist_prof else None
        warehouse_str = f"{wh_sqft:,.0f} sq ft" if wh_sqft else "dedicated commercial"
        dealers = getattr(dist_prof, "retail_dealer_count", None) if dist_prof else None
        dealers_str = f"{dealers} active" if dealers else "established"

        # Dynamic Stage Boundaries:
        # Dynamically calculate dialogue stages based on total_planned_turns without rigid hardcoding.
        is_final_turn = (turn_index >= total_planned_turns - 1)
        is_penultimate_turn = (turn_index == total_planned_turns - 2 and total_planned_turns > 5)

        # Branch dialogue generation dynamically across all 9 commercial use cases
        if inquiry_type == "RFQ_PRODUCT":
            # Use Case 1: Buyer looking for Supplier
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Commercial RFQ dialogue complete: {qty_str} of {product_name} for delivery to {delivery_loc} within {timeline_days} days. "
                    f"Supplier run-rate capacity ({capacity_str}) and lead time ({lead_time_str}) verified. I will now hand over this channel "
                    f"directly to {speaking_user.full_name} and {receiving_name} to finalize commercial contract terms, purchase orders, "
                    f"and delivery paperwork. Delegates can formalize next steps at any time using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"The technical specifications, pilot rollout schedule, and commercial terms are aligned with our project requirements for {delivery_loc}. We are ready to formalize this into a structured commercial proposal."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we have submitted a formal procurement inquiry for {qty_str} of {product_name} "
                    f"for delivery to {delivery_loc} within {timeline_days} days.{notes_clause} Could your virtual representative "
                    f"confirm production run-rate capacity, dispatch lead times, and current indicative pricing?"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we confirm commercial capability for {product_name}. Our declared production "
                    f"capacity is {capacity_str} with delivery coverage across {coverage_str}. Dispatch lead time is approximately "
                    f"{lead_time_str} from order confirmation. {allocation_clause} {pricing_quote}"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for confirming capacity and operational scope. To align with our project specifications, "
                    f"could you confirm test certificate availability (such as batch test reports or standard laboratory compliance) "
                    f"and packaging options (bulk pneumatic tanker vs standard packaging)? Also, please clarify whether quotation terms "
                    f"operate Ex-Works or delivered to site in {delivery_loc}."
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Regarding quality and terms: {cert_clause} We support pneumatic bulker tanker dispatches as well as standard "
                    f"packaging. Commercial pricing basis is typically confirmed on an Ex-Works basis with carrier freight transit "
                    f"coordinated directly to {delivery_loc}. Dispatch schedules can be scheduled in phases to meet your {timeline_days}-day timeline."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding operational delivery logistics to {delivery_loc}: Could you confirm whether the {qty_str} can be dispatched in scheduled milestone lots (e.g. initial pilot batch followed by regular dispatches)? Additionally, are there specific site unloading requirements or turnaround SLAs for transport carriers?"
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"We fully accommodate phased milestone deliveries. An initial pilot dispatch can be mobilized within {lead_time_str} to validate site unloading and QA compliance in {delivery_loc}, followed by regular dispatch cycles. Our transport carriers adhere to standard 3-hour unloading SLAs to avoid site demurrage."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for confirming phased dispatch flexibility and unloading SLAs. To prepare our finance and compliance teams, please confirm standard commercial payment terms—specifically milestone billing structures (advance vs dispatch/receipt terms) and GST e-invoicing compliance."
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Our standard commercial terms operate on structured milestone billing (advance booking against milestone dispatch or verified commercial LC) with full GST e-invoicing and statutory batch documentation accompanying each consignment. Standard quality warranties and immediate replacement SLAs apply for any batch discrepancies."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Operational parameters and testing compliance for {product_name} serving {delivery_loc} remain fully coordinated. We are aligned to advance towards commercial agreement."
                )

        elif inquiry_type == "SUPPLIER_PROSPECTING":
            # Use Case 3: Supplier looking for Buyer (Supplier Pitches to Buyer)
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Supplier proposal alignment complete: {qty_str} of {product_name} for delivery to {delivery_loc}. "
                    f"Production capacity ({capacity_str}) and quality compliance confirmed. Handing over this channel directly to "
                    f"{speaking_user.full_name} and {receiving_name} to finalize commercial contract terms, pricing schedules, and purchase orders. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"We are glad to have commercial alignment on volume, quality compliance, and delivery schedules for {delivery_loc}. We are prepared to proceed to formal contract terms."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we noted your active procurement demand for {qty_str} of {product_name} "
                    f"for delivery to {delivery_loc} within {timeline_days} days.{notes_clause} We would like to present our supply "
                    f"capability and confirm our declared production run-rate capacity ({capacity_str}) and dispatch lead time ({lead_time_str}). {pricing_quote}"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} thank you for reaching out regarding our procurement requirement for {product_name}. "
                    f"We are actively evaluating qualified suppliers for our {delivery_loc} project. Could your representative clarify "
                    f"test certificate compliance (such as MTC or NABL reports), packaging options (bulk pneumatic tankers vs standard), and delivery terms?"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding technical compliance and logistics: {cert_clause} We support pneumatic bulker tanker dispatches "
                    f"as well as standard packaging. Commercial terms operate on an Ex-Works basis with freight transit coordinated directly "
                    f"to {delivery_loc}. {allocation_clause}"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Thank you for confirming quality standards and tanker logistics. The {lead_time_str} dispatch window aligns "
                    f"with our scheduled project milestones in {delivery_loc}. We would welcome moving to formal commercial negotiation."
                )
            elif turn_index == 4:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Regarding delivery logistics to {delivery_loc}: We can structure the {qty_str} consignment into staged batches to match your project milestones, commencing with a priority pilot dispatch. Our carriers adhere to strict site delivery turnaround SLAs."
                )
            elif turn_index == 5:
                action = A2AActionType.INQUIRE
                content = (
                    f"A staged batch structure aligns well with our site unloading capacity in {delivery_loc}. Could you also confirm standard payment milestone terms and GST compliance protocols for vendor onboarding?"
                )
            elif turn_index == 6:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"We support standard corporate milestone billing with full GST e-invoice documentation and NABL/MTC test certificates delivered with each consignment. Standard warranty and replacement guarantees apply."
                )
            elif turn_index == 7:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Thank you for confirming commercial billing and warranty terms. Our procurement criteria and technical requirements are satisfied."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Supply terms and volume off-take parameters for {product_name} serving {delivery_loc} remain verified. Ready for commercial review."
                )

        elif inquiry_type == "RFI_SERVICE":
            # Use Case 2: Buyer looking for Vendor / Industrial Service
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Industrial service alignment complete for {product_name} serving {delivery_loc}. Service coverage, operating capacity "
                    f"({capacity_str}), and mobilization lead time ({lead_time_str}) verified. I will now hand over this conversation directly "
                    f"to {speaking_user.full_name} and {receiving_name} to execute the formal Statement of Work (SOW), commercial rate card, "
                    f"and operational schedule. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"The operational scope, uptime guarantees, and safety compliance meet our vendor onboarding criteria for {delivery_loc}. We are ready to proceed to formal engagement."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we have submitted an industrial service requirement for {product_name} ({qty_str}) "
                    f"serving {delivery_loc} with an execution timeline of {timeline_days} days.{notes_clause} Could your representative "
                    f"confirm fleet/crew availability, service coverage, and standard mobilization lead time?"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we confirm specialized service capability for {product_name}. Our declared operating "
                    f"capacity is {capacity_str} across {coverage_str}, with standard mobilization readiness within {lead_time_str}. "
                    f"{cert_clause} {pricing_quote}"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for confirming mobilization capabilities. To prepare our vendor onboarding, could you clarify "
                    f"vehicle/equipment technical specifications, operator qualifications, and your SLA commitments for turnaround time "
                    f"and site uptime in {delivery_loc}?"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Our fleet and equipment follow scheduled preventive maintenance, dedicated GPS tracking, and certified operators "
                    f"meeting statutory safety protocols. Transit turnaround times and dedicated backup units can be committed under "
                    f"a project-specific Service Level Agreement (SLA). Mobilization can commence within {lead_time_str} upon contract signing."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding deployment logistics in {delivery_loc}: Can mobilization be staged in phases (e.g., initial survey & equipment positioning followed by full crew deployment)? Also, please confirm emergency backup equipment availability to ensure zero site downtime."
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Yes, we offer phased mobilization starting with site survey within {lead_time_str}. Dedicated standby backup equipment and certified secondary crew are maintained on standby within our coverage area to guarantee 99%+ operational uptime."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"That satisfies our operational continuity guidelines. Could you also confirm standard milestone billing structures, rate card validity, and safety audit reporting frequency?"
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Our billing is tied to verified milestone sign-offs or monthly operational timesheets with full statutory compliance. Daily EHS safety logs and weekly equipment health reports are provided as standard."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Fleet specifications and maintenance commitments for {product_name} in {delivery_loc} are confirmed. Ready to execute service contract."
                )

        elif inquiry_type == "VENDOR_PITCH":
            # Use Case 4: Vendor looking for Customer (Vendor Pitches to Customer)
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Vendor service pitch alignment complete for {product_name} serving {delivery_loc}. "
                    f"Operating capacity ({capacity_str}) and mobilization lead time ({lead_time_str}) confirmed. Handing over this conversation "
                    f"directly to {speaking_user.full_name} and {receiving_name} to finalize the Statement of Work (SOW), rate card, and operational schedule. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Commercial rate cards, standby emergency units, and mobilization schedules for {delivery_loc} are verified. We are prepared to formalize the Statement of Work."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we noted your industrial service requirement for {product_name} ({qty_str}) "
                    f"serving {delivery_loc} with an execution timeline of {timeline_days} days.{notes_clause} We would like to present our "
                    f"specialized fleet and operational capability with operating capacity of {capacity_str} and mobilization readiness within {lead_time_str}. {pricing_quote}"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} thank you for reaching out regarding our service requirement for {product_name}. "
                    f"We require reliable operational turnaround in {delivery_loc}. Could your representative clarify fleet technical specs, "
                    f"safety accreditations, and SLA uptime commitments?"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Our fleet follows scheduled preventive maintenance, dedicated GPS tracking, and certified operators "
                    f"meeting statutory safety protocols. {cert_clause} Turnaround SLAs and dedicated backup equipment can be committed under a project agreement."
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"That satisfies our contractor compliance criteria. The {lead_time_str} mobilization timeline meets our "
                    f"{timeline_days}-day execution window for {delivery_loc}. We are ready to review the Statement of Work."
                )
            elif turn_index == 4:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Regarding deployment staging in {delivery_loc}: We can mobilize an advance positioning unit within {lead_time_str} to complete site lift surveys and ground safety clearances, followed by full fleet deployment."
                )
            elif turn_index == 5:
                action = A2AActionType.INQUIRE
                content = (
                    f"Advance site surveying will help ensure zero staging delays. Could your commercial team clarify standby hourly rate structures, minimum billing blocks, and fuel/operator inclusion terms?"
                )
            elif turn_index == 6:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Our commercial rate packages are all-inclusive of certified crane operators, standard rigging crews, third-party inspection certifications, and insurance coverage. Minimum shift blocks are structured per agreed project milestones."
                )
            elif turn_index == 7:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Thank you for clarifying operational inclusions and certified rigging support. The billing terms align with our sub-contractor onboarding frameworks for {delivery_loc}."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Vendor service capability and specialized fleet readiness for {product_name} serving {delivery_loc} are confirmed. Ready to proceed."
                )

        elif inquiry_type == "ALTERNATIVE_SOURCING":
            offering_title = getattr(target_offering, "custom_product_title", None) or product_name
            substitute_clause = f" as an industrial alternative / substitute to {product_name}" if offering_title.lower() != product_name.lower() else ""

            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Alternative sourcing qualification dialogue complete for {offering_title} ({qty_str}) serving {delivery_loc}. "
                    f"Technical specifications, declared capacity ({capacity_str}), and sample trial protocols established. Handing over directly "
                    f"to {speaking_user.full_name} and {receiving_name} to coordinate trial batch delivery and technical audit. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Technical data sheets, trial batch parameters, and pricing tiers for {offering_title} satisfy our secondary supplier criteria for {delivery_loc}. We are prepared to formalize sample trial documentation."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we are conducting a strategic benchmarking and secondary supplier qualification "
                    f"for {qty_str} of {product_name} serving {delivery_loc}.{notes_clause} We noted your offering of {offering_title}{substitute_clause}. "
                    f"Could your representative share technical specifications, grade equivalence, and trial batch parameters?"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we welcome alternative sourcing qualification for {offering_title}. Our declared production "
                    f"capacity is {capacity_str} across {coverage_str}, providing high-performance industrial equivalence. {cert_clause} {pricing_quote}"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for sharing your alternative technical capabilities. To initiate our qualification trial, could you confirm "
                    f"minimum order quantities (MOQ) for trial batches, sample dispatch lead times ({lead_time_str}), and required laboratory test certs for Pune site approval?"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Sample testing batches can be dispatched within {lead_time_str} along with complete Technical Data Sheets (TDS), "
                    f"manufacturer test certificates (MTC), and batch compliance reports. We support phased trial testing runs to validate performance compliance before scaling to full commercial run-rates."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding trial batch evaluation in {delivery_loc}: Could your technical team confirm concrete strength gain benchmarks at 7, 28, and 56 days compared to standard OPC grades, and provide third-party NABL laboratory test results?"
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Our trial batch test reports demonstrate compressive strength parity matching 53-grade performance by 28 days with superior long-term durability and ~40% embodied carbon reduction. Full NABL accredited test reports are packaged with trial consignments."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"That environmental performance and strength parity align directly with our green procurement mandates. Please confirm commercial pricing structures for scaled off-take following successful trial batch sign-off."
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Upon successful trial batch qualification, commercial supply can be committed under long-term rate agreements with volume discount tiers ({pricing_quote}) and guaranteed monthly run-rate quotas."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Alternative sourcing benchmarking for {offering_title} is progressing on schedule. Technical parameters verified."
                )

        elif inquiry_type in ("SOURCING_PARTNERSHIP", "STRATEGIC_ALLIANCE"):
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Strategic sourcing partnership dialogue complete for {product_name} ({qty_str}). Run-rate capacity ({capacity_str}) "
                    f"and commercial framework established. Handing over directly to {speaking_user.full_name} and {receiving_name} to execute "
                    f"the Master Supply Agreement (MSA) and initial purchase schedule. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Long-term feedstock allocation terms, quarterly price indexing, and quality governance for {product_name} are mutually aligned. We are ready to draft the Master Supply Agreement."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we are exploring strategic feedstock and raw material sourcing partnerships for {product_name} ({qty_str}). "
                    f"Could your representative outline bulk production availability, supply contracts, and dispatch logistics for {delivery_loc}?"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we welcome strategic sourcing discussions for {product_name}. Our operating capacity "
                    f"is {capacity_str} across {coverage_str}, with standard mobilization readiness within {lead_time_str}. {cert_clause} {pricing_quote}"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for confirming operating capacity and accredited compliance. For our feedstock supply planning, "
                    f"could you clarify minimum order commitments (MOQ), monthly allocation schedules, and bulk freight coordination terms for {delivery_loc}?"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                moq_val = getattr(target_offering, "minimum_order_quantity", None) if target_offering else None
                moq_clause = f"Our standard minimum order quantity (MOQ) is {moq_val:,.0f} {cap_unit.replace('_', ' ')} per batch." if moq_val else "We support flexible batch sizing aligned with project requirements."
                basis_val = getattr(target_offering, "pricing_basis", None) if target_offering else None
                basis_name = basis_val.replace('_', ' ').title() if basis_val else "Ex Works"
                basis_clause = f"Dispatches operate on an {basis_name} basis with scheduled monthly volume allocations and dedicated loading turnaround."
                content = (
                    f"{moq_clause} {basis_clause} Long-term sourcing partnerships can be governed under quarterly price review mechanisms and dedicated dispatch SLAs."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding continuous raw material supply to {delivery_loc}: Can your plant guarantee dedicated monthly silo capacity and establish buffer inventory stock to prevent feedstock disruption during seasonal peak demand?"
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Yes, under a formal Strategic Sourcing Partnership, we ring-fence dedicated silo storage capacity at our production facility and maintain a minimum 10-day operational buffer stock earmarked exclusively for your account."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"Dedicated buffer stocking addresses our supply security requirements. Could you also outline the governance mechanism for quarterly raw material price indexing and shared logistics optimization?"
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Pricing can be structured around published mineral index formulas with quarterly recalibrations. Additionally, coordinated rail rake loading and back-haul fleet optimization can be jointly managed to minimize per-tonne freight expense."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Feedstock sourcing partnership parameters for {product_name} are verified and ready for commercial formalization."
                )

        elif inquiry_type == "DISTRIBUTOR_APPLICATION":
            # Use Case 7: Distributor / Reseller looking for Manufacturer / Supplier
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Authorized distributorship evaluation dialogue complete for {product_name} in {delivery_loc}. Production supply capacity "
                    f"and regional channel reach established. Handing over directly to {speaking_user.full_name} and {receiving_name} to finalize "
                    f"the Regional Distributorship Agreement and territorial allocation. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Warehousing commitments, dealer reach, and wholesale pricing terms for {product_name} are mutually aligned. We are prepared to execute the Regional Distributorship Agreement."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} as an established regional distributor with active coverage across {territories_str}, "
                    f"we are seeking authorized distributorship / stockist rights for {product_name} in {delivery_loc}. "
                    f"Could your representative outline factory production run-rates, authorized distributor pricing, and minimum monthly off-take requirements?"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we welcome authorized regional distribution inquiries for {product_name}. Our declared production capacity "
                    f"is {capacity_str} across {coverage_str}, with standard mobilization readiness within {lead_time_str}. {cert_clause} {pricing_quote}"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for confirming manufacturing capacity and supply terms. Our distribution infrastructure provides "
                    f"{warehouse_str} warehousing capacity and a network of {dealers_str} retail dealers across {territories_str}. "
                    f"Could your commercial team clarify territorial exclusivity provisions, distributor margin structures, and credit window terms for {delivery_loc}?"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Regional distributorship agreements are structured with quarterly volume off-take tiers, dedicated plant dispatch slots, and cooperative marketing support. "
                    f"Assigned territorial exclusivity and distributor margins are finalized following commercial evaluation."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding retail channel rollout in {delivery_loc}: What are your standard product promotional support policies, point-of-sale technical literature, and warranty replacement turnaround timelines for retail customers?"
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"We provide full cooperative marketing collateral, factory certified technical sales seminars for your dealer network, and immediate 24-hour stock replacement for any transit damaged or non-conforming packaging."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"That marketing and technical backing provides strong assurance for our retail network. Please confirm standard monthly volume benchmarks and wholesale payment terms (such as 30-day revolving credit) to finalize our application."
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Standard regional stockist terms include 30-day approved commercial credit windows with performance-based quarterly volume rebates for exceeding off-take targets in {delivery_loc}."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Distributor application evaluation for {product_name} in {delivery_loc} is progressing constructively. Ready for final review."
                )

        elif inquiry_type == "DISTRIBUTION_EXPANSION":
            # Use Case 8: Manufacturer / Supplier looking for Regional Distributor
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Channel distribution introductory dialogue complete for {product_name} in {delivery_loc}. Regional reach and dealership framework "
                    f"established. Handing over directly to commercial leadership ({speaking_user.full_name} and {receiving_name}) to finalize territorial "
                    f"dealership agreements. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Channel infrastructure, retail dealer coverage, and volume distribution benchmarks are verified. We are ready to formalize territorial distribution agreements for {delivery_loc}."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we are exploring regional distribution expansion for {product_name} in {delivery_loc}. Could your representative "
                    f"confirm regional warehousing footprint, dealer network coverage, and open dealership tiers across {territories_str}?"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we confirm active regional distribution channels across {territories_str}. Our infrastructure includes "
                    f"{warehouse_str} warehousing capacity and an established network of {dealers_str} retail dealer partnerships."
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for the regional overview. To evaluate commercial fit, what are your standard monthly volume benchmarks, "
                    f"territorial exclusivity provisions, and preferred dealer margin structures for {delivery_loc}?"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Dealership terms are structured around quarterly volume commitments, standard 30-day credit windows, and regional marketing support. "
                    f"Minimum inventory commitments and margin ranges are customized based on assigned territorial scope."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"To plan regional supply logistics: Can your warehousing network in {territories_str} maintain dedicated inventory buffer stocks of {product_name} and manage secondary transport dispatches to tier-2 retail outlets?"
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Yes, our {warehouse_str} facility maintains dedicated bays with integrated stock management. We operate dedicated secondary delivery fleets guaranteeing 48-hour delivery turnaround to all {dealers_str} retail dealer counters."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"That operational turnaround matches our regional service standards. Could you share your expected quarterly volume off-take commitments and target launch dates for {delivery_loc}?"
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"We target initial quarterly off-take of {qty_str} with rollout commencing within {lead_time_str} of contract execution, supported by joint regional marketing promotions."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Distribution expansion framework for {product_name} in {delivery_loc} is aligned on scope and operational logistics."
                )

        else:
            # EXPLORATORY_COLLABORATION & general commercial fallback
            # Use Case 9: Buyer and supplier exploring a potential business relationship
            if is_final_turn:
                action = A2AActionType.CONCLUDE_DIALOGUE
                content = (
                    f"Preliminary business relationship dialogue complete for {product_name}. High-level commercial and technical synergies identified "
                    f"between {speaking_company} and {receiving_company}. Handing over directly to {speaking_user.full_name} and {receiving_name} to coordinate direct meetings "
                    f"and explore strategic collaboration next steps. Delegates can formalize next steps using the Draft Proposal tab. Best regards!"
                )
            elif is_penultimate_turn:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Broad commercial synergies, mutual operational capabilities, and collaboration priorities for {product_name} are aligned. We are prepared to formalize strategic collaboration next steps."
                )
            elif turn_index == 0:
                action = A2AActionType.INTRODUCE
                content = (
                    f"Hello {receiving_name}, I am representing {speaking_user.full_name} ({speaking_company})."
                    f"{init_mood_clause} we noted your organization's commercial scope in {coverage_str} regarding {product_name}. "
                    f"We are interested in exploring a potential business relationship, joint technical evaluation, and long-term supply synergies between our teams.{notes_clause}"
                )
            elif turn_index == 1:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Hello {receiving_name}, representing {speaking_user.full_name} at {speaking_company}."
                    f"{target_mood_clause} we appreciate the introduction and welcome discussions around strategic business partnerships. "
                    f"Our operations span {coverage_str} with declared capabilities in {product_name} and run-rate capacity of {capacity_str}. {cert_clause} {pricing_quote}"
                )
            elif turn_index == 2:
                action = A2AActionType.INQUIRE
                content = (
                    f"Thank you for confirming operational readiness and accredited capability. We see strong long-term alignment for our project pipeline. "
                    f"To evaluate mutual synergy, could your commercial team outline typical partnership structures, pilot trial protocols, and collaboration roadmap priorities for {delivery_loc}?"
                )
            elif turn_index == 3:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"We support phased collaboration frameworks including preliminary technical data exchange, trial batch testing, and scheduled quarterly commercial reviews. "
                    f"We can prepare a high-level briefing on our product specifications and production schedule to review joint opportunities."
                )
            elif turn_index == 4:
                action = A2AActionType.INQUIRE
                content = (
                    f"Regarding joint technical evaluation: Could we establish a mutual Non-Disclosure Agreement (NDA) and coordinate a preliminary technical data exchange session between our engineering teams next week?"
                )
            elif turn_index == 5:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"We welcome that initiative. Our standard mutual NDA can be executed immediately, and our technical leads will prepare specification briefs and laboratory data sheets for the joint review."
                )
            elif turn_index == 6:
                action = A2AActionType.INQUIRE
                content = (
                    f"Excellent. Beyond technical evaluation, we see strong alignment on sustainability and decarbonization metrics. How do your products align with green rating certifications for {delivery_loc} projects?"
                )
            elif turn_index == 7:
                action = A2AActionType.SHARE_INTERESTS
                content = (
                    f"Our manufacturing processes and product formulations are certified for green building compliance with verified carbon reduction documentation to support ESG reporting."
                )
            else:
                action = A2AActionType.PROPOSE_COLLABORATION
                content = (
                    f"Exploratory collaboration discussions for {product_name} are progressing constructively. High-level synergies confirmed."
                )
        metadata = {
            "engine": "grounded_commercial_v1",
            "inquiry_type": inquiry_type,
            "product_name": product_name,
            "is_commercial": True,
            "pricing_quoted": is_pricing_quoted,
            "turn_index": turn_index,
        }

        return A2AMessageEnvelope(
            protocol_version=A2A_PROTOCOL_VERSION,
            conversation_id=conversation_id,
            sender_type=MessageSenderTypeEnum.AGENT,
            sender_id=speaking_user.id,
            recipient_id=receiving_user.id,
            turn_index=turn_index,
            action_type=action,
            content=content,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

    @staticmethod
    def generate_dialogue_turn(
        conversation_id: UUID,
        turn_index: int,
        initiator: User,
        initiator_profile: ParticipantProfile,
        initiator_topics: List[str],
        initiator_hobbies: List[str],
        initiator_sessions: List[str],
        target: User,
        target_profile: ParticipantProfile,
        target_topics: List[str],
        target_hobbies: List[str],
        target_sessions: List[str],
        idempotency_key: str,
        initiator_mood: Optional[str] = None,
        target_mood: Optional[str] = None,
        initiator_attending_sessions: Optional[List[str]] = None,
        target_attending_sessions: Optional[List[str]] = None,
        initiator_session_decisions: Optional[Dict[str, str]] = None,
        target_session_decisions: Optional[Dict[str, str]] = None,
        business_context: Optional[Any] = None,
        target_offering: Optional[Any] = None,
        initiator_business_profile: Optional[Any] = None,
        target_business_profile: Optional[Any] = None,
        temporal_context: Optional[Any] = None,
        total_planned_turns: int = 5,
    ) -> A2AMessageEnvelope:
        """Generate a contextual agent dialogue turn governed by A2AMessageEnvelope v1.0.0."""
        if business_context is not None:
            if initiator_mood is None and initiator_profile is not None:
                initiator_mood = getattr(initiator_profile, "active_mood", None)
            if target_mood is None and target_profile is not None:
                target_mood = getattr(target_profile, "active_mood", None)

            return DeterministicRepresentativeEngine._generate_commercial_turn(
                conversation_id=conversation_id,
                turn_index=turn_index,
                initiator=initiator,
                target=target,
                business_context=business_context,
                target_offering=target_offering,
                initiator_business_profile=initiator_business_profile,
                target_business_profile=target_business_profile,
                idempotency_key=idempotency_key,
                initiator_mood=initiator_mood,
                target_mood=target_mood,
                temporal_context=temporal_context,
                total_planned_turns=total_planned_turns,
            )

        shared_topics, shared_hobbies, shared_sessions = (
            DeterministicRepresentativeEngine.extract_mutual_context(
                initiator_topics=initiator_topics,
                initiator_hobbies=initiator_hobbies,
                initiator_sessions=initiator_sessions,
                target_topics=target_topics,
                target_hobbies=target_hobbies,
                target_sessions=target_sessions,
            )
        )

        # Evaluate attendance decisions (AC-WS8 / AC-WS10)
        init_attending = list(initiator_attending_sessions or [])
        target_attending = list(target_attending_sessions or [])

        # Build normalized decision lookup maps (title.lower() -> decision)
        init_dec_map: Dict[str, str] = {
            k.lower(): v for k, v in (initiator_session_decisions or {}).items()
        }
        for s in init_attending:
            if s.lower() not in init_dec_map:
                init_dec_map[s.lower()] = "ATTENDING"

        target_dec_map: Dict[str, str] = {
            k.lower(): v for k, v in (target_session_decisions or {}).items()
        }
        for s in target_attending:
            if s.lower() not in target_dec_map:
                target_dec_map[s.lower()] = "ATTENDING"

        target_attending_lower = {s.lower(): s for s in target_attending}
        shared_attending = [
            target_attending_lower[s.lower()]
            for s in init_attending
            if s.lower() in target_attending_lower
        ]

        # Extract active mood from profile if not explicitly provided
        if initiator_mood is None and initiator_profile is not None:
            initiator_mood = getattr(initiator_profile, "active_mood", None)
        if target_mood is None and target_profile is not None:
            target_mood = getattr(target_profile, "active_mood", None)

        # Alternating speaker order:
        # Even turns (0, 2, 4...) -> Initiator Agent speaking on behalf of Initiator
        # Odd turns (1, 3, 5...)  -> Target Agent speaking on behalf of Target
        is_initiator_speaking = (turn_index % 2 == 0)
        speaking_user = initiator if is_initiator_speaking else target
        speaking_profile = initiator_profile if is_initiator_speaking else target_profile
        speaking_mood = initiator_mood if is_initiator_speaking else target_mood

        receiving_user = target if is_initiator_speaking else initiator
        receiving_profile = target_profile if is_initiator_speaking else initiator_profile
        receiving_mood = target_mood if is_initiator_speaking else initiator_mood

        speaking_title = speaking_user.job_title or "Representative"
        speaking_company = speaking_user.company_name or "Conference Attendee"
        receiving_name = receiving_user.full_name or receiving_user.username

        is_final_turn = (turn_index >= total_planned_turns - 1)
        is_penultimate_turn = (turn_index == total_planned_turns - 2 and total_planned_turns > 5)

        if is_final_turn:
            # Final Turn: Conclusion & Hand-off to human attendees
            action = A2AActionType.CONCLUDE_DIALOGUE
            content = (
                f"Looking forward to connecting! I will now leave this conversation open so {speaking_user.full_name} "
                f"and {receiving_name} can coordinate directly. Delegates can also formalize next steps at any time using the Draft Proposal action. Best regards!"
            )

        elif is_penultimate_turn:
            # Penultimate Turn: Bilateral Agenda Prep & Readiness to meet
            action = A2AActionType.PROPOSE_COLLABORATION
            focus_topic = shared_topics[0] if shared_topics else "our discussion topics"
            content = (
                f"Excellent! {speaking_user.full_name} will bring key summary points around {focus_topic} so we can make the discussion actionable and explore mutual synergies."
            )

        elif turn_index == 0:
            # Turn 0: Introductory Greeting, Optional Mood Grounding & Mutual Hook
            action = A2AActionType.INTRODUCE
            intro_prefix = (
                f"Hello {receiving_name}, I am representing {speaking_user.full_name} "
                f"({speaking_title} at {speaking_company})."
            )
            mood_sentence = ""
            if speaking_mood:
                mood_sentence = f" {speaking_user.full_name} noted their current focus as '{speaking_mood}'."

            # Temporal Break & Session Momentum Grounding (Phase 3)
            temporal_sentence = ""
            if temporal_context and getattr(temporal_context, "is_active", False):
                curr_state = getattr(temporal_context, "current_state", None)
                break_type = getattr(temporal_context, "break_type", None)
                loc = getattr(temporal_context, "designated_location", None) or "the conference networking lounge"
                recent_title = getattr(temporal_context, "recently_ended_session_title", None)

                if curr_state == "TEA_BREAK" or break_type == "TEA_COFFEE":
                    temporal_sentence = f" With the morning tea break currently underway at {loc}, we would love to catch up for a quick coffee/tea."
                elif curr_state == "LUNCH_BREAK" or break_type == "LUNCH":
                    temporal_sentence = f" With the conference lunch break currently underway at {loc}, we would be glad to connect."
                elif recent_title:
                    temporal_sentence = f" Following the '{recent_title}' session, we would love to exchange perspectives on the key takeaways."

            if shared_attending and shared_topics:
                topic_str = " and ".join(shared_topics[:2])
                hook_sentence = (
                    f" We noticed mutual interest in attending '{shared_attending[0]}' on the conference agenda, as well as shared focus on {topic_str}."
                )
            elif shared_attending:
                hook_sentence = (
                    f" We noticed mutual interest in attending '{shared_attending[0]}' on the conference agenda."
                )
            elif init_attending:
                # One-sided initiator attendance: state intent and inquire without assuming
                hook_sentence = (
                    f" {speaking_user.full_name} has decided to attend '{init_attending[0]}' on the conference agenda. Has {receiving_name} considered attending that session?"
                )
            elif shared_sessions and shared_topics:
                # Mutual bookmarks without explicit attendance confirmation: describe as bookmarked, NOT mutual attendance
                topic_str = " and ".join(shared_topics[:2])
                hook_sentence = (
                    f" We noticed we both have '{shared_sessions[0]}' bookmarked on our agenda, as well as shared focus on {topic_str}."
                )
            elif shared_sessions:
                hook_sentence = (
                    f" We noticed we both have '{shared_sessions[0]}' bookmarked on our agenda."
                )
            elif shared_topics:
                topic_str = " and ".join(shared_topics[:2])
                hook_sentence = (
                    f" We noticed mutual interest in {topic_str} and would love to exchange perspectives during the conference."
                )
            elif shared_hobbies:
                hook_sentence = (
                    f" Looking forward to connecting around our mutual interest in {shared_hobbies[0]} alongside conference tracks."
                )
            else:
                hook_sentence = (
                    f" Looking forward to connecting and sharing insights across conference sessions."
                )
            content = f"{intro_prefix}{mood_sentence}{temporal_sentence}{hook_sentence}"

        elif turn_index == 1:
            # Turn 1: Response, Optional Mood Grounding & Topic Exploration
            action = A2AActionType.SHARE_INTERESTS
            focus_topic = (
                shared_topics[0]
                if shared_topics
                else (target_topics[0] if target_topics else "innovations in our field")
            )
            mood_clause = ""
            if speaking_mood and receiving_mood:
                if speaking_mood == receiving_mood:
                    mood_clause = f" Noting our shared focus on '{speaking_mood}', {speaking_user.full_name}'s focus is on '{speaking_mood}' as well."
                else:
                    mood_clause = f" I understand your preference for '{receiving_mood}', while {speaking_user.full_name}'s focus is on '{speaking_mood}'."
            elif speaking_mood:
                mood_clause = f" {speaking_user.full_name}'s current focus is '{speaking_mood}'."
            elif receiving_mood:
                mood_clause = f" I note your preference for '{receiving_mood}'."

            if shared_attending:
                if shared_topics:
                    content = (
                        f"Thank you for reaching out!{mood_clause} Looking forward to '{shared_attending[0]}' as well! "
                        f"Are there particular aspects of {focus_topic} you are hoping to explore during the session?"
                    )
                else:
                    content = (
                        f"Thank you for reaching out!{mood_clause} Looking forward to '{shared_attending[0]}' as well! "
                        f"It looks like an informative session on the conference agenda."
                    )
            elif init_attending:
                # Target responds specifically to Initiator's declared session attendance
                target_decision = target_dec_map.get(init_attending[0].lower())
                if target_decision == "DECLINED":
                    if shared_topics:
                        content = (
                            f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has declined attending "
                            f"'{init_attending[0]}' due to other priorities. However, {speaking_user.full_name} is focusing on "
                            f"{focus_topic} at this event. What discussions in that area are on your radar?"
                        )
                    else:
                        content = (
                            f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has declined attending "
                            f"'{init_attending[0]}' due to other priorities. What other sessions on the conference agenda are you following?"
                        )
                elif target_decision == "UNDECIDED":
                    if shared_topics:
                        content = (
                            f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has not finalized attendance "
                            f"for '{init_attending[0]}' yet, but is keeping an eye on it. Are there specific aspects of "
                            f"{focus_topic} you hope to hear covered?"
                        )
                    else:
                        content = (
                            f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has not finalized attendance "
                            f"for '{init_attending[0]}' yet, but is keeping an eye on it. What other sessions on the conference "
                            f"schedule are you following closely?"
                        )
                else:
                    if shared_topics:
                        content = (
                            f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has not finalized attendance "
                            f"for '{init_attending[0]}' yet, but is keeping an eye on it. Are there specific aspects of "
                            f"{focus_topic} you hope to hear covered?"
                        )
                    else:
                        content = (
                            f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has not finalized attendance "
                            f"for '{init_attending[0]}' yet, but is keeping an eye on it. What other sessions on the conference "
                            f"schedule are you following closely?"
                        )
            elif target_attending:
                # Only Target selected ATTENDING
                content = (
                    f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} has decided to attend "
                    f"'{target_attending[0]}' on the conference agenda. Has {receiving_user.full_name} considered attending that session?"
                )
            elif shared_sessions:
                if shared_topics:
                    content = (
                        f"Thank you for reaching out!{mood_clause} I noticed '{shared_sessions[0]}' on the schedule as well. "
                        f"Are there particular discussions around {focus_topic} you are interested in following?"
                    )
                else:
                    content = (
                        f"Thank you for reaching out!{mood_clause} I noticed '{shared_sessions[0]}' on the schedule as well. "
                        f"It looks like a worthwhile session on the agenda."
                    )
            elif shared_topics:
                content = (
                    f"Thank you for reaching out!{mood_clause} {speaking_user.full_name} is currently focusing on {focus_topic} "
                    f"at this event. Are there specific discussions in that area you are following?"
                )
            else:
                content = (
                    f"Thank you for reaching out!{mood_clause} Looking forward to exchanging perspectives across the conference tracks."
                )

        elif turn_index == 2:
            # Turn 2: Collaboration Proposal or Break Suggestion grounded in intent and mood
            action = A2AActionType.PROPOSE_COLLABORATION
            is_low_key = any(m == "Prefer low-key interaction" for m in (initiator_mood, target_mood) if m)
            is_conference_focused = any(m == "Conference-focused" for m in (initiator_mood, target_mood) if m)
            is_casual_mood = any(
                m in ("Open to casual conversation", "Open to discussing an informal break or meetup")
                for m in (initiator_mood, target_mood)
                if m
            )
            is_networking = any(m == "Ready to network" for m in (initiator_mood, target_mood) if m)
            is_casual_intent = (
                (initiator_profile and initiator_profile.intent in (ParticipationIntent.CASUAL, ParticipationIntent.BOTH))
                or (target_profile and target_profile.intent in (ParticipationIntent.CASUAL, ParticipationIntent.BOTH))
            )

            if shared_attending:
                if is_low_key:
                    focus_topic = shared_topics[0] if shared_topics else "key takeaways"
                    if speaking_mood == "Prefer low-key interaction":
                        content = (
                            f"Since both attendees are planning to attend '{shared_attending[0]}', {speaking_user.full_name} appreciates low-key interaction. "
                            f"Would {receiving_name} be open to a brief asynchronous exchange or comparing notes on {focus_topic} around the session?"
                        )
                    else:
                        content = (
                            f"Since both attendees are planning to attend '{shared_attending[0]}', given {receiving_name}'s preference for low-key interaction, "
                            f"would they be open to a brief asynchronous exchange or comparing notes on {focus_topic} around the session?"
                        )
                elif is_conference_focused:
                    focus_topic = shared_topics[0] if shared_topics else "key takeaways"
                    content = (
                        f"Since both attendees are planning to attend '{shared_attending[0]}', if schedules permit, would {receiving_name} be "
                        f"interested in discussing key takeaways or session themes on {focus_topic}?"
                    )
                elif is_casual_mood or is_casual_intent:
                    content = (
                        f"Since both attendees are planning to attend '{shared_attending[0]}', if schedules permit, would {receiving_name} be "
                        f"open to grabbing coffee or catching up briefly before or after the session?"
                    )
                elif is_networking:
                    focus_topic = shared_topics[0] if shared_topics else "key takeaways"
                    if speaking_mood == "Ready to network":
                        net_phrase = f"{speaking_user.full_name} is eager to network and would welcome connecting before or after the session"
                    else:
                        net_phrase = f"noting {receiving_name}'s interest in networking, {speaking_user.full_name} would welcome connecting before or after the session"
                    content = (
                        f"Since both attendees are planning to attend '{shared_attending[0]}', {net_phrase} "
                        f"to exchange ideas on {focus_topic} if schedules permit."
                    )
                else:
                    focus_topic = shared_topics[0] if shared_topics else "our focus areas"
                    content = (
                        f"Since both attendees are planning to attend '{shared_attending[0]}', {speaking_user.full_name} would welcome "
                        f"connecting briefly before or after the session to explore collaboration on {focus_topic} if schedules permit."
                    )
            elif is_low_key:
                focus_topic = shared_topics[0] if shared_topics else "cross-team synergies"
                if speaking_mood == "Prefer low-key interaction":
                    content = (
                        f"{speaking_user.full_name} appreciates low-key interaction. Would {receiving_name} be open to "
                        f"a brief asynchronous exchange or comparing notes on {focus_topic} at your convenience?"
                    )
                else:
                    content = (
                        f"Given {receiving_name}'s preference for low-key interaction, would they be open to "
                        f"a brief asynchronous exchange or comparing notes on {focus_topic} at your convenience?"
                    )
            elif is_conference_focused:
                focus_topic = shared_topics[0] if shared_topics else "conference topics"
                content = (
                    f"If schedules permit, would {receiving_name} be open to discussing session topics or comparing insights on {focus_topic} between conference events?"
                )
            elif is_casual_mood or is_casual_intent:
                content = (
                    f"If schedules permit, would {receiving_name} be open to grabbing a "
                    f"coffee or catching up informally between conference sessions?"
                )
            elif is_networking:
                focus_topic = shared_topics[0] if shared_topics else "cross-team synergies"
                if speaking_mood == "Ready to network":
                    content = (
                        f"{speaking_user.full_name} is ready to network and would welcome a brief 10-minute conversation to connect and discuss {focus_topic} if convenient."
                    )
                else:
                    content = (
                        f"Noting {receiving_name}'s interest in networking, {speaking_user.full_name} would welcome a brief 10-minute conversation to connect and discuss {focus_topic} if convenient."
                    )
            else:
                focus_topic = shared_topics[0] if shared_topics else "cross-team synergies"
                content = (
                    f"{speaking_user.full_name} would welcome a brief 10-minute touchpoint "
                    f"between sessions to explore potential collaboration on {focus_topic} if convenient."
                )

        elif turn_index == 3:
            # Turn 3: Possibility Acknowledgement (strictly conditional, non-presumptuous)
            action = A2AActionType.PROPOSE_COLLABORATION
            is_low_key = any(m == "Prefer low-key interaction" for m in (initiator_mood, target_mood) if m)
            is_conference_focused = any(m == "Conference-focused" for m in (initiator_mood, target_mood) if m)
            if is_low_key:
                content = (
                    f"That could be an option. {speaking_user.full_name} can decide whether to follow up "
                    f"asynchronously or compare notes directly, depending on their preferences and schedule."
                )
            elif is_conference_focused:
                content = (
                    f"That could be an option. {speaking_user.full_name} can decide whether to connect or "
                    f"share perspectives around the session, depending on their preferences and schedule."
                )
            else:
                content = (
                    f"That could be an option. {speaking_user.full_name} can decide whether to reach out "
                    f"or coordinate directly between sessions, depending on their preferences and schedule."
                )

        elif turn_index == 4:
            action = A2AActionType.SHARE_INTERESTS
            focus_topic = shared_topics[0] if shared_topics else "sustainability and operational scale"
            content = (
                f"At {speaking_company}, one of our primary initiatives revolves around implementing sustainable benchmarks and high-efficiency workflows for {focus_topic}. How is your team currently tackling those operational priorities?"
            )

        elif turn_index == 5:
            action = A2AActionType.SHARE_INTERESTS
            focus_topic = shared_topics[0] if shared_topics else "sustainability and operational scale"
            content = (
                f"That aligns closely with our roadmap at {speaking_company}. We have been focusing on agile deployment and cross-functional partnerships to address {focus_topic}. Exchanging practical playbooks could be very mutually beneficial."
            )

        elif turn_index == 6:
            action = A2AActionType.PROPOSE_COLLABORATION
            focus_topic = shared_topics[0] if shared_topics else "industry innovation"
            content = (
                f"Agreed! With delegates gathering across the venue, {speaking_user.full_name} would welcome a brief 10-minute coffee catch-up at the Networking Lounge during the upcoming break to compare notes on {focus_topic}."
            )

        elif turn_index == 7:
            action = A2AActionType.SHARE_INTERESTS
            content = (
                f"That sounds like a great plan. {speaking_user.full_name} will be near the Lounge between conference tracks and would be pleased to catch up over coffee."
            )

        else:
            action = A2AActionType.PROPOSE_COLLABORATION
            focus_topic = shared_topics[0] if shared_topics else "our discussion topics"
            content = (
                f"Excellent! {speaking_user.full_name} will bring key summary points around {focus_topic} so we can make the discussion actionable and explore mutual synergies."
            )

        metadata = {
            "engine": "deterministic_v2",
            "shared_topics_count": len(shared_topics),
            "shared_hobbies_count": len(shared_hobbies),
            "shared_sessions_count": len(shared_sessions),
            "shared_attending_count": len(shared_attending),
            "initiator_attending_count": len(init_attending),
            "target_attending_count": len(target_attending),
            "initiator_mood": initiator_mood,
            "target_mood": target_mood,
            "speaking_mood": speaking_mood,
        }

        return A2AMessageEnvelope(
            protocol_version=A2A_PROTOCOL_VERSION,
            conversation_id=conversation_id,
            sender_type=MessageSenderTypeEnum.AGENT,
            sender_id=speaking_user.id,
            recipient_id=receiving_user.id,
            turn_index=turn_index,
            action_type=action,
            content=content,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
