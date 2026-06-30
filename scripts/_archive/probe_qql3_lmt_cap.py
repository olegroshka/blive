"""Single-shot LMT confirmation for IB warning 2161 cap binding.

The 5%-offset LMT path in :mod:`scripts.run_m2ib6_ib_paper` cannot
cleanly answer the "does LMT bypass the cap" question because the
strategy uses EODHD close * 1.05 as the limit price, and the EODHD
QQL3 close (~$380) is roughly 10× IB's actual reference (~$39 — the
ETP probably had a recent reverse split or EODHD reports in different
units; flagged in INV-14 v0.7 changelog as M7 parity work). At a 10×-too-high
limit, IB rejects with error 110 ("price does not conform to allowed
range") before ever evaluating 2161.

This probe submits **one** LMT BUY for 1 share of QQL3 at $50 — well
above IB's live reference (~$39) but within the allowed-range
envelope, so error 110 won't pre-empt 2161. Two outcomes that close
the investigation:

1. **2161 fires + cap binds**: order goes ACCEPTED with
   ``mktCapPrice ≈ live_bid``. With our LMT at $50 vs cap at $39ish,
   we see capped-LMT no-fill behaviour identical to MKT/ADAPTIVE_MKT
   — confirming **the cap binds across all retail-account order types**
   on this leveraged ETP. M2-IB.6 close path: accept the constraint.
2. **No 2161, fills cleanly**: LMT bypasses the regulatory cap
   somehow. Operationally interesting; would change recommended order
   type for the QQL3 leg.

Read-only against IB Paper. Produces a single QQL3 BUY at most $50;
won't fill above $50 (well below the $50 ceiling vs IB ref of $39 means
it COULD fill if no cap; with cap, won't).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

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

# QQL3 on LSEETF in USD per ADR-047 + ADR-048-PROPOSED (the SMART/LSEETF
# discriminator is in IBInstrumentResolver as of `c34267d`).
_QQL3 = Instrument(
    symbol="QQL3",
    venue="XLON",
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
    await asyncio.wait_for(broker._events.get(), timeout=2.0)  # noqa: SLF001

    cid = ClientOrderId(uuid4())
    order = Order(
        client_order_id=cid,
        strategy_id="probe-qql3-lmt-cap",
        instrument=_QQL3,
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        # $50: well above IB's QQL3 reference (~$39), within allowed-range
        # envelope (so error 110 doesn't fire), high enough that any
        # honest fill happens significantly below this ceiling.
        limit_price=Decimal("50.00"),
        stop_price=None,
        parent_id=None,
        tags={"probe": "qql3-lmt-cap"},
        created_at=datetime.now(tz=timezone.utc),
    )

    await broker.submit(order)
    print(f"submitted LMT BUY 1 QQL3 @ $50.00  client_order_id={str(cid)[:8]}...")

    # Drain events for ~15 seconds; covers SUBMITTED + ACCEPTED + (maybe) FILLED
    # or 2161 capping.
    deadline = asyncio.get_event_loop().time() + 15.0
    saw_terminal = False
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
        if event.kind in {OrderEventKind.FILLED, OrderEventKind.CANCELED, OrderEventKind.REJECTED}:
            saw_terminal = True
            break

    # Look up the underlying ib_async.Trade and inspect cap + log entries.
    ib = client._ib  # noqa: SLF001
    print()
    print("=" * 70)
    for trade in ib.trades():
        if trade.contract.symbol == "QQL3":
            print(f"trade.order.orderId        = {trade.order.orderId}")
            print(f"trade.contract             = {trade.contract}")
            print(f"trade.orderStatus.status   = {trade.orderStatus.status!r}")
            print(f"trade.orderStatus.mktCapPrice = {trade.orderStatus.mktCapPrice}")
            print(f"trade.orderStatus.lastFillPrice = {trade.orderStatus.lastFillPrice}")
            print(f"trade.orderStatus.filled   = {trade.orderStatus.filled}")
            print(f"trade.orderStatus.whyHeld  = {trade.orderStatus.whyHeld!r}")
            print(f"trade.log entries: {len(trade.log)}")
            for i, entry in enumerate(trade.log):
                print(
                    f"  [{i}] status={entry.status!r}  errorCode={getattr(entry, 'errorCode', '<missing>')}"
                )
                if entry.message:
                    print(f"       message: {entry.message[:300]}")
    print("=" * 70)

    # If still active, cancel.
    if not saw_terminal:
        try:
            await broker.cancel(cid)
            print("(cancel issued because we hit the wait timeout without terminal)")
        except Exception as exc:  # noqa: BLE001
            print(f"(cancel raised: {exc})")
        await asyncio.sleep(2)

    await broker.disconnect()
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
