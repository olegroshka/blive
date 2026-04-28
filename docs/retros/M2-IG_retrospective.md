---
id: RETRO-M2-IG
title: M2-IG (IG Bridge) Retrospective
status: STABLE
owner: Oleg
last_reviewed: 2026-04-28
version: 1.0
sources:
  - TASK_REGISTRY.md M2-IG
  - RETRO-M1
depends_on:
  - TASK_REGISTRY
  - RETRO-M1
referenced_by: []
---

# RETRO-M2-IG — IG Bridge Retrospective

> **Frozen record.** This file is `STABLE` on first complete write and not edited thereafter. If a future session needs to add context, append a separate `RETRO-M2-IG-addendum.md` rather than modifying this file.

> **Bridge-close framing.** This retrospective closes the M2-IG bridge **at architectural surface**, not at G3-IG gate completion. The bridge was scoped to the duration of the IB Paper account being unavailable; with the IB account being commissioned on 2026-04-28 (operator confirmed; account enabled 2026-04-29), the bridge's preconditions are ending. M2-IG.5 (strategy run on IG demo for ≥ 5 trading days) and the production Lightstreamer wrapper are explicitly **deferred** rather than failed. The decision to close the bridge here is operator-driven and recorded in §"Recommendations" below.

## Date and session(s)

- **Date:** 2026-04-27 (M2-IG.1 substrate batches + M2-IG.2 cross-cutting infra) and 2026-04-28 (M2-IG.3 read side + Lightstreamer abstraction + M2-IG.4 minimum-viable + this retro).
- **Sessions involved:** 2 (Claude Opus 4.7 across both).
- **Closing milestone:** M2-IG (bridge), bridge-close-at-architectural-surface.

## Gate status

**G3-IG status:** **NOT REACHED** (operator-driven close, not gate failure).

The G3-IG gate criteria (defined in [TASK_REGISTRY.md M2-IG](../../TASK_REGISTRY.md)) presume an actual IG demo handshake plus ≥ 5 trading days of strategy run. The bridge was archived before those preconditions were exercised — IB Paper became available, and the architectural value of the bridge had already been captured in cross-cutting substrate that transfers to M2-IB resumption.

| G3-IG exit criterion (from TASK_REGISTRY.md M2-IG) | Status | Notes |
|---|---|---|
| blive connects to IG demo within 5 s of process start | ⏸ deferred | No IG demo handshake performed. IGClient REST core implemented + 18 unit tests; auth flow paths covered via `httpx.MockTransport`. |
| `positions()` returns the same set IG web UI shows | ⏸ deferred | Parser logic complete (27 IGBroker tests); never validated against IG's actual response shape. |
| Subscribe to CAC 40 CFD prices via Lightstreamer; receive ≥ 100 ticks within market hours | ⏸ deferred | `LightstreamerSource` Protocol + `FakeLightstreamerSource` for tests; production wrapper around `lightstreamer-client-lib` not built. |
| Throttle test: simulate burst of 100 calls/min; outbound rate stays ≤ 60 calls/min (per ADR-038) | ✓ at unit scale | `tests/unit/adapters/shared/test_rate_limiter.py::test_g3_ig_throttle_100_per_minute_into_30_per_minute_sustained` and per-bucket trading-bucket tests pass under SimClock. Wire-level validation deferred. |
| IG session-token expiry test (6 h on demo): observe automatic re-authentication | ⏸ deferred | Refresh-and-reauth recovery loop implemented + 4 tests cover the contract under MockTransport; never exercised against real expiry. |
| `refresh_artefact.py` round-trip works against the IG-bridge strategy run | ⏸ deferred | Script doesn't exist yet (was originally an M2-IB deliverable; not duplicated for the bridge). |
| `tkan_v4_momentum_timing` 1× runs end-to-end on IG demo for ≥ 5 trading days without manual intervention | ⏸ deferred | M2-IG.5 not started. |
| ≥ 5 round-trip orders observed end-to-end against IG demo; FSM transitions logged | ⏸ deferred | Submit path implemented + 5 tests cover happy / rejected / polling / non-MKT / before-connect; no real round trips. |
| Strategy equity curve directionally aligned with btest replay; envelope per ADR-039 honoured | ⏸ deferred | M2-IG.5 not started. |

