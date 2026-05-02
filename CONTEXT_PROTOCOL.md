# blive — Context Protocol

> **Purpose:** the discipline that keeps `blive`'s context system coherent as it iterates. The entropy filter for the artifacts catalogued in [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md).
>
> **Audience:** any agent (Claude or other) and any human contributor working on `blive`. This file is mandatory reading before the first edit of a session.
>
> **Status:** v0.4 DRAFT.
>
> **Companion files:**
> - [`REQUIREMENTS.md`](./REQUIREMENTS.md) — what we're building.
> - [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) — what artifacts exist.
> - **`CONTEXT_PROTOCOL.md`** (this file) — how to work with them.
>
> If these three files disagree, the order of precedence is: **CONTEXT_PROTOCOL > CONTEXT_INVENTORY > REQUIREMENTS** (the protocol governs the inventory; the inventory points at the requirements). Any disagreement is a bug to be reconciled in a single coordinated edit, not silently absorbed.

---

## 0. TL;DR

Before any edit:

1. **READ** `CONTEXT_INVENTORY.md` to locate the artifact you'll touch.
2. **IDENTIFY** the single source of truth (SSOT) for the fact you're changing.
3. **IMPACT-CHECK** by scanning `referenced_by` for downstream artifacts.

While editing:

4. **EDIT THE SSOT, NOT A COPY.** Duplication is a bug.
5. **CITE BY STABLE ID** (`KB-N`, `INV-N`, `DD-N`, `ADR-N`, `OQ-N`) — never by file path or section number.
6. **BUMP** `last_reviewed` and (if substantive) `version`.

After editing:

7. **UPDATE** `CONTEXT_INVENTORY.md` if status changed.
8. **LOG** decisions as ADRs and questions as OQs.
9. **COMMIT MESSAGE** lists every artifact touched, by id.

If your edit is genuinely trivial (typo, formatting), use the **trivial-fix lane** in §3.4.

---

## 1. The Entropy Problem

Documentation and code drift apart over time unless a force pushes back. This force costs effort. Without a clear protocol, the natural state of a multi-artifact project is:

| Drift mode | Symptom | Mitigation |
|------------|---------|------------|
| **Vertical drift** | A change to `REQUIREMENTS.md` doesn't propagate to `DESIGN.md`, `tests/`, `RUNBOOK.md`. | Forward-propagation rules (§4); `referenced_by` checks. |
| **Horizontal drift** | Two artifacts at the same level describe the same fact slightly differently. | DRY-for-prose (§2.3); SSOT rule (§2.1). |
| **Stale references** | A cross-ref points to `KB-5 strategy_taxonomy.md` but the file moved or was renamed. | Stable-id rule (§2.4); CI link checks (§7). |
| **Phantom decisions** | "We decided to use SQLite" exists in chat but no ADR records it. | ADR-mandatory rule (§5); session handoff (§8.3). |
| **Stale knowledge** | IB pacing limits changed; our `KB-3` still cites the old number. | Periodic review cadence (§6.3); source-link discipline (§2.6). |
| **Inventory drift** | Code adds a metric; `INV-8` doesn't list it. | Machine-checkable inventories (§7.2). |
| **Glossary drift** | Same term used with two meanings in different files. | Glossary-authoritative rule (§2.7). |
| **Silent reversal** | A decision is reversed without a superseding ADR. | ADR `Supersedes` chain (§5.3). |

These eight modes account for almost all the friction in long-running multi-artifact projects. The protocol below addresses each.

---

## 2. Foundational Principles (Invariants)

These are the load-bearing axioms. Every rule below derives from one of these.

### 2.1 Single Source of Truth (SSOT)

Every fact has exactly one home. All other places reference it by id.

- IB's 50-msg/sec throttle lives in `KB-3`. `REQUIREMENTS.md §10`, `DESIGN.md`, and the adapter code refer to it as "see KB-3".
- The `Order` shape lives in `DD-1`. Everywhere else uses `DD-1.Order` or links the section.

If you find the same fact in two places, **the duplicate is the bug**, not the disagreement between them. Pick the SSOT, delete or replace the other with a reference.

### 2.2 One-Way Dependency

Higher abstraction layers reference lower ones for *motivation*, not *binding*. Lower layers may reference higher ones to cite the requirement they implement.

