# Session kickoff prompt — M3.4: mixed-currency P&L reconciliation (Phase 1 deployment-decision milestone)

> **v1.4 (2026-06-05).** **M3.3 is closed** — [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) RESOLVED with **Option 1** ([ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1)): Phase 1 **accepts** the PMA-bound leveraged-leg non-fill (QQL3 0/69 fills vs IBTM 6/6) as a deployment characteristic, no code change; the leveraged-leg redesign is deferred to Phase 2 as [OQ-032](./docs/decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure). M3.4 now exercises the **live mixed-currency P&L surface** — QQL3 (USD) + IBTL / IBTM (GBP-hedged) on the GBP-base paper account — confirming MaintMargin / GrossPositionValue / NetLiquidation reconcile across the currency pair (M2-IB exercised these fields *synthetically*; M3.4 confirms the *live* shape per [RETRO-M2-IB §"Recommendations" #4](./docs/retros/M2-IB_retrospective.md)).

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

> **⚠️ This host has standing gotchas — read before running anything:**
>
> 1. **`uv run` is blocked by Smart App Control** (fails with "Application Control policy has blocked this file", os error 4551). Run blive via the **venv Python directly**:
>    `$env:PYTHONPATH = "C:\Users\olegr\PycharmProjects\blive\src"; & "C:\Users\olegr\PycharmProjects\blive\.venv\Scripts\python.exe" -m pytest` — likewise `scripts\foo.py`, `-m mypy src`, `-m black`, `-m isort`. Console-script `.exe`s under `.venv\Scripts\` (e.g. `lint-imports.exe`) run directly too.
> 2. **The IB paper account (`DUP886336`) is Cash + GBP-base** — load-bearing for M3.4. The mixed-currency surface is *already present*: GBP base, USD cash (FX-converted from GBP 2026-06-05), GBP-hedged IBTL / IBTM positions. USD-denominated **QQL3** needs USD cash; top up in TWS (type `GBP.USD`, pick **Forex / IDEALPRO** — *not* the CFD; "Override and Transmit" past the size-precaution warning) if "insufficient funds" recurs on the USD leg.
> 3. **The replay driver accumulates paper positions.** `run_m2ib6_ib_paper.py` starts each run from a fresh local $100k view, so it re-buys the Treasury legs every run and the paper account accumulates real IBTM/IBTL shares. Reset between campaigns with `scripts/flatten_ib_paper.py` (`--dry-run` to report first). For M3.4 you may *want* non-zero Treasury positions present (they are the GBP-hedged leg of the reconciliation) — flatten deliberately, not reflexively.

---

## You are the M3.4 session

`blive` is a multi-broker live execution engine, sibling to `btest`. Phase 1 is in its **deployment-decision milestone (M3)**. M3.1 + M3.1b CLOSED (ADR-050 unit-of-quote + ADR-051 tick-grid). M3.2 CAPTURE-COMPLETE. **M3.3 CLOSED** (OQ-031 → ADR-052, Option 1). M3.4 is the **live mixed-currency P&L reconciliation** — an operator-driven account-snapshot observation, not a code milestone (the fields already exist; M3.4 confirms the *live* shape).

Follow **Cognitive Cartography**: one fact has one home; stable IDs (`ADR-*` / `INV-*` / `DD-*` / `OQ-*`) are mandatory; ADRs / OQs / RETROs are append-only; `CONTEXT_INVENTORY.md` + `TASK_REGISTRY.md` must stay aligned with reality.

### State at session entry

- **M3.3 closed** (commit at session entry): [ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) ACCEPTED (OQ-031 Option 1 — accept the leveraged-leg non-fill; **no code change**); OQ-031 OPEN → RESOLVED-BY-ADR-052; [OQ-032](./docs/decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) raised (Phase 2 leveraged-leg redesign — full design space incl. the leverage-preserving margin-on-a-1×-UCITS path); `refined-by: ADR-052` backref on ADR-043 + ADR-047. G4 exit-criterion #1 ✓ MET.
- **Substrate:** DECISIONS v0.23; OPEN_QUESTIONS v0.5; TASK_REGISTRY v0.12; CONTEXT_INVENTORY v0.20; INV-8 / INV-9 DRAFT v0.1; INV-14 v0.9; DD-7 v1.5; DD-2 v0.2; KB-6 v0.1.
- **Tests: 590** green; mypy `src` / lint-imports green; black / isort clean on the M3.x-touched files (M3.3 changed **no Python**). ⚠️ **Pre-existing full-tree drift (not M3.x's):** repo-wide `black --check` / `isort --check-only` flag ~15 files in the `adapters/ig/*` + `adapters/shared/{rate_limiter,credentials}` cluster (committed in the M2-IG era — the M3.1b "env-drift" note). Unrelated to the M3 docs work, not fixed here; candidate for a dedicated formatting commit (check for a black-version mismatch first). There is **no** active local `.git/hooks/pre-commit`, so it does not block commits — but a CI full-tree gate would catch it.
- **All ADRs ACCEPTED** except ADR-021 (SUPERSEDED-BY-ADR-043). No PROPOSED ADRs in the working tree.

### What M3.4 produces

A **live observation** that the mixed-currency account math reconciles: with QQL3 (USD) and IBTL / IBTM (GBP-hedged) positions present on the GBP-base paper account, the `AccountSnapshot` fields **MaintMargin / GrossPositionValue / NetLiquidation** are internally consistent across the currency pair and match the synthetic shape M2-IB exercised. The 30s diff-suppress `AccountUpdate` emission timer (per [ADR-033](./docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence)) is the observation surface. Substrate (only if the live shape reveals something new): **DD-2** v0.2 → v0.3 (mixed-currency footnote); **KB-6** v0.1 → v0.2 (currency-pair section). If the live fields reconcile cleanly with no new surface, M3.4 closes with the observation logged and no substrate change beyond the milestone ledger.

### ⚠️ The M3.4 wrinkle created by ADR-052 (read before planning)

G4 exit-criterion #4 wants **QQL3 (USD) at a non-zero position** simultaneously with the GBP-hedged Treasury legs. But ADR-052 / OQ-031 just established that **QQL3 does not fill via the engine** (PMA cap / Adaptive non-fill). So a QQL3 USD *position* cannot be acquired through a normal `run_m2ib6_ib_paper.py` run. Resolve this deliberately — options for the operator:
- **(a) Manually acquire a small QQL3 position in TWS** (a human-placed marketable / aggressive-LMT order — may partial-fill in a favourable tick even under the cap; accept whatever fills). Gives a true QQL3 USD position line.
- **(b) Reconcile on the existing mixed state** — USD *cash* (from the FX conversion) + GBP base + GBP-hedged IBTL / IBTM positions is *already* a mixed-currency account; the MaintMargin / GrossPositionValue / NetLiquidation reconciliation is observable without a QQL3 position, with the QQL3-position-absent line explicitly noted as a consequence of ADR-052.
- **(c) Note the limitation** and reconcile what is observable, deferring a full QQL3-position-present observation to whenever a QQL3 position is acquired (e.g. under the Phase-2 OQ-032 redesign).

This is a genuine consequence of the OQ-031 resolution — surface it in the warm-up summary; don't quietly assume a QQL3 fill will materialise.

### Scope (M3.4)

1. **Operator brings up IB Gateway during/after an LSE-RTH window** with IBTL / IBTM positions present (a fresh `run_m2ib6_ib_paper.py` run re-buys them; or they already sit on the account), and a QQL3 USD position per option (a)/(b)/(c) above.
2. **Capture an `AccountSnapshot`** (via the read-side broker / the 30s `AccountUpdate` timer surface) with both currencies live; verify MaintMargin / GrossPositionValue / NetLiquidation reconcile across USD + GBP-hedged + GBP-base.
3. **Record the observation**; amend DD-2 / KB-6 only if the live shape reveals a surface not already covered (e.g. an FX-reval or hedged-share-class nuance).

**Out of scope (M3.4):** M3.5 (INV-14 extension + chaos drills + KB-7 stub) / M3.6 (KB-2 / KB-3 STABLE flip) — later M3 sub-milestones; M3-close (RETRO-M3 + G4 report) after those. The Phase-2 leveraged-leg redesign is **OQ-032**, not an M3 task.

### Step 1 — Warm-up (before any code/substrate edit)

Per [CLAUDE.md](./CLAUDE.md): read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) §0/§3/§3.5; [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) (v0.20 banner + §10 priority queue); [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) **M3.4** + the G4 gate; [DD-2 event_schemas](./docs/dd/event_schemas.md) (`AccountUpdate` shape, per ADR-033); [KB-6 cost_margin_dictionary](./docs/kb/cost_margin_dictionary.md) (currency / financing sections); [RETRO-M2-IB §"Recommendations" #4](./docs/retros/M2-IB_retrospective.md) (the synthetic-vs-live mixed-currency gap M3.4 closes); [ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) (the M3.3 resolution that creates the QQL3-position wrinkle); [ADR-048 §"side-finding"](./docs/decisions/DECISIONS.md) (IBTL/IBTM resolve to GBP-hedged accumulating share classes — the source of the currency mix). Reply with the standard **5-line warm-up summary** and **wait for "go"** before any edit.

### Step 2 — At session end

1. Commit (surface the message draft first, per [CLAUDE.md](./CLAUDE.md)). Run the gates via the venv Python (see the host-gotchas banner).
2. Update [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) §10 + [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) M3.4 with the observation + any DD-2 / KB-6 transition.
3. Replace this `NEXT_PROMPT.md` with **v1.5 targeting M3.5 (INV-14 catalogue extension + chaos drills + KB-7 stub-DRAFT)**.

### Discipline reminders

- Stable IDs in conversation, comments, commit messages.
- M3.4 is an **observation**, not a decision — likely no new ADR (unlike M3.3). If the live mixed-currency shape forces an architectural choice, *then* draft a PROPOSED ADR, surface, wait.
- Append-only ADR / OQ / RETRO bodies. The QQL3-position wrinkle (above) is a real consequence of ADR-052 — don't paper over it.
- When in doubt: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
