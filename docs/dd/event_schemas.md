---
id: DD-2
title: Event Schemas
status: DRAFT
owner: Claude
last_reviewed: 2026-04-27
version: 0.1
sources:
  - INV-5 (event catalogue)
  - DD-1 §2.6, §2.8, §2.10 (OrderEvent, AccountSnapshot, ConnectionStatus)
  - ADR-022 (TKAN freshness window)
  - ADR-033 (AccountUpdate cadence)
depends_on:
  - DD-1
  - INV-5
  - INV-13
  - ADR-033
  - ADR-022
referenced_by:
  - src/blive/domain/events.py  # implementation; widens M-by-M
  - INV-5 §2 (DomainEvent union)
---

# DD-2 — Event Schemas

## Purpose

Field-level data dictionary for every domain event that crosses the [`EventBusPort`](../inv/ports_adapters.md#16-eventbusport) or hits [`PersistencePort`](../inv/ports_adapters.md#14-persistenceport). The event-by-event catalogue lives in [INV-5](../inv/domain_events.md); this artefact owns the **payload contract** (per-field semantics, types, invariants, samples).

DD-2 widens milestone-by-milestone alongside [INV-5](../inv/domain_events.md) and `blive.domain.events`. M0 events (`OrderEvent`, `ConnectionStatus`) shipped at M0; M1 added `RiskBreach`; M2 adds `AccountUpdate` + `ArtefactFreshnessWarning`. M4/M5/M7 events have INV-5 rows but no DD-2 entries until they implement.

## Scope

**In:** every event type in [INV-5 §1](../inv/domain_events.md#1-event-catalogue) that is currently implemented (M0 → current milestone).

**Out:**

- The btest `DataSource` event payloads (those are btest-side artefacts).
- IB-adapter wire events that are translated into domain events at the adapter boundary (the wire shape lives in `ib_async`'s docs).
- REST request payloads (DD-5, MISSING — M6).
- SQLite DDL for persisted rows (DD-4, MISSING — M4).

## Conventions

- Every event is `@dataclass(frozen=True, slots=True)` per [DD-1 §0 conventions](./domain_objects.md).
- Every event carries `time_utc: datetime` (UTC, `tzinfo == timezone.utc`); the field's invariant raises if not.
- Topic strings use the `<domain>.<verb>` shape ([INV-5 §"Conventions"](../inv/domain_events.md)).
- Decimal fields, ISO-4217 currency codes, and ISO-8601 timestamps follow [DD-1](./domain_objects.md) conventions verbatim.

## 1. `OrderEvent` (M0)

INV-5 rows: `order.submitted`, `order.accepted`, `order.partial_fill`, `order.filled`, `order.canceled`, `order.rejected`, `order.expired`.

Defined in [DD-1 §2.6](./domain_objects.md#26-orderevent); the per-`kind` reason / fill discipline is in [INV-13 §3](../inv/order_state_transitions.md#3-transition-table). Implementation: `blive.domain.events.OrderEvent`.

DD-2 does not duplicate — see DD-1 §2.6 for the full field table.

## 2. `ConnectionStatus` (M0)

INV-5 row: `broker.connection`. Defined in [DD-1 §2.10](./domain_objects.md#210-connectionstatus). Implementation: `blive.domain.events.ConnectionStatus`.

## 3. `RiskBreach` (M1)

INV-5 row: `risk.breach`. Implementation: `blive.domain.events.RiskBreach`.

| Field | Type | Semantics | Invariant |
|---|---|---|---|
| `strategy_id` | `str` | strategy whose order tripped the check | non-empty |
| `check` | `RiskCheckCode` (enum) | which RC fired (M1 subset: `RC_08`, `RC_09`, `RC_12`, `RC_13`; widens at M4) | one of the enum members |
| `severity` | `RiskBreachSeverity` (enum) | `BLOCK`, `SCALE`, or `WARN` per [INV-4 "On-breach actions"](../inv/risk_checks.md) | one of the enum members |
| `detail` | `str` | human-readable explanation (`"bar for CAC.PA is stale: 7200s old > threshold 86400s"`) | non-empty |
| `time_utc` | `datetime` | when the check fired | `tzinfo == timezone.utc` |

**Method:** `RiskBreach.alert_severity() -> Severity` — maps the breach severity onto the [DD-1 §1.1 `Severity` enum](./domain_objects.md#11-enums) for `AlertPort.send`. `BLOCK → HIGH`, `SCALE → MEDIUM`, `WARN → LOW` (per [INV-13 §4](../inv/order_state_transitions.md#4-side-effects-per-transition)).

**Sample:**

```python
RiskBreach(
    strategy_id="tkan_v4_momentum_timing_1x",
    check=RiskCheckCode.RC_12,
    severity=RiskBreachSeverity.BLOCK,
    detail="model artefact 'tkan_max' is 35.2d old; hard threshold 30d (ADR-022)",
    time_utc=datetime(2026, 5, 30, 13, 30, tzinfo=timezone.utc),
)
```

## 4. `AccountUpdate` (M2)

INV-5 row: `account.update`. Cadence + diff-suppress thresholds per [ADR-033](../decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence). Implementation: `blive.domain.events.AccountUpdate` (M2 deliverable).

| Field | Type | Semantics | Invariant |
|---|---|---|---|
| `snapshot` | [`AccountSnapshot`](./domain_objects.md#28-accountsnapshot) | full account view at the moment of emission | invariants inherited from DD-1 §2.8 |
| `time_utc` | `datetime` | when blive subsampled (not when IB pushed) | UTC; equals `snapshot.taken_at` |

**Cadence rule** ([ADR-033](../decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence)): emitted at most once per 30 s wall-clock interval, *and* only when at least one `AccountSnapshot` field changed by more than its per-field threshold compared to the last emission. Default thresholds:

| Field | Threshold |
|---|---|
| `equity`, `cash_by_ccy[ccy]`, `buying_power`, `gross_exposure`, `net_exposure`, `margin_used` | ≥ 0.01 currency unit |
| `leverage` | ≥ 0.001 (3 d.p.) |

Below threshold, no event; the next 30-s tick re-evaluates against the latest emission.

**Sample:**

```python
AccountUpdate(
    snapshot=AccountSnapshot(
        equity=Decimal("125_432.18"),
        cash_by_ccy={"EUR": Decimal("60_000.00"), "USD": Decimal("0")},
        buying_power=Decimal("125_432.18"),
        gross_exposure=Decimal("65_432.18"),
        net_exposure=Decimal("65_432.18"),
        leverage=Decimal("0.521"),
        margin_used=Decimal("0"),
        base_currency="EUR",
        taken_at=datetime(2026, 5, 1, 13, 30, tzinfo=timezone.utc),
    ),
    time_utc=datetime(2026, 5, 1, 13, 30, tzinfo=timezone.utc),
)
```

## 5. `ArtefactFreshnessWarning` (M2)

INV-5 row: `artefact.freshness_warning`. Triggered by [INV-4 RC-12](../inv/risk_checks.md) at the **warn** threshold (21 d) per [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning); the **block** threshold (30 d) emits a `RiskBreach(RC_12, BLOCK)` instead. Implementation: `blive.domain.events.ArtefactFreshnessWarning` (M2 deliverable; the M1 `RiskEngine` already produces the equivalent `RiskBreach(RC_12, WARN)` — ADR-022's separate event type lands at M2 alongside `AccountUpdate`).

| Field | Type | Semantics | Invariant |
|---|---|---|---|
| `strategy_id` | `str` | strategy whose artefact triggered the warning | non-empty |
| `model_name` | `str` | factor name (e.g. `"tkan_max"`) | non-empty |
| `path` | `str` | absolute path to the artefact file (`~`-expanded) | non-empty |
| `age_days` | `Decimal` | days since artefact mtime | `> 0` |
| `warning_threshold_days` | `int` | the threshold that triggered emission (default 21 per ADR-022) | `≥ 1` |
| `hard_threshold_days` | `int` | the corresponding RC-12 hard threshold (default 30 per ADR-022) | `> warning_threshold_days` |
| `time_utc` | `datetime` | when the check ran | UTC |

**Sample:**

```python
ArtefactFreshnessWarning(
    strategy_id="tkan_v4_momentum_timing_1x",
    model_name="tkan_max",
    path="/home/oleg/.blive/artefacts/tkan_v4_momentum_timing/tkan_v4/pred_cache.pkl",
    age_days=Decimal("23.4"),
    warning_threshold_days=21,
    hard_threshold_days=30,
    time_utc=datetime(2026, 5, 20, 13, 30, tzinfo=timezone.utc),
)
```

**Why a separate event type, not just `RiskBreach(WARN)`?** [INV-5](../inv/domain_events.md) catalogues both rows; the `ArtefactFreshnessWarning` carries structured `age_days` / threshold context, which the UI dashboard renders as a count-down badge. `RiskBreach`'s `detail` is a human-readable string and would force the UI to parse it. Both events fire on the same condition; consumers subscribe to whichever shape they need.

## 6. The `DomainEvent` union (current state)

Tracked in [INV-5 §2](../inv/domain_events.md#2-the-domainevent-union). Current implementation in `blive.domain.events`:

```python
DomainEvent: TypeAlias = OrderEvent | ConnectionStatus | RiskBreach
```

When M2 lands `AccountUpdate` and `ArtefactFreshnessWarning`, the union widens to:

```python
DomainEvent: TypeAlias = (
    OrderEvent
    | ConnectionStatus
    | RiskBreach
    | AccountUpdate
    | ArtefactFreshnessWarning
)
```

INV-5 §2 enumerates the eventual full union (M4/M5/M7 events catalogued, not yet implemented).

## 7. Cross-References

- [INV-5](../inv/domain_events.md) — event catalogue (topic, payload type, emission rule, consumers).
- [DD-1 §2.6, §2.8, §2.10](./domain_objects.md) — payload-bearing types this DD references.
- [INV-13 §3](../inv/order_state_transitions.md#3-transition-table) — `OrderEvent` per-kind discipline.
- [INV-4](../inv/risk_checks.md) — `RiskBreach.check` enumeration; M1 subset, widens at M4.
- [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning) — TKAN freshness thresholds.
- [ADR-033](../decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence) — `AccountUpdate` cadence + diff-suppress.

## Open Questions

None blocking M2. Future:

- DD-2 grows when M4/M5/M7 events implement (`KillSwitchArmed`/`Cleared`, `*DriftDetected`, `ParityBreach`/`Failed`).
- `ArtefactFreshnessWarning` may pick up an `acknowledged_at: datetime | None` field at M4 if the UI gets an "ack" action; flagged for that milestone.

## Changelog

- **v0.1 (2026-04-27)** — initial DRAFT at M2 entry. Covers M0 events (`OrderEvent`, `ConnectionStatus`), M1 (`RiskBreach`), and the M2 additions (`AccountUpdate` per ADR-033, `ArtefactFreshnessWarning` per ADR-022). Later events catalogued in [INV-5](../inv/domain_events.md) but pending implementation.
