"""Tests for :mod:`blive.adapters.ib.broker`.

Covers the IB broker read-side per [INV-6 §1.1](../../../../../docs/inv/ports_adapters.md#11-brokerport):
connect/disconnect lifecycle, ConnectionStatus emission, positions /
account_snapshot / open_orders parsing from ``ib_async`` cached state,
the events() iterator, and write-method NotImplementedError raises.

Mocking strategy:

- ``ib_async.IB`` instance: :class:`unittest.mock.MagicMock` with
  ``spec=ib_async.IB`` (same pattern as other IB tests).
- ``accountValueEvent``: a real :class:`eventkit.Event` so the
  broker's ``+=`` / ``-=`` registration round-trips realistically and
  tests can drive pushes via ``event.emit(account_value)``.
- ``accountValues`` / ``reqPositionsAsync`` / ``reqAllOpenOrdersAsync``:
  configured per-test to return the desired payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import eventkit
import ib_async
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.broker import IBBroker, IBShapeError
from blive.adapters.ib.client import IBClient
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.events import ConnectionStatus
from blive.domain.types import (
    AssetClass,
    OrderSide,
    OrderType,
    TimeInForce,
)

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
        account_id="DUTEST",
    )


def _make_mock_ib(
    *,
    initial_account_values: list[ib_async.AccountValue] | None = None,
    positions: list[ib_async.Position] | None = None,
    open_trades: list[ib_async.Trade] | None = None,
) -> MagicMock:
    """Build an ``ib_async.IB`` mock with the live-event surface wired.

    ``accountValueEvent`` is a real :class:`eventkit.Event` so the
    broker can register / detach handlers; tests drive pushes via
    ``event.emit(account_value)``.

    ``accountValues``, ``reqPositionsAsync``, ``reqAllOpenOrdersAsync``
    are configured per-test.
    """
    m = MagicMock(spec=ib_async.IB)
    state = {"connected": False}

    def _is_connected() -> bool:
        return state["connected"]

    async def _connect_async(**_kwargs: object) -> None:
        state["connected"] = True

    def _disconnect() -> None:
        state["connected"] = False

    m.isConnected.side_effect = _is_connected
    m.connectAsync = AsyncMock(side_effect=_connect_async)
    m.disconnect.side_effect = _disconnect

    # Real eventkit.Event for accountValueEvent so += / -= work realistically.
    m.accountValueEvent = eventkit.Event()

    # Account values cache (read by IBBroker.connect to seed local cache).
    m.accountValues.return_value = list(initial_account_values or [])

    # Async readers.
    m.reqPositionsAsync = AsyncMock(return_value=list(positions or []))
    m.reqAllOpenOrdersAsync = AsyncMock(return_value=list(open_trades or []))

    return m


def _make_broker(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    mock_ib: MagicMock,
) -> IBBroker:
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    resolver = IBInstrumentResolver(client)
    return IBBroker(client=client, resolver=resolver, clock=clock)


def _ib_account_value(
    *,
    tag: str,
    value: str,
    currency: str = "EUR",
    account: str = "DUTEST",
) -> ib_async.AccountValue:
    return ib_async.AccountValue(
        account=account,
        tag=tag,
        value=value,
        currency=currency,
        modelCode="",
    )


def _ib_position(
    *,
    symbol: str,
    secType: str = "STK",
    exchange: str = "SBF",
    currency: str = "EUR",
    quantity: Decimal | float,
    avg_cost: Decimal | float,
    account: str = "DUTEST",
    primary_exchange: str = "",
) -> ib_async.Position:
    contract = ib_async.Contract(
        symbol=symbol,
        secType=secType,
        exchange=exchange,
        primaryExchange=primary_exchange,
        currency=currency,
    )
    return ib_async.Position(
        account=account,
        contract=contract,
        position=Decimal(str(quantity)),
        avgCost=float(avg_cost),
    )


def _ib_trade(
    *,
    symbol: str,
    action: str = "BUY",
    order_type: str = "LMT",
    tif: str = "DAY",
    quantity: Decimal | float = 100,
    limit_price: float = 78.50,
    stop_price: float = 0.0,
    order_id: int = 42,
    perm_id: int = 1234567,
    exchange: str = "SBF",
    currency: str = "EUR",
) -> ib_async.Trade:
    contract = ib_async.Contract(
        symbol=symbol,
        secType="STK",
        exchange=exchange,
        currency=currency,
    )
    order = ib_async.LimitOrder(action, Decimal(str(quantity)), limit_price)
    order.orderId = order_id
    order.permId = perm_id
    order.orderType = order_type
    order.tif = tif
    order.lmtPrice = limit_price
    order.auxPrice = stop_price
    order.totalQuantity = Decimal(str(quantity))
    return ib_async.Trade(contract=contract, order=order)


# --- Construction & accessors -----------------------------------------------


def test_broker_starts_disconnected_with_synthetic_strategy_id(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    assert broker.is_connected is False
    assert broker.broker_strategy_id == "ib_DUTEST"


# --- connect / disconnect lifecycle -----------------------------------------


async def test_connect_seeds_cache_subscribes_and_emits_status(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        _ib_account_value(tag="TotalCashBalance", value="50000.00"),
        _ib_account_value(tag="BuyingPower", value="200000.00"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)

    await broker.connect()

    assert broker.is_connected is True
    # ib_async.accountValues was queried with the account id.
    mock_ib.accountValues.assert_called_once_with("DUTEST")
    # An additional push via the event handler is captured.
    mock_ib.accountValueEvent.emit(_ib_account_value(tag="GrossPositionValue", value="80000.00"))
    snapshot = await broker.account_snapshot()
    assert snapshot.equity == Decimal("100000.00")
    assert snapshot.gross_exposure == Decimal("80000.00")  # event-pushed value


async def test_connect_emits_connection_status_event(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)

    await broker.connect()

    events_iter = broker.events()
    event = await events_iter.__anext__()
    assert isinstance(event, ConnectionStatus)
    assert event.connected is True
    assert "DUTEST" in event.detail


async def test_connect_is_idempotent(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)

    await broker.connect()
    await broker.connect()

    # accountValues called once (the second connect was a no-op).
    assert mock_ib.accountValues.call_count == 1


async def test_disconnect_clears_cache_detaches_and_emits_status(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    initial = [_ib_account_value(tag="NetLiquidationByCurrency", value="100000")]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    # Sanity: cache populated.
    snapshot1 = await broker.account_snapshot()
    assert snapshot1.equity == Decimal("100000")

    await broker.disconnect()

    assert broker.is_connected is False
    # account_snapshot now raises since the cache is cleared.
    with pytest.raises(RuntimeError, match="connect"):
        await broker.account_snapshot()


async def test_disconnect_is_idempotent_when_not_connected(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    # No-op (no events should be emitted, no underlying IB calls).
    await broker.disconnect()


async def test_disconnect_after_connect_emits_status(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    await broker.disconnect()

    # Drain two events (connect then disconnect).
    events_iter = broker.events()
    e1 = await events_iter.__anext__()
    e2 = await events_iter.__anext__()
    assert isinstance(e1, ConnectionStatus) and e1.connected is True
    assert isinstance(e2, ConnectionStatus) and e2.connected is False


# --- positions --------------------------------------------------------------


async def test_positions_returns_parsed_records(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    positions = [
        _ib_position(symbol="CAC", quantity=Decimal("10"), avg_cost=78.42),
    ]
    mock_ib = _make_mock_ib(positions=positions)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.positions()

    assert len(result) == 1
    pos = result[0]
    assert pos.instrument.symbol == "CAC"
    assert pos.instrument.venue == "XPAR"  # SBF reverse-mapped
    assert pos.instrument.currency == "EUR"
    assert pos.instrument.asset_class == AssetClass.EQUITY  # STK default
    assert pos.strategy_id == "ib_DUTEST"
    assert pos.quantity == Decimal("10")
    assert pos.avg_cost == Decimal("78.42")


async def test_positions_uses_primary_exchange_when_set(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """When IB sets primaryExchange, prefer it over the routing exchange."""
    positions = [
        _ib_position(
            symbol="AAPL",
            exchange="SMART",
            primary_exchange="NASDAQ",
            currency="USD",
            quantity=Decimal("50"),
            avg_cost=180.0,
        )
    ]
    mock_ib = _make_mock_ib(positions=positions)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.positions()

    assert result[0].instrument.venue == "XNAS"  # primaryExchange NASDAQ → XNAS


async def test_positions_consumes_global_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib(positions=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    before = rate_limiter.metrics()["global"].available
    await broker.positions()
    after = rate_limiter.metrics()["global"].available
    assert after == before - Decimal(1)


async def test_positions_skips_unparseable_entries(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A malformed Position entry is logged + skipped, not raised."""
    bad = ib_async.Position(
        account="DUTEST",
        contract=ib_async.Contract(symbol="", secType="STK", exchange="SBF", currency="EUR"),
        position=Decimal("1"),
        avgCost=10.0,
    )
    good = _ib_position(symbol="CAC", quantity=Decimal("5"), avg_cost=78)
    mock_ib = _make_mock_ib(positions=[bad, good])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.positions()

    # Bad one (empty symbol) skipped; good one returned.
    assert len(result) == 1
    assert result[0].instrument.symbol == "CAC"


