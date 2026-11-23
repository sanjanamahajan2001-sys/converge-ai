"""Business Profile, Dynamic Role Management, Catalog Offerings and Requirement APIs."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.db.models.business import (
    BusinessOffering,
    BusinessProfile,
    BusinessRequirement,
    CanonicalProduct,
    ProductGrade,
    ProductTaxonomy,
    ServiceTaxonomy,
)
from app.db.models.user import User
from app.db.session import get_db_session
from app.lib.units import get_unit_info
from app.schemas.business_profile import (
    BusinessOfferingCreate,
    BusinessOfferingResponse,
    BusinessOfferingUpdate,
    BusinessProfileResponse,
    BusinessProfileUpdate,
    BusinessRequirementCreate,
    BusinessRequirementResponse,
    BusinessRequirementUpdate,
    CanonicalProductDTO,
    ProductGradeDTO,
    ProductTaxonomyDTO,
    ServiceTaxonomyDTO,
)

router = APIRouter(prefix="/business", tags=["Business Profiles & Dynamic Roles"])


def _compute_offering_response(offering: BusinessOffering, now: datetime) -> BusinessOfferingResponse:
    """Compute staleness and reconfirmation flags for offering response."""
    cap_time = offering.capacity_last_confirmed_at
    price_time = offering.price_last_confirmed_at

    is_cap_stale = cap_time is None or (now - cap_time) > timedelta(days=90)
    is_price_stale = price_time is None or (now - price_time) > timedelta(days=60)
    reconfirm_req = cap_time is None or (now - cap_time) > timedelta(days=30) or not offering.is_active

    return BusinessOfferingResponse(
        id=offering.id,
        business_profile_id=offering.business_profile_id,
        custom_product_title=offering.custom_product_title,
        product_code=offering.product_code,
        grade_code=offering.grade_code,
        service_code=offering.service_code,
        specifications_text=offering.specifications_text,
        declared_monthly_capacity=offering.declared_monthly_capacity,
        declared_committed_volume=offering.declared_committed_volume,
        capacity_unit=offering.capacity_unit,
        minimum_order_quantity=offering.minimum_order_quantity,
        lead_time_days=offering.lead_time_days,
        geographic_coverage=offering.geographic_coverage,
        offers_test_certificates=offering.offers_test_certificates,
        vendor_certifications=offering.vendor_certifications,
        open_to_distribution=offering.open_to_distribution,
        target_distribution_regions=offering.target_distribution_regions,
        distributor_tier_preferred=offering.distributor_tier_preferred,
        is_public_indicative=offering.is_public_indicative,
        indicative_price_min=offering.indicative_price_min,
        indicative_price_max=offering.indicative_price_max,
        price_currency=offering.price_currency,
        pricing_basis=offering.pricing_basis,
        offers_delivered_pricing=offering.offers_delivered_pricing,
        quote_validity_days=offering.quote_validity_days,
        is_active=offering.is_active,
        price_last_confirmed_at=price_time,
        capacity_last_confirmed_at=cap_time,
        is_capacity_stale=is_cap_stale,
        is_price_stale=is_price_stale,
        reconfirmation_required=reconfirm_req,
        created_at=offering.created_at,
        updated_at=offering.updated_at,
    )


# ---------------------------------------------------------------------------
# Business Profile Routes
# ---------------------------------------------------------------------------
@router.get("/profile/me", response_model=BusinessProfileResponse)
async def get_my_business_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve current user's business profile with catalog and active requirements."""
    stmt = (
        select(BusinessProfile)
        .where(BusinessProfile.user_id == current_user.id)
        .options(
            selectinload(BusinessProfile.offerings),
            selectinload(BusinessProfile.requirements),
        )
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commercial profile not initialized for this user.",
        )

    now = datetime.now(timezone.utc)
    offering_dtos = [_compute_offering_response(o, now) for o in profile.offerings]
    req_dtos = [BusinessRequirementResponse.model_validate(r) for r in profile.requirements]

    return BusinessProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        is_buyer=profile.is_buyer,
        is_supplier=profile.is_supplier,
        is_vendor=profile.is_vendor,
        is_distributor=profile.is_distributor,
        is_partner=profile.is_partner,
        allow_business_matching=profile.allow_business_matching,
        company_name=profile.company_name,
        industry=profile.industry,
        business_website=profile.business_website,
        hq_city=profile.hq_city,
        hq_country=profile.hq_country,
        company_bio=profile.company_bio,
        distributor_territories=profile.distributor_territories,
        warehousing_capacity_sqft=profile.warehousing_capacity_sqft,
        retail_dealer_count=profile.retail_dealer_count,
        partnership_types=profile.partnership_types,
        partnership_interests=profile.partnership_interests,
        offerings=offering_dtos,
        requirements=req_dtos,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put("/profile/me", response_model=BusinessProfileResponse)
