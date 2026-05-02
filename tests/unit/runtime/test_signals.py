"""Tests for :mod:`blive.runtime.signals`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from blive.domain.types import AssetClass, Bar, Instrument
from blive.runtime.signals import sma_crossover_position


def _instrument() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )


def _make_bars(closes: list[float]) -> list[Bar]:
    inst = _instrument()
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    bars: list[Bar] = []
    for i, c in enumerate(closes):
        t = base + timedelta(days=i)
        bars.append(
            Bar(
                instrument=inst,
                open_time_utc=t - timedelta(hours=8),
                close_time_utc=t,
                open=Decimal(str(c)),
                high=Decimal(str(c + 0.5)),
                low=Decimal(str(c - 0.5)),
                close=Decimal(str(c)),
                volume=Decimal("1000"),
                vwap=None,
            )
        )
    return bars


def test_empty_bars_returns_empty_series() -> None:
    out = sma_crossover_position([], sma_window=10)
    assert len(out) == 0
    assert isinstance(out.index, pd.DatetimeIndex)
    assert out.index.tz is not None  # UTC


def test_warmup_window_is_flat() -> None:
    """First sma_window - 1 entries are 0 regardless of price action."""
    closes = [100.0] * 5 + [200.0] * 5  # second half spikes; SMA still warming
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # First 4 bars have insufficient history for SMA(5) → must be 0.
    assert (out.iloc[:4] == 0).all(), "warmup bars should be flat"


def test_long_when_close_above_sma() -> None:
    """A clean uptrend: every bar's close is above its trailing SMA."""
    closes = [100.0 + i for i in range(20)]  # strictly rising
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # Bars 4 onward have full SMA window AND close > sma (rising trend).
    assert (out.iloc[4:] == 1).all(), "rising trend should be fully long after warmup"


def test_flat_when_close_below_sma() -> None:
    """A clean downtrend: every bar's close is below its trailing SMA."""
    closes = [200.0 - i for i in range(20)]  # strictly falling
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # Bars 4 onward have full SMA window AND close < sma (falling).
    assert (out.iloc[4:] == 0).all(), "falling trend should be fully flat after warmup"


def test_regime_flip_at_sma_crossing() -> None:
    """Rising then falling: position should flip from 1 to 0 around the
    crossover."""
    # 5 days flat at 100, then 10 days rising to 110, then 10 days falling to 90.
    closes = [100.0] * 5 + [100.0 + i for i in range(1, 11)] + [110.0 - i for i in range(1, 11)]
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # Sanity: at least one flip from 1→0 in the falling segment.
    flips = ((out.shift() == 1) & (out == 0)).sum()
    assert flips >= 1, "expected at least one long→flat flip on the downtrend"


def test_index_matches_close_time_utc() -> None:
    """Output index aligns with bars' close_time_utc — what run_ib_pipeline
    consumes via ``position_series.loc[ts_key]``."""
    closes = [100.0 + i for i in range(10)]
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=3)
    expected_index = pd.to_datetime([b.close_time_utc for b in bars], utc=True)
    assert (out.index == expected_index).all()


def test_invalid_window_raises() -> None:
    bars = _make_bars([100.0, 101.0, 102.0])
    with pytest.raises(ValueError, match="sma_window"):
        sma_crossover_position(bars, sma_window=1)
    with pytest.raises(ValueError, match="sma_window"):
        sma_crossover_position(bars, sma_window=0)
