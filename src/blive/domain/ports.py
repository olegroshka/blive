"""Domain ports (Protocols).

SSOT is :doc:`../../docs/inv/ports_adapters.md` (INV-6). Adapters live
under ``blive.adapters.*`` and may import from this module; the domain may
not import from adapters (enforced by import-linter, see ``pyproject.toml``).
"""

from __future__ import annotations

from datetime import datetime
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    NewType,
    Protocol,
    runtime_checkable,
)

from blive.domain.events import ConnectionStatus, DomainEvent, OrderEvent
from blive.domain.types import (
    AccountSnapshot,
    Bar,
    BarFreq,
    ClientOrderId,
    Instrument,
    Order,
    OrderUpdate,
    Position,
    Severity,
    Trade,
)

# --- Opaque ID aliases for the persistence / bus layer ----------------------

EventOffset = NewType("EventOffset", int)
SubscriptionId = NewType("SubscriptionId", int)


# --- BrokerEvent union -------------------------------------------------------

# What ``BrokerPort.events()`` yields. Widens at M2 with AccountUpdate.
BrokerEvent = OrderEvent | ConnectionStatus


# --- Ports (INV-6 §1) --------------------------------------------------------


@runtime_checkable
class BrokerPort(Protocol):
    """The single point of contact between the domain and any broker."""

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def submit(self, order: Order) -> ClientOrderId: ...

    async def cancel(self, client_order_id: ClientOrderId) -> None: ...

    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None: ...

    async def open_orders(self) -> list[Order]: ...

    async def positions(self) -> list[Position]: ...

    async def account_snapshot(self) -> AccountSnapshot: ...

    def events(self) -> AsyncIterator[BrokerEvent]: ...


@runtime_checkable
class MarketDataPort(Protocol):
    async def subscribe_bars(self, instrument: Instrument, freq: BarFreq) -> AsyncIterator[Bar]: ...

    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]: ...

    async def unsubscribe(self, instrument: Instrument) -> None: ...

    async def historical_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
        start: datetime,
        end: datetime,
    ) -> list[Bar]: ...


@runtime_checkable
class ClockPort(Protocol):
    """Time abstraction. Domain code must use this — never ``datetime.now()`` directly."""

    def now(self) -> datetime: ...

    async def sleep(self, seconds: float) -> None: ...


@runtime_checkable
class PersistencePort(Protocol):
    async def append(self, event: DomainEvent) -> EventOffset: ...

    async def read_from(self, offset: EventOffset) -> AsyncIterator[DomainEvent]: ...

    async def snapshot(self, key: str, blob: bytes) -> None: ...

    async def load_snapshot(self, key: str) -> bytes | None: ...


@runtime_checkable
class AlertPort(Protocol):
    async def send(self, severity: Severity, subject: str, body: str) -> None: ...


EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


@runtime_checkable
class EventBusPort(Protocol):
    def publish(self, topic: str, event: DomainEvent) -> None: ...

    def subscribe(
        self,
        topic: str,
        handler: EventHandler,
    ) -> SubscriptionId: ...


__all__ = [
    "BrokerEvent",
    "EventOffset",
    "SubscriptionId",
    "EventHandler",
    "BrokerPort",
    "MarketDataPort",
    "ClockPort",
    "PersistencePort",
    "AlertPort",
    "EventBusPort",
]
