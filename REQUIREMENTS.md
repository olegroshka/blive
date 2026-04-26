 # blive — Live Algo Strategy Execution Engine

> **Status:** v0.2 DRAFT — pre-implementation requirements (post-KB pass).
> **Author:** Oleg + Claude.
> **Companion projects:** `btest` (research / backtesting DSL), `harp` (HARP paper). See [KB-13 companion_projects](./docs/kb/companion_projects.md).
> **Companion files in this repo:**
> - [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) — the discipline for editing this and any other artifact. **Read before any edit.**
> - [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) — the registry of all knowledge artifacts (KBs, INVs, DDs, ADRs, OQs).
> - [KB-5 strategy_taxonomy](./docs/kb/strategy_taxonomy.md), [KB-1 btest_dsl_inventory](./docs/kb/btest_dsl_inventory.md), [KB-2 ib_capability_matrix](./docs/kb/ib_capability_matrix.md), [KB-3 ib_pacing_spec](./docs/kb/ib_pacing_spec.md), [KB-4 frameworks_survey](./docs/kb/frameworks_survey.md), [KB-6 cost_margin_dictionary](./docs/kb/cost_margin_dictionary.md), [KB-9 uk_regulatory](./docs/kb/uk_regulatory.md), [KB-10 DECISIONS](./docs/decisions/DECISIONS.md), [KB-11 OPEN_QUESTIONS](./docs/decisions/OPEN_QUESTIONS.md), [KB-12 GLOSSARY](./docs/GLOSSARY.md), [KB-13 companion_projects](./docs/kb/companion_projects.md).
>
> **Purpose of this doc:** establish the smallest set of design decisions strong enough to start building, while leaving open questions explicit. This file is expected to iterate, governed by [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md).
>
> **v0.2 changes vs v0.1**: §9 (solutions survey) collapsed to KB-4 reference; §10 (IB gotchas) collapsed to KB-2 + KB-3 reference; §16 (open questions) collapsed to KB-11 reference; §17 (glossary) collapsed to KB-12 reference; §1, §15 reference ADR-013 phased priority. Cross-references throughout use stable IDs.

---

## TL;DR

`blive` is a long-running execution engine that runs `btest`-DSL strategies against real brokers (Interactive Brokers first), behind a hexagonal `BrokerPort` so other venues plug in as adapters. A backtested strategy graduates to live by importing the same `Strategy` dataclass, choosing a broker adapter, and pressing **Start** in a 3-page web control plane that exposes a kill-switch. The engine guarantees a stated **backtest–live parity contract**, persists every domain event, and recovers from crashes by replaying the log.

---

## 1. Purpose

Bridge `btest` strategies to live broker execution behind clean, broker-agnostic ports.

A strategy I have backtested in `btest` should be deployable to live trading by:

