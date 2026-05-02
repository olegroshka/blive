---
id: DD-7
title: Instrument Dictionary (`blive.Instrument` ↔ IB `Contract` / `ConID`)
status: STABLE
owner: Claude
last_reviewed: 2026-05-02
version: 1.1
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

## 3. `venue` (MIC) → IB `exchange` + (optional) `primaryExchange`

Per [ADR-046](../decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) (2026-05-02 refinement of ADR-032), US-equity venues route via SMART with a `primaryExchange` hint; non-US venues retain direct routing. The `primaryExchange` column carries the IB-named exchange when `IB exchange` is `SMART`; otherwise `—`.

| MIC (ISO 10383) | IB `Contract.exchange` | `primaryExchange` (when SMART) | Used by |
|---|---|---|---|
| `XPAR` | `SBF` | — | Substrate for [ADR-021](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) (`CAC.PA`); SUPERSEDED-BY-ADR-043 as Phase 1 strategy designation, but the resolver path stays durable (M2-IB.4a-happy-cacpa wire validation). Direct routing requires API → Precautions bypass per `M2-IB.4a-happy-cacpa`. |
| `XNAS` | **`SMART`** | `NASDAQ` | **Phase 1** (TQQQ / IEF on QQQ / IEF venue per [ADR-043](../decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)). Per [ADR-046](../decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032). |
| `XNYS` | **`SMART`** | `NYSE` | **Phase 1** (TMF on NYSE per [ADR-043](../decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)). Per ADR-046. |
| `ARCX` | **`SMART`** | `ARCA` | Future US-equity strategies. Per ADR-046. |
| `BATS` | **`SMART`** | `BATS` | Future US-equity strategies. Per ADR-046. |
| `XLON` | `LSE` | — | post-M8 ([ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8)) — direct routing; SMART support for European cash equities is venue-by-venue and revisited then. |
| `XETR` | `IBIS` | — | future — direct routing. |

Sourced from [KB-2 §5](../kb/ib_capability_matrix.md#5-routing). Unknown MICs raise `InstrumentNotResolvable`; the operator extends the table when a new venue lands.

**SMART vs direct discriminator**: the resolver applies the SMART convention when `instrument.venue` is in the **US-SMART set** (`XNAS`, `XNYS`, `ARCX`, `BATS`) AND `instrument.tradability == "spot"` AND `instrument.asset_class ∈ {EQUITY, ETF}`. Other combinations (CFD / spread_bet, non-US venues, options / futures) bypass the SMART logic — CFD/spread_bet are IG-side per ADR-037; options/futures grow their own routing table when those asset classes land.

## 3.1 Yahoo Finance / EODHD exchange-suffix → MIC

Yahoo Finance and EODHD encode the listing exchange in the ticker suffix (e.g. `CAC.PA` for Euronext Paris, `BARC.L` for London). IB's TWS API uses the **bare** ticker on the corresponding primary exchange. Per [ADR-041](../decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver), the IB resolver strips the suffix when it matches the instrument's `venue` MIC.

| MIC (ISO 10383) | Yahoo suffix | IB sees | Example |
|---|---|---|---|
| `XPAR` | `.PA` | bare ticker | `CAC.PA` → `CAC` (validated 2026-05-01: `conId=11183823`) |
| `XLON` | `.L` | bare ticker | `BARC.L` → `BARC` |
| `XETR` | `.DE` | bare ticker | `SAP.DE` → `SAP` |
| `XAMS` | `.AS` | bare ticker | (post-M8 candidate) |

Symbols **not** ending in their venue's Yahoo suffix pass through unchanged (e.g. `AAPL` on `XNAS`). Symbols with a Yahoo-style suffix on a non-matching MIC also pass through (e.g. `ABC.PA` on `XNAS` — `.PA` is XPAR-only convention; the resolver doesn't apply the rule cross-venue). Both cases are tested.

The broker-neutral `Instrument` keeps its EODHD-friendly form so the same dataclass round-trips through btest's `parquet://` and `eodhd://` data sources without translation; the IB-specific stripping lives only in the IB resolver.

## 4. ConID resolution + caching

Per [ADR-032](../decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract):

