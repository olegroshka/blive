---
id: KB-4
title: Frameworks Survey — Live Algo Execution in Python
status: DRAFT
owner: Claude
last_reviewed: 2026-04-26
version: 0.1
sources:
  - https://github.com/ib-api-reloaded/ib_async                    # accessed 2026-04-26
  - https://nautilustrader.io/docs/latest/concepts/architecture/   # accessed 2026-04-26
  - https://nautilustrader.io/docs/latest/concepts/live/           # accessed 2026-04-26
  - https://nautilustrader.io/docs/nightly/integrations/ib/        # accessed 2026-04-26
  - https://github.com/QuantConnect/Lean                           # accessed 2026-04-26
  - https://www.backtrader.com/docu/live/ib/ib/                    # accessed 2026-04-26
  - https://github.com/atreyuxtrading/atreyu-backtrader-api        # accessed 2026-04-26
  - https://github.com/Lumiwealth/lumibot                          # accessed 2026-04-26
  - https://lumibot.lumiwealth.com/brokers.interactive_brokers.html # accessed 2026-04-26
  - https://github.com/vnpy/vnpy                                   # accessed 2026-04-26
  - https://hummingbot.org/connectors/connectors/architecture/     # accessed 2026-04-26
  - https://github.com/mhallsmoore/qstrader                        # accessed 2026-04-26
  - https://github.com/stefan-jansen/zipline-reloaded              # accessed 2026-04-26
  - https://github.com/alpacahq/pylivetrader                       # accessed 2026-04-26
  - https://www.quantrocket.com/                                   # accessed 2026-04-26
  - https://github.com/9600dev/mmr                                 # accessed 2026-04-26
  - https://news.ycombinator.com/item?id=44810552                  # accessed 2026-04-26
depends_on:
  - KB-2 ib_capability_matrix
  - KB-3 ib_pacing_spec
referenced_by:
  - REQUIREMENTS.md §9 (existing solutions survey)
  - ADR-002 (adopt ib_async)
  - ADR-003 (borrow NautilusTrader patterns)
---

# KB-4 — Frameworks Survey

## Purpose

