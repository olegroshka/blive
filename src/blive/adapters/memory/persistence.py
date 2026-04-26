"""In-memory :class:`PersistencePort` adapter.

Append-only event log + snapshot blob store, both held in process memory.
For development and unit tests only — SQLite arrives at M4 per ADR-006.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from blive.domain.events import DomainEvent
from blive.domain.ports import EventOffset


class InMemoryPersistence:
    """Implements ``PersistencePort`` against in-process structures."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []
        self._snapshots: dict[str, bytes] = {}
        self._lock = asyncio.Lock()

    async def append(self, event: DomainEvent) -> EventOffset:
        async with self._lock:
            offset = EventOffset(len(self._events))
            self._events.append(event)
            return offset

    async def read_from(self, offset: EventOffset) -> AsyncIterator[DomainEvent]:
        async with self._lock:
            snapshot = list(self._events[offset:])
        for event in snapshot:
            yield event

    async def snapshot(self, key: str, blob: bytes) -> None:
        if not key:
            raise ValueError("snapshot key must be non-empty")
        async with self._lock:
            self._snapshots[key] = blob

    async def load_snapshot(self, key: str) -> bytes | None:
        async with self._lock:
            return self._snapshots.get(key)


__all__ = ["InMemoryPersistence"]
