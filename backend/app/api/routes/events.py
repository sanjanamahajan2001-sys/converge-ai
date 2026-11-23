"""Real-Time Event Stream & WebSocket API Routes (Phase 6).

Endpoints:
- GET /events/stream: Server-Sent Events (SSE) stream for real-time conference updates.
- WS  /events/ws: WebSocket endpoint for bi-directional streaming.
- GET /events/health: Event broker telemetry & metrics.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.events import event_broker

logger = logging.getLogger("converge.events.api")

router = APIRouter(prefix="/events", tags=["Real-Time Events"])


@router.get(
    "/health",
    summary="Event Broker Health & Telemetry",
    description="Retrieve active subscriber counts and event publication metrics.",
)
async def get_event_broker_health() -> Dict[str, Any]:
    """Retrieve event broker telemetry metrics."""
    return event_broker.get_metrics()


@router.get(
    "/stream",
    summary="Server-Sent Events Stream",
    description="Stream real-time conference lifecycle, review decisions, and agenda publication updates.",
)
async def stream_realtime_events() -> StreamingResponse:
    """Server-Sent Events endpoint for real-time frontend synchronization."""
    queue = await event_broker.register_sse_subscriber()

    async def sse_generator() -> AsyncGenerator[str, None]:
        # Send initial connection handshake
        now = datetime.now(timezone.utc).isoformat()
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'timestamp': now})}\n\n"

        try:
            while True:
                try:
                    # Wait for next event or send keepalive ping after 15 seconds
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = msg.get("event", "message")
                    data = msg.get("data", {})
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping to prevent proxy/browser timeout
                    yield f": ping {datetime.now(timezone.utc).isoformat()}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            logger.info("SSE client stream connection terminated.")
        finally:
            await event_broker.unregister_sse_subscriber(queue)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        },
    )


@router.websocket("/ws")
async def websocket_events_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time event streaming and health checks."""
    await websocket.accept()
    await event_broker.register_ws_subscriber(websocket)

    # Handshake greeting
    now = datetime.now(timezone.utc).isoformat()
    await websocket.send_json({
        "event": "connected",
        "data": {"status": "connected", "timestamp": now},
    })

    try:
        while True:
            # Client heartbeat ping/pong listener
            text = await websocket.receive_text()
            if text == "ping" or text == '{"type":"ping"}':
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /events/ws")
    except Exception as e:
        logger.debug("WebSocket event loop exception: %s", e)
    finally:
        await event_broker.unregister_ws_subscriber(websocket)
