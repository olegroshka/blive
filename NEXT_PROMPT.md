# Session kickoff prompt — M3.2: Empirical paper-mode window (10 LSE-RTH trading days)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

> **⚠️ This host has two standing gotchas — read before running anything:**
>
> 1. **`uv run` is blocked by Smart App Control** (fails with "Application Control policy has blocked this file", os error 4551). Run blive via the **venv Python directly**:
>    `$env:PYTHONPATH = "C:\Users\olegr\PycharmProjects\blive\src"; & "C:\Users\olegr\PycharmProjects\blive\.venv\Scripts\python.exe" -m pytest` — likewise `scripts\foo.py`, `-m mypy src`, `-m black`, `-m isort`. Console-script `.exe`s under `.venv\Scripts\` (e.g. `lint-imports.exe`) run directly too.
> 2. **The IB paper account (`DUP886336`) is Cash + GBP-base.** USD-denominated **QQL3** needs USD cash; it was funded 2026-06-05 via a GBP→USD FX conversion. If "insufficient funds" recurs on the USD leg, top up in TWS (type `GBP.USD`, pick **Forex / IDEALPRO** — *not* the `GBP.USD` CFD; "Override and Transmit" past the size-precaution warning).

---

## You are the M3.2 session

`blive` is a multi-broker live execution engine, sibling to `btest`. Phase 1 is in its **deployment-decision milestone (M3)**. **M3.1 (EODHD-vs-IB unit-of-quote, [ADR-050](./docs/decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only)) and M3.1b (order-price tick-grid normalization, [ADR-051](./docs/decisions/DECISIONS.md#adr-051--normalize-ib-order-prices-to-the-contract-tick-grid-at-submit-time)) are CLOSED** — both ADRs ACCEPTED, wire-validated 2026-06-05 (QQL3 now sizes correctly *and* places on its 0.10 tick grid with **zero IB error 110**). This `NEXT_PROMPT.md` v1.1 targets **M3.2 — the empirical paper-mode window**.

Follow **Cognitive Cartography**: one fact has one home; stable IDs (`ADR-*` / `INV-*` / `DD-*` / `OQ-*`) are mandatory; ADRs / OQs / RETROs are append-only; `CONTEXT_INVENTORY.md` + `TASK_REGISTRY.md` must stay aligned with reality.

### State at session entry

- **HEAD = the M3.1 + M3.1b close commit** (ADR-050 + ADR-051 ACCEPTED). Substrate: DECISIONS v0.22; CONTEXT_INVENTORY v0.16; TASK_REGISTRY v0.8; INV-14 v0.9; DD-7 v1.5.
- **All ADRs ACCEPTED** except ADR-021 (SUPERSEDED-BY-ADR-043). No PROPOSED ADRs in the working tree.
- **Tests: 568** green; mypy `src` / black / isort / lint-imports all green.
- **OQ-031 OPEN** — Phase 1 deployment under the PMA-bound retail account; resolves at **M3.3** on M3.2's evidence.
- **The wire path is now clean** (no error 110, no rejections; QQL3 places on-grid; IBTM fills). The open empirical question M3.2 answers: **QQL3's fill-rate under the structural 2161 PMA cap** (the 5 QQL3 LMTs in the M3.1b validation reached ACCEPTED→CANCELED without filling — that's the OQ-031 signal, on now-correctly-sized orders).

### What M3.2 produces

A **10-LSE-RTH-trading-day empirical dataset** of paper-mode runs on the QQL3 / IBTL / IBTM universe, capturing **per run/day**:

- per-instrument **fill-rate** (placed vs filled),
- **regime-flip count** (long vs short equity-leg signal),
- **warning-2161 cap-binding** events (the OQ-031 signal),
- **RiskEngine breach** count,
- **FSM-trace coverage** (SUBMITTED → ACCEPTED → FILLED / CANCELED / REJECTED ratio).

**Exit:** a data file ready for the **M3.3 OQ-031 resolution** (operator chooses the deployment mode on this evidence).

### Scope

1. **Results capture (code).** Add a lightweight per-run results sink — append one structured row (JSON/CSV) per run under `~/.blive/data/m3_2_window/` — so the 10-day window aggregates without manual log-scraping. Source the fields from `IBMultiRunResult` (counts, `fills_by_symbol`, `breaches`) plus the observed 2161 cap-binding events. Wire it into `scripts/run_m2ib6_ib_paper.py` (or a thin M3.2 wrapper).
2. **INV-8 `metrics` MISSING → DRAFT v0.1** — catalogue the **M3.2 metrics only** (fill-rate, regime-flip, 2161 cap-binding, breach count, FSM-trace ratio); the full Prometheus stack stays M7.
3. **INV-9 `alerts` MISSING → DRAFT v0.1** — catalogue the **M3.2 alerts only** (kill-switch / RiskEngine breach); full alerting stays M7.
4. **Run the window (operator-driven).** During LSE RTH, across 10 trading days: bring up IB Gateway (or TWS) with the API enabled, **"Read-Only API" OFF**, **"Bypass Order Precautions for API Orders" ON**; run `run_m2ib6_ib_paper.py --order-type LMT --max-bars 5` (or the M3.2 wrapper); capture the results row each day.

**Out of scope (M3.2):** OQ-031 resolution (M3.3); the M5 real-time daemon (the "10 days" here is 10 operator-driven runs, **not** an unattended daemon); full Prometheus / alerting (M7); strategy or universe changes.

### Step 1 — Warm-up (before any code)

Per [CLAUDE.md](./CLAUDE.md): read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) §0/§3/§3.5; [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) (v0.16 banner + §10 priority queue); [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) **M3.2** sub-milestone; [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account); [INV-14 v0.9](./docs/inv/ib_error_codes.md) (error 110's two now-fixed sub-causes; warning 2161); INV-8 / INV-9 (MISSING — M3.2 creates the stubs). Skim `src/blive/runtime/ib_pipeline.py` (`IBMultiRunResult` shape) and `scripts/run_m2ib6_ib_paper.py`. Reply with the standard **5-line warm-up summary** and **wait for "go"** before code.

### Step 2 — At session end

1. Commit (surface the message draft first, per [CLAUDE.md](./CLAUDE.md)). Run the gates via the venv Python (see the host-gotchas banner).
2. Update [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) §10 + [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) M3.2 with what shipped + the window's progress.
3. Replace this `NEXT_PROMPT.md` with **v1.2 targeting M3.3 (OQ-031 resolution)** once the 10-day dataset is complete.

### Discipline reminders

- Stable IDs in conversation, comments, commit messages.
- ADRs only for genuinely architectural choices (the M3.2 results-sink shape is likely a refinement, not an ADR — but if a real fork arises, draft `PROPOSED`, surface, wait).
- Append-only ADR / OQ / RETRO bodies; M3.x sub-milestone descriptions can be updated as the milestone executes.
- When in doubt: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
