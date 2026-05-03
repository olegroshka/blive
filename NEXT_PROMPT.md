# Session kickoff prompt — M2-IB.6.2 PRIIPs probe + LSE-RTH validation (paste into a fresh Claude Code session)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are joining a disciplined project mid-M2-IB.6.2

This project is `blive` — a *multi-broker* live algorithmic-execution engine, sibling to `btest`. Supported brokers via the [ADR-034](docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) multi-broker registry are **Interactive Brokers (IB)** and **IG**, plus paper / mock for development. Current integration milestone is M2-IB.6 (multi-instrument paper run for the Phase 1 A3 strategy `triple_lev_sma_filter_dsl` per [ADR-043](docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)). Run by Oleg Roshka, a UK-based independent quant researcher.

The project practises **Cognitive Cartography**, a substrate-engineering discipline articulated in `CONTEXT_PROTOCOL.md` and the methodology paper at `docs/method/paper/cognitive_cartography.tex`. Every fact has one home; cross-references use stable IDs; decisions are append-only ADRs; questions are append-only OQs; status lifecycle is explicit; an edit protocol governs all changes.

**State at session entry** (most-recent commit on `origin/main`: `c34267d` — *"M2-IB.6.2 Path A: LSE-ETF SMART routing + IBTL/IBTM GBP currency"*):

- **M2-IB.4a / M2-IB.5 closed** earlier; substrate path through M2-IB.6.1 landed: ADR-043, ADR-044, ADR-045, ADR-046, ADR-047 all ACCEPTED; the multi-instrument pipeline + LongShortPortfolio btest dispatch + IB resolver SMART routing for US equities are wire-validated.
- **M2-IB.6.1 wire run (Sun 2026-05-03)** against the original ADR-043 universe (TQQQ / TMF / IEF) produced **104 PRIIPs / KID rejections** (IB error 201, reason text *"This product does not have a KID in English…"*). [ADR-047](docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) substituted UK-listed analogues: **QQL3** (3× Nasdaq-100 ETP), **IBTL** (1× 20+yr US-Treasury UCITS — *no UK 3× US-Treasury exists; strategy regime shifts 3×/3× → 3×/1×*), **IBTM** (1× 7-10yr US-Treasury UCITS). All on LSE.
- **M2-IB.6.2 wire smoke (Sun 2026-05-03, post-ADR-047)** initially returned IB error 200 on every order against the new universe — `XLON → "LSE"` direct routing was wrong: IB exposes UCITS / ETPs on `LSEETF`, a distinct venue. Probed via `reqContractDetails` and confirmed all three resolve via `Contract(exchange="SMART", primaryExchange="LSEETF")`.
  - **QQL3** → conId 566361457, currency USD ("3X US TECH 100").
  - **IBTL** → conId 181150859, currency **GBP** ("ISHARES USD TRES 20+yr" GBP-hedged accumulating).
  - **IBTM** → conId 68489974,  currency **GBP** ("ISHARES USD TREASURY 7-10Y" GBP-hedged accumulating).
- **Resolver fix landed in `c34267d`**: `XLON + ETF → SMART/primaryExchange=LSEETF`; `XLON + EQUITY` keeps direct `LSE` routing. `IBTL` / `IBTM` Instrument records updated to `currency="GBP"`. Phase 1 P&L is now mixed-currency on the IB side; the M7 parity envelope absorbs the divergence (already noted in ADR-047).
- **Re-run of `scripts/run_m2ib6_ib_paper.py --max-bars 5`** produced **submitted 10 / accepted 10 / canceled 10 / rejected 0 / breaches 0**: contracts resolve cleanly, no PRIIPs / KID surfaces under the LSE universe, all orders reach `PreSubmitted` and warning 399 ("order held until 2026-05-05 09:00 MET"), then engine-cancel at the 10s timeout because LSE is closed (Sun + UK May Day Bank Holiday Mon).
- **ADR-048 PROPOSED is drafted but UNCOMMITTED** in the working tree. It codifies the LSE-ETF SMART discriminator (`XLON + ETF → SMART/LSEETF`) as a refinement of ADR-046. Held PROPOSED-uncommitted until Tuesday's LSE RTH window actually produces fills. See **operator decision tree** below.
- **Today's wire status**: `c34267d` is the head; ADR-048 changes sit in working tree as uncommitted modifications to `docs/decisions/DECISIONS.md`. `git status` will show this; do not stash or revert without reading the rest of this prompt.

