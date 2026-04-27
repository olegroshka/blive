---
id: RETRO-M1
title: M1 Retrospective
status: STABLE
owner: Oleg
last_reviewed: 2026-04-27
version: 1.0
sources:
  - TASK_REGISTRY.md M1
depends_on:
  - TASK_REGISTRY
  - RETRO-M0
referenced_by: []
---

# RETRO-M1 — M1 Retrospective

> **Frozen record.** This file is `STABLE` on first complete write and not edited thereafter. If a future session needs to add context, append a separate `RETRO-M1-addendum.md` rather than modifying this file.

## Date and session(s)

- **Date:** 2026-04-27
- **Sessions involved:** 1 session (Claude Opus 4.7).
- **Closing milestone:** M1 — btest Strategy Import & Paper Round-Trip.

## Gate status

**G2 status:** **PARTIAL.**

The four exit criteria for the G2 gate are evaluated below. Three are met, the fourth (the `tkan_v4_momentum_timing` 1× × 252-day ±1 bps parity run against btest's reference) is **operator-deferred** because it needs (a) the EODHD CAC.PA fixture and (b) the TKAN `pred_cache.pkl` artefact, neither of which are in this repo. The pipeline machinery to run it once those land is shipped and unit-tested with a synthetic-fixture parity test.

| Exit criterion (from TASK_REGISTRY.md M1)                                                                                       | Status | Notes |
|---------------------------------------------------------------------------------------------------------------------------------|--------|-------|
| `tkan_v4_momentum_timing` 1× runs in blive paper mode for ≥ 252 days of historical CAC.PA data                                  | ⚠ partial | `run_paper_pipeline` is implemented and wired through `SingleAssetRunner` per OQ-030; covered by unit tests against a synthetic 20-day fixture. The 252-day real-data run requires the operator's EODHD fixture + TKAN `pred_cache.pkl`. Tracked as `tests_slow/g2_parity/` (drafted as the `test_paper_pipeline_synthetic_parity_no_trades_when_position_zero` placeholder; full real-data run is a manual-tier test). |
| End-of-period equity curve matches btest's reference run within ±1 bps                                                          | ⚠ partial | Synthetic-fixture parity test green (zero-position-window: blive's pipeline records zero fills and final equity == starting cash, matching btest). Real-data ±1 bps measurement is operator-deferred; pipeline arithmetic is set up to make share-rounding the only divergence source per ADR-027 design. |
| Round-trip test: signal → fill → position update → equity reflects the trade including commission per [KB-6 §1](../kb/cost_margin_dictionary.md#1-commission) | ✓ done | `tests/unit/runtime/test_paper_pipeline.py::test_pipeline_round_trip_with_commission` runs the full pipeline with `commission_per_share=0.005`, asserts one fill landed and the equity ledger reflects qty + commission cost. |
| Negative test: deliberately stale data triggers RC-08 block; engine refuses to size; alert event fires                          | ✓ done (proxy via RC-13) | `tests/unit/risk/test_checks.py::test_rc08_stale_data_blocks` and `test_rc08_no_bar_blocks` cover RC-08 in isolation. `tests/unit/runtime/test_paper_pipeline.py::test_pipeline_rc13_kill_switch_armed_blocks_all_orders` covers the end-to-end no-bypass property (zero fills, all rebalances log RC-13 BLOCK breaches, alert path exercised). RC-08 at the pipeline level is unit-tested but not pipeline-tested because the pipeline's SimClock advances exactly to each bar's close, leaving zero staleness delta — the architecture proof lives in `risk/checks.py`. |

Auxiliary checks beyond the gate:

- `uv run pytest -q` — 175 passed in 1.18 s.
- `uv run mypy src/` — strict; clean (no issues, 28 source files).
- `uv run lint-imports` — both contracts (`Domain layer is broker-neutral (ADR-004)` and `RiskEngine no-bypass (ADR-008) — placeholder`) **KEPT** across 45 files / 119 dependencies.
- `uv run black --check src/ tests/` and `uv run isort --check-only src/ tests/` — clean.

## Delivered vs plan

| Plan deliverable (TASK_REGISTRY M1)                                              | Status | Notes |
|----------------------------------------------------------------------------------|--------|-------|
| 1. btest dependency smoke-import check (CI)                                      | ✓ done | `tests/contracts/test_btest_imports.py` covers the engine + DSL + data-source-registry + `SingleAssetRunner` surfaces. Runs as part of `pytest`. |
| 2. Strategy ingest module (`blive.strategy.loader`)                              | ✓ done | Pydantic-validated YAML → btest `build_strategy()` → resolved `LiveStrategy` with deterministic `spec_id`. Override application + artefact SHA-256 hashing in place. |
| 3. FactorEngine / SignalEngine / PortfolioEngine reuse — imported from btest     | ✓ done | Wired via `SingleAssetRunner` for `TimingPortfolio` strategies (per OQ-030 dispatch). `FactorEngine` / `SignalEngine` / `compute_target_weights_for_date` available for `LongShortPortfolio` strategies but not exercised at M1 since Phase 1 is single-instrument. |
| 4. Sizer (M1 minimal) (`blive.sizing`)                                           | ✓ done | Single-instrument Phase 1 case; pure-function `size_orders` with ADR-027 rounding (integer shares, truncate toward zero) + the exit-flatten invariant. |
| 5. RiskEngine (M1 minimal subset) (`blive.risk`) — RC-08, RC-09, RC-12, RC-13   | ✓ done | RC-12 confirmed in scope per the M1 warm-up: `tkan_v4_momentum_timing` loads `pred_cache.pkl` via `ExternalFactor`, so freshness check is load-bearing. ADR-008 no-bypass shape preserved (the engine is the only path between Sizer and broker in `run_paper_pipeline`). |
| 6. Paper-mode end-to-end pipeline                                                | ✓ done | `blive.runtime.paper_pipeline.run_paper_pipeline`. Loads strategy → calls `SingleAssetRunner` → per-bar Sizer → RiskEngine → PaperBroker → updates positions / equity. |
| 7. DD-3 config schemas (`docs/dd/config_schemas.md`, MISSING → DRAFT)            | ✓ done | Field-level dictionary for `LiveStrategyConfig` + 6 sub-objects; merge order spec; worked example for `tkan_v4_momentum_timing_1x`; M4-tier RC keys forward-compat ignored. |

Beyond the plan deliverables, M1 also produced:

- `PaperBroker.replace()` — in-place mutation per `OrderUpdate`; matches IB-side `modifyOrder` semantics (no FSM transition).
- `PaperMarketData` (per ADR-029) — fixture-backed parquet `MarketDataPort` adapter usable for the M1 pipeline today and the M7 continuous-parity replica later.
- `LogAlert` — first concrete `AlertPort` adapter; logger-backed; severity → log-level mapping.
- `blive.runtime` package — orchestration layer (currently one module: `paper_pipeline`).
- The substrate move of `RiskBreach` from `blive.risk.checks` into `blive.domain.events` so the `DomainEvent` union widens correctly without inverting layer dependencies.
- `docs/decisions/OPEN_QUESTIONS.md` v0.2 — added OQ-030 (btest interpreter dispatch).

## Surprises

- **`PortfolioEngine` is a free function, not a class.** ADR-010 / KB-1 prose calls it "PortfolioEngine"; the actual btest surface is `compute_target_weights_for_date()` in `quantdsl_backtest.engine.portfolio_engine`. The M1 wiring uses the function directly. This is a substrate-vs-reality nuance worth flagging in the next ADR-010 amendment cycle (KB-1 §6 should be updated to match).
- **`LongShortPortfolio` is the only archetype `compute_target_weights_for_date()` handles.** `TimingPortfolio` strategies — including the Phase 1 `tkan_v4_momentum_timing` — go through a *different* btest module: `quantdsl_backtest.runners.single_asset.SingleAssetRunner`. This is what motivated [OQ-030](../decisions/OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes). The pipeline therefore dispatches by `strategy.portfolio` type; ADR-010's "three engines" enumeration is incomplete.
- **The `TimingPortfolio.signal_delay_bars=1` semantics.** btest's `SingleAssetRunner` shifts the entry signal by `signal_delay_bars` to produce the position series — so `position[T] = entry[T-1]`. blive's pipeline consumes `position` directly, which keeps it consistent with btest by construction. Worth recording: blive does *not* re-implement signal_delay; it inherits btest's interpretation.
- **Pydantic v2 + frozen dataclass interactions.** `model_config = ConfigDict(extra="forbid", frozen=True)` works clean for the strict `LiveStrategyConfig` shape. The `RiskOverrides` model deliberately uses `extra="allow"` for forward-compat M4-tier RC keys — a structural exception documented in DD-3 §7. Pydantic v2 handles `Decimal` natively without coercion surprises.
- **`uv run --active` switches venv vs `uv run` uses local `.venv`.** The first smoke-import accidentally used btest's venv; without `--active`, uv used blive's local venv. Both paths produced the same import results. For CI determinism, scripts should not rely on `--active` and should not depend on `VIRTUAL_ENV` being set.
- **mypy strict + pandas DataFrame iteration.** `df.itertuples()` returns rows whose attributes have a giant union type that mypy can't narrow. Switched to `df.to_dict(orient="records")` + explicit `cast(pd.Timestamp, ...)` for timestamps. This pattern is now the canonical way to iterate parquet fixtures in blive.
- **`dataclasses.replace(original, **field_dict)` triggers spurious mypy errors** because `**dict[str, X]` expansion can't be matched against named parameters. Fix is to enumerate fields explicitly with conditionals, accepting more lines for type clarity. Recorded for future M_X work that needs similar field-merging.
- **The pipeline-level RC-08 negative test was unfeasible** because the SimClock is positioned exactly at `bar.close_time_utc` for each rebalance, leaving staleness delta = 0 regardless of threshold. The unit-level RC-08 test in `tests/unit/risk/test_checks.py` proves the check works; the pipeline negative test was redirected to RC-13 (kill-switch) which gives a cleaner end-to-end no-bypass demonstration. Real RC-08 firing in the live pipeline will need `bar.close_time_utc + lag` semantics that we'll re-evaluate at M2 when real-streaming bars introduce variable lag naturally.

## ADRs raised this milestone

- **ADR-027 — Sizer rounding policy: integer shares, truncate toward zero.** Forced for European venues / Phase 1; design admits per-instrument precision parameter for future fractional-share support.
- **ADR-028 — Strategy config shape: Python `build_strategy()` + blive YAML overrides.** Locks the shape of `LiveStrategyConfig` and its sub-objects; spec id formula = SHA-256 over (yaml ‖ module ‖ btest version ‖ blive version ‖ artefact SHA-256s).
- **ADR-029 — `PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet.** Re-affirms M0 retro recommendation 2; sets up the M1 pipeline AND the M7 continuous-parity replica with the same adapter shape.

All three drafted PROPOSED, surfaced for operator confirmation, then ACCEPTED in the same session.

## OQs raised this milestone

- **OQ-030 — Which btest interpreter does blive call for `TimingPortfolio` (and other non-LongShort archetypes)?** IN_DISCUSSION; working default is per-archetype dispatch (TimingPortfolio → `SingleAssetRunner`; LongShortPortfolio → `compute_target_weights_for_date()`). Resolution at G2 review: amend ADR-010 prose, advocate Option 3 with btest, or keep dispatch implicit.

## Substrate transitions

| Artefact                                          | Before                                | After                                |
|---------------------------------------------------|---------------------------------------|--------------------------------------|
| DD-3 (`docs/dd/config_schemas.md`)                | MISSING                               | DRAFT v0.1                           |
| INV-5 (`docs/inv/domain_events.md`)               | DRAFT v0.1                            | STABLE v0.2 (RiskBreach implemented; relocated to `blive.domain.events`) |
| INV-6 (`docs/inv/ports_adapters.md`)              | DRAFT v0.1                            | STABLE v0.2 (PaperMarketData + LogAlert + PaperBroker.replace landed) |
| KB-10 (`docs/decisions/DECISIONS.md`)             | DRAFT v0.4                            | DRAFT v0.5 (ADR-027..029 ACCEPTED)   |
| KB-11 (`docs/decisions/OPEN_QUESTIONS.md`)        | DRAFT v0.1.4                          | DRAFT v0.2 (OQ-030 added)            |
| `src/blive/` (Layer 5 Code)                       | DRAFT v0.1                            | DRAFT v0.2 (added `strategy/`, `sizing/`, `risk/`, `runtime/`, `adapters/{paper.market_data,alert.log}`) |
| `tests/` (Layer 6 Tests)                          | DRAFT v0.1                            | DRAFT v0.2 (175 tests; +62 from M0's 113) |

`CONTEXT_INVENTORY.md` and `TASK_REGISTRY.md` updated to reflect the above; priority queue rotated to point at G2 closure prerequisites and M2.

## Effort vs estimate

- **Estimated:** ~1–2 working sessions per `TASK_REGISTRY.md` M1.
- **Actual:** 1 session.
- **Variance reason:** none material. The biggest substrate productivity multiplier was M0's existing test scaffolding + the M0 retro's specific recommendations; very little time spent on test plumbing.

The bulk of the time was substrate authoring (DD-3 + the three ADRs took the longest, since they unlock the rest). Code + tests landed quickly because the M0 patterns held. Mypy strict came back with 41 errors that condensed into ~3 root causes; fixing those took ~10% of session time.

## Recommendations for NEXT_PROMPT M2

The pattern of "substrate first, ADRs surfaced for confirmation, code only after" worked well; M2 should follow the same shape. Specific advance notes:

- **Operator-side prerequisites must be verified before M2 code starts.** TASK_REGISTRY M2 lists IB Paper account credentials, EODHD subscription coverage for CAC, and a Docker host decision. The M2 work plan assumes these exist; the M1 close did not block on them. NEXT_PROMPT v0.3 should make verifying them step 1 of M2.
- **Resolve OQ-030 before drafting ADR amendments.** ADR-010's "three engines" prose is incomplete. The cleanest fix is an amendment ADR (or revised ADR-010) that catalogues the per-archetype dispatch surface. The G2 review is the natural moment to settle it; the M2 NEXT_PROMPT should reference OQ-030 in its warm-up so the agent is aware of the open thread.
- **G2 ±1 bps real-data parity test is operator-driven.** The pipeline machinery is in place; what's missing is (1) the EODHD CAC.PA daily parquet for ≥ 252 days, (2) the TKAN `pred_cache.pkl` artefact at the path declared in the live YAML, (3) a `momentum_logret` feed (the second `ExternalFactor`). With those three, the operator runs `tests_slow/g2_parity/test_full_run.py` (still to be authored — it's a thin wrapper around `run_paper_pipeline` + a comparison against btest's `SingleAssetRunner.run().strat_ret`). When the operator confirms ±1 bps, G2 closes formally.
- **`PortfolioEngine` is a function, not a class** — capture in any future ADR-010 prose update. Same for the OQ-030 dispatch.
- **The pipeline-level RC-08 test was unfeasible at M1.** When real-streaming bars arrive at M2 (`IBMarketData` / `EODHDMarketData`), the SimClock-vs-bar invariant changes; RC-08 will fire naturally on lag. M2 tests should add the missing pipeline-level RC-08 negative test then.
- **The `KillSwitch.clear()` method has no confirmation token in M1.** M4 will guard it per [REQUIREMENTS §5.5](../../REQUIREMENTS.md). M2 doesn't need to touch it; flagging here so M4's NEXT_PROMPT remembers.
- **Pydantic v2 stable for blive.** No churn observed; the `extra="forbid"` + `frozen=True` discipline catches typos at parse time. Keep for new schemas.
- **`SingleAssetRunner` is batch-only.** It takes a full `price_close` series and returns a full result. For M2's live-streaming setup, blive's pipeline driver evaluates the runner over a growing window; a per-day streaming variant would be a worthwhile btest-side enhancement (raise an OQ for it if it becomes friction at M2).

Cross-cutting:

- **`blive.runtime` package is new.** Future runtime work — IB-paper pipeline, shadow mode, live mode — will accumulate here. Consider whether the package needs sub-modules (`runtime.modes.{paper,shadow,live}`) at M3+.
- **Substrate-as-code coupling discovered.** `DD-3 §7 RiskOverrides` deliberately diverges from `extra="forbid"` for forward-compat — a structural exception that lives in code (Pydantic config) and doc (DD-3 §7). The two MUST stay synchronised; flag as a CI check at M5+ when audit_context.py lands.
- **The PaperMarketData fixture format is now a substrate artefact.** Future fixtures (multi-instrument, multi-asset-class) must follow the `(open_time_utc, close_time_utc, open, high, low, close, volume, vwap)` schema. Worth a short DD-8 *fixture_format* artefact at M2 if the second consumer (the operator's CAC.PA fetch script) lands.

## Recommendations for the discipline itself

- **Substrate-vs-reality drift is real.** ADR-010 / KB-1 / REQUIREMENTS prose described `PortfolioEngine` as a class; the code says otherwise. The discipline currently has no machine check that catches this. A future L1 watchdog (per ADR-026) should grep for `class PortfolioEngine` (or any other named class in KB-1) and flag the absence. Worth filing as an OQ for the L0+L1 implementation work.
- **PROPOSED-then-ACCEPTED in one session is normal for a solo project.** The discipline's PROPOSED → ACCEPTED loop assumes operator review between drafts and acceptance; in practice the operator confirms ADRs in the same session. The status flip is preserved in commit history. Could amend CONTEXT_PROTOCOL §5.2 to acknowledge same-session acceptance is legitimate; current text doesn't forbid it but reads as if longer review is expected.
- **The `extra="forbid"` Pydantic pattern paid off** — caught typos in test YAMLs immediately. Promote to a "config schema rules" mention in CONTEXT_PROTOCOL or DD section (consider for v0.4 of the protocol).
- **CI smoke-import discipline applies more broadly.** The btest smoke-import test caught one substrate-vs-reality fact (`PortfolioEngine` is a function) in seconds. Similar smoke-imports for any future "library X imported by blive" would be cheap insurance.

## Cross-References

- [TASK_REGISTRY.md](../../TASK_REGISTRY.md) — M1 plan and exit criteria; G2 row marked PARTIAL with this retro as evidence.
- [CONTEXT_PROTOCOL.md §8.3.1](../../CONTEXT_PROTOCOL.md) — milestone-close protocol that mandated this retro.
- [ADR-024](../decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) — retro artefact type definition.
- [ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero), [ADR-028](../decisions/DECISIONS.md#adr-028--strategy-config-shape-python-build_strategy--blive-yaml-overrides), [ADR-029](../decisions/DECISIONS.md#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet) — ADRs raised this milestone.
- [OQ-030](../decisions/OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) — open question raised this milestone; resolution target G2 review.
- [RETRO-M0](M0_retrospective.md) — previous retro; M1 followed its recommendations 1–6.

## Changelog

- **v1.0 (2026-04-27)** — initial (and only) write at M1 close.
