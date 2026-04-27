---
id: DD-3
title: Config Schemas
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1
sources:
  - REQUIREMENTS.md §5.1, §5.10, §5.12, §5.13
  - ADR-028 (strategy config shape)
  - ADR-020 (Phase 1 NAV slice)
  - ADR-021 (CAC.PA proxy)
  - ADR-022 (TKAN freshness window)
  - ADR-023 (TKAN artefact path and refresh)
  - INV-4 (risk check thresholds and override paths)
depends_on:
  - DD-1
  - INV-4
  - INV-6
  - REQUIREMENTS
referenced_by:
  - src/blive/strategy/loader.py (consumes these schemas via Pydantic)
  - src/blive/risk/* (reads risk_overrides)
  - tests/unit/strategy/* (validation tests)
---

# DD-3 — Config Schemas

## Purpose

Field-level data dictionary for every YAML config knob blive consumes at startup. The shape is locked by [ADR-028](../decisions/DECISIONS.md#adr-028--strategy-config-shape-python-build_strategy--blive-yaml-overrides); this artefact specifies the *concrete fields*: type, default, range, override path, validation rule, and worked example.

The Pydantic models in `blive.strategy.config` (M1 deliverable) are the executable counterpart of this dictionary.

## Scope

**In:**

- `LiveStrategyConfig` — top-level YAML at `~/.blive/strategies/{strategy_id}/live.yaml`.
- Sub-objects: `LiveOverrides`, `LiveBorrowProvider`, `LiveFinancingProvider`, `LiveKillSwitch`, `RiskOverrides`, `ArtefactPaths`.

**Out:**

- The btest `Strategy` dataclass schema — owned by KB-1 (btest-side).
- `BacktestConfig` knobs — owned by btest; blive's `risk_overrides` only overlays specific risk-check thresholds.
- Storage schemas (DD-4, MISSING — M4).
- REST payloads (DD-5, MISSING — M6).
- Metric schemas (DD-6, MISSING — M7).

## Conventions

- Every schema is a Pydantic v2 `BaseModel` with `model_config = ConfigDict(extra="forbid", frozen=True)`. Unknown keys raise at parse time so typos don't silently drop. Frozen so the resolved config is immutable per [ADR-009](../decisions/DECISIONS.md#adr-009--crash-only-design).
- Numeric thresholds are `Decimal`, never `float`, per [DD-1](./domain_objects.md) conventions.
- File paths admit `~` expansion at parse time (resolved to absolute paths).
- Times are durations in seconds (integers) for staleness windows; days for artefact freshness; both are non-negative.

## 1. `LiveStrategyConfig` (top-level)

The contents of `~/.blive/strategies/{strategy_id}/live.yaml`. One file per strategy id.

| Field | Type | Default | Range | Notes |
|-------|------|---------|-------|-------|
| `strategy_id` | `str` | (required) | non-empty; `[a-z0-9_]+` | matches the directory name and the `Order.strategy_id` written by the Sizer ([DD-1 §2.4](./domain_objects.md#24-order)) |
| `strategy_module` | `str` | (required) | dotted Python path | e.g. `btest.strategies.tkan_v4_momentum_timing`; module must expose `build_strategy(**kwargs) -> Strategy` per [REQUIREMENTS §5.13](../../REQUIREMENTS.md) |
| `build_strategy_kwargs` | `Mapping[str, Any]` | `{}` | JSON-serialisable | keyword arguments forwarded to `build_strategy(**kwargs)` |
| `nav_slice` | `Decimal` | (required) | `0 < x ≤ 0.10` | fraction of account NAV; cap of 0.10 enforced per [ADR-020](../decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10) |
| `live_overrides` | `LiveOverrides` | (default-constructed) | — | execution-level overrides (§2) |
| `live_borrow_provider` | `LiveBorrowProvider \| None` | `None` | — | overlays `Strategy.costs.live_borrow_provider` if set (§3) |
| `live_financing_provider` | `LiveFinancingProvider \| None` | `None` | — | overlays `Strategy.costs.live_financing_provider` if set (§4) |
| `live_kill_switch` | `LiveKillSwitch \| None` | `None` | — | per-strategy kill criteria distinct from `BacktestConfig.drawdown_policy` (§5) |
| `artefact_paths` | `ArtefactPaths` | `ArtefactPaths(paths={})` | — | per-factor path overrides (§6) |
| `risk_overrides` | `RiskOverrides` | (default-constructed) | — | per-strategy overrides for [INV-4](../inv/risk_checks.md) thresholds (§7) |

### Validation rules

- `strategy_id` and the *directory name containing the YAML* must match — the loader raises if they disagree (catches misplaced files).
- `nav_slice > 0.10` raises a hard validation error citing ADR-020.
- Forbidden top-level keys (per [REQUIREMENTS §5.10](../../REQUIREMENTS.md)): `factors`, `signals`, `universe`, `portfolio.long_book`, `portfolio.short_book` — these would change the strategy's topology and are not legal as overrides. `extra="forbid"` catches them.

## 2. `LiveOverrides`

Overlays `Strategy.execution.live_overrides`. None of these have backtest counterparts; they only matter in live mode.

| Field | Type | Default | Range | Notes |
|-------|------|---------|-------|-------|
| `time_in_force` | `Literal["DAY", "GTC", "IOC", "FOK", "OPG"] \| None` | `None` | — | overrides the strategy's TIF when set |
| `routing` | `Literal["SMART", "PRIMARY", "DIRECT"] \| None` | `"SMART"` | — | IB routing per [KB-2 §5](../kb/ib_capability_matrix.md#5-routing); explicit, never silent default |
| `direct_venue` | `str \| None` | `None` | uppercase MIC when set | required iff `routing == "DIRECT"` |
| `ib_algo` | `str \| None` | `None` | one of `{"Adaptive","TWAP","VWAP","Arrival Price","Percentage of Volume",None}` | when set, the IB adapter (M3) routes via the algo |
| `ib_algo_params` | `Mapping[str, Any]` | `{}` | JSON-serialisable | algo-specific parameters; passed through unchanged |
| `outside_rth` | `bool` | `False` | — | when True, RC-09 is bypassed for this strategy ([INV-4 §RC-09](../inv/risk_checks.md)) |

## 3. `LiveBorrowProvider`

Overlays `Strategy.costs.live_borrow_provider`. Replaces btest's static `BorrowCost.default_annual_rate` ([KB-1 §8](../kb/btest_dsl_inventory.md#8-costs)) with a live source.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `kind` | `Literal["ib", "static"]` | (required) | `"ib"` queries the IB adapter; `"static"` keeps a `default_annual_rate` |
| `default_annual_rate` | `Decimal \| None` | `None` | required iff `kind == "static"` |
| `cache_ttl_seconds` | `int` | `3600` | `≥ 0` | IB adapter caches per-symbol rates for this long |

## 4. `LiveFinancingProvider`

Overlays `Strategy.costs.live_financing_provider`. Replaces btest's static `FinancingCost` curve.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `kind` | `Literal["ib", "static"]` | (required) | `"ib"` queries IB tier rate; `"static"` keeps the btest curve |
| `base_rate_curve` | `Literal["ESTER", "SOFR", "static"] \| None` | `None` | when `kind == "static"`; defaults to the strategy's btest spec value |
| `spread_bps` | `Decimal` | `0` | `≥ 0` | added to the base rate |

## 5. `LiveKillSwitch`

Per-strategy kill criteria distinct from the system kill-switch ([INV-4 RC-13](../inv/risk_checks.md)) and distinct from `BacktestConfig.drawdown_policy`. When triggered, blive cancels the strategy's open orders and pauses submission for that strategy (other strategies unaffected).

| Field | Type | Default | Range | Notes |
|-------|------|---------|-------|-------|
| `max_intraday_drawdown_bps` | `Decimal \| None` | `None` | `> 0` when set | trigger when intraday drawdown exceeds threshold (in bps of strategy NAV) |
| `max_consecutive_rejects` | `int \| None` | `5` | `≥ 1` when set | trigger when ≥ N rejects in a row from the broker |
| `max_consecutive_reject_window_seconds` | `int` | `60` | `≥ 1` | window for the consecutive-reject count |
| `max_position_age_days` | `int \| None` | `None` | `≥ 1` when set | trigger when an open position is held longer than threshold (paranoid stop-loss) |

## 6. `ArtefactPaths`

Per-factor overrides for `ExternalFactor.path` ([KB-1 §4](../kb/btest_dsl_inventory.md#4-factors)). Lets prod artefact paths differ from research paths per [ADR-023](../decisions/DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership).

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `paths` | `Mapping[str, Path]` | `{}` | keys are factor names (matching `Strategy.factors[name]`), values are paths to artefact files; `~` expanded |

### Validation rules

- Every key must reference a factor in the loaded `Strategy` (raises after `build_strategy()` returns if a key has no matching factor).
- Every path must exist at parse time (validation error if not — fails fast).
- For each path, the loader records the SHA-256 in the spec id per [ADR-028](../decisions/DECISIONS.md#adr-028--strategy-config-shape-python-build_strategy--blive-yaml-overrides) decision body.

## 7. `RiskOverrides`

Per-strategy overrides for the [INV-4](../inv/risk_checks.md) risk-check thresholds. Only the M1 RC subset is exposed at M1 (RC-08, RC-09, RC-12, RC-13); the field set widens at M4 when the rest of the RCs land.

| Field | Type | Default | Range | INV-4 row | Notes |
|-------|------|---------|-------|-----------|-------|
| `max_data_staleness_intraday_sec` | `int` | `300` (5 min) | `> 0` | RC-08 | per [INV-4 RC-08](../inv/risk_checks.md); per-strategy / per-frequency aware |
| `max_data_staleness_daily_sec` | `int` | `86400` (1 d) | `> 0` | RC-08 | EOD data window |
| `outside_rth_allowed` | `bool` | `False` | — | RC-09 | mirrored from `live_overrides.outside_rth` for consistency |
| `max_model_artefact_age_days` | `int` | `30` | `≥ 1` | RC-12 | hard threshold per [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning); refuses to size when exceeded |
| `model_artefact_warning_age_days` | `int` | `21` | `≥ 1` | RC-12 | warning threshold per ADR-022; emits `ArtefactFreshnessWarning` event |

### Validation rules

- `model_artefact_warning_age_days < max_model_artefact_age_days` enforced (warn before block).
- M1 fields-only at M1; the loader admits but **ignores** unknown M4-tier RC keys (RC-01..RC-07, RC-10, RC-11) so a forward-compatible YAML written today doesn't reject when the rest of the RCs land. Until M4, these keys log a one-time `RiskOverrideKeyIgnored` warning. After M4, they validate normally. This is a deliberate exception to `extra="forbid"` for `RiskOverrides` only.

## 8. Worked example: `tkan_v4_momentum_timing` 1×

```yaml
# ~/.blive/strategies/tkan_v4_momentum_timing_1x/live.yaml
strategy_id: tkan_v4_momentum_timing_1x
strategy_module: btest.strategies.tkan_v4_momentum_timing
build_strategy_kwargs:
  theta: 0.08
nav_slice: 0.05            # Phase 1 lower bound per ADR-020

live_overrides:
  time_in_force: DAY
  routing: SMART
  outside_rth: false

live_kill_switch:
  max_intraday_drawdown_bps: 200       # 2% of strategy NAV
  max_consecutive_rejects: 5
  max_consecutive_reject_window_seconds: 60

artefact_paths:
  paths:
    tkan_max: ~/.blive/artefacts/tkan_v4_momentum_timing/tkan_v4/pred_cache.pkl

risk_overrides:
  max_data_staleness_intraday_sec: 300
  max_model_artefact_age_days: 30
  model_artefact_warning_age_days: 21
```

The Phase 1 binding to `CAC.PA` is *not* in this YAML — it lives in the btest module's `build_strategy()` body (the Phase-1 deviation from research-CACT-totalreturn to live-CAC.PA-priceview is part of the strategy module's build, not a YAML override) per [ADR-021](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf). Future Phase-1.1 work may parameterise the instrument and move it into `build_strategy_kwargs`.

## 9. Override merge order

When the loader resolves a `LiveStrategyConfig` against a freshly-built `Strategy`:

1. `build_strategy(**build_strategy_kwargs)` returns a `Strategy`.
2. `live_overrides.*` non-`None` fields are written onto a copy of `Strategy.execution.live_overrides` (or installed if absent).
3. `live_borrow_provider` / `live_financing_provider` (when set) are installed on `Strategy.costs.live_borrow_provider` / `Strategy.costs.live_financing_provider`.
4. `live_kill_switch` (when set) is installed at a blive-only attribute `LiveStrategy.kill_switch_config` (the btest `Strategy` is not modified — kill-switch is purely live-mode).
5. `artefact_paths.paths` rewrites `ExternalFactor.path` for each named factor.
6. `risk_overrides.*` are surfaced to the `RiskEngine` constructor via `LiveStrategy.risk_overrides`; they do not modify the btest `Strategy`.
7. The loader computes `spec_id = sha256(yaml_canonical_bytes ‖ strategy_module ‖ btest_version ‖ blive_version ‖ Σ artefact_sha256)` and records it on `LiveStrategy.spec_id`.

The merge is idempotent: applying twice with the same YAML yields the same `LiveStrategy` (modulo `spec_id` which is deterministic).

## 10. Cross-References

- [REQUIREMENTS §5.1, §5.10, §5.12, §5.13](../../REQUIREMENTS.md) — strategy ingest, override grammar, spec id, sizer / discovery.
- [ADR-028](../decisions/DECISIONS.md#adr-028--strategy-config-shape-python-build_strategy--blive-yaml-overrides) — config shape locked.
- [ADR-020](../decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10), [ADR-021](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf), [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-023](../decisions/DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership) — Phase 1 specifics consumed here.
- [INV-4](../inv/risk_checks.md) — risk-check thresholds and override paths.
- [KB-1 §1, §4, §7, §8](../kb/btest_dsl_inventory.md) — btest fields these schemas overlay.
- [DD-1](./domain_objects.md) — `Decimal` / UTC / enum conventions.
- `src/blive/strategy/config.py` (M1) — Pydantic models for these schemas.

## Open Questions

None blocking M1. Future:

- DD-3 may grow a top-level `engine` section (paper/ib/shadow/live mode + per-strategy mode override) when M2 lands the IB adapter.
- DD-3 may grow `data_sources` keys when ADR-017's per-instrument routing config gets concrete at M2 (per-instrument EODHD vs IB streaming).

## Changelog

- **v0.1 (2026-04-27)** — initial DRAFT at M1. Locks the YAML schema for `LiveStrategyConfig` and its sub-objects per ADR-028; surfaces the M1 RC subset for `RiskOverrides` with M4 forward-compat for the rest.
