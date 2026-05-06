---
id: RETRO-M2-IB
title: M2-IB Retrospective
status: STABLE
owner: Oleg
last_reviewed: 2026-05-06
version: 1.0
sources:
  - TASK_REGISTRY.md M2-IB
depends_on:
  - TASK_REGISTRY
  - RETRO-M2-IG
referenced_by: []
---

# RETRO-M2-IB — M2-IB Retrospective

> **Frozen record.** This file is `STABLE` on first complete write and not edited thereafter. If a future session needs to add context, append a separate `RETRO-M2-IB-addendum.md` rather than modifying this file.

## Date and session(s)

- **Date:** 2026-05-06 (close)
- **Sessions involved:** ~10 sessions across 2026-04-28 → 2026-05-06; daily-cadence working tempo with two paper-mode wire windows (US RTH 2026-05-04, LSE RTH 2026-05-06)
- **Closing milestone:** M2-IB (sub-milestones M2-IB.1 → M2-IB.6)

## Gate status

**G3-IB-A3 status: PASSED at architectural surface.** The "pure-fills" interpretation of G3-IB on the original A2 plan was superseded twice — once by ADR-043 (A2 → A3 strategy switch) and once by ADR-047 (US-domiciled → UK-listed PRIIPs-compliant universe). Final evaluation against the rewritten G3-IB-A3 criteria (TASK_REGISTRY M2-IB.6 §"Exit criteria"):

| Exit criterion | Status | Notes |
|---|---|---|
| 1. Connect to IB Paper Gateway within 5s | ✓ | Validated repeatedly across .3-prereq / .3a / .4a probes; consistently 0.51–0.53s |
| 2. SMART-routed orders for QQL3 / IBTL / IBTM reach ACCEPTED via ADR-048 shape, no error 200 regression | ✓ | Wire-validated 2026-05-06 — all 3 instruments resolve cleanly via SMART/primaryExchange=LSEETF; no error 200 |
| 3. ≥ 2 BUY-then-SELL round trips exercising FILLED across the run window | ⚠ | **Partial.** 1 IBTM fill landed cleanly (BUY 19 @ £128.5); QQL3 fills blocked by IB warning 2161 (PMA cap) — structural for UK retail leveraged ETPs regardless of order type. The architectural FSM path SUBMITTED → ACCEPTED → FILLED is wire-exercised at least once on M2-IB. The fill-rate concern is captured in OQ-031 (deferred to M3); architectural surface is validated |
| 4. Multi-instrument target_weights_series correctly drives per-instrument orders, no cross-instrument confusion | ✓ | Pipeline correctly routes per-symbol (verified across 5-bar smoke + 60s-wait runs); per-symbol `order_type_by_symbol` override added at .6.2c |
| 5. RiskEngine clean — zero breaches across the run | ✓ | All four wire runs: `breaches: 0` |
| 6. INV-14 grows with newly observed LSEETF / UK-retail codes | ✓ | INV-14 v0.5 → v0.7: error 201 (PRIIPs/KID variant + dual-channel reason-extraction taxonomy) + warning 2161 (PMA cap with 4-run validation matrix) |
| 7. RETRO-M2-IB written | ✓ | This file |

## Delivered vs plan

| Plan deliverable | Status | Notes |
|---|---|---|
| 1. ADRs 043 / 044 / 045 / 046 ACCEPTED + KB-5 §7 / INV-1 / DD-7 §3 amendments (M2-IB.6-substrate) | ✓ | Committed 2026-05-02 |
| 2. Multi-instrument `run_ib_pipeline` support (M2-IB.6.1) | ✓ | `run_ib_multi_pipeline` + `IBMultiRunResult` shipped |
| 3. EODHD 5-ticker refresh (M2-IB.6.1) | ✓ | `scripts/refresh_eodhd_signals.py`; tradables revised TQQQ/TMF/IEF → QQL3/IBTL/IBTM per ADR-047 |
| 4. LongShortPortfolio btest dispatch wired (M2-IB.6.1) | ✓ | `eligibility_to_target_weights` + ADR-045 dispatch |
| 5. `IBInstrumentResolver` SMART convention codified (M2-IB.6.1 / .6.2) | ✓ | US-equity SMART (ADR-046) + LSE-ETF SMART (ADR-048 ACCEPTED at this close) |
| 6. `scripts/run_m2ib6_ib_paper.py` driver (M2-IB.6.1 / .6.2) | ✓ | Per-symbol `order_type_by_symbol` override added at .6.2c |
| 7. LSE-RTH wire run (M2-IB.6.2b) | ✓ | First IB-paper FILL on M2-IB.6 (IBTM 19 × £128.5) |
| 8. RETRO-M2-IB (M2-IB.6-close) | ✓ | This file |
| 9. Successor `NEXT_PROMPT.md` (M2-IB.6-close) | ✓ | Replaced v0.7 → v0.8 targeting Phase 2 readiness audit |