- `REQUIREMENTS.md` does not reference specific class names or SQL schemas.
- `DESIGN.md` does reference `REQUIREMENTS.md §X`.
- `tests/` reference `DESIGN.md` items they verify.
- A test failure is allowed to push back into `DESIGN` (and rarely `REQUIREMENTS`) via the **reverse-propagation rule** (§4.2).

### 2.3 DRY for Prose

If you're typing a fact you've seen before, stop. Reference it instead.

The cost of restating is invisible at write time and high at maintenance time, because the two copies will diverge.

Exception: a one-line summary in a TL;DR is not a violation as long as it is consistent with the SSOT and links it.

### 2.4 Stable IDs Over File Paths

Cross-references use the artifact's stable id (`KB-3`, `ADR-002`, `INV-4`), not its file path or section number. File layout may reorganize; section numbers shift on insert. Ids do not.

### 2.5 Append-Only Decisions

The decision log (`KB-10`) is append-only. To reverse a prior decision, write a **new** ADR with `Supersedes: ADR-NNN`. Never edit a past ADR's body except to mark it `SUPERSEDED-BY-ADR-MMM`.

This makes history legible: the *reasoning trail* is recoverable, not just the current answer.

### 2.6 Sources Cited

External-fact KBs (IB API limits, framework versions, etc.) cite sources by URL with **date accessed**. Without that, KB-3 in 2027 is no better than guessing — facts about the world rot.

### 2.7 Glossary Is Authoritative

The Glossary (`KB-12`) defines every project-specific term once. If two artifacts disagree on a term's meaning, the Glossary wins, or both are wrong. Disagreement triggers a coordinated edit, not a re-interpretation.

### 2.8 Eventually-Consistent Is a Bug

If two artifacts must be consistent and currently aren't, the inconsistency is logged as a known defect with a target reconciliation date — not silently tolerated. We do not "let them sync up over time".

### 2.9 No Orphans

- **No orphan facts**: every claim in `REQUIREMENTS.md` traces to a KB / ADR / DD.
- **No orphan artifacts**: every artifact in `CONTEXT_INVENTORY.md` is referenced by something. An artifact with empty `referenced_by` for > 1 milestone is a candidate for `DEPRECATED`.

---

## 3. The Edit Protocol

The load-bearing procedure. Follow this for every non-trivial edit.

### 3.1 Pre-Edit (READ → IDENTIFY → IMPACT-CHECK)

1. **READ** `CONTEXT_INVENTORY.md`. Locate the artifact you intend to change.
2. **READ** the artifact's frontmatter (`id`, `status`, `depends_on`, `referenced_by`, `last_reviewed`).
3. **IDENTIFY THE SSOT**. The fact you're changing — is it owned by *this* artifact, or does it really live somewhere else? If it lives elsewhere, edit there.
4. **IMPACT-CHECK**. Walk `referenced_by`. For each downstream artifact, ask: does my change require an update there? If yes, you have a multi-artifact edit; plan it as one coordinated commit.
5. **DECIDE THE LANE**: trivial (§3.4), normal, or decision-bearing. The lane determines ceremony level.

### 3.2 During Edit

6. **TOUCH MINIMUM SURFACE**. The narrower the diff, the easier the review. Don't refactor while editing.
7. **STABLE IDS ONLY** for cross-refs. Use `(see KB-3)`, never `(see docs/kb/ib_pacing_spec.md §2.1)`.
8. **NO RESTATING**. If you find yourself paraphrasing another artifact's content, replace with a link.
9. **PRESERVE LAYER PURITY**. A `REQUIREMENTS` edit that introduces design specifics is a smell — design content belongs in `DESIGN.md`. A `DESIGN` edit that references file paths is similar.

### 3.3 Post-Edit

10. **BUMP `last_reviewed`** to today. If the change is substantive, bump `version`.
11. **UPDATE STATUS** if it changed: `MISSING` → `DRAFT`, `DRAFT` → `STABLE`, `STABLE` → `STALE`.
12. **UPDATE `CONTEXT_INVENTORY.md`** if any row's status changed or a new row was added.
13. **DECISION → ADR**. If your edit reflects a choice made between alternatives, write the ADR (§5).
14. **QUESTION → OQ**. If your edit raised a question that you couldn't answer in-line, file an OQ (§5.4).
15. **COMMIT MESSAGE** lists every artifact touched, by id. Format:
    ```
    [blive] Brief summary

    - Touched: REQUIREMENTS.md (§5.5 risk thresholds), KB-3 (added pacing source).
    - New: ADR-013 (chose token-bucket over sliding-window).
    - Status changes: KB-3 DRAFT → STABLE.
    ```

