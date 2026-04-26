"""Unit tests for the in-memory event bus."""

from __future__ import annotations

import asyncio
from datetime import datetime

from blive.adapters.memory.bus import InMemoryEventBus
from blive.domain.events import ConnectionStatus, DomainEvent


async def test_publish_routes_to_topic_subscribers(frozen_now: datetime) -> None:
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    async def handler(ev: DomainEvent) -> None:
        received.append(ev)

    bus.subscribe("system", handler)
    event = ConnectionStatus(connected=True, detail="hi", time_utc=frozen_now)
    bus.publish("system", event)
    # publish is fire-and-forget; let the scheduled task run
    await asyncio.sleep(0)

    assert received == [event]


async def test_publish_to_unsubscribed_topic_is_noop(frozen_now: datetime) -> None:
    bus = InMemoryEventBus()
    bus.publish(
        "nobody-listening", ConnectionStatus(connected=False, detail="x", time_utc=frozen_now)
    )
    await asyncio.sleep(0)
    # No exception raised, no side effects.


async def test_subscribe_returns_unique_ids() -> None:
    bus = InMemoryEventBus()

    async def handler(ev: DomainEvent) -> None:
        return None

    s1 = bus.subscribe("x", handler)
    s2 = bus.subscribe("x", handler)
    assert s1 != s2


async def test_unsubscribe_stops_delivery(frozen_now: datetime) -> None:
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    async def h1(ev: DomainEvent) -> None:
        received.append(ev)

    sid = bus.subscribe("x", h1)
    bus.unsubscribe(sid)

    bus.publish("x", ConnectionStatus(connected=True, detail="y", time_utc=frozen_now))
    await asyncio.sleep(0)

    assert received == []
