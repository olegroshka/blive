---
id: TASK_REGISTRY
title: Task Registry — Phase 1 Plan
status: DRAFT
owner: Oleg primary, Claude assist
last_reviewed: 2026-04-28
version: 0.3
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

**2026-04-28 amendment**: M2 history:

- **M2-IG path** (operator-driven IG demo bridge while IB Paper was unavailable) — **CLOSED at architectural surface 2026-04-28**. Sub-milestones .1 substrate / .2 cross-cutting infra / .3 read side / .4 minimum-viable submit shipped (7 tags placed; 359 tests; ADR-030/033/034..039 ACCEPTED). Sub-milestone .5 strategy run + production Lightstreamer wrapper DEFERRED (operator pivoted to M2-IB resumption when the IB Paper account became available). See [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md). The IG-specific code (5 modules + Lightstreamer abstraction + KB-16/17 + DD-8) is preserved in repo for future bridge revival; no scheduled revival.
- **M2-IB path** (canonical Phase 1) — **ACTIVE 2026-04-28**. IB Paper account commissioned 2026-04-28; enabled 2026-04-29. Resumes from the [`M2-substrate-IB.checkpoint`](./docs/decisions/DECISIONS.md) commit. Architecturally scaffolded by the M2-IG cross-cutting work (broker registry, shared rate limiter, shared credentials, `Instrument.tradability` field) — IB read+write modules mirror IG's file structure 1:1 per RETRO-M2-IG §"Recommendations".

Phase 1 specifics (canonical M2-IB path; M2-IG bridge variant **ARCHIVED**):

| Specifier | M2-IB path (ACTIVE) | M2-IG bridge variant (ARCHIVED) | Source |
|-----------|---------------------|----------------------------------|--------|
| Tradable instrument | `CAC.PA` (Lyxor CAC 40 UCITS ETF, XPAR) | CAC 40 cash CFD on IG (epic TBD if revived) | [ADR-021](./docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) / [ADR-039](./docs/decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) (bridge-paused; ACCEPTED but not the canonical Phase 1 strategy) |
| Tradability | `spot` (ETF shares; ADR-027 integer-share rounding) | `cfd` (fractional contracts) | [ADR-037](./docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet) |
| NAV slice | 5–10% of total account, hard cap 10% | same | [ADR-020](./docs/decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10) |
| TKAN freshness window | 30d hard (RC-12 block); 21d warning | same | [ADR-022](./docs/decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning) |
| TKAN artefact path | `~/.blive/artefacts/{strategy_id}/{model_name}/pred_cache.pkl` | same | [ADR-023](./docs/decisions/DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership) |
| TKAN refresh | manual via `scripts/refresh_artefact.py` (M2-IB.4 deliverable) | same script (broker-agnostic) | ADR-023 |
| Parity envelope | ±1 bps target (G2-IB / G3-IB) | (CFD-specific envelope, not exercised) | ADR-021 / ADR-039 |
| Credentials | `~/.blive/secrets/ib.env` (host/port/clientId/account_id only — IB Gateway + IBC handle username/password) | (would have been `~/.blive/secrets/ig.env` if revived) | [ADR-035](./docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) |

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

### M2-IB — IB Adapter (Read + Write Side) & First Live (Paper) Strategy Run — **ACTIVE 2026-04-28**