async def update_my_business_profile(
    payload: BusinessProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create or update business profile, managing dynamic role state transitions."""
    stmt = (
        select(BusinessProfile)
        .where(BusinessProfile.user_id == current_user.id)
        .options(
            selectinload(BusinessProfile.offerings),
            selectinload(BusinessProfile.requirements),
        )
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    is_new = False
    if not profile:
        is_new = True
        profile = BusinessProfile(user_id=current_user.id)
        db.add(profile)

    # Detect role deactivations and reactivations
    prev_supplier = profile.is_supplier
    prev_vendor = profile.is_vendor
    prev_buyer = profile.is_buyer

    # Update profile fields
    profile.is_buyer = payload.is_buyer
    profile.is_supplier = payload.is_supplier
    profile.is_vendor = payload.is_vendor
    profile.is_distributor = payload.is_distributor
    profile.is_partner = payload.is_partner
    profile.allow_business_matching = payload.allow_business_matching

    profile.company_name = payload.company_name
    profile.industry = payload.industry
    profile.business_website = payload.business_website
    profile.hq_city = payload.hq_city
    profile.hq_country = payload.hq_country
    profile.company_bio = payload.company_bio

    profile.distributor_territories = payload.distributor_territories
    profile.warehousing_capacity_sqft = payload.warehousing_capacity_sqft
    profile.retail_dealer_count = payload.retail_dealer_count

    profile.partnership_types = payload.partnership_types
    profile.partnership_interests = payload.partnership_interests

    # Role lifecycle transitions on existing offerings:
    # If supplier & vendor are both deactivated, soft-disable catalog offerings
    if not is_new:
        if (prev_supplier or prev_vendor) and not (payload.is_supplier or payload.is_vendor):
            for off in profile.offerings:
                off.is_active = False

        # If supplier or vendor re-activated, restore is_active = True
        if not (prev_supplier or prev_vendor) and (payload.is_supplier or payload.is_vendor):
            for off in profile.offerings:
                off.is_active = True

        # If buyer deactivated, soft-disable requirements
        if prev_buyer and not payload.is_buyer:
            for req in profile.requirements:
                req.is_active = False
        elif not prev_buyer and payload.is_buyer:
            for req in profile.requirements:
                req.is_active = True

    await db.commit()
    await db.refresh(profile)

    # Reload relationships
    reloaded_stmt = (
        select(BusinessProfile)
        .where(BusinessProfile.id == profile.id)
        .options(
            selectinload(BusinessProfile.offerings),
            selectinload(BusinessProfile.requirements),
        )
    )
    reloaded = (await db.execute(reloaded_stmt)).scalar_one()

    now = datetime.now(timezone.utc)
    offering_dtos = [_compute_offering_response(o, now) for o in reloaded.offerings]
    req_dtos = [BusinessRequirementResponse.model_validate(r) for r in reloaded.requirements]

    return BusinessProfileResponse(
        id=reloaded.id,
        user_id=reloaded.user_id,
        is_buyer=reloaded.is_buyer,
        is_supplier=reloaded.is_supplier,
        is_vendor=reloaded.is_vendor,
        is_distributor=reloaded.is_distributor,
        is_partner=reloaded.is_partner,
        allow_business_matching=reloaded.allow_business_matching,
        company_name=reloaded.company_name,
        industry=reloaded.industry,
        business_website=reloaded.business_website,
        hq_city=reloaded.hq_city,
        hq_country=reloaded.hq_country,
        company_bio=reloaded.company_bio,
        distributor_territories=reloaded.distributor_territories,
        warehousing_capacity_sqft=reloaded.warehousing_capacity_sqft,
        retail_dealer_count=reloaded.retail_dealer_count,
        partnership_types=reloaded.partnership_types,
        partnership_interests=reloaded.partnership_interests,
        offerings=offering_dtos,
        requirements=req_dtos,
        created_at=reloaded.created_at,
        updated_at=reloaded.updated_at,
    )


# ---------------------------------------------------------------------------
# Offering Management Endpoints
# ---------------------------------------------------------------------------
@router.post("/offerings", response_model=BusinessOfferingResponse, status_code=status.HTTP_201_CREATED)
async def create_offering(
    payload: BusinessOfferingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add a new product or service offering to the user's commercial catalog."""
    stmt = select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must initialize your business profile before creating offerings.",
        )

    if not (profile.is_supplier or profile.is_vendor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must enable the Supplier or Vendor role to publish catalog offerings.",
        )

    # Validate canonical references if provided
    if payload.product_code:
        prod_exists = (
            await db.execute(
                select(CanonicalProduct).where(CanonicalProduct.product_code == payload.product_code)
            )
        ).scalar_one_or_none()
        if not prod_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized canonical product code: '{payload.product_code}'",
            )

    if payload.service_code:
        srv_exists = (
            await db.execute(
                select(ServiceTaxonomy).where(ServiceTaxonomy.service_code == payload.service_code)
            )
        ).scalar_one_or_none()
        if not srv_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized service code: '{payload.service_code}'",
            )

    if payload.grade_code:
        grade_exists = (
            await db.execute(
                select(ProductGrade).where(ProductGrade.grade_code == payload.grade_code)
            )
        ).scalar_one_or_none()
        if not grade_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized grade code: '{payload.grade_code}'",
            )

    if payload.capacity_unit:
        if not get_unit_info(payload.capacity_unit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported or unrecognized capacity unit: '{payload.capacity_unit}'",
            )

    now = datetime.now(timezone.utc)
    offering = BusinessOffering(
        business_profile_id=profile.id,
        custom_product_title=payload.custom_product_title,
        product_code=payload.product_code,
        grade_code=payload.grade_code,
        service_code=payload.service_code,
        specifications_text=payload.specifications_text,
        declared_monthly_capacity=payload.declared_monthly_capacity,
        declared_committed_volume=payload.declared_committed_volume,
        capacity_unit=payload.capacity_unit,
        minimum_order_quantity=payload.minimum_order_quantity,
        lead_time_days=payload.lead_time_days,
        geographic_coverage=payload.geographic_coverage,
        offers_test_certificates=payload.offers_test_certificates,
        vendor_certifications=payload.vendor_certifications,
        open_to_distribution=payload.open_to_distribution,
        target_distribution_regions=payload.target_distribution_regions,
        distributor_tier_preferred=payload.distributor_tier_preferred,
        is_public_indicative=payload.is_public_indicative,
        indicative_price_min=payload.indicative_price_min,
        indicative_price_max=payload.indicative_price_max,
        price_currency=payload.price_currency,
        pricing_basis=payload.pricing_basis,
        offers_delivered_pricing=payload.offers_delivered_pricing,
        quote_validity_days=payload.quote_validity_days,
        is_active=True,
        capacity_last_confirmed_at=now,
        price_last_confirmed_at=now if payload.is_public_indicative else None,
    )
    db.add(offering)
    await db.commit()
    await db.refresh(offering)

    return _compute_offering_response(offering, now)


