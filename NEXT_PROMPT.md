# Session kickoff prompt — paste this into a fresh Claude Code session

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are joining a disciplined project

This project is `blive` — a live algorithmic-execution engine for Interactive Brokers, sibling to `btest` (research backtesting framework). It is run by Oleg Roshka, a UK-based independent quant researcher.

The project practises **Cognitive Cartography**, a substrate-engineering discipline articulated in `docs/method/paper/cognitive_cartography.tex`. In short: every fact has one home; cross-references use stable IDs; decisions are append-only ADRs; questions are append-only OQs; status lifecycle is explicit; an edit protocol governs all changes.

You will read the discipline (and the M0 substrate that you are extending) before working. You will then plan. Only then will you produce code.

---

## Step 1 — Warm-up (do this BEFORE any work, in order)

Read the following files. Do **not** skim. Stop and re-read if anything is unclear.

1. **`CONTEXT_PROTOCOL.md`** — at minimum §0 (TL;DR). The protocol governs every edit you will make. The trivial-fix lane is in §3.4. Anti-patterns are in §3.5.
2. **`CONTEXT_INVENTORY.md`** — the registry of every knowledge artefact. Read it end-to-end. The §10 "Outstanding queue" tells you where the project is right now (M1 is the next concrete milestone).
3. **`TASK_REGISTRY.md`** — the Phase 1 plan. Today's work is the **M1 milestone** in that file. Read M1 in full. Skim M2–M3 for context. Note the G2 gate at the end of M1.
4. **`docs/retros/M0_retrospective.md`** — the M0 close retrospective. The "Recommendations for NEXT_PROMPT M1" and "Surprises" sections in particular contain hard-won notes from the prior session that will save you time.
5. **`REQUIREMENTS.md`** — re-read §5.1 (strategy ingest from btest), §5.5 (Risk Engine — for the M1 subset), §5.13 (Sizer + ramp), §8 (parity contract).
6. **`docs/decisions/DECISIONS.md`** — read **ADR-008 (RiskEngine no-bypass)**, **ADR-010 (btest reuse by import)**, **ADR-014 (data sources via clean abstraction)**, **ADR-021 (CAC.PA proxy)**, **ADR-022 (TKAN freshness 30d / 21d)** in full. These are load-bearing for M1 design choices.
7. **`docs/kb/btest_dsl_inventory.md`** (KB-1) — focus on §1 (Strategy), §6 (Portfolio — `TimingPortfolio` is what `tkan_v4_momentum_timing` uses), §7 (Execution), §8 (Costs), §10 (DataSource registry).
8. **`docs/kb/strategy_taxonomy.md`** (KB-5) — §2 (A2 archetype) and §3 (the `tkan_v4_momentum_timing` row).
9. **`docs/inv/risk_checks.md`** (INV-4) — the M1 subset is **RC-08 (stale data), RC-09 (market hours), RC-13 (kill-switch armed)**. **Verify whether RC-12 (model-artefact freshness) also belongs in M1** — depends on whether the M1 paper pipeline actually loads `pred_cache.pkl`. If it does, RC-12 lands at M1; if not, it can wait for M2.
10. **The M0 substrate you are extending**: `docs/dd/domain_objects.md` (DD-1 STABLE), `docs/inv/order_state_transitions.md` (INV-13 STABLE), `docs/inv/ports_adapters.md` (INV-6 DRAFT — promote to STABLE at M1 close), `docs/inv/domain_events.md` (INV-5 DRAFT — same). These are the contract you are building against.
11. **The M0 code baseline**: skim `src/blive/domain/{types,events,order_fsm,ports,positions}.py` and `src/blive/adapters/` so you know what already exists. Then skim `tests/` so you know the M0 test pattern; M1 tests should follow it.

When you finish warm-up, **before proposing any work**, reply to me with a 5-line summary:

```
Warm-up complete. I have read:
- [list the artefacts you read]

Project state: [G1 status, current milestone, key architectural commitments, what's already built]

I propose to start M1 by: [first concrete action]
```

Wait for my "go" before producing code.

---

## Step 2 — Today's mission: Milestone M1 (btest Strategy Import & Paper Round-Trip)

Per `TASK_REGISTRY.md` M1 (canonical source — do not paraphrase from this prompt, read the file).

**Goal:** `tkan_v4_momentum_timing` 1× runs in blive's paper mode end-to-end and matches btest's equity curve to within rounding tolerance (±1 bps).

**Deliverables (7 items, condensed — full list in TASK_REGISTRY.md M1):**

1. btest dependency smoke-import check (CI). The btest install path is already pinned in `pyproject.toml` `[tool.uv.sources]` from M0; confirm `from quantdsl_backtest.engine import …` works end-to-end.
2. **Strategy ingest module** (`blive.strategy.loader`).
3. **FactorEngine / SignalEngine / PortfolioEngine reuse** — imported from btest, wired into the blive runtime per ADR-010.
4. **Sizer (M1 minimal)** (`blive.sizing`) — single-instrument case (CAC.PA only) suffices for Phase 1.
5. **RiskEngine (M1 minimal subset)** (`blive.risk`) — implement RC-08, RC-09, RC-13 (and RC-12 if §1 step 9 verification says so).
6. **Paper-mode end-to-end pipeline** — load strategy → replay deterministic CAC.PA bars → factor → signal → portfolio → sizer → risk → paper broker → record fills / positions / equity curve.
7. **DD-3 config schemas** (`docs/dd/config_schemas.md`, **MISSING → DRAFT**).

**Substrate transitions at M1 close:**

