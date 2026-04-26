---
id: INV-10
title: Asset Classes Inventory
status: DRAFT
owner: Claude
last_reviewed: 2026-04-26
version: 0.1
sources:
  - KB-2 ib_capability_matrix §2
  - KB-5 strategy_taxonomy §5
  - https://eodhd.com/financial-apis/all-in-one-package/  # accessed 2026-04-26
depends_on:
  - KB-2 ib_capability_matrix §2
  - KB-5 strategy_taxonomy §5
referenced_by:
  - REQUIREMENTS.md §15 (out of scope)
  - ADR-013 (v1 scope)
---

# INV-10 — Asset Classes Inventory

## Purpose

Canonical list of asset classes `blive` does or might support, with current btest coverage, EODHD coverage, IB tradability, and v1 priority. Lifted from [KB-5 §5](../kb/strategy_taxonomy.md#5-asset-class-coverage-current-and-near-future); KB-5 owns the narrative, this file owns the table.

## Scope

In scope: every asset class that could plausibly appear in a `blive` strategy in v1 or post-v1.

Out of scope: asset-class-specific risk parameters (those live in INV-4); broker-specific tier requirements (KB-2 §2 / KB-3 §3).

## Inventory

| asset_class_id | description | btest current support | EODHD All-in-One | IB tradable | v1 priority |
|----------------|-------------|------------------------|-------------------|-------------|-------------|
| `us_cash_equity` | NYSE / NASDAQ / ARCA listed common stocks | yes (A1 strategies) | EOD ✓; intraday ✓; fundamentals ✓ | yes | **deferred (post-M8)** per ADR-013 (single-name) |
| `us_etf` | US-listed ETFs (incl. leveraged 2×/3×) | yes (A3) | EOD ✓; intraday ✓ | yes | **high — Phase 1, 2, 3** |
| `us_index` | non-tradable US indices (SP500, NDX, DJX) | implicit (A1a tradable proxy) | EOD ✓ | not directly | **high — via ETF proxy (SPY, QQQ, etc.)** |
| `eu_index` | non-tradable European indices (CAC, DAX, FTSE) | yes A2 (CACT) | EOD ✓ for indices | not directly | **medium — via ETF proxy (CACX.PA, EWG, EWU)** |
| `eu_cash_equity` | LSE / XETR / EPA cash equities | partial (smim research) | EOD ✓ | yes | **deferred (post-M8)** per ADR-018 (UK strategies) |
| `index_etf_global` | Country / region index ETFs (EFA, EWJ, IEMG, etc.) | yes A1a | EOD ✓ | yes | **medium — Phase 3** |
| `us_options` | US listed options (single-name, index) | no | EOD options ✓; real-time options paid add-on | yes (paid OPRA tier) | **out of v1** (A6, post-M8) |
| `us_index_futures` | ES, NQ, MES, MNQ on CME | no | EOD futures ✓ | yes (paid CME tier) | **out of v1** (A2 alt or A8) |
| `eu_index_futures` | DAX, EuroStoxx, FTSE futures | no | EOD ✓ | yes (paid Eurex tier) | **out of v1** |
| `fx` | major and cross pairs on IDEALPRO | no | ✓ | yes (paid IDEALPRO tier) | **out of v1** (A8) |
| `crypto` | BTC / ETH / etc. via IB-PAXOS | no | ✓ | yes (separate IB sub-account) | **out of v1** |
| `bonds_govt` | US Treasuries, UK Gilts | no | ✓ | yes | **out of v1** |
| `bonds_corporate` | corporate bonds | partial (pt-liqadj research) | partial | yes | **out of v1** |

## Conventions

- `v1 priority`: aligned with [ADR-013 phasing](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only).
- `IB tradable: yes (paid X tier)`: means tier subscription required; `BrokerPort` adapter must surface "tier missing" explicitly per [KB-3 §3](../kb/ib_pacing_spec.md#3-market-data-subscription-tiers).
- "ETF proxy" mappings (e.g. CACT → CACX.PA, SP500 → SPY) live in the strategy spec, not in this inventory.

## Cross-References

- [KB-2 §2](../kb/ib_capability_matrix.md#2-asset-classes) — IB-side support detail.
- [KB-5 §5](../kb/strategy_taxonomy.md#5-asset-class-coverage-current-and-near-future) — narrative + EODHD context.
- [KB-3 §3](../kb/ib_pacing_spec.md#3-market-data-subscription-tiers) — subscription tier requirements.
- [ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) — v1 ETF/index scope.
- [ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8) — UK equities deferred.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from KB-5 §5.
