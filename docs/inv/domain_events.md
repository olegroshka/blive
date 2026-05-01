---
id: INV-5
title: Domain Events
status: STABLE
owner: Claude
last_reviewed: 2026-05-01
version: 0.3.1
sources:
  - REQUIREMENTS.md §5.3 (order events)
  - REQUIREMENTS.md §5.5 (risk events, kill-switch)
  - REQUIREMENTS.md §5.7 (reconciliation events)
  - REQUIREMENTS.md §8 (parity events)
  - REQUIREMENTS.md §11 (persistence)
  - DD-1 §2.6, §2.10 (OrderEvent, ConnectionStatus)
depends_on:
  - DD-1
  - INV-13
  - INV-4
  - REQUIREMENTS
referenced_by:
  - INV-6 ports_adapters (DomainEvent union for PersistencePort, EventBusPort)
  - src/blive/domain/events.py (implementation)
---

# INV-5 — Domain Events

## Purpose

Catalogue every event type that crosses the `EventBusPort` or hits the
`PersistencePort`. Each row lists payload, emission rule, expected
consumer set, and milestone in which the type lands.

The catalogue is the contract that `DomainEvent` (the union type used by
[INV-6 §1.4](ports_adapters.md#14-persistenceport)) refers to.

## Scope

**In:** every domain-level event with persistence or pub/sub
implications.

**Out:** internal log records (covered by application logging, not the
event bus); REST request payloads (DD-5, MISSING — M6); IB-adapter wire
events that are translated into domain events at the adapter boundary.

## Conventions

- Every event is `@dataclass(frozen=True, slots=True)` per
  [DD-1 §0 conventions](../dd/domain_objects.md).
- Every event carries `time_utc: datetime` (UTC) and a topic name string
  (used for `EventBusPort` routing and for log-table partitioning).
- Topics use a `<domain>.<verb>` shape: `order.submitted`,
  `risk.breach`, `parity.breach`, etc.

## 1. Event catalogue

| Topic | Type | Payload (load-bearing fields) | Emitted when | Consumers | Milestone |
|-------|------|-------------------------------|-------------|-----------|-----------|
| `order.submitted` | `OrderEvent(kind=SUBMITTED)` | `client_order_id`, `venue_order_id` | T2 ([INV-13 §3](order_state_transitions.md)) | persistence, UI, parity diagnostic | **M0** |
| `order.accepted` | `OrderEvent(kind=ACCEPTED)` | `client_order_id`, `venue_order_id` | T4 | persistence, UI | **M0** |
| `order.partial_fill` | `OrderEvent(kind=PARTIAL_FILL, fill=...)` | `client_order_id`, `Fill` | T7, T11 | persistence, UI, position-update consumer | **M0** |
| `order.filled` | `OrderEvent(kind=FILLED, fill=...)` | `client_order_id`, `Fill` | T8, T12 | persistence, UI, position-update consumer | **M0** |
| `order.canceled` | `OrderEvent(kind=CANCELED, reason=...)` | `client_order_id`, `reason` | T6, T9, T13 | persistence, UI, alerts (when reason ≠ `"engine"`) | **M0** |
| `order.rejected` | `OrderEvent(kind=REJECTED, reason=...)` | `client_order_id`, `reason` | T3, T5 | persistence, UI, **alerts (HIGH)** | **M0** |
| `order.expired` | `OrderEvent(kind=EXPIRED)` | `client_order_id` | T10, T14 | persistence, UI, alerts (LOW) | **M0** |
| `broker.connection` | `ConnectionStatus` | `connected`, `detail` | adapter on broker connect/disconnect | reconciliation watcher, kill-switch trigger (per [REQUIREMENTS §5.5](../../REQUIREMENTS.md) — disconnect > 30 s arms) | **M0** (PaperBroker emits one on construct) |
| `risk.breach` | `RiskBreach` | `strategy_id`, `check_name`, `severity ∈ {block, scale, warn}`, `details: dict` | `RiskEngine` rejects / scales an order ([INV-4](risk_checks.md)) | persistence, UI, alerts (HIGH for `block`, MEDIUM for `scale`) | **M1** (M1 RC subset; M4 full set) |
| `parity.breach` | `ParityBreach` | `strategy_id`, `realised_pnl_bps`, `simulated_pnl_bps`, `residual_bps`, `window_days` | daily diagnostic ([ADR-012](../decisions/DECISIONS.md#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)) crosses the envelope | persistence, alerts (HIGH) | **M7** |
| `parity.diagnostic_failed` | `ParityDiagnosticFailed` | `reason` | the diagnostic itself raised (e.g. btest import fail) | persistence, alerts (CRITICAL) | **M7** |
| `system.kill_switch_armed` | `KillSwitchArmed` | `source ∈ {manual, auto.*}`, `reason` | manual UI / REST call OR auto-trigger ([REQUIREMENTS §5.5](../../REQUIREMENTS.md)) | persistence, all engines (each refuses new orders), alerts (CRITICAL) | **M4** |
| `system.kill_switch_cleared` | `KillSwitchCleared` | `actor`, `confirmation_token_hash` | human resume call | persistence, alerts (HIGH) | **M4** |
| `account.update` | `AccountUpdate` | `AccountSnapshot` | broker periodic push or 30 s sample | persistence (subsampled), UI | **M2** |
| `recon.order_drift` | `OrderDriftDetected` | `client_order_id`, `local_state`, `venue_state` | reconciliation tick observes mismatch | persistence, alerts (MEDIUM) | **M5** |
| `recon.position_drift` | `PositionDriftDetected` | `instrument`, `local_qty`, `venue_qty` | reconciliation tick observes mismatch | persistence, alerts (MEDIUM) | **M5** |
| `recon.account_drift` | `AccountDriftDetected` | `field`, `local`, `venue` | reconciliation tick observes mismatch | persistence, alerts (MEDIUM) | **M5** |
| `artefact.freshness_warning` | `ArtefactFreshnessWarning` | `strategy_id`, `model_name`, `age_days` | RC-12 warn threshold crossed (21 d per [ADR-022](../decisions/DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning)) | persistence, alerts (MEDIUM) | **M2** |

## 2. The `DomainEvent` union

The aggregate type used by [INV-6 §1.4](ports_adapters.md#14-persistenceport)'s `PersistencePort.append` and `EventBusPort.publish`. Eventual full union:

```python
DomainEvent = (
    OrderEvent
    | ConnectionStatus
    | RiskBreach            # M1
    | AccountUpdate         # M2
    | ArtefactFreshnessWarning  # M2
    | ParityBreach          # M7
    | ParityDiagnosticFailed  # M7
    | KillSwitchArmed       # M4
    | KillSwitchCleared     # M4
    | OrderDriftDetected    # M5
    | PositionDriftDetected # M5
    | AccountDriftDetected  # M5
)
```

Current implementation in `blive.domain.events` (post M2-IB.3b-i):

```python
DomainEvent = (
    OrderEvent
    | ConnectionStatus
    | RiskBreach
    | AccountUpdate
    | ArtefactFreshnessWarning
)
```

The union widens milestone-by-milestone; each addition bumps this inventory.

## 3. Persistence ordering rule

Per [ADR-007](../decisions/DECISIONS.md#adr-007--in-process-event-bus-for-v1)
consequence (durability): the engine must call
`PersistencePort.append(event)` **before** `EventBusPort.publish(...)`.
Crash between persist and publish loses the publish (recoverable on
replay); reverse order would lose the persistence (unrecoverable).

## 4. Idempotency

Events are append-only. The persistence layer does not deduplicate on
replay — adapter-level dedup ([INV-13 §6](order_state_transitions.md#6-idempotency))
prevents duplicate fills from reaching the FSM in the first place.

## 5. Cross-References

- [INV-13 §3](order_state_transitions.md#3-transition-table) — which transition emits which `OrderEvent` kind.
- [INV-4](risk_checks.md) — which check raises which `RiskBreach`.
- [INV-6 §1.4, §1.6](ports_adapters.md) — `DomainEvent` consumer.
- [DD-1 §2.6, §2.10](../dd/domain_objects.md) — `OrderEvent`, `ConnectionStatus`.
- [REQUIREMENTS §5.3, §5.5, §5.7, §8, §11](../../REQUIREMENTS.md) — narrative origin.

## Open Questions

None blocking M0. M5/M7 event payloads will be refined when those
milestones land.

## Changelog

- **v0.1 (2026-04-26)** — initial DRAFT at M0. M0 events (order events, connection) live; later events catalogued for forward-planning.
- **v0.2 (2026-04-27)** — promoted to STABLE at M1 close. `RiskBreach` (M1) implemented in `blive.domain.events` (relocated from `blive.risk.checks` to honour the layer hierarchy); `DomainEvent = OrderEvent | ConnectionStatus | RiskBreach`. Other catalogued events (M2+) remain forward-planned, not yet code.
- **v0.3 (2026-05-01)** — M2-IB.3b-i implementation pass. M2 event types now live: `AccountUpdate` (per ADR-033 — wraps `AccountSnapshot` with topic-friendly identity; emission cadence + diff-suppress timer is the M2-IB.3b-i follow-up) and `ArtefactFreshnessWarning` (per ADR-022 — RC-12 warn-threshold at 21d; the structured `age_days` / threshold payload). Both implemented in `blive.domain.events`; `DomainEvent = OrderEvent | ConnectionStatus | RiskBreach | AccountUpdate | ArtefactFreshnessWarning`. `IBBroker.connect/disconnect` emits `ConnectionStatus` records (the M0-catalogued `broker.connection` row is now exercised by IB in addition to PaperBroker). M4/M5/M7 event types (`KillSwitchArmed/Cleared`, `*DriftDetected`, `ParityBreach/Failed`) remain forward-planned. Status stays STABLE — additive widening, no contract change.
- **v0.3.1 (2026-05-01)** — M2-IB.3b-i-timer follow-up. `IBBroker` now ships the 30s diff-suppress `AccountUpdate` emission timer per ADR-033 §"Decision" item 2. Per-field thresholds: currency-unit 0.01 (equity / cash_by_ccy / buying_power / gross_exposure / net_exposure / margin_used); leverage 0.001 (3 d.p.). Background task started in `IBBroker.connect`, cancelled in `IBBroker.disconnect`. First tick after connect emits the baseline (no prior snapshot to diff against); subsequent ticks emit only on above-threshold change. The `account.update` row's "consumer set" stays unchanged (persistence subsampled, UI). `BrokerEvent` union widened to `OrderEvent | ConnectionStatus | AccountUpdate` (IBBroker's events queue now emits these too). Status stays STABLE — implementation-completeness only, no inventory contract change.
