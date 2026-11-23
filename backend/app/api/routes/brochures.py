"""API routes for Company Digital Brochures and Flipbook Viewer (Phase 1)."""
import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.events import event_broker
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.brochure import (
    BrochureAdEventCreate,
    BrochureAdItem,
    BrochureAnalyticsDetail,
    BrochureDirectoryItem,
    BrochurePageItem,
    BrochurePageReadEventCreate,
    BrochurePageReorderRequest,
    BrochurePublicView,
    CompanyBrochureDetail,
    CompanyBrochureUpdate,
    FlipbookViewerSettings,
)
from app.services.brochure import BrochureService

router = APIRouter(prefix="/brochures", tags=["Digital Brochures & Flipbooks"])


@router.get(
    "/my-brochure",
    response_model=CompanyBrochureDetail,
    summary="Get or initialize current user's company brochure",
)
async def get_my_brochure(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CompanyBrochureDetail:
    """Retrieve or initialize the authenticated user's company brochure."""
    brochure = await BrochureService.get_or_create_user_brochure(db, current_user.id)
    return CompanyBrochureDetail(
        id=brochure.id,
        business_profile_id=brochure.business_profile_id,
        owner_user_id=brochure.owner_user_id,
        company_name=brochure.company_name,
        title=brochure.title,
        description=brochure.description,
        slug=brochure.slug,
        is_published=brochure.is_published,
        view_count=brochure.view_count,
        total_pages=len(brochure.pages),
        pages=[BrochurePageItem.model_validate(p) for p in brochure.pages],
        created_at=brochure.created_at,
        updated_at=brochure.updated_at,
    )


@router.put(
    "/my-brochure",
    response_model=CompanyBrochureDetail,
    summary="Update brochure metadata",
)
async def update_my_brochure(
    payload: CompanyBrochureUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CompanyBrochureDetail:
    """Update title, description, slug or publication status."""
    brochure = await BrochureService.get_or_create_user_brochure(db, current_user.id)
    try:
        updated = await BrochureService.update_brochure(db, brochure, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return CompanyBrochureDetail(
        id=updated.id,
        business_profile_id=updated.business_profile_id,
        owner_user_id=updated.owner_user_id,
        company_name=updated.company_name,
        title=updated.title,
        description=updated.description,
        slug=updated.slug,
        is_published=updated.is_published,
        view_count=updated.view_count,
        total_pages=len(updated.pages),
        pages=[BrochurePageItem.model_validate(p) for p in updated.pages],
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.post(
    "/my-brochure/upload-page",
    response_model=BrochurePageItem,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and append a page image to the brochure",
)
async def upload_brochure_page(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BrochurePageItem:
    """Upload an image file (PNG, JPEG, WebP) to append as the next brochure page."""
    # Validate content type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type and file.content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Allowed types: JPG, PNG, WebP.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Max 25MB check
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 25MB maximum limit.")

    brochure = await BrochureService.get_or_create_user_brochure(db, current_user.id)
    page = await BrochureService.add_page(
        session=db,
        brochure=brochure,
        file_bytes=file_bytes,
        original_filename=file.filename or "page.jpg",
        title=title,
    )
    return BrochurePageItem.model_validate(page)


@router.post(
    "/my-brochure/reorder",
    response_model=List[BrochurePageItem],
    summary="Reorder brochure pages",
)
async def reorder_brochure_pages(
    payload: BrochurePageReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[BrochurePageItem]:
    """Reorder brochure pages according to the provided page ID array."""
    brochure = await BrochureService.get_or_create_user_brochure(db, current_user.id)
    try:
        pages = await BrochureService.reorder_pages(db, brochure.id, payload.page_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return [BrochurePageItem.model_validate(p) for p in pages]


@router.delete(
    "/my-brochure/pages/{page_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a brochure page",
)
async def delete_brochure_page(
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a page from the brochure and automatically re-sequence remaining pages."""
    brochure = await BrochureService.get_or_create_user_brochure(db, current_user.id)
    deleted = await BrochureService.delete_page(db, brochure.id, page_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found on this brochure.")
    return {"success": True, "deleted_page_id": str(page_id)}


@router.get(
    "/directory",
    response_model=List[BrochureDirectoryItem],
    summary="List all published company brochures for ecosystem discovery",
)
async def get_brochures_directory(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> List[BrochureDirectoryItem]:
    """Retrieve all published exhibitor digital brochures matching optional search query."""
    return await BrochureService.list_directory(db, search=search)


@router.get(
    "/public/{slug}",
    response_model=BrochurePublicView,
    summary="Public flipbook viewer payload with resolved ads",
)
async def get_public_brochure(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> BrochurePublicView:
    """Public flipbook data endpoint delivering pages and dynamically targeted sponsor ads."""
    brochure = await BrochureService.get_brochure_by_slug(db, slug)
    if not brochure or not brochure.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brochure not found or unpublished.")

    viewer_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await BrochureService.record_magazine_open(
        db,
        brochure,
        viewer_ip=viewer_ip,
        user_agent=user_agent,
    )

    try:
        await event_broker.publish(
            "brochure:viewed",
            {
                "brochure_id": str(brochure.id),
                "slug": brochure.slug,
                "company_name": brochure.company_name,
            },
        )
    except Exception:
        pass

    # Resolve active top banner & pre-roll ads
    top_ad, pre_ad = await BrochureService.resolve_brochure_ads(db, brochure.id)

    return BrochurePublicView(
        id=brochure.id,
        company_name=brochure.company_name,
        title=brochure.title,
        description=brochure.description,
        slug=brochure.slug,
        total_pages=len(brochure.pages),
        pages=[BrochurePageItem.model_validate(p) for p in brochure.pages],
        top_banner_ad=BrochureAdItem.model_validate(top_ad) if top_ad else None,
        pre_roll_ad=BrochureAdItem.model_validate(pre_ad) if pre_ad else None,
    )


@router.post(
    "/public/{slug}/page-read",
    status_code=status.HTTP_200_OK,
    summary="Record page-level read telemetry for a public brochure",
)
async def track_brochure_page_reads(
    slug: str,
    payload: BrochurePageReadEventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Log individual brochure page views over time and broadcast live SSE sync updates."""
    brochure = await BrochureService.get_brochure_by_slug(db, slug)
    if not brochure or not brochure.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brochure not found or unpublished.")

    viewer_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    recorded = await BrochureService.record_page_reads(
        session=db,
        brochure=brochure,
        page_numbers=payload.page_numbers,
        session_key=payload.session_key,
        view_mode=payload.view_mode,
        viewer_ip=viewer_ip,
        user_agent=user_agent,
    )

    if recorded:
        try:
            await event_broker.publish(
                "brochure:page_read",
                {
                    "brochure_id": str(brochure.id),
                    "slug": brochure.slug,
                    "page_numbers": recorded,
                },
            )
        except Exception:
            pass

    return {"success": True, "recorded_pages": recorded}


@router.get(
    "/my-brochure/analytics",
    response_model=BrochureAnalyticsDetail,
    summary="Get page & time-series analytics for the current user's company brochure",
)
async def get_my_brochure_analytics(
    period: str = "7d",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BrochureAnalyticsDetail:
    """Return reads over time and per-page engagement breakdown for the owner's brochure."""
    return await BrochureService.get_owner_brochure_analytics(
        session=db,
        user_id=current_user.id,
        period=period,
    )


@router.post(
    "/ads/{ad_id}/track",
    status_code=status.HTTP_200_OK,
    summary="Record ad impression or click telemetry",
)
async def track_ad_event(
    ad_id: uuid.UUID,
    payload: BrochureAdEventCreate,
    request: Request,
    brochure_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Log an impression or click event for a sponsor ad."""
    viewer_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await BrochureService.record_ad_event(
        session=db,
        ad_id=ad_id,
        brochure_id=brochure_id,
        event_type=payload.event_type,
        viewer_ip=viewer_ip,
        user_agent=user_agent,
    )
    return {"success": True, "event": payload.event_type}


@router.get(
    "/viewer-settings",
    response_model=FlipbookViewerSettings,
    summary="Get summit-wide flipbook acoustics and page-turn animation defaults",
)
async def get_flipbook_viewer_settings() -> FlipbookViewerSettings:
    """Return global sound and animation defaults configured in Admin."""
    data = BrochureService.get_viewer_settings()
    return FlipbookViewerSettings(**data)