## Surprises

Six milestone-defining surprises, in chronological order:

1. **Direct-routing precaution on CAC.PA (M2-IB.4a)** — IB Paper's "Direct Routed Orders" precaution rejected the first CAC.PA submit with error 10311. Initial framing was "hard restriction not bypassable"; the operator's API → Precautions item #1 (master) + #7 toggles bypass it cleanly. Surfaced the IB Cancelled-with-errorCode → REJECTED disambiguation path; landed `_last_error_log_entry` + `_rejected_reason_from_log_entry` helpers as production code.

2. **Post-acceptance disambiguation bug (M2-IB.4a-happy-cacpa)** — once the bypass was applied, CAC.PA reached ACCEPTED but warning 399 ("order held until next session open") in the trade log was being misclassified as a rejection because the same disambiguation path fired regardless of `accepted_emitted` state. Fixed by gating disambiguation on `tracking.accepted_emitted` (errorCode-in-log only triggers REJECTED for *pre-acceptance* Cancelled events). Test test_submit_emits_canceled_when_cancelled_post_acceptance_with_warning_in_log is the canary.

3. **A2 → A3 strategy switch (M2-IB.6-substrate)** — at M2-IB.5 architectural-surface close, the operator decided the original A2 strategy `tkan_v4_momentum_timing` on CAC.PA was not the right Phase 1 candidate, and switched to A3 `triple_lev_sma_filter_dsl` (TQQQ/TMF/IEF). ADR-021 SUPERSEDED-BY-ADR-043; multi-instrument pipeline (ADR-044) + LongShortPortfolio dispatch (ADR-045) + US-equity SMART (ADR-046) all spawned in the same substrate batch.

4. **PRIIPs / KID hard block on US-domiciled ETFs for UK retail (M2-IB.6.1 wire run)** — first wire run of A3 against TQQQ/TMF/IEF returned 104 rejections with error 201 reason text "This product does not have a KID in English or in a language approved for your country." Substituted to UK-listed PRIIPs-compliant analogues per ADR-047: QQL3 (3× Nasdaq ETP, leverage preserved) / IBTL (1× 20+yr UST UCITS — **leverage drops 3× → 1× because no UK-listed 3× US-Treasury exists**) / IBTM (1× 7-10yr UST UCITS). Trend signals (QQQ/TLT) remain US-listed since they're signal-only consumption, never traded. Strategy regime profile shifts; backtest CAGR/Sharpe/MDD do not carry forward; M7 parity envelope re-derives.

5. **LSE main book and LSE-ETF book are distinct IB venues (M2-IB.6.2)** — first M2-IB.6.2 wire smoke against the substituted universe with `XLON → "LSE"` direct routing returned IB error 200 on every order. `reqContractDetails` probe revealed: UCITS / ETPs do NOT resolve via bare `"LSE"`; they live on `LSEETF`. ADR-048 codifies the discriminator `XLON + ETF → SMART/primaryExchange=LSEETF`, paralleling ADR-046's US-SMART pattern. Side-discovery: IBTL / IBTM on LSEETF expose only **GBP-hedged** share classes — Phase 1 P&L is mixed-currency on the IB side (USD on QQL3, GBP-hedged on IBTL/IBTM); the hedge tracks USD-Treasury returns in GBP so the directional signal is preserved, but FX residuals at fill time are real.

