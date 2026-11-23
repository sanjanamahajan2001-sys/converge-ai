"""Multi-Dimensional Business Matching Engine for Mode B commercial discovery."""
import math
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import and_, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.business import (
    BusinessOffering,
    BusinessProfile,
    BusinessRequirement,
    CanonicalProduct,
    ProductGrade,
    ServiceTaxonomy,
)
from app.db.models.user import User
from app.lib.units import are_units_compatible, convert_quantity, IncompatibleUnitError
from app.schemas.business_matching import (
    BusinessMatchCandidate,
    BusinessMatchSearchRequest,
    BusinessMatchSearchResponse,
    ParsedBusinessRequirement,
    ScoreBreakdown,
)
from app.services.query_parser import parse_procurement_query, COMMON_CITIES

# Strict technical eligibility gate: minimum product relevance to qualify
MIN_ELIGIBLE_PRODUCT_RELEVANCE = 0.60

STOPWORDS: Set[str] = {
    "need", "looking", "require", "required", "for", "in", "and", "or", "of", "the",
    "a", "an", "to", "at", "by", "from", "with", "within", "under", "per", "into", "on"
}

GENERIC_COMMERCIAL_TERMS: Set[str] = {
    "fleet", "service", "services", "rental", "rentals", "supply", "supplier",
    "solutions", "pvt", "ltd", "inc", "company", "contractor", "contractors",
    "equipment", "material", "materials", "commercial", "enterprise", "industrial",
    "custom", "requirement", "offering", "hire", "hiring", "provider", "provision"
}

GEO_FILTER_TERMS: Set[str] = {c.lower() for c in COMMON_CITIES} | {
    "india", "maharashtra", "gujarat", "karnataka", "delhi", "pan", "all", "zone", "state"
}


def extract_domain_tokens(text: Optional[str]) -> Set[str]:
    """Extract domain-discriminative tokens excluding stopwords, generic terms, and geographic words."""
    if not text:
        return set()
    raw_tokens = re.findall(r"[a-z0-9]+", text.lower())
    domain_tokens = set()
    for token in raw_tokens:
        if len(token) <= 2:
            continue
        if token in STOPWORDS or token in GENERIC_COMMERCIAL_TERMS or token in GEO_FILTER_TERMS:
            continue
        domain_tokens.add(token)
    return domain_tokens


def evaluate_product_relevance(
    offering: BusinessOffering,
    target_product_code: Optional[str],
    target_grade_code: Optional[str],
    target_service_code: Optional[str],
    target_item_name: Optional[str],
    substitutes_map: Dict[str, List[str]],
    allow_substitutes: bool,
) -> float:
    """Calculate Product / Service Relevance S_prod (0.0 to 1.0).

    Hard gates:
        - Cross-category mismatch (Physical product vs Service) returns 0.0.
        - Canonical conflict (different canonical product without substitute) returns 0.0.
        - Custom unstructured text must meet minimum domain token coverage.
    """
    # 0. Cross-type incompatibility hard gate: Physical product vs Service
    target_is_product = bool(target_product_code or target_grade_code)
    target_is_service = bool(target_service_code)
    offering_is_product = bool(offering.product_code or offering.grade_code)
    offering_is_service = bool(offering.service_code)

    if target_is_product and offering_is_service and not offering_is_product:
        return 0.0
    if target_is_service and offering_is_product and not offering_is_service:
        return 0.0

    # 1. Exact Grade Match (1.0)
    if target_grade_code and offering.grade_code:
        if target_grade_code == offering.grade_code:
            return 1.0
        # Different grade under same canonical product?
        if target_product_code and offering.product_code and target_product_code == offering.product_code:
            return 0.70
        return 0.0

    # 2. Canonical Product Match (0.85)
    if target_product_code and offering.product_code:
        if target_product_code == offering.product_code:
            return 0.85
        # 3. Approved Substitute Match (0.65)
        if allow_substitutes:
            allowed_subs = substitutes_map.get(target_product_code, [])
            if offering.product_code in allowed_subs:
                return 0.65
        return 0.0

    # 4. Service Taxonomy Match (0.90)
    if target_service_code and offering.service_code:
        if target_service_code == offering.service_code:
            return 0.90
        return 0.0

    # 5. Domain Token Overlap for Custom Products / Services
    target_tokens = extract_domain_tokens(target_item_name)
    offering_title_tokens = extract_domain_tokens(offering.custom_product_title)
    offering_spec_tokens = extract_domain_tokens(offering.specifications_text)
    all_offering_tokens = offering_title_tokens | offering_spec_tokens

    if target_tokens and all_offering_tokens:
        title_overlap = target_tokens.intersection(offering_title_tokens)
        spec_overlap = target_tokens.intersection(offering_spec_tokens)
        all_overlap = target_tokens.intersection(all_offering_tokens)

        # Primary title matching: core product identity must match primary title
        if title_overlap:
            min_len = min(len(target_tokens), len(offering_title_tokens))
            title_containment = len(title_overlap) / max(1, min_len)
            target_coverage = len(title_overlap) / max(1, len(target_tokens))

            if target_coverage >= 0.60 or title_containment >= 0.60:
                return 0.85
            elif target_coverage >= 0.35 or title_containment >= 0.35:
                return 0.70
            else:
                return 0.65
        elif len(all_overlap) >= 2 and len(target_tokens) <= 3:
            # Fallback for detailed custom specifications when title is generic
            return 0.60
        else:
            return 0.0

    return 0.0


