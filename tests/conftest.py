"""Shared fixtures for the M0 test suite."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable
from uuid import UUID, uuid4

import pytest

from blive.domain.types import (
    AssetClass,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
)


@pytest.fixture
def frozen_now() -> datetime:
    """A canonical UTC timestamp, used wherever a time value is needed."""
    return datetime(2026, 4, 26, 13, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def cac_pa() -> Instrument:
    """The Phase 1 tradable instrument: Lyxor CAC 40 UCITS ETF (ADR-021)."""
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


@pytest.fixture
def aapl() -> Instrument:
    return Instrument(
        symbol="AAPL",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )


@pytest.fixture
def make_order(cac_pa: Instrument, frozen_now: datetime) -> Callable[..., Order]:
    """Factory for ``Order`` with sensible defaults.

    Override individual fields by keyword argument.
    """

    def _factory(
        *,
        client_order_id: UUID | None = None,
        strategy_id: str = "tkan_v4_momentum_timing_1x",
        instrument: Instrument | None = None,
        side: OrderSide = OrderSide.BUY,
        quantity: Decimal = Decimal("10"),
        order_type: OrderType = OrderType.MKT,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
        parent_id: UUID | None = None,
        tags: dict[str, str] | None = None,
        created_at: datetime | None = None,
    ) -> Order:
        return Order(
            client_order_id=client_order_id or uuid4(),
            strategy_id=strategy_id,
            instrument=instrument or cac_pa,
            side=side,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            parent_id=parent_id,
            tags=tags or {},
            created_at=created_at or frozen_now,
        )

    return _factory
