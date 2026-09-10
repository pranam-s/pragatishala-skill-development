"""Tests for the SSE events endpoint.

The stream is infinite, so we exercise the endpoint's generator directly
instead of through httpx (whose ASGI transport buffers whole responses).
"""

import asyncio
import json
from types import SimpleNamespace

import pytest
from app.routers.events import stream_events
from fastapi.responses import StreamingResponse

from tests.conftest import login_headers, register_user


async def test_stream_requires_auth(bus_client: tuple[object, object]) -> None:
    client, _bus = bus_client
    response = await client.get("/api/v1/events")
    assert response.status_code == 401


async def test_stream_yields_events_and_cleans_up(
    bus_client: tuple[object, object],
) -> None:
    client, bus = bus_client
    await register_user(client)
    headers = await login_headers(client)
    user_id = (await client.get("/api/v1/users/me", headers=headers)).json()["id"]
    user = SimpleNamespace(id=user_id)

    response = await stream_events(user, bus)
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"

    stream = response.body_iterator
    connected = await asyncio.wait_for(anext(stream), timeout=5)
    assert connected == ": connected\n\n"

    await bus.publish(
        user_id,
        {"type": "assessment.completed", "message": "done", "payload": {"id": 1}},
    )
    # Each yield is one complete SSE frame: event line, data line, blank line.
    chunk = await asyncio.wait_for(anext(stream), timeout=5)
    assert chunk.startswith("event: assessment.completed\ndata: ")
    payload = json.loads(chunk.split("data: ", 1)[1].strip())
    assert payload["payload"] == {"id": 1}

    # Closing the generator runs the finally-block and unsubscribes.
    await stream.aclose()
    assert bus.subscriber_count(user_id) == 0


async def test_keepalive_comment_on_idle(
    monkeypatch: pytest.MonkeyPatch, bus_client: tuple[object, object]
) -> None:
    monkeypatch.setenv("PRAGATISHALA_SSE_KEEPALIVE_SECONDS", "0.05")
    from app.config import get_settings

    get_settings.cache_clear()
    client, bus = bus_client
    await register_user(client)
    headers = await login_headers(client)
    user_id = (await client.get("/api/v1/users/me", headers=headers)).json()["id"]

    response = await stream_events(SimpleNamespace(id=user_id), bus)
    stream = response.body_iterator
    connected = await asyncio.wait_for(anext(stream), timeout=5)
    assert connected == ": connected\n\n"

    keepalive = await asyncio.wait_for(anext(stream), timeout=5)
    assert keepalive == ": keep-alive\n\n"

    await stream.aclose()
    assert bus.subscriber_count(user_id) == 0
