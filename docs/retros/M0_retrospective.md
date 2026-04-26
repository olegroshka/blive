---
id: RETRO-M0
title: M0 Retrospective
status: STABLE
owner: Oleg
last_reviewed: 2026-04-26
version: 1.0
sources:
  - TASK_REGISTRY.md M0
depends_on:
  - TASK_REGISTRY
referenced_by: []
---

# RETRO-M0 — M0 Retrospective

> **Frozen record.** This file is `STABLE` on first complete write and not edited thereafter. If a future session needs to add context, append a separate `RETRO-M0-addendum.md` rather than modifying this file.

## Date and session(s)

- **Date:** 2026-04-26
- **Sessions involved:** 1 session (Claude Opus 4.7).
- **Closing milestone:** M0 — Skeleton & Domain Types.

## Gate status

**G1 status:** **PASSED**.

| Exit criterion (from TASK_REGISTRY.md M0)                                            | Status | Notes |
|--------------------------------------------------------------------------------------|--------|-------|
| `uv run pytest` green                                                                | ✓      | 113 passed in 0.47 s |
| Unit test creates an `Order`, traverses the full FSM, asserts every emitted event has the expected payload | ✓      | `tests/unit/domain/test_order_fsm.py::test_full_lifecycle_emits_canonical_sequence` plus parametrised `test_each_legal_transition` covers all 14 INV-13 §3 rows |
| PaperBroker round-trip: submit a market order; receive a `Fill`; observe `Position` updates correctly | ✓      | `tests/unit/adapters/paper/test_paper_broker.py::test_round_trip_mkt_order_drives_fsm_and_position` — drives the FSM through SUBMITTED → ACCEPTED → FILLED, folds the Fill into a Position via `apply_fill`, asserts quantity / avg_cost / instrument / strategy_id |
| Import-linter passes against a deliberately violating commit (negative test)         | ✓      | `tests/contracts/test_import_linter.py::test_violation_is_caught` constructs a hermetic `proj.{domain,adapters}` package with a deliberate cross-layer import, runs `lint-imports` via the Python API, asserts non-zero exit and `BROKEN` in stdout. Companion `test_clean_package_passes` rules out false positives |

Auxiliary checks beyond the gate:

- `uv run mypy src/` — strict mode; no issues found in 16 source files.
- `uv run lint-imports` against the live tree — both contracts (`Domain layer is broker-neutral (ADR-004)` and `RiskEngine no-bypass (ADR-008) — placeholder`) KEPT across 24 files / 51 dependencies.
- `uv run black --check src/ tests/` and `uv run isort --check-only src/ tests/` — clean.

## Delivered vs plan

