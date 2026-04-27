---
id: KB-16
title: IG Capability Matrix
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1
sources:
  - https://labs.ig.com/rest-trading-api-reference                  # accessed 2026-04-27
  - https://labs.ig.com/streaming-api-reference                     # accessed 2026-04-27
  - https://www.ig.com/uk/help-and-support/spread-betting-and-cfds  # accessed 2026-04-27
  - https://github.com/ig-python/trading-ig                          # accessed 2026-04-27 (rejected per ADR-036; reference for endpoint shapes)
depends_on: []
referenced_by:
  - ADR-036, ADR-038, ADR-039
  - KB-17 ig_pacing_spec (numerical limits)
  - DD-8 ig_instrument_dictionary
  - REQUIREMENTS.md §10 (operational gotchas, IG row added M2-IG)
---

# KB-16 — IG Capability Matrix

## Purpose

What [IG Markets](https://labs.ig.com/) supports per asset class, order type, TIF, and trading mode (CFD / spread bet / share dealing). Companion to [KB-17 IG pacing spec](ig_pacing_spec.md) (numerical limits). Together they are the SSOT for "what IG can do" referenced by the M2-IG bridge ADRs ([ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer), [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031), [ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd)) and the IG adapter implementation.

Parallel to [KB-2 IB capability matrix](ib_capability_matrix.md); read both side-by-side when evaluating multi-broker work.

## Scope

**In:**

- IG account types and trading modes (CFD, spread bet, share dealing).
- Asset classes IG exposes via the REST + Lightstreamer API.
- Order types and TIFs per trading mode.
- Market hours / trading session concepts.
- Connectivity surface (REST, Lightstreamer, demo vs live).
- Multi-currency.

**Out:**

- Pacing limits and quotas (KB-17).
- IG-specific identity scheme (epic taxonomy) — [DD-8 IG instrument dictionary](../dd/ig_instrument_dictionary.md).
- IG L&S broking platform (separate product from the trading API; not in scope).

## Conventions

- "✓" = supported on IG retail UK demo + live; "✓\*" = supported with caveats (footnoted); "✗" = not supported / not exposed; "—" = not applicable.

---

## 1. Connectivity Surface

| Surface | Protocol | Auth | Demo URL | Live URL |
|---|---|---|---|---|
| **REST API** | HTTPS (TLS) | 3-step `POST /session` → CST + X-SECURITY-TOKEN headers; refresh via `POST /session/refresh-token` | `https://demo-api.ig.com/gateway/deal` | `https://api.ig.com/gateway/deal` |
| **Lightstreamer** | HTTP (long-poll) / HTTPS | shares CST + X-SECURITY-TOKEN from REST session | `https://demo-apd.marketdatasystems.com` | `https://apd.marketdatasystems.com` |

For blive: REST + Lightstreamer used together inside a single `IGClient` ([ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)). The REST session and Lightstreamer session are conceptually one — the same auth tokens drive both; closing the REST session terminates streaming subscriptions.

---

## 2. Account Types and Trading Modes

| Trading mode | Sizing unit | Tax (UK retail) | blive `tradability` | M2-IG bridge use |
|---|---|---|---|---|
| **CFD** | contracts (often fractional, e.g. 0.01) | capital gains | `"cfd"` | **Phase 1 bridge** ([ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd)) |
| **Spread bet** | £ per point (or local equivalent) | tax-free (UK retail) | `"spread_bet"` | future option; not in M2-IG scope |
| **Share dealing** | shares (whole) | capital gains in ISA-wrapped; tax-free in ISA wrapper | `"spot"` | not available on most IG demo accounts |

The IG demo account assigned to the M2-IG bridge is a **CFD demo** per the operator-supplied credentials. Share-dealing demo accounts exist but require a different account type and are not the bridge target.

For blive: every `Instrument` carries `tradability` ([ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet)) which discriminates these. The Sizer rounds differently per `tradability`: integer shares for `"spot"` ([ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero)); per-instrument precision for `"cfd"` / `"spread_bet"`.

---

## 3. Asset Classes

| Asset class | Trading mode | M2-IG priority | Notes |
|---|---|---|---|
| Major indices (CAC, FTSE, DAX, S&P 500, Nasdaq 100, Dow) | CFD | **high** (Phase 1 bridge: CAC 40) | Cash CFD epics: `IX.D.{INDEX}.CASH.IP`; daily CFD epics: `IX.D.{INDEX}.DAILY.IP` |
| Cash equities (UK + US + EU listings) | CFD or share dealing | medium (post-M8) | Epics: `KC.D.{TICKER}.CASH.IP` |
| Forex (major + cross + minor pairs) | CFD | low | Epics: `CS.D.{PAIR}.{MODE}.IP` |
| Commodities (oil, gold, silver, gas, metals) | CFD | low | Epics: `CC.D.{NAME}.{MODE}.IP` |
| Bonds (gilts, treasuries, bunds) | CFD | low | Epics: `IR.D.{NAME}.{MODE}.IP` |
| Cryptocurrencies | CFD on demo only; spread bet only on UK live (regulatory) | out of v1 | Epics: `CS.D.{COIN}.{MODE}.IP` |
| Futures | CFD (continuous and dated) | out of v1 | Epics: `IX.D.{NAME}.MONTH{N}.IP` |

For Phase 1 bridge: CAC 40 cash CFD via epic `IX.D.CAC40.CASH.IP` (first guess; confirmed at first IG handshake per [ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd)).

---

## 4. Order Types

| Type | CFD | Spread bet | Notes |
|---|---|---|---|
| `MARKET` | ✓ | ✓ | Filled at current bid/ask |
| `LIMIT` | ✓ | ✓ | Resting at price |
| `STOP` | ✓ | ✓ | Becomes market when triggered |
| `QUOTE` | ✓\* | ✓\* | Dealer-quoted; not used by blive |

For blive v1: `MARKET`, `LIMIT`, `STOP`. `MOC` / `LOC` / `OPG` from [DD-1 §1.1 OrderType](../dd/domain_objects.md#11-enums) are **not supported on IG**; the IG adapter raises `IGOrderTypeNotSupported` if a strategy emits one. Phase 1 strategy uses `MARKET` only.

In addition to `Order.order_type`, IG's order endpoints accept:

- **Stop-loss / take-profit attached to the position**: `stopDistance` / `limitDistance` parameters (in points) on `POST /positions/otc`. These are not separate `Order`s in blive's model; if a strategy declares them, they're applied at submission and tracked on the position itself.
- **Guaranteed stop**: optional `guaranteedStop=True`; charges a premium. Out of v1 scope.
- **Trailing stop**: optional `trailingStop=True`; out of v1 scope.

---

## 5. Time-in-Force

| TIF | CFD | Spread bet | Notes |
|---|---|---|---|
| `EXECUTE_AND_ELIMINATE` | ✓ | ✓ | IG's analogue of `IOC` (fill what you can, kill the rest) |
| `FILL_OR_KILL` | ✓ | ✓ | Same as IB `FOK` |
| `GOOD_TILL_CANCELLED` | ✓ | ✓ | For `LIMIT` and `STOP`; behaves like `GTC` |
| `GOOD_TILL_DATE` | ✓ | ✓ | Requires `goodTillDate` field |

For blive v1 mapping ([DD-1 §1.1 TimeInForce](../dd/domain_objects.md#11-enums) → IG TIF):
- `DAY` → no direct IG equivalent; map to `GOOD_TILL_CANCELLED` and rely on session boundaries (most IG markets settle daily). Document the imperfect mapping in [DD-8](../dd/ig_instrument_dictionary.md).
- `GTC` → `GOOD_TILL_CANCELLED`.
- `IOC` → `EXECUTE_AND_ELIMINATE`.
- `FOK` → `FILL_OR_KILL`.
- `OPG` → not supported on IG; raises `IGTifNotSupported`.

Phase 1 strategy uses `DAY`-equivalent (mapped to `GOOD_TILL_CANCELLED`).

---

## 6. Routing

IG is the venue. There is no SMART order router; orders go to IG's own internal matching / market-making engine. `Execution.live_overrides.routing` (per [REQUIREMENTS §5.1](../../REQUIREMENTS.md)) is therefore unused for IG strategies — the IG adapter ignores it (with a one-time warning at strategy load if set).

---

## 7. Market Hours

Per-instrument; IG's `/markets/{epic}` endpoint returns `marketStatus`, `delayTime`, and `openingHours`. Most CFD markets follow the underlying exchange's RTH ± a buffer (IG runs CFD markets ~5 minutes around official open/close) plus 24-hour rolling for major indices (e.g. CAC 40 CFD trades during Frankfurt/London hours plus extended).

For blive: [INV-4 RC-09](../inv/risk_checks.md) market-hours check consults `marketStatus` from `/markets/{epic}`. The exact mapping from IG's status enum (`TRADEABLE`, `CLOSED`, `EDITS_ONLY`, …) to blive's `is_market_open` boolean lives in `blive.adapters.ig.market_hours` (M2-IG.3).

---

## 8. Multi-Currency

- IG accounts are denominated in a single base currency (typically GBP, EUR, or USD; declared at account creation).
- Trading instruments in non-base currencies works without explicit FX conversion — IG handles realised P&L in the instrument's currency at the rate IG applies on each fill.
- For blive: realised FX P&L per fill at IG's quoted rate; daily reval at close ([REQUIREMENTS §5.4](../../REQUIREMENTS.md), [OQ-007](../decisions/OPEN_QUESTIONS.md#oq-007--fx-real-time-conversion-vs-daily-close)).

For Phase 1 bridge: account base currency = GBP (operator's UK retail demo); CAC 40 CFD priced in EUR. Daily FX reval at close.

---

## 9. Authentication / Operations

- 3-step REST flow: `POST /session` with `identifier` + `password` + `X-IG-API-KEY` header → response provides CST + X-SECURITY-TOKEN headers + account list. Subsequent calls send all three headers.
- **No 2FA** on the API surface (the web UI has 2FA but the API key bypass is intentional).
- **Session token TTL**: 6 hours on demo; 24 hours on live. Auto-refresh via `POST /session/refresh-token` extends to a new token; full re-auth needed when both tokens expire.
- **No daily restart** (cf. IB's 23:45 ET restart per [KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events)). The session continues across UTC midnight, weekend, etc.
- **Weekend market closure**: most CFD markets close Friday evening, reopen Sunday/Monday. The session itself stays valid; sub­scriptions resume on market reopen.
- **Lightstreamer disconnect**: Lightstreamer maintains its own keepalive; transient disconnects are auto-reconnected by `lightstreamer-client-lib`. Adapter-level retry on REST 401 (token expired) re-authenticates.

Operational implications captured in [KB-8 §1.5 IG operational events](operational_events.md) (amendment forthcoming in M2-IG.2).

---

## 10. Cross-References

- [KB-17 IG pacing spec](ig_pacing_spec.md) — numerical limits and pacing.
- [KB-2 IB capability matrix](ib_capability_matrix.md) — IB analogue.
- [DD-8 IG instrument dictionary](../dd/ig_instrument_dictionary.md) — `Instrument` ↔ IG epic.
- [ADR-036](../decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer) — driver choice.
- [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031) — rate-limit defaults.
- [ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) — Phase 1 under bridge.
- IG REST API reference: https://labs.ig.com/rest-trading-api-reference (accessed 2026-04-27).
- IG Streaming API reference: https://labs.ig.com/streaming-api-reference (accessed 2026-04-27).

## Open Questions

None blocking M2-IG. Future:

- Confirm exact `EXECUTE_AND_ELIMINATE` semantics on `MARKET` orders (some venues let `MARKET + IOC`-equivalent partial-fill; others reject if not fully fillable). Resolved at first observed reject.
- Spread-bet TIF / cost model differs from CFD; deferred until spread-bet path is on the M2-IG roadmap.

## Changelog

- **v0.1 (2026-04-27)** — initial bootstrap from IG Labs docs at session date. Phase 1 bridge surface only. STABLE flip when M2-IG.3 read-side adapter has exercised the §3 (asset classes via /markets), §4 (order types via /positions/otc), §5 (TIFs), §7 (market hours via /markets/{epic}) surfaces against IG demo.