def evaluate_capacity_run_rate(
    offering: BusinessOffering,
    quantity: Optional[float],
    quantity_unit: Optional[str],
    timeline_days: Optional[int],
) -> Tuple[float, str, Optional[float]]:
    """Evaluate run-rate capacity feasibility S_cap (0.0 to 1.0).

    Formula:
        RequiredRunRate = Q * (30 / max(T, 15))
    """
    if quantity is None or quantity <= 0:
        if offering.declared_monthly_capacity is not None and offering.declared_monthly_capacity > 0:
            return 0.85, "✓ Capacity Declared", float(offering.declared_monthly_capacity)
        return 0.0, "⚠️ Capacity Unverified", None

    t = max(timeline_days or 30, 15)
    run_rate = float(quantity) * (30.0 / float(t))

    if offering.declared_monthly_capacity is None or offering.declared_monthly_capacity <= 0:
        return 0.0, "⚠️ Capacity Unverified", None

    off_capacity = float(offering.declared_monthly_capacity)

    # Unit dimensional compatibility check
    normalized_run_rate = run_rate
    if quantity_unit and offering.capacity_unit and quantity_unit != offering.capacity_unit:
        if not are_units_compatible(quantity_unit, offering.capacity_unit):
            return 0.0, f"⚠️ Incompatible Dimensions ({quantity_unit} vs {offering.capacity_unit})", off_capacity
        try:
            converted = convert_quantity(
                Decimal(str(run_rate)),
                quantity_unit,
                offering.capacity_unit,
            )
            normalized_run_rate = float(converted)
        except IncompatibleUnitError:
            return 0.0, f"⚠️ Incompatible Dimensions ({quantity_unit} vs {offering.capacity_unit})", off_capacity

    # Check MOQ
    if offering.minimum_order_quantity and quantity < float(offering.minimum_order_quantity):
        return 0.20, f"⚠️ Below MOQ ({int(offering.minimum_order_quantity)} {offering.capacity_unit})", off_capacity

    # Capacity run rate comparison
    if normalized_run_rate <= off_capacity:
        return 1.0, f"✓ Capacity Feasible ({int(off_capacity):,} {offering.capacity_unit}/mo)", off_capacity
    else:
        ratio = max(0.10, off_capacity / normalized_run_rate)
        return round(ratio, 2), f"⚠️ Capacity Constrained ({int(off_capacity):,} {offering.capacity_unit}/mo)", off_capacity


