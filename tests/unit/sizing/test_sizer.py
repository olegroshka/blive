"""Sizer tests — ADR-027 rounding policy and the exit-flatten invariant."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from blive.domain.types import (
    AssetClass,
    Instrument,
    OrderSide,
    OrderType,
    Position,
    TimeInForce,
)
from blive.sizing import SizerInput, quantize_share_qty, size_orders


def _instr() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


def _now() -> datetime:
    return datetime(2026, 4, 27, 15, 30, tzinfo=timezone.utc)


def test_quantize_truncates_toward_zero() -> None:
    assert quantize_share_qty(Decimal("1.7")) == Decimal("1")
    assert quantize_share_qty(Decimal("0.99")) == Decimal("0")
    assert quantize_share_qty(Decimal("-1.7")) == Decimal("-1")
    assert quantize_share_qty(Decimal("-0.99")) == Decimal("0")
    assert quantize_share_qty(Decimal("0")) == Decimal("0")


def test_size_orders_basic_buy() -> None:
    inst = _instr()
    orders = size_orders(
        SizerInput(
            target_weights={"CAC.PA": Decimal("1.0")},
            equity=Decimal("100000"),
            nav_slice=Decimal("0.05"),  # effective_capital = 5000
            current_positions={},
            instrument_resolver=lambda _: inst,
            price_lookup=lambda _: Decimal("78"),  # desired_qty = 5000/78 = 64.10... → 64
            strategy_id="s",
            now=_now(),
        )
    )
    assert len(orders) == 1
    o = orders[0]
    assert o.side == OrderSide.BUY
    assert o.quantity == Decimal("64")
    assert o.order_type == OrderType.MKT
    assert o.time_in_force == TimeInForce.DAY


def test_size_orders_no_op_when_already_at_target() -> None:
    inst = _instr()
    pos = Position(
        instrument=inst,
        strategy_id="s",
        quantity=Decimal("64"),
        avg_cost=Decimal("78"),
        currency="EUR",
        opened_at=_now(),
        updated_at=_now(),
    )
    orders = size_orders(
        SizerInput(
            target_weights={"CAC.PA": Decimal("1.0")},
            equity=Decimal("100000"),
            nav_slice=Decimal("0.05"),
            current_positions={"CAC.PA": pos},
            instrument_resolver=lambda _: inst,
            price_lookup=lambda _: Decimal("78"),
            strategy_id="s",
            now=_now(),
        )
    )
    # Desired 5000/78 ≈ 64.10 → 64; already hold 64 → delta 0 → no order.
    assert orders == []


def test_size_orders_exit_flatten_full_close() -> None:
    """ADR-027 invariant: target_weight=0 forces exact close, not rounded delta."""
    inst = _instr()
    pos = Position(
        instrument=inst,
        strategy_id="s",
        quantity=Decimal("64"),
        avg_cost=Decimal("78"),
        currency="EUR",
        opened_at=_now(),
        updated_at=_now(),
    )
    orders = size_orders(
        SizerInput(
            target_weights={"CAC.PA": Decimal("0")},
            equity=Decimal("100000"),
            nav_slice=Decimal("0.05"),
            current_positions={"CAC.PA": pos},
            instrument_resolver=lambda _: inst,
            price_lookup=lambda _: Decimal("78"),
            strategy_id="s",
            now=_now(),
        )
    )
    assert len(orders) == 1
    assert orders[0].side == OrderSide.SELL
    assert orders[0].quantity == Decimal("64")  # exact full close, no leftover


def test_size_orders_short_side_when_negative_weight() -> None:
    inst = _instr()
    orders = size_orders(
        SizerInput(
            target_weights={"CAC.PA": Decimal("-1")},
            equity=Decimal("100000"),
            nav_slice=Decimal("0.05"),
            current_positions={},
            instrument_resolver=lambda _: inst,
            price_lookup=lambda _: Decimal("78"),
            strategy_id="s",
            now=_now(),
        )
    )
    assert len(orders) == 1
    assert orders[0].side == OrderSide.SELL
    assert orders[0].quantity == Decimal("64")


def test_size_orders_invalid_weight_rejected() -> None:
    inst = _instr()
    with pytest.raises(ValueError, match=r"\[-1, 1\]"):
        size_orders(
            SizerInput(
                target_weights={"CAC.PA": Decimal("1.5")},
                equity=Decimal("100000"),
                nav_slice=Decimal("0.05"),
                current_positions={},
                instrument_resolver=lambda _: inst,
                price_lookup=lambda _: Decimal("78"),
                strategy_id="s",
                now=_now(),
            )
        )


def test_size_orders_zero_equity_rejected() -> None:
    inst = _instr()
    with pytest.raises(ValueError, match="equity must be > 0"):
        size_orders(
            SizerInput(
                target_weights={"CAC.PA": Decimal("1")},
                equity=Decimal("0"),
                nav_slice=Decimal("0.05"),
                current_positions={},
                instrument_resolver=lambda _: inst,
                price_lookup=lambda _: Decimal("78"),
                strategy_id="s",
                now=_now(),
            )
        )


def test_size_orders_subshare_delta_no_order() -> None:
    inst = _instr()
    # effective_capital = 100 * 0.005 = 0.5; desired_qty = 0.5/78 ≈ 0.0064 → 0
    orders = size_orders(
        SizerInput(
            target_weights={"CAC.PA": Decimal("1")},
            equity=Decimal("100"),
            nav_slice=Decimal("0.005"),
            current_positions={},
            instrument_resolver=lambda _: inst,
            price_lookup=lambda _: Decimal("78"),
            strategy_id="s",
            now=_now(),
        )
    )
    assert orders == []
