---
id: KB-10
title: Architectural Decision Records (ADRs)
status: DRAFT
owner: Claude record, Oleg approve
last_reviewed: 2026-04-26
version: 0.1
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

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. ADR-001..012 backfill from REQUIREMENTS rationale; ADR-013..019 from Oleg's 2026-04-26 OQ resolution session.
- **v0.2 (2026-04-26)** — added ADR-020..023 covering Phase 1 operational specifics: NAV slice (5–10% cap 10%), CAC ETF proxy (`CAC.PA`), TKAN freshness window (30d hard / 21d warn), TKAN artefact path and refresh ownership.
- **v0.3 (2026-04-26)** — added ADR-024 (RETRO artefact type) and ADR-025 (protocol amendment for milestone-close + phase-boundary handoff rules).
- **v0.4 (2026-04-26)** — added ADR-026 (agentic-execution layer; human-governance / agent-execution division of labour; five-layer adoption stack).
