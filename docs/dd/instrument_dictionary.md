---
id: DD-7
title: Instrument Dictionary (`blive.Instrument` ↔ IB `Contract` / `ConID`)
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1
sources:
  - https://interactivebrokers.github.io/tws-api/contracts.html  # accessed 2026-04-27
  - https://github.com/ib-api-reloaded/ib_async                  # accessed 2026-04-27
depends_on:
  - DD-1
  - KB-2
  - ADR-032
referenced_by:
  - src/blive/adapters/ib/instrument_resolver.py  # M2
  - INV-6 §2.1 IBBroker
---

# DD-7 — Instrument Dictionary

## Purpose

The single source of truth (SSOT) for how broker-neutral [DD-1 §2.1](./domain_objects.md#21-instrument) `Instrument` values map to IB `ib_async.Contract` objects + integer `ConID`s. The mapping policy itself lives in [ADR-032](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract); this artefact is the field-level reference + the lookup-table substrate.

Companion to [DD-1](./domain_objects.md) (the broker-neutral types) and [KB-2](../kb/ib_capability_matrix.md) (what IB can do).

## Scope

**In:**

- `Instrument` field-by-field map to `Contract` constructor parameters.
- `AssetClass` → IB `secType` mapping table.
- `venue` (MIC) → IB `exchange` mapping table.
- ConID lookup mechanism + caching contract.
- Ambiguity-handling discipline.

**Out:**

- `ib_async.Contract` internals (their docs are the SSOT for IB-side fields).
- Order-side fields (`Order.tif`, `outsideRth`, etc. — those are [DD-1 §2.4](./domain_objects.md#24-order) + [DD-3 §2 LiveOverrides](./config_schemas.md#2-liveoverrides)).
- Adapter testing fixtures (`tests_slow/fixtures/ib_qualified_contracts/`, M2 deliverable).

## 1. Field-by-field map

`blive.Instrument` is a frozen dataclass; the resolver constructs a fresh `ib_async.Contract` from its fields on demand.

| `Instrument` field | IB `Contract` field | Notes |
|---|---|---|
| `symbol` | `symbol` | direct copy |
| `currency` | `currency` | direct copy (ISO 4217) |
| `asset_class` | `secType` | via §2 table |
| `venue` | `exchange` | via §3 table; non-empty MIC required |
| `multiplier` | `multiplier` | only meaningful for `OPTION` / `FUTURE`; left at `Decimal("1")` for cash equities/ETFs/INDEX/FX. IB expects a `str`, so the resolver casts. |

`Instrument` does **not** carry IB's `primaryExchange` field; the resolver derives it from `venue` (the MIC) and the §3 table. If multiple primaryExchanges share the same MIC (rare), [ADR-032](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) §"Ambiguity" applies.

## 2. `AssetClass` → IB `secType`

Per [ADR-032](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract):

| `AssetClass` | `secType` | M2 path |
|---|---|---|
| `EQUITY` | `STK` | future |
| `ETF` | `STK` | **Phase 1** (CAC.PA per [ADR-021](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)) |
| `INDEX` | `IND` | nice-to-have for parity-residual decomposition |
| `FX` | `CASH` | future |
| `FUTURE` | `FUT` | future |
| `OPTION` | `OPT` | future |

IB does not distinguish ETFs from equities at the `secType` level — both resolve to `STK`. The `AssetClass.ETF` distinction is preserved on the blive side for cost-model and risk-check semantics.

Unsupported asset classes raise `InstrumentNotResolvable(instrument)` at the adapter boundary; the call never reaches the wire.

## 3. `venue` (MIC) → IB `exchange`

Phase 1 only needs one row; the table grows per venue.

| MIC (ISO 10383) | IB `exchange` | Used by |
|---|---|---|
| `XPAR` | `SBF` | Phase 1 (`CAC.PA`, [ADR-021](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)) |
| `XNAS` | `NASDAQ` | future Phase 2/3 |
| `XNYS` | `NYSE` | future Phase 2/3 |
| `ARCX` | `ARCA` | future Phase 2/3 |
| `BATS` | `BATS` | future |
| `XLON` | `LSE` | post-M8 ([ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8)) |
| `XETR` | `IBIS` | future |

Sourced from [KB-2 §5](../kb/ib_capability_matrix.md#5-routing). Unknown MICs raise `InstrumentNotResolvable`; the operator extends the table when a new venue lands.

## 4. ConID resolution + caching

Per [ADR-032](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract):

1. **Lazy:** the resolver does not look up `ConID` at `Instrument` construction. The first call to `resolve(instrument)` (or a method that needs the `ConID`) triggers an `ib.qualifyContractsAsync(contract)` round trip.
2. **Cache key:** the full `Instrument` tuple equality (`(symbol, venue, currency, asset_class)`; `multiplier` informational, not part of identity). Cache lives in process memory, no disk persistence.
3. **Cache lifetime:** process. ConIDs are stable for non-corp-action instruments; corp actions invalidate the lookup, observed either by IB returning a new conId on a fresh resolve or by an explicit `clear_cache(instrument)` accessor (M5 reconciliation hook).
4. **Ambiguity:** when `qualifyContractsAsync()` returns more than one candidate, raise `InstrumentAmbiguous(instrument, candidates: list[ContractCandidate])` where each candidate carries `(conId, primaryExchange, currency)`. Never silently pick — the caller must construct a more specific `Instrument` (typically by setting `venue` to the desired primary exchange's MIC).

## 5. Public surface (M2 module)

`blive.adapters.ib.instrument_resolver`:

```python
class InstrumentResolver:
    def __init__(self, ib: ib_async.IB, rate_limiter: TokenBucketRateLimiter) -> None: ...

    async def resolve(self, instrument: Instrument) -> int:
        """Return the ConID, looking up + caching on first call. Honours the rate limiter."""

    def to_contract(self, instrument: Instrument) -> ib_async.Contract:
        """Build a fresh Contract object (synchronous; no wire call)."""

    def clear_cache(self, instrument: Instrument | None = None) -> None:
        """Drop a cache entry (or all entries when called with None)."""


class InstrumentNotResolvable(Exception): ...
class InstrumentAmbiguous(Exception): ...
```

The resolver depends on the [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter so first-resolve calls share the global throttle budget.

## 6. Cross-References

- [DD-1 §2.1](./domain_objects.md#21-instrument) — broker-neutral `Instrument` shape.
- [KB-2 §2, §5](../kb/ib_capability_matrix.md) — IB asset classes + routing.
- [ADR-004](../decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — broker-neutrality contract.
- [ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) — rate limiter consumed by the resolver.
- [ADR-032](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) — policy this DD implements.

## Open Questions

None blocking M2. When Phase 2 introduces multi-venue routing for the same instrument (e.g. `AAPL` on NYSE vs ARCA via SMART), the §3 table grows; mapping is mechanical.

## Changelog

- **v0.1 (2026-04-27)** — initial DRAFT at M2 entry; substrate for ADR-032. Promotes to STABLE when M2 IBBroker successfully exercises the path against IB Paper.
