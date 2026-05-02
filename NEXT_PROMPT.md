# Session kickoff prompt — M2-IB resumption (paste this into a fresh Claude Code session)

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

## You are joining a disciplined project mid-pivot

This project is `blive` — a *multi-broker* live algorithmic-execution engine, sibling to `btest` (research backtesting framework). Supported brokers via the [ADR-034](docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) multi-broker registry are **Interactive Brokers (IB)** and **IG**, plus paper / mock for development. The current integration focus this milestone is IB (M2-IB); IG is also a first-class supported broker (the M2-IG.5 strategy-run sub-milestone was deferred, but the IG adapter code in repo is supported, not archived). Run by Oleg Roshka, a UK-based independent quant researcher.

The project practises **Cognitive Cartography**, a substrate-engineering discipline articulated in `docs/method/paper/cognitive_cartography.tex`. In short: every fact has one home; cross-references use stable IDs; decisions are append-only ADRs; questions are append-only OQs; status lifecycle is explicit; an edit protocol governs all changes.

**The pivot you're inheriting** (read this first):

- M0 + M1 closed cleanly (paper-mode pipeline, 175 tests, RETRO-M0 / RETRO-M1).
- M2 was originally a single milestone (IB read side). When the IB Paper account was unavailable in late April 2026, the project ran a 2-session **IG demo bridge** (M2-IG) to exercise the multi-broker abstraction against a non-paper venue. The bridge shipped at architectural surface (~359 tests, broker-agnostic shared modules, IG-specific code, Lightstreamer abstraction) but **was never run against IG's actual servers** — it closed at architectural surface when the IB Paper account became available on **2026-04-28** (enabled 2026-04-29).
- The **IG bridge's primary dividend** was the cross-cutting architectural work — broker registry ([ADR-034](docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)), secrets handling ([ADR-035](docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)), `Instrument.tradability` field ([ADR-037](docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet)), `blive.adapters.shared.{rate_limiter, credentials}`, `blive.runtime.broker_registry`. **All of this transfers to IB unchanged.** M2-IB is now scaffolded by what M2-IG built.
- The **M2-IG-specific code** (`blive.adapters.ig.*`, KB-16, KB-17, DD-8, ADR-036/038/039) is preserved in repo as durable reference. It is **not** active and has no scheduled revival.

You will read the discipline (and the M0+M1+M2-IG substrate that you are extending) before working. You will then plan. Only then will you produce code.

---

## Step 1 — Warm-up (do this BEFORE any work, in order)

Read the following. Do **not** skim. Stop and re-read if anything is unclear.