**Status:** ACTIVE — IB Paper account commissioned 2026-04-28; enabled 2026-04-29. Substrate at [`M2-substrate-IB.checkpoint`](./docs/decisions/DECISIONS.md). Cross-cutting infra (broker registry, shared rate limiter, shared credentials, `Instrument.tradability` field) shipped via the M2-IG bridge work and reuses unchanged. Architecturally scaffolded — implementation now mirrors the M2-IG file structure 1:1 per [RETRO-M2-IG §"Recommendations"](./docs/retros/M2-IG_retrospective.md#recommendations-for-next_promptmd-v04-m2-ib-resumption).

**Goal:** blive runs `tkan_v4_momentum_timing` 1× against `CAC.PA` ETF on IB Paper for ≥ 5 trading days, with end-of-period equity matching btest's reference within ±1 bps (G2-IB) and the operational stack (Docker, IBC, rate limiter, credentials, broker registry) operational.

**Sub-milestones:**

- **M2-IB.1 — Substrate verification.** Confirm the substrate at `M2-substrate-IB.checkpoint` is internally consistent post-M2-IG (most rows are; KB-8 grew §8 IG events; INV-6 grew IG rows + cross-cutting `blive.adapters.shared.*` catalogue). No code in this sub-milestone.
- **M2-IB.2 — IBClient + IBCredentials.** New `blive.adapters.ib.client` wrapping `ib_async.IB` (TCP socket + callback model — different transport from IGClient's REST). connect / disconnect / submit / cancel / event subscription. Rate-limited via `blive.adapters.shared.rate_limiter` with [KB-3 §9](./docs/kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults) IB defaults (20 msg/s global; 5/s per-strategy). New `blive.adapters.ib.credentials` (schema is simpler than IG — no API key, no password; just host/port/clientId/account_id per `secrets/ib.env.example` from ADR-035).
- **M2-IB.3 — IBInstrumentResolver + IBBroker read + IBMarketData.** Mirror M2-IG.3 file structure. IBInstrumentResolver: `Instrument` ↔ IB `Contract` via `qualifyContractsAsync` per [DD-7 §4](./docs/dd/instrument_dictionary.md). IBBroker read: positions / account_snapshot / open_orders / events. IBMarketData: subscribe_bars via `ib_async.reqMktData` / `reqHistoricalData` (no Lightstreamer abstraction — IB has its own stream model; the `MarketDataPort.subscribe_bars` shape stays identical from the consumer's perspective). Wire `create_ib_broker` + `create_ib_market_data` into `broker_registry`. **ADR-031 + ADR-032 flip PROPOSED → ACCEPTED** on first IB exercise. **DD-7 STABLE flip** on first successful Contract resolution. **KB-2 + KB-3 STABLE flip** when M2-IB.3 has exercised the §1-§9 surfaces against IB Paper.
- **M2-IB.4 — IBBroker write side + reconciliation.** submit / cancel / replace via `ib_async` order placement. FSM event emission driven by `ib_async`'s `orderStatusEvent` / `execDetailsEvent` / `commissionReportEvent` callbacks (event-driven, unlike IG's confirms-poll). Reconciliation on startup: `reqAllOpenOrders` + `reqPositions` per [REQUIREMENTS §5.7](./REQUIREMENTS.md#57-reconciliation). **INV-14** (IB error codes) MISSING → DRAFT as observed-rejects accumulate. Optionally consolidate with the original M3 plan; see "M2-IB.4 vs M3" note below.
- **M2-IB.5 — Strategy run + RETRO-M2-IB.** Pipeline (refactor `paper_pipeline.py` to be broker-agnostic via `broker_registry`, OR new `ib_pipeline.py` analogue of the deferred M2-IG.5 plan). Run `tkan_v4_momentum_timing` 1× against IB Paper for ≥ 5 trading days. G3-IB gate criteria validated. Write `RETRO-M2-IB.md` per [CONTEXT_PROTOCOL §8.3.1](./CONTEXT_PROTOCOL.md).

**M2-IB.4 vs M3 note**: the original M3 milestone (per TASK_REGISTRY v0.1.x) was "IB Adapter (Write Side) & First Live (Paper) Strategy". With the M2-IG bridge having shipped MARKET-submit at M2-IG.4 + the multi-broker registry pattern in place, the cleanest plan is to consolidate write side into M2-IB.4 and let M2-IB.5 be the strategy run. M3 in the v0.3 sketch becomes Phase 2 entry / second strategy slot rather than "IB write side". Re-evaluate at M2-IB.3 close.

**Goal (read-side, restated from earlier scope):** blive connects to IB Paper, reads positions / account values / market data; the operational stack (Docker, IBC, rate limiter) is in place.

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

### M2-IG — IG Demo Bridge — **ARCHIVED 2026-04-28** (architectural-surface close; G3-IG NOT_REACHED)

**Status:** **CLOSED at architectural surface 2026-04-28** per [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md). The G3-IG gate criteria were NOT REACHED — this was an operator-driven close after the IB Paper account became available, not a gate failure. The M2-IG sub-milestones .1 (substrate) / .2 (cross-cutting infra) / .3 (read side) / .4 (minimum-viable submit) shipped at architectural surface (7 tags placed: `M2-IG.1-batch1`, `M2-IG.1-batch2`, `M2-IG.2-complete`, `M2-IG.3-broker`, `M2-IG.3-readside-complete`, `M2-IG.4-market-submit`); **never exercised against IG demo**. M2-IG.5 (strategy run + 5-day demo) and the production Lightstreamer wrapper are explicitly **DEFERRED with no scheduled revival**.

The IG-specific code (modules under `blive/adapters/ig/`, KB-16, KB-17, DD-8, ADR-036/038/039) is preserved as durable reference. If the bridge is ever revived, the work is reusable. The cross-cutting work — broker registry, shared rate limiter, shared credentials, `Instrument.tradability` field — applies directly to M2-IB resumption (this was the bridge's primary architectural dividend, captured in RETRO-M2-IG §"What the IG bridge bought us").

**Original goal (not achieved):** blive runs `tkan_v4_momentum_timing` 1× against CAC 40 CFD on IG demo for ≥ 5 trading days.

**Why M2-IG was bigger than M2-IB scope-wise**: M2-IG covered read + write + strategy run as a single unit because the bridge's primary purpose was end-to-end validation of the abstraction. The M2-IB resumption splits that: read side (M2-IB.3) + write side (M2-IB.4) + strategy run (M2-IB.5).

**Sub-milestones:**

- **M2-IG.1 — Substrate phase.** Cross-cutting ADRs (ADR-034 multi-broker registry, ADR-035 secrets) shipped 2026-04-27 batch 1. IG-specific ADRs (ADR-036 IG driver, ADR-037 `Instrument.tradability`, ADR-038 IG rate-limit defaults, ADR-039 Phase 1 strategy under bridge) + KB-16 (IG capability matrix), KB-17 (IG pacing spec), DD-8 (IG instrument dictionary), plus DD-3/DD-1/INV-6/KB-8 amendments — batch 2.
- **M2-IG.2 — Cross-cutting infra.** `blive.adapters.shared.rate_limiter` (token bucket per [ADR-031](./docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters), per-broker config), `blive.adapters.shared.credentials` (env-var loader per ADR-035), `blive.runtime.broker_registry` (factory dispatch per ADR-034). `secrets/ig.env.example` committed; `.gitignore` rule for `secrets/*.env`. Updated import-linter contract for broker-registry isolation.
- **M2-IG.3 — IG read-side adapter.** `blive.adapters.ig.broker.IGBroker` (read methods); `blive.adapters.ig.market_data.IGMarketData` (Lightstreamer + REST historical); `blive.adapters.ig.instrument_resolver` (Instrument↔epic); `blive.adapters.ig.credentials` (IG schema). 3-step REST auth flow.
- **M2-IG.4 — IG write-side adapter.** `IGBroker.submit / cancel / replace` against `/positions/otc` + `/workingorders/otc`; FSM driven by IG's order-status callbacks (Lightstreamer trade subscription); reconciliation on startup.
- **M2-IG.5 — Strategy run + retro.** Lift `paper_pipeline.py` to IG (broker registry pluggable). Run `tkan_v4_momentum_timing` 1× against the CAC 40 CFD epic on IG demo for ≥ 5 trading days. Verify directional alignment + envelope per ADR-039. Write [`docs/retros/M2-IG_retrospective.md`](./docs/retros/) per [CONTEXT_PROTOCOL §8.3.1](./CONTEXT_PROTOCOL.md). G3-IG gate report.

**Substrate transitions at M2-IG close:**

- ADR-030..033 status reviewed: broker-agnostic ones (ADR-030, ADR-033) flip PROPOSED → ACCEPTED; IB-specific ones (ADR-031, ADR-032) stay PROPOSED until M2-IB resumes.
- ADR-034 (multi-broker registry), ADR-035 (secrets), ADR-036..039 (IG-specific) flip PROPOSED → ACCEPTED.
- DD-7 stays IB-specific DRAFT (parked); DD-8 (IG instrument dictionary) DRAFT → STABLE on first successful epic resolution against IG demo.
- KB-16, KB-17 DRAFT; STABLE confirmed at M2-IG close via the IG read-side exercise.
- INV-14 (IB error codes) stays MISSING; equivalent IG error-code inventory authored as the M2-IG.3 work observes IG rejects.
- INV-5 widens with `AccountUpdate` (M2-IG.3) and `ArtefactFreshnessWarning` (M2-IG.3) — both already catalogued in [INV-5 §1](./docs/inv/domain_events.md), now implemented.

**Exit criteria (G3-IG gate):**

- blive connects to IG demo within 5 s of process start.
- `positions()` returns the same set IG web UI shows (manual eyeball check).
- Subscribe to CAC 40 CFD prices via Lightstreamer; receive ≥ 100 ticks within market hours.
- Throttle test: simulate burst of 100 calls/min; outbound rate stays ≤ 60 calls/min (per ADR-038).
- IG session-token expiry test (6 h on demo): observe automatic re-authentication; engine continues running.
- `refresh_artefact.py` round-trip works against the IG-bridge strategy run (broker-agnostic — same script as M2-IB).
- `tkan_v4_momentum_timing` 1× runs end-to-end on IG demo for **≥ 5 trading days without manual intervention**.
- ≥ 5 round-trip orders observed end-to-end against IG demo; FSM transitions logged.
- Strategy equity curve directionally aligned with btest replay; envelope per ADR-039 honoured.

**Operator-side prerequisites for M2-IG:**

- IG demo account commissioned ✓ (operator confirmed 2026-04-27 with API key, username, password, account id; paper-only test account; rotation discipline per ADR-035 understood).
- Deployment target — Linux VM vs Windows host. **Still OPEN**; less critical than for M2-IB since IG has no daily-restart equivalent and runs entirely over HTTPS (no TWS / IBC dependency). May be deferred to M2-IG.5 deployment.

**Estimated effort:** ~5–6 sessions across M2-IG.1 to M2-IG.5.

**Dependencies:** M1 complete; G2 gate PARTIAL accepted (synthetic-fixture parity green at M1 close).

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
| **G2** (M1 → M2) | btest equity-match within ±1 bps; M1 deliverables complete; operator-side prereqs verified | **PARTIAL 2026-04-27** (see [RETRO-M1](./docs/retros/M1_retrospective.md)) — pipeline machinery + 175 tests green; real-data ±1 bps run deferred to operator EODHD CAC.PA + TKAN artefact run |
| **G3-IB** (M2-IB → M2-IB.5 close) | blive connects to IB Paper within 5s; positions match TWS UI; CAC.PA bars receive ≥ 100 ticks within RTH; throttle test (60 calls/sec → ≤ 20 msg/sec); reconnect within 30s after Gateway restart; `refresh_artefact.py` round-trip works | Oleg — **ACTIVE 2026-04-28** |
| **G3-IG** (M2-IG → M2-IG.5 close) | IG demo read+write working; Lightstreamer + REST throttle green; session-token auto-refresh tested; `tkan_v4_momentum_timing` 1× runs ≥ 5 trading days on IG demo with directional alignment | Oleg — **NOT_REACHED 2026-04-28** (operator-driven bridge close before strategy run; not a gate failure — see [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md)) |
| **G4** (M3 → M4 / Phase 2 entry) | All M2-IB.5 strategy-run criteria met; PHASE_2_READINESS audit drafted | Oleg — re-scoped at M2-IB.5 close (M3 may consolidate with M2-IB.4 per the M2-IB.4-vs-M3 note above) |

---

## Risk register (Phase 1)

Risks specific to Phase 1 (broader risks live in [REQUIREMENTS](./REQUIREMENTS.md) and [INV-4](./docs/inv/risk_checks.md)):

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ~~IB Paper account reopen takes longer than expected~~ ✓ Resolved 2026-04-28 (account commissioned; enabled 2026-04-29) | — | — | — |
| ~~IG demo session token expires unexpectedly mid-run~~ ✓ Archived with M2-IG bridge close | — | — | — |
| ~~CAC 40 CFD financing-cost variability blows past parity envelope~~ ✓ Archived with M2-IG bridge close | — | — | — |
| ~~`lightstreamer-client-lib` callback-driven API maturity~~ ✓ Archived; abstraction layer captured the contract; production wrapper deferred | — | — | — |
| ~~IG demo CAC 40 CFD epic differs from `IX.D.CAC40.CASH.IP` guess~~ ✓ Archived with M2-IG bridge close | — | — | — |
| Docker / IBC setup fragile on Windows host | Medium | M2-IB.2 friction | Plan Linux-host fallback; document discoveries in [KB-8](./docs/kb/operational_events.md) §1-§3 (IB-side) |
| btest version drift breaks blive imports during M2-IB | Medium | rebuild | Pin btest commit; CI smoke-imports check (M0 deliverable) catches early; coordination policy in [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) |
| TKAN artefact retrained mid-Phase-1 produces non-stationary signal | Low | strategy underperforms | Acceptable on paper; revisit at G3-IB / G4 |
| Parity envelope between CAC.PA price-return and CACT total-return wider than expected | High | documentation only | Document; do not block M2-IB.5; feed into M7 parity diagnostic design |
| `ib_async`'s callback model bridges to asyncio cleanly | Low | M2-IB.2 friction | `ib_async` is asyncio-native (per [ADR-002](./docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver)); thinner adapter than the IG Lightstreamer wrapper would have needed |
| IB daily TWS restart at 23:45 ET disrupts the ≥ 5-day strategy run | Medium | M2-IB.5 friction | First-class operational event per [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) + [KB-8 §1](./docs/kb/operational_events.md); engine pauses + reconciles + resumes per [REQUIREMENTS §5.7](./REQUIREMENTS.md#57-reconciliation) |
| EODHD CAC index coverage insufficient | Low (verified) | M2 redo | **Verified 2026-04-27** (M1-close lane). EODHD probe ran with operator-supplied key: `CAC.PA` daily EOD (2024-12 sample) returns full OHLC + adjusted_close + volume — primary tradable per [ADR-021](./docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) covered. `CAC.PA` real-time quote returns delayed-tier data (sufficient for Phase-1 EOD strategy). Open small follow-up for M2: the CAC 40 *index* ticker is not `CAC.INDX` (404 from EODHD); when wiring `EODHDDataSource`, try `PX1.INDX` / `^FCHI`. Index feed is nice-to-have for parity-residual decomposition, not a G2 blocker. |
| Docker / IBC setup fragile on Windows host | Medium | M2 friction | Plan Linux-host fallback; document discoveries in KB-8 |
| btest version drift breaks blive imports during Phase 1 | Medium | rebuild | Pin btest minor; CI smoke-imports check (M0 deliverable); coordination policy in [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) |
| TKAN artefact retrained mid-Phase-1 produces non-stationary signal | Low | strategy underperforms | Acceptable on paper; revisit at G4 |
| Parity envelope between CAC.PA price-return and CACT total-return wider than expected | High | documentation only | Document; do not block M3; feed into M7 parity diagnostic design |

---

## Open dependencies on operator action

Items still requiring Oleg's input or action:

1. ~~Confirm or override OQ-024..OQ-027 defaults.~~ ✓ Done 2026-04-26 (ADR-020..023).
2. ~~**Verify IG demo account credentials**.~~ ✓ Done 2026-04-27 (M2-IG.1). Now archived with the M2-IG bridge close.
3. ~~**Verify IB Paper account access**.~~ ✓ Done 2026-04-28: account commissioned, enabled 2026-04-29.
4. **Place IB connection params at `~/.blive/secrets/ib.env`** per [ADR-035](./docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets). File scaffolded 2026-04-28 from [`secrets/ib.env.example`](./secrets/ib.env.example) at `~/.blive/secrets/ib.env`; `IB_HOST=127.0.0.1` / `IB_PORT=4002` / `IB_CLIENT_ID=1` defaults already filled. **PARTIAL** — operator still needs to edit `IB_PAPER_ACCOUNT_ID` from the placeholder to the actual paper account id (e.g. `DUxxxxxxx`). Required before M2-IB.3 first wire-level handshake (M2-IB.2 architectural-surface ship is broker-agnostic / mock-tested). Note: IB Gateway / IBC handle username+password; blive only needs `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`, `IB_PAPER_ACCOUNT_ID`.
5. ~~**Decide deployment target** (Linux VM vs Windows host).~~ ✓ Resolved 2026-04-28 by [ADR-040](./docs/decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway): Phase 1 = Windows host with native IB Gateway (no Docker / IBC); Linux VM + Docker + IBC deferred to M8 production cutover. Daily 23:45 ET TWS-restart handled by operator-managed manual relogin during the M2-IB.5 ≥5-day run; blive's reconciliation handles the disconnect/reconnect transient unchanged.
6. **First IB Gateway handshake** from blive's host (TCP `127.0.0.1:4002` paper port reachable; `clientId=1` chosen). Operator runs `uv run python scripts/probe_ib_handshake.py` (manual smoke test scaffolded 2026-04-28) after editing `ib.env` and starting IB Gateway. Required before M2-IB.3 IBInstrumentResolver / IBBroker.read code starts substrate-flipping ADR-032 / DD-7 / KB-2 / KB-3. **OPEN.**

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
- **v0.1.3 (2026-04-27)** — **M1 closed; G2 gate PARTIAL.** All seven M1 deliverables landed (smoke-import, strategy loader, btest engine wiring via `SingleAssetRunner` per OQ-030, Sizer with ADR-027 rounding, RiskEngine M1-subset RC-08/09/12/13, paper-mode pipeline, DD-3 DRAFT). Plus PaperMarketData / LogAlert / PaperBroker.replace / RiskBreach domain-event relocation. ADR-027..029 ACCEPTED; OQ-030 raised; INV-5/INV-6 promoted to STABLE. 175 tests green; mypy strict clean; both contracts KEPT. See [RETRO-M1](./docs/retros/M1_retrospective.md). G2 ±1 bps real-data parity run is operator-deferred (needs EODHD CAC.PA fixture + TKAN artefact + momentum factor). M2 begins after G2 closure — see [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.3.
- **v0.2 (2026-04-27)** — **M2 split into M2-IB (PARKED) and M2-IG (ACTIVE)** per option (S) of operator-driven IG-demo-bridge pivot. Substrate authored: cross-cutting [ADR-034](./docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) (multi-broker registry pattern; extends ADR-004) and [ADR-035](./docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) (secrets handling discipline; ~/.blive/secrets/{broker}.env + redaction list) — both PROPOSED; first-batch IG-bridge substrate. Phase 1 specifics table grew an "M2-IG bridge path" column (CAC 40 CFD on IG demo; ADR-021 PAUSED for the bridge). Quality Gates table split G3 → G3-IB (DEFERRED) + G3-IG (ACTIVE). Risk register grew IG-specific rows. Open dependencies cleaned up for IG bridge. M2-IG sub-milestones .1 (substrate) / .2 (cross-cutting infra) / .3 (read side) / .4 (write side) / .5 (strategy run + retro) defined.
- **v0.3 (2026-04-28)** — **M2-IG bridge CLOSED at architectural surface; M2-IB UNPARKED to ACTIVE.** Operator pivot: IB Paper account commissioned 2026-04-28 (enabled 2026-04-29). [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md) STABLE-on-first-write captures the bridge close: ~2 sessions delivered M2-IG.1 substrate + M2-IG.2 cross-cutting infra + M2-IG.3 read side + M2-IG.4 minimum-viable submit (7 tags placed; 359 tests). M2-IG.5 strategy run + production Lightstreamer wrapper DEFERRED with no scheduled revival. M2-IB resumption defined with sub-milestones M2-IB.1 (substrate verification) / .2 (IBClient + IBCredentials) / .3 (IBInstrumentResolver + read side + IBMarketData) / .4 (write side + reconciliation) / .5 (strategy run on IB Paper + RETRO-M2-IB). M2-IG section relabelled ARCHIVED (G3-IG NOT_REACHED, operator-driven close not gate failure). Phase 1 specifics table reverts to ADR-021 ETF path as canonical; ADR-039 CFD variant stays ACCEPTED but bridge-paused. Quality Gates: G3-IB ACTIVE; G3-IG NOT_REACHED. Risk register: IG-specific rows archived; IB-specific rows reasserted. Open dependencies updated: IG operator-side items closed; IB connection params + deployment target + first IB Gateway handshake opened. NEXT_PROMPT.md v0.4 drafted to target M2-IB.
