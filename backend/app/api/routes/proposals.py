"""Proposal Generation & Dual-Sided Approval API routes (Phase 7 - Subphases 3 & 4)."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_client_ip, get_current_user
from app.db.models.proposal import ProposalStatus
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.proposal import (
    CounterProposalRequest,
    DisclosedContactCredentials,
    ProposalApprovalRequest,
    ProposalCreateRequest,
    ProposalDetailResponse,
    ProposalDraftPrefillRequest,
    ProposalDraftPrefillResponse,
    ProposalListItem,
    ProposalRejectionRequest,
    ProposalRevisionDiffResponse,
)
from app.services.proposal import ProposalService
from app.services.proposal_agent import ProposalAgentService
from app.services.proposal_approval import ProposalApprovalService

logger = logging.getLogger("converge.api.proposals")

router = APIRouter(prefix="/proposals", tags=["Commercial Proposals & Dual-Sided Approval"])


@router.post(
    "",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Formal Proposal (Revision 1)",
    description="Transition bilateral dialogue into a binding commercial contract offer.",
)
async def create_proposal(
    request: Request,
    payload: ProposalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Submit a formal commercial proposal (Revision 1)."""
    client_ip = get_client_ip(request)
    return await ProposalService.create_proposal(db, current_user, payload, client_ip)


@router.post(
    "/draft",
    response_model=ProposalDraftPrefillResponse,
    status_code=status.HTTP_200_OK,
    summary="AI/Auto-Prefill Proposal Draft",
    description="Analyze active dialogue context, frozen business briefs, and catalog offerings to synthesize a pre-populated proposal draft.",
)
async def draft_proposal_prefill(
    payload: ProposalDraftPrefillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDraftPrefillResponse:
    """Generate pre-populated proposal draft."""
    return await ProposalAgentService.generate_draft_prefill(db, current_user, payload)


@router.get(
    "",
    response_model=List[ProposalListItem],
    summary="List Authenticated Delegate's Proposals",
    description="Retrieve all sent and received proposals with tab and status filters.",
)
async def list_proposals(
    status: Optional[ProposalStatus] = Query(default=None, description="Optional status filter"),
    tab: Optional[str] = Query(default=None, description="Segmented tab filter: action_required, approved, archive"),
    conversation_id: Optional[UUID] = Query(default=None, description="Optional conversation UUID filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[ProposalListItem]:
    """List proposals for the active user."""
    return await ProposalService.list_proposals(
        db, current_user, status_filter=status, tab=tab, conversation_id=conversation_id
    )


@router.get(
    "/{proposal_id}/diff",
    response_model=ProposalRevisionDiffResponse,
    summary="Compare Proposal Revisions",
    description="Compute parameter-by-parameter commercial diff between baseline (from_rev) and target (to_rev) revisions.",
)
async def get_proposal_revision_diff(
    proposal_id: UUID,
    from_rev: int = Query(default=1, ge=1, description="Baseline revision number (default: 1)"),
    to_rev: Optional[int] = Query(default=None, ge=1, description="Target revision number (default: active revision)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalRevisionDiffResponse:
    """Compute structured commercial parameter diff between revisions."""
    return await ProposalApprovalService.compute_revision_diff(
        db, proposal_id, current_user, from_rev_num=from_rev, to_rev_num=to_rev
    )


@router.get(
    "/{proposal_id}",
    response_model=ProposalDetailResponse,
    summary="Get Proposal Detail Sheet",
    description="Fetch full commercial agreement sheet with version history, revision diffs, and approval trail. Contact credentials are strictly gated until mutual approval.",
)
async def get_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Fetch complete proposal details."""
    return await ProposalService.get_proposal(db, proposal_id, current_user)


@router.post(
    "/{proposal_id}/approve",
    response_model=ProposalDetailResponse,
    summary="Approve Active Proposal Revision",
    description="Commit non-repudiable approval. If both parties have approved the active revision, transitions to MUTUALLY_APPROVED and unlocks verified contact credentials.",
)
async def approve_proposal(
    proposal_id: UUID,
    request: Request,
    payload: ProposalApprovalRequest = ProposalApprovalRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Approve active proposal revision."""
    client_ip = get_client_ip(request)
    return await ProposalService.approve_proposal(db, proposal_id, current_user, payload, client_ip)


@router.post(
    "/{proposal_id}/counter",
    response_model=ProposalDetailResponse,
    summary="Submit Counterproposal Revision",
    description="Submit an updated commercial revision (Vk+1). Re-sets required approvals and renews the validity window.",
)
async def counter_proposal(
    proposal_id: UUID,
    request: Request,
    payload: CounterProposalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Counter a proposal by submitting a new revision."""
    client_ip = get_client_ip(request)
    return await ProposalService.counter_proposal(db, proposal_id, current_user, payload, client_ip)


@router.post(
    "/{proposal_id}/reject",
    response_model=ProposalDetailResponse,
    summary="Decline / Reject Proposal",
    description="Formally reject a pending proposal with a mandatory explanation.",
)
async def reject_proposal(
    proposal_id: UUID,
    request: Request,
    payload: ProposalRejectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Reject a proposal."""
    client_ip = get_client_ip(request)
    return await ProposalService.reject_proposal(db, proposal_id, current_user, payload, client_ip)


@router.post(
    "/{proposal_id}/withdraw",
    response_model=ProposalDetailResponse,
    summary="Withdraw Authored Proposal",
    description="Withdraw an authored proposal revision before the counterparty takes action.",
)
async def withdraw_proposal(
    proposal_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProposalDetailResponse:
    """Withdraw an authored proposal."""
    client_ip = get_client_ip(request)
    return await ProposalService.withdraw_proposal(db, proposal_id, current_user, client_ip)


@router.get(
    "/{proposal_id}/contacts",
    response_model=DisclosedContactCredentials,
    summary="Fetch Disclosed Contact Coordinates",
    description="Retrieve verified corporate contact credentials strictly guarded by mutual dual-sided approval. Returns 403 Forbidden if not mutually approved.",
)
async def get_contacts(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DisclosedContactCredentials:
    """Retrieve unlocked contact credentials."""
    return await ProposalService.get_unlocked_contacts(db, proposal_id, current_user)