def evaluate_commitment_confidence(
    offering: BusinessOffering,
    required_run_rate: float,
) -> Tuple[float, Optional[str], Optional[float]]:
    """Evaluate commitment confidence C_commit (0.0 to 1.0).

    Grounding rule: Unknown values NEVER imply verified availability.
    """
    if offering.declared_monthly_capacity is None or offering.declared_monthly_capacity <= 0:
        return 0.0, "⚠️ Capacity Unverified", None

    # If committed volume is unrecorded, confidence is strictly 0.0 (unverified)
    if offering.declared_committed_volume is None:
        return 0.0, "⚠️ Uncommitted Allocation Unverified", None

    declared_cap = float(offering.declared_monthly_capacity)
    committed_vol = float(offering.declared_committed_volume)
    uncommitted = max(0.0, declared_cap - committed_vol)

    if required_run_rate <= 0:
        if uncommitted > 0:
            return 1.0, "✓ Uncommitted Allocation Recorded", uncommitted
        else:
            return 0.0, "⚠️ 100% Capacity Committed", 0.0

    if uncommitted >= required_run_rate:
        return 1.0, "✓ High Commitment Confidence", uncommitted
    elif uncommitted > 0:
        ratio = uncommitted / required_run_rate
        return max(0.10, min(0.90, round(ratio, 2))), "⚠️ Partially Committed Capacity", uncommitted
    else:
        return 0.0, "⚠️ 100% Capacity Committed", 0.0


REGION_CITY_MAP: Dict[str, Set[str]] = {
    "western maharashtra": {
        "pune", "satara", "solapur", "kolhapur", "sangli", "ahmednagar", "western maharashtra"
    },
    "maharashtra": {
        "pune", "mumbai", "nashik", "nagpur", "thane", "kolhapur", "solapur",
        "aurangabad", "chhatrapati sambhajinagar", "navi mumbai", "satara", "sangli",
        "ahmednagar", "western maharashtra", "maharashtra"
    },
    "ncr": {
        "delhi", "new delhi", "noida", "gurugram", "gurgaon", "ghaziabad", "faridabad", "ncr", "delhi ncr"
    },
    "delhi ncr": {
        "delhi", "new delhi", "noida", "gurugram", "gurgaon", "ghaziabad", "faridabad", "ncr", "delhi ncr"
    },
    "gujarat": {
        "ahmedabad", "surat", "vadodara", "rajkot", "south gujarat", "gujarat"
    },
    "south gujarat": {
        "surat", "vadodara", "valsad", "navsari", "south gujarat"
    },
    "karnataka": {
        "bengaluru", "bangalore", "mysuru", "hubli", "dharwad", "karnataka"
    },
    "tamil nadu": {
        "chennai", "coimbatore", "madurai", "tamil nadu"
    },
    "telangana": {
        "hyderabad", "warangal", "telangana"
    },
}


def check_location_covered(delivery_city: str, coverage: List[str]) -> bool:
    """Check if delivery location is covered by offering coverage with regional normalization."""
    clean_del = delivery_city.strip().lower()
    clean_cov = [c.strip().lower() for c in coverage if c]

    # 1. Pan-India
    if any(p in clean_cov for p in ("all india", "pan india", "nationwide", "india")):
        return True

    # 2. Direct string / substring match
    if any(clean_del in c or c in clean_del for c in clean_cov):
        return True

    # 3. Regional hierarchy
    # Case A: clean_del is a recognized region (e.g. "western maharashtra")
    if clean_del in REGION_CITY_MAP:
        region_cities = REGION_CITY_MAP[clean_del]
        if any(c in region_cities for c in clean_cov):
            return True

    # Case B: offering has a recognized region in coverage (e.g. "western maharashtra")
    for c in clean_cov:
        if c in REGION_CITY_MAP and clean_del in REGION_CITY_MAP[c]:
            return True

    # Case C: Both clean_del and a coverage city belong to the same regional cluster
    for reg_cities in REGION_CITY_MAP.values():
        if clean_del in reg_cities and any(c in reg_cities for c in clean_cov):
            return True

    return False


