"""Tests for the in-process EventBus."""

import asyncio

from app.events import EventBus, get_event_bus


async def test_publish_reaches_subscriber() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    assert len(bus._subscribers.get(1, ())) == 1

    await bus.publish(1, {"type": "test", "message": "hi"})
    assert queue.get_nowait() == {"type": "test", "message": "hi", "seq": 1}


async def test_publish_without_subscribers_is_noop() -> None:
    bus = EventBus()
    await bus.publish(99, {"type": "test"})  # must not raise


async def test_unsubscribe_removes_queue() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    await bus.unsubscribe(1, queue)
    assert 1 not in bus._subscribers
    await bus.unsubscribe(1, queue)  # idempotent
    await bus.unsubscribe(2, queue)  # unknown user is a no-op


async def test_full_queue_drops_event() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    for i in range(100):  # fill the maxsize=100 queue
        await bus.publish(1, {"i": i})
    await bus.publish(1, {"i": "dropped"})  # must not block or raise
    assert queue.qsize() == 100
    assert queue.get_nowait() == {"i": 0, "seq": 1}


async def test_sequence_numbers_are_monotonic_per_user() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    other = await bus.subscribe(2)
    await bus.publish(1, {"n": 1})
    await bus.publish(1, {"n": 2})
    await bus.publish(2, {"n": 3})
    assert queue.get_nowait()["seq"] == 1
    assert queue.get_nowait()["seq"] == 2
    assert other.get_nowait()["seq"] == 1  # counters are independent per user


async def test_full_queue_creates_detectable_sequence_gap() -> None:
    bus = EventBus()
    queue = await bus.subscribe(1)
    for i in range(100):
        await bus.publish(1, {"i": i})
    await bus.publish(1, {"i": "dropped"})
    received = [queue.get_nowait() for _ in range(100)]
    assert [event["seq"] for event in received] == list(range(1, 101))
    # the dropped event carried seq 101: a client reading 1..100 then 102
    # (or nothing) sees the gap and knows to re-fetch via REST


async def test_multiple_subscribers_fan_out() -> None:
    bus = EventBus()
    q1 = await bus.subscribe(1)
    q2 = await bus.subscribe(1)
    assert len(bus._subscribers.get(1, ())) == 2
    await bus.publish(1, {"n": 1})
    assert q1.get_nowait() == {"n": 1, "seq": 1}
    assert q2.get_nowait() == {"n": 1, "seq": 1}


def test_singleton_bus() -> None:
    assert get_event_bus() is get_event_bus()


async def test_subscribe_lock_serializes() -> None:
    bus = EventBus()
    queues = await asyncio.gather(*(bus.subscribe(i) for i in range(5)))
    assert len(queues) == 5
    assert len(bus._subscribers.get(4, ())) == 1
