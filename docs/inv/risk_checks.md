---
id: INV-4
title: Risk Checks Inventory
status: DRAFT
owner: Claude
last_reviewed: 2026-05-06
version: 0.2
sources:
  - REQUIREMENTS.md §5.5
  - btest/src/quantdsl_backtest/dsl/backtest_config.py  # accessed 2026-04-26
depends_on:
  - KB-1 btest_dsl_inventory §9 (RiskChecks, DrawdownPolicy)
  - KB-3 ib_pacing_spec §1, §9 (rate-limit defaults)
  - KB-6 cost_margin_dictionary §6, §7 (RiskChecks, DrawdownPolicy)
  - KB-15 parity_methodology §"Unit-of-quote" (RC-10 cross-link)
  - ADR-050 (EODHD-vs-IB unit-of-quote conversion at sizing time)
referenced_by:
  - REQUIREMENTS.md §5.5
  - ADR-008 (RiskEngine no-bypass)
  - ADR-050 (RC-10 implementation surface)
---

# INV-4 — Risk Checks Inventory

## Purpose

Canonical list of every pre-trade risk check the `RiskEngine` enforces, with default thresholds, override paths, and on-breach actions. Lifted from [REQUIREMENTS §5.5](../../REQUIREMENTS.md); REQUIREMENTS will reference this file in v0.2.

## Scope

In scope: pre-trade risk checks executed in order on every order before submission.

Out of scope: post-trade reconciliation drift detection (REQUIREMENTS §5.7); kill-switch trigger sources (REQUIREMENTS §5.5.kill-switch); strategy-internal `DrawdownPolicy` (KB-6 §7 — applies before order proposal, not at risk-check time).

## Conventions

- **Severity**: `block` (refuse the order, emit `RiskBreach`) · `scale` (proportionally shrink the order) · `warn` (allow but emit warning event).
- **Override path**: where in the strategy YAML the default can be raised/lowered.
- **Persistence**: whether the breach state survives a restart (relevant for hard-kill conditions).

## Inventory

