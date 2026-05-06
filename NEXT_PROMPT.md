# Session kickoff prompt — M3 plan-drafting (paste into a fresh Claude Code session)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are the M3 plan-drafting session

This project is `blive` — a multi-broker live execution engine, sibling to `btest`. M2-IB closed at the `M2-IB.6-close` commit on 2026-05-06; the Phase 2 readiness audit ([`docs/PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) DRAFT v0.1) was written in the session immediately following. Per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md), the M2 → Phase 2 transition is the three-session pattern: **(1) implementation close** ✓ at `M2-IB.6-close` (RETRO-M2-IB frozen), **(2) readiness audit** ✓ (`PHASE_2_READINESS.md` DRAFT v0.1), **(3) this session — M3 plan-drafting**. Mixing modes is forbidden — this session produces an M3 entry in [`TASK_REGISTRY.md`](./TASK_REGISTRY.md), informed by operator answers to the audit's five cross-cutting questions. **Do NOT implement code in this session.**

The project follows **Cognitive Cartography**: one fact has one home; stable IDs (`ADR-*`, `INV-*`, `DD-*`, `OQ-*`) are mandatory; ADRs / OQs / RETROs are append-only; `CONTEXT_INVENTORY.md` and `TASK_REGISTRY.md` must stay aligned with reality.

### State at session entry

- **Head is at the Phase 2 readiness audit commit** — `docs/PHASE_2_READINESS.md` DRAFT v0.1 in the working tree (or already committed depending on which commit the audit session pushed); CONTEXT_INVENTORY §10 marks the audit complete and item #15 (M3 plan-drafting) as the front of the queue; this `NEXT_PROMPT.md` v0.9 targets the plan-drafting work.
- **Tag `M2-IB.6-close`** marks the prior milestone close; no new tags expected from this session (tags land at *implementation* close, not at plan-drafting close).
- **Substrate state**: ADRs 001–049 with ADR-021 SUPERSEDED-BY-ADR-043; OQ-031 OPEN (operator-deferred to M3 — *this is the load-bearing OQ for the plan*); INV-14 v0.7 with the four-run PMA-cap validation matrix; RETRO-M2-IB v1.0 frozen.
- **Test count: 519** unit tests passing at `M2-IB.6-close`; mypy / black / isort / lint-imports all green.

### What this session produces

A `TASK_REGISTRY.md` update (bump version, add changelog entry) with:

1. **M3 detailed plan** at the same granularity as the closed M0 / M1 / M2-IB sections: goal, sub-milestones, deliverables, substrate transitions, exit criteria (G4 gate), estimated effort, dependencies. M3 is now the **Phase 1 deployment-decision milestone** — *not* the legacy "IB Adapter Write Side" framing (that closed inside M2-IB.4 / M2-IB.6 already). Per RETRO-M2-IB §"Recommendations", M3 sequences: empirical paper-mode fill-rate window → OQ-031 resolution → EODHD-vs-IB unit-of-quote reconciliation (timing TBD per the audit's Question 3) → INV-14 catalogue extension → mixed-currency P&L reconciliation → KB-2 / KB-3 STABLE flip.
2. **M4..M8 sketch refresh**, milestone-headline level only, informed by the five cross-cutting questions resolved in this session. The existing M4..M8 sketch in `TASK_REGISTRY.md` §"Sketched M4+ (post-Phase-1)" is the starting point; refresh it where Phase 2 readiness moved the picture (e.g., if the operator decides M3 ships M7 parity-prep early, M7 weight reduces).
3. **Quality Gate G4 redefinition** — the legacy G4 in `TASK_REGISTRY.md` §"Quality Gates" is shaped around the obsolete M3-write-side framing. Rewrite G4's exit criteria around the deployment-decision M3 and Phase 2 entry posture.
4. **Risk register update** — Phase-1 risks that closed during M2-IB are already crossed out; add Phase-2-entry risks surfaced by the audit (e.g., Phase 2 substrate prerequisite gaps; M3 paper-mode-window calibration risk if the empirical window is too short to ground OQ-031).

### What this session does NOT produce

- **Code changes of any kind.** Substrate-only session, like the audit.
- **New ADRs** unless a genuinely architectural choice surfaces while drafting (raise as `PROPOSED` only; do not pre-resolve).
- **OQ-031 resolution** in code or config — the operator's chosen Option (1 / 2 / 3 / 4) feeds the M3 plan but the resolution itself is an M3 deliverable, not a plan-drafting deliverable.
- **A wholly new `TASK_REGISTRY_PHASE_2.md`** unless scope warrants it (per CONTEXT_PROTOCOL §8.3.2 third paragraph). Default: keep one `TASK_REGISTRY.md` and add a "Phase 2 sketch" section. Split only if M4..M8 detail starts crowding the file.

---

## Step 1 — Warm-up (do this BEFORE any plan writing)

Per [CLAUDE.md](./CLAUDE.md):

1. Read `CONTEXT_PROTOCOL.md` end-to-end — especially §8.3 (milestone-close + phase-boundary) and §8.3.2 (the third-session protocol that frames this work).
2. Read `CONTEXT_INVENTORY.md` end-to-end — especially the new status banner and §10 priority queue items 14–15.
3. Read `TASK_REGISTRY.md` end-to-end — closed milestones (M0 / M1 / M2-IG / M2-IB.1..M2-IB.6) for shape; the existing "Sketched M4+" section as the refresh starting point; the legacy "M3 — IB Adapter (Write Side)" section as the *to-be-rewritten* reference.
4. Read [`docs/PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) end-to-end — *this is the load-bearing input*. The five cross-cutting questions at the top become the operator-input agenda.
5. Read [`docs/retros/M2-IB_retrospective.md`](./docs/retros/M2-IB_retrospective.md) §"Recommendations for NEXT_PROMPT M3" — pre-staged recommendations from the close session.
6. Skim [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — its four resolution options frame the M3 plan's main branch.
7. Skim [INV-14 v0.7](./docs/inv/ib_error_codes.md) §"Reason-extraction taxonomy" + warning 2161 row — the empirical evidence under OQ-031.
8. Skim the `TASK_REGISTRY.md` "Risk register (Phase 1)" section — for the Phase 2 risk additions.

When warm-up is done, reply with the standard 5-line warm-up summary and wait for operator "go" before producing the plan.

---

## Step 2 — Operator agenda before plan-drafting

The operator answers the five cross-cutting questions from [`PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) §"Cross-cutting summary" *before* the agent drafts the plan. The agent should not pre-resolve any of these — surface them as a numbered list and wait for operator answers.

The five questions, summarised:

1. **OQ-031 sequencing.** M3 resolves it as a precondition, or M3 runs an empirical window that informs a later resolution?
2. **Empirical fill-rate window scope.** Minimum trading-day count for statistically meaningful QQL3 fill-rate data?
3. **EODHD-vs-IB unit-of-quote reconciliation timing.** M3 (M7 prep) or M7 proper?
4. **Strategy-slot scope through Phase 1 deployment.** A3-only, or A1 / A1a as parallel candidates?
5. **Phase 2 substrate prerequisites.** Which M4+ artefacts (KB-7, KB-15, full RC catalogue, DD-4, INV-8, INV-9) need DRAFT before Phase 2 entry?

Each answer feeds a specific M3 sub-milestone and / or M4..M8 sketch refresh. Without operator answers, the plan would embed unverified defaults and re-introduce the phantom-decision risk CONTEXT_PROTOCOL §3.5 forbids.

---

## Step 3 — Draft the M3 plan + M4..M8 sketch refresh

Mirror the M2-IB section's structure for M3:

```markdown
### M3 — <name reflecting the deployment-decision framing> — <STATUS>

**Status:** <DRAFT | ACTIVE | …>

**Goal:** <one paragraph>

**Sub-milestones:**

- **M3.1 — <name>.** <one-paragraph description of work + substrate transitions>
- **M3.2 — <name>.** …
- …
- **M3-close.** Write `RETRO-M3.md` per [`docs/retros/_template.md`](docs/retros/_template.md); replace `NEXT_PROMPT.md` v0.9 → v1.0 targeting Phase 2 entry.

**Deliverables:** <numbered list>

**Substrate transitions:** <which artefacts move which states>

**Exit criteria (G4 gate):** <numbered list of testable criteria>

**Estimated effort:** <session count>

**Dependencies:** <prior milestone state>
```

For M4..M8, refresh the existing `TASK_REGISTRY.md` §"Sketched M4+" headlines per question (5)'s answer. No detailed deliverables — just headline + 1–2 lines of "what changed since the v0.1 sketch".

---

## Step 4 — At session end

1. Commit `TASK_REGISTRY.md` (and `CONTEXT_INVENTORY.md` priority queue update) with a clear commit message listing the M3 sub-milestones added and which audit questions the operator resolved this session. **Surface the commit message draft for confirmation before pushing**, per CLAUDE.md "Executing actions with care".
2. Update `CONTEXT_INVENTORY.md` §10 priority queue: tick "M3 plan-drafting session" ✓ done; add "M3.1 execution" (or the first M3 sub-milestone) as the next-front-of-queue item.
3. Update `CONTEXT_INVENTORY.md` status banner to reflect M3 plan ready and Phase 2 transition complete (the §8.3.2 three-session pattern fully discharged).
4. Replace this `NEXT_PROMPT.md` v0.9 with **v1.0** — kickoff prompt for the first M3 sub-milestone session. v1.0 because this is the first NEXT_PROMPT to target post-Phase-2-transition implementation work; the v0.x line was the M2-IB transition arc.

---

## Step 5 — Hard constraints (out of scope this session)

- **Code changes of any kind.** Substrate-only.
- **OQ-031 resolution as code / config.** The chosen Option informs the M3 plan; the resolution itself is an M3 deliverable.
- **Implementation of M4+ work.** Sketch only; detail at the milestone's own plan-drafting session.
- **Pre-resolving the five cross-cutting questions** without operator input.

---

## Step 6 — Discipline reminders

- Stable IDs in conversation, comments, commit messages.
- No new ADRs unless a genuinely architectural choice surfaces (it shouldn't in plan-drafting; if it does, raise as PROPOSED and surface).
- The plan is a *snapshot* — it captures the M3 plan as of this session's wall-clock. Future updates land as new versions, not edits to past sub-milestone bodies.
- Append-only — no editing past ADR / OQ / RETRO bodies; M3 sub-milestone descriptions can be updated as the milestone executes (they're plan, not retro).

---

## A note on this prompt itself

`NEXT_PROMPT.md` v0.9 (this) was authored at the Phase 2 readiness audit close on 2026-05-06. The successor (v1.0 targeting the first M3 sub-milestone) is the §8.3.2 third-session deliverable at this plan-drafting session's close.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