@router.put("/offerings/{offering_id}", response_model=BusinessOfferingResponse)
async def update_offering(
    offering_id: uuid.UUID,
    payload: BusinessOfferingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update an existing catalog offering with ownership verification (IDOR protection)."""
    stmt = (
        select(BusinessOffering)
        .join(BusinessProfile)
        .where(BusinessOffering.id == offering_id, BusinessProfile.user_id == current_user.id)
    )
    offering = (await db.execute(stmt)).scalar_one_or_none()

    if not offering:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offering not found or you do not have permission to modify it.",
        )

    # Validate updated canonical references or units if passed
    if payload.product_code is not None and payload.product_code != "":
        prod_exists = (
            await db.execute(
                select(CanonicalProduct).where(CanonicalProduct.product_code == payload.product_code)
            )
        ).scalar_one_or_none()
        if not prod_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized canonical product code: '{payload.product_code}'",
            )

    if payload.service_code is not None and payload.service_code != "":
        srv_exists = (
            await db.execute(
                select(ServiceTaxonomy).where(ServiceTaxonomy.service_code == payload.service_code)
            )
        ).scalar_one_or_none()
        if not srv_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized service code: '{payload.service_code}'",
            )

    if payload.grade_code is not None and payload.grade_code != "":
        grade_exists = (
            await db.execute(
                select(ProductGrade).where(ProductGrade.grade_code == payload.grade_code)
            )
        ).scalar_one_or_none()
        if not grade_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized grade code: '{payload.grade_code}'",
            )

    if payload.capacity_unit:
        if not get_unit_info(payload.capacity_unit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported or unrecognized capacity unit: '{payload.capacity_unit}'",
            )

    now = datetime.now(timezone.utc)
    update_data = payload.model_dump(exclude_unset=True)

    for field, val in update_data.items():
        setattr(offering, field, val)

    # Any modification resets confirmation timestamps to current time
    offering.capacity_last_confirmed_at = now
    if offering.is_public_indicative:
        offering.price_last_confirmed_at = now

    await db.commit()
    await db.refresh(offering)

    return _compute_offering_response(offering, now)


@router.delete("/offerings/{offering_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offering(
    offering_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete an offering with ownership verification."""
    stmt = (
        select(BusinessOffering)
        .join(BusinessProfile)
        .where(BusinessOffering.id == offering_id, BusinessProfile.user_id == current_user.id)
    )
    offering = (await db.execute(stmt)).scalar_one_or_none()

    if not offering:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offering not found or you do not have permission to delete it.",
        )

    await db.delete(offering)
    await db.commit()


