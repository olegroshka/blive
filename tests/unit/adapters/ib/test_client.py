"""Tests for :mod:`blive.adapters.ib.client`.

Covers the IB driver wrapper per ADR-002 + ADR-031:

- Connection lifecycle (idempotent connect / disconnect).
- Rate-limiter integration (one ``global`` token consumed per connect).
- Typed exception mapping at the connection boundary
  (:class:`IBConnectionError` for socket-level failures).
- Constructor's ``ib=`` injection point used by tests.

Mock the underlying ``ib_async.IB`` via :class:`unittest.mock.MagicMock` +
:class:`unittest.mock.AsyncMock` so no TCP traffic happens — mirrors the
``httpx.MockTransport`` discipline in :mod:`tests.unit.adapters.ig.test_client`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import ib_async
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.client import IBClient, IBConnectionError, IBError
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def clock() -> SimClock:
    return SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def rate_limiter(clock: SimClock) -> TokenBucketRateLimiter:
    """IB-default-shaped buckets but with generous capacities so tests don't block."""
    return TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "global": RateLimitBucket(capacity=100, refill_per_second=Decimal("20")),
                "historical": RateLimitBucket(capacity=50, refill_per_second=Decimal("1")),
            }
        ),
    )


@pytest.fixture
def credentials() -> IBCredentials:
    return IBCredentials(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account_id="DU1234567",
    )


def _make_mock_ib(*, connected: bool = False) -> MagicMock:
    """Build a mocked ``ib_async.IB``.

    ``isConnected`` and ``disconnect`` are sync; ``connectAsync`` is async
    and is replaced with :class:`AsyncMock`. The mock starts disconnected
    by default; tests flip it to "connected" by either calling :meth:`connect`
    (which will mutate state via the side effect we wire) or by overriding
    ``isConnected.return_value`` directly.
    """
    m = MagicMock(spec=ib_async.IB)
    state = {"connected": connected}

    def _is_connected() -> bool:
        return state["connected"]

    async def _connect_async(**_kwargs: object) -> None:
        state["connected"] = True

    def _disconnect() -> None:
        state["connected"] = False

    m.isConnected.side_effect = _is_connected
    m.connectAsync = AsyncMock(side_effect=_connect_async)
    m.disconnect.side_effect = _disconnect
    return m


# --- Construction & accessors -----------------------------------------------


def test_client_exposes_ib_credentials_rate_limiter(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    client = IBClient(
        credentials=credentials,
        rate_limiter=rate_limiter,
        clock=clock,
        ib=mock_ib,
    )
    assert client.ib is mock_ib
    assert client.credentials is credentials
    assert client.rate_limiter is rate_limiter
    assert client.is_connected is False


def test_client_allocates_real_ib_when_not_injected(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """When ``ib=`` is omitted the client owns a real ``ib_async.IB``.

    No TCP traffic is initiated until :meth:`IBClient.connect` is called,
    so this stays a unit test.
    """
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    assert isinstance(client.ib, ib_async.IB)
    assert client.is_connected is False


# --- Connect happy path -----------------------------------------------------


async def test_connect_calls_connect_async_with_credentials(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)

    await client.connect()

    mock_ib.connectAsync.assert_awaited_once_with(
        host="127.0.0.1",
        port=4002,
        clientId=1,
    )
    assert client.is_connected is True


async def test_connect_is_idempotent(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Calling connect on an already-connected client is a no-op (no second
    connectAsync call, no second rate-limiter token consumed)."""
    mock_ib = _make_mock_ib(connected=True)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)

    await client.connect()

    mock_ib.connectAsync.assert_not_awaited()


async def test_connect_consumes_global_rate_limit_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """One ``global`` token consumed per connect call (KB-3 §1)."""
    mock_ib = _make_mock_ib()
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    before = rate_limiter.metrics()["global"].available

    await client.connect()

    after = rate_limiter.metrics()["global"].available
    assert after == before - Decimal(1)


# --- Connect error mapping --------------------------------------------------


async def test_connect_refused_maps_to_ibconnection_error(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """IB Gateway not listening on the configured port → IBConnectionError."""
    mock_ib = _make_mock_ib()
    mock_ib.connectAsync = AsyncMock(side_effect=ConnectionRefusedError("nope"))
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)

    with pytest.raises(IBConnectionError, match="refused"):
        await client.connect()
    assert client.is_connected is False


async def test_connect_timeout_maps_to_ibconnection_error(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Slow gateway → asyncio.TimeoutError → IBConnectionError."""

    async def _hang(**_kwargs: object) -> None:
        # Simulate a hang by raising TimeoutError directly — equivalent to
        # asyncio.wait_for timing out the underlying connectAsync.
        raise asyncio.TimeoutError()

    mock_ib = _make_mock_ib()
    mock_ib.connectAsync = AsyncMock(side_effect=_hang)
    client = IBClient(
        credentials=credentials,
        rate_limiter=rate_limiter,
        clock=clock,
        ib=mock_ib,
    )

    with pytest.raises(IBConnectionError, match="timed out"):
        await client.connect()


async def test_connect_oserror_maps_to_ibconnection_error(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Other socket-level failures → IBConnectionError."""
    mock_ib = _make_mock_ib()
    mock_ib.connectAsync = AsyncMock(side_effect=OSError("network unreachable"))
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)

    with pytest.raises(IBConnectionError, match="network unreachable"):
        await client.connect()


async def test_ibconnection_error_is_subclass_of_iberror() -> None:
    """The typed-exception hierarchy: catching IBError catches IBConnectionError."""
    assert issubclass(IBConnectionError, IBError)


# --- Disconnect -------------------------------------------------------------


async def test_disconnect_calls_underlying_disconnect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    await client.connect()
    assert client.is_connected is True

    await client.disconnect()

    mock_ib.disconnect.assert_called_once()
    assert client.is_connected is False


async def test_disconnect_is_idempotent_when_not_connected(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)

    await client.disconnect()

    mock_ib.disconnect.assert_not_called()


async def test_disconnect_swallows_underlying_errors(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A best-effort disconnect must not propagate exceptions — matches the
    IGClient.disconnect pattern."""
    mock_ib = _make_mock_ib()
    await_count = {"called": 0}

    def _boom() -> None:
        await_count["called"] += 1
        raise RuntimeError("disconnect blew up")

    # Connect first so the disconnect path actually fires.
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    await client.connect()
    mock_ib.disconnect.side_effect = _boom

    # Should NOT raise.
    await client.disconnect()
    assert await_count["called"] == 1