**Honest summary:** the architectural surface is in place and unit-tested; **zero round trips against IG's actual servers**. That gap is acknowledged and was always implicit in choosing to keep the bridge unit-test-driven while IB was unavailable.

## Delivered vs plan

The M2-IG plan in [TASK_REGISTRY.md](../../TASK_REGISTRY.md) decomposed the bridge into M2-IG.1 substrate / M2-IG.2 cross-cutting infra / M2-IG.3 read side / M2-IG.4 write side / M2-IG.5 strategy run + retro. Status table:

| Sub-milestone | Status | Tag (where placed) | Notes |
|---|---|---|---|
| **M2-IG.1 — Substrate phase** (ADRs + KBs + DDs) | ✓ complete | `M2-IG.1-batch1`, `M2-IG.1-batch2` | ADR-034..039 written; ADR-034..035 + 030/033 + 036..039 ACCEPTED en bloc; ADR-031, ADR-032 stay PROPOSED (IB-specific; revisit at M2-IB resumption). KB-16, KB-17, DD-8 DRAFT. KB-8 v0.2 IG amendment. |
| **M2-IG.2 — Cross-cutting infra code** (registry, shared rate limiter, shared credentials, DD-1 amendment, DD-3 amendment, INV-6 amendment, import-linter contract, secrets/) | ✓ complete | `M2-IG.2-complete` | All deliverables shipped; 49 new tests; new `Broker registry isolation (ADR-034)` import-linter contract KEPT alongside the M0+M1 contracts. |
| **M2-IG.3 — IG read-side adapter** (IGCredentials, IGClient, IGInstrumentResolver, IGBroker.read, IGMarketData REST + streaming abstraction, broker_registry wiring) | ✓ architectural surface | `M2-IG.3-broker`, `M2-IG.3-readside-complete` | All 6 modules + factories shipped; 102 new tests (9+18+19+27+44 incl. 17 streaming + 12 lightstreamer-abstraction tests). All under `httpx.MockTransport` + `FakeLightstreamerSource`. **Production Lightstreamer wrapper around `lightstreamer-client-lib` deferred** — abstraction implemented, wire-level integration not. |
| **M2-IG.4 — IG write-side adapter** (submit, cancel, replace, FSM via Lightstreamer trade subscription, reconciliation, chaos drills) | ⚠ minimum-viable | `M2-IG.4-market-submit` | `IGBroker.submit()` MARKET path only: POST /positions/otc + GET /confirms/{ref} polling + SUBMITTED/ACCEPTED+FILLED/REJECTED FSM event emission. 5 new tests. cancel() / replace() raise NotImplementedError citing "working orders Phase 2 needs". Lightstreamer trade-event stream + reconciliation + chaos drills not started. |
| **M2-IG.5 — Strategy run + retro** (ig_pipeline.py, 5-day demo run, RETRO-M2-IG) | ⏸ deferred | — | The retrospective half is this document; the strategy-run half is operator-deferred per the bridge-close decision. |

**Beyond the plan**, the M2-IG cross-cutting work delivered:

