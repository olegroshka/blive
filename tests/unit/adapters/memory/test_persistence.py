"""Unit tests for the in-memory persistence adapter."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from blive.adapters.memory.persistence import InMemoryPersistence
from blive.domain.events import ConnectionStatus, OrderEvent
from blive.domain.ports import EventOffset
from blive.domain.types import OrderEventKind


async def _conn(detail: str, when: datetime) -> ConnectionStatus:
    return ConnectionStatus(connected=True, detail=detail, time_utc=when)


async def test_append_returns_monotonic_offsets(frozen_now: datetime) -> None:
    p = InMemoryPersistence()
    o1 = await p.append(await _conn("first", frozen_now))
    o2 = await p.append(await _conn("second", frozen_now))
    o3 = await p.append(await _conn("third", frozen_now))
    assert (o1, o2, o3) == (0, 1, 2)


async def test_read_from_yields_events_in_insertion_order(frozen_now: datetime) -> None:
    p = InMemoryPersistence()
    e1 = await _conn("a", frozen_now)
    e2 = await _conn("b", frozen_now)
    e3 = await _conn("c", frozen_now)
    await p.append(e1)
    await p.append(e2)
    await p.append(e3)

    out = [ev async for ev in p.read_from(EventOffset(0))]
    assert out == [e1, e2, e3]


async def test_read_from_offset_skips_earlier(frozen_now: datetime) -> None:
    p = InMemoryPersistence()
    e1 = await _conn("a", frozen_now)
    e2 = await _conn("b", frozen_now)
    e3 = await _conn("c", frozen_now)
    await p.append(e1)
    await p.append(e2)
    await p.append(e3)

    out = [ev async for ev in p.read_from(EventOffset(2))]
    assert out == [e3]


async def test_read_from_past_end_yields_nothing(frozen_now: datetime) -> None:
    p = InMemoryPersistence()
    await p.append(await _conn("a", frozen_now))
    out = [ev async for ev in p.read_from(EventOffset(99))]
    assert out == []


async def test_snapshot_roundtrip() -> None:
    p = InMemoryPersistence()
    assert await p.load_snapshot("k") is None
    await p.snapshot("k", b"\x00\x01")
    assert await p.load_snapshot("k") == b"\x00\x01"


async def test_snapshot_overwrites() -> None:
    p = InMemoryPersistence()
    await p.snapshot("k", b"first")
    await p.snapshot("k", b"second")
    assert await p.load_snapshot("k") == b"second"


async def test_appending_order_event_works(frozen_now: datetime) -> None:
    """Concrete check that the union type doesn't reject OrderEvent payloads."""
    p = InMemoryPersistence()
    ev = OrderEvent(
        client_order_id=uuid4(),
        venue_order_id="paper-1",
        kind=OrderEventKind.SUBMITTED,
        reason=None,
        time_utc=frozen_now,
    )
    offset = await p.append(ev)
    assert offset == 0
    out = [e async for e in p.read_from(EventOffset(0))]
    assert out == [ev]
