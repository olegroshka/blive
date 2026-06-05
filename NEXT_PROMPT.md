# Session kickoff prompt — M3.3: OQ-031 resolution (Phase 1 deployment-mode decision)

> **v1.3 (2026-06-05).** **M3.2 is capture-complete** — its bounded deterministic capture criterion is met: ≥ 1 flip-spanning RTH run is in `~/.blive/data/m3_2_window/runs.jsonl` with **QQL3 fill-rate ≈ 0 and the Treasury leg (IBTM) ~100%**. M3.3 now **resolves [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account)** — the Phase 1 deployment-mode decision — on that evidence, recording the chosen option as a new ADR.

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

> **⚠️ This host has standing gotchas — read before running anything:**
>
> 1. **`uv run` is blocked by Smart App Control** (fails with "Application Control policy has blocked this file", os error 4551). Run blive via the **venv Python directly**:
>    `$env:PYTHONPATH = "C:\Users\olegr\PycharmProjects\blive\src"; & "C:\Users\olegr\PycharmProjects\blive\.venv\Scripts\python.exe" -m pytest` — likewise `scripts\foo.py`, `-m mypy src`, `-m black`, `-m isort`. Console-script `.exe`s under `.venv\Scripts\` (e.g. `lint-imports.exe`) run directly too.
> 2. **The IB paper account (`DUP886336`) is Cash + GBP-base.** USD-denominated **QQL3** needs USD cash; it was funded 2026-06-05 via a GBP→USD FX conversion. If "insufficient funds" recurs on the USD leg, top up in TWS (type `GBP.USD`, pick **Forex / IDEALPRO** — *not* the `GBP.USD` CFD; "Override and Transmit" past the size-precaution warning).
> 3. **The replay driver accumulates paper positions.** `run_m2ib6_ib_paper.py` starts each run from a fresh local $100k view, so it re-buys the Treasury legs every run and the paper account accumulates real IBTM/IBTL shares. Reset between campaigns with `scripts/flatten_ib_paper.py` (`--dry-run` to report first). Cosmetic on paper, but flatten before a fresh capture if you want clean account state.

---

## You are the M3.3 session

`blive` is a multi-broker live execution engine, sibling to `btest`. Phase 1 is in its **deployment-decision milestone (M3)**. M3.1 + M3.1b are CLOSED (ADR-050 unit-of-quote + ADR-051 tick-grid, ACCEPTED). **M3.2 is capture-complete** (bounded deterministic capture per plan-call #6). M3.3 is the **operator-led OQ-031 resolution**: choose the Phase 1 deployment mode and record it as a new ADR.

Follow **Cognitive Cartography**: one fact has one home; stable IDs (`ADR-*` / `INV-*` / `DD-*` / `OQ-*`) are mandatory; ADRs / OQs / RETROs are append-only; `CONTEXT_INVENTORY.md` + `TASK_REGISTRY.md` must stay aligned with reality.

### State at session entry

- **M3.2 capture-complete** (commit at session entry): the per-run results sink (`src/blive/runtime/m3_2_record.py` → `~/.blive/data/m3_2_window/runs.jsonl`) + the additive capture surface on `IBMultiRunResult` / `IBBroker.observed_error_codes` / `signals.equity_leg_regime_flips` landed; ≥ 1 flip-spanning RTH capture row exists; `scripts/flatten_ib_paper.py` added for paper-account reset.
- **Substrate:** DECISIONS v0.22; CONTEXT_INVENTORY v0.19; TASK_REGISTRY v0.11; INV-8 / INV-9 DRAFT v0.1; INV-14 v0.9; DD-7 v1.5.
- **Tests: 590** green; mypy `src` / black / isort / lint-imports all green.
- **OQ-031 OPEN** — resolves THIS session.
- **All ADRs ACCEPTED** except ADR-021 (SUPERSEDED-BY-ADR-043). No PROPOSED ADRs in the working tree.

### The M3.2 evidence (the OQ-031 input)

Real LSE-RTH paper captures on 2026-06-05 (`runs.jsonl`), `triple_lev_sma_filter_dsl` on QQL3 / IBTL / IBTM, MKT (QQL3 → ADAPTIVE_MKT), flip-spanning windows:

- **QQL3 (3× leveraged equity leg): fill-rate ≈ 0** — every order ACCEPTED then engine-cancelled on timeout, **0 fills** across all submitted. The structural non-fill the M2-IB.6.2c matrix predicted, now confirmed on now-correctly-sized orders (no error 110, no rejects, no breaches).
- **IBTM (1× Treasury leg): fill-rate ~100%** — fills cleanly at market.
- **Nuance for the write-up:** `cap_binding_2161_count = 0` on the ADAPTIVE_MKT runs (`mktCapPrice` stayed 0.0). So the QQL3 non-fill here was *the Adaptive order not crossing within the wait*, **not** a *visible* 2161 cap — unlike the raw-MKT M2-IB.6.2c runs where 2161 fired. The **non-fill is the load-bearing fact regardless of mechanism**; "Adaptive doesn't trip the visible cap yet still doesn't fill" is itself an OQ-031 finding. (Read the actual rows; do not restate from memory.)

### What M3.3 produces

**OQ-031 RESOLVED** — a new ADR (next free index after ADR-051) records the operator's chosen deployment-mode option, with the supersedes / amends chain as applicable; OQ-031 flips OPEN → RESOLVED-BY-ADR-NNN. The decision must be auditable: **data (`runs.jsonl`) → option chosen → why.**

### The four OQ-031 options (operator chooses)

Per [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account), with the M3.2 evidence bearing on each:

1. **Accept the cap as a real Phase-1 deployment characteristic** (working default). Document the regime-dependent (here: ~never) QQL3 fill profile; deploy A3 understanding the equity leg rarely/never fills, so live behaviour is Treasury-leg-dominated. **No code change.** The 0% QQL3 fill makes this concrete: the live strategy ≈ the Treasury legs alone.
2. **Pursue MiFID II Professional Client classification** (enables `priceManagementOff`). Operator declined at M2-IB.6.1; revisit only if Option 1's profile is unacceptable.
3. **Substitute the leveraged equity leg with a non-leveraged analogue.** Materially changes the strategy (1×/1× vs intended 3×/1×); amends [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) + [ADR-047](./docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); needs a universe re-validation half-session. The 0% QQL3 fill is the strongest argument *for* this option.
4. **Restructure as a passive-limit-only strategy** that accepts the cap as the execution model. Needs a fresh ADR + re-derived parity envelope.

### Scope (M3.3)

1. **Operator decides** among options 1–4 on the `runs.jsonl` evidence.
2. **Agent drafts the resolution ADR** (PROPOSED → surface → ACCEPTED on operator confirm), records the data → option → why chain, flips OQ-031 → RESOLVED-BY-ADR-NNN in [OPEN_QUESTIONS](./docs/decisions/OPEN_QUESTIONS.md), updates [TASK_REGISTRY](./TASK_REGISTRY.md) M3.3.
3. **If Option 3:** reserve a half-session for the ADR-043/047 amendment + universe re-validation (a non-leveraged UK-listed equity analogue; re-run `--dry-run` regime check + an RTH capture on the new leg).

**Out of scope (M3.3):** M3.4 (mixed-currency P&L reconciliation) / M3.5 (INV-14 extension + chaos drills + KB-7 stub) / M3.6 (KB-2 / KB-3 STABLE flip) — later M3 sub-milestones; M3-close (RETRO-M3 + G4) after those.

### Step 1 — Warm-up (before any ADR/code)

Per [CLAUDE.md](./CLAUDE.md): read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) §0/§3/§3.5 + §5 (ADR discipline); [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) (v0.19 banner + §10 priority queue); [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) **M3.2** (capture-complete) + **M3.3**; [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) (the 4 options); [INV-14 v0.9](./docs/inv/ib_error_codes.md) (warning 2161 = the PMA cap); the M2-IB.6.2c matrix in INV-14 (raw-MKT 2161 firing, vs the M3.2 Adaptive runs). **Read the actual `~/.blive/data/m3_2_window/runs.jsonl` rows** — the evidence is data, not memory. Reply with the standard **5-line warm-up summary** and **wait for "go"** before drafting the ADR.

### Step 2 — At session end

1. Commit (surface the message draft first, per [CLAUDE.md](./CLAUDE.md)). Run the gates via the venv Python (see the host-gotchas banner).
2. Update [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) §10 + [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) M3.3 with the resolution + OQ-031 status flip.
3. Replace this `NEXT_PROMPT.md` with **v1.4 targeting M3.4 (mixed-currency P&L reconciliation)** — or, if Option 3 was chosen, the universe-re-validation follow-up first.

### Discipline reminders

- Stable IDs in conversation, comments, commit messages.
- **OQ-031 resolution is genuinely decision-bearing → it gets an ADR** (unlike the M3.2 sink/re-scope, which were refinements). Draft PROPOSED, surface, wait for operator confirm before ACCEPTED.
- Append-only ADR / OQ / RETRO bodies; flip OQ-031's status field only (don't edit its body).
- When in doubt: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