- Multi-broker registry pattern ([ADR-034](../decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)) was originally framed as IG-specific scaffolding; in execution it generalised cleanly to N brokers and now bootstraps both `paper` and `ig` factories with `ib` slot ready.
- Secrets handling discipline ([ADR-035](../decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)) operationalised [REQUIREMENTS §6.3](../../REQUIREMENTS.md#63-security--audit) which had been prose-only since M0. This will apply to IB credentials directly when M2-IB resumes.
- `Instrument.tradability` field ([ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet)) discriminates spot ETF from CFD without coupling to a broker; the same field will mark IB Paper's `CAC.PA` ETF as `"spot"` and any IG-resumption CFDs as `"cfd"`.

## Surprises

- **`lightstreamer-client-lib` exists on PyPI as expected** but its public API is callback-driven Java/JS-style despite its `aiohttp` dependency. The library uses `aiohttp` internally for HTTP transport but does NOT expose an asyncio interface to callers. This forced the abstract `LightstreamerSource` Protocol approach with the production wrapper deferred — building a clean asyncio bridge over a callback-driven library is non-trivial and benefits from real-server validation.
- **IG's resolution token differs between REST and streaming.** REST `/prices` uses `MINUTE` / `MINUTE_5` / `MINUTE_15` etc.; streaming chart items use `1MINUTE` / `5MINUTE` / `15MINUTE` etc. The two parallel mapping tables (`_BLIVE_FREQ_TO_IG_RESOLUTION` and `_BLIVE_FREQ_TO_LIGHTSTREAMER_RESOLUTION`) are an IG quirk we have to track. Discovered during implementation, not at plan time.
- **IG `Position.opened_at` defensive fallback needed.** IG's `/positions` response doesn't always include a creation date; blive's `Position(quantity != 0)` invariant requires `opened_at`. Fall-back logic at the parser level (use snapshot time when IG omits the date) was added without an ADR — the rule is that "we observed it at this snapshot time" is a strict upper bound on actual open time. Worth flagging as a small convention added at code time.
- **The `/confirms/{dealReference}` polling model** is unusual for live trading APIs (most are event-driven). For market orders that resolve in 100-300ms it's fine; for working orders that may sit pending, this would need refactoring to event-driven via Lightstreamer trade subscription. M2-IG.4 cancel/replace deferred precisely because of this — they apply to working orders which need the streaming model.
- **The import-linter contract for ADR-034 caught no actual violations** at landing time, because the M0 / M1 codebase had already converged on hexagonal hygiene independently. This is a positive surprise — drift was lower than feared. The contract is still load-bearing for future code (it will catch a strategy-side mistake the moment one is made).
- **`PaperBroker` is registered in the registry as the class itself** (since its constructor signature accepts the kwargs the caller supplies); IG needs a higher-level `create_ig_broker` factory that constructs IGClient + IGInstrumentResolver internally. The asymmetry is documented in ADR-034 §"Decision" item 4 + reflected in `broker_registry.py` comments. IB will likely need a similar factory pattern (IBClient + IBInstrumentResolver wrapping `ib_async.IB`).
- **IB's daily TWS restart and IG's session token TTL are different temporal patterns.** KB-8 v0.2 captured this in the §8.5 IG-vs-IB comparison table; the engine handling will differ per broker. This is captured in ADR-034 / KB-8 but worth re-noting because operators running both will encounter both patterns.
- **The CFD financing-cost variability problem (ADR-039)** never got tested against real IG data. The "directional alignment + characterised < 100 bps over 5-day run" envelope was a prudent design but is now archived without empirical validation. If the bridge is ever revived, the envelope assumption needs first-handshake validation.

## ADRs raised this milestone

All listed ADRs are documented in [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md). Status as of 2026-04-28:

- **ADR-030 — Per-archetype btest interpreter dispatch (amends ADR-010)** [ACCEPTED] — resolves OQ-030. Broker-agnostic; load-bearing for both M2-IG and M2-IB resumption.
- **ADR-031 — Token-bucket rate limiter shape for IB adapters** [PROPOSED still] — algorithm landed at M2-IG.2 in `blive.adapters.shared.rate_limiter`; IB-specific defaults still pending IB-side validation. Flips ACCEPTED at first M2-IB code session.
- **ADR-032 — Instrument resolution policy (`blive.Instrument` ↔ IB `Contract` / `ConID`)** [PROPOSED still] — IB-specific; flips ACCEPTED at first M2-IB IBInstrumentResolver session.
- **ADR-033 — `AccountUpdate` event shape and sampling cadence** [ACCEPTED] — broker-agnostic.
- **ADR-034 — Multi-broker registry pattern (extends ADR-004)** [ACCEPTED] — load-bearing for everything else; bootstraps both paper + ig + (future) ib factories.
- **ADR-035 — Secrets handling discipline (`~/.blive/secrets/`)** [ACCEPTED] — operationalises REQUIREMENTS §6.3.
- **ADR-036 — IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer** [ACCEPTED] — IG-specific; `httpx` in use, Lightstreamer wrapper deferred. **Stays ACCEPTED** even though the wrapper is unbuilt — the decision was the right one for the M2-IG path; the operational follow-up is parked.
- **ADR-037 — `Instrument.tradability` field (spot / cfd / spread_bet)** [ACCEPTED] — broker-agnostic; transfers to IB.
- **ADR-038 — IG rate-limit defaults (parameterise ADR-031)** [ACCEPTED] — IG-specific; numbers from KB-17 not validated against live IG.
- **ADR-039 — Phase 1 strategy under IG bridge: CAC 40 CFD** [ACCEPTED, **bridge-paused**] — the decision was correct *for the bridge phase*; it is not the canonical Phase 1 strategy. ADR-021 (CAC.PA ETF on IB) reasserts as the canonical path at M2-IB resumption. The ADR stays ACCEPTED rather than DEPRECATED because a future bridge revival would re-use this decision unchanged. Bridge-paused status captured in TASK_REGISTRY v0.3 §"Phase 1 specifics" rather than mutating the ADR body.

## OQs raised this milestone

- **OQ-030 — Which btest interpreter does blive call for `TimingPortfolio` (and other non-LongShort archetypes)?** RESOLVED-BY-ADR-030 (2026-04-27).

No other OQs were raised. The IG bridge work raised many decisions but they all landed as ADRs rather than open questions.

## Substrate transitions

| Artefact | Before | After | Notes |
|---|---|---|---|
| KB-10 (DECISIONS.md) | DRAFT v0.5 | DRAFT v0.9 | ADR-030..039 added. ADR-031, ADR-032 stay PROPOSED. |
| KB-11 (OPEN_QUESTIONS.md) | DRAFT v0.2 | DRAFT v0.3 | OQ-030 RESOLVED-BY-ADR-030. |
| KB-2 (IB capability matrix) | DRAFT v0.1 | DRAFT v0.1.1 | M2-entry review pass; STABLE flip pending IB exercise. |
| KB-3 (IB pacing spec) | DRAFT v0.1 | DRAFT v0.1.1 | Same. |
| KB-8 (operational events) | MISSING | DRAFT v0.2 | M2-IG.1 batch 1 created the file; M2-IG.2 added §8 IG-specific events + §8.5 IG-vs-IB comparison. |
| KB-16 (IG capability matrix) | MISSING | DRAFT v0.1 | M2-IG.1 batch 2. |
| KB-17 (IG pacing spec) | MISSING | DRAFT v0.1 | M2-IG.1 batch 2. |
| DD-1 (domain objects) | STABLE v0.1 | STABLE v0.2 | `Tradability` literal alias + `Instrument.tradability` field per ADR-037 (additive; STABLE preserved). |
| DD-2 (event schemas) | MISSING | DRAFT v0.1 | M2-IB substrate batch (M2-substrate-IB.checkpoint commit). |
| DD-3 (config schemas) | DRAFT v0.1 | DRAFT v0.2 | `LiveStrategyConfig.broker` field + per-broker config blocks per ADR-034. |
| DD-7 (instrument dictionary, IB) | MISSING | DRAFT v0.1 | M2-IB substrate batch. STABLE flip pending IB-side exercise. |
| DD-8 (instrument dictionary, IG) | MISSING | DRAFT v0.1 | M2-IG.1 batch 2. STABLE flip would have happened at first IG demo handshake; deferred with bridge close. |
| INV-5 (domain events) | STABLE v0.2 | unchanged | `AccountUpdate` / `ArtefactFreshnessWarning` rows catalogued at M2-IB substrate; not implemented yet. |
| INV-6 (ports/adapters) | STABLE v0.2 | STABLE v0.3 | Adapter-tracker grew IG read+write rows + IB rows marked PARKED. New §3.1 cross-cutting `blive.adapters.shared.*` catalogue. |
| TASK_REGISTRY | DRAFT v0.1.3 | DRAFT v0.2 → v0.3 (this retro) | M2 split into M2-IB (parked) + M2-IG (active); now M2-IG → archived-architecturally-complete + M2-IB → unparked. |
| `src/blive/` | DRAFT v0.2 (M1 close) | DRAFT v1.2 | M2-IG.2 + M2-IG.3 + M2-IG.4 modules. 11 new files in `blive/adapters/{shared, ig}` + `blive/runtime/broker_registry.py`. |
| `tests/` | DRAFT v0.2 (175 tests) | DRAFT v1.2 (359 tests) | +184 tests for M2-IG.x. |
| `pyproject.toml` | M0+M1 deps | + httpx, + lightstreamer-client-lib, + Broker-registry-isolation import-linter contract | |
| `secrets/` | (didn't exist) | secrets/.gitkeep + ig.env.example + ib.env.example + .gitignore rule | Per ADR-035. |

`CONTEXT_INVENTORY.md` priority-queue and rows updated continuously through the M2-IG sub-milestones; v0.6 → v0.6 (rolling) at M2-IG.4 close.

**Tags placed**: `M2-IG.1-batch1`, `M2-IG.1-batch2`, `M2-IG.2-complete`, `M2-IG.3-broker`, `M2-IG.3-readside-complete`, `M2-IG.4-market-submit`. Plus the parked `M2-substrate-IB.checkpoint` from M2-IB substrate work.

## Effort vs estimate

- **Estimated** (TASK_REGISTRY v0.2 M2-IG): ~5–6 sessions across M2-IG.1 to M2-IG.5.
- **Actual** (closing at architectural surface, M2-IG.5 deferred): 2 sessions — 2026-04-27 (M2-IG.1 + M2-IG.2 substrate + first code module) and 2026-04-28 (M2-IG.3 read side + Lightstreamer abstraction + M2-IG.4 minimum-viable + this retro).
- **Variance reason**: closing the bridge before M2-IG.5 (strategy run + 5-day demo) means we delivered M2-IG.1..M2-IG.4 architectural surface in 2 sessions vs an estimated 4–5 sessions for the same scope. The deferred items (production Lightstreamer wrapper, ig_pipeline, demo run) account for the remaining 1-2 sessions in the original estimate; they're not "saved" — they're parked. **Realised cost: ~2 sessions of architectural value + 0 sessions of operational validation.**

## Recommendations for `NEXT_PROMPT.md` v0.4 (M2-IB resumption)

The most important section. The next session resumes M2-IB from the `M2-substrate-IB.checkpoint` commit, with the M2-IG architecture as scaffolding.

1. **Use the M2-IG file structure as the IB blueprint.** The mapping is one-to-one:
   - `blive/adapters/ig/credentials.py` → `blive/adapters/ib/credentials.py` (IB schema is simpler — no API key, no password; just connection params per the existing `secrets/ib.env.example`).
   - `blive/adapters/ig/client.py` → `blive/adapters/ib/client.py` (`IBClient` wraps `ib_async.IB` — TCP socket + callback model rather than `httpx.AsyncClient` REST. Pattern: connect / disconnect / `submit` / `cancel` / `account_values` / event subscription. ADR-002 commits us to `ib_async`.).
   - `blive/adapters/ig/instrument_resolver.py` → `blive/adapters/ib/instrument_resolver.py` (`IBInstrumentResolver`: `Instrument` ↔ IB `Contract` via `qualifyContractsAsync` per DD-7 §4. Same lazy-cache + ambiguity handling pattern as IG.).
   - `blive/adapters/ig/broker.py` → `blive/adapters/ib/broker.py` (`IBBroker`: read methods + write methods. IB's order events arrive via `ib_async`'s `orderStatusEvent` / `execDetailsEvent` callbacks — closer to a streaming model than IG's poll model. The FSM event emission shape stays the same.).
   - `blive/adapters/ig/market_data.py` → `blive/adapters/ib/market_data.py` (`IBMarketData`: `subscribe_bars` via `ib_async.reqHistoricalData` for live + `historical_bars` for warm-up. The Lightstreamer abstraction does NOT translate; IB has its own stream model. But the **shape** of "subscribe + yield Bar" stays identical from the consumer's perspective.).
   - `blive/adapters/ig/__init__.py` → `blive/adapters/ib/__init__.py` (factories `create_ib_broker` / `create_ib_market_data` registered into `broker_registry`).

2. **Reuse `blive.adapters.shared.*` unchanged.** The rate limiter, credentials loader, and broker-agnostic Bar / Instrument / Order types all transfer. The IB rate-limit defaults table per [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults) is just a per-broker `RateLimitConfig` instance: `global` 20/sec, `per_strategy` 5/sec (same `acquire(bucket)` semantics).

3. **Flip ADR-031 + ADR-032 PROPOSED → ACCEPTED on first IB exercise.** Both ADRs are IB-specific; they wait for the IB code to actually execute against IB Paper. ADR-031's algorithm is already shared (lives in `blive.adapters.shared.rate_limiter`); the ACCEPTED flip captures "the IB-specific defaults are right".

4. **DD-7 STABLE flip on first successful Contract resolution** against IB Paper. The substrate is in place; the validation is the round trip.

5. **KB-2 + KB-3 STABLE flip when M2-IB read side has exercised the §1-§9 surfaces** against IB Paper. The DRAFT review pass at M2-IG.1 batch 1 (KB-2 v0.1.1, KB-3 v0.1.1) found no amendments needed; STABLE flip is a real-API-validation step.

6. **INV-14 (IB error codes) MISSING → DRAFT** as the IB code observes real rejects. The substrate item was seeded in M2-IB checkpoint; the population happens during M2-IB.3 / M2-IG.4-equivalent for IB.

7. **The Phase 1 strategy reverts to ADR-021 ETF path.** `Instrument(symbol="CAC.PA", venue="XPAR", currency="EUR", asset_class=AssetClass.ETF, multiplier=Decimal("1"), tradability="spot")`. The Sizer's [ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) integer-share rounding applies (no fractional shares on European venues for cash equities). The ±1 bps parity envelope per G2 / G3-IB is the canonical target — the CFD-specific envelope from ADR-039 is not relevant.

8. **Operator-side prereqs** are documented in TASK_REGISTRY M2-IB. With the IB Paper account commissioned 2026-04-28 (enabled 2026-04-29), the remaining operator tasks before M2-IB.2 code lands are:
   - Place IB connection params at `~/.blive/secrets/ib.env` per [ADR-035](../decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) using `secrets/ib.env.example` as the template. Note: IB Gateway / IBC handle the username+password (the operator's `ib-blive-test` credentials); blive only needs `IB_HOST` / `IB_PORT` / `IB_CLIENT_ID` / `IB_PAPER_ACCOUNT_ID`.
   - Decide deployment target: Linux VM vs Windows host. Affects how IBC + `gnzsnz/ib-gateway-docker` get installed. Less urgent than for the original M2-IB plan because the M2-IG bridge demonstrated that the in-process asyncio model handles the broker-of-the-day cleanly; the operational complexity is on the IB Gateway side, not blive's.
   - First IB Gateway handshake from blive's host: confirm port 4002 (paper) reachable; `clientId` chosen.

9. **M3 IB write side should consolidate with M2-IB.4 / .5** unless there's a clean split point. The original TASK_REGISTRY M3 was written before the M2 split into M2-IB / M2-IG; with the IG bridge having shipped MARKET-submit at M2-IG.4, the equivalent for IB likely lands as "M2-IB write side" rather than a separate M3 milestone. Re-evaluate at M2-IB plan-drafting time.

10. **Don't try to reuse the CFD strategy-pipeline machinery from M2-IG.5.** It doesn't exist (M2-IG.5 was deferred). The IB pipeline is a fresh adaptation of M1's `paper_pipeline.py` with `broker: "ib"` plumbed through the registry. The M2-IG.5 plan in [TASK_REGISTRY M2-IG](../../TASK_REGISTRY.md) names it `ig_pipeline.py`; the analogue is `ib_pipeline.py` OR a refactor of `paper_pipeline.py` to be broker-agnostic. The latter is more elegant; consider it.

11. **Production Lightstreamer wrapper stays parked indefinitely.** Mark task #18 as DEFERRED-WITHOUT-DATE in any future TASK_REGISTRY iteration. It's only revived if the operator decides to revive the IG bridge — which currently has no scheduled revival.

12. **Two IG-specific `secrets/ig.env.example` rows in the template assume a structure that the operator must maintain even though no IG handshake will happen.** The template can stay (it documents the schema if the bridge is ever revived); the actual `~/.blive/secrets/ig.env` file the operator was going to create can stay un-created.

## Recommendations for the discipline itself

- **Bridge-close-without-gate-pass needs a category in CONTEXT_PROTOCOL §6.** The current status lifecycle (`MISSING` → `DRAFT` → `STABLE` → `STALE` → `DEPRECATED`) doesn't have a clean state for "milestone closed without exit-criteria pass for valid operator-driven reasons". The retros are the current mechanism for capturing this — adequate for now, but if it happens again (which is plausible given how often plans pivot in research-driven work), formalising a `CLOSED-EARLY-BY-OPERATOR` state on milestones (not artefacts) would help. Worth filing as an OQ or amendment ADR if the pattern recurs.

- **PROPOSED ADRs that depend on a deferred milestone need explicit revisit-triggers.** ADR-031 + ADR-032 stay PROPOSED with the IB-resumption trigger; other ADRs in similar limbo (ADR-039 paused) had to capture their state in the retro+TASK_REGISTRY rather than the ADR itself. CONTEXT_PROTOCOL §5 could grow a "PAUSED-PENDING-{trigger}" state, or we accept the discipline-side pattern of capturing pause state in the retro.

- **The dual-resolution-token IG quirk** (REST `MINUTE_5` vs streaming `5MINUTE`) is a documentation pattern that emerges in many financial APIs (different teams within the same vendor pick different enum styles). KB-16 / KB-17 could grow a §"API consistency notes" section that catalogues these to help future implementers. Defer until the second instance lands.

- **Architectural-only milestone closes are higher-velocity than operational ones**, by a factor of ~2-3× given this session's data (2 sessions delivered the architectural surface of a 5-6-session plan; the deferred 1-2 sessions of operational validation account for the gap). Future plan estimates could split "architecture" and "validation" line items to make the pattern visible.

## Cross-References

- [TASK_REGISTRY.md](../../TASK_REGISTRY.md) — M2-IG plan + exit criteria; G3-IG row marked NOT_REACHED with this retro as evidence.
- [CONTEXT_PROTOCOL.md §8.3.1](../../CONTEXT_PROTOCOL.md) — milestone-close protocol that mandated this retro.
- [ADR-024](../decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) — retro artefact type definition.
- [ADR-034](../decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004), [ADR-035](../decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets), [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet) — the architectural wins this retro emphasises as durable.
- [RETRO-M0](M0_retrospective.md), [RETRO-M1](M1_retrospective.md) — previous retros.
- [`M2-substrate-IB.checkpoint`](../decisions/DECISIONS.md) tag — the M2-IB resumption starting point.
- [`M2-IG.4-market-submit`](../decisions/DECISIONS.md) tag — the M2-IG bridge's last commit before close.

## Changelog

- **v1.0 (2026-04-28)** — initial (and only) write at M2-IG bridge close. Captures: ~2-session architectural delivery (M2-IG.1 substrate batches + M2-IG.2 cross-cutting infra + M2-IG.3 read side architectural surface + M2-IG.4 minimum-viable submit). G3-IG gate criteria NOT REACHED — operator-driven close before the strategy-run / production-Lightstreamer-wrapper / first-IG-demo-handshake steps. M2-IB resumption recommended in §"Recommendations" with detailed mapping from M2-IG file structure to IB equivalents.
