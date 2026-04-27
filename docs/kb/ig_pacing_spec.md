---
id: KB-17
title: IG Pacing & Limits Spec
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1
sources:
  - https://labs.ig.com/rest-trading-api-reference  # accessed 2026-04-27
  - https://labs.ig.com/streaming-api-reference     # accessed 2026-04-27
  - https://labs.ig.com/faq                          # accessed 2026-04-27
depends_on:
  - KB-16 ig_capability_matrix
referenced_by:
  - REQUIREMENTS.md §10 (gotchas, IG row added M2-IG)
  - ADR-036, ADR-038
---

# KB-17 — IG Pacing & Limits Spec

## Purpose

Numerical limits, pacing rules, and quotas IG enforces. Companion to [KB-16 ig_capability_matrix](ig_capability_matrix.md). The IG adapter's rate limiter, pacer, and budget tracker derive their parameters from this KB. Parallel to [KB-3 ib_pacing_spec](ib_pacing_spec.md) for IB.

## Scope

In scope: per-bucket REST rate limits, Lightstreamer subscription budget, session-token lifecycle, error codes at the pacing boundary.

Out of scope: order types and asset classes ([KB-16](ig_capability_matrix.md)); IG-side margin formulas (out of v1); strategy-specific risk thresholds ([REQUIREMENTS §5.5](../../REQUIREMENTS.md), [INV-4](../inv/risk_checks.md)).

---

## 1. Per-Bucket REST Rate Limits

IG publishes per-minute rate limits separated by endpoint family. blive's [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) token-bucket with the [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031) per-bucket config consumes these:

| Bucket | Limit | Endpoints | Notes |
|---|---|---|---|
| **General** | ≤ 30 / min | `/session` (excl. POST), `/accounts`, `/positions` (GET), `/markets`, `/marketnavigation`, `/operations`, etc. | The default bucket for everything that isn't trading or historical |
| **Trading** | ≤ 60 / min | `POST /positions/otc`, `PUT /positions/otc/{dealId}`, `DELETE /positions/otc/{dealId}`, `POST /workingorders/otc`, `PUT /workingorders/otc/{dealId}`, `DELETE /workingorders/otc/{dealId}` | Higher budget reflects expected order-rate during active trading |
| **Historical prices** | ≤ 40 / min | `GET /prices/{epic}`, `GET /prices/{epic}/{resolution}/{numPoints}`, `GET /prices/{epic}/{resolution}/{from}/{to}` | Tighter bucket; warm-up bursts risk hitting this |
| **Authentication (POST /session)** | ≤ 30 / min (within `general`); separate per-IP throttling on excessive failed-auth attempts | `POST /session`, `POST /session/refresh-token`, `DELETE /session` | Failed auth too often → temporary IP block; rare in practice |

**Adapter implementation**: per [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031), the [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) token-bucket runs four buckets at IG defaults. Each call site declares which bucket it draws from (e.g. `IGBroker.submit()` → `trading`; `IGMarketData.historical_bars()` → `historical_prices`).