1. Importing the same `Strategy` dataclass (no rewrite, no re-port). The strategies in scope and their archetypes are catalogued in [KB-5 strategy_taxonomy](./docs/kb/strategy_taxonomy.md); the DSL primitives reused from `btest` are inventoried in [KB-1 btest_dsl_inventory](./docs/kb/btest_dsl_inventory.md).
2. Choosing a `blive` adapter (paper, IB, future Alpaca/Tradier). IB is the v1 adapter ([ADR-002](./docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver)); the broker-port shape is hexagonal ([ADR-004](./docs/decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement)).
3. Pressing **Start** in a minimal web UI with a kill-switch ([ADR-011](./docs/decisions/DECISIONS.md#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred)).

v1 scope is **ETF and index strategies only** ([ADR-013](./docs/decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only)). The phased priority is A2 → A3 → A1a (Phases 1, 2, 3); leveraged variants, A3 generalisation, and UK equities are Phase 4+ (post-M8).

The engine guarantees a backtest–live **parity contract** (Section 8) so live results track simulated results within stated tolerance, and any divergence is observable, attributable, and not silent ([ADR-012](./docs/decisions/DECISIONS.md#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)).

---

## 2. What blive IS

- A long-running execution engine for systematic strategies authored in the `btest` DSL.
- Broker-agnostic core; pluggable adapters (IB, paper, mock; future Alpaca / Tradier / Schwab / CCXT).
- Crash-only design with externalised state and an append-only event log; restart path = cold-start path.
- Single-process, single-asyncio-loop kernel for deterministic event ordering.
- A pre-trade RiskEngine that no order can bypass.
- A minimum-but-comprehensive web control plane (3 pages, see §5.8).

## 3. What blive IS NOT

- **Not a backtester** — `btest` owns research, replay, parameter sweeps.
- **Not a discretionary OMS/EMS** — no manual order ticket UI.
- **Not multi-tenant SaaS** — single-operator, one or a few accounts.
- **Not HFT** — sub-second roundtrip is the target, not microseconds.
- **Not a smart router across multiple brokers** — broker is selected per strategy.
- **Not a research IDE** — strategies are authored in `btest`, deployed in `blive`.

---

## 4. Guiding Principles

| # | Principle | Enforced by |
|---|-----------|-------------|
| 1 | Domain depends only on ports | Hexagonal layer split; `import ib_async` is forbidden anywhere outside `adapters/ib/`. Verified by an import-linter rule. |
| 2 | Every order goes through the RiskEngine | Architectural — `Strategy` cannot reach `BrokerPort` without traversing `RiskEngine`. No bypass API exists. |
| 3 | Persist every domain event; externalise state | Append-only event log + periodic snapshots. Restart == cold start. |
| 4 | Backtest = Live, modulo data + venue | `FactorEngine`, `SignalEngine`, `PortfolioEngine` are imported from `btest` and not reimplemented. |
| 5 | Deterministic single-thread asyncio | One event loop in the domain. Adapters may use threads internally but must hand off via async queues. |
| 6 | Adapters are dumb | Parse venue protocol → emit domain events. No business rules in adapters. |
| 7 | Fail loud, fail fast | Structured errors with cause chain. No silent retries beyond declared policy. Default action under uncertainty: kill-switch. |
| 8 | The parity diagnostic is the canary | A daily replay of realised fills through `btest` is a first-class operational artefact (see §8). |

---

## 5. Functional Requirements

### 5.1 Strategy Ingest from btest

`blive` imports an unmodified `btest.Strategy` dataclass. All DSL nodes (`DataConfig`, `Universe`, factors, signals, `LongShortPortfolio`, `TimingPortfolio`, `Execution`, `Costs`, `BacktestConfig`) carry the same meaning as in `btest`, with three additive extension points:

- `execution.live_overrides` — venue-specific overrides (TIF, routing tag, IB algo, `OutsideRth`).
- `costs.live_borrow_provider`, `costs.live_financing_provider` — hooks to query live rates instead of static values.
- `risk.live_kill_switch` — per-strategy kill criteria distinct from backtest `DrawdownPolicy`.

Strategies that depend on backtest-only constructs without a live counterpart (e.g. `LimitOrderBookModel` with no paired live execution algo) cause `blive` to refuse to start with an explicit error naming the offending field.

The natural attach point is the `target_weights` series produced by `PortfolioEngine.compute_target_weights_for_date` (`btest/engine/backtest_runner.py:967-973`). `blive` consumes that series and replaces what `btest` does next (`rebalance_to_target_weights`, line 1042) with live submission, fill tracking, and reconciliation.

### 5.2 Live Market Data

- Implement `MarketDataPort` with fan-in from one or more adapters (the IB adapter is one of many possible).
- Day-1 capability: bar streams (1-minute, 5-minute, 1-day) and trade ticks. Quote-level and depth are flagged for M3+.
- Subscription budget management: IB has paid tiers per exchange (Network A/B/C, OPRA, etc.); the adapter surfaces tier shortfall as a clear error rather than IB's cryptic codes.
- Late-tick / out-of-order handling: a monotonic-timestamp invariant per instrument; out-of-order ticks dropped with a counter incremented and an event emitted.
- Clock-skew detection: every adapter timestamp compared to `ClockPort.now()`; skew > threshold (default 2 s) is a kill-switch trigger.
- Historical bar fetch (for warm-start of factors): respects IB pacing limits (≤ 60 `reqHistoricalData` per 10 min, BID_ASK counts double).

### 5.3 Order Submission & Lifecycle

`blive`-native `Order` dataclass — broker-neutral, never an `ib_async.Order`:

```
Order(
    client_order_id: UUID,           # blive-generated, owned through full lifecycle
    strategy_id: StrategyId,
    instrument: Instrument,
    side: Literal["BUY", "SELL"],
    quantity: Decimal,
    order_type: Literal["MKT", "LMT", "MOC", "LOC", "STP", "STP_LMT"],
    time_in_force: Literal["DAY", "GTC", "IOC", "FOK", "OPG"],
    limit_price: Decimal | None,
    stop_price: Decimal | None,
    parent_id: UUID | None,
    tags: dict[str, str],            # routing hints, algo params, audit context
    created_at: datetime,
)
```

Order finite-state machine:

```
INITIALIZED → SUBMIT_PENDING → SUBMITTED → ACCEPTED
                                              ↓
                                        PARTIALLY_FILLED ─→ FILLED
                                              ↓
                                  CANCELED | REJECTED | EXPIRED
```

Every transition emits a typed domain event (`OrderSubmitted`, `OrderAccepted`, `OrderPartiallyFilled`, `OrderFilled`, `OrderCanceled`, `OrderRejected`, `OrderExpired`). Illegal transitions raise — they are not a runtime concern.

Idempotency: re-submitting the same `client_order_id` is a no-op that returns the existing order's current state.

Cancel and replace are separate FSM actions; replace is modelled as `CancelReplace(client_order_id, new_fields)` and may be implemented as cancel-then-new on venues that don't support atomic replace.

### 5.4 Position & Account State

- `Position(instrument, qty, avg_cost, currency, opened_at, updated_at)`.
- `AccountSnapshot(equity, cash_by_ccy, buying_power, gross_exposure, net_exposure, leverage, margin_used, taken_at)`.
- State is updated on `Fill`, `AccountUpdate`, or reconciliation tick. Never derived from the order log alone — fills and venue snapshots are authoritative.
- Multi-currency from M1: cash leg per ccy. FX P&L attribution may follow later; for v1, daily mark using IB conversion rates is sufficient.
- Per-strategy attribution: positions opened by strategy A are tagged so that B's risk checks see only B's slice.

### 5.5 Risk Engine & Kill-Switch

**Pre-trade checks** (every order, in order):

| Check | Default threshold |
|-------|-------------------|
| Strategy gross leverage | `BacktestConfig.risk.max_gross_leverage` (e.g. 2.0) |
| Strategy net exposure | `LongShortPortfolio.target_net_exposure` ± 0.10 |
| Per-name max abs weight | `LongShortPortfolio.max_abs_weight_per_name` (e.g. 0.03) |
| Daily loss vs. session-start equity | -2.0% soft warn, -3.5% hard kill |
| Order rate per strategy | ≤ 5/sec, ≤ 60/min |
| Order rate global | ≤ 20/sec (well below IB 50/s) |
| Position concentration | single-name notional ≤ 8% of strategy NAV |
| Stale data | refuse if last bar > 5 min old (intraday) or > 1 day (EOD) |
| Market hours | refuse if not RTH unless `Execution.live_overrides.outside_rth=True` |
| Reference price sanity | refuse if limit price > ±20% from last trade |

All thresholds overridable per strategy via YAML; defaults intentionally conservative.

**Kill-switch** halts new submissions across all strategies, cancels open orders (configurable per strategy: cancel vs. let-fill), and holds existing positions until explicit human resume.

Trigger sources:

- Manual: web UI button + `POST /system/kill_switch` (idempotent).
- Auto: IB disconnected > 30 s, intraday equity drop > 5%, ≥ 5 rejects in 60 s, `ClockPort` skew > 2 s, persistence write failure, market-data heartbeat lost > 60 s.

The kill-switch state is persistent — a crash mid-kill stays killed on restart until a human clears it via `POST /system/clear_kill_switch` with a confirmation token.

### 5.6 Modes: Paper / IB Paper / Shadow / Live

| Mode | Adapter | Order submission | Use |
|------|---------|------------------|-----|
| **Paper** | local in-process matcher | simulated fills using btest cost models | dev, smoke, CI, parity tests |
| **IB Paper** | IB Gateway, paper account | real IB infrastructure with simulated fills | end-to-end pre-prod, IB-specific bugs |
| **Shadow** | live IB data + adapter; submission stubbed to log | none — orders are logged but never sent | observe-only validation in real markets |
| **Live** | IB live account | real | production |

Mode is a runtime flag, never a code branch in the domain layer.

Shadow mode in particular is a first-class promotion gate: a strategy must run clean in shadow for a configurable window (default 5 trading days) before live promotion, with parity diagnostic green throughout.

### 5.7 Reconciliation

**Startup reconciliation**: query venue for `(open_orders, positions, account_values)`. Diff against persisted state. Synthesise missing transitions to bring local state in line. Venue is authoritative on conflicts.

**Continuous reconciliation**: every 60 s, repeat the diff. Emit `OrderDriftDetected` / `PositionDriftDetected` / `AccountDriftDetected` events on mismatch. Drift triggers an alert, not (immediately) the kill-switch — drift is expected on reconnect transients.

**Daily TWS restart at 23:45 ET**: treated as a normal operational event. Engine pauses submission, awaits reconnect, runs full reconciliation, resumes. The window must be configurable per IB region.

**Cold restart**: reload event log from last snapshot offset; replay; reconcile; resume in `paused` state and require explicit human resume — never auto-resume into live submission after an unclean shutdown.

### 5.8 Web Control Plane (3 pages, dashboard-centric)

| # | Page | Content | Actions |
|---|------|---------|---------|
| 1 | **Dashboard** | All strategies (name, mode, status, today P&L, equity, leverage); global account stats; connection status; **kill-switch button**. | Start / Stop / Pause / Resume / Flatten per strategy; global kill / clear-kill. |
| 2 | **Strategy** | One strategy: equity curve (intraday / week / month); positions table; recent orders; recent fills; structured-log tail (SSE); param overrides form. | Edit & restart with overrides; flatten; export run snapshot. |
| 3 | **System** | Connections (IB Gateway / market data); reconciliation status; last event-log offset; version & build hash; alert history; backup status. | Trigger reconciliation; trigger backup; force-disconnect (operational tool). |

Logs are accessible via SSE from any page; no separate Logs page.

REST endpoints for everything the UI does (the UI is just a client of the REST surface). Auth: shared-secret bearer token + TLS for v1; OAuth/SSO is M9+.

### 5.9 Observability

- Structured JSON logs (one record per line) to disk + stdout.
- Per-event correlation id traces an order through signal → submission → ack → fill → P&L update.
- Prometheus metrics on `:9100`: orders/sec by status, fills/sec, equity gauge, leverage gauge, IB throttle headroom, reconciliation drift counters, kill-switch-armed gauge, latency histograms (signal→submit, submit→ack, ack→fill).
- Grafana dashboard JSON committed to repo.
- Alerts (configurable channels: Slack / email / SMS): kill-switch triggered, broker disconnect > 30 s, drawdown threshold crossed, reject storm, parity residual outside band, daily summary.

### 5.10 Strategy Parameter Override at Runtime

A strategy can be (re)started with a parameter override applied to the resolved YAML config.

**Allowed overrides (whitelist):**

- Scalars in `factors.{name}.{param}` (e.g. lookback windows).
- Scalars in `signals.{name}.{param}` (thresholds, ranks).
- Numeric fields of `LongShortPortfolio` / `TimingPortfolio` (`target_gross_leverage`, `signal_delay_bars`, etc.).
- Numeric fields of `RiskChecks`, `DrawdownPolicy`.
- `execution.live_overrides.*`.

**Forbidden overrides:**

- Type fields (e.g. swapping `ReturnFactor` for `VolatilityFactor`) — that is a new strategy, not an override.
- Universe definition (`Universe.filters`, `static_instruments`) — same reason.
- Anything that changes the topology of factor/signal DAGs.

The override is captured as a snapshot in the run record. The override grammar is JSON Patch (RFC 6902) operating on the resolved config tree; whitelist is enforced before patch application.

### 5.11 Time & Calendar

- `ClockPort` abstracts wall-clock (live), simulated clock (paper), and replay clock (replay tests). Domain code never touches `datetime.now()` directly — that is an import-linter rule.
- Trading calendars sourced via the same provider `btest` uses (`exchange_calendars` / `pandas_market_calendars`); calendar version pinned in run snapshot.
- All persisted timestamps are UTC; UI displays in the user's configured timezone.
- Holiday handling: market closure forces pause; partial sessions (early close) handled by `rebalance_at` translation rules.

### 5.12 Strategy Versioning & Migration

Every running strategy carries a `strategy_spec_id = sha256(resolved_yaml + dsl_lib_version + btest_version + blive_version)`. The id is recorded with every domain event.

If `btest` releases a DSL-breaking change, an existing live run continues on its frozen spec; the operator must explicitly migrate via Stop → upgrade → Start with a new spec id. The run history tracks the spec lineage.

### 5.13 Sizing, Strategy Discovery & Initial Position Ramp

**Sizer** sits between `PortfolioEngine` and the `RiskEngine` and is a first-class domain component. It converts `target_weights: pd.Series[instrument → float]` into `desired_orders: list[Order]` accounting for:

- Lot size / minimum trade size (e.g. options contracts, futures contract size, fractional-share availability per IB account class).
- Currency and FX leg (a UK account trading USD instruments requires implicit or explicit FX conversion; sizer chooses).
- IB margin per instrument (queried via the broker port, not assumed from `MarginConfig`).
- Open positions (delta from current → target, not absolute).

Sizing is deterministic and pure given inputs — it has no side effects and is fully unit-testable.

**Strategy discovery** mirrors `btest`'s `platform_api` pattern: strategies live as Python modules under a configured search path; each module exposes `build_strategy(config: dict) -> Strategy`. The UI enumerates discovered strategies via `GET /strategies`. Strategy definitions are read at startup; hot-reload is a M8+ concern.

**Initial position ramp**: a strategy starting from flat with target weights ≠ 0 cannot slam to target on day 1 without breaking the volume-participation cap and likely incurring large impact. The sizer applies a configurable **ramp policy** per strategy:

| Policy | Behavior |
|--------|----------|
| `immediate` | full target on first rebalance (use only for tiny positions) |
| `linear(N)` | reach target over N rebalance dates, equal increments |
| `vwap_capped(p)` | step-size capped at p% of trailing ADV per day |
| `manual` | block submission until operator confirms initial trades |

Default is `vwap_capped(0.05)` — 5% of ADV per rebalance — which respects `VolumeParticipation.max_participation` even on cold start. A symmetric **wind-down policy** applies on `Stop` with a flatten request.

---

## 6. Non-Functional Requirements

### 6.1 Latency

- Tick → order submit, p50 < 100 ms; p99 < 500 ms (single-strategy, normal load).
- Order submit → ACCEPTED, p50 < 250 ms (network-bounded by IB; budget for adapter overhead < 20 ms).
- Web UI command → effect, p99 < 1 s.

### 6.2 Reliability

- RTO (recovery time objective) < 60 s after engine crash, via event-log replay.
- RPO (recovery point objective) = zero loss of acknowledged events; in-flight pre-ack orders may need reconciliation, never duplication.
- Process supervision: systemd unit or Docker `restart: always`; supervisor restart count alerted above 3/hour.
- Daily backup of event log + snapshots to S3-compatible store; restore test in CI weekly.

### 6.3 Security & Audit

- Credentials in OS keyring or env; never in repo or logs (log redaction list enforced).
- TLS on the web UI from M1 (self-signed acceptable for single-host; Let's Encrypt path documented).
- Two token classes: `monitor` (read-only) and `operator` (read-write). Kill-switch is `operator` only.
- Append-only audit entry per mutating REST call: `(timestamp, token_subject, ip, action, payload_hash, result)`.
- Audit log is hash-chained from M2 (each entry's hash includes the prior entry's hash) — tamper-evident.
- UK considerations: even non-MiFID retail trading benefits from a clear trade-tape export. Generate end-of-day NDJSON of `(orders, fills, positions)` that can feed downstream tax/MiFID-style reporting if required later.

### 6.4 Performance Footprint

- Single host: 4 vCPU / 16 GB RAM target.
- ≤ 50 instruments under active subscription per default IB tier; degrade gracefully with explicit "tier insufficient" error otherwise.
- Event-log write throughput ≥ 1000 events/s sustained on commodity SSD.

### 6.5 Data Retention

| Class | Default retention | Notes |
|-------|-------------------|-------|
| Domain events (orders/fills/positions) | 7 years | regulatory-friendly |
| Account snapshots | 2 years | sampled at 30 s |
| Bar/trade tape | 90 days | longer is `btest`'s job |
| Application logs | 30 days | rotate daily, gzip |
| Audit entries | 7 years | hash-chained |
| Snapshots (state) | last 14 + monthly | for fast restart |

All retention windows are configurable.

---

## 7. Architecture Sketch

### 7.1 Layer Diagram

```
┌──────────────────────── blive/ ────────────────────────────────┐
│                                                                │
│  ┌────────────────────── domain ────────────────────────────┐  │
│  │  Strategy (from btest.dsl, unmodified)                   │  │
│  │       │                                                  │  │
│  │       ▼                                                  │  │
│  │  FactorEngine  →  SignalEngine  →  PortfolioEngine       │  │
│  │       (re-exported from btest.engine, same code path)    │  │
│  │       │                                                  │  │
│  │       ▼  target_weights / target_positions               │  │
│  │  Sizer (§5.13: lots, FX, IB margin, ramp policy)         │  │
│  │       │                                                  │  │
│  │       ▼  desired_orders                                  │  │
│  │  RiskEngine ── reject ──→ RiskBreachEvent                │  │
│  │       │                                                  │  │
│  │       ▼  approved_orders                                 │  │
│  │  ExecutionEngine                                         │  │
│  │       │                                                  │  │
│  │  ┌────┴── Ports ──────────────────────────────────────┐  │  │
│  │  │ BrokerPort        MarketDataPort       ClockPort   │  │  │
│  │  │ PersistencePort   EventBusPort         AlertPort   │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ▲                                   │
│  ┌──────────────────── adapters ──────────────────────────┐    │
│  │  IBBroker (ib_async)   IBMarketData    PaperBroker     │    │
│  │  WallClock             SimClock        SQLitePersist   │    │
│  │  InProcessBus          AlertSlack      AlertEmail      │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────── control plane ─────────────────────────┐    │
│  │  FastAPI + Vite/React (mirrors btest stack)            │    │
│  │  3 pages, REST + SSE; same process as engine in v1.    │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 Ports

```python
class BrokerPort(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def submit(self, order: Order) -> ClientOrderId: ...
    async def cancel(self, client_order_id: ClientOrderId) -> None: ...
    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None: ...
    async def open_orders(self) -> list[Order]: ...
    async def positions(self) -> list[Position]: ...
    async def account_snapshot(self) -> AccountSnapshot: ...
    def events(self) -> AsyncIterator[BrokerEvent]: ...

class MarketDataPort(Protocol):
    async def subscribe_bars(self, instrument: Instrument, freq: BarFreq) -> AsyncIterator[Bar]: ...
    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]: ...
    async def unsubscribe(self, instrument: Instrument) -> None: ...
    async def historical_bars(
        self, instrument: Instrument, freq: BarFreq, start: datetime, end: datetime
    ) -> list[Bar]: ...

class ClockPort(Protocol):
    def now(self) -> datetime: ...
    async def sleep(self, seconds: float) -> None: ...

class PersistencePort(Protocol):
    async def append(self, event: DomainEvent) -> EventOffset: ...
    async def read_from(self, offset: EventOffset) -> AsyncIterator[DomainEvent]: ...
    async def snapshot(self, key: str, blob: bytes) -> None: ...
    async def load_snapshot(self, key: str) -> bytes | None: ...

class AlertPort(Protocol):
    async def send(self, severity: Severity, subject: str, body: str) -> None: ...

class EventBusPort(Protocol):
    def publish(self, topic: str, event: DomainEvent) -> None: ...
    def subscribe(
        self, topic: str, handler: Callable[[DomainEvent], Awaitable[None]]
    ) -> SubscriptionId: ...
```

### 7.3 Concrete Domain Event Shapes

```python
# Market data
@dataclass(frozen=True, slots=True)
class Bar:
    instrument: Instrument
    open_time_utc: datetime
    close_time_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None

@dataclass(frozen=True, slots=True)
class Trade:
    instrument: Instrument
    time_utc: datetime
    price: Decimal
    quantity: Decimal
    aggressor: Literal["BUY", "SELL", "UNKNOWN"]

# Broker events
@dataclass(frozen=True, slots=True)
class Fill:
    client_order_id: UUID
    venue_order_id: str
    venue_exec_id: str
    instrument: Instrument
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    price: Decimal
    commission: Decimal
    currency: str
    time_utc: datetime

@dataclass(frozen=True, slots=True)
class OrderEvent:
    client_order_id: UUID
    venue_order_id: str | None
    kind: Literal["SUBMITTED", "ACCEPTED", "PARTIAL_FILL", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]
    reason: str | None
    time_utc: datetime
```

---

## 8. Backtest–Live Parity Contract

`blive` and `btest` share these code paths verbatim:

- `Strategy` and all DSL nodes.
- `FactorEngine`, `SignalEngine`, `PortfolioEngine`.
- Pure cost formulas: `Commission` (per-share / bps), `StaticFees`.
- Risk math: `DrawdownPolicy`, `RiskChecks`.

`blive` and `btest` necessarily diverge here, with documented expected envelopes:

| Concern | Backtest | Live | Expected residual envelope |
|---------|----------|------|----------------------------|
| Slippage | `PowerLawSlippageModel` | Real fills | ±5 bps per trade typical for liquid US equities |
| Borrow cost | `BorrowCost.default_annual_rate` | IB live rate per symbol | ±25 bps annualised on short notional |
| Financing | `FinancingCost` curve + spread | IB tier rate | ±15 bps annualised on financed notional |
| Margin | `MarginConfig` global | IB per-instrument | structural; logged, not bounded |
| Volume cap | `VolumeParticipation` vs ADV | Real LOB depth | structural |
| Order book | `LimitOrderBookModel` | IB SMART routing | structural |
| Calendar | btest calendar | IB venue calendar | should match exactly; mismatch = bug |

**Parity diagnostic** runs at two cadences:

- **Daily (mandatory)**: take the day's realised fills + EOD positions + EOD account values, replay through `btest`'s vectorised engine starting from yesterday's positions, report `(realised_pnl, simulated_pnl, residual_bps)` per strategy. Aggregate residual outside ±15 bps over 5 trading days raises a `ParityBreach` alert. The diagnostic output is checked into the run snapshot daily.
- **Continuous (M7+)**: a parallel `btest`-paper replica runs alongside live with the same data feed, producing simulated fills in lock-step. Live vs. simulated divergence per fill is monitored as a metric; sustained divergence beyond expected envelope (above) emits the same `ParityBreach`. This catches drift hours before the daily report would.

This is one of the load-bearing principles. If the parity diagnostic is broken or skipped, the engine is in degraded mode by definition.

---

## 9. Existing Solutions Survey

Full structured survey lives in [KB-4 frameworks_survey](./docs/kb/frameworks_survey.md). Headline:

- **Adopt**: `ib_async` v2.1+ (BSD-2; actively maintained at `ib-api-reloaded`). Wire-level driver inside the `IBBroker` adapter only. Pin `>=2.1,<2.2`. **Never imported above the adapter layer** ([ADR-002](./docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver), [ADR-004](./docs/decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement)).
- **Study (do not depend)**: NautilusTrader (architecture reference per [ADR-003](./docs/decisions/DECISIONS.md#adr-003--borrow-nautilustrader-architecture-do-not-depend)); Hummingbot (order-lifecycle event names); Lumibot (`Broker` subclass shape, **not** the polling lifecycle); vnpy (80+ gateway proof of the pattern).
- **Reject**: QuantConnect Lean (C# wrong shape), Backtrader live (dead), Zipline+pylivetrader (Alpaca-skewed), QSTrader (live not delivered), QuantRocket (commercial monolith), PyAlgoTrade / Catalyst (dead), native `ibapi` (too low-level), CPAPI (operationally worse).

The decision shape is **borrow architecture, not code**: NautilusTrader's `Strategy` would compete with `btest`'s DSL; we lift the patterns and own the domain. See [KB-4 §"Architectural Patterns to Copy"](./docs/kb/frameworks_survey.md#architectural-patterns-to-copy-cross-cutting) for the 10-point pattern list.

---

## 10. IB-Specific Gotchas (must be first-class in adapter)

Full IB capability matrix is [KB-2](./docs/kb/ib_capability_matrix.md); numerical pacing limits with sources are [KB-3](./docs/kb/ib_pacing_spec.md). The 12 gotchas the adapter must handle:

| # | Gotcha | Mitigation in adapter | Reference |
|---|--------|----------------------|-----------|
| 1 | 50 msg/sec throttle (3 violations terminate session) | Token-bucket; default global cap 20/sec | [KB-3 §1](./docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle) |
| 2 | Historical data pacing (≤60/10min, BID_ASK ×2) | Pacer wraps `historical_bars`; queues backlog | [KB-3 §2](./docs/kb/ib_pacing_spec.md#2-historical-data-pacing) |
| 3 | `orderId` monotonic management; multi-client races | Single master client owns counter; persisted | [KB-3 §4](./docs/kb/ib_pacing_spec.md#4-order-id--multi-client) |
| 4 | Daily TWS restart at 23:45 ET | First-class op event; pause + reconcile on reconnect | [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) |
| 5 | Ghost orders after disconnect | `reqAllOpenOrders` + `reqPositions`; venue authoritative; synthesise events | [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) |
| 6 | `reqMktData` vs `reqTickByTickData` budgets | Default 250 ms aggregated; explicit per-instrument upgrade | [KB-3 §3](./docs/kb/ib_pacing_spec.md#3-market-data-subscription-tiers) |
| 7 | Paid market-data tier prerequisites | Tier check at subscribe; explicit "tier missing" error | [KB-3 §3](./docs/kb/ib_pacing_spec.md#3-market-data-subscription-tiers) |
| 8 | 2FA on IB Gateway | Weekly token + IBC; `gnzsnz/ib-gateway-docker` or equivalent | [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) |
| 9 | TWS auto-update breaks IBC | Pin offline TWS installer; auto-update disabled | [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) |
| 10 | `Order.Transmit=False` is session-local | Used internally for OCA construction; never persisted | [KB-3 §6](./docs/kb/ib_pacing_spec.md#6-ordertransmitfalse-footgun) |
| 11 | Multi-client `clientId` master/non-master visibility | `blive` is the single master client; manual TWS read-only from our POV | [KB-3 §4](./docs/kb/ib_pacing_spec.md#4-order-id--multi-client) |
| 12 | SMART vs primary exchange routing | Explicit `Execution.live_overrides.routing`; never silent default | [KB-2 §5](./docs/kb/ib_capability_matrix.md#5-routing) |

---

## 11. Data Model & Persistence

| Entity | Storage shape | Lifecycle |
|--------|---------------|-----------|
| `StrategySpecSnapshot` | append-only table; PK = spec_id (sha256) | immutable; one row per resolved YAML |
| `LiveRun` | mixed: row + lifecycle events | row mutates `status`; events append |
| `Order` | event-sourced from `OrderEvent` log | rebuilt from log; latest snapshot every N events |
| `Fill` | append-only | one row per execution |
| `Position` | derived from fills + corp actions | snapshot daily; rebuilt from event log if needed |
| `AccountSnapshot` | append-only sample every 30 s | TTL per §6.5 |
| `RiskBreach` | append-only | indexed by strategy_id |
| `AlertEvent` | append-only | indexed by severity, time |
| `AuditEntry` | append-only, hash-chained from M2 | tamper-evident |

**Storage v1**: SQLite (single file, simple backup, plenty fast at < 100 events/s sustained for our load). Migration path to Postgres documented but not built. The choice is intentional: our event volume is bounded by trade frequency, not market data — all market data flows through memory, not the event log.

---

## 12. Operational Model

- Single host: Linux preferred, Windows supported (the user runs Windows 11 daily; production target is Linux VM/box).
- IB Gateway in Docker (`gnzsnz/ib-gateway-docker` or equivalent); `blive` connects locally over loopback.
- `blive` runs as a systemd service or Docker container with `restart: always`.
- Daily backup of event log + snapshots to S3-compatible store; weekly restore drill in CI.
- Monitoring: Prometheus scrape from `:9100`; Grafana dashboard JSON committed.
- Daily TWS-restart window (23:45 ET): engine pauses → reconciles → resumes.
- Disaster recovery: cold-start from latest snapshot + replay tail; documented in `RUNBOOK.md` (M5 deliverable).
- Versioning: `blive` ships with a build hash visible in System page; rolling deploy = stop / replace / start; no in-place upgrade with active strategies.

---

## 13. Test Strategy

### 13.1 Test Levels

- **Unit**: per port adapter (mock the wire), per FSM transition, per risk check; `tests/unit/` mirrors source. Target ≥ 85% line coverage on core domain.
- **Integration**: against IB Paper account, gated and manual. Exercises full round-trip including reconnect, partial fill, cancel, reject, daily restart.
- **Replay**: record live event tape to NDJSON; deterministically replay through engine; assert state convergence. The same NDJSON is the gold artefact for crash-recovery tests.
- **Parity**: take a `btest` result; run `blive` in `paper` mode with deterministic data; assert end-of-day P&L matches within tolerance from §8.
- **Property-based**: order FSM transitions (`hypothesis`) — no path leads to an illegal state.

### 13.2 Chaos Catalog

Faults injected in chaos tests; engine must remain consistent:

- TCP drop mid-submit (before ACK).
- TCP drop mid-fill (after partial).
- Out-of-order fill events.
- Duplicate fill event with same `venue_exec_id`.
- Reject storm (10 rejects in 5 s).
- Clock-skew (adapter clock 5 s ahead, then 5 s behind).
- Persistence write failure (disk full / read-only mount).
- Slow venue (ack delay 30 s).
- TWS restart at 23:45 (simulated).
- Venue replies with positions that don't match local state.
- IB throttle hit (50 msg/sec exceeded by load test).
- 2FA timeout on IB Gateway.
- Audit-log hash-chain mismatch (simulated tamper).
- Snapshot file truncated mid-write.
- SQLite WAL replay after kill -9.
- Parity diagnostic itself raises (e.g. `btest` import fails on upgrade) — engine must enter degraded mode, not crash.

### 13.3 CI Layout

Mirrors `btest`: `tests/unit` runs in CI by default; `tests_slow/` for replay + parity; `tests_chaos/` gated; `tests/integration_ib_paper/` requires credentials and is manual.

---

## 14. Phased Delivery

| M | Deliverable | Verification |
|---|-------------|--------------|
| **M0** | Repo skeleton; ports; domain types (`Order`, `Fill`, `Position`, etc.); `PaperBroker`; in-memory persistence | unit tests green |
| **M1** | `btest.Strategy` import; `FactorEngine`/`SignalEngine`/`PortfolioEngine` reuse; PaperBroker round-trip | a `TimingPortfolio` runs in `blive`-paper, equity curve matches `btest` exactly |
| **M2** | IB adapter, read side: connect, positions, account values, market-data subscribe | manual: connect to IB Paper; positions match TWS UI; pacing tests |
| **M3** | IB adapter, write side: submit, cancel, replace; full FSM | manual: round-trip 5 orders against IB Paper; FSM transitions logged; reject path exercised |
| **M4** | RiskEngine + kill-switch; SQLite persistence; structured logging | unit + chaos tests pass; kill-switch from web `curl` halts new orders |
| **M5** | Reconciliation (startup + continuous); daily TWS-restart handling; runbook | integration: kill engine mid-trade, restart, no drift |
| **M6** | Web UI (3 pages); REST endpoints; SSE log stream | manual end-to-end on IB Paper |
| **M7** | Parity diagnostic + alerts; observability (Prometheus + Grafana) | parity test passes on 3 strategies; alert routes verified |
| **M8** | Hardening: TLS, audit-log hash chain, backup automation, ops runbook | 2-week unattended paper trade clean |

Real-money cutover gated by M8 + manual sign-off + a documented kill-switch drill.

---

## 15. Out of Scope (v1)

Per [ADR-013 phased priority](./docs/decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only), v1 focus is **ETF and index strategies only**. Out of scope:

- **Single-name cross-sectional strategies** (A1: SP500 momentum L/S, harp quarterly, etc.) — deferred to post-M8.
- **UK equity strategies** — deferred to post-M8 per [ADR-018](./docs/decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8); UK-LC / UK-MC universes from `equities/smim/*` are candidate sources when revisited.
- **A3 generalisation** to additional leveraged-ETF pairs (SOXL/SQQQ, UPRO/SPXU, sector rotations) — engine kept generic but concrete generalisation deferred to Phase 4+ per [ADR-019](./docs/decisions/DECISIONS.md#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs).
- **Online ML training** inside `blive` — assumed live-trained eventually but training is out of v1 per [ADR-015](./docs/decisions/DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1); v1 consumes static artefacts only.
- **F1+ frequencies** (hourly, 5-min, 1-min, tick) — architecturally not precluded ([KB-5 §4 frequency roadmap](./docs/kb/strategy_taxonomy.md#4-frequency-roadmap)) but no v1 strategy operates above F0 (daily).
- Multi-tenant / multi-user.
- HFT-grade latency.
- Smart routing across multiple brokers.
- Options / futures (out of v1 per [ADR-013](./docs/decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only); architectural slot reserved per [KB-5 §2 A6/A8](./docs/kb/strategy_taxonomy.md#future-archetypes-architectural-slots-not-v1-scope)).
- Portfolio-level optimisation at execution time (TCA solvers, Almgren–Chriss schedules).
- Tax-lot accounting (operator handles via accountant; KB-9 records the trade tape).
- Cross-strategy risk overlay (strategies treated as independent; aggregate guard by global kill-switch only).
- Dark pools / IOC / ICEBERG order types beyond what IB SMART exposes.
- Mobile UI; OAuth/SSO ([ADR-011](./docs/decisions/DECISIONS.md#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred)).

---

## 16. Open Questions

Full OQ register lives in [KB-11 OPEN_QUESTIONS](./docs/decisions/OPEN_QUESTIONS.md) (22 OQs catalogued). Status snapshot:

- **8 RESOLVED-BY-ADR-NNN** (formally recorded in [KB-10 DECISIONS](./docs/decisions/DECISIONS.md)): OQ-013 (v1 ETF/index scope), OQ-014 (data sources clean abstraction), OQ-015 + OQ-018 (ML training: live-trained eventually, static for v1, training out of scope), OQ-016 (both leverage paths), OQ-019 (hybrid live data), OQ-021 (UK deferred post-M8), OQ-022 (A3 generalises).
- **1 RESOLVED** (factual finding): OQ-017 (Triple Leveraged ETF instrument set is `{TQQQ, TMF, IEF}`).
- **1 OPEN**: OQ-012 (parity tolerance bands; calibrate at M7).
- **12 IN_DISCUSSION** with working defaults: OQ-001 (single vs split process), OQ-002 (event bus), OQ-003 (persistence), OQ-004 (`ib_async` dependency strategy), OQ-005 (strategy isolation), OQ-006 (intra-bar richness), OQ-007 (FX), OQ-008 (UI auth), OQ-009 (btest reuse), OQ-010 (capital allocation), OQ-011 (CLI), OQ-020 (multi-currency P&L; same as OQ-007).

---

## 17. Glossary

Full glossary lives in [KB-12 GLOSSARY](./docs/GLOSSARY.md). Key terms used in this document: Adapter, Archetype, `client_order_id`, Domain event, FSM, Hexagonal architecture, Kill-switch, Parity contract / envelope / diagnostic / residual, Port, Reconciliation, Shadow mode, Spec id, SSOT, Stable id, TIF, TKAN, Tradable proxy.

The glossary is authoritative ([CONTEXT_PROTOCOL §2.7](./CONTEXT_PROTOCOL.md)) — if any other artifact in this repo disagrees with KB-12 on a term's meaning, the glossary wins.

---

## 18. Naming Note

Decision recorded as [ADR-001 Adopt project name `blive`](./docs/decisions/DECISIONS.md#adr-001--adopt-project-name-blive). Pairs with `btest` (same `b-` family in directory listings); lowercase / ASCII / short; functional-descriptive matching the `btest` / `pt-liqadj` convention; no major Python-tooling collision.

---

## 19. Self-Critique / Next-Pass TODOs

**Done in v0.2 (2026-04-26)**:

- [x] §9 (solutions survey) collapsed to KB-4 reference.
- [x] §10 (IB gotchas) collapsed to KB-2 + KB-3 reference.
- [x] §16 (open questions) collapsed to KB-11 reference.
- [x] §17 (glossary) collapsed to KB-12 reference.
- [x] §1, §15 reference ADR-013 phased priority.
- [x] Confirm `harp` interaction (KB-13 — none direct; via deferred A1 strategy only).
- [x] §5.5 default risk thresholds — INV-4 now SSOT; defaults captured.
- [x] §13.2 chaos catalogue — partial structure (the file-fixture spec is still a DESIGN-phase artefact).

**To be addressed in v0.3 / DESIGN-phase**:

- [ ] §7.2 — flesh out `OrderUpdate`, `BrokerEvent` union, `Instrument` shape (multi-leg? options chain ids?). Will land as DD-1 / DD-2 in design phase.
- [ ] §8 — re-derive parity envelopes from a sample IB Paper run when M3 data is available (OQ-012).
- [ ] §11 — concrete SQL DDL for SQLite v1 (DD-4).
- [ ] §12 — full `RUNBOOK.md` outline (DESIGN-phase artefact).
- [ ] §13 — formalise the chaos fault catalogue as a test-fixture spec (KB-7 failure_modes, currently MISSING).
- [ ] Add §20 OpenAPI sketch for the 3-page UI's REST surface (DD-5).
- [ ] Confirm whether `btest`'s `platform_api/services/run_store.py` can be reused or `blive` needs its own (DESIGN-phase decision).
- [ ] Decide whether multi-account routing within IB (sub-accounts, FA accounts) is in v1 or deferred (raise as new OQ when relevant).
- [ ] §5.13 ramp policy: validate `vwap_capped(0.05)` default against typical A2/A3 strategy holdings.
- [ ] §8 continuous parity (M7+): decide whether the parallel `btest` replica runs in-process or as a sidecar (KB-15 parity_methodology).