| # | Check | Default threshold | Severity | Override path | Notes |
|---|-------|-------------------|----------|---------------|-------|
| RC-01 | Strategy gross leverage | `RiskChecks.max_gross_leverage` (default 2.0) | block | `risk.max_gross_leverage` | computed as `(\|long\| + \|short\|) / NAV_strategy` |
| RC-02 | Strategy net exposure | `LongShortPortfolio.target_net_exposure` ± 0.10 | block | `portfolio.target_net_exposure_tolerance` | applies only to L/S portfolios |
| RC-03 | Per-name max abs weight | `LongShortPortfolio.max_abs_weight_per_name` (default 0.03) | block | `portfolio.max_abs_weight_per_name` | per-strategy NAV |
| RC-04 | Daily loss vs session-start equity | -2.0% soft warn, -3.5% hard kill | warn / block | `risk.max_daily_loss_warn`, `risk.max_daily_loss_kill` | resets at IB session boundary |
| RC-05 | Order rate per strategy | ≤ 5/sec, ≤ 60/min | block | `risk.max_orders_per_sec_strategy`, `_per_min` | defends against engine bugs |
| RC-06 | Order rate global | ≤ 20/sec | block | `risk.max_orders_per_sec_global` | cumulative across strategies; well below IB's 50/sec hard limit (KB-3 §1) |
| RC-07 | Position concentration | single-name notional ≤ 8% of strategy NAV | block | `risk.max_single_name_notional_pct` | tighter than RC-03 since net-of-leverage |
| RC-08 | Stale data | refuse if last bar > 5 min old (intraday) or > 1 day (EOD) | block | `risk.max_data_staleness_intraday_sec`, `..._daily_sec` | per-strategy frequency-aware (KB-5 §4 commitment) |
| RC-09 | Market hours | refuse if not RTH unless explicitly enabled | block | `execution.live_overrides.outside_rth` | per-strategy |
| RC-10 | Reference price sanity | refuse if limit/stop price deviates > ±50% from IB-equivalent reference | block | `risk.max_price_deviation_pct` | M3.1 implemented per [ADR-050](../decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only); reference is the EODHD bar close converted via [`blive.adapters.eodhd.eodhd_to_ib_price`](../../src/blive/adapters/eodhd/conventions.py); MKT/ADAPTIVE_MKT skip; threshold widened from v0.1's ±20% because leveraged ETPs (e.g. QQL3) hit 11.74% max daily range per INV-14 v0.7 |
| RC-11 | Drawdown scaling | applies `DrawdownPolicy.mode` per [KB-6 §7](../kb/cost_margin_dictionary.md#7-drawdownpolicy) | scale | `risk.drawdown_policy.*` | reduces target weights before order proposal; not strictly a risk check but governs the same flow |
| RC-12 | Stale model artefact | refuse if A2/A3 ML artefact older than freshness window | block (warn at 21d) | `risk.max_model_artefact_age_days` | default **30 days hard, 21 days warning** per [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning); per-strategy override allowed |
| RC-13 | Kill-switch armed | refuse all new submissions when armed | block | n/a (system) | system-wide; cancels open orders, holds positions until human resume |

## Order of evaluation

The RiskEngine applies checks **in order**. First failure short-circuits to a `RiskBreach` event; later checks not evaluated. Order matters for diagnostics — operators should see "stale data" before "order rate" if both would trip.

Default order: RC-13 (kill-switch armed) → RC-08 (stale data) → RC-09 (market hours) → RC-12 (model artefact) → RC-11 (drawdown scaling, applied as multiplier; if scale=0, treat as RC-block) → RC-04 (daily loss) → RC-01, RC-02, RC-03 (portfolio shape) → RC-07 (concentration) → RC-10 (price sanity) → RC-05, RC-06 (rate limits, last because they're "engine bugs" defences).

## On-breach actions

- **block**: emit `RiskBreach(strategy_id, check_name, severity="block", details)`; the order is not submitted; an alert is raised.
- **scale**: target weights / quantities multiplied by the scale factor; `RiskBreach(severity="scale", scale_factor)` emitted; submission proceeds with scaled order.
- **warn**: order submitted normally; `RiskBreach(severity="warn")` emitted for observability.

`RiskBreach` events are persisted (REQUIREMENTS §11) and visible in the UI System page (REQUIREMENTS §5.8).

## Cross-References

- [REQUIREMENTS §5.5](../../REQUIREMENTS.md) — narrative description.
- [KB-1 §9](../kb/btest_dsl_inventory.md#9-backtest-configuration) — RiskChecks DSL surface.
- [KB-3 §1, §9](../kb/ib_pacing_spec.md) — rate-limit defaults.
- [KB-6 §6, §7](../kb/cost_margin_dictionary.md) — RiskChecks and DrawdownPolicy semantics.
- [ADR-008](../decisions/DECISIONS.md#adr-008--riskengine-no-bypass-enforced-architecturally) — no-bypass.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from REQUIREMENTS §5.5.
- **v0.2 (2026-05-06 / M3.1)** — RC-10 promoted from DRAFT-only to implemented per [ADR-050](../decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only). Threshold widened from ±20% to ±50%: the original ±20% would false-positive on legitimate gap-overnight moves on leveraged ETPs (QQL3 hit 11.74% max daily range per [INV-14 v0.7](./ib_error_codes.md)). Reference price source: the EODHD bar close converted via [`blive.adapters.eodhd.eodhd_to_ib_price`](../../src/blive/adapters/eodhd/conventions.py) — `RiskInputs.reference_price` is the IB-equivalent value. MKT / ADAPTIVE_MKT orders skip RC-10 (no price to sanity-check; the conversion at sizing time is the only relevant check for them). Catalogue-miss detection (a symbol absent from the EODHD convention catalogue) is the catalogue's own job — operator-curated entries with a documented confirmation source. M7 forward-list per [KB-15](../kb/parity_methodology.md): per-instrument bands once the M3.2 window characterises volatility profiles. Implementation: `src/blive/risk/checks.py` (RC-10 branch ordered after RC-12, before any future RC-05/RC-06 rate limits per §"Order of evaluation"); `RiskCheckCode.RC_10` added to `blive.domain.events`; tests at `tests/unit/risk/test_checks.py` (8 RC-10 tests including the canonical M3.1 case `test_rc10_lmt_far_above_reference_blocks` — EODHD-derived LMT $415 vs IB ref $39 → BLOCK).
