---
id: KB-12
title: Glossary
status: DRAFT
owner: Claude
last_reviewed: 2026-04-26
version: 0.1
sources: []
depends_on: []
referenced_by:
  - every other artifact (terms used)
  - REQUIREMENTS.md §17 (originally hosted these terms inline)
  - CONTEXT_PROTOCOL.md §2.7 (Glossary-authoritative rule)
---

# KB-12 — Glossary

## Purpose

Single source of truth for project-specific terms. If two artifacts disagree on a term's meaning, the Glossary wins or both are wrong (CONTEXT_PROTOCOL §2.7).

## Scope

In scope: every term used in two or more `blive` artifacts that has a specific meaning beyond its plain English / general technical sense.

Out of scope: industry-standard terms whose meaning is unambiguous (e.g. "TCP", "JSON"); ad-hoc terms used in only one artifact.

---

## Terms

### Adapter
Concrete implementation of a Port. `IBBroker` is an Adapter for `BrokerPort`. See [ADR-004 hexagonal](decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement).

### ADR
Architectural Decision Record. Append-only entry in [KB-10 DECISIONS](decisions/DECISIONS.md). Reverse via supersede chain, never edit body of past ADR.

### Archetype
Strategy archetype — one of A1, A1a, A2, A3 (current) or A4–A8 (future). See [KB-5 §2](kb/strategy_taxonomy.md#2-archetype-catalogue).

### Backtest-live parity
The contract that `blive` and `btest` compute strategy P&L identically modulo expected divergences (slippage, broker rates). See [REQUIREMENTS §8](../REQUIREMENTS.md), [ADR-012](decisions/DECISIONS.md#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken).

### Bar
OHLCV record for an instrument over a frequency window. See [REQUIREMENTS §7.3](../REQUIREMENTS.md) for the concrete shape.

### Book
One side of a `LongShortPortfolio` (long_book or short_book). Composed of a Selector and a Weighting. See [KB-1 §6](kb/btest_dsl_inventory.md#6-portfolio).

### `client_order_id`
`blive`-generated UUID owned through full order lifecycle. Distinct from venue's `orderId` (which `IBBroker` allocates). See [REQUIREMENTS §5.3](../REQUIREMENTS.md).

### CONID
IB's integer Contract ID. Authoritative identifier for a tradable instrument on IB. blive's `Instrument` ↔ `Contract.conId` mapping happens in `IBBroker`.

### Crash-only design
The principle that the engine recovers from crashes by running the same code path as a clean cold start: replay log, reconcile, enter `paused` state, require human resume. See [ADR-009](decisions/DECISIONS.md#adr-009--crash-only-design).

### Domain event
Immutable record of something that happened in the engine. Persisted to the event log; restart replays them. Examples: `OrderSubmitted`, `OrderAccepted`, `Fill`, `PositionUpdated`, `RiskBreach`.

### DRY-for-prose
The discipline that a fact has one home (SSOT) and other artifacts reference it by id, never restate it. See [CONTEXT_PROTOCOL §2.3](../CONTEXT_PROTOCOL.md).

### EODHD
End-Of-Day Historical Data — third-party data provider for historical and real-time data, accessed via REST API. blive uses `eodhd://` adapter via the data-source registry. See [ADR-014](decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction), [ADR-017](decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing).

### Event-sourcing
Persistence pattern where domain state is rebuilt by replaying an append-only event log. blive uses this for `Order` and (derived) `Position`.

### Fill
Execution of part or all of an order at a specific price. Distinct from the order itself — one order can have many fills.

### FSM
Finite State Machine. `blive`'s `Order` has an FSM: `INITIALIZED → SUBMIT_PENDING → SUBMITTED → ACCEPTED → (PARTIALLY_FILLED) → FILLED | CANCELED | REJECTED | EXPIRED`. Refusal-of-illegal-transitions is enforced in code, not by convention.

### Hexagonal architecture
Ports & Adapters. Domain at centre, infrastructure at the edge. See [ADR-004](decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement).

### IBC
Interactive Brokers Controller. Automates the TWS / Gateway login UI. Required for headless deployment; works only with offline TWS installer (auto-update breaks it). See [KB-3 §5](kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events).

### IB Gateway
Stripped-down headless version of TWS for API-only use. Recommended for blive's deployment. See [KB-2 §1](kb/ib_capability_matrix.md#1-connectivity-surface).

### Instrument
`blive`'s broker-neutral representation of a tradable security. Distinct from IB's `Contract` / `ConID`. The mapping is `IBBroker`'s job.

### Kill-switch
Engine-wide halt of new order submission; cancels open orders (configurable), holds positions, refuses new orders until human resume. See [REQUIREMENTS §5.5](../REQUIREMENTS.md).

### `MarketDataPort`
The Port through which the domain consumes market data. Adapters: `IBMarketData`, `EODHDMarketData`, `PaperMarketData`. See [REQUIREMENTS §7.2](../REQUIREMENTS.md).

### Mode
One of `paper`, `IB Paper`, `shadow`, `live`. See [REQUIREMENTS §5.6](../REQUIREMENTS.md), [INV-11 modes](inv/modes.md) (MISSING).

### NDJSON tape
Daily newline-delimited JSON file of `(orders, fills, positions)` for the trading day. Operational artefact for tax, audit, downstream tools (e.g. ForgeFolio integration). See [REQUIREMENTS §6.3](../REQUIREMENTS.md).

### OPRA
Options Price Reporting Authority — the SIP for US listed options. IB tier required to receive options market data. Out of v1 scope. See [KB-3 §3](kb/ib_pacing_spec.md#3-market-data-subscription-tiers).

### OQ
Open Question. Tracked in [KB-11 OPEN_QUESTIONS](decisions/OPEN_QUESTIONS.md). Resolved by an ADR or by inline finding.

### Parity contract / parity envelope / parity diagnostic / parity residual
- **Parity contract**: the documented set of guarantees about what backtest and live compute identically vs. expectedly differently. See [REQUIREMENTS §8](../REQUIREMENTS.md).
- **Parity envelope**: the numerical tolerance band per cost component (e.g. ±5 bps slippage on liquid US equities). See [KB-6](kb/cost_margin_dictionary.md).
- **Parity diagnostic**: the daily / continuous process that measures `(realized, simulated, residual)` per strategy. See [ADR-012](decisions/DECISIONS.md#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken).
- **Parity residual**: the difference `realized_pnl - simulated_pnl` in basis points; alerts on aggregate residual outside envelope.

### Port
Abstract interface the domain depends on. blive's ports: `BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `EventBusPort`, `AlertPort`. See [REQUIREMENTS §7.2](../REQUIREMENTS.md).

### Reconciliation
The process of bringing local engine state in line with venue state. Two-phase: startup (one-shot) + continuous (every N seconds). See [REQUIREMENTS §5.7](../REQUIREMENTS.md), [ADR-009](decisions/DECISIONS.md#adr-009--crash-only-design).

### `RiskEngine`
The component every order traverses before submission. Pre-trade checks; never bypassable. See [ADR-008](decisions/DECISIONS.md#adr-008--riskengine-no-bypass-enforced-architecturally).

### Sector-neutral
Portfolio constraint that limits sector-level net exposure within a tolerance. See `dsl/portfolio.py:SectorNeutral`.

### Shadow mode
Live data, live decisions, no order submission — observe-only validation. See [REQUIREMENTS §5.6](../REQUIREMENTS.md).

### Sizer
Component between `PortfolioEngine` and `RiskEngine` that converts target weights into orders accounting for lot size, FX, IB margin, and ramp policy. See [REQUIREMENTS §5.13](../REQUIREMENTS.md).

### SMART
IB's smart order router. Default routing for US equities/ETFs. See [KB-2 §5](kb/ib_capability_matrix.md#5-routing).

### SSOT
Single Source of Truth. Every fact has one home; everywhere else references it. See [CONTEXT_PROTOCOL §2.1](../CONTEXT_PROTOCOL.md).

### Spec id
`sha256(resolved_yaml + dsl_lib_version + btest_version + blive_version)`. Immutable identifier of a strategy version. Recorded with every domain event. See [REQUIREMENTS §5.12](../REQUIREMENTS.md).

### Stable id
Project identifier that cross-references use instead of file paths or section numbers (which change). Forms: `KB-N`, `INV-N`, `DD-N`, `ADR-N`, `OQ-N`. See [CONTEXT_PROTOCOL §2.4](../CONTEXT_PROTOCOL.md).

### TIF
Time-in-Force. `DAY`, `GTC`, `IOC`, `FOK`, `OPG`, `GTD`. See [KB-2 §4](kb/ib_capability_matrix.md#4-time-in-force-tif).

### TKAN
Temporal Kolmogorov-Arnold Network — ML model used in A2 strategies (`index_directional`, `tkan_v4_momentum_timing`). Produces `pred_cache.pkl` artefacts consumed via `ExternalFactor`. See [KB-5 §2 A2](kb/strategy_taxonomy.md#a2--single-instrument-market-timing-xs-universe-daily), [ADR-015](decisions/DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).

### Tradable proxy
ETF (or other tradable instrument) used to gain exposure to a non-tradable index. CACT (CAC Total Return) → `CACX.PA` ETF; SPY for SP500 timing. See [KB-5 §2 A1a](kb/strategy_taxonomy.md#a1a--cross-index-lagging-m-universe-daily), KB-5 §3.

### TWS
Trader Workstation — IB's desktop trading application. Hosts the API socket; required (or IB Gateway) for blive to connect. See [KB-2 §1](kb/ib_capability_matrix.md#1-connectivity-surface).

---

## Cross-References

- [CONTEXT_PROTOCOL §2.7](../CONTEXT_PROTOCOL.md) — Glossary-authoritative rule.
- [REQUIREMENTS §17](../REQUIREMENTS.md) — original inline glossary; v0.2 will collapse to a pointer here.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. Extracted REQUIREMENTS §17 + added terms accumulated in KBs (archetype, ADR, parity envelope, etc.).
