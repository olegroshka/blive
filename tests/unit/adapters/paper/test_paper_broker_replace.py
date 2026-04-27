"""PaperBroker.replace() in-place mutation test (M1 deliverable 12)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.paper.broker import PaperBroker
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    OrderUpdate,
    TimeInForce,
)


def _instr() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


@pytest.mark.asyncio
async def test_replace_lmt_quantity_and_price() -> None:
    clock = SimClock(start=datetime(2026, 4, 27, 15, tzinfo=timezone.utc))
    broker = PaperBroker(clock=clock, price_lookup=lambda _: Decimal("78"))
    await broker.connect()
    cid = uuid4()
    order = Order(
        client_order_id=cid,
        strategy_id="s",
        instrument=_instr(),
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("75"),
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=clock.now(),
    )
    await broker.submit(order)
    await broker.replace(
        ClientOrderId(cid),
        OrderUpdate(quantity=Decimal("12"), limit_price=Decimal("76")),
    )
    open_orders = await broker.open_orders()
    assert len(open_orders) == 1
    assert open_orders[0].quantity == Decimal("12")
    assert open_orders[0].limit_price == Decimal("76")
    assert open_orders[0].client_order_id == cid


@pytest.mark.asyncio
async def test_replace_unknown_order_idempotent() -> None:
    clock = SimClock(start=datetime(2026, 4, 27, 15, tzinfo=timezone.utc))
    broker = PaperBroker(clock=clock, price_lookup=lambda _: Decimal("78"))
    await broker.connect()
    # No order submitted: replace is a no-op (matches cancel() semantics).
    await broker.replace(ClientOrderId(uuid4()), OrderUpdate(quantity=Decimal("5")))
    assert await broker.open_orders() == []


@pytest.mark.asyncio
async def test_replace_invalid_field_raises() -> None:
    """Adding a stop_price to a LMT order should fail Order.__post_init__."""
    clock = SimClock(start=datetime(2026, 4, 27, 15, tzinfo=timezone.utc))
    broker = PaperBroker(clock=clock, price_lookup=lambda _: Decimal("78"))
    await broker.connect()
    cid = uuid4()
    order = Order(
        client_order_id=cid,
        strategy_id="s",
        instrument=_instr(),
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("75"),
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=clock.now(),
    )
    await broker.submit(order)
    with pytest.raises(ValueError):
        await broker.replace(ClientOrderId(cid), OrderUpdate(stop_price=Decimal("70")))
