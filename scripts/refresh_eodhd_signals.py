"""Refresh the M2-IB.6 EODHD data + SMA-eligibility signals parquet.

Operationalises [ADR-043](../docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)'s
Phase 1 strategy `triple_lev_sma_filter_dsl`, with the universe substituted
for UK-listed PRIIPs-compliant analogues per
[ADR-047](../docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043).
Fetches the 5 tickers it needs (3 tradables + 2 trend signals) from EODHD
and writes:

1. **5 PaperMarketData parquets** — one per IB symbol — at
   ``~/.blive/data/eodhd/{ib_symbol}_1d.parquet``, matching the format
   :class:`blive.adapters.paper.market_data.PaperMarketData` consumes
   per [ADR-029](../docs/decisions/DECISIONS.md#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet).
   File names use the IB symbol (no `.LSE` suffix); EODHD is fetched with
   the `.LSE` suffix where applicable.
2. **One wide eligibility-signals parquet** at
   ``~/.blive/data/signals/triple_lev_sma_eligible.parquet`` —
   columns ``QQL3`` / ``IBTL`` / ``IBTM`` (the IB symbols of the Phase 1
   tradable legs) with float ``0.0`` / ``1.0`` values, derived from the
   QQQ / TLT trend signals via
   :func:`blive.runtime.signals.triple_lev_sma_eligibility`. The
   eligibility function natively returns columns labelled by the
   notebook's original tradables (TQQQ / TMF / IEF); the driver renames
   them to the IB symbols before persisting so downstream consumers
   (driver + tests) reference instruments by their IB symbol throughout.

Five tickers fetched:

- **QQL3.LSE** — 3× Nasdaq-100 leveraged ETP (LSE; tradable; TQQQ analogue).
- **IBTL.LSE** — iShares $ Treasury 20+yr UCITS ETF (LSE; **1× not 3×**;
  tradable; TMF analogue — there is no UK-listed 3× US-Treasury ETP, so
  the leg's effective leverage drops 3×→1×; the strategy's regime profile
  shifts accordingly per ADR-047).
- **IBTM.LSE** — iShares $ Treasury 7-10yr UCITS ETF (LSE; tradable; IEF
  analogue).
- **QQQ** — Nasdaq-100 ETF (US; trend signal for the TQQQ-analogue leg
  only; signal-only consumption — never traded — so PRIIPs / KID does
  not apply).
- **TLT** — 20+y Treasury ETF (US; trend signal for the TMF-analogue leg
  only; signal-only).

Usage::

    uv run python scripts/refresh_eodhd_signals.py
    uv run python scripts/refresh_eodhd_signals.py --from 2024-01-01 --to 2026-05-02

Defaults: from=730 days before today, to=today. Fetches in series (5
sequential EODHD calls; no parallelism since EODHD's rate limit is
generous and parallelism complicates error reporting).

Prereqs: ``EODHD_API_KEY`` populated in ``~/.blive/secrets/eodhd.env``
or as an environment variable, per [ADR-035](../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).

Exit codes:

    0  success — all 5 parquets + the signals parquet written and
       schema-validated
    2  credentials / args / file-not-found
    3  HTTP / API error (which ticker is named in the message)
    4  one or more empty responses (no rows in the requested range)
    5  validation failure (schema / parquet write / signal computation)
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
from blive.runtime.signals import triple_lev_sma_eligibility

# --- EODHD schema (mirrors refresh_eodhd_parquet.py — kept local to avoid -----
# --- a scripts/-package import dance; eventually consolidates into a real    --
# --- src/blive/adapters/eodhd/ module when EODHDDataSource lands per ADR-014) -

_EODHD_SCHEMA = CredentialSchema(
    broker_name="eodhd",
    fields=(CredentialField(name="EODHD_API_KEY", required=True, secret=True),),
)


# --- Bar synthesis convention -----------------------------------------------
#
# Match scripts/refresh_eodhd_parquet.py's convention exactly so the
# parquets produced here are interchangeable with single-ticker refresh
# output. Daily bars at 09:00 UTC (proxy market open) → 15:30 UTC (proxy
# market close; matches the default rebalance_close_time in
# `run_paper_pipeline`). Both are nominal; the close_time_utc is the
# load-bearing field for rebalance triggering.

_OPEN_TIME_UTC = time(9, 0, tzinfo=timezone.utc)
_CLOSE_TIME_UTC = time(15, 30, tzinfo=timezone.utc)


# --- M2-IB.6 ticker set per ADR-043 + ADR-047 -------------------------------
#
# Three tradables + two trend signals. Order matters for output stability
# (PaperMarketData parquets get written in this order; signals parquet
# always has columns in IB-symbol order: QQL3 / IBTL / IBTM).
#
# Tradables are UK-listed UCITS / ETP analogues per ADR-047 (the original
# notebook's TQQQ / TMF / IEF are PRIIPs-blocked from UK retail accounts;
# error 201 KID-variant catalogued in INV-14 v0.5). EODHD ticker uses the
# `.LSE` suffix; the IB symbol used by IBInstrumentResolver, the
# parquet filename, and the eligibility column header is the bare symbol
# (no suffix). Trend signals (QQQ / TLT) remain US-listed — they are
# signal-only consumption, never traded, so PRIIPs does not apply.

# EODHD ticker -> IB symbol. Order is load-bearing: matches the canonical
# eligibility column order (QQL3 [3x QQQ analogue], IBTL [TLT/TMF analogue
# at 1x], IBTM [IEF analogue]).
_TRADABLE_EODHD_TO_IB: dict[str, str] = {
    "QQL3.LSE": "QQL3",
    "IBTL.LSE": "IBTL",
    "IBTM.LSE": "IBTM",
}
_TRADABLE_EODHD: tuple[str, ...] = tuple(_TRADABLE_EODHD_TO_IB.keys())
_TRADABLE_IB: tuple[str, ...] = tuple(_TRADABLE_EODHD_TO_IB.values())
_TREND_SIGNALS: tuple[str, ...] = ("QQQ", "TLT")
_ALL_EODHD_TICKERS: tuple[str, ...] = _TRADABLE_EODHD + _TREND_SIGNALS

# Rename map applied to the eligibility frame returned by
# triple_lev_sma_eligibility — its native column labels are the notebook's
# original tradables (TQQQ / TMF / IEF). Persisted parquet uses IB symbols
# so the driver and downstream tooling reference instruments by IB symbol
# end-to-end.
_ELIGIBILITY_COLUMN_RENAME: dict[str, str] = {
    "TQQQ": "QQL3",
    "TMF": "IBTL",
    "IEF": "IBTM",
}


def _eodhd_to_ib_symbol(eodhd_ticker: str) -> str:
    """Map an EODHD ticker (with optional venue suffix) to the IB symbol used
    for parquet filenames and instrument records. Trend-signal tickers
    (QQQ / TLT) have no suffix — return them unchanged.
    """
    return _TRADABLE_EODHD_TO_IB.get(eodhd_ticker, eodhd_ticker)


# --- Default paths ----------------------------------------------------------


def _default_eodhd_dir() -> Path:
    return Path.home() / ".blive" / "data" / "eodhd"


def _default_signals_path() -> Path:
    return Path.home() / ".blive" / "data" / "signals" / "triple_lev_sma_eligible.parquet"


# --- HTTP fetch (small duplicate of refresh_eodhd_parquet._fetch_eod) --------


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

    Raises :class:`httpx.HTTPStatusError` on HTTP 4xx / 5xx (caller logs
    + exits 3); :class:`ValueError` if the response isn't a JSON array.
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
            f"EODHD response for {ticker!r} was not a JSON array (got {type(body).__name__})"
        )
    return body


def _rows_to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert the parsed EODHD response to the PaperMarketData parquet schema.

    Matches scripts/refresh_eodhd_parquet.py exactly. Drops rows missing
    any required OHLCV field with a soft error; raises only on
    structural problems (missing columns).
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
        description=(
            "Refresh the 5 EODHD ticker parquets (QQL3.LSE/IBTL.LSE/IBTM.LSE/"
            "QQQ/TLT) + the SMA-eligibility signals parquet for "
            "triple_lev_sma_filter_dsl (Phase 1 PRIIPs-compliant universe per "
            "ADR-047)."
        ),
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
        "--eodhd-dir",
        type=Path,
        default=None,
        help=(
            "Output directory for the per-ticker daily parquets. " "Default: ~/.blive/data/eodhd/"
        ),
    )
    parser.add_argument(
        "--signals-path",
        type=Path,
        default=None,
        help=(
            "Output path for the wide SMA-eligibility parquet. "
            "Default: ~/.blive/data/signals/triple_lev_sma_eligible.parquet"
        ),
    )
    parser.add_argument(
        "--sma-window",
        type=int,
        default=200,
        help="SMA window (default: 200; matches the notebook).",
    )
    parser.add_argument(
        "--enter-buffer",
        type=float,
        default=0.05,
        help="Hysteresis re-entry buffer (default: 0.05 = 5%%; matches the notebook).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + compute but do not write anything. Prints summary only.",
    )
    return parser.parse_args(argv)


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"  - {label}{suffix}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    _print_header("EODHD M2-IB.6 refresh (5 tickers + signals)")

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

    print(f"  range: {start.isoformat()} .. {end.isoformat()}")
    print(f"  tickers (EODHD): {', '.join(_ALL_EODHD_TICKERS)}")
    print(f"  tradable IB symbols: {', '.join(_TRADABLE_IB)}")
    print(f"  SMA window: {args.sma_window}, enter_buffer: {args.enter_buffer}")

    # Fetch + parse all 5 tickers up-front so a single failure aborts before
    # any partial writes. Frames are keyed by the IB symbol — the EODHD
    # `.LSE` suffix is fetch-time only.
    frames: dict[str, pd.DataFrame] = {}
    for eodhd_ticker in _ALL_EODHD_TICKERS:
        ib_symbol = _eodhd_to_ib_symbol(eodhd_ticker)
        label = eodhd_ticker if eodhd_ticker == ib_symbol else f"{eodhd_ticker} -> {ib_symbol}"
        _print_step(f"fetching {label}")
        try:
            rows = _fetch_eod(ticker=eodhd_ticker, api_key=api_key, start=start, end=end)
        except httpx.HTTPStatusError as exc:
            print(
                f"\nFAILED on EODHD HTTP {exc.response.status_code} for {eodhd_ticker!r}: "
                f"{exc.response.text[:200]}"
            )
            return 3
        except httpx.HTTPError as exc:
            print(f"\nFAILED on EODHD network error for {eodhd_ticker!r}: {exc}")
            return 3
        if not rows:
            print(
                f"\nFAILED: EODHD returned zero rows for {eodhd_ticker!r}. "
                f"Check ticker / range / subscription coverage."
            )
            return 4
        try:
            df = _rows_to_frame(rows)
        except (ValueError, KeyError) as exc:
            print(f"\nFAILED on response parse for {eodhd_ticker!r}: {exc}")
            return 5
        if df.empty:
            print(f"\nFAILED: all rows dropped during validation for {eodhd_ticker!r}.")
            return 4
        frames[ib_symbol] = df
        print(
            f"    {ib_symbol}: {len(df)} bar(s) "
            f"({df['close_time_utc'].iloc[0].date()} .. {df['close_time_utc'].iloc[-1].date()})"
        )

    # Compute the SMA-eligibility signals from QQQ + TLT closes.
    # Align on the intersection of dates so SMA computation has matched
    # samples (rare for QQQ + TLT to disagree on US calendar, but defensive).
    qqq_df = frames["QQQ"]
    tlt_df = frames["TLT"]
    # Use the close_time_utc Series (not .values) so the tz-aware UTC
    # info is preserved on the index. .values strips tz to numpy
    # datetime64[ns], which makes downstream intersections with
    # tz-aware indices (e.g. canonical bar timestamps in the driver)
    # silently empty.
    qqq_closes = pd.Series(qqq_df["close"].values, index=qqq_df["close_time_utc"], name="QQQ")
    tlt_closes = pd.Series(tlt_df["close"].values, index=tlt_df["close_time_utc"], name="TLT")
    common_idx = qqq_closes.index.intersection(tlt_closes.index)
    qqq_closes = qqq_closes.reindex(common_idx)
    tlt_closes = tlt_closes.reindex(common_idx)
    if len(qqq_closes) < args.sma_window:
        print(
            f"\nFAILED: only {len(qqq_closes)} aligned QQQ+TLT bars; "
            f"need >= {args.sma_window} for the SMA window. "
            f"Extend --from / --to range."
        )
        return 5

    _print_step(
        "computing eligibility",
        f"sma_window={args.sma_window} enter_buffer={args.enter_buffer}",
    )
    try:
        eligibility = triple_lev_sma_eligibility(
            qqq_closes=qqq_closes,
            tlt_closes=tlt_closes,
            sma_window=args.sma_window,
            enter_buffer=args.enter_buffer,
        )
    except ValueError as exc:
        print(f"\nFAILED on signal computation: {exc}")
        return 5

    # Rename eligibility columns from the notebook's original tradables
    # (TQQQ / TMF / IEF) to the IB symbols of the PRIIPs-compliant Phase 1
    # universe (QQL3 / IBTL / IBTM) per ADR-047. The hysteresis state-machine
    # logic is unchanged — only the column labels move with the underlying
    # tradables.
    eligibility = eligibility.rename(columns=_ELIGIBILITY_COLUMN_RENAME)

    qql3_active = int((eligibility["QQL3"] == 1.0).sum())
    ibtl_active = int((eligibility["IBTL"] == 1.0).sum())
    ibtm_active = int((eligibility["IBTM"] == 1.0).sum())
    print(
        f"    eligibility (active days / total {len(eligibility)}): "
        f"QQL3={qql3_active}  IBTL={ibtl_active}  IBTM={ibtm_active}"
    )

    if args.dry_run:
        _print_header("dry-run -- nothing written")
        return 0

    # Write the per-ticker daily parquets. Frames are keyed by IB symbol
    # already (no `.LSE` suffix in filenames) so PaperMarketData's
    # fixture-by-symbol lookup in the driver finds them directly.
    eodhd_dir = args.eodhd_dir if args.eodhd_dir is not None else _default_eodhd_dir()
    eodhd_dir.mkdir(parents=True, exist_ok=True)
    for ib_symbol, df in frames.items():
        out_path = eodhd_dir / f"{ib_symbol}_1d.parquet"
        try:
            df.to_parquet(out_path, index=False)
        except (OSError, ValueError) as exc:
            print(f"\nFAILED on parquet write for {ib_symbol!r}: {exc}")
            return 5
        size_kb = out_path.stat().st_size / 1024
        print(f"    wrote {out_path}  ({size_kb:.1f} KB)")

    # Write the eligibility signals parquet.
    signals_path = args.signals_path if args.signals_path is not None else _default_signals_path()
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        eligibility.to_parquet(signals_path, index=True)
    except (OSError, ValueError) as exc:
        print(f"\nFAILED on signals parquet write: {exc}")
        return 5
    size_kb = signals_path.stat().st_size / 1024
    print(f"    wrote {signals_path}  ({size_kb:.1f} KB)")

    # Round-trip validation: read back via PaperMarketData's loader to confirm
    # the per-ticker parquets match the schema the pipeline expects.
    try:
        from blive.adapters.paper.market_data import _read_fixture  # noqa: SLF001

        for ib_symbol in (*_TRADABLE_IB, *_TREND_SIGNALS):
            _read_fixture(eodhd_dir / f"{ib_symbol}_1d.parquet")
    except Exception as exc:  # noqa: BLE001 — defensive validation
        print(f"\nWARNING: per-ticker parquet(s) written but PaperMarketData rejected one: {exc}")
        return 5

    _print_header("OK -- all 5 ticker parquets + signals parquet validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
