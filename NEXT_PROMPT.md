# Session kickoff prompt — Phase 2 readiness audit (M3 → M4 / Phase 1 → Phase 2 boundary)

> **v1.5 (2026-06-05).** **M3 is CLOSED — G4 PASSED** (all 10 exit criteria; see [RETRO-M3](./docs/retros/M3_retrospective.md)). M3 → M4 is the **Phase 1 → Phase 2 boundary**, which per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) needs a **three-session** transition: (1) implementation close ✓ [done at M3 close]; (2) **this session — readiness audit**; (3) plan-drafting. This session **refreshes** [`docs/PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) (DRAFT v0.1, written at the M2→Phase-2 boundary *before* M3's outcomes) against M3's **real** empirical artefacts, and may raise new OQs. **It is an audit, single-mode — it does NOT draft the Phase-2 plan or write code** (that mode-mixing is the §8.3.2-forbidden drift).

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

> **⚠️ Standing host gotchas (no Gateway/code needed this session, but keep for reference):**
>
> 1. **`uv run` is blocked by Smart App Control.** Run via the venv Python directly: `$env:PYTHONPATH = "...\src"; & "...\.venv\Scripts\python.exe" -m pytest` (likewise mypy / black / isort). Formatters are now **pinned** (`black==26.3.1`, `isort==8.0.1`) — a full-tree `black --check` is clean.
> 2. **The IB paper account (`DUP886336`) is Cash + GBP-base** with USD cash from a GBP→USD FX. Load-bearing for the trilemma below.
> 3. **`scripts/probe_ib_reconnect.py`** is the M3.5 chaos-drill fixture; **`scripts/probe_ib_account_ccy.py`** dumps raw per-currency account values (M3.4).

---

## You are the Phase-2 readiness-audit session

`blive` is a multi-broker live execution engine, sibling to `btest`. **Phase 1 is complete** (M0 → M3; G4 PASSED). This is the **second** of the three §8.3.2 phase-boundary sessions: refresh the Phase-2 readiness audit with what M3 actually taught us, so the *third* session can draft the Phase-2 plan on solid ground.

Follow **Cognitive Cartography**: one fact has one home; stable IDs mandatory; ADRs / OQs / RETROs append-only; substrate stays aligned with reality.

### State at session entry

- **M3 CLOSED 2026-06-05; G4 PASSED.** Commits: `d4f7bfd` (M3.3 OQ-031), `5166e20` (formatter pin), `3a0ce2a` (M3.4 equity fix), `a2c78f5` (M3.5 chaos), + the M3-close commit (KB-2/KB-3 STABLE + RETRO-M3 + this prompt). On branch `session/2026-06-05-m3.2-capture`.
- **Substrate:** DECISIONS v0.23 (ADR-001..052 ACCEPTED except ADR-021 SUPERSEDED); OPEN_QUESTIONS v0.5 (OQ-031 RESOLVED-BY-ADR-052; **OQ-032 OPEN**); TASK_REGISTRY v0.15; CONTEXT_INVENTORY v0.23; KB-2 / KB-3 **STABLE v1.0**; KB-7 / KB-15 / INV-8 / INV-9 DRAFT v0.1; INV-14 v0.10; DD-1 v0.3; DD-7 v1.5.
- **Tests 591** green; mypy `src` / black / isort / lint-imports all green (full-tree).
- **No PROPOSED ADRs** in the working tree.

### The M3 outcomes the audit must fold into PHASE_2_READINESS

1. **The leverage trilemma (OQ-032).** A UK-retail **Cash** account has **no** open path to leveraged equity exposure: **PRIIPs/KID** blocks US-domiciled leveraged ETPs (ADR-047), the **PMA cap (2161)** blocks UK-listed leveraged ETPs (ADR-049/OQ-031), and a **Cash** account blocks margin-financed leverage. Phase 2 must pick a lever — the leverage-preserving margin-on-a-1×-UCITS path (needs a **Margin** account + its own no-PMA validation), Pro-Client, de-lever, or restructure. This is OQ-032, resolved in **session 3**, not here.
2. **The incoming strategy** (operator's `lab/research/r_lev_001_triple_leveraged_etf` deep-analysis notebook): a **VIX term-structure** (contango/backwardation, UX6/UX1) strategy on **TQQQ / VXX / IEF** — needs **VIX-futures data (UX1/UX6)** blive doesn't source yet, adds a vol ETP (VXX), and is *more* leverage/vol-dependent — it reinforces the trilemma. New data + universe + signal + execution-access scope.
3. **The M5 reconnect gap (KB-7 FM-1).** No native disconnect detection / auto-reconnect; `IBBroker.is_connected` goes stale; recovery needs `disconnect()+connect()`; a Gateway restart raises IB **10141** (paper-trading disclaimer) + a `clientId`-in-use transient. A multi-day live run needs at least the minimal `disconnectedEvent` fix; full watchdog + continuous reconciliation = M5.
4. **The M3.4 equity fix.** `AccountSnapshot.equity` now reads the consolidated `BASE` total (was the base-currency sleeve), so NAV-slice sizing / RiskEngine can trust it — but the Phase-1 driver still sizes off a synthetic $100k view; wiring live equity into sizing is M4/M5.
5. **The structural QQL3 non-fill** (ADR-052) — Phase 1 deployed accepting it (Treasury-dominated); Phase 2's redesign is where the strategy regains a tradeable equity leg.

### Scope (this session)

1. **Refresh `docs/PHASE_2_READINESS.md`** (DRAFT v0.1 → v0.2): re-audit each dimension against the M3 outcomes above; mark what M3 *answered* vs what's *newly open*; surface the Phase-2-entry questions (the agenda for session 3's plan-drafting).
2. **Raise OQs** for anything the audit surfaces (e.g. VIX-futures data sourcing, the Margin-account decision) — append-only, with target = Phase 2 entry.
3. **Do NOT** draft the Phase-2 `TASK_REGISTRY` plan, resolve OQ-032, or write code — those are session 3 (plan-drafting) / Phase-2 implementation.

**Optional (operator's call):** the §6.4 freeze ceremony — snapshot `CONTEXT_INVENTORY.md` to `docs/_freezes/M3-CONTEXT_INVENTORY.md` + a `git tag` at the M3-close commit. (Flagged in RETRO-M3's discipline recommendations.)

### Step 1 — Warm-up

Per [CLAUDE.md](./CLAUDE.md): read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) §0/§3/§8.3.2; [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) (v0.23 banner + §10); [`docs/PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) (the artefact to refresh); [RETRO-M3](./docs/retros/M3_retrospective.md) (the outcomes + recommendations); [OQ-032](./docs/decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure); skim the `r_lev_001` notebook for the incoming-strategy shape. Reply with the standard **5-line warm-up summary** and **wait for "go"**.

### Step 2 — At session end

1. Commit (surface the message draft first). Substrate-only session — no gates beyond markdown consistency.
2. Replace this `NEXT_PROMPT.md` with **v1.6 targeting the Phase-2 plan-drafting session** (session 3: operator resolves OQ-032 + the audit's OQs; agent drafts the Phase-2 plan with the notebook as input).

### Discipline reminders

- **Single mode (audit only).** No plan-drafting, no code — §8.3.2.
- Stable IDs everywhere; OQs get target dates; append-only ADR/OQ/RETRO bodies.
- When in doubt: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
