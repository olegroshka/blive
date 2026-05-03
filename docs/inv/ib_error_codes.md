---
id: INV-14
title: IB Error Codes
status: DRAFT
owner: Claude
last_reviewed: 2026-05-03
version: 0.5
sources:
  - https://interactivebrokers.github.io/tws-api/message_codes.html  # accessed 2026-05-01
  - blive wire-level probes (handshake, resolve, broker-read, market-data, submit)
depends_on:
  - KB-3 ib_pacing_spec §8
referenced_by:
  - src/blive/adapters/ib/client.py (IBError hierarchy)
  - src/blive/adapters/ib/market_data.py (IBMarketDataError)
  - src/blive/adapters/ib/broker.py (IBShapeError; _last_error_log_entry / _rejected_reason_from_log_entry helpers)
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
| **201** | `Order rejected - reason: {…}` | FSM `REJECTED` event via `_on_order_status`; reason rendered as `"ib:201 {message}"` from the `TradeLogEntry` (helper `_rejected_reason_from_log_entry`). | Diagnose underlying cause (account funding, instrument tradability, venue acceptance). **Observed in two distinct contexts**: (1) **M2-IB.4a wire probe (2026-05-02)** — follow-up event after error 10311 (precaution-cascade); IB pushed `Order was discarded` on the rejected order. (2) **M2-IB.6.1 wire run (2026-05-03)** — primary failure mode for UK retail accounts trading PRIIPs-non-compliant products: reason text contains `"No Trading Permission, Customer Ineligible; Ineligibility reasons: This product does not have a KID in English or in a language approved for your country..."`. The PRIIPs-KID variant is a **regulatory blocker, not a configurable precaution** — bypassing it requires either substituting PRIIPs-compliant instruments (per [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)) or upgrading the account to MiFID II Professional Client status. The broker's reason-parsing helper handles both variants identically (no code change needed); operator-side action depends on which variant fired. See [KB-9 §5.5](../kb/uk_regulatory.md) for the PRIIPs context. |
| **202** | `Order Canceled - reason: {…}` | IB's explicit cancel confirmation; `_on_order_status` already maps the resulting `status="Cancelled"` to FSM `CANCELED` (reason `"engine"` when engine-initiated, per `_cancel_reason_from_status`). The 202 itself is informational on the wire — no separate handling required. | None — the 202 confirms a normal cancel. **Observed at M2-IB.4a-happy wire probe (2026-05-02)** for AAPL on SMART/NASDAQ and CAC.PA on SBF when the probe issued `broker.cancel()` after ACCEPTED. |
| **399** | `Order Message: {…} Warning: Your order will not be placed at the exchange until {next session open}` | IB **warning** (not rejection) when an LMT/STP order is submitted outside RTH for a venue whose next session hasn't opened yet. IB still ACCEPTs the order (status pushes through to `Submitted` / `PreSubmitted`); the order is parked until session open. The warning lands in `trade.log` with `errorCode=399`, but the broker's `_on_order_status` correctly distinguishes this from a rejection because the order has already reached ACCEPTED — `tracking.accepted_emitted` gates the disambiguation: any errorCode in the log is contextual once ACCEPTED is emitted (see fix at `src/blive/adapters/ib/broker.py:_on_order_status`). | None — the order will execute at session open. **Observed at M2-IB.4a-happy-cacpa wire probe (2026-05-02)** when CAC.PA was submitted on a Saturday; IB held the order for Monday 09:00 MET. Surfaced the post-acceptance disambiguation bug fixed in the same commit. |
| **10147** | `OrderId {N} that needs to be cancelled is not found` | `IBError` warning surfaced via `ib_async`'s logger; the cancel call returns; no FSM event emitted (the order is already terminal — REJECTED / CANCELED was emitted earlier). | Operator: usually no action — indicates a cancel-after-terminal race. **Observed at M2-IB.4a wire probe (2026-05-02)** when the probe attempted `cancelOrder` on an order that had already been REJECTED via the disambiguation path. The probe now skips cancel on REJECTED, so this code is mostly diagnostic for engine-side cancel-after-terminal races (M5 reconciliation territory). |
| **10311** | `This order will be directly routed to {exchange}. Direct routed orders may result in higher trade fees. Restriction is specified in Precautionary Settings of Global Configuration/API.` | FSM `REJECTED` event via the `Cancelled`-with-errorCode disambiguation in `_on_order_status`; reason rendered as `"ib:10311 Error 10311, …"`. | TWS Configuration → API → **Precautions** → allow direct-routed orders for the venue (or for the API in general). Required for any non-SMART venue (European cash equities like CAC.PA on SBF, etc., have no SMART option). **Observed at M2-IB.4a wire probe (2026-05-02)** — the first wire-level validation of the IB Cancelled-with-errorCode → REJECTED disambiguation. |

## Codes catalogued in [KB-3 §8](../kb/ib_pacing_spec.md#8-error-codes-at-the-pacing-boundary) but not yet observed

