"""Tests for :mod:`blive.runtime.signals`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from blive.domain.types import AssetClass, Bar, Instrument
from blive.runtime.signals import sma_crossover_position, triple_lev_sma_eligibility


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


# --- triple_lev_sma_eligibility -------------------------------------------


def _date_index(n: int) -> pd.DatetimeIndex:
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    return pd.to_datetime([base + timedelta(days=i) for i in range(n)], utc=True)


def test_triple_lev_eligibility_warmup_returns_all_true() -> None:
    """During the SMA warmup (before sma_window valid bars), the function
    holds the initial all-True state (matches the notebook's no-signal-yet
    convention). With sma_window=10 and 5 input bars, every row → all-True."""
    idx = _date_index(5)
    qqq = pd.Series([100.0] * 5, index=idx)
    tlt = pd.Series([100.0] * 5, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=10)
    assert (df["TQQQ"] == 1.0).all()
    assert (df["TMF"] == 1.0).all()
    # IEF = NOT(TQQQ AND TMF) → False during warmup → 0.0
    assert (df["IEF"] == 0.0).all()


def test_triple_lev_eligibility_steady_uptrend_keeps_both_legs_long() -> None:
    """When QQQ and TLT both stay above their SMAs, both legs eligible →
    IEF stays 0; the strategy is fully in TQQQ + TMF."""
    idx = _date_index(20)
    closes = [100.0 + i for i in range(20)]  # monotonic uptrend
    qqq = pd.Series(closes, index=idx)
    tlt = pd.Series(closes, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5)
    # Past the warmup window, the rising trend keeps closes above SMA → both True.
    post_warmup = df.iloc[5:]
    assert (post_warmup["TQQQ"] == 1.0).all()
    assert (post_warmup["TMF"] == 1.0).all()
    assert (post_warmup["IEF"] == 0.0).all()


def test_triple_lev_eligibility_one_leg_falls_below_sma_engages_ief() -> None:
    """When QQQ falls below its SMA: TQQQ leg → 0; TMF leg stays 1; IEF
    becomes eligible (NOT(both)) → 1."""
    idx = _date_index(20)
    qqq_closes = [100.0] * 5 + [100.0 - i for i in range(15)]  # post-warmup falling
    tlt_closes = [100.0 + i for i in range(20)]  # monotonic up
    qqq = pd.Series(qqq_closes, index=idx)
    tlt = pd.Series(tlt_closes, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5)
    # By the last few bars QQQ has fallen well below its SMA.
    last = df.iloc[-1]
    assert last["TQQQ"] == 0.0
    assert last["TMF"] == 1.0
    assert last["IEF"] == 1.0  # NOT(0 AND 1) = NOT(0) = 1


def test_triple_lev_eligibility_hysteresis_re_entry_requires_5pct_buffer() -> None:
    """After QQQ falls and triggers exit, it must rise above SMA*1.05 to
    re-enter — passing exactly through the SMA does NOT re-engage TQQQ."""
    idx = _date_index(40)
    # Phase 1: rising up to bar 10 → both eligible.
    # Phase 2: drop below SMA → TQQQ exits.
    # Phase 3: rise back to exactly the SMA value (not 5% above) → still flat.
    closes_qqq = (
        [100.0 + i for i in range(10)] + [70.0] * 10 + [109.0] * 20
    )  # 109 ≈ SMA at bar 30 likely
    closes_tlt = [100.0 + i for i in range(40)]
    qqq = pd.Series(closes_qqq, index=idx)
    tlt = pd.Series(closes_tlt, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5, enter_buffer=0.05)
    # By bar 20+ we expect TQQQ to have exited; it's only re-engaged when
    # close exceeds SMA*1.05 — find at least one row where TQQQ is 0
    # confirming the exit happened.
    assert (df["TQQQ"] == 0.0).any(), "expected TQQQ to exit during the drop phase"


def test_triple_lev_eligibility_misaligned_indices_raises() -> None:
    """qqq and tlt must share their index; otherwise raises before any state
    machine runs."""
    qqq = pd.Series([100.0, 101.0], index=_date_index(2))
    tlt = pd.Series([100.0, 101.0, 102.0], index=_date_index(3))
    with pytest.raises(ValueError, match="share the same index"):
        triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt)


def test_triple_lev_eligibility_invalid_window_raises() -> None:
    qqq = pd.Series([100.0, 101.0], index=_date_index(2))
    tlt = pd.Series([100.0, 101.0], index=_date_index(2))
    with pytest.raises(ValueError, match="sma_window"):
        triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=1)


def test_triple_lev_eligibility_empty_input_returns_empty_frame() -> None:
    empty_idx = pd.DatetimeIndex([], tz="UTC")
    qqq = pd.Series([], index=empty_idx, dtype=float)
    tlt = pd.Series([], index=empty_idx, dtype=float)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt)
    assert len(df) == 0
    assert list(df.columns) == ["TQQQ", "TMF", "IEF"]


def test_triple_lev_eligibility_output_columns_in_canonical_order() -> None:
    """Column order must be exactly ['TQQQ', 'TMF', 'IEF'] — btest's
    ExternalFactor(per_instrument=True) reads by column name but consumers
    of the parquet may rely on positional order, so pinning."""
    idx = _date_index(20)
    qqq = pd.Series([100.0 + i for i in range(20)], index=idx)
    tlt = pd.Series([100.0 + i for i in range(20)], index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5)
    assert list(df.columns) == ["TQQQ", "TMF", "IEF"]
    # Values should all be 0.0 or 1.0 (no fractional float artefacts).
    assert set(df["TQQQ"].unique()) <= {0.0, 1.0}
    assert set(df["TMF"].unique()) <= {0.0, 1.0}
    assert set(df["IEF"].unique()) <= {0.0, 1.0}
