"""Domain events.

SSOT is :doc:`../../docs/inv/domain_events.md` (INV-5). The ``DomainEvent``
union widens milestone-by-milestone; M1 adds :class:`RiskBreach` (INV-5
row ``risk.breach``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

from blive.domain.types import (
    Fill,
    OrderEventKind,
    Severity,
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


# --- RiskBreach (INV-5 row `risk.breach`; M1) -------------------------------


class RiskBreachSeverity(StrEnum):
    """Per INV-4 §"On-breach actions"."""

    BLOCK = "block"
    SCALE = "scale"
    WARN = "warn"


class RiskCheckCode(StrEnum):
    """Stable identifiers matching INV-4 row labels.

    Values are M1 subset; widens at M4 with the rest of the RC set.
    """

    RC_08 = "RC-08"  # stale data
    RC_09 = "RC-09"  # market hours
    RC_12 = "RC-12"  # model-artefact freshness
    RC_13 = "RC-13"  # kill-switch armed


@dataclass(frozen=True, slots=True)
class RiskBreach:
    """One risk-check breach observed by the RiskEngine.

    Lives on the domain-event side per INV-5 §2 so the ``DomainEvent`` union
    can include it without inverting the layer dependency
    (``blive.risk`` → ``blive.domain``).
    """

    strategy_id: str
    check: RiskCheckCode
    severity: RiskBreachSeverity
    detail: str
    time_utc: datetime

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("RiskBreach.strategy_id must be non-empty")
        if not self.detail:
            raise ValueError("RiskBreach.detail must be non-empty")
        _require_utc(self.time_utc, "RiskBreach.time_utc")

    def alert_severity(self) -> Severity:
        """Map RiskBreachSeverity → AlertPort.Severity per INV-13 §4."""
        if self.severity == RiskBreachSeverity.BLOCK:
            return Severity.HIGH
        if self.severity == RiskBreachSeverity.SCALE:
            return Severity.MEDIUM
        return Severity.LOW


# --- DomainEvent union (INV-5 §2) -------------------------------------------

# M0+M1 subset. Widens as later milestones land per INV-5 §2.
DomainEvent: TypeAlias = OrderEvent | ConnectionStatus | RiskBreach


__all__ = [
    "OrderEvent",
    "ConnectionStatus",
    "RiskBreach",
    "RiskBreachSeverity",
    "RiskCheckCode",
    "DomainEvent",
]
