"""Refresh an EODHD daily-bar parquet for a single instrument.

Operationalises [ADR-014](../docs/decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction)
+ [ADR-017](../docs/decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing)
for the M2-IB.5 paper run: CAC.PA market data comes from EODHD (operator's
All-in-One subscription), order execution stays on IB Paper. The two paths
are independent thanks to the ``MarketDataPort`` / ``BrokerPort`` split.

Schema produced (matches :class:`blive.adapters.paper.market_data.PaperMarketData`
per ADR-029):

    open_time_utc   datetime64[ns, UTC]
    close_time_utc  datetime64[ns, UTC]
    open            float64
    high            float64
    low             float64
    close           float64
    volume          int64
    adjusted_close  float64    (optional; EODHD ships it; we keep it)

For daily bars on European venues, ``open_time_utc`` and ``close_time_utc``
are synthesised at fixed UTC offsets per the convention in
:meth:`run_paper_pipeline` (default rebalance close at 15:30 UTC); this
matches existing PaperMarketData fixtures.

Usage:

    uv run python scripts/refresh_eodhd_parquet.py
    uv run python scripts/refresh_eodhd_parquet.py --ticker CAC.PA --from 2024-01-01

Defaults: ticker=CAC.PA, from=2y ago, to=today, out=~/.blive/data/eodhd/{ticker}_1d.parquet.

Exit codes:
    0  success
    2  credentials missing / invalid
    3  HTTP / API error
    4  empty response (no rows in the requested range)
    5  validation failure (schema / parquet write)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from blive.adapters.shared.credentials import (
    CredentialField,
    CredentialSchema,
    CredentialsMissing,
    load_credentials,
)

# --- EODHD schema -----------------------------------------------------------

_EODHD_SCHEMA = CredentialSchema(
    broker_name="eodhd",
    fields=(CredentialField(name="EODHD_API_KEY", required=True, secret=True),),
)


# --- Bar synthesis convention -----------------------------------------------
#
# Daily bars don't have intraday timestamps in EODHD's response (the venue's
# session-open / session-close are implicit). To match the format
# `PaperMarketData` consumes — which the M1 paper pipeline uses
# `bar.close_time_utc` as the rebalance moment — we synthesise consistent
# UTC times. 09:00 UTC for open, 15:30 UTC for close: the latter is the
# default `rebalance_close_time` in `run_paper_pipeline`. Both are
# *approximate* (Euronext Paris opens 07:00 UTC summer / 08:00 UTC winter,
# closes 15:30 UTC summer / 16:30 UTC winter — daylight-saving variance is
# absorbed into the convention).

_OPEN_TIME_UTC = time(9, 0, tzinfo=timezone.utc)
_CLOSE_TIME_UTC = time(15, 30, tzinfo=timezone.utc)


# --- Default paths ----------------------------------------------------------


def _default_out_path(ticker: str) -> Path:
    return Path.home() / ".blive" / "data" / "eodhd" / f"{ticker}_1d.parquet"


# --- HTTP fetch -------------------------------------------------------------


def _fetch_eod(
    *,
    ticker: str,
    api_key: str,
    start: date,
    end: date,
    timeout_s: float = 30.0,
) -> list[dict[str, Any]]:
    """Call EODHD's `/api/eod/{ticker}` and return the parsed JSON rows.

    EODHD response is a JSON array of dicts with keys:
    ``date, open, high, low, close, adjusted_close, volume``.
    """
    url = f"https://eodhd.com/api/eod/{ticker}"
    params: dict[str, Any] = {
        "api_token": api_key,
        "fmt": "json",
        "from": start.isoformat(),
        "to": end.isoformat(),
    }
    with httpx.Client(timeout=timeout_s) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, list):
        raise ValueError(
            f"EODHD response was not a JSON array (got {type(body).__name__}): "
            f"{body if isinstance(body, dict) else '...'}"
        )
    return body


# --- Frame conversion -------------------------------------------------------


def _rows_to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert the parsed EODHD response to the PaperMarketData parquet schema.

    Drops rows missing any of the required OHLCV fields with a warning.
    """
    if not rows:
        return pd.DataFrame(
            columns=[
                "open_time_utc",
                "close_time_utc",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adjusted_close",
            ]
        )
    raw = pd.DataFrame(rows)
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(
            f"EODHD response missing required field(s) {sorted(missing)}; "
            f"got columns {sorted(raw.columns)}"
        )
    raw["date"] = pd.to_datetime(raw["date"], utc=True).dt.date
    raw = raw.dropna(subset=["open", "high", "low", "close", "volume"])
    open_dt = pd.to_datetime([datetime.combine(d, _OPEN_TIME_UTC) for d in raw["date"]], utc=True)
    close_dt = pd.to_datetime([datetime.combine(d, _CLOSE_TIME_UTC) for d in raw["date"]], utc=True)
    out = pd.DataFrame(
        {
            "open_time_utc": open_dt,
            "close_time_utc": close_dt,
            "open": raw["open"].astype(float).values,
            "high": raw["high"].astype(float).values,
            "low": raw["low"].astype(float).values,
            "close": raw["close"].astype(float).values,
            "volume": raw["volume"].astype("int64").values,
        }
    )
    if "adjusted_close" in raw.columns:
        out["adjusted_close"] = raw["adjusted_close"].astype(float).values
    out = out.sort_values("open_time_utc").reset_index(drop=True)
    return out