1. **`CONTEXT_PROTOCOL.md`** — at minimum §0 (TL;DR). The protocol governs every edit you will make. The trivial-fix lane is in §3.4. Anti-patterns are in §3.5.
2. **`CONTEXT_INVENTORY.md`** — the registry of every knowledge artefact. Read it end-to-end. The §10 "Outstanding queue" tells you where the project is right now (M2-IB resumption is the active path).
3. **`TASK_REGISTRY.md`** v0.3 — the Phase 1 plan. Today's work is **M2-IB.1** (substrate verification, then move to .2 if everything checks out). Read M2-IB in full. Skim M3 — note the M2-IB.4-vs-M3 consolidation note.
4. **`docs/retros/M2-IG_retrospective.md`** — **read this in full**. It captures what the IG bridge built, what was deferred, and the §"Recommendations" section maps M2-IG's file structure 1:1 onto M2-IB equivalents. It is the load-bearing piece of context for this session.
5. **`docs/retros/M0_retrospective.md`** and **`docs/retros/M1_retrospective.md`** — earlier retros for the substrate + pipeline patterns.
6. **`REQUIREMENTS.md`** — re-read §5.2 (live market data + pacing), §5.7 (reconciliation: startup form is M2; continuous loop is M5), §6.1 (latency NFRs), §10 (12 IB-specific gotchas), §12 (operational model — Docker, IBC, daily TWS restart).
7. **`docs/decisions/DECISIONS.md`** — read **ADR-002** (`ib_async` v2.1+), **ADR-004** (hexagonal + import-linter), **ADR-005** (single-process asyncio kernel), **ADR-014** (data sources), **ADR-017** (hybrid EODHD + IB streaming — note IG-streaming part is now archived), **ADR-021** (CAC.PA ETF on IB — **canonical Phase 1 strategy now reasserted**), **ADR-022** + **ADR-023** (TKAN), **ADR-027** (Sizer integer-share rounding for spot), **ADR-031** (token-bucket rate limiter — algorithm shipped, IB defaults pending ACCEPTED flip), **ADR-032** (instrument resolution policy: blive.Instrument ↔ IB Contract / ConID — pending ACCEPTED flip), **ADR-033** (AccountUpdate cadence), **ADR-034** (multi-broker registry — ACCEPTED at M2-IG.1; **the substrate that makes M2-IB easy**), **ADR-035** (secrets handling — applies to IB credentials too), **ADR-037** (`Instrument.tradability` — spot is the IB path), **ADR-039** (Phase 1 strategy under IG bridge — ACCEPTED but bridge-paused; not the canonical path).
8. **`docs/kb/ib_capability_matrix.md`** (KB-2 v0.1.1) — read §1, 2, 5, 6, 8.
9. **`docs/kb/ib_pacing_spec.md`** (KB-3 v0.1.1) — full read; numerical limits power the rate limiter's IB defaults table you'll write at M2-IB.2.
10. **`docs/kb/operational_events.md`** (KB-8 v0.2) — read §1–§5 (IB-side) + §8.5 (IG-vs-IB comparison; the IG side is reference now).
11. **`docs/kb/frameworks_survey.md`** (KB-4) — re-skim the `ib_async` adoption rationale.
12. **`docs/inv/risk_checks.md`** (INV-4) — full set; M2-IB.4 work touches RC-08 / RC-09 / RC-12 / RC-13 (already implemented at M1) and starts to inform RC-05 / RC-06 (the M4 widening).
13. **The substrate you are extending**: `docs/dd/domain_objects.md` (DD-1 STABLE v0.2 — `Instrument.tradability` field), `docs/dd/config_schemas.md` (DD-3 DRAFT v0.2 — top-level `broker` field), `docs/dd/instrument_dictionary.md` (DD-7 DRAFT v0.1 — IB-specific; STABLE flip at M2-IB.3 first Contract resolution), `docs/dd/event_schemas.md` (DD-2 DRAFT v0.1), `docs/dd/ig_instrument_dictionary.md` (DD-8 DRAFT v0.1 — IG analogue, **archived**; read for the parallel pattern), `docs/inv/order_state_transitions.md` (INV-13 STABLE), `docs/inv/ports_adapters.md` (INV-6 STABLE v0.3 — IG rows present, IB rows MISSING-PARKED → MISSING-ACTIVE), `docs/inv/domain_events.md` (INV-5 STABLE v0.2).
14. **The M0+M1+M2-IG code baseline**: skim `src/blive/{domain,strategy,sizing,risk,runtime}/*.py` and `src/blive/adapters/{paper,memory,clock,alert,shared,ig}/*.py`. The M2-IG modules under `blive/adapters/ig/` are your **template** — IB modules at M2-IB.2 / .3 / .4 mirror their structure. Read at least: `blive/adapters/ig/{__init__,credentials,client,instrument_resolver,broker,market_data}.py` to see the pattern. Then skim `tests/unit/adapters/ig/test_*.py` for the test patterns; M2-IB tests should follow them.
15. **The M2-IG bridge tags** (`git tag --list 'M2-*'`): `M2-substrate-IB.checkpoint` is your starting point; `M2-IG.{1-batch1,1-batch2,2-complete,3-broker,3-readside-complete,4-market-submit}` mark the bridge work for reference.

When you finish warm-up, **before proposing any work**, reply with a 5-line summary:

```
Warm-up complete. I have read:
- [list the artefacts you read]

Project state: [G2 status, M2-IG closed at architectural surface, M2-IB ACTIVE,
key architectural commitments from M2-IG that transfer]

I propose to start M2-IB.1 by: [first concrete action]
```

Wait for "go" before producing code.

---

## Step 2 — Today's mission: M2-IB resumption

Per `TASK_REGISTRY.md` M2-IB (canonical source — do not paraphrase from this prompt, read the file).

