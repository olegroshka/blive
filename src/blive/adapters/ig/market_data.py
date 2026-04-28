"""IG market-data adapter — :class:`MarketDataPort` implementation.

M2-IG.3 ships :meth:`historical_bars` over REST ``GET /prices/{epic}/...``
(rate-limited via the ``historical_prices`` bucket per
[ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)).
The streaming half — :meth:`subscribe_bars` / :meth:`subscribe_trades` —
lands in M2-IG.3-followup alongside the Lightstreamer client integration
per [ADR-036](../../../../docs/decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer);
those methods currently raise :class:`NotImplementedError`.

The historical endpoint returns OHLC as separate bid / ask prices. We
prefer ``lastTraded`` when IG includes it (real traded prices on cash
equities); otherwise we synthesise a mid from ``bid`` + ``ask``. This
matches what a strategy backtest would compare against — neutral mid
rather than directional bid/ask.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Mapping

from blive.adapters.ig.client import IGClient
from blive.adapters.ig.instrument_resolver import IGInstrumentResolver
from blive.domain.ports import ClockPort
from blive.domain.types import Bar, BarFreq, Instrument, Trade

log = logging.getLogger(__name__)


# --- BarFreq → IG resolution mapping ----------------------------------------

# IG's resolution enum (KB-16 §1 / IG Labs docs). We only map the BarFreq
# subset blive currently supports; if BarFreq widens, extend this table.
_BLIVE_FREQ_TO_IG_RESOLUTION: dict[BarFreq, str] = {
    "1m": "MINUTE",
    "5m": "MINUTE_5",
    "15m": "MINUTE_15",
    "1h": "HOUR",
    "1d": "DAY",
}

# Bar interval duration (used to compute close_time_utc from snapshotTime).
_BLIVE_FREQ_TO_TIMEDELTA: dict[BarFreq, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


def _freq_to_ig_resolution(freq: BarFreq) -> str:
    return _BLIVE_FREQ_TO_IG_RESOLUTION[freq]


def _freq_to_timedelta(freq: BarFreq) -> timedelta:
    return _BLIVE_FREQ_TO_TIMEDELTA[freq]


def _format_ig_datetime(dt: datetime) -> str:
    """IG's ``GET /prices`` URL segments expect ``yyyy-MM-dd'T'HH:mm:ss`` (UTC)."""
    if dt.tzinfo is None:
        raise ValueError("IGMarketData expects timezone-aware datetimes")
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S")


# --- The adapter ------------------------------------------------------------


class IGMarketData:
    """`MarketDataPort` adapter for IG Markets.

    Constructed via :func:`blive.adapters.ig.create_ig_market_data` (when
    the ig market-data factory lands; for now callers wire directly).
    """

    def __init__(
        self,
        *,
        client: IGClient,
        resolver: IGInstrumentResolver,
        clock: ClockPort,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._clock = clock

    # --- MarketDataPort -----------------------------------------------------

    async def subscribe_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
    ) -> AsyncIterator[Bar]:
        raise NotImplementedError(
            "IGMarketData.subscribe_bars lands in M2-IG.3 follow-up alongside "
            "the Lightstreamer client (ADR-036). M2-IG.3 ships historical_bars only."
        )

    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]:
        raise NotImplementedError(
            "IGMarketData.subscribe_trades is out of scope for v1 — Phase 1 "
            "strategies use bars only. Lightstreamer trade ticks are an M2-IG.4 "
            "concern (order events) but not a market-data deliverable."
        )

    async def unsubscribe(self, instrument: Instrument) -> None:
        # No-op while subscribe_* are not implemented. When Lightstreamer
        # lands, this releases the concurrent-subscription budget per
        # KB-17 §3.
        return None

    async def historical_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Fetch historical OHLCV bars from IG ``GET /prices/{epic}/{res}/{from}/{to}``.

        Rate-limited via the ``historical_prices`` bucket per ADR-038.
        Returns :class:`Bar` records sorted ascending by ``open_time_utc``.
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("IGMarketData.historical_bars requires UTC-aware start / end")
        if start >= end:
            raise ValueError(
                f"IGMarketData.historical_bars: start ({start}) must be < end ({end})"
            )

        epic = await self._resolver.resolve(instrument)
        resolution = _freq_to_ig_resolution(freq)
        bar_duration = _freq_to_timedelta(freq)
        path = (
            f"/prices/{epic}/{resolution}"
            f"/{_format_ig_datetime(start)}/{_format_ig_datetime(end)}"
        )

        body = await self._client.get(path, version=3, bucket="historical_prices")
        if not isinstance(body, dict):
            return []
        raw_prices = body.get("prices", [])
        if not isinstance(raw_prices, list):
            return []

        out: list[Bar] = []
        for entry in raw_prices:
            if not isinstance(entry, dict):
                continue
            try:
                bar = _parse_price_bar(
                    entry, instrument=instrument, bar_duration=bar_duration
                )
            except (KeyError, ValueError, TypeError) as exc:
                log.warning("IG /prices entry skipped (parse failure): %s", exc)
                continue
            out.append(bar)
        # IG returns bars in ascending order normally; sort defensively.
        out.sort(key=lambda b: b.open_time_utc)
        return out


