"""Domain events.

SSOT is :doc:`../../docs/inv/domain_events.md` (INV-5). The ``DomainEvent``
union widens milestone-by-milestone; M0 ships ``OrderEvent`` and
``ConnectionStatus``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias
from uuid import UUID

from blive.domain.types import (
    Fill,
    OrderEventKind,
    _require_utc,
)

# --- OrderEvent (DD-1 §2.6 / INV-5 row 1–7) ---------------------------------


@dataclass(frozen=True, slots=True)
class OrderEvent:
    """One observed FSM transition for an order.

    Emitted by ``blive.domain.order_fsm.transition`` whenever a non-internal
    transition fires. See INV-13 §3 for the per-transition emission rule.
    """

    client_order_id: UUID
    venue_order_id: str | None
    kind: OrderEventKind
    reason: str | None
    time_utc: datetime
    fill: Fill | None = None

    def __post_init__(self) -> None:
        _require_utc(self.time_utc, "OrderEvent.time_utc")
        # Reason discipline (INV-13 §3 column 5)
        if self.kind == OrderEventKind.REJECTED and not self.reason:
            raise ValueError("OrderEvent.reason required for REJECTED")
        if self.kind == OrderEventKind.CANCELED and not self.reason:
            raise ValueError("OrderEvent.reason required for CANCELED")
        # Fill payload discipline
        needs_fill = self.kind in (OrderEventKind.PARTIAL_FILL, OrderEventKind.FILLED)
        if needs_fill and self.fill is None:
            raise ValueError(f"OrderEvent.fill required for {self.kind.value}")
        if not needs_fill and self.fill is not None:
            raise ValueError(f"OrderEvent.fill must be None for {self.kind.value}")


# --- ConnectionStatus (DD-1 §2.10 / INV-5 broker.connection) -----------------


@dataclass(frozen=True, slots=True)
class ConnectionStatus:
    """Broker connectivity state-change event.

    Adapter-emitted on connect / disconnect. The PaperBroker emits a single
    ``connected=True`` on construction.
    """

    connected: bool
    detail: str
    time_utc: datetime

    def __post_init__(self) -> None:
        if not self.detail:
            raise ValueError("ConnectionStatus.detail must be non-empty")
        _require_utc(self.time_utc, "ConnectionStatus.time_utc")


# --- DomainEvent union (INV-5 §2) -------------------------------------------

# M0 subset. Widens as later milestones land per INV-5 §2.
DomainEvent: TypeAlias = OrderEvent | ConnectionStatus


__all__ = [
    "OrderEvent",
    "ConnectionStatus",
    "DomainEvent",
]
