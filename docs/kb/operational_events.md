---
id: KB-8
title: Operational Events Calendar
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.2
sources:
  - https://www.ibkrguides.com/traderworkstation/auto-restart-considerations.htm  # accessed 2026-04-27
  - https://www.interactivebrokers.com/en/trading/exchanges-calendar.php           # accessed 2026-04-27
  - https://github.com/IbcAlpha/IBC                                                # accessed 2026-04-27
  - https://labs.ig.com/rest-trading-api-reference                                  # accessed 2026-04-27
depends_on:
  - KB-2
  - KB-3
  - KB-9
  - KB-16
  - KB-17
referenced_by:
  - REQUIREMENTS.md §5.7 (reconciliation), §12 (operational model)
  - ADR-009 (crash-only design)
  - ADR-035 (secrets handling — session-token operational concerns)
  - RUNBOOK.md  # MISSING; populated post-M5
---

# KB-8 — Operational Events Calendar

## Purpose

Catalogues the recurring operational events that affect blive's connection to IB and the venues it trades on: daily TWS/Gateway restart, weekly auth-token rotation, exchange holidays, IB maintenance windows, corporate-action windows. Each row identifies the timing, the engine response, and the milestone in which the response lands.

This KB does **not** duplicate the numerical pacing limits ([KB-3](ib_pacing_spec.md)) or the capability matrix ([KB-2](ib_capability_matrix.md)); it complements both with the *temporal* surface — what happens *when* and what blive does about it.

## Scope

**In:** scheduled events that recur at known cadence and require explicit engine handling. Each event names: trigger, frequency, expected duration, observable signal, blive response, milestone.