6. **IB warning 2161 PMA-cap binds structurally on UK retail leveraged ETPs (M2-IB.6.2c)** — Wed 2026-05-06 LSE-RTH wire run produced the first IB-paper FILL (IBTM) but 0 fills on QQL3, all cancelled after IB cap-rounded MKT to LMT @ ~$39. Hypothesis: timing-tight cap that resolves with longer event-wait. Refuted: 60s wait → still 0 fills. Hypothesis: IBALGO Adaptive bypasses the cap (IB's own warning-text recommendation). Refuted: ADAPTIVE_MKT routing wired correctly (algoStrategy='Adaptive' verified) → still capped, 0 fills, FSM trace differs but cap binds. Hypothesis: LMT with explicit price above cap bypasses. Refuted: single-shot probe at LMT $50 → IB literally cap-rounds to $39.4 per warning text "to {cap} or a more aggressive price still within your specified limit price". **Empirical conclusion: PMA cap binds structurally on UK retail leveraged ETPs across MKT, ADAPTIVE_MKT, and LMT.** `priceManagementOff` flag is institutional-only. Bypass requires Pro Client classification (declined per ADR-047 alt #2) or non-leveraged product substitution. Captured as ADR-049 + INV-14 v0.7 + OQ-031.

Two operational surprises beyond the substrate-defining six:

7. **EODHD-vs-IB QQL3 price 10× discrepancy (M2-IB.6.2c side-finding)** — EODHD reports QQL3 close ~$383; IB live reference is ~$39. Likely a recent reverse-split on the leveraged ETP (common after 3× drawdowns) or an EODHD unit-of-quote convention. Strategy sizing/limit-pricing uses EODHD's price → undersized 10× in actual IB-dollar terms; LMTs computed from EODHD close × multiplier produce IB error 110 ("price out of allowed range") before 2161 fires. Doesn't break FSM testing; M7 parity work.

8. **Broker `ib.errorEvent` subscription gap (M2-IB.6.2 PRIIPs-probe surprise)** — initial Mon 2026-05-04 PRIIPs probe returned `event.reason='rejected'` (literal placeholder) instead of the formatted `"ib:201 {message}"` INV-14 v0.5 documented. Diagnostic dump revealed: `Inactive`-status rejections deliver the error text via `ib.errorEvent` (global channel), not `trade.log`. Broker subscribed only to per-trade `statusEvent`, never to global `errorEvent`. Fix: subscribe at connect, stash by `reqId/orderId`, deferred async helper for the Inactive branch (because ib_async dispatches `statusEvent` *before* `errorEvent` for the same wire message). Captured in INV-14 v0.6.

## ADRs raised this milestone

- **ADR-031** (PROPOSED → ACCEPTED 2026-04-28 at M2-IB.2) — Token-bucket rate limiter shape for IB adapters; flipped at IBClient first wire exercise.
- **ADR-032** (PROPOSED → ACCEPTED 2026-05-01 at M2-IB.3a-resolved) — Instrument resolution policy `blive.Instrument` ↔ IB `Contract`/`ConID`.
- **ADR-040** (PROPOSED → ACCEPTED 2026-04-28 at M2-IB.3-prereq) — Phase 1 deployment target = Windows native IB Gateway.
- **ADR-041** (PROPOSED → ACCEPTED 2026-05-01 at M2-IB.3a-resolved) — Yahoo-suffix translation in IB instrument resolver (`.PA` / `.L` / `.DE` / `.AS`).
- **ADR-042** (PROPOSED → ACCEPTED 2026-05-02 at M2-IB.4a) — Session-bootstrap files: agent-agnostic pattern for L0 warm-up entry point (first instance: `CLAUDE.md`).
- **ADR-043** (PROPOSED → ACCEPTED 2026-05-02 at M2-IB.6-substrate) — Phase 1 strategy switch: `triple_lev_sma_filter_dsl` (A3) replaces `tkan_v4_momentum_timing` (A2); supersedes ADR-021.
- **ADR-044** (PROPOSED → ACCEPTED 2026-05-02 at M2-IB.6-substrate) — Multi-instrument pipeline support (companion to ADR-043).
- **ADR-045** (PROPOSED → ACCEPTED 2026-05-02 at M2-IB.6-substrate) — LongShortPortfolio btest dispatch (extends ADR-030).
- **ADR-046** (PROPOSED → ACCEPTED 2026-05-02 at M2-IB.6-substrate) — IB resolver SMART routing for US equities (refines ADR-032).
- **ADR-047** (PROPOSED → ACCEPTED 2026-05-03 at M2-IB.6.1 wire-finding) — PRIIPs-compliant universe for Phase 1 A3 strategy (refines ADR-043); QQL3/IBTL/IBTM substituted for TQQQ/TMF/IEF.
- **ADR-048** (PROPOSED 2026-05-03 → ACCEPTED 2026-05-06 at M2-IB.6 close) — LSE-ETF SMART routing discriminator (refines ADR-046); held PROPOSED for the LSE-RTH wire validation that landed at .6.2b.
- **ADR-049** (PROPOSED → ACCEPTED 2026-05-06 same-session at M2-IB.6 close) — `OrderType.ADAPTIVE_MKT` for IBALGO Adaptive routing + empirical PMA-cap finding; companion to ADR-046/048.

## OQs raised this milestone

- **OQ-031** — Phase 1 deployment under PMA-bound retail account: OPEN, target resolution before Phase 1 live cutover (G3-IB → G4 transition). Operator decided at close to address in M3, not block M2-IB.6.

## Substrate transitions

| Artefact | Before | After |
|---|---|---|
| ADR-021 | ACCEPTED | SUPERSEDED-BY-ADR-043 |
| ADR-031 / ADR-032 | PROPOSED | ACCEPTED |
| ADR-040 / ADR-041 / ADR-042 | (new) | ACCEPTED |
| ADR-043 / ADR-044 / ADR-045 / ADR-046 | (new) | ACCEPTED |
| ADR-047 | (new) | ACCEPTED |
| ADR-048 | PROPOSED 2026-05-03 | ACCEPTED 2026-05-06 |
| ADR-049 | (new) | ACCEPTED |
| DD-7 | DRAFT v0.2 | STABLE v1.3 (XLON split by `asset_class` per ADR-048; IB warning 2161 cross-link) |
| DD-2 | (existing) | DRAFT v0.2 (M2 events `AccountUpdate` / `ArtefactFreshnessWarning`) |
| INV-1 | DRAFT v0.1 | DRAFT v0.3 (Phase 1 universe column updated for ADR-047 substitution) |
| INV-13 | (existing) | (unchanged at M2-IB; promoted earlier) |
| INV-14 | MISSING | DRAFT v0.7 (162 / 200 / 201 [precaution-cascade + PRIIPs-KID variants] / 202 / 399 / 2161 / 10147 / 10311 catalogued + reason-extraction taxonomy + 2161 PMA-cap validation matrix) |
| INV-5 / INV-6 | STABLE | STABLE v0.3.1 / preserved (events surface widened) |
| KB-9 | DRAFT v0.1 | DRAFT v0.2 (PRIIPs / KID §5.5 added per ADR-047) |
| KB-10 | DRAFT v0.13 | DRAFT v0.19 (ADRs 040..049 added; six version bumps) |
| KB-11 (OPEN_QUESTIONS) | DRAFT v0.3 | DRAFT v0.4 (OQ-031 raised) |
| RETRO-M2-IB | (new) | STABLE v1.0 (this file) |
| KB-2 / KB-3 | DRAFT | (STABLE flip deferred to M3 close as a follow-up — write-side §3 / §4 / §6 / §7 surface coverage now exercised through 2161/PMA-cap edge cases; minor table refinements remain) |

Code-side: `OrderType` enum gains `ADAPTIVE_MKT`; `IBBroker` subscribes to `ib.errorEvent` with stash + deferred Inactive-branch helper; `run_ib_multi_pipeline` accepts per-symbol `order_type_by_symbol`; `scripts/run_m2ib6_ib_paper.py` routes QQL3 → ADAPTIVE_MKT, IBTM/IBTL → MKT. Three new diagnostic scripts (`probe_tqqq_us_rth.py` for PRIIPs; `probe_tqqq_diag.py` for trade-state inspection; `probe_qql3_lmt_cap.py` for PMA-cap LMT confirmation). Test count: 358 → 519 across the milestone.

## Effort vs estimate

- **Estimated:** TASK_REGISTRY M2-IB v0.4 estimate was ~3 wire sessions across .3 / .4 / .5; later revised to ~1 LSE-RTH session + ~1 close session at the M2-IB.6 entry.
- **Actual:** ~10 working sessions; M2-IB.4a (3 sub-sessions), M2-IB.5 (2 sub-sessions), M2-IB.6-substrate (1 batch), M2-IB.6.1 (3 commits), M2-IB.6.2a/b/c (3 sessions across 3 days).
- **Variance reason:** primarily driven by two unexpected substrate-trail expansions: (a) the A2 → A3 strategy switch at M2-IB.5 close created a new sub-milestone ladder (M2-IB.6.x) that the original plan didn't anticipate, and (b) the PRIIPs / LSEETF / PMA-cap empirical findings each spawned investigation + ADR + INV-14 catalogue work that wasn't in the estimate. The architectural-surface validation was on schedule; the *real-world wire surprises* are what bent the timeline. This is consistent with M2-IG's pattern (RETRO-M2-IG noted similar wire-finding-driven scope expansion).

## Recommendations for NEXT_PROMPT M3

The single most important framing for M3 is: **OQ-031 is the load-bearing decision before Phase 1 live cutover.** Four candidate paths exist (accept regime-dependent fills / pursue Pro Client / substitute non-leveraged equity leg / restructure as passive-limit-only); resolving this is a Phase 1 deployment decision, not a code question. M3 should sequence:

1. **Empirical fill-rate measurement on Phase 1 paper-mode** (1–2 trading weeks of `scripts/run_m2ib6_ib_paper.py` against the substituted universe during LSE RTH) to ground the OQ-031 decision in data rather than principle.
2. **Address the EODHD-vs-IB price 10× discrepancy** as M7 parity infrastructure (subscribe to IB live market data for sizing reference, OR document the EODHD unit-of-quote convention so the strategy converts).
3. **Extend INV-14 catalogue** as additional codes surface during the longer paper-mode window (322 dup orderId still on the forward list; additional 2xxx warnings likely).
4. **Reconcile MaintMargin / GrossPositionValue / NetLiquidation in mixed-currency P&L** — Phase 1's QQL3 USD + IBTL/IBTM GBP-hedged combination needs an account-snapshot smoke during a paper-mode run that includes both legs at non-zero positions. M2-IB exercised the fields synthetically; M3 / OQ-031-resolution should confirm the live shape.
5. **KB-2 / KB-3 STABLE flip** — write-side §3 / §4 / §6 / §7 surface now exercised through 2161/PMA-cap edge cases; minor table refinements remain.

Phase-boundary protocol per CONTEXT_PROTOCOL §8.3.2 means M3 entry is a separate session from this close. The Phase 2 readiness audit (NEXT_PROMPT v0.8) is the next session.

## Recommendations for the discipline itself

Two items worth flagging:

1. **PROPOSED-uncommitted-in-working-tree pattern works.** The session sequence "land code → hold ADR PROPOSED in working tree → next session validates wire shape → flip to ACCEPTED in single batch" was used twice in M2-IB.6 (ADR-048 between 2026-05-03 and 2026-05-06; ADR-049 same-session because the empirical investigation matrix already provided the validation). Both flips landed cleanly with the body unchanged (append-only) and a PROPOSED → ACCEPTED date trail in the header. Worth codifying as part of the session-bootstrap pattern (ADR-042) — sessions that span wire-validation windows benefit from holding the ADR uncommitted to preserve the option to amend without an append-only retraction. No formal amendment needed yet; pattern is documented in this retro for future reference.

2. **Wire-finding investigations should aim to be falsifiable from session entry.** The PMA-cap investigation (M2-IB.6.2c) was healthier than the M2-IB.4a "10311 is unbypassable" framing because it made each hypothesis explicit and ran wire experiments that could refute. The "do not paper over the surprise" instruction in NEXT_PROMPT v0.7 demonstrably worked. Future investigations should mirror this shape: list hypotheses, design refuting experiments, capture the matrix in INV-14 / RETRO. The four-run wire matrix on QQL3 is the template.

## Cross-References

- [TASK_REGISTRY.md](../../TASK_REGISTRY.md) — M2-IB plan and exit criteria.
- [CONTEXT_PROTOCOL.md §8.3.1](../../CONTEXT_PROTOCOL.md) — milestone-close protocol that mandated this retro.
- [ADR-024](../decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) — retro artefact type definition.
- [previous retro: RETRO-M2-IG](M2-IG_retrospective.md) — IG bridge close (architectural surface; M2-IG.5 deferred). Recommendations §"NEXT_PROMPT v0.4" mapped M2-IG file structure 1:1 onto M2-IB resumption — the reuse worked.
- [ADRs 040–049](../decisions/DECISIONS.md) — the ADR ladder filed during M2-IB.
- [INV-14 v0.7](../inv/ib_error_codes.md) — IB error / warning catalogue with the four-run PMA-cap validation matrix.
- [OQ-031](../decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — Phase 1 deployment trade-off carried into M3.
- [DD-7 v1.3](../dd/instrument_dictionary.md) — instrument dictionary with XLON `asset_class` discriminator.

## Changelog

- **v1.0 (2026-05-06)** — initial (and only) write at M2-IB close.
