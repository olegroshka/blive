# Session kickoff prompt — M3.1: EODHD-vs-IB unit-of-quote reconciliation (paste into a fresh Claude Code session)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are the M3.1 session

This project is `blive` — a multi-broker live execution engine, sibling to `btest`. Phase 1 entered its **deployment-decision milestone (M3)** at the [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) third-session close on 2026-05-06; this `NEXT_PROMPT.md` v1.0 targets the **first M3 sub-milestone — M3.1: EODHD-vs-IB unit-of-quote reconciliation**.

The project follows **Cognitive Cartography**: one fact has one home; stable IDs (`ADR-*`, `INV-*`, `DD-*`, `OQ-*`) are mandatory; ADRs / OQs / RETROs are append-only; `CONTEXT_INVENTORY.md` and `TASK_REGISTRY.md` must stay aligned with reality.

### State at session entry

- **Head is at the M3 plan-drafted commit** ([`TASK_REGISTRY.md`](./TASK_REGISTRY.md) v0.6 with the deployment-decision M3 plan; five plan-drafting calls recorded inline; [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) v0.13 with M3.1 as front-of-queue).
- **No PROPOSED ADRs in working tree.** ADRs 001–049 ACCEPTED (021 SUPERSEDED-BY-043).
- **Substrate state:** OQ-031 OPEN, target resolution at M3.3 based on M3.2 empirical evidence; INV-14 v0.7; RETRO-M2-IB v1.0 frozen; PHASE_2_READINESS.md DRAFT v0.1.
- **Test count: 519** unit tests passing at the `M2-IB.6-close` commit; mypy / black / isort / lint-imports all green.

### What this session produces

A code + substrate change addressing **the EODHD-vs-IB QQL3 ~10× price discrepancy** surfaced as a side-finding at M2-IB.6.2c ([RETRO-M2-IB](./docs/retros/M2-IB_retrospective.md) §"Surprises" #7). The discrepancy:

- EODHD reports QQL3 close ~$383, IB live reference ~$39 (~10× wider).
- Strategy sizing using EODHD's price under-sizes positions ~10× in actual IB-dollar terms.
- LMTs computed from EODHD close × multiplier produce **IB error 110** ("price not in allowed range") *before* warning 2161 (PMA cap) fires.
- Likely a recent reverse-split on the leveraged ETP (common after 3× drawdowns) or an EODHD unit-of-quote convention.

This contaminates the M3.2 empirical paper-mode window — under-sized positions don't generate the cap-binding behaviour the OQ-031 decision rests on. **Hence M3.1 ships first.**

**Scope (narrow):**

1. **Investigate the discrepancy.** Determine: is it a recent reverse-split, an EODHD unit-of-quote convention, or both? Likely investigation tools: EODHD splits-history API, reference-data probe, IB `reqContractDetails` for the conID, manual cross-check against published QQL3 reverse-split history (e.g. Bloomberg / issuer page).
2. **Implement narrow-scope sizing fix — operator-decision (Route A vs Route B).** See "Operator agenda before code" below.
3. **Implement RC-10 (price sanity)** in `blive.risk` per [INV-4](./docs/inv/risk_checks.md). Catches sizing-time discrepancies before IB error 110 surfaces. Configurable threshold (default: ±50% sanity band against last-known live reference price).
4. **KB-15 `parity_methodology` stub-DRAFT.** Author the unit-of-quote / reverse-split section only; full M7 parity envelope defers to M7. The stub captures: data-source-specific unit-of-quote conventions, reverse-split detection / handling at sizing time, the QQL3 case as the canonical example. INV-4 RC-10 row promoted from DRAFT to implemented.
5. **INV-14 grows** if new error codes surface during the investigation.

**Out of scope (M3.1):**

- Full M7 parity diagnostic surface (stays M7).
- M3.2 empirical paper-mode window (M3.2; sequential after M3.1 lands).
- OQ-031 resolution (M3.3; depends on M3.2 data).
- Full RC catalogue implementation (M4 territory; only RC-10 here).
- KB-7 / INV-8 / INV-9 stubs (M3.5 / M3.2 territories).

---

## Step 1 — Warm-up (do this BEFORE any code)

Per [CLAUDE.md](./CLAUDE.md):

1. Read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) — at minimum §0 TL;DR + §3 edit protocol + §3.5 anti-patterns.
2. Read [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) end-to-end — note v0.13 banner + §10 priority queue items 15 (M3 plan-drafted ✓) + 16 (M3.1 active).
3. Read [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) end-to-end — especially the new **M3 — Phase 1 Deployment Decision** section (sub-milestones, deliverables, exit criteria, the five plan-drafting calls inline).
4. Read [`docs/retros/M2-IB_retrospective.md`](./docs/retros/M2-IB_retrospective.md) §"Surprises" #7 — the EODHD-vs-IB discrepancy framing.
5. Read [INV-4](./docs/inv/risk_checks.md) — RC-10 row for price-sanity (current: DRAFT only; M3.1 implements).
6. Read [INV-14 v0.7](./docs/inv/ib_error_codes.md) §"Error 110" — the surface that pre-empts warning 2161 with broken sizing.
7. Skim `src/blive/runtime/ib_pipeline.py` and `scripts/run_m2ib6_ib_paper.py` — the load-bearing strategy run path; M3.1 sizing fix lands here.
8. Skim `src/blive/sizing.py` — the current sizer; understand where the EODHD-derived price enters the order-size calculation.

