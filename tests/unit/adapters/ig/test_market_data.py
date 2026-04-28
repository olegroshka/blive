"""Tests for :mod:`blive.adapters.ig.market_data`.

M2-IG.3 covers :meth:`historical_bars` over REST plus the helpers; the
streaming side (:meth:`subscribe_bars`) is asserted to raise
``NotImplementedError`` until M2-IG.3 follow-up lands the Lightstreamer
integration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable

import httpx
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ig.client import IGClient
from blive.adapters.ig.credentials import IGCredentials
from blive.adapters.ig.instrument_resolver import IGInstrumentResolver
from blive.adapters.ig.market_data import (
    IGMarketData,
    _format_ig_datetime,
    _freq_to_ig_resolution,
    _freq_to_timedelta,
    _ohlc_value,
    _parse_ig_snapshot,
    _parse_price_bar,
)
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.types import AssetClass, Instrument


# --- Fixtures ---------------------------------------------------------------


def _login_response() -> httpx.Response:
    return httpx.Response(
        status_code=200,
        headers={"CST": "test-cst", "X-SECURITY-TOKEN": "test-token"},
        json={"accountId": "ACC123"},
    )


def _market_response(epic: str = "IX.D.CAC40.CASH.IP") -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={
            "instrument": {
                "epic": epic,
                "name": "France 40",
                "currencies": [{"code": "EUR"}],
                "lotSize": 1.0,
            },
            "dealingRules": {"minDealSize": {"value": 0.1, "unit": "POINTS"}},
            "snapshot": {},
        },
    )


@pytest.fixture
def cac40_cfd() -> Instrument:
    return Instrument(
        symbol="CAC40",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )


def _make_market_data(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[IGMarketData, IGClient, SimClock]:
    clock = SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))
    creds = IGCredentials(
        api_key="k", username="u", password="p", account_id="ACC", environment="demo"
    )
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "general": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
                "trading": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
                "historical_prices": RateLimitBucket(
                    capacity=100, refill_per_second=Decimal("10")
                ),
            }
        ),
    )
    transport = httpx.MockTransport(handler)
    client = IGClient(
        credentials=creds, rate_limiter=rate_limiter, clock=clock, transport=transport
    )
    resolver = IGInstrumentResolver(client)
    md = IGMarketData(client=client, resolver=resolver, clock=clock)
    return md, client, clock


# --- Resolution + duration mapping (pure tables) ---------------------------


def test_freq_to_ig_resolution_table() -> None:
    assert _freq_to_ig_resolution("1m") == "MINUTE"
    assert _freq_to_ig_resolution("5m") == "MINUTE_5"
    assert _freq_to_ig_resolution("15m") == "MINUTE_15"
    assert _freq_to_ig_resolution("1h") == "HOUR"
    assert _freq_to_ig_resolution("1d") == "DAY"


def test_freq_to_timedelta_table() -> None:
    assert _freq_to_timedelta("1m") == timedelta(minutes=1)
    assert _freq_to_timedelta("5m") == timedelta(minutes=5)
    assert _freq_to_timedelta("15m") == timedelta(minutes=15)
    assert _freq_to_timedelta("1h") == timedelta(hours=1)
    assert _freq_to_timedelta("1d") == timedelta(days=1)


def test_format_ig_datetime_uses_iso_no_z() -> None:
    dt = datetime(2026, 4, 28, 9, 30, 45, tzinfo=timezone.utc)
    assert _format_ig_datetime(dt) == "2026-04-28T09:30:45"


def test_format_ig_datetime_naive_raises() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _format_ig_datetime(datetime(2026, 4, 28, 9, 30))


def test_format_ig_datetime_converts_to_utc() -> None:
    """Non-UTC tz-aware datetimes get converted to UTC before formatting."""
    from datetime import timezone as _tz

    plus_one = _tz(timedelta(hours=1))
    dt = datetime(2026, 4, 28, 10, 30, 45, tzinfo=plus_one)
    # Equivalent UTC: 09:30:45.
    assert _format_ig_datetime(dt) == "2026-04-28T09:30:45"


# --- _ohlc_value helper ----------------------------------------------------


def test_ohlc_value_prefers_last_traded() -> None:
    entry = {"openPrice": {"bid": 100.0, "ask": 102.0, "lastTraded": 101.5}}
    assert _ohlc_value(entry, "openPrice") == Decimal("101.5")


def test_ohlc_value_falls_back_to_mid() -> None:
    entry = {"openPrice": {"bid": 100.0, "ask": 102.0}}
    assert _ohlc_value(entry, "openPrice") == Decimal("101")


def test_ohlc_value_missing_field_raises() -> None:
    with pytest.raises(ValueError, match="missing 'openPrice'"):
        _ohlc_value({}, "openPrice")


def test_ohlc_value_missing_bid_or_ask_raises() -> None:
    entry = {"openPrice": {"bid": 100.0}}  # no ask, no lastTraded
    with pytest.raises(ValueError, match="missing bid / ask"):
        _ohlc_value(entry, "openPrice")


# --- _parse_ig_snapshot ----------------------------------------------------


def test_parse_snapshot_iso_z() -> None:
    assert _parse_ig_snapshot("2026-04-28T09:00:00Z") == datetime(
        2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc
    )


def test_parse_snapshot_iso_naive_assumed_utc() -> None:
    assert _parse_ig_snapshot("2026-04-28T09:00:00") == datetime(
        2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc
    )


def test_parse_snapshot_slash_format() -> None:
    assert _parse_ig_snapshot("2026/04/28 09:00:00") == datetime(
        2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc
    )


def test_parse_snapshot_unrecognised_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised"):
        _parse_ig_snapshot("nope")


# --- _parse_price_bar ------------------------------------------------------


def test_parse_price_bar_full_entry(cac40_cfd: Instrument) -> None:
    entry: dict[str, Any] = {
        "snapshotTimeUTC": "2026-04-28T09:00:00",
        "openPrice": {"bid": 7000.0, "ask": 7002.0, "lastTraded": 7001.0},
        "highPrice": {"bid": 7050.0, "ask": 7052.0, "lastTraded": 7051.0},
        "lowPrice": {"bid": 6990.0, "ask": 6992.0, "lastTraded": 6991.0},
        "closePrice": {"bid": 7030.0, "ask": 7032.0, "lastTraded": 7031.0},
        "lastTradedVolume": 12345,
    }
    bar = _parse_price_bar(entry, instrument=cac40_cfd, bar_duration=timedelta(minutes=5))
    assert bar.instrument == cac40_cfd
    assert bar.open_time_utc == datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc)
    assert bar.close_time_utc == datetime(2026, 4, 28, 9, 5, 0, tzinfo=timezone.utc)
    assert bar.open == Decimal("7001.0")
    assert bar.high == Decimal("7051.0")
    assert bar.low == Decimal("6991.0")
    assert bar.close == Decimal("7031.0")
    assert bar.volume == Decimal("12345")
    assert bar.vwap is None


def test_parse_price_bar_uses_mid_when_no_last_traded(cac40_cfd: Instrument) -> None:
    entry: dict[str, Any] = {
        "snapshotTimeUTC": "2026-04-28T09:00:00",
        "openPrice": {"bid": 7000.0, "ask": 7002.0},  # no lastTraded
        "highPrice": {"bid": 7050.0, "ask": 7052.0},
        "lowPrice": {"bid": 6990.0, "ask": 6992.0},
        "closePrice": {"bid": 7030.0, "ask": 7032.0},
        "lastTradedVolume": 0,
    }
    bar = _parse_price_bar(entry, instrument=cac40_cfd, bar_duration=timedelta(days=1))
    assert bar.open == Decimal("7001")  # midpoint
    assert bar.close == Decimal("7031")
    assert bar.volume == Decimal("0")


def test_parse_price_bar_negative_volume_clamped_to_zero(cac40_cfd: Instrument) -> None:
    """Defensive: weird IG response with negative volume clamps to 0."""
    entry: dict[str, Any] = {
        "snapshotTimeUTC": "2026-04-28T09:00:00",
        "openPrice": {"bid": 1.0, "ask": 1.0},
        "highPrice": {"bid": 1.0, "ask": 1.0},
        "lowPrice": {"bid": 1.0, "ask": 1.0},
        "closePrice": {"bid": 1.0, "ask": 1.0},
        "lastTradedVolume": -5,
    }
    bar = _parse_price_bar(entry, instrument=cac40_cfd, bar_duration=timedelta(days=1))
    assert bar.volume == Decimal("0")


def test_parse_price_bar_falls_back_to_snapshot_time_without_utc(
    cac40_cfd: Instrument,
) -> None:
    """When snapshotTimeUTC is missing, fall back to snapshotTime (slash format)."""
    entry: dict[str, Any] = {
        "snapshotTime": "2026/04/28 09:00:00",
        "openPrice": {"bid": 1.0, "ask": 1.0},
        "highPrice": {"bid": 1.0, "ask": 1.0},
        "lowPrice": {"bid": 1.0, "ask": 1.0},
        "closePrice": {"bid": 1.0, "ask": 1.0},
        "lastTradedVolume": 1,
    }
    bar = _parse_price_bar(entry, instrument=cac40_cfd, bar_duration=timedelta(days=1))
    assert bar.open_time_utc == datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_price_bar_missing_snapshot_raises(cac40_cfd: Instrument) -> None:
    entry: dict[str, Any] = {
        # no snapshotTime[UTC]
        "openPrice": {"bid": 1.0, "ask": 1.0},
        "highPrice": {"bid": 1.0, "ask": 1.0},
        "lowPrice": {"bid": 1.0, "ask": 1.0},
        "closePrice": {"bid": 1.0, "ask": 1.0},
    }
    with pytest.raises(ValueError, match="snapshotTime"):
        _parse_price_bar(entry, instrument=cac40_cfd, bar_duration=timedelta(days=1))


# --- historical_bars (REST) ------------------------------------------------


async def test_historical_bars_returns_parsed_bars(cac40_cfd: Instrument) -> None:
    requests_seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        requests_seen.append(f"{request.method} {path}")
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response()
        if "/prices/IX.D.CAC40.CASH.IP/DAY" in path:
            return httpx.Response(
                status_code=200,
                json={
                    "prices": [
                        {
                            "snapshotTimeUTC": "2026-04-25T00:00:00",
                            "openPrice": {"bid": 7000.0, "ask": 7002.0},
                            "highPrice": {"bid": 7050.0, "ask": 7052.0},
                            "lowPrice": {"bid": 6990.0, "ask": 6992.0},
                            "closePrice": {"bid": 7030.0, "ask": 7032.0},
                            "lastTradedVolume": 1000,
                        },
                        {
                            "snapshotTimeUTC": "2026-04-26T00:00:00",
                            "openPrice": {"bid": 7030.0, "ask": 7032.0},
                            "highPrice": {"bid": 7080.0, "ask": 7082.0},
                            "lowPrice": {"bid": 7020.0, "ask": 7022.0},
                            "closePrice": {"bid": 7060.0, "ask": 7062.0},
                            "lastTradedVolume": 1500,
                        },
                    ]
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    md, client, _clock = _make_market_data(handler)
    await client.connect()

    bars = await md.historical_bars(
        cac40_cfd,
        "1d",
        start=datetime(2026, 4, 25, tzinfo=timezone.utc),
        end=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    assert len(bars) == 2
    assert bars[0].open_time_utc < bars[1].open_time_utc
    assert bars[0].instrument == cac40_cfd
    assert bars[0].open == Decimal("7001")  # bid/ask mid
    assert bars[1].close == Decimal("7061")
    # URL contained the expected resolution + date segments.
    assert any(
        "/prices/IX.D.CAC40.CASH.IP/DAY/2026-04-25T00:00:00/2026-04-27T00:00:00" in r
        for r in requests_seen
    )


async def test_historical_bars_rejects_naive_datetimes(cac40_cfd: Instrument) -> None:
    md, _client, _clock = _make_market_data(lambda _: _login_response())
    with pytest.raises(ValueError, match="UTC-aware"):
        await md.historical_bars(
            cac40_cfd,
            "1d",
            start=datetime(2026, 4, 25),  # naive
            end=datetime(2026, 4, 27, tzinfo=timezone.utc),
        )


async def test_historical_bars_rejects_inverted_range(cac40_cfd: Instrument) -> None:
    md, _client, _clock = _make_market_data(lambda _: _login_response())
    with pytest.raises(ValueError, match="must be <"):
        await md.historical_bars(
            cac40_cfd,
            "1d",
            start=datetime(2026, 4, 27, tzinfo=timezone.utc),
            end=datetime(2026, 4, 25, tzinfo=timezone.utc),
        )


async def test_historical_bars_empty_response(cac40_cfd: Instrument) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response()
        if "/prices/" in path:
            return httpx.Response(status_code=200, json={"prices": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    md, client, _clock = _make_market_data(handler)
    await client.connect()
    bars = await md.historical_bars(
        cac40_cfd,
        "1d",
        start=datetime(2026, 4, 25, tzinfo=timezone.utc),
        end=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    assert bars == []


async def test_historical_bars_skips_malformed_entries(cac40_cfd: Instrument) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response()
        if "/prices/" in path:
            return httpx.Response(
                status_code=200,
                json={
                    "prices": [
                        {  # missing snapshotTime — skipped
                            "openPrice": {"bid": 1, "ask": 1},
                            "highPrice": {"bid": 1, "ask": 1},
                            "lowPrice": {"bid": 1, "ask": 1},
                            "closePrice": {"bid": 1, "ask": 1},
                        },
                        "not-a-dict",  # skipped
                        {  # well-formed
                            "snapshotTimeUTC": "2026-04-26T00:00:00",
                            "openPrice": {"bid": 7000.0, "ask": 7002.0},
                            "highPrice": {"bid": 7050.0, "ask": 7052.0},
                            "lowPrice": {"bid": 6990.0, "ask": 6992.0},
                            "closePrice": {"bid": 7030.0, "ask": 7032.0},
                            "lastTradedVolume": 100,
                        },
                    ]
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    md, client, _clock = _make_market_data(handler)
    await client.connect()
    bars = await md.historical_bars(
        cac40_cfd,
        "1d",
        start=datetime(2026, 4, 25, tzinfo=timezone.utc),
        end=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    assert len(bars) == 1


async def test_historical_bars_uses_historical_prices_bucket(
    cac40_cfd: Instrument,
) -> None:
    """Drain the historical_prices bucket; verify historical_bars blocks
    until refill (proves it draws from the correct bucket)."""
    clock = SimClock(start=datetime(2026, 4, 28, tzinfo=timezone.utc))
    creds = IGCredentials(
        api_key="k", username="u", password="p", account_id="ACC", environment="demo"
    )
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "general": RateLimitBucket(capacity=10, refill_per_second=Decimal("10")),
                "trading": RateLimitBucket(capacity=10, refill_per_second=Decimal("10")),
                "historical_prices": RateLimitBucket(
                    capacity=1, refill_per_second=Decimal("0.5")
                ),
            }
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response()
        if "/prices/" in path:
            return httpx.Response(status_code=200, json={"prices": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    transport = httpx.MockTransport(handler)
    client = IGClient(
        credentials=creds, rate_limiter=rate_limiter, clock=clock, transport=transport
    )
    resolver = IGInstrumentResolver(client)
    md = IGMarketData(client=client, resolver=resolver, clock=clock)
    await client.connect()

    # Drain the historical_prices bucket.
    await rate_limiter.acquire("historical_prices")
    before = clock.now()
    await md.historical_bars(
        cac40_cfd,
        "1d",
        start=datetime(2026, 4, 25, tzinfo=timezone.utc),
        end=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    elapsed = (clock.now() - before).total_seconds()
    assert elapsed >= 2.0, (
        f"historical_bars should wait for historical_prices bucket refill "
        f"(~2s for 1 token at 0.5/s), got {elapsed}"
    )


# --- Streaming-side stubs --------------------------------------------------


async def test_subscribe_bars_raises_not_implemented(cac40_cfd: Instrument) -> None:
    md, _client, _clock = _make_market_data(lambda _: _login_response())
    with pytest.raises(NotImplementedError, match="Lightstreamer"):
        await md.subscribe_bars(cac40_cfd, "1d")


async def test_subscribe_trades_raises_not_implemented(cac40_cfd: Instrument) -> None:
    md, _client, _clock = _make_market_data(lambda _: _login_response())
    with pytest.raises(NotImplementedError, match="out of scope"):
        await md.subscribe_trades(cac40_cfd)


async def test_unsubscribe_is_noop(cac40_cfd: Instrument) -> None:
    md, _client, _clock = _make_market_data(lambda _: _login_response())
    # Should not raise; returns None.
    result = await md.unsubscribe(cac40_cfd)
    assert result is None
