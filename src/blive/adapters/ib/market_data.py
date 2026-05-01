"""IB market-data adapter — :class:`MarketDataPort` implementation.

M2-IB.3b-ii ships ``historical_bars`` against ``ib_async.IB.reqHistoricalDataAsync``.
``subscribe_bars`` / ``subscribe_trades`` raise :class:`NotImplementedError`
for v1 — the Phase 1 strategy ([ADR-021](../../../../docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf))
runs at daily frequency where streaming bars don't add value over an
end-of-day ``historical_bars`` poll. The polling-based subscribe_bars
shape lands at M2-IB.5 pipeline integration time when the deferred
``ib_pipeline.py`` needs it.

What this module exercises:

- [KB-3 §2](../../../../docs/kb/ib_pacing_spec.md#2-historical-data-pacing) —
  ≤ 60 ``reqHistoricalData`` per 10-minute window; ``BID_ASK`` whatToShow
  doubles the cost. Both enforced via :data:`blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS`'
  ``historical`` bucket (50/600s, with extra-token logic for BID_ASK).
- [DD-7 §3](../../../../docs/dd/instrument_dictionary.md#3-venue-mic-ib-exchange) —
  the resolved Contract is fed to ``reqHistoricalDataAsync``; symbol
  translation (Yahoo-suffix stripping per ADR-041) applies.
- [INV-6 §1.2](../../../../docs/inv/ports_adapters.md#12-marketdataport) —
  the ``MarketDataPort.historical_bars`` shape is broker-neutral; the
  IB-specific bar parsing lives here.

What is NOT here:

- ``subscribe_bars`` — a polling-over-historical implementation lands
  alongside the M2-IB.5 ``ib_pipeline`` (or as a refactor of
  ``paper_pipeline.py`` to be broker-agnostic via the broker registry).
- ``subscribe_trades`` — Phase 1 daily strategy doesn't need trade-level
  data; defer.
- ``unsubscribe`` — no-op for v1 (matches :class:`blive.adapters.paper.market_data.PaperMarketData`'s
  shape since there is no active subscription to cancel).

Per [REQUIREMENTS §5.2](../../../../REQUIREMENTS.md#52-live-market-data) the
day-1 capability is "bar streams (1-minute, 5-minute, 1-day) and trade
ticks". Phase 1's daily-frequency strategy makes the ``1-day`` slot
load-bearing; the others are Phase 2+ work.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncIterator

import ib_async

from blive.adapters.ib.client import IBClient
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.domain.ports import ClockPort
from blive.domain.types import Bar, BarFreq, Instrument, Trade

log = logging.getLogger(__name__)


# --- BarFreq → IB barSizeSetting mapping (KB-2 §3 / IB TWS API) -------------
#
# IB accepts a fixed set of bar-size strings. blive's BarFreq is a small
# Literal subset; the ones we don't support raise. blive's "1d" maps to
# "1 day" (lowercase day; IB is fussy).
_BAR_FREQ_TO_IB_BAR_SIZE: dict[BarFreq, str] = {
    "1m": "1 min",
    "5m": "5 mins",
    "15m": "15 mins",
    "1h": "1 hour",
    "1d": "1 day",
}


# --- whatToShow defaults ------------------------------------------------------
#
# For STK / ETF / IND the default is "TRADES" (last-traded prices). For
# FX (CASH) the default is "MIDPOINT" since FX has no consolidated
# trade tape. For "BID_ASK" callers must pay the double-token cost per
# KB-3 §2 — opt-in only, not the default.
_DEFAULT_WHAT_TO_SHOW = "TRADES"
_BID_ASK_WHAT_TO_SHOW = "BID_ASK"


class IBMarketDataError(Exception):
    """Raised when historical data request can't be parsed or fails at the
    adapter boundary. Wraps the underlying ``ib_async``-side error in
    ``__cause__`` for diagnostics."""


class IBMarketData:
    """IB-side :class:`MarketDataPort` implementation.

    Wraps a single :class:`IBClient` (TCP handshake + rate limiter) plus
    an :class:`IBInstrumentResolver` (Instrument↔Contract). Each
    :meth:`historical_bars` call consumes from the rate limiter's
    ``historical`` bucket per [KB-3 §2 / §9](../../../../docs/kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults).
    """

    def __init__(
        self,
        *,
        client: IBClient,
        resolver: IBInstrumentResolver,
        clock: ClockPort,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._clock = clock

    # --- MarketDataPort: historical -----------------------------------------

    async def historical_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
        start: datetime,
        end: datetime,
        *,
        what_to_show: str = _DEFAULT_WHAT_TO_SHOW,
        use_rth: bool = True,
    ) -> list[Bar]:
        """Fetch historical bars for ``instrument`` between ``start`` and ``end``.

        Implementation detail: ib_async's ``reqHistoricalDataAsync`` takes
        ``(endDateTime, durationStr, barSizeSetting)`` rather than
        ``(start, end)``. We compute the duration string from the
        timestamps. Bars are returned in chronological order; the
        adapter filters to ``[start, end]`` since IB sometimes returns
        earlier bars within the requested duration window.

        Raises :class:`IBMarketDataError` on parse / wire errors; the
        underlying ``ib_async`` exception is preserved as ``__cause__``.

        Rate-limit: consumes one ``historical`` token (or two for
        ``what_to_show=BID_ASK`` per [KB-3 §2](../../../../docs/kb/ib_pacing_spec.md#2-historical-data-pacing)).
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError(
                "historical_bars requires tz-aware start / end (UTC). "
                f"Got start.tzinfo={start.tzinfo}, end.tzinfo={end.tzinfo}."
            )
        if start > end:
            raise ValueError(f"historical_bars start ({start}) must be <= end ({end})")

        bar_size = _BAR_FREQ_TO_IB_BAR_SIZE.get(freq)
        if bar_size is None:
            raise ValueError(
                f"Unsupported BarFreq for IB historical: {freq!r}. "
                f"Supported: {list(_BAR_FREQ_TO_IB_BAR_SIZE)}"
            )

        contract = self._resolver.to_contract(instrument)
        duration_str = _duration_str_for_range(start, end, freq)

        # KB-3 §2: BID_ASK whatToShow counts double; acquire 2 tokens.
        tokens = 2 if what_to_show == _BID_ASK_WHAT_TO_SHOW else 1
        await self._client.rate_limiter.acquire("historical", tokens=tokens)

        try:
            ib_bars = await self._client.ib.reqHistoricalDataAsync(
                contract,
                endDateTime=end,
                durationStr=duration_str,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=use_rth,
                formatDate=2,  # 2 = UTC seconds since epoch (vs locale)
            )
        except Exception as exc:  # noqa: BLE001 — translate to typed exception
            raise IBMarketDataError(
                f"reqHistoricalDataAsync failed for {instrument!r} "
                f"freq={freq} duration={duration_str!r}: {exc}"
            ) from exc

        out: list[Bar] = []
        for ib_bar in ib_bars:
            try:
                bar = _parse_ib_bar(ib_bar=ib_bar, instrument=instrument, freq=freq)
            except (ValueError, TypeError, AttributeError) as exc:
                log.warning(
                    "IB historical bar skipped (parse failure) for %s %s: %s",
                    instrument.symbol,
                    freq,
                    exc,
                )
                continue
            # Filter to caller-requested window — IB sometimes returns
            # earlier bars when the duration is wider than the gap.
            if bar.close_time_utc < start or bar.open_time_utc >= end:
                continue
            out.append(bar)
        # IB returns bars chronologically; preserve ordering after the filter.
        out.sort(key=lambda b: b.open_time_utc)
        return out

    # --- MarketDataPort: streaming (M2-IB.5 / Phase 2 work) -----------------

    async def subscribe_bars(self, instrument: Instrument, freq: BarFreq) -> AsyncIterator[Bar]:
        """Streaming bar subscription.

        Not implemented at M2-IB.3b-ii. Phase 1's daily strategy ([ADR-021](../../../../docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf))
        is best served by an end-of-day ``historical_bars`` poll, which
        the M2-IB.5 pipeline integration will own. Intra-day streaming
        (1m / 5m via ``reqRealTimeBars`` or aggregated ``reqMktData``)
        is Phase 2+ work.
        """
        raise NotImplementedError(
            "IBMarketData.subscribe_bars is not implemented at M2-IB.3b-ii. "
            "Phase 1's daily strategy uses historical_bars; the polling-based "
            "subscribe_bars (or a per-frequency reqRealTimeBars wiring) lands "
            "at M2-IB.5 pipeline integration time."
        )

    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]:
        """Streaming trade-tick subscription.

        Not implemented at v1 — Phase 1 daily-frequency strategies don't
        need trade-level data. M5+ for trade-level analytics (parity
        diagnostic, signal validation).
        """
        raise NotImplementedError(
            "IBMarketData.subscribe_trades is not implemented at v1. "
            "Phase 1 daily strategies don't need trade ticks; revisit at M5+."
        )

    async def unsubscribe(self, instrument: Instrument) -> None:
        """No-op at v1 — there are no active streaming subscriptions to
        cancel. Matches :class:`blive.adapters.paper.market_data.PaperMarketData`'s
        shape. When :meth:`subscribe_bars` lands at M2-IB.5, this method
        will tear down the active polling task or ``cancelMktData``
        call."""
        log.debug("IBMarketData.unsubscribe(%r) — no-op at v1", instrument.symbol)


# --- Helpers ----------------------------------------------------------------


def _duration_str_for_range(start: datetime, end: datetime, freq: BarFreq) -> str:
    """Compute IB's ``durationStr`` from a (start, end) range.

    IB durationStr format: ``"<int> <S|D|W|M|Y>"`` (seconds / days / weeks
    / months / years). For 1d freq we use D-units; for sub-day freqs we
    use S-units (seconds), capped at 86400 seconds per day to avoid
    pacing-window blowup. The selection covers the Phase 1 case
    (1d, 30 days lookback) cleanly.
    """
    delta_seconds = (end - start).total_seconds()
    if delta_seconds <= 0:
        return "1 D"  # IB requires positive duration; minimum granularity
    if freq == "1d":
        days = max(1, int((delta_seconds + 86399) // 86400))  # ceil
        # IB caps "X D" at 365 D for many bar sizes; clamp + use Y if needed.
        if days > 365:
            years = max(1, (days + 364) // 365)
            return f"{years} Y"
        return f"{days} D"
    # Sub-day freq: use seconds, but capped at 86400 per request to stay
    # well within IB's per-call limits. Larger ranges should be issued as
    # multiple historical_bars calls; that's the caller's concern.
    seconds = max(60, int(delta_seconds))
    seconds = min(seconds, 86400)
    return f"{seconds} S"


def _parse_ib_bar(*, ib_bar: ib_async.BarData, instrument: Instrument, freq: BarFreq) -> Bar:
    """Map ``ib_async.BarData`` to broker-neutral :class:`Bar`.

    IB's bar's ``date`` field is a ``datetime`` in either UTC or the
    contract's exchange timezone depending on ``formatDate`` — we pass
    ``formatDate=2`` so it's UTC seconds-since-epoch encoded as a
    timezone-aware datetime. ``close_time_utc`` is computed from
    ``open_time_utc + freq_duration`` since IB only carries bar-start
    timestamps.
    """
    raw_date = ib_bar.date
    if isinstance(raw_date, datetime):
        if raw_date.tzinfo is None:
            # formatDate=2 should always be UTC-aware; defensive fallback.
            open_time_utc = raw_date.replace(tzinfo=timezone.utc)
        else:
            open_time_utc = raw_date.astimezone(timezone.utc)
    else:
        # IB returns datetime.date for daily bars under some setups.
        # Treat as midnight UTC of that date.
        open_time_utc = datetime(raw_date.year, raw_date.month, raw_date.day, tzinfo=timezone.utc)

    close_time_utc = open_time_utc + _duration_for_freq(freq)

    open_p = Decimal(str(ib_bar.open))
    high_p = Decimal(str(ib_bar.high))
    low_p = Decimal(str(ib_bar.low))
    close_p = Decimal(str(ib_bar.close))
    volume = Decimal(str(ib_bar.volume))

    # IB sometimes reports volume=-1 for missing data; clamp to 0 since
    # blive's Bar invariant is volume >= 0.
    if volume < 0:
        volume = Decimal("0")

    raw_vwap = getattr(ib_bar, "average", None)
    if raw_vwap is None or raw_vwap == 0 or raw_vwap == -1:
        vwap: Decimal | None = None
    else:
        vwap = Decimal(str(raw_vwap))

    return Bar(
        instrument=instrument,
        open_time_utc=open_time_utc,
        close_time_utc=close_time_utc,
        open=open_p,
        high=high_p,
        low=low_p,
        close=close_p,
        volume=volume,
        vwap=vwap,
    )


def _duration_for_freq(freq: BarFreq) -> timedelta:
    """Timedelta covered by one bar at the given frequency."""
    if freq == "1m":
        return timedelta(minutes=1)
    if freq == "5m":
        return timedelta(minutes=5)
    if freq == "15m":
        return timedelta(minutes=15)
    if freq == "1h":
        return timedelta(hours=1)
    if freq == "1d":
        return timedelta(days=1)
    raise ValueError(f"Unknown BarFreq {freq!r}")


__all__ = [
    "IBMarketData",
    "IBMarketDataError",
]
