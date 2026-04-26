---
id: KB-1
title: btest DSL Inventory
status: DRAFT
owner: Claude
last_reviewed: 2026-04-26
version: 0.1
sources:
  - btest/src/quantdsl_backtest/dsl/strategy.py        # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/data_config.py     # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/universe.py        # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/factors.py         # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/signals.py         # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/portfolio.py       # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/execution.py       # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/costs.py           # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/backtest_config.py # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/transforms.py      # accessed 2026-04-26
  - btest/src/quantdsl_backtest/data/sources/registry.py  # accessed 2026-04-26
depends_on:
  - KB-13   # companion_projects (btest is the dependency this inventories)
referenced_by:
  - KB-5 strategy_taxonomy §1, §2 (archetypes built from these primitives)
  - KB-6 cost_margin_dictionary (extends costs section)
  - REQUIREMENTS.md §5.1 (strategy ingest)
  - ADR-010 (btest reuse decision)
---

# KB-1 — btest DSL Inventory

## Purpose

Authoritative table of every public dataclass and Protocol in `btest`'s DSL, with broker-neutrality verdict and live-lift implications. This is the SSOT for what `blive` can reuse vs. what needs a live override.

## Scope

In scope: every dataclass under `btest/src/quantdsl_backtest/dsl/`, plus the `DataSource` protocol from `data/sources/`.

Out of scope: factor / signal / portfolio engine internals (covered when needed by specific REQUIREMENTS sections); non-DSL helper modules.

## Verdict legend

- **broker-neutral**: pure spec or pure formula; reusable in blive without modification.
- **backtest-only**: assumes properties (perfect fills, knowable slippage, instant settlement) that don't hold in live.
- **mixed**: structurally neutral, but specific fields require live data to evaluate.

---

## 1. Strategy & Top-Level Composition

### `Strategy` — `dsl/strategy.py:18-37`

The root dataclass binding everything together.

**Fields**: `name: str`, `data: DataConfig`, `universe: Universe`, `factors: dict[str, FactorNode]`, `signals: dict[str, SignalNode]`, `portfolio: LongShortPortfolio | TimingPortfolio`, `execution: Execution`, `costs: Costs`, `backtest: BacktestConfig`.

**Verdict**: **broker-neutral**. Pure spec; describes intent, not how it's executed.

**Live-lift**: blive imports `Strategy` unmodified. The three additive extensions live in `execution.live_overrides`, `costs.live_*_provider` hooks, `risk.live_kill_switch` (REQUIREMENTS §5.1) — none touch the core dataclass.

---

## 2. Data Configuration

### `DataConfig` — `dsl/data_config.py:18-54`

**Fields**: `source: str` (URL, e.g. `parquet://`, `eodhd://`, `ib://`), `calendar: str` (e.g. `XNYS`, `XPAR`), `frequency: str` (e.g. `1d`), `start: str`, `end: str`, `price_adjustment: Literal["raw", "split", "split_dividend"]`, `fields: list[str]`, optional `transforms: list[DataTransform]`.

**Verdict**: **broker-neutral** for historical; live mode resolves `source` to a streaming adapter.

**Live-lift**: registry pattern ([ADR-014](../decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction)) means new schemes (`eodhd://`, `ib://`) plug in without DSL changes.

### `DataTransform` Protocol — `dsl/transforms.py`

`apply(prices, volumes) -> (prices, volumes)`. Used for `CleaningTransform` and similar. **Broker-neutral**: pure function on data; reusable in live with streaming bars.

---

## 3. Universe

### `Universe` — `dsl/universe.py:36-50`

**Fields**: `name: str`, `filters: list[UniverseFilter] = []`, `id_field: str = "ticker"`, `static_instruments: list[str] = []`.

**Verdict**: **broker-neutral**.

**Live-lift**: filters re-evaluate at intra-day intervals; static_instruments resolve to IB `Contract` / `ConID` once at strategy start.

### Filters

| Filter | Fields | Verdict |
|--------|--------|---------|
| `HasHistory` | `min_days: int` | broker-neutral; pure data check |
| `MinPrice` | `min_price: float` | broker-neutral |
| `MinDollarADV` | `min_dollar_adv: float` | broker-neutral; ADV is a window calculation |

---

## 4. Factors

`FactorNode` is the abstract type; concrete subclasses live in `dsl/factors.py:14-100`.

| Factor | Key fields | Verdict |
|--------|-----------|---------|
| `ReturnFactor` | `field, lookback, method (log\|simple)` | broker-neutral; pure window calc |
| `VolatilityFactor` | `field, lookback, method (realized\|...)` | broker-neutral |
| `FiboRetraceFactor` | `field_high, field_low, lookback, level` | broker-neutral |
| `OvernightReturnFactor` | OHLC-derived | broker-neutral |
| `IntradayReturnFactor` | OHLC-derived | broker-neutral |
| `WinsorizedFactor` | wraps inner factor with σ-clipping | broker-neutral |
| `RatioFactor` | numerator / denominator factors | broker-neutral |
| `FieldFactor` | `field` (for aux series) | broker-neutral |
| `ExternalFactor` | `path, loader, per_instrument: bool` | broker-neutral spec; **live-lift care needed** — `path` resolution must work in prod, `loader` is pickled callable, `per_instrument=True` returns wide DataFrame (one column per ticker) — used by A3 strategies |

