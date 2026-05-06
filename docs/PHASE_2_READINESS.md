---
id: PHASE_2_READINESS
title: Phase 2 Readiness Audit
status: DRAFT
owner: shared
last_reviewed: 2026-05-06
version: 0.1
sources:
  - docs/PHASE_1_READINESS.md
  - docs/retros/M2-IB_retrospective.md
  - TASK_REGISTRY.md
  - CONTEXT_INVENTORY.md
depends_on:
  - RETRO-M2-IB
  - PHASE_1_READINESS
referenced_by: []
---

# Phase 2 Readiness Audit

## Purpose

A one-time gate document. Before drafting the M3 / Phase 2 plan,
this audit checks whether we have enough substrate to plan well,
and identifies what specifically blocks or merely informs the
planning. Mirrors [`PHASE_1_READINESS`](./PHASE_1_READINESS.md) in
shape; informed this time by the *real* outcomes of M2-IB rather
than the paper-clean architectural state at M0 entry.

**Wall-clock state**: as of the `M2-IB.6-close` commit on
2026-05-06. The closing retrospective is
[RETRO-M2-IB v1.0](./retros/M2-IB_retrospective.md) — the
load-bearing input here. Per
[CONTEXT_PROTOCOL §8.3.2](../CONTEXT_PROTOCOL.md), this audit is
the **second** of the three phase-boundary sessions; it does
**not** draft the M3 plan.

## Conventions

Status per dimension: ✓ READY · ⚠ PARTIAL · ✗ BLOCKING.

The question being asked is: **can we draft a credible M3 / Phase
2 plan today, or does something have to be settled first?**

---

## Cross-cutting summary — five questions that gate the M3 plan-drafting session

These are the questions whose answers become the *agenda* of the
plan-drafting session, not its output. None of them is resolved
here.

1. **OQ-031 sequencing.** Does M3 *resolve* [OQ-031](./decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account)
   (the PMA-bound deployment trade-off) as a Phase 1 live-cutover
   precondition, or does M3 run an empirical paper-mode window
   that *informs* a later resolution? The four resolution options
   in OQ-031 (accept the constraint / pursue Pro Client / substitute
   non-leveraged leg / restructure as passive-limit-only) imply
   different M3 work scopes.
2. **Empirical fill-rate window scope.** What minimum paper-mode
   trading-day count produces statistically meaningful fill-rate
   data on QQL3 given the [INV-14 v0.7](./inv/ib_error_codes.md)
   evidence that PMA cap binding is regime-dependent on the
   leveraged equity leg? (RETRO-M2-IB §"Recommendations" suggested
   1–2 trading weeks; the plan-drafting session pins the number.)
