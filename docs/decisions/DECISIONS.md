---
id: KB-10
title: Architectural Decision Records (ADRs)
status: DRAFT
owner: Claude record, Oleg approve
last_reviewed: 2026-04-28
version: 0.11
sources: []
depends_on:
  - KB-11   # OPEN_QUESTIONS — many ADRs resolve OQs
referenced_by:
  - REQUIREMENTS.md (rationale claims now traced to specific ADRs)
  - KB-5 strategy_taxonomy (Phase priority cites ADR-013)
  - KB-11 OPEN_QUESTIONS (resolution chains)
  - CONTEXT_PROTOCOL.md §5 (governs format)
---

# KB-10 — Architectural Decision Records

> **Format:** one big file for now (per [CONTEXT_INVENTORY §7](../../CONTEXT_INVENTORY.md#7-file-layout)) — split to `docs/decisions/adr/ADR-NNN-slug.md` when count exceeds usability or commit conflicts get painful.
>
> **Convention** ([CONTEXT_PROTOCOL §5](../../CONTEXT_PROTOCOL.md#5-decision--question-discipline)):
> - Each ADR is append-only. Reverse a decision via a new ADR with `supersedes: ADR-NNN`.
> - Status: `PROPOSED` · `ACCEPTED` · `SUPERSEDED-BY-ADR-MMM` · `DEPRECATED`.
> - Stable id `ADR-NNN`; numbering monotonic.

---

## Index

| Id | Title | Status | Date | Resolves |
|----|-------|--------|------|----------|
| [ADR-001](#adr-001--adopt-project-name-blive) | Adopt project name `blive` | ACCEPTED | 2026-04-26 | — |
| [ADR-002](#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver) | Adopt `ib_async` v2.1+ as wire-level IB driver | ACCEPTED | 2026-04-26 | — |
| [ADR-003](#adr-003--borrow-nautilustrader-architecture-do-not-depend) | Borrow NautilusTrader architecture, do not depend | ACCEPTED | 2026-04-26 | — |
| [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) | Hexagonal ports/adapters with import-linter enforcement | ACCEPTED | 2026-04-26 | — |
| [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1) | Single-process, single-asyncio-loop kernel for v1 | ACCEPTED | 2026-04-26 | — |
| [ADR-006](#adr-006--sqlite-for-persistence-in-v1) | SQLite for persistence in v1 | ACCEPTED | 2026-04-26 | — |
| [ADR-007](#adr-007--in-process-event-bus-for-v1) | In-process event bus for v1 | ACCEPTED | 2026-04-26 | — |
| [ADR-008](#adr-008--riskengine-no-bypass-enforced-architecturally) | RiskEngine no-bypass enforced architecturally | ACCEPTED | 2026-04-26 | — |
| [ADR-009](#adr-009--crash-only-design) | Crash-only design | ACCEPTED | 2026-04-26 | — |
| [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) | Reuse btest's Factor / Signal / Portfolio engines by import | ACCEPTED | 2026-04-26 | — |
| [ADR-011](#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred) | 3-page minimal web UI; mobile and OAuth deferred | ACCEPTED | 2026-04-26 | — |
| [ADR-012](#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken) | Parity diagnostic mandatory daily; degraded mode if broken | ACCEPTED | 2026-04-26 | — |
| [ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) | v1 scope: ETF and index strategies only | ACCEPTED | 2026-04-26 | OQ-013 |
| [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) | Data sources via clean API abstraction | ACCEPTED | 2026-04-26 | OQ-014 |
| [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) | ML training: live-trained eventually, static artefacts in v1 | ACCEPTED | 2026-04-26 | OQ-015, OQ-018 |
| [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) | Leverage: support both margin-financed and leveraged-ETF instruments | ACCEPTED | 2026-04-26 | OQ-016 |
| [ADR-017](#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) | Live data: hybrid EODHD + IB streaming, per-instrument routing | ACCEPTED | 2026-04-26 | OQ-019 |
| [ADR-018](#adr-018--uk-equity-strategies-deferred-to-post-m8) | UK equity strategies deferred to post-M8 | ACCEPTED | 2026-04-26 | OQ-021 |
| [ADR-019](#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs) | A3 archetype generalises to other leveraged-ETF pairs | ACCEPTED | 2026-04-26 | OQ-022 |
| [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10) | Phase 1 NAV slice: 5–10% of total, cap 10% | ACCEPTED | 2026-04-26 | OQ-024 |
| [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) | CAC ETF proxy: `CAC.PA` (Lyxor CAC 40 UCITS ETF) | ACCEPTED | 2026-04-26 | OQ-025 |
| [ADR-022](#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning) | TKAN artefact freshness window: 30d hard, 21d warning | ACCEPTED | 2026-04-26 | OQ-026 |
| [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) | TKAN artefact path and refresh ownership | ACCEPTED | 2026-04-26 | OQ-027 |
| [ADR-024](#adr-024--add-session-retrospective-artefact-type) | Add session-retrospective artefact type | ACCEPTED | 2026-04-26 | — |
| [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) | Amend CONTEXT_PROTOCOL §8.3 with milestone-close and phase-boundary rules | ACCEPTED | 2026-04-26 | — |
| [ADR-026](#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) | Adopt agentic-execution layer; reduce human action surface | ACCEPTED | 2026-04-26 | — |
| [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) | Sizer rounding policy: integer shares, truncate toward zero | ACCEPTED | 2026-04-27 | — |
| [ADR-028](#adr-028--strategy-config-shape-python-build_strategy--blive-yaml-overrides) | Strategy config shape: Python `build_strategy()` + blive YAML overrides | ACCEPTED | 2026-04-27 | — |
| [ADR-029](#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet) | `PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet | ACCEPTED | 2026-04-27 | — |
| [ADR-030](#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010) | Per-archetype btest interpreter dispatch (amends ADR-010) | ACCEPTED | 2026-04-27 | OQ-030 |
| [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) | Token-bucket rate limiter shape for IB adapters | PROPOSED | 2026-04-27 | — |
| [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) | Instrument resolution policy (`blive.Instrument` ↔ IB `Contract` / `ConID`) | PROPOSED | 2026-04-27 | — |
| [ADR-033](#adr-033--accountupdate-event-shape-and-sampling-cadence) | `AccountUpdate` event shape and sampling cadence | ACCEPTED | 2026-04-27 | — |
| [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) | Multi-broker registry pattern (extends ADR-004) | ACCEPTED | 2026-04-27 | — |
| [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) | Secrets handling discipline (`~/.blive/secrets/`) | ACCEPTED | 2026-04-27 | — |
| [ADR-036](#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer) | IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer | ACCEPTED | 2026-04-27 | — |
| [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet) | `Instrument.tradability` field (spot / cfd / spread_bet) | ACCEPTED | 2026-04-27 | — |
| [ADR-038](#adr-038--ig-rate-limit-defaults-parameterise-adr-031) | IG rate-limit defaults (parameterise ADR-031) | ACCEPTED | 2026-04-27 | — |
| [ADR-039](#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) | Phase 1 strategy under IG bridge: CAC 40 CFD | ACCEPTED | 2026-04-27 | — |

---

## ADR-001 — Adopt project name `blive`

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
A new project alongside `btest`, `harp`, `pt-liqadj` needs a name. The name must (1) communicate that this is the live counterpart to `btest`, (2) sit cleanly in directory listings next to siblings, (3) avoid major Python-tooling collisions, (4) be cheap to type and grep.

### Decision
Project is named **`blive`** — the `b-` prefix family pairs with `btest`, lowercase compact form matches the existing aesthetic (`btest`, `harp`), the `live` token states the operational intent.

### Alternatives Considered
1. **`helm`** — evocative ("at the helm of live trading"), but Kubernetes Helm collision pollutes search. Rejected.
2. **`pilot`** — clean metaphor, but Istio Pilot collision. Rejected.
3. **`rudder`** — clean, no major collision, but less obviously paired with `btest`. Weaker option.

### Consequences
- **Positive**: pairs visually with `btest`; trivial to find in shells; no major collision.
- **Negative**: minor collision with a Bilibili-livestream Python lib (`blive`, unrelated domain — low practical risk).
- **Follow-ups**: project root `C:\Users\olegr\PycharmProjects\blive\` created.

### Cross-References
- [REQUIREMENTS §18 naming note](../../REQUIREMENTS.md)

---

## ADR-002 — Adopt `ib_async` v2.1+ as wire-level IB driver

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Interactive Brokers offers two API surfaces — TWS API (TCP socket, callback-driven `EWrapper`/`EClient`) and IBKR Web API (CPAPI, REST + WebSocket). The native Python `ibapi` is verbose and threading-awkward; the community `ib_async` (formerly `ib_insync`) is the de-facto modern wrapper. Maintenance transitioned to `ib-api-reloaded` after Ewald de Wit's death (March 2024).

### Decision
Use **`ib_async` v2.1+** (BSD-2) as the wire-level driver, instantiated only inside the `IBBroker` adapter. Pin `>=2.1,<2.2`. **Never imported above the adapter layer** ([ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement)).

### Alternatives Considered
1. **Native `ibapi`** — too low-level; reinvents what `ib_async` already does cleanly.
2. **IBKR Web API (CPAPI)** — 10 req/s, 6-min idle session death, IBKR Pro only; operationally worse than TWS for serious execution.
3. **Vendor-fork `ib_async`** — premature; depend on upstream first, fork only on stall.

### Consequences
- **Positive**: thin async wrapper, real maintenance cadence, modern asyncio + eventkit; minimal boilerplate.
- **Negative**: dependency on a community library that has already had one maintenance discontinuity; risk it stalls again.
- **Follow-ups**: monitor upstream release cadence; revisit OQ-004 if a stall recurs (vendor-fork plan).

### Cross-References
- [REQUIREMENTS §9.1](../../REQUIREMENTS.md), [REQUIREMENTS §10](../../REQUIREMENTS.md) (gotchas), KB-4 (MISSING).

---

## ADR-003 — Borrow NautilusTrader architecture, do not depend

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
NautilusTrader is the most architecturally aligned production framework: deterministic single-thread asyncio kernel, MessageBus, ExecutionEngine, RiskEngine, Cache, DataClient/ExecutionClient adapters, two-phase reconciliation. But it ships its own `Strategy` abstraction that would compete with `btest`'s DSL — the very thing `blive` is built around. It's also LGPL-3 with a Rust core that adds build complexity.

### Decision
Read NautilusTrader's [concept docs](https://nautilustrader.io/docs/latest/concepts/architecture/) **as our spec**; reimplement the patterns in Python code we own. Treat their reference implementation as a quality bar, not a dependency.

### Alternatives Considered
1. **Adopt NautilusTrader wholesale** — `Strategy` competes with `btest` DSL; LGPL-3 friction in legal review; Rust + Cython build adds a dimension to ops; not Python-native enough for our other goals.
2. **Ignore NautilusTrader** — would re-derive the wheel, slower and lower-quality.

### Consequences
- **Positive**: own all abstractions; pure Python; no LGPL/Rust dependencies; free to evolve.
- **Negative**: implementation effort is non-trivial; risk of subtle deviation from a battle-tested design (e.g. reconciliation has nuances easy to miss).
- **Follow-ups**: KB-4 frameworks_survey to document what specifically to harvest; RiskEngine + ExecutionEngine + Cache + reconciliation are the priority targets.

### Cross-References
- [REQUIREMENTS §9.2](../../REQUIREMENTS.md), KB-4 (MISSING).

---

## ADR-004 — Hexagonal ports/adapters with import-linter enforcement

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
We need clean separation between domain (Strategy, Sizer, RiskEngine, ExecutionEngine) and infrastructure (broker, market data, persistence, event bus, alerts) so multi-broker is feasible, tests don't depend on IB, and the domain stays portable as adapters evolve.

### Decision
**Hexagonal architecture (Ports & Adapters)**:
- Domain depends only on Ports: `BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `EventBusPort`, `AlertPort`.
- Adapters implement Ports.
- **Enforced by import-linter**: a CI rule forbids any import from `blive.adapters.*` (or third-party broker libraries like `ib_async`) inside `blive.domain.*`. Violations fail CI.

### Alternatives Considered
1. **Layered MVC** — too coarse; doesn't capture the asymmetry between domain and venue adapter.
2. **Service-oriented (gRPC microservices)** — overkill for v1 single-host.
3. **Convention-only (no linter)** — relies on memory; will rot.

### Consequences
- **Positive**: testable; swappable; clean to add Alpaca/Tradier later; refactor risk lowered.
- **Negative**: more abstraction surface initially; more types to maintain; a hard onboarding step for newcomers.
- **Follow-ups**: import-linter config in `pyproject.toml` from M0; CI rule from M0; ADR-008 RiskEngine no-bypass uses the same enforcement.

### Cross-References
- [REQUIREMENTS §4 principle 1, §7.1, §7.2](../../REQUIREMENTS.md).

---

## ADR-005 — Single-process, single-asyncio-loop kernel for v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The engine handles concurrent market-data subscriptions, order events, risk checks, and a web UI. Concurrency model choices: single asyncio loop, multi-thread, multi-process. Each has trade-offs in determinism, debugability, throughput.

### Decision
**Single Python process running a single asyncio event loop in the domain layer.** Adapters may use threads internally (e.g. `ib_async`'s reader thread) but must hand off via async queues so domain code observes a deterministic event stream.

### Alternatives Considered
1. **Multi-process per strategy** — operational complexity for v1; defer per OQ-005.
2. **Threading throughout** — race conditions, debugging hell, GIL still a bottleneck.
3. **Multi-loop** — coordination complexity; the deterministic-replay benefit of a single loop is lost.

### Consequences
- **Positive**: deterministic event ordering ⇒ backtest-live parity tractable; simpler debugging; one GIL is fine for our event volume (≤ 50 instruments, < 1000 events/s sustained).
- **Negative**: ceiling on throughput; CPU-heavy strategies may pin a core.
- **Follow-ups**: revisit OQ-005 if any strategy demands > 50% of a core or has incompatible Python deps.

### Cross-References
- [REQUIREMENTS §4 principle 5, §7.1](../../REQUIREMENTS.md), [OQ-005](OPEN_QUESTIONS.md#oq-005--strategy-isolation-one-process-per-strategy-or-one-process-for-all).

---

## ADR-006 — SQLite for persistence in v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The crash-only design (ADR-009) requires a durable event log + periodic snapshots + state queries. Database choice trades off operational complexity vs. concurrency vs. analytical reporting.

### Decision
**SQLite for v1.** Single file, easy backup, well-understood, plenty fast at our event rate. Migration path to Postgres documented but not built.

### Alternatives Considered
1. **Postgres** — concurrent writers, network access, more ops; overkill until HA is needed.
2. **DuckDB** — analytics-friendly columnar; less battle-tested for OLTP-style append; revisit if reporting workloads dominate.
3. **Append-only files (NDJSON)** — simple but loses indexed queries for the UI.

### Consequences
- **Positive**: zero external service; backup = file copy; well-understood failure modes.
- **Negative**: single-host write only; no HA; large transactions hold a global lock.
- **Follow-ups**: revisit OQ-003 if event throughput > 1000/s sustained or multi-host writes required.

### Cross-References
- [REQUIREMENTS §11](../../REQUIREMENTS.md), [OQ-003](OPEN_QUESTIONS.md#oq-003--persistence-sqlite-vs-postgres-vs-duckdb).

---

## ADR-007 — In-process event bus for v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The kernel needs pub/sub between actors (Strategy emits target_weights → Sizer → RiskEngine → ExecutionEngine; market data → Strategy; broker events → Cache → Strategy). The bus is the spine of the engine.

### Decision
**In-process asyncio queues** for v1. Implement `EventBusPort` with an in-memory implementation. Redis Streams remains an opt-in adapter for HA setups later.

### Alternatives Considered
1. **Redis Streams from M1** — durable across process restart, multi-process-friendly, but introduces an external service dependency for v1.
2. **Kafka** — overkill for our scale.
3. **ZeroMQ** — multi-process complexity for v1.

### Consequences
- **Positive**: simple, low latency, no external service; matches single-process kernel (ADR-005).
- **Negative**: events lost between adapter receipt and persistence append on crash; mitigation is to persist before publishing on the bus.
- **Follow-ups**: revisit OQ-002 if HA / multi-process required.

### Cross-References
- [REQUIREMENTS §7.1, §11](../../REQUIREMENTS.md), [OQ-002](OPEN_QUESTIONS.md#oq-002--event-bus-in-process-vs-redis-streams-from-m1).

---

## ADR-008 — RiskEngine no-bypass enforced architecturally

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Risk checks must apply to every order, every time. Any pattern with an "emergency override" or "fast path" creates a footgun that will eventually fire; many trading-system disasters have followed precisely that shape.

### Decision
The RiskEngine sits between the Sizer and the ExecutionEngine on the only code path that produces orders. **Strategy code has no import path to the ExecutionEngine.** Architecturally enforced (ADR-004 import-linter rule extended): `blive.domain.strategies.*` and `blive.domain.sizing.*` cannot import `blive.domain.execution.*` directly; `blive.domain.execution.*` accepts only orders coming from `blive.domain.risk.RiskEngine.approve(...)`.

### Alternatives Considered
1. **Decorator pattern** — easier to forget the decorator on a new code path; not enforced.
2. **Permission flag on Order** — easier to set wrong; debugging-friendly is a footgun.
3. **Fast-path "skip risk" override** — never; correctness > microseconds for our scale.

### Consequences
- **Positive**: every order is risk-checked; impossible to forget by accident; CI catches bypass attempts.
- **Negative**: harder to do "raw order" testing; tests that need to bypass must mock the RiskEngine.
- **Follow-ups**: import-linter rule wired by M0; the kill-switch is itself a RiskEngine check (so no special-case bypass even for shutdown).

### Cross-References
- [REQUIREMENTS §4 principle 2, §5.5, §7.1](../../REQUIREMENTS.md).

---

## ADR-009 — Crash-only design

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The engine must recover from process crashes (OOM, segfault, kill, host reboot) and from clean restarts. Any "soft restart" code path that differs from cold start adds latent bug surface — and such bugs only fire under stress.

### Decision
**Crash-only design.** Every domain event is appended to a durable log before being published on the bus. Restart path = cold-start path:
1. Load latest snapshot.
2. Replay log tail.
3. Reconcile against venue (open orders, positions, account values; venue is authoritative).
4. Enter `paused` state — refuse new submissions.
5. **Require explicit human resume** via UI / REST.

No auto-resume after unclean shutdown.

### Alternatives Considered
1. **Graceful shutdown only** — easy to skip in real crash; doesn't help.
2. **Auto-resume after crash** — dangerous; could re-submit duplicate orders; the same code path that handles crash recovery is then not regularly exercised.

### Consequences
- **Positive**: simple recovery model; one code path; recovery is regularly exercised every restart.
- **Negative**: every restart requires human attention to clear pause state — no truly hands-off restart.
- **Follow-ups**: reconciliation engine M5; pause-state UI affordance M6; chaos tests for kill-mid-trade scenarios.

### Cross-References
- [REQUIREMENTS §4 principle 3, §5.7, §6.2](../../REQUIREMENTS.md).

---

## ADR-010 — Reuse btest's Factor / Signal / Portfolio engines by import

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Strategies are authored in `btest`'s DSL. `blive` evaluates factors / signals / portfolio targets in live. Two paths: import `btest` as a library, or fork the relevant modules into `blive`. The first preserves backtest-live parity by construction; the second risks drift.

### Decision
**Import `btest` as a library.** `blive` depends on a pinned `btest` version and re-exports `FactorEngine`, `SignalEngine`, `PortfolioEngine` for use in the live kernel. Fork specific modules **only** if upstream changes break us faster than we can absorb.

### Alternatives Considered
1. **Fork the modules into `blive`** — duplication; maintenance burden; near-certain drift.
2. **Reimplement** — would reintroduce drift between backtest and live; the parity contract (ADR-012) would be much harder to keep.

### Consequences
- **Positive**: single source of truth for strategy semantics; backtest-live parity by construction; new btest factors / signals automatically usable in live.
- **Negative**: `btest` must remain installable and stable; coordinated releases needed if breaking changes happen; CI must check `btest` import works.
- **Follow-ups**: btest version pin discipline; CI smoke-imports; revisit OQ-009 if breakage rate too high.

### Cross-References
- [REQUIREMENTS §4 principle 4, §5.1, §8](../../REQUIREMENTS.md), [OQ-009](OPEN_QUESTIONS.md#oq-009--btest-engine-reuse-import-as-library-or-fork-relevant-modules).

---

## ADR-011 — 3-page minimal web UI; mobile and OAuth deferred

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The control plane must let an operator start/stop strategies, see global state, hit a kill switch, and view logs. A full multi-page app is overscope for v1; CLI-only is operationally awkward.

### Decision
**Three pages** + REST + SSE backend:
1. **Dashboard** — all strategies, global account stats, kill-switch button at top.
2. **Strategy** (per-strategy detail) — equity curve, positions, orders, fills, log tail, parameter overrides form.
3. **System** — connections, reconciliation status, version, alert history, backup status.

Auth: shared bearer token + TLS for v1.

### Alternatives Considered
1. **Full multi-page web app** — overscope; slower to ship; more bugs.
2. **CLI only** — operational friction in real use.
3. **Native mobile app** — out of scope.
4. **OAuth/SSO** — overkill for single-operator; revisit OQ-008.

### Consequences
- **Positive**: small surface; fast to ship; easy to test end-to-end manually.
- **Negative**: limited usability beyond bare essentials; no mobile-friendly view; bearer-token auth is single-secret.
- **Follow-ups**: CLI from M6 (OQ-011); OAuth post-M8 if multi-operator emerges (OQ-008).

### Cross-References
- [REQUIREMENTS §5.8](../../REQUIREMENTS.md), [OQ-008](OPEN_QUESTIONS.md#oq-008--ui-auth-shared-secret-vs-local-only-vs-oauth), [OQ-011](OPEN_QUESTIONS.md#oq-011--cli-alongside-web-ui).

---

## ADR-012 — Parity diagnostic mandatory daily; degraded mode if broken

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Backtest-live parity is one of the project's load-bearing claims (ADR-010 makes it tractable; this ADR makes it observable). Without measurement, drift is invisible, and the parity contract becomes aspirational instead of provable.

### Decision
- **Daily** parity diagnostic runs automatically: take realised fills + EOD positions + EOD account values, replay through `btest`'s vectorised engine starting from yesterday's positions, report `(realised_pnl, simulated_pnl, residual_bps)` per strategy.
- Aggregate residual outside the envelope (REQUIREMENTS §8 — provisional ±15 bps over 5d) raises a `ParityBreach` alert.
- **Continuous** parity (parallel `btest` replica running in lock-step) added in M7+.
- If the diagnostic itself fails (btest import error, etc.), the engine enters **degraded mode** — does not crash, but signals a `ParityDiagnosticFailed` alert and continues trading. Crashing here would weaponise the diagnostic against availability.

### Alternatives Considered
1. **Weekly parity** — drift accumulates too long.
2. **Continuous-only** — operationally heavier in v1.
3. **Optional parity** — would inevitably get disabled, then rot.

### Consequences
- **Positive**: drift is observable, attributable, alertable; parity contract becomes operational, not aspirational.
- **Negative**: parity diagnostic is now load-bearing infrastructure; chaos-test it in M5+.
- **Follow-ups**: tolerance bands TBD per OQ-012; chaos-test fault for diagnostic failure; M7 continuous parity.

### Cross-References
- [REQUIREMENTS §4 principle 8, §8](../../REQUIREMENTS.md), [OQ-012](OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right).

---

## ADR-013 — v1 scope: ETF and index strategies only

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-013](OPEN_QUESTIONS.md#oq-013--which-strategies-are-funded-for-v1-and-what-nav-slice)

### Context
KB-5 catalogues seven `btest` strategies plus active research, spanning A1 (single-name SP500 cross-sectional), A1a (cross-index L/S), A2 (single-instrument timing), A3 (multi-ETF SMA-filter with safe-haven park). Building all simultaneously overstretches the engine in M0–M8; without a focus decision, scope drifts.

### Decision
**v1 scope is ETF and index strategies only.** Single-name SP500 cross-sectional strategies (`xsec_momentum_long_short_sp500`, `harp_quarterly_momentum`, `tiny_momentum_ls`) are **catalogued but deferred to post-M8**.

Phased priority codified:

| Phase | Milestone | Strategy | Archetype |
|-------|-----------|----------|-----------|
| 1 | M3 (IB Paper) | `tkan_v4_momentum_timing` 1× via tradable ETF proxy (CAC-tracking) | A2 |
| 2 | post-M5 | `triple_lev_sma_filter_dsl` (TQQQ / TMF / IEF) | A3 |
| 3 | post-M7 | `lagging_indecies` via index ETF proxies (SPY, EFA, EWJ, EWG, EWU, IEMG) | A1a |
| 4+ | post-M8 (live) | A2 leveraged variants; A3 generalised pairs (per ADR-019); UK equities (per ADR-018) | mixed |

Design intent: **complexity ramps A2 → A3 → A1a so the engine learns simple flows first**; A1 single-name is the highest-friction archetype and parked behind M8.

### Alternatives Considered
1. **Cover all archetypes from v1** — engine complexity climbs too fast; risk of multiple half-baked archetypes.
2. **Single-archetype v1 (A2 only)** — too narrow; can't validate A3 patterns or multi-venue (A1a).

### Consequences
- **Positive**: focused engine evolution; each phase exercises a new dimension of complexity (single-instrument → paired-leg → multi-currency / multi-calendar).
- **Negative**: A1 single-name use cases parked for >12 months; user appetite may shift.
- **Follow-ups**: NAV slice per phase still TBD (OQ-013 sub-question); revisit phasing if any phase delivers ≪ expected.

### Cross-References
- [KB-5 §3 strategies table](../kb/strategy_taxonomy.md#3-currently-active--in-research-strategies), [KB-5 §7 NAV Slice & Priorities](../kb/strategy_taxonomy.md#7-nav-slice--priorities), [REQUIREMENTS §1, §15](../../REQUIREMENTS.md).

---

## ADR-014 — Data sources via clean API abstraction

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-014](OPEN_QUESTIONS.md#oq-014--data-source-switch-from-sfera-bloomberg-to-live-equivalent)

### Context
`btest` strategies use heterogeneous historical sources today: `parquet://equities/sp500_daily`, `sfera://bbgidx/index_prices` (Bloomberg via sfera-db), `yf://`, `fred://`. Live `blive` adds `eodhd://` for warm-up + `ib://` for streaming. Without a clean abstraction, strategy code couples to source — losing portability and testability.

### Decision
**All data sources implement the existing `DataSource` protocol** from `btest/data/sources/registry.py`. Each source is a pluggable adapter. Strategies declare the URL (`parquet://`, `sfera://`, `eodhd://`, `ib://`, `yf://`, `fred://`); the registry resolves to the right adapter. **No source-specific hard-coding above the adapter layer.**

### Alternatives Considered
1. **Migrate everything to EODHD only** — disregards existing strategies; loses Bloomberg-quality index data for A2.
2. **Hard-code per strategy** — violates ADR-004 hexagonal principle; couples strategy code to infrastructure.

### Consequences
- **Positive**: existing `btest` strategies work in `blive` unchanged; new sources are additive; testing uses mock or parquet sources without IB/EODHD network calls.
- **Negative**: must implement adapters per source we use; some sources (sfera-Bloomberg) require enterprise access already arranged in `btest`.
- **Follow-ups**: implement `eodhd://` adapter (M2); implement `ib://` adapter for live streaming (M2); ensure existing `parquet://`, `yf://`, `fred://` adapters import cleanly into `blive`.

### Cross-References
- [REQUIREMENTS §5.2, §7.2](../../REQUIREMENTS.md), [KB-5 §6](../kb/strategy_taxonomy.md#6-data-source-mapping).

---

## ADR-015 — ML training: live-trained eventually, static artefacts in v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-015](OPEN_QUESTIONS.md#oq-015--ml-model-training-in-process-or-static-artefacts), [OQ-018](OPEN_QUESTIONS.md#oq-015--oq-018--ml-model-training-in-process-or-static-artefacts-artefact-lifecycle)

### Context
A2 strategies (`index_directional`, `tkan_v4_momentum_timing`) use ML models — TKAN networks producing `pred_cache.pkl` artefacts via `TKAN_v4_train.py`. Two architectural questions: (1) does `blive` train the models in-process during live, (2) where do trained artefacts live in prod and when do they stale?

### Decision
- **For v1**: `blive` consumes **static artefacts** produced offline by `btest` (e.g. `pred_cache.pkl`). The artefact loader is in scope; the trainer is not.
- **Architecturally**: assume that ML models will be **live-trained eventually** — the loader interface is designed so the artefact source can be swapped to a live trainer without redesign.
- **Operations**: strategy spec records artefact path, build hash, last-trained timestamp; `RiskEngine` enforces a configurable freshness window with `StaleModelArtefact` alerts when exceeded.

### Alternatives Considered
1. **Include online training in v1** — overscope; ML training is a separate concern with separate failure modes (GPU, hyperparameter sensitivity, training-set drift).
2. **Static artefacts forever** — closes off future evolution; an artefact-only design tends to bake in assumptions hard to undo.

### Consequences
- **Positive**: clean separation between training and inference; v1 stays focused on execution.
- **Negative**: artefact lifecycle is operationally manual in v1 — operator reruns trainer in `btest`, copies artefact, restarts strategy; this is friction.
- **Follow-ups**: artefact freshness window default TBD; M8+ retraining pipeline (online trainer behind the loader interface) is its own project.

### Cross-References
- [KB-5 §2 A2](../kb/strategy_taxonomy.md#a2--single-instrument-market-timing-xs-universe-daily), [REQUIREMENTS §5.12 strategy versioning](../../REQUIREMENTS.md).

---

## ADR-016 — Leverage: support both margin-financed and leveraged-ETF instruments

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-016](OPEN_QUESTIONS.md#oq-016--synthetic-leverage-via-margin-or-only-via-leveraged-etf-instruments)

### Context
Strategies achieve leverage two ways: (a) margin-finance the underlying (e.g. hold CACT at 2× by borrowing half via IB margin, paying ESTER spread), or (b) trade a leveraged ETF (e.g. TQQQ for 3× QQQ, where the leverage is internal to the fund and rebalanced daily). Different cost structures, different parity envelopes.

### Decision
**Engine supports both leverage paths.** Per-strategy declaration:

- **Margin-financed leverage**: strategy declares `target_leverage > 1` on an underlying instrument; `blive` borrows via IB margin and tracks `FinancingCost` (e.g. ESTER + spread for European, SOFR + spread for US) against the financed half.
- **Leveraged-ETF instruments**: strategy directly trades a 2×/3× ETF (TQQQ, TMF, SPXL, UPRO, SOXL); financing decay is internal to the ETF and not modelled separately by `blive`. Parity tolerance must absorb the daily-reset slippage characteristic of leveraged ETFs.

### Alternatives Considered
1. **Margin only** — disregards A3 leveraged-ETF strategies; can't run `triple_lev_sma_filter_dsl`.
2. **Leveraged-ETF only** — disregards A2 strategies that prefer underlying + margin (e.g. `tkan_v4_momentum_timing` 2× variant uses ESTER-financed CACT).

### Consequences
- **Positive**: `blive` runs both classes of strategy without translation; user retains choice per strategy.
- **Negative**: Sizer + RiskEngine must understand both leverage mechanisms; cost models differ; parity envelopes differ per leverage path.
- **Follow-ups**: parity calibration per leverage path (OQ-012); document the choice in strategy spec template.

### Cross-References
- [KB-5 §2 (A2 leveraged variants, A3)](../kb/strategy_taxonomy.md#2-archetype-catalogue), [KB-5 §8](../kb/strategy_taxonomy.md#8-live-lift-implications-for-blive-requirements-hooks).

---

## ADR-017 — Live data: hybrid EODHD + IB streaming, per-instrument routing

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-019](OPEN_QUESTIONS.md#oq-019--live-data-eodhd-real-time-vs-ib-streaming-vs-hybrid)

### Context
Live market data has two viable sources for `blive`: EODHD All-in-One (real-time / delayed depending on subscription tier; 200+ exchanges; not necessarily lowest latency) and IB streaming (`reqMktData` / `reqTickByTickData`; lowest latency to the venue we trade on; subscription-tier-gated per exchange).

### Decision
**`MarketDataPort` admits multiple concurrent providers; routing is per-instrument** (and possibly per-frequency). Default mapping pending calibration:

- **IB streaming** for instruments traded via IB (lowest latency to the venue we trade on).
- **EODHD real-time / delayed** for instruments not in our IB market-data subscription tier (broader coverage at modest latency cost).
- **EODHD historical** for warm-up of factor lookbacks and backtest replay.

The architecture forbids hard-wiring a single provider above the adapter layer (already a CONTEXT_PROTOCOL §2.2 / ADR-004 consequence).

### Alternatives Considered
1. **IB only** — coverage gaps for instruments we don't subscribe to; outside-RTH data limits.
2. **EODHD only** — adds latency vs. direct IB; might miss intraday events that IB delivers more reliably.

### Consequences
- **Positive**: best-of-both coverage; broader instrument support than either alone; degradation is graceful (fall back to EODHD if IB drops a stream).
- **Negative**: more adapter code; routing config is a new locus where bugs hide; subscription accounting (which exchanges paid on which provider) becomes operational concern.
- **Follow-ups**: per-instrument routing rules TBD; default mapping pending observed performance in M2; subscription-tier mismatch alerts.

### Cross-References
- [REQUIREMENTS §5.2](../../REQUIREMENTS.md), [KB-5 §6](../kb/strategy_taxonomy.md#6-data-source-mapping).

---

## ADR-018 — UK equity strategies deferred to post-M8

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-021](OPEN_QUESTIONS.md#oq-021--uk-equity-strategies-in-scope-post-m8)

### Context
Oleg is UK-based; SMIM research includes `equities/smim/UK-LC` (large cap) and `UK-MC` (mid cap) universes. UK live trading is operationally relevant and politically sympathetic. But adding UK in v1 broadens scope before US ETF/index trading is solid.

### Decision
**UK-listed cash equities are in scope later (post-M8) but deferred for v1.** Initial focus is US ETFs/indices and European indices via tradable ETF proxies. Likely entry post-M8: a UK-only A1 cross-sectional from the SMIM research universe (`UK-LC` or `UK-MC`).

### Alternatives Considered
1. **Include UK from M3** — broadens scope before US is solid; multi-venue / multi-currency in M3 is too much new at once.
2. **Drop UK entirely** — closes off relevant home market; mismatch with user's research base.

### Consequences
- **Positive**: scope discipline; US-first stabilises engine before multi-venue live; UK is a known follow-up not a forgotten one.
- **Negative**: UK trades remain manual / btest-only until post-M8; user's home-market alpha sits unrealised for >12 months.
- **Follow-ups**: UK strategy spec deferred to post-M8 planning; KB-13 companion_projects clarifies SMIM relationship.

### Cross-References
- [KB-5 §5 asset classes](../kb/strategy_taxonomy.md#5-asset-class-coverage-current-and-near-future), [KB-5 §7 Phase 4+](../kb/strategy_taxonomy.md#7-nav-slice--priorities), KB-13 (MISSING).

---

## ADR-019 — A3 archetype generalises to other leveraged-ETF pairs

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-022](OPEN_QUESTIONS.md#oq-022--generalise-a3-to-other-leveraged-etf-pairs)

### Context
`triple_lev_sma_filter_dsl` is one A3 instance (TQQQ / TMF / IEF). The pattern — risk-on legs with a safe-haven park, SMA-200 trend filter with hysteresis — is reusable across many leveraged-ETF families. If we treat A3 as TQQQ-specific, we close off pattern reuse.

### Decision
**A3 is parameterised by `(risk_on_pair, safe_haven_park, trend_filter, hysteresis)`.** `triple_lev_sma_filter_dsl` is one instance; future instances on the roadmap include SOXL / SQQQ (semis), UPRO / SPXU (broad index), cross-sector (XLK / XLF style). Concrete generalisation work is **deferred to Phase 4+ (post-M8)** per ADR-013, but engine code from M5 must be generic — no TQQQ/TMF/IEF specialisations baked into the engine.

### Alternatives Considered
1. **A3 = only TQQQ/TMF/IEF specific** — closes off pattern reuse; specialisation creep into engine code.
2. **Build a full generalised framework now** — premature; first prove A3 with one instance.

### Consequences
- **Positive**: pattern reuse explicit; future strategies use the same engine paths; no engine specialisation around three tickers.
- **Negative**: engine code must remain generic from day one even when only one instance is in flight (slightly more abstraction than minimum).
- **Follow-ups**: factor out A3 blueprint helpers in M5; concrete generalisation post-M8.

### Cross-References
- [KB-5 §2 A3](../kb/strategy_taxonomy.md#a3--multi-instrument-trend-filter-with-safe-haven-park-s-universe-daily), [KB-5 §7 Phase 4+](../kb/strategy_taxonomy.md#7-nav-slice--priorities).

---

## ADR-020 — Phase 1 NAV slice: 5–10% of total, cap 10%

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-024](OPEN_QUESTIONS.md#oq-024--nav-slice-for-the-phase-1-strategy)

### Context
[ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) selects `tkan_v4_momentum_timing` 1× as the Phase 1 strategy. Phase 1 is a technology-validation phase, not an alpha-capture phase. The NAV slice committed to it should reflect that posture: large enough to observe meaningful behaviour, small enough that the entire phase can fail without breaking the account.

### Decision
Allocate **5–10% of total account NAV** to the Phase 1 strategy, with a **hard cap of 10%**. Combined with RC-07 (single-name notional ≤ 8% of strategy NAV from [INV-4](../inv/risk_checks.md)), this caps any single position at ≤ 0.8% of total NAV.

### Alternatives Considered
1. **Larger slice (20–30%)** — premature; correctness has not been validated in live conditions; an undetected risk-engine bug at this scale could be costly.
2. **Smaller slice (≤ 1%)** — too small to observe meaningful P&L behaviour or to detect risk-engine misbehaviour at scale; calibration would be uninformative.
3. **Variable slice keyed to strategy confidence** — out of v1 scope; an interesting Phase 4+ idea.

### Consequences
- **Positive:** Phase 1 cannot break the account. Risk-engine misbehaviour, if it occurs, has bounded impact.
- **Negative:** observed P&L noise floor is large relative to signal; calibration of risk thresholds and parity envelope will be coarse.
- **Follow-ups:** scale up at Phase 2/3 entry once parity envelope and runtime behaviour are calibrated; revisit at G4 gate.

### Cross-References
- [INV-4 RC-07](../inv/risk_checks.md) — per-name notional cap.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) — Phase 1 plan.

---

## ADR-021 — CAC ETF proxy: `CAC.PA` (Lyxor CAC 40 UCITS ETF)

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-025](OPEN_QUESTIONS.md#oq-025--which-cac-etf-proxy-for-the-phase-1-strategy)

### Context
The btest research strategy `tkan_v4_momentum_timing` operates on `CACT` (CAC 40 Total Return index). CAC indices are not directly tradable; Phase 1 requires a tradable ETF proxy. Most CAC ETFs are price-return; the model was trained on CACT (TR), so any price-return proxy introduces a known parity divergence.

### Decision
Use **`CAC.PA` (Lyxor CAC 40 UCITS ETF, distributing share class)** as the tradable proxy on Euronext Paris (XPAR). Price-return tracking; the dividend-tracking gap (≈3–4% annual yield) is absorbed into the Phase 1 parity envelope and explicitly logged.

### Alternatives Considered
1. **`CACX.PA` (Amundi CAC 40 ETF, accumulating share class)** — closer to total-return tracking, but lower liquidity. Worth revisiting if liquidity proves adequate.
2. **iShares CAC 40 ETF** — less liquid than the Lyxor.
3. **Retrain TKAN model on `CAC.PA` price-return history** — would close the parity gap; out of v1 scope per [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).
4. **CAC 40 future contract** — out of v1 scope (no futures support yet); would close the price-vs-TR gap differently.

### Consequences
- **Positive:** tradable proxy obtained; Phase 1 can run on a real exchange.
- **Negative:** ≈3–4% annual dividend gap manifests as parity divergence vs. the btest CACT reference; documentation-only at M3, but feeds into M7 parity diagnostic design.
- **Follow-ups:** at M3 close, evaluate whether the divergence is within acceptable parity envelope or whether retraining on CAC.PA history is warranted.

### Cross-References
- [KB-5 §3](../kb/strategy_taxonomy.md) — strategies table.
- [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) — training out of v1 scope.

---

## ADR-022 — TKAN artefact freshness window: 30d hard, 21d warning

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-026](OPEN_QUESTIONS.md#oq-026--tkan-artefact-freshness-window-default)

### Context
[INV-4 RC-12](../inv/risk_checks.md) requires a `risk.max_model_artefact_age_days` threshold; [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) left the default unspecified. The TKAN model drifts as market regime changes; staleness becomes a real risk over weeks. Phase 1 needs a number.

### Decision
- **Hard threshold (RC-12 block):** 30 days. After 30 days, RiskEngine refuses to size new orders for any strategy whose artefact is older.
- **Warning alert:** 21 days. At 21 days, an `ArtefactFreshnessWarning` event fires.

Conservative for a daily-frequency strategy where the model retrains in minutes to hours offline.

### Alternatives Considered
1. **7 days hard** — too aggressive; would cause unnecessary blocks during normal retraining cycles, since the operator may go a week without refreshing.
2. **90 days hard** — too lax; the signal will have drifted substantially in three months in any non-stationary market.
3. **No threshold (warning only)** — violates ADR-015's commitment to staleness alerts as a control.

### Consequences
- **Positive:** operator is forced to refresh at least monthly; warning at week 3 gives a week of slack to act.
- **Negative:** if the operator is unavailable for > 30 days, the strategy halts on its own — a feature, but worth knowing.
- **Follow-ups:** re-tune from observed retraining cadence after first month of live (paper) operation; revisit at G4 gate.

### Cross-References
- [INV-4 RC-12](../inv/risk_checks.md) — model artefact freshness check.
- [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) — static artefact policy.

---

## ADR-023 — TKAN artefact path and refresh ownership

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-027](OPEN_QUESTIONS.md#oq-027--tkan-artefact-prod-location-and-retraining-ownership)

### Context
[ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) left artefact storage location and retraining ownership open. Phase 1 needs concrete answers.

### Decision
- **Path scheme:** `~/.blive/artefacts/{strategy_id}/{model_name}/pred_cache.pkl`. Example: `~/.blive/artefacts/tkan_v4_momentum_timing/tkan_v4/pred_cache.pkl`.
- **Hash:** SHA256 of the artefact recorded in the strategy spec snapshot per [REQUIREMENTS §5.12](../../REQUIREMENTS.md).
- **Refresh:** **manual**. Operator runs the retraining script in btest (`research/Index Directional/signals/tkan/versions/v4/TKAN_v4_train.py`) and then `scripts/refresh_artefact.py` (an M2 deliverable) which copies, checksums, and records the new artefact in blive.
- **No auto-train pipeline in v1**, consistent with [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).

### Alternatives Considered
1. **Centralised artefact registry (S3 / database)** — premature for v1; single-operator setting does not need it.
2. **Auto-retrain on staleness** — violates [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).
3. **Path under `/etc/blive/`** — less convenient for single-user development; better suited to a multi-tenant host (out of v1).

### Consequences
- **Positive:** simple operational model; works for single-operator setting; no infrastructure dependencies.
- **Negative:** multi-host deployment requires syncing the artefact directory — not a Phase 1 concern but flagged for Phase 2+.
- **Follow-ups:** `scripts/refresh_artefact.py` is an M2 deliverable per [TASK_REGISTRY](../../TASK_REGISTRY.md); auto-pipeline is post-M8 if ever.

### Cross-References
- [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) — static artefacts in v1.
- [REQUIREMENTS §5.12](../../REQUIREMENTS.md) — strategy spec versioning.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 — `refresh_artefact.py` deliverable.

---

## ADR-024 — Add session-retrospective artefact type

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** —

### Context
Milestone close benefits from a structured retrospective capturing delivered-vs-plan, surprises, ADRs / OQs raised, substrate transitions, effort, and recommendations for the next milestone. Without a dedicated artefact type, this content is scattered across chat history — non-substrate, ephemeral, lost to the next session. The CONTEXT_INVENTORY §1 hierarchy does not currently have a layer for backward-looking records.

### Decision
Introduce a new artefact category **RETRO**, with id form `RETRO-M{N}`, stored at `docs/retros/M{N}_retrospective.md`. Standard frontmatter; status lifecycle simplified to `DRAFT → STABLE` only (retros are frozen historical records — no `STALE` or `DEPRECATED` transitions). Template at `docs/retros/_template.md`.

A retrospective is written at every milestone close, by the agent at end of the closing implementation session, per the protocol amendment in [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules).

### Alternatives Considered
1. **Stuff retros into TASK_REGISTRY as appendix sections** — bloats the plan; mixing forward-plan with backward-look is poor cognitive ergonomics; the two have different update cadences.
2. **Treat retros as informal markdown without frontmatter** — drift risk; hard to discover; not boundary-objects in the [Star & Griesemer 1989] sense.
3. **Combine retro + next-prompt into one document** — they have different audiences (operator review vs agent kickoff); keeping them separate keeps each focused.
4. **Skip retros entirely** — loses milestone-level learning; subsequent NEXT_PROMPT updates would have to reconstruct context from chat or memory, exactly what the discipline forbids.

### Consequences
- **Positive:** structured artefact captures milestone-level learning; feeds subsequent NEXT_PROMPT updates; enables cross-milestone trend analysis later.
- **Positive:** retros are STABLE-frozen on completion so they don't decay; can be cited as historical record at any time.
- **Negative:** one more artefact category to maintain; one more row class in CONTEXT_INVENTORY.
- **Follow-ups:** template lands in same commit (`docs/retros/_template.md`); CONTEXT_INVENTORY registers the RETRO category in §0 conventions; ADR-025 amends CONTEXT_PROTOCOL §8.3 to mandate retro-on-milestone-close.

### Cross-References
- [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) — protocol amendment that mandates retros.
- [CONTEXT_PROTOCOL §8.3](../../CONTEXT_PROTOCOL.md) — session handoff (extended).
- `docs/retros/_template.md` — frontmatter and section template.

---

## ADR-025 — Amend CONTEXT_PROTOCOL §8.3 with milestone-close and phase-boundary rules

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** —

### Context
The existing CONTEXT_PROTOCOL §8.3 Session Handoff is generic — applies to every session. Two specific scenarios benefit from additional discipline:

- **Milestone close** (the last session of an M_N when its exit criteria are met or it is formally blocked): the agent should write a retrospective (per ADR-024), update `NEXT_PROMPT.md` for M_{N+1} informed by the retrospective, and report the gate status to the operator.
- **Phase boundary** (e.g., M3 → Phase 2 entry at the G4 gate): the closing implementation session of the prior phase should *not* be the session that plans the next phase. The mixing of implementation and next-phase planning in saturated context is a known substrate-drift mode.

Without explicit protocol, both scenarios slip into "we'll just plan the next thing in the same chat", violating the discipline.

### Decision
Amend `CONTEXT_PROTOCOL.md` §8.3 by adding two sub-sections:

- **§8.3.1 Additional steps at milestone close** — write retrospective per [ADR-024](#adr-024--add-session-retrospective-artefact-type); update `NEXT_PROMPT.md` for M_{N+1}; report gate status with explicit checklist.
- **§8.3.2 Phase boundary rule** — at phase boundaries, the closing implementation session ends with §8.3 + §8.3.1 only; next-phase planning requires a separate readiness-audit session and a separate plan-drafting session, with operator review between them.

### Alternatives Considered
1. **Leave as informal guidance** — would drift; the protocol exists precisely to prevent informal drift becoming silent practice change.
2. **Top-level §8.4, §8.5 instead of §8.3 sub-sections** — fragments the handoff coverage; the items belong logically to handoff.
3. **Make every session do retros** — too much ceremony for non-milestone sessions; retros are about milestone-level learning, not per-session friction.
4. **Combine milestone-close and phase-boundary rules into one paragraph** — they apply to different scopes; collapsing loses the distinction.

### Consequences
- **Positive:** explicit rules eliminate the "where does next-phase planning happen?" ambiguity.
- **Positive:** phase-boundary rule prevents the most common form of substrate drift in long projects: planning the next phase from saturated implementation context.
- **Positive:** existing §8.3 list is unchanged — additive amendment, not breaking.
- **Negative:** protocol slightly longer; reader must absorb sub-sections.
- **Follow-ups:** implement the amendment in the same commit as ADR-024; update `CONTEXT_PROTOCOL.md` §9 templates with the RETRO frontmatter shape; register RETRO category in CONTEXT_INVENTORY §0 conventions.

### Cross-References
- [ADR-024](#adr-024--add-session-retrospective-artefact-type) — retro artefact type.
- [CONTEXT_PROTOCOL §8.3](../../CONTEXT_PROTOCOL.md) — the section being amended.
- [TASK_REGISTRY G4](../../TASK_REGISTRY.md) — phase boundary case.

---

## ADR-026 — Adopt agentic-execution layer; reduce human action surface

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** —

### Context

The discipline as articulated in CONTEXT_PROTOCOL v0.2 places substantial manual burden on the human operator: warm-up reading, edit-protocol enforcement, cross-reference tracking, ADR / OQ writing, retrospective drafting, NEXT_PROMPT updating, status-lifecycle management. The Gemini research plan ([`docs/method/Research_Plan_for_Paper_Iteration_Gemini.md`](../method/Research_Plan_for_Paper_Iteration_Gemini.md)) catalogues the rapid maturation of agentic memory architectures (MemGPT, Agentic Memory / Zettelkasten, Multi-Layer Memory, Sculptor / ARC, graph-native context, Recursive Language Models). Both human practitioners (via the discipline) and AI researchers (via these architectures) have arrived at structurally similar substrate solutions. The discipline's posture should reflect this convergence by repositioning itself as the human-governance schema over agentic execution rather than as a manual alternative to it.

### Decision

Adopt a **human-governance / agent-execution division of labour**. The discipline's *content* is unchanged (six artefact categories, stable IDs, status lifecycle, edit protocol, propagation rules, anti-patterns). What changes is *who performs each step*: progressively more is delegated to substrate-aware tooling and agents, while the human's role refines to high-leverage actions — intent declaration, decision approval, scope governance, voice authority on substrate authoring.

Codify a five-layer adoption stack:

- **L0 — Substrate-aware warm-up agent.** Replaces manual file-list reading in `NEXT_PROMPT.md`.
- **L1 — Continuous integrity watchdog.** Background agent runs scheduled drift / orphan / staleness scans.
- **L2 — In-situ ADR auto-drafting.** Agent detects decisions and drafts ADRs at the moment of decision.
- **L3 — Auto-drafted retros + NEXT_PROMPTs.** At milestone close, agent populates RETRO and successor prompt from observable state.
- **L4 — Graph-native substrate.** Markdown becomes views over a knowledge graph; cross-references become first-class edges.

**Adoption order:** L0 + L1 first (low cost, immediate utility, layer-independent). L2 + L3 after L0/L1 prove reliable. L4 at discipline v2.0; deferred until current substrate's limits force the migration.

**Implementation deferred.** This ADR locks the *direction* and the *posture*; concrete tooling decisions land in [OQ-028](OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) and [OQ-029](OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1).

### Alternatives Considered

1. **Status quo — continue manual discipline.** Sustainable for low project complexity but doesn't scale; manual fatigue is the most common cause of substrate drift in practice. Rejected: doesn't future-proof against the maturing agentic-memory landscape.
2. **Replace discipline with autonomous memory only.** Loses human governance / auditability; over-trusts opaque memory systems. Rejected: violates the principle of legible substrate.
3. **Hybrid via ad-hoc scripts.** Drifts; no unified semantics; no guarantee of substrate integrity. Rejected: ends up at the same problem the discipline solves.
4. **Skip layers (jump directly to L4).** Tooling complexity dominates while value remains uncertain; loses the iterative validation that smaller layers provide.

### Consequences

- **Positive:** Human burden drops substantially per milestone (estimated 70–90% reduction once L0+L1 are operational; calibrate after first L0+L1 session).
- **Positive:** Substrate quality goes UP — drift detection runs continuously rather than per-milestone; retros populate from observable state rather than memory; ADRs filed at decision-moment rather than retrospectively.
- **Positive:** Discipline becomes practicable at larger project scales where current manual burden is prohibitive.
- **Positive:** Future-proofs the discipline against the maturing agentic-memory landscape; positions Cognitive Cartography as the governance complement to autonomous memory rather than a manual alternative.
- **Negative:** Introduces dependency on agentic execution; agent unavailability or confabulation become failure modes. Mitigated by L1 watchdog and mandatory human-approval gates on all agent-drafted outputs.
- **Negative:** Tooling dependency; L4 graph-native substrate is a non-trivial migration when adopted.
- **Follow-ups:**
  - `CONTEXT_PROTOCOL.md` §11 (NEW) specifies the division of labour and the layer stack. Existing §11 Self-Critique becomes §12.
  - [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) (NEW) records the amendment for future paper iteration.
  - [OQ-028](OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1): which framework / tooling stack for L0+L1.
  - [OQ-029](OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1): timing of L0+L1 implementation.

### Cross-References

- [`CONTEXT_PROTOCOL.md` §11](../../CONTEXT_PROTOCOL.md) — division-of-labour specification.
- [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) — paper-iteration tracking.
- [`docs/method/Research_Plan_for_Paper_Iteration_Gemini.md`](../method/Research_Plan_for_Paper_Iteration_Gemini.md) — motivating literature.
- [ADR-024](#adr-024--add-session-retrospective-artefact-type) — RETRO type, auto-draftable at L3.
- [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) — milestone-close protocol, target for L3 automation.

---

## ADR-027 — Sizer rounding policy: integer shares, truncate toward zero

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

The Sizer ([REQUIREMENTS §5.13](../../REQUIREMENTS.md)) converts `target_weight ∈ [-1, 1]`, `equity`, and `price` into a concrete `Order.quantity` (a `Decimal` per [DD-1 §2.4](../dd/domain_objects.md#24-order)). The arithmetic `(equity * target_weight) / price` in general yields a non-integer. We must commit to a rounding rule before writing code, because:

1. The rule directly affects the M1 G2 parity envelope (±1 bps end-of-period equity match against btest). Rounding is the *only* legitimate source of drift between btest and blive when the engines are imported by reference per [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import).
2. Different IB account classes support different precisions. Cash accounts can hold fractional shares of *some US-listed instruments only* (excludes ADRs, OTC, leveraged ETFs in some periods, and *all European venues*). Margin accounts are integer-only across the board.
3. The Phase 1 instrument is `CAC.PA` on XPAR ([ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)) — fractional shares are not available on European venues regardless of account class. So the integer rule is forced for Phase 1; the only question is whether to design for fractional later.

### Decision

For v1 (Phases 1–3), the Sizer **rounds to integer shares using truncation toward zero** (`Decimal.quantize(Decimal("1"), rounding=ROUND_DOWN)` for positive desired quantities; `ROUND_UP` toward zero for negative). Sub-share desired quantities (`abs(desired) < 1`) produce **no order** (the rebalance is a no-op for that instrument).

The Sizer's interface admits an `instrument_precision: Decimal` parameter defaulted to `Decimal("1")` (integer). Future fractional-share support flips the default per asset class via the `Instrument` lookup; the change is additive, not breaking.

**Parity contract.** btest's `event_driven` engine's sizing path must be inspected during M1 implementation; if btest does not already round to integer shares, we file an OQ on the parity-arithmetic question rather than papering over divergence.

### Alternatives Considered

1. **Round to IB fractional precision per account class.** Rejected for v1: precision varies per `(account_class, instrument)` tuple and is not stable; introduces a cross-cutting query into the Sizer that the broker port doesn't currently expose; adds complexity for a Phase-1 instrument that doesn't support it anyway.
2. **Round to nearest (banker's rounding / `ROUND_HALF_EVEN`).** Rejected: half-share boundary cases on small allocations cause asymmetric over-/under-sizing relative to a deterministic truncate-toward-zero rule. ROUND_DOWN is conservative (always under-size, never over).
3. **Allow fractional `Decimal` quantities and let the broker reject.** Rejected: late failure; risk-engine bypass smell; obscures parity test.
4. **Fixed-precision per `Instrument`** (the precision field stored on `Instrument`). Considered, deferred: requires `Instrument` to grow a field, which would be a DD-1 change. Re-raise at M2 when fractional becomes plausible for US ETFs.

### Consequences

- **Positive:** deterministic, conservative, reproducible. Parity test against btest reduces to a known-shape check.
- **Positive:** Sub-share rebalances become no-ops, which is the right default for Phase 1's small NAV slice (5–10%, [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10)) where rebalance fractions of e.g. 0.4 share happen on small price gaps.
- **Negative:** tracking error vs. target weight on small accounts; mitigated by Phase 1 NAV slice cap (~€50k–€100k notional on a ~€78 share is ≥ 600 shares, so tracking error on 1 share is < 17 bps — well-bounded).
- **Negative:** when the strategy goes to/from flat, a single 1-share leftover position can persist after the "exit" rebalance if the new target rounds to zero but the old position was not zero. M1 implementation must explicitly reset to zero on exit signals (not derive zero by rounding).
- **Follow-ups:** revisit at G2 with observed parity envelope; revisit at M2 entry when fractional shares become plausible for US ETF strategies (Phase 2 A3 — `triple_lev_sma_filter_dsl`).

### Cross-References

- [REQUIREMENTS §5.13](../../REQUIREMENTS.md) — Sizer scope.
- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — engine reuse; parity assumption.
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — Phase 1 instrument.
- [DD-1 §2.4](../dd/domain_objects.md#24-order) — `Order.quantity` is `Decimal`.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M1 G2 — ±1 bps parity criterion.

---

## ADR-028 — Strategy config shape: Python `build_strategy()` + blive YAML overrides

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[REQUIREMENTS §5.1](../../REQUIREMENTS.md) commits blive to importing an unmodified `btest.Strategy` dataclass. [REQUIREMENTS §5.13](../../REQUIREMENTS.md) commits to strategy discovery via Python modules exposing `build_strategy(config: dict) -> Strategy`. blive adds three sidecar extensions: `execution.live_overrides`, `costs.live_*_provider` hooks, `risk.live_kill_switch`.

DD-3 ([CONTEXT_INVENTORY §4](../../CONTEXT_INVENTORY.md#4-data-dictionaries-dds), MISSING) is the data dictionary for these YAML knobs. Before we author DD-3 we must lock the *shape*: where the canonical strategy spec lives, where blive-only overrides live, how they merge, and how the spec id (`sha256(resolved_yaml + ...)` per [REQUIREMENTS §5.12](../../REQUIREMENTS.md)) is computed.

Three options have been considered:

1. **Single YAML, btest-extended.** Extend btest's existing strategy YAML with new keys; btest must ignore unknown keys. Risk: btest's validators reject unknown keys; blive would have to fork btest's loader.
2. **Single YAML, blive-owned.** Replace btest's loader entirely; build the btest `Strategy` from blive's YAML. Risk: parallel maintenance of every btest DSL field shape; high drift.
3. **Hybrid: Python module produces `Strategy`, blive YAML provides live-only overrides keyed by strategy_id.** The Python module is btest's existing `build_strategy()`. blive's YAML lives next to the module and carries only blive-specific keys (live_overrides, kill_switch, NAV slice, artefact paths, RC threshold overrides).

### Decision

Adopt **Option 3 (hybrid)**.

**Strategy ingest pipeline:**

1. blive YAML at `~/.blive/strategies/{strategy_id}/live.yaml` declares:
   - `strategy_module: str` — dotted-path Python module (e.g. `btest.strategies.tkan_v4_momentum_timing`).
   - `build_strategy_kwargs: dict` — kwargs passed to the module's `build_strategy(**kwargs)` call.
   - `nav_slice: Decimal` — fraction of account NAV allocated; capped at 0.10 per [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10).
   - `live_overrides: { tif, routing, ib_algo, outside_rth, ... }` — overlays `Strategy.execution.live_overrides`.
   - `live_borrow_provider: { kind, config }` — overlays `Strategy.costs.live_borrow_provider`.
   - `live_financing_provider: { kind, config }` — overlays `Strategy.costs.live_financing_provider`.
   - `live_kill_switch: { max_intraday_drawdown, max_consecutive_rejects, ... }` — per-strategy kill criteria.
   - `artefact_paths: dict[str, str]` — overrides for `ExternalFactor.path` (so prod artefact path differs from research path per [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership)).
   - `risk_overrides: dict[str, Decimal]` — per-strategy overrides for [INV-4](../inv/risk_checks.md) thresholds (`max_data_staleness_intraday_sec`, `max_model_artefact_age_days`, etc.).

2. blive's loader (`blive.strategy.loader`) parses YAML via Pydantic v2 models (per CLAUDE.md "all tunables read from YAML config via Pydantic"), imports the module, calls `build_strategy(**build_strategy_kwargs)`, then applies overrides as a structured patch to the resulting `Strategy`.

3. **Spec id computation:** SHA-256 of `(canonical_yaml_bytes, strategy_module_dotted_path, btest_version, blive_version, artefact_sha256_for_each_external_factor)`. Recorded with every domain event per [REQUIREMENTS §5.12](../../REQUIREMENTS.md).

**Override merge rules:**

- Numeric scalars in `live_overrides` / `live_kill_switch` / `risk_overrides` overwrite by key.
- `artefact_paths` overwrites `ExternalFactor.path` by factor name.
- Forbidden overrides per [REQUIREMENTS §5.10](../../REQUIREMENTS.md): type fields, universe definition, factor / signal DAG topology. The override applier raises if a forbidden field appears.

### Alternatives Considered

1. **Single YAML btest-extended** — rejected (above): forks btest's loader.
2. **Single YAML blive-owned** — rejected (above): high drift maintenance.
3. **JSON Patch (RFC 6902) overrides** ([REQUIREMENTS §5.10](../../REQUIREMENTS.md) suggested this for runtime parameter overrides). Considered: structured, validated. Decision: keep JSON Patch as the mechanism for *runtime* parameter overrides (Strategy detail page form). Persistent strategy config uses the structured YAML schema above for ergonomics. Both end up applying patches against the resolved tree; the *grammar* of validation is the same.

### Consequences

- **Positive:** btest stays untouched; blive owns its sidecar config without forking. Strategy discovery is the existing Python-module pattern from REQUIREMENTS §5.13.
- **Positive:** YAML is human-readable for ops; Pydantic validation gives clear errors at startup.
- **Positive:** spec id remains stable across blive versions as long as YAML + module + artefact hashes don't change.
- **Negative:** two locations for "what the strategy is" — the Python module and the YAML. Ops must understand both.
- **Negative:** override application is a custom step; bugs there bypass btest's own validation. M1 unit tests must exercise allowed and forbidden override surfaces.
- **Follow-ups:** DD-3 codifies the field-level schema after this ADR is accepted; M1 implementation produces the Pydantic models; M2 IB adapter reads `live_overrides.routing` / `live_overrides.ib_algo` and feeds them through.

### Cross-References

- [REQUIREMENTS §5.1, §5.10, §5.12, §5.13](../../REQUIREMENTS.md) — strategy ingest, override grammar, spec id, sizer / discovery.
- [DD-3 config_schemas](../dd/config_schemas.md) — MISSING; authored against this ADR at M1.
- [INV-4](../inv/risk_checks.md) — risk threshold override paths.
- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — btest reuse contract.
- [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) — artefact prod path policy.

---

## ADR-029 — `PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

The M1 paper-mode end-to-end pipeline ([TASK_REGISTRY](../../TASK_REGISTRY.md) M1 deliverable 6) needs a deterministic CAC.PA bar source. Two shapes are viable:

1. **Ad-hoc fixture loading** — the test or runner reads a parquet file directly and feeds bars into the pipeline.
2. **`PaperMarketData` as a `MarketDataPort` adapter** — `blive.adapters.paper.market_data.PaperMarketData` implements the [INV-6 §1.2](../inv/ports_adapters.md#12-marketdataport) Protocol and reads from a fixture file.

The M0 retro recommendation 2 explicitly preferred (b). [INV-6 §2.2](../inv/ports_adapters.md#22-marketdataport-adapters) already lists `PaperMarketData` at M1 as MISSING. [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) commits to all data sources implementing the existing `DataSource` protocol — `PaperMarketData` is the live-side analogue of btest's `parquet://` source.

### Decision

Implement `blive.adapters.paper.market_data.PaperMarketData` as a `MarketDataPort` adapter. Concrete shape:

- **Source:** parquet file with columns `(open_time_utc, close_time_utc, open, high, low, close, volume)` and optional `vwap`. Path passed to constructor.
- **Frequency:** initial scope is `1d` (Phase 1 = F0). Fixture parquet implies the bar frequency; mismatched `subscribe_bars(freq=...)` raises.
- **Async iterator semantics:** `subscribe_bars(instrument, freq)` yields one `Bar` per row in chronological order, then awaits the next `clock.sleep(...)` tick if the runner is in real-time-paced mode, or yields immediately in tape-replay mode (M1 default).
- **`subscribe_trades`:** raises `NotImplementedError` for v1 (no trade-level fixtures yet; Phase 1 F0 daily strategies don't subscribe to trades).
- **`historical_bars`:** returns the slice of the fixture overlapping `[start, end]`; respects `instrument` lookup.
- **Fixture location:** `tests_slow/fixtures/paper_market_data/{venue}/{symbol}_{freq}.parquet` for committed test fixtures; arbitrary path admitted at runtime via constructor.

The adapter is the M1 substrate-level placeholder slot already declared in [INV-6 §2.2](../inv/ports_adapters.md#22-marketdataport-adapters). It also serves the long-running parity test (M7 continuous parity replay) by providing a deterministic playback engine inside blive's process.

### Alternatives Considered

1. **Ad-hoc fixture loading inside the test or runner.** Rejected per the M0 retro: violates [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) (the runner would have to know about parquet); doesn't exercise the `MarketDataPort` contract; M2's `IBMarketData` / `EODHDMarketData` would then have a different code path than M1's tests.
2. **Use btest's `parquet://` source verbatim.** Considered: btest's `DataSource` returns a `DataBundle` of full DataFrames, not a stream of `Bar` objects. The shapes don't align with `MarketDataPort.subscribe_bars` async-iterator contract. Bridge code would be larger than a clean reimplementation.
3. **Generate synthetic bars in-memory.** Considered for unit tests: too low-fidelity for the G2 ±1 bps parity test which needs real CAC.PA price history.

### Consequences

- **Positive:** unifies M1 paper test path with M2/M3 live test path — same `MarketDataPort` contract.
- **Positive:** the parity test is reproducible from a checked-in parquet (or a deterministic fetch script that re-creates it from EODHD when needed).
- **Positive:** the same adapter is the natural foundation for the M7 continuous-parity replica (`btest`-paper alongside live, see [ADR-012](#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)).
- **Negative:** writing the adapter is real M1 work (~1 small module + tests). The ad-hoc alternative is cheaper *for M1 only*.
- **Negative:** parquet fixture is repo weight; mitigated by limiting Phase 1 fixture to ≥ 252 trading days (~80 KB compressed for a single instrument).
- **Follow-ups:** the EODHD historical-fetch script that produces the fixture is a Phase-1 utility (`scripts/fetch_paper_fixture.py`); itself an M1 deliverable so the fixture is reproducible.

### Cross-References

- [INV-6 §1.2, §2.2](../inv/ports_adapters.md) — `MarketDataPort` contract; adapter slot.
- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — hexagonal contract; runner cannot read parquet directly.
- [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) — data sources via clean abstraction.
- [ADR-017](#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) — hybrid live data routing; M2 swaps in `IBMarketData` / `EODHDMarketData`.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M1 deliverable 6 — paper-mode end-to-end pipeline.
- [`docs/retros/M0_retrospective.md`](../retros/M0_retrospective.md) "Recommendations for NEXT_PROMPT M1" rec 2.

---

## ADR-030 — Per-archetype btest interpreter dispatch (amends ADR-010)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes)

### Context

[ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) commits blive to importing btest's "FactorEngine, SignalEngine, PortfolioEngine" rather than forking. M1 implementation surfaced two facts that ADR-010's prose does not capture:

1. `PortfolioEngine` is a **free function** (`compute_target_weights_for_date()` in `quantdsl_backtest.engine.portfolio_engine`), not a class, and it only handles `LongShortPortfolio`.
2. `TimingPortfolio` strategies — including the Phase 1 `tkan_v4_momentum_timing` 1× — are interpreted by `quantdsl_backtest.runners.single_asset.SingleAssetRunner`, a separate module that bundles factor evaluation, signal evaluation, and position derivation in one batch interpreter. This is **not** the three-engine composition ADR-010 names.

ADR-010's spirit ("reuse btest's strategy semantics, do not fork") is preserved — but its enumeration is incomplete, and the M1 paper pipeline already dispatches by archetype. [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) captured this gap with a working default and three resolution options.

### Decision

Adopt **per-archetype dispatch** as the canonical interpretation pattern between blive and btest, codified at the strategy-loader / runtime boundary. The dispatch table for v1:

| `strategy.portfolio` archetype | btest interpreter surface | blive call site |
|---|---|---|
| `LongShortPortfolio` | `FactorEngine` + `SignalEngine` + `compute_target_weights_for_date()` | M2+; not exercised at M1 (no LongShort strategy in Phase 1) |
| `TimingPortfolio` | `quantdsl_backtest.runners.single_asset.SingleAssetRunner.run(price_close=...)` | `blive.runtime.paper_pipeline` (M1); same path in IB-paper / live (M3+) |

Future archetypes (multi-instrument timing, basket rotation, etc.) register a new row when they land. Unrecognised archetypes raise `NotImplementedError` at strategy-load time, naming the archetype and pointing here.

ADR-010 stays ACCEPTED — its spirit holds; this ADR amends only the *enumeration of interpreters* as a complementary record, per [CONTEXT_PROTOCOL §2.5](../../CONTEXT_PROTOCOL.md) (decision log is append-only; we do not edit ADR-010's body).

### Alternatives Considered

1. **Reimplement `TimingPortfolio` inside blive** as a streaming evaluator. Rejected: reintroduces the drift ADR-010 was meant to prevent; ADR-012's parity contract becomes much harder to keep.
2. **Extend btest** to expose a class-shaped `TimingPortfolioEngine`. Rejected for v1: cross-project coordination cost; doesn't match how btest already structures runners; nothing forces a uniform shape across archetypes.
3. **Keep ADR-010 unchanged and treat dispatch as undocumented**. Rejected: leaves M2+ authors guessing; M1 retro already flagged this; phantom-decision anti-pattern ([CONTEXT_PROTOCOL §3.5](../../CONTEXT_PROTOCOL.md)).

### Consequences

- **Positive:** explicit dispatch table; new archetypes have a named home; M2+ adapter authors know where to plug in; ADR-010's spirit preserved.
- **Negative:** the table grows as archetypes land; small upstream-drift risk — mitigated by `tests/contracts/test_btest_imports.py` smoke-import contract.
- **Follow-ups:**
  - **KB-1 §6** prose (btest engines section) is now incomplete; an editorial pass should add one paragraph linking here. Tracked as a CONTEXT_INVENTORY priority-queue item; not a same-commit update because KB-1 lives btest-side and the canonical home is its file.
  - When M2+ exercises `LongShortPortfolio`, add a smoke test analogous to the `SingleAssetRunner` one in `test_btest_imports.py`.
  - `SingleAssetRunner` is batch-only ([RETRO-M1](../retros/M1_retrospective.md) "Recommendations"); when M3 introduces per-bar streaming dispatch, revisit the "blive call site" column.

### Cross-References

- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — reused-by-import policy (this ADR amends scope, does not supersede).
- [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) — resolved by this ADR.
- [KB-1 §6](../kb/btest_dsl_inventory.md) — btest engines section (forward-update follow-up).
- [`blive.runtime.paper_pipeline`](../../src/blive/runtime/paper_pipeline.py) — M1 dispatch site.
- [`tests/contracts/test_btest_imports.py`](../../tests/contracts/test_btest_imports.py) — smoke-import contract.
- [RETRO-M1](../retros/M1_retrospective.md) — "Surprises" raised this question.

---

## ADR-031 — Token-bucket rate limiter shape for IB adapters

- **status:** ACCEPTED
- **date:** 2026-04-27 (PROPOSED) / 2026-04-28 (ACCEPTED at M2-IB.2)
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[REQUIREMENTS §10 gotcha 1](../../REQUIREMENTS.md#10-ib-specific-gotchas-must-be-first-class-in-adapter) and [KB-3 §1](../kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle) require the IB adapter to throttle outbound calls below IB's 50 msg/sec hard cap (3 violations terminate the session). [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults) sets defaults: 20 msg/sec global ceiling; 5 msg/sec per-strategy ceiling (also [INV-4 RC-05/RC-06](../inv/risk_checks.md)). The rate limiter is the **first M2 code module** because it sits beneath both `IBBroker` and `IBMarketData`, and the G3 throttle test ("burst of 60 calls/sec; outbound rate stays ≤ 20 msg/sec") is the gate criterion.

Three algorithm options exist (token bucket, leaky bucket, sliding window) and three accounting choices (global only, per-strategy only, both).

### Decision

- **Algorithm:** **token bucket**, refilled at a constant rate. Two-level: a **global** bucket (default capacity = 20 tokens, refill = 20/s) and **per-strategy** sub-buckets (default capacity = 5 tokens, refill = 5/s). A call requires one token from the strategy bucket *and* one from the global bucket; if either is empty, the caller awaits until both refill.
- **Awaiting semantics:** the limiter's public method is `async def acquire(strategy_id: str) -> None`, blocking until both tokens are available. Caller never sees a rejection from the limiter — back-pressure flows through asyncio. The IB-side error code 100 ("max rate exceeded") is therefore *defence-in-depth*, not the primary throttle.
- **Clock source:** [`ClockPort`](../inv/ports_adapters.md#13-clockport). Tests use [`SimClock`](../../src/blive/adapters/clock/sim.py) to advance time deterministically.
- **Persistence:** in-memory only. Counters reset on process restart, which matches IB's view (the 50 msg/sec window resets on reconnect anyway). No SQLite row.
- **Configurability:** thresholds passed to constructor; defaults from [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults). Per-strategy override admitted via `RiskOverrides.max_orders_per_sec_strategy` at M4 ([INV-4 RC-05](../inv/risk_checks.md), forward-compat ignored at M2).
- **Module location:** `blive.adapters.ib.rate_limiter` — adapter-side, not domain-side. The domain has no rate-limit concept; this is purely how blive throttles its own outbound traffic to honour IB's contract.
- **Public surface:** `class TokenBucketRateLimiter`, with `acquire(strategy_id)`, `set_global_rate(...)`, `set_strategy_rate(...)`, plus a `metrics()` accessor for observability ([REQUIREMENTS §5.9](../../REQUIREMENTS.md): "IB throttle headroom" Prometheus gauge).

### Alternatives Considered

1. **Leaky bucket.** Equivalent throughput shape, but the two-level composition is awkward — leaky-bucket models smoothing, not budgeting. Token bucket maps cleanly to IB's "messages per second" budget.
2. **Sliding window.** Exact 1-second window; precise but storage-heavy (per-call timestamps); marginal benefit over token bucket at our message volumes.
3. **Global only (no per-strategy).** Rejected: violates [INV-4 RC-05](../inv/risk_checks.md) "≤ 5/sec per strategy" requirement; leaves a single misbehaving strategy able to consume the whole 20-token budget.
4. **Per-strategy only (no global).** Rejected: doesn't directly defend against the 50-msg/sec hard cap if many strategies fire simultaneously.

### Consequences

- **Positive:** simple, well-understood algorithm; deterministic via `ClockPort` for tests; pure-Python; no IB dependency (testable without the wire).
- **Positive:** the G3 throttle test (`burst of 60 calls/sec` → `≤ 20 msg/sec sustained`) becomes a unit test that runs in milliseconds with `SimClock`.
- **Negative:** two-level token bucket has slightly more state than a single counter; mitigated by simple internal structure (`dict[strategy_id, Bucket]`).
- **Negative:** the limiter does not back-pressure data-flow producers (e.g. `subscribe_bars`) — those are read-side IB callbacks, not outbound calls. Read-side flow control (if needed) is a separate concern.
- **Follow-ups:**
  - Prometheus gauge `blive_ib_throttle_headroom` populated from `metrics()` at M7.
  - When IB's hard cap changes (rare, but not unprecedented), bump the global default via [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults).
  - The `set_strategy_rate(...)` path is the integration point with [DD-3 §7 RiskOverrides](../dd/config_schemas.md#7-riskoverrides) when M4 widens that section.

### Cross-References

- [REQUIREMENTS §10 gotcha 1](../../REQUIREMENTS.md#10-ib-specific-gotchas-must-be-first-class-in-adapter), [§5.5 (rate limits)](../../REQUIREMENTS.md), [§5.9 (observability)](../../REQUIREMENTS.md).
- [KB-3 §1](../kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle), [§9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults).
- [INV-4 RC-05, RC-06](../inv/risk_checks.md) — order-rate risk checks (full set lands at M4).
- [INV-6 §1.3](../inv/ports_adapters.md#13-clockport) — `ClockPort`.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 deliverable 4 — `IBBroker` adapter (consumer of this limiter).

---

## ADR-032 — Instrument resolution policy: blive Instrument ↔ IB Contract

- **status:** PROPOSED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[DD-1 §2.1](../dd/domain_objects.md#21-instrument) defines `Instrument(symbol, venue, currency, asset_class, multiplier)` as the broker-neutral identity. The IB adapter must map this to an `ib_async.Contract` (and, internally, an integer `ConID`). [KB-2 §2](../kb/ib_capability_matrix.md#2-asset-classes) notes "`Contract` resolution is by `ConID` (an integer IB ID); blive's `Instrument` ↔ `Contract` mapping happens in `IBBroker` and is documented in DD-7 (MISSING)." DD-7 is the deferred MISSING artefact this ADR's design feeds into.

Three concerns: the field-level mapping; the ConID lookup mechanism + caching strategy; behaviour when `qualifyContracts()` returns multiple candidates (ambiguous symbology, e.g. `AAPL` on multiple exchanges).

### Decision

- **secType mapping:** `AssetClass.EQUITY` → `STK`; `AssetClass.ETF` → `STK` (IB does not distinguish ETFs from equities at secType); `AssetClass.INDEX` → `IND`; `AssetClass.FX` → `CASH`; `AssetClass.FUTURE` → `FUT`; `AssetClass.OPTION` → `OPT`. Unsupported asset classes raise `InstrumentNotResolvable` at the adapter boundary (don't reach the wire).
- **Field carry-through:** `symbol`, `currency` map directly. `venue` (MIC code, e.g. `XPAR`) maps to `ib_async.Contract.exchange` (e.g. `SBF`); the mapping is via a small static table (`MIC_TO_IB_EXCHANGE`) in the adapter, sourced from [KB-2 §5](../kb/ib_capability_matrix.md#5-routing). For Phase 1 the table only needs `XPAR → SBF`; new venues add rows.
- **ConID resolution:** lazy, on first use per Instrument. Call `ib.qualifyContractsAsync(contract)`; on success, cache `(Instrument → conId)` in memory keyed by full `Instrument` tuple equality.
- **Cache TTL:** process lifetime. `ConID`s are stable for non-corp-action instruments; corp actions (rare) invalidate the lookup, which is detected by IB returning a different conId or by an explicit `clear_cache(instrument)` call wired into M5 reconciliation.
- **Ambiguity:** when `qualifyContractsAsync()` returns >1 candidate (or `>1` after primaryExchange filter), raise `InstrumentAmbiguous(instrument, candidates)` with each candidate's `(conId, primaryExchange, currency)` listed. **Never silently pick one.** The caller must resolve via a more specific `Instrument` (typically by setting `venue` to the primary exchange MIC).
- **Module location:** `blive.adapters.ib.instrument_resolver` — pure adapter concern, not in the domain.
- **DD-7 publication:** this ADR's mapping table + cache contract are the DD-7 v0.1 substrate. DD-7 lands DRAFT in this commit batch; it goes STABLE when the M2 IBBroker exercises the path against IB Paper.

### Alternatives Considered

1. **Eager resolution at Instrument construction.** Rejected: would require IB connection at strategy-load time, violating layer purity ([ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement)) — domain code constructs `Instrument`s.
2. **Cache to disk.** Rejected for v1: ConIDs are cheap to re-resolve (one `qualifyContracts` round trip per instrument per process); persistence adds invalidation surface.
3. **Auto-disambiguate by primary exchange heuristic.** Rejected: the symbology surprises IB sometimes throws (e.g. a fund with the same ticker on two MICs) deserve an explicit error so the operator picks correctly.
4. **Bind `Instrument` directly to `ib_async.Contract`.** Rejected: breaks broker-neutrality; the `Instrument` would no longer round-trip to non-IB adapters (e.g. `EODHDDataSource`).

### Consequences

- **Positive:** clean broker-neutral identity; explicit ambiguity errors surface at the boundary; cache is in-process only (no persistence surface).
- **Negative:** the static MIC↔IB-exchange table is a substrate that drifts if IB renames a routing destination; pinned to KB-2 §5 with date-accessed citations.
- **Negative:** a fresh process re-resolves every instrument once; for Phase 1 (1 instrument) this is one round trip on startup — negligible; for many-instrument strategies the warm-up cost is bounded by [KB-3 §2](../kb/ib_pacing_spec.md#2-historical-data-pacing) historical-data pacing already.
- **Follow-ups:**
  - DD-7 STABLE flip when M2 IBBroker exercises the path successfully against IB Paper.
  - `clear_cache(instrument)` accessor wired into M5 reconciliation when corp-action handling lands.
  - The `MIC_TO_IB_EXCHANGE` table grows with each new venue (Phase 2/3 US equities → `XNAS`/`XNYS`/`ARCA` → `NASDAQ`/`NYSE`/`ARCA`).

### Cross-References

- [DD-1 §2.1](../dd/domain_objects.md#21-instrument) — `Instrument` shape.
- [KB-2 §2, §5](../kb/ib_capability_matrix.md) — IB asset classes + routing.
- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — broker-neutrality.
- [`docs/dd/instrument_dictionary.md`](../dd/instrument_dictionary.md) — DD-7 (DRAFT, this commit).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 substrate transitions — DD-7 MISSING → DRAFT.

---

## ADR-033 — `AccountUpdate` event shape and sampling cadence

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[INV-5](../inv/domain_events.md) catalogues `account.update` (M2 row) carrying an `AccountSnapshot` payload, with consumers "persistence (subsampled), UI". [REQUIREMENTS §6.5](../../REQUIREMENTS.md#65-data-retention) implies a 30 s sampling cadence for snapshots. `ib_async`'s `accountValuesEvent` fires on every IB push (potentially many times per second across many fields), so blive needs to define normalisation + cadence so the event bus is not flooded.

Two sub-decisions: (1) **payload** — what fields land in the emitted event; (2) **cadence** — how often blive emits.

### Decision

- **Payload type:** `AccountUpdate(snapshot: AccountSnapshot, time_utc: datetime)`. Reuses the existing [DD-1 §2.8](../dd/domain_objects.md#28-accountsnapshot) `AccountSnapshot` dataclass — no new fields. The wrapper carries a topic-friendly type identity for [INV-5](../inv/domain_events.md) and the `DomainEvent` union.
- **Cadence:** **30-second wall-clock subsample, with diff-suppress.** Internally the IB adapter accumulates the latest values from `accountValuesEvent`; a periodic 30-s task takes a snapshot, compares against the previously emitted one, and emits only when at least one field changed by more than its per-field threshold. Default thresholds:

  | Field | Threshold for emission |
  |---|---|
  | `equity` | ≥ 0.01 currency unit |
  | `cash_by_ccy[ccy]` | ≥ 0.01 currency unit |
  | `buying_power` | ≥ 0.01 currency unit |
  | `gross_exposure`, `net_exposure` | ≥ 0.01 currency unit |
  | `leverage` | ≥ 0.001 (3 d.p.) |
  | `margin_used` | ≥ 0.01 currency unit |

  Below threshold, no event; the next 30-s tick re-evaluates against the latest emission.

- **Persistence:** event-log append per [INV-5 §3](../inv/domain_events.md#3-persistence-ordering-rule) ordering rule (persist before publish). M4 SQLite tables will store full history; M1 in-memory persistence keeps the latest N for the UI (N=2,880 = 24h at 30-s cadence).
- **Subscription model:** the IB adapter calls `ib.reqAccountUpdates(True, accountId)` on connect; the 30-s timer is internal to `IBBroker.account_snapshot()` polling — `account_snapshot()` returns synchronously from cached state, the timer task is what produces emitted events.
- **Module location:** `blive.domain.events.AccountUpdate` (the dataclass — sits with the other domain events) + emission timer in `blive.adapters.ib.broker`.

### Alternatives Considered

1. **Emit every IB push.** Rejected: floods the event bus with tens of events per second of essentially the same state; [REQUIREMENTS §11](../../REQUIREMENTS.md) "event volume bounded by trade frequency, not market data" framing breaks.
2. **Emit on demand (no timer; only when a consumer calls `account_snapshot()`).** Rejected: misses the "periodic 30-s sample" framing of [REQUIREMENTS §6.5](../../REQUIREMENTS.md); UI dashboard wouldn't update without a polling consumer.
3. **Emit on every change, no thresholds.** Rejected: floating-point oscillation in `leverage` / `gross_exposure` would emit no-op events; the diff-suppress is cheap insurance.
4. **Vary the cadence per-field** (e.g. `buying_power` every push, `leverage` every minute). Rejected as premature; one cadence keeps the implementation simple and the diff-suppress thresholds carry the load.

### Consequences

- **Positive:** bounded event-bus load (≤ 1 emit per 30 s per account); UI dashboard refreshes at predictable cadence; no new domain types beyond a slim wrapper.
- **Positive:** `AccountSnapshot` reuse means the existing invariants ([DD-1 §2.8](../dd/domain_objects.md#28-accountsnapshot)) carry over.
- **Negative:** a sudden large change between 30-s ticks is observed at most 30 s late; acceptable for v1 (the dashboard is monitoring, not control).
- **Negative:** thresholds are per-currency-unit and may need scaling for high-NAV accounts; revisit at M7 with observed real-account behaviour.
- **Follow-ups:**
  - DD-2 row added in this commit batch.
  - When IB pushes `pnlSingle` / `pnl` events (per-position PnL), wire those into the same cadence as a separate `PnLUpdate` event family — out of M2 scope; flagged for M5 reconciliation.

### Cross-References

- [INV-5](../inv/domain_events.md#1-event-catalogue) — `account.update` row (M2).
- [DD-1 §2.8](../dd/domain_objects.md#28-accountsnapshot) — `AccountSnapshot` payload.
- [DD-2](../dd/event_schemas.md) — DRAFT in this commit; carries the field-level dictionary for `AccountUpdate`.
- [REQUIREMENTS §6.5](../../REQUIREMENTS.md#65-data-retention), [§11](../../REQUIREMENTS.md).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 substrate transitions — INV-5 widens with `AccountUpdate`.

---

## ADR-034 — Multi-broker registry pattern (extends ADR-004)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none (extends [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement))
- **resolves:** —

### Context

[ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) establishes hexagonal architecture: domain depends only on Ports; adapters implement them. M0+M1 shipped one concrete `BrokerPort` adapter (`PaperBroker`); M2-IB planned a second (`IBBroker`). The 2026-04-27 pivot to an IG demo bridge ([TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG) introduces a third (`IGBroker`), and the operator's directive — "make sure we have a clean abstraction layer for various broker apis" — asserts that we expect more, not just two.

The hexagonal Pattern alone does not specify:

- How a strategy YAML declares which broker it uses.
- Where per-broker config lives.
- How the runtime resolves the broker selection.
- How adapters discover their configuration.
- How credentials are loaded (split into [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets)).

These choices are currently implicit (M1 hardcoded `PaperBroker` construction in the test harness). Without explicit substrate, dispatch logic will accumulate as ad-hoc imports + conditionals across `runtime/`, `strategy/`, and `adapters/` — exactly the rot ADR-004 was meant to prevent. Substrate is needed before the second concrete adapter (IG) ships.

### Decision

Adopt a **multi-broker registry pattern**, layered on top of [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement). Concrete shape:

1. **Top-level config field.** [DD-3 §1](../dd/config_schemas.md#1-livestrategyconfig-top-level) gains a required top-level `broker: Literal["paper", "ig", "ib"]` field. Per-broker config blocks are optional sub-objects (`paper_config`, `ig_config`, `ib_config`); only the selected broker's block is read.

2. **Adapter package layout convention.** Each broker adapter family lives at `blive.adapters.{broker_name}`. Required modules per broker:
   - `broker.py` — the `BrokerPort` implementation (e.g. `IGBroker`, `IBBroker`, `PaperBroker`)
   - `market_data.py` — the `MarketDataPort` implementation
   - `instrument_resolver.py` — `Instrument` ↔ broker-specific identity (skip for `paper` which has no native identity)
   - `credentials.py` — credential schema + load helpers (per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets); skip for `paper`)

3. **Cross-cutting shared modules.** Pieces used by multiple broker adapters live under `blive.adapters.shared.*`:
   - `rate_limiter.py` — the [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) token-bucket algorithm, configured per-broker at construction (defaults supplied by each broker's KB).
   - `credentials.py` — env-var / file loading helpers per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets).

4. **Runtime dispatch.** A new module `blive.runtime.broker_registry` exposes:
   ```python
   def get_broker(name: str, config: BrokerConfig, *, clock: ClockPort) -> BrokerPort: ...
   def get_market_data(name: str, config: MarketDataConfig, *, clock: ClockPort) -> MarketDataPort: ...
   ```
   The registry maps broker names to factory functions. Importing the registry is the **only** path outside `blive.adapters.*` that knows which broker names exist; strategies, the Sizer, the RiskEngine, and the runtime never enumerate brokers directly.

5. **Strategy-broker binding.** The strategy loader resolves `LiveStrategyConfig.broker` via the registry before constructing the rest of the pipeline. A single blive process can run multiple strategies on different brokers simultaneously — each strategy holds its own `BrokerPort` instance from the registry; the registry caches per-(broker, account) connections so multiple strategies on the same demo account share a connection.

6. **Inventory tracking.** [INV-6 §2.1, §2.2](../inv/ports_adapters.md) widens to enumerate per-broker adapters as new rows. No new tables; broker dimension is just rows.

7. **Import-linter contract amendment.** The existing `Domain layer is broker-neutral (ADR-004)` contract stays unchanged. A **new** contract is added: `Broker registry isolation (ADR-034)` — only `blive.runtime.broker_registry` may import from `blive.adapters.{paper,ig,ib}.*`; no other `blive.runtime.*` or `blive.strategy.*` module may. Enforced via `lint-imports`.

### Alternatives Considered

1. **Implicit dispatch via type-checking at strategy-load time** (e.g. "if `LiveStrategyConfig.ig_config` is set, use IG; else `ib_config` → IB; else paper"). Rejected: encodes selection in config presence rather than declaration; surprises if multiple `_config` blocks are present; doesn't extend cleanly to runtime broker switching.
2. **Strategy module imports its broker adapter directly** ("the strategy's `build_strategy()` returns the `BrokerPort` it wants"). Rejected: violates [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) (strategies depend on Ports, not adapters); makes strategies broker-coupled; defeats the abstraction.
3. **Plugin-discovery via `setuptools` entry points.** Rejected for v1: adds installation-time complexity; the static `{paper, ig, ib}` set is small enough that explicit factory dispatch is clearer; revisit at M8+ if a third-party adapter ecosystem emerges.

### Consequences

- **Positive:** adding a new broker is mechanical — implement four modules under `blive.adapters.{name}.*`, register the factory in `broker_registry`, add a config block to DD-3, add KB pair, add INV-6 rows. No domain-side changes; no `runtime` changes.
- **Positive:** strategy YAML clearly declares which broker; per-broker config lives in its own block; multi-broker support is a property of the architecture, not bolted on.
- **Positive:** the contract is enforceable via `import-linter` — drift detected at CI time, not runtime.
- **Negative:** more substrate per broker (4 modules + 1 KB pair + 1 DD entry + 1 INV-6 entry); justified by "we expect more brokers, not fewer".
- **Negative:** the strategy YAML changes shape (top-level `broker` required) — a minor breaking change to [DD-3](../dd/config_schemas.md), mitigated by giving M1's PaperBroker `broker: "paper"` as the migration path.
- **Negative:** the registry adds an indirection between "load strategy" and "construct broker" that wasn't present in M1.
- **Follow-ups:**
  - [DD-3 §1](../dd/config_schemas.md#1-livestrategyconfig-top-level) amendment: top-level `broker` field + per-broker config blocks. M1 tests need a one-line addition (`broker: "paper"`).
  - [INV-6 §2.1, §2.2](../inv/ports_adapters.md) amendments: enumerate IG (new) + IB (PARKED) + Paper rows.
  - `pyproject.toml` import-linter amendment: new contract `Broker registry isolation (ADR-034)`.
  - New module: `blive.runtime.broker_registry` (M2-IG.2 deliverable).
  - The [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter relocates from "`blive.adapters.ib.rate_limiter`" to "`blive.adapters.shared.rate_limiter`" — that ADR's body update should accompany this one's ACCEPTED flip, or be captured as an amendment ADR if append-only discipline applies.

### Cross-References

- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — hexagonal architecture this ADR extends.
- [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) — rate limiter; this ADR generalises its module location.
- [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — secrets handling (paired with this ADR).
- [DD-3](../dd/config_schemas.md) — config schemas (amendment forthcoming in M2-IG.1 batch 2).
- [INV-6](../inv/ports_adapters.md) — port catalogue + adapter tracker (amendment).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG — the active milestone informed by this ADR.

---

## ADR-035 — Secrets handling discipline (`~/.blive/secrets/`)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[REQUIREMENTS §6.3](../../REQUIREMENTS.md#63-security--audit) commits to "credentials in OS keyring or env; never in repo or logs (log redaction list enforced)". The IG bridge ([TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG) brings the first concrete credentials surface — IG demo API key + username + password + account id — and the operator-pasted-them-in-chat moment confirmed we need explicit substrate, not implicit "we'll handle it when we get there".

Implicit "handle later" is a known anti-pattern; secrets discipline rots into "the test harness happens to read from an env var that nobody documented" and from there into "credentials end up in CI logs". This ADR fixes the shape before any code touches a credential.

### Decision

1. **Storage location.** Credentials live at `~/.blive/secrets/{broker}.env` outside the repo. One file per broker (e.g. `ig.env`, `ib.env`). KEY=VALUE format readable by `python-dotenv` or shell. File permissions `chmod 600` (operator's responsibility on Linux/macOS; on Windows, NTFS user-only ACL — documented when [`RUNBOOK.md`](../../RUNBOOK.md) lands at M5).

2. **Loading mechanism.** `blive.adapters.shared.credentials.load_credentials(broker_name) -> Credentials` reads the appropriate `~/.blive/secrets/{broker}.env`, validates required keys per the broker's schema (declared in `blive.adapters.{broker}.credentials`), and returns a frozen dataclass. **Env vars take priority over file values** — this lets Docker / systemd / CI inject credentials without writing files.

3. **Per-broker schema.** Each broker adapter declares its credential schema as a frozen dataclass in `blive.adapters.{broker}.credentials`:
   - **IG**: `IG_API_KEY`, `IG_USERNAME`, `IG_PASSWORD`, `IG_ACCOUNT_ID`, `IG_ENVIRONMENT ∈ {"demo", "live"}`.
   - **IB**: `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`, `IB_PAPER_ACCOUNT_ID` (no password — IB Gateway handles auth via IBC per [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events)).
   - **Paper**: empty (no credentials needed).

4. **Repo discipline.**
   - No credentials in git history (the inverse — committing a real secret — is a security incident requiring rotation, not a typo).
   - No credentials in tests; unit tests use mocked `Credentials` instances; integration tests against demo accounts pull from `~/.blive/secrets/`.
   - No credentials in commit messages, ADRs, OQs, or any `docs/` artefact.
   - A `secrets/` directory at repo root holds **example files** with placeholder values: `secrets/ig.env.example`, `secrets/ib.env.example`. Real `.env` files live outside the repo. `.gitignore` blocks `secrets/*.env` (only `.example` files committed).

5. **Log redaction.** A new `blive.utils.logging` module (M2-IG.2 deliverable) maintains a redaction list of credential field names (constructed from the union of every broker's credential-schema fields). Any log message containing a value matching a redaction-list key gets the value replaced with `[REDACTED]` before emission. The list is populated at process start by walking `blive.adapters.{paper,ig,ib}.credentials` schemas.

6. **Chat / transcript discipline (operational, not enforceable in code).** Credentials shall not be pasted into Claude Code conversations or any tool whose transcripts are logged externally. When credentials need to be communicated (e.g. operator → blive process), the channel is the `~/.blive/secrets/` files. Claude does not echo credentials it has been told and does not write them into any file in the repo.

### Alternatives Considered

1. **OS keyring as default** (Windows Credential Manager / macOS Keychain / Secret Service via the `keyring` Python package). Rejected as default: keyring is per-user-session and complicates Docker deployment; the file path is portable across host and container with a volume mount. Keyring remains an opt-in path via a future `KEYRING_BACKEND=…` env var; not v1.
2. **Plain env vars only.** Rejected: env vars work but are awkward for many keys; `.env` files are more ergonomic for the operator.
3. **HashiCorp Vault or equivalent.** Rejected for v1: massive overkill for a single-operator setting. Worth revisiting only if the project goes multi-operator.

### Consequences

- **Positive:** credentials never enter git history; each broker's credential schema is explicit; loading is one call.
- **Positive:** redaction protects against accidental log leaks (developer-side). The discipline is auditable.
- **Positive:** migration path to OS keyring or Vault is clean — swap the loader implementation; the schema dataclasses don't change.
- **Negative:** operator must maintain `~/.blive/secrets/` files manually (acceptable for v1 single-operator; flagged for the [`RUNBOOK.md`](../../RUNBOOK.md) draft at M5).
- **Negative:** Docker deployment requires volume mount for `~/.blive/secrets/` — documented at M5 alongside `RUNBOOK.md`.
- **Negative:** redaction list maintenance is manual; new credential keys must be added when new brokers land — the union-walk at process start makes drift detectable but not prevented.
- **Follow-ups:**
  - `.gitignore` rule: `secrets/*.env` (block all but `.example` files).
  - `secrets/.gitkeep` + `secrets/ig.env.example` + `secrets/ib.env.example` committed at first M2-IG.2 code session.
  - `blive.utils.logging` module with redaction; M2-IG.2 deliverable.
  - `blive.adapters.shared.credentials` loader; M2-IG.2 deliverable.
  - Each broker's `credentials.py` schema; M2-IG.3 (IG) / M2-IB resumption (IB).

### Cross-References

- [REQUIREMENTS §6.3](../../REQUIREMENTS.md#63-security--audit) — credentials policy.
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; this ADR is its operational pair.
- [INV-6 §1.1](../inv/ports_adapters.md#11-brokerport) — `BrokerPort` (consumes credentials at construction).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG — first milestone using this discipline.

---

## ADR-036 — IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) commits blive to multi-broker support; the IG bridge (M2-IG) is the first non-paper broker landing. IG Markets exposes its API via two channels:

- **REST** for connection management, account queries, instrument search, and order placement (`POST /session`, `GET /accounts`, `GET /positions`, `POST /positions/otc`, `GET /markets`, `GET /prices`, etc.).
- **Lightstreamer** (a streaming protocol over HTTP) for live price subscriptions and trade-update events.

Two driver options:

1. **`trading_ig`** — community Python wrapper for IG. Sync-leaning (uses `requests`); ~600 GitHub stars; reasonably maintained but the asyncio story is awkward.
2. **Roll our own** — `httpx` for async REST + an asyncio Lightstreamer client.

### Decision

**Roll our own.** Concretely:

- **REST client**: `httpx.AsyncClient` for async HTTP. The IG API surface needed for v1 is small (~10 endpoints); a focused module is cleaner than wrapping a sync library.
- **Lightstreamer client**: official IG-recommended `lightstreamer-client-lib` (Python; supports asyncio). Streaming subscriptions wrapped per-instrument inside `IGMarketData`.
- **Module location**: `blive.adapters.ig.client.IGClient` owns auth state (CST + X-SECURITY-TOKEN headers); used by both `IGBroker` and `IGMarketData`.
- **Auth flow**: `IGClient.connect()` performs the 3-step REST auth (`POST /session` → header tokens stored), and starts a Lightstreamer session using the same credentials. `IGClient.close()` calls `DELETE /session`. Token TTL is 6 h on demo / 24 h on live; auto-refresh via `POST /session/refresh-token` on 401.
- **Rate limiting**: outbound REST calls go through `blive.adapters.shared.rate_limiter` ([ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters), now broker-agnostic per [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004)) configured per [ADR-038](#adr-038--ig-rate-limit-defaults-parameterise-adr-031).
- **Error handling**: HTTP errors mapped to typed engine exceptions (`IGAuthError`, `IGRateLimited`, `IGOrderRejected`, `IGSessionExpired`, …) at the adapter boundary. Specific code mapping in [KB-17](../kb/ig_pacing_spec.md) §"Error codes".
- **Dependencies pinned in `pyproject.toml`**: `httpx>=0.27,<0.28`, `lightstreamer-client-lib>=2.0` (verify exact pin at first install).

### Alternatives Considered

1. **`trading_ig`.** Sync model fights [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1) (single asyncio loop). Wrapping in `asyncio.to_thread` adds threading concerns we just got rid of in M0. The library also pulls `pandas`/`requests` we'd otherwise control narrowly. Rejected.
2. **CCXT.** IG is not a CCXT-supported venue. Rejected.
3. **gRPC sidecar wrapping `trading_ig`.** Operationally heavy; defers the asyncio mismatch rather than solving it. Rejected.

### Consequences

- **Positive:** asyncio-native; clean fit with [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1); narrow dependency surface (`httpx`, `lightstreamer-client-lib`); errors mapped to typed exceptions at the boundary.
- **Positive:** "small enough to read" — ~10 REST endpoints + Lightstreamer subscriptions is bounded.
- **Negative:** more code to write and maintain than wrapping an existing library. Justified by the small surface area.
- **Negative:** Lightstreamer is a non-trivial protocol; we depend on `lightstreamer-client-lib` for the streaming layer. If that library stalls, vendor-fork plan flagged for OQ at first sign of trouble.
- **Follow-ups:**
  - `IGClient` module + `IGAuthError`/`IGRateLimited`/etc. typed-exception hierarchy in M2-IG.3.
  - First-pass `INV-?` IG error-code inventory drafted from observed responses; analogous to MISSING [INV-14](../inv/ib_error_codes.md) for IB.
  - Pin verification: `httpx` and `lightstreamer-client-lib` versions confirmed at first install.

### Cross-References

- [ADR-002](#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver) — IB analogue (we adopted a wrapper for IB; for IG no good wrapper exists).
- [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1) — single-loop asyncio commitment.
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; this driver lives under that pattern.
- [ADR-038](#adr-038--ig-rate-limit-defaults-parameterise-adr-031) — IG rate-limit defaults consumed by this driver.
- [KB-17 IG pacing spec](../kb/ig_pacing_spec.md) — DRAFT this batch.

---

## ADR-037 — `Instrument.tradability` field (spot / cfd / spread_bet)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none (extends [DD-1 §2.1](../dd/domain_objects.md#21-instrument))
- **resolves:** —

### Context

[DD-1 §2.1](../dd/domain_objects.md#21-instrument) defines `Instrument(symbol, venue, currency, asset_class, multiplier)` as the broker-neutral identity of a tradable thing. The `asset_class` enum has `EQUITY`, `ETF`, `INDEX`, `FX`, `FUTURE`, `OPTION`. None of these distinguish *how* the instrument is held: an `ETF` `Instrument` could be physical shares (cash equity), or a CFD on the same underlying, or a spread bet — three very different cost / leverage / settlement / tax profiles.

The IG bridge ([M2-IG](../../TASK_REGISTRY.md)) turns this abstract concern into a concrete one: `CAC.PA` ETF on IB ([ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)) and `IX.D.CAC40.CASH.IP` CFD on IG are both broadly "CAC 40 exposure" but they're not interchangeable instances of `Instrument`. The Sizer's [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) integer-share rounding is correct for ETF shares and wrong for CFDs (which allow fractional contracts).

### Decision

Add `tradability: Literal["spot", "cfd", "spread_bet"] = "spot"` to `Instrument` ([DD-1 §2.1](../dd/domain_objects.md#21-instrument)) as a new field with default value, backward-compatible.

Semantics:

- **`"spot"`** — physical position in the underlying; cash equity / ETF / direct FX / direct futures contract. ADR-027 integer-share rounding applies. This is the M0+M1 default; no existing `Instrument` construction needs to change.
- **`"cfd"`** — Contract for Difference; fractional position size allowed; per-instrument precision (e.g. 0.01 for CAC 40 CFD on IG; 0.1 for some FX CFDs). The Sizer's quantize step uses an instrument-derived precision instead of the integer-share rule. Overnight financing applies.
- **`"spread_bet"`** — UK spread bet; sized in £/point; tax-free for UK retail. Quantize step uses pence-per-point precision. Overnight financing applies.

The Sizer's `quantize_share_qty(raw, *, precision=Decimal("1"))` already accepts a `precision` parameter; the change is at the *call site* — it picks `Decimal("1")` for `tradability=="spot"` and `Decimal("0.01")` (or whatever the instrument declares) for CFDs / spread bets.

The `Instrument` identity tuple ([DD-1 §2.1](../dd/domain_objects.md#21-instrument) "Equality / hashing") widens to include `tradability` — `CAC.PA` ETF and `IX.D.CAC40.CASH.IP` CFD are distinct `Instrument`s.

### Alternatives Considered

1. **Encode tradability in `venue`** (e.g. `venue="IG_DEMO_CFD"`). Rejected: conflates the venue (where the instrument trades) with the broker primitive (how it's held). Two separate concerns that should not be smashed into one field.
2. **Encode tradability in `asset_class`** (e.g. add `CFD`, `SPREAD_BET` enum members). Rejected: a CFD on `EQUITY` and a CFD on `INDEX` are still meaningfully different at the asset-class level; `tradability` is orthogonal to `asset_class`.
3. **Parallel `Instrument` types** (e.g. `CFDInstrument`, `SpreadBetInstrument`). Rejected: explodes the domain-type surface; the broker-neutral identity is one type, and tradability is just a discriminator on it.
4. **Defer the decision; have the Sizer call broker-specific code paths.** Rejected: violates [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) (Sizer is domain code; adapters are not).

### Consequences

- **Positive:** backward-compatible (default `"spot"`); M0+M1 tests need no change. The CAC.PA ETF `Instrument` continues to construct without tradability and defaults to `"spot"`.
- **Positive:** minimal expansion to the type surface; one field, one enum literal, zero new dataclasses.
- **Positive:** Sizer rule branches on `tradability`, not on broker — domain-side; broker-neutral.
- **Negative:** [DD-1 §2.1](../dd/domain_objects.md#21-instrument) and `src/blive/domain/types.py` need to be amended. DD-1 stays STABLE because the change is additive with default; `types.py` add the field; existing tests construct `Instrument(...)` without keyword-args other than the original five and continue to work.
- **Negative:** the Sizer has a new branching rule; per-instrument precision needs to be sourced from somewhere (probably an `IGInstrumentMetadata` mapping inside the IG adapter, or an extra field on `Instrument`). Resolved at M2-IG.2 / .3 time.
- **Follow-ups:**
  - DD-1 amendment (STABLE v0.1 → v0.2) lands in M2-IG.2 alongside the `types.py` change. Same commit.
  - Sizer ([`src/blive/sizing/sizer.py`](../../src/blive/sizing/sizer.py)) gets a per-instrument precision lookup. Open: where does precision live — on `Instrument`, on `LiveStrategyConfig`, or fetched from the broker adapter? Default lean: `Instrument.precision` field (broker-neutral, simple); revisit if a single instrument needs different precisions per broker (unlikely).
  - [`tests/conftest.py`](../../tests/conftest.py) `cac_pa` fixture stays unchanged (defaults `"spot"`); a new `cac40_cfd` fixture lands at M2-IG.3.

### Cross-References

- [DD-1 §2.1](../dd/domain_objects.md#21-instrument) — `Instrument` shape (amendment forthcoming in M2-IG.2).
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — CAC.PA ETF (PAUSED for the bridge per ADR-039).
- [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) — integer-share rounding (now scoped to `tradability=="spot"`).
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; the IG vs IB distinction surfaces this need.
- [ADR-039](#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) — Phase 1 under bridge (uses `tradability="cfd"`).

---

## ADR-038 — IG rate-limit defaults (parameterise ADR-031)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none (parameterises [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters))
- **resolves:** —

### Context

[ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) defined a two-level token-bucket rate limiter with **IB-specific defaults** (20 msg/sec global, 5 msg/sec per-strategy) sourced from [KB-3 §1, §9](../kb/ib_pacing_spec.md). [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) generalised the limiter's location (`blive.adapters.shared.rate_limiter`) but left per-broker default budgets unspecified.

IG's published limits — see [KB-17 IG pacing spec](../kb/ig_pacing_spec.md) — are roughly an order of magnitude tighter than IB's, and have a different shape: per-minute buckets, separate buckets for trading vs general vs historical, plus a Lightstreamer subscription budget.

### Decision

Make the [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter accept a **per-bucket configuration table** at construction time, and ship the IG defaults in `blive.adapters.ig`. Concretely:

```python
@dataclass(frozen=True)
class RateLimitBucket:
    capacity: int
    refill_per_second: Decimal

@dataclass(frozen=True)
class RateLimitConfig:
    buckets: Mapping[str, RateLimitBucket]  # keyed by bucket name
```

The IG defaults (`blive.adapters.ig.rate_limiter.IG_DEFAULT_RATE_LIMITS`):

| Bucket | Capacity | Refill | Source |
|---|---|---|---|
| `global` | 30 | 0.5 / s (= 30/min) | IG REST general; [KB-17 §1](../kb/ig_pacing_spec.md) |
| `trading` | 60 | 1.0 / s (= 60/min) | IG REST trading endpoints (`/positions/otc`, `/workingorders/otc`); [KB-17 §1](../kb/ig_pacing_spec.md) |
| `historical_prices` | 40 | 2/3 per s (= 40/min) | IG REST `/prices`; [KB-17 §1](../kb/ig_pacing_spec.md) |
| `lightstreamer_subscriptions` | 40 | n/a (concurrent budget, not a refill bucket) | [KB-17 §3](../kb/ig_pacing_spec.md) |

Each call site declares which bucket it draws from — e.g. `IGBroker.submit()` consumes from `trading`; `IGMarketData.historical_bars()` consumes from `historical_prices`; everything else from `global`. The `lightstreamer_subscriptions` "budget" is enforced as a concurrent-subscription counter inside `IGMarketData`, not the token-bucket algorithm (no refill semantics).

The IB defaults (`blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS`) preserve [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) values: `global` 20/s, `per_strategy_*` 5/s, etc. They live in the parked M2-IB code surface (not implemented yet) but the config shape is now uniform.

Per-strategy overrides are admitted via [DD-3 §7 RiskOverrides](../dd/config_schemas.md#7-riskoverrides) when M4 widens that section; M2 reads constructor defaults only.

### Alternatives Considered

1. **Hardcode IG defaults in the limiter.** Rejected: makes the limiter broker-aware, breaks the shared-module abstraction.
2. **Per-broker subclasses of the rate limiter.** Rejected: the algorithm is shared; only the config differs.
3. **Single global ceiling, ignore per-bucket distinctions.** Rejected: IG's trading/general/historical buckets really are separate at the IG side; a single ceiling either over-throttles trading or under-throttles general.

### Consequences

- **Positive:** uniform algorithm across brokers; per-broker config localised in the broker's own module; the [G3-IG throttle test](../../TASK_REGISTRY.md) exercises the limiter with real IG defaults.
- **Positive:** the limiter stays in `blive.adapters.shared.rate_limiter`; no broker-specific code in domain or runtime.
- **Negative:** the limiter is now slightly more configurable than the M2-IB ADR-031 needed; minor over-engineering justified by "we now have two brokers".
- **Follow-ups:**
  - The [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) body's "Public surface" sketch was per-strategy-only; it widens to the named-bucket shape under this ADR. Documented as a cross-reference here; ADR-031's body stays unchanged (append-only), readers follow the cross-ref.
  - `IGMarketData` Lightstreamer subscription counter implementation in M2-IG.3.
  - When M4 surfaces `RiskOverrides.max_orders_per_sec_strategy` etc., the IG strategy defaults (60/min) are the cap; per-strategy config can only narrow, not widen.

### Cross-References

- [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) — algorithm and shape; this ADR parameterises its config.
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; rate limiter relocation.
- [KB-17 §1, §3](../kb/ig_pacing_spec.md) — DRAFT this batch; numerical source.
- [INV-4 RC-05, RC-06](../inv/risk_checks.md) — order-rate risk checks (M4 widens to consume per-broker config).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG G3-IG gate — throttle test references these defaults.

---

## ADR-039 — Phase 1 strategy under IG bridge: CAC 40 CFD

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

The Phase 1 plan ([TASK_REGISTRY](../../TASK_REGISTRY.md)) was: run `tkan_v4_momentum_timing` 1× as the `CAC.PA` ETF on IB Paper, ±1 bps parity vs btest, ≥ 5 trading days, 5–10% NAV slice. The 2026-04-27 IG bridge pivot needs an explicit answer to: **what is the strategy's tradable instrument under the bridge, and what does "the strategy works on IG demo" mean concretely?**

Three things change under the bridge:

1. **Instrument.** IG retail UK accounts trade CFDs and spread bets, not actual ETF shares. The closest CAC 40 exposure is a CAC 40 cash CFD (`tradability="cfd"` per [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet)).
2. **Cost model.** CFDs charge daily overnight financing (tom-next or similar) instead of (or in addition to) the ETF's internal swap cost. Btest's [`FinancingCost`](../kb/cost_margin_dictionary.md#5-financingcost) handles the financing curve, but CFD-specific spread is a new component.
3. **Parity envelope.** The G2-IB ±1 bps target was tight because the only legitimate divergence was share-rounding ([ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero)). CFD financing-cost variability (intraday tom-next moves; weekend financing rolls) makes ±1 bps unachievable. The bridge needs a different envelope.

### Decision

1. **Tradable instrument.** `Instrument(symbol="CAC40", venue="IG_LDN", currency="EUR", asset_class=AssetClass.INDEX, tradability="cfd")` resolved by [DD-8](../dd/ig_instrument_dictionary.md) to IG epic — first guess `IX.D.CAC40.CASH.IP`, confirmed against `/markets?searchTerm=CAC%2040` on first IG handshake. The exact symbol/venue/currency triple may shift when the handshake confirms; this ADR locks the *concept*, not the keys.
2. **[ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) status: PAUSED** (not SUPERSEDED). The CAC.PA ETF path resumes when IB returns; ADR-021's choice is still correct for that path. The bridge runs in parallel.
3. **NAV slice**: unchanged — 5–10% per [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10), hard cap 10%. CFD leverage built into the contract is irrelevant to NAV-slice computation; we slice account equity, not gross exposure.
4. **Cost model**: btest's `FinancingCost` curve handles base rate (ESTER); CFD financing spread adds ~25–50 bps annualised on top — provided as a `LiveFinancingProvider` override per [DD-3 §4](../dd/config_schemas.md#4-livefinancingprovider) when the bridge runs. Exact spread observed from IG `/positions` at first run; documented in [`docs/retros/M2-IG_retrospective.md`](../retros/) for future reference.
5. **Parity envelope**: the ±1 bps target is **not** the M2-IG.5 success criterion. Instead:
   - **Directional alignment**: every rebalance day's signed position matches btest's signed position (sign-only test). This is the strongest claim under CFD friction.
   - **Magnitude envelope**: end-of-period equity-curve divergence < 100 bps over the 5-day run, with the gap *characterised* (financing cost vs spread vs share-rounding-on-CFD-fractional-precision). The "characterised" requirement is harder than just "< 100 bps"; we need to attribute the residual.
   - The full parity diagnostic ([ADR-012](#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)) for M7 can absorb CFD-specific decomposition; M2-IG.5 is a sanity check, not a calibration.
6. **TKAN artefact**: unchanged. [ADR-022](#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) apply identically; broker-agnostic.
7. **Sizer rounding**: per [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet) `tradability="cfd"` rule — fractional contracts at the IG-instrument's declared precision (CAC 40 CFD on IG is typically 0.01 contract minimum; verified at first handshake).

### Alternatives Considered

1. **Skip the strategy, just exercise IG read-side connectivity.** Rejected: operator's intent is "exercise the broker abstraction with a real venue end-to-end". Stopping at read-side leaves the multi-broker abstraction untested under writes.
2. **Different instrument** (e.g. SP500 CFD on IG). Rejected: changes more variables than necessary; the strategy is calibrated against CAC; staying with CAC isolates the broker / tradability variables.
3. **Spread bet instead of CFD.** Rejected as default for v1 bridge: spread-bet sizing in £/point is more friction; CFD aligns better with the existing notional-EUR strategy mental model. Spread-bet path remains an option later.
4. **Tighter parity envelope (e.g. ±10 bps).** Rejected: financing-cost variability at IG demo over 5 trading days can exceed 10 bps just from the demo's idiosyncratic financing curve. 100 bps is the right "sanity check, not calibration" envelope.

### Consequences

- **Positive:** the bridge has a concrete, falsifiable success criterion that doesn't require chasing a parity envelope that's not achievable on CFDs anyway.
- **Positive:** ADR-021 stays valid for IB return; no decision is reversed; the bridge is a parallel track.
- **Negative:** the M2-IG.5 retro will record a CFD-financing characterisation that doesn't directly inform the M2-IB / M3 future ±1 bps target. Some M2-IG learning is bridge-specific.
- **Negative:** CFD financing is an additional cost component the operator hasn't seen in btest historical results; the strategy's net P&L on IG demo will differ from btest's net P&L by a non-trivial margin even when "directionally aligned".
- **Follow-ups:**
  - First IG handshake confirms the CAC 40 CFD epic; DD-8 row updated.
  - First IG `/positions` query records the demo's actual financing rate; documented.
  - Sizer per-instrument precision lookup: M2-IG.2/.3 work.
  - Strategy `LiveStrategyConfig` for the bridge: `~/.blive/strategies/tkan_v4_momentum_timing_1x_ig/live.yaml` with `broker: "ig"` per [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) plus `live_financing_provider` override for IG's CFD financing curve. Concrete YAML lands in M2-IG.5.

### Cross-References

- [ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) — v1 scope (bridge phase exercises CFD; ETF path resumes when IB returns).
- [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10) — NAV slice (unchanged).
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — CAC.PA ETF (PAUSED for the bridge).
- [ADR-022](#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) — TKAN artefact policy (unchanged).
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004), [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — multi-broker / secrets substrate.
- [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet) — `tradability="cfd"`.
- [DD-8 IG instrument dictionary](../dd/ig_instrument_dictionary.md) — DRAFT this batch.
- [TASK_REGISTRY M2-IG.5](../../TASK_REGISTRY.md) — strategy run + retro milestone.

---

## ADR-040 — Phase 1 deployment target: Windows host with native IB Gateway

- **status:** ACCEPTED
- **date:** 2026-04-28
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[TASK_REGISTRY M2-IB §"Operator-side prerequisites"](../../TASK_REGISTRY.md) requires deciding the deployment target before M2-IB.3 first wire-level handshake. [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model) commits to "Linux preferred, Windows supported (the user runs Windows 11 daily; production target is Linux VM/box)" but does not pin the Phase 1 dev/paper-mode choice.

The decision matters because it drives:

- Whether IB Gateway runs in Docker (`gnzsnz/ib-gateway-docker` per [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model) + [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events)) or as a native Windows process.
- Whether IBC ([KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events)) automates the daily 23:45 ET TWS restart or the operator handles it manually.
- How the [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) `~/.blive/secrets/` discipline maps onto Windows NTFS ACLs vs Linux `chmod 600`.
- The latency / reliability profile of the M2-IB.5 ≥ 5-trading-day strategy run.

### Decision

For Phase 1 (M2-IB through M3 / G4 gate) use the **Windows host with native IB Gateway**, no Docker, no IBC. Concretely:

- Operator installs IB Gateway from the IB website (the "offline" installer per [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) recommendation).
- Operator launches IB Gateway manually, logs in to the paper account, leaves the process running.
- blive (running natively on Windows under `uv`) connects via TCP `127.0.0.1:4002`.
- Daily 23:45 ET restart is **operator-managed** for Phase 1: blive's [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation) reconciliation loop already handles disconnect-then-reconnect; the operator just needs to log Gateway back in once a day during the M2-IB.5 5-day run.
- File permissions: `~/.blive/secrets/ib.env` lives at `C:\Users\olegr\.blive\secrets\ib.env`. Per-user-only NTFS ACL is the Windows analogue of `chmod 600`; Phase 1 relies on the file being inside the user profile (already access-controlled by the OS for non-admin processes). The full ACL hardening lands when [`RUNBOOK.md`](../../RUNBOOK.md) gets authored at M5 per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) §"Consequences".

Linux VM / Docker / IBC are **deferred to the production cutover at M8+** ([REQUIREMENTS §14](../../REQUIREMENTS.md) M8: "Hardening: ... ops runbook ... 2-week unattended paper trade clean").

### Alternatives Considered

1. **Linux VM with Docker (`gnzsnz/ib-gateway-docker` + IBC).** Rejected for Phase 1: operationally more standard and what the production cutover wants, but adds VM-host overhead, Docker-Desktop install, container-volume mounts for credentials, and a Linux-side ops layer that the user has not yet picked. The complexity is appropriate when the cutover to live trading is in scope (M8+); paying it now buys nothing for paper-mode dev. [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model)'s "Linux preferred" guidance applies to the production target, not the Phase 1 paper-mode workflow.
2. **WSL2 with Docker on Windows.** Considered as a hybrid. Lower friction than a full VM but still adds a container layer + IBC config. Worth re-evaluating at M5 when the operational story matures; not needed for Phase 1.
3. **TWS Desktop instead of IB Gateway.** Rejected: TWS has the same daily-restart and pacing characteristics ([KB-2 §1](../kb/ib_capability_matrix.md#1-connectivity-surface)), heavier UI, no operational benefit for headless-style automation. Gateway is the standard for API-only workflows.

### Consequences

- **Positive:** Lowest possible setup friction for the M2-IB.3 first handshake. Operator runs IB Gateway, fills in `~/.blive/secrets/ib.env`, runs blive's smoke probe — three steps, no VM / Docker / IBC config.
- **Positive:** No new dependencies or container-runtime requirements. blive runs the same way it has since M0 (`uv run`, native Windows process).
- **Positive:** Decision is reversible — switching to a Linux VM at M8 doesn't invalidate Phase 1 work; the abstraction layers (broker registry, IBClient, IBCredentials) are deployment-target-agnostic.
- **Negative:** Daily 23:45 ET TWS-restart window requires operator attention during the M2-IB.5 ≥ 5-trading-day strategy run. Acceptable for Phase 1 (paper, single-operator, dev workflow); blive's reconciliation handles the disconnect/reconnect transient correctly per [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation).
- **Negative:** NTFS-ACL credential-file hardening is deferred (per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) "Consequences" already flagged for M5). Phase 1 risk is bounded by the file living inside the user profile and the system being a single-operator workstation.
- **Negative:** Re-doing the deployment at M8 will require a fresh setup pass on the Linux VM (Docker + IBC + secret-volume-mounts + systemd / `restart: always`); documented but not pre-built.
- **Follow-ups:**
  - M2-IB.3 first-handshake validation runs on the Windows native target.
  - [`RUNBOOK.md`](../../RUNBOOK.md) (M5) documents the Linux VM / Docker path as the production target with concrete steps.
  - Re-evaluate at the [G4 → Phase 2 readiness audit](../../CONTEXT_PROTOCOL.md#832-phase-boundary-rule) whether Phase 2 strategies justify the Linux migration earlier.
  - The existing [TASK_REGISTRY M2-IB §"Operator-side prerequisites"](../../TASK_REGISTRY.md) "Decide deployment target" item is closed by this ADR.

### Cross-References

- [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model) — operational model (Linux preferred for production).
- [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — secrets handling (NTFS ACL note).
- [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) — daily TWS restart + IBC + offline installer.
- [KB-8 §1](../kb/operational_events.md#1-daily-tws--ib-gateway-restart) — daily restart engine response.
- [TASK_REGISTRY M2-IB](../../TASK_REGISTRY.md) — M2-IB.3 prerequisite this ADR resolves.

---

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. ADR-001..012 backfill from REQUIREMENTS rationale; ADR-013..019 from Oleg's 2026-04-26 OQ resolution session.
- **v0.2 (2026-04-26)** — added ADR-020..023 covering Phase 1 operational specifics: NAV slice (5–10% cap 10%), CAC ETF proxy (`CAC.PA`), TKAN freshness window (30d hard / 21d warn), TKAN artefact path and refresh ownership.
- **v0.3 (2026-04-26)** — added ADR-024 (RETRO artefact type) and ADR-025 (protocol amendment for milestone-close + phase-boundary handoff rules).
- **v0.4 (2026-04-26)** — added ADR-026 (agentic-execution layer; human-governance / agent-execution division of labour; five-layer adoption stack).
- **v0.5 (2026-04-27)** — added ADR-027 (Sizer rounding policy: integer shares, truncate toward zero), ADR-028 (Strategy config shape: Python `build_strategy()` + blive YAML overrides), ADR-029 (`PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet) — drafted PROPOSED, accepted by operator same day; status flipped to ACCEPTED for all three.
- **v0.6 (2026-04-27)** — added ADR-030 (per-archetype btest interpreter dispatch; resolves OQ-030; amends ADR-010 prose), ADR-031 (token-bucket rate limiter shape for IB adapters), ADR-032 (instrument resolution policy `blive.Instrument` ↔ IB `Contract` / `ConID`), ADR-033 (`AccountUpdate` event shape and 30-s diff-suppressed cadence). All four PROPOSED at M2 entry; awaiting operator review before flip to ACCEPTED.
- **v0.7 (2026-04-27)** — operator-driven pivot to IG demo bridge (M2-IG) while IB Paper account is being reopened. Added cross-cutting ADRs: ADR-034 (multi-broker registry pattern; extends ADR-004 with explicit registry, package layout, and import-linter contract for N>2 brokers), ADR-035 (secrets handling discipline: `~/.blive/secrets/{broker}.env`, env-var override, log redaction list, never-in-git rule). Both PROPOSED; M2-IG.1 batch 1. IG-specific ADRs (036..039) + KB-16/17 + DD-8 land in batch 2.
- **v0.8 (2026-04-27)** — M2-IG.1 batch 2 IG-specific substrate. ADR-036 (IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer; rejects `trading_ig` for asyncio mismatch with ADR-005), ADR-037 (`Instrument.tradability` field — backward-compatible spot/cfd/spread_bet discriminator; scopes ADR-027 integer-share rounding to spot only), ADR-038 (IG rate-limit defaults — parameterises ADR-031 with named-bucket config; IG defaults 30/60/40 per minute + 40 concurrent Lightstreamer subscriptions; broker-agnostic shape), ADR-039 (Phase 1 strategy under IG bridge — CAC 40 CFD as tradable instrument; ADR-021 PAUSED not SUPERSEDED; new parity envelope: directional alignment + characterised < 100 bps over 5-day run, *not* G2-IB ±1 bps). All four PROPOSED; awaiting operator review alongside ADR-034..035 to flip ACCEPTED en bloc.
- **v0.9 (2026-04-27)** — operator approval moment. Eight ADRs flipped PROPOSED → ACCEPTED en bloc: ADR-030 (per-archetype dispatch — broker-agnostic; resolves OQ-030), ADR-033 (AccountUpdate cadence — broker-agnostic), ADR-034 (multi-broker registry; load-bearing), ADR-035 (secrets handling discipline), ADR-036 (IG driver), ADR-037 (Instrument.tradability), ADR-038 (IG rate-limit defaults), ADR-039 (Phase 1 under IG bridge). **Two ADRs stay PROPOSED**: ADR-031 (IB-specific rate-limit defaults; revisit when M2-IB resumes) and ADR-032 (IB-specific instrument resolution; revisit when M2-IB resumes). Updated OQ-030 status RESOLVED-BY-ADR-030 in OPEN_QUESTIONS.md.
- **v0.10 (2026-04-28)** — M2-IB.2 milestone flip. ADR-031 (token-bucket rate limiter shape for IB adapters) PROPOSED → ACCEPTED: the algorithm shipped at M2-IG.2 inside `blive.adapters.shared.rate_limiter` and the IB-specific defaults table now lives at `blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS` (`global` 20/s, `historical` 50/600s per [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults)). `IBClient.connect()` exercises the limiter via `acquire("global")` per the M2-IB.2 unit-test suite. Body of ADR-031 unchanged (append-only); status field flipped + a parenthetical PROPOSED→ACCEPTED date trail added in the ADR header. **ADR-032 stays PROPOSED** until M2-IB.3 IBInstrumentResolver exercises `qualifyContractsAsync` against IB Paper.
- **v0.11 (2026-04-28)** — M2-IB.3 prereq closure. Added ADR-040 (Phase 1 deployment target: Windows host with native IB Gateway; no Docker / IBC for paper-mode dev; Linux VM revisited at M8 production cutover). Drafted PROPOSED, accepted same-session per the established same-day-ACCEPTED pattern; status flipped to ACCEPTED. Closes the "Decide deployment target" item from [TASK_REGISTRY M2-IB §"Operator-side prerequisites"](../../TASK_REGISTRY.md). Daily 23:45 ET TWS-restart handled by operator-managed manual relogin during the M2-IB.5 ≥5-trading-day run; blive's reconciliation handles the disconnect/reconnect transient unchanged.
