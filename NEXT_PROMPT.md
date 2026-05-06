# Session kickoff prompt — Phase 2 readiness audit (paste into a fresh Claude Code session)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are the Phase 2 readiness audit session

This project is `blive` — a multi-broker live execution engine, sibling to `btest`. The current integration focus has just closed M2-IB (Interactive Brokers paper-mode A3 strategy). Phase 1 is wire-validated end-to-end against IB Paper for the substituted PRIIPs-compliant universe; the architectural surface for Phase 1 deployment is fully in place.

**This session is the Phase 2 readiness audit per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md).** Per the phase-boundary protocol, three separate sessions span M2 → M3 / Phase 2 entry: **(1) milestone close** (M2-IB.6 retrospective; done at commit `[hash]` 2026-05-06), **(2) this readiness audit**, **(3) plan-drafting for M3 / Phase 2**. Mixing modes is forbidden — this session produces `docs/PHASE_2_READINESS.md` modelled on `docs/PHASE_1_READINESS.md`, *informed by the real outcomes of M2-IB*. **Do NOT draft the M3 / Phase 2 plan in this session.**

The project follows **Cognitive Cartography**: one fact has one home; stable IDs (`ADR-*`, `INV-*`, `DD-*`, `OQ-*`) are mandatory; ADRs / OQs / RETROs are append-only; `CONTEXT_INVENTORY.md` and `TASK_REGISTRY.md` must stay aligned with reality.

### State at session entry

- **Head is the M2-IB.6-close commit** — substrate ladder closed: ADR-048 + ADR-049 ACCEPTED, DD-7 §3 amended (XLON split by `asset_class`), RETRO-M2-IB written + frozen, INV-14 v0.7 with the four-run PMA-cap validation matrix.
- **Tag `M2-IB.6-close`** marks the milestone close.
- **Test count: 519** unit tests passing; mypy / black / isort / lint-imports gates all green.
- **First IB-paper FILL on M2-IB.6** landed Wed 2026-05-06 09:33 BST: IBTM 19 × £128.5 via `Contract(exchange="SMART", primaryExchange="LSEETF")`.

### Live findings the audit must absorb

Three real-world wire findings from M2-IB that Phase 2 readiness inherits:

