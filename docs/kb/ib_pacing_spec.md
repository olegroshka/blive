---
id: KB-3
title: IB Pacing & Limits Spec
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1.1
sources:
  - https://interactivebrokers.github.io/tws-api/order_limitations.html      # accessed 2026-04-26
  - https://interactivebrokers.github.io/tws-api/historical_limitations.html # accessed 2026-04-26
  - https://interactivebrokers.github.io/tws-api/order_submission.html       # accessed 2026-04-26
  - https://www.interactivebrokers.com/campus/ibkr-api-page/market-data-subscriptions/ # accessed 2026-04-26
  - https://www.ibkrguides.com/traderworkstation/auto-restart-considerations.htm        # accessed 2026-04-26
  - https://github.com/IbcAlpha/IBC                                                     # accessed 2026-04-26
  - https://github.com/gnzsnz/ib-gateway-docker                                         # accessed 2026-04-26
depends_on:
  - KB-2 ib_capability_matrix
referenced_by:
  - REQUIREMENTS.md §10 (12 IB gotchas), §5.2, §5.5
  - ADR-008 (RiskEngine rate-limit defaults)
  - INV-14 ib_error_codes (MISSING — derived in part)
---

# KB-3 — IB Pacing & Limits Spec

## Purpose

Numerical limits, pacing rules, and quotas IB enforces. Companion to [KB-2 ib_capability_matrix](ib_capability_matrix.md). The IB adapter's rate limiter, pacer, and budget tracker derive their parameters from this KB; REQUIREMENTS §10's 12 gotchas reference here for numbers.

## Scope

In scope: throttle limits, historical-data pacing, market-data subscription budgets, order ID rules, daily / weekly operational windows, error-code mapping at the pacing boundary.

Out of scope: order types and asset classes (KB-2); IB account margin formulas (KB-6); strategy-specific risk thresholds (REQUIREMENTS §5.5, INV-4).

---

## 1. The 50 msg/sec Client Throttle

- **Limit**: ≤ 50 messages per second from a client to TWS / Gateway.
- **What counts**: every API call (`reqMktData`, `placeOrder`, `cancelOrder`, `reqPositions`, `reqHistoricalData`, etc.).
- **Enforcement**: 3 violations terminate the API session. Recovery: reconnect.
- **Multi-client**: clients connected to the **same** TWS share the budget — count cumulatively.

**Adapter implementation**: token-bucket rate limiter sized to ≤ 20 msg/sec global ceiling (40% headroom). Per-strategy sub-buckets enforced by RiskEngine (REQUIREMENTS §5.5: strategy ≤ 5/sec, ≤ 60/min).

