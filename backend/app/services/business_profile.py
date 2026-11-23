"""Business Profile Domain Service (Phase 7 - Subphase 4).

Provides helper utilities to inspect business profiles, catalog offerings,
and procurement requirements for commercial role resolution and proposal prefill.
"""

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.business import (
    BusinessOffering,
    BusinessProfile,
    BusinessRequirement,
    ProductGrade,
)
from app.db.models.proposal import CommercialRole, ProposalType


class BusinessProfileService:
    """Service providing profile inspection and commercial role resolution."""

    @staticmethod
    async def get_profile_with_catalog(
        db: AsyncSession,
        user_id: UUID,
    ) -> Optional[BusinessProfile]:
        """Fetch business profile with offerings and requirements eagerly loaded."""
        stmt = (
            select(BusinessProfile)
            .where(BusinessProfile.user_id == user_id)
            .options(
                selectinload(BusinessProfile.offerings),
                selectinload(BusinessProfile.requirements),
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    def resolve_bilateral_roles(
        proposer_profile: Optional[BusinessProfile],
        recipient_profile: Optional[BusinessProfile],
        inquiry_type: Optional[str] = None,
    ) -> Tuple[CommercialRole, CommercialRole]:
        """Determine respective commercial roles for the bilateral negotiation pair."""
        inq = (inquiry_type or "").upper()

        # Distribution inquiries
        if inq in ("DISTRIBUTION_EXPANSION", "DISTRIBUTOR_APPLICATION"):
            if proposer_profile and proposer_profile.is_distributor:
                return CommercialRole.DISTRIBUTOR, CommercialRole.SUPPLIER
            return CommercialRole.SUPPLIER, CommercialRole.DISTRIBUTOR

        # Partnership inquiries
        if inq in ("SOURCING_PARTNERSHIP", "EXPLORATORY_COLLABORATION"):
            return CommercialRole.PARTNER, CommercialRole.PARTNER

        # Vendor/Service inquiries
        if inq in ("VENDOR_PITCH", "RFI_SERVICE"):
            if proposer_profile and proposer_profile.is_vendor:
                return CommercialRole.VENDOR, CommercialRole.BUYER
            return CommercialRole.BUYER, CommercialRole.VENDOR

        # Profile-driven role resolution
        if proposer_profile:
            if proposer_profile.is_supplier:
                return CommercialRole.SUPPLIER, CommercialRole.BUYER
            elif proposer_profile.is_vendor:
                return CommercialRole.VENDOR, CommercialRole.BUYER
            elif proposer_profile.is_distributor:
                return CommercialRole.DISTRIBUTOR, CommercialRole.SUPPLIER
            elif proposer_profile.is_partner:
                return CommercialRole.PARTNER, CommercialRole.PARTNER
            elif proposer_profile.is_buyer:
                return CommercialRole.BUYER, CommercialRole.SUPPLIER

        if recipient_profile:
            if recipient_profile.is_buyer:
                return CommercialRole.SUPPLIER, CommercialRole.BUYER
            elif recipient_profile.is_supplier:
                return CommercialRole.BUYER, CommercialRole.SUPPLIER
            elif recipient_profile.is_distributor:
                return CommercialRole.SUPPLIER, CommercialRole.DISTRIBUTOR

        # Fallback default
        return CommercialRole.SUPPLIER, CommercialRole.BUYER

    @staticmethod
    def resolve_proposal_type(
        inquiry_type: Optional[str],
        proposer_role: CommercialRole,
    ) -> ProposalType:
        """Resolve proposal category based on inquiry nature and proposer role."""
        inq = (inquiry_type or "").upper()

        if proposer_role == CommercialRole.DISTRIBUTOR or inq in (
            "DISTRIBUTION_EXPANSION",
            "DISTRIBUTOR_APPLICATION",
        ):
            return ProposalType.DISTRIBUTION_AGREEMENT

        if proposer_role == CommercialRole.PARTNER or inq in (
            "SOURCING_PARTNERSHIP",
            "EXPLORATORY_COLLABORATION",
        ):
            return ProposalType.STRATEGIC_PARTNERSHIP

        if proposer_role == CommercialRole.VENDOR or inq in ("RFI_SERVICE", "VENDOR_PITCH"):
            return ProposalType.SERVICE_MOU

        if proposer_role == CommercialRole.BUYER:
            return ProposalType.PROCUREMENT_ORDER

        return ProposalType.SUPPLY_CONTRACT

    @staticmethod
    async def get_governing_standard_for_grade(
        db: AsyncSession,
        grade_code: Optional[str],
    ) -> Optional[str]:
        """Lookup formal governing standard from product taxonomy."""
        if not grade_code:
            return None
        stmt = select(ProductGrade.governing_standard).where(ProductGrade.grade_code == grade_code)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