@router.post("/offerings/{offering_id}/confirm", response_model=BusinessOfferingResponse)
async def reconfirm_offering(
    offering_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Explicitly re-confirm offering capacity & pricing freshness without editing data."""
    stmt = (
        select(BusinessOffering)
        .join(BusinessProfile)
        .where(BusinessOffering.id == offering_id, BusinessProfile.user_id == current_user.id)
    )
    offering = (await db.execute(stmt)).scalar_one_or_none()

    if not offering:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offering not found or you do not have permission to confirm it.",
        )

    now = datetime.now(timezone.utc)
    offering.capacity_last_confirmed_at = now
    if offering.is_public_indicative:
        offering.price_last_confirmed_at = now
    offering.is_active = True

    await db.commit()
    await db.refresh(offering)

    return _compute_offering_response(offering, now)


# ---------------------------------------------------------------------------
# Requirement Management Endpoints
# ---------------------------------------------------------------------------
@router.post("/requirements", response_model=BusinessRequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: BusinessRequirementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new procurement requirement for a buyer or partner."""
    stmt = select(BusinessProfile).where(BusinessProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must initialize your business profile before creating requirements.",
        )

    if not (profile.is_buyer or profile.is_partner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must enable the Buyer or Partner role to publish procurement requirements.",
        )

    # Validate canonical references if provided
    canonical_prod_name = None
    if payload.product_code:
        prod = (
            await db.execute(
                select(CanonicalProduct).where(CanonicalProduct.product_code == payload.product_code)
            )
        ).scalar_one_or_none()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized canonical product code: '{payload.product_code}'",
            )
        canonical_prod_name = prod.canonical_name

    canonical_srv_name = None
    if payload.service_code:
        srv = (
            await db.execute(
                select(ServiceTaxonomy).where(ServiceTaxonomy.service_code == payload.service_code)
            )
        ).scalar_one_or_none()
        if not srv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized service code: '{payload.service_code}'",
            )
        canonical_srv_name = srv.canonical_name

    if payload.grade_code:
        grade_exists = (
            await db.execute(
                select(ProductGrade).where(ProductGrade.grade_code == payload.grade_code)
            )
        ).scalar_one_or_none()
        if not grade_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized grade code: '{payload.grade_code}'",
            )

    if payload.quantity_unit:
        if not get_unit_info(payload.quantity_unit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported or unrecognized quantity unit: '{payload.quantity_unit}'",
            )

    req_title = (payload.custom_requirement_title or "").strip()
    if not req_title:
        if canonical_prod_name:
            req_title = canonical_prod_name
        elif canonical_srv_name:
            req_title = canonical_srv_name
        elif payload.notes and len(payload.notes.strip()) >= 2:
            req_title = payload.notes.strip()[:200]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A custom requirement title or a valid product/service selection is required.",
            )

    requirement = BusinessRequirement(
        business_profile_id=profile.id,
        custom_requirement_title=req_title,
        product_code=payload.product_code,
        grade_code=payload.grade_code,
        service_code=payload.service_code,
        required_quantity=payload.required_quantity,
        quantity_unit=payload.quantity_unit,
        delivery_city=payload.delivery_city,
        delivery_country=payload.delivery_country,
        target_timeline_days=payload.target_timeline_days,
        target_budget_indication=payload.target_budget_indication,
        is_budget_public=payload.is_budget_public,
        urgency=payload.urgency,
        excluded_supplier_ids=payload.excluded_supplier_ids,
        allow_substitutes=payload.allow_substitutes,
        required_certifications=payload.required_certifications,
        is_feedstock_procurement=payload.is_feedstock_procurement,
        notes=payload.notes,
        is_active=True,
    )
    db.add(requirement)
    await db.commit()
    await db.refresh(requirement)

    return BusinessRequirementResponse.model_validate(requirement)