### 3.4 Trivial-Fix Lane

For typos, formatting, broken markdown, link fixes that don't change meaning:

- Skip steps 3, 4, 13, 14.
- Still bump `last_reviewed`.
- Commit message can be one line.

If you're unsure whether the fix is trivial — it isn't. Use the normal lane.

### 3.5 Anti-Patterns

Forbidden:

1. ❌ **"Just adding a note"** to a `STABLE` artifact without bumping `last_reviewed` — invisible change.
2. ❌ **Pasting the same content in two places** — a fact has one home.
3. ❌ **"We decided X"** in conversation without writing an ADR — phantom decision.
4. ❌ **Renaming a file without sweep-updating cross-refs** — but this is rare because we use stable ids; `mv` is safe.
5. ❌ **Creating an artifact without adding a row to `CONTEXT_INVENTORY.md`** — orphan that won't be discovered.
6. ❌ **Quoting an artifact's prose verbatim** — that's a duplicate that will drift.
7. ❌ **Letting OPEN_QUESTIONS accumulate** without target resolution dates.
8. ❌ **Mixing levels** — design specifics in REQUIREMENTS, file paths in DESIGN, etc.
9. ❌ **"I'll update tests later"** — defer-everything is the road to drift. Either do it now or write the OQ that captures the gap.
10. ❌ **Editing a past ADR's body** — append-only.
11. ❌ **Bypassing the SSOT rule "just for clarity"** — clarity is achieved through structure, not duplication.

---

## 4. Layer-Crossing Rules

Changes at one level often imply work at others. Here is when, and how to handle it.

### 4.1 Forward Propagation (high → low)

A change at a higher layer flags every lower layer that depends on it for review.

| Change at | Triggers review of |
|-----------|-------------------|
| `REQUIREMENTS.md` | `DESIGN.md`, affected KBs (sources of fact), affected INVs / DDs, eventually `tests/`, `RUNBOOK.md`. |
| `DESIGN.md` | `src/blive/`, `tests/`, possibly `INV` / `DD` updates. |
| KB (e.g. `KB-3` IB pacing) | Adapter code, `DESIGN.md` rate-limiter section, possibly `REQUIREMENTS.md` if a constraint became infeasible. |
| ADR (new accepted) | Every artifact in the ADR's `Cross-References` block. |

**Rule**: when forward propagation is required, do it in the same commit, or file an OQ with a target resolution date if it cannot be done now.

### 4.2 Reverse Propagation (low → high)

When a lower layer discovers something that contradicts a higher layer:

- **Code reveals a constraint not in design** → file ADR proposing a design amendment; if accepted, update `DESIGN.md`; if it implies a requirements change, escalate to `REQUIREMENTS.md`.
- **Test reveals a missing requirement** → log as OQ first; convert to ADR + REQUIREMENTS amendment if substantive.
- **Ops reveals a runtime constraint** → ADR + DESIGN/REQUIREMENTS amendment as warranted.

**Rule**: reverse propagation always passes through an ADR. We do not silently retro-fit higher layers to match what's been built — that's how requirements rot into post-hoc justifications.

### 4.3 Frozen-Layer Protocol

A `REQUIREMENTS.md` marked as `STABLE` for a milestone is **frozen**. To open it:

1. File an ADR proposing the unfreeze, citing the discovery that requires it.
2. Acceptance of the ADR is the unfreeze act.
3. After the amendment, REQUIREMENTS re-enters `DRAFT` until re-frozen.

This prevents creeping requirements changes from polluting in-flight implementation.

---

## 5. Decision & Question Discipline

### 5.1 Three Classes of Edit

| Class | Definition | Ceremony |
|-------|-----------|----------|
| **Refinement** | Clarifies an existing artifact without changing its meaning. | Edit Protocol §3.1–3.3 only. No ADR. |
| **Decision** | Chooses between alternatives that have material consequence. | ADR mandatory (§5.2). |
| **Reversal** | Undoes a prior decision. | New ADR with `Supersedes: ADR-NNN` (§5.3). |

If you're unsure whether an edit is a refinement or a decision, write the ADR. The cost is one short file; the benefit is permanent legibility.