# --- CLI --------------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh an EODHD daily-bar parquet (PaperMarketData fixture format).",
    )
    parser.add_argument(
        "--ticker",
        default="CAC.PA",
        help="EODHD ticker including exchange suffix (default: CAC.PA — Phase 1 per ADR-021).",
    )
    today = date.today()
    parser.add_argument(
        "--from",
        dest="from_date",
        default=(today - timedelta(days=730)).isoformat(),
        help="Start date YYYY-MM-DD (inclusive). Default: 730 days before today.",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        default=today.isoformat(),
        help="End date YYYY-MM-DD (inclusive). Default: today.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output parquet path. Default: ~/.blive/data/eodhd/{ticker}_1d.parquet "
            "(parents created on demand)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + parse but do not write the parquet. Prints summary only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    print(f"=== EODHD refresh ({args.ticker}) ===")

    # Credentials.
    try:
        creds = load_credentials(_EODHD_SCHEMA)
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    api_key = creds["EODHD_API_KEY"]
    if api_key == "replace-with-your-eodhd-api-key":
        print(
            "\nFAILED: EODHD_API_KEY is still the template placeholder. "
            "Edit ~/.blive/secrets/eodhd.env or set the env var."
        )
        return 2

    # Date parsing.
    try:
        start = date.fromisoformat(args.from_date)
        end = date.fromisoformat(args.to_date)
    except ValueError as exc:
        print(f"\nFAILED: invalid date -- {exc}")
        return 2
    if start > end:
        print(f"\nFAILED: --from ({start}) is after --to ({end})")
        return 2

    print(f"  - ticker={args.ticker}  range={start.isoformat()}..{end.isoformat()}")

    # Fetch.
    try:
        rows = _fetch_eod(ticker=args.ticker, api_key=api_key, start=start, end=end)
    except httpx.HTTPStatusError as exc:
        print(f"\nFAILED on EODHD HTTP {exc.response.status_code}: {exc.response.text[:200]}")
        return 3
    except httpx.HTTPError as exc:
        print(f"\nFAILED on EODHD network error: {exc}")
        return 3

    print(f"  - EODHD returned {len(rows)} row(s)")

    if not rows:
        print(
            "\nFAILED: EODHD returned zero rows. Possible causes: "
            "ticker symbol wrong, range outside subscription coverage, "
            "or the venue had no trading days in the range."
        )
        return 4

    # Convert.
    try:
        df = _rows_to_frame(rows)
    except (ValueError, KeyError) as exc:
        print(f"\nFAILED on response parse: {exc}")
        return 5
    if df.empty:
        print("\nFAILED: all rows were dropped during validation (missing OHLCV fields).")
        return 4

    out_path = args.out if args.out is not None else _default_out_path(args.ticker)

    if args.dry_run:
        print(
            f"  - dry-run: parsed {len(df)} bar(s); first={df['open_time_utc'].iloc[0]}, "
            f"last={df['close_time_utc'].iloc[-1]}; would write {out_path}"
        )
        print("\nOK (dry-run)")
        return 0

    # Write.
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
    except (OSError, ValueError) as exc:
        print(f"\nFAILED on parquet write: {exc}")
        return 5

    size_kb = out_path.stat().st_size / 1024
    print(
        f"  - wrote {len(df)} bar(s) to {out_path} ({size_kb:.1f} KB); "
        f"first close={df['close_time_utc'].iloc[0]}, "
        f"last close={df['close_time_utc'].iloc[-1]}"
    )

    # Round-trip validation: read back via PaperMarketData's loader to confirm
    # the schema matches what the pipeline expects.
    try:
        from blive.adapters.paper.market_data import _read_fixture  # noqa: SLF001

        _read_fixture(out_path)
    except Exception as exc:  # noqa: BLE001 — defensive validation
        print(f"\nWARNING: parquet written but PaperMarketData rejected it: {exc}")
        return 5

    print("\nOK -- parquet validated against PaperMarketData schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
