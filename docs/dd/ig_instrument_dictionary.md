---
id: DD-8
title: IG Instrument Dictionary (`blive.Instrument` ↔ IG epic)
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1
sources:
  - https://labs.ig.com/rest-trading-api-reference  # accessed 2026-04-27
  - ADR-037 (Instrument.tradability)
  - ADR-039 (Phase 1 strategy under IG bridge)
depends_on:
  - DD-1
  - KB-16
  - ADR-037
referenced_by:
  - src/blive/adapters/ig/instrument_resolver.py  # M2-IG.3
  - INV-6 §2.1 IGBroker
---

# DD-8 — IG Instrument Dictionary

## Purpose

The single source of truth (SSOT) for how broker-neutral [DD-1 §2.1](./domain_objects.md#21-instrument) `Instrument` values map to IG **epic** strings, and the IG asset taxonomy underlying those epics.

Parallel to [DD-7 IB instrument dictionary](./instrument_dictionary.md) for IB. Both consumed via the [ADR-034](../decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) registry pattern.

## Scope

**In:**

- `Instrument` field-by-field map to IG `Contract` parameters (epic + market metadata).
- `AssetClass` × `tradability` → IG epic family table.
- `venue` (MIC) → IG market grouping where meaningful.
- Epic resolution + caching contract.
- Per-instrument precision lookup (consumed by Sizer per [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet)).

**Out:**

- IG REST API internals (their docs are SSOT).
- Order-side fields (those are [DD-1 §2.4](./domain_objects.md#24-order) + [DD-3 §2 LiveOverrides](./config_schemas.md#2-liveoverrides)).
- IB-specific resolution ([DD-7](./instrument_dictionary.md)).

---

## 1. The IG `epic` taxonomy

IG identifies tradable instruments by **epic** strings. The format is dotted segments:

```
{family}.{type}.{instrument}.{mode}.{settlement}
```

Examples (Phase 1 + adjacent):

| Epic | Family | Type | Instrument | Mode | Settlement | What |
|---|---|---|---|---|---|---|
| `IX.D.CAC40.CASH.IP` | `IX` (Index) | `D` (Daily-funded) | `CAC40` | `CASH` (rolling cash) | `IP` (UK retail) | CAC 40 cash CFD — **Phase 1 bridge target** |
| `IX.D.CAC40.DAILY.IP` | `IX` | `D` | `CAC40` | `DAILY` (daily-resetting) | `IP` | CAC 40 daily-resetting CFD (different financing semantics) |
| `IX.D.FTSE.CASH.IP` | `IX` | `D` | `FTSE` | `CASH` | `IP` | FTSE 100 cash CFD |
| `IX.D.SPTRD.CASH.IP` | `IX` | `D` | `SPTRD` | `CASH` | `IP` | S&P 500 cash CFD |
| `KC.D.AAPL.CASH.IP` | `KC` (Cash equity) | `D` | `AAPL` | `CASH` | `IP` | Apple share CFD |
| `CS.D.EURUSD.CFD.IP` | `CS` (Currency / spot) | `D` | `EURUSD` | `CFD` | `IP` | EUR/USD CFD |
| `CC.D.LCO.UNC.IP` | `CC` (Commodity) | `D` | `LCO` (Brent) | `UNC` (uncovered/cash) | `IP` | Brent oil CFD |

**Family codes** (the most commonly seen):

| Family | Asset class |
|---|---|
| `IX` | Indices |
| `KC` | Cash equities |
| `KX` | Equity dividend futures |
| `CS` | Forex (cash/spot) |
| `CC` | Commodities |
| `IR` | Interest-rate / bonds |
| `KA` | Equity options |
| `KB` | Index options |

The Phase 1 bridge only needs `IX.D.CAC40.CASH.IP`. The taxonomy is documented for forward-compatibility; new families add rows when needed.

---

## 2. Field-by-field map

`Instrument` ↔ IG resolver parameters:

| `Instrument` field | IG concept | Notes |
|---|---|---|
| `symbol` | first half of resolution: search-input + family-code derivation | e.g. `"CAC40"` → resolver searches in family `IX.D` (because `asset_class=INDEX`) for an instrument matching this symbol |
| `currency` | match against `currencies[].code` returned from `/markets/{epic}` | EUR for CAC 40 |
| `asset_class` | maps to family code + secondary type | per §3 table |
| `venue` | informational only | IG is the venue; the field carries the *underlying* exchange MIC for reference (e.g. `XPAR` for CAC.PA-equivalent), but does not affect resolution |
| `tradability` | maps to `mode` segment of the epic | `"cfd"` → `CASH` (rolling) or `CFD` (FX); `"spread_bet"` → epic family suffix `.IP` (already implicit in retail UK demo); `"spot"` → not directly tradable on IG retail UK, but maps to "CASH" for share-dealing accounts |
| `multiplier` | matches `instrumentDetails.lotSize` | typically 1 for cash CFDs |

The `Instrument` does **not** carry the IG epic directly. The resolver computes it from `(symbol, asset_class, tradability)` and confirms via `/markets/{epic}` on first use.

---

## 3. `AssetClass` × `tradability` → IG epic family

Combined dispatch table:

| `AssetClass` | `tradability` | IG family | Mode segment | Notes |
|---|---|---|---|---|
| `INDEX` | `"cfd"` | `IX.D` | `.CASH` (rolling) or `.DAILY` | **Phase 1 bridge** uses `INDEX` + `cfd` + `CASH` → `IX.D.{symbol}.CASH.IP` |
| `INDEX` | `"spread_bet"` | `IX.D` | same as above | spread bet sizing in £/point |
| `EQUITY` | `"cfd"` | `KC.D` | `.CASH` | individual equity CFDs |
| `EQUITY` | `"spot"` | n/a (share dealing only on different account type) | — | not in M2-IG scope |
| `ETF` | `"cfd"` | `KC.D` (IG treats ETFs in the cash-equity family) | `.CASH` | for non-Phase-1 ETFs |
| `ETF` | `"spot"` | n/a (share dealing) | — | this is what M2-IB does on IB; not IG |
| `FX` | `"cfd"` | `CS.D` | `.CFD` (or `.MINI` for minis) | unique mode segment |
| `OPTION` | `"cfd"` | `KA.D` (equity options) / `KB.D` (index options) | varies | out of v1 |
| `FUTURE` | `"cfd"` | `IX.D` (continuous index futures) | `.MONTH{N}.IP` | out of v1 |

Phase 1 row ([ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd)): `Instrument(symbol="CAC40", asset_class=INDEX, tradability="cfd")` → epic guess `IX.D.CAC40.CASH.IP`.

Unsupported combinations raise `InstrumentNotResolvable` at the adapter boundary.

---

## 4. Epic resolution + caching

Per [ADR-032 IB analogue](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) but for IG:

1. **Lazy.** Resolver does not look up the epic at `Instrument` construction. First call to `resolve(instrument)` triggers `GET /markets/{epic_guess}`; on 200 → cache the epic + market metadata; on 404 → fall back to `GET /markets?searchTerm={symbol}` and pick the best match using the §3 table.
2. **Cache key.** `Instrument` tuple equality (`(symbol, venue, currency, asset_class, tradability)`); `multiplier` not part of identity. In-process memory cache; no disk persistence.
3. **Cache lifetime.** Process. IG epics are stable; corp actions on cash CFDs are uncommon. `clear_cache(instrument)` invalidates if needed (M5 reconciliation hook).
4. **Disambiguation.** If `/markets?searchTerm=…` returns multiple candidates, pick by exact symbol match + family-code match (e.g. `CAC40` + family `IX` gets `IX.D.CAC40.CASH.IP` not the daily-resetting `IX.D.CAC40.DAILY.IP`). If still ambiguous, raise `InstrumentAmbiguous(instrument, candidates)` with each candidate's `(epic, instrumentName, expiry)`.

---

## 5. Per-instrument precision

Per [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet) the Sizer rounds based on `tradability` + per-instrument precision. For IG:

- **`tradability="spot"`** → `Decimal("1")` (integer shares; never used on IG retail demo).
- **`tradability="cfd"`** → `instrumentDetails.minDealSize` from `/markets/{epic}`. CAC 40 CFD on IG: typically `Decimal("0.1")`. CAC 40 mini: `Decimal("0.01")`. Verified at first IG handshake.
- **`tradability="spread_bet"`** → `instrumentDetails.minDealSize` (in £/point); typically `Decimal("0.5")` for CAC 40 spread bet.

The Sizer fetches precision via the `instrument_resolver.precision_for(instrument) -> Decimal` helper at sizing time. Cache entry holds the value; refreshes when the epic cache is invalidated.

---

## 6. Public surface (M2-IG.3 module)

`blive.adapters.ig.instrument_resolver`:

```python
class IGInstrumentResolver:
    def __init__(self, ig_client: IGClient, rate_limiter: TokenBucketRateLimiter) -> None: ...

    async def resolve(self, instrument: Instrument) -> str:
        """Return the IG epic, looking up + caching on first call. Honours the rate limiter."""

    async def precision_for(self, instrument: Instrument) -> Decimal:
        """Return the sizing precision (per ADR-037) for the resolved instrument."""

    async def market_metadata(self, instrument: Instrument) -> IGMarketMetadata:
        """Return the full /markets/{epic} payload (cached) — currency, lot size, market hours, etc."""

    def clear_cache(self, instrument: Instrument | None = None) -> None: ...


class InstrumentNotResolvable(Exception): ...
class InstrumentAmbiguous(Exception): ...
```

The resolver depends on the [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter (with [ADR-038](../decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031) IG defaults) so first-resolve calls share the global throttle budget — particularly important for the `historical_prices` bucket which is the tightest at 40/min.

---

## 7. Cross-References

- [DD-1 §2.1](./domain_objects.md#21-instrument) — broker-neutral `Instrument` shape (amendment forthcoming for `tradability` field).
- [DD-7 IB instrument dictionary](./instrument_dictionary.md) — IB analogue.
- [KB-16 IG capability matrix](../kb/ig_capability_matrix.md) — IG's asset-class surface.
- [KB-17 IG pacing spec](../kb/ig_pacing_spec.md) — rate limiter consumed by the resolver.
- [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet) — `tradability` field.
- [ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) — Phase 1 bridge specifics (CAC 40 CFD).
- [TASK_REGISTRY M2-IG](../../TASK_REGISTRY.md) — M2-IG.3 IG read-side milestone.

## Open Questions

None blocking M2-IG. Future:

- When Phase 2 introduces multi-currency strategies, the §3 table needs FX-specific rows for `CS.D.{pair}.MINI.IP` (lower-leverage minis); not in M2-IG scope.
- Spread-bet sizing semantics differ (£/point); §5 captures the precision mapping but DD-8 may grow a §8 "Spread bet specifics" when that path is exercised.

## Changelog

- **v0.1 (2026-04-27)** — initial DRAFT at M2-IG.1 batch 2. Substrate for [ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) Phase 1 bridge; epic guess `IX.D.CAC40.CASH.IP`. STABLE flip on first successful resolution against IG demo at M2-IG.3.
