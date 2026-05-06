---
id: KB-11
title: Open Questions
status: DRAFT
owner: shared (Oleg primary, Claude assist)
last_reviewed: 2026-05-06
version: 0.4
sources: []
depends_on: []
referenced_by:
  - REQUIREMENTS.md §16 (originally hosted OQ-001..012)
  - KB-5 strategy_taxonomy.md §9 (raised OQ-013..022)
  - CONTEXT_PROTOCOL.md §5 (governs status transitions)
---

# KB-11 — Open Questions

## Purpose

Track every deliberately-unresolved question with target resolution date, options under consideration, and dependency graph. Pulls together what was inline in `REQUIREMENTS.md §16` and what has accumulated in KBs.

## Conventions

Status (per [CONTEXT_PROTOCOL §5.4](../../CONTEXT_PROTOCOL.md#5-decision--question-discipline) plus one transitional state):

- **OPEN** — not yet discussed.
- **IN_DISCUSSION** — being weighed; default options proposed.
- **RESOLVED-PENDING-ADR** — answered in conversation; ADR pending in KB-10 (transitional state used while ADRs are being back-filled).
- **RESOLVED-BY-ADR-NNN** — formally recorded.
- **ABANDONED** — no longer relevant.

OQ ids are stable. Resolved OQs are not deleted; they retain history.

---

## Section A — OQs originating in REQUIREMENTS §16

These were inline in REQUIREMENTS v0.1; externalised here on 2026-04-26.

### OQ-001 — Single process or split (engine + UI)?

- **status:** IN_DISCUSSION (default: single process for v1)
- **opened:** 2026-04-26 · **target_resolution:** M0
- **depends_on:** —
- **Background:** REQUIREMENTS §16. Whether the engine and web UI live in one Python process or are split for ops resilience.
- **Options:** (a) single process — simpler dev, simpler deploy. (b) split (engine + UI as separate processes) — more ops complexity but UI restart doesn't kill engine.
- **Resolution criteria:** revisit if v1 ops experience shows UI bugs taking down trading.

### OQ-002 — Event bus: in-process vs Redis Streams from M1?

- **status:** IN_DISCUSSION (default: in-process; Redis as opt-in)
- **opened:** 2026-04-26 · **target_resolution:** M1
- **depends_on:** —
- **Background:** REQUIREMENTS §16.
- **Options:** (a) in-process asyncio queues — simple, sufficient for v1 single-host. (b) Redis Streams from M1 — durable, multi-process, but operational dependency.
- **Resolution criteria:** Redis becomes mandatory if HA / multi-process is required pre-M8.

### OQ-003 — Persistence: SQLite vs Postgres vs DuckDB?

- **status:** IN_DISCUSSION (default: SQLite v1)
- **opened:** 2026-04-26 · **target_resolution:** M4
- **depends_on:** —
- **Options:** (a) SQLite — single file, easy backup, plenty fast at our event rate. (b) Postgres — concurrent writers, network access, more ops. (c) DuckDB — analytics-friendly columnar, less battle-tested for OLTP.
- **Resolution criteria:** SQLite stays unless event throughput exceeds ~1000/s sustained or multi-host writes are needed.

### OQ-004 — `ib_async` dependency strategy?

- **status:** IN_DISCUSSION (default: pin minor `>=2.1,<2.2`, treat as vendored adapter)
- **opened:** 2026-04-26 · **target_resolution:** M2
- **depends_on:** —
- **Options:** (a) pin minor and depend; (b) vendor-fork; (c) pin patch.
- **Resolution criteria:** if upstream breaks, switch to vendor-fork.

### OQ-005 — Strategy isolation: one process per strategy or one process for all?

- **status:** IN_DISCUSSION (default: one process for all, `Actor`-isolated)
- **opened:** 2026-04-26 · **target_resolution:** M5
- **depends_on:** —
- **Options:** (a) one process; (b) one process per strategy.
- **Resolution criteria:** revisit if any strategy demands > 50% of a core or has incompatible Python deps.

### OQ-006 — Intra-bar trading richness?

- **status:** IN_DISCUSSION (default: rebalance + emergency-exit only at v1)
- **opened:** 2026-04-26 · **target_resolution:** M5
- **depends_on:** OQ-013 (resolved), KB-5 §4 frequency roadmap
- **Options:** (a) v1 = rebalance windows only; (b) v1 = full intra-bar event reactions.
- **Resolution criteria:** richer intra-bar trading is a frequency-roadmap concern; defer until F1+ work begins.

### OQ-007 — FX: real-time conversion vs daily close?

- **status:** IN_DISCUSSION (default: realised FX P&L per fill via IB rate; daily reval at close)
- **opened:** 2026-04-26 · **target_resolution:** M3
- **depends_on:** —
- **Options:** (a) realised per fill + daily reval (current default); (b) live FX feed for intra-day reval.
- **Resolution criteria:** revisit if FX P&L volatility distorts intra-day risk measures.

### OQ-008 — UI auth: shared secret vs local-only vs OAuth?

- **status:** IN_DISCUSSION (default: shared secret + TLS for v1)
- **opened:** 2026-04-26 · **target_resolution:** M6
- **depends_on:** —
- **Options:** (a) shared secret bearer; (b) local-only loopback; (c) OAuth/SSO.
- **Resolution criteria:** OAuth/SSO becomes interesting if more than one operator.

### OQ-009 — `btest` engine reuse: import as library or fork relevant modules?

- **status:** IN_DISCUSSION (default: import; fork only on upstream-break)
- **opened:** 2026-04-26 · **target_resolution:** M1
- **depends_on:** KB-1 btest_dsl_inventory (MISSING)
- **Options:** (a) `pip install -e ../btest` style; (b) vendor specific modules.
- **Resolution criteria:** if `btest` introduces breaking changes faster than `blive` can absorb, switch to vendor.

### OQ-010 — Capital allocation: explicit per-strategy NAV slice or shared account?

- **status:** IN_DISCUSSION (default: explicit slice tracked in `blive`, IB account ground truth)
- **opened:** 2026-04-26 · **target_resolution:** M4
- **depends_on:** OQ-013 (resolved)
- **Options:** (a) explicit slice; (b) shared pot.
- **Resolution criteria:** explicit is safer for risk attribution.

### OQ-011 — CLI alongside web UI?

- **status:** IN_DISCUSSION (default: yes from M6, parity with REST surface)
- **opened:** 2026-04-26 · **target_resolution:** M6
- **depends_on:** —
- **Options:** (a) CLI shipped from M6; (b) REST + curl is enough.
- **Resolution criteria:** ship CLI when first headless ops scenario emerges (typically operator running on a remote box without browser).

### OQ-012 — Parity tolerance bands: are §8 numbers right?

- **status:** OPEN (calibrate from real fills in M7)
- **opened:** 2026-04-26 · **target_resolution:** M7
- **depends_on:** A2 / A3 strategies running in IB Paper for ≥ 30 days
- **Background:** REQUIREMENTS §8 currently has provisional bands (slippage ±5 bps, borrow ±25 bps annualised, financing ±15 bps annualised, parity residual ±15 bps over 5d).
- **Resolution criteria:** observe live fills, fit empirical envelope, replace provisional numbers in REQUIREMENTS.

---

## Section B — OQs raised in KB-5 strategy_taxonomy

### OQ-013 — Which strategies are funded for v1, and what NAV slice?

- **status:** RESOLVED-BY-ADR-013 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** KB-5 §3, §7
- **Resolution:** v1 focus is **ETF and index strategies only**. Single-name SP500 cross-sectional strategies (`xsec_momentum_long_short_sp500`, `harp_quarterly_momentum`, `tiny_momentum_ls`) are catalogued but **deferred to post-M8**. Phased priority codified in [ADR-013](DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only): Phase 1 (M3) A2 → Phase 2 (post-M5) A3 → Phase 3 (post-M7) A1a → Phase 4+ (post-M8) leveraged variants, A3 generalisations, UK equities.
- **Sub-question still open:** NAV slice per strategy is not yet decided; carry forward as part of M3 planning.
- **Cross-references:** [ADR-013](DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only), KB-5 §3, §7, §8.

### OQ-014 — Data source switch from `sfera://` (Bloomberg) to live equivalent?

- **status:** RESOLVED-BY-ADR-014 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** —
- **Resolution:** support **all** data sources (`parquet://`, `sfera://`, `eodhd://`, `ib://`, `yf://`, `fred://`) via the existing clean API abstraction (`btest`'s `data/sources/registry.py` pattern). Each source is a pluggable adapter implementing the `DataSource` protocol; the strategy declares its source URL and the registry resolves it. No source-specific hard-coding above the adapter layer.
- **Cross-references:** [ADR-014](DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction), REQUIREMENTS §5.2, §7.1; KB-5 §6.

### OQ-015 / OQ-018 — ML model training in-process or static artefacts? Artefact lifecycle?

- **status:** RESOLVED-BY-ADR-015 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** architectural assumption is that ML models are **live-trained** eventually. For **v1**, `blive` consumes **static artefacts** produced offline by `btest`. Training itself is out of scope for v1; loader is in scope, trainer is not. Strategy spec records artefact path, build hash, last-trained timestamp; staleness alerts fire on configurable freshness windows.
- **Sub-questions still open:** artefact freshness window defaults; M8+ retraining pipeline owner. Both deferred to M3 / M8 as appropriate.
- **Cross-references:** [ADR-015](DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), KB-5 §2 (A2), §7 (Phase 1).

### OQ-016 — Synthetic leverage via margin or only via leveraged-ETF instruments?

- **status:** RESOLVED-BY-ADR-016 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **support both**. Margin-financed leverage (target_leverage > 1, IB margin, ESTER/SOFR spread on financed half) AND leveraged-ETF instruments (TQQQ, TMF, SPXL, UPRO, SOXL). Choice is per-strategy. Parity envelopes differ per leverage path.
- **Cross-references:** [ADR-016](DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments), KB-5 §2 (A2 leveraged variants, A3), KB-5 §8 (cost parity), OQ-012.

### OQ-017 — Triple Leveraged ETF instrument set?

- **status:** RESOLVED (2026-04-26, by inspection of `triple_leveraged_etf_dsl.ipynb`)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26
- **depends_on:** —
- **Resolution:** `{TQQQ, TMF, IEF}`. TQQQ leg parks in IEF when QQQ < SMA-200 (5% hysteresis re-entry); TMF leg parks in IEF when TLT < SMA-200; otherwise 50/50 across the two risk-on legs. Implemented via `LongShortPortfolio` with empty `short_book`, `MaskSelector`, and `ExternalFactor(per_instrument=True)`. See KB-5 §2 A3.
- **Cross-references:** KB-5 §2 (A3), §3 (strategies table).

### OQ-019 — Live data: EODHD real-time vs IB streaming vs hybrid?

- **status:** RESOLVED-BY-ADR-017 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** —
- **Resolution:** **hybrid**. `MarketDataPort` admits multiple concurrent providers; routing is per-instrument (and possibly per-frequency). Default mapping pending calibration: IB streaming for IB-traded instruments; EODHD real-time / delayed for instruments outside our IB tier; EODHD historical for warm-up / backtest replay. Architecture forbids hard-wiring a single provider above the adapter layer (CONTEXT_PROTOCOL §2.2 / ADR-004).
- **Sub-questions still open:** per-instrument default routing rules — pending calibration in M2.
- **Cross-references:** [ADR-017](DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing), REQUIREMENTS §5.2, KB-5 §6.

### OQ-020 — Multi-currency P&L: real-time vs daily reval?

- **status:** IN_DISCUSSION (REQUIREMENTS §5.4 has working answer: realised FX per fill via IB rate, daily reval)
- **opened:** 2026-04-26 · **target_resolution:** M4
- **depends_on:** —
- **Background:** Earlier OQ-007 in Section A is the same question framed from REQUIREMENTS §16; OQ-020 is the strategy-taxonomy framing. Treat as the same question; resolution applies to both.
- **Resolution criteria:** revisit if FX P&L volatility on multi-currency strategies (A1a global indices, European A2 strategies) distorts intra-day risk attribution.

### OQ-021 — UK equity strategies in scope post-M8?

- **status:** RESOLVED-BY-ADR-018 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **in scope later** — deferred but not abandoned. UK-listed cash equities (LSE-Main / AIM) become candidates post-M8. Likely entry: UK-only A1 cross-sectional from SMIM research universe (`equities/smim/UK-LC` or `UK-MC`).
- **Sub-questions still open:** concrete UK strategy spec — deferred to post-M8 planning.
- **Cross-references:** [ADR-018](DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8), KB-5 §5 (asset classes), KB-13 (MISSING — clarifies smim relationship).

### OQ-022 — Generalise A3 to other leveraged-ETF pairs?

- **status:** RESOLVED-BY-ADR-019 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **yes**. A3 is parameterised by `(risk_on_pair, safe_haven_park, trend_filter, hysteresis)`; `triple_lev_sma_filter_dsl` is one instance. Future instances on roadmap: SOXL/SQQQ (semis), UPRO/SPXU (broad index), cross-sector rotations (XLK/XLF). Engine code from M5 must remain generic — no TQQQ/TMF/IEF specialisations baked into engine. Concrete generalisation deferred to Phase 4+ (post-M8).
- **Cross-references:** [ADR-019](DECISIONS.md#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs), KB-5 §2 (A3), §7 (Phase 4+).

---

## Section B' — Sub-questions raised after parent-OQ resolution

These sub-questions surfaced when the parent decisions (OQ-013, 014, 015, 018) were resolved, or in subsequent KBs (KB-13 ForgeFolio integration). Each carries a proposed default; operator confirmation pending.

### OQ-023 — ForgeFolio read-only integration with blive event log?

- **status:** OPEN
- **opened:** 2026-04-26 · **target_resolution:** post-M8
- **depends_on:** Phase 4+ work
- **Background:** [KB-13](../kb/companion_projects.md#forgefolio--portfolio-monitoring--analysis-pyqt6-gui) raised this. blive produces a daily NDJSON trade tape (REQUIREMENTS §6.3); ForgeFolio is a separate desktop monitoring app reading IB Flex Query independently. Whether they should share the trade-tape feed is a post-v1 question.
- **Options:** (a) keep them independent forever; (b) ForgeFolio reads blive's NDJSON tape on a schedule; (c) blive emits a ForgeFolio-shaped event stream.
- **Resolution criteria:** revisit when ForgeFolio integration becomes operationally desirable.

### OQ-024 — NAV slice for the Phase 1 strategy?

- **status:** RESOLVED-BY-ADR-020 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **5–10% of total account NAV, hard cap 10%**. Combined with RC-07 (single-name notional ≤ 8% of strategy NAV), this caps any single position at ≤ 0.8% of total NAV — conservative for a paper-account technology-validation phase.
- **Cross-references:** [ADR-020](DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10), [TASK_REGISTRY](../../TASK_REGISTRY.md), [INV-4 RC-07](../inv/risk_checks.md).

### OQ-025 — Which CAC ETF proxy for the Phase 1 strategy?

- **status:** RESOLVED-BY-ADR-021 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-014 (RESOLVED-BY-ADR-014)
- **Resolution:** **`CAC.PA` (Lyxor CAC 40 UCITS ETF, distributing share class)** — most liquid CAC tracker on Euronext Paris (XPAR). Price-return tracking; ≈3–4% annual dividend gap vs. CACT (TR index) absorbed into the Phase 1 parity envelope and explicitly logged.
- **Sub-decisions deferred:** whether to retrain TKAN on `CAC.PA` price-return history (would close the gap; out of v1 scope per ADR-015); revisit at G4 gate.
- **Cross-references:** [ADR-021](DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf), [ADR-014](DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction), [KB-5 §3](../kb/strategy_taxonomy.md), [TASK_REGISTRY](../../TASK_REGISTRY.md).

### OQ-026 — TKAN artefact freshness window default?

- **status:** RESOLVED-BY-ADR-022 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-015 (RESOLVED-BY-ADR-015)
- **Resolution:** **30 days hard (RC-12 block); 21 days warning alert**. Conservative for a daily-frequency strategy where retraining is minutes to hours offline. Re-tune from observed retraining cadence after first month of live (paper) operation.
- **Cross-references:** [ADR-022](DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-015](DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), [INV-4 RC-12](../inv/risk_checks.md).

### OQ-027 — TKAN artefact prod location and retraining ownership?

- **status:** RESOLVED-BY-ADR-023 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-018 (RESOLVED-BY-ADR-015)
- **Resolution:**
  - **Path scheme:** `~/.blive/artefacts/{strategy_id}/{model_name}/pred_cache.pkl` (e.g. `~/.blive/artefacts/tkan_v4_momentum_timing/tkan_v4/pred_cache.pkl`).
  - **Hash recording:** SHA256 of artefact in strategy spec snapshot per REQUIREMENTS §5.12.
  - **Retraining:** manual; operator runs btest's `TKAN_v4_train.py` then `scripts/refresh_artefact.py` (M2 deliverable) which copies + checksums + records.
  - **Auto-train pipeline:** out of v1 (consistent with ADR-015).
- **Cross-references:** [ADR-023](DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership), [ADR-015](DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), [REQUIREMENTS §5.12](../../REQUIREMENTS.md), [TASK_REGISTRY](../../TASK_REGISTRY.md).

---

## Section B'' — Agentic-execution layer (raised from ADR-026)

### OQ-028 — Which agentic memory framework / tooling for L0+L1?

- **status:** OPEN (default proposed below; revisit at L0+L1 implementation)
- **opened:** 2026-04-26 · **target_resolution:** before L0+L1 implementation begins
- **depends_on:** ADR-026
- **Background:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) codifies the agentic-execution layer but leaves the choice of framework open. Candidates have different trade-offs in maturity, lock-in, and substrate compatibility:
  - **Custom lightweight agent** — minimal dependency; full control; slow to feature-parity with frameworks; easy to integrate with our markdown substrate.
  - **Letta (formerly MemGPT)** — mature, Python-first, integration cost; designed for general agentic memory rather than disciplined substrate.
  - **Sculptor / ARC** — research-stage; Active Context Management primitives map well to L0; less mature.
  - **Native IDE / harness tooling** (e.g. Claude Code MCP servers, similar) — leverage existing infrastructure; risk of vendor lock; substrate-aware tools become possible without separate framework.
  - **Graph-native first** (Neo4j + Cypher MCP) — skips the markdown-era and goes directly to L4; bigger one-time investment, but L0/L1 become trivial graph queries.
- **Proposed default:** **custom-light for L0** (an agent that just reads `CONTEXT_INVENTORY.md` and walks `depends_on` closures); evaluate Letta or Sculptor for L1+ once L0 is operational and the cost of building the watchdog manually becomes the binding constraint.
- **Resolution criteria:** pick whichever path supports our markdown substrate and gives us L0+L1 in ≤ 2 working sessions of integration. Revisit at G4 gate or earlier if implementation friction is high.
- **Cross-references:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface), [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md).

### OQ-029 — When to implement L0+L1?

- **status:** OPEN (default proposed below; revisit at G4)
- **opened:** 2026-04-26 · **target_resolution:** at or before G4 gate
- **depends_on:** ADR-026; OQ-028 (framework choice)
- **Background:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) sets the direction but does not commit to a milestone. Options:
  - **Concurrent with M3** — split focus; M3 may slip; L0+L1 may benefit from being designed against real M3 substrate state.
  - **New M3.5 milestone** — dedicated layer-0 / 1 work, well-scoped, between M3 and M4.
  - **As part of M5 Reconciliation / ops** — bundles related operational work but pushes the savings later.
  - **After Phase 1 (post-G4)** — leverages M3 outcomes and parity calibration; clean phase boundary.
- **Proposed default:** **post-G4, as a Phase 2 entry concern** — L0+L1 land in a dedicated milestone after Phase 1 closes, leveraging real Phase 1 substrate state to calibrate the integrity watchdog. This keeps Phase 1 manual (acceptable for the small scale) and uses Phase 2's larger scope to motivate the agentic layer's value.
- **Resolution criteria:** revisit at G4. If Phase 1 manual burden is becoming the bottleneck during M2 or M3, accelerate to "concurrent with M3" or "M3.5". Otherwise, post-G4.
- **Cross-references:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface), [TASK_REGISTRY](../../TASK_REGISTRY.md), [OQ-028](#oq-028--which-agentic-memory-framework--tooling-for-l0l1).

### OQ-030 — Which btest interpreter does blive call for `TimingPortfolio` (and other non-LongShort archetypes)?

- **status:** RESOLVED-BY-ADR-030 (2026-04-27)
- **opened:** 2026-04-27 · **target_resolution:** G2 gate
- **depends_on:** [ADR-010](DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import); [KB-1 §6, §7](../kb/btest_dsl_inventory.md)
- **Background:** [ADR-010](DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) commits blive to importing `FactorEngine`, `SignalEngine`, `PortfolioEngine` from btest. M1 work surfaced two facts:
  1. `PortfolioEngine` is a free function `compute_target_weights_for_date()` (not a class), and it only handles `LongShortPortfolio`.
  2. The Phase 1 strategy (`tkan_v4_momentum_timing`) uses `TimingPortfolio`, which btest interprets via `quantdsl_backtest.runners.single_asset.SingleAssetRunner` — a different module that bundles factor evaluation, signal evaluation, and position derivation in one batch interpreter, **not** the three engines named in ADR-010.
- **Options:**
  1. **Call `SingleAssetRunner` from blive's pipeline** for `TimingPortfolio`-based strategies; call `FactorEngine + SignalEngine + compute_target_weights_for_date` for `LongShortPortfolio`-based strategies. Each archetype maps to its native btest interpreter. (Working default for M1.)
  2. **Reimplement TimingPortfolio's logic inside blive** as a streaming-friendly evaluator that sits alongside FactorEngine/SignalEngine. Closer to ADR-010's prose but introduces the very drift ADR-010 was meant to prevent.
  3. **Extend btest's engine package** to expose a `TimingPortfolioEngine` matching the LongShort one. Upstream change; cross-project coordination cost.
- **Proposed default (working answer for M1):** Option 1. The Strategy Loader inspects `strategy.portfolio` type and the M1 pipeline dispatches to the appropriate btest interpreter. ADR-010's spirit — reuse btest's engines, don't fork — is preserved; the prose's "three engines" is a partial enumeration that needs amendment when this OQ resolves.
- **Resolution criteria:** at G2 review, decide whether to (a) amend ADR-010 prose to acknowledge `SingleAssetRunner` and any future archetype-specific interpreters, (b) advocate Option 3 with btest, or (c) keep ADR-010 unchanged and treat the dispatch as an undocumented but stable pattern. Plus: confirm `LongShortPortfolio` archetype works under the same M1 pipeline shape when Phase 3 (`lagging_indecies`) lands at M7.
- **Cross-references:** [ADR-010](DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import); [KB-1 §6, §7](../kb/btest_dsl_inventory.md); [`runners/single_asset.py`](`btest/src/quantdsl_backtest/runners/single_asset.py`); M0 retro recommendation 1; M1 work this session.

### OQ-031 — Phase 1 deployment under PMA-bound retail account

- **status:** OPEN
- **opened:** 2026-05-06 · **target_resolution:** before Phase 1 live cutover (G3-IB → G4 transition)
- **depends_on:** [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049 PROPOSED](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [INV-14 v0.7](../inv/ib_error_codes.md)
- **Background:** The 2026-05-06 LSE-RTH validation runs of `scripts/run_m2ib6_ib_paper.py` empirically confirmed that **IB warning 2161 (Price Management Algo / regulatory disruptive-orders cap) binds structurally** on QQL3 (3× Nasdaq leveraged ETP on LSEETF) for the operator's UK retail IB Paper account. The cap pegs the effective limit to IB's live bid/ask reference; in rising markets, BUY orders capped at the bid don't fill. Tested across raw MKT (10s + 60s waits), `OrderType.ADAPTIVE_MKT` (IBALGO Adaptive — IB's recommended workaround in the warning text), and LMT @ $50 (well above IB ref ~$39 but within allowed-range envelope) — all subject to the cap; 0 QQL3 fills across 16 placeOrders. The `priceManagementOff` order flag is institutional-only. IBTM (1× UCITS Treasury ETF) is unaffected — fills land cleanly. Implication: Phase 1 deployment of A3 has a **regime-dependent fill profile** on its leveraged equity leg — fills happen only when the market mean-reverts to the cap level. In extended uptrends, the strategy spends time long the equity leg without acquiring full position, then is forced to acquire on regime-flips into safe-haven (when ask drops to bid). This is **opposite to the intended trend-following profile**.
- **Options:**
  1. **Accept the constraint as a real-world Phase 1 deployment characteristic.** Document the regime-dependent fill profile in the strategy's risk-and-execution-profile note. M7 parity envelope absorbs the divergence from the article's backtest fill-rate assumptions. Operator monitors fill-rate empirically over the first ~5 trading days of live deployment; if the fill-rate is unacceptable (TBD threshold), revisit. **No code change.**
  2. **Pursue MiFID II Professional Client classification** to enable the `priceManagementOff` order flag (institutional-only opt-out from PMA). Per [ADR-047 §"Alternatives Considered" item 2](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043), this requires meeting wealth / experience / transaction-frequency thresholds. Operator declined at M2-IB.6.1; revisit if Option 1's fill-rate is unacceptable.
  3. **Substitute the leveraged equity leg with a non-leveraged analogue** (e.g. directly hold QQQ via UK-listed UCITS or remove the 3× leverage entirely). Materially changes the strategy's risk profile (1×/1× vs intended 3×/1× post-ADR-047 vs original 3×/3× from the notebook); equivalent to a different strategy. Captured here for completeness; would amend ADR-043 + ADR-047.
  4. **Restructure as a passive-limit-only strategy** that explicitly accepts the PMA cap as the execution model — submits at the cap, accepts the regime-dependent fill rate as the strategy's intended behaviour rather than a constraint. Closer to a mean-reversion strategy than the trend-following A3; would need a fresh ADR + parity envelope.
- **Proposed default (working answer):** Option 1 for the first ~5 trading days of paper-mode validation; revisit the choice based on empirical fill-rate data before live cutover. The architectural surface (M2-IB.6) closes on Option 1 — the cap is a real wire finding that does not block FSM / pipeline validation; the operational decision is downstream.
- **Resolution criteria:** before live cutover (G3-IB → G4 gate). Operator decides between Options 1–4 based on (a) the M2-IB.6 retro's fill-rate evidence, (b) the strategy's empirical regime-bias when the parity envelope re-derives at M7, (c) the operator's own risk tolerance for PMA-bound execution.
- **Cross-references:** [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049 PROPOSED](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [INV-14 v0.7](../inv/ib_error_codes.md); M2-IB.6.2b/c wire-finding (2026-05-06).

---

## Section C — Index by status

### RESOLVED-BY-ADR-NNN (formally recorded in [KB-10](DECISIONS.md))

| OQ | ADR | Title |
|----|-----|-------|
| OQ-013 | ADR-013 | v1 scope: ETF and index strategies only |
| OQ-014 | ADR-014 | Data sources via clean API abstraction |
| OQ-015 | ADR-015 | ML training: live-trained eventually, static artefacts in v1 |
| OQ-016 | ADR-016 | Leverage: support both margin-financed and leveraged-ETF instruments |
| OQ-018 | ADR-015 | (shared resolution with OQ-015) |
| OQ-019 | ADR-017 | Live data: hybrid EODHD + IB streaming |
| OQ-021 | ADR-018 | UK equity strategies deferred to post-M8 |
| OQ-022 | ADR-019 | A3 archetype generalises to other leveraged-ETF pairs |
| OQ-024 | ADR-020 | Phase 1 NAV slice: 5–10% of total, cap 10% |
| OQ-025 | ADR-021 | CAC ETF proxy: `CAC.PA` (Lyxor CAC 40 UCITS ETF) |
| OQ-026 | ADR-022 | TKAN artefact freshness window: 30d hard, 21d warning |
| OQ-027 | ADR-023 | TKAN artefact path and refresh ownership |
| OQ-030 | ADR-030 | Per-archetype btest interpreter dispatch (amends ADR-010) |

### RESOLVED (no ADR needed, factual finding)

OQ-017 — Triple Leveraged ETF instrument set is `{TQQQ, TMF, IEF}`.

### OPEN

| OQ | Question | Target |
|----|----------|--------|
| OQ-012 | Parity tolerance bands | calibrate at M7 |
| OQ-023 | ForgeFolio integration | post-M8 |
| OQ-028 | Agentic memory framework / tooling for L0+L1 | before L0+L1 implementation |
| OQ-029 | Timing of L0+L1 implementation | at or before G4 gate |
| OQ-031 | Phase 1 deployment under PMA-bound retail account | before Phase 1 live cutover (G3-IB → G4) |

### IN_DISCUSSION (have a working default in REQUIREMENTS §16; ADRs not yet written)

OQ-001..OQ-011, OQ-020.

---

## Section D — Maintenance

- New OQs are appended; existing OQs are not deleted.
- Status transitions are recorded inline in the OQ block (date + decider).
- When an ADR lands in KB-10, update the status from `RESOLVED-PENDING-ADR` to `RESOLVED-BY-ADR-NNN`.
- Weekly review per [CONTEXT_PROTOCOL §6.3](../../CONTEXT_PROTOCOL.md#63-review-cadence): scan for stale `IN_DISCUSSION` items past their target resolution date.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. OQ-001..012 externalised from REQUIREMENTS §16. OQ-013..022 captured from KB-5 v0.1.1. 8 RESOLVED-PENDING-ADR after Oleg's 2026-04-26 session, 1 RESOLVED, 1 OPEN, 12 IN_DISCUSSION.
- **v0.1.1 (2026-04-26)** — KB-10 ADR-001..019 landed. Promoted OQ-013, OQ-014, OQ-015, OQ-016, OQ-018, OQ-019, OQ-021, OQ-022 from RESOLVED-PENDING-ADR to RESOLVED-BY-ADR-NNN. Section C status index updated to a 4-state table.
- **v0.1.2 (2026-04-26)** — Phase 1 readiness audit raised OQ-023 (KB-13 ForgeFolio), OQ-024..OQ-027 (sub-questions of resolved OQ-013/014/015/018 that block detailed Phase 1 planning). All carry proposed defaults; operator confirmation pending. New Section B' added.
- **v0.1.3 (2026-04-26)** — Operator confirmed OQ-024..OQ-027. Promoted to RESOLVED-BY-ADR-020 (NAV slice), ADR-021 (CAC ETF proxy), ADR-022 (TKAN freshness window), ADR-023 (TKAN artefact path/ownership). Section C tables updated. G0 gate now passable.
- **v0.1.4 (2026-04-26)** — ADR-026 (agentic-execution layer) added; OQ-028 (memory framework choice) and OQ-029 (implementation timing) raised. New Section B'' for layer-related questions.
- **v0.2 (2026-04-27 / M1 close)** — OQ-030 raised at M1 close (btest interpreter dispatch for non-LongShort archetypes); IN_DISCUSSION pending G2 review.
- **v0.3 (2026-04-27 / M2-IG.1 substrate ACCEPTED batch)** — OQ-030 status flipped IN_DISCUSSION → RESOLVED-BY-ADR-030 alongside the eight-ADR ACCEPTED flip. Section C tables updated. Now: 13 RESOLVED-BY-ADR (013–016, 018, 019, 021, 022, 024–027, 030); 1 RESOLVED-by-finding (017); 4 OPEN (012, 023, 028, 029); 11 IN_DISCUSSION (001–011, 020).
- **v0.4 (2026-05-06 / M2-IB.6.2c)** — OQ-031 raised: Phase 1 deployment under PMA-bound retail account. The M2-IB.6.2b/c LSE-RTH validation runs empirically confirmed that IB warning 2161 (Price Management Algo / regulatory disruptive-orders cap) binds structurally on QQL3 (3× Nasdaq leveraged ETP on LSEETF) for UK retail accounts, regardless of order type (raw MKT, OrderType.ADAPTIVE_MKT, LMT-with-aggressive-offset all subject). 0 QQL3 fills across 16 placeOrders today; IBTM (1× UCITS Treasury ETF) is unaffected. Implication: A3's effective execution profile on the leveraged equity leg is regime-dependent (fills only on flat/down moves). Four resolution options: (1) accept the constraint, monitor empirically; (2) pursue Pro Client classification for `priceManagementOff` opt-out; (3) substitute non-leveraged equity leg; (4) restructure as passive-limit-only. Working default: Option 1 for the first ~5 trading days, revisit pre-cutover. OPEN section grows to 5 (012, 023, 028, 029, **031**).
