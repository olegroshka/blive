"""Execute a sfera strategy's target weights on IB Paper — strategy-agnostic.

This generalises ``run_today_sfera_signal.py`` (which was hardcoded to the
``leveraged_etf_trend_filter`` *signal* parquet + TQQQ/TMF/IEF) to the
canonical sfera platform output: **``strategy.target_weights``** — the final
TARGET WEIGHTS PER STRATEGY (per ``sfera/run_daily.py``). Signals are an
intermediate layer; this reads the layer a book actually trades.

Weight sources (operator's "DB-primary, file-fallback" directive):
  * ``--source db``   (default) — read ``strategy.target_weights`` straight
    from the sfera Postgres for ``--strategy`` at ``--as-of`` (latest by
    default). Connection coords come from sfera's ``.env`` (``--sfera-root``)
    so blive does not import the sfera package (KB-13 boundary).
  * ``--source file`` — read a parquet/CSV snapshot. Accepts the long
    ``strategy.target_weights`` shape (date, strategy, identifier, weight)
    or the legacy signal shape (date, identifier, value).

Order semantics: MOO (market-on-open) by default — matches every sfera
strategy's spec ("decide close[T], fill next open"). On IB this is a MARKET
order with ``tif=OPG`` (no new OrderType needed). ``--order-type MKT`` submits
an immediate day market order instead.

CASH is the *residual* (1 - sum of stored leg weights); it is never an order.
A leg you currently hold that is not in today's target is sized down to zero
(full rebalance to target) by the sizer.

Safety: **dry-run by default.** Nothing is submitted unless ``--submit`` is
passed, and then only after an interactive confirm (skip with ``--yes``).
The connect step is also a *detect-at-connect* probe: it reports the account
base currency and which target instruments are actually tradable on this
account (a US-ETF universe is PRIIPs-blocked on a UK retail account).

Usage::

    # offline preview (no IB needed): what would R02 trade today?
    uv run python scripts/execute_sfera_strategy.py --offline

    # live dry-run (connects, detects eligibility, sizes — submits nothing)
    uv run python scripts/execute_sfera_strategy.py --strategy R02

    # actually place MOO orders on IB Paper (gated)
    uv run python scripts/execute_sfera_strategy.py --strategy R02 --submit

Exit codes:
    0  success (preview or submit)
    2  credentials / data error
    3  IB connect failure
    4  no target instrument tradable on this account (eligibility)
    5  pipeline / sizing error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd

sys.path.insert(0, "src")

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
    IBInstrumentResolver,
    IBMarketData,
)
from blive.adapters.ib.broker import IBBroker
from blive.adapters.ib.instrument_resolver import InstrumentNotResolvable
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import (
    AssetClass,
    Bar,
    ClientOrderId,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    Position,
    TimeInForce,
)
from blive.runtime.ib_pipeline import _drain_order_lifecycle, _drain_startup_events  # noqa: PLC2701
from blive.sizing import SizerInput, size_orders

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("execute_sfera")

# --- US-ETF instrument catalogue --------------------------------------------
# symbol -> (primary-exchange hint, currency). The IBInstrumentResolver routes
# US equities via SMART with this primary-exchange hint (ADR-046). Hints are
# best-effort and validated empirically by the detect-at-connect probe; a wrong
# hint surfaces IB error 200 and the symbol is reported blocked, not silently
# mis-sized. CASH/BIL: CASH is the residual (no instrument); BIL is a real ETF.
_CATALOGUE: dict[str, Instrument] = {
    sym: Instrument(
        symbol=sym,
        venue=venue,
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )
    for sym, venue in {
        "TQQQ": "XNAS",
        "TECL": "ARCX",
        "TECS": "ARCX",
        "SPXL": "ARCX",
        "UVXY": "BATS",
        "VXX": "BATS",
        "IEF": "XNAS",
        "TMF": "ARCX",
        "BIL": "ARCX",
    }.items()
}

_NON_TRADABLE = {"CASH"}  # residual sleeve — never an order

# --- Canonical strategy registry --------------------------------------------
# Naming convention (per operator):
#   * R-code (R01, R02, ...) = the research/strategy identity that lab + sfera
#     produce. This is the canonical id the operator types/sees.
#   * `slot` = the ForgeFolio PROD slot it's currently deployed into (S14, ...).
#     The R->S binding is a deployment decision and CAN change, so it lives as a
#     field here, not as the primary key.
#   * `db_key` = the *current* sfera DB key (``strategy.target_weights.strategy``)
#     — still ``r_lev_*`` until/unless that column is re-keyed. Kept in exactly
#     one place so the legacy name never leaks into the rest of the tool.
#
# (ForgeFolio's systematic_strategies.json S14 row is stale — it still lists the
# old vix_vxx_rotation signal + TQQQ/VXX/IEF; R02 is the qc_cash conditional-
# rotation tree on TQQQ/TECL/UVXY/TECS.)
_STRATEGIES: dict[str, dict] = {
    "R01": {"db_key": "r_lev_001", "slot": None,    "name": "SMA-200 trend (TQQQ/IEF)",             "status": "retired"},
    "R02": {"db_key": "r_lev_002", "slot": "S14",   "name": "Conditional rotation (qc_cash)",       "status": "live"},
    "R03": {"db_key": "r_lev_003", "slot": None,    "name": "Keeper (rotation + vol/chop overlays)", "status": "candidate"},
    "R04": {"db_key": "r_lev_004", "slot": "S14v2", "name": "Sized rotation (+iv9M/COT)",            "status": "candidate"},
}
_SLOT_TO_RCODE = {v["slot"]: k for k, v in _STRATEGIES.items() if v["slot"]}
_LEGACY_TO_RCODE = {v["db_key"]: k for k, v in _STRATEGIES.items()}


def _resolve_code(token: str) -> tuple[str, str]:
    """(R-code, sfera db_key) for an R-code, a prod slot (S14), or legacy r_lev_*."""
    if token in _STRATEGIES:
        return token, _STRATEGIES[token]["db_key"]
    if token in _SLOT_TO_RCODE:
        rc = _SLOT_TO_RCODE[token]
        return rc, _STRATEGIES[rc]["db_key"]
    if token in _LEGACY_TO_RCODE:
        rc = _LEGACY_TO_RCODE[token]
        return rc, _STRATEGIES[rc]["db_key"]
    raise WeightLoadError(f"unknown strategy {token!r}")

_DEFAULT_SFERA_ROOT = Path(
    r"C:\Personal\Business & Investments\Python codes\sfera"
)


# --- Weight sources ----------------------------------------------------------


class WeightLoadError(RuntimeError):
    """Raised when target weights cannot be loaded from the chosen source."""


def _normalise_long(df: pd.DataFrame, strategy: str, as_of: date | None) -> tuple[dict[str, Decimal], date]:
    """Long frame (date, identifier, weight[, strategy]) -> latest-or-as_of weights."""
    df = df.copy()
    if "strategy" in df.columns:
        df = df[df["strategy"].astype(str) == strategy]
    weight_col = "weight" if "weight" in df.columns else "value"
    if weight_col not in df.columns or "identifier" not in df.columns or "date" not in df.columns:
        raise WeightLoadError(
            f"weights frame missing required columns; got {list(df.columns)}"
        )
    df["date"] = pd.to_datetime(df["date"])
    if df.empty:
        raise WeightLoadError(f"no rows for strategy {strategy!r}")
    target_date = pd.Timestamp(as_of) if as_of else df["date"].max()
    rows = df[df["date"] == target_date]
    if rows.empty:
        raise WeightLoadError(f"no rows for strategy {strategy!r} on {target_date.date()}")
    weights = {
        str(r["identifier"]): Decimal(str(float(r[weight_col]))) for _, r in rows.iterrows()
    }
    return weights, target_date.date()


def load_weights_db(
    strategy: str, *, sfera_root: Path, as_of: date | None
) -> tuple[dict[str, Decimal], date, str]:
    """Read ``strategy.target_weights`` straight from the sfera Postgres.

    Connection coords are loaded from ``<sfera_root>/.env`` (DB_HOST/PORT/
    NAME/USER/PASSWORD) — the same values sfera's ``database_config`` reads —
    without importing the sfera package.
    """
    try:
        import psycopg  # local import: only the DB source needs it
        from dotenv import load_dotenv
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise WeightLoadError(
            "DB source needs 'psycopg' + 'python-dotenv' in the blive venv "
            "(pip install 'psycopg[binary]' python-dotenv), or use --source file"
        ) from exc

    env_path = Path(sfera_root) / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "sfera")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    conn_str = f"host={host} port={port} dbname={dbname} user={user} password={password}"

    sql = (
        "SELECT date, identifier, weight FROM strategy.target_weights "
        "WHERE strategy = %s" + (" AND date = %s" if as_of else "") + " ORDER BY identifier"
    )
    params: tuple = (strategy, as_of) if as_of else (strategy,)
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if not as_of:
                    cur.execute(
                        "SELECT MAX(date) FROM strategy.target_weights WHERE strategy = %s",
                        (strategy,),
                    )
                    latest = cur.fetchone()[0]
                    if latest is None:
                        raise WeightLoadError(f"no rows for strategy {strategy!r} in DB")
                    cur.execute(sql.replace("ORDER BY", "AND date = %s ORDER BY"), (strategy, latest))
                else:
                    cur.execute(sql, params)
                fetched = cur.fetchall()
                cols = [d[0] for d in cur.description]
    except WeightLoadError:
        raise
    except Exception as exc:  # connection / query failure
        raise WeightLoadError(f"sfera DB read failed: {exc}") from exc

    frame = pd.DataFrame(fetched, columns=cols)
    weights, target_date = _normalise_long(frame, strategy, None)
    return weights, target_date, f"sfera.strategy.target_weights@{host}:{port}/{dbname}"


def load_weights_file(
    path: Path, strategy: str, *, as_of: date | None
) -> tuple[dict[str, Decimal], date, str]:
    """Read target weights from a parquet/CSV snapshot (fallback source)."""
    if not path.is_file():
        raise WeightLoadError(f"weights file not found: {path}")
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    weights, target_date = _normalise_long(df, strategy, as_of)
    return weights, target_date, f"file:{path.name}"


# --- Order construction ------------------------------------------------------


def _make_order(desired: Order, *, order_type: OrderType, tif: TimeInForce,
                limit_price: Decimal | None, label: str) -> Order:
    """Re-stamp a sized order with the chosen execution order_type + tif (+ limit)."""
    return Order(
        client_order_id=ClientOrderId(uuid4()),
        strategy_id=desired.strategy_id,
        instrument=desired.instrument,
        side=desired.side,
        quantity=desired.quantity,
        order_type=order_type,
        time_in_force=tif,
        limit_price=limit_price,
        stop_price=None,
        parent_id=None,
        tags={**desired.tags, "pipeline": label},
        created_at=desired.created_at,
    )


def _print_weights(weights: dict[str, Decimal], as_of: date, source: str) -> tuple[dict[str, Decimal], Decimal]:
    """Print the weight table, return (tradable target weights, cash residual)."""
    invested = sum((w for w in weights.values()), Decimal("0"))
    cash_residual = max(Decimal("0"), Decimal("1") - invested)
    print(f"\n=== target weights  (as-of {as_of}, source={source}) ===")
    tradable: dict[str, Decimal] = {}
    for sym, w in sorted(weights.items()):
        if sym in _NON_TRADABLE:
            note = "  (residual -> no order)"
        elif sym not in _CATALOGUE:
            note = "  <-- NOT in catalogue (will be skipped)"
        else:
            inst = _CATALOGUE[sym]
            note = f"  {inst.venue}/{inst.currency}"
            tradable[sym] = w
        held = "  *** HELD ***" if w > 0 else ""
        print(f"  {sym:6} {float(w):8.2%}{note}{held}")
    if cash_residual > 0:
        print(f"  {'CASH':6} {float(cash_residual):8.2%}  (residual -> no order)")
    return tradable, cash_residual


# --- Detect-at-connect + execution ------------------------------------------


def _sfera_last_close(symbols: list[str], sfera_root: Path) -> dict[str, Decimal]:
    """Fallback price source: latest close from sfera's ``yfmktdt.stock_prices``.

    Used when IB market data is unavailable (error 162 session/market-data
    contention, or no MD subscription) so sizing can still proceed — the MOO
    fill happens at the next open regardless, so this is only a share-count
    reference, never the execution price.
    """
    try:
        import psycopg
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - environment dependent
        return {}
    env_path = Path(sfera_root) / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    conn_str = (
        f"host={os.getenv('DB_HOST','localhost')} port={os.getenv('DB_PORT','5432')} "
        f"dbname={os.getenv('DB_NAME','sfera')} user={os.getenv('DB_USER','postgres')} "
        f"password={os.getenv('DB_PASSWORD','')}"
    )
    out: dict[str, Decimal] = {}
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                for sym in symbols:
                    cur.execute(
                        "SELECT close_price FROM yfmktdt.stock_prices WHERE ticker=%s "
                        "ORDER BY trade_date DESC LIMIT 1",
                        (sym,),
                    )
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        out[sym] = Decimal(str(float(row[0])))
    except Exception:  # noqa: BLE001 - fallback is best-effort
        return out
    return out


async def _probe_eligibility_and_price(
    market_data: IBMarketData,
    resolver: IBInstrumentResolver,
    symbols: list[str],
    sfera_root: Path,
) -> tuple[dict[str, Decimal], dict[str, str], dict[str, str], list[str]]:
    """Detect-at-connect, done right — eligibility separate from price.

    Eligibility = contract qualification (``resolver.resolve`` ->
    ``qualifyContractsAsync``), which is INDEPENDENT of market data. A symbol is
    BLOCKED only when IB cannot qualify the contract (genuinely unavailable /
    not permitted). The price is fetched separately: IB historical bars first,
    falling back to sfera's last close when IB market data is unavailable (e.g.
    error 162 session contention). This stops a market-data/session hiccup from
    masquerading as an eligibility block (the bug that flagged TQQQ/IEF — which
    the account demonstrably holds — as "BLOCKED").

    Returns (prices, price_source, blocked_reason, eligible_symbols).
    """
    blocked: dict[str, str] = {}
    eligible: list[str] = []
    for sym in symbols:
        try:
            await resolver.resolve(_CATALOGUE[sym])
            eligible.append(sym)
        except InstrumentNotResolvable as exc:
            blocked[sym] = f"contract not tradable: {str(exc).splitlines()[0][:120]}"
        except Exception as exc:  # noqa: BLE001 - surface any resolve failure
            blocked[sym] = f"resolve failed: {str(exc).splitlines()[0][:120]}"

    prices: dict[str, Decimal] = {}
    price_src: dict[str, str] = {}
    last_bars: dict[str, Bar] = {}
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=7)
    need_fallback: list[str] = []
    for sym in eligible:
        try:
            bars = await market_data.historical_bars(_CATALOGUE[sym], freq="1d", start=start, end=end)
            if bars:
                prices[sym] = bars[-1].close
                price_src[sym] = "IB"
                last_bars[sym] = bars[-1]
            else:
                need_fallback.append(sym)
        except Exception:  # noqa: BLE001 - IB MD failure -> sfera fallback
            need_fallback.append(sym)
    if need_fallback:
        for sym, px in _sfera_last_close(need_fallback, sfera_root).items():
            prices[sym] = px
            price_src[sym] = "sfera-close"
            last_bars[sym] = Bar(instrument=_CATALOGUE[sym], close_time_utc=end,
                                 open=px, high=px, low=px, close=px, volume=Decimal("0"))
    return prices, price_src, blocked, eligible, last_bars


async def _fx_base_to_usd(broker: IBBroker, base_ccy: str) -> tuple[Decimal, str]:
    """Rate to convert the account base currency into USD (the instrument ccy).

    All sfera legs are USD ETFs; the account may be GBP-denominated, so a budget
    (or nav-slice of equity) expressed in the base currency must be converted to
    USD before sizing — otherwise positions come out ~1/fx undersized. Primary
    source is IB's reported ``ExchangeRate`` account value (currency -> base);
    falls back to a GBPUSD forex spot, then to 1.0 with a loud warning.
    """
    if base_ccy.upper() == "USD":
        return Decimal("1"), "base=USD"
    try:
        for av in broker._client.ib.accountValues():  # noqa: SLF001 - script-level access
            if av.tag == "ExchangeRate" and av.currency == "USD":
                rate = Decimal(str(av.value))  # GBP per 1 USD (USD -> base)
                if rate > 0:
                    return (Decimal("1") / rate), f"IB ExchangeRate(USD)={rate}"
    except Exception:  # noqa: BLE001 - best-effort
        pass
    if base_ccy.upper() == "GBP":
        try:
            import ib_async

            bars = await broker._client.ib.reqHistoricalDataAsync(  # noqa: SLF001
                ib_async.Forex("GBPUSD"), endDateTime="", durationStr="3 D",
                barSizeSetting="1 day", whatToShow="MIDPOINT", useRTH=False,
            )
            if bars:
                return Decimal(str(bars[-1].close)), "IB GBPUSD spot"
        except Exception:  # noqa: BLE001
            pass
    return Decimal("1"), "FX UNAVAILABLE -> treating budget as USD (CALIBRATE!)"


async def _run(args: argparse.Namespace) -> int:
    # --- 1. Load target weights (single strategy OR blended portfolio) ------
    as_of = date.fromisoformat(args.as_of) if args.as_of else None

    def _load_one(dbk: str):
        if args.source == "file":
            return load_weights_file(Path(args.weights_path), dbk, as_of=as_of)
        return load_weights_db(dbk, sfera_root=Path(args.sfera_root), as_of=as_of)

    if args.portfolio:
        # Blend MULTIPLE strategies on ONE account into a combined target. The
        # weight blend is budget-weighted and FX-independent:
        #   combined_weight[i] = sum_s(budget_s * weight_s[i]) / sum_s budget_s ;
        #   total pot = sum_s budget_s.
        # This is the correct way to run >1 strategy on a single account that
        # shares instruments — a per-strategy delta-sizer would otherwise fight
        # over the shared position. (Per-strategy P&L attribution needs a
        # separate ledger — future.)
        try:
            plan = json.loads(args.portfolio)
            combined: dict[str, Decimal] = {}
            total_budget = Decimal("0")
            oldest: date | None = None
            labels: list[str] = []
            for item in plan:
                code_i, dbk_i = _resolve_code(str(item["strategy"]))
                b = Decimal(str(item["budget"]))
                w_i, d_i, _ = _load_one(dbk_i)
                for sym, wt in w_i.items():
                    combined[sym] = combined.get(sym, Decimal("0")) + b * wt
                total_budget += b
                oldest = d_i if oldest is None else min(oldest, d_i)
                labels.append(f"{code_i} {float(b):,.0f}")
            if total_budget <= 0:
                print("\nFAILED: portfolio total budget must be > 0")
                return 2
            weights = {sym: (notional / total_budget) for sym, notional in combined.items()}
            signal_date = oldest  # type: ignore[assignment]
            source = "portfolio[" + " + ".join(labels) + "]"
            code, db_key = "PORTFOLIO", "portfolio"
            args.budget = float(total_budget)
            print(f"  PORTFOLIO: {' + '.join(labels)}  (total budget {float(total_budget):,.0f})")
        except WeightLoadError as exc:
            print(f"\nFAILED building portfolio: {exc}")
            return 2
        except Exception as exc:  # noqa: BLE001 - bad JSON / keys
            print(f"\nFAILED parsing --portfolio: {exc}")
            return 2
    else:
        try:
            code, db_key = _resolve_code(args.strategy)
        except WeightLoadError:
            print(f"\nFAILED: unknown strategy {args.strategy!r}; known: {', '.join(sorted(_STRATEGIES))}")
            return 2
        meta = _STRATEGIES[code]
        slot = f" (slot {meta['slot']})" if meta["slot"] else ""
        print(f"  strategy: {code}{slot} - {meta['name']}  (sfera key: {db_key})")
        try:
            weights, signal_date, source = _load_one(db_key)
        except WeightLoadError as exc:
            print(f"\nFAILED: {exc}")
            return 2

    tradable_targets, cash_residual = _print_weights(weights, signal_date, source)
    if not tradable_targets:
        print("\nNo tradable (catalogued) legs in today's target — fully CASH / out-of-universe.")
        # Still meaningful: a live run would flatten held legs. Offline, nothing to do.

    # Freshness guard — don't act on stale weights (e.g. today's pipeline hasn't run).
    today = datetime.now(tz=timezone.utc).date()
    staleness = (today - signal_date).days
    stale = staleness > args.max_staleness_days
    if stale:
        print(f"\n  WARNING STALE: weights are {staleness}d old (as-of {signal_date}; "
              f"max {args.max_staleness_days}d). Compute today's signals first — "
              f"--submit will refuse unless --force-stale.")

    # Execution policy. MOO/MKT = market orders (always fill, NO price protection).
    # LOO/LMT = LIMIT orders with a band around the reference price: LOO fills at
    # the open within the band else cancels; LMT works the day and STAYS PENDING
    # if the price never enters the band. Both stop a runaway open from filling
    # at an absurd price.
    _POLICY = {
        "MOO": (OrderType.MKT, TimeInForce.OPG, False),
        "MKT": (OrderType.MKT, TimeInForce.DAY, False),
        "LOO": (OrderType.LMT, TimeInForce.OPG, True),
        "LMT": (OrderType.LMT, TimeInForce.DAY, True),
    }
    order_type, tif, is_limit = _POLICY[args.order_type]
    band = Decimal(str(args.limit_band))
    print(f"\n  order plan: {args.order_type}  (IB {order_type.value} tif={tif.value}"
          + (f", limit band ±{float(band):.1%}" if is_limit else "") + ")")

    # --- 2. Offline preview short-circuit -----------------------------------
    if args.offline:
        pot = args.budget if args.budget > 0 else args.example_equity * args.nav_slice
        basis = (f"budget ${args.budget:,.0f}" if args.budget > 0
                 else f"nav_slice {args.nav_slice:.0%} x example equity ${args.example_equity:,.0f}")
        print(f"\n=== OFFLINE preview (no IB) - {basis} -> ${pot:,.0f} deployable ===")
        for sym, w in tradable_targets.items():
            if w > 0:
                print(f"    {sym}: target ${float(w) * pot:,.0f}  (shares at execution from live IB price)")
        print("\n  (offline: FX, live equity, eligibility, prices and orders require IB Gateway up)")
        return 0

    # --- 3. Connect to IB (detect-at-connect) -------------------------------
    try:
        credentials = IBCredentials.load()
    except (CredentialsMissing, ValueError) as exc:
        print(f"\nFAILED: IB credentials: {exc}")
        return 2

    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    market_data = IBMarketData(client=client, resolver=resolver, clock=clock)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    print("\n=== Connecting to IB Paper ===")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        print("  (is IB Gateway running on the configured host/port, paper, API enabled?)")
        return 3
    print(f"  connected: {broker.is_connected}")
    await _drain_startup_events(broker)

    snap = await broker.account_snapshot()
    equity = snap.equity
    print("\n=== Account snapshot (detect-at-connect) ===")
    print(f"  Account:  {credentials.account_id}")
    print(f"  Currency: {snap.base_currency}")
    print(f"  Equity:   {snap.base_currency} {float(equity):,.2f}")
    if snap.base_currency and snap.base_currency.upper() != "USD":
        print(
            f"  NOTE: base currency is {snap.base_currency}, not USD. The sfera universe is "
            "US ETFs — check the eligibility report below for PRIIPs/permission blocks."
        )

    ib_positions = await broker.positions()
    positions: dict[str, Position] = {p.instrument.symbol: p for p in ib_positions}
    print(f"  Open positions: {list(positions.keys()) or '(none)'}")

    # Probe the union of today's tradable targets and any held catalogue legs
    # (held-but-not-target legs must be price-known so the sizer can flatten them).
    probe_syms = sorted(set(tradable_targets) | (set(positions) & set(_CATALOGUE)))
    print("\n=== Instrument eligibility + prices ===")
    prices, price_src, blocked, eligible, last_bars = await _probe_eligibility_and_price(
        market_data, resolver, probe_syms, Path(args.sfera_root)
    )
    for sym in probe_syms:
        if sym in prices:
            print(f"  {sym:6} ELIGIBLE   ${float(prices[sym]):>9.4f}  (price: {price_src[sym]})")
        elif sym in eligible:
            print(f"  {sym:6} ELIGIBLE   (no price: IB MD + sfera fallback both unavailable — can't size)")
        else:
            print(f"  {sym:6} BLOCKED    {blocked.get(sym, 'unknown')}")

    eligible_target_syms = [s for s in tradable_targets if s in eligible]
    priced_targets = {s: w for s, w in tradable_targets.items() if s in prices}
    if tradable_targets and not eligible_target_syms:
        print(
            "\nFAILED: none of today's target instruments can be qualified on this account "
            "(contract qualify failed) — a genuine availability / jurisdiction block."
        )
        await broker.disconnect()
        return 4
    if tradable_targets and not priced_targets:
        print(
            "\nFAILED: targets are tradable but no price is available (IB market data down "
            "and sfera fallback empty) — cannot size. Fix the IB session/MD or the sfera price feed."
        )
        await broker.disconnect()
        return 5

    # --- 4. Size orders (full rebalance to target) --------------------------
    # Build a target over the full eligible universe (held legs not in target -> 0).
    target_weights: dict[str, Decimal] = {s: Decimal("0") for s in prices}
    target_weights.update({s: w for s, w in priced_targets.items()})

    base_ccy = snap.base_currency or "USD"
    fx, fx_src = await _fx_base_to_usd(broker, base_ccy)
    if args.budget and args.budget > 0:
        pot_base = Decimal(str(args.budget))
        pot_label = f"budget {float(pot_base):,.0f} {base_ccy}"
    else:
        pot_base = equity * Decimal(str(args.nav_slice))
        pot_label = f"nav_slice {args.nav_slice:.1%} x {float(equity):,.0f} {base_ccy} = {float(pot_base):,.0f} {base_ccy}"
    pot_usd = (pot_base * fx).quantize(Decimal("0.01"))
    # AUM model: budget = allocated AUM; weights deploy within it. Strategies may
    # LEVER beyond AUM (e.g. R04 COT washout -> leg weight up to 1.5x, BIL floored
    # at 0) so a weight can exceed 1.0. The pure sizer caps |weight| <= 1, so we
    # pre-scale: inflate the pot by the max leg weight and normalise weights into
    # [-1, 1]. Per-leg notional (pot_usd * weight) is preserved exactly, and
    # sum(weight) > 1 then deploys > AUM on margin — the intended leverage.
    max_w = max((abs(w) for w in target_weights.values()), default=Decimal("1"))
    lev = max(Decimal("1"), max_w)
    size_equity = (pot_usd * lev).quantize(Decimal("0.01"))
    size_weights = (
        {k: (w / lev) for k, w in target_weights.items()} if lev > 1 else target_weights
    )
    lev_note = f";  leverage {float(lev):.2f}x (deploys > AUM on margin)" if lev > 1 else ""
    print(
        f"\n=== Sizing ({pot_label};  FX {base_ccy}->USD {float(fx):.4f} [{fx_src}];  "
        f"AUM ${float(pot_usd):,.2f}{lev_note}) ==="
    )
    sizer_in = SizerInput(
        target_weights=size_weights,
        equity=size_equity,
        nav_slice=Decimal("1"),
        current_positions={s: positions[s] for s in positions if s in prices},
        instrument_resolver=lambda sym: _CATALOGUE[sym],
        price_lookup=lambda inst: prices[inst.symbol],
        strategy_id=code,
        now=datetime.now(tz=timezone.utc),
    )
    try:
        candidate_orders = size_orders(sizer_in)
    except Exception as exc:
        print(f"\nFAILED in sizer: {exc}")
        await broker.disconnect()
        return 5

    if not candidate_orders:
        print("  No orders — already at target weights.")
        await broker.disconnect()
        return 0
    for o in candidate_orders:
        print(f"  -> {o.side.value} {float(o.quantity):.0f} {o.instrument.symbol}")

    # --- 5. Dry-run vs submit ------------------------------------------------
    if not args.submit:
        print("\n=== DRY-RUN — nothing submitted. Re-run with --submit to place these orders. ===")
        await broker.disconnect()
        return 0

    if stale and not args.force_stale:
        print("\nFAILED: refusing to submit STALE signals — run today's signal pipeline first, "
              "or pass --force-stale to override.")
        await broker.disconnect()
        return 2

    # Double-submit guard: a prior run may have queued MOO orders not yet filled
    # (sizer compares to filled positions, not pending orders) — skip dupes.
    pending = await broker.open_orders()
    pending_syms = {p.instrument.symbol for p in pending}
    dup = pending_syms & {o.instrument.symbol for o in candidate_orders}
    if dup:
        print(f"  NOTE: pending orders already exist for {sorted(dup)} — skipping to avoid duplicates.")
        candidate_orders = [o for o in candidate_orders if o.instrument.symbol not in pending_syms]
        if not candidate_orders:
            print("  Nothing new to submit.")
            await broker.disconnect()
            return 0

    if not args.yes:
        prompt = (
            f"\nSubmit {len(candidate_orders)} {args.order_type} order(s) "
            f"for {code} to account {credentials.account_id}? [y/N] "
        )
        if input(prompt).strip().lower() not in ("y", "yes"):
            print("Aborted by operator.")
            await broker.disconnect()
            return 0

    # Optional RiskEngine (RC-13 kill-switch / RC-08 stale / RC-09 hours / RC-10
    # price sanity). RC-10 only bites on LIMIT orders (LOO/LMT) — it checks the
    # limit is within ±50% of the reference, catching gross sizing/price bugs.
    # outside_rth_allowed=True since MOO/LOO intentionally submit at the open.
    engine = None
    if args.risk_checks or args.kill_switch:
        from blive.risk.checks import KillSwitch, RiskEngine, RiskEngineConfig, RiskInputs
        ks = KillSwitch()
        if args.kill_switch:
            ks.arm("operator --kill-switch")
        engine = RiskEngine(
            config=RiskEngineConfig(outside_rth_allowed=True,
                                    max_data_staleness_daily_sec=5 * 86400,
                                    max_price_deviation_pct=Decimal("0.5")),
            kill_switch=ks, strategy_id=code)
        print(f"  risk engine ON (price-sanity ±50%; kill-switch="
              f"{'ARMED — all orders blocked' if args.kill_switch else 'clear'})")

    print(f"\n=== Submitting {args.order_type} orders ===")
    filled = canceled = rejected = risk_blocked = 0
    now_utc = datetime.now(tz=timezone.utc)
    for desired in candidate_orders:
        lp: Decimal | None = None
        if is_limit:
            ref = prices[desired.instrument.symbol]
            mult = (Decimal("1") + band) if desired.side == OrderSide.BUY else (Decimal("1") - band)
            lp = (ref * mult).quantize(Decimal("0.01"))
        order = _make_order(desired, order_type=order_type, tif=tif, limit_price=lp, label=f"sfera-{code}")

        if engine is not None:
            approved, breaches = engine.approve(
                order,
                inputs=RiskInputs(last_bar=last_bars.get(desired.instrument.symbol),
                                  is_market_open=True,
                                  reference_price=prices.get(desired.instrument.symbol)),
                now=now_utc)
            for b in breaches:
                chk = b.check.value if hasattr(b.check, "value") else b.check
                print(f"    risk {chk}: {b.detail}")
            if approved is None:
                print(f"    BLOCKED by risk engine — skipping {order.instrument.symbol}")
                risk_blocked += 1
                continue

        px_str = f" @ {float(lp):.2f}" if lp is not None else ""
        print(f"  Submitting {order.side.value} {float(order.quantity):.0f} "
              f"{order.instrument.symbol} {args.order_type}{px_str} ...")
        await broker.submit(order)
        terminal_state, _ = await _drain_order_lifecycle(
            broker=broker,
            target_id=ClientOrderId(order.client_order_id),
            timeout_s=args.event_wait_seconds,
        )
        print(f"    -> {terminal_state}")
        state_name = getattr(terminal_state, "name", str(terminal_state))
        if state_name == "FILLED":
            filled += 1
        elif state_name == "CANCELED":
            canceled += 1
        elif state_name == "REJECTED":
            rejected += 1

    print(f"\n=== Done: filled={filled}  canceled={canceled}  rejected={rejected}  risk-blocked={risk_blocked} ===")
    await broker.disconnect()
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Execute a sfera strategy's target weights on IB Paper")
    p.add_argument("--strategy", default="R02", help="strategy R-code e.g. R02 (also accepts slot S14 or legacy r_lev_*); default R02")
    p.add_argument("--portfolio", default="",
                   help='blend multiple strategies on ONE account, JSON: '
                        '[{"strategy":"R02","budget":50000},{"strategy":"R04","budget":50000}]')
    p.add_argument("--source", choices=("db", "file"), default="db", help="weight source (default db)")
    p.add_argument("--weights-path", default="", help="parquet/CSV path for --source file")
    p.add_argument("--sfera-root", default=str(_DEFAULT_SFERA_ROOT), help="sfera root (for DB .env)")
    p.add_argument("--as-of", default="", help="weights date YYYY-MM-DD (default latest)")
    p.add_argument("--nav-slice", type=float, default=0.05, help="NAV slice fraction of equity (default 0.05) if --budget unset")
    p.add_argument("--budget", type=float, default=0.0, help="absolute strategy budget in account base ccy (overrides --nav-slice)")
    p.add_argument("--max-staleness-days", type=int, default=4, help="refuse --submit if weights older than N days (default 4)")
    p.add_argument("--force-stale", action="store_true", help="override the staleness guard on --submit")
    p.add_argument("--order-type", choices=("MOO", "MKT", "LOO", "LMT"), default="MOO",
                   help="MOO/MKT=market (no price protection); LOO/LMT=limit at +/-band "
                        "(LOO fills at open else cancels; LMT works the day & stays pending)")
    p.add_argument("--limit-band", type=float, default=0.03, help="price band for LOO/LMT (default 0.03 = 3%%)")
    p.add_argument("--risk-checks", action="store_true",
                   help="run blive RiskEngine (RC-10 price sanity etc.) before each submit")
    p.add_argument("--kill-switch", action="store_true", help="arm RC-13 kill-switch — blocks ALL orders")
    p.add_argument("--offline", action="store_true", help="no IB; print target preview only")
    p.add_argument("--submit", action="store_true", help="actually place orders (default dry-run)")
    p.add_argument("--yes", action="store_true", help="skip interactive submit confirmation")
    p.add_argument("--example-equity", type=float, default=100_000.0, help="equity for --offline preview")
    p.add_argument("--event-wait-seconds", type=float, default=30.0, help="per-order FSM drain timeout")
    return p.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