1. **Lazy:** the resolver does not look up `ConID` at `Instrument` construction. The first call to `resolve(instrument)` (or a method that needs the `ConID`) triggers an `ib.qualifyContractsAsync(contract)` round trip.
2. **Cache key:** the full `Instrument` tuple equality (`(symbol, venue, currency, asset_class)`; `multiplier` informational, not part of identity). Cache lives in process memory, no disk persistence.
3. **Cache lifetime:** process. ConIDs are stable for non-corp-action instruments; corp actions invalidate the lookup, observed either by IB returning a new conId on a fresh resolve or by an explicit `clear_cache(instrument)` accessor (M5 reconciliation hook).
4. **Ambiguity:** when `qualifyContractsAsync()` returns more than one candidate, raise `InstrumentAmbiguous(instrument, candidates: list[ContractCandidate])` where each candidate carries `(conId, primaryExchange, currency)`. Never silently pick — the caller must construct a more specific `Instrument` (typically by setting `venue` to the desired primary exchange's MIC).

## 5. Public surface (M2-IB.3a module)

`blive.adapters.ib.instrument_resolver`:

```python
class IBInstrumentResolver:
    def __init__(self, client: IBClient) -> None: ...

    async def resolve(self, instrument: Instrument) -> int:
        """Return the ConID, looking up + caching on first call. Honours the rate limiter."""

    def to_contract(self, instrument: Instrument) -> ib_async.Contract:
        """Build a fresh Contract object (synchronous; no wire call)."""

    def clear_cache(self, instrument: Instrument | None = None) -> None:
        """Drop a cache entry (or all entries when called with None)."""


class InstrumentNotResolvable(Exception): ...
class InstrumentAmbiguous(Exception): ...
```

The resolver takes a single :class:`blive.adapters.ib.client.IBClient`
which encapsulates both the underlying ``ib_async.IB`` instance and the
[ADR-031](../decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters)
:class:`TokenBucketRateLimiter`. This mirrors the IG analogue
:class:`blive.adapters.ig.instrument_resolver.IGInstrumentResolver` and
keeps factory wiring uniform across brokers per [ADR-034](../decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004).
First-resolve calls acquire one ``global`` token from the limiter; cache
hits do not.

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
- **v0.2 (2026-05-01)** — M2-IB.3a refinement. §5 public surface updated: class renamed `InstrumentResolver` → `IBInstrumentResolver` to match implementation + IG-side parallelism (`IGInstrumentResolver`); constructor signature refined from `(ib, rate_limiter)` to `(client: IBClient)` because the M2-IB.2 :class:`IBClient` already encapsulates both — taking it directly avoids duplicate wiring at the factory boundary and matches the IG analogue. The functional contract (lazy resolve + cache + raises on zero / multiple / zero-conId / unmapped fields) is unchanged. Status stays DRAFT — STABLE flip remains gated on first successful Contract resolution against IB Paper (handled at the `M2-IB.3a-resolved` commit when the operator runs `scripts/probe_ib_resolve_contract.py`).
- **v1.0 (2026-05-01)** — M2-IB.3a-resolved STABLE flip. The Phase 1 instrument `Instrument(symbol="CAC.PA", venue="XPAR", currency="EUR", asset_class=ETF, tradability="spot")` resolved cleanly against IB Paper Gateway (`scripts/probe_ib_resolve_contract.py` reported `conId=11183823 primaryExchange=SBF` in 0.04s; cache hit on second resolve in 0ms). DD-7 §1 field map + §2 secType table + §3 MIC→exchange table + §4 ConID lazy-resolve + §5 IBInstrumentResolver contract + new §3.1 Yahoo-suffix sub-table all empirically validated. Added §3.1 (Yahoo Finance / EODHD exchange-suffix → MIC) per [ADR-041](../decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver) — IB resolver strips `.PA` / `.L` / `.DE` / `.AS` suffixes when the suffix matches the venue MIC. Status DRAFT → STABLE; future venue additions to §3 / §3.1 are routine refinements rather than substrate-flipping changes.
- **v1.1 (2026-05-02)** — §3 venue table grew a `primaryExchange` column per [ADR-046](../decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032). US-equity venues (XNAS / XNYS / ARCX / BATS) route via `exchange="SMART"` with the `primaryExchange` hint set; non-US venues (XPAR / XLON / XETR) retain direct routing. SMART vs direct discriminator codified: applies when `venue` is in the US-SMART set AND `tradability="spot"` AND `asset_class ∈ {EQUITY, ETF}`. Added load-bearing for [ADR-043](../decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)'s A3 strategy on TQQQ/TMF/IEF; production resolver implements at M2-IB.6.1 (the probe-local `_SmartUsResolver` in `scripts/probe_ib_submit.py` is the prototype). XPAR / SBF row carries forward the substrate-durable note (CAC.PA stays wire-validated; only the Phase 1 strategy designation moved per ADR-043). STABLE preserved across this refinement.