**Open question driving this session** (uncommitted as of session entry; see [decision tree](#today-decision-tree)): is **PRIIPs / KID** genuinely a hard regulatory block on TQQQ / TMF / IEF for the operator's UK retail IB Paper account, *or* could the M2-IB.6.1 weekend run have surfaced PRIIPs reason text under conditions where the underlying cause was actually market-time? The answer determines whether ADR-047 (universe substitution) is empirically validated or speculatively over-applied.

---

## Today's mission

A two-day operational window:

| Day | Wire test | Purpose | Time window (UTC) |
|---|---|---|---|
| **Mon 2026-05-04** | `scripts/probe_tqqq_us_rth.py` (single-shot) | Validate ADR-047 PRIIPs premise | NYSE/NASDAQ open: 13:30–20:00 UTC |
| **Tue 2026-05-05** | `scripts/run_m2ib6_ib_paper.py --max-bars N` | M2-IB.6.2 LSE RTH fills | LSE open: 07:00–15:30 UTC |

**Decision tree:**

1. **Mon probe → REJECTED with PRIIPs / KID reason text** (expected; exit code 0):
   - ADR-047 premise validated empirically.
   - Proceed to Tuesday LSE RTH run.
   - Expect fills on the eligible legs (eligibility from `~/.blive/data/signals/triple_lev_sma_eligible.parquet`).
   - On Tuesday fills: flip ADR-048 PROPOSED → ACCEPTED in same commit as DD-7 §3 amendment, then close M2-IB.6 with a retro.

2. **Mon probe → REJECTED with non-PRIIPs reason** (mis-attribution; exit code 1):
   - Stop. Capture the reason text. Re-investigate ADR-047.
   - Possible paths: revisit the substitution (Path C — full revert), or amend ADR-047 with the corrected cause.
   - Do NOT proceed to Tuesday run until ADR-047 is re-grounded.

3. **Mon probe → ACCEPTED / FILLED** (major surprise; exit code 4):
   - PRIIPs is somehow not enforced under this wire path.
   - Stop. Investigate possible causes (IB Paper relaxation? account misclassification? pre-existing transient?).
   - May warrant reverting ADR-047 + ADR-048 PROPOSED entirely; original TQQQ / TMF / IEF universe back in scope.
   - Do NOT proceed to Tuesday run; the substrate-of-record needs revision first.

4. **Mon probe → no terminal event / inconclusive** (exit code 5):
   - Re-run later in the same RTH window with cleaner conditions (warmer cache, no recent restart).
   - If still inconclusive after a second attempt: surface to operator and consult before Tuesday.

The probe is in `scripts/probe_tqqq_us_rth.py` (committed at session entry). Single LMT BUY of 1 share of TQQQ at $1 (won't fill if accepted; cancel cycle handles ACCEPTED defensively). Run at any point during US RTH on Monday.

The Tuesday run is the existing `scripts/run_m2ib6_ib_paper.py` — re-fire as-is. The fixture data at `~/.blive/data/eodhd/` and `~/.blive/data/signals/` is current as of 2026-05-03; refresh isn't strictly needed but is safe (`uv run python scripts/refresh_eodhd_signals.py`).

---

## Step 1 — Warm-up (do this BEFORE any work, in order)

Per [CLAUDE.md](CLAUDE.md):

1. Read `CONTEXT_PROTOCOL.md` §0 TL;DR + §3 edit protocol + §3.5 anti-patterns.
2. Read `CONTEXT_INVENTORY.md` end-to-end — §10 priority queue is the load-bearing source of truth on current state.
3. Read `TASK_REGISTRY.md` M2-IB.6 section — note the .6.1 / .6.2 / .6-close ladder.
4. Skim:
   - [ADR-043](docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) — Phase 1 strategy switch.
   - [ADR-046](docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) — US-equity SMART pattern (the shape ADR-048 mirrors).
   - [ADR-047](docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) — PRIIPs-compliant universe (load-bearing for this session's probe).
   - [ADR-048 PROPOSED](docs/decisions/DECISIONS.md#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046) — LSE-ETF SMART discriminator (UNCOMMITTED in working tree).
   - [INV-14 v0.5](docs/inv/ib_error_codes.md) — error 201 PRIIPs-KID variant.
   - [KB-9 §5.5](docs/kb/uk_regulatory.md) — PRIIPs / KID for UK retail clients.
5. Read commit body of `c34267d` (the resolver-fix commit) — it captures the `reqContractDetails` probe output that motivates ADR-048.
6. Read `scripts/probe_tqqq_us_rth.py` end-to-end — understand the three-outcome decision tree before firing it.
7. Read `scripts/run_m2ib6_ib_paper.py` (especially the Instrument-records block) and `scripts/refresh_eodhd_signals.py`.

When you finish warm-up, reply with a 5-line summary:

```
Warm-up complete. I have read:
- [list the artefacts you read]

Project state: [M2-IB.6.2 mid-validation; PRIIPs probe + LSE RTH run pending;
ADR-048 PROPOSED uncommitted; current head c34267d.]

I propose to start by: [first concrete action — typically running the Mon probe
during US RTH if today is Mon during 13:30-20:00 UTC, else surfacing the wait]
```

Wait for "go" before producing code or firing wire actions.

---

## Step 2 — Today's mission, in detail

### 2.1 Confirm prereqs are still in place

The wire setup needs:

- IB Gateway running on the operator's host, port 4002 (paper).
- "Read-Only API" unchecked under Configuration → API → Settings.
- "Bypass Order Precautions for API Orders" (item #1) ticked under Configuration → API → Precautions. (For LSE ETFs via SMART/LSEETF this isn't strictly required — SMART avoids the direct-routing precaution at error 10311 — but keep it ticked from the M2-IB.4a-happy-cacpa setup.)
- `~/.blive/secrets/ib.env` populated.
- `~/.blive/data/eodhd/{QQL3,IBTL,IBTM,QQQ,TLT}_1d.parquet` populated (already there from 2026-05-03 refresh).
- `~/.blive/data/signals/triple_lev_sma_eligible.parquet` populated (same refresh).

If anything has drifted — e.g., IB Gateway isn't running, or the operator restarted Windows and the bypass got reset — surface it before proceeding. Do NOT guess.

A quick handshake sanity check: `uv run python scripts/probe_ib_handshake.py` — should connect cleanly within 1s.

### 2.2 Monday: PRIIPs validation probe (US RTH)

```
uv run python scripts/probe_tqqq_us_rth.py
```

US RTH is 13:30–20:00 UTC Mon–Fri while the US is in daylight saving (which 2026-05-04 is). Outside that window the probe warns and runs anyway, but the signal is less clean — IB may surface different reason text for pre/post-RTH submission.

Read the printed terminal block. The probe self-classifies the outcome and prints a recommendation. Cross-reference the recommendation against the [decision tree](#todays-mission). Do NOT proceed past the Monday probe until the outcome is unambiguous.

If the probe surfaces something ambiguous (e.g. REJECTED with a reason fragment that's unclear), capture the raw event.reason verbatim and surface to the operator.

### 2.3 If Monday's probe was conclusive PRIIPs → Tuesday LSE RTH run

```
uv run python scripts/refresh_eodhd_signals.py     # safe; idempotent if already populated
uv run python scripts/run_m2ib6_ib_paper.py        # default --max-bars 60 is fine
```

LSE RTH is 07:00–15:30 UTC Mon–Fri (08:00–16:30 BST during summer). Note 2026-05-04 is a UK Bank Holiday so Tuesday 2026-05-05 is the first available window post-substitution.

Expected behaviour:

- Per the eligibility frame, days alternate among `{QQL3 + IBTL}`, `{QQL3 + IBTM}`, `{QQL3 + IBTL + IBTM}` (always 2 active legs unless both filter out, then 100% IBTM safe-haven). Equal-weighted per-row.
- Order-of-magnitude: with `--max-bars 60` (~3 months of replay), expect tens of submits across 2 instruments per day × N regime-flip days.
- The FSM should now traverse SUBMITTED → ACCEPTED → FILLED for at least some submits — the previously-unexercised wire path for LSE.
- `rejected == 0` (PRIIPs is gone with the substitution).
- `breaches == 0` (risk engine clean).
- Mixed-currency P&L: positions in QQL3 settle USD, IBTL / IBTM settle GBP. The `equity_curve` block reports a base-currency-converted total; surface if anything looks off.

### 2.4 If Tuesday's run produced fills: flip ADR-048 + close M2-IB.6

Single commit batch:

1. ADR-048 status PROPOSED → ACCEPTED (`docs/decisions/DECISIONS.md` — body unchanged per append-only rule; flip the status field + add a PROPOSED→ACCEPTED date trail in the ADR header; bump the changelog with v0.18).
2. **DD-7 §3 amendment**: split XLON into two rows by `asset_class` — `XLON + EQUITY → LSE` (direct), `XLON + ETF → SMART / primaryExchange=LSEETF`. Bump DD-7 frontmatter version + changelog.
3. **INV-14**: add an annotation on error 200 documenting the LSE-ETF-against-bare-LSE empirical regression marker (one-line bullet in the existing 200 row's "Operator action" cell).
4. **CONTEXT_INVENTORY** §10 priority queue: tick M2-IB.6.2 ✓; add M2-IB.6-close as the new front-of-queue.
5. Commit, push, tag (`M2-IB.6.2-rth-validated`).

Then write `docs/retros/M2-IB.6_retrospective.md` per [`docs/retros/_template.md`](docs/retros/_template.md). Capture:

- Gate status: G3-IB exit criteria checklist for the multi-instrument case (connect, positions match TWS UI for 3 instruments, ≥ 5 fills across the 3 legs, throttle clean).
- Delivered vs plan: M2-IB.{6-substrate, 6.1-resolver, 6.1-pipeline, 6.1-driver, 6.1-wire-PRIIPs, 6.2-resolver-LSEETF, 6.2-rth-validated} ladder with tags + dates.
- Surprises: PRIIPs / KID hard block on UK retail (M2-IB.6.1 finding, formalised in ADR-047 + KB-9 §5.5); LSE main-book vs LSE-ETF distinct IB venues (M2-IB.6.2 probe, formalised in ADR-048); IBTL / IBTM exposed as GBP-hedged share classes only on LSEETF (mixed-currency P&L surprise).
- ADRs raised in this milestone: ADR-043 (Phase 1 switch), ADR-044 (multi-instrument pipeline), ADR-045 (LongShortPortfolio dispatch), ADR-046 (US-equity SMART), ADR-047 (PRIIPs universe), ADR-048 (LSE-ETF SMART).
- OQs raised: 0 new (all unknowns resolved by ADRs in-flight).
- Substrate transitions: INV-1 row, INV-14 v0.4 → v0.5, KB-9 v0.1 → v0.2 (PRIIPs §5.5 added), DD-7 §3 amended (twice — XLON for Phase 1 use in v1.2, then split-by-asset_class in v1.3 at ADR-048 flip).

Frozen on first write — do NOT edit thereafter.

### 2.5 If Tuesday surprises (no fills despite RTH; new reject codes; FSM breakage): stop and surface

Do not paper over surprises. The whole point of the RTH validation is to catch what the smoke can't. Capture, surface, do not invent workarounds.

### 2.6 Phase-boundary handoff per CONTEXT_PROTOCOL §8.3.2

If M2-IB.6 closes cleanly Tuesday, the next step is a Phase 2 readiness audit (separate session — **do NOT draft Phase 2 plan in this session**). Replace this `NEXT_PROMPT.md` with v0.8 targeting that audit.

---

## Step 3 — Discipline reminders

Same as the standing CLAUDE.md guidance:

- Stable IDs in conversation, code comments, commit messages.
- ADRs for architectural choices not already in `docs/decisions/DECISIONS.md`.
- Append-only — no editing past ADR / OQ / RETRO bodies. ADR-048 status flip is a *header-field change*; the body stays untouched.
- Status lifecycle: bump `last_reviewed` on every edit, `version` on substantive change.
- Commit messages list every artefact touched by stable ID.
- The Mon probe is **diagnostic, not architectural** — its result feeds the operator decision; it is not itself an ADR-bearing event.

---

## Step 4 — Hard constraints (out of scope)

- **Real-money trading.** M2-IB is paper only.
- **Real-time multi-day daemon shape** (the canonical "≥ 5 trading days unattended" run from REQUIREMENTS §14). M5+ scope; not in this session.
- **Phase 2 plan drafting.** Phase-boundary protocol forbids it (§8.3.2).
- **Path B (IDTL / IDTM USD share classes) substitution.** Decided to defer per the operator's "Path A first, B after" — not in scope unless Monday's probe forces a re-think.
- **Methodology paper revision.** Out of scope per Amendments_Log v0.3.

---

## Step 5 — Handoff (at session end)

Per CONTEXT_PROTOCOL §8.3 + §8.3.1 + §8.3.2, depending on outcome:

**If Monday's probe was conclusive AND Tuesday's run produced fills:**

1. ADR-048 PROPOSED → ACCEPTED + DD-7 §3 amendment + INV-14 annotation + CONTEXT_INVENTORY tick — single commit batch.
2. RETRO-M2-IB.6 written + frontmatter + index-row in CONTEXT_INVENTORY §5.5.
3. Tag `M2-IB.6.2-rth-validated` pushed.
4. NEXT_PROMPT.md v0.8 drafted — focused on Phase 2 readiness audit (next session).
5. G3-IB gate status reported as a checklist.

**If Monday's probe was non-PRIIPs or surprising:**

1. Stop. Capture observation. Do not commit Tuesday-conditional substrate.
2. Surface to operator with the captured reason text + recommended next step (revert / amend / probe-deeper).
3. Leave NEXT_PROMPT.md unchanged — the next session continues the diagnosis.

**If Tuesday surprises with no fills despite RTH:**

1. Same as above — do not commit ADR-048 ACCEPTED flip.
2. Capture, surface, plan a follow-up wire test or substrate revision.

In all cases: every artefact touched is committed; commit messages list artefacts by stable ID; uncommitted ADR-048 changes in the working tree must be either staged (on success) or stashed/reverted (on revisit) — never silently discarded.

---

## A note on this prompt itself

`NEXT_PROMPT.md` v0.7 (this) was authored at the M2-IB.6.2 wire-finding stop on 2026-05-03 (Sunday) for the Mon probe + Tue RTH window. The successor (v0.8 targeting Phase 2 readiness audit if M2-IB.6 closes; or vN targeting the diagnosis path if it doesn't) is a §8.3.2 deliverable at the close session.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