@router.put("/requirements/{requirement_id}", response_model=BusinessRequirementResponse)
async def update_requirement(
    requirement_id: uuid.UUID,
    payload: BusinessRequirementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a procurement requirement with ownership verification."""
    stmt = (
        select(BusinessRequirement)
        .join(BusinessProfile)
        .where(BusinessRequirement.id == requirement_id, BusinessProfile.user_id == current_user.id)
    )
    req = (await db.execute(stmt)).scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found or you do not have permission to modify it.",
        )

    # Validate updated references or units if passed
    if payload.product_code is not None and payload.product_code != "":
        prod_exists = (
            await db.execute(
                select(CanonicalProduct).where(CanonicalProduct.product_code == payload.product_code)
            )
        ).scalar_one_or_none()
        if not prod_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized canonical product code: '{payload.product_code}'",
            )

    if payload.service_code is not None and payload.service_code != "":
        srv_exists = (
            await db.execute(
                select(ServiceTaxonomy).where(ServiceTaxonomy.service_code == payload.service_code)
            )
        ).scalar_one_or_none()
        if not srv_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized service code: '{payload.service_code}'",
            )

    if payload.grade_code is not None and payload.grade_code != "":
        grade_exists = (
            await db.execute(
                select(ProductGrade).where(ProductGrade.grade_code == payload.grade_code)
            )
        ).scalar_one_or_none()
        if not grade_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized grade code: '{payload.grade_code}'",
            )

    if payload.quantity_unit:
        if not get_unit_info(payload.quantity_unit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported or unrecognized quantity unit: '{payload.quantity_unit}'",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(req, field, val)

    await db.commit()
    await db.refresh(req)

    return BusinessRequirementResponse.model_validate(req)


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a procurement requirement with ownership verification."""
    stmt = (
        select(BusinessRequirement)
        .join(BusinessProfile)
        .where(BusinessRequirement.id == requirement_id, BusinessProfile.user_id == current_user.id)
    )
    req = (await db.execute(stmt)).scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found or you do not have permission to delete it.",
        )

    await db.delete(req)
    await db.commit()


# ---------------------------------------------------------------------------
# Taxonomy Discovery Endpoints
# ---------------------------------------------------------------------------
@router.get("/taxonomies/products", response_model=List[ProductTaxonomyDTO])
async def list_product_taxonomies(db: AsyncSession = Depends(get_db_session)):
    """List 4-tier product taxonomy hierarchy (Sectors, Categories, Products, Grades)."""
    stmt = (
        select(ProductTaxonomy)
        .options(
            selectinload(ProductTaxonomy.canonical_products).selectinload(CanonicalProduct.grades)
        )
        .order_by(ProductTaxonomy.category_code)
    )
    result = await db.execute(stmt)
    taxonomies = result.scalars().all()
    return [ProductTaxonomyDTO.model_validate(t) for t in taxonomies]


@router.get("/taxonomies/services", response_model=List[ServiceTaxonomyDTO])
async def list_service_taxonomies(db: AsyncSession = Depends(get_db_session)):
    """List service taxonomies for vendor and contractor capabilities."""
    stmt = select(ServiceTaxonomy).order_by(ServiceTaxonomy.category_code, ServiceTaxonomy.service_code)
    result = await db.execute(stmt)
    services = result.scalars().all()
    return [ServiceTaxonomyDTO.model_validate(s) for s in services]
