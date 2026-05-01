"""Tests for :mod:`blive.adapters.ib.market_data`.

Covers IBMarketData per [INV-6 §1.2](../../../../../docs/inv/ports_adapters.md#12-marketdataport):

- ``historical_bars`` happy path: bar parsing, chronological ordering,
  filtering to the caller's [start, end) window.
- Rate-limit acquire on ``historical`` bucket; BID_ASK doubles cost
  per [KB-3 §2](../../../../../docs/kb/ib_pacing_spec.md#2-historical-data-pacing).
- BarFreq → IB barSizeSetting mapping; unsupported freq raises.
- subscribe_bars / subscribe_trades raise NotImplementedError.
- unsubscribe is a no-op.
- Error mapping: reqHistoricalDataAsync exception → IBMarketDataError.

Mock pattern matches ``test_broker.py``: MagicMock(spec=ib_async.IB) +
AsyncMock for reqHistoricalDataAsync.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import ib_async
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.client import IBClient
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.ib.market_data import IBMarketData, IBMarketDataError
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.types import AssetClass, Instrument

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def clock() -> SimClock:
    return SimClock(start=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def rate_limiter(clock: SimClock) -> TokenBucketRateLimiter:
    return TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "global": RateLimitBucket(capacity=100, refill_per_second=Decimal("20")),
                "historical": RateLimitBucket(capacity=100, refill_per_second=Decimal("1")),
            }
        ),
    )


@pytest.fixture
def credentials() -> IBCredentials:
    return IBCredentials(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account_id="DUTEST",
    )


@pytest.fixture
def cac_pa() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


def _make_market_data(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    *,
    historical_returns: list[ib_async.BarData] | None = None,
    historical_raises: Exception | None = None,
) -> tuple[IBMarketData, MagicMock]:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.isConnected.return_value = True
    if historical_raises is not None:
        mock_ib.reqHistoricalDataAsync = AsyncMock(side_effect=historical_raises)
    else:
        mock_ib.reqHistoricalDataAsync = AsyncMock(return_value=list(historical_returns or []))
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    resolver = IBInstrumentResolver(client)
    md = IBMarketData(client=client, resolver=resolver, clock=clock)
    return md, mock_ib


def _ib_bar(
    *,
    when: datetime,
    open_p: float = 78.0,
    high: float = 78.5,
    low: float = 77.5,
    close: float = 78.25,
    volume: int = 12000,
    average: float = 78.1,
) -> ib_async.BarData:
    return ib_async.BarData(
        date=when,
        open=open_p,
        high=high,
        low=low,
        close=close,
        volume=Decimal(str(volume)),
        average=Decimal(str(average)),
        barCount=1,
    )


# --- historical_bars: happy path --------------------------------------------


async def test_historical_bars_returns_parsed_bars_in_order(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """Daily CAC.PA bars from IB → blive Bars sorted by open_time_utc."""
    bars_in = [
        _ib_bar(when=datetime(2026, 4, 28, tzinfo=timezone.utc), close=78.10),
        _ib_bar(when=datetime(2026, 4, 29, tzinfo=timezone.utc), close=78.30),
        _ib_bar(when=datetime(2026, 4, 30, tzinfo=timezone.utc), close=78.50),
    ]
    md, mock_ib = _make_market_data(credentials, rate_limiter, clock, historical_returns=bars_in)

    result = await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 28, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    assert len(result) == 3
    assert [b.close for b in result] == [
        Decimal("78.10"),
        Decimal("78.30"),
        Decimal("78.50"),
    ]
    # close_time_utc = open + 1 day for daily bars.
    assert result[0].close_time_utc == result[0].open_time_utc + timedelta(days=1)
    # Each bar carries the original instrument.
    assert all(b.instrument == cac_pa for b in result)


async def test_historical_bars_filters_to_start_end_window(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """IB sometimes returns earlier bars within the requested duration; the
    adapter filters to the [start, end) window."""
    bars_in = [
        # Outside window (too early)
        _ib_bar(when=datetime(2026, 4, 25, tzinfo=timezone.utc)),
        # Inside window
        _ib_bar(when=datetime(2026, 4, 29, tzinfo=timezone.utc)),
        _ib_bar(when=datetime(2026, 4, 30, tzinfo=timezone.utc)),
        # Outside window (after end)
        _ib_bar(when=datetime(2026, 5, 5, tzinfo=timezone.utc)),
    ]
    md, _ = _make_market_data(credentials, rate_limiter, clock, historical_returns=bars_in)

    result = await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 28, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    assert len(result) == 2
    assert all(
        datetime(2026, 4, 28, tzinfo=timezone.utc)
        <= b.open_time_utc
        < datetime(2026, 5, 1, tzinfo=timezone.utc)
        for b in result
    )


async def test_historical_bars_passes_correct_contract(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """Contract sent to reqHistoricalDataAsync is the resolver's translation
    (CAC.PA → CAC on SBF per ADR-041)."""
    md, mock_ib = _make_market_data(credentials, rate_limiter, clock, historical_returns=[])

    await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 28, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    call_args = mock_ib.reqHistoricalDataAsync.await_args
    contract = call_args.args[0]
    assert contract.symbol == "CAC"  # Yahoo-suffix stripped
    assert contract.secType == "STK"
    assert contract.exchange == "SBF"


async def test_historical_bars_passes_correct_bar_size(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """blive's BarFreq maps to IB's barSizeSetting per the table."""
    md, mock_ib = _make_market_data(credentials, rate_limiter, clock, historical_returns=[])

    await md.historical_bars(
        cac_pa,
        freq="1m",
        start=datetime(2026, 5, 1, 13, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, 14, tzinfo=timezone.utc),
    )

    kwargs = mock_ib.reqHistoricalDataAsync.await_args.kwargs
    assert kwargs["barSizeSetting"] == "1 min"


async def test_historical_bars_consumes_one_historical_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock, historical_returns=[])
    before = rate_limiter.metrics()["historical"].available
    await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 30, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    after = rate_limiter.metrics()["historical"].available
    assert after == before - Decimal(1)


async def test_historical_bars_bid_ask_consumes_two_tokens(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """KB-3 §2: BID_ASK whatToShow counts double against the historical cap."""
    md, _ = _make_market_data(credentials, rate_limiter, clock, historical_returns=[])
    before = rate_limiter.metrics()["historical"].available
    await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 30, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
        what_to_show="BID_ASK",
    )
    after = rate_limiter.metrics()["historical"].available
    assert after == before - Decimal(2)


# --- historical_bars: rejection paths ---------------------------------------


async def test_historical_bars_naive_datetime_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock)
    with pytest.raises(ValueError, match="tz-aware"):
        await md.historical_bars(
            cac_pa,
            freq="1d",
            start=datetime(2026, 4, 30),  # naive
            end=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )


async def test_historical_bars_inverted_range_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock)
    with pytest.raises(ValueError, match="start"):
        await md.historical_bars(
            cac_pa,
            freq="1d",
            start=datetime(2026, 5, 1, tzinfo=timezone.utc),
            end=datetime(2026, 4, 30, tzinfo=timezone.utc),
        )


async def test_historical_bars_unsupported_freq_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock)
    with pytest.raises(ValueError, match="Unsupported BarFreq"):
        await md.historical_bars(
            cac_pa,
            freq="30s",  # type: ignore[arg-type]
            start=datetime(2026, 5, 1, 13, tzinfo=timezone.utc),
            end=datetime(2026, 5, 1, 14, tzinfo=timezone.utc),
        )


async def test_historical_bars_wraps_underlying_error(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(
        credentials,
        rate_limiter,
        clock,
        historical_raises=RuntimeError("IB pacing violation"),
    )
    with pytest.raises(IBMarketDataError, match="reqHistoricalDataAsync failed"):
        await md.historical_bars(
            cac_pa,
            freq="1d",
            start=datetime(2026, 4, 30, tzinfo=timezone.utc),
            end=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )


async def test_historical_bars_skips_unparseable_bars(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """A malformed BarData entry is logged + skipped, not raised."""
    bad = ib_async.BarData(
        date="not-a-date",  # type: ignore[arg-type]
        open=78.0,
        high=78.5,
        low=77.5,
        close=78.25,
        volume=Decimal("1000"),
        average=Decimal("78.1"),
        barCount=1,
    )
    good = _ib_bar(when=datetime(2026, 4, 30, tzinfo=timezone.utc))
    md, _ = _make_market_data(credentials, rate_limiter, clock, historical_returns=[bad, good])

    result = await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 28, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    # Only the well-formed bar survives.
    assert len(result) == 1
    assert result[0].close == Decimal("78.25")


async def test_historical_bars_volume_minus_one_clamped_to_zero(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """IB reports volume=-1 for missing data; blive's Bar requires volume >= 0."""
    bar_in = _ib_bar(when=datetime(2026, 4, 30, tzinfo=timezone.utc), volume=-1)
    md, _ = _make_market_data(credentials, rate_limiter, clock, historical_returns=[bar_in])

    result = await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 30, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    assert len(result) == 1
    assert result[0].volume == Decimal("0")


