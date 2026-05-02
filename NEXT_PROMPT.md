# Session kickoff prompt — M2-IB.5 in-RTH validation + RETRO-M2-IB (paste this into a fresh Claude Code session)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are joining a disciplined project at the M2-IB.5 finish line

This project is `blive` — a *multi-broker* live algorithmic-execution engine, sibling to `btest`. Supported brokers via the [ADR-034](docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) multi-broker registry are **Interactive Brokers (IB)** and **IG**, plus paper / mock for development. Current integration milestone is M2-IB. Run by Oleg Roshka, a UK-based independent quant researcher.

The project practises **Cognitive Cartography**, a substrate-engineering discipline articulated in `CONTEXT_PROTOCOL.md` and the methodology paper at `docs/method/paper/cognitive_cartography.tex`. Every fact has one home; cross-references use stable IDs; decisions are append-only ADRs; questions are append-only OQs; status lifecycle is explicit; an edit protocol governs all changes.

**State at session entry** (commit `98bf997`, all on `origin/main`):

- **M2-IB.4a** is closed across three tags: `M2-IB.4a-rejected`, `M2-IB.4a-happy`, `M2-IB.4a-happy-cacpa`. The IB write side (`submit` / `cancel`) is fully wire-validated against IB Paper for both terminal-state paths (REJECTED via the Cancelled-with-errorCode disambiguation, and ACCEPTED → CANCELED via engine cancel after the operator applied the API → Precautions bypass for the direct-routing restriction).
- **M2-IB.5 prereqs** all shipped:
  - `scripts/refresh_eodhd_parquet.py` — fetches CAC.PA daily bars from EODHD into a `PaperMarketData`-compatible parquet at `~/.blive/data/eodhd/CAC.PA_1d.parquet`. **Already populated** (510 bars, ~2 trading years, last close 2026-04-30).
  - `src/blive/runtime/ib_pipeline.py` — broker-injected, signal-decoupled pipeline; 6 unit tests.
  - `src/blive/runtime/signals.py` — SMA-crossover stub producing the `position_series` the pipeline consumes; 7 unit tests.
  - `scripts/run_m2ib5_paper.py` — end-to-end driver wiring all three plus IBBroker.
- **M2-IB.5 architectural-surface wire run** (out-of-RTH, 2026-05-02 Saturday): 60-bar replay against IB Paper produced 35 SUBMITTED → ACCEPTED → CANCELED FSM cycles (orders held until next session via warning 399; pipeline timed out and engine-canceled each). Zero rejected, zero risk-engine breaches. FSM coverage validated except FILLED / PARTIAL_FILL — those need RTH.

**Today's mission** (this session):