**Live-lift implications:** factors are pure window calculations and reusable verbatim; `ExternalFactor` is the trickiest because it loads pickled artefacts (e.g. `pred_cache.pkl`). Per [ADR-015](../decisions/DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), v1 consumes static artefacts; freshness window enforced by RiskEngine.

---

## 5. Signals

`Signal` Protocol (`dsl/signals.py:21-32`): `def evaluate(engine: Any) -> Any`. Double-dispatch friendly.

| Signal | Purpose | Verdict |
|--------|---------|---------|
| `NotNull` | mask of non-null entries | broker-neutral |
| `And` / `Or` | logical mask combinators | broker-neutral |
| `LessEqual` / `GreaterEqual` / `Less` / `Greater` | element-wise comparisons; right-hand can be a `Quantile` | broker-neutral |
| `Quantile` | rolling quantile over a factor | broker-neutral |
| `CrossSectionRank` | percentile rank within universe at each time | broker-neutral |
| `CrossSectionAggregate` | per-bar aggregate | broker-neutral |
| `MaskFromBoolean` | wraps a boolean expression as a named mask | broker-neutral |
| `ZScoreRolling` | z-score of factor in rolling window | broker-neutral |

**Verdict overall**: **broker-neutral** — every signal is a pure function over factor panels. The Protocol pattern supports both batch (backtest) and stream (live) evaluation.

---

## 6. Portfolio

### `LongShortPortfolio` — `dsl/portfolio.py:99-122`

Cross-sectional portfolio with two `Book` objects (long, short).

**Fields**: `long_book: Book`, `short_book: Book`, `rebalance_frequency: Literal["1d","1w","1m"]`, `rebalance_at: Literal["market_open","market_close"]`, `signal_delay_bars: int = 0`, `target_gross_leverage: float`, `target_net_exposure: float`, `max_abs_weight_per_name: float`, `sector_neutral: SectorNeutral | None`, `turnover_limit: TurnoverLimit | None`, `debugging: bool`.

**Verdict**: **broker-neutral**.

**Live-lift**: produces target-weight `pd.Series[instrument → float]` via `compute_target_weights_for_date`. The series is the seam between btest and blive — see REQUIREMENTS §5.1 attach point at `backtest_runner.py:967-973`.

### `TimingPortfolio` — `dsl/portfolio.py:125-169`

Single-instrument boolean-driven timing portfolio (used by A2 strategies).

**Fields**: `signal_name: str`, `instrument: str`, `rebalance_frequency`, `rebalance_at`, `signal_delay_bars: int = 1`, `target_leverage: float = 1.0`.

**Verdict**: **broker-neutral**.

**Live-lift**: produces target weight = `target_leverage` (when signal True) or 0.0 (when False). The simplest archetype to lift live (Phase 1).

### `Book` / Selectors / Weighting — `dsl/portfolio.py:12-97`

| Component | Purpose | Verdict |
|-----------|---------|---------|
| `Book` | one side of L/S (name, selector, weighting) | broker-neutral |
| `TopN` / `BottomN` | rank-based selection with `n`, optional mask, `fill_from_unmasked` | broker-neutral |
| `MaskSelector` | select instruments where named boolean signal is True | broker-neutral; used by A3 |
| `EqualWeight` | equal notional across selected | broker-neutral |
| `SectorNeutral` | sector exposure constraint with `tolerance` | broker-neutral; needs sector reference data in live |
| `TurnoverLimit` | `window_bars`, `max_fraction` of gross | broker-neutral |

---

## 7. Execution

### `Execution` — `dsl/execution.py:78-89`

Aggregates the execution sub-spec.

**Fields**: `order_policy: OrderPolicy`, `latency: LatencyModel`, `slippage: PowerLawSlippageModel`, `volume_limits: VolumeParticipation`, `book_model: LimitOrderBookModel | None`.

**Verdict**: **mixed** — `OrderPolicy` is broker-neutral; `LatencyModel`, slippage, LOB model are backtest-only abstractions whose live equivalents come from real fills.

### `OrderPolicy` — `dsl/execution.py:12-24`

`default_order_type: Literal["MKT","MOC","LIMIT"]`, `time_in_force: Literal["DAY","GTC"]`, `fill_on: Literal["close","open"]`.

**Verdict**: **broker-neutral**, but `MOC` and `fill_on` carry backtest semantics. Live mode replaces `fill_on` with real-time semantics; `MOC` maps to IB MOC if supported by exchange.

### `LatencyModel` — `dsl/execution.py:27-34`

`signal_to_order_delay_bars: int`, `market_latency_ms: int`. **Backtest-only**. In live, observed latency replaces the model.

### `PowerLawSlippageModel` — `dsl/execution.py:40-49`