async def test_historical_bars_vwap_minus_one_or_zero_becomes_none(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    """IB sentinels for "no vwap available" map to None on the blive side."""
    bar_in = _ib_bar(when=datetime(2026, 4, 30, tzinfo=timezone.utc), average=-1.0)
    md, _ = _make_market_data(credentials, rate_limiter, clock, historical_returns=[bar_in])

    result = await md.historical_bars(
        cac_pa,
        freq="1d",
        start=datetime(2026, 4, 30, tzinfo=timezone.utc),
        end=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    assert result[0].vwap is None


# --- streaming methods: NotImplementedError ---------------------------------


async def test_subscribe_bars_raises_not_implemented(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock)
    # `async def` returning AsyncIterator: awaiting raises before any
    # iteration begins. Match PaperMarketData's pattern for the same
    # NotImplementedError shape.
    with pytest.raises(NotImplementedError, match="subscribe_bars"):
        await md.subscribe_bars(cac_pa, freq="1d")


async def test_subscribe_trades_raises_not_implemented(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock)
    with pytest.raises(NotImplementedError, match="subscribe_trades"):
        await md.subscribe_trades(cac_pa)


async def test_unsubscribe_is_noop(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    cac_pa: Instrument,
) -> None:
    md, _ = _make_market_data(credentials, rate_limiter, clock)
    await md.unsubscribe(cac_pa)  # must not raise