### 5.2 ADR Template

```markdown
---
id: ADR-NNN
title: Short imperative title
status: PROPOSED | ACCEPTED | SUPERSEDED-BY-ADR-MMM | DEPRECATED
date: YYYY-MM-DD
decider: Oleg (with Claude)
supersedes: ADR-MMM | none
---

## Context
What problem are we solving? What forces are at play?

## Decision
What did we decide? One paragraph, declarative.

## Alternatives Considered
1. **Option A** — pros / cons / why not chosen.
2. **Option B** — pros / cons / why not chosen.

## Consequences
- **Positive**: ...
- **Negative / risks**: ...
- **Follow-ups**: tasks this decision creates.

## Cross-References
- REQUIREMENTS §X
- KB-N
- ADR-MMM (related, not superseded)
```

### 5.3 Reversal Protocol

To reverse ADR-007:

1. Write `ADR-NNN` with `supersedes: ADR-007`. Body explains *what changed in our understanding*.
2. Update ADR-007's frontmatter only: `status: SUPERSEDED-BY-ADR-NNN`. Do not edit ADR-007's body.
3. Forward-propagate (§4.1) any consequences.

The chain is the documentation. Even decisions we walk away from are kept — they explain *why we don't do that*.

### 5.4 OQ Template

```markdown
---
id: OQ-NNN
question: One-sentence statement of the open question.
status: OPEN | IN_DISCUSSION | RESOLVED-BY-ADR-NNN | ABANDONED
opened: YYYY-MM-DD
target_resolution: YYYY-MM-DD
depends_on: [OQ-MMM, KB-N]
---

## Background
Why is this open? What forced the question?

## Options Under Consideration
1. ...
2. ...

## Resolution Criteria
What would have to be true for us to resolve this? E.g., "calibrated against 30 days of paper trading data."
```

OQs without `target_resolution` accumulate as a wishlist that never closes. Set a date even if it's "by milestone M3"; revise as needed.

---

## 6. Status Lifecycle

### 6.1 The Five States

```
MISSING ──new artifact──→ DRAFT ──owner reviews + complete──→ STABLE
                                                              │
                            ┌─────────────────────────────────┤
                            │                                 │
                            ▼                                 ▼
                          STALE                       (superseded by edit/ADR)
                            │                                 │
                            └──re-review──→ STABLE            ▼
                                                          DEPRECATED
                                                       (kept for history)
```

| Status | Meaning |
|--------|---------|
| `MISSING` | Listed in `CONTEXT_INVENTORY.md` but no file exists yet, or stub only. |
| `DRAFT` | File exists, content incomplete or unreviewed. May be authoritative-in-progress. |
| `STABLE` | Reviewed by owner, complete to the level required for the current lifecycle stage, no internal contradictions. |
| `STALE` | Was `STABLE` but `last_reviewed` is older than the current milestone freeze, OR an upstream artifact changed. |
| `DEPRECATED` | Superseded; kept for history. New work must not reference it. |

### 6.2 Transition Triggers

- **MISSING → DRAFT**: any first content commit.
- **DRAFT → STABLE**: owner reviews; all sections complete; no `TODO` or `?` markers; `last_reviewed` set.
- **STABLE → STALE**: `last_reviewed < current_milestone_freeze_date`, **or** any artifact in `depends_on` had a `STABLE → DRAFT` transition.
- **STALE → STABLE**: re-review; update `last_reviewed`; resolve any issues that the upstream change introduced.
- **\* → DEPRECATED**: a superseding artifact exists; this artifact is moved to `docs/_deprecated/` (kept, not deleted).

### 6.3 Review Cadence

| Artifact class | Default review cadence |
|----------------|-----------------------|
| `REQUIREMENTS.md` | At every milestone freeze (M0, M1, ..., M8). |
| `DESIGN.md` | At every minor milestone (M2.x, M3.x). |
| KB-* (world facts) | Quarterly OR on external-source change notification. |
| INV-* (lists) | At each milestone freeze; auto-checked by CI from M5. |
| DD-* (schemas) | At each schema-touching milestone. |
| ADR / OQ | Append-only; OQ targets reviewed weekly. |
| Glossary (`KB-12`) | At each milestone freeze. |

### 6.4 Freeze Ceremony

At each milestone freeze:

1. Walk `CONTEXT_INVENTORY.md`. For every `STABLE` artifact, confirm `last_reviewed` is fresh; otherwise mark `STALE`.
2. For every `DRAFT` artifact required by the milestone (per §6.2 of `CONTEXT_INVENTORY`), drive to `STABLE`.
3. Tag the repo (`git tag M2.0`).
4. Snapshot `CONTEXT_INVENTORY.md` to `docs/_freezes/M2.0-CONTEXT_INVENTORY.md`.

The frozen inventory lets future-self ask "what did we believe when we shipped M2?".

---

## 7. Drift Detection

### 7.1 Manual Checks (until automation lands)

- **Per-commit**: commit message lists every artifact touched (§3.3.15).
- **Weekly**: scan `CONTEXT_INVENTORY.md` for `STALE` rows; resolve or schedule.
- **Per-milestone**: full freeze ceremony (§6.4).
- **On-edit**: explicit `referenced_by` walk (§3.1.4).

### 7.2 Automated Checks (planned)

To be added under `tests/context/` from M4+:

| Check | What it asserts |
|-------|-----------------|
| `test_inventory_completeness` | Every `*.md` in `docs/` has a row in `CONTEXT_INVENTORY.md`. |
| `test_no_dangling_ids` | Every `KB-N` / `ADR-N` / `OQ-N` reference resolves to an existing artifact with matching id in frontmatter. |
| `test_metric_inventory_match` | Every metric registered in code is in `INV-8`; every entry in `INV-8` is registered in code. |
| `test_error_code_inventory_match` | Every IB error code mapped in code is in `INV-14`. |
| `test_glossary_uniqueness` | No term defined in two artifacts. |
| `test_orphan_artifacts` | No artifact has empty `referenced_by` for more than one freeze. |
| `test_adr_supersede_chain` | Every `SUPERSEDED-BY` points to an existing ADR; no cycles. |
| `test_status_consistency` | `CONTEXT_INVENTORY.md` status matches each artifact's frontmatter status. |
| `test_frozen_layers_locked` | If `REQUIREMENTS.md` is frozen for a milestone, edits in that branch require a corresponding ADR commit. |

### 7.3 Tooling Tickets (to add to `TASK_REGISTRY.md` when it exists)

- `import-linter` rule: domain code may not import from `adapters/`; verified at CI.
- `pre-commit` hook: warn when editing `REQUIREMENTS.md` without `CONTEXT_INVENTORY.md` change in same commit (heuristic, override-able).
- A small Python script `scripts/audit_context.py` to run all §7.2 checks locally.

---

## 8. Session Protocol

### 8.1 Session Start (warm-up sequence)

The first thing an agent does in a new `blive` session, before any edit:

1. Read `CLAUDE.md` (project root, when it exists).
2. Read `CONTEXT_INVENTORY.md` end-to-end.
3. Read `CONTEXT_PROTOCOL.md` (§0 TL;DR is sufficient if previously read in full).
4. Identify which artifacts the current task touches; read their frontmatter and bodies.
5. Spawn `Explore`-style sub-agents for any unread KBs the task depends on.
6. Only then begin work.

This warm-up takes ~5 minutes and prevents 90% of the avoidable mistakes.

### 8.2 During Session

- Follow Edit Protocol (§3) for every change.
- Use `TaskCreate` to track multi-doc edits as a unit.
- Cite artifacts by id (`KB-3`, `ADR-002`) in conversation with the user.
- When in doubt about which artifact owns a fact, ask before editing.

### 8.3 Session Handoff (end of session)

Before declaring the session done:

1. All edits committed; commit messages list artifacts by id.
2. Any new `MISSING` artifacts created have a stub frontmatter and a `CONTEXT_INVENTORY.md` row.
3. Any decisions made during the session have ADR entries.
4. Any open questions raised have OQ entries.
5. `last_reviewed` and `version` fields are current on touched artifacts.
6. The `CONTEXT_INVENTORY.md` "Priority Queue" section reflects what's now next.

#### 8.3.1 Additional steps at milestone close

If this session closes a milestone (M_N exit criteria reached, or the milestone is formally blocked):

