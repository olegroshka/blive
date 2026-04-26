---
id: KB-5
title: Strategy Taxonomy
status: DRAFT
owner: shared (Oleg primary, Claude assist)
last_reviewed: 2026-04-26
version: 0.1
sources:
  - btest/strategies/momentum_long_short_sp500.py             # accessed 2026-04-26
  - btest/strategies/harp_quarterly_momentum.py               # accessed 2026-04-26
  - btest/strategies/tkan_v4_momentum_timing.py               # accessed 2026-04-26
  - btest/strategies/lagging_indecies.py                      # accessed 2026-04-26
  - btest/strategies/tiny_momentum_ls.py                      # accessed 2026-04-26
  - btest/research/Index Directional/dsl_strategy.py          # accessed 2026-04-26
  - btest/research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb  # accessed 2026-04-26
  - https://eodhd.com/financial-apis/all-in-one-package/      # accessed 2026-04-26
depends_on:
  - KB-1   # btest_dsl_inventory (MISSING — claims here cite btest source files directly until KB-1 lands)
  - KB-13  # companion_projects (MISSING — boundary with btest research vs. blive deployment)
referenced_by:
  - REQUIREMENTS.md §1, §3, §5.1, §5.13, §15
  - INV-1 strategies (derived; MISSING)
  - INV-10 asset_classes (derived; MISSING)
  - OQ-013..OQ-017 (this file)
---

# KB-5 — Strategy Taxonomy

## Purpose

Catalogue the strategy archetypes `blive` must support. The taxonomy is grounded in strategies already running in `btest`, extended with the architectural surface needed to admit future strategies up to millisecond frequency without rework.

This KB owns the *shape* of strategies. Specific strategy parameters, weights, and run history live in [INV-1 strategies](../inv/strategies.md). Specific data feed adapters live in [INV-10 asset_classes](../inv/asset_classes.md) and (eventually) `data_sources_inventory`.

## Scope

**In scope:**
- Every strategy currently runnable in `btest` (six modules under `btest/strategies/` plus active research under `btest/research/`).
- Archetype dimensions: frequency, asset class, universe size, decision style, holding horizon, instrument type.
- EODHD All-in-One coverage versus what current and likely-future strategies need.
- Implications for `blive` of each archetype (for `REQUIREMENTS` propagation).

