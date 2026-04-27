# blive — Context Inventory

> **Purpose:** the canonical map of every knowledge artifact this project depends on. Any agent (Claude, contributor, future-self) reading this file should understand *what we know, where it lives, and what's missing* in under 10 minutes.
>
> **Status:** v0.2 DRAFT — M0-close pass. Will be edited every time an artifact is added, retired, or moved.
>
> **Maintainer:** Oleg + Claude.
>
> **Companion files in this repo:**
> - [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) — the rules that keep the artifacts catalogued here coherent over time. Edits to anything in this inventory must follow that protocol.
> - [`REQUIREMENTS.md`](./REQUIREMENTS.md) — the project requirements (one of the artifacts catalogued below).
>
> **Conventions used here:**
> - **KB-N** — durable knowledge base (slow-changing world facts).
> - **INV-N** — inventory (a list of items in some category).
> - **DD-N** — data dictionary (schema-level documentation).
> - **ADR-N** — architectural decision record.
> - **OQ-N** — open question.
> - **RETRO-M{N}** — milestone retrospective (per [ADR-024](./docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type)); frozen historical record.
>
> Status tags: `MISSING` (not yet started) · `DRAFT` (started, incomplete) · `STABLE` (current, accurate) · `STALE` (needs review) · `DEPRECATED` (kept for history).
>
> RETRO artefacts use a simplified lifecycle: `DRAFT → STABLE` only (no `STALE` / `DEPRECATED`).

---

## 0. Why this file exists

Complex software projects fail when context is implicit. As soon as the same project spans more than one session, more than one agent, or more than one person, undocumented context becomes the bottleneck — not skill, not tooling.

The fix is to keep multiple **representation hierarchies** of the same project alongside the code:

- **Vision** — why this exists (1 paragraph).
- **Requirements** — what we will build (`REQUIREMENTS.md`).
- **Design** — how it's shaped (`DESIGN.md`, future).
- **Plan** — what to do next (`TASK_REGISTRY.md`, future).
- **Code** — the system itself.
- **Tests** — proof.
- **Ops** — how to run it (`RUNBOOK.md`, future).

Around those hierarchies, four supporting context layers:

1. **Knowledge bases (KBs)** — durable facts about the world we're building in (btest DSL, IB API, regulations, frameworks).
2. **Inventories (INVs)** — exhaustive lists of items in well-defined categories (strategies, order types, risk checks, events, ports, metrics, alerts).
3. **Data dictionaries (DDs)** — schema-level definitions of every domain object, every persisted row, every API payload.
4. **Decision & question logs** — append-only history of choices made and choices deferred (ADRs, OQs).

This file is the index of all of those. It does not contain the knowledge itself — only pointers to it, lifecycle status, and ownership.

---

## 1. Representation Hierarchy