7. **Write a retrospective** at `docs/retros/M{N}_retrospective.md` per the [`docs/retros/_template.md`](docs/retros/_template.md) template (per [ADR-024](docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type)). Captures: delivered-vs-plan, surprises, ADRs / OQs raised this milestone, substrate transitions, effort vs estimate, and recommendations for the next milestone's `NEXT_PROMPT.md`.
8. **Update `NEXT_PROMPT.md`** to target M_{N+1}, informed by the retrospective. The `NEXT_PROMPT.md` is itself substrate; each milestone close produces its successor.
9. **Report the milestone gate status** (G_{N+1}) explicitly to the operator with a checklist of the gate's exit criteria — passed / partial / blocked, with the reason on each line.

The retrospective is `STABLE` on first write and never edited (frozen historical record).

#### 8.3.2 Phase boundary rule

A *phase boundary* (e.g., M3 → Phase 2 entry at the G4 gate) is structurally different from a milestone hop and requires a different ceremony.

The closing implementation session of the prior phase ends with §8.3 + §8.3.1 only. **It does not draft the next phase's plan.** Mixing implementation-mode and next-phase-planning-mode in saturated context is a known substrate-drift mode and explicitly forbidden.

The next phase requires three sessions, each with a single mode:

1. **Implementation close** (last M_N session of the prior phase) — ends with retrospective and gate report, per §8.3 + §8.3.1.
2. **Readiness audit session** — produces `docs/PHASE_{N+1}_READINESS.md` modelled on [`docs/PHASE_1_READINESS.md`](docs/PHASE_1_READINESS.md), now informed by *real* outcomes from the prior phase (calibrated thresholds, observed parity envelope, real broker behaviour). May raise new OQs.
3. **Plan-drafting session** — operator resolves OQs from the audit; agent drafts the next phase's plan in `TASK_REGISTRY.md` (or splits to a phase-specific `TASK_REGISTRY_PHASE_{N+1}.md` if scope warrants).

Operator review happens between each pair of sessions.

### 8.4 Multi-Agent Coordination

If multiple agents (or sessions) work on `blive` concurrently:

- Each session takes a unique branch (`session/<date>-<purpose>`).
- Sessions claim artifacts they intend to edit by adding their session id to a temporary `claimed_by` field in frontmatter; remove on commit.
- Conflicts at merge are resolved by Oleg, not by either agent.
- Long-running agent state (e.g. `agentId`) is logged in the session handoff so others can see what was attempted.

For now, this is rare; rule exists in case it isn't later.

---

## 9. Templates

### 9.1 Standard Frontmatter (KB / INV / DD)

```yaml
---
id: KB-NNN
title: Human-readable title
status: DRAFT          # MISSING | DRAFT | STABLE | STALE | DEPRECATED
owner: Claude          # Claude | Oleg | shared
last_reviewed: YYYY-MM-DD
version: 0.1
sources:               # external URLs with date accessed
  - https://...        # accessed YYYY-MM-DD
depends_on: []         # list of artifact ids this references
referenced_by: []      # backlinks; auto-generated if tooling exists
---
```

### 9.2 ADR

See §5.2.

### 9.3 OQ

See §5.4.

### 9.4 RETRO (milestone retrospective)

Per [ADR-024](docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) and §8.3.1. Status lifecycle simplified to `DRAFT → STABLE` only (retros are frozen historical records). Full template at [`docs/retros/_template.md`](docs/retros/_template.md). Frontmatter shape:

```yaml
---
id: RETRO-M{N}
title: M{N} Retrospective
status: STABLE
owner: Oleg
last_reviewed: YYYY-MM-DD
version: 1.0
sources:
  - TASK_REGISTRY.md M{N}
depends_on:
  - TASK_REGISTRY
referenced_by: []
---
```

### 9.5 Standard Top-Section for a New KB

```markdown
# KB-NNN — Title

(frontmatter as above)

## Purpose
Why this artifact exists; what facts it owns.

## Scope
What's in / out.

## Content
... the actual knowledge ...

## Sources
Same as frontmatter sources, with annotations on what each contributes.

## Open Questions
Inline OQ-NNN references; do not duplicate the OQ body here.

## Cross-References
Other artifacts that read from or write to this one.

## Changelog
- vX.Y (YYYY-MM-DD): what changed and why.
```

---

## 10. How the Three Meta Files Relate

| File | Role | Read first? |
|------|------|-------------|
| [`REQUIREMENTS.md`](./REQUIREMENTS.md) | What we will build (the contract). | Read after the meta files for context. |
| [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) | What artifacts exist (the registry). | Read second. |
| **`CONTEXT_PROTOCOL.md`** (this file) | How to maintain them (the rules). | Read first; §0 TL;DR is the daily refresher. |