**Goal:** blive runs `tkan_v4_momentum_timing` 1× against `CAC.PA` ETF on IB Paper for ≥ 5 trading days, with end-of-period equity matching btest's reference within ±1 bps. The Phase 1 strategy reverts to the canonical [ADR-021](docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) ETF path.

**Sub-milestones (as defined in TASK_REGISTRY.md M2-IB):**

- **M2-IB.1** — Substrate verification at the `M2-substrate-IB.checkpoint` commit. Confirm internal consistency post-M2-IG (KB-8 grew §8 IG events; INV-6 grew IG rows + cross-cutting `blive.adapters.shared.*` catalogue). **No code in this sub-milestone.** Touch only docs that need updates discovered during the read-through.
- **M2-IB.2** — `blive.adapters.ib.client.IBClient` wrapping `ib_async.IB` (TCP socket + callback model — different transport from M2-IG.3's IGClient REST). + `blive.adapters.ib.credentials.IBCredentials` schema (host/port/clientId/account_id only). Module structure mirrors `blive.adapters.ig`.
- **M2-IB.3** — `blive.adapters.ib.instrument_resolver` (Contract via `qualifyContractsAsync`); `blive.adapters.ib.broker.IBBroker` read methods; `blive.adapters.ib.market_data.IBMarketData` (subscribe_bars via `ib_async.reqMktData` / `reqHistoricalData`). `create_ib_broker` + `create_ib_market_data` factories registered in `broker_registry`. **ADR-031 + ADR-032 flip PROPOSED → ACCEPTED.** **DD-7 STABLE flip** on first successful Contract resolution. **KB-2 + KB-3 STABLE flip** when read-side has exercised the §1-§9 surfaces.
- **M2-IB.4** — `IBBroker.submit/cancel/replace`; FSM events from `ib_async`'s `orderStatusEvent` / `execDetailsEvent` / `commissionReportEvent` callbacks; reconciliation on startup. **INV-14** (IB error codes) MISSING → DRAFT as observed-rejects accumulate.
- **M2-IB.5** — Pipeline (refactor `paper_pipeline.py` to be broker-agnostic via `broker_registry`, OR new `ib_pipeline.py`). Run the strategy ≥ 5 trading days. G3-IB gate. Write `RETRO-M2-IB.md`.

**The M2-IG file structure is the IB blueprint.** Per [RETRO-M2-IG §"Recommendations"](docs/retros/M2-IG_retrospective.md#recommendations-for-next_promptmd-v04-m2-ib-resumption) the mapping is one-to-one. The cross-cutting `blive.adapters.shared.{rate_limiter, credentials}` and `blive.runtime.broker_registry` + the new import-linter contract `Broker registry isolation (ADR-034)` are reused unchanged.

**Substrate transitions at M2-IB close:**

- ADR-031 + ADR-032 PROPOSED → ACCEPTED on first IB exercise.
- DD-7 DRAFT → STABLE on first successful Contract resolution.
- KB-2 + KB-3 DRAFT v0.1.1 → STABLE when M2-IB.3 has exercised the §1-§9 surfaces.
- INV-14 (IB error codes) MISSING → DRAFT at M2-IB.4 as rejects accumulate.
- INV-5 widens with `AccountUpdate` (M2-IB.3) and `ArtefactFreshnessWarning` (M2-IB.3) — both already catalogued in [INV-5 §1](docs/inv/domain_events.md#1-event-catalogue), now implemented.
- New M2-IB-specific ADRs are likely if `ib_async`'s asyncio integration patterns need formalising; expect 0-2 new ADRs at M2-IB.2.

**Exit criteria (G3-IB gate):**

- blive connects to IB Paper Gateway within 5 s of process start.
- `positions()` returns the same set TWS UI shows (manual eyeball check).
- Subscribe to `CAC.PA` bars; receive ≥ 100 ticks within RTH.
- Throttle test: simulate burst of 60 calls/sec; outbound rate stays ≤ 20 msg/sec.
- Disconnect IB Gateway mid-session; blive detects within 30 s; reconnects when Gateway returns.
- `refresh_artefact.py` round-trip: copy a fresh `pred_cache.pkl` from btest output; observe checksum recorded; observe RC-12 freshness check passes.

**Operator-side prerequisites for M2-IB.2 first handshake:**

- IB Paper account commissioned ✓ 2026-04-28; enabled 2026-04-29.
- **Place IB connection params at `~/.blive/secrets/ib.env`** per [ADR-035](docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) using [`secrets/ib.env.example`](secrets/ib.env.example) as the template. **OPEN.**
- **Decide deployment target** (Linux VM vs Windows host). Affects how IBC + `gnzsnz/ib-gateway-docker` get installed. **OPEN.**
- **First IB Gateway handshake** from blive's host (TCP `127.0.0.1:4002` paper port reachable; `clientId` chosen). **OPEN.**

If any are not yet ready, surface in your warm-up summary and we'll resolve before code lands.

---

## Step 3 — Discipline reminders

Every edit you make — to substrate or code — follows **CONTEXT_PROTOCOL §3**:

- **Pre-edit:** READ the inventory → IDENTIFY SSOT → IMPACT-CHECK by walking `referenced_by`.
- **During:** stable IDs in cross-refs (`KB-N`, `ADR-N`, `OQ-N`); no paraphrasing other artefacts (link instead); minimum-surface change.
- **Post-edit:** bump `last_reviewed`; bump `version` if substantive; update `CONTEXT_INVENTORY.md` if status changed; new ADR for new architectural choices; new OQ for unresolvable questions.
- **Commit messages** list every artefact touched, by stable ID.

The **trivial-fix lane** (§3.4) exists for typos / formatting / link fixes. M2-IB.2 / .3 / .4 are *not* trivial-fix scenarios; use the full lane.

If you find yourself about to make an architectural choice that isn't already captured in ADR-001..039, **stop**: write the proposed ADR with status `PROPOSED`, surface it to me, and wait for confirmation before committing. Likely M2-IB candidates for new ADRs:

- **`ib_async` asyncio integration** — `ib_async`'s `IB.connectAsync()` runs its own event loop / tasks. blive's single-loop kernel ([ADR-005](docs/decisions/DECISIONS.md#adr-005--single-process-single-asyncio-loop-kernel-for-v1)) needs explicit thinking on how to share / nest. The IG REST path was simpler (httpx is asyncio-native). Expect this at M2-IB.2.
- **OrderId persistence policy** — IB's master `clientId` owns the orderId counter ([KB-3 §4](docs/kb/ib_pacing_spec.md#4-order-id--multi-client)); blive must persist it across restarts. Where? In InMemoryPersistence for v1, SQLite at M4. Worth an ADR if the persistence shape isn't obvious.
- **`MarketDataPort.subscribe_bars` over `ib_async`** — `reqMktData` (250 ms aggregated) vs `reqHistoricalData` for warm-up. Multi-instrument scaling. This is a small ADR or a §"Decisions" subsection in DD-7.

Use the task-tracking primitives (TaskCreate / TaskUpdate / TaskList) to track multi-artefact edits as a coherent unit.

---

## Step 4 — Hard constraints (out of scope)

These belong to later milestones; do **not** start them in this session:

- **IG bridge revival** — M2-IG is archived. The IG-specific code under `blive/adapters/ig/` stays untouched. Revival requires explicit operator action to re-open M2-IG.5 and the production Lightstreamer wrapper.
- **Real-money trading.** M2-IB is IB *Paper* only.
- **Full RiskEngine with all RCs** (RC-01..RC-07, RC-10, RC-11) — M4. M2-IB stays at M1's RC-08/09/12/13 subset.
- **SQLite persistence** — M4.
- **Continuous reconciliation loop** — M5. (Startup reconciliation per [REQUIREMENTS §5.7](REQUIREMENTS.md#57-reconciliation) is in M2-IB scope; the 60s tick loop is M5.)
- **Web UI** — M6.
- **Parity diagnostic** — M7.
- **Kill-switch UI / REST surface** (the `KillSwitch.clear()` confirmation token) — M4.

If you find an M2-IB design choice forces an early decision about M3+ architecture, capture it as an ADR (don't pre-build).

---

## Step 5 — Handoff (at session end)

Standard handoff per CONTEXT_PROTOCOL §8.3:

1. Every artefact touched is **committed**, with the commit message listing artefacts by stable ID.
2. Every new artefact created has frontmatter (id, title, status, owner, last_reviewed, version, sources, depends_on, referenced_by) and a row in `CONTEXT_INVENTORY.md`.
3. Status changes (DRAFT → STABLE) reflected in artefact + CONTEXT_INVENTORY.
4. New ADRs in `docs/decisions/DECISIONS.md` and indexed.
5. New OQs in `docs/decisions/OPEN_QUESTIONS.md`.
6. `TASK_REGISTRY.md` reflects M2-IB progress (which sub-milestones done, which blocked, why).

**Additional milestone-close steps** per CONTEXT_PROTOCOL §8.3.1 (applies if this session closes M2-IB):

7. **Write `docs/retros/M2-IB_retrospective.md`** per [`docs/retros/_template.md`](docs/retros/_template.md). Capture: G3-IB gate status (six exit criteria as a checklist), delivered-vs-plan, surprises, ADRs/OQs raised, substrate transitions, effort vs estimate, recommendations for the M3 / Phase-2-entry NEXT_PROMPT.
8. **Write `NEXT_PROMPT.md` v0.5** targeting M3 / Phase 2 entry, informed by the retro.
9. **Report the G3-IB gate status** as a checklist in chat — passed / partial / blocked, with reason on each line.

If this session inadvertently runs into M3 / Phase-2 work, **stop**: that violates the milestone-close discipline.

If a deliverable is blocked by something I need to decide, **stop and ask** — do not guess.

---

## Notes carried over from M2-IG

The M2-IG retrospective flagged the following items as worth your attention from the start:

- **Most cross-cutting work is reusable.** `blive.adapters.shared.{rate_limiter, credentials}` + `blive.runtime.broker_registry` + the import-linter contract `Broker registry isolation (ADR-034)` apply to IB unchanged. The M2-IG.2 commits are your scaffolding.
- **Mirror the IG file layout for IB.** The IG modules at `blive/adapters/ig/{credentials, client, instrument_resolver, broker, market_data}.py` map 1:1 to IB equivalents at `blive/adapters/ib/`. Test files mirror under `tests/unit/adapters/ib/`.
- **IB has its own stream model — no Lightstreamer abstraction needed.** `ib_async`'s `reqMktData` / `reqHistoricalData` + event subscriptions are asyncio-native (the lib uses `eventkit`). The M2-IG `LightstreamerSource` Protocol abstraction does *not* transfer; IB's stream directly produces bar/tick events through `ib_async`'s event system.
- **Two ADRs (031, 032) flip PROPOSED → ACCEPTED on first IB exercise.** The algorithm (rate limiter) and policy (Instrument↔Contract) are already substrate; the IB-specific defaults / mappings are validated by the read side actually running.
- **DD-7 STABLE flip** is the M2-IB.3 milestone marker for "the substrate is now empirically verified".
- **`secrets/ib.env.example`** is already in repo (committed at M2-IG.2). Operator copies to `~/.blive/secrets/ib.env` and fills values.
- **`PortfolioEngine` is a free function** (`compute_target_weights_for_date()`); the per-archetype dispatch is settled per [ADR-030](docs/decisions/DECISIONS.md#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010). The Phase 1 strategy uses `TimingPortfolio` → `SingleAssetRunner` (already wired in `paper_pipeline.py`).
- **Pipeline-level RC-08 negative test** was unfeasible at M1 (SimClock-vs-bar invariant left zero staleness delta). At M2-IB.5 with real-streaming bars from `ib_async`, RC-08 will fire naturally on lag — write the missing pipeline-level test then.
- **`KillSwitch.clear()` is unguarded in M1.** M4 adds the confirmation token. M2-IB doesn't need to touch it; the IB-disconnect auto-arm path ([REQUIREMENTS §5.5](REQUIREMENTS.md): disconnect > 30 s arms) is the first M2-IB caller of `KillSwitch.arm()`.
- **`SingleAssetRunner` is batch-only.** It takes a full `price_close` series. For M2-IB.5 live-streaming setup, the pipeline driver evaluates the runner over a growing window. A per-day streaming variant would be a worthwhile btest-side enhancement; raise an OQ if it becomes friction at M2-IB.5.

---

## A note on this prompt itself

This prompt v0.4 was authored at M2-IG bridge close (2026-04-28), targeting M2-IB resumption. The successor (`NEXT_PROMPT.md` v0.5 targeting M3 / Phase 2 entry) is a Step-5 deliverable at M2-IB close.

When in doubt about anything: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
