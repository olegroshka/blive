---
id: PHASE_1_READINESS
title: Phase 1 Readiness Audit
status: STABLE
owner: Oleg primary, Claude assist
last_reviewed: 2026-04-26
version: 0.1
sources:
  - REQUIREMENTS.md §14 (milestones)
  - KB-5 §7 (phased priority)
  - ADR-013 (v1 scope)
  - KB-11 (open questions)
  - CONTEXT_INVENTORY.md §6 (lifecycle tags)
depends_on:
  - REQUIREMENTS.md
  - KB-5
  - KB-11
  - CONTEXT_INVENTORY.md
referenced_by:
  - TASK_REGISTRY.md (Phase 1 plan)
---

# Phase 1 Readiness Audit

## Purpose

A one-time gate document. Before drafting the Phase 1 plan
(`TASK_REGISTRY.md`), this audit checks whether we have enough
substrate to plan well, and identifies what specifically blocks
or merely informs the planning. Status is recorded so a later
revisit at M3 close can confirm what was true on this date.

## Conventions

Status per dimension: ✓ READY · ⚠ PARTIAL · ✗ BLOCKING.

The question being asked is: **can we draft a credible Phase 1
(M0 → M3) plan today, or does something have to be settled
first?**

---

## 1. Strategy specification — ⚠ PARTIAL

| Item | Status |
|------|--------|
| Phase 1 strategy chosen | ✓ ADR-013: `tkan_v4_momentum_timing` 1× variant |
| Archetype dimensions known | ✓ KB-5 §2 A2 |
| Tradable instrument (CAC index → which ETF proxy?) | ⚠ Not decided. See OQ-025. |
| Signal generator (TKAN v4) artefact location | ⚠ Not decided. See OQ-027. |
| NAV slice for the strategy | ⚠ Not decided. See OQ-024. |
| Rebalance cadence + delay bars | ✓ Inherited from btest spec (1d, signal_delay_bars=1) |

Blocks deep planning until the instrument is named and NAV slice
has at least a placeholder.

## 2. Architecture & design — ⚠ PARTIAL

| Item | Status |
|------|--------|
| Strategic ADRs | ✓ ADR-001..019 |
| REQUIREMENTS v0.2 | ✓ |
| DD-1 domain objects (Order, Fill, Position, Bar, ...) | ✗ MISSING — required for M0 |
| INV-13 order FSM transitions | ✗ MISSING — required for M0 |
| INV-5 domain events | ✗ MISSING — required for M0/M1 |
| INV-6 ports/adapters | ✗ MISSING — required for M0 |
| Concrete port signatures (REQUIREMENTS §7.2) | ✓ specified, not yet code |

Strategic architecture settled; tactical schemas not. M0 (skeleton)
work creates DD-1, INV-13, INV-5, INV-6 as deliverables.

## 3. Data sources & subscriptions — ⚠ PARTIAL

| Item | Status |
|------|--------|
| Hybrid EODHD + IB strategy | ✓ ADR-017 |
| Clean API abstraction | ✓ ADR-014 |
| IB capability + pacing | ✓ KB-2, KB-3 |
| EODHD All-in-One subscription active | ⚠ Stated yes; CAC index coverage not verified |
| IB market-data subscription tiers (EU/SBF for CAC ETFs) | ⚠ Not yet acquired |
| `eodhd://` adapter | ✗ Not yet implemented (M2 deliverable) |
| `ib://` streaming adapter | ✗ Not yet implemented (M2 deliverable) |
| Historical warm-up plan | ⚠ Concept clear; specifics pending |

## 4. Infrastructure & operations — ⚠ PARTIAL

| Item | Status |
|------|--------|
| IB Paper account | ⚠ Not verified |
| IB Gateway via Docker | ✗ Not yet (M2 prerequisite) |
| IBC + offline TWS pinning | ✓ Concept in KB-3 §5 |
| Deployment target (Linux vs Windows) | ⚠ Not finalised |
| Storage / backup plan for event log | ⚠ Conceptual only |
| Daily TWS restart handling | ✓ Concept in KB-3 + REQUIREMENTS §5.7 |

## 5. Risk & safety — ⚠ PARTIAL

| Item | Status |
|------|--------|
| Risk-check inventory with defaults | ✓ INV-4 (RC-01..RC-13) |
| RiskEngine no-bypass | ✓ ADR-008 |
| Kill-switch behaviour | ✓ REQUIREMENTS §5.5 |
| Threshold calibration vs. actual P&L | ⚠ Defaults conservative; calibration post-M3 |
| Per-strategy NAV cap | ⚠ See OQ-024 |
| Stale-data, market-hours, kill-switch checks | ✓ INV-4 |