Reference: [TWS API Order Limitations](https://interactivebrokers.github.io/tws-api/order_limitations.html).

---

## 2. Historical Data Pacing

`reqHistoricalData` has tighter limits:

| Window | Cap |
|--------|-----|
| Per 10-minute window | ≤ 60 calls |
| Per contract, ≤ 30s bars, in 2 seconds | ≤ 6 calls |
| Identical request repeated | ≤ 1 per 15 seconds |
| Repeat of same request | enforced ≥ 10-second gap |
| `BID_ASK` whatToShow | counts **double** against the cap |

**Implication**: warm-up requests (factor lookbacks at strategy start) must be paced. A 50-instrument strategy needing 252-day history can hit the 60/10min cap; the adapter queues and surfaces ETA.

Reference: [Historical Data Limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html).

---

## 3. Market Data Subscription Tiers

Live market data is **paid per exchange tier**:

| Tier | Coverage | Approx cost |
|------|----------|-------------|
| `Network A` | NYSE | small monthly |
| `Network B` | ARCA, AMEX | small monthly |
| `Network C` | NASDAQ | small monthly |
| `OPRA` | US options | larger monthly |
| `CME L1` / `CME L2` | CME futures | tiered |
| `LSE`, `EUREX`, `XETR`, `SBF`, etc. | per-exchange | per-exchange |

- Account ≥ $500 USD value avoids monthly minima for most retail tiers.
- **Without the tier, `reqMktData` returns delayed-frozen data** with cryptic error codes; the adapter must surface "tier missing for X" explicitly ([REQUIREMENTS §10 gotcha 7](../../REQUIREMENTS.md)).

Reference: [Market Data Subscriptions](https://www.interactivebrokers.com/campus/ibkr-api-page/market-data-subscriptions/).

### `reqMktData` vs `reqTickByTickData`

- `reqMktData` — aggregated 250 ms snapshots; **larger concurrent budget** (~100 simultaneous lines depending on tier).
- `reqTickByTickData` — true tick stream; **limited concurrent subscriptions** (formula tied to `marketDepth` budget; typically 1× number of market-depth lines).

**Default for blive v1**: `reqMktData` per instrument; explicit upgrade per-instrument via `Execution.live_overrides.tick_by_tick=True`.

---

## 4. Order ID & Multi-Client

- TWS pushes a starting `orderId` at connect via `nextValidId`.
- The client must **monotonically increment** thereafter.
- With **multiple clients** connected (e.g. blive + a manual TWS user), the next valid ID **must exceed every ID seen via `openOrder` / `orderStatus`** — otherwise duplicate-ID errors.
- The "master client" can see other clients' order events; non-master clients see only their own.

**For blive**: a single client connection owns the orderId counter; persist to disk; restore on restart. blive is the master client; manual TWS use is read-only from blive's perspective.

Reference: [Placing Orders](https://interactivebrokers.github.io/tws-api/order_submission.html).

---

## 5. Daily and Weekly Operational Events

| Event | Timing | Effect |
|-------|--------|--------|
| **Daily TWS / Gateway restart** | configurable, default ~23:45 ET | ~2–3 minute API outage; positions/orders persist on IB side; client must reconnect |
| **Weekly authentication token rotation** | Sunday | Manual approval needed unless IBC + offline TWS automation |
| **Auto-update** | rolling | **Breaks IBC** if the offline installer is not pinned |

**For blive operational model** ([REQUIREMENTS §12](../../REQUIREMENTS.md)):
- IB Gateway in Docker (`gnzsnz/ib-gateway-docker` or equivalent) bundling IBC + Xvfb.
- Pin offline TWS installer; auto-update disabled.
- Engine pauses submission across the daily restart window; runs full reconciliation on reconnect.
- Weekly token: alert-only if Sunday window slips.

Reference: [Auto-restart considerations](https://www.ibkrguides.com/traderworkstation/auto-restart-considerations.htm), [IBC](https://github.com/IbcAlpha/IBC), [gnzsnz/ib-gateway-docker](https://github.com/gnzsnz/ib-gateway-docker).

---

## 6. `Order.Transmit=False` Footgun

- Orders with `Transmit=False` are **TWS-session local** and clear on restart.
- Used internally for OCA construction (parent placed first with `Transmit=False`, child placed referencing the parent ID, then parent re-sent with `Transmit=True`).
- **Footgun**: if persisted as state, restart drops the order silently.

**For blive**: this pattern is internal to the adapter; never persisted as a domain order state.

---

## 7. CPAPI / Web API Limits (for reference; not used by blive)

If anyone considers CPAPI:

- **10 req/sec global** — much tighter than TWS API.
- **Session dies after ~6 min idle**; must `/tickle` ≤ 5 min.
- IBKR **Pro** account only.
- Java gateway must run alongside; auth flow is fragile.

[ADR-002](../decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver) rejects CPAPI; documented here for completeness.

---

## 8. Error Codes at the Pacing Boundary

Selected codes the adapter must handle explicitly (full list in [INV-14 ib_error_codes](../inv/ib_error_codes.md), MISSING):

| Code | Meaning | Adapter action |
|------|---------|----------------|
| 100 | Max rate of messages per second exceeded | back off; flag throttle warning |
| 162 | Historical Market Data Service error message | parse text; honour pacing message; queue retry |
| 200 | No security definition | bubble up as `InstrumentNotFound`; never retry |
| 201 | Order rejected — reason | parse reason; map to `OrderRejected` event with FSM transition |
| 202 | Order cancelled — reason | parse; FSM transition |
| 322 | Error processing request — Duplicate orderId | reconcile orderId counter from venue; refuse to submit |
| 354 | Requested market data not subscribed | surface as "tier missing for X"; do not retry |
| 366 | No historical data query found for ticker id | bubble up; not a retryable error |
| 1100 | Connectivity between IB and TWS lost | trigger reconnect logic; pause submission |
| 1101 | Connectivity restored — data lost | full reconciliation |
| 1102 | Connectivity restored — data maintained | resume |
| 1300 | TWS socket port reset | reconnect |
| 2103 / 2104 / 2106 / 2107 / 2108 | Market data farm connection status messages | informational; track but do not act |

---

## 9. Summary: Adapter Budget Defaults

Concrete numbers the IBBroker adapter ships with (overridable):

| Parameter | Default | Source |
|-----------|---------|--------|
| Global msg/sec ceiling | 20 | §1, 40% headroom under 50/sec hard limit |
| Per-strategy msg/sec ceiling | 5 | REQUIREMENTS §5.5 risk check |
| Historical req per 10 min | 50 | §2, 17% headroom under 60/10min |
| Concurrent `reqMktData` instruments | 50 | conservative; tiered up by ADR-017 routing |
| Concurrent `reqTickByTickData` | 10 | smaller budget; explicit opt-in |
| Reconnect-on-disconnect timeout | 30 s | §5; longer = kill switch ([REQUIREMENTS §5.5](../../REQUIREMENTS.md)) |
| OrderId persistence interval | every event | §4 — never lose monotonic counter |

---

## 10. Cross-References

- [KB-2 ib_capability_matrix](ib_capability_matrix.md) — what IB can do.
- [REQUIREMENTS §10](../../REQUIREMENTS.md) — 12 gotchas + mitigations.
- [REQUIREMENTS §5.2, §5.5, §12](../../REQUIREMENTS.md) — market data, risk thresholds, ops model.
- [ADR-002](../decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver), [ADR-017](../decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing).
- [INV-14 ib_error_codes](../inv/ib_error_codes.md) (MISSING) — full error-code catalogue.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from IB docs.
- **v0.1.1 (2026-04-27)** — M2-entry review pass. No amendments needed; the §1 (50 msg/sec), §2 (≤ 60/10min historical, BID_ASK ×2), §3 (market data tiers + reqMktData/reqTickByTickData budgets), §4 (orderId monotonic), §5 (daily/weekly events), §8 (error codes) tables are unchanged from IB sources at session date. The DRAFT → STABLE flip is deferred to M2 close once the [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter has been exercised against IB Paper (the §9 default budgets become "verified by behaviour" rather than "verified by docs only").
