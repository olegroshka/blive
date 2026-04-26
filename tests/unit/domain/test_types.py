"""Invariants on the DD-1 dataclasses."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from blive.domain.types import (
    AccountSnapshot,
    AssetClass,
    Bar,
    Fill,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    OrderUpdate,
    Position,
    TimeInForce,
)

# --- Instrument --------------------------------------------------------------


def test_instrument_rejects_lowercase_currency() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        Instrument(
            symbol="AAPL",
            venue="XNAS",
            currency="usd",
            asset_class=AssetClass.EQUITY,
            multiplier=Decimal("1"),
        )


def test_instrument_rejects_whitespace_symbol() -> None:
    with pytest.raises(ValueError, match="symbol"):
        Instrument(
            symbol=" AAPL",
            venue="XNAS",
            currency="USD",
            asset_class=AssetClass.EQUITY,
            multiplier=Decimal("1"),
        )


def test_instrument_rejects_zero_multiplier() -> None:
    with pytest.raises(ValueError, match="multiplier"):
        Instrument(
            symbol="AAPL",
            venue="XNAS",
            currency="USD",
            asset_class=AssetClass.EQUITY,
            multiplier=Decimal("0"),
        )


# --- Order -------------------------------------------------------------------


def test_lmt_order_requires_limit_price(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="limit_price"):
        Order(
            client_order_id=uuid4(),
            strategy_id="s",
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            order_type=OrderType.LMT,
            time_in_force=TimeInForce.DAY,
            limit_price=None,
            stop_price=None,
            parent_id=None,
            tags={},
            created_at=frozen_now,
        )


def test_mkt_order_rejects_limit_price(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="limit_price"):
        Order(
            client_order_id=uuid4(),
            strategy_id="s",
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            order_type=OrderType.MKT,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("78.42"),
            stop_price=None,
            parent_id=None,
            tags={},
            created_at=frozen_now,
        )


def test_stp_order_requires_stop_price(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="stop_price"):
        Order(
            client_order_id=uuid4(),
            strategy_id="s",
            instrument=cac_pa,
            side=OrderSide.SELL,
            quantity=Decimal("10"),
            order_type=OrderType.STP,
            time_in_force=TimeInForce.DAY,
            limit_price=None,
            stop_price=None,
            parent_id=None,
            tags={},
            created_at=frozen_now,
        )


def test_order_rejects_zero_quantity(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="quantity"):
        Order(
            client_order_id=uuid4(),
            strategy_id="s",
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("0"),
            order_type=OrderType.MKT,
            time_in_force=TimeInForce.DAY,
            limit_price=None,
            stop_price=None,
            parent_id=None,
            tags={},
            created_at=frozen_now,
        )


def test_order_rejects_naive_datetime(cac_pa: Instrument) -> None:
    with pytest.raises(ValueError, match="UTC"):
        Order(
            client_order_id=uuid4(),
            strategy_id="s",
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MKT,
            time_in_force=TimeInForce.DAY,
            limit_price=None,
            stop_price=None,
            parent_id=None,
            tags={},
            created_at=datetime(2026, 4, 26, 12, 0),  # naive
        )


# --- Bar ---------------------------------------------------------------------


def test_bar_ohlc_invariant(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="OHLC"):
        Bar(
            instrument=cac_pa,
            open_time_utc=frozen_now,
            close_time_utc=datetime(2026, 4, 26, 13, 31, tzinfo=timezone.utc),
            open=Decimal("78.5"),
            high=Decimal("78.4"),  # high < open
            low=Decimal("78.0"),
            close=Decimal("78.3"),
            volume=Decimal("1000"),
        )


def test_bar_vwap_in_range(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="vwap"):
        Bar(
            instrument=cac_pa,
            open_time_utc=frozen_now,
            close_time_utc=datetime(2026, 4, 26, 13, 31, tzinfo=timezone.utc),
            open=Decimal("78.5"),
            high=Decimal("78.6"),
            low=Decimal("78.4"),
            close=Decimal("78.5"),
            volume=Decimal("1000"),
            vwap=Decimal("80.0"),  # outside [low, high]
        )


# --- Fill --------------------------------------------------------------------


def test_fill_requires_venue_exec_id(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="venue_exec_id"):
        Fill(
            client_order_id=uuid4(),
            venue_order_id="paper-1",
            venue_exec_id="",
            instrument=cac_pa,
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("78.42"),
            commission=Decimal("0.05"),
            currency="EUR",
            time_utc=frozen_now,
        )


# --- Position ----------------------------------------------------------------


def test_position_currency_must_match_instrument(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="currency"):
        Position(
            instrument=cac_pa,
            strategy_id="s",
            quantity=Decimal("10"),
            avg_cost=Decimal("78.42"),
            currency="USD",  # mismatch with cac_pa.currency = EUR
            opened_at=frozen_now,
            updated_at=frozen_now,
        )


def test_zero_position_must_have_no_opened_at(cac_pa: Instrument, frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="opened_at"):
        Position(
            instrument=cac_pa,
            strategy_id="s",
            quantity=Decimal("0"),
            avg_cost=Decimal("0"),
            currency="EUR",
            opened_at=frozen_now,  # should be None when qty == 0
            updated_at=frozen_now,
        )


# --- AccountSnapshot ---------------------------------------------------------


def test_account_snapshot_rejects_negative_buying_power(frozen_now: datetime) -> None:
    with pytest.raises(ValueError, match="buying_power"):
        AccountSnapshot(
            equity=Decimal("100"),
            cash_by_ccy={"USD": Decimal("100")},
            buying_power=Decimal("-1"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            leverage=Decimal("0"),
            margin_used=Decimal("0"),
            base_currency="USD",
            taken_at=frozen_now,
        )


# --- OrderUpdate -------------------------------------------------------------


def test_order_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValueError, match="at least one"):
        OrderUpdate()
