"""In-process real-time event bus backing the SSE endpoint.

Each connected user gets one or more ``asyncio.Queue`` subscribers. Services
publish :class:`~app.schemas.PlatformEvent` payloads when long-running AI work
finishes.

Single-process by design for the MVP; a Redis pub/sub backend is the planned
Phase 3 upgrade (see docs/adr/0004).
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Per-user fan-out of JSON-serializable events."""

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: int) -> asyncio.Queue[dict[str, Any]]:
        """Register a queue for *user_id* and return it."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.setdefault(user_id, set()).add(queue)
        return queue

    async def unsubscribe(self, user_id: int, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a previously registered queue."""
        async with self._lock:
            queues = self._subscribers.get(user_id)
            if queues is not None:
                queues.discard(queue)
                if not queues:
                    del self._subscribers[user_id]

    async def publish(self, user_id: int, event: dict[str, Any]) -> None:
        """Fan *event* out to every subscriber of *user_id*.

        Slow consumers never block publishers: full queues are dropped with a
        warning (the client can always re-fetch authoritative state via REST).
        """
        async with self._lock:
            queues = list(self._subscribers.get(user_id, ()))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Dropping event for user %s: subscriber queue full", user_id)


_bus = EventBus()


def get_event_bus() -> EventBus:
    """Module-level singleton used by routers, services, and tests."""
    return _bus
