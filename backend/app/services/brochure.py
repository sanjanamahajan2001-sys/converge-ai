"""Domain service handling company digital brochures, page sequencing, and ad resolution."""
import io
import json
import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models.brochure import (
    AdEventType,
    AdPlacementType,
    BrochureAd,
    BrochureAdAssignment,
    BrochureAdEvent,
    BrochurePage,
    BrochurePageReadEvent,
    CompanyBrochure,
)
from app.db.models.business import BusinessProfile
from app.db.models.organizer import OrganizerProfile
from app.db.models.user import User
from app.schemas.brochure import (
    AdminBrochureAdDetail,
    AdminBrochureAdsListResponse,
    AdminBrochureAnalyticsOverview,
    AdminBrochureCompanyTarget,
    AdminCompanyBrochureOption,
    BrochureAdCreate,
    BrochureAdItem,
    BrochureAdUpdate,
    BrochureAnalyticsDetail,
    BrochureDirectoryItem,
    BrochurePageAnalyticsItem,
    BrochurePageItem,
    BrochurePublicView,
    CompanyBrochureDetail,
    CompanyBrochureUpdate,
    ReadTimeSeriesPoint,
)


def slugify(text: str) -> str:
    """Generate a clean URL slug from string."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "brochure"


class BrochureService:
    """Domain service for brochures and sponsorship assets."""

    @staticmethod
    def _get_brochure_dir(brochure_id: uuid.UUID) -> str:
        """Ensure and return the disk directory for a brochure's uploaded pages."""
        settings = get_settings()
        base_dir = os.path.abspath(settings.UPLOAD_DIR)
        brochure_dir = os.path.join(base_dir, "brochures", str(brochure_id))
        os.makedirs(brochure_dir, exist_ok=True)
        return brochure_dir

    @classmethod
    def process_and_save_page(
        cls,
        brochure_id: uuid.UUID,
        file_bytes: bytes,
        original_filename: str,
        page_number: int,
    ) -> Tuple[str, Optional[str], int, int, Decimal, int]:
        """Save high-resolution page image, compute aspect ratio, and create thumbnail."""
        settings = get_settings()
        brochure_dir = cls._get_brochure_dir(brochure_id)
        file_uuid = uuid.uuid4().hex[:8]
        file_size = len(file_bytes)

        # Detect image format and dimensions via Pillow
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"

        page_filename = f"page_{page_number:03d}_{file_uuid}{ext}"
        page_path = os.path.join(brochure_dir, page_filename)

        thumb_filename = f"thumb_{page_number:03d}_{file_uuid}.webp"
        thumb_path = os.path.join(brochure_dir, thumb_filename)

        width = 1240
        height = 1754
        aspect_ratio = Decimal("0.707")

        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                if height > 0:
                    aspect_ratio = Decimal(str(round(width / height, 3)))
                
                # Convert RGBA to RGB for JPEG compatibility if needed
                save_img = img
                if ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P"):
                    save_img = img.convert("RGB")
                save_img.save(page_path, quality=92, optimize=True)

                # Generate thumbnail (max width 300px)
                thumb = img.copy()
                thumb.thumbnail((300, int(300 / float(aspect_ratio))))
                if thumb.mode in ("RGBA", "P"):
                    thumb = thumb.convert("RGB")
                thumb.save(thumb_path, "WEBP", quality=80)
        except Exception:
            # Fallback raw write if Pillow encountered unhandled encoding
            with open(page_path, "wb") as f:
                f.write(file_bytes)

        # Relative public URLs mapped via /converge-api/v1/uploads
        prefix = settings.API_V1_PREFIX
        image_url = f"{prefix}/uploads/brochures/{brochure_id}/{page_filename}"
        thumb_url = f"{prefix}/uploads/brochures/{brochure_id}/{thumb_filename}"

        return image_url, thumb_url, width, height, aspect_ratio, file_size

    @classmethod
    async def get_or_create_user_brochure(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> CompanyBrochure:
        """Retrieve existing brochure or automatically initialize one for the user's business."""
        # 1. Check for existing brochure owned by user
        stmt = (
            select(CompanyBrochure)
            .where(CompanyBrochure.owner_user_id == user_id)
            .options(selectinload(CompanyBrochure.pages))
        )
        result = await session.execute(stmt)
        brochure = result.scalar_one_or_none()
        if brochure:
            return brochure

        # 2. Lookup BusinessProfile and User company details
        user_stmt = select(User).where(User.id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one()

        bp_stmt = select(BusinessProfile).where(BusinessProfile.user_id == user_id)
        bp_res = await session.execute(bp_stmt)
        business_profile = bp_res.scalar_one_or_none()

        if not business_profile:
            # Auto-provision minimal BusinessProfile if not present
            business_profile = BusinessProfile(
                user_id=user_id,
                company_name=user.company_name or user.full_name,
                is_vendor=False,
                is_buyer=False,
                allow_business_matching=False,
            )
            session.add(business_profile)
            await session.flush()

        # Check if user has an OrganizerProfile with organization_name
        org_stmt = select(OrganizerProfile).where(OrganizerProfile.user_id == user_id)
        org_res = await session.execute(org_stmt)
        organizer_profile = org_res.scalar_one_or_none()

        company_name = (
            (organizer_profile and organizer_profile.organization_name)
            or business_profile.company_name
            or user.company_name
            or user.full_name
            or "Participant Organization"
        )
        base_slug = slugify(company_name)

        # Ensure slug uniqueness
        unique_slug = base_slug
        count = 1
        while True:
            slug_check = await session.execute(
                select(CompanyBrochure.id).where(CompanyBrochure.slug == unique_slug)
            )
            if not slug_check.scalar_one_or_none():
                break
            count += 1
            unique_slug = f"{base_slug}-{count}"

        brochure_desc = (
            (organizer_profile and organizer_profile.bio)
            or business_profile.company_bio
            or f"Official summit guide, handbook, and digital brochure for {company_name}."
        )

        brochure = CompanyBrochure(
            business_profile_id=business_profile.id,
            owner_user_id=user.id,
            company_name=company_name,
            title=f"{company_name} — Official Digital Brochure",
            description=brochure_desc,
            slug=unique_slug,
            is_published=True,
        )
        session.add(brochure)
        await session.commit()
        stmt = (
            select(CompanyBrochure)
            .where(CompanyBrochure.id == brochure.id)
            .options(selectinload(CompanyBrochure.pages))
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    @classmethod
    async def get_brochure_by_slug(
        cls,
        session: AsyncSession,
        slug: str,
    ) -> Optional[CompanyBrochure]:
        """Fetch published brochure by unique URL slug."""
        stmt = (
            select(CompanyBrochure)
            .where(CompanyBrochure.slug == slug)
            .options(selectinload(CompanyBrochure.pages))
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_brochure_by_id(
        cls,
        session: AsyncSession,
        brochure_id: uuid.UUID,
    ) -> Optional[CompanyBrochure]:
        """Fetch brochure by primary key."""
        stmt = (
            select(CompanyBrochure)
            .where(CompanyBrochure.id == brochure_id)
            .options(selectinload(CompanyBrochure.pages))
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def update_brochure(
        cls,
        session: AsyncSession,
        brochure: CompanyBrochure,
        payload: CompanyBrochureUpdate,
    ) -> CompanyBrochure:
        """Update metadata on an existing brochure."""
        if payload.title is not None:
            brochure.title = payload.title.strip()
        if payload.description is not None:
            brochure.description = payload.description.strip()
        if payload.is_published is not None:
            brochure.is_published = payload.is_published
        if payload.slug is not None:
            cleaned_slug = slugify(payload.slug)
            if cleaned_slug != brochure.slug:
                # Check uniqueness
                slug_check = await session.execute(
                    select(CompanyBrochure.id).where(
                        CompanyBrochure.slug == cleaned_slug,
                        CompanyBrochure.id != brochure.id,
                    )
                )
                if slug_check.scalar_one_or_none():
                    raise ValueError(f"Brochure slug '{cleaned_slug}' is already in use.")
                brochure.slug = cleaned_slug

        await session.commit()
        stmt = (
            select(CompanyBrochure)
            .where(CompanyBrochure.id == brochure.id)
            .options(selectinload(CompanyBrochure.pages))
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    @classmethod
    async def add_page(
        cls,
        session: AsyncSession,
        brochure: CompanyBrochure,
        file_bytes: bytes,
        original_filename: str,
        title: Optional[str] = None,
    ) -> BrochurePage:
        """Upload and append a new page to the brochure."""
        # Current maximum page number
        max_page_stmt = select(func.coalesce(func.max(BrochurePage.page_number), 0)).where(
            BrochurePage.brochure_id == brochure.id
        )
        max_page_res = await session.execute(max_page_stmt)
        next_page_num = max_page_res.scalar_one() + 1

        img_url, thumb_url, width, height, aspect, size_bytes = cls.process_and_save_page(
            brochure_id=brochure.id,
            file_bytes=file_bytes,
            original_filename=original_filename,
            page_number=next_page_num,
        )

        page = BrochurePage(
            brochure_id=brochure.id,
            page_number=next_page_num,
            image_url=img_url,
            thumbnail_url=thumb_url,
            title=title or f"Page {next_page_num}",
            aspect_ratio=aspect,
            width=width,
            height=height,
            file_size_bytes=size_bytes,
        )
        session.add(page)
        await session.commit()
        await session.refresh(page)
        return page

    @classmethod
    async def reorder_pages(
        cls,
        session: AsyncSession,
        brochure_id: uuid.UUID,
        page_ids: List[uuid.UUID],
    ) -> List[BrochurePage]:
        """Reorder brochure pages matching the provided ID sequence."""
        # Fetch current pages
        stmt = (
            select(BrochurePage)
            .where(BrochurePage.brochure_id == brochure_id)
        )
        res = await session.execute(stmt)
        current_pages = {p.id: p for p in res.scalars().all()}

        # Verify page IDs match
        for pid in page_ids:
            if pid not in current_pages:
                raise ValueError(f"Page ID {pid} does not belong to brochure {brochure_id}")

        # Temporarily offset page numbers to avoid uq_brochure_page_number conflicts during update
        for idx, pid in enumerate(page_ids, start=1):
            page = current_pages[pid]
            page.page_number = 10000 + idx
        await session.flush()

        # Set final sequential page numbers 1..N
        for idx, pid in enumerate(page_ids, start=1):
            page = current_pages[pid]
            page.page_number = idx
        await session.commit()

        # Return updated ordered list
        ordered_stmt = (
            select(BrochurePage)
            .where(BrochurePage.brochure_id == brochure_id)
            .order_by(BrochurePage.page_number.asc())
        )
        ordered_res = await session.execute(ordered_stmt)
        return list(ordered_res.scalars().all())

    @classmethod
    async def delete_page(
        cls,
        session: AsyncSession,
        brochure_id: uuid.UUID,
        page_id: uuid.UUID,
    ) -> bool:
        """Delete an existing page and re-sequence remaining pages 1..N."""
        del_stmt = delete(BrochurePage).where(
            BrochurePage.id == page_id,
            BrochurePage.brochure_id == brochure_id,
        )
        res = await session.execute(del_stmt)
        if res.rowcount == 0:
            return False

        await session.flush()

        # Re-number remaining pages
        pages_stmt = (
            select(BrochurePage)
            .where(BrochurePage.brochure_id == brochure_id)
            .order_by(BrochurePage.page_number.asc())
        )
        pages_res = await session.execute(pages_stmt)
        remaining = list(pages_res.scalars().all())

        # Offset first
        for idx, p in enumerate(remaining, start=1):
            p.page_number = 10000 + idx
        await session.flush()

        for idx, p in enumerate(remaining, start=1):
            p.page_number = idx
        await session.commit()
        return True

    @classmethod
    async def resolve_brochure_ads(
        cls,
        session: AsyncSession,
        brochure_id: uuid.UUID,
    ) -> Tuple[Optional[BrochureAd], Optional[BrochureAd]]:
        """Resolve active BANNER_TOP and PRE_ROLL ads targeted or globally available."""
        # Find all active ads assigned either specifically to this brochure or globally (NULL)
        stmt = (
            select(BrochureAd, BrochureAdAssignment)
            .join(BrochureAdAssignment, BrochureAdAssignment.ad_id == BrochureAd.id)
            .where(
                BrochureAd.is_active.is_(True),
                (BrochureAdAssignment.brochure_id == brochure_id) | (BrochureAdAssignment.brochure_id.is_(None)),
            )
            .order_by(
                # Targeted ads prioritized over global fallback
                BrochureAdAssignment.brochure_id.isnot(None).desc(),
                BrochureAdAssignment.priority.desc(),
                BrochureAd.created_at.desc(),
            )
        )
        res = await session.execute(stmt)
        records = res.all()

        top_banner_ad = None
        pre_roll_ad = None

        for ad, assignment in records:
            if ad.placement_type == AdPlacementType.BANNER_TOP and top_banner_ad is None:
                top_banner_ad = ad
            elif ad.placement_type == AdPlacementType.PRE_ROLL and pre_roll_ad is None:
                pre_roll_ad = ad

            if top_banner_ad and pre_roll_ad:
                break

        return top_banner_ad, pre_roll_ad

    @classmethod
    async def record_ad_event(
        cls,
        session: AsyncSession,
        ad_id: uuid.UUID,
        brochure_id: Optional[uuid.UUID],
        event_type: AdEventType,
        viewer_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BrochureAdEvent:
        """Store impression or click engagement telemetry."""
        event = BrochureAdEvent(
            ad_id=ad_id,
            brochure_id=brochure_id,
            event_type=event_type,
            viewer_ip=viewer_ip,
            user_agent=user_agent,
        )
        session.add(event)
        await session.commit()
        return event

    @classmethod
    def save_ad_creative(
        cls,
        file_bytes: bytes,
        original_filename: str,
    ) -> str:
        """Save sponsor ad creative image to disk and return public URL."""
        settings = get_settings()
        base_dir = os.path.abspath(settings.UPLOAD_DIR)
        ads_dir = os.path.join(base_dir, "brochures", "ads")
        os.makedirs(ads_dir, exist_ok=True)

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"

        file_id = f"ad_{uuid.uuid4().hex[:12]}{ext}"
        target_path = os.path.join(ads_dir, file_id)

        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                save_img = img
                if ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P"):
                    save_img = img.convert("RGB")
                save_img.save(target_path, quality=90, optimize=True)
        except Exception:
            with open(target_path, "wb") as f:
                f.write(file_bytes)

        prefix = settings.API_V1_PREFIX
        return f"{prefix}/uploads/brochures/ads/{file_id}"

    @classmethod
    async def list_admin_ads(
        cls,
        session: AsyncSession,
    ) -> AdminBrochureAdsListResponse:
        """List all ads with telemetry metrics and brochure assignment details."""
        stmt = (
            select(BrochureAd)
            .options(
                selectinload(BrochureAd.assignments).selectinload(BrochureAdAssignment.brochure)
            )
            .order_by(BrochureAd.created_at.desc())
        )
        res = await session.execute(stmt)
        ads = res.scalars().all()

        # Telemetry aggregations
        telemetry_stmt = (
            select(
                BrochureAdEvent.ad_id,
                BrochureAdEvent.event_type,
                func.count(BrochureAdEvent.id).label("cnt"),
            )
            .group_by(BrochureAdEvent.ad_id, BrochureAdEvent.event_type)
        )
        telemetry_res = await session.execute(telemetry_stmt)
        telemetry_map: dict = {}
        for row in telemetry_res.all():
            ad_id, event_type, count = row[0], row[1], row[2]
            if ad_id not in telemetry_map:
                telemetry_map[ad_id] = {"IMPRESSION": 0, "CLICK": 0}
            telemetry_map[ad_id][event_type] = count

        items: List[AdminBrochureAdDetail] = []
        total_active_ads = 0
        total_impressions = 0
        total_clicks = 0

        for ad in ads:
            if ad.is_active:
                total_active_ads += 1

            impr = telemetry_map.get(ad.id, {}).get("IMPRESSION", 0)
            clicks = telemetry_map.get(ad.id, {}).get("CLICK", 0)
            ctr = round((clicks / impr * 100), 2) if impr > 0 else 0.0

            total_impressions += impr
            total_clicks += clicks

            # Evaluate assignments
            is_global = False
            assigned_ids: List[uuid.UUID] = []
            assigned_brochures: List[AdminBrochureCompanyTarget] = []

            if not ad.assignments:
                is_global = True
            else:
                for asgn in ad.assignments:
                    if asgn.brochure_id is None:
                        is_global = True
                    elif asgn.brochure:
                        assigned_ids.append(asgn.brochure.id)
                        assigned_brochures.append(
                            AdminBrochureCompanyTarget(
                                brochure_id=asgn.brochure.id,
                                company_name=asgn.brochure.company_name,
                                title=asgn.brochure.title,
                                slug=asgn.brochure.slug,
                            )
                        )

            items.append(
                AdminBrochureAdDetail(
                    id=ad.id,
                    sponsor_name=ad.sponsor_name,
                    title=ad.title,
                    placement_type=ad.placement_type,
                    creative_image_url=ad.creative_image_url,
                    destination_url=ad.destination_url,
                    tagline=ad.tagline,
                    is_active=ad.is_active,
                    is_global=is_global,
                    assigned_brochure_ids=assigned_ids,
                    assigned_brochures=assigned_brochures,
                    impression_count=impr,
                    click_count=clicks,
                    ctr=ctr,
                    created_at=ad.created_at,
                    updated_at=ad.updated_at,
                )
            )

        avg_ctr = round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0.0

        return AdminBrochureAdsListResponse(
            items=items,
            total_active_ads=total_active_ads,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            average_ctr=avg_ctr,
        )

    @classmethod
    async def create_admin_ad(
        cls,
        session: AsyncSession,
        payload: BrochureAdCreate,
    ) -> BrochureAd:
        """Create a new sponsored ad campaign with initial assignments."""
        ad = BrochureAd(
            sponsor_name=payload.sponsor_name,
            title=payload.title,
            placement_type=payload.placement_type,
            creative_image_url=payload.creative_image_url,
            destination_url=payload.destination_url,
            tagline=payload.tagline,
            is_active=payload.is_active,
        )
        session.add(ad)
        await session.flush()

        if payload.brochure_ids and len(payload.brochure_ids) > 0:
            for b_id in payload.brochure_ids:
                assignment = BrochureAdAssignment(
                    ad_id=ad.id,
                    brochure_id=b_id,
                    priority=10,
                )
                session.add(assignment)
        else:
            # Default to global fallback
            assignment = BrochureAdAssignment(
                ad_id=ad.id,
                brochure_id=None,
                priority=10,
            )
            session.add(assignment)

        await session.commit()
        return ad

    @classmethod
    async def update_admin_ad(
        cls,
        session: AsyncSession,
        ad_id: uuid.UUID,
        payload: BrochureAdUpdate,
    ) -> Optional[BrochureAd]:
        """Update an existing sponsored ad campaign."""
        stmt = select(BrochureAd).where(BrochureAd.id == ad_id)
        res = await session.execute(stmt)
        ad = res.scalar_one_or_none()
        if not ad:
            return None

        if payload.sponsor_name is not None:
            ad.sponsor_name = payload.sponsor_name
        if payload.title is not None:
            ad.title = payload.title
        if payload.placement_type is not None:
            ad.placement_type = payload.placement_type
        if payload.creative_image_url is not None:
            ad.creative_image_url = payload.creative_image_url
        if payload.destination_url is not None:
            ad.destination_url = payload.destination_url
        if payload.tagline is not None:
            ad.tagline = payload.tagline
        if payload.is_active is not None:
            ad.is_active = payload.is_active

        if payload.brochure_ids is not None:
            del_stmt = delete(BrochureAdAssignment).where(BrochureAdAssignment.ad_id == ad_id)
            await session.execute(del_stmt)

            if len(payload.brochure_ids) == 0:
                assignment = BrochureAdAssignment(
                    ad_id=ad.id,
                    brochure_id=None,
                    priority=10,
                )
                session.add(assignment)
            else:
                for b_id in payload.brochure_ids:
                    assignment = BrochureAdAssignment(
                        ad_id=ad.id,
                        brochure_id=b_id,
                        priority=10,
                    )
                    session.add(assignment)

        await session.commit()
        return ad

    @classmethod
    async def assign_ad_targets(
        cls,
        session: AsyncSession,
        ad_id: uuid.UUID,
        is_global: bool,
        brochure_ids: List[uuid.UUID],
    ) -> bool:
        """Update targeting matrix for a specific ad campaign."""
        stmt = select(BrochureAd).where(BrochureAd.id == ad_id)
        res = await session.execute(stmt)
        ad = res.scalar_one_or_none()
        if not ad:
            return False

        del_stmt = delete(BrochureAdAssignment).where(BrochureAdAssignment.ad_id == ad_id)
        await session.execute(del_stmt)

        if is_global or not brochure_ids:
            assignment = BrochureAdAssignment(
                ad_id=ad.id,
                brochure_id=None,
                priority=10,
            )
            session.add(assignment)
        else:
            for b_id in brochure_ids:
                assignment = BrochureAdAssignment(
                    ad_id=ad.id,
                    brochure_id=b_id,
                    priority=10,
                )
                session.add(assignment)

        await session.commit()
        return True

    @classmethod
    async def delete_admin_ad(
        cls,
        session: AsyncSession,
        ad_id: uuid.UUID,
    ) -> bool:
        """Permanently delete an ad campaign and associated events."""
        del_stmt = delete(BrochureAd).where(BrochureAd.id == ad_id)
        res = await session.execute(del_stmt)
        if res.rowcount == 0:
            return False
        await session.commit()
        return True

    @classmethod
    async def list_company_brochures_for_admin(
        cls,
        session: AsyncSession,
    ) -> List[AdminCompanyBrochureOption]:
        """List all company brochures available for ad targeting."""
        stmt = (
            select(CompanyBrochure)
            .options(selectinload(CompanyBrochure.pages))
            .order_by(CompanyBrochure.company_name.asc())
        )
        res = await session.execute(stmt)
        brochures = res.scalars().all()

        return [
            AdminCompanyBrochureOption(
                id=b.id,
                company_name=b.company_name,
                title=b.title,
                slug=b.slug,
                total_pages=len(b.pages),
                is_published=b.is_published,
            )
            for b in brochures
        ]

    @classmethod
    async def list_directory(
        cls,
        session: AsyncSession,
        search: Optional[str] = None,
    ) -> List[BrochureDirectoryItem]:
        """List all published company brochures with pages for public directory discovery."""
        stmt = (
            select(CompanyBrochure)
            .options(selectinload(CompanyBrochure.pages))
            .where(CompanyBrochure.is_published.is_(True))
            .order_by(CompanyBrochure.created_at.desc())
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    CompanyBrochure.company_name.ilike(pattern),
                    CompanyBrochure.title.ilike(pattern),
                    CompanyBrochure.description.ilike(pattern),
                )
            )
        res = await session.execute(stmt)
        brochures = res.scalars().all()

        results = []
        for b in brochures:
            sorted_pages = sorted(b.pages, key=lambda p: p.page_number)
            # Exclude draft/empty brochures with no pages from public discovery
            if not sorted_pages:
                continue
            cover_img = sorted_pages[0].image_url if sorted_pages else None
            cover_thumb = sorted_pages[0].thumbnail_url if sorted_pages else None
            results.append(
                BrochureDirectoryItem(
                    id=b.id,
                    business_profile_id=b.business_profile_id,
                    owner_user_id=b.owner_user_id,
                    company_name=b.company_name,
                    title=b.title,
                    description=b.description,
                    slug=b.slug,
                    total_pages=len(sorted_pages),
                    cover_image_url=cover_img,
                    cover_thumbnail_url=cover_thumb,
                    view_count=b.view_count,
                    created_at=b.created_at,
                )
            )
        return results

    VALID_SOUND_PRESETS = {
        "REALISTIC_BOOK_FLIP",
        "PAPER_RUSTLE",
        "BOOK_SNAP",
        "GLOSSY_MAGAZINE",
        "DIGITAL_SWOOSH",
        "CARD_FLICK",
        "SILENT",
    }

    VALID_ANIMATION_PRESETS = {
        "REAL_PAGE_FLIP",
        "BOOK_CURL_3D",
        "HARDCOVER_SWING",
        "GLOSSY_GLIDE",
        "DIGITAL_HORIZON",
        "CARD_SNAP",
        "INSTANT_FADE",
    }

    @classmethod
    def _viewer_settings_path(cls) -> str:
        settings = get_settings()
        base_dir = os.path.abspath(settings.UPLOAD_DIR)
        brochures_dir = os.path.join(base_dir, "brochures")
        os.makedirs(brochures_dir, exist_ok=True)
        return os.path.join(brochures_dir, "viewer_settings.json")

    @classmethod
    def get_viewer_settings(cls) -> dict:
        """Load global summit flipbook acoustics and page-turn animation settings."""
        defaults = {
            "sound_preset": "PAPER_RUSTLE",
            "animation_preset": "BOOK_CURL_3D",
        }
        path = cls._viewer_settings_path()
        if not os.path.exists(path):
            return defaults
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            sound = data.get("sound_preset", defaults["sound_preset"])
            anim = data.get("animation_preset", defaults["animation_preset"])
            return {
                "sound_preset": sound if sound in cls.VALID_SOUND_PRESETS else defaults["sound_preset"],
                "animation_preset": anim if anim in cls.VALID_ANIMATION_PRESETS else defaults["animation_preset"],
            }
        except Exception:
            return defaults

    @classmethod
    def update_viewer_settings(cls, sound_preset: str, animation_preset: str) -> dict:
        """Persist global summit flipbook sound & animation settings to disk."""
        if sound_preset not in cls.VALID_SOUND_PRESETS:
            raise ValueError(f"Unsupported sound_preset '{sound_preset}'.")
        if animation_preset not in cls.VALID_ANIMATION_PRESETS:
            raise ValueError(f"Unsupported animation_preset '{animation_preset}'.")

        payload = {
            "sound_preset": sound_preset,
            "animation_preset": animation_preset,
        }
        path = cls._viewer_settings_path()
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, path)
        return payload

    # ------------------------------------------------------------------
    # Magazine & Page Read Telemetry + Time-Series Analytics
    # ------------------------------------------------------------------
    VALID_ANALYTICS_PERIODS = {"24h", "7d", "30d", "all"}

    @staticmethod
    def _normalize_utc(dt: datetime) -> datetime:
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

    @classmethod
    def _resolve_period_cutoff(cls, period: str, now: datetime) -> Tuple[str, Optional[datetime]]:
        clean = (period or "7d").lower().strip()
        if clean not in cls.VALID_ANALYTICS_PERIODS:
            clean = "7d"
        if clean == "24h":
            return clean, now - timedelta(hours=24)
        if clean == "7d":
            return clean, now - timedelta(days=7)
        if clean == "30d":
            return clean, now - timedelta(days=30)
        return "all", None

    @classmethod
    def _build_time_buckets(
        cls,
        period: str,
        now: datetime,
        earliest_dt: Optional[datetime] = None,
    ) -> Tuple[List[Tuple[str, str]], str]:
        """Return ordered (bucket_key, label) pairs and granularity ('hour' | 'day' | 'month')."""
        buckets: List[Tuple[str, str]] = []
        if period == "24h":
            start_hour = (now - timedelta(hours=23)).replace(minute=0, second=0, microsecond=0)
            for idx in range(24):
                slot = start_hour + timedelta(hours=idx)
                buckets.append((slot.strftime("%Y-%m-%dT%H:00Z"), slot.strftime("%H:00")))
            return buckets, "hour"

        today = now.date()
        if period in {"7d", "30d"}:
            days = 7 if period == "7d" else 30
            start_day = today - timedelta(days=days - 1)
            for idx in range(days):
                day = start_day + timedelta(days=idx)
                buckets.append((day.isoformat(), day.strftime("%b %d")))
            return buckets, "day"

        # period == "all"
        earliest_date = cls._normalize_utc(earliest_dt).date() if earliest_dt else today
        span_days = max(0, (today - earliest_date).days)
        if span_days > 60:
            cur_y, cur_m = earliest_date.year, earliest_date.month
            end_y, end_m = today.year, today.month
            while (cur_y, cur_m) <= (end_y, end_m):
                dt_m = datetime(cur_y, cur_m, 1, tzinfo=timezone.utc)
                buckets.append((dt_m.strftime("%Y-%m"), dt_m.strftime("%b %Y")))
                if cur_m == 12:
                    cur_y += 1
                    cur_m = 1
                else:
                    cur_m += 1
            return buckets, "month"

        start_day = min(earliest_date, today - timedelta(days=13))
        total_days = (today - start_day).days + 1
        for idx in range(total_days):
            day = start_day + timedelta(days=idx)
            buckets.append((day.isoformat(), day.strftime("%b %d")))
        return buckets, "day"

    @classmethod
    def _bucket_key_for_dt(cls, dt: datetime, granularity: str) -> str:
        utc_dt = cls._normalize_utc(dt)
        if granularity == "hour":
            return utc_dt.strftime("%Y-%m-%dT%H:00Z")
        if granularity == "month":
            return utc_dt.strftime("%Y-%m")
        return utc_dt.date().isoformat()

    @classmethod
    async def record_magazine_open(
        cls,
        session: AsyncSession,
        brochure: CompanyBrochure,
        viewer_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Increment brochure open counter and log a time-series OPEN telemetry row."""
        brochure.view_count += 1
        session.add(
            BrochurePageReadEvent(
                brochure_id=brochure.id,
                page_id=None,
                page_number=0,
                event_kind="OPEN",
                session_key=None,
                view_mode=None,
                viewer_ip=viewer_ip,
                user_agent=user_agent,
            )
        )
        await session.commit()

    @classmethod
    async def record_page_reads(
        cls,
        session: AsyncSession,
        brochure: CompanyBrochure,
        page_numbers: List[int],
        session_key: Optional[str] = None,
        view_mode: Optional[str] = None,
        viewer_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> List[int]:
        """Log time-series PAGE_READ events for one or more viewed page numbers."""
        pages_by_num = {p.page_number: p for p in brochure.pages}
        clean_numbers: List[int] = []
        seen: Set[int] = set()
        for num in page_numbers:
            if num in pages_by_num and num not in seen:
                seen.add(num)
                clean_numbers.append(num)

        if not clean_numbers:
            return []

        clean_session_key = session_key.strip()[:64] if session_key and session_key.strip() else None
        clean_mode = view_mode.strip()[:20] if view_mode and view_mode.strip() else None

        for num in clean_numbers:
            page_obj = pages_by_num[num]
            session.add(
                BrochurePageReadEvent(
                    brochure_id=brochure.id,
                    page_id=page_obj.id,
                    page_number=num,
                    event_kind="PAGE_READ",
                    session_key=clean_session_key,
                    view_mode=clean_mode,
                    viewer_ip=viewer_ip,
                    user_agent=user_agent,
                )
            )
        await session.commit()
        return clean_numbers

    @classmethod
    async def _compute_brochures_analytics(
        cls,
        session: AsyncSession,
        brochures: List[CompanyBrochure],
        period: str = "7d",
    ) -> Tuple[str, datetime, List[BrochureAnalyticsDetail], List[ReadTimeSeriesPoint], Set[str]]:
        """Aggregate time-series open/page-read metrics across one or more brochures."""
        now = datetime.now(timezone.utc)
        clean_period, cutoff = cls._resolve_period_cutoff(period, now)

        if not brochures:
            buckets, _ = cls._build_time_buckets(clean_period, now)
            empty_series = [ReadTimeSeriesPoint(bucket=k, label=lbl) for k, lbl in buckets]
            return clean_period, now, [], empty_series, set()

        brochure_ids = [b.id for b in brochures]

        # 1. All-time event totals grouped by (brochure_id, event_kind, page_number)
        totals_stmt = (
            select(
                BrochurePageReadEvent.brochure_id,
                BrochurePageReadEvent.event_kind,
                BrochurePageReadEvent.page_number,
                func.count(BrochurePageReadEvent.id),
            )
            .where(BrochurePageReadEvent.brochure_id.in_(brochure_ids))
            .group_by(
                BrochurePageReadEvent.brochure_id,
                BrochurePageReadEvent.event_kind,
                BrochurePageReadEvent.page_number,
            )
        )
        totals_rows = (await session.execute(totals_stmt)).all()

        all_time_opens_by_b: Dict[uuid.UUID, int] = defaultdict(int)
        all_time_reads_by_b: Dict[uuid.UUID, int] = defaultdict(int)
        all_time_page_reads: Dict[Tuple[uuid.UUID, int], int] = defaultdict(int)

        for b_id, ev_kind, p_num, cnt in totals_rows:
            if ev_kind == "OPEN":
                all_time_opens_by_b[b_id] += int(cnt)
            else:
                all_time_reads_by_b[b_id] += int(cnt)
                all_time_page_reads[(b_id, int(p_num))] += int(cnt)

        # 2. Events inside the selected period
        events_stmt = (
            select(BrochurePageReadEvent)
            .where(BrochurePageReadEvent.brochure_id.in_(brochure_ids))
            .order_by(BrochurePageReadEvent.created_at.asc())
        )
        if cutoff is not None:
            events_stmt = events_stmt.where(BrochurePageReadEvent.created_at >= cutoff)
        period_events = (await session.execute(events_stmt)).scalars().all()

        earliest_dt = period_events[0].created_at if period_events else None
        buckets, granularity = cls._build_time_buckets(clean_period, now, earliest_dt=earliest_dt)

        combined_opens_bucket: Dict[str, int] = defaultdict(int)
        combined_reads_bucket: Dict[str, int] = defaultdict(int)
        portfolio_sessions: Set[str] = set()

        opens_by_b: Dict[uuid.UUID, int] = defaultdict(int)
        reads_by_b: Dict[uuid.UUID, int] = defaultdict(int)
        sessions_by_b: Dict[uuid.UUID, Set[str]] = defaultdict(set)
        last_activity_by_b: Dict[uuid.UUID, datetime] = {}
        b_opens_bucket: Dict[uuid.UUID, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        b_reads_bucket: Dict[uuid.UUID, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        page_period_reads: Dict[Tuple[uuid.UUID, int], int] = defaultdict(int)
        page_sessions: Dict[Tuple[uuid.UUID, int], Set[str]] = defaultdict(set)
        page_last_read: Dict[Tuple[uuid.UUID, int], datetime] = {}

        for ev in period_events:
            ev_dt = cls._normalize_utc(ev.created_at)
            b_key = cls._bucket_key_for_dt(ev_dt, granularity)
            reader_token = (
                ev.session_key
                if ev.session_key
                else (f"ip:{ev.viewer_ip}" if ev.viewer_ip else f"ev:{ev.id}")
            )

            if ev.brochure_id not in last_activity_by_b or ev_dt > last_activity_by_b[ev.brochure_id]:
                last_activity_by_b[ev.brochure_id] = ev_dt

            if ev.event_kind == "OPEN":
                opens_by_b[ev.brochure_id] += 1
                combined_opens_bucket[b_key] += 1
                b_opens_bucket[ev.brochure_id][b_key] += 1
            else:
                reads_by_b[ev.brochure_id] += 1
                combined_reads_bucket[b_key] += 1
                b_reads_bucket[ev.brochure_id][b_key] += 1
                sessions_by_b[ev.brochure_id].add(reader_token)
                portfolio_sessions.add(f"{ev.brochure_id}:{reader_token}")

                p_key = (ev.brochure_id, int(ev.page_number))
                page_period_reads[p_key] += 1
                page_sessions[p_key].add(reader_token)
                if p_key not in page_last_read or ev_dt > page_last_read[p_key]:
                    page_last_read[p_key] = ev_dt

        details: List[BrochureAnalyticsDetail] = []
        for b in brochures:
            sorted_pages = sorted(b.pages, key=lambda p: p.page_number)
            p_reads_total = reads_by_b[b.id]
            b_series = [
                ReadTimeSeriesPoint(
                    bucket=k,
                    label=lbl,
                    opens=b_opens_bucket[b.id].get(k, 0),
                    page_reads=b_reads_bucket[b.id].get(k, 0),
                )
                for k, lbl in buckets
            ]

            page_items: List[BrochurePageAnalyticsItem] = []
            top_page_num: Optional[int] = None
            top_page_reads = 0

            for page in sorted_pages:
                p_key = (b.id, page.page_number)
                period_cnt = page_period_reads.get(p_key, 0)
                all_time_cnt = all_time_page_reads.get(p_key, 0)
                if period_cnt > top_page_reads:
                    top_page_reads = period_cnt
                    top_page_num = page.page_number

                share_pct = round((period_cnt / p_reads_total * 100.0), 1) if p_reads_total > 0 else 0.0
                page_items.append(
                    BrochurePageAnalyticsItem(
                        page_id=page.id,
                        page_number=page.page_number,
                        title=page.title,
                        thumbnail_url=page.thumbnail_url,
                        image_url=page.image_url,
                        read_count=period_cnt,
                        total_read_count=all_time_cnt,
                        unique_readers=len(page_sessions.get(p_key, set())),
                        share_pct=share_pct,
                        last_read_at=page_last_read.get(p_key),
                    )
                )

            uniq_count = len(sessions_by_b[b.id])
            avg_pages = round((p_reads_total / uniq_count), 1) if uniq_count > 0 else 0.0
            total_views_all = max(int(b.view_count or 0), all_time_opens_by_b[b.id])
            period_views = b.view_count if (clean_period == "all" and opens_by_b[b.id] == 0) else max(
                opens_by_b[b.id], b.view_count if clean_period == "all" else 0
            )

            details.append(
                BrochureAnalyticsDetail(
                    brochure_id=b.id,
                    company_name=b.company_name,
                    title=b.title,
                    slug=b.slug,
                    is_published=b.is_published,
                    total_pages=len(sorted_pages),
                    period=clean_period,
                    total_views_all_time=total_views_all,
                    period_views=period_views,
                    total_page_reads_all_time=all_time_reads_by_b[b.id],
                    period_page_reads=p_reads_total,
                    unique_sessions=uniq_count,
                    avg_pages_per_session=avg_pages,
                    top_page_number=top_page_num,
                    last_activity_at=last_activity_by_b.get(b.id),
                    cover_thumbnail_url=(
                        sorted_pages[0].thumbnail_url or sorted_pages[0].image_url
                        if sorted_pages
                        else None
                    ),
                    time_series=b_series,
                    pages=page_items,
                )
            )

        combined_series = [
            ReadTimeSeriesPoint(
                bucket=k,
                label=lbl,
                opens=combined_opens_bucket.get(k, 0),
                page_reads=combined_reads_bucket.get(k, 0),
            )
            for k, lbl in buckets
        ]

        return clean_period, now, details, combined_series, portfolio_sessions

    @classmethod
    async def get_owner_brochure_analytics(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        period: str = "7d",
    ) -> BrochureAnalyticsDetail:
        """Return detailed time-series and per-page analytics for the authenticated company owner."""
        brochure = await cls.get_or_create_user_brochure(session, user_id)
        _, _, details, _, _ = await cls._compute_brochures_analytics(session, [brochure], period=period)
        return details[0]

    @classmethod
    async def get_admin_brochure_analytics(
        cls,
        session: AsyncSession,
        period: str = "7d",
    ) -> AdminBrochureAnalyticsOverview:
        """Return portfolio-wide and per-magazine analytics across all company brochures."""
        stmt = (
            select(CompanyBrochure)
            .options(selectinload(CompanyBrochure.pages))
            .order_by(CompanyBrochure.view_count.desc(), CompanyBrochure.company_name.asc())
        )
        brochures = (await session.execute(stmt)).scalars().all()

        clean_period, now, details, combined_series, portfolio_sessions = (
            await cls._compute_brochures_analytics(session, list(brochures), period=period)
        )

        # Sort magazines by period engagement first, then all-time views
        details.sort(
            key=lambda m: (m.period_page_reads, m.period_views, m.total_views_all_time),
            reverse=True,
        )

        return AdminBrochureAnalyticsOverview(
            period=clean_period,
            generated_at=now,
            total_magazines=len(details),
            published_magazines=sum(1 for d in details if d.is_published),
            total_views_all_time=sum(d.total_views_all_time for d in details),
            period_views=sum(d.period_views for d in details),
            total_page_reads_all_time=sum(d.total_page_reads_all_time for d in details),
            period_page_reads=sum(d.period_page_reads for d in details),
            unique_sessions=len(portfolio_sessions),
            combined_time_series=combined_series,
            magazines=details,
        )

