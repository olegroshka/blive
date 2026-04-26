---
id: TASK_REGISTRY
title: Task Registry — Phase 1 Plan
status: DRAFT
owner: Oleg primary, Claude assist
last_reviewed: 2026-04-26
version: 0.1.2
sources:
  - REQUIREMENTS.md §14
  - KB-5 §7
  - ADR-013
  - PHASE_1_READINESS.md
depends_on:
  - REQUIREMENTS
  - KB-5
  - PHASE_1_READINESS
  - KB-11 (proposed OQ-024..OQ-027 resolutions)
referenced_by:
  - CONTEXT_INVENTORY §1 layer 4
---

# TASK_REGISTRY — Phase 1 Plan

## Purpose

Layer-4 Plan artefact (per [CONTEXT_INVENTORY §1](./CONTEXT_INVENTORY.md#1-representation-hierarchy)). Specifies milestones, deliverables, gates, exit criteria, dependencies, and substrate-artefact requirements for **Phase 1 (M0 → M3)** — the path to first IB Paper strategy run.

## Scope

**In scope (this version):** detailed plan for M0, M1, M2, M3.

**Sketched only:** M4+ (Phase 2 entry); detail awaits M3 close.

**Out of scope:** execution itself.

## Phase 1 Strategy

[ADR-013](./docs/decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) selects `tkan_v4_momentum_timing` 1× variant.

Phase 1 specifics (confirmed 2026-04-26):

| Specifier | Value | Source |
|-----------|-------|--------|
| Tradable instrument | `CAC.PA` (Lyxor CAC 40 UCITS ETF, XPAR) | [ADR-021](./docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) |
| NAV slice | 5–10% of total account, hard cap 10% | [ADR-020](./docs/decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10) |
| TKAN freshness window | 30d hard (RC-12 block); 21d warning | [ADR-022](./docs/decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning) |
| TKAN artefact path | `~/.blive/artefacts/{strategy_id}/{model_name}/pred_cache.pkl` | [ADR-023](./docs/decisions/DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership) |
| TKAN refresh | manual via `scripts/refresh_artefact.py` (M2 deliverable) | ADR-023 |

---

## Milestone Plan

### M0 — Skeleton & Domain Types

**Goal:** repository structure exists; domain types defined; ports declared; minimal paper broker round-trips an order through the full FSM.

**Deliverables:**

1. **Repo scaffolding** — `pyproject.toml` (Python 3.11, `uv` package manager), `src/blive/`, `tests/`, build shortcuts.
2. **Pinned dependencies** — `btest >=X.Y,<X.Y+1` (TBD on first build), `ib_async >=2.1,<2.2` per [ADR-002](./docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver).
3. **DD-1 domain objects** (`docs/dd/domain_objects.md`, **MISSING → STABLE**) — `Order`, `Fill`, `Position`, `Bar`, `Trade`, `AccountSnapshot`, `Instrument`, `OrderEvent`. Pure dataclasses; frozen where applicable; no business logic.
4. **INV-13 order FSM transitions** (`docs/inv/order_state_transitions.md`, **MISSING → STABLE**) — `INITIALIZED → SUBMIT_PENDING → SUBMITTED → ACCEPTED → (PARTIALLY_FILLED) → FILLED | CANCELED | REJECTED | EXPIRED` with explicit allowed sources, triggers, side-effects per transition.
5. **INV-5 domain events** (`docs/inv/domain_events.md`, **MISSING → DRAFT**) — every event type, payload, emission rule.
6. **INV-6 ports/adapters** (`docs/inv/ports_adapters.md`, **MISSING → DRAFT**) — `BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `EventBusPort`, `AlertPort` as Python `Protocol` classes with concrete signatures from [REQUIREMENTS §7.2](./REQUIREMENTS.md).
7. **PaperBroker adapter** (`src/blive/adapters/paper/`) — in-process matcher honouring the order FSM; configurable simulated latency / fills.
8. **InMemoryPersistence adapter** — append-only event log in memory (development use; SQLite arrives at M4).
9. **Test scaffolding** — pytest config; mock implementations of each port; golden FSM-transition tests.
10. **Import-linter rule** — `blive.domain` cannot import `blive.adapters.*`; enforced via CI or pre-commit hook per [ADR-004](./docs/decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement).

**Substrate transitions:** DD-1 STABLE; INV-13 STABLE; INV-5 DRAFT; INV-6 DRAFT.

**Exit criteria (G1 gate):**

- `uv run pytest` green.
- Unit test creates an `Order`, traverses the full FSM, asserts every emitted event has the expected payload.
- PaperBroker round-trip test: submit a market order; receive a `Fill`; observe `Position` updates correctly.
- Import-linter passes against a deliberately violating commit (negative test).

**Estimated effort:** ~1 working session.

**Dependencies:** none (entry milestone).

---

### M1 — btest Strategy Import & Paper Round-Trip

**Goal:** `tkan_v4_momentum_timing` 1× runs in blive's paper mode end-to-end and matches btest's equity curve to within rounding tolerance.

**Deliverables:**

1. **btest dependency** installed and pinned; CI smoke-imports check ensures `from quantdsl_backtest.dsl.strategy import Strategy` and friends work.
2. **Strategy ingest module** (`blive.strategy.loader`) — given a Python module producing a btest `Strategy`, register it with the blive runtime.
3. **FactorEngine / SignalEngine / PortfolioEngine reuse** — imported from btest, wired into the blive runtime per [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import).
4. **Sizer (M1 minimal)** (`blive.sizing`) — convert `target_weights: pd.Series[instrument → float]` into concrete `Order` objects per [REQUIREMENTS §5.13](./REQUIREMENTS.md). Single-instrument case suffices for Phase 1; multi-instrument path is Phase 2 work.
5. **RiskEngine (M1 minimal subset)** (`blive.risk`) — implement RC-08 stale data, RC-09 market hours, RC-13 kill-switch from [INV-4](./docs/inv/risk_checks.md). Other RCs land at M4.
6. **Paper-mode end-to-end pipeline:**
   - Load `tkan_v4_momentum_timing` strategy spec.
   - Replay deterministic historical CAC.PA bars (offline, fixture-backed).
   - At each rebalance: factor → signal → portfolio → sizer → risk → paper broker.
   - Record fills, positions, equity curve.
7. **DD-3 config schemas** (`docs/dd/config_schemas.md`, **MISSING → DRAFT**) — strategy YAML schema with field-level validation.

**Substrate transitions:** DD-3 DRAFT; INV-5 DRAFT → STABLE; INV-6 DRAFT → STABLE.

**Exit criteria (G2 gate):**

- `tkan_v4_momentum_timing` 1× runs in blive paper mode for ≥ 252 days of historical CAC.PA data.
- End-of-period equity curve matches btest's reference run **within ±1 bps** (divergence should come only from share-rounding in the sizer; the engines are identical by import).
- Round-trip test: signal → fill → position update → equity reflects the trade including commission per [KB-6 §1](./docs/kb/cost_margin_dictionary.md#1-commission).
- A negative test: deliberately stale data triggers RC-08 block; engine refuses to size; alert event fires.

**Estimated effort:** ~1–2 sessions.

**Dependencies:** M0 complete; G1 gate passed.

---

### M2 — IB Adapter (Read Side) & Operational Foundation

**Goal:** blive connects to IB Paper, reads positions / account values / market data; the operational stack (Docker, IBC, rate limiter) is in place.

**Deliverables:**

1. **IB Paper account verified** (operator action) — credentials available; `clientId` chosen; documented in a private `secrets/` location not under version control.
2. **IB Gateway via Docker** (e.g. `gnzsnz/ib-gateway-docker`) operational — auto-restart on failure; pinned offline TWS installer per [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events); IBC configured.
3. **EODHD subscription verified** — CAC index daily history reachable via `eodhd://` test fetch.
4. **`IBBroker` adapter — read methods** (`adapters/ib/broker.py`) — `connect()`, `disconnect()`, `positions()`, `account_snapshot()`, `open_orders()`, `events()`. All outbound calls pass through a token-bucket rate limiter (default 20 msg/sec global per [KB-3 §1](./docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle)).
5. **`IBMarketData` adapter — read methods** (`adapters/ib/market_data.py`) — `subscribe_bars()`, `historical_bars()`. Historical pacing per [KB-3 §2](./docs/kb/ib_pacing_spec.md#2-historical-data-pacing).
6. **`EODHDDataSource`** registered in btest's data source registry (`adapters/eodhd/`) — `eodhd://...` URL scheme resolves to delayed/historical fetch.
7. **`scripts/refresh_artefact.py`** (per [OQ-027](./docs/decisions/OPEN_QUESTIONS.md#oq-027--tkan-artefact-prod-location-and-retraining-ownership)) — copy + checksum + record TKAN artefact freshness.
8. **PaperBroker → real-IB-Paper read-mirror harness** — blive runs with PaperBroker for execution but reads positions via IBBroker; the two views match.
9. **Reconnect logic** — disconnect / reconnect cycles tested by stopping/starting the IB Gateway container.

**Substrate transitions:** KB-2, KB-3 STABLE confirmed; INV-14 (IB error codes) MISSING → DRAFT; KB-8 (operational events) MISSING → DRAFT.

**Exit criteria (G3 gate):**

- blive connects to IB Paper Gateway within 5 s of process start.
- `positions()` returns the same set TWS UI shows (manual eyeball check).
- Subscribe to CAC.PA bars; receive ≥ 100 ticks within RTH.
- Throttle test: simulate burst of 60 calls/sec; outbound rate stays ≤ 20 msg/sec.
- Disconnect IB Gateway mid-session; blive detects within 30 s; reconnects when Gateway returns.
- `refresh_artefact.py` round-trip: copy a fresh `pred_cache.pkl` from btest output; observe checksum recorded; observe RC-12 freshness check passes.

**Estimated effort:** ~2–3 sessions, dominated by Docker / IBC setup time and IB Paper account commissioning. **Operator-side prerequisites must be verified before M2 starts.**

**Dependencies:** M1 complete; G2 gate passed; OQ-024..OQ-027 confirmed.

---

### M3 — IB Adapter (Write Side) & First Live (Paper) Strategy

**Goal:** `tkan_v4_momentum_timing` 1× submits real orders to IB Paper through blive; FSM transitions are driven by IB events; first live (paper) strategy run on a regulated venue.

**Deliverables:**

1. **`IBBroker.submit() / cancel() / replace()`** — full FSM driven by IB callbacks (`orderStatus`, `execDetails`, `commissionReport`).
2. **Order state machine observed in real time** — every transition emits a typed domain event; events persisted to in-memory log.
3. **Reconciliation on startup** (basic version per [REQUIREMENTS §5.7](./REQUIREMENTS.md)) — `reqAllOpenOrders` + `reqPositions` on connect; diff against persisted state; venue authoritative; synthesise local events.
4. **Smoke-test harness** (`tests_smoke/ib_paper/`) — manual integration tests against IB Paper. Marked `manual`; not in CI.
5. **First strategy run** — `tkan_v4_momentum_timing` 1× loaded; runs against IB Paper for ≥ 5 trading days; NAV slice per [OQ-024](./docs/decisions/OPEN_QUESTIONS.md#oq-024--nav-slice-for-the-phase-1-strategy); CAC.PA per [OQ-025](./docs/decisions/OPEN_QUESTIONS.md#oq-025--which-cac-etf-proxy-for-the-phase-1-strategy).
6. **Manual chaos drills** — simulated IB disconnect mid-fill; simulated reject; manual cancel from TWS UI; `kill -9` of blive process mid-trade. Each drill must produce a correct end-state after recovery.

**Substrate transitions:** INV-2 (order types) MISSING → DRAFT; INV-3 (TIFs) MISSING → DRAFT; KB-7 (failure modes) MISSING → DRAFT (chaos catalogue from observed M3 drills); INV-14 DRAFT → STABLE.

**Exit criteria (G4 gate — the "M3 done" test):**

1. `tkan_v4_momentum_timing` 1× runs end-to-end on IB Paper for **≥ 5 trading days without manual intervention**.
2. **≥ 5 round-trip orders** observed end-to-end; every FSM transition logged with `client_order_id`, `venue_order_id`, timestamp.
3. **Simulated reject** correctly handled — FSM → `REJECTED`; alert fires; engine continues running.
4. **Simulated cancel from TWS UI mid-order** correctly observed — FSM → `CANCELED`; alert fires; position unchanged.
5. **`kill -9` mid-trade**, restart reconciles correctly — blive's positions match IB-side positions; no orphan orders; engine enters `paused` state per [ADR-009](./docs/decisions/DECISIONS.md#adr-009--crash-only-design); operator-resume succeeds.
6. **Throttle headroom** — peak observed message rate ≤ 50% of IB's 50 msg/sec hard cap.

**Estimated effort:** ~3–4 sessions, depending on IB Paper behaviour and number of chaos-drill iterations needed.

**Dependencies:** M2 complete; G3 gate passed.

---

## Sketched M4+ (post-Phase-1)

The detailed plan stops at M3. M4+ are sketched here only to set expectations and to identify the artefact ladder Phase 2 will depend on:

- **M4** — RiskEngine full (RC-01..RC-12); SQLite persistence (`PersistencePort` switches from in-memory to SQLite-backed per [ADR-006](./docs/decisions/DECISIONS.md#adr-006--sqlite-for-persistence-in-v1)); structured logging.
- **M5** — Reconciliation continuous loop; daily TWS-restart handling first-class; `RUNBOOK.md` drafted; Phase 2 readiness audit.
- **M6** — Web UI (3 pages) per [ADR-011](./docs/decisions/DECISIONS.md#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred); REST endpoints; SSE log stream.
- **M7** — Parity diagnostic; observability (Prometheus + Grafana); KB-15 parity_methodology drafted.
- **M8** — Hardening: TLS, audit-log hash chain, backup automation, ops runbook fully realised. Real-money cutover gate.

Phase 2 begins at the entry to M4 with strategy `triple_lev_sma_filter_dsl` (TQQQ/TMF/IEF) added per [KB-5 §7](./docs/kb/strategy_taxonomy.md#7-nav-slice--priorities). Phase 2 detailed plan is **not** drafted yet; it awaits M3 close so that calibrated risk thresholds and observed parity envelope can inform the plan.

---

## Quality Gates

A quality gate is a checkpoint at the boundary between milestones. The gate must pass before the next milestone begins.

| Gate | What it checks | Owner |
|------|----------------|-------|
| **G0** (M0 entry) | ADR-001..023 stable (✓ ADR-020..023 added 2026-04-26) | **PASSED 2026-04-26** |
| **G1** (M0 → M1) | DD-1, INV-13 STABLE; PaperBroker round-trip green; import-linter passing | **PASSED 2026-04-26** (see [RETRO-M0](./docs/retros/M0_retrospective.md)) |
| **G2** (M1 → M2) | btest equity-match within ±1 bps; M1 deliverables complete; operator-side prereqs verified | Oleg |
| **G3** (M2 → M3) | IB Paper read-mirror passes; throttle + reconnect tests green | Oleg |
| **G4** (M3 → M4 / Phase 2 entry) | All six M3 exit criteria met; PHASE_2_READINESS audit drafted | Oleg |

---

## Risk register (Phase 1)

Risks specific to Phase 1 (broader risks live in [REQUIREMENTS](./REQUIREMENTS.md) and [INV-4](./docs/inv/risk_checks.md)):

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| IB Paper account commissioning takes longer than expected | Medium | M2 slip | Verify account at G2 gate, before M2 starts |
| EODHD CAC index coverage insufficient | Low | M2 redo | Verify before M2 (G2 gate); fall back to IB-only data for CAC.PA |
| Docker / IBC setup fragile on Windows host | Medium | M2 friction | Plan Linux-host fallback; document discoveries in KB-8 |
| btest version drift breaks blive imports during Phase 1 | Medium | rebuild | Pin btest minor; CI smoke-imports check (M0 deliverable); coordination policy in [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) |
| TKAN artefact retrained mid-Phase-1 produces non-stationary signal | Low | strategy underperforms | Acceptable on paper; revisit at G4 |
| Parity envelope between CAC.PA price-return and CACT total-return wider than expected | High | documentation only | Document; do not block M3; feed into M7 parity diagnostic design |

---

## Open dependencies on operator action

Items still requiring Oleg's input or action (G0 passed 2026-04-26; remaining items required at G2 → M2):

1. ~~Confirm or override OQ-024..OQ-027 defaults.~~ ✓ Done 2026-04-26 (ADR-020..023).
2. **Verify IB Paper account access** (credentials, port, `clientId`).
3. **Verify EODHD All-in-One subscription** covers CAC index daily history.
4. **Decide deployment target** (Linux VM vs Windows host) — affects M2 Docker setup approach.

---

## Cross-References

- [REQUIREMENTS.md §14](./REQUIREMENTS.md) — milestones M0..M8.
- [PHASE_1_READINESS.md](./docs/PHASE_1_READINESS.md) — readiness audit gating this plan.
- [ADR-013](./docs/decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) — v1 scope.
- [KB-5 §7](./docs/kb/strategy_taxonomy.md#7-nav-slice--priorities) — phased priority.
- [KB-11](./docs/decisions/OPEN_QUESTIONS.md) — OQ-023..OQ-027.
- [INV-4](./docs/inv/risk_checks.md) — risk checks RC-01..RC-13.
- [CONTEXT_INVENTORY.md §1](./CONTEXT_INVENTORY.md#1-representation-hierarchy) — this file is layer 4.
- [CONTEXT_PROTOCOL.md §3](./CONTEXT_PROTOCOL.md) — edit discipline that governs updates here.

---

## Changelog

- **v0.1 (2026-04-26)** — initial draft. M0..M3 detailed; M4+ sketched. Five quality gates defined. Risk register seeded. Conditional on OQ-024..OQ-027 default confirmation.
- **v0.1.1 (2026-04-26)** — operator confirmed OQ-024..OQ-027. Phase 1 specifics table promoted from "proposed" to confirmed values, citing ADR-020..023 instead of OQs. **G0 gate passed.** Remaining operator dependencies are now operational prereqs for G2 (IB Paper account, EODHD coverage, deployment target).
- **v0.1.2 (2026-04-26)** — **M0 closed; G1 gate PASSED**. All ten M0 deliverables landed (scaffolding, DD-1 STABLE, INV-13 STABLE, INV-6 DRAFT, INV-5 DRAFT, domain layer, paper / in-memory / clock adapters, tests, import-linter contract + negative test, CONTEXT_INVENTORY sync). 113 tests green; mypy strict clean; both contracts KEPT. See [RETRO-M0](./docs/retros/M0_retrospective.md). Next milestone is M1 — see [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.2.
