---
id: KB-13
title: Companion Projects Map
status: DRAFT
owner: Oleg primary, Claude assist
last_reviewed: 2026-04-26
version: 0.1
sources:
  - C:\Users\olegr\PycharmProjects\btest\README.md      # accessed 2026-04-26
  - C:\Users\olegr\PycharmProjects\harp\README.md       # accessed 2026-04-26
  - C:\Users\olegr\PycharmProjects\pt-liqadj\README.md  # accessed 2026-04-26
  - C:\Users\olegr\PycharmProjects\ForgeFolio\README.md # accessed 2026-04-26
depends_on: []
referenced_by:
  - KB-5 strategy_taxonomy §3, §5
  - ADR-018 (UK strategies refer to SMIM research)
  - REQUIREMENTS.md §1 (companion projects line)
---

# KB-13 — Companion Projects Map

## Purpose

Document Oleg's sibling projects under `C:\Users\olegr\PycharmProjects\` and how each does (or does not) interact with `blive`. Boundary clarity prevents accidental scope creep and accidental coupling.

## Sibling Projects

### btest — Backtesting research framework

- **Path**: `C:\Users\olegr\PycharmProjects\btest`.
- **Role**: Python DSL for systematic-strategy research and backtesting. Source of every strategy `blive` will run.
- **Status**: active, primary research workbench.
- **Stack**: Python 3.11, `uv`, FastAPI + React platform UI, ArcticDB cache, vectorbt + custom event-driven engines.
- **Relationship to blive**:
  - **blive depends on btest** ([ADR-010](../decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import)) — imports `FactorEngine`, `SignalEngine`, `PortfolioEngine`, all DSL dataclasses.
  - blive does **not** modify btest source; upstream changes flow via pinned version bump.
  - The btest `data/sources/registry.py` pattern is reused for live data adapters ([ADR-014](../decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction)).
  - btest's platform_api is a parallel control plane for backtest runs; blive has its own ([ADR-011](../decisions/DECISIONS.md#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred)). Shared aesthetic, separate deployments.
- **Versioning**: blive pins to a btest minor version; coordinated bumps. CI test that imports work after bump.

### harp — HARP paper replication

- **Path**: `C:\Users\olegr\PycharmProjects\harp`.
- **Role**: replication code + data for the paper *"Global Persistence, Local Residual Structure: Forecasting Heterogeneous Investment Panels"* (Roshka, 2026). Two-stage architecture (global pooled AR(1) + block-specific local PCA+ridge) for cross-sectional investment-panel forecasting.
- **Status**: paper submitted (arXiv econ.EM, SSRN); replication artefact.
- **Stack**: Python 3.11, `uv`.
- **Relationship to blive**:
  - **No direct runtime dependency.** blive does not import harp.
  - The `harp_quarterly_momentum` strategy in `btest/strategies/` references the paper's risk-adjusted-momentum signal as the strongest pure-price proxy for the G1-M2 disagreement signal. [ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) defers this strategy to post-M8 (single-name SP500 cross-sectional), so harp influences blive via btest indirectly, only when that phase activates.
  - harp's UK/EU panel results inform the universe basis for future UK strategies (per [ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8)).

### pt-liqadj — Portfolio-aware Liquidity Adjustment

- **Path**: `C:\Users\olegr\PycharmProjects\pt-liqadj`.
- **Role**: research / engineering project on portfolio-aware bond price/liquidity adjustments (GNN + Transformer + MLP baseline).
- **Status**: independent research; under publication evaluation (`PUBLICATION_EVAL_*.md` files present).
- **Stack**: Python with PyTorch.
- **Relationship to blive**: **none for v1.** Bond-market focus is orthogonal to ETF/index trading scope ([ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only)). Could become relevant if blive ever extends to bond strategies (far horizon).

### ForgeFolio — Portfolio monitoring & analysis (PyQt6 GUI)

