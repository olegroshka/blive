"""M2-IB.6 multi-instrument paper-test driver — `triple_lev_sma_filter_dsl` on IB Paper.

Operationalises [ADR-043](../docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)
+ [ADR-044](../docs/decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043)
+ [ADR-045](../docs/decisions/DECISIONS.md#adr-045--longshortportfolio-btest-dispatch-extends-adr-030)
+ [ADR-046](../docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032)
+ [ADR-047](../docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)
end-to-end. Wires:

1. **5 EODHD parquets** (QQL3 / IBTL / IBTM / QQQ / TLT) loaded via
   :class:`PaperMarketData`. Three of those are tradables (UK-listed
   PRIIPs-compliant analogues per ADR-047 — the original notebook's
   TQQQ / TMF / IEF are PRIIPs-blocked from UK retail accounts; see
   INV-14 v0.5 for the error 201 KID-variant). QQQ + TLT are the
   trend-signal tickers used by `refresh_eodhd_signals.py` (signal-only,
   never traded — PRIIPs does not apply).
2. **Eligibility signals parquet** loaded from
   ``~/.blive/data/signals/triple_lev_sma_eligible.parquet`` (produced
   by `scripts/refresh_eodhd_signals.py` with columns QQL3 / IBTL /
   IBTM in IB-symbol order).
3. **Target weights** via
   :func:`blive.runtime.signals.eligibility_to_target_weights` — the
   LongShortPortfolio + MaskSelector + EqualWeight semantics applied
   per row.
4. **`IBBroker`** with the production :class:`IBInstrumentResolver`
   (XLON venue → SMART or direct-routed, per the resolver's venue-MIC
   handling) connecting to IB Paper Gateway.
5. **`run_ib_multi_pipeline`** orchestrates the rebalance loop.

Pipeline-mechanics test, **not** a parity-meaningful run. Orders submitted
to IB Paper fill at the venue's *current* market, not at the historical
bar's close — the equity curve informs FSM correctness and integration
health, not strategy quality. Note also that IBTL is **1× leverage** (not
3× — no UK-listed 3× US-Treasury ETP exists per ADR-047) so the strategy's
risk-on regime profile shifts vs. the notebook's TMF leg; the parity
envelope re-derives at M7. The full real-time-clock multi-day
"≥ 5 trading days" run is the M5+ daemon shape.

Defaults:

- Order type **MKT** (guaranteed FSM termination during LSE RTH).
- ``--max-bars 60`` (~3 months of daily bars; eligibility computation
  needs ~SMA-200 of warmup so the parquet's earlier history is the
  warmup, the last N bars are replayed).
- NAV slice **0.05** (Phase 1 lower bound per ADR-020).
- Per-order timeout **10s**.

Operator prereqs (per `M2-IB.4a-happy-cacpa`):

- IB Gateway running on the configured port (default 4002 paper).
- "Read-Only API" unchecked.
- For LSE-listed UCITS / ETPs the
  "Bypass Order Precautions for API Orders" toggle is **recommended on**
  (matches the M2-IB.4a-happy-cacpa setup); LSE direct-routing does not
  trigger the SMART-vs-direct error 10311 cascade since LSE is the
  primary venue.
- ``~/.blive/secrets/ib.env`` populated.
- ``~/.blive/data/eodhd/{ib_symbol}_1d.parquet`` for all 5 IB symbols
  (QQL3 / IBTL / IBTM / QQQ / TLT), produced by
  `scripts/refresh_eodhd_signals.py`.
- ``~/.blive/data/signals/triple_lev_sma_eligible.parquet`` produced
  by the same script.

Usage::

    uv run python scripts/run_m2ib6_ib_paper.py
    uv run python scripts/run_m2ib6_ib_paper.py --order-type LMT --max-bars 30
    uv run python scripts/run_m2ib6_ib_paper.py --max-bars 0  # full replay

Exit codes:

    0  success — pipeline ran to completion (regardless of fill counts)
    2  credentials / args / file-not-found
    3  IB Paper connect / network failure
    5  internal pipeline error (raised + traceback printed)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import traceback
from decimal import Decimal
from pathlib import Path

import pandas as pd

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
    IBInstrumentResolver,
)
from blive.adapters.ib.broker import IBBroker
from blive.adapters.paper.market_data import PaperMarketData
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import AssetClass, Instrument, OrderType
from blive.runtime.ib_pipeline import IBMultiRunResult, run_ib_multi_pipeline
from blive.runtime.signals import eligibility_to_target_weights
from blive.strategy.config import (
    ArtefactPaths,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)
from blive.strategy.loader import LiveStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("m2ib6")


# Phase 1 instruments per ADR-043 + ADR-047. The PRIIPs-compliant
# substitution is QQL3 (LSE; 3× Nasdaq-100 ETP) for TQQQ, IBTL (LSE; 1×
# 20+yr US Treasury UCITS — no UK-listed 3× US Treasury exists, so the
# leg's leverage drops 3×→1× and the strategy regime profile shifts
# accordingly per ADR-047) for TMF, and IBTM (LSE; 1× 7-10yr US Treasury
# UCITS) for IEF. All three are USD-denominated on LSE; the IB resolver
# maps XLON venue per DD-7 §3.
_QQL3 = Instrument(
    symbol="QQL3",
    venue="XLON",
    currency="USD",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)
_IBTL = Instrument(
    symbol="IBTL",
    venue="XLON",
    currency="USD",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)
_IBTM = Instrument(
    symbol="IBTM",
    venue="XLON",
    currency="USD",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)
_TRADABLES: list[Instrument] = [_QQL3, _IBTL, _IBTM]


def _default_eodhd_dir() -> Path:
    return Path.home() / ".blive" / "data" / "eodhd"


def _default_signals_path() -> Path:
    return Path.home() / ".blive" / "data" / "signals" / "triple_lev_sma_eligible.parquet"


def _build_live_strategy(*, strategy_id: str, nav_slice: Decimal) -> LiveStrategy:
    cfg = LiveStrategyConfig(
        strategy_id=strategy_id,
        strategy_module="scripts.run_m2ib6_ib_paper",
        nav_slice=nav_slice,
        live_overrides=LiveOverrides(),
        risk_overrides=RiskOverrides(),
        artefact_paths=ArtefactPaths(),
    )
    return LiveStrategy(
        strategy=object(),  # the eligibility helper produces target_weights; pipeline doesn't read .strategy
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"  - {label}{suffix}")


def _print_summary(result: IBMultiRunResult, *, starting_cash: Decimal) -> None:
    _print_header("M2-IB.6 paper run summary")
    print(f"  submitted: {result.submitted_count}")
    print(f"  filled:    {result.fills_count}")
    print(f"  canceled:  {result.canceled_count}")
    print(f"  rejected:  {result.rejected_count}")
    print(f"  breaches:  {len(result.breaches)}")
    print(f"  per-symbol fills: {dict(sorted(result.fills_by_symbol.items()))}")
    print(f"  starting cash:  {starting_cash}")
    print(f"  final equity:   {result.final_equity}")
    if result.equity_curve:
        first = result.equity_curve[0]
        last = result.equity_curve[-1]
        print(f"  equity curve:   {len(result.equity_curve)} point(s)")
        print(
            f"    first: {first.time_utc.isoformat()}  positions={dict(first.positions)}  "
            f"equity={first.equity}"
        )
        print(
            f"    last:  {last.time_utc.isoformat()}  positions={dict(last.positions)}  "
            f"equity={last.equity}"
        )
    if result.breaches:
        print("  breaches detail (first 5):")
        for b in result.breaches[:5]:
            print(f"    - {b.check.value}: {b.detail}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "End-to-end M2-IB.6 paper-test driver: triple_lev_sma_filter_dsl "
            "(QQL3/IBTL/IBTM, Phase 1 PRIIPs-compliant universe per ADR-047) x "
            "IB Paper, multi-instrument pipeline."
        ),
    )
    parser.add_argument(
        "--eodhd-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing the per-ticker EODHD parquets (QQL3 / IBTL / IBTM / "
            "QQQ / TLT)_1d.parquet. Default: ~/.blive/data/eodhd/"
        ),
    )
    parser.add_argument(
        "--signals-path",
        type=Path,
        default=None,
        help=(
            "Path to the wide eligibility-signals parquet. Default: "
            "~/.blive/data/signals/triple_lev_sma_eligible.parquet"
        ),
    )
    parser.add_argument(
        "--starting-cash",
        type=Decimal,
        default=Decimal("100000"),
        help="Starting cash in USD. Default: 100000.",
    )
    parser.add_argument(
        "--nav-slice",
        type=Decimal,
        default=Decimal("0.05"),
        help="NAV slice for the strategy. Default: 0.05 (per ADR-020).",
    )
    parser.add_argument(
        "--order-type",
        choices=["MKT", "LMT"],
        default="MKT",
        help="Order type for submits. Default: MKT (guaranteed fills during RTH).",
    )
    parser.add_argument(
        "--limit-offset-bps",
        type=Decimal,
        default=Decimal("50"),
        help="LMT offset (bps) from bar.close when --order-type LMT. Default: 50.",
    )
    parser.add_argument(
        "--event-wait-seconds",
        type=float,
        default=10.0,
        help="Per-order timeout waiting for terminal event. Default: 10.",
    )
    parser.add_argument(
        "--max-bars",
        type=int,
        default=60,
        help=(
            "Cap the number of replayed rebalance bars (smoke-bound). 0 = no cap. "
            "Default: 60. The eligibility computation in refresh_eodhd_signals.py "
            "uses the full parquet for SMA-200 warmup; --max-bars only caps the "
            "replay window."
        ),
    )
    parser.add_argument(
        "--strategy-id",
        default="triple_lev_sma_filter_dsl",
        help="Strategy id for the run record. Default matches the canonical id.",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    eodhd_dir = args.eodhd_dir if args.eodhd_dir is not None else _default_eodhd_dir()
    signals_path = args.signals_path if args.signals_path is not None else _default_signals_path()

    # Validate inputs.
    missing: list[str] = []
    for inst in _TRADABLES:
        p = eodhd_dir / f"{inst.symbol}_1d.parquet"
        if not p.is_file():
            missing.append(str(p))
    if not signals_path.is_file():
        missing.append(str(signals_path))
    if missing:
        print("\nFAILED: missing input file(s). Run scripts/refresh_eodhd_signals.py first.")
        for m in missing:
            print(f"  missing: {m}")
        return 2

    _print_header("M2-IB.6 paper-test driver")
    print(f"  eodhd dir:      {eodhd_dir}")
    print(f"  signals path:   {signals_path}")
    print(f"  instruments:    {[i.symbol for i in _TRADABLES]}")
    print(f"  nav slice:      {args.nav_slice}")
    print(f"  starting cash:  {args.starting_cash}")
    print(f"  order type:     {args.order_type}")
    print(f"  max bars:       {'no cap' if args.max_bars == 0 else args.max_bars}")

    # Load IB credentials.
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials -- {exc}")
        return 2
    print(
        f"  IB:             host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} account=[REDACTED]"
    )

    # Construct broker stack.
    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    _print_header("Connecting to IB Paper")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"  is_connected={broker.is_connected}")

    # Build PaperMarketData with the 3 tradable parquets.
    fixtures = {inst: eodhd_dir / f"{inst.symbol}_1d.parquet" for inst in _TRADABLES}
    md = PaperMarketData(fixtures=fixtures)
    canonical_bars = md.bars(_TRADABLES[0])  # QQL3 canonical
    print(
        f"  bars (QQL3 canonical): {len(canonical_bars)} ({canonical_bars[0].close_time_utc.date()} -> {canonical_bars[-1].close_time_utc.date()})"
    )

    # Load eligibility signals + compute target weights.
    eligibility_df = pd.read_parquet(signals_path)
    if eligibility_df.empty:
        print(f"\nFAILED: signals parquet at {signals_path} is empty.")
        await broker.disconnect()
        return 5
    # Defensive: older eligibility parquets may have a tz-naive index
    # (built from .values in earlier refresh script versions). Force
    # tz-aware UTC so the downstream intersection with canonical bar
    # timestamps doesn't silently come up empty.
    eligibility_index = pd.DatetimeIndex(eligibility_df.index)
    if eligibility_index.tz is None:
        eligibility_index = eligibility_index.tz_localize("UTC")
    eligibility_df.index = eligibility_index
    target_weights_full = eligibility_to_target_weights(eligibility_df)

    # Cap the replay window to --max-bars by trimming the canonical bars and
    # restricting target_weights to the corresponding timestamps.
    if args.max_bars > 0 and len(canonical_bars) > args.max_bars:
        capped_bars = canonical_bars[-args.max_bars :]
        print(
            f"  capping bars: using last {args.max_bars} of {len(canonical_bars)} "
            f"({capped_bars[0].close_time_utc.date()} -> {capped_bars[-1].close_time_utc.date()})"
        )
    else:
        capped_bars = canonical_bars

    capped_index = pd.to_datetime([b.close_time_utc for b in capped_bars], utc=True)
    common_index = target_weights_full.index.intersection(capped_index)
    target_weights_capped = target_weights_full.loc[common_index]
    print(f"  target_weights rows: {len(target_weights_capped)}")
    if len(target_weights_capped) == 0:
        print(
            "\nFAILED: no target_weight rows align with the bar window. "
            "Check that eligibility parquet covers the same date range as the "
            "EODHD ticker parquets."
        )
        await broker.disconnect()
        return 5

    # If --max-bars trimmed the canonical bar set, we need a market_data view
    # restricted to those bars too — write a small temp parquet per ticker with
    # only the capped bars.
    if capped_bars is not canonical_bars:
        import tempfile

        tmp_dir = Path(tempfile.mkdtemp(prefix="m2ib6-"))
        tmp_fixtures: dict[Instrument, Path] = {}
        for inst in _TRADABLES:
            full_bars = md.bars(inst)
            # Filter full bars to those whose close_time_utc is in capped_index
            capped_set = set(capped_index)
            inst_capped = [b for b in full_bars if pd.Timestamp(b.close_time_utc) in capped_set]
            df_rows = []
            for b in inst_capped:
                df_rows.append(
                    dict(
                        open_time_utc=b.open_time_utc,
                        close_time_utc=b.close_time_utc,
                        open=float(b.open),
                        high=float(b.high),
                        low=float(b.low),
                        close=float(b.close),
                        volume=float(b.volume),
                    )
                )
            tmp_p = tmp_dir / f"{inst.symbol}_capped.parquet"
            pd.DataFrame(df_rows).to_parquet(tmp_p)
            tmp_fixtures[inst] = tmp_p
        capped_md = PaperMarketData(fixtures=tmp_fixtures)
    else:
        capped_md = md

    # Build LiveStrategy + run.
    live = _build_live_strategy(strategy_id=args.strategy_id, nav_slice=args.nav_slice)
    order_type = OrderType.MKT if args.order_type == "MKT" else OrderType.LMT

    _print_header("Running multi-instrument pipeline")
    try:
        result = await run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,
            market_data=capped_md,
            instruments=_TRADABLES,
            target_weights_series=target_weights_capped,
            starting_cash=args.starting_cash,
            base_currency="USD",
            order_type=order_type,
            limit_price_offset_bps=args.limit_offset_bps,
            event_wait_seconds=args.event_wait_seconds,
        )
    except Exception as exc:  # noqa: BLE001 — driver-level error wrapper
        print(f"\nFAILED in pipeline: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        try:
            await broker.disconnect()
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass
        return 5

    _print_summary(result, starting_cash=args.starting_cash)

    _print_header("Disconnecting")
    await broker.disconnect()
    print("OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
