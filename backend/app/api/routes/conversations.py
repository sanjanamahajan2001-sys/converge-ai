"""Authenticated Participant Conversation & Persistent Messaging API routes (P5-WS2, GAP-06)."""

import logging
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_client_ip, get_current_user
from app.core.session import SESSION_COOKIE_NAME, validate_session
from app.db.models.conversation import Conversation, ConversationOutcome
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.auth import ErrorResponse
from app.schemas.conversation import (
    ConversationActionRequest,
    ConversationBusinessContextResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationOutcomeEnum,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation import ConversationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations & Messaging"])


class ConnectionManager:
    """Manages active WebSocket connections mapped by conversation UUID."""

    def __init__(self) -> None:
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}

    async def connect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()
        self.active_connections[conversation_id].add(websocket)
        logger.info("WebSocket connected for conversation %s (total: %d)", conversation_id, len(self.active_connections[conversation_id]))

    def disconnect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
        logger.info("WebSocket disconnected for conversation %s", conversation_id)

    async def broadcast(self, conversation_id: UUID, message: dict) -> None:
        """Broadcast payload to all connected participants of this conversation."""
        if conversation_id not in self.active_connections:
            return

        dead_connections: Set[WebSocket] = set()
        for connection in list(self.active_connections[conversation_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("Failed to send WebSocket payload to client: %s", e)
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(conversation_id, dead)


manager = ConnectionManager()


async def broadcast_conversation_event(conversation_id: UUID, payload: dict) -> None:
    """Helper to broadcast real-time event payloads to active WebSocket participants."""
    await manager.broadcast(conversation_id, payload)


@router.get(
    "",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Conversations for Current User",
    responses={
        status.HTTP_200_OK: {"description": "List of user conversations.", "model": List[ConversationResponse]},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
    },
)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[ConversationResponse]:
    """Fetch all conversations where the authenticated user is either initiator or target."""
    return await ConversationService.get_participant_conversations(db, current_user.id)


@router.post(
    "",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a New Conversation",
    responses={
        status.HTTP_201_CREATED: {"description": "Conversation successfully initiated.", "model": ConversationDetailResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid initiator/target combination.", "model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Pair in cooldown interval.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Target participant not found.", "model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"description": "Active conversation already exists with participant.", "model": ErrorResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Active conversation quota (3) exceeded.", "model": ErrorResponse},
    },
)
async def create_conversation(
    payload: ConversationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Initiate a 1-to-1 conversation with another participant under deterministic quota and cooldown guards."""
    client_ip = get_client_ip(request)
    return await ConversationService.initiate_conversation(
        db=db,
        initiator=current_user,
        target_id=payload.target_id,
        client_ip=client_ip,
        business_context=payload.business_context,
        auto_start=payload.auto_start or False,
    )


@router.get(
    "/{conversation_id}/business-context",
    response_model=Optional[ConversationBusinessContextResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Frozen Commercial Business Context Snapshot",
    responses={
        status.HTTP_200_OK: {"description": "Commercial business context snapshot or null.", "model": Optional[ConversationBusinessContextResponse]},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied (IDOR protection).", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Conversation not found.", "model": ErrorResponse},
    },
)
async def get_business_context(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[ConversationBusinessContextResponse]:
    """Fetch immutable commercial brief snapshot, strictly isolating non-participants (GAP-06 / Phase 4)."""
    return await ConversationService.get_conversation_business_context(db, conversation_id, current_user.id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Conversation Details and Message History",
    responses={
        status.HTTP_200_OK: {"description": "Conversation details and message list.", "model": ConversationDetailResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied (IDOR protection).", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Conversation not found.", "model": ErrorResponse},
    },
)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Fetch conversation details and chronological message history, strictly isolating non-participants."""
    return await ConversationService.get_conversation_by_id(db, conversation_id, current_user.id)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a Message Turn",
    responses={
        status.HTTP_201_CREATED: {"description": "Message turn persisted and broadcast.", "model": MessageResponse},
        status.HTTP_400_BAD_REQUEST: {"description": "Conversation not yet accepted.", "model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required.", "model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied.", "model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"description": "Conversation not found.", "model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"description": "Conversation completed or 30-turn limit reached.", "model": ErrorResponse},
    },
)
async def post_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Persist a message turn and instantly broadcast to real-time subscribers."""
    client_ip = get_client_ip(request)
    loc_obj = payload.location or payload.location_payload
    loc_dict = loc_obj.model_dump() if loc_obj else None
    msg_type = payload.message_type or ("LOCATION" if loc_dict else "TEXT")
    msg, conv_detail = await ConversationService.append_message(
        db=db,
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=payload.content,
        client_ip=client_ip,
        message_type=msg_type,
        location_payload=loc_dict,
    )

    # Persist-before-publish: message is committed to PostgreSQL before sending event payload
    event_payload = {
        "event": "message:new",
        "data": {
            "id": str(msg.id),
            "conversation_id": str(msg.conversation_id),
            "sender_id": str(msg.sender_id) if msg.sender_id else None,
            "sender_type": msg.sender_type.value,
            "turn_index": msg.turn_index,
            "content": msg.content,
            "message_type": getattr(msg, "message_type", "TEXT") or "TEXT",
            "location_payload": getattr(msg, "location_payload", None),
            "created_at": msg.created_at.isoformat(),
        },
        "conversation_status": conv_detail.status.value,
    }
    await manager.broadcast(conversation_id, event_payload)

    return msg


@router.post(
    "/{conversation_id}/trigger-agent",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Autonomous Virtual Representative Dialogue",
)
async def trigger_agent_dialogue(
    conversation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Explicitly trigger autonomous agent dialogue for an active conversation."""
    client_ip = get_client_ip(request)
    detail = await ConversationService.trigger_agent_dialogue(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        client_ip=client_ip,
    )
    await manager.broadcast(
        conversation_id,
        {
            "event": "conversation:agent_triggered",
            "data": {"conversation_id": str(conversation_id), "status": detail.status.value},
        },
    )
    return detail

@router.post(
    "/{conversation_id}/accept",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Conversation Invitation",
)
async def accept_conversation(
    conversation_id: UUID,
    request: Request,
    trigger_agent: bool = Query(default=True, description="Whether to immediately trigger agent dialogue on accept"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Accept an invited conversation (target participant only)."""
    client_ip = get_client_ip(request)
    updated = await ConversationService.update_conversation_status(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        client_ip=client_ip,
        action="ACCEPT",
        trigger_agent=trigger_agent,
    )
    await manager.broadcast(
        conversation_id,
        {
            "event": "conversation:status",
            "data": {"conversation_id": str(conversation_id), "status": updated.status.value},
        },
    )
    return updated


@router.post(
    "/{conversation_id}/cancel",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Conversation",
)
async def cancel_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Cancel or reject a conversation."""
    client_ip = get_client_ip(request)
    updated = await ConversationService.update_conversation_status(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        client_ip=client_ip,
        action="CANCEL",
    )
    await manager.broadcast(
        conversation_id,
        {
            "event": "conversation:status",
            "data": {
                "conversation_id": str(conversation_id),
                "status": updated.status.value,
                "terminal_outcome": updated.terminal_outcome.value if updated.terminal_outcome else None,
            },
        },
    )
    return updated


@router.post(
    "/{conversation_id}/conclude",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Conclude Active Conversation",
)
async def conclude_conversation(
    conversation_id: UUID,
    payload: ConversationActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """Conclude an active conversation with terminal outcome (PROPOSAL_GENERATED or COMPLETED_WITHOUT_PROPOSAL)."""
    client_ip = get_client_ip(request)
    updated = await ConversationService.update_conversation_status(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        client_ip=client_ip,
        action="CONCLUDE",
        outcome=payload.outcome,
    )
    await manager.broadcast(
        conversation_id,
        {
            "event": "conversation:status",
            "data": {
                "conversation_id": str(conversation_id),
                "status": updated.status.value,
                "terminal_outcome": updated.terminal_outcome.value if updated.terminal_outcome else None,
            },
        },
    )
    return updated


@router.websocket("/ws/{conversation_id}")
async def conversation_websocket_endpoint(
    websocket: WebSocket,
    conversation_id: UUID,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Authenticated real-time WebSocket connection for instant bi-directional messaging."""
    # 1. Resolve authentication token from query param, cookie, or authorization header
    raw_token = token or websocket.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()

    if not raw_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Validate session against database state
    try:
        user_session = await validate_session(session=db, raw_token=raw_token)
        current_user = user_session.user
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3. IDOR Authorization: Verify participant belongs to this conversation
    conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
    conv = await db.scalar(conv_stmt)
    if not conv or (conv.initiator_id != current_user.id and conv.target_id != current_user.id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 4. Register connection
    await manager.connect(conversation_id, websocket)

    try:
        while True:
            # Client heartbeat / ping handling
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(conversation_id, websocket)
    except Exception as e:
        logger.debug("WebSocket connection closed with error: %s", e)
        manager.disconnect(conversation_id, websocket)