These are documented in KB-3 with the intended adapter handling but haven't surfaced from IB Paper yet. Promoted to the §"Error catalogue" table when observed; until then this list is forward-planning.

| Code | Meaning | Planned blive mapping |
|------|---------|----------------------|
| 100 | Max rate of messages per second exceeded | `IBError` warning; back off; flag throttle warning. Defended-against by [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter. |
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

None blocking. STABLE flip when M2-IB.4 has populated the §"Error catalogue" with the remaining order-side codes (322 dup orderId still on the forward list) — at that point the catalogue is no longer a stub against the §"Codes catalogued in KB-3 but not yet observed" forward list. Both the disambiguation path (code 10311 + 201) and the happy-path SUBMITTED → ACCEPTED → CANCELED (codes 202, 399) are now wire-validated for both AAPL/SMART and CAC.PA/SBF via the M2-IB.4a probes (2026-05-02).

**The IB Paper "Direct Routed Orders" restriction at error 10311 IS bypassable via API → Precautions** — but only when the **master bypass (item #1 "Bypass Order Precautions for API Orders")** is ticked, AND the more specific item #7 "Bypass Redirect Order warning for Stock API Orders" was also useful at validation time. Earlier session notes that called this a "hard restriction" were wrong: with the operator's bypass applied, CAC.PA on SBF reached ACCEPTED on the wire (held until next session open per warning 399). M2-IB.5 (Phase 1 strategy run on CAC.PA) is unblocked from the IB Gateway side. The probe-local `_SmartUsResolver` workaround in `scripts/probe_ib_submit.py` remains as a fallback when the bypass isn't applied (also good production guidance for US equities, where SMART routing is the IB-recommended pattern regardless).

## Changelog

- **v0.1 (2026-05-01)** — initial DRAFT at M2-IB.3b-ii. Catalogues 162 (market-data permissions) + 200 (security definition not found) — both observed via blive's wire-level probes. Forward-list of KB-3 §8 codes catalogued for M2-IB.4 / M5 promotion.
- **v0.2 (2026-05-02)** — M2-IB.4a wire-probe observations. Promoted 201 from forward-list to catalogue (observed as the follow-up event after a precaution-blocked order was discarded). Added 10311 (direct-routing precaution → REJECTED via the Cancelled-with-errorCode disambiguation; first wire-level validation of `_last_error_log_entry` / `_rejected_reason_from_log_entry` helpers). Added 10147 (cancel-after-terminal — observed when the probe naively cancelled an already-REJECTED order; the probe now skips cancel on REJECTED, so 10147 is mostly diagnostic for M5 reconciliation races). Updated `referenced_by` to point at the broker's helpers and bumped `last_reviewed`.
- **v0.3 (2026-05-02)** — M2-IB.4a-happy wire-probe observations. Promoted 202 from forward-list to catalogue (observed as IB's explicit cancel confirmation when the probe submitted-and-cancelled AAPL on SMART/NASDAQ; FSM-level handling stays in `_on_order_status` via the existing `Cancelled` status path). The 10311 restriction issue + the resolver SMART-routing question are documented in §"Open Questions" as M2-IB.5 prereqs.
- **v0.4 (2026-05-02)** — M2-IB.4a-happy-cacpa wire-probe observations: bypass via API → Precautions item #1 (master) + #7 IS effective for the 10311 restriction; CAC.PA on SBF reached ACCEPTED on the wire and the engine cancel produced CANCELED cleanly. Added 399 to catalogue (warning, "order held until next session open") — surfaced the post-acceptance disambiguation bug in `_on_order_status` where any non-zero errorCode in `trade.log` was treated as a rejection signal regardless of whether ACCEPTED had already been emitted. Fixed by gating the disambiguation on `tracking.accepted_emitted` (only treat errorCode-in-log as REJECTED for **pre-acceptance** Cancelled events). 202 row updated to mention CAC.PA observation. §"Open Questions" rewritten: the bypass works, M2-IB.5 unblocked from the IB Gateway side. SMART resolver workaround retained in the probe as documentation + fallback.
- **v0.5 (2026-05-03)** — M2-IB.6.1 wire-run observation: error 201 surfaces a second distinct context — the **PRIIPs / KID variant** for UK retail accounts, with reason text `"No Trading Permission, Customer Ineligible; Ineligibility reasons: This product does not have a KID in English or in a language approved for your country..."`. Observed across all 104 orders against TQQQ / TMF / IEF (US-domiciled ETFs without UK-filed KIDs). Distinct from the M2-IB.4a precaution-cascade variant: the PRIIPs variant is a **regulatory blocker** rather than a configurable precaution — bypass is not via TWS API → Precautions but via instrument-set substitution (per [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)) or Professional Client classification. Code 201 row in the catalogue rewritten to document both contexts with shared adapter mapping (no broker code change needed — `_rejected_reason_from_log_entry` handles both reason strings identically). Cross-link added to [KB-9 §5.5](../kb/uk_regulatory.md) (PRIIPs section).