def evaluate_delivery_feasibility(
    offering: BusinessOffering,
    delivery_city: Optional[str],
    target_timeline_days: Optional[int],
) -> Tuple[float, Optional[str]]:
    """Evaluate location coverage and dispatch lead time feasibility S_del (0.0 to 1.0)."""
    # 1. Location Coverage
    loc_score = 1.0
    loc_badge = None
    if delivery_city:
        coverage = offering.geographic_coverage or []
        if coverage:
            if not check_location_covered(delivery_city, coverage):
                return 0.0, "⚠️ Destination Out of Coverage"
        loc_badge = f"✓ Delivers to {delivery_city.title()}"

    # 2. Lead Time Feasibility
    lead_score = 1.0
    if offering.lead_time_days is not None and target_timeline_days is not None:
        if offering.lead_time_days <= target_timeline_days:
            lead_score = 1.0
        else:
            lead_score = 0.30
            return 0.30, f"⚠️ Lead time ({offering.lead_time_days}d) exceeds timeline ({target_timeline_days}d)"

    return loc_score * lead_score, loc_badge


def evaluate_data_freshness(offering: BusinessOffering) -> Tuple[float, str]:
    """Evaluate anti-staleness confidence C_ver (0.0 to 1.0)."""
    now = datetime.now(timezone.utc)
    cap_time = offering.capacity_last_confirmed_at or offering.created_at
    if not cap_time:
        return 0.50, "Declared Parameters"

    age = now - cap_time
    if age > timedelta(days=90):
        return 0.0, "⚠️ Stale Data (>90d)"
    elif age > timedelta(days=30):
        return 0.50, "⚠️ Moderate Age (<90d)"
    else:
        return 1.0, "✓ Verified Fresh"


