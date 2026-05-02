"""Signal helpers that produce a ``position_series`` for the pipeline.

The M2-IB.5 paper test runs ``tkan_v4_momentum_timing`` 1× through
:func:`blive.runtime.ib_pipeline.run_ib_pipeline`, which takes a
pre-computed ``position_series: pd.Series[close_time_utc → 0|1]`` rather
than running the strategy's btest interpreter inline. This module
provides simple, deterministic stubs producing such series for end-to-end
paper testing without the real TKAN ``pred_cache.pkl`` artefact (per
operator's M2-IB.5 instruction: TKAN deferred until end-to-end paper
testing is done).

Stubs here are **not** strategies — they are signal generators useful
for exercising the full data → signal → portfolio → sizer → risk →
broker → fills → equity loop with realistic regime flips. When the real
TKAN artefact is wired (post-paper-test), the loader replaces the stub
with the production signal source; the pipeline contract stays the same.

Available stubs:

- :func:`sma_crossover_position`: long when ``close > SMA(window)``,
  flat otherwise. Warmup bars (insufficient history for SMA) → 0.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from blive.domain.types import Bar


def sma_crossover_position(
    bars: Sequence[Bar],
    *,
    sma_window: int = 50,
) -> pd.Series:
    """Return ``position_series`` indexed by each bar's ``close_time_utc``.

    Values are ``1`` when the bar's ``close`` is strictly above the
    trailing SMA of length ``sma_window`` (computed inclusive of the
    current bar — the pipeline reads ``position[t]`` after seeing
    ``bar[t]``, matching the typical "decide at close, place at next
    open" pattern for daily-frequency strategies). Values are ``0``
    during the warmup period (first ``sma_window - 1`` bars where the
    SMA is undefined) and whenever ``close <= SMA``.

    Empty ``bars`` returns an empty Series with a UTC datetime index.

    Output shape matches what
    :func:`blive.runtime.ib_pipeline.run_ib_pipeline` consumes: integer
    {0, 1} values, indexed by tz-aware UTC timestamps.
    """
    if sma_window < 2:
        raise ValueError(f"sma_window must be >= 2; got {sma_window}")

    if not bars:
        return pd.Series(
            data=pd.array([], dtype="int64"),
            index=pd.DatetimeIndex([], tz="UTC"),
            name="position",
        )

    closes = pd.Series(
        data=[float(b.close) for b in bars],
        index=pd.to_datetime([b.close_time_utc for b in bars], utc=True),
        name="close",
    )
    sma = closes.rolling(window=sma_window, min_periods=sma_window).mean()
    position = (closes > sma).astype("int64")
    # Warmup bars (sma is NaN) → already 0 due to NaN > x being False, but the
    # comparison sets them to False explicitly via the boolean cast. Ensure
    # the first sma_window-1 entries are exactly 0 for clarity.
    position.iloc[: sma_window - 1] = 0
    position.name = "position"
    return position


__all__ = ["sma_crossover_position"]
