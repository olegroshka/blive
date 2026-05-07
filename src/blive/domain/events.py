"""Domain events.

SSOT is :doc:`../../docs/inv/domain_events.md` (INV-5). The ``DomainEvent``
union widens milestone-by-milestone; M1 adds :class:`RiskBreach` (INV-5
row ``risk.breach``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

from blive.domain.types import (
    AccountSnapshot,
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

    Values are the implemented subset (M1 + M3.1); widens at M4 with the
    rest of the RC set.
    """

    RC_08 = "RC-08"  # stale data
    RC_09 = "RC-09"  # market hours
    RC_10 = "RC-10"  # reference price sanity (M3.1; ADR-050)
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


# --- AccountUpdate (INV-5 row `account.update`; M2) -------------------------


@dataclass(frozen=True, slots=True)
class AccountUpdate:
    """Periodic account-snapshot emission per [ADR-033](../decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence).

    Wraps the existing :class:`AccountSnapshot` (DD-1 §2.8) with a
    topic-friendly type identity for the [INV-5](../inv/domain_events.md)
    catalogue and the :data:`DomainEvent` union. Cadence + diff-suppress
    thresholds live on the IB adapter side (the field-level emission
    rule is per ADR-033 §"Decision"; not part of this dataclass).
    """

    snapshot: AccountSnapshot
    time_utc: datetime

    def __post_init__(self) -> None:
        _require_utc(self.time_utc, "AccountUpdate.time_utc")
        # Per DD-2 §4: time_utc equals snapshot.taken_at by convention.
        # Don't enforce strict equality (clock skew between subsample
        # tick and snapshot construction is possible); enforce ordering
        # only as a defensive check.
        if self.time_utc < self.snapshot.taken_at:
            raise ValueError(
                f"AccountUpdate.time_utc ({self.time_utc}) must be >= "
                f"snapshot.taken_at ({self.snapshot.taken_at})"
            )


# --- ArtefactFreshnessWarning (INV-5 row `artefact.freshness_warning`; M2) --


@dataclass(frozen=True, slots=True)
class ArtefactFreshnessWarning:
    """RC-12 warn-threshold artefact-freshness event per [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning).

    Triggered by the RiskEngine at the 21-day soft warn threshold; the
    30-day hard threshold emits a :class:`RiskBreach` (RC-12, BLOCK)
    instead. The structured payload (``age_days`` / thresholds) lets the
    UI dashboard render a count-down badge that ``RiskBreach.detail``
    couldn't carry.
    """

    strategy_id: str
    model_name: str
    path: str
    age_days: Decimal
    warning_threshold_days: int
    hard_threshold_days: int
    time_utc: datetime

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("ArtefactFreshnessWarning.strategy_id must be non-empty")
        if not self.model_name:
            raise ValueError("ArtefactFreshnessWarning.model_name must be non-empty")
        if not self.path:
            raise ValueError("ArtefactFreshnessWarning.path must be non-empty")
        if self.age_days <= 0:
            raise ValueError(f"ArtefactFreshnessWarning.age_days must be > 0, got {self.age_days}")
        if self.warning_threshold_days < 1:
            raise ValueError(
                f"ArtefactFreshnessWarning.warning_threshold_days must be >= 1, "
                f"got {self.warning_threshold_days}"
            )
        if self.hard_threshold_days <= self.warning_threshold_days:
            raise ValueError(
                f"ArtefactFreshnessWarning.hard_threshold_days "
                f"({self.hard_threshold_days}) must be > warning_threshold_days "
                f"({self.warning_threshold_days})"
            )
        _require_utc(self.time_utc, "ArtefactFreshnessWarning.time_utc")


# --- DomainEvent union (INV-5 §2) -------------------------------------------

# M0 + M1 + M2 subset. Widens as M4/M5/M7 milestones land per INV-5 §2.
DomainEvent: TypeAlias = (
    OrderEvent | ConnectionStatus | RiskBreach | AccountUpdate | ArtefactFreshnessWarning
)


__all__ = [
    "OrderEvent",
    "ConnectionStatus",
    "RiskBreach",
    "RiskBreachSeverity",
    "RiskCheckCode",
    "AccountUpdate",
    "ArtefactFreshnessWarning",
    "DomainEvent",
]