When warm-up is done, reply with the standard 5-line warm-up summary and **wait for operator "go"** before writing code.

---

## Step 2 — Operator agenda before code (Route A vs Route B)

The narrow sizing fix has two viable routes. Surface both as a numbered list with a cost / friction sketch and **wait for operator answer** before implementing. Don't pre-resolve.

- **Route A — IB live market data subscription for sizing reference.** Subscribe to `reqMktData` (or delayed-tier equivalent) for the tradable universe; sizer takes the live IB reference price instead of the EODHD close. Pros: authoritative, eliminates the unit-of-quote question entirely, sets up M7 parity diagnostics. Cons: monthly subscription cost (LSEETF tier per KB-2); depends on operator's IB tariff; latency footprint at sizing time.
- **Route B — EODHD-convention conversion at sizing time.** Document EODHD's unit-of-quote convention (likely a specific currency / cents / pre-split-adjusted convention); apply a per-instrument multiplier at sizing so the EODHD close converts to the IB-equivalent price. Pros: zero subscription cost; immediate fix; reversible. Cons: per-instrument convention may differ; reverse-split events require manual catalogue updates; doesn't cover M7 parity diagnostics.
- **Hybrid — B now, A later.** Route B as the immediate M3.1 fix; Route A as the M7 / live-cutover-time eventual replacement. Likely the lowest-friction path; would land as a small ADR.

If operator chooses hybrid (or any other multi-step path), a small ADR records the choice (with `PROPOSED → ACCEPTED` flip on first wire exercise per the M2-IB pattern).

---

## Step 3 — Investigation, implementation, substrate

1. **Investigation phase.** Probe scripts to confirm the discrepancy's origin. Likely shape: `scripts/probe_qql3_unit_of_quote.py` analogous to the existing PMA-cap probes. **Don't paper over the surprise** — list hypotheses, design refuting probes, capture the matrix, per [RETRO-M2-IB §"Recommendations for the discipline itself"](./docs/retros/M2-IB_retrospective.md) #2.
2. **Implementation phase.** Once Route is chosen + investigation grounds the convention, implement the narrow sizing fix + RC-10. Tests for both. Wire the existing `scripts/run_m2ib6_ib_paper.py` to use the fixed sizing.
3. **Substrate phase.** KB-15 stub-DRAFT (unit-of-quote section); INV-4 RC-10 row promoted; INV-14 if new codes surface; INV-1 / DD-7 footnotes if QQL3's reverse-split needs explicit handling.

---

## Step 4 — At session end

1. Commit code + substrate changes with a clear commit message listing artefacts touched + ADR raised (if any). **Surface the commit message draft for confirmation before pushing**, per [CLAUDE.md](./CLAUDE.md) "Executing actions with care".
2. Update [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) §10: tick "M3.1 ✓ done"; add **M3.2 — empirical paper-mode window** as next-front-of-queue.
3. Update [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) M3 section: tick M3.1 deliverable + substrate transitions actually shipped; bump version v0.6 → v0.7 with a changelog entry.
4. Replace this `NEXT_PROMPT.md` v1.0 with **v1.1** — kickoff prompt for the M3.2 empirical paper-mode window session.

---

## Step 5 — Hard constraints

- **No M2-IB regressions.** All 519 tests must remain green; G3-IB-A3 must still pass; SMART/LSEETF routing unchanged.
- **No M3.2 work.** The 10-day window is M3.2; M3.1 is sizing reconciliation only.
- **No OQ-031 pre-resolution.** Working default per OQ-031 (Option 1) stands; OQ-031 resolves at M3.3 based on M3.2 evidence.
- **Narrow KB-15 scope.** Unit-of-quote / reverse-split section only; full parity envelope stays M7.

---

## Step 6 — Discipline reminders

- Stable IDs in conversation, comments, commit messages.
- ADRs only for genuinely architectural choices (Route A vs B is one such — raise as `PROPOSED` if needed; flip ACCEPTED on first wire exercise per the M2-IB pattern).
- The plan is a snapshot — current TASK_REGISTRY M3 section captures the plan as of 2026-05-06; future updates land as new versions, not edits to past sub-milestone bodies.
- Append-only — no editing past ADR / OQ / RETRO bodies; M3 sub-milestone descriptions can be updated as the milestone executes (they're plan, not retro).

---

## A note on this prompt itself

`NEXT_PROMPT.md` v1.0 (this) was authored at the M3 plan-drafting session close on 2026-05-06 — the third and final session of the M2 → Phase 2 transition per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md). v1.0 because this is the first NEXT_PROMPT to target post-Phase-2-transition implementation work; the v0.x line was the M2-IB transition arc. The successor (v1.1 targeting M3.2) is this M3.1 session's close-deliverable.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