# --- Bar parser (module-level, unit-testable) -------------------------------


def _parse_price_bar(
    entry: Mapping[str, Any],
    *,
    instrument: Instrument,
    bar_duration: timedelta,
) -> Bar:
    """Translate one IG /prices entry into a :class:`Bar`.

    IG fields used (KB-16 / IG Labs `/prices` reference):
    - ``snapshotTimeUTC`` (preferred) or ``snapshotTime`` — start of bar.
    - ``openPrice``, ``highPrice``, ``lowPrice``, ``closePrice`` — OHLC,
      each a dict with ``bid``, ``ask``, optional ``lastTraded``.
    - ``lastTradedVolume`` — bar volume.
    """
    snapshot = entry.get("snapshotTimeUTC") or entry.get("snapshotTime")
    if not isinstance(snapshot, str) or not snapshot:
        raise ValueError("IG /prices entry missing snapshotTime[UTC]")
    open_time = _parse_ig_snapshot(snapshot)
    close_time = open_time + bar_duration

    open_price = _ohlc_value(entry, "openPrice")
    high_price = _ohlc_value(entry, "highPrice")
    low_price = _ohlc_value(entry, "lowPrice")
    close_price = _ohlc_value(entry, "closePrice")

    volume_raw = entry.get("lastTradedVolume", 0)
    try:
        volume = Decimal(str(volume_raw))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"IG /prices lastTradedVolume not numeric: {volume_raw!r}") from exc
    if volume < 0:
        volume = Decimal("0")

    return Bar(
        instrument=instrument,
        open_time_utc=open_time,
        close_time_utc=close_time,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        vwap=None,  # IG's /prices doesn't return VWAP
    )


def _ohlc_value(entry: Mapping[str, Any], field: str) -> Decimal:
    """Extract a single OHLC value from an IG price entry.

    Prefers ``lastTraded`` (real trades on cash equities); falls back to
    the bid/ask midpoint (typical for indices / FX where lastTraded is
    not meaningful).
    """
    obj = entry.get(field)
    if not isinstance(obj, dict):
        raise ValueError(f"IG /prices entry missing {field!r} dict")
    last_traded = obj.get("lastTraded")
    if last_traded is not None:
        try:
            return Decimal(str(last_traded))
        except (TypeError, ValueError):
            pass  # fall through to mid
    bid = obj.get("bid")
    ask = obj.get("ask")
    if bid is None or ask is None:
        raise ValueError(f"IG /prices {field!r} missing bid / ask: {obj!r}")
    try:
        bid_d = Decimal(str(bid))
        ask_d = Decimal(str(ask))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"IG /prices {field!r} bid / ask not numeric: {obj!r}") from exc
    return (bid_d + ask_d) / Decimal("2")


def _parse_ig_snapshot(s: str) -> datetime:
    """Parse IG's snapshotTime[UTC] field. Same shape as the order-side
    timestamp helper but kept here to avoid an inter-module dependency."""
    s = s.strip()
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"unrecognised IG snapshot timestamp: {s!r}") from exc


__all__ = ["IGMarketData"]
