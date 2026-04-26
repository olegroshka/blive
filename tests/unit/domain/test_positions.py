"""Unit tests for :func:`blive.domain.positions.apply_fill`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from blive.domain.positions import apply_fill
from blive.domain.types import Fill, Instrument, OrderSide, Position


def _fill(
    *,
    instrument: Instrument,
    side: OrderSide,
    quantity: Decimal,
    price: Decimal,
    time_utc: datetime,
    venue_exec_id: str = "exec-1",
) -> Fill:
    return Fill(
        client_order_id=uuid4(),
        venue_order_id="paper-1",
        venue_exec_id=venue_exec_id,
        instrument=instrument,
        side=side,
        quantity=quantity,
        price=price,
        commission=Decimal("0"),
        currency=instrument.currency,
        time_utc=time_utc,
    )


def test_open_from_flat(cac_pa: Instrument, frozen_now: datetime) -> None:
    fill = _fill(
        instrument=cac_pa,
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("78.42"),
        time_utc=frozen_now,
    )
    pos = apply_fill(None, fill, strategy_id="s", now=frozen_now)
    assert pos.quantity == Decimal("10")
    assert pos.avg_cost == Decimal("78.42")
    assert pos.opened_at == frozen_now


def test_open_short_from_flat(cac_pa: Instrument, frozen_now: datetime) -> None:
    fill = _fill(
        instrument=cac_pa,
        side=OrderSide.SELL,
        quantity=Decimal("5"),
        price=Decimal("78.42"),
        time_utc=frozen_now,
    )
    pos = apply_fill(None, fill, strategy_id="s", now=frozen_now)
    assert pos.quantity == Decimal("-5")
    assert pos.avg_cost == Decimal("78.42")


def test_same_side_add_weighted_avg(cac_pa: Instrument, frozen_now: datetime) -> None:
    later = frozen_now + timedelta(minutes=5)
    open_fill = _fill(
        instrument=cac_pa,
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        time_utc=frozen_now,
    )
    pos1 = apply_fill(None, open_fill, strategy_id="s", now=frozen_now)

    add_fill = _fill(
        instrument=cac_pa,
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("110"),
        time_utc=later,
        venue_exec_id="exec-2",
    )
    pos2 = apply_fill(pos1, add_fill, strategy_id="s", now=later)
    # weighted avg = (10*100 + 10*110) / 20 = 105
    assert pos2.quantity == Decimal("20")
    assert pos2.avg_cost == Decimal("105")
    # opened_at preserved from the first open
    assert pos2.opened_at == frozen_now


def test_partial_close_avg_unchanged(cac_pa: Instrument, frozen_now: datetime) -> None:
    later = frozen_now + timedelta(minutes=5)
    pos = apply_fill(
        None,
        _fill(
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            time_utc=frozen_now,
        ),
        strategy_id="s",
        now=frozen_now,
    )
    closed = apply_fill(
        pos,
        _fill(
            instrument=cac_pa,
            side=OrderSide.SELL,
            quantity=Decimal("3"),
            price=Decimal("120"),
            time_utc=later,
            venue_exec_id="exec-2",
        ),
        strategy_id="s",
        now=later,
    )
    assert closed.quantity == Decimal("7")
    assert closed.avg_cost == Decimal("100")  # unchanged on partial close


def test_full_close(cac_pa: Instrument, frozen_now: datetime) -> None:
    later = frozen_now + timedelta(minutes=5)
    pos = apply_fill(
        None,
        _fill(
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            time_utc=frozen_now,
        ),
        strategy_id="s",
        now=frozen_now,
    )
    closed = apply_fill(
        pos,
        _fill(
            instrument=cac_pa,
            side=OrderSide.SELL,
            quantity=Decimal("10"),
            price=Decimal("120"),
            time_utc=later,
            venue_exec_id="exec-2",
        ),
        strategy_id="s",
        now=later,
    )
    assert closed.quantity == Decimal("0")
    assert closed.avg_cost == Decimal("0")
    assert closed.opened_at is None


def test_flip(cac_pa: Instrument, frozen_now: datetime) -> None:
    later = frozen_now + timedelta(minutes=5)
    pos = apply_fill(
        None,
        _fill(
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            time_utc=frozen_now,
        ),
        strategy_id="s",
        now=frozen_now,
    )
    flipped = apply_fill(
        pos,
        _fill(
            instrument=cac_pa,
            side=OrderSide.SELL,
            quantity=Decimal("15"),
            price=Decimal("120"),
            time_utc=later,
            venue_exec_id="exec-2",
        ),
        strategy_id="s",
        now=later,
    )
    assert flipped.quantity == Decimal("-5")
    assert flipped.avg_cost == Decimal("120")  # new leg at flip-fill price
    assert flipped.opened_at == later
