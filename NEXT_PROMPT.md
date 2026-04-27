# Session kickoff prompt — paste this into a fresh Claude Code session

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are joining a disciplined project

This project is `blive` — a live algorithmic-execution engine for Interactive Brokers, sibling to `btest` (research backtesting framework). It is run by Oleg Roshka, a UK-based independent quant researcher.

The project practises **Cognitive Cartography**, a substrate-engineering discipline articulated in `docs/method/paper/cognitive_cartography.tex`. In short: every fact has one home; cross-references use stable IDs; decisions are append-only ADRs; questions are append-only OQs; status lifecycle is explicit; an edit protocol governs all changes.

You will read the discipline (and the M0+M1 substrate that you are extending) before working. You will then plan. Only then will you produce code.

---

## Step 1 — Warm-up (do this BEFORE any work, in order)

Read the following files. Do **not** skim. Stop and re-read if anything is unclear.

1. **`CONTEXT_PROTOCOL.md`** — at minimum §0 (TL;DR). The protocol governs every edit you will make. The trivial-fix lane is in §3.4. Anti-patterns are in §3.5.
2. **`CONTEXT_INVENTORY.md`** — the registry of every knowledge artefact. Read it end-to-end. The §10 "Outstanding queue" tells you where the project is right now (M2 is the next concrete milestone).
3. **`TASK_REGISTRY.md`** — the Phase 1 plan. Today's work is the **M2 milestone** in that file. Read M2 in full. Skim M3 for context. Note the G3 gate at the end of M2.
4. **`docs/retros/M0_retrospective.md`** and **`docs/retros/M1_retrospective.md`** — the M0 and M1 close retrospectives. The "Recommendations for NEXT_PROMPT M_{N+1}" and "Surprises" sections in particular contain hard-won notes from prior sessions that will save you time. The M1 retro flags **OQ-030** (btest-interpreter dispatch for non-LongShort archetypes) which you'll likely need to settle this session.
5. **`REQUIREMENTS.md`** — re-read §5.2 (live market data + pacing), §5.7 (reconciliation: startup form is M2), §6.1 (latency NFRs), §10 (IB-specific gotchas), §12 (operational model — Docker, IBC, daily TWS restart).
6. **`docs/decisions/DECISIONS.md`** — read **ADR-002 (`ib_async` v2.1+)**, **ADR-004 (hexagonal + import-linter)**, **ADR-005 (single-process asyncio kernel)**, **ADR-014 (data sources via clean abstraction)**, **ADR-017 (hybrid EODHD + IB streaming)**, **ADR-022 (TKAN freshness)** and **ADR-023 (TKAN artefact path)** in full. These are load-bearing for M2 design choices.
7. **`docs/kb/ib_capability_matrix.md`** (KB-2) — focus on §1 (asset classes), §2 (order types), §5 (routing), §6 (market data tiers), §8 (account types).
8. **`docs/kb/ib_pacing_spec.md`** (KB-3) — full read; M2 is where these limits become operational. The 50-msg/s throttle, historical-data pacing (≤60/10min, BID_ASK ×2), market-data subscription tiers, and the daily 23:45 ET restart are all M2 concerns.
9. **`docs/kb/frameworks_survey.md`** (KB-4) — re-skim the `ib_async` adoption rationale and the patterns we lift from NautilusTrader.
10. **`docs/inv/risk_checks.md`** (INV-4) — M2 doesn't widen the RC set (that's M4), but the M2 pipeline-level RC-08 negative test that was deferred at M1 close lands here when real-streaming bars introduce variable lag.
11. **The M0+M1 substrate you are extending**: `docs/dd/domain_objects.md` (DD-1 STABLE), `docs/dd/config_schemas.md` (DD-3 DRAFT), `docs/inv/order_state_transitions.md` (INV-13 STABLE), `docs/inv/ports_adapters.md` (INV-6 STABLE — adapter status tracker now reflects M1 implementations), `docs/inv/domain_events.md` (INV-5 STABLE — `DomainEvent` widens with `AccountUpdate` + `ArtefactFreshnessWarning` at M2).
12. **The M0+M1 code baseline**: skim `src/blive/{domain,strategy,sizing,risk,runtime}/*.py` and `src/blive/adapters/{paper,memory,clock,alert}/*.py` so you know what already exists. Then skim `tests/` so you know the M0+M1 test patterns; M2 tests should follow them.

