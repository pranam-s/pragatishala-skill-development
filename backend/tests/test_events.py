"""Tests for the in-process EventBus."""

import asyncio

from app.events import EventBus, get_event_bus


async def test_publish_reaches_subscriber() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    assert bus.subscriber_count(1) == 1

    await bus.publish(1, {"type": "test", "message": "hi"})
    assert queue.get_nowait() == {"type": "test", "message": "hi"}


async def test_publish_without_subscribers_is_noop() -> None:
    bus = EventBus()
    await bus.publish(99, {"type": "test"})  # must not raise


async def test_unsubscribe_removes_queue() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    await bus.unsubscribe(1, queue)
    assert bus.subscriber_count(1) == 0
    await bus.unsubscribe(1, queue)  # idempotent
    await bus.unsubscribe(2, queue)  # unknown user is a no-op


async def test_full_queue_drops_event() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    for i in range(100):  # fill the maxsize=100 queue
        await bus.publish(1, {"i": i})
    await bus.publish(1, {"i": "dropped"})  # must not block or raise
    assert queue.qsize() == 100
    assert queue.get_nowait() == {"i": 0}


async def test_multiple_subscribers_fan_out() -> None:
    bus = EventBus()
    q1 = await bus.subscribe(1)
    q2 = await bus.subscribe(1)
    assert bus.subscriber_count(1) == 2
    await bus.publish(1, {"n": 1})
    assert q1.get_nowait() == {"n": 1}
    assert q2.get_nowait() == {"n": 1}


def test_singleton_bus() -> None:
    assert get_event_bus() is get_event_bus()


async def test_subscribe_lock_serializes() -> None:
    bus = EventBus()
    queues = await asyncio.gather(*(bus.subscribe(i) for i in range(5)))
    assert len(queues) == 5
    assert bus.subscriber_count(4) == 1