- **Path**: `C:\Users\olegr\PycharmProjects\ForgeFolio`.
- **Role**: desktop portfolio-monitoring and analysis app — IB Flex Query, Tinkoff, Hargreaves Lansdown, Bloomberg Terminal integration; multi-currency; QuantStats reports.
- **Status**: active personal-finance / monitoring tool.
- **Stack**: Python with PyQt6.
- **Relationship to blive**:
  - **Adjacent but not part of blive's scope.** ForgeFolio is **monitoring**; blive is **execution**. Different concerns, different stacks, different runtime.
  - **Risk of confusion / overlap**: ForgeFolio reads IB account data and renders dashboards; blive will produce IB account events that ForgeFolio could in principle ingest. They may eventually share data but should not share processes.
  - **Decision deferred**: whether ForgeFolio reads from blive's event log directly (read-only) is post-M8 and depends on monitoring requirements; for v1 ForgeFolio continues to read from IB Flex Query independently.
  - **Open question**: should blive's daily NDJSON tape ([REQUIREMENTS §6.3](../../REQUIREMENTS.md)) be ForgeFolio-readable? Worth a separate OQ when ForgeFolio integration is contemplated.

### b-autobot — Placeholder

- **Path**: `C:\Users\olegr\PycharmProjects\b-autobot`.
- **Role**: appears to be an empty PyCharm starter (only `main.py` with the default `print_hi("PyCharm")` template).
- **Status**: placeholder / unused.
- **Relationship to blive**: **none.** Listed for completeness only.

### equities/smim/* — SMIM research universes (under btest)

- **Path**: `C:\Users\olegr\PycharmProjects\btest\equities\smim\` with subdirs `MIXED-200`, `UK-LC`, `UK-MC`, `US-LC`, `US-LC-ENERGY`, `US-LC-FINS`, `US-LC-HEALTH`.
- **Role**: research universes for the SMIM (Spectral Modal Investment Models) framework — sectoral / regional research.
- **Status**: research-only within btest. SMIM-Specific Context lives at `btest/docs/smim/CLAUDE.md`.
- **Relationship to blive**:
  - **Out of scope for v1**: SMIM is a research framework producing research outputs, not deployed strategies.
  - Post-M8: UK-LC and UK-MC universes are candidate sources for the deferred UK strategies ([ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8)).
  - blive does not import any `smim/` code.

## Boundary Summary

| Project | blive imports it? | blive runs strategies from it? | Active interaction in v1? |
|---------|-------------------|--------------------------------|---------------------------|
| btest | yes (engines + DSL) | yes (every blive strategy is btest-authored) | **yes — primary dependency** |
| harp | no | indirectly (via `harp_quarterly_momentum` in btest, deferred post-M8) | no for v1 |
| pt-liqadj | no | no | no |
| ForgeFolio | no | no | no for v1; read-only monitoring integration possibly post-M8 |
| b-autobot | no | no | no |
| smim/* | no | no for v1; UK-LC/UK-MC post-M8 (see ADR-018) | no for v1 |

## Repository / Deployment Choices

- Each project has its own git repo and its own `.venv`.
- blive depends on btest as a Python package (pinned version); installed via `uv sync` or equivalent. No git-submodule coupling.
- ForgeFolio runs on a separate machine / workstation and is unrelated to blive's deploy host.
- harp and pt-liqadj are research artefacts; not deployed.

## Open Questions

- **OQ-023** (raised here for tracking) — should blive's daily NDJSON trade tape (REQUIREMENTS §6.3) be ForgeFolio-readable, and if so, on what cadence and how is access mediated? Defer to post-M8 ForgeFolio integration discussion.

## Cross-References

- [REQUIREMENTS §1](../../REQUIREMENTS.md) — companion projects line.
- [KB-5 §3](strategy_taxonomy.md#3-currently-active--in-research-strategies) — strategies sourced from `btest/strategies/`.
- [KB-5 §5](strategy_taxonomy.md#5-asset-class-coverage-current-and-near-future) — UK equities asset class.
- [ADR-010](../decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — btest reuse.
- [ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8) — UK deferral.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from sibling READMEs.