- DD-3 → DRAFT.
- INV-5 → STABLE (the event surface stabilises once the M1 events are exercised end-to-end).
- INV-6 → STABLE (the Port contracts are exercised by Sizer + RiskEngine + the paper pipeline).

**Exit criteria (G2 gate):**

- `tkan_v4_momentum_timing` 1× runs in blive paper mode for ≥ 252 days of historical CAC.PA data.
- End-of-period equity curve matches btest's reference run within ±1 bps.
- Round-trip test: signal → fill → position update → equity reflects the trade including commission per KB-6 §1.
- A negative test: deliberately stale data triggers RC-08 block; engine refuses to size; alert event fires.

---

## Step 3 — Discipline reminders

Every edit you make — to substrate or code — follows **CONTEXT_PROTOCOL §3**:

- **Pre-edit:** READ the inventory → IDENTIFY SSOT for the fact you're changing → IMPACT-CHECK by walking `referenced_by`.
- **During:** stable IDs in cross-refs (`KB-N`, `ADR-N`, `OQ-N`); no paraphrasing other artefacts (link instead); minimum-surface change.
- **Post-edit:** bump `last_reviewed`; bump `version` if substantive; if status changed, update `CONTEXT_INVENTORY.md`; if the edit reflects a new architectural choice, write the corresponding **ADR** in the same commit; if it raises a question that can't be resolved in line, write the corresponding **OQ**.
- **Commit messages** list every artefact touched, by stable ID.

The **trivial-fix lane** (§3.4) exists for typos / formatting / link fixes. M1 is *not* a trivial-fix scenario; use the full lane.

If you find yourself about to make an architectural choice that isn't already captured in ADR-001..026, **stop**: write the proposed ADR with status `PROPOSED`, surface it to me, and wait for confirmation before committing. Likely M1 candidates for new ADRs:

- The Sizer's rounding policy (round-down to integer shares vs. respect IB fractional-share precision per account class).
- The strategy YAML schema (DD-3) — schema choices (e.g. how to declare `live_overrides`, `live_*_provider` hooks) lock in for the rest of Phase 1.
- The paper-mode market-data adapter (per the M0 retro recommendation: a `PaperMarketData` implementing `MarketDataPort` rather than ad-hoc fixture loading).

If you discover a new question whose answer matters for M1, file an OQ rather than guessing.

Use the task-tracking primitives (TaskCreate / TaskUpdate / TaskList) to track multi-artefact edits as a coherent unit.

---

## Step 4 — Hard constraints (out of scope)

These belong to later milestones; do **not** start them in this session:

- IB adapter (any read or write methods) — M2 and M3.
- Real-streaming data sources (`eodhd://`, `ib://`) — M2.
- Full RiskEngine with all RCs (RC-01..RC-12 except the M1 subset) — M4.
- SQLite persistence — M4.
- Reconciliation loop — M5.
- Web UI — M6.
- Parity diagnostic — M7.

If you find an M1 design choice forces an early decision about M2+ architecture, capture it as an ADR (don't pre-build).

---

## Step 5 — Handoff (at session end)

Standard handoff per CONTEXT_PROTOCOL §8.3:

1. Every artefact touched is **committed**, with the commit message listing artefacts by stable ID.
2. Every new artefact created has frontmatter (id, title, status, owner, last_reviewed, version, sources, depends_on, referenced_by) and a row in `CONTEXT_INVENTORY.md`.
3. Status changes (DRAFT → STABLE) are reflected both in the artefact itself and in `CONTEXT_INVENTORY.md`.
4. Any new ADRs are in `docs/decisions/DECISIONS.md` and indexed in its top table.
5. Any new OQs are in `docs/decisions/OPEN_QUESTIONS.md`.
6. `TASK_REGISTRY.md` reflects M1 progress (which deliverables done, which blocked, why).

**Additional milestone-close steps** per CONTEXT_PROTOCOL §8.3.1 (applies because this session closes M1):

7. **Write a retrospective** at `docs/retros/M1_retrospective.md`, copying the structure from `docs/retros/_template.md`. Capture: G2 gate status (four exit criteria as a checklist), delivered-vs-plan, surprises, ADRs/OQs raised this milestone, substrate transitions, effort vs estimate, recommendations for the M2 NEXT_PROMPT. Status STABLE on first write; do not edit afterwards.
8. **Write `NEXT_PROMPT.md` v0.3** targeting M2, informed by the retrospective. Most of this current prompt's warm-up files stay the same in v0.3; the Step 2 "Today's mission" is rewritten for M2; Step 3 discipline reminders stay; Step 4 out-of-scope updates (M1 deliverables drop off; IB adapter still out at M1, *in* at M2; real data sources *in* at M2).
9. **Report the G2 gate status back to me** as a checklist in chat — passed / partial / blocked, with reason on each line.

If this session inadvertently runs into M2 work, **stop**: that violates the milestone-close discipline (substrate gets confused if one session straddles two milestones). Defer M2 to the next session.

If a deliverable is blocked by something I need to decide, **stop and ask** — do not guess. Substrate work is more valuable when it sits on confirmed decisions than when it ships fast on assumptions.

---

## A note on this prompt itself

This prompt is the previous milestone (M0)'s handoff to the next (M1). The successor (`NEXT_PROMPT.md` v0.3 targeting M2) is itself a Step-5 deliverable. The prompt is substrate; it evolves milestone-by-milestone, informed by each retrospective. ADR-024 (RETRO artefact type) and ADR-025 (CONTEXT_PROTOCOL §8.3.1 amendment) make this loop explicit.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
