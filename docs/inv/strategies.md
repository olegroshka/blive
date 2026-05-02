---
id: INV-1
title: Strategies Inventory
status: DRAFT
owner: shared
last_reviewed: 2026-05-02
version: 0.2
sources:
  - btest/strategies/                                       # accessed 2026-04-26
  - btest/research/Index Directional/                       # accessed 2026-04-26
  - btest/research/Triple Leveraged ETF/                    # accessed 2026-04-26
depends_on:
  - KB-5 strategy_taxonomy
referenced_by:
  - REQUIREMENTS.md §1, §15
  - ADR-013 (v1 scope)
---

# INV-1 — Strategies Inventory

## Purpose

Canonical list of every strategy `blive` will run, in catalogue or deferred form. Lifted from [KB-5 §3](../kb/strategy_taxonomy.md#3-currently-active--in-research-strategies); KB-5 owns archetype semantics, this file owns the run-list.

## Scope

In scope: every strategy in `btest/strategies/` and `btest/research/` that produces a `Strategy` dataclass. SMIM research-only strategies excluded ([KB-13](../kb/companion_projects.md#equitiessmim--smim-research-universes-under-btest)).

## Inventory

| strategy_id | btest path | archetype | universe | freq | rebal | btest status | v1 phase | NAV slice |
|-------------|------------|-----------|----------|------|-------|--------------|----------|-----------|
| `triple_lev_sma_filter_dsl` | `research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb` | A3 | TQQQ / TMF / IEF (US ETFs on NASDAQ / NYSE) | F0 | 1d (T+1 open) | active research, DSL-formalised | **Phase 1 (M2-IB.6)** — per [ADR-043](../decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) | 5–10% of total NAV, cap 10% ([ADR-020](../decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10)) |
| `tkan_v4_momentum_timing__1x` | `strategies/tkan_v4_momentum_timing.py` | A2 | `CAC.PA` (Lyxor CAC 40 UCITS ETF, XPAR — substrate per [ADR-021 SUPERSEDED](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) + [ADR-041](../decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver) Yahoo-suffix translation) | F0 | 1d close | research, **wire-validated end-to-end at `M2-IB.4a-happy-cacpa`** | **DEFERRED-NO-TARGET** per [ADR-043](../decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) (code stays in `blive.runtime.paper_pipeline` + `SingleAssetRunner` dispatch via [ADR-030](../decisions/DECISIONS.md#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010); revives when an A2-style timing strategy returns to scope) | TBD on revival |
| `tkan_v4_momentum_timing__2x` | `strategies/tkan_v4_momentum_timing.py` (2× variant) | A2 | CACT proxy (margin or 2× ETF, per ADR-016) | F0 | 1d close | research | Phase 4+ — DEFERRED with the 1× variant per ADR-043 | TBD |
| `index_directional` | `research/Index Directional/dsl_strategy.py` | A2 | CACT | F0 | 1d close | research, TKAN-driven | DEFERRED-NO-TARGET (was Phase 1 alt candidate; superseded with the rest of A2 by ADR-043) | TBD |
| `lagging_indecies` | `strategies/lagging_indecies.py` | A1a | global indices via ETF proxies (~5–15) | F0 | 1d close | research | **Phase 2 (post-Phase-1 live)** — promoted from Phase 3 by ADR-043 reorder | TBD |
| `xsec_momentum_long_short_sp500` | `strategies/momentum_long_short_sp500.py` | A1 | SP500 (~500 names) | F0 | 1d | btest stable | **deferred (post-M8)** | — |
| `harp_quarterly_momentum` | `strategies/harp_quarterly_momentum.py` | A1 | SP500 (~500 names) | F0 | 1m | btest stable, harp paper companion | **deferred (post-M8)** | — |
| `tiny_momentum_ls` | `strategies/tiny_momentum_ls.py` | A1 | small subset | F0 | 1d | dev / smoke | deferred — single-name | — |
| `custom_strategy` | `strategies/custom_strategy.py` | — | — | — | — | placeholder | — | — |

## Conventions

- `strategy_id`: stable id used in `LiveRun` records and event log.
- `freq`: F0–F5 per [KB-5 §4](../kb/strategy_taxonomy.md#4-frequency-roadmap).
- `archetype`: A1, A1a, A2, A3 (current) or A4–A8 (future) per [KB-5 §2](../kb/strategy_taxonomy.md#2-archetype-catalogue).
- `v1 phase`: per [ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only).

## Cross-References

- [KB-5 §3](../kb/strategy_taxonomy.md#3-currently-active--in-research-strategies) — full strategies table with v1 scope annotation.
- [ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) — phasing decision.
- [OQ-013](../decisions/OPEN_QUESTIONS.md#oq-013--which-strategies-are-funded-for-v1-and-what-nav-slice) — NAV slice still pending.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from KB-5 §3.
- **v0.2 (2026-05-02)** — Phase 1 strategy switch per [ADR-043](../decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2). `triple_lev_sma_filter_dsl` row promoted to Phase 1 (M2-IB.6 target). `tkan_v4_momentum_timing__1x` row demoted to DEFERRED-NO-TARGET (code stays — wire-validated end-to-end at `M2-IB.4a-happy-cacpa`; revives when an A2-style strategy returns to scope). `tkan_v4_momentum_timing__2x` carries the same A2 deferral. `index_directional` (was Phase 1 alt candidate) demoted with the rest of A2. `lagging_indecies` promoted Phase 3 → Phase 2 to reflect the ADR-043 reorder.
