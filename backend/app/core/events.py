"""Real-Time Event Broker & Pub/Sub System (Phase 6).

Provides an in-memory asynchronous pub/sub event bus supporting:
- Server-Sent Events (SSE) queues for web browsers
- WebSockets for bi-directional and streaming clients
- Cross-panel synchronization: Organizer submissions, Admin approvals/rejections,
  attendee agenda updates, and organizer verification events.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger("converge.events")


class RealtimeEventBroker:
    """Central event broker for real-time conference and system event dispatch."""

    def __init__(self) -> None:
        # Queues for SSE subscribers
        self._sse_subscribers: Set[asyncio.Queue] = set()
        # Active WebSocket connections
        self._ws_subscribers: Set[WebSocket] = set()
        # Metrics and counters
        self._total_published: int = 0
        self._last_event_timestamp: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def sse_subscriber_count(self) -> int:
        return len(self._sse_subscribers)

    @property
    def ws_subscriber_count(self) -> int:
        return len(self._ws_subscribers)

    async def register_sse_subscriber(self) -> asyncio.Queue:
        """Register a new SSE client subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._sse_subscribers.add(queue)
        logger.info("New SSE client subscribed. Active SSE subscribers: %d", len(self._sse_subscribers))
        return queue

    async def unregister_sse_subscriber(self, queue: asyncio.Queue) -> None:
        """Unregister an SSE client subscriber queue."""
        async with self._lock:
            self._sse_subscribers.discard(queue)
        logger.info("SSE client unsubscribed. Active SSE subscribers: %d", len(self._sse_subscribers))

    async def register_ws_subscriber(self, websocket: WebSocket) -> None:
        """Register an active WebSocket connection."""
        async with self._lock:
            self._ws_subscribers.add(websocket)
        logger.info("New WebSocket client subscribed. Active WS subscribers: %d", len(self._ws_subscribers))

    async def unregister_ws_subscriber(self, websocket: WebSocket) -> None:
        """Unregister an active WebSocket connection."""
        async with self._lock:
            self._ws_subscribers.discard(websocket)
        logger.info("WebSocket client unsubscribed. Active WS subscribers: %d", len(self._ws_subscribers))

    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Broadcast a named event and payload to all connected clients (SSE & WebSocket)."""
        now = datetime.now(timezone.utc)
        payload = {
            "event": event_type,
            "data": data or {},
            "timestamp": now.isoformat(),
        }

        async with self._lock:
            self._total_published += 1
            self._last_event_timestamp = now

        logger.info(
            "Broadcasting real-time event: %s to %d SSE, %d WS subscribers",
            event_type,
            len(self._sse_subscribers),
            len(self._ws_subscribers),
        )

        # 1. Dispatch to SSE subscriber queues
        dead_queues = []
        for queue in list(self._sse_subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("SSE subscriber queue full, dropping oldest event.")
                try:
                    queue.get_nowait()
                    queue.put_nowait(payload)
                except Exception:
                    dead_queues.append(queue)
            except Exception:
                dead_queues.append(queue)

        for q in dead_queues:
            await self.unregister_sse_subscriber(q)

        # 2. Dispatch to WebSocket subscribers
        dead_ws = set()
        for ws in list(self._ws_subscribers):
            try:
                await ws.send_json(payload)
            except Exception as ex:
                logger.debug("Failed sending payload to WebSocket client: %s", ex)
                dead_ws.add(ws)

        for ws in dead_ws:
            await self.unregister_ws_subscriber(ws)

    def get_metrics(self) -> Dict[str, Any]:
        """Telemetry snapshot of event broker."""
        return {
            "active_sse_subscribers": len(self._sse_subscribers),
            "active_ws_subscribers": len(self._ws_subscribers),
            "total_events_published": self._total_published,
            "last_event_timestamp": self._last_event_timestamp.isoformat() if self._last_event_timestamp else None,
        }


# Global singleton instance
event_broker = RealtimeEventBroker()