Structured analysis of every Python framework relevant to bridging a backtest DSL to live IB trading. Foundation for [ADR-002 ib_async adoption](../decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver) and [ADR-003 NautilusTrader-borrow](../decisions/DECISIONS.md#adr-003--borrow-nautilustrader-architecture-do-not-depend). Replaces inline survey content in [REQUIREMENTS §9](../../REQUIREMENTS.md) (slated for removal in v0.2 pass).

## Scope

In scope: every framework surveyed for live algo trade execution against IB or as a multi-broker abstraction. Each entry covers license, maintenance, connection model, broker abstraction, strategy authoring, order/position model, risk, persistence, UI, production track record, pros/cons for blive's use case.

Out of scope: backtest-only frameworks unless they have a live story; HFT-specific frameworks (out of v1 scope per [ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only)).

## Verdict legend

- **Adopt** — depend on directly in blive code.
- **Study** — read patterns, don't depend.
- **Reject** — wrong shape / dead / overscope.

---

## Adopt

### `ib_async` v2.1+

- **Verdict:** **Adopt** ([ADR-002](../decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver)).
- **License:** BSD-2-Clause.
- **Maintenance:** active under `ib-api-reloaded` org since Matt Stancliff took over post Ewald de Wit's death (March 2024). Latest stable v2.1.0+; v2.0.1 (June 2025) was the first proper post-transition release. ~857 commits on main.
- **Connection model:** TCP socket to TWS or IB Gateway; built on `asyncio` + `eventkit`. Both blocking (`run()`) and async (`connectAsync()`) entry points.
- **Broker abstraction:** none — IB-only wrapper, not a framework.
- **Strategy authoring:** none — caller subscribes to events (`pendingTickersEvent`, `orderStatusEvent`) and drives `IB` methods.
- **Order/position model:** `Trade` aggregates order + contract + `OrderStatus` log. `IB.positions()`, `IB.accountValues()`.
- **Risk / kill switch:** none.
- **Persistence:** none. `IB.reqAllOpenOrders` / `reqPositions` re-fetches on reconnect.
- **UI:** none.
- **Production track record:** very heavy retail use (ThetaGang, many retail bots, MMR).
- **Pros for blive:** cleanest IB API in Python; thin enough to wrap behind our own port; real async; explicit reconnection helpers.
- **Cons:** no abstraction above IB — that's blive's job. Dependency on a community library that has had one maintenance discontinuity.

---

## Study (do not depend)

### NautilusTrader

- **Verdict:** **Study** ([ADR-003](../decisions/DECISIONS.md#adr-003--borrow-nautilustrader-architecture-do-not-depend)).
- **License:** LGPL-3.0.
- **Maintenance:** very active. v1.225.0 Beta in April 2026; ~22.3k stars. Built by Nautech Systems.
- **Connection model:** Rust core, Python control. For IB: wraps `ibapi` via its own `InteractiveBrokersClient`; supports direct TWS/Gateway and a `DockerizedIBGateway` helper. Async, single-threaded deterministic kernel; reconnect watchdog with `IB_MAX_CONNECTION_ATTEMPTS`.
- **Broker abstraction:** **hexagonal / ports-and-adapters** (best-in-class). Strategies depend on `MessageBus`, `ExecutionEngine`, `RiskEngine`, `Cache`, `Portfolio`. Venues plug in via `DataClient` + `ExecutionClient` adapters. Many adapters (IB, Binance, Bybit, dYdX, OKX, Databento, Polymarket, Tardis).
- **Strategy authoring:** subclass `Strategy`; receive events (`on_bar`, `on_trade_tick`, `on_order_filled`); call `self.submit_order()`. Same code runs in backtest and live.
- **Order state machine:** formal FSM (`INITIALIZED → SUBMITTED → ACCEPTED → (PARTIALLY_FILLED) → FILLED / CANCELED / REJECTED / EXPIRED`). `RiskEngine` validates pre-trade.
- **Reconciliation:** first-class. Startup reconcile + continuous loop with `reconciliation_startup_delay_secs`, `open_check_lookback_mins=60`. Known issue: orders older than lookback can drift ([Issue #3176](https://github.com/nautechsystems/nautilus_trader/issues/3176)).
- **Persistence:** optional Redis-backed `MessageBus` durability (Redis ≥ 6.2 streams). Crash-only design.
- **Risk:** built-in `RiskEngine` with position limits, notional limits, order rate limits.
- **UI:** none — explicitly out of scope.
- **Production track record:** individuals and small teams.
- **Pros:** best-in-class architecture; canonical reference for the patterns blive wants.
- **Cons:** LGPL-3 link friction; Rust + Cython build complexity; their `Strategy` would compete with btest DSL (the very thing blive preserves); IB extra not yet on Python 3.14.

### Hummingbot

- **Verdict:** **Study (event-name patterns).**
- **License:** Apache-2.0; very active.
- **Why it matters:** crypto-only — no IB connector — but its **order-lifecycle event contract** is the cleanest pub/sub in this space:
  - `BuyOrderCreatedEvent`, `SellOrderCreatedEvent`
  - `OrderFilledEvent`
  - `BuyOrderCompletedEvent`, `SellOrderCompletedEvent`
  - `OrderCancelledEvent`
  - `MarketOrderFailureEvent`
- **Pros:** the cleanest event names; copy verbatim.
- **Cons:** crypto-only, so you take the names but not the implementation.

### Lumibot

- **Verdict:** **Study (Broker subclass ergonomics).**
- **License:** MIT; active. v4.5.5 (April 2026); 4800+ commits.
- **Connection model:** per-broker; IB uses TWS/Gateway. Lifecycle is **polling** (`on_trading_iteration` every `sleeptime` minutes).
- **Broker abstraction:** `Broker` base class with concrete `Alpaca`, `InteractiveBrokers`, `Tradier`, `Schwab`, `Ccxt` subclasses. Strategy code is broker-independent.
- **Strategy authoring:** subclass `Strategy`; implement `on_trading_iteration` mandatory + lifecycle callbacks.
- **Pros:** clean broker port abstraction; closest in spirit to what blive wants.
- **Cons:** **polling lifecycle is not event-driven**; 2FA pain on IB; not embeddable in another engine. blive copies the *interface shape*, not the polling loop.

### vnpy / VeighNa

- **Verdict:** **Study (proof of port-and-adapter at scale).**
- **License:** MIT; very active. v4.3.0 (Dec 2025); 39.9k stars; 80+ gateways.
- **Connection model:** custom `EventEngine` (single-threaded queue-based event loop, pure Python) + `MainEngine`.
- **Broker abstraction:** `BaseGateway` is the port; concrete gateways for IB, CTP, Binance, Deribit, OKX, Bybit, etc.
- **UI:** PySide6 GUI included — one of the few here with a real desktop UI.
- **Pros:** mature event engine; pluggable gateways prove the pattern at 80+ adapters.
- **Cons:** Chinese-language documentation primary; PySide6 coupling in mainline.

---

## Reject

### Native `ibapi`

- **Verdict:** **Reject** — too low-level. `ib_async` exists for a reason.
- **Maintenance:** IB-maintained.
- **Connection:** TCP socket; raw `EWrapper` / `EClient` callbacks.

### IBKR Web API (CPAPI)

- **Verdict:** **Reject** for serious execution.
- **Why:** 10 req/sec global, 6-min idle session death (must `/tickle` ≤ 5 min), IBKR Pro only, Java gateway dependency. Operationally worse than TWS API for blive's use case.

### QuantConnect Lean

- **Verdict:** **Reject** — wrong shape.
- **License:** Apache-2.0; very active.
- **Why:** C# core; Python algorithms via PythonNet (1/20th C# speed per [Issue #2026](https://github.com/QuantConnect/Lean/issues/2026)). The `IBrokerage` interface is in C#. Cannot be cleanly *embedded* in a Python-native engine, only run alongside it. Wrong shape if your DSL/engine is pure Python (which blive is, via btest).
- **Could have been adopted as a host runtime**, but that disposes of btest's Python DSL.

### Backtrader (live)

- **Verdict:** **Reject** — upstream effectively dead.
- **Maintenance:** original `mementum/backtrader` last meaningful commit ~2 years stale.
- **IB story:** `ibpy`-style threading; flaky in 2026. Forks (`atreyu-backtrader-api`, `backtrader-slim`, `backtrader-lucidinvestor`) update bits but none are production-ready as a fresh foundation.

### Zipline-Reloaded + pylivetrader

- **Verdict:** **Reject** for IB live.
- **Why:** `zipline-reloaded` is backtest only (Stefan Jansen). `pylivetrader` (Alpaca) is dormant; IB is bespoke bridges.

### QSTrader

- **Verdict:** **Reject** for live IB today.
- **License:** MIT; active but small.
- **Why:** clean alpha/sizing/risk/execution separation, but live IB is announced as "early alpha" and not delivered as a polished open-source product.

### Lumibot polling lifecycle

- **Lumibot is in "Study"** above for ergonomics, but the polling `on_trading_iteration` lifecycle is rejected as a model — blive is event-driven, not polled.

### QuantRocket / Moonshot

- **Verdict:** **Reject** as a foundation.
- **License:** QuantRocket commercial (from $19.99/month); Moonshot OSS is backtest-only.
- **IB integration:** original and tightest of any framework; routes everything via IB Gateway in containers; supports "dry runs". Operationally excellent.
- **Why reject:** **not embeddable** — it's a platform you adopt, not a library. Worth studying for deployment patterns (Docker Compose with IB Gateway, IBC, blotter, data services as separate services).

### PyAlgoTrade

- **Verdict:** **Reject — dead.**
- **Last meaningful push:** ~2 years ago; ~13-year-old codebase.

### Catalyst

- **Verdict:** **Reject — dead.**
- **Last update:** Nov 2022.
- **Was:** Enigma's crypto Zipline fork.

### MMR ([9600dev/mmr](https://github.com/9600dev/mmr))

- **Verdict:** notable mention; not a foundation but architecturally aligned. Solo project; hexagonal IB platform on `ib_async` + ZeroMQ + DuckDB; "every operation as a JSON-returning CLI command".
- **Use:** read for inspiration on CLI shape and DuckDB persistence option.

### ThetaGang

- **Verdict:** notable mention. Production options-strategy bot built directly on `ib_async`; useful as a real-world reference for how to structure an `ib_async`-based bot.

---

## Architectural Patterns to Copy (cross-cutting)

Distilled from the **Study** set; informs blive's own implementation:

1. **Hexagonal "ports and adapters" core.** Domain depends only on `BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `EventBusPort`, `AlertPort`. NautilusTrader and Lumibot both demonstrate it.
2. **Single-threaded asyncio kernel with a MessageBus.** NautilusTrader's deterministic single-thread event-ordering is what makes backtest-live parity tractable. Pub/sub on named topics + targeted dispatch by actor ID.
3. **Explicit order finite-state machine.** `INITIALIZED → SUBMIT_PENDING → SUBMITTED → ACCEPTED → (PARTIALLY_FILLED) → FILLED / CANCELED / REJECTED / EXPIRED`. Every transition fires a typed event; refuse illegal transitions in code, not by convention.
4. **In-flight order tracker separate from `OrderBook`.** Hummingbot's `InFlightOrderBase` pattern. Connector tracks orders with client-id but no venue-id yet; reconciles when venue assigns one.
5. **Two-phase reconciliation.**
   - Startup: query open orders, positions, account values; diff against persisted `Cache`; synthesise missing events.
   - Continuous: configurable interval (Nautilus uses 60 min lookback); poll open orders; audit own-orderbook against venue.
6. **Crash-only design with externalised state.** Persist every domain event; restart path == cold-start path. Optional Redis stream as bus durability.
7. **Backtest/live parity via shared kernel.** Same engine code; only data source and execution adapter differ. Simulated execution adapter must emit the same event types as the IB one; cost/slippage/latency models configurable identically.
8. **Pre-trade RiskEngine layer.** Validate every order before it leaves the engine: position limits, notional limits, order rate limits, kill-switch state. Sits between Strategy and ExecutionEngine — never bypassable ([ADR-008](../decisions/DECISIONS.md#adr-008--riskengine-no-bypass-enforced-architecturally)).
9. **Event-source the audit log.** Every command and every event in append-only log; regulatory review and post-mortem trivial.
10. **Adapter responsibilities are narrow.** Adapter parses venue protocol → domain objects. Does NOT enforce business rules; engine does.

---

## Cross-References

- [REQUIREMENTS §9](../../REQUIREMENTS.md) — current inline survey content; v0.2 will replace with pointer here.
- [ADR-002 ib_async](../decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver), [ADR-003 NautilusTrader-borrow](../decisions/DECISIONS.md#adr-003--borrow-nautilustrader-architecture-do-not-depend), [ADR-004 hexagonal](../decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement), [ADR-008 RiskEngine](../decisions/DECISIONS.md#adr-008--riskengine-no-bypass-enforced-architecturally), [ADR-009 crash-only](../decisions/DECISIONS.md#adr-009--crash-only-design).
- [KB-2 ib_capability_matrix](ib_capability_matrix.md), [KB-3 ib_pacing_spec](ib_pacing_spec.md).

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap; persists the survey produced in earlier session research.