**Reading order for a new agent / new contributor:**

1. `README.md` (when it exists) — 30 seconds.
2. `CLAUDE.md` (when it exists) — 1 minute.
3. **`CONTEXT_PROTOCOL.md` §0 TL;DR** — 1 minute, daily.
4. `CONTEXT_INVENTORY.md` — 5 minutes, lay of the land.
5. `REQUIREMENTS.md` — 15 minutes, what we're building.
6. Specific KBs/INVs/DDs as the task requires.

**Cross-reference convention:**

- Inside markdown, link by relative path on first mention in a section: `[KB-3](./docs/kb/ib_pacing_spec.md)`.
- Subsequent references in the same section may use bare id: `KB-3`.
- In code or commit messages, always use the bare stable id.

---

## 11. Human-Governance, Agent-Execution Division of Labour

The discipline's *content* — six artefact categories, stable IDs, status lifecycle, edit protocol, propagation rules, anti-patterns — is independent of who executes the discipline. As substrate-aware tooling and agentic memory architectures mature, **execution of the discipline progressively delegates to agents while governance remains human**. This section specifies the division of labour and the adoption order. See [ADR-026](docs/decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface).

### 11.1 The division

| Activity | Human | Agent |
|----------|-------|-------|
| Intent declaration (what to do) | ✓ | — |
| Substrate traversal / warm-up reading | governance only | ✓ (L0) |
| Drift / orphan / staleness detection | review only | ✓ (L1) |
| Decision approval (review proposed ADRs) | ✓ | — |
| ADR drafting at decision moment | review / approve | ✓ (L2) |
| Retrospective drafting (populate observable state) | review / approve | ✓ (L3) |
| `NEXT_PROMPT` drafting (informed by retro + remaining plan) | review / approve | ✓ (L3) |
| Scope / boundary calls (is this in scope?) | ✓ | — |
| Phase-boundary readiness audit | ✓ + agent assist | drafts under direction |
| Substrate authoring (the prose of KBs / DDs) | ✓ + agent draft | proposes drafts |

The default posture: **agent proposes; human approves**. The human's residual surface area collapses to intent, approval, scope, and voice authority on substantive prose.

### 11.2 The five-layer adoption stack

**L0 — Substrate-aware warm-up.** An agent reads `CONTEXT_INVENTORY.md`, takes a task description, walks the `depends_on` closure of relevant artefacts, and pages them into working context. Replaces manual file-list curation in `NEXT_PROMPT.md`. Layer-independent — useful even if no other layer is implemented.

The simplest manual implementation of L0 is a **session-bootstrap file** at the project root: a small markdown pointer that any agent harness loads automatically at session start (per its native convention — `CLAUDE.md` for Claude Code; `AGENTS.md`, `.cursorrules`, or system-prompt config for others). The bootstrap file is itself substrate (frontmatter, version, `referenced_by`) and is governed by the same edit protocol; its content is *pointers* to the canonical substrate, never restated rules. The pattern is **agent-agnostic in semantics, platform-specific in filename** — the discipline does not couple to any single AI vendor or model generation. See [ADR-042](docs/decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point). When fuller L0 tooling lands (per [OQ-028](docs/decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) and [OQ-029](docs/decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1)), the bootstrap file becomes the fallback for environments without it; the pattern is durable across the L0 → L1 → L4 transitions.

**L1 — Continuous integrity watchdog.** A second-class agent runs scheduled scans for: orphan stable-id references; STABLE artefacts past freshness window; glossary divergence (same term used with different semantics across artefacts — detectable via embedding similarity); supersede-chain cycles; FSM-vs-code drift in INV-13. Produces a drift report for human review. Catches §7's drift modes proactively rather than at next freeze gate.

**L2 — In-situ ADR auto-drafting.** An *intent-monitor* agent watches the conversation and edit stream. When semantic patterns indicate a non-trivial architectural commitment (alternatives weighed, rationale stated, choice committed), the agent pauses and drafts an ADR with full frontmatter, context, decision, alternatives, consequences. Human approves / edits / rejects inline. Eliminates phantom-decision risk at the source.