**Out of scope:**
- Building new alpha; this KB describes the form, not the content.
- Per-strategy parameter calibration (lives in the strategy's YAML config).
- The btest DSL inventory itself (lives in [KB-1](btest_dsl_inventory.md), MISSING).

## 1. Dimensions of the Taxonomy

Five orthogonal axes. Any strategy is a point in this space; archetypes are the clusters that occur in practice.

| Axis | Values |
|------|--------|
| **Decision style** | cross-sectional rank · single-instrument timing · multi-instrument rotation · pairs / stat-arb · options-spread · market-making |
| **Frequency** | F0 daily · F1 hourly · F2 5-min · F3 1-min · F4 trade-tick · F5 quote-tick / sub-millisecond |
| **Universe size** | XS (1) · S (2–10) · M (10–50) · L (50–500) · XL (500+) |
| **Holding horizon** | intraday · 1d · multi-day · weekly · monthly · quarterly |
| **Instrument type** | cash equity · ETF · index future · single-name future · option · FX · crypto |

`blive`'s ports must be neutral on every axis. The current adapter set covers the upper-left of this space (F0, equities/ETFs, M–L universe) — but the architecture is committed not to bake those values in.

## 2. Archetype Catalogue

### A1 — Cross-Sectional Rank Long/Short (L universe, daily)

**Mechanics:** Rank a universe by a factor (or factor combination); long the top decile, short the bottom decile; rebalance daily-to-monthly. Sector-neutral construction common.

**Examples in btest:**
- `xsec_momentum_long_short_sp500` (`btest/strategies/momentum_long_short_sp500.py`) — 6m momentum L/S over S&P 500, top/bottom 50, equal-weight, sector-neutral, ~200% gross.
- `harp_quarterly_momentum` (`btest/strategies/harp_quarterly_momentum.py`) — 252d return / 252d vol L/S, monthly rebalance, top/bottom 50.

**btest DSL realisation:** `LongShortPortfolio` with `TopN` / `BottomN` selectors, `EqualWeight`, optional `SectorNeutral`, optional `TurnoverLimit`.

**Key live characteristics:**
- 100+ simultaneous orders at rebalance — IB 50 msg/s throttle is a hard ceiling.
- Borrow availability matters (short leg can fail to fill if not borrowable).
- `BorrowCost` is per-name and time-varying — backtest's static rate diverges noticeably from live.
- Sector-neutral construction needs sector reference data live (EODHD `Fundamentals/General::GicSector`).

**Live-lift complexity:** **High.** This is the most demanding archetype on the engine.

### A1a — Cross-Index Lagging (M universe, daily)

**Mechanics:** Subset of A1 with smaller universe. Cross-sectional ranking over a handful of major indices (typically 5–15) to capture timezone lead/lag effects.

**Examples in btest:**
- `lagging_indecies` (`btest/strategies/lagging_indecies.py`) — short-term momentum L/S over global equity indices, parquet `equities/indicies.parquet`.

**btest DSL realisation:** Same as A1 (`LongShortPortfolio`) but with smaller universe and no sector neutrality.

**Live difference vs A1:** ETF wrappers required since indices aren't directly tradable. Tradable proxies: `SPY` (S&P 500), `EFA` (EAFE), `EWJ` (Japan), `EWG` (Germany), `EWU` (UK), `IEMG` (EM). Each lives in different timezones / IB primary exchanges. Multi-calendar handling is real here.

**Live-lift complexity:** **Medium.** Fewer orders than A1 but multi-venue / multi-calendar.

### A2 — Single-Instrument Market Timing (XS universe, daily)

**Mechanics:** Hold one instrument; binary signal switches between 0% and `target_leverage` (typically 100% or 200%). ML-driven or rule-based regime filter.

**Examples in btest:**
- `index_directional` (`btest/research/Index Directional/dsl_strategy.py`) — TKAN ML prediction + 139d momentum regime filter, instrument `CACT` (CAC TR), Bloomberg index data via `sfera-db`.
- `tkan_v4_momentum_timing` (`btest/strategies/tkan_v4_momentum_timing.py`) — same archetype, ESTER-financed 1× and 2× variants.

**btest DSL realisation:** `TimingPortfolio(signal_name, instrument, rebalance_frequency, signal_delay_bars, target_leverage)`.

**Key live characteristics:**
- One or two orders per regime change → low IB throughput pressure.
- Tradable proxy required: index itself isn't tradable. CACT → Lyxor `CACX.PA` or Amundi `CAC.PA`. SP500 timing → `SPY` or `ES` future.
- ML model artefacts (TKAN `pred_cache.pkl`) need a clean lifecycle: who trains, where the artefact lives, how `blive` loads it. (See OQ-018.)
- Stop-loss / safety exit: a timing strategy that's "long" must also know how to flatten on an emergency. `blive` adds a venue-aware emergency flatten not present in btest.

**Live-lift complexity:** **Low–Medium.** Simple order flow, but ML-artefact lifecycle is novel.

### A3 — Multi-Instrument Trend Filter with Safe-Haven Park (S universe, daily)

**Mechanics:** A small static set of instruments split into "risk-on" legs and a "safe-haven" park. Each leg holds its leveraged exposure when an underlying trend filter is bullish; otherwise the leg parks in a Treasury/cash ETF. Rebalanced (in DSL form) daily with T+1 open fill.

**Examples in btest:**
- `triple_lev_sma_filter_dsl` (`btest/research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb`) — DSL build inside the notebook. Instruments: **TQQQ** (3× QQQ), **TMF** (3× TLT 20+ Treasury), **IEF** (7-10y Treasury safe-haven park). Two legs at 50% each: TQQQ leg holds when QQQ > SMA-200 (5% hysteresis re-entry), parks in IEF otherwise; TMF leg holds when TLT > SMA-200, parks in IEF otherwise. T+1 open fill (`signal_delay_bars=1`).

**btest DSL realisation:** Uses **`LongShortPortfolio`** with empty `short_book`, **`MaskSelector(signal_name=...)`** for instrument selection, and **`ExternalFactor(per_instrument=True)`** loading a wide parquet (one column per ticker). The "always 2 selected" invariant is enforced by `IEF_eligible = NOT(TQQQ_eligible AND TMF_eligible)`, giving `EqualWeight` an exact 50/50 split. Crucially **not** a `TimingPortfolio` despite the timing flavour — it is a multi-instrument mask-driven allocator.

**Key live characteristics:**
- Leveraged ETFs (TQQQ, TMF) decay overnight — financing parity matters; `Costs.financing` model needs daily reset semantics in live.
- The TQQQ ↔ IEF and TMF ↔ IEF transitions are **paired exits/entries** — both should clear before mark-to-market; in live they may be split across seconds, requiring intra-leg consistency tolerance.
- Three tickers, mostly stable holdings — low order rate; trade events cluster on regime transitions.
- The `ExternalFactor(per_instrument=True)` source pattern means signal computation lives outside the engine; `blive` needs the same wide-parquet feed (or a streaming live equivalent) at run time.

**Live-lift complexity:** **Medium.** Order count is small, but financing parity and the paired-leg-rebalance pattern are first non-trivial parity tests.

### Future Archetypes (architectural slots, not v1 scope)

| Id | Archetype | Frequency | Why future |
|----|-----------|-----------|------------|
| **A4** | Pairs / stat-arb | F0–F2 | needs cointegration testing, proper Z-score signal infra |
| **A5** | Intraday momentum / mean-reversion | F2–F4 | needs streaming data, intraday risk reset, OOH handling |
| **A6** | Options spreads (vol selling, hedges) | F0–F1 | needs options chain feed (EODHD has EOD, real-time options needs upgrade); needs Greek-aware sizing |
| **A7** | Market making / HFT | F4–F5 | needs co-located adapter, full LOB, microsecond clock — far horizon, strictly architectural slot |
| **A8** | Macro / cross-asset | F0 | mixes equities, FX, rates futures, commodities; data fan-in across domains |

The `blive` architecture must keep slots open for A4–A8 by **not** baking equity-only assumptions into `Instrument`, `BrokerPort`, or `Sizer`.

## 3. Currently Active / In-Research Strategies

OQ-013 resolved 2026-04-26: **v1 scope is ETF and index strategies only**. Single-name SP500 cross-sectional strategies are catalogued for completeness but deferred to post-M8.

| Strategy file | Archetype | Universe | Freq | Rebal | btest status | v1 scope (OQ-013) |
|---------------|-----------|----------|------|-------|--------------|---------------------|
| `momentum_long_short_sp500` | A1 | SP500 (~500) | F0 | 1d | btest stable | **deferred (post-M8)** — single-name |
| `harp_quarterly_momentum` | A1 | SP500 (~500) | F0 | 1m | btest stable; HARP paper companion | **deferred (post-M8)** — single-name |
| `tiny_momentum_ls` | A1 | small subset | F0 | 1d | dev / smoke | **deferred** — single-name |
| `lagging_indecies` | A1a | global indices via ETF proxies (~5–15) | F0 | 1d | research | **Phase 3 (post-M7)** |
| `index_directional` | A2 | CACT (via tradable ETF proxy) | F0 | 1d | research, TKAN-driven | Phase 1 alt candidate (M3) |
| `tkan_v4_momentum_timing` | A2 | **`CAC.PA`** (1×, per ADR-021); CACT 2× (margin or 2× ETF) | F0 | 1d | research | **Phase 1 (M3)** 1× via `CAC.PA`; Phase 4+ for 2× |
| `triple_lev_sma_filter_dsl` (in `triple_leveraged_etf_dsl.ipynb`) | A3 | TQQQ / TMF / IEF | F0 | 1d (T+1 open) | active research, DSL-formalised | **Phase 2 (post-M5)** |
| `custom_strategy` | — | — | — | — | placeholder | — |
| `equities/smim/*` | A1 (research) | SMIM regimes | F0 | various | research only; harp/SMIM workflow | out-of-scope for v1 (per [KB-13](companion_projects.md), MISSING) |

**Note**: until [INV-1 strategies](../inv/strategies.md) is created, this table doubles as the running inventory. INV-1 should pull this content out and be the canonical list.

## 4. Frequency Roadmap

| Phase | Frequency | What it adds | When |
|-------|-----------|--------------|------|
| **F0** | 1d | EOD bars; rebalance at open or close; current scope | M0–M8 (live) |
| **F1** | 1h | hourly bars; intraday rebalance windows | post-M8 |
| **F2** | 5m / 15m | finer rebalance, intraday momentum | post-M8 |
| **F3** | 1m | mostly-live data feed; bar aggregation engine | future |
| **F4** | trade tick | every print; LOB-aware sizing | future |
| **F5** | quote tick / sub-second | full LOB; co-location concerns | far future, architectural slot only |

**Architectural commitments tied to this roadmap:**

1. `MarketDataPort.subscribe_bars` and `subscribe_trades` are async iterators (REQUIREMENTS §7.2) — works at any frequency.
2. `ClockPort` is mandatory; domain code never reads `datetime.now()` (REQUIREMENTS §5.11).
3. `Sizer` (REQUIREMENTS §5.13) consumes target weights; ramp policy `vwap_capped(p)` extends to intraday by re-interpreting "ADV" as window-volume.
4. Risk thresholds (REQUIREMENTS §5.5) are unitless ratios → portable across frequencies; only "stale data" threshold needs frequency-aware override.

## 5. Asset Class Coverage (current and near-future)

| Asset class | Current btest? | EODHD All-in-One? | IB tradable? | v1 priority |
|-------------|----------------|-------------------|--------------|-------------|
| US cash equities (SP500) | yes (A1) | EOD ✓; intraday ✓; fundamentals ✓ | yes | high |
| US ETFs (incl. 3×) | yes (A3) | EOD ✓; intraday ✓ | yes | high |
| Index ETFs (SPY/IWM/QQQ/EFA/IEMG) | implicit (A1a tradable proxy) | EOD ✓ | yes | high |
| European indices / ETFs (CAC, DAX, FTSE) | yes (A2: CACT) | EOD ✓ for indices; ETFs ✓ | yes | medium (multi-currency live) |
| UK cash equities (LSE) | research (smim/UK-LC, smim/UK-MC) | EOD ✓ | yes | low for v1; relevant for Oleg's UK base |
| US listed options | no | EOD options ✓; real-time options is paid add-on | yes (paid IB tier) | future (A6) |
| Index futures (ES, NQ, MES, MNQ) | no | EOD futures ✓ | yes (paid IB tier) | future (A2 alternative; A8) |
| FX | no | ✓ | yes (IDEALPRO) | future (A8) |
| Crypto | no | ✓ | partial (IB CRYPTO) | out of scope v1 |

EODHD All-in-One headline: covers EOD across 200+ exchanges, intraday historical (1m/5m/1h, limited windows), fundamentals, options EOD, macro, news. Real-time / Level-1 quotes for live US equities require add-on subscription. This means **for live, blive's market data may come from IB itself** for real-time bars/quotes, while EODHD is used for historical warm-up and fundamentals reference. (See OQ-019.)

## 6. Data Source Mapping

`btest` strategies use heterogeneous historical sources today:

| Source URL scheme | Used by |
|-------------------|---------|
| `parquet://equities/sp500_daily` | A1 SP500 strategies |
| `parquet://equities/indicies.parquet` | A1a lagging indices |
| `sfera://bbgidx/index_prices` | A2 Index Directional (Bloomberg via sfera-db) |
| `yf://...` | ad-hoc dev |
| `fred://...` | macro factor injection |

For live deployment, the data layer split is:

- **Historical warm-up** (factor lookbacks, training data): EODHD (`eodhd://...` adapter to write).
- **Live tick / bar feed**: IB's `reqMktData` and `reqHistoricalData` via the `IBMarketData` adapter (REQUIREMENTS §5.2).
- **Reference data** (fundamentals, sector, ConID resolution): EODHD for sector / fundamentals, IB for `Contract` / `ConID` resolution.

The strategy's `DataConfig.source` URL therefore differs between btest research (`parquet://`, `sfera://`, `yf://`) and `blive` live (`eodhd://` for warm-up + `ib://` for streaming). Strategy code is unchanged; only the registered adapter set differs. This is exactly what `btest/data/sources/registry.py` was designed for (see [KB-1](btest_dsl_inventory.md), MISSING).

## 7. NAV Slice & Priorities

[OQ-013](../decisions/OPEN_QUESTIONS.md#oq-013--which-strategies-are-funded-for-v1-and-what-nav-slice) resolved 2026-04-26: **v1 focus is ETF and index strategies only**; A1 single-name cross-sectional strategies deferred to post-M8.

**Resolved phased priority** (ADR-013 pending in KB-10):

- **Phase 1 (M3 IB Paper)**: A2 simplest — `tkan_v4_momentum_timing` 1× variant via a tradable ETF proxy (CACX.PA, Amundi `CAC.PA`, or equivalent — see OQ-014 resolution and KB-5 §6 for live data routing). Single instrument, simplest parity diagnostic.
- **Phase 2 (post-M5)**: A3 — `triple_lev_sma_filter_dsl` (TQQQ / TMF / IEF). Multi-instrument US-only; first paired-leg rebalance under live conditions.
- **Phase 3 (post-M7)**: A1a — `lagging_indecies` via index ETF proxies (SPY, EFA, EWJ, EWG, EWU, IEMG). Multi-currency, multi-calendar. Engine first proves cross-venue under live.
- **Phase 4+ (post-M8 live, in any order pending observed performance)**:
  - A2 leveraged variants (`tkan_v4_momentum_timing` 2×) — exercises both leverage paths (margin and leveraged-ETF instrument) per OQ-016 resolution.
  - A3 generalised to additional leveraged-ETF pairs (SOXL/SQQQ, UPRO/SPXU, sector rotations) per OQ-022 resolution.
  - UK equity strategies (per OQ-021 resolution) — likely a UK-only A1 cross-sectional from `equities/smim/UK-LC`.
  - Reconsider A1 single-name SP500 strategies if appetite remains.

Design intent of the phasing: **complexity ramps A2 → A3 → A1a so the engine learns to fill, reconcile, and risk-check on simple flows before tackling multi-venue or many-name rebalances.** A1 single-name is the highest-friction archetype and is deliberately parked behind M8.

NAV slice per phase is **not yet decided**; leave as a follow-up entry on OQ-013 when first capital is committed.

## 8. Live-Lift Implications for blive (REQUIREMENTS hooks)

For each archetype, what lifting it to live demands beyond what `btest` already provides:

| Archetype | New demands on blive | REQUIREMENTS section affected |
|-----------|---------------------|-------------------------------|
| **A1** | per-name live `BorrowCost` + `FinancingCost`; sector reference data; 50-msg/s throttle headroom; failed-short-leg handling; rebalance cadence aware sizer | §5.4 cost extension hooks; §5.5 rate limits; §10 IB gotchas; §5.13 sizing |
| **A1a** | multi-currency cash legs; multi-calendar rebalance (CAC closes 16:30 CET, SPY closes 16:00 ET); FX exposure attribution | §5.4 multi-ccy; §5.11 calendar |
| **A2** | ML artefact lifecycle (where pred_cache.pkl lives in prod, who refreshes); emergency flatten on data outage; tradable proxy mapping (CACT→CACX.PA) | §5.12 strategy versioning; §5.5 stale-data check |
| **A3** | leveraged-ETF financing parity; rotation-batch order optimisation; daily T+1 open semantics | §8 parity (financing); §5.13 ramp |
| **A4–A8** | architectural slot — ports must remain neutral; new instrument types (`option_contract`, `futures_contract`, `fx_pair`) accepted without DSL break | §15 out-of-scope today; §7 ports never assume equity |

**Concrete REQUIREMENTS deltas this KB suggests for v0.2:**

1. §1 Purpose — replace "systematic strategies authored as `btest` DSL" with "the strategies catalogued in [KB-5 §3]"; specifies grounding.
2. §3 (IS NOT) — add explicit "F1+ frequencies are deferred but not architecturally precluded".
3. §5.1 — cite §3 of this KB rather than restating archetype names; remove redundancy.
4. §5.5 — frequency-aware "stale data" threshold (5 min for F0, scaled for F1+).
5. §5.13 — ramp policy default `vwap_capped(0.05)` is right for A1; **A2/A3 strategies often want `linear(N)` or `immediate`** — make ramp policy required-per-strategy not engine-default.
6. §15 — make explicit that **A1 daily rebalance is post-M8** in the phased delivery; phased plan above.

## 9. Open Questions

The full OQ entries (background, options, resolution criteria) live in [KB-11 OPEN_QUESTIONS.md](../decisions/OPEN_QUESTIONS.md). Summary status as of 2026-04-26:

| Id | Question | Status |
|----|----------|--------|
| **OQ-013** | Which strategies funded for v1, NAV slice? | **RESOLVED-PENDING-ADR** — ETF/index only; phasing in §7 above |
| **OQ-014** | Data source switch sfera → live equivalent? | **RESOLVED-PENDING-ADR** — all sources via clean API abstraction (existing registry pattern) |
| **OQ-015** | ML training in-process or static artefacts? | **RESOLVED-PENDING-ADR** — live-trained eventually; v1 consumes static artefacts; training out of scope |
| **OQ-016** | Synthetic leverage via margin or only leveraged-ETF instruments? | **RESOLVED-PENDING-ADR** — support both, declared per-strategy |
| **OQ-017** | A3 instrument set? | **RESOLVED** — `{TQQQ, TMF, IEF}` |
| **OQ-018** | ML artefact lifecycle (where, when stale, who recomputes)? | **RESOLVED-PENDING-ADR** — same as OQ-015; v1 consumes static, freshness windows + alerts only |
| **OQ-019** | Live data: EODHD real-time vs IB streaming? | **RESOLVED-PENDING-ADR** — hybrid, per-instrument routing |
| **OQ-020** | Multi-currency P&L: real-time vs daily reval? | IN_DISCUSSION — REQUIREMENTS §5.4 working answer |
| **OQ-021** | UK equity strategies in scope post-M8 or out? | **RESOLVED-PENDING-ADR** — in scope later (post-M8) |
| **OQ-022** | Generalise A3 to other leveraged-ETF pairs? | **RESOLVED-PENDING-ADR** — yes, A3 is parameterised |

The eight `RESOLVED-PENDING-ADR` items become formally `RESOLVED-BY-ADR-NNN` once KB-10 lands. KB-10 ADR-013..020 are the next priority queue item (CONTEXT_INVENTORY §10).

## 10. Cross-References

- [REQUIREMENTS.md](../../REQUIREMENTS.md) §1, §3, §5.1, §5.13, §15 — consumers of this taxonomy.
- [CONTEXT_INVENTORY.md](../../CONTEXT_INVENTORY.md) — registers KB-5; this file flips it from MISSING → DRAFT.
- KB-1 btest_dsl_inventory (MISSING) — provides the underlying DSL primitives that A1/A2/A3 are built from.
- KB-13 companion_projects (MISSING) — clarifies SMIM (`equities/smim/*`) is research-only, not blive-deployed.
- INV-1 strategies (MISSING) — derived inventory; should pull §3 table out.
- INV-10 asset_classes (MISSING) — derived inventory; should pull §5 table out.

## 11. Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. Three current archetypes (A1/A1a, A2, A3) catalogued from btest source. Five future slots (A4–A8) reserved. EODHD All-in-One coverage mapped. Phased priority proposal pending OQ-013.
- **v0.1.1 (2026-04-26)** — A3 corrected after Oleg confirmed `triple_lev_sma_filter_dsl` is the DSL form (inside `triple_leveraged_etf_dsl.ipynb`); revised archetype as "trend filter with safe-haven park" using `LongShortPortfolio + MaskSelector + ExternalFactor(per_instrument=True)`, not `TimingPortfolio`. Concrete instrument set `{TQQQ, TMF, IEF}` resolved (OQ-017). New OQ-022 raised on A3 generalisation.
- **v0.1.2 (2026-04-26)** — OQ-013, OQ-014, OQ-015/018, OQ-016, OQ-019, OQ-021, OQ-022 resolved by Oleg. v1 scope narrowed to ETF and index strategies only. §3 strategies table annotated with v1 phase per strategy; §7 NAV Slice & Priorities replaced with the resolved phased priority (Phase 1 A2 → Phase 2 A3 → Phase 3 A1a → Phase 4+ leveraged variants, A3 generalisations, UK equities). §9 OQ table replaced with status summary; full bodies live in [KB-11 OPEN_QUESTIONS.md](../decisions/OPEN_QUESTIONS.md). Pending: ADR-013..020 in KB-10.
