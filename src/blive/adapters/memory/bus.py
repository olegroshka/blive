"""In-memory :class:`EventBusPort` adapter.

Topic-routed pub/sub. Subscribers receive events as scheduled tasks on the
running event loop; ``publish`` is fire-and-forget.
"""

from __future__ import annotations

import asyncio

from blive.domain.events import DomainEvent
from blive.domain.ports import EventHandler, SubscriptionId


class InMemoryEventBus:
    """Implements ``EventBusPort``. Single-process, single-loop only."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[SubscriptionId, EventHandler]]] = {}
        self._next_id = 0

    def publish(self, topic: str, event: DomainEvent) -> None:
        for _, handler in self._subscribers.get(topic, []):
            asyncio.create_task(handler(event))

    def subscribe(
        self,
        topic: str,
        handler: EventHandler,
    ) -> SubscriptionId:
        sid = SubscriptionId(self._next_id)
        self._next_id += 1
        self._subscribers.setdefault(topic, []).append((sid, handler))
        return sid

    def unsubscribe(self, sid: SubscriptionId) -> None:
        """Best-effort removal. Convenience method beyond the Port surface."""
        for topic, subs in self._subscribers.items():
            self._subscribers[topic] = [(s, h) for s, h in subs if s != sid]


__all__ = ["InMemoryEventBus"]
