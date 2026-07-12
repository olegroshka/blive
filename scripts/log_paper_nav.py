"""Snapshot the IB paper account NAV into the shared NAV feed.

Writes one row per (book, date) into ``derived_data/nav/paper_nav.csv`` per the
contract in ``derived_data/nav/README.md``. Run daily (idempotent — re-running
the same day overwrites that day's row). This is blive's half of the
theoretical-vs-paper-vs-actual reconciliation: it publishes the *paper* NAV feed;
lab computes *theoretical*; ForgeFolio will publish *actual*.

    uv run python scripts/log_paper_nav.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, "src")

from pathlib import Path

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import IB_DEFAULT_RATE_LIMITS, IBClient, IBCredentials, IBInstrumentResolver
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter

_FEED = Path(__file__).resolve().parents[2] / "lab" / "reporting" / "nav" / "paper_nav.csv"


def _upsert(row: dict) -> None:
    _FEED.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(_FEED) if _FEED.is_file() else pd.DataFrame()
    if not df.empty:
        df = df[~((df["book"] == row["book"]) & (df["date"].astype(str) == row["date"]))]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.sort_values(["book", "date"]).reset_index(drop=True)
    df.to_csv(_FEED, index=False)


async def main() -> int:
    creds = IBCredentials.load()
    clock = WallClock()
    rl = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=creds, rate_limiter=rl, clock=clock)
    broker = IBBroker(client=client, resolver=IBInstrumentResolver(client), clock=clock)
    await broker.connect()
    snap = await broker.account_snapshot()
    await broker.disconnect()

    row = {
        "date": date.today().isoformat(),
        "book": f"PAPER:{creds.account_id}",
        "nav": round(float(snap.equity), 2),
        "gross_exposure": round(float(getattr(snap, "gross_exposure", 0) or 0), 2),
        "ccy": snap.base_currency or "",
        "source": "blive",
    }
    _upsert(row)
    print(f"logged paper NAV -> {_FEED}")
    print(f"  {row['date']}  {row['book']}  {row['ccy']} {row['nav']:,.2f}  (gross {row['gross_exposure']:,.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