`base_bps + k * (participation ** exponent)` with `use_intraday_vol`. **Backtest-only**. Live uses real fills; the model becomes a parity-reference (live realised slippage compared to model-predicted) per ADR-012.

### `VolumeParticipation` — `dsl/execution.py:52-61`

`max_participation: float`, `mode: Literal["proportional","clip"]`, `min_fill_notional: float`. **Mixed**: spec is broker-neutral; live evaluates against real LOB depth.

### `LimitOrderBookModel` — `dsl/execution.py:64-72`

`levels: int`, `queue_priority: Literal["fifo","pro_rata"]`, `use_spread: bool`. **Backtest-only**. Live mode delegates to IB SMART routing or a configured algo.

---

## 8. Costs

See [KB-6 cost_margin_dictionary](cost_margin_dictionary.md) for full treatment. Brief inventory:

| Component | Verdict |
|-----------|---------|
| `Commission(type, amount)` | **pure formula, broker-neutral, reusable live** |
| `BorrowCost(default_annual_rate, curve_name)` | **mixed** — backtest uses static; live needs per-symbol IB rate |
| `FinancingCost(base_rate_curve, spread_bps)` | **mixed** — backtest uses static SOFR/ESTER; live needs IB tier rate |
| `StaticFees(nav_fee_annual, perf_fee_fraction)` | **pure formula, broker-neutral** |
| `Costs` | container; broker-neutral wrapper |

---

## 9. Backtest Configuration

### `BacktestConfig` — `dsl/backtest_config.py:87-127`

**Fields**: `engine: Literal["event_driven","vectorized"]`, `cash_initial: float`, `margin: MarginConfig`, `risk_checks: RiskChecks`, `drawdown_policy: DrawdownPolicy`, `reporting: Reporting`, plus extra knobs.

**Verdict**: **partially broker-neutral**.

- `cash_initial`: broker-neutral.
- `engine`: backtest-only (live always uses live execution path).
- `margin`: **mixed** — see below.
- `risk_checks` / `drawdown_policy`: **broker-neutral pure formulas**, reusable live (REQUIREMENTS §5.5 and ADR-008).
- `reporting`: backtest-only output spec; live has its own reporting (REQUIREMENTS §5.9).

### `MarginConfig` — `dsl/backtest_config.py:15-23`

`long_initial: float`, `short_initial: float`, `maintenance: float`. **Mixed**: backtest applies global rates; live must apply IB's per-instrument margin rules (queried via broker port).

### `RiskChecks` — `dsl/backtest_config.py:26-X`

`max_drawdown: float`, `max_gross_leverage: float`, `max_daily_loss: float | None`, plus extras.

**Verdict**: **broker-neutral, reusable live**. blive's `RiskEngine` ([ADR-008](../decisions/DECISIONS.md#adr-008--riskengine-no-bypass-enforced-architecturally)) applies the same checks against live equity / leverage.

### `DrawdownPolicy` — `dsl/backtest_config.py:X-X`

`mode: Literal["none","hard_kill","soft_scale"]`, plus parameters. **Broker-neutral pure formula, reusable live**.

### `Reporting` — `dsl/backtest_config.py:X-X`

Backtest output configuration (metrics, output_dir, strategyAnalytics, signalAnalytics). **Backtest-only.**

---

## 10. Data Source Registry

### `DataSource` Protocol — `data/sources/base.py:20-27`

```python
class DataSource(Protocol):
    name: str
    def can_load(self, request: DataRequest) -> bool: ...
    def load(self, request: DataRequest, universe: Universe | None,
             cache: CacheStore | None) -> DataBundle: ...
```

Plus a registry in `data/sources/registry.py` resolving URL schemes to providers.

**Current providers**: `parquet`, `yfinance`, `fred`, `csv`, `sfera`.

**Live-lift**: per [ADR-014](../decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction), implement `eodhd` and `ib` providers; the latter is more than a `DataSource` — it's also a streaming source. blive may need a `StreamingDataSource(Protocol)` extension that yields bars asynchronously.

---

## 11. What blive Provides on Top

The DSL is intentionally not extended in btest itself. blive adds three sidecar fields:

- `execution.live_overrides`: venue-specific (TIF, routing, IB algo, OutsideRTH).
- `costs.live_borrow_provider`, `costs.live_financing_provider`: hooks to query live rates that override the static rates in `BorrowCost` / `FinancingCost`.
- `risk.live_kill_switch`: per-strategy live-only kill criteria distinct from `DrawdownPolicy`.

These are extensions, not modifications — btest remains untouched.

---

## 12. Cross-References

- [REQUIREMENTS §5.1](../../REQUIREMENTS.md) — strategy ingest from btest.
- [KB-5](strategy_taxonomy.md) — archetypes built from these primitives.
- [KB-6](cost_margin_dictionary.md) — deeper treatment of costs/margin.
- [ADR-010](../decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — reuse decision.
- [ADR-014](../decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction) — data-source registry decision.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from btest source.
