"""Diagnostic for the M2-IB.6.2 reason='rejected' bug.

The Mon 2026-05-04 PRIIPs probe surfaced an event.reason of literal
``'rejected'`` instead of the formatted ``'ib:201 {message}'`` that
INV-14 v0.5 documents. This diagnostic re-submits a single TQQQ order
and dumps the underlying ``ib_async.Trade`` state at terminal — the
``orderStatus.status``, the full ``trade.log`` list (each
TradeLogEntry's status / errorCode / message), and ``whyHeld`` — so
we can tell which branch in ``IBBroker._on_order_status`` fired and
why the message field was empty.

Read-only against IB Paper. Produces a single rejected order.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import ib_async

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBCredentials,
    IBInstrumentResolver,
)
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.events import OrderEvent
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderType,
    TimeInForce,
)

_TQQQ = Instrument(
    symbol="TQQQ",
    venue="XNAS",
    currency="USD",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)


async def _run() -> int:
    credentials = IBCredentials.load()
    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    await broker.connect()
    print(f"connected: {broker.is_connected}")
    await asyncio.wait_for(broker._events.get(), timeout=2.0)  # noqa: SLF001 — drain conn status

    cid = ClientOrderId(uuid4())
    order = Order(
        client_order_id=cid,
        strategy_id="probe-diag",
        instrument=_TQQQ,
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("1.00"),
        stop_price=None,
        parent_id=None,
        tags={"probe": "diag-201"},
        created_at=datetime.now(tz=timezone.utc),
    )

    await broker.submit(order)
    print(f"submitted client_order_id={str(cid)[:8]}...")

    # Drain events until we see a terminal one.
    deadline = asyncio.get_event_loop().time() + 8.0
    terminal_event: OrderEvent | None = None
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        try:
            event = await asyncio.wait_for(broker._events.get(), timeout=remaining)  # noqa: SLF001
        except asyncio.TimeoutError:
            break
        if not isinstance(event, OrderEvent):
            continue
        print(
            f"  event {event.kind.name}  reason={event.reason!r}  venue_oid={event.venue_order_id}"
        )
        if event.kind in {
            OrderEventKind.FILLED,
            OrderEventKind.CANCELED,
            OrderEventKind.REJECTED,
        }:
            terminal_event = event
            break

    # Now look up the underlying ib_async.Trade and dump its full state.
    ib = client._ib  # noqa: SLF001
    trades_match = (
        [t for t in ib.trades() if str(t.order.orderId) == (terminal_event.venue_order_id or "")]
        if terminal_event
        else []
    )
    if not trades_match:
        print("\nNO TRADE FOUND for the terminal event's venue_order_id — fallback to all trades:")
        trades_match = list(ib.trades())

    for trade in trades_match:
        print()
        print("=" * 70)
        print(f"trade.order.orderId = {trade.order.orderId}")
        print(f"trade.contract = {trade.contract}")
        print(f"trade.orderStatus.status     = {trade.orderStatus.status!r}")
        print(f"trade.orderStatus.whyHeld    = {trade.orderStatus.whyHeld!r}")
        print(f"trade.orderStatus.permId     = {trade.orderStatus.permId}")
        print(f"trade.advancedError          = {trade.advancedError!r}")
        print(f"trade.log entries: {len(trade.log)}")
        for i, entry in enumerate(trade.log):
            print(f"  [{i}] time={entry.time.isoformat() if entry.time else None}")
            print(f"      status   = {entry.status!r}")
            print(f"      errorCode= {getattr(entry, 'errorCode', '<missing>')!r}")
            print(f"      message  = {entry.message!r}")
        print("=" * 70)

    await broker.disconnect()
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