1. **PRIIPs / KID hard block on US-domiciled ETFs for UK retail** — original A3 universe (TQQQ/TMF/IEF) is broker-rejected by IB UK at order acceptance. Substituted to UK-listed UCITS / ETP analogues per [ADR-047](./docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) (QQL3 / IBTL / IBTM). Strategy regime profile shifts because no UK-listed 3× US-Treasury exists (bond leg 3× → 1×).
2. **LSE main book vs LSEETF venue split** — UCITS / ETPs require `Contract(exchange="SMART", primaryExchange="LSEETF")`; bare `LSE` returns IB error 200. Codified in [ADR-048](./docs/decisions/DECISIONS.md#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046) + DD-7 §3 split-by-`asset_class`.
3. **IB warning 2161 PMA-cap binds structurally on UK retail leveraged ETPs** — empirically validated across MKT, `OrderType.ADAPTIVE_MKT`, and LMT (4-run wire matrix). `priceManagementOff` is institutional-only. Captured in [INV-14 v0.7](./docs/inv/ib_error_codes.md), [ADR-049](./docs/decisions/DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding), [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account). **Operator decided at M2-IB.6 close to address OQ-031 in M3, not block close.**

These findings shift Phase 2 readiness from a paper-clean architectural exercise to a deployment-decision-gated one.

---

## Step 1 — Warm-up (do this BEFORE any audit writing)

Per [CLAUDE.md](./CLAUDE.md):

1. Read `CONTEXT_PROTOCOL.md` end-to-end — especially §8.3 (milestone-close + phase-boundary) and §8.3.2 (the three-session phase-boundary protocol that frames this session).
2. Read `CONTEXT_INVENTORY.md` end-to-end — especially §10 priority queue (now reflects M2-IB closed).
3. Read `TASK_REGISTRY.md` — M2-IB.6 section (now CLOSED), and the M3 / M4+ sketch sections.
4. Read [`docs/retros/M2-IB_retrospective.md`](./docs/retros/M2-IB_retrospective.md) end-to-end — *this is the load-bearing input for the audit*. Its §"Recommendations for NEXT_PROMPT M3" pre-stages the audit's findings.
5. Read [`docs/PHASE_1_READINESS.md`](./docs/PHASE_1_READINESS.md) end-to-end — this is the template + reference shape for `PHASE_2_READINESS.md`.
6. Skim the M2-IB ladder retros for context: [RETRO-M0](./docs/retros/M0_retrospective.md), [RETRO-M1](./docs/retros/M1_retrospective.md), [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md).
7. Skim the load-bearing ADRs from M2-IB: 043 (Phase 1 strategy switch), 044 (multi-instrument pipeline), 045 (LongShortPortfolio dispatch), 046 (US-equity SMART), 047 (PRIIPs universe), 048 (LSE-ETF SMART), 049 (ADAPTIVE_MKT + PMA-cap finding). Frontmatter + body for each.
8. Skim [INV-14 v0.7](./docs/inv/ib_error_codes.md) for the IB error / warning surface that Phase 2 inherits.
9. Skim [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — its four resolution options frame a chunk of the audit.

When warm-up is done, reply with the standard 5-line warm-up summary and wait for operator "go" before producing the readiness audit.

---

## Step 2 — Produce `docs/PHASE_2_READINESS.md`

Mirror the eight-dimension structure of `PHASE_1_READINESS.md`. For each dimension, evaluate where Phase 2 stands (READY / GAPS / BLOCKED) and what work it requires. Do not list M3 plan items — list *readiness questions* whose answers feed the M3 plan-drafting session.

### Suggested dimensions (match Phase 1 structure unless a dimension no longer applies)

1. **Strategy & universe** — A3 wire-validated on UK-listed substitution. Phase 2's A1 (`xsec_momentum_long_short_sp500`), A1a (`lagging_indecies`), or post-A3-deployment expansion candidates? OQ-031 deferred to M3 — readiness question: at what point does Phase 2 entry require OQ-031 resolved vs. at what point is it ortholgonal?
2. **Data feeds** — EODHD is the cross-sectional Phase 2 likely candidate. The M2-IB.6.2c side-finding (EODHD-vs-IB QQL3 10× price discrepancy) is a real M7 parity concern; readiness question: does Phase 2 entry require the EODHD unit-of-quote convention reconciled or live IB market data subscription?
3. **Engine surface** — `OrderType.ADAPTIVE_MKT` shipped; per-symbol `order_type_by_symbol` override on `run_ib_multi_pipeline`; multi-instrument pipeline wire-validated. Readiness question: does Phase 2 require any new order types (e.g. `MOC` / `LOC` / `OPG` for end-of-day rebalance), or is the current surface sufficient?
4. **Risk engine** — RC-08 / RC-09 / RC-12 / RC-13 active per M1 (basic gross-leverage / per-instrument cap / per-strategy NAV cap / killswitch); breaches stayed at 0 across all M2-IB wire runs. Readiness question: does Phase 2 require the full RC-01..RC-08 catalogue, or does the M1 subset stay sufficient?
5. **Reconciliation (M5 territory)** — paused throughout M2-IB. Readiness question: does Phase 2 require M5 reconciliation in scope, or is paper-mode-with-process-restart still acceptable?
6. **Operations / observability** — daily NDJSON trade tape unverified at scale; AccountUpdate emission timer at 30s diff-suppress validated; ConnectionStatus / FreshnessWarning surfaces exist. Readiness question: what observability is *load-bearing* for Phase 2 vs nice-to-have?
7. **Regulatory / compliance** — PRIIPs / KID reach catalogued in KB-9 §5.5. Readiness question: are there other regulatory surfaces Phase 2 introduces (cross-exchange? CFD via IG? non-UK accounts?) that need pre-flight diligence?
8. **OQs that gate Phase 2 entry** — OQ-012 (parity tolerance bands; M7 work — does Phase 2 entry need it resolved?), OQ-023 (ForgeFolio integration; post-M8 — confirm still post-M8), OQ-028 / OQ-029 (L0+L1 agentic work), OQ-031 (PMA-bound retail).

### What the audit produces

For each dimension:
- **READY** — sub-bullet listing the substrate that's in place
- **GAPS** — sub-bullet listing what's missing or weak
- **BLOCKED** — sub-bullet listing dependencies on operator action / OQ resolution / external state
- **Phase 2 entry question** — single sentence

Cross-cutting summary at the top: ≤ 5 questions whose answers gate the M3 plan-drafting session. These become the *agenda* for the plan-drafting session, not its output.

### What the audit does NOT produce

- A milestone plan for M3 (that's the next session).
- New ADRs (raise as `PROPOSED` only if a non-trivial architectural choice surfaces while writing the audit; do not pre-resolve).
- New OQs unless something genuinely new surfaces; OQ-031 already covers the PMA-cap deployment question.
- Changes to `TASK_REGISTRY.md` (the plan-drafting session updates that file).

### Frontmatter for `PHASE_2_READINESS.md`

Mirror `PHASE_1_READINESS.md`:

```markdown
---
id: PHASE_2_READINESS
title: Phase 2 Readiness Audit
status: DRAFT
owner: shared
last_reviewed: YYYY-MM-DD
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
```

---

## Step 3 — At session end

1. Commit `docs/PHASE_2_READINESS.md` with a clear commit message listing the dimensions evaluated and which questions the audit raised for the M3 plan-drafting session.
2. Update `CONTEXT_INVENTORY.md` §10 priority queue: tick "Phase 2 readiness audit" ✓ done with link to `PHASE_2_READINESS.md`; add "M3 plan-drafting session" as the next-front-of-queue item.
3. Update `CONTEXT_INVENTORY.md` status banner to reflect Phase 2 readiness audit complete.
4. Replace this `NEXT_PROMPT.md` with v0.9 — **kickoff prompt for the M3 plan-drafting session**. That prompt should reference `PHASE_2_READINESS.md`'s open questions and ask the plan-drafting session to address them.

---

## Step 4 — Hard constraints (out of scope this session)

- **M3 plan drafting.** Phase-boundary protocol forbids it (§8.3.2). The plan-drafting session comes after this audit.
- **OQ-031 resolution.** Operator deferred to M3; the audit can flag it as a Phase-2-entry consideration but does not resolve it.
- **Strategy / universe changes.** A3 stays as the Phase 1 deployment candidate; any restructuring lands in M3+ scope.
- **Code changes of any kind.** This is a substrate-only audit session.

---

## Step 5 — Discipline reminders

- Stable IDs in conversation, comments, commit messages.
- No new ADRs unless a genuinely architectural choice surfaces (it shouldn't in a readiness audit).
- The audit is a *snapshot* — it captures readiness as of this session's wall-clock. Future updates land as new versions, not edits to the existing body.
- Append-only — no editing past ADR / OQ / RETRO bodies.

---

## A note on this prompt itself

`NEXT_PROMPT.md` v0.8 (this) was authored at the M2-IB.6-close commit on 2026-05-06. The successor (v0.9 targeting the M3 plan-drafting session) is a §8.3.2 deliverable at this audit session's close.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
