"""End-to-end PaperBroker round-trip — the load-bearing G1 exit-criterion test.

A market order is submitted; the broker emits SUBMITTED → ACCEPTED → FILLED;
the test drives the FSM at each event and folds the resulting Fill into a
Position. Final state must be FILLED with a Position matching the order.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable

import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.paper.broker import PaperBroker
from blive.domain.events import ConnectionStatus, OrderEvent
from blive.domain.order_fsm import Trigger, transition
from blive.domain.positions import apply_fill
from blive.domain.types import (
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderState,
    OrderType,
    OrderUpdate,
    Position,
    TimeInForce,
)

# --- Round-trip (G1 exit criterion) -----------------------------------------


async def test_round_trip_mkt_order_drives_fsm_and_position(
    make_order: Callable[..., Order],
    cac_pa: Instrument,
) -> None:
    clock = SimClock()
    broker = PaperBroker(clock, lambda _i: Decimal("78.42"))
    await broker.connect()

    order = make_order(side=OrderSide.BUY, quantity=Decimal("10"), order_type=OrderType.MKT)
    returned_id = await broker.submit(order)
    assert returned_id == order.client_order_id

    # The engine simulator: drive the FSM as broker events arrive,
    # fold fills into a Position.
    state = OrderState.INITIALIZED
    state, _ = transition(
        state, Trigger.SUBMIT_CALL, client_order_id=order.client_order_id, time_utc=clock.now()
    )
    assert state == OrderState.SUBMIT_PENDING

    position: Position | None = None
    received_kinds: list[OrderEventKind] = []

    async for event in broker.events():
        if isinstance(event, ConnectionStatus):
            continue
        assert isinstance(event, OrderEvent)
        received_kinds.append(event.kind)

        if event.kind == OrderEventKind.SUBMITTED:
            state, ev = transition(
                state,
                Trigger.WIRE_ACK,
                client_order_id=order.client_order_id,
                time_utc=event.time_utc,
                venue_order_id=event.venue_order_id,
            )
            assert state == OrderState.SUBMITTED
            assert ev is not None and ev.venue_order_id == event.venue_order_id
        elif event.kind == OrderEventKind.ACCEPTED:
            state, ev = transition(
                state,
                Trigger.ACCEPT,
                client_order_id=order.client_order_id,
                time_utc=event.time_utc,
            )
            assert state == OrderState.ACCEPTED
        elif event.kind == OrderEventKind.FILLED:
            assert event.fill is not None
            state, ev = transition(
                state,
                Trigger.FILL,
                client_order_id=order.client_order_id,
                time_utc=event.time_utc,
                fill=event.fill,
            )
            assert state == OrderState.FILLED
            position = apply_fill(
                position, event.fill, strategy_id=order.strategy_id, now=clock.now()
            )
            break
        else:
            pytest.fail(f"unexpected event kind: {event.kind}")

    assert received_kinds == [
        OrderEventKind.SUBMITTED,
        OrderEventKind.ACCEPTED,
        OrderEventKind.FILLED,
    ]
    assert state == OrderState.FILLED
    assert position is not None
    assert position.quantity == Decimal("10")
    assert position.avg_cost == Decimal("78.42")
    assert position.instrument == cac_pa
    assert position.strategy_id == order.strategy_id

    # Open orders book is empty after the fill.
    assert await broker.open_orders() == []


# --- Cancel a resting LMT order ---------------------------------------------


async def test_cancel_lmt_order_emits_canceled_event(
    make_order: Callable[..., Order],
) -> None:
    clock = SimClock()
    broker = PaperBroker(clock, lambda _i: Decimal("78.42"))
    await broker.connect()

    order = make_order(
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("80.00"),
    )
    await broker.submit(order)

    received_kinds: list[OrderEventKind] = []
    async for event in broker.events():
        if isinstance(event, ConnectionStatus):
            continue
        assert isinstance(event, OrderEvent)
        received_kinds.append(event.kind)

        if event.kind == OrderEventKind.ACCEPTED:
            # LMT held in the book → cancel now.
            await broker.cancel(order.client_order_id)
        if event.kind == OrderEventKind.CANCELED:
            break

    assert received_kinds == [
        OrderEventKind.SUBMITTED,
        OrderEventKind.ACCEPTED,
        OrderEventKind.CANCELED,
    ]
    assert await broker.open_orders() == []


# --- Idempotent submit (REQUIREMENTS §5.3) ----------------------------------


async def test_submit_is_idempotent_on_same_client_order_id(
    make_order: Callable[..., Order],
) -> None:
    clock = SimClock()
    broker = PaperBroker(clock, lambda _i: Decimal("78.42"))
    await broker.connect()

    order = make_order(order_type=OrderType.LMT, limit_price=Decimal("80.00"))
    cid1 = await broker.submit(order)
    cid2 = await broker.submit(order)
    assert cid1 == cid2
    assert len(await broker.open_orders()) == 1


# --- Replace landed at M1; richer cases live in test_paper_broker_replace.py


# --- Account snapshot stub --------------------------------------------------


async def test_account_snapshot_returns_starting_cash() -> None:
    clock = SimClock()
    broker = PaperBroker(clock, lambda _i: Decimal("100"), starting_cash=Decimal("250000"))
    await broker.connect()
    snap = await broker.account_snapshot()
    assert snap.equity == Decimal("250000")
    assert snap.cash_by_ccy["USD"] == Decimal("250000")


# --- Submit before connect should fail loud ---------------------------------


async def test_submit_before_connect_raises(make_order: Callable[..., Order]) -> None:
    clock = SimClock()
    broker = PaperBroker(clock, lambda _i: Decimal("100"))
    with pytest.raises(RuntimeError, match="connect"):
        await broker.submit(make_order())
