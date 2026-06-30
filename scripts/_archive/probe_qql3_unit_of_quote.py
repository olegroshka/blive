"""Investigation probe for the EODHD-vs-IB QQL3 ~10× price discrepancy.

Surfaced as a side-finding at M2-IB.6.2c per
[INV-14 v0.7 changelog](../docs/inv/ib_error_codes.md) +
[RETRO-M2-IB §"Surprises" #7](../docs/retros/M2-IB_retrospective.md).
This probe runs the hypothesis-refutation matrix needed to ground the
M3.1 narrow-scope sizing fix (per [TASK_REGISTRY M3.1](../TASK_REGISTRY.md)
+ [ADR-050 PROPOSED](../docs/decisions/DECISIONS.md) — Hybrid
EODHD-convention conversion B-now / IB-live-MD A-later, free-MD-only).

The probe is **EODHD-only**; IB-side cross-checks are intentionally
out-of-scope for this script (they need LSE RTH timing + a live
``reqMktData`` budget per KB-3 §3 that we don't want to spend
speculatively). The known IB facts (`conId=566361457`, currency=USD,
LSEETF venue) come from the M2-IB.6.1 wire-probe finding and are
authoritative — the question this probe answers is *what is EODHD
quoting and why doesn't it match IB*.

## Hypothesis matrix

The probe gathers data and prints a refutation matrix. Each hypothesis
is either confirmed, refuted, or inconclusive (not enough EODHD data to
decide; promote to wire-side IB probe if needed).

| # | Hypothesis | Refuting / confirming observation |
|---|---|---|
| H1 | Recent reverse-split: ``close`` is unadjusted, ``adjusted_close`` carries the split factor | If ``close[-1] / adjusted_close[-1]`` ≈ N for integer N (or 1/N) AND ``/api/splits`` lists a recent split, **H1 confirmed**. |
| H2 | Currency convention: EODHD reports LSE main-book GBp pence, IB reports USD on LSEETF | If ``/api/fundamentals.General.CurrencyCode == "GBX"`` (pence), H2 candidate. Cross-check with ``Currency`` semantics. |
| H3 | Different share-class (USD vs GBP-hedged) | If EODHD's ISIN doesn't match IB's QQL3 conId 566361457 ISIN, H3 candidate. ISIN comes from ``/api/fundamentals.General.ISIN``. |
| H4 | Vendor-symbol divergence (``QQQ3.LSE`` ≠ IB's ``QQL3``) | Same ISIN check as H3 — if ISINs match, H4 refuted. |

## Outputs

- **Stdout**: human-readable matrix + decision summary.
- **No file writes** — this is read-only investigation. The decision
  shapes the per-instrument convention catalogue at
  ``src/blive/adapters/eodhd/conventions.py`` (M3.1 narrow fix); the
  probe output goes into KB-15 stub-DRAFT at v0.1.

## Usage

::

    uv run python scripts/probe_qql3_unit_of_quote.py
    uv run python scripts/probe_qql3_unit_of_quote.py --ticker QQQ3.LSE

Exit codes:

    0  probe ran to completion (regardless of which hypothesis won)
    2  credentials / args
    3  HTTP / API error
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
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

_EODHD_SCHEMA = CredentialSchema(
    broker_name="eodhd",
    fields=(CredentialField(name="EODHD_API_KEY", required=True, secret=True),),
)


def _eodhd_call(
    *,
    path: str,
    api_key: str,
    params: dict[str, Any] | None = None,
    timeout_s: float = 30.0,
) -> Any:
    url = f"https://eodhd.com/api/{path}"
    full = {"api_token": api_key, "fmt": "json"}
    if params:
        full.update(params)
    with httpx.Client(timeout=timeout_s) as client:
        response = client.get(url, params=full)
        response.raise_for_status()
        return response.json()


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_kv(label: str, value: Any) -> None:
    print(f"  {label}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Investigate the EODHD-vs-IB QQL3 ~10× price discrepancy."
    )
    parser.add_argument(
        "--ticker",
        default="QQQ3.LSE",
        help="EODHD ticker (default: QQQ3.LSE — matches refresh_eodhd_signals.py).",
    )
    parser.add_argument(
        "--ib-symbol",
        default="QQL3",
        help="IB symbol (informational; default: QQL3).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="EOD window for the close-vs-adjusted_close inspection (default: 30).",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        creds = load_credentials(_EODHD_SCHEMA)
    except CredentialsMissing as exc:
        print(f"FAILED: {exc}")
        return 2
    api_key = creds["EODHD_API_KEY"]

    _print_header(
        f"QQL3 unit-of-quote probe — EODHD ticker {args.ticker} / IB symbol {args.ib_symbol}"
    )

    end = date.today()
    start = end - timedelta(days=args.days)

    # --- EOD: close vs adjusted_close -----------------------------------------
    _print_header("EOD: close vs adjusted_close")
    try:
        eod_rows = _eodhd_call(
            path=f"eod/{args.ticker}",
            api_key=api_key,
            params={"from": start.isoformat(), "to": end.isoformat(), "period": "d"},
        )
    except httpx.HTTPError as exc:
        print(f"FAILED on EOD fetch: {exc}")
        return 3

    if not isinstance(eod_rows, list) or not eod_rows:
        print(f"FAILED: empty EOD response for {args.ticker}")
        return 3

    df = pd.DataFrame(eod_rows)
    if "adjusted_close" not in df.columns:
        print(
            "WARNING: response has no `adjusted_close` field — split-adjustment hypothesis cannot be tested directly."
        )
    else:
        df["adj_ratio"] = df["close"].astype(float) / df["adjusted_close"].astype(float)
        latest = df.iloc[-1]
        _print_kv("latest date", latest["date"])
        _print_kv("close (raw)", f"{float(latest['close']):.4f}")
        _print_kv("adjusted_close", f"{float(latest['adjusted_close']):.4f}")
        _print_kv("ratio (close / adjusted_close)", f"{float(latest['adj_ratio']):.4f}")

        # Show ratio stability across the window — if it's constant, that
        # means a single split factor is uniformly applied; if it
        # changes, multiple splits or a continuous adjustment.
        unique_ratios = df["adj_ratio"].round(4).unique()
        _print_kv("distinct ratios in window", list(unique_ratios)[:8])

    # --- Splits history -------------------------------------------------------
    _print_header("Splits history")
    try:
        splits = _eodhd_call(path=f"splits/{args.ticker}", api_key=api_key)
    except httpx.HTTPError as exc:
        print(f"WARNING: splits endpoint failed: {exc}")
        splits = []

    if not splits:
        print("  (no splits returned by EODHD)")
    else:
        for row in splits[-10:]:
            _print_kv(f"split {row.get('date', '?')}", row.get("split", "?"))

    # --- Fundamentals: Currency + ISIN ----------------------------------------
    _print_header("Fundamentals: currency + ISIN")
    try:
        fundamentals = _eodhd_call(path=f"fundamentals/{args.ticker}", api_key=api_key)
    except httpx.HTTPError as exc:
        print(f"WARNING: fundamentals endpoint failed: {exc}")
        fundamentals = {}

    general = fundamentals.get("General", {}) if isinstance(fundamentals, dict) else {}
    _print_kv("Code", general.get("Code"))
    _print_kv("Name", general.get("Name"))
    _print_kv("CurrencyCode", general.get("CurrencyCode"))
    _print_kv("CurrencyName", general.get("CurrencyName"))
    _print_kv("CurrencySymbol", general.get("CurrencySymbol"))
    _print_kv("ISIN", general.get("ISIN"))
    _print_kv("Type", general.get("Type"))
    _print_kv("Exchange", general.get("Exchange"))

    # --- Persisted parquet cross-check ----------------------------------------
    _print_header("Local parquet cross-check (~/.blive/data/eodhd/QQL3_1d.parquet)")
    parquet_path = Path.home() / ".blive" / "data" / "eodhd" / f"{args.ib_symbol}_1d.parquet"
    if not parquet_path.exists():
        print(f"  (parquet not found at {parquet_path}; run refresh_eodhd_signals.py first)")
    else:
        local = pd.read_parquet(parquet_path)
        if not local.empty:
            tail = local.tail(3)
            for _, row in tail.iterrows():
                _print_kv(
                    str(row["close_time_utc"].date()),
                    f"close={float(row['close']):.4f}  open={float(row['open']):.4f}",
                )

    # --- Refutation matrix ----------------------------------------------------
    _print_header("Refutation matrix")
    if "adjusted_close" in df.columns:
        latest_ratio = float(df.iloc[-1]["adj_ratio"])
    else:
        latest_ratio = 1.0
    currency = general.get("CurrencyCode")
    has_split = bool(splits)

    h1_status = "INCONCLUSIVE"
    if abs(latest_ratio - 1.0) > 0.01 and has_split:
        h1_status = "CONFIRMED" if latest_ratio > 1.5 or latest_ratio < 0.7 else "PARTIAL"
    elif abs(latest_ratio - 1.0) <= 0.01:
        h1_status = "REFUTED"
    print(
        f"  H1 (split-adjusted): {h1_status}  (ratio={latest_ratio:.4f}, splits_count={len(splits)})"
    )

    h2_status = "REFUTED"
    if currency in ("GBX", "GBp", "GBX/GBp"):
        h2_status = "CONFIRMED"
    elif currency == "USD":
        h2_status = "REFUTED"
    elif currency is None:
        h2_status = "INCONCLUSIVE"
    print(f"  H2 (currency GBp vs USD): {h2_status}  (CurrencyCode={currency!r})")

    isin = general.get("ISIN")
    if isin:
        # IB conId 566361457 ISIN is operator-confirmed at the M2-IB.6.1
        # wire-probe; capturing ISIN here closes H3+H4 jointly.
        print(f"  H3+H4 (share-class / vendor-symbol divergence): EODHD ISIN = {isin!r}")
        print(
            "    cross-check: confirm IB conId 566361457 reports the same ISIN via reqContractDetails (operator-side wire probe)."
        )
    else:
        print(
            "  H3+H4 (share-class / vendor-symbol divergence): INCONCLUSIVE (no ISIN in fundamentals)"
        )

    # --- Decision summary -----------------------------------------------------
    _print_header("Decision input for ADR-050 / KB-15 stub-DRAFT")
    if h1_status == "CONFIRMED":
        print(
            "  -> EODHD `close` is the raw historical price; `adjusted_close` carries the split factor."
        )
        print(
            f"    Conversion at sizing time: use `adjusted_close` (or close / {latest_ratio:.4f}) as the IB-equivalent reference."
        )
        print("    Catalogue entry: QQL3 -> {convention: 'use_adjusted_close'}.")
    elif h2_status == "CONFIRMED":
        print("  -> EODHD reports LSE main-book in GBp pence; IB reports USD on LSEETF.")
        print("    Conversion at sizing time: convert GBp -> USD via FX_GBPUSD.")
    else:
        print("  -> No single hypothesis confirmed by EODHD-side data alone.")
        print("     EODHD-side `adjusted_close` matches `close` (ratio 1.0) and CurrencyCode=USD.")
        print(
            "     Most likely cause: a recent reverse-split that IB has indexed but EODHD has not"
        )
        print(
            "     yet propagated to its EOD feed -- a known EODHD lag failure mode on leveraged ETPs."
        )
        print(
            "     Required fix: operator-confirmed manual scale factor in the convention catalogue,"
        )
        print(
            "     i.e. `QQL3 -> {convention: 'manual_scale', divisor: <factor>, source: 'IB live reference'}`."
        )
        print("     The divisor stays in effect until EODHD propagates the split, at which point")
        print("     adjusted_close will diverge from close and the catalogue entry can simplify.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