**L3 — Auto-drafted retros + `NEXT_PROMPT`s.** At milestone close, the agent populates `RETRO-M{N}` from observable state: commit log, substrate-state diff, ADRs / OQs filed, tracked effort. Generates `NEXT_PROMPT` v(N+1) targeting M_{N+1}, informed by the retro and the remaining plan. Human reviews and approves.

**L4 — Graph-native substrate.** Markdown becomes views over a knowledge graph (Neo4j or RDF triplestore). Cross-references become first-class edges. Queries become graph traversals. Tooling (drift detection, propagation simulation, orphan analysis) becomes mechanical via graph algorithms. The discipline (categories, lifecycle, edit protocol) is unchanged; the *physical substrate* changes underneath.

### 11.3 Adoption order

L0 + L1 first — immediate utility, low cost, layer-independent. L2 + L3 after L0 / L1 prove reliable. L4 at discipline v2.0; deferred until current substrate's limits force the migration. Concrete tooling and timing decisions tracked in [OQ-028](docs/decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) and [OQ-029](docs/decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1).

### 11.4 Failure modes specific to the agentic layer

- **Agent confabulating fixes / drafts.** L1 watchdog or L2 ADR draft might propose plausible-but-wrong content. **Mitigation:** human-approval gates are mandatory on all agent-drafted outputs; review-thrash protection via batched approval rather than per-item.
- **Drafting bias drift.** Agent-drafted ADRs / RETROs might embed agent perspectives that aren't the human's. **Mitigation:** periodic comparison of drafted-vs-final outputs; human re-asserts voice on signal of drift.
- **Layer coupling.** A higher layer (e.g. L2 ADR drafter) must not strictly require lower layers; layers are designed to be useful independently.
- **Over-delegation.** If the human stops reviewing because the agent does the work, governance erodes. **Mitigation:** explicit approval gates that require active engagement; periodic spot-audits.
- **Execution disagreement.** When the agent's reading of the substrate disagrees with the human's, the substrate wins (it is the SSOT); the agent's reading is the bug to investigate.

### 11.5 Relationship to autonomous memory architectures

Cognitive Cartography is the **governance schema** over autonomous memory, not its replacement. As agentic memory systems mature (MemGPT, Agentic Memory / Zettelkasten, Multi-Layer Memory, Sculptor / ARC, graph-native context, Recursive Language Models), they handle progressively more substrate execution. The discipline contributes:

- **Categories** that map to memory tiers — KB ≈ semantic memory; ADR ≈ decision log; OQ ≈ open questions; RETRO ≈ episodic summary.
- **Stable IDs** that survive memory paging, re-organisation, and version drift — boundary objects between today's substrate and tomorrow's tooling.
- **Status lifecycle** that governs trust — STABLE = trustworthy; STALE = needs re-verification; DEPRECATED = preserved for history but not for new work.
- **Edit protocol** that constrains what an agent can change without human approval.
- **Anti-pattern catalogue** that names known failure modes.

Without the discipline, autonomous memory systems are opaque and unauditable. Without autonomous memory, the discipline is human-laborious and doesn't scale beyond a complexity threshold. Together: **human-governed, agent-executed substrate engineering**, sustainable across project complexities and model generations.

---

## 12. Self-Critique / Next-Pass TODOs

For v0.2 of this file:

- [ ] Add a short "common failure modes when this protocol is violated" appendix with real examples (will accumulate organically).
- [ ] Decide whether the trivial-fix lane (§3.4) is too generous; revisit after first 10 edits.
- [ ] Calibrate review cadences (§6.3) — quarterly KB review may be too rare for fast-moving libraries like `ib_async`.
- [ ] §7.2 — codify the eight automated checks as a single `scripts/audit_context.py` script with a stub now, even if it only reports `STUB` for each check.
- [ ] §8.4 multi-agent coordination is speculative; revisit only if it becomes real.
- [ ] Consider whether `RUNBOOK.md` (operational play-by-play) should follow the same protocol or have its own, given operational urgency may not allow ceremony.
- [ ] Add a "minimum viable protocol" cheat sheet card for printing / pinning — the §0 TL;DR may be that already.
- [ ] Confirm the precedence rule (PROTOCOL > INVENTORY > REQUIREMENTS at the top of this file) is the right ordering. Argument against: REQUIREMENTS is the contract and should win. Argument for: REQUIREMENTS without protocol becomes incoherent over time. Current view: protocol governs the *form* of all docs; requirements is the *content* of one of them. Form precedes content for consistency, content precedes form for relevance.
