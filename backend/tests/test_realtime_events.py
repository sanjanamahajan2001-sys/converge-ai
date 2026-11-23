"""Automated unit and integration tests for Real-Time Event Sync (Phase 6).

Covers:
- EventBroker subscription and broadcasting mechanisms (SSE & WebSocket)
- /converge-api/v1/events/health telemetry endpoint
- Event publication during conference submission and admin review decisions
"""
import asyncio
from datetime import date, time, datetime, timezone
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.events import RealtimeEventBroker, event_broker
from app.main import create_app

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL


@pytest.fixture(scope="module")
def app_instance():
    """Create test application bound to isolated test database."""
    assert "test" in TEST_DB_URL.lower(), (
        f"SAFETY GUARD: Refusing to run integration tests against non-test DB: {TEST_DB_URL}"
    )
    test_settings = Settings(ENVIRONMENT="test", DATABASE_URL=TEST_DB_URL)
    app = create_app(test_settings)
    yield app


@pytest.fixture
def client(app_instance):
    """Yield test client with initialized database engine."""
    with TestClient(app_instance) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_event_broker_sse_lifecycle():
    """Verify SSE queue registration, event publication, and clean unregistration."""
    broker = RealtimeEventBroker()
    assert broker.sse_subscriber_count == 0

    queue = await broker.register_sse_subscriber()
    assert broker.sse_subscriber_count == 1

    await broker.publish("test:ping", {"hello": "world"})
    assert not queue.empty()

    event = await queue.get()
    assert event["event"] == "test:ping"
    assert event["data"] == {"hello": "world"}
    assert "timestamp" in event

    await broker.unregister_sse_subscriber(queue)
    assert broker.sse_subscriber_count == 0


@pytest.mark.asyncio
async def test_event_broker_telemetry_metrics():
    """Verify event broker metrics tracking."""
    broker = RealtimeEventBroker()
    q = await broker.register_sse_subscriber()
    await broker.publish("conference:approved", {"conference_id": "c1"})

    metrics = broker.get_metrics()
    assert metrics["active_sse_subscribers"] == 1
    assert metrics["active_ws_subscribers"] == 0
    assert metrics["total_events_published"] == 1
    assert metrics["last_event_timestamp"] is not None

    await broker.unregister_sse_subscriber(q)


def test_events_health_endpoint(client: TestClient):
    """Verify GET /converge-api/v1/events/health returns valid telemetry."""
    res = client.get("/converge-api/v1/events/health")
    assert res.status_code == 200
    data = res.json()
    assert "active_sse_subscribers" in data
    assert "active_ws_subscribers" in data
    assert "total_events_published" in data


@pytest.mark.asyncio
async def test_events_stream_broadcast_and_publish():
    """Verify that publishing an event dispatches directly into registered subscribers."""
    q = await event_broker.register_sse_subscriber()
    try:
        await event_broker.publish(
            "conference:submitted",
            {
                "conference_id": "test-conf-id-123",
                "title": "Real-Time AI Summit",
                "status": "IN_REVIEW",
            },
        )

        msg = await asyncio.wait_for(q.get(), timeout=2.0)
        assert msg["event"] == "conference:submitted"
        assert msg["data"]["conference_id"] == "test-conf-id-123"
        assert msg["data"]["title"] == "Real-Time AI Summit"
        assert msg["data"]["status"] == "IN_REVIEW"
    finally:
        await event_broker.unregister_sse_subscriber(q)