1. Re-run `scripts/run_m2ib5_paper.py` during European market hours to exercise the FILLED / PARTIAL_FILL FSM paths against IB Paper at real venue prices.
2. Once clean, write `docs/retros/M2-IB_retrospective.md` per [`docs/retros/_template.md`](docs/retros/_template.md) and [CONTEXT_PROTOCOL §8.3.1](CONTEXT_PROTOCOL.md).
3. Replace this `NEXT_PROMPT.md` with v0.6 targeting M3 / Phase 2 entry per [ADR-025](docs/decisions/DECISIONS.md#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) §8.3.2 phase-boundary protocol.

---

## Step 1 — Warm-up (do this BEFORE any work, in order)

Per [CLAUDE.md](CLAUDE.md):

1. Read `CONTEXT_PROTOCOL.md` §0 TL;DR + §3 edit protocol + §3.5 anti-patterns.
2. Read `CONTEXT_INVENTORY.md` end-to-end — §10 priority queue is the load-bearing source of truth on current state. Note the M2-IB.5 sub-bullets, especially the "M2-IB.5 in-RTH FILLED validation" entry (the PENDING one).
3. Read `TASK_REGISTRY.md` M2-IB section — note the M2-IB.5 strategy-run + RETRO-M2-IB closing requirements.
4. Skim recent retros: `docs/retros/M0_retrospective.md`, `M1_retrospective.md`, `M2-IG_retrospective.md` (the IG bridge close — same pattern you'll mirror for M2-IB).
5. Skim the most recent commits: `git log --oneline -15` then read the bodies of `M2-IB.4a-happy-cacpa`, `M2-IB.5 prereq` trio, and the M2-IB.5 driver commit. Each commit message is intentionally rich — the wire findings + INV-14 codes + FSM coverage are all there.
6. Specifically read `src/blive/runtime/ib_pipeline.py`, `src/blive/runtime/signals.py`, `scripts/run_m2ib5_paper.py` — these are what you'll be running and reasoning about.

When you finish warm-up, reply with a 5-line summary:

```
Warm-up complete. I have read:
- [list the artefacts you read]

Project state: [M2-IB.4a closed across 3 tags; M2-IB.5 prereqs done;
M2-IB.5 architectural surface validated out-of-RTH; pending in-RTH
FILLED validation + RETRO-M2-IB.]

I propose to start by: [first concrete action]
```

Wait for "go" before producing code.

---

## Step 2 — Today's mission, in detail

### 2.1 Confirm prereqs are still in place

The wire setup needs:

- IB Gateway running on the operator's host, port 4002 (paper).
- "Read-Only API" unchecked under Configuration → API → Settings.
- "Bypass Order Precautions for API Orders" (item #1) ticked under Configuration → API → Precautions. (Item #7 "Bypass Redirect Order warning" was also ticked in the M2-IB.4a-happy-cacpa run; either way the master bypass #1 is what unblocks the direct-routing restriction at error 10311.)
- `~/.blive/secrets/ib.env` populated.
- `~/.blive/data/eodhd/CAC.PA_1d.parquet` populated (already there from 2026-05-02 run).

If anything has drifted — e.g., IB Gateway isn't running, or the operator restarted Windows and the bypass got reset — surface it before proceeding. Do NOT guess.

A quick handshake sanity check: `uv run python scripts/probe_ib_handshake.py` — should connect cleanly within 1s.

### 2.2 Run the in-RTH paper probe

```
uv run python scripts/run_m2ib5_paper.py
```

CAC.PA on SBF trades Mon–Fri 09:00–17:30 MET (07:00–15:30 UTC). Only run during those hours, otherwise you'll get the same "all canceled" outcome as the Saturday run.

Expected behaviour during RTH:

- Most regime-stable days: zero submits.
- Few regime-flip days: BUY or SELL submitted, real fill from IB Paper at *current* market (not historical close).
- The FSM should now traverse SUBMITTED → ACCEPTED → FILLED for at least some submits — the previously-unexercised wire path.

The script's `--max-bars 60` default keeps the run bounded. SMA(50) on a 60-bar capped window typically produces 0–3 transitions, so total submits will be small (in the Saturday run, 35 of 60 bars submitted — ~58% transition rate — because each submit was canceled and re-submitted on the next bar's still-long target. With actual fills in RTH, the holding state will reduce subsequent submits.)

Surface the `IBRunResult` summary block. Specifically check:

- `filled > 0` — confirms the FILLED path exercises.
- `rejected == 0` — bypass still works.
- `breaches == 0` — risk engine clean.
- Equity curve shows movement (cash debits / credits as fills happen).

### 2.3 If the run is clean: write `RETRO-M2-IB.md`

Per [`docs/retros/_template.md`](docs/retros/_template.md) and [CONTEXT_PROTOCOL §8.3.1](CONTEXT_PROTOCOL.md). Capture:

- **Gate status:** G3-IB exit criteria (per [TASK_REGISTRY.md](TASK_REGISTRY.md)) — checklist of: connect within 5s, positions match TWS UI, ≥ 100 ticks (n/a for daily; treat as "≥ 5 fills"), throttle test (rate-limiter behaviour), reconnect within 30s after Gateway restart, `refresh_artefact.py` round-trip (n/a for SMA stub; flag for the canonical TKAN run later).
- **Delivered vs plan:** the M2-IB.{1, 2, 3-prereq, 3a, 3a-resolved, 3b-i, 3b-i-timer, 3b-ii, 4a-rejected, 4a-happy, 4a-happy-cacpa, 5 prereqs, 5 driver, 5 architectural-surface, 5 in-RTH} ladder, with tags + dates.
- **Surprises:** the "10311 isn't bypassable" mistake → operator-applied bypass actually works; the post-acceptance disambiguation bug + fix; warning 399 ("order held until next session") behaviour outside RTH; the 35-submit pattern when no fills happen (each rebalance produces a fresh order since position never updates).
- **ADRs raised:** ADR-042 (session-bootstrap files; methodology amendment v0.3, in scope at M2-IB.5 close).
- **OQs raised:** none new this milestone (the SMART-routing convention noted in INV-14 §"Open Questions" is a planning concern, not formally OQ-ised yet).
- **Substrate transitions:** INV-14 v0.1 → v0.4 (codes 162, 200, 201, 202, 399, 10147, 10311 catalogued); KB-2 / KB-3 STABLE flip if the in-RTH run plus the existing wire history covers §1–§9 surfaces (it does for the read side; the write-side §3/§4/§6 surfaces are now exercised for MKT/LMT, DAY TIF, no algos used yet — pragmatic flip is fair). DD-7 already STABLE v1.0 from M2-IB.3a-resolved.
- **Recommendations for `NEXT_PROMPT.md` v0.6 (M3 / Phase 2 entry):** the M5+ daemon shape (real-time multi-day runner) is the natural next deliverable; phase-boundary protocol (CONTEXT_PROTOCOL §8.3.2) requires this session ends with the retro + gate report only — Phase 2 readiness audit is a separate session.

Frozen on first write — do NOT edit thereafter.

### 2.4 Update CONTEXT_INVENTORY priority queue and ship the retro commit

Mark the M2-IB.5 in-RTH bullet ✓ done with the tag (e.g. `M2-IB.5-rth-validated`). Add a final sub-bullet for "M2-IB.5 close" with the retro link.

Commit message lists `RETRO-M2-IB` (new), `CONTEXT_INVENTORY.md` (touched, status changes), `NEXT_PROMPT.md` (will be v0.6 in a separate commit), and the tag.

### 2.5 Phase-boundary handoff per CONTEXT_PROTOCOL §8.3.2

This session closes M2-IB. Per the phase-boundary protocol:

- This session ends with the retro + gate report. **Do NOT draft Phase 2 plan in this session.**
- The next session is the Phase 2 readiness audit (produces `docs/PHASE_2_READINESS.md` modelled on `docs/PHASE_1_READINESS.md`, informed by *real* outcomes from M2-IB).
- The session after that is plan-drafting for M3 / Phase 2.

So end this session by:

1. Pushing `RETRO-M2-IB` + tag to GitHub (`git push origin main && git push origin --tags`).
2. Reporting the G3-IB gate status as a checklist (passed / partial / blocked, reason per line).
3. Drafting `NEXT_PROMPT.md` v0.6 targeting the **Phase 2 readiness audit session** — this is the kickoff prompt for the next session, not a plan.

If the in-RTH run surfaces unexpected behaviour (rejections, breaches, latent bugs), surface and fix in this session before the retro.

---

## Step 3 — Discipline reminders

Same as the standing CLAUDE.md guidance:

- Stable IDs in conversation, code comments, commit messages.
- ADRs for architectural choices not already in `docs/decisions/DECISIONS.md`.
- Append-only — no editing past ADR / OQ / RETRO bodies.
- Status lifecycle: bump `last_reviewed` on every edit, `version` on substantive change.
- Commit messages list every artefact touched by stable ID.
- Trivial-fix lane only for typos / formatting — `RETRO-M2-IB` is decision-bearing, not trivial.

The post-acceptance disambiguation fix in `src/blive/adapters/ib/broker.py` (commit `5cf465d`) is load-bearing — don't accidentally regress it. Test `test_submit_emits_canceled_when_cancelled_post_acceptance_with_warning_in_log` is the canary.

---

## Step 4 — Hard constraints (out of scope)

- **Real-money trading.** M2-IB is paper only.
- **Real-time multi-day daemon shape** (the canonical "≥ 5 trading days unattended" run from REQUIREMENTS §14). M5+ scope; not in this session.
- **Phase 2 plan drafting.** Phase-boundary protocol forbids it (§8.3.2). The plan-drafting session comes after the readiness-audit session, which comes after this one.
- **TKAN real artefact.** Operator-deferred until end-to-end paper testing is done. SMA stub is sufficient for M2-IB close; TKAN comes back at Phase 2 entry.
- **Methodology paper revision.** Moved to a separate research project per the Amendments_Log v0.3 scope note (commit `eb74818`). Do NOT edit `docs/method/paper/cognitive_cartography.tex` here.

---

## Step 5 — Handoff (at session end)

Per CONTEXT_PROTOCOL §8.3 + §8.3.1 + §8.3.2:

1. Every artefact touched is committed; commit messages list artefacts by stable ID.
2. New `RETRO-M2-IB.md` has full frontmatter + a row in `CONTEXT_INVENTORY.md` §5.5 (Retrospectives table).
3. New ADRs in `docs/decisions/DECISIONS.md` and indexed (likely none, but check).
4. New OQs in `docs/decisions/OPEN_QUESTIONS.md` (likely none).
5. `NEXT_PROMPT.md` v0.6 drafted — focused on Phase 2 readiness audit (the next session).
6. Git tags pushed.
7. G3-IB gate status reported as a checklist.

If the in-RTH run is blocked (markets closed, IB Gateway not running, bypass got reset): stop, surface, do not invent workarounds.

---

## A note on this prompt itself

`NEXT_PROMPT.md` v0.5 (this) was authored at the M2-IB.5 architectural-surface stop on 2026-05-02 (Saturday) for the next-session in-RTH run. The successor (v0.6 targeting Phase 2 readiness audit) is a §8.3.2 deliverable at this session's close.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