3. **EODHD-vs-IB unit-of-quote reconciliation timing.** Does M3
   ship the QQL3 10× price-discrepancy reconciliation
   (M2-IB.6.2c side-finding) as M7 parity preparation, or defer
   it to M7 proper? The discrepancy currently undersizes positions
   10× and pre-empts IB warning 2161 with IB error 110 ("price not
   in allowed range") at LMT computation time.
4. **Strategy-slot scope through Phase 1 deployment.** Does M3
   stay single-strategy on A3 (the operator-chosen Phase 1
   candidate per [ADR-043](./decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)),
   or invite A1 (`xsec_momentum_long_short_sp500`) / A1a
   (`lagging_indecies`) as parallel candidates? This shapes whether
   Phase 2 entry needs the multi-strategy NAV-allocation question
   ([OQ-010](./decisions/OPEN_QUESTIONS.md#oq-010--capital-allocation-explicit-per-strategy-nav-slice-or-shared-account))
   answered earlier than its M4 default.
5. **Phase 2 substrate prerequisites.** Which Phase 2 / M4+
   artefacts (KB-7 `failure_modes` MISSING, KB-15 `parity_methodology`
   MISSING, full RC-01..RC-08 catalogue, DD-4 `storage_schemas`
   MISSING for SQLite, INV-8 metrics, INV-9 alerts) must be at
   least DRAFT before Phase 2 entry, vs land inside their owning
   M4+ milestone?

---

## 1. Strategy & universe — ⚠ PARTIAL (deployment-decision-gated)

- **READY**
  - A3 (`triple_lev_sma_filter_dsl`) wire-validated end-to-end on
    IB Paper (first FILL: IBTM 19 × £128.5 on 2026-05-06).
    [ADR-043](./decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)
    ACCEPTED.
  - PRIIPs-compliant tradable universe codified: `QQL3` /
    `IBTL` / `IBTM` per
    [ADR-047](./decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043);
    signal-only `QQQ` / `TLT` retained.
  - Multi-instrument pipeline (`run_ib_multi_pipeline`) +
    `LongShortPortfolio` btest dispatch wire-validated per
    [ADR-044](./decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043) +
    [ADR-045](./decisions/DECISIONS.md#adr-045--longshortportfolio-btest-dispatch-extends-adr-030).
  - LSE-ETF SMART routing convention codified:
    [ADR-048](./decisions/DECISIONS.md#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046)
    ACCEPTED; [DD-7 v1.3](./dd/instrument_dictionary.md) §3 split
    by `asset_class`.
- **GAPS**
  - Strategy regime profile shifted: no UK-listed 3× US-Treasury
    UCITS exists, so the bond leg drops 3× → 1× under ADR-047.
    Backtest CAGR / Sharpe / MDD do **not** carry forward; the
    M7 parity envelope re-derives.
  - QQL3 leg has a regime-dependent fill profile under the PMA
    cap ([INV-14 v0.7](./inv/ib_error_codes.md), warning 2161):
    fills only when the market mean-reverts to the cap level.
    The intended trend-following profile is partially inverted.
  - A1 (`xsec_momentum_long_short_sp500`) and A1a (`lagging_indecies`)
    not wire-exercised against IB; not even substrate-validated
    for IB-side instrument resolution.
- **BLOCKED**
  - [OQ-031](./decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account)
    OPEN; operator-deferred to M3 at M2-IB.6 close. Until
    resolved (or accepted), the strategy's effective execution
    profile on the leveraged equity leg is regime-dependent.
- **Phase 2 entry question.** At what point does Phase 2 entry
  require OQ-031 *resolved* (full deployment-mode commitment)
  versus *orthogonal* (Phase 2 = post-Phase-1 expansion path; OQ-031
  lives entirely in Phase 1 deployment scope and Phase 2 inherits
  whichever option was chosen)?

---

## 2. Data feeds — ⚠ PARTIAL (parity envelope gap surfaced)

- **READY**
  - EODHD daily refresh wired for the 5-ticker bundle
    (`scripts/refresh_eodhd_signals.py`); broker-agnostic
    credentials via `~/.blive/secrets/eodhd.env` per
    [ADR-035](./decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).
  - Hybrid data routing (per-instrument, per-frequency) codified
    in [ADR-017](./decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing).
  - `IBMarketData` adapter wire-validated for historical bars
    (US ETFs via delayed-daily tier; KB-3 §2 pacing exercised).
- **GAPS**
  - **EODHD-vs-IB QQL3 10× price discrepancy** (M2-IB.6.2c
    side-finding): EODHD reports ~$383, IB reference ~$39 — likely
    a recent reverse-split or EODHD unit-of-quote convention.
    Strategy sizing uses EODHD's price → undersized 10× in actual
    IB-dollar terms; LMTs computed from EODHD close × multiplier
    pre-empt IB error 110 before warning 2161 fires. Not yet
    catalogued in INV-14 (it's an EODHD-side issue, not an IB
    error code).
  - No live IB market-data subscription — strategy lacks a live
    reference price for sizing / LMT computation.
  - LSE-ETF subscription tier for live data not acquired (M2-IB.5
    surfaced the SBF case; LSEETF is the equivalent here).
- **BLOCKED**
  - Operator decision on EODHD vs IB live-data subscription cost
    vs convenience trade-off.
  - Reverse-split detection / handling on the EODHD side is out
    of blive scope but affects sizing.
- **Phase 2 entry question.** Does Phase 2 entry require the
  EODHD unit-of-quote convention reconciled to IB reference (M7
  parity infrastructure pre-empted in M3), or is it acceptable to
  document the divergence and defer reconciliation to M7 proper?

---

## 3. Engine surface — ✓ READY (for A3 family; ⚠ PARTIAL for end-of-day MOC/LOC strategies)

- **READY**
  - `OrderType.ADAPTIVE_MKT` (IBALGO Adaptive) shipped per
    [ADR-049](./decisions/DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding);
    per-symbol `order_type_by_symbol` override on
    `run_ib_multi_pipeline`.
  - Multi-instrument pipeline wire-validated; per-symbol routing
    correct (no cross-instrument confusion in M2-IB.6 wire runs).
  - IBBroker FSM event emission wire-validated across SUBMITTED →
    ACCEPTED → CANCELED / REJECTED / FILLED via both
    `trade.statusEvent` and global `ib.errorEvent` channels
    ([INV-14 v0.7](./inv/ib_error_codes.md) §"Reason-extraction
    taxonomy").
  - PaperBroker round-trip green from M0; broker registry
    ([ADR-034](./decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004))
    supports paper / IB / IG dispatch.
- **GAPS**
  - Order types catalogue is `MKT` / `LMT` / `ADAPTIVE_MKT` only;
    no `MOC` / `LOC` / `OPG` / `STP` / `STP_LMT` / `IOC` / `FOK`
    for end-of-day rebalance or stop-driven strategies. INV-2
    (order types) still MISSING per CONTEXT_INVENTORY §3.
  - INV-3 (TIFs) MISSING; only `DAY` observed in wire runs.
  - `IBBroker.replace()` raises `NotImplementedError` (M2-IB.4b
    deferred). Phase 2 candidates that modify in-flight orders
    would need it.
- **BLOCKED**
  - None — the gaps land inside their own milestones when
    triggered by a strategy that needs them.
- **Phase 2 entry question.** Does Phase 2 require any new order
  types (`MOC`/`LOC`/`OPG` for end-of-day rebalance, or working-order
  modification via `replace()`), or is the current
  `MKT`/`LMT`/`ADAPTIVE_MKT` surface sufficient given that the
  candidate strategies (A3, A1, A1a) all rebalance daily at the
  open per `signal_delay_bars=1`?

---

## 4. Risk engine — ⚠ PARTIAL (M1-subset only; calibration data still pending)

- **READY**
  - RC-08 (stale data) / RC-09 (market hours) / RC-12 (artefact
    freshness) / RC-13 (kill-switch) implemented and exercised.
  - RiskEngine no-bypass enforced via import-linter contract per
    [ADR-008](./decisions/DECISIONS.md#adr-008--riskengine-no-bypass-architectural-enforcement) +
    [ADR-004](./decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement).
  - **Zero breaches across all four M2-IB.6 wire runs** — clean
    operational signal.
- **GAPS**
  - RC-01 (gross leverage) / RC-02..RC-07 (exposure / weight / daily
    loss / per-strategy + global rate limits / concentration) not
    implemented — full catalogue at [INV-4](./inv/risk_checks.md).
  - RC-10 (price sanity) not implemented — would have caught the
    EODHD 10× discrepancy at sizing time, before IB error 110.
  - RC-11 (drawdown scaling) not implemented.
  - Threshold calibration vs. actual P&L still post-M3 per
    [PHASE_1_READINESS §5](./PHASE_1_READINESS.md).
- **BLOCKED**
  - Calibration data needs the empirical paper-mode window M3
    will produce.
- **Phase 2 entry question.** Does Phase 2 require the full
  RC-01..RC-08 catalogue active (M4 deliverable), or does the
  M1-subset (RC-08/09/12/13) stay sufficient given that OQ-031's
  regime-dependent fill profile already constrains the QQL3 leg's
  exposure naturally?

---

## 5. Reconciliation (M5 territory) — ✗ BLOCKING for live cutover, ⚠ PARTIAL acceptable for paper

- **READY**
  - `IBBroker.connect()` invokes `reqAccountUpdatesAsync` — basic
    startup snapshot.
  - `AccountUpdate` 30 s diff-suppress emission timer per
    [ADR-033](./decisions/DECISIONS.md#adr-033--accountupdate-emission-timer-30s-diff-suppress)
    wire-validated.
  - Crash-only design ([ADR-009](./decisions/DECISIONS.md#adr-009--crash-only-design-restart-path--cold-start-path))
    means restart = cold-start with reconciliation on connect;
    architectural shape is correct.
- **GAPS**
  - No continuous reconciliation loop (M5 deliverable).
  - No persistent state — `InMemoryPersistence` only; SQLite
    (per [ADR-006](./decisions/DECISIONS.md#adr-006--sqlite-for-persistence-in-v1) +
    DD-4 `storage_schemas` MISSING) is the M4 cut.
  - Daily 23:45 ET TWS-restart handled by operator-managed
    manual relogin per
    [ADR-040](./decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway);
    not first-class in code.
  - KB-7 (`failure_modes`) MISSING — chaos-test catalogue was an
    M3 deliverable in the v0.1 plan but not yet authored.
  - **Mixed-currency P&L reconciliation** (RETRO-M2-IB
    Recommendation §4): QQL3 USD + IBTL/IBTM GBP-hedged
    combination needs an account-snapshot smoke during a paper-mode
    run with both legs at non-zero positions; M2-IB exercised the
    fields synthetically.
- **BLOCKED**
  - M5 work is forward-planned per TASK_REGISTRY M4+ sketch.
- **Phase 2 entry question.** Does Phase 2 require M5
  reconciliation in scope (continuous loop + persistent state +
  daily-restart handling + KB-7 chaos catalogue) before live
  cutover, or is paper-mode-with-process-restart-on-disconnect
  still acceptable for the deployment-decision window M3 produces?

---

## 6. Operations / observability — ⚠ PARTIAL (M7-deferred for the full stack)

- **READY**
  - `ConnectionStatus` / `ArtefactFreshnessWarning` / `AccountUpdate`
    / `RiskBreach` event types implemented per [INV-5](./inv/domain_events.md)
    + [DD-2 v0.2](./dd/event_schemas.md).
  - `IBBroker` subscribes to both `trade.statusEvent` and global
    `ib.errorEvent` channels ([INV-14 v0.7](./inv/ib_error_codes.md)
    §"Reason-extraction taxonomy") — load-bearing fix from M2-IB.6.2.
  - Daily NDJSON trade tape *concept* per REQUIREMENTS §6.3.
- **GAPS**
  - Daily NDJSON trade tape unverified at scale (M5 / KB-7
    territory).
  - No structured logging stack (M4 deliverable).
  - INV-8 (metrics) MISSING; INV-9 (alerts) MISSING.
  - No Prometheus / Grafana; no Web UI (M6 / M7 deliverables).
  - No fill-rate dashboard — load-bearing for empirical OQ-031
    measurement during M3 paper-mode window.
- **BLOCKED**
  - M6 / M7 deliverables forward-planned per TASK_REGISTRY M4+
    sketch.
- **Phase 2 entry question.** What observability is *load-bearing*
  for Phase 2 entry (e.g., fill-rate dashboard for OQ-031;
  mixed-currency P&L visibility) versus nice-to-have (full
  Prometheus / Grafana stack), and which subset must M3 ship as a
  precondition for the OQ-031 decision?

---

## 7. Regulatory / compliance — ⚠ PARTIAL (PRIIPs covered; CFD / cross-exchange surfaces not yet)

- **READY**
  - PRIIPs / KID reach catalogued in [KB-9 §5.5](./kb/uk_regulatory.md);
    Phase 1 universe substituted per
    [ADR-047](./decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043).
  - HMRC trade-by-trade record requirement (5+ years) noted in
    KB-9.
  - MiFID-II audit-trail shape satisfied by event-log + hash-chained
    audit (KB-9).
  - Deployment target codified: Windows native IB Gateway per
    [ADR-040](./decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway).
- **GAPS**
  - Trading-vs-investment classification awaiting professional
    confirmation (KB-9 — operator-side, off-blive).
  - No CFD-specific section in KB-9 — relevant only if Phase 2
    reactivates the IG bridge or introduces another CFD broker.
  - Cross-exchange / non-UK-account surfaces not catalogued.
  - MiFID II Professional Client classification path not pursued
    (per ADR-047 §"Alternatives Considered" item 2; OQ-031 Option
    2). Operator declined at M2-IB.6.1; revisit if OQ-031 forces
    it.
- **BLOCKED**
  - Operator's accountant / lawyer review (off-blive).
  - Pro Client classification decision (operator).
- **Phase 2 entry question.** Are there other regulatory surfaces
  Phase 2 introduces (cross-exchange routing? CFD via reactivated
  IG adapter? non-UK-account scenarios? MiFID II PCC classification
  if OQ-031 → Option 2?) that need pre-flight diligence beyond what
  KB-9 §5.5 covers today?

---

## 8. OQs that gate Phase 2 entry — ⚠ PARTIAL (5 OPEN; 1 deferred-to-M3 by operator)

The five OPEN OQs in [KB-11 v0.4](./decisions/OPEN_QUESTIONS.md):

| OQ | Question | Target | Phase-2-entry posture |
|----|----------|--------|----------------------|
| **[OQ-012](./decisions/OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right)** | Parity tolerance bands — are §8 numbers right? | calibrate at M7 | Acceptable to defer; M7 is its native milestone. M3's empirical paper-mode window seeds the calibration data. |
| **[OQ-023](./decisions/OPEN_QUESTIONS.md#oq-023--forgefolio-read-only-integration-with-blive-event-log)** | ForgeFolio read-only integration | post-M8 | Confirmed orthogonal to Phase 2 entry. |
| **[OQ-028](./decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1)** | Agentic memory framework / tooling for L0+L1 | before L0+L1 implementation | Default per OQ-029: post-G4. Phase 2 entry IS the G4-equivalent; needs at least a working answer. |
| **[OQ-029](./decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1)** | When to implement L0+L1 | at or before G4 gate | Same as OQ-028. Default "post-G4" implies decision happens at Phase 2 entry. |
| **[OQ-031](./decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account)** | Phase 1 deployment under PMA-bound retail account | before Phase 1 live cutover (G3-IB → G4) | Operator-deferred to M3. Working default: Option 1 for ~5 trading days then revisit. **Load-bearing for the M3 plan.** |

- **READY**
  - OQ catalogue maintained; all five OPEN OQs have target
    resolution dates and proposed defaults / option lists.
  - Append-only discipline preserved (no edits to past OQ bodies).
- **GAPS**
  - OQ-031 has four resolution options but no decision; the M3
    plan's shape depends on which option dominates.
  - OQ-028 / OQ-029 have proposed defaults but no commitment;
    Phase 2 entry needs at least the default reaffirmed.
- **BLOCKED**
  - OQ-031 — operator deferred to M3.
  - OQ-012 — needs the empirical paper-mode data M3 will produce.
  - OQ-023 — post-M8 by design.
- **Phase 2 entry question.** Of the five OPEN OQs, which must be
  resolved *before* Phase 2 entry (load-bearing for the M3 plan)
  versus which can be carried into Phase 2 substrate work as
  scheduled work items?

---

## Verdict

**For drafting the M3 plan at milestone-level granularity**:
**READY**, conditional on the five cross-cutting questions above
becoming the agenda of the M3 plan-drafting session. The
substrate is internally consistent post-M2-IB.6 close; no
PROPOSED ADRs remain in the working tree; no STABLE artefact has
gone STALE.

**For executing M3 / Phase 1 deployment decision**: **READY for
the empirical paper-mode window** (Recommendation §1 of
RETRO-M2-IB); **NOT READY for live cutover** until OQ-031 is
resolved.

**For drafting Phase 2 (M4..M8) at milestone granularity**:
**NOT READY**. Phase 2 detail depends on M3 outcomes:
- the OQ-031 resolution shapes whether Phase 2 expands to A1 / A1a
  or stays single-strategy on A3;
- the empirical fill-rate / parity envelope from M3 calibrates
  Phase 2's risk-engine thresholds and parity-diagnostic
  acceptance bands;
- the EODHD-vs-IB reconciliation either lands in M3 (M7 work
  pulled forward) or sits in M7 proper, shifting Phase 2's
  milestone weights.

The plan-drafting session can sketch M4..M8 to milestone-headline
level (as the Phase 1 plan did at the equivalent point), but
detailed M4 deliverables should wait until M3 ships its first
empirical artefacts.

## Recommended next steps

1. ✓ **Save this audit** as substrate artefact (this file).
2. **Update [`CONTEXT_INVENTORY.md`](../CONTEXT_INVENTORY.md) §10** —
   tick "Phase 2 readiness audit" complete with link to this
   file; add "M3 plan-drafting session" as the next-front-of-queue
   item; refresh the status banner.
3. **Replace [`NEXT_PROMPT.md`](../NEXT_PROMPT.md) v0.8 → v0.9** —
   kickoff prompt for the M3 plan-drafting session, referencing
   the five cross-cutting questions above as the session's
   agenda.
4. **Re-audit at Phase 2 entry / G4 gate** — confirm what was
   true on 2026-05-06 vs what changed during M3.

## Cross-References

- [PHASE_1_READINESS](./PHASE_1_READINESS.md) — sibling artefact;
  same eight-dimension shape.
- [RETRO-M2-IB](./retros/M2-IB_retrospective.md) — the
  load-bearing input that informed each dimension.
- [TASK_REGISTRY](../TASK_REGISTRY.md) — Phase 1 plan and the
  M4+ sketch this audit feeds.
- [CONTEXT_PROTOCOL §8.3.2](../CONTEXT_PROTOCOL.md) — the
  three-session phase-boundary protocol that frames this audit.
- [KB-11 v0.4](./decisions/OPEN_QUESTIONS.md) — open-questions
  catalogue.
- [INV-14 v0.7](./inv/ib_error_codes.md) — IB error / warning
  catalogue including the four-run PMA-cap validation matrix
  that drives Question 1 + Dimension 1.
- [ADRs 040–049](./decisions/DECISIONS.md) — the M2-IB ADR ladder.

## Changelog

- **v0.1 (2026-05-06)** — initial audit at the gate before the
  M3 / Phase 2 plan-drafting session, per
  [CONTEXT_PROTOCOL §8.3.2](../CONTEXT_PROTOCOL.md). Eight
  dimensions evaluated against the M2-IB.6-close commit state.
  Five cross-cutting questions raised as the agenda for the
  plan-drafting session. No new ADRs raised; no new OQs raised
  (OQ-031 already covers the PMA-cap deployment question).
