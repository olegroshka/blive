---
id: INV-14
title: IB Error Codes
status: DRAFT
owner: Claude
last_reviewed: 2026-05-01
version: 0.1
sources:
  - https://interactivebrokers.github.io/tws-api/message_codes.html  # accessed 2026-05-01
  - blive wire-level probes (handshake, resolve, broker-read, market-data)
depends_on:
  - KB-3 ib_pacing_spec §8
referenced_by:
  - src/blive/adapters/ib/client.py (IBError hierarchy)
  - src/blive/adapters/ib/market_data.py (IBMarketDataError)
  - src/blive/adapters/ib/broker.py (IBShapeError)
---

# INV-14 — IB Error Codes

## Purpose

Catalogue every IB error code blive's adapter has observed against IB Paper Gateway, with the typed-exception mapping the adapter applies and the operator action (when any). Authored at M2-IB.3b-ii close from observed-rejects on the wire-level probes; widens through M2-IB.4 (write-side rejects) and M5 (reconciliation drift).

This is **not** an exhaustive IB error catalogue — that lives in IB's TWS API docs (sourced above). It is the subset blive *handles*: maps to a typed exception, surfaces a useful message to the operator, and (where applicable) drives FSM transitions / reconciliation actions.

## Scope

**In:** error codes blive has observed and decided how to handle; adapter-side mapping (which `IBError` subclass / FSM transition); operator action.

**Out:** every IB error code in the TWS API docs (link in `sources`); broker / order-state semantics that aren't error-driven (those live in [INV-13](order_state_transitions.md)).

## Error catalogue

| Code | Meaning | blive mapping | Operator action |
|------|---------|---------------|-----------------|
| **162** | Historical Market Data Service error message: `No market data permissions for {exchange} {secType}` | `IBMarketDataError` (wraps via `__cause__`); 0 bars returned to caller | Subscribe to the relevant exchange's historical-data tier in IB Account Management > Settings > User Settings > Market Data Subscriptions. **Observed at M2-IB.3b-ii** for `SBF STK`; AAPL on NASDAQ works without subscription (default delayed tier). |
| **200** | No security definition has been found for the request | `InstrumentNotResolvable` (zero-candidate path in `IBInstrumentResolver`) | Verify symbol / exchange / currency in DD-7 §1. **Observed at M2-IB.3a** for the literal `CAC.PA` symbol on `SBF` — the `.PA` Yahoo suffix needed stripping per ADR-041. |

## Codes catalogued in [KB-3 §8](../kb/ib_pacing_spec.md#8-error-codes-at-the-pacing-boundary) but not yet observed

These are documented in KB-3 with the intended adapter handling but haven't surfaced from IB Paper yet. Promoted to the §"Error catalogue" table when observed; until then this list is forward-planning.

| Code | Meaning | Planned blive mapping |
|------|---------|----------------------|
| 100 | Max rate of messages per second exceeded | `IBError` warning; back off; flag throttle warning. Defended-against by [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter. |
| 201 | Order rejected (reason text) | `IBOrderRejected` → FSM `REJECTED` event with parsed reason. **M2-IB.4** (write side). |
| 202 | Order cancelled (reason text) | FSM `CANCELED` event. **M2-IB.4**. |
| 322 | Duplicate orderId | `IBError`; reconcile orderId counter from venue; refuse to submit. **M2-IB.4**. |
| 354 | Requested market data not subscribed | `IBMarketDataError` similar to 162 but for live market data; surface as "tier missing" — operator subscribes. |
| 366 | No historical data query found for ticker id | `IBMarketDataError`; not retryable. |
| 1100 | Connectivity between IB and TWS lost | `IBConnectionError`; trigger reconnect logic; pause submission. **M5** reconciliation. |
| 1101 | Connectivity restored — data lost | full reconciliation. **M5**. |
| 1102 | Connectivity restored — data maintained | resume. **M5**. |
| 1300 | TWS socket port reset | reconnect. **M5**. |
| 2103/2104/2106/2107/2108 | Market data farm connection status | informational; track but do not act. |

## Cross-References

- [KB-3 §8](../kb/ib_pacing_spec.md#8-error-codes-at-the-pacing-boundary) — full error-code table at the pacing boundary (the SSOT for "IB says X").
- [INV-13](order_state_transitions.md) — FSM transitions (which kinds of errors map to which transitions).
- [`src/blive/adapters/ib/client.py`](../../src/blive/adapters/ib/client.py) — `IBError` hierarchy (base + `IBConnectionError`).
- [`src/blive/adapters/ib/market_data.py`](../../src/blive/adapters/ib/market_data.py) — `IBMarketDataError`.
- [`src/blive/adapters/ib/broker.py`](../../src/blive/adapters/ib/broker.py) — `IBShapeError` (parser failures, distinct from wire errors).

## Open Questions

None blocking. STABLE flip when M2-IB.4 has populated the §"Error catalogue" with the order-side codes (201, 202, 322 at minimum) — at that point the catalogue is no longer a stub against the §"Codes catalogued in KB-3 but not yet observed" forward list.

## Changelog

- **v0.1 (2026-05-01)** — initial DRAFT at M2-IB.3b-ii. Catalogues 162 (market-data permissions) + 200 (security definition not found) — both observed via blive's wire-level probes. Forward-list of KB-3 §8 codes catalogued for M2-IB.4 / M5 promotion.