When you finish warm-up, **before proposing any work**, reply to me with a 5-line summary:

```
Warm-up complete. I have read:
- [list the artefacts you read]

Project state: [G2 status, current milestone, key architectural commitments, what's already built]

I propose to start M2 by: [first concrete action]
```

Wait for my "go" before producing code.

---

## Step 2 — Today's mission: Milestone M2 (IB Adapter — Read Side & Operational Foundation)

Per `TASK_REGISTRY.md` M2 (canonical source — do not paraphrase from this prompt, read the file).

**Goal:** blive connects to IB Paper, reads positions / account values / market data; the operational stack (Docker, IBC, rate limiter) is in place. blive runs with `PaperBroker` for execution but reads real positions via `IBBroker`; the two views match.

**Deliverables (9 items, condensed — full list in TASK_REGISTRY.md M2):**

1. **IB Paper account verified** (operator action) — credentials available; `clientId` chosen; documented in a private `secrets/` location not under version control.
2. **IB Gateway via Docker** (e.g. `gnzsnz/ib-gateway-docker`) operational — auto-restart on failure; pinned offline TWS installer per [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events); IBC configured.
3. **EODHD subscription verified** — CAC index daily history reachable via `eodhd://` test fetch.
4. **`IBBroker` adapter — read methods** (`adapters/ib/broker.py`) — `connect()`, `disconnect()`, `positions()`, `account_snapshot()`, `open_orders()`, `events()`. All outbound calls pass through a token-bucket rate limiter (default 20 msg/sec global per [KB-3 §1](./docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle)).
5. **`IBMarketData` adapter — read methods** (`adapters/ib/market_data.py`) — `subscribe_bars()`, `historical_bars()`. Historical pacing per [KB-3 §2](./docs/kb/ib_pacing_spec.md#2-historical-data-pacing).
6. **`EODHDDataSource`** registered in btest's data source registry (`adapters/eodhd/`) — `eodhd://...` URL scheme resolves to delayed/historical fetch.
7. **`scripts/refresh_artefact.py`** (per [ADR-023](./docs/decisions/DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership)) — copy + checksum + record TKAN artefact freshness.
8. **PaperBroker → real-IB-Paper read-mirror harness** — blive runs with PaperBroker for execution but reads positions via IBBroker; the two views match.
9. **Reconnect logic** — disconnect / reconnect cycles tested by stopping/starting the IB Gateway container.

**Substrate transitions at M2 close:**

- `KB-2`, `KB-3` STABLE confirmed (or amended if reality-checked against the live IB API).
- `INV-14` (IB error codes) **MISSING → DRAFT** as observed-rejects accumulate.
- `KB-8` (operational events: daily TWS restart, IBC weekly token, holidays) **MISSING → DRAFT**.
- `INV-5` widens with `AccountUpdate` (M2 row) and `ArtefactFreshnessWarning` (M2 row) — both already catalogued, now implemented.
- `DD-7` (instrument dictionary — blive `Instrument` ↔ IB `Contract` / `ConID`) **MISSING → DRAFT**.

**Exit criteria (G3 gate):**

- blive connects to IB Paper Gateway within 5 s of process start.
- `positions()` returns the same set TWS UI shows (manual eyeball check).
- Subscribe to CAC.PA bars; receive ≥ 100 ticks within RTH.
- Throttle test: simulate burst of 60 calls/sec; outbound rate stays ≤ 20 msg/sec.
- Disconnect IB Gateway mid-session; blive detects within 30 s; reconnects when Gateway returns.
- `refresh_artefact.py` round-trip: copy a fresh `pred_cache.pkl` from btest output; observe checksum recorded; observe RC-12 freshness check passes.

**Operator-side prerequisites for G2 → M2 transition (verify before starting M2 code):**

- IB Paper account commissioned; credentials accessible.
- **EODHD subscription for CAC.PA** — ✓ verified at M1 close (2026-04-27): daily EOD + delayed real-time confirmed in tier. **Small open follow-up for M2:** the CAC 40 *index* ticker on EODHD is not `CAC.INDX` (404). When wiring `EODHDDataSource`, try `PX1.INDX` / `^FCHI`. Index feed is nice-to-have for parity-residual decomposition; ETF path (ADR-021) is sufficient on its own.
- Deployment target chosen (Linux VM vs Windows host).
- The G2 ±1 bps real-data parity test against `tkan_v4_momentum_timing` 1× × 252 days of CAC.PA history closed (the M1 retro left this PARTIAL — the pipeline is ready, what's missing is the EODHD CAC.PA fixture + the TKAN `pred_cache.pkl` artefact + the `cact_momentum.parquet` factor file). The G2 parity run is best done *after* the EODHD probe confirms CAC.PA daily history is in tier.

If any of these are not yet ready, surface it in your warm-up summary and we'll resolve before code lands.

---

## Step 3 — Discipline reminders

Every edit you make — to substrate or code — follows **CONTEXT_PROTOCOL §3**:

- **Pre-edit:** READ the inventory → IDENTIFY SSOT for the fact you're changing → IMPACT-CHECK by walking `referenced_by`.
- **During:** stable IDs in cross-refs (`KB-N`, `ADR-N`, `OQ-N`); no paraphrasing other artefacts (link instead); minimum-surface change.
- **Post-edit:** bump `last_reviewed`; bump `version` if substantive; if status changed, update `CONTEXT_INVENTORY.md`; if the edit reflects a new architectural choice, write the corresponding **ADR** in the same commit; if it raises a question that can't be resolved in line, write the corresponding **OQ**.
- **Commit messages** list every artefact touched, by stable ID.

The **trivial-fix lane** (§3.4) exists for typos / formatting / link fixes. M2 is *not* a trivial-fix scenario; use the full lane.

If you find yourself about to make an architectural choice that isn't already captured in ADR-001..029, **stop**: write the proposed ADR with status `PROPOSED`, surface it to me, and wait for confirmation before committing. Likely M2 candidates for new ADRs:

- **OQ-030 resolution** — amend ADR-010 prose to acknowledge `SingleAssetRunner` (or settle on per-archetype dispatch as the canonical pattern). Pick at G2 review or early M2.
- **Token-bucket rate limiter shape** — algorithmic choice (token bucket vs sliding window vs leaky bucket), per-strategy vs global accounting, persistence behaviour on restart.
- **Instrument resolution policy** (DD-7) — how blive `Instrument(symbol, venue, currency, asset_class)` maps to IB `Contract`. Caching strategy for `ConID` lookups; fallback behaviour when ambiguous.
- **`AccountUpdate` payload shape** (DD-2 entry) — what IB pushes into the snapshot subscription, and what blive normalises into a `DomainEvent` payload.
- **EODHD adapter URL semantics** — the exact `eodhd://...` query grammar and how it resolves to EODHD's REST shape.

If you discover a new question whose answer matters for M2, file an OQ rather than guessing.

Use the task-tracking primitives (TaskCreate / TaskUpdate / TaskList) to track multi-artefact edits as a coherent unit.

---

## Step 4 — Hard constraints (out of scope)

These belong to later milestones; do **not** start them in this session:

- `IBBroker` **write** methods (`submit`, `cancel`, `replace`) — those land at M3. M2 is read-side only.
- Real-money trading. M2 is IB *Paper* only.
- Full RiskEngine with all RCs (RC-01..RC-07, RC-10, RC-11 — the M2 subset stays at M1's RC-08/09/12/13) — M4.
- SQLite persistence — M4.
- Continuous reconciliation loop — M5. (Startup reconciliation diff per REQUIREMENTS §5.7 is in M2 scope; the 60s tick loop is M5.)
- Web UI — M6.
- Parity diagnostic — M7.
- Kill-switch UI / REST surface (the `KillSwitch.clear()` confirmation token) — M4.

If you find an M2 design choice forces an early decision about M3+ architecture, capture it as an ADR (don't pre-build).

---

## Step 5 — Handoff (at session end)

Standard handoff per CONTEXT_PROTOCOL §8.3:

1. Every artefact touched is **committed**, with the commit message listing artefacts by stable ID.
2. Every new artefact created has frontmatter (id, title, status, owner, last_reviewed, version, sources, depends_on, referenced_by) and a row in `CONTEXT_INVENTORY.md`.
3. Status changes (DRAFT → STABLE) are reflected both in the artefact itself and in `CONTEXT_INVENTORY.md`.
4. Any new ADRs are in `docs/decisions/DECISIONS.md` and indexed in its top table.
5. Any new OQs are in `docs/decisions/OPEN_QUESTIONS.md`.
6. `TASK_REGISTRY.md` reflects M2 progress (which deliverables done, which blocked, why).

**Additional milestone-close steps** per CONTEXT_PROTOCOL §8.3.1 (applies because this session closes M2):

7. **Write a retrospective** at `docs/retros/M2_retrospective.md`, copying the structure from `docs/retros/_template.md`. Capture: G3 gate status (six exit criteria as a checklist), delivered-vs-plan, surprises, ADRs/OQs raised this milestone, substrate transitions, effort vs estimate, recommendations for the M3 NEXT_PROMPT. Status STABLE on first write; do not edit afterwards.
8. **Write `NEXT_PROMPT.md` v0.4** targeting M3, informed by the retrospective. Most of this current prompt's warm-up files stay the same in v0.4; the Step 2 "Today's mission" is rewritten for M3 (IB write side + first live-paper run); Step 3 discipline reminders stay; Step 4 out-of-scope updates (M2 read methods drop off; `IBBroker` write methods *in* at M3; first 5-day live-paper run *in* at M3).
9. **Report the G3 gate status back to me** as a checklist in chat — passed / partial / blocked, with reason on each line.

If this session inadvertently runs into M3 work, **stop**: that violates the milestone-close discipline (substrate gets confused if one session straddles two milestones). Defer M3 to the next session.

If a deliverable is blocked by something I need to decide, **stop and ask** — do not guess. Substrate work is more valuable when it sits on confirmed decisions than when it ships fast on assumptions.

---

## Notes carried over from M1

The M1 retro flagged the following items as worth your attention from the start; they don't necessarily belong in M2 scope but they shape M2 design choices:

- **`PortfolioEngine` is a free function `compute_target_weights_for_date()`, not a class.** ADR-010 / KB-1 prose still says "PortfolioEngine"; treat that as a known imprecision until OQ-030 resolves.
- **Per-archetype dispatch (OQ-030).** TimingPortfolio strategies go through `quantdsl_backtest.runners.single_asset.SingleAssetRunner`; LongShortPortfolio strategies go through `compute_target_weights_for_date()`. M2 doesn't add archetypes but should not paint itself into a corner that assumes only one of the two dispatch paths.
- **Pipeline-level RC-08 deferred from M1.** The M1 SimClock-vs-bar invariant left zero staleness delta; the unit test in `tests/unit/risk/test_checks.py` proves the check works. M2's real-streaming bars introduce variable lag — the missing pipeline-level RC-08 negative test should land here.
- **`PaperMarketData` fixture format** (`open_time_utc`, `close_time_utc`, `open`, `high`, `low`, `close`, `volume`, optional `vwap`). Future fixtures must follow this schema; consider DD-8 *fixture_format* if a second consumer (the EODHD fetch script) lands.
- **`KillSwitch.clear()` is unguarded in M1.** M4 adds the confirmation token. M2 doesn't need to touch it, but the IB-disconnect auto-arm path (REQUIREMENTS §5.5: disconnect > 30 s arms) is the first M2 caller of `KillSwitch.arm()`.

---

## A note on this prompt itself

This prompt is the previous milestone (M1)'s handoff to the next (M2). The successor (`NEXT_PROMPT.md` v0.4 targeting M3) is itself a Step-5 deliverable. The prompt is substrate; it evolves milestone-by-milestone, informed by each retrospective. ADR-024 (RETRO artefact type) and ADR-025 (CONTEXT_PROTOCOL §8.3.1 amendment) make this loop explicit.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
