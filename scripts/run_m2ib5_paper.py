"""M2-IB.5 end-to-end paper-test driver.

Wires the M2-IB.5 prereq trio together for a single tape-replay run
against IB Paper:

1. Connects an :class:`IBBroker` to IB Paper Gateway (credentials at
   ``~/.blive/secrets/ib.env``; bypass for the direct-routing
   restriction must be applied via API → Precautions per the
   M2-IB.4a-happy-cacpa wire validation).
2. Loads the EODHD CAC.PA daily-bar parquet via :class:`PaperMarketData`
   (refreshed by ``scripts/refresh_eodhd_parquet.py``).
3. Computes the SMA-crossover ``position_series`` stub via
   :func:`blive.runtime.signals.sma_crossover_position` (per the
   operator's M2-IB.5 instruction: TKAN deferred until end-to-end
   paper testing is done).
4. Calls :func:`blive.runtime.ib_pipeline.run_ib_pipeline` with the
   broker + market_data + position_series + a minimal
   :class:`LiveStrategy` config.
5. Prints the :class:`IBRunResult` summary (fills / submitted /
   canceled / rejected counts, equity curve endpoints).
6. Disconnects the broker cleanly.

This is a **pipeline-mechanics test**, not a parity-meaningful run.
Orders submitted to IB Paper fill at the venue's *current* market, not
at the historical bar's close — so the equity curve is informative
about FSM correctness and integration health, not about strategy
quality. The full real-time-clock multi-day "≥ 5 trading days" run is
the M5+ daemon shape.

Defaults:

- Order type ``MKT`` for guaranteed FSM termination during market hours.
- ``--max-bars 60`` (~3 months of daily bars) so a smoke run is bounded.
  Pass ``--max-bars 0`` to process the full parquet.
- SMA window 50 — typical mid-frequency crossover anchor.
- NAV slice 0.05 (Phase 1 lower bound per ADR-020).

Prerequisites:

- ``~/.blive/secrets/ib.env`` populated, IB Gateway running, "Read-Only
  API" unchecked, "Bypass Order Precautions for API Orders" ticked
  (per M2-IB.4a-happy-cacpa wire validation).
- ``~/.blive/data/eodhd/CAC.PA_1d.parquet`` populated by
  ``scripts/refresh_eodhd_parquet.py``.

Usage::

    uv run python scripts/run_m2ib5_paper.py
    uv run python scripts/run_m2ib5_paper.py --order-type LMT --max-bars 30
    uv run python scripts/run_m2ib5_paper.py --max-bars 0  # full 2y replay

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
from blive.runtime.ib_pipeline import IBRunResult, run_ib_pipeline
from blive.runtime.signals import sma_crossover_position
from blive.strategy.config import (
    ArtefactPaths,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)
from blive.strategy.loader import LiveStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("m2ib5")


# Phase 1 instrument per ADR-021. The XPAR → SBF mapping in
# IBInstrumentResolver direct-routes; "Bypass Order Precautions for API
# Orders" must be ticked in IB Gateway → API → Precautions.
_PHASE_1_INSTRUMENT = Instrument(
    symbol="CAC.PA",
    venue="XPAR",
    currency="EUR",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)


def _default_parquet_path() -> Path:
    return Path.home() / ".blive" / "data" / "eodhd" / "CAC.PA_1d.parquet"


def _build_live_strategy(*, strategy_id: str, nav_slice: Decimal) -> LiveStrategy:
    cfg = LiveStrategyConfig(
        strategy_id=strategy_id,
        strategy_module="scripts.run_m2ib5_paper",
        nav_slice=nav_slice,
        live_overrides=LiveOverrides(),
        risk_overrides=RiskOverrides(),
        artefact_paths=ArtefactPaths(),
    )
    return LiveStrategy(
        strategy=object(),  # the stub provides the position_series; pipeline doesn't read .strategy
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_summary(result: IBRunResult, *, starting_cash: Decimal) -> None:
    _print_header("M2-IB.5 paper run summary")
    print(f"  submitted: {result.submitted_count}")
    print(f"  filled:    {result.fills_count}")
    print(f"  canceled:  {result.canceled_count}")
    print(f"  rejected:  {result.rejected_count}")
    print(f"  breaches:  {len(result.breaches)}")
    print(f"  starting cash:  {starting_cash}")
    print(f"  final equity:   {result.final_equity}")
    if result.equity_curve:
        first = result.equity_curve[0]
        last = result.equity_curve[-1]
        print(f"  equity curve:   {len(result.equity_curve)} point(s)")
        print(
            f"    first: {first.time_utc.isoformat()}  "
            f"qty={first.position_qty}  mark={first.mark_price}  equity={first.equity}"
        )
        print(
            f"    last:  {last.time_utc.isoformat()}  "
            f"qty={last.position_qty}  mark={last.mark_price}  equity={last.equity}"
        )
    if result.breaches:
        print("  breaches detail (first 5):")
        for b in result.breaches[:5]:
            print(f"    - {b.check.value}: {b.detail}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-end M2-IB.5 paper-test driver: SMA-stub signal × IB Paper.",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=None,
        help="Path to the EODHD CAC.PA daily-bar parquet. "
        "Default: ~/.blive/data/eodhd/CAC.PA_1d.parquet (produced by refresh_eodhd_parquet.py).",
    )
    parser.add_argument(
        "--sma-window",
        type=int,
        default=50,
        help="SMA crossover window for the signal stub. Default: 50.",
    )
    parser.add_argument(
        "--starting-cash",
        type=Decimal,
        default=Decimal("100000"),
        help="Starting cash in EUR. Default: 100000.",
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
        help="Cap the number of bars processed (smoke-bound). 0 = no cap. Default: 60.",
    )
    parser.add_argument(
        "--strategy-id",
        default="tkan_v4_momentum_timing_1x_sma_stub",
        help="Strategy id for the run record. Default identifies this as the SMA stub variant.",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    parquet_path = args.parquet if args.parquet is not None else _default_parquet_path()
    if not parquet_path.is_file():
        print(
            f"\nFAILED: parquet not found at {parquet_path}. "
            f"Run scripts/refresh_eodhd_parquet.py first."
        )
        return 2

    _print_header("M2-IB.5 paper-test driver")
    print(f"  parquet:        {parquet_path}")
    print(
        f"  signal:         SMA({args.sma_window}) crossover stub " f"(per blive.runtime.signals)"
    )
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

    # Load market data + apply --max-bars cap.
    md = PaperMarketData(fixtures={_PHASE_1_INSTRUMENT: parquet_path})
    bars = md.bars(_PHASE_1_INSTRUMENT)
    if args.max_bars > 0 and len(bars) > args.max_bars:
        # Use the *last* N bars so the SMA has enough warmup behind the
        # cap (the parquet's earlier bars warm the SMA implicitly via
        # signal computation below; trimming bars at the data layer
        # would cut the SMA's history too).
        capped_bars = bars[-args.max_bars :]
        print(
            f"  capping bars: using last {args.max_bars} of {len(bars)} ({capped_bars[0].close_time_utc.date()} → {capped_bars[-1].close_time_utc.date()})"
        )
    else:
        capped_bars = bars
        print(
            f"  bars: {len(bars)} ({bars[0].close_time_utc.date()} → {bars[-1].close_time_utc.date()})"
        )

    # Compute the SMA stub signal over the *full* bar set (so the SMA
    # has its warmup history), then filter the position_series to the
    # capped range so the pipeline iterates only over those.
    full_position = sma_crossover_position(bars, sma_window=args.sma_window)
    capped_index = [bar.close_time_utc for bar in capped_bars]
    import pandas as pd

    capped_positions = full_position.loc[pd.to_datetime(capped_index, utc=True)]
    long_count = int((capped_positions == 1).sum())
    flat_count = int((capped_positions == 0).sum())
    print(f"  signal:       long {long_count} / flat {flat_count} day(s) in the capped window")

    # Build a PaperMarketData restricted to the capped bars by filtering
    # the parquet through a temp view (the simplest is to write a temp
    # parquet; but we can also pass a smaller fixture by reusing
    # `md.bars` — since `run_ib_pipeline` calls `market_data.bars(instrument)`,
    # we need the fixture to return only the capped bars). For the
    # initial driver, write a small temporary parquet of the capped
    # bars.
    if capped_bars is not bars:
        import tempfile

        tmp_dir = Path(tempfile.mkdtemp(prefix="m2ib5-"))
        tmp_parquet = tmp_dir / "CAC.PA_capped.parquet"
        # Reconstruct a DataFrame from the capped bars and write it.
        df_rows = []
        for b in capped_bars:
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
        capped_df = pd.DataFrame(df_rows)
        capped_df.to_parquet(tmp_parquet)
        capped_md = PaperMarketData(fixtures={_PHASE_1_INSTRUMENT: tmp_parquet})
    else:
        capped_md = md

    # Build LiveStrategy + run.
    live = _build_live_strategy(strategy_id=args.strategy_id, nav_slice=args.nav_slice)

    order_type = OrderType.MKT if args.order_type == "MKT" else OrderType.LMT

    _print_header("Running pipeline")
    try:
        result = await run_ib_pipeline(
            live_strategy=live,
            broker=broker,
            market_data=capped_md,
            instrument=_PHASE_1_INSTRUMENT,
            position_series=capped_positions,
            starting_cash=args.starting_cash,
            base_currency="EUR",
            target_leverage=Decimal("1"),
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
