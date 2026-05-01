"""IB broker read-side smoke test.

Manual smoke test that exercises ``IBBroker``'s read methods against
the live IB Paper Gateway:

- ``connect()`` — wire handshake + initial ``reqAccountUpdatesAsync``
  + ``reqPositionsAsync`` + ``reqOpenOrdersAsync`` batch.
- ``positions()`` — what IB thinks we hold.
- ``account_snapshot()`` — equity / cash / leverage / margin built
  from the accumulated ``accountValueEvent`` cache.
- ``open_orders()`` — IB's view of our working orders.
- ``disconnect()`` — clean teardown.

A successful run is the trigger for KB-2 + KB-3 STABLE flips (the
read-side has exercised §1-§9 surfaces against IB Paper). Any errors
populate INV-14 (IB error codes) DRAFT.

Prerequisites — same as :mod:`scripts.probe_ib_handshake` + the M2-IB.3a
prereqs.

Run:

    uv run python scripts/probe_ib_read.py

Exits 0 on success; non-zero with a diagnostic on failure.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
)
from blive.adapters.ib.broker import IBBroker, IBShapeError
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"  - {label}{suffix}")


async def _run_probe() -> int:
    _print_header("IB broker read-side probe")

    # Step 1: load credentials.
    _print_step("loading IBCredentials from ~/.blive/secrets/ib.env / env")
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials value -- {exc}")
        return 2

    print(
        f"    host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} account_id=[REDACTED]"
    )
    if credentials.account_id == "replace-with-your-ib-paper-account-id":
        print("\nFAILED: IB_PAPER_ACCOUNT_ID is still the template placeholder.")
        return 2

    # Step 2: build broker.
    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    # Step 3: connect.
    started_at = datetime.now(tz=timezone.utc)
    _print_step("connecting to IB Paper Gateway")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    print(f"    is_connected={broker.is_connected} (connect+subscribe in {elapsed:.2f}s)")

    # Step 4: positions.
    _print_step("fetching positions (reqPositionsAsync)")
    try:
        positions = await broker.positions()
    except (IBShapeError, RuntimeError) as exc:
        print(f"\nFAILED on positions(): {exc}")
        await broker.disconnect()
        return 4
    print(f"    positions count={len(positions)}")
    for pos in positions[:5]:  # first 5 to keep output bounded
        print(
            f"      {pos.instrument.symbol} ({pos.instrument.venue}/{pos.instrument.currency}) "
            f"qty={pos.quantity} avg_cost={pos.avg_cost} strategy_id={pos.strategy_id}"
        )
    if len(positions) > 5:
        print(f"      ... ({len(positions) - 5} more)")

    # Step 5: account_snapshot.
    _print_step("composing account_snapshot from accountValueEvent cache")
    try:
        snapshot = await broker.account_snapshot()
    except IBShapeError as exc:
        # Account values may not have arrived yet on a slow handshake;
        # wait briefly and retry once.
        print(f"    initial attempt empty ({exc}); waiting 2s for first batch")
        await asyncio.sleep(2.0)
        try:
            snapshot = await broker.account_snapshot()
        except IBShapeError as exc2:
            print(f"\nFAILED on account_snapshot(): {exc2}")
            await broker.disconnect()
            return 5
    print(f"    base_currency={snapshot.base_currency}")
    print(f"    equity={snapshot.equity}")
    print(f"    buying_power={snapshot.buying_power}")
    print(f"    gross_exposure={snapshot.gross_exposure}")
    print(f"    leverage={snapshot.leverage}")
    print(f"    margin_used={snapshot.margin_used}")
    print(f"    cash_by_ccy={dict(snapshot.cash_by_ccy)}")

    # Step 6: open_orders.
    _print_step("fetching open_orders (reqAllOpenOrdersAsync)")
    try:
        open_orders = await broker.open_orders()
    except (IBShapeError, RuntimeError) as exc:
        print(f"\nFAILED on open_orders(): {exc}")
        await broker.disconnect()
        return 6
    print(f"    open_orders count={len(open_orders)}")
    for order in open_orders[:5]:
        print(
            f"      {order.side.value} {order.quantity} {order.instrument.symbol} "
            f"({order.order_type.value}/{order.time_in_force.value}) "
            f"limit={order.limit_price} stop={order.stop_price} "
            f"tags={dict(order.tags)}"
        )
    if len(open_orders) > 5:
        print(f"      ... ({len(open_orders) - 5} more)")

    # Step 7: rate-limiter usage.
    metrics = rate_limiter.metrics()
    global_metrics = metrics["global"]
    print(
        f"    rate_limiter.global available={global_metrics.available:.2f}"
        f"/{global_metrics.capacity} after read calls"
    )

    # Step 8: disconnect.
    _print_step("disconnecting")
    await broker.disconnect()
    print(f"    is_connected={broker.is_connected}")

    _print_header("OK -- read-side surfaces clean")
    print(
        "M2-IB.3b-i wire-level read methods exercised end-to-end against IB "
        "Paper. Paste output to the agent for the substrate-flip commit "
        "(KB-2 / KB-3 STABLE flip pending §1-§9 surface coverage)."
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run_probe())
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