**Out:** unscheduled events (chaos catalogue is [REQUIREMENTS §13.2](../../REQUIREMENTS.md#132-chaos-catalog), expanded into KB-7 MISSING at M3); UK regulatory schedule items ([KB-9](uk_regulatory.md)).

## 1. Daily TWS / IB Gateway restart

| Property | Value |
|---|---|
| Trigger | TWS / Gateway internal |
| Frequency | daily |
| Default time | ~23:45 ET (configurable per region) |
| Expected duration | ~2–3 minutes API outage |
| Source | [KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events) |

**Observable signal:** `ConnectionStatus(connected=False)` event from the IB adapter; `ib_async` raises an internal `disconnectedEvent` which the adapter translates to a domain event.

**blive response (M2):**

1. Engine pauses **submission** for any strategy currently running. Open orders persist on the IB side; positions persist on the IB side.
2. Engine attempts reconnect on a back-off schedule (initial: every 5 s for 60 s; after 60 s: every 30 s indefinitely).
3. On reconnect, full **startup reconciliation** per [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation): `reqAllOpenOrders` + `reqPositions`; diff against persisted state; venue authoritative.
4. After reconciliation completes cleanly, submission resumes automatically — this is a *normal* operational event, not a kill-switch trigger ([REQUIREMENTS §5.5](../../REQUIREMENTS.md)).

**Operator response:** none under normal conditions. If reconnect takes > 30 s the kill-switch arms automatically per [REQUIREMENTS §5.5](../../REQUIREMENTS.md); operator clears via the resume path.

## 2. Weekly authentication-token rotation

| Property | Value |
|---|---|
| Trigger | IB-side IBKey weekly rotation |
| Frequency | weekly (Sundays) |
| Source | [KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events) |

**Observable signal:** Gateway login fails; absent IBC, the operator must re-approve manually on the mobile IBKey app.

**blive response (M2):**

- IB Gateway runs in Docker (`gnzsnz/ib-gateway-docker` per [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model)) with IBC + offline TWS installer pinned ([KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events)). IBC handles the re-authentication automatically.
- If IBC fails: alert (`HIGH`) within 5 minutes of the Sunday window; engine remains paused until manual recovery.

**Operator response:** verify IBC is running on each Sunday; alert tells you when it isn't.

## 3. TWS auto-update window

| Property | Value |
|---|---|
| Trigger | IB-side rolling release |
| Frequency | rolling, no fixed cadence |
| Effect | breaks IBC if the offline installer is not pinned |
| Source | [KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events) |

**blive response (M2):** auto-update **disabled** in the Docker image; operator re-pins the offline installer when an IBC-compatible new release lands. The engine treats auto-update as out-of-band — there is no per-event response, only the prevention via image pinning.

## 4. Exchange holidays

| Property | Value |
|---|---|
| Source | `exchange_calendars` Python library; per [REQUIREMENTS §5.11](../../REQUIREMENTS.md) |
| Frequency | per-venue calendar |
| Effect | no fills available; some venues run half-day sessions |

**Observable signal:** the engine's `MarketCalendar` (M5 deliverable; consumed at M2 in basic form by [INV-4 RC-09](../inv/risk_checks.md)) reports `is_session_open(venue, time_utc) == False`.

**blive response (M2):**

- [INV-4 RC-09](../inv/risk_checks.md) refuses to size new orders unless `Execution.live_overrides.outside_rth=True` for the strategy.
- Half-day sessions: `RC-09` honours the venue's actual close time; the engine does not ship orders past close.

**Operator response:** none.

## 5. Corporate actions

| Property | Value |
|---|---|
| Trigger | issuer-side; observed via IB position drift, ConID change, or ratio change |
| Frequency | sporadic |
| Effect | position quantity / cost basis may shift; ConID may change |

**blive response:**

- M2: the [DD-7 §4](../dd/instrument_dictionary.md#4-conid-resolution--caching) ConID cache invalidation hook (`clear_cache(instrument)`) exists but is not yet driven by an event source.
- M5: continuous reconciliation observes position-quantity drift; emits `recon.position_drift`; alerts (`MEDIUM`); operator investigates.
- The full corp-action machinery (split / dividend / spin-off accounting) is **out of scope** for v1; flagged for post-M8 enhancement.

**Operator response:** when a corp action is anticipated, operator may manually call `clear_cache` and verify positions on resume. Corp actions on Phase 1 instrument (`CAC.PA`, an ETF) are infrequent and limited to occasional dividend distributions.

## 6. IB maintenance windows

| Property | Value |
|---|---|
| Trigger | IB-side scheduled |
| Frequency | typically Saturday US-overnight; check IB calendar |
| Effect | broader API outage beyond the daily TWS restart |
| Source | IB system status page (operator monitors externally) |

**blive response (M2):** behaves like an extended daily-restart event — pause + reconnect + reconcile. The engine does not poll the IB system status page; operator subscribes to IB notifications and pauses strategies manually before scheduled maintenance.

**Operator response:** check IB calendar weekly; pause strategies preventatively if a window overlaps active trading hours.

## 7. blive-side scheduled events

For completeness, the blive process itself has scheduled internal events that interact with the above:

| Event | Cadence | Module | Milestone |
|---|---|---|---|
| `AccountUpdate` subsample | every 30 s | `blive.adapters.ib.broker` | M2 ([ADR-033](../decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence)) |
| Continuous reconciliation tick | every 60 s | `blive.runtime.reconciliation` | M5 |
| Daily backup | nightly | external supervisor | M5 |
| Parity diagnostic | daily | `blive.runtime.parity` | M7 |

## 8. IG-specific operational events (M2-IG bridge)

Added at v0.2 alongside the M2-IG bridge ([ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd)). IG's operational temporality differs materially from IB's (no daily restart; session token TTL is the dominant cycle).

### 8.1 IG session token TTL

| Property | Value |
|---|---|
| Trigger | IG REST `POST /session` returns CST + X-SECURITY-TOKEN headers; both have a finite lifetime |
| Frequency | every 6 h on demo; every 24 h on live |
| Source | [KB-17 §4](ig_pacing_spec.md#4-session-token-lifecycle) |

**Observable signal:** any REST call after expiry returns HTTP 401; mapped by the IG adapter to `IGSessionExpired` ([KB-17 §6](ig_pacing_spec.md#6-error-codes-at-the-pacing-boundary)).

**blive response (M2-IG.3):**

1. The `IGClient` ([ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)) maintains a heartbeat task that refreshes the token via `POST /session/refresh-token` 30 seconds before known TTL boundary — a clean refresh round trip avoids the 401-then-retry path.
2. If refresh fails (e.g. both tokens expired, or refresh-token endpoint itself returns 401): `IGClient` falls back to a full re-auth (`POST /session` with stored credentials).
3. Lightstreamer session re-authenticates internally when REST tokens refresh; the client library handles this transparently.

**Operator response:** none under normal conditions. If full re-auth fails (operator changed credentials, IG-side revocation), the engine alerts (`HIGH`) and pauses; operator updates `~/.blive/secrets/ig.env` per [ADR-035](../decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) and restarts.

### 8.2 IG idle-session timeout

| Property | Value |
|---|---|
| Trigger | IG-side; ~6 minutes of zero traffic |
| Source | [KB-17 §4](ig_pacing_spec.md#4-session-token-lifecycle) |

**blive response:** `IGClient` runs a 5-minute heartbeat (`GET /accounts`) when no other traffic is flowing. The heartbeat costs 1 token from the `general` rate-limit bucket per 5 minutes ≪ 30/min budget — rate-budget-safe.

### 8.3 IG weekend market closure

| Property | Value |
|---|---|
| Trigger | per-market — most CFD markets close Friday evening, reopen Sunday/Monday |
| Effect | session stays valid; subscriptions resume on market reopen |

**Observable signal:** Lightstreamer subscription for a closed market continues to receive heartbeats but no price ticks; resumes on reopen.

**blive response:** [INV-4 RC-09](../inv/risk_checks.md) refuses orders during closed sessions; positions persist; no special handling needed.

### 8.4 IG maintenance windows

| Property | Value |
|---|---|
| Trigger | IG-side; rare; announced via Twitter / IG status page |
| Effect | extended REST + Lightstreamer outage |

**blive response:** behaves like a transient outage — `IGSessionExpired` retry logic catches the recovery. No proactive scrape of the IG status page in v1.

### 8.5 IG vs IB temporal-event comparison

For operators running both brokers (eventual M2-IB resumption + M2-IG bridge concurrent operation):

| Concern | IB | IG |
|---|---|---|
| Daily restart | yes, ~23:45 ET (§1 above) | **no** — session continues across UTC midnight |
| Weekly auth | yes, IBKey Sunday rotation (§2) | no equivalent |
| Auto-update | TWS auto-update breaks IBC (§3) | no offline installer; IG uses HTTPS exclusively |
| Token TTL | n/a — IB Gateway maintains session | **yes**, 6h demo / 24h live (§8.1) |
| Idle timeout | none (within session) | **yes**, ~6 min (§8.2) |
| Maintenance | rare; weekend overnight (§6) | rare; per IG status page (§8.4) |

The cross-broker engine ([ADR-034](../decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) registry) handles these per-broker without leaking timing details into strategy / sizing / risk code.

---

## 9. Cross-References

- [KB-2](ib_capability_matrix.md) — IB capability surface (what's affected by these events).
- [KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events) — daily/weekly window numbers (SSOT for timings).
- [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation), [§12](../../REQUIREMENTS.md#12-operational-model) — reconciliation + operational model.
- [INV-4 RC-09](../inv/risk_checks.md) — market-hours risk check.
- [ADR-009](../decisions/DECISIONS.md#adr-009--crash-only-design) — crash-only design (auto-resume only after clean reconciliation).
- [ADR-033](../decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence) — `AccountUpdate` cadence.
- `RUNBOOK.md` (MISSING) — operator playbook to be populated at M5+.

## Sources

- IB TWS auto-restart docs (accessed 2026-04-27).
- IB exchanges calendar (accessed 2026-04-27).
- `IbcAlpha/IBC` (accessed 2026-04-27).

## Open Questions

None blocking M2. Future:

- The corp-action observability path (M5) needs more concrete event source; flagged for the M5 plan.
- IB maintenance-window detection could be automated via a scraper of the IB system status page; deferred.

## Changelog

- **v0.1 (2026-04-27)** — initial DRAFT at M2 entry. Lifts the timing surface implicit in KB-3 §5 + REQUIREMENTS §5.7 / §12 into a single referenceable artefact.
- **v0.2 (2026-04-27)** — M2-IG.2 amendment. New §8 IG-specific operational events (token TTL, idle-session timeout, weekend market closure, IG maintenance windows, IG vs IB temporal-event comparison table). Renumbered "Cross-References" from §8 to §9. Sources + depends_on grew the IG references.
