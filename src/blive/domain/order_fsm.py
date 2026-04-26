"""Order FSM.

SSOT is :doc:`../../docs/inv/order_state_transitions.md` (INV-13). The
transition table here mirrors INV-13 §3 row-for-row; any change is a
multi-artefact edit per ``CONTEXT_PROTOCOL §3``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from blive.domain.events import OrderEvent
from blive.domain.types import (
    Fill,
    OrderEventKind,
    OrderState,
)


class Trigger(StrEnum):
    """FSM triggers (INV-13 §2)."""

    SUBMIT_CALL = "submit_call"
    WIRE_ACK = "wire_ack"
    WIRE_REJECT = "wire_reject"
    ACCEPT = "accept"
    REJECT = "reject"
    PARTIAL_FILL = "partial_fill"
    FILL = "fill"
    CANCEL = "cancel"
    EXPIRE = "expire"


class IllegalTransition(Exception):
    """Raised when a (state, trigger) pair is not in the transition table."""

    def __init__(self, state: OrderState, trigger: Trigger) -> None:
        self.state = state
        self.trigger = trigger
        super().__init__(f"illegal transition: {state.value} --[{trigger.value}]-->")


# (from_state, trigger) -> (to_state, event_kind | None)
# None event_kind means the transition emits no event (only T1).
# Order matches INV-13 §3 row T1..T14.
_TRANSITIONS: dict[
    tuple[OrderState, Trigger],
    tuple[OrderState, OrderEventKind | None],
] = {
    # T1
    (OrderState.INITIALIZED, Trigger.SUBMIT_CALL): (OrderState.SUBMIT_PENDING, None),
    # T2
    (OrderState.SUBMIT_PENDING, Trigger.WIRE_ACK): (OrderState.SUBMITTED, OrderEventKind.SUBMITTED),
    # T3
    (OrderState.SUBMIT_PENDING, Trigger.WIRE_REJECT): (
        OrderState.REJECTED,
        OrderEventKind.REJECTED,
    ),
    # T4
    (OrderState.SUBMITTED, Trigger.ACCEPT): (OrderState.ACCEPTED, OrderEventKind.ACCEPTED),
    # T5
    (OrderState.SUBMITTED, Trigger.REJECT): (OrderState.REJECTED, OrderEventKind.REJECTED),
    # T6
    (OrderState.SUBMITTED, Trigger.CANCEL): (OrderState.CANCELED, OrderEventKind.CANCELED),
    # T7
    (OrderState.ACCEPTED, Trigger.PARTIAL_FILL): (
        OrderState.PARTIALLY_FILLED,
        OrderEventKind.PARTIAL_FILL,
    ),
    # T8
    (OrderState.ACCEPTED, Trigger.FILL): (OrderState.FILLED, OrderEventKind.FILLED),
    # T9
    (OrderState.ACCEPTED, Trigger.CANCEL): (OrderState.CANCELED, OrderEventKind.CANCELED),
    # T10
    (OrderState.ACCEPTED, Trigger.EXPIRE): (OrderState.EXPIRED, OrderEventKind.EXPIRED),
    # T11
    (OrderState.PARTIALLY_FILLED, Trigger.PARTIAL_FILL): (
        OrderState.PARTIALLY_FILLED,
        OrderEventKind.PARTIAL_FILL,
    ),
    # T12
    (OrderState.PARTIALLY_FILLED, Trigger.FILL): (OrderState.FILLED, OrderEventKind.FILLED),
    # T13
    (OrderState.PARTIALLY_FILLED, Trigger.CANCEL): (OrderState.CANCELED, OrderEventKind.CANCELED),
    # T14
    (OrderState.PARTIALLY_FILLED, Trigger.EXPIRE): (OrderState.EXPIRED, OrderEventKind.EXPIRED),
}


def transition(
    state: OrderState,
    trigger: Trigger,
    *,
    client_order_id: UUID,
    time_utc: datetime,
    venue_order_id: str | None = None,
    fill: Fill | None = None,
    reason: str | None = None,
) -> tuple[OrderState, OrderEvent | None]:
    """Compute the next FSM state and the event to emit.

    Pure function. Does **not** persist or publish — that is the consumer's
    job after observing the returned event.

    Raises ``IllegalTransition`` when ``(state, trigger)`` is not in the
    transition table (INV-13 §3). Raises ``ValueError`` when reason / fill
    payload discipline is violated for the emitted event kind (INV-13 §3
    "Reason discipline" column).
    """
    key = (state, trigger)
    if key not in _TRANSITIONS:
        raise IllegalTransition(state, trigger)

    new_state, event_kind = _TRANSITIONS[key]
    if event_kind is None:
        return new_state, None

    # The OrderEvent dataclass enforces its own reason / fill invariants
    # in __post_init__ (DD-1 §2.6); we let it raise so the rule lives in
    # exactly one place.
    event = OrderEvent(
        client_order_id=client_order_id,
        venue_order_id=venue_order_id,
        kind=event_kind,
        reason=reason,
        time_utc=time_utc,
        fill=fill,
    )
    return new_state, event


def is_terminal(state: OrderState) -> bool:
    """True when the state has no outgoing transitions (FILLED / CANCELED / REJECTED / EXPIRED)."""
    from blive.domain.types import TERMINAL_ORDER_STATES

    return state in TERMINAL_ORDER_STATES


__all__ = [
    "Trigger",
    "IllegalTransition",
    "transition",
    "is_terminal",
]