async def search_business_match_candidates(
    db: AsyncSession,
    caller_user: User,
    request: BusinessMatchSearchRequest,
) -> BusinessMatchSearchResponse:
    """Execute Mode B multi-dimensional commercial matching."""
    # 1. Verify caller has commercial profile and opt-in consent
    caller_prof_res = await db.execute(
        select(BusinessProfile).where(BusinessProfile.user_id == caller_user.id)
    )
    caller_profile = caller_prof_res.scalar_one_or_none()
    if not caller_profile or not caller_profile.allow_business_matching:
        raise ValueError(
            "Commercial matching requires opt-in consent. Please enable 'Allow Commercial & Business Discovery' in your profile."
        )

    # 2. Derive matching parameters: from saved requirement or freeform query
    excluded_ids: List[str] = []
    target_product_code = request.product_code
    target_grade_code = request.grade_code
    target_service_code = request.service_code
    target_item_name = request.item_name
    quantity = request.quantity
    quantity_unit = request.quantity_unit
    delivery_city = request.delivery_city
    timeline_days = request.target_timeline_days
    allow_substitutes = request.allow_substitutes
    parsed_summary: Optional[ParsedBusinessRequirement] = None

    if request.requirement_id:
        req_res = await db.execute(
            select(BusinessRequirement).where(
                BusinessRequirement.id == request.requirement_id,
                BusinessRequirement.business_profile_id == caller_profile.id,
            )
        )
        saved_req = req_res.scalar_one_or_none()
        if saved_req:
            target_product_code = saved_req.product_code
            target_grade_code = saved_req.grade_code
            target_service_code = saved_req.service_code
            target_item_name = saved_req.custom_requirement_title
            quantity = float(saved_req.required_quantity) if saved_req.required_quantity else None
            quantity_unit = saved_req.quantity_unit
            delivery_city = saved_req.delivery_city
            timeline_days = saved_req.target_timeline_days
            allow_substitutes = saved_req.allow_substitutes
            excluded_ids = saved_req.excluded_supplier_ids or []
            parsed_summary = ParsedBusinessRequirement(
                raw_query=saved_req.custom_requirement_title,
                item_name=saved_req.custom_requirement_title,
                matched_product_code=saved_req.product_code,
                matched_grade_code=saved_req.grade_code,
                matched_service_code=saved_req.service_code,
                quantity=quantity,
                quantity_unit=quantity_unit,
                destination_city=delivery_city,
                target_timeline_days=timeline_days,
                inquiry_type="RFI_SERVICE" if saved_req.service_code else "RFQ_PRODUCT",
                confidence=1.0,
            )
    elif request.query:
        parsed_summary = parse_procurement_query(request.query)
        target_product_code = target_product_code or parsed_summary.matched_product_code
        target_grade_code = target_grade_code or parsed_summary.matched_grade_code
        target_service_code = target_service_code or parsed_summary.matched_service_code
        target_item_name = target_item_name or parsed_summary.item_name
        quantity = quantity or parsed_summary.quantity
        quantity_unit = quantity_unit or parsed_summary.quantity_unit
        delivery_city = delivery_city or parsed_summary.destination_city
        timeline_days = timeline_days or parsed_summary.target_timeline_days

    # 3. Load substitute product mappings
    substitutes_map: Dict[str, List[str]] = {}
    if allow_substitutes:
        prod_res = await db.execute(select(CanonicalProduct))
        for p in prod_res.scalars().all():
            substitutes_map[p.product_code] = p.substitute_product_codes or []

    # Check search_type: "SUPPLIERS" (default, Buyer looking for Offerings) or "BUYERS" (Supplier/Vendor looking for Requirements)
    if request.search_type == "BUYERS":
        # 4b. Query active buyer requirements across the network
        req_stmt = (
            select(BusinessRequirement)
            .join(BusinessProfile, BusinessRequirement.business_profile_id == BusinessProfile.id)
            .options(selectinload(BusinessRequirement.business_profile))
            .where(
                BusinessRequirement.is_active.is_(True),
                BusinessProfile.allow_business_matching.is_(True),
                BusinessProfile.user_id != caller_user.id,
            )
        )
        req_res = await db.execute(req_stmt)
        requirements = req_res.scalars().all()

        candidates: List[BusinessMatchCandidate] = []
        for req in requirements:
            prof: BusinessProfile = req.business_profile

            # Check incumbent exclusions
            if req.excluded_supplier_ids and (str(caller_profile.id) in req.excluded_supplier_ids or str(caller_user.id) in req.excluded_supplier_ids):
                continue

            # Evaluate product relevance between search query/offering and the buyer requirement
            # Create a mock offering adapter for evaluate_product_relevance
            class ReqOfferingAdapter:
                def __init__(self, r):
                    self.product_code = r.product_code
                    self.grade_code = r.grade_code
                    self.service_code = r.service_code
                    self.custom_product_title = r.custom_requirement_title
                    self.specifications_text = r.notes

            s_prod = evaluate_product_relevance(
                ReqOfferingAdapter(req),
                target_product_code,
                target_grade_code,
                target_service_code,
                target_item_name,
                substitutes_map,
                allow_substitutes or req.allow_substitutes,
            )
            if s_prod < MIN_ELIGIBLE_PRODUCT_RELEVANCE:
                continue

            # Location compatibility
            s_del = 1.0
            del_badge = f"📍 Demands delivery to {req.delivery_city}" if req.delivery_city else "📍 Flexible Location"
            if delivery_city and req.delivery_city:
                if delivery_city.lower().strip() == req.delivery_city.lower().strip():
                    s_del = 1.0
                else:
                    s_del = 0.5

            # Volume / Timeline compatibility
            s_cap = 1.0
            cap_badge = f"📦 {float(req.required_quantity):,.0f} {(req.quantity_unit or 'Units').replace('_', ' ')}" if req.required_quantity else "📦 Quantity on Request"

            c_ver = 1.0
            ver_badge = "✓ Active Demand"

            composite = 0.50 * s_prod + 0.30 * s_cap + 0.20 * s_del
            score_percent = round(composite * 100.0, 1)

            badges: List[str] = [ver_badge, cap_badge, del_badge]
            if req.target_timeline_days:
                badges.append(f"⏱️ {req.target_timeline_days} Days")
            if req.service_code:
                badges.append("🛠️ Service Need")

            # Buyer budget display: strictly preserve privacy
            price_display = "Target budget disclosed upon pitch acceptance"
            if req.is_budget_public and req.target_budget_indication is not None:
                price_display = f"Public Target Budget: ₹{float(req.target_budget_indication):,.0f}"

            req_role = "DISTRIBUTOR" if prof.is_distributor else ("PARTNER" if prof.is_partner and not prof.is_buyer else "BUYER")
            candidate = BusinessMatchCandidate(
                offering_id=None,
                requirement_id=req.id,
                candidate_type="REQUIREMENT",
                business_profile_id=prof.id,
                supplier_user_id=prof.user_id,
                supplier_company_name=prof.company_name or "Verified Commercial Entity",
                supplier_industry=prof.industry or "Procurement & Construction",
                supplier_hq_city=prof.hq_city or "Flexible",
                supplier_role=req_role,
                offering_title=req.custom_requirement_title,
                product_code=req.product_code,
                grade_code=req.grade_code,
                service_code=req.service_code,
                composite_score=score_percent,
                score_breakdown=ScoreBreakdown(
                    product_relevance=round(s_prod, 2),
                    capacity_feasibility=round(s_cap, 2),
                    commitment_confidence=1.0,
                    delivery_feasibility=round(s_del, 2),
                    verification_confidence=round(c_ver, 2),
                ),
                declared_monthly_capacity=float(req.required_quantity) if req.required_quantity else None,
                capacity_unit=req.quantity_unit,
                uncommitted_monthly_capacity=None,
                lead_time_days=req.target_timeline_days,
                geographic_coverage=[req.delivery_city] if req.delivery_city else [],
                offers_test_certificates=len(req.required_certifications or []) > 0,
                confidence_badges=badges,
                indicative_price_display=price_display,
                pricing_basis=None,
                price_currency="INR",
                destination_city=req.delivery_city,
                target_timeline_days=req.target_timeline_days,
                required_quantity=float(req.required_quantity) if req.required_quantity else None,
            )
            candidates.append(candidate)

        candidates.sort(key=lambda c: c.composite_score, reverse=True)
        paginated = candidates[request.offset : request.offset + request.limit]
        return BusinessMatchSearchResponse(
            total_candidates=len(candidates),
            query_summary=parsed_summary,
            candidates=paginated,
        )

    # 4. Query active supplier & vendor offerings across the network
    # Exclude self-owned offerings, unapproved profiles, and excluded incumbent suppliers
    stmt = (
        select(BusinessOffering)
        .join(BusinessProfile, BusinessOffering.business_profile_id == BusinessProfile.id)
        .options(selectinload(BusinessOffering.business_profile))
        .where(
            BusinessOffering.is_active.is_(True),
            BusinessProfile.allow_business_matching.is_(True),
            BusinessProfile.user_id != caller_user.id,
        )
    )

    result = await db.execute(stmt)
    offerings = result.scalars().all()

    candidates: List[BusinessMatchCandidate] = []

    for off in offerings:
        prof: BusinessProfile = off.business_profile

        # Hard Gate: Incumbent supplier exclusion
        if str(prof.id) in excluded_ids or str(prof.user_id) in excluded_ids:
            continue

        # Dimension 1: Product Relevance (Hard Gate)
        s_prod = evaluate_product_relevance(
            off,
            target_product_code,
            target_grade_code,
            target_service_code,
            target_item_name,
            substitutes_map,
            allow_substitutes,
        )
        if s_prod < MIN_ELIGIBLE_PRODUCT_RELEVANCE:
            continue  # Disqualified: Failed technical product relevance gate

        # Dimension 2: Capacity Run-Rate Feasibility
        s_cap, cap_badge, declared_cap = evaluate_capacity_run_rate(
            off, quantity, quantity_unit, timeline_days
        )

        # Dimension 3: Commitment Confidence
        t_days = max(timeline_days or 30, 15)
        req_run_rate = (quantity or 0.0) * (30.0 / float(t_days))
        c_com, com_badge, uncommitted_cap = evaluate_commitment_confidence(off, req_run_rate)

        # Dimension 4: Delivery Feasibility
        s_del, del_badge = evaluate_delivery_feasibility(off, delivery_city, timeline_days)
        if s_del <= 0.0:
            continue  # Hard Gate: Out of geographical delivery coverage

        # Dimension 5: Data Freshness
        c_ver, ver_badge = evaluate_data_freshness(off)

        # Calculate Weighted Composite Score across all 5 dimensions
        # S_prod (0.40) + S_cap (0.25) + C_com (0.15) + S_del (0.15) + C_ver (0.05) = 1.00
        composite = (
            0.40 * s_prod
            + 0.25 * s_cap
            + 0.15 * c_com
            + 0.15 * s_del
            + 0.05 * c_ver
        )
        score_percent = round(composite * 100.0, 1)

        # Minimum qualified score filter
        if score_percent < 30.0:
            continue

        is_substitute_match = False
        if target_product_code and off.product_code and target_product_code != off.product_code:
            if off.product_code in substitutes_map.get(target_product_code, []):
                is_substitute_match = True

        badges: List[str] = [ver_badge]
        if is_substitute_match:
            badges.append("♻️ Alternative / Substitute Material")
        if cap_badge:
            badges.append(cap_badge)
        if com_badge:
            badges.append(com_badge)
        if del_badge:
            badges.append(del_badge)
        if off.offers_test_certificates:
            badges.append("📜 Mill Certs")
        if off.vendor_certifications:
            for cert in off.vendor_certifications:
                if cert and isinstance(cert, str) and cert.strip():
                    badges.append(f"🎖️ {cert.strip()}")
        if off.service_code:
            badges.append("🛠️ Verified Service")

        # Determine Indicative Price Display (Strictly respect public flag & privacy)
        price_display = None
        if off.is_public_indicative and off.indicative_price_min is not None:
            min_p = float(off.indicative_price_min)
            max_p = float(off.indicative_price_max) if off.indicative_price_max else min_p
            unit_str = off.capacity_unit or "unit"
            basis_str = f" ({off.pricing_basis.replace('_', ' ').title()})" if off.pricing_basis else ""
            if max_p > min_p:
                price_display = f"₹{min_p:,.0f} – ₹{max_p:,.0f} / {unit_str}{basis_str}"
            else:
                price_display = f"₹{min_p:,.0f} / {unit_str}{basis_str}"
        elif not off.is_public_indicative:
            price_display = "Indicative price available upon RFQ"

        # Determine Role
        supplier_role = "VENDOR" if off.service_code else "SUPPLIER"
        if prof.is_distributor:
            supplier_role = "DISTRIBUTOR"
        elif prof.is_partner and not prof.is_supplier and not prof.is_vendor:
            supplier_role = "PARTNER"

        candidate = BusinessMatchCandidate(
            offering_id=off.id,
            business_profile_id=prof.id,
            supplier_user_id=prof.user_id,
            supplier_company_name=prof.company_name or "Verified Supplier Entity",
            supplier_industry=prof.industry or "Commercial Materials & Services",
            supplier_hq_city=prof.hq_city or "Flexible",
            supplier_role=supplier_role,
            offering_title=off.custom_product_title,
            product_code=off.product_code,
            grade_code=off.grade_code,
            service_code=off.service_code,
            composite_score=score_percent,
            score_breakdown=ScoreBreakdown(
                product_relevance=round(s_prod, 2),
                capacity_feasibility=round(s_cap, 2),
                commitment_confidence=round(c_com, 2),
                delivery_feasibility=round(s_del, 2),
                verification_confidence=round(c_ver, 2),
            ),
            declared_monthly_capacity=declared_cap,
            capacity_unit=off.capacity_unit,
            uncommitted_monthly_capacity=uncommitted_cap,
            lead_time_days=off.lead_time_days,
            geographic_coverage=off.geographic_coverage or [],
            offers_test_certificates=off.offers_test_certificates,
            confidence_badges=badges,
            indicative_price_display=price_display,
            pricing_basis=off.pricing_basis,
            price_currency=off.price_currency or "INR",
        )
        candidates.append(candidate)

    # Sort candidates by composite score descending
    candidates.sort(key=lambda c: c.composite_score, reverse=True)

    paginated = candidates[request.offset : request.offset + request.limit]

    return BusinessMatchSearchResponse(
        total_candidates=len(candidates),
        query_summary=parsed_summary,
        candidates=paginated,
    )