Sufficient for M3 with conservative defaults; calibration deferred.

## 6. Verification & parity — ⚠ PARTIAL (acceptable for M3)

| Item | Status |
|------|--------|
| Parity diagnostic mandated | ✓ ADR-012 |
| KB-15 parity_methodology | ✗ MISSING |
| Daily diagnostic implementation | ✗ M7+ per REQUIREMENTS §14 |
| Continuous parity (parallel btest replica) | ✗ M7+ |
| M3-level acceptance criteria | ⚠ To be drafted in TASK_REGISTRY |

For M3 only: parity diagnostic is *not* a blocker; it is an M7+
deliverable. M3 acceptance criteria need drafting as part of the
plan.

## 7. Open questions blocking Phase 1 — 4 BLOCKERS

The 12 OQs in `IN_DISCUSSION` have working defaults — not
blocking. The blocking ones for Phase 1 *planning*:

| OQ | Question | Why it blocks |
|----|----------|---------------|
| **OQ-024** (sub of OQ-013) | NAV slice for Phase 1 strategy | Sets sizing + risk thresholds in plan |
| **OQ-025** (sub of OQ-014) | Which ETF proxy for CAC? | Plan can't name "trade X" without an X |
| **OQ-026** (sub of OQ-015) | TKAN artefact freshness window default | RiskEngine RC-12 needs a number |
| **OQ-027** (sub of OQ-018) | TKAN artefact prod location + ownership | Operational ownership matters for plan |

All four are quick conversational decisions — minutes, not days.
Each is filed in KB-11 with a proposed default.

## 8. Substrate completeness — ⚠ PARTIAL but adequate for *planning*

| Layer | Status |
|-------|--------|
| Vision / README | ✗ MISSING |
| Requirements-phase artefacts | ✓ Substantively complete |
| Design-phase artefacts (KB-7, KB-8, KB-15, DDs, most INVs) | ✗ Mostly MISSING — classified as design-phase per CONTEXT_INVENTORY §6.2 |
| Plan layer (`TASK_REGISTRY.md`) | ✗ MISSING — this is what Phase 1 planning produces |
| CONTEXT_INVENTORY tracking gaps | ✓ |

The plan itself is the next substrate artefact. Design-phase
artefact gaps become M0--M2 deliverables (a feature of the plan,
not a blocker).

---

## Verdict

**For drafting Phase 1 (M0 → M3) at milestone-level granularity:**
**READY**, conditional on resolving four sub-OQs (OQ-024 to OQ-027,
all with proposed defaults).

- ✓ Strategic decisions in place (ADR-001..019).
- ✓ Requirements-phase substrate sufficient.
- ⚠ Need: instrument, NAV slice, freshness window, artefact ownership.
- ✓ Design-phase gaps become M0--M2 deliverables — a feature of the plan.

**For executing Phase 1:** **NOT READY**. Operational ground-truth
(IB Paper account verification, EODHD subscription verification for
CAC, Docker setup) is unverified, and design-phase artefacts (DD-1,
INV-13) need at least DRAFT status before code lands. These belong
inside M0/M1.

**For drafting all of Phase 1 + Phase 2 + Phase 3:** **NOT READY**.
Phase 2/3 planning depends on M3 outcomes (calibrated risk
thresholds, observed parity envelope, real IB pacing behaviour).
Don't plan past M3 in detail yet.

## Recommended next steps

1. ✓ **Save this audit** as substrate artefact (this file).
2. **Propose resolutions** for OQ-024..OQ-027 in KB-11 (defaults the operator can confirm or override).
3. **Draft `TASK_REGISTRY.md`** as the Phase 1 plan: per-milestone deliverables, gates, exit criteria, dependency map, MISSING-artefact-to-create list per milestone.
4. **Re-audit at M3 close** to confirm what was true on 2026-04-26 vs what changed.

## Cross-References

- [REQUIREMENTS.md §14](../REQUIREMENTS.md) — milestones M0..M8.
- [KB-5 §7](kb/strategy_taxonomy.md#7-nav-slice--priorities) — phased priority.
- [ADR-013](decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) — v1 scope.
- [KB-11](decisions/OPEN_QUESTIONS.md) — open questions.
- [CONTEXT_INVENTORY §6](../CONTEXT_INVENTORY.md) — lifecycle tags.
- TASK_REGISTRY.md (sibling to this file at root) — the plan this audit gates.

## Changelog

- **v0.1 (2026-04-26)** — initial audit at gate before Phase 1 planning.
