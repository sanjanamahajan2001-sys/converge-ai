"""API endpoints for Phase 3 Multi-Dimensional Business Matching & NLP Query Parser."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db_session
from app.db.models.business import BusinessProfile, BusinessRequirement
from app.db.models.user import User
from app.schemas.business_matching import (
    BusinessMatchSearchRequest,
    BusinessMatchSearchResponse,
    ParsedBusinessRequirement,
    QueryParseRequest,
)
from app.schemas.business_profile import BusinessOfferingResponse, BusinessRequirementResponse
from app.services.business_matching import search_business_match_candidates
from app.services.query_parser import parse_procurement_query

router = APIRouter(prefix="/business/matching", tags=["Business Matching & Discovery"])


@router.post(
    "/parse-query",
    response_model=ParsedBusinessRequirement,
    summary="NLP Commercial Requirement Query Parser",
    description="Parses unstructured procurement text into structured parameters (product, quantity, unit, city, timeline).",
)
async def parse_query_endpoint(
    payload: QueryParseRequest,
    current_user: User = Depends(get_current_user),
) -> ParsedBusinessRequirement:
    """Parse unstructured procurement text query."""
    return parse_procurement_query(payload.query)


@router.post(
    "/search",
    response_model=BusinessMatchSearchResponse,
    summary="Multi-Dimensional Mode B Commercial Matching Search",
    description=(
        "Executes 5-dimensional matching (product relevance, run-rate capacity, commitment confidence, "
        "delivery feasibility, verification freshness) with incumbent exclusions and budget privacy."
    ),
)
async def search_candidates_endpoint(
    payload: BusinessMatchSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BusinessMatchSearchResponse:
    """Execute multi-dimensional commercial matching search."""
    try:
        return await search_business_match_candidates(db, current_user, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/my-requirements",
    response_model=List[BusinessRequirementResponse],
    summary="Get Caller's Active Procurement Requirements for 1-Click Matching",
)
async def get_my_active_requirements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[BusinessRequirementResponse]:
    """Retrieve active requirements owned by current user to drive 1-click matching."""
    prof_res = await db.execute(
        select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    )
    prof = prof_res.scalar_one_or_none()
    if not prof:
        return []

    req_res = await db.execute(
        select(BusinessRequirement).where(
            BusinessRequirement.business_profile_id == prof.id,
            BusinessRequirement.is_active.is_(True),
        )
    )
    reqs = req_res.scalars().all()
    return [
        BusinessRequirementResponse(
            id=r.id,
            business_profile_id=r.business_profile_id,
            custom_requirement_title=r.custom_requirement_title,
            product_code=r.product_code,
            grade_code=r.grade_code,
            service_code=r.service_code,
            required_quantity=r.required_quantity,
            quantity_unit=r.quantity_unit,
            delivery_city=r.delivery_city,
            delivery_country=r.delivery_country,
            target_timeline_days=r.target_timeline_days,
            target_budget_indication=r.target_budget_indication if r.is_budget_public else None,
            is_budget_public=r.is_budget_public,
            urgency=r.urgency,
            excluded_supplier_ids=r.excluded_supplier_ids or [],
            allow_substitutes=r.allow_substitutes,
            required_certifications=r.required_certifications or [],
            is_feedstock_procurement=r.is_feedstock_procurement,
            notes=r.notes,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in reqs
    ]


@router.get(
    "/my-offerings",
    response_model=List[BusinessOfferingResponse],
    summary="Get Caller's Active Catalog Offerings for 1-Click Reverse Matching",
)
async def get_my_active_offerings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[BusinessOfferingResponse]:
    """Retrieve active catalog offerings owned by current user to drive 1-click buyer demand discovery."""
    from app.db.models.business import BusinessOffering
    prof_res = await db.execute(
        select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    )
    prof = prof_res.scalar_one_or_none()
    if not prof:
        return []

    off_res = await db.execute(
        select(BusinessOffering).where(
            BusinessOffering.business_profile_id == prof.id,
            BusinessOffering.is_active.is_(True),
        )
    )
    offerings = off_res.scalars().all()
    return [
        BusinessOfferingResponse(
            id=o.id,
            business_profile_id=o.business_profile_id,
            custom_product_title=o.custom_product_title,
            product_code=o.product_code,
            grade_code=o.grade_code,
            service_code=o.service_code,
            specifications_text=o.specifications_text,
            declared_monthly_capacity=o.declared_monthly_capacity,
            declared_committed_volume=o.declared_committed_volume,
            capacity_unit=o.capacity_unit,
            minimum_order_quantity=o.minimum_order_quantity,
            lead_time_days=o.lead_time_days,
            geographic_coverage=o.geographic_coverage or [],
            offers_test_certificates=o.offers_test_certificates,
            vendor_certifications=o.vendor_certifications or [],
            open_to_distribution=o.open_to_distribution,
            target_distribution_regions=o.target_distribution_regions or [],
            distributor_tier_preferred=o.distributor_tier_preferred,
            is_public_indicative=o.is_public_indicative,
            indicative_price_min=o.indicative_price_min,
            indicative_price_max=o.indicative_price_max,
            price_currency=o.price_currency,
            pricing_basis=o.pricing_basis,
            offers_delivered_pricing=o.offers_delivered_pricing,
            quote_validity_days=o.quote_validity_days,
            price_last_confirmed_at=o.price_last_confirmed_at,
            is_active=o.is_active,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in offerings
    ]