| Layer | Artifact | Status | Lifecycle | Purpose |
|-------|----------|--------|-----------|---------|
| 0. Process | [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) | DRAFT v0.3 (2026-04-26) | rare amendments, iterative until v1 | the discipline that keeps every other artifact coherent. v0.2 amended §8.3 with milestone-close (8.3.1) and phase-boundary (8.3.2) rules per [ADR-025](./docs/decisions/DECISIONS.md#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules). v0.3 added §11 (Human-governance / agent-execution division of labour with five-layer adoption stack) per [ADR-026](./docs/decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface); existing §11 Self-Critique renumbered to §12 |
| 0. Index | **this file** (`CONTEXT_INVENTORY.md`) | DRAFT v0.2 (2026-04-26) | continuous | the registry of all artifacts |
| 1. Vision | (top of `README.md`, future) | MISSING | rare | one paragraph: why blive exists |
| 2. Requirements | [`REQUIREMENTS.md`](./REQUIREMENTS.md) | DRAFT v0.1 | iterative until M0 frozen | what we will build |
| 3. Design | `DESIGN.md` | MISSING | iterative through M2 | how it is shaped (component, sequence, state diagrams) |
| 4. Plan | [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) | DRAFT v0.1 (2026-04-26) | per milestone | Phase 1 plan: M0–M3 detailed with G0–G4 gates and risk register; M4+ sketched. Conditional on OQ-024..027 confirmation. |
| 5. Code | `src/blive/` | DRAFT v0.2 (2026-04-27) | continuous | M0+M1: `domain/{types,events,order_fsm,ports,positions}.py`; `adapters/{paper.{broker,market_data}, memory.{persistence,bus}, clock.{wall,sim}, alert.log}`; `strategy/{config,loader}.py`; `sizing/sizer.py`; `risk/checks.py`; `runtime/paper_pipeline.py`. |
| 6. Tests | `tests/` | DRAFT v0.2 (2026-04-27) | continuous | 175 tests green; M1 adds `unit/{strategy,sizing,risk,runtime}/*`, `unit/adapters/{paper/test_market_data,paper/test_paper_broker_replace,alert/test_log_alert}/*`, and `contracts/test_btest_imports.py`. PaperBroker round-trip + FSM coverage from M0 retained. |
| 7. Ops | `RUNBOOK.md` | MISSING | post-M5 | running it |

Rule: each layer down narrows scope and is internally consistent with the layer above. If layer N changes, layer N-1 either approved the change (forward propagation) or is now stale (must be flagged).

---

## 2. Knowledge Bases (KBs)

Durable, slow-changing context. Each KB is one file under `docs/kb/` with a header listing **owner, status, last-reviewed, sources**.

| Id | File | Status | Why it matters | Owner | Needed by |
|----|------|--------|---------------|-------|-----------|
| **KB-1** | [`docs/kb/btest_dsl_inventory.md`](./docs/kb/btest_dsl_inventory.md) | DRAFT v0.1 (2026-04-26) | Every `btest` dataclass with broker-neutrality verdict (broker-neutral / backtest-only / mixed). Strategy → DataConfig → Universe → factors → signals → portfolio → execution → costs → backtest config → DataSource registry. blive's three sidecar extensions documented (live_overrides, live_*_provider, live_kill_switch). | Claude | REQUIREMENTS |
| **KB-2** | [`docs/kb/ib_capability_matrix.md`](./docs/kb/ib_capability_matrix.md) | DRAFT v0.1 (2026-04-26) | Connectivity (TWS / Gateway / CPAPI), asset classes, order types, TIFs, routing (SMART / direct), IB algos (Adaptive, TWAP, VWAP, etc.), market hours, multi-currency, account types (IBKR Pro Margin), 2FA / IBC / daily restart. | Claude | REQUIREMENTS, DESIGN |
| **KB-3** | [`docs/kb/ib_pacing_spec.md`](./docs/kb/ib_pacing_spec.md) | DRAFT v0.1 (2026-04-26) | 50 msg/sec throttle; historical-data pacing (≤60/10min, BID_ASK ×2); market-data tiers; reqMktData vs reqTickByTickData budgets; orderId monotonic + multi-client; daily/weekly ops; CPAPI limits (rejected); error-code mapping at pacing boundary; concrete adapter budget defaults table. | Claude | REQUIREMENTS, DESIGN |
| **KB-4** | [`docs/kb/frameworks_survey.md`](./docs/kb/frameworks_survey.md) | DRAFT v0.1 (2026-04-26) | Adopt: ib_async. Study: NautilusTrader, Hummingbot, Lumibot, vnpy. Reject: native ibapi, CPAPI, Lean, Backtrader live, Zipline+pylivetrader, QSTrader, Lumibot polling lifecycle, QuantRocket, PyAlgoTrade, Catalyst. 10 architectural patterns to copy. | Claude | REQUIREMENTS |
| **KB-5** | [`docs/kb/strategy_taxonomy.md`](./docs/kb/strategy_taxonomy.md) | DRAFT v0.1 (2026-04-26) | The actual strategies blive must support: A1 cross-sectional L/S, A1a cross-index lagging, A2 single-instrument timing, A3 multi-ETF rotation; future A4–A8 slots. Phased priority proposal §7 pending OQ-013. Raised OQ-013..OQ-021. | shared (Oleg primary, Claude assist) | REQUIREMENTS |
| **KB-6** | [`docs/kb/cost_margin_dictionary.md`](./docs/kb/cost_margin_dictionary.md) | DRAFT v0.1 (2026-04-26) | Each component: backtest semantic, live equivalent, parity envelope. Commission (pure formula, IB ground truth), BorrowCost (live override needed, ±25 bps gen-coll), FinancingCost (live override, ±15 bps within tier), StaticFees (pure formula), MarginConfig (live per-instrument), RiskChecks + DrawdownPolicy (pure formulas). Aggregation pipeline + parity-residual decomposition for ADR-012. | Claude | REQUIREMENTS |
| **KB-7** | `docs/kb/failure_modes.md` | MISSING | Every failure mode + required engine response + chaos-test fixture. Expansion of REQUIREMENTS §13.2. | Claude | REQUIREMENTS, DESIGN |
| **KB-8** | `docs/kb/operational_events.md` | MISSING | Daily TWS restart at 23:45 ET, weekly token, holidays, exchange schedules, corp actions, IB maintenance windows. | Claude | DESIGN, OPS |
| **KB-9** | [`docs/kb/uk_regulatory.md`](./docs/kb/uk_regulatory.md) | DRAFT v0.1 (2026-04-26) | Personal trading not FCA-regulated; HMRC trade-by-trade records 5+ years; existing event-log + hash-chained audit already satisfies MiFID-II shape; market abuse always applies; data privacy n/a personal. Items needing accountant/lawyer flagged. **(Oleg / professional)** confirmation expected on trading-vs-investment classification. | Oleg primary | REQUIREMENTS (NFRs) |
| **KB-10** | [`docs/decisions/DECISIONS.md`](./docs/decisions/DECISIONS.md) | DRAFT v0.5 (2026-04-27) | ADR-001..029 ACCEPTED. Latest batch ADR-027..029 (M1 entry): Sizer rounding policy (integer shares, truncate toward zero), strategy config shape (Python `build_strategy()` + blive YAML overrides; DD-3 prep), `PaperMarketData` as `MarketDataPort` adapter (fixture-backed parquet). | Claude record, Oleg approve | continuous |
| **KB-11** | [`docs/decisions/OPEN_QUESTIONS.md`](./docs/decisions/OPEN_QUESTIONS.md) | DRAFT v0.2 (2026-04-27) | OQ-001..030 catalogued. **12 RESOLVED-BY-ADR** (013, 014, 015, 016, 018, 019, 021, 022, 024, 025, 026, 027); 1 RESOLVED-by-finding (017); 4 OPEN (012, 023, 028, 029); 13 IN_DISCUSSION (001–011, 020, **030 btest-interpreter dispatch for non-LongShort archetypes — raised at M1**). | shared | continuous |
| **KB-12** | [`docs/GLOSSARY.md`](./docs/GLOSSARY.md) | DRAFT v0.1 (2026-04-26) | Extracted from REQUIREMENTS §17 + accumulated terms (archetype, ADR, parity envelope, parity diagnostic, parity residual, NDJSON tape, OPRA, SMART, TIF, TKAN, tradable proxy, etc.). Now SSOT for terminology. | Claude | continuous |
| **KB-13** | [`docs/kb/companion_projects.md`](./docs/kb/companion_projects.md) | DRAFT v0.1 (2026-04-26) | btest = primary dependency (blive imports engines + DSL). harp = paper, indirect via deferred A1 strategy. pt-liqadj = independent, bond focus. ForgeFolio = monitoring, possibly post-M8 read-only integration (raised OQ-023). b-autobot = empty placeholder. equities/smim/* = research-only, UK-LC/UK-MC candidate post-M8. | Oleg primary, Claude assist | REQUIREMENTS |
| **KB-14** | Claude memory `~/.claude/projects/.../memory/` | STABLE | User profile, feedback, project context that persists across conversations. Already maintained. | implicit | continuous |
| **KB-15** | `docs/kb/parity_methodology.md` | MISSING | How the parity diagnostic actually works: replay engine, position seeding, residual decomposition. Loadbearing for REQUIREMENTS §8; can wait until M7 design but worth a stub now. | Claude | DESIGN (M7) |

---

## 3. Inventories (INVs)

Exhaustive lists in well-defined categories. Each lives at `docs/inv/<name>.md` and is expected to be machine-checkable (an automated test asserts the inventory matches code).

| Id | File | Status | Items | Needed by |
|----|------|--------|-------|-----------|
| **INV-1** | [`docs/inv/strategies.md`](./docs/inv/strategies.md) | DRAFT v0.1 (2026-04-26) | 9 strategies catalogued; v1 phase per ADR-013; NAV slice TBD per OQ-013. | REQUIREMENTS, DESIGN |
| **INV-2** | `docs/inv/order_types.md` | MISSING | MKT, LMT, MOC, LOC, STP, STP_LMT, OPG, IOC, FOK + IB support matrix per asset class | REQUIREMENTS, DESIGN |
| **INV-3** | `docs/inv/tif_values.md` | MISSING | DAY, GTC, IOC, FOK, OPG, GTD + venue compatibility | DESIGN |
| **INV-4** | [`docs/inv/risk_checks.md`](./docs/inv/risk_checks.md) | DRAFT v0.1 (2026-04-26) | RC-01..RC-13: leverage, exposure, weight, daily loss, rate limits (per-strategy + global), concentration, stale data, market hours, price sanity, drawdown scaling, model-artefact freshness, kill-switch armed. Order-of-evaluation specified. | REQUIREMENTS |
| **INV-5** | [`docs/inv/domain_events.md`](./docs/inv/domain_events.md) | STABLE v0.2 (2026-04-27) | 17 event topics catalogued with payload, emission rule, consumer set, milestone. M0+M1 implemented: order.*, broker.connection, risk.breach. `DomainEvent = OrderEvent \| ConnectionStatus \| RiskBreach`. Other events (M2+) remain forward-planned. | DESIGN |
| **INV-6** | [`docs/inv/ports_adapters.md`](./docs/inv/ports_adapters.md) | STABLE v0.2 (2026-04-27) | 6 Ports (Broker, MarketData, Clock, Persistence, Alert, EventBus). M0+M1 adapters live: PaperBroker (incl. replace), PaperMarketData, InMemoryPersistence, InMemoryEventBus, Sim/WallClock, LogAlert. IB & EODHD adapters at M2/M3. Port Protocol surfaces unchanged from v0.1. | DESIGN |
| **INV-7** | `docs/inv/rest_endpoints.md` | MISSING (eventually superseded by OpenAPI) | path, method, auth class, request/response, idempotency | M6 |
| **INV-8** | `docs/inv/metrics.md` | MISSING | Prometheus metric name, type, labels, alert thresholds | DESIGN, M7 |
| **INV-9** | `docs/inv/alerts.md` | MISSING | alert name, trigger condition, severity, channels, runbook link | M7 |
| **INV-10** | [`docs/inv/asset_classes.md`](./docs/inv/asset_classes.md) | DRAFT v0.1 (2026-04-26) | 13 asset classes catalogued with btest support, EODHD All-in-One coverage, IB tradability, v1 priority. | REQUIREMENTS |
| **INV-11** | `docs/inv/modes.md` | DRAFT (inline REQUIREMENTS §5.6) | Paper / IB Paper / Shadow / Live — capabilities, transitions, gates | REQUIREMENTS |
| **INV-12** | `docs/inv/backup_artifacts.md` | MISSING | what gets backed up, frequency, retention, restore SLA | M5 |
| **INV-13** | [`docs/inv/order_state_transitions.md`](./docs/inv/order_state_transitions.md) | STABLE v0.1 (2026-04-26) | 9 states × 9 triggers → 14 legal transitions (T1..T14); side effects per row; reason / fill payload discipline; cancel-/reject-reason taxonomy; idempotency rules. Implementation in `blive.domain.order_fsm`; tests cover every row + illegal sample. | DESIGN |
| **INV-14** | `docs/inv/ib_error_codes.md` | MISSING | IB-specific error codes we map to typed engine errors | DESIGN |

---

## 4. Data Dictionaries (DDs)

Schema-level documentation. Each `docs/dd/<name>.md` lists every field with type, semantics, invariants, sample, lineage.

| Id | File | Status | Coverage | Needed by |
|----|------|--------|----------|-----------|
| **DD-1** | [`docs/dd/domain_objects.md`](./docs/dd/domain_objects.md) | STABLE v0.1 (2026-04-26) | 11 types: Instrument, Bar, Trade, Order, Fill, OrderEvent, Position, AccountSnapshot, OrderUpdate, ConnectionStatus, BrokerEvent (alias). Plus 7 enums (OrderSide/Type/TIF/State/EventKind, AssetClass, Severity). Field-level invariants enforced in `__post_init__`. | DESIGN |
| **DD-2** | `docs/dd/event_schemas.md` | MISSING | Every domain event payload, JSON shape, version field policy | DESIGN |
| **DD-3** | [`docs/dd/config_schemas.md`](./docs/dd/config_schemas.md) | DRAFT v0.1 (2026-04-27) | `LiveStrategyConfig` + 6 sub-objects (`LiveOverrides`, `LiveBorrowProvider`, `LiveFinancingProvider`, `LiveKillSwitch`, `ArtefactPaths`, `RiskOverrides`); merge order; worked `tkan_v4_momentum_timing_1x` example. M1 RC subset only; M4-tier RC keys forward-compat-ignored. | DESIGN |
| **DD-4** | `docs/dd/storage_schemas.md` | MISSING | SQLite DDL for every table, indexes, migrations | DESIGN, M4 |
| **DD-5** | `docs/dd/api_schemas.md` | MISSING (eventually OpenAPI) | REST request/response schemas | M6 |
| **DD-6** | `docs/dd/metric_schemas.md` | MISSING | Prometheus metric definitions in code-checkable form | M7 |
| **DD-7** | `docs/dd/instrument_dictionary.md` | MISSING | How `blive`'s `Instrument` maps to IB `Contract`; ConID resolution; symbology | DESIGN |

---

## 5. Decision & Question Logs

| Id | File | Status | Purpose |
|----|------|--------|---------|
| **DEC** | `docs/decisions/DECISIONS.md` | MISSING | ADR-NNN entries, append-only with supersede chain |
| **OQ** | `docs/decisions/OPEN_QUESTIONS.md` | MISSING | OQ-NNN entries, each with target resolution date + depends-on |

**ADR seed list** (drafts to write at the same time as the file is created):

- ADR-001 — Project name `blive` (rationale: pairing with `btest`).
- ADR-002 — Adopt `ib_async` v2.1+ as wire-level driver behind a single adapter.
- ADR-003 — Borrow architecture from NautilusTrader, do not depend on it.
- ADR-004 — Hexagonal ports/adapters with import-linter enforcement.
- ADR-005 — Single-process, single-asyncio-loop kernel for v1.
- ADR-006 — SQLite for persistence in v1; Postgres migration deferred.
- ADR-007 — In-process event bus for v1; Redis Streams as opt-in.
- ADR-008 — RiskEngine no-bypass: architectural enforcement.
- ADR-009 — Crash-only design; restart path = cold-start path.
- ADR-010 — Reuse `btest`'s `FactorEngine`/`SignalEngine`/`PortfolioEngine` by import; vendor specific modules only on upstream-break.
- ADR-011 — 3-page minimal web UI; mobile and OAuth deferred.
- ADR-012 — Parity diagnostic is mandatory daily; degraded mode if broken.

**OQ seed list** (12 items already in REQUIREMENTS §16, ready to externalize on creation).

---

## 5.5 Retrospectives (RETRO-M{N})

Frozen per-milestone records per [ADR-024](./docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type). Lifecycle: `DRAFT → STABLE` only.

| Id | File | Status | Closes | Notes |
|----|------|--------|--------|-------|
| **RETRO-template** | [`docs/retros/_template.md`](./docs/retros/_template.md) | STABLE | — | template; copy to `M{N}_retrospective.md` at milestone close |
| **RETRO-M0** | [`docs/retros/M0_retrospective.md`](./docs/retros/M0_retrospective.md) | STABLE v1.0 (2026-04-26) | M0 (G1 PASSED) | M0 close: substrate (DD-1, INV-13, INV-5, INV-6) + domain code + paper/memory/clock adapters + 113 tests + import-linter rule with negative test |
| **RETRO-M1** | [`docs/retros/M1_retrospective.md`](./docs/retros/M1_retrospective.md) | STABLE v1.0 (2026-04-27) | M1 (G2 PARTIAL) | M1 close: ADR-027..029 ACCEPTED; DD-3 → DRAFT; INV-5/INV-6 → STABLE; OQ-030 raised; strategy loader / Sizer / RiskEngine M1-subset / PaperMarketData / LogAlert / PaperBroker.replace / paper-mode pipeline; 175 tests + CI smoke-import; G2 real-data ±1 bps deferred to operator EODHD+TKAN run |

---

## 6. Lifecycle Tags — what's needed when

To avoid premature elaboration, each artifact is tagged by which lifecycle stage *blocks on it*. Earlier stages must complete before later ones, but artifacts can be drafted ahead.

### 6.1 Needed NOW to finalize REQUIREMENTS (v0.1 → v1.0)

These are the gaps that turn confident-sounding claims in REQUIREMENTS into facts:

| Artifact | What it unblocks in REQUIREMENTS |
|----------|---------------------------------|
| **KB-5 strategy_taxonomy** | §1, §3, §5, §15 — without knowing the actual strategy mix, scope decisions are guesses |
| **KB-1 btest_dsl_inventory** | §5.1 reuse claims; §8 parity contract |
| **KB-2 ib_capability_matrix** | §5.3 order types; §10 gotchas; §15 out-of-scope |
| **KB-3 ib_pacing_spec** | §5.5 rate-limit defaults; §10 gotcha mitigations |
| **KB-4 frameworks_survey** | §9 (move detail out of REQUIREMENTS body) |
| **KB-6 cost_margin_dictionary** | §8 parity envelopes (numbers need derivation, not guess) |
| **KB-9 uk_regulatory** | §6.3 audit/security requirements |
| **KB-13 companion_projects** | §1, §3 (boundaries with btest/harp) |
| **KB-12 GLOSSARY extracted** | every section depends on consistent terminology |
| **KB-10 DECISIONS bootstrap** (ADR-001..012) | makes REQUIREMENTS skim-friendly by referencing ADRs instead of repeating rationale |
| **KB-11 OPEN_QUESTIONS** | externalize §16 |
| **INV-1 strategies** | §1 scope |
| **INV-4 risk_checks** | §5.5 |
| **INV-10 asset_classes** | §15 out-of-scope |

### 6.2 Needed for DESIGN (M0–M2)

KB-7 failure_modes (full), KB-15 parity_methodology, all DDs (DD-1..7), INV-2/3/5/6/8/13/14.

### 6.3 Needed for IMPLEMENTATION (M2–M6)

INV-7, INV-9, DD-5, KB-8 operational_events.

### 6.4 Needed for OPERATIONS (M6+)

`RUNBOOK.md`, INV-12, full OpenAPI, monitoring dashboard JSON.

---

## 7. File Layout

```
blive/
  README.md                                  ← short overview, links to everything
  REQUIREMENTS.md                            ← v0.2 DRAFT (current)
  CONTEXT_INVENTORY.md                       ← this file
  CONTEXT_PROTOCOL.md                        ← v0.2 DRAFT (the discipline)
  TASK_REGISTRY.md                           ← v0.1 DRAFT (Phase 1 plan)
  NEXT_PROMPT.md                             ← session kickoff prompt
  DESIGN.md                                  ← future (post-REQUIREMENTS freeze)
  TASK_REGISTRY.md                           ← future
  RUNBOOK.md                                 ← future
  CLAUDE.md                                  ← project instructions for Claude (small, points here)
  docs/
    GLOSSARY.md                              ← KB-12
    kb/
      btest_dsl_inventory.md                 ← KB-1
      ib_capability_matrix.md                ← KB-2
      ib_pacing_spec.md                      ← KB-3
      frameworks_survey.md                   ← KB-4
      strategy_taxonomy.md                   ← KB-5
      cost_margin_dictionary.md              ← KB-6
      failure_modes.md                       ← KB-7
      operational_events.md                  ← KB-8
      uk_regulatory.md                       ← KB-9
      companion_projects.md                  ← KB-13
      parity_methodology.md                  ← KB-15
    PHASE_1_READINESS.md                     ← Phase 1 readiness audit
    retros/
      _template.md                           ← RETRO frontmatter + sections
      M{N}_retrospective.md                  ← per-milestone (created at M_{N} close)
    method/
      paper/cognitive_cartography.tex        ← canonical paper source
      paper/references.bib                   ← bibliography
      Amendments_Log.md                      ← methodology amendments staging for paper iteration
      Research_Plan_for_Paper_Iteration_*.md ← research plans informing iterations
    decisions/
      DECISIONS.md                           ← KB-10
      OPEN_QUESTIONS.md                      ← KB-11
      adr/
        ADR-001-name-blive.md                ← optional one-file-per-ADR variant
        ADR-002-adopt-ib-async.md
        ...
    inv/
      strategies.md                          ← INV-1
      order_types.md                         ← INV-2
      tif_values.md                          ← INV-3
      risk_checks.md                         ← INV-4
      domain_events.md                       ← INV-5
      ports_adapters.md                      ← INV-6
      rest_endpoints.md                      ← INV-7
      metrics.md                             ← INV-8
      alerts.md                              ← INV-9
      asset_classes.md                       ← INV-10
      modes.md                               ← INV-11
      backup_artifacts.md                    ← INV-12
      order_state_transitions.md             ← INV-13
      ib_error_codes.md                      ← INV-14
    dd/
      domain_objects.md                      ← DD-1
      event_schemas.md                       ← DD-2
      config_schemas.md                      ← DD-3
      storage_schemas.md                     ← DD-4
      api_schemas.md                         ← DD-5
      metric_schemas.md                      ← DD-6
      instrument_dictionary.md               ← DD-7
```

Two structural choices to note:

- **One file per ADR** (`docs/decisions/adr/ADR-NNN-slug.md`) is more scalable than one big DECISIONS.md once we cross ~10 ADRs. The DECISIONS.md becomes the index. We may start in one file and split later.
- **All inventories and DDs live under `docs/`** so they don't clutter the project root. Only the ~6 living top-level docs (README, REQUIREMENTS, CONTEXT_INVENTORY, DESIGN, TASK_REGISTRY, RUNBOOK, CLAUDE) sit at the root.

---

## 8. Standard Header for Every Artifact

Every KB / INV / DD / ADR file starts with this YAML-ish frontmatter so an agent can scan ownership and freshness without reading the body:

```markdown
---
id: KB-2
title: IB Capability Matrix
status: DRAFT          # MISSING | DRAFT | STABLE | STALE | DEPRECATED
owner: Claude
last_reviewed: 2026-04-26
sources:
  - https://interactivebrokers.github.io/tws-api/...
  - https://www.interactivebrokers.com/campus/...
depends_on: []         # other artifact ids this references
referenced_by:         # backlinks; can be auto-generated
  - REQUIREMENTS.md §10
  - DESIGN.md §IB
---
```

---

## 9. Maintenance Rules

1. **CONTEXT_INVENTORY.md is the index of indexes.** Adding a new KB/INV/DD/ADR/OQ requires a row update here in the same commit.
2. **Status field is mandatory** on every artifact and must be one of the five values listed above.
3. **`STABLE` artifacts** are reviewed at every milestone freeze; if last_reviewed is older than the most recent freeze, status auto-degrades to `STALE`.
4. **Decision log is append-only.** Reverse a decision via a new ADR with `Supersedes: ADR-NNN`; never edit the original.
5. **Inventories must be machine-checkable** where feasible: a test asserts every IB error code in code is listed in `INV-14`, every metric in code is in `INV-8`, etc. Drift detected at CI time, not in production.
6. **Cross-references use stable ids** (KB-N, INV-N, DD-N, ADR-N, OQ-N), not file paths. File paths can be reorganized; ids should not.
7. **The Glossary (KB-12) is authoritative.** If two artifacts disagree on a term, the Glossary wins or both are wrong; conversation is required.
8. **Every artifact links its sources.** Especially KBs sourced from external docs: link with date accessed.

---

## 10. Priority Queue — what to write next

Ordered by what unblocks REQUIREMENTS finalization:

**Done this session (2026-04-26)**:

- ~~**KB-5 `strategy_taxonomy.md`**~~ — DRAFT v0.1.2.
- ~~**KB-11 `OPEN_QUESTIONS.md`**~~ — DRAFT v0.1.2 (now includes OQ-023..027 sub-questions raised in PHASE_1_READINESS).
- ~~**KB-10 `DECISIONS.md`**~~ — DRAFT v0.1. ADR-001..019 ACCEPTED.
- ~~**REQUIREMENTS.md v0.2**~~ — applied KB references; collapsed inline survey/OQs/glossary into pointers.
- ~~**`docs/PHASE_1_READINESS.md`**~~ — eight-dimension readiness audit; gates Phase 1 plan.
- ~~**`TASK_REGISTRY.md`**~~ — DRAFT v0.1, Phase 1 plan with M0–M3 detailed and G0–G4 gates.

**Outstanding queue (in order)**:

1. ~~Operator confirmation of OQ-024..OQ-027.~~ ✓ Done 2026-04-26; ADR-020..023 added; G0 gate **PASSED**.
2. ~~**M0 execution**~~ ✓ Done 2026-04-26. **G1 gate exit criteria met** — see [RETRO-M0](./docs/retros/M0_retrospective.md).
3. ~~**M1 execution**~~ ✓ Done 2026-04-27. ADR-027..029 ACCEPTED; DD-3 → DRAFT; INV-5/INV-6 → STABLE; OQ-030 raised; strategy loader / Sizer / RiskEngine M1-subset (RC-08/09/12/13) / PaperMarketData / LogAlert / PaperBroker.replace() / paper-mode pipeline shipped; 175 tests green; CI smoke-import for btest engines added. RETRO-M1 written. **G2 gate criteria 1–4: see [RETRO-M1](./docs/retros/M1_retrospective.md) for partial-pass detail (synthetic-fixture parity green; full real-data ±1 bps test deferred to operator-driven `tests_slow/g2_parity` run with EODHD CAC.PA + TKAN artefact).**
4. **Operator-side prereqs for G2 → M2**:
   - IB Paper account commissioned (operator). **OPEN.**
   - **EODHD subscription for CAC.PA** — ✓ **verified 2026-04-27** (CAC.PA daily EOD + delayed real-time quotes confirmed in tier). Open small follow-up for M2: correct CAC-40 *index* ticker on EODHD (try `PX1.INDX` / `^FCHI`); not a G2 blocker since [ADR-021](./docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) trades the ETF.
   - Docker host decision (Linux VM vs Windows). **OPEN.**
   - **Real-data G2 ±1 bps parity run** — pipeline ready; needs EODHD CAC.PA daily history fixture + TKAN `pred_cache.pkl` + `cact_momentum.parquet`. **OPEN.** EODHD CAC.PA path now confirmed; the fetch script for the fixture is itself an M2 deliverable per [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.3.
5. **M2 execution** — IB read-side adapter + operational foundation per [TASK_REGISTRY](./TASK_REGISTRY.md) M2; conditioned on G2 closure. [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.3 drafted at M1 close.

Outside the Phase 1 critical path:

- **Vision / `README.md`** — minimal stub committed at M0; full vision paragraph still pending.
- **Design-phase artefacts** (KB-7 failure_modes, KB-8 operational_events, KB-15 parity_methodology, DD-2..7, INV-2/3/7/8/9/11/12/14) — produced as M1/M2/M3 deliverables per `TASK_REGISTRY.md` rather than in advance.

After this batch, `REQUIREMENTS.md` gets the v0.2 pass that *removes* content now living in KBs and replaces with id references — slimmer, more authoritative, easier to iterate further.

---

## 11. Self-Critique / Next-Pass TODOs

Notes for v0.2 of this file:

- [ ] Add a "tooling" section: which agents/skills/scripts maintain which artifacts (e.g. a script that audits inventory machine-checkability).
- [ ] Add a "review cadence" table — which artifacts review monthly vs. per-milestone vs. on-change.
- [ ] Decide whether `CLAUDE.md` (project-level Claude instructions) should be authored now or after KB-5; current view: now, but minimal — points to this file and REQUIREMENTS.
- [ ] Add a top-level `README.md` with the 30-second pitch and links to (1) REQUIREMENTS, (2) this file, (3) ADRs, (4) future RUNBOOK.
- [ ] Consider whether to mirror the SMIM project's `TASK_REGISTRY.md` structure verbatim or adapt; the SMIM model has worked for the user before.
- [ ] Confirm the ADR-vs-OQ split is right — some open questions are better expressed as "ADR-X status=PROPOSED" than as a separate OQ.
- [ ] Add a section on how this file is consumed by the agent at session start (read-first protocol), so future sessions warm up faster.
