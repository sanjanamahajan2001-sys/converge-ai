"""Quotes and Multi-Vendor RFQ Dispatch API routes (Quote Subphase 3)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.quote import (
    QuoteRequestCreate,
    QuoteRequestDetail,
    QuoteVendorPanelResponse,
    SendQuoteEmailRequest,
    SendQuoteEmailResponse,
)
from app.services.quote import QuoteService
from app.services.quote_agent import QuoteAgentService

router = APIRouter(prefix="/quotes", tags=["Commercial Quotes & RFQ Dispatch"])


@router.post(
    "/asks",
    response_model=QuoteRequestDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create Procurement Ask (RFQ)",
    description="Initiate a procurement ask and broadcast technical specifications to qualified vendors.",
)
async def create_quote_request(
    payload: QuoteRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteRequestDetail:
    """Create a new procurement ask and broadcast to vendors."""
    return await QuoteService.create_quote_request(db, current_user, payload)


@router.get(
    "/asks/prefill-from-conversation/{conversation_id}",
    response_model=QuoteRequestCreate,
    status_code=status.HTTP_200_OK,
    summary="Prefill Ask from Active Conversation Brief",
    description="Analyze active dialogue and connection context to synthesize a pre-filled ask proposal.",
)
async def prefill_ask_from_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteRequestCreate:
    """Generate pre-filled procurement ask from dialogue brief."""
    return await QuoteAgentService.generate_ask_prefill(db, current_user, conversation_id)


@router.post(
    "/asks/broadcast-from-conversation/{conversation_id}",
    response_model=QuoteRequestDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Broadcast Ask from Conversation to Qualified Vendors",
    description="1-Click action extracting the conversation brief, creating the ask, matching vendors, and publishing real-time events.",
)
async def broadcast_ask_from_conversation(
    conversation_id: UUID,
    payload_override: Optional[QuoteRequestCreate] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteRequestDetail:
    """Broadcast an ask synthesized from conversation to vendors in real-time."""
    return await QuoteAgentService.broadcast_ask_from_conversation(
        db, current_user, conversation_id, payload_override
    )


@router.get(
    "/vendor-panel",
    response_model=QuoteVendorPanelResponse,
    status_code=status.HTTP_200_OK,
    summary="List Incoming Asks (Vendor Quotes Panel)",
    description="Query incoming procurement asks distributed to the authenticated vendor.",
)
async def list_vendor_quotes_panel(
    status: str = Query("all", description="Filter by status: 'all', 'new', 'quoted', 'declined'"),
    search: Optional[str] = Query(None, description="Search across title, product, delivery location, or customer"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteVendorPanelResponse:
    """List incoming asks for authenticated vendor."""
    return await QuoteService.list_vendor_quotes_panel(
        db, current_user, status_filter=status, search=search, page=page, page_size=page_size
    )


@router.get(
    "/buyer-panel",
    response_model=QuoteVendorPanelResponse,
    status_code=status.HTTP_200_OK,
    summary="List My Broadcasted Asks (Buyer Panel)",
    description="Query procurement asks initiated by the authenticated customer delegate.",
)
async def list_buyer_asks_panel(
    status: str = Query("all", description="Filter by status: 'all', 'new', 'quoted', 'declined'"),
    search: Optional[str] = Query(None, description="Search across title, product, delivery location"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteVendorPanelResponse:
    """List broadcasted asks for authenticated buyer."""
    return await QuoteService.list_buyer_asks_panel(
        db, current_user, status_filter=status, search=search, page=page, page_size=page_size
    )


@router.get(
    "/{quote_request_id}",
    response_model=QuoteRequestDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Ask Specifications & Quote History",
    description="Inspect full technical specifications and quoting history of an ask.",
)
async def get_quote_request_detail(
    quote_request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteRequestDetail:
    """Get full specifications of an ask with IDOR enforcement."""
    return await QuoteService.get_quote_request_detail(db, current_user, quote_request_id)


@router.post(
    "/matches/{match_id}/send-email",
    response_model=SendQuoteEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Send Commercial Quote via Email",
    description="Submit quotation terms and deliver a branded HTML quotation directly to the customer's email.",
)
async def send_quote_via_email(
    match_id: UUID,
    payload: SendQuoteEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SendQuoteEmailResponse:
    """Dispatch formal quotation to customer via email."""
    return await QuoteService.send_quote_via_email(db, current_user, match_id, payload)


@router.post(
    "/matches/{match_id}/decline",
    status_code=status.HTTP_200_OK,
    summary="Decline Incoming Ask",
    description="Mark an incoming procurement inquiry as declined by the vendor.",
)
async def decline_quote_request(
    match_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Decline an incoming ask."""
    return await QuoteService.decline_quote_request(db, current_user, match_id)


@router.post(
    "/conversations/{conversation_id}/direct-quote",
    response_model=SendQuoteEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Dispatch Direct Quotation from 1-on-1 Conversation",
    description="Allows a vendor participant in a bilateral conversation to formulate and dispatch an official commercial quotation via email directly to the customer delegate.",
)
async def send_direct_quote_from_conversation(
    conversation_id: UUID,
    payload: SendQuoteEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SendQuoteEmailResponse:
    """Dispatch formal commercial quotation directly from active bilateral conversation."""
    return await QuoteService.send_direct_quote_from_conversation(
        db, current_user, conversation_id, payload
    )
