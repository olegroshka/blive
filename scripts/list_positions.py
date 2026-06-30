"""Quick script to list all positions with estimated market values."""
import asyncio
import sys
sys.path.insert(0, 'src')

from blive.adapters.ib import IBClient, IBCredentials, IB_DEFAULT_RATE_LIMITS
from blive.adapters.ib.broker import IBBroker
from blive.adapters.clock.wall import WallClock
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter


async def main():
    creds = IBCredentials.load()
    clock = WallClock()
    rl = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=creds, rate_limiter=rl, clock=clock)
    from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)
    await broker.connect()

    positions = await broker.positions()
    snap = await broker.account_snapshot()

    print(f"\nAccount: {creds.account_id}  |  Base: {snap.base_currency}")
    print(f"Equity:        {snap.base_currency} {float(snap.equity):>12,.2f}")
    print(f"Cash:          {snap.cash_by_ccy}")
    print(f"Gross Exposure:{snap.base_currency} {float(snap.gross_exposure):>12,.2f}")
    print()
    print(f"{'Ticker':<8}  {'Exchange':<8}  {'Qty':>10}  {'Avg Cost':>12}  {'Est. Value':>12}")
    print("-" * 58)

    total_long = 0.0
    total_short = 0.0
    for p in sorted(positions, key=lambda x: x.instrument.symbol):
        qty = float(p.quantity)
        cost = float(p.avg_cost)
        mv = qty * cost
        if qty >= 0:
            total_long += mv
        else:
            total_short += mv
        exch = p.instrument.venue or ""
        print(f"{p.instrument.symbol:<8}  {exch:<8}  {qty:>10.2f}  {cost:>12.4f}  {mv:>12.2f}")

    print("-" * 58)
    print(f"{'Long value':<30}  {total_long:>12,.2f}")
    print(f"{'Short value':<30}  {total_short:>12,.2f}")
    print(f"{'Net value':<30}  {total_long + total_short:>12,.2f}")

    await broker.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
