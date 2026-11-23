"""FastAPI router for Thematic Networking Circles (Group Chat in Mode A)."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import ErrorResponse
from app.schemas.group_conversation import (
    GroupConversationCreate,
    GroupConversationDetailResponse,
    GroupConversationResponse,
    GroupMessageCreate,
    GroupMessageResponse,
)
from app.services.group_conversation import GroupConversationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups/circles", tags=["Thematic Networking Circles"])


@router.get(
    "",
    response_model=List[GroupConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Circles for Current User",
    responses={
        status.HTTP_200_OK: {"description": "List of user's networking circles.", "model": List[GroupConversationResponse]},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
    },
)
async def list_circles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[GroupConversationResponse]:
    """Fetch all Thematic Networking Circles the authenticated user belongs to."""
    return await GroupConversationService.get_user_circles(db, current_user.id)


@router.post(
    "",
    response_model=GroupConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Thematic Networking Circle",
    responses={
        status.HTTP_201_CREATED: {"description": "Circle created successfully.", "model": GroupConversationDetailResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid participants or payload.", "model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Invited peer not found.", "model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"description": "Active circle with identical members exists.", "model": ErrorResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Active circle quota exceeded.", "model": ErrorResponse},
    },
)
async def create_circle(
    payload: GroupConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GroupConversationDetailResponse:
    """Create a new Thematic Networking Circle with 2 to 4 invited peers (3 to 5 total members)."""
    return await GroupConversationService.create_circle(db, current_user.id, payload)


@router.get(
    "/{group_id}",
    response_model=GroupConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Circle Details & Messages",
    responses={
        status.HTTP_200_OK: {"description": "Circle details with messages.", "model": GroupConversationDetailResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Not a member of this circle.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Circle not found.", "model": ErrorResponse},
    },
)
async def get_circle(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GroupConversationDetailResponse:
    """Fetch complete circle details and message history for authorized members."""
    return await GroupConversationService.get_circle_detail(db, group_id, current_user.id)


@router.post(
    "/{group_id}/messages",
    response_model=GroupMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post Message to Circle",
    responses={
        status.HTTP_201_CREATED: {"description": "Message posted successfully.", "model": GroupMessageResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Circle concluded or inactive.", "model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Not a member of this circle.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Circle not found.", "model": ErrorResponse},
    },
)
async def post_circle_message(
    group_id: UUID,
    payload: GroupMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GroupMessageResponse:
    """Append a human message turn to an active networking circle."""
    return await GroupConversationService.post_message(db, group_id, current_user.id, payload)


@router.post(
    "/{group_id}/leave",
    response_model=GroupConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Leave Circle",
    responses={
        status.HTTP_200_OK: {"description": "Successfully left circle.", "model": GroupConversationResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Not a member of this circle.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Circle not found.", "model": ErrorResponse},
    },
)
async def leave_circle(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GroupConversationResponse:
    """Voluntarily leave a networking circle."""
    return await GroupConversationService.leave_circle(db, group_id, current_user.id)


@router.post(
    "/{group_id}/close",
    response_model=GroupConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Close/Conclude Circle (Host Only)",
    responses={
        status.HTTP_200_OK: {"description": "Circle concluded successfully.", "model": GroupConversationResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Circle not active.", "model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Only the host can close this circle.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Circle not found.", "model": ErrorResponse},
    },
)
async def close_circle(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> GroupConversationResponse:
    """Explicitly conclude an active networking circle (Host only)."""
    return await GroupConversationService.close_circle(db, group_id, current_user.id)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete/Disband Circle (Host Only)",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Circle deleted successfully."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Only the host can delete this circle.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Circle not found.", "model": ErrorResponse},
    },
)
async def delete_circle(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Permanently delete a networking circle and all its messages (Host only)."""
    await GroupConversationService.delete_circle(db, group_id, current_user.id)
    return None