| Plan deliverable (TASK_REGISTRY M0)                                              | Status   | Notes |
|----------------------------------------------------------------------------------|----------|-------|
| 1. Repo scaffolding (`pyproject.toml`, `src/blive/`, `tests/`, build shortcuts)  | ✓ done   | Hatchling build backend; `src/`-layout package; `.gitignore`; minimal `README.md`; pytest / mypy / black / isort / import-linter all configured. Initialised the git repo (`main` branch) at session start — the discipline assumes a repo. |
| 2. Pinned dependencies (btest path-editable, `ib_async >=2.1,<2.2`)              | ✓ done   | `quantdsl-backtest` pinned via `[tool.uv.sources]` to `../btest` (path = editable). `ib_async==2.1.0` resolved by uv. |
| 3. **DD-1** domain objects (MISSING → STABLE)                                    | ✓ done   | 11 types: Instrument, Bar, Trade, Order, Fill, OrderEvent, Position, AccountSnapshot, OrderUpdate, ConnectionStatus, BrokerEvent. 7 enums (OrderSide / Type / TIF / State / EventKind, AssetClass, Severity). Field-level invariants enforced in `__post_init__`. |
| 4. **INV-13** order FSM transitions (MISSING → STABLE)                           | ✓ done   | Full 14-row transition table; trigger taxonomy; reason / fill payload discipline; cancel- and reject-reason taxonomies; idempotency rules. |
| 5. **INV-5** domain events (MISSING → DRAFT)                                     | ✓ done   | 17 event topics catalogued with payload, emission rule, consumers, milestone. M0 ships `order.*` + `broker.connection`; later events forward-planned. |
| 6. **INV-6** ports / adapters (MISSING → DRAFT)                                  | ✓ done   | All 6 ports (`BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `AlertPort`, `EventBusPort`) lifted from REQUIREMENTS §7.2 with concrete signatures; per-port adapter status tracker. |
| 7. PaperBroker adapter                                                           | ✓ done   | `blive.adapters.paper.broker.PaperBroker`. Honours the FSM via SUBMITTED → ACCEPTED → FILLED for MKT orders; LMT held in book until cancel; idempotent submit; configurable simulated latencies; `replace()` raises `NotImplementedError` (M1). |
| 8. InMemoryPersistence adapter                                                   | ✓ done   | `blive.adapters.memory.persistence.InMemoryPersistence`. Append-only event log + snapshot blob store; asyncio-locked. |
| 9. Test scaffolding                                                              | ✓ done   | 113 tests across `tests/unit/domain/{test_order_fsm,test_types,test_positions}.py`, `tests/unit/adapters/{paper.test_paper_broker,memory.{test_persistence,test_bus}}`. Plus shared fixtures in `tests/conftest.py`. |
| 10. Import-linter rule + negative test                                            | ✓ done   | Two contracts in `pyproject.toml` (`Domain layer is broker-neutral (ADR-004)` + a placeholder for ADR-008); hermetic negative test in `tests/contracts/test_import_linter.py` confirms a cross-layer violation is caught. |

Beyond the plan deliverables, M0 also produced:

- `blive.adapters.memory.bus.InMemoryEventBus` — opportunistic, since the EventBusPort exists and the in-memory shape is trivial; useful for M1 wiring.
- `blive.adapters.clock.{wall.WallClock, sim.SimClock}` — both clock adapters, since the FSM tests need `SimClock` and live mode will need `WallClock`.
- `blive.domain.positions.apply_fill` — pure position-arithmetic helper that handles the five fill cases (open, add, partial close, full close, flip). The PaperBroker round-trip test depends on this.

## Surprises

- **Import-linter needed `include_external_packages = true`** before it would honour a contract whose `forbidden_modules` include third-party packages (the `ib_async` rule). The error message was clear, but the silent default surprised the first run.
- **`.importlinter` standalone config is INI, not TOML.** Only the embedded-in-`pyproject.toml` form uses TOML. The first version of the negative test wrote TOML and got `Could not find package '['` because the parser read the literal string `["proj"]`.
- **import-linter has no `__main__`.** `python -m importlinter` errors with "is a package and cannot be directly executed". Solutions: invoke the `lint-imports` script (which depends on the venv's Scripts/ being on PATH) or call `importlinter.cli.lint_imports(config_filename=...)` from a `python -c` runner. The negative test uses the latter for portability.
- **`asyncio.create_task` rejects `Awaitable[None]` under mypy strict.** It wants a `Coroutine`. The EventBusPort handler type was therefore narrowed to `Coroutine[Any, Any, None]` (exposed as the `EventHandler` alias in `blive.domain.ports`); INV-6's signature was updated to match. This is a strictly-narrower contract that any async function naturally satisfies.
- **`SimClock.sleep()` does not yield to the event loop.** It advances the clock synchronously and returns — intentional for deterministic FSM tests. The consequence is that you cannot pause a PaperBroker lifecycle task between `SUBMITTED` and `ACCEPTED` purely by setting a non-zero `accept_latency_s` and waiting; the lifecycle just runs straight through. The `cancel()` test therefore uses an LMT order (which the M0 PaperBroker holds in the book without auto-filling) instead of trying to interject between MKT-lifecycle states.
- **`PaperBroker` deliberately does not track positions.** `positions()` returns `[]`; the engine (or, at M0, the test harness) derives positions from observed `Fill`s by folding through `blive.domain.positions.apply_fill`. This matches how the live IB adapter will work (the broker reports fills, the engine maintains the local view that reconciles against the broker's view) and keeps the PaperBroker focused on FSM correctness.
- **`asyncio_mode = "auto"`** in pytest-asyncio 0.24+ removes the need for `@pytest.mark.asyncio` markers. All async tests in the M0 suite rely on this and "just work".

## ADRs raised this milestone

None. All M0 work fit within ADR-001..026.

## OQs raised this milestone

None.

## Substrate transitions

| Artefact                                           | Before                  | After                  |
|----------------------------------------------------|-------------------------|------------------------|
| DD-1 (`docs/dd/domain_objects.md`)                 | MISSING                 | STABLE v0.1            |
| INV-13 (`docs/inv/order_state_transitions.md`)     | MISSING                 | STABLE v0.1            |
| INV-6 (`docs/inv/ports_adapters.md`)               | MISSING                 | DRAFT v0.1             |
| INV-5 (`docs/inv/domain_events.md`)                | MISSING                 | DRAFT v0.1             |
| `src/blive/` (Layer 5 Code)                        | MISSING                 | DRAFT v0.1             |
| `tests/` (Layer 6 Tests)                           | MISSING                 | DRAFT v0.1             |
| `CONTEXT_INVENTORY.md`                             | DRAFT v0.1              | DRAFT v0.2             |
| `TASK_REGISTRY.md`                                 | DRAFT v0.1.1            | DRAFT v0.1.2 (G1 PASSED logged) |
| `README.md`                                        | MISSING                 | minimal stub committed (full Vision paragraph still pending) |

The repository was also initialised as a git repo on `main` at session start (the discipline assumes one).

## Effort vs estimate

- **Estimated:** ~1 working session (TASK_REGISTRY M0).
- **Actual:** 1 session.
- **Variance reason:** none material.

The bulk of the time was substrate authoring (DD-1 STABLE took the longest, since it owns the type contract that everything else cites). Code + tests landed quickly because the substrate was already settled. Import-linter / mypy / format polish was ~10–15% of session time.

## Recommendations for NEXT_PROMPT M1

The substrate plus implementation pattern worked well; M1 should follow the same shape. Specific advance notes:

- **btest reuse — verify import paths early.** ADR-010 commits to importing `FactorEngine`, `SignalEngine`, `PortfolioEngine` from `quantdsl_backtest.engine` (or wherever btest exposes them). Before writing the strategy loader, smoke-import these to catch the renaming surprise (if any) cheaply. Pin a btest commit hash in `[tool.uv.sources]` if the head moves between sessions.
- **Choose the M1 pricing source explicitly.** The end-to-end pipeline needs deterministic CAC.PA bars. Options: (a) a fixture parquet checked into `tests_slow/fixtures/`; (b) a `PaperMarketData` adapter implementing `MarketDataPort` that reads from a fixture file. (b) is the right shape per INV-6 §2.2 and aligns with how M2 will swap in `EODHDMarketData` / `IBMarketData`. Recommend (b), even if the fixture file is small.
- **Sizer (M1 minimal) is single-instrument.** `tkan_v4_momentum_timing` 1× targets one instrument (CAC.PA). The sizer reduces to: given `target_weight ∈ [0, 1]`, `equity`, `price`, compute `signed_qty = round((equity * target_weight) / price)`. Whether to round to integer shares vs IB fractional-share precision is an early design decision — flag it as an OQ (or resolve via ADR if simple).
- **RiskEngine M1 subset reminder.** RC-08 (stale data), RC-09 (market hours), RC-13 (kill-switch) per TASK_REGISTRY M1. **Verify whether RC-12 (model artefact freshness) needs to land at M1**: if the M1 strategy actually uses the TKAN artefact, then yes; if the M1 paper-mode pipeline uses the strategy's spec without consulting `pred_cache.pkl`, RC-12 can wait for M2. Read `experiments/...yaml` (or whatever btest spec) to settle this in the warm-up.
- **Equity-curve parity within ±1 bps** is structurally tight (only share-rounding can drift it). Make the comparison reproducible: same fixture, same calendar, same starting cash. Save the btest reference run as a pinned artefact alongside the test fixture.
- **`replace()` lands at M1** alongside the Sizer (per the `NotImplementedError` comment). Don't leave it raising past M1.

Cross-cutting:

- **The `EventOffset` / `SubscriptionId` `NewType` aliases** show up at the boundary between domain and adapter. mypy strict accepts the round-trip; passing a plain `int` to `read_from()` requires a cast. M1 wiring should keep the discipline (use `EventOffset(0)` etc.) so we don't end up with type confusion at M4 when SQLite arrives.
- **The `BrokerEvent = OrderEvent | ConnectionStatus` union widens at M2.** When `AccountUpdate` lands, the existing `isinstance(event, ConnectionStatus)` / `isinstance(event, OrderEvent)` checks in M0 tests stay correct, but new consumers must learn the third member.
- **Observation about CONTEXT_PROTOCOL §11 (agentic execution layer).** This was the first milestone authored *after* §11 went into the protocol (it landed in v0.3 of the protocol earlier on 2026-04-26). M0 substrate execution was entirely manual — no L0 (warm-up agent), no L1 (drift watchdog), no L2 (in-situ ADR drafting), no L3 (auto retro). A future session could test how much of M1 / M2 substrate could shift to L0 / L1 without losing fidelity. The retrospective itself is a candidate for L3 once OQ-028 / OQ-029 are resolved.

## Recommendations for the discipline itself

- **Trivial substrate edits during a milestone-close session don't always need v-bumps.** I bumped CONTEXT_INVENTORY to v0.2 because the changes were substantive (multiple status promotions). For TASK_REGISTRY I went to v0.1.2 (matching the existing convention). A short note in CONTEXT_PROTOCOL §3.3 clarifying when a `.x` bump suffices vs when a major version bump is warranted would help the next session decide without thinking.
- **Add a "post-flight checks" sub-section to CONTEXT_PROTOCOL §3.3** capturing the conventional set we ran here: `pytest -q`, `mypy`, `lint-imports`, `black --check`, `isort --check-only`. Right now they're implicit; making them explicit removes ambiguity for future agents about what "the artefact compiled cleanly" means.
- **Consider a CI-time check that every artefact's `referenced_by` list is reciprocal** — if A says it depends_on B, B's referenced_by should list A. Currently maintained by hand; orphan reciprocity will rot first.

## Cross-References

- [TASK_REGISTRY.md](../../TASK_REGISTRY.md) — M0 plan and exit criteria; G1 row marked PASSED.
- [CONTEXT_PROTOCOL.md §8.3.1](../../CONTEXT_PROTOCOL.md) — milestone-close protocol that mandated this retro.
- [ADR-024](../decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) — retro artefact type definition.
- [ADR-025](../decisions/DECISIONS.md#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) — milestone-close + phase-boundary handoff rules.
- (no previous retro — M0 is the first milestone of Phase 1.)

## Changelog

- **v1.0 (2026-04-26)** — initial (and only) write at M0 close.
