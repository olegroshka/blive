# blive — Context Inventory

> **Purpose:** the canonical map of every knowledge artifact this project depends on. Any agent (Claude, contributor, future-self) reading this file should understand *what we know, where it lives, and what's missing* in under 10 minutes.
>
> **Status:** v0.7 DRAFT — M2-IG bridge close at architectural surface (RETRO-M2-IG STABLE; M2-IG.5 strategy run + production Lightstreamer wrapper deferred). M2-IB resumption is now the active path (IB Paper account commissioned 2026-04-28; enabled 2026-04-29). Will be edited every time an artifact is added, retired, or moved.
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
| 4. Plan | [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) | DRAFT v0.3 (2026-04-28) | per milestone | Phase 1 plan: M0–M1 closed; M2-IG bridge **closed at architectural surface 2026-04-28** (sub-milestones .1–.4 shipped; .5 strategy run deferred — see [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md)); **M2-IB unparked 2026-04-28** (IB Paper account commissioned, enabled 2026-04-29) with sub-milestones M2-IB.1 (substrate at checkpoint) / .2 (IBClient + IBCredentials) / .3 (IBInstrumentResolver + read side + IBMarketData) / .4 (write side + reconciliation, optionally consolidated with M3) / .5 (strategy run + RETRO-M2-IB). Quality gates: G3-IG marked NOT_REACHED (operator-driven close, not gate failure); G3-IB re-activated. Phase 1 specifics table reverts to ADR-021 ETF path as canonical; ADR-039 CFD variant marked bridge-paused. |
| 5. Code | `src/blive/` | DRAFT v1.5 (2026-05-01) | continuous | M0+M1: domain + adapters/{paper, memory, clock, alert} + strategy + sizing + risk + runtime/paper_pipeline. **M2-IG.2:** adapters/shared/{rate_limiter, credentials} + runtime/broker_registry + DD-1 v0.2 + DD-3 v0.2 substrate. **M2-IG.3:** adapters/ig/{credentials, client, instrument_resolver, broker, market_data, lightstreamer} + __init__.py factories. IGMarketData ships `historical_bars` (REST) + `subscribe_bars` (LightstreamerSource abstraction; production wrapper deferred). **M2-IG.4 (MARKET submit only):** IGBroker.submit() implements POST /positions/otc + GET /confirms/{ref} polling + FSM event emission. **M2-IB.2:** adapters/ib/{credentials, client, rate_limiter, __init__}. IBClient wraps `ib_async.IB` (TCP socket + callback model); IBCredentials per ADR-035; IB_DEFAULT_RATE_LIMITS table. **M2-IB.3a:** adapters/ib/instrument_resolver.py — IBInstrumentResolver per DD-7 §5 v0.2; Yahoo-suffix translation per ADR-041. **M2-IB.3b-i:** adapters/ib/broker.py — IBBroker (read methods). connect/disconnect lifecycle (auto-subscribes via ib_async's connectAsync), positions / account_snapshot (built from accountValueEvent push stream) / open_orders, events() iterator emitting ConnectionStatus. submit/cancel/replace raise NotImplementedError (M2-IB.4). domain/events.py widened with AccountUpdate + ArtefactFreshnessWarning (M2 event types). **scripts/probe_ib_*.py** = wire-level smoke tests (handshake / resolve_contract / read). |
| 6. Tests | `tests/` | DRAFT v1.5 (2026-05-01) | continuous | 440 tests green (was 416 at M2-IB.3a-resolved). M0/M1/M2-IG/M2-IB.2/M2-IB.3a modules unchanged. **M2-IB.3b-i additions:** `unit/adapters/ib/test_broker.py` adds 24 tests for IBBroker read side — connect/disconnect/idempotency, ConnectionStatus emission, accountValues seed + post-connect event-push merging, account_snapshot composition + base-currency inference + cash_by_ccy + leverage, positions parsing (primaryExchange-preferring, unparseable-skip), open_orders parsing (LMT happy path, unsupported orderType skip), rate-limit acquire on positions/open_orders, write methods (submit/cancel/replace) raise NotImplementedError. Uses real `eventkit.Event` for `accountValueEvent` so `+=`/`-=` round-trip realistically. Domain event types validated implicitly through IBBroker tests. |
| 7. Ops | `RUNBOOK.md` | MISSING | post-M5 | running it |

Rule: each layer down narrows scope and is internally consistent with the layer above. If layer N changes, layer N-1 either approved the change (forward propagation) or is now stale (must be flagged).

---

## 2. Knowledge Bases (KBs)

Durable, slow-changing context. Each KB is one file under `docs/kb/` with a header listing **owner, status, last-reviewed, sources**.

| Id | File | Status | Why it matters | Owner | Needed by |
|----|------|--------|---------------|-------|-----------|
| **KB-1** | [`docs/kb/btest_dsl_inventory.md`](./docs/kb/btest_dsl_inventory.md) | DRAFT v0.1 (2026-04-26) | Every `btest` dataclass with broker-neutrality verdict (broker-neutral / backtest-only / mixed). Strategy → DataConfig → Universe → factors → signals → portfolio → execution → costs → backtest config → DataSource registry. blive's three sidecar extensions documented (live_overrides, live_*_provider, live_kill_switch). | Claude | REQUIREMENTS |
| **KB-2** | [`docs/kb/ib_capability_matrix.md`](./docs/kb/ib_capability_matrix.md) | DRAFT v0.1.1 (2026-04-27) | Connectivity (TWS / Gateway / CPAPI), asset classes, order types, TIFs, routing (SMART / direct), IB algos (Adaptive, TWAP, VWAP, etc.), market hours, multi-currency, account types (IBKR Pro Margin), 2FA / IBC / daily restart. M2-entry review pass: no amendments; STABLE flip deferred to M2 close. | Claude | REQUIREMENTS, DESIGN |
| **KB-3** | [`docs/kb/ib_pacing_spec.md`](./docs/kb/ib_pacing_spec.md) | DRAFT v0.1.1 (2026-04-27) | 50 msg/sec throttle; historical-data pacing (≤60/10min, BID_ASK ×2); market-data tiers; reqMktData vs reqTickByTickData budgets; orderId monotonic + multi-client; daily/weekly ops; CPAPI limits (rejected); error-code mapping at pacing boundary; concrete adapter budget defaults table. M2-entry review pass: no amendments; STABLE flip deferred to M2 close once ADR-031 rate limiter is exercised. | Claude | REQUIREMENTS, DESIGN |
| **KB-4** | [`docs/kb/frameworks_survey.md`](./docs/kb/frameworks_survey.md) | DRAFT v0.1 (2026-04-26) | Adopt: ib_async. Study: NautilusTrader, Hummingbot, Lumibot, vnpy. Reject: native ibapi, CPAPI, Lean, Backtrader live, Zipline+pylivetrader, QSTrader, Lumibot polling lifecycle, QuantRocket, PyAlgoTrade, Catalyst. 10 architectural patterns to copy. | Claude | REQUIREMENTS |
| **KB-5** | [`docs/kb/strategy_taxonomy.md`](./docs/kb/strategy_taxonomy.md) | DRAFT v0.1 (2026-04-26) | The actual strategies blive must support: A1 cross-sectional L/S, A1a cross-index lagging, A2 single-instrument timing, A3 multi-ETF rotation; future A4–A8 slots. Phased priority proposal §7 pending OQ-013. Raised OQ-013..OQ-021. | shared (Oleg primary, Claude assist) | REQUIREMENTS |
| **KB-6** | [`docs/kb/cost_margin_dictionary.md`](./docs/kb/cost_margin_dictionary.md) | DRAFT v0.1 (2026-04-26) | Each component: backtest semantic, live equivalent, parity envelope. Commission (pure formula, IB ground truth), BorrowCost (live override needed, ±25 bps gen-coll), FinancingCost (live override, ±15 bps within tier), StaticFees (pure formula), MarginConfig (live per-instrument), RiskChecks + DrawdownPolicy (pure formulas). Aggregation pipeline + parity-residual decomposition for ADR-012. | Claude | REQUIREMENTS |
| **KB-7** | `docs/kb/failure_modes.md` | MISSING | Every failure mode + required engine response + chaos-test fixture. Expansion of REQUIREMENTS §13.2. | Claude | REQUIREMENTS, DESIGN |
| **KB-8** | [`docs/kb/operational_events.md`](./docs/kb/operational_events.md) | DRAFT v0.2 (2026-04-27) | Daily TWS restart (23:45 ET), weekly token rotation, TWS auto-update window, exchange holidays, corp actions, IB maintenance windows, blive-side scheduled events (`AccountUpdate` 30s, reconciliation 60s, daily backup, parity diagnostic). **v0.2 (M2-IG.2)**: §8 IG-specific operational events — session token TTL (6h demo / 24h live; auto-refresh 30s pre-emptive), idle-session timeout (~6 min; 5-min heartbeat on `general` bucket), weekend market closure, IG maintenance windows, IG-vs-IB comparison table. | Claude | DESIGN, OPS |
| **KB-9** | [`docs/kb/uk_regulatory.md`](./docs/kb/uk_regulatory.md) | DRAFT v0.1 (2026-04-26) | Personal trading not FCA-regulated; HMRC trade-by-trade records 5+ years; existing event-log + hash-chained audit already satisfies MiFID-II shape; market abuse always applies; data privacy n/a personal. Items needing accountant/lawyer flagged. **(Oleg / professional)** confirmation expected on trading-vs-investment classification. | Oleg primary | REQUIREMENTS (NFRs) |
| **KB-10** | [`docs/decisions/DECISIONS.md`](./docs/decisions/DECISIONS.md) | DRAFT v0.12 (2026-05-01) | **ADR-001..041 all ACCEPTED.** No PROPOSED ADRs remain. Operator-approval moment 2026-04-27: eight ADRs flipped en bloc (ADR-030/033..039). M2-IB.2 (2026-04-28): ADR-031 ACCEPTED. M2-IB.3-prereq (2026-04-28): ADR-040 ACCEPTED. M2-IB.3a-resolved (2026-05-01): ADR-032 ACCEPTED (instrument resolution validated by IB Paper handshake; CAC.PA → conId=11183823); ADR-041 ACCEPTED (Yahoo-suffix translation in IB resolver — refines ADR-032). | Claude record, Oleg approve | continuous |
| **KB-11** | [`docs/decisions/OPEN_QUESTIONS.md`](./docs/decisions/OPEN_QUESTIONS.md) | DRAFT v0.3 (2026-04-27) | OQ-001..030 catalogued. **13 RESOLVED-BY-ADR** (013, 014, 015, 016, 018, 019, 021, 022, 024, 025, 026, 027, 030); 1 RESOLVED-by-finding (017); 4 OPEN (012, 023, 028, 029); 11 IN_DISCUSSION (001–011, 020). | shared | continuous |
| **KB-12** | [`docs/GLOSSARY.md`](./docs/GLOSSARY.md) | DRAFT v0.1 (2026-04-26) | Extracted from REQUIREMENTS §17 + accumulated terms (archetype, ADR, parity envelope, parity diagnostic, parity residual, NDJSON tape, OPRA, SMART, TIF, TKAN, tradable proxy, etc.). Now SSOT for terminology. | Claude | continuous |
| **KB-13** | [`docs/kb/companion_projects.md`](./docs/kb/companion_projects.md) | DRAFT v0.1 (2026-04-26) | btest = primary dependency (blive imports engines + DSL). harp = paper, indirect via deferred A1 strategy. pt-liqadj = independent, bond focus. ForgeFolio = monitoring, possibly post-M8 read-only integration (raised OQ-023). b-autobot = empty placeholder. equities/smim/* = research-only, UK-LC/UK-MC candidate post-M8. | Oleg primary, Claude assist | REQUIREMENTS |
| **KB-14** | Claude memory `~/.claude/projects/.../memory/` | STABLE | User profile, feedback, project context that persists across conversations. Already maintained. | implicit | continuous |
| **KB-15** | `docs/kb/parity_methodology.md` | MISSING | How the parity diagnostic actually works: replay engine, position seeding, residual decomposition. Loadbearing for REQUIREMENTS §8; can wait until M7 design but worth a stub now. | Claude | DESIGN (M7) |
| **KB-16** | [`docs/kb/ig_capability_matrix.md`](./docs/kb/ig_capability_matrix.md) | DRAFT v0.1 (2026-04-27) | Connectivity (REST + Lightstreamer; demo + live URLs), account types (CFD / spread bet / share dealing), asset classes, order types (`MARKET`/`LIMIT`/`STOP`), TIFs (`EXECUTE_AND_ELIMINATE` / `FILL_OR_KILL` / `GOOD_TILL_CANCELLED` / `GOOD_TILL_DATE`; mapping from blive's `TimeInForce` enum), routing (n/a — IG is the venue), market hours, multi-currency, 3-step REST auth + 6h/24h session token TTL + no daily restart. STABLE flip when M2-IG.3 read-side adapter has exercised these surfaces against IG demo. | Claude | REQUIREMENTS, DESIGN |
| **KB-17** | [`docs/kb/ig_pacing_spec.md`](./docs/kb/ig_pacing_spec.md) | DRAFT v0.1 (2026-04-27) | Per-bucket REST rate limits (general 30/min, trading 60/min, historical-prices 40/min); Lightstreamer subscription budget (40 concurrent); session token lifecycle (6h demo / 24h live; refresh-token; idle timeout 6 min); operational events (no daily restart cf. IB; weekend close; IG maintenance windows); IG error codes at the pacing boundary + adapter typed-exception hierarchy (`IGAuthError`, `IGSessionExpired`, `IGRateLimited`, `IGOrderRejected`, …); concrete adapter budget defaults table consumed by [ADR-038](./docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031). STABLE flip when [G3-IG throttle test](./TASK_REGISTRY.md) has run against IG demo. | Claude | REQUIREMENTS, DESIGN |

---

## 3. Inventories (INVs)

Exhaustive lists in well-defined categories. Each lives at `docs/inv/<name>.md` and is expected to be machine-checkable (an automated test asserts the inventory matches code).

| Id | File | Status | Items | Needed by |
|----|------|--------|-------|-----------|
| **INV-1** | [`docs/inv/strategies.md`](./docs/inv/strategies.md) | DRAFT v0.1 (2026-04-26) | 9 strategies catalogued; v1 phase per ADR-013; NAV slice TBD per OQ-013. | REQUIREMENTS, DESIGN |
| **INV-2** | `docs/inv/order_types.md` | MISSING | MKT, LMT, MOC, LOC, STP, STP_LMT, OPG, IOC, FOK + IB support matrix per asset class | REQUIREMENTS, DESIGN |
| **INV-3** | `docs/inv/tif_values.md` | MISSING | DAY, GTC, IOC, FOK, OPG, GTD + venue compatibility | DESIGN |
| **INV-4** | [`docs/inv/risk_checks.md`](./docs/inv/risk_checks.md) | DRAFT v0.1 (2026-04-26) | RC-01..RC-13: leverage, exposure, weight, daily loss, rate limits (per-strategy + global), concentration, stale data, market hours, price sanity, drawdown scaling, model-artefact freshness, kill-switch armed. Order-of-evaluation specified. | REQUIREMENTS |
| **INV-5** | [`docs/inv/domain_events.md`](./docs/inv/domain_events.md) | STABLE v0.3 (2026-05-01) | 17 event topics catalogued with payload, emission rule, consumer set, milestone. M0+M1+M2-IB.3b-i implemented: order.*, broker.connection, risk.breach, account.update, artefact.freshness_warning. `DomainEvent = OrderEvent \| ConnectionStatus \| RiskBreach \| AccountUpdate \| ArtefactFreshnessWarning`. M4/M5/M7 events remain forward-planned. | DESIGN |
| **INV-6** | [`docs/inv/ports_adapters.md`](./docs/inv/ports_adapters.md) | STABLE v0.3.1 (2026-04-28) | 6 Ports (Broker, MarketData, Clock, Persistence, Alert, EventBus). M0+M1 adapters live: PaperBroker (incl. replace), PaperMarketData, InMemoryPersistence, InMemoryEventBus, Sim/WallClock, LogAlert. **v0.3 (M2-IG.2)**: §2.1/§2.2 grew IG read+write rows + explicit PARKED markers on IB/EODHD; §3 references [ADR-034](./docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) + new `Broker registry isolation` import-linter contract; new §3.1 catalogues `blive.adapters.shared.*` cross-cutting modules (rate limiter + credentials). **v0.3.1 (M2-IB.1)**: PARKED markers removed from IB/EODHD rows (M2-IB ACTIVE); IG rows MISSING → DRAFT (architectural surface; bridge-paused, never wire-validated per RETRO-M2-IG). Port Protocol surfaces unchanged. | DESIGN |
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
| **DD-1** | [`docs/dd/domain_objects.md`](./docs/dd/domain_objects.md) | STABLE v0.2 (2026-04-27) | 11 types: Instrument, Bar, Trade, Order, Fill, OrderEvent, Position, AccountSnapshot, OrderUpdate, ConnectionStatus, BrokerEvent (alias). Plus 7 enums (OrderSide/Type/TIF/State/EventKind, AssetClass, Severity) and the `Tradability` literal alias (`spot`/`cfd`/`spread_bet`) added at v0.2 per [ADR-037](./docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet). Field-level invariants enforced in `__post_init__`. | DESIGN |
| **DD-2** | [`docs/dd/event_schemas.md`](./docs/dd/event_schemas.md) | DRAFT v0.2 (2026-05-01) | Field-level for `OrderEvent` / `ConnectionStatus` (M0), `RiskBreach` (M1), `AccountUpdate` (M2-IB.3b-i; per ADR-033), `ArtefactFreshnessWarning` (M2-IB.3b-i; per ADR-022). All implemented in `blive.domain.events`. M4/M5/M7 events catalogued in INV-5 but not yet detailed. | DESIGN |
| **DD-3** | [`docs/dd/config_schemas.md`](./docs/dd/config_schemas.md) | DRAFT v0.2 (2026-04-27) | `LiveStrategyConfig` + 6 sub-objects (`LiveOverrides`, `LiveBorrowProvider`, `LiveFinancingProvider`, `LiveKillSwitch`, `ArtefactPaths`, `RiskOverrides`); merge order; worked `tkan_v4_momentum_timing_1x` example. M1 RC subset only; M4-tier RC keys forward-compat-ignored. **v0.2 (M2-IG.2 amendment per ADR-034)**: top-level `broker: Literal["paper","ig","ib"]` (default `"paper"`) + optional per-broker config blocks `paper_config` / `ig_config` / `ib_config`. | DESIGN |
| **DD-4** | `docs/dd/storage_schemas.md` | MISSING | SQLite DDL for every table, indexes, migrations | DESIGN, M4 |
| **DD-5** | `docs/dd/api_schemas.md` | MISSING (eventually OpenAPI) | REST request/response schemas | M6 |
| **DD-6** | `docs/dd/metric_schemas.md` | MISSING | Prometheus metric definitions in code-checkable form | M7 |
| **DD-7** | [`docs/dd/instrument_dictionary.md`](./docs/dd/instrument_dictionary.md) | STABLE v1.0 (2026-05-01) | `Instrument` field-by-field map to IB `Contract`; `AssetClass` → `secType` table; `venue` (MIC) → IB `exchange` table (Phase 1: `XPAR → SBF`); §3.1 Yahoo-suffix → MIC sub-table (per ADR-041); ConID lazy lookup + in-memory cache; ambiguity discipline. **v1.0 (M2-IB.3a-resolved)**: STABLE flip — Phase 1 path empirically validated (CAC.PA → conId=11183823 via probe 2026-05-01). All field-mapping / venue / Yahoo-suffix tables exercised by `IBInstrumentResolver`. | DESIGN |
| **DD-8** | [`docs/dd/ig_instrument_dictionary.md`](./docs/dd/ig_instrument_dictionary.md) | DRAFT v0.1 (2026-04-27) | `Instrument` field-by-field map to IG epic; epic taxonomy (`IX.D.{symbol}.{mode}.IP` family + KC, CS, CC, etc.); `AssetClass × tradability` → IG epic family table (Phase 1: `INDEX × cfd` → `IX.D.CAC40.CASH.IP` guess); epic resolution via `/markets/{epic}` lookup with `/markets?searchTerm=…` fallback; per-instrument precision lookup consumed by Sizer per [ADR-037](./docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet). Substrate for [ADR-039](./docs/decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd); STABLE flip on first successful resolution against IG demo at M2-IG.3. | DESIGN |

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
| **RETRO-M2-IG** | [`docs/retros/M2-IG_retrospective.md`](./docs/retros/M2-IG_retrospective.md) | STABLE v1.0 (2026-04-28) | M2-IG bridge (G3-IG NOT_REACHED — operator-driven close, not gate failure) | IG bridge close at architectural surface: ~2 sessions delivered M2-IG.1 substrate + M2-IG.2 cross-cutting infra + M2-IG.3 read side + M2-IG.4 minimum-viable submit; 359 tests; 7 tags. ADR-030/033/034..039 ACCEPTED; ADR-031/032 stay PROPOSED for M2-IB. M2-IG.5 strategy run + production Lightstreamer wrapper DEFERRED (no scheduled revival). Phase 1 strategy reverts to ADR-021 ETF on IB Paper. Recommendations §"NEXT_PROMPT v0.4" maps M2-IG file structure 1:1 onto M2-IB equivalents. |

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
5. ~~**M2-IB substrate phase**~~ ✓ Committed 2026-04-27 at `M2-substrate-IB.checkpoint` (ADR-030..033 PROPOSED; DD-7/DD-2/KB-8 DRAFT; KB-2/KB-3 v0.1.1 review pass).
6. ~~**M2-IB execution** — PARKED 2026-04-27 pending operator's IB Paper account reopening. Resumes when IB account ready and M2-IG bridge has stabilised.~~ **Superseded by item 13** (M2-IB unparked 2026-04-28; IB Paper account commissioned 2026-04-28, enabled 2026-04-29). Historical record kept for traceability.
7. ~~**M2-IG.1 batch 1 substrate**~~ ✓ Committed 2026-04-27 at `M2-IG.1-batch1` (ADR-034 multi-broker registry, ADR-035 secrets handling, TASK_REGISTRY v0.2 milestone restructure).
8. ~~**M2-IG.1 batch 2 substrate**~~ ✓ Committed 2026-04-27 at `M2-IG.1-batch2`.
9. ~~**M2-IG.2 cross-cutting infra code**~~ ✓ Committed 2026-04-27 at `M2-IG.2-complete` (rate limiter + credentials + broker_registry + DD-1/DD-3/INV-6/KB-8 amendments + new import-linter contract + secrets/ scaffolding).
10. ~~**M2-IG.3 read side**~~ ✓ Committed 2026-04-28 at `M2-IG.3-readside-complete` (IGClient + IGInstrumentResolver + IGBroker read + IGMarketData REST + Lightstreamer abstraction; production wrapper deferred).
11. ~~**M2-IG.4 minimum-viable submit**~~ ✓ Committed 2026-04-28 at `M2-IG.4-market-submit` (IGBroker.submit MARKET path; cancel/replace deferred to working-order Phase 2 needs).
12. ~~**M2-IG.5 strategy run + RETRO-M2-IG**~~ ⚠ **Bridge closed 2026-04-28 at architectural surface**: retro half done at [`docs/retros/M2-IG_retrospective.md`](./docs/retros/M2-IG_retrospective.md); strategy-run half DEFERRED with no scheduled revival (operator pivoted to M2-IB resumption with the IB Paper account becoming available 2026-04-29). Production Lightstreamer wrapper, ig_pipeline.py, 5-day demo run all parked.
13. **M2-IB resumption (current active path)** — sub-milestones M2-IB.1 (substrate at `M2-substrate-IB.checkpoint`) / .2 (IBClient + IBCredentials) / .3 (IBInstrumentResolver + IBBroker read + IBMarketData) / .4 (write side + reconciliation, optionally consolidated with M3) / .5 (strategy run on IB Paper for ≥ 5 trading days + RETRO-M2-IB). Mirror M2-IG file structure 1:1 per [RETRO-M2-IG §"Recommendations"](./docs/retros/M2-IG_retrospective.md#recommendations-for-next_promptmd-v04-m2-ib-resumption). Reuse `blive.adapters.shared.{rate_limiter, credentials}` + `runtime.broker_registry` unchanged. ADR-031 + ADR-032 flip PROPOSED → ACCEPTED on first IB exercise; DD-7 / KB-2 / KB-3 STABLE flip on first IB Paper handshake. See [`NEXT_PROMPT.md`](./NEXT_PROMPT.md) v0.4 for the kickoff prompt.
    - ~~**M2-IB.1 — Substrate verification.**~~ ✓ Committed 2026-04-28 at tag `M2-IB.1-substrate-verified` (INV-6 STABLE v0.3.1; PARKED markers removed; IG rows MISSING → DRAFT-architectural; CONTEXT_INVENTORY §10 item 6 superseded).
    - ~~**M2-IB.2 — IBClient + IBCredentials.**~~ ✓ Committed 2026-04-28 at tag `M2-IB.2-client-credentials` (`blive.adapters.ib.{credentials, client, rate_limiter, __init__}` + 34 unit tests against `AsyncMock(spec=ib_async.IB)`; ADR-031 PROPOSED → ACCEPTED; KB-10 v0.9 → v0.10).
    - ~~**M2-IB.3-prereq — operator-side closure.**~~ ✓ Closed 2026-05-01 at tag `M2-IB.3-prereq-confirmed`. ADR-040 (Phase 1 deployment target = Windows native IB Gateway) ACCEPTED 2026-04-28. `~/.blive/secrets/ib.env` populated by operator. `scripts/probe_ib_handshake.py` ran clean — connected to IB Paper Gateway in 0.53s (well under the G3-IB 5s target); rate limiter consumed + refilled correctly; clean disconnect. The wire is alive.
    - ~~**M2-IB.3a — IBInstrumentResolver (architectural surface).**~~ ✓ Tag `M2-IB.3a-resolver` 2026-05-01. `IBInstrumentResolver` shipped per DD-7 §5 v0.2.
    - ~~**M2-IB.3a-resolved — wire-level validation + substrate flips.**~~ ✓ Tag `M2-IB.3a-resolved` 2026-05-01. Resolve probe ran cleanly against IB Paper (CAC.PA → conId=11183823 in 0.04s; cache hit 0ms). Surfaced + fixed: IB rejects EODHD/Yahoo-style `.PA` suffixes — added Yahoo-suffix translation table per [ADR-041](./docs/decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver) (XPAR/.PA, XLON/.L, XETR/.DE, XAMS/.AS). Substrate flips: ADR-032 PROPOSED → ACCEPTED; ADR-041 PROPOSED → ACCEPTED (same-session); DD-7 v0.2 DRAFT → v1.0 STABLE; KB-10 v0.11 → v0.12 (no PROPOSED ADRs remain).
    - ~~**M2-IB.3b-i — IBBroker read methods.**~~ ✓ Tag `M2-IB.3b-i-broker-read` 2026-05-01. `IBBroker(client, resolver, clock)` ships with connect/disconnect (auto-subscribes via `connectAsync`'s internal `reqAccountUpdatesAsync`), positions / account_snapshot / open_orders, events() iterator emitting `ConnectionStatus`. `submit/cancel/replace` raise `NotImplementedError` (M2-IB.4). Wire-level probe ran clean against IB Paper: equity=£1,000,177 (GBP-denominated UK paper account); 0.51s connect+initial-batch; rate-limiter usage as designed. M2 event types (`AccountUpdate`, `ArtefactFreshnessWarning`) implemented in `blive.domain.events`; INV-5 v0.3, DD-2 v0.2. **30s diff-suppress timer for AccountUpdate emission per ADR-033 deferred** to a small follow-up commit.
    - **M2-IB.3b-ii — IBMarketData.** Next. `historical_bars` via `reqHistoricalDataAsync`; `subscribe_bars` via `reqMktData`. Will surface KB-2 §7 market hours + KB-3 §2 historical pacing + KB-3 §3 market-data tiers. KB-2 / KB-3 STABLE flip likely lands here or at M2-IB.4 close (after enough §1-§9 surface coverage).
    - **M2-IB.4 — IBBroker write side.** Blocked on M2-IB.3b-ii. Will surface ADR-033 30s diff-suppress timer + INV-14 (IB error codes) MISSING → DRAFT as observed-rejects accumulate.

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