Reference: [IG REST Trading API reference](https://labs.ig.com/rest-trading-api-reference) §"Rate limits".

---

## 2. Account-Level Quotas

| Item | Limit | Notes |
|---|---|---|
| Open positions per account | typically ≤ 200 (account-tier dependent) | Phase 1 bridge runs at most 1 open position |
| Working orders per account | typically ≤ 200 | Phase 1 bridge uses no working orders (MARKET only) |
| Concurrent sessions per API key | unbounded in practice; IG aggressively kills idle sessions | blive runs one session per `IGClient` instance |

These aren't strict pacing limits; they're more like quotas. blive does not police these proactively at v1; surfacing IG errors when crossed is sufficient.

---

## 3. Lightstreamer Subscription Budget

Lightstreamer subscriptions count separately from REST budgets:

| Resource | Limit | Notes |
|---|---|---|
| Concurrent subscribed items per session | ~40 (account-tier dependent; verify on first handshake) | blive treats this as a 40-token concurrent counter, not a refilling bucket |
| Subscription rate (subs/sec) | unbounded in published docs | adapter-side throttle ~5/sec is conservative |
| Push frequency per item | up to ~10 ticks/sec on liquid items | Lightstreamer aggregates if consumer can't keep up |

**Adapter implementation**: `IGMarketData` maintains a concurrent-subscription counter (max 40); `subscribe_bars(instrument, freq)` checks the counter at subscribe time; `unsubscribe(instrument)` releases. Different from REST rate-limiting: this is a budget, not a refill. Per [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031) the `lightstreamer_subscriptions` "bucket" exists in the rate-limit config table for visibility but is enforced as a counter, not via the token-bucket algorithm.

Reference: [IG Streaming API reference](https://labs.ig.com/streaming-api-reference) §"Subscriptions".

---

## 4. Session Token Lifecycle

| Event | Timing | Effect |
|---|---|---|
| **Initial auth** | `POST /session` | Returns CST (~25 chars) + X-SECURITY-TOKEN (~25 chars) headers; both required on subsequent requests; also lazy-fills `account-id` for the user |
| **Token TTL** | 6 hours (demo) / 24 hours (live) | Past TTL: 401 on next REST call |
| **Refresh** | `POST /session/refresh-token` (with the *current* tokens) | Issues new CST + X-SECURITY-TOKEN; old tokens invalidated |
| **Lightstreamer auth** | shares CST + X-SECURITY-TOKEN | When REST tokens refresh, Lightstreamer re-authenticates internally; transient |
| **Logout** | `DELETE /session` | Invalidates both REST and Lightstreamer sessions |
| **Idle timeout** | ~6 minutes of zero traffic | Session marked stale; first call after wake gets 401 |

**For blive**: `IGClient` ([ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)) handles this transparently:

- 401 on any REST call → attempt `POST /session/refresh-token`; on success retry the original call.
- 401 again or refresh-token endpoint also fails → full re-auth via `POST /session` with stored credentials.
- Idle timeout: a heartbeat task pings `GET /accounts` every 5 minutes when no other traffic. (Falls within the `general` bucket — 5/min ≪ 30/min.)
- 30 seconds before known TTL boundary: pre-emptive refresh, avoiding the 401-then-retry round trip.

---

## 5. Operational Events

Unlike IB ([KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events)), IG has no scheduled daily restart. The relevant temporal events are:

| Event | Timing | Effect |
|---|---|---|
| **Token TTL boundary** | every 6 h (demo) / 24 h (live) | handled per §4 above |
| **Idle timeout** | after ~6 min of zero traffic | handled per §4 above |
| **Weekend market close** | Friday evening (per-market hours) → Sunday/Monday open | session stays valid; subscriptions resume on market reopen |
| **Holiday closure** | per-market | RC-09 (market hours) refuses orders; positions persist |
| **IG maintenance windows** | rare; IG announces externally via Twitter / status page | blive treats like a transient outage; `IGSessionExpired` retry logic catches it |

For [KB-8 operational_events](operational_events.md): the IG row is added at M2-IG.2 alongside the IB rows.

---

## 6. Error Codes at the Pacing Boundary

Selected codes the adapter must handle explicitly (full set populated as observed during M2-IG.3):

| Code (IG `errorCode`) | HTTP | Meaning | Adapter action |
|---|---|---|---|
| `error.security.invalid-details` | 401 | Bad credentials | `IGAuthError`; do **not** retry; surface to operator |
| `error.security.api-key-revoked` | 403 | API key disabled | `IGAuthError`; bubble; operator rotates key |
| `error.security.client-token-invalid` | 401 | Session expired | refresh token, retry once; if still 401, full re-auth |
| `error.public-api.exceeded-api-key-allowance` | 403 | API-key-level quota exceeded (rarer than per-min) | `IGRateLimited`; back off; alert |
| `error.public-api.exceeded-account-allowance` | 403 | Account-level quota exceeded | `IGRateLimited`; back off |
| `error.public-api.exceeded-trading-allowance` | 403 | Trading bucket exhausted | back off (the limiter shouldn't normally let us hit this) |
| `error.public-api.exceeded-historical-data-allowance` | 403 | Historical-prices bucket exhausted | back off |
| `error.confirms.deal-rejected` (with `reason`) | 200 | Order rejected | `IGOrderRejected(reason)`; FSM transition `REJECTED` |
| `error.invalid.instrument` | 404 | Epic not found | `InstrumentNotResolvable`; never retry |
| `error.invalid.resolution` | 400 | Bad bar resolution for `/prices` | bubble as `IGRequestInvalid`; programming bug |
| `error.public-api.failure.kyc.required` | 403 | Account requires KYC | shouldn't happen on demo; live-only concern |

Adapter typed-exception hierarchy (per [ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)):

```
IGError
├── IGAuthError              (don't retry; operator action)
├── IGSessionExpired         (refresh-and-retry path)
├── IGRateLimited            (back-off; surface to alerts after N retries)
├── IGOrderRejected(reason)  (FSM REJECTED; map to typed reject reason via INV-? mapping)
├── IGRequestInvalid         (programming bug; bubble)
└── IGConnectionError        (transient; back-off + retry)
```

The IG-error inventory analogous to MISSING [INV-14](../inv/ib_error_codes.md) for IB is created at first M2-IG.3 work; rows added as observed.

---

## 7. Summary: Adapter Budget Defaults (IG)

Concrete numbers the IG adapter ships with (overridable):

| Parameter | Default | Source |
|---|---|---|
| `general` bucket capacity | 30 | §1 |
| `general` refill | 0.5 / s | §1 (= 30/min) |
| `trading` bucket capacity | 60 | §1 |
| `trading` refill | 1.0 / s | §1 (= 60/min) |
| `historical_prices` bucket capacity | 40 | §1 |
| `historical_prices` refill | 2/3 per s | §1 (= 40/min) |
| `lightstreamer_subscriptions` budget | 40 (concurrent) | §3 |
| Token refresh lead time | 30 s before TTL | §4 |
| Idle-timeout heartbeat interval | 300 s (5 min) | §4 |
| Reconnect backoff initial | 5 s, doubling to 60 s | adapter convention |

These match the [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031) `IG_DEFAULT_RATE_LIMITS` table.

---

## 8. Cross-References

- [KB-16 ig_capability_matrix](ig_capability_matrix.md) — what IG can do.
- [KB-3 ib_pacing_spec](ib_pacing_spec.md) — IB analogue (parallel structure).
- [REQUIREMENTS §10](../../REQUIREMENTS.md) — operational gotchas (the IG row added in M2-IG).
- [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) — token-bucket algorithm.
- [ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer), [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031) — IG driver and rate-limit defaults.

## Sources

- IG REST Trading API reference (https://labs.ig.com/rest-trading-api-reference, accessed 2026-04-27).
- IG Streaming API reference (https://labs.ig.com/streaming-api-reference, accessed 2026-04-27).
- IG Labs FAQ (https://labs.ig.com/faq, accessed 2026-04-27).

## Changelog

- **v0.1 (2026-04-27)** — initial bootstrap from IG Labs docs. Numerical limits per published rate-limit headers; operationally validated at first M2-IG.3 connection. STABLE flip when the [G3-IG throttle test](../../TASK_REGISTRY.md) has exercised these numbers against IG demo.
