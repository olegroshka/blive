"""Fixture-backed :class:`MarketDataPort` adapter.

Per :doc:`../../../../docs/decisions/DECISIONS.md` (ADR-029): bars come from
a parquet file with columns
``(open_time_utc, close_time_utc, open, high, low, close, volume)`` and an
optional ``vwap``. Used by the M1 paper-mode pipeline and as the foundation
for the M7 continuous-parity replica.

The adapter has two replay modes:

- **Tape replay** (default; M1 paper pipeline): bars yield as fast as the
  consumer can pull. Time advances at the bar's own ``close_time_utc``.
- **Real-time-paced** (M7 continuous-parity replica; M1 stub): bars yield
  in lockstep with ``ClockPort``; not exercised in M1.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import AsyncIterator, Mapping, cast

import pandas as pd

from blive.domain.types import AssetClass, Bar, BarFreq, Instrument, Trade


class PaperMarketData:
    """In-process :class:`MarketDataPort` over a parquet fixture per ADR-029."""

    def __init__(
        self,
        fixtures: Mapping[Instrument, Path],
        *,
        freq: BarFreq = "1d",
    ) -> None:
        self._freq = freq
        self._frames: dict[Instrument, pd.DataFrame] = {
            instrument: _read_fixture(path) for instrument, path in fixtures.items()
        }

    # --- MarketDataPort ----------------------------------------------------

    async def subscribe_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
    ) -> AsyncIterator[Bar]:
        if freq != self._freq:
            raise ValueError(
                f"PaperMarketData configured at freq={self._freq!r}; " f"caller requested {freq!r}"
            )
        if instrument not in self._frames:
            raise KeyError(f"no fixture loaded for {instrument}")

        async def _gen() -> AsyncIterator[Bar]:
            for row in self._iter_bars(instrument):
                yield row

        return _gen()

    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]:
        raise NotImplementedError(
            "PaperMarketData.subscribe_trades is out of v1 scope (ADR-029); "
            "Phase 1 daily strategies do not subscribe to trades."
        )

    async def unsubscribe(self, instrument: Instrument) -> None:
        # Stateless tape-replay; nothing to unsubscribe from.
        return None

    async def historical_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        if freq != self._freq:
            raise ValueError(
                f"PaperMarketData configured at freq={self._freq!r}; " f"caller requested {freq!r}"
            )
        if instrument not in self._frames:
            raise KeyError(f"no fixture loaded for {instrument}")
        return [
            bar
            for bar in self._iter_bars(instrument)
            if start <= bar.open_time_utc and bar.close_time_utc <= end
        ]

    # --- Convenience helpers --------------------------------------------------

    def latest(self, instrument: Instrument, *, on_or_before: datetime) -> Bar | None:
        """Return the latest fixture bar with ``close_time_utc <= on_or_before``.

        Convenience for the M1 pipeline driver and RC-08 stale-data check.
        """
        latest: Bar | None = None
        for bar in self._iter_bars(instrument):
            if bar.close_time_utc <= on_or_before:
                latest = bar
            else:
                break
        return latest

    def bars(self, instrument: Instrument) -> list[Bar]:
        return list(self._iter_bars(instrument))

    # --- Internals ----------------------------------------------------------

    def _iter_bars(self, instrument: Instrument) -> list[Bar]:
        df = self._frames[instrument]
        has_vwap = "vwap" in df.columns
        out: list[Bar] = []
        for record in df.to_dict(orient="records"):
            open_t = cast(pd.Timestamp, record["open_time_utc"]).to_pydatetime()
            close_t = cast(pd.Timestamp, record["close_time_utc"]).to_pydatetime()
            vwap_val: Decimal | None = None
            if has_vwap:
                raw_vwap = record.get("vwap")
                if raw_vwap is not None and pd.notna(raw_vwap):
                    vwap_val = Decimal(str(raw_vwap))
            out.append(
                Bar(
                    instrument=instrument,
                    open_time_utc=open_t,
                    close_time_utc=close_t,
                    open=Decimal(str(record["open"])),
                    high=Decimal(str(record["high"])),
                    low=Decimal(str(record["low"])),
                    close=Decimal(str(record["close"])),
                    volume=Decimal(str(record["volume"])),
                    vwap=vwap_val,
                )
            )
        return out


def _read_fixture(path: Path) -> pd.DataFrame:
    """Load and validate a fixture parquet for a single instrument.

    Required columns: ``open_time_utc``, ``close_time_utc``, ``open``, ``high``,
    ``low``, ``close``, ``volume``. Optional: ``vwap``.
    """
    df = pd.read_parquet(path)
    required = {"open_time_utc", "close_time_utc", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"PaperMarketData fixture at {path} is missing required columns: {sorted(missing)}"
        )
    df = df.sort_values("open_time_utc").reset_index(drop=True)
    df["open_time_utc"] = pd.to_datetime(df["open_time_utc"], utc=True)
    df["close_time_utc"] = pd.to_datetime(df["close_time_utc"], utc=True)
    return df


def make_default_cac_pa() -> Instrument:
    """Convenience constructor for the Phase 1 instrument (ADR-021)."""
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


__all__ = ["PaperMarketData", "make_default_cac_pa"]
