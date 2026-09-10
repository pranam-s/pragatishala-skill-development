"""Server-Sent Events endpoint for real-time updates (Phase 2)."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.deps import BusDep, CurrentUser

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def stream_events(current_user: CurrentUser, bus: BusDep) -> StreamingResponse:
    """Stream this user's platform events as Server-Sent Events."""
    queue = await bus.subscribe(current_user.id)
    keepalive = get_settings().sse_keepalive_seconds

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield ": connected\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=keepalive)
                    payload = json.dumps(event, default=str)
                    yield f"event: {event.get('type', 'message')}\ndata: {payload}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            await bus.unsubscribe(current_user.id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