async def test_positions_requires_connect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(RuntimeError, match="connect"):
        await broker.positions()


# --- account_snapshot -------------------------------------------------------


async def test_account_snapshot_builds_from_seed_cache(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00", currency="EUR"),
        _ib_account_value(tag="TotalCashBalance", value="40000.00", currency="EUR"),
        _ib_account_value(tag="TotalCashBalance", value="20000.00", currency="USD"),
        _ib_account_value(tag="BuyingPower", value="200000.00", currency="EUR"),
        _ib_account_value(tag="GrossPositionValue", value="60000.00", currency="EUR"),
        _ib_account_value(tag="MaintMarginReq", value="5000.00", currency="EUR"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    snapshot = await broker.account_snapshot()

    assert snapshot.base_currency == "EUR"
    assert snapshot.equity == Decimal("100000.00")
    assert snapshot.buying_power == Decimal("200000.00")
    assert snapshot.gross_exposure == Decimal("60000.00")
    assert snapshot.margin_used == Decimal("5000.00")
    assert snapshot.cash_by_ccy == {"EUR": Decimal("40000.00"), "USD": Decimal("20000.00")}
    # leverage = gross / equity = 0.6
    assert snapshot.leverage == Decimal("0.6")


async def test_account_snapshot_raises_when_cache_empty(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib(initial_account_values=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    with pytest.raises(IBShapeError, match="not yet received"):
        await broker.account_snapshot()


async def test_account_snapshot_accepts_post_connect_event_pushes(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Values pushed via accountValueEvent after connect update the cache."""
    mock_ib = _make_mock_ib(
        initial_account_values=[
            _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        ]
    )
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    # Push a fresher value via the event.
    mock_ib.accountValueEvent.emit(
        _ib_account_value(tag="NetLiquidationByCurrency", value="105000.00")
    )

    snapshot = await broker.account_snapshot()
    assert snapshot.equity == Decimal("105000.00")  # event value won


async def test_account_snapshot_filters_other_account_pushes(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Pushes for a different account id (sub-account stream) are dropped."""
    mock_ib = _make_mock_ib(
        initial_account_values=[
            _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        ]
    )
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    # Push a value for a different account — should be ignored.
    mock_ib.accountValueEvent.emit(
        _ib_account_value(
            tag="NetLiquidationByCurrency",
            value="999999.00",
            account="DUOTHERACCT",
        )
    )

    snapshot = await broker.account_snapshot()
    assert snapshot.equity == Decimal("100000.00")  # not overwritten


async def test_account_snapshot_requires_connect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(RuntimeError, match="connect"):
        await broker.account_snapshot()


# --- open_orders ------------------------------------------------------------


async def test_open_orders_returns_parsed_orders(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    trades = [
        _ib_trade(symbol="CAC", action="BUY", order_type="LMT", quantity=100, limit_price=78.50),
    ]
    mock_ib = _make_mock_ib(open_trades=trades)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.open_orders()

    assert len(result) == 1
    order = result[0]
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.LMT
    assert order.time_in_force == TimeInForce.DAY
    assert order.quantity == Decimal("100")
    assert order.limit_price == Decimal("78.5")
    assert order.stop_price is None
    assert order.strategy_id == "ib_DUTEST"
    assert order.tags["ib_order_id"] == "42"
    assert order.tags["ib_perm_id"] == "1234567"


async def test_open_orders_skips_unparseable(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """An unsupported orderType is logged + skipped, not raised."""
    bad = _ib_trade(symbol="X", order_type="MIDPRICE", quantity=10, limit_price=100)
    good = _ib_trade(symbol="CAC", quantity=50, limit_price=78.5)
    mock_ib = _make_mock_ib(open_trades=[bad, good])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.open_orders()

    assert len(result) == 1
    assert result[0].instrument.symbol == "CAC"


async def test_open_orders_consumes_global_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib(open_trades=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    before = rate_limiter.metrics()["global"].available
    await broker.open_orders()
    after = rate_limiter.metrics()["global"].available
    assert after == before - Decimal(1)


async def test_open_orders_requires_connect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(RuntimeError, match="connect"):
        await broker.open_orders()


# --- write methods (M2-IB.4) ------------------------------------------------


async def test_submit_raises_not_implemented(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Write methods raise pending M2-IB.4. Error mentions Read-Only API
    checkbox so the operator knows what to fix in Gateway too."""
    from uuid import uuid4

    from blive.domain.types import ClientOrderId, Instrument, Order

    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    order = Order(
        client_order_id=ClientOrderId(uuid4()),
        strategy_id="test",
        instrument=Instrument(
            symbol="CAC",
            venue="XPAR",
            currency="EUR",
            asset_class=AssetClass.ETF,
            multiplier=Decimal("1"),
        ),
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MKT,
        time_in_force=TimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NotImplementedError, match="M2-IB.4"):
        await broker.submit(order)


async def test_cancel_raises_not_implemented(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    from uuid import uuid4

    from blive.domain.types import ClientOrderId

    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    with pytest.raises(NotImplementedError, match="M2-IB.4"):
        await broker.cancel(ClientOrderId(uuid4()))


async def test_replace_raises_not_implemented(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    from uuid import uuid4

    from blive.domain.types import ClientOrderId, OrderUpdate

    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    with pytest.raises(NotImplementedError, match="M2-IB.4"):
        await broker.replace(
            ClientOrderId(uuid4()),
            OrderUpdate(quantity=Decimal("50"), limit_price=None, stop_price=None),
        )
