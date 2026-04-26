"""Golden tests for the order FSM (INV-13).

Each transition in INV-13 §3 has a row in :data:`LEGAL_TRANSITIONS` below.
Anything not in that table is illegal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from blive.domain.events import OrderEvent
from blive.domain.order_fsm import (
    IllegalTransition,
    Trigger,
    is_terminal,
    transition,
)
from blive.domain.types import (
    AssetClass,
    Fill,
    Instrument,
    OrderEventKind,
    OrderSide,
    OrderState,
)

# --- Fixtures local to the FSM tests -----------------------------------------


@pytest.fixture
def time_at() -> datetime:
    return datetime(2026, 4, 26, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def order_id() -> UUID:
    return uuid4()


@pytest.fixture
def fill(order_id: UUID, time_at: datetime, cac_pa: Instrument) -> Fill:
    return Fill(
        client_order_id=order_id,
        venue_order_id="paper-1",
        venue_exec_id="paper-1-exec-1",
        instrument=cac_pa,
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("78.42"),
        commission=Decimal("0.05"),
        currency="EUR",
        time_utc=time_at,
    )


# --- The transition table (mirrors INV-13 §3 row T1..T14) -------------------


LEGAL_TRANSITIONS: list[tuple[OrderState, Trigger, OrderState, OrderEventKind | None]] = [
    (OrderState.INITIALIZED, Trigger.SUBMIT_CALL, OrderState.SUBMIT_PENDING, None),
    (OrderState.SUBMIT_PENDING, Trigger.WIRE_ACK, OrderState.SUBMITTED, OrderEventKind.SUBMITTED),
    (OrderState.SUBMIT_PENDING, Trigger.WIRE_REJECT, OrderState.REJECTED, OrderEventKind.REJECTED),
    (OrderState.SUBMITTED, Trigger.ACCEPT, OrderState.ACCEPTED, OrderEventKind.ACCEPTED),
    (OrderState.SUBMITTED, Trigger.REJECT, OrderState.REJECTED, OrderEventKind.REJECTED),
    (OrderState.SUBMITTED, Trigger.CANCEL, OrderState.CANCELED, OrderEventKind.CANCELED),
    (
        OrderState.ACCEPTED,
        Trigger.PARTIAL_FILL,
        OrderState.PARTIALLY_FILLED,
        OrderEventKind.PARTIAL_FILL,
    ),
    (OrderState.ACCEPTED, Trigger.FILL, OrderState.FILLED, OrderEventKind.FILLED),
    (OrderState.ACCEPTED, Trigger.CANCEL, OrderState.CANCELED, OrderEventKind.CANCELED),
    (OrderState.ACCEPTED, Trigger.EXPIRE, OrderState.EXPIRED, OrderEventKind.EXPIRED),
    (
        OrderState.PARTIALLY_FILLED,
        Trigger.PARTIAL_FILL,
        OrderState.PARTIALLY_FILLED,
        OrderEventKind.PARTIAL_FILL,
    ),
    (OrderState.PARTIALLY_FILLED, Trigger.FILL, OrderState.FILLED, OrderEventKind.FILLED),
    (OrderState.PARTIALLY_FILLED, Trigger.CANCEL, OrderState.CANCELED, OrderEventKind.CANCELED),
    (OrderState.PARTIALLY_FILLED, Trigger.EXPIRE, OrderState.EXPIRED, OrderEventKind.EXPIRED),
]


# --- Tests -------------------------------------------------------------------


@pytest.mark.parametrize("from_state,trigger,to_state,event_kind", LEGAL_TRANSITIONS)
def test_each_legal_transition(
    from_state: OrderState,
    trigger: Trigger,
    to_state: OrderState,
    event_kind: OrderEventKind | None,
    order_id: UUID,
    time_at: datetime,
    fill: Fill,
) -> None:
    """Every row of INV-13 §3 lands on the expected (state, event_kind)."""
    kwargs: dict[str, object] = {
        "client_order_id": order_id,
        "time_utc": time_at,
    }
    # Reason / fill discipline (INV-13 §3 column 5).
    if event_kind in (OrderEventKind.REJECTED, OrderEventKind.CANCELED):
        kwargs["reason"] = "test"
    if event_kind in (OrderEventKind.PARTIAL_FILL, OrderEventKind.FILLED):
        kwargs["fill"] = fill
    if event_kind == OrderEventKind.SUBMITTED:
        kwargs["venue_order_id"] = "paper-1"

    new_state, event = transition(from_state, trigger, **kwargs)  # type: ignore[arg-type]

    assert new_state == to_state
    if event_kind is None:
        assert event is None
    else:
        assert isinstance(event, OrderEvent)
        assert event.kind == event_kind
        assert event.client_order_id == order_id
        assert event.time_utc == time_at


def test_full_lifecycle_emits_canonical_sequence(
    order_id: UUID, time_at: datetime, fill: Fill
) -> None:
    """A happy-path order: INITIALIZED → SUBMIT_PENDING → SUBMITTED → ACCEPTED → FILLED."""
    state = OrderState.INITIALIZED

    state, ev = transition(state, Trigger.SUBMIT_CALL, client_order_id=order_id, time_utc=time_at)
    assert state == OrderState.SUBMIT_PENDING and ev is None

    state, ev = transition(
        state,
        Trigger.WIRE_ACK,
        client_order_id=order_id,
        time_utc=time_at,
        venue_order_id="paper-1",
    )
    assert state == OrderState.SUBMITTED
    assert ev is not None and ev.kind == OrderEventKind.SUBMITTED and ev.venue_order_id == "paper-1"

    state, ev = transition(state, Trigger.ACCEPT, client_order_id=order_id, time_utc=time_at)
    assert state == OrderState.ACCEPTED
    assert ev is not None and ev.kind == OrderEventKind.ACCEPTED

    state, ev = transition(
        state, Trigger.FILL, client_order_id=order_id, time_utc=time_at, fill=fill
    )
    assert state == OrderState.FILLED
    assert ev is not None and ev.kind == OrderEventKind.FILLED and ev.fill == fill
    assert is_terminal(state)


# --- Illegal transitions ----------------------------------------------------


_ILLEGAL_SAMPLE: list[tuple[OrderState, Trigger]] = [
    (OrderState.INITIALIZED, Trigger.WIRE_ACK),  # cannot ack before submit_call
    (OrderState.INITIALIZED, Trigger.FILL),
    (OrderState.SUBMIT_PENDING, Trigger.SUBMIT_CALL),  # cannot re-issue
    (OrderState.SUBMIT_PENDING, Trigger.ACCEPT),  # accept comes from SUBMITTED
    (OrderState.SUBMIT_PENDING, Trigger.PARTIAL_FILL),
    (OrderState.SUBMITTED, Trigger.SUBMIT_CALL),
    (OrderState.SUBMITTED, Trigger.WIRE_ACK),
    (OrderState.SUBMITTED, Trigger.PARTIAL_FILL),  # must be ACCEPTED first
    (OrderState.SUBMITTED, Trigger.FILL),
    (OrderState.SUBMITTED, Trigger.EXPIRE),  # only after ACCEPTED
    (OrderState.ACCEPTED, Trigger.SUBMIT_CALL),
    (OrderState.ACCEPTED, Trigger.WIRE_ACK),
    (OrderState.ACCEPTED, Trigger.ACCEPT),
    (OrderState.ACCEPTED, Trigger.WIRE_REJECT),
    (OrderState.PARTIALLY_FILLED, Trigger.WIRE_ACK),
    (OrderState.PARTIALLY_FILLED, Trigger.ACCEPT),
    (OrderState.PARTIALLY_FILLED, Trigger.WIRE_REJECT),
    (OrderState.PARTIALLY_FILLED, Trigger.REJECT),
]


@pytest.mark.parametrize("state,trigger", _ILLEGAL_SAMPLE)
def test_illegal_transition_raises(
    state: OrderState, trigger: Trigger, order_id: UUID, time_at: datetime
) -> None:
    with pytest.raises(IllegalTransition) as excinfo:
        transition(state, trigger, client_order_id=order_id, time_utc=time_at)
    assert excinfo.value.state == state
    assert excinfo.value.trigger == trigger


@pytest.mark.parametrize(
    "terminal",
    [OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED, OrderState.EXPIRED],
)
@pytest.mark.parametrize("trigger", list(Trigger))
def test_terminal_states_reject_all_triggers(
    terminal: OrderState, trigger: Trigger, order_id: UUID, time_at: datetime
) -> None:
    """Terminal states have no outgoing transitions."""
    assert is_terminal(terminal)
    with pytest.raises(IllegalTransition):
        transition(terminal, trigger, client_order_id=order_id, time_utc=time_at, reason="x")


# --- Reason / fill payload discipline ---------------------------------------


def test_reject_requires_reason(order_id: UUID, time_at: datetime) -> None:
    with pytest.raises(ValueError, match="reason required"):
        transition(
            OrderState.SUBMITTED,
            Trigger.REJECT,
            client_order_id=order_id,
            time_utc=time_at,
            reason=None,
        )


def test_cancel_requires_reason(order_id: UUID, time_at: datetime) -> None:
    with pytest.raises(ValueError, match="reason required"):
        transition(
            OrderState.ACCEPTED,
            Trigger.CANCEL,
            client_order_id=order_id,
            time_utc=time_at,
            reason=None,
        )


def test_fill_requires_payload(order_id: UUID, time_at: datetime) -> None:
    with pytest.raises(ValueError, match="fill required"):
        transition(
            OrderState.ACCEPTED,
            Trigger.FILL,
            client_order_id=order_id,
            time_utc=time_at,
            fill=None,
        )


def test_partial_fill_requires_payload(order_id: UUID, time_at: datetime) -> None:
    with pytest.raises(ValueError, match="fill required"):
        transition(
            OrderState.ACCEPTED,
            Trigger.PARTIAL_FILL,
            client_order_id=order_id,
            time_utc=time_at,
            fill=None,
        )
