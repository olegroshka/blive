---
id: INV-13
title: Order State Transitions
status: STABLE
owner: Claude
last_reviewed: 2026-04-26
version: 0.1
sources:
  - REQUIREMENTS.md §5.3 (Order FSM diagram)
  - REQUIREMENTS.md §7.3 (OrderEvent shape)
  - DD-1 §1.1 (OrderState, OrderEventKind enums)
depends_on:
  - DD-1
  - REQUIREMENTS
referenced_by:
  - INV-5 domain_events (OrderEvent variants)
  - INV-14 ib_error_codes (MISSING; reject reason mapping at M3)
  - src/blive/domain/order_fsm.py (implementation)
  - tests/unit/domain/test_order_fsm.py (golden transition tests)
---

# INV-13 — Order State Transitions

## Purpose

The single source of truth for the order finite-state machine (FSM). Every
allowed transition is listed in §3, with trigger, emitted event, side
effects, and reason discipline. Anything not listed is **illegal** and the
implementation in `src/blive/domain/order_fsm.py` must raise on the attempt.

This file is the contract that
[`tests/unit/domain/test_order_fsm.py`](../../tests/unit/domain/test_order_fsm.py)
exercises in full.

## Scope

**In:** the nine-state FSM for a single `Order` from creation to terminal
state; the seven event kinds emitted along the way; trigger taxonomy;
on-transition side effects.

**Out:** cancel-replace as a separate workflow (covered when M3 lands);
cross-order coordination (OCA / brackets — out of v1 scope, no parent_id
support shipped); reconciliation-driven state synthesis (M5).

## 1. States

The nine FSM states are the members of `OrderState` ([DD-1 §1.1](../dd/domain_objects.md#11-enums)). Categorised:

| Category | State | Meaning |
|----------|-------|---------|
| **initial** | `INITIALIZED` | the `Order` dataclass exists; the engine has not yet called `BrokerPort.submit()` |
| **wire** | `SUBMIT_PENDING` | `BrokerPort.submit()` is in flight; no acknowledgement yet |
| **at venue** | `SUBMITTED` | the broker has acknowledged receipt; venue id known but order may not yet be marketable |
| **at venue** | `ACCEPTED` | the venue has the order live and it is eligible to trade (IB-speak: `Submitted` order status) |
| **at venue** | `PARTIALLY_FILLED` | one or more `Fill`s received; cumulative quantity < ordered quantity |
| **terminal** | `FILLED` | cumulative quantity = ordered quantity |
| **terminal** | `CANCELED` | venue confirmed cancellation |
| **terminal** | `REJECTED` | broker or venue refused the order |
| **terminal** | `EXPIRED` | TIF window elapsed before fill |

Terminal states have no outgoing transitions. Re-receiving any trigger in a
terminal state is a no-op for idempotent triggers (`partial_fill` /
`fill` with a previously-seen `venue_exec_id`) and an `IllegalTransition`
otherwise.

## 2. Triggers

| Trigger | Source | Carries |
|---------|--------|---------|
| `submit_call` | engine — engine has invoked `BrokerPort.submit(order)` | none |
| `wire_ack` | adapter — `BrokerPort.submit` returned with a `venue_order_id` | `venue_order_id` |
| `wire_reject` | adapter — `BrokerPort.submit` raised before the venue accepted | reason |
| `accept` | adapter — venue says order is live and tradable | none |
| `reject` | adapter — venue rejected an already-acknowledged order | reason |
| `partial_fill` | adapter — venue executed part of the order | `Fill` (with `venue_exec_id`) |
| `fill` | adapter — venue executed the remaining (or whole) quantity | `Fill` |
| `cancel` | adapter — venue confirmed cancellation (initiated by engine OR by an external actor — see §5) | reason (e.g. `"engine"`, `"tws_ui"`, `"venue_purge"`) |
| `expire` | adapter — TIF window elapsed | none |

Triggers are **observed**, not chosen by the FSM. The engine does not
"decide" to enter `CANCELED`; it observes that the venue confirmed the
cancel. The pure-function FSM signature is therefore:

```python
def transition(
    state: OrderState,
    trigger: Trigger,
    *,
    venue_order_id: str | None = None,
    fill: Fill | None = None,
    reason: str | None = None,
) -> tuple[OrderState, OrderEvent | None]:
    ...
```

The function returns the new state and, when applicable, the `OrderEvent`
that should be appended to the persistence log. `submit_call` is the only
trigger that emits no event (purely internal step-from-`INITIALIZED`).

## 3. Transition table

Twelve transitions are allowed. Anything else raises `IllegalTransition`.

| # | From | Trigger | To | Event emitted | Reason discipline |
|---|------|---------|----|----|-------------------|
| T1 | `INITIALIZED` | `submit_call` | `SUBMIT_PENDING` | (none) | n/a |
| T2 | `SUBMIT_PENDING` | `wire_ack` | `SUBMITTED` | `OrderEvent(kind=SUBMITTED, venue_order_id=…)` | reason None |
| T3 | `SUBMIT_PENDING` | `wire_reject` | `REJECTED` | `OrderEvent(kind=REJECTED, reason=…)` | reason **required** (broker error message) |
| T4 | `SUBMITTED` | `accept` | `ACCEPTED` | `OrderEvent(kind=ACCEPTED)` | reason None |
| T5 | `SUBMITTED` | `reject` | `REJECTED` | `OrderEvent(kind=REJECTED, reason=…)` | reason **required** (venue error code) |
| T6 | `SUBMITTED` | `cancel` | `CANCELED` | `OrderEvent(kind=CANCELED, reason=…)` | reason **required** (`"engine"` if our request, source-attribution otherwise) |
| T7 | `ACCEPTED` | `partial_fill` | `PARTIALLY_FILLED` | `OrderEvent(kind=PARTIAL_FILL, fill=…)` | `fill` **required** |
| T8 | `ACCEPTED` | `fill` | `FILLED` | `OrderEvent(kind=FILLED, fill=…)` | `fill` **required** |
| T9 | `ACCEPTED` | `cancel` | `CANCELED` | `OrderEvent(kind=CANCELED, reason=…)` | reason **required** |
| T10 | `ACCEPTED` | `expire` | `EXPIRED` | `OrderEvent(kind=EXPIRED)` | reason None |
| T11 | `PARTIALLY_FILLED` | `partial_fill` | `PARTIALLY_FILLED` | `OrderEvent(kind=PARTIAL_FILL, fill=…)` | `fill` **required** (must be a *new* `venue_exec_id`) |
| T12 | `PARTIALLY_FILLED` | `fill` | `FILLED` | `OrderEvent(kind=FILLED, fill=…)` | `fill` **required**; cumulative quantity = order quantity |
| T13 | `PARTIALLY_FILLED` | `cancel` | `CANCELED` | `OrderEvent(kind=CANCELED, reason=…)` | reason **required** |
| T14 | `PARTIALLY_FILLED` | `expire` | `EXPIRED` | `OrderEvent(kind=EXPIRED)` | reason None |

**Note on numbering.** The table has 14 rows because `partial_fill` /
`cancel` / `expire` legitimately fire from two source states. The set of
*distinct* edges in the state diagram is 12 (T11 is a self-loop and counts
once). Tests should cover each numbered row.

## 4. Side effects (per transition)

Beyond the emitted event, each transition has well-defined side effects.
The FSM transition function itself is **pure** — these effects happen at
the consumer's call site (the engine) after observing the event.

| Transition | Side effect |
|------------|-------------|
| T2 (`SUBMITTED`) | engine records `venue_order_id` against `client_order_id` for future correlation |
| T3, T5 (`REJECTED`) | engine emits `AlertPort.send(severity=HIGH, …)`; rate-limited (≥ 5 in 60 s arms kill-switch per [INV-4 RC-13](risk_checks.md)) |
| T7, T8, T11, T12 (fills) | engine updates `Position` (DD-1 §2.7) and `AccountSnapshot.cash_by_ccy` from the `Fill` |
| T6, T9, T13 (`CANCELED`) | when reason ≠ `"engine"`, emit `AlertPort.send(severity=MEDIUM, …)` — an external actor cancelled our order |
| T10, T14 (`EXPIRED`) | informational; emit `AlertPort.send(severity=LOW, …)` |
| every transition | emit `OrderEvent` on `EventBusPort`; persist via `PersistencePort.append(event)` **before** publishing on the bus (durability ordering, [ADR-007](../decisions/DECISIONS.md#adr-007--in-process-event-bus-for-v1) consequence) |

## 5. Reason taxonomy for cancel and reject

Reason strings are not free-form. The following discriminators are
expected; unknown values are accepted but logged as `unrecognised`.

**For `cancel`:**

| Value | Meaning |
|-------|---------|
| `"engine"` | the engine called `BrokerPort.cancel()` itself |
| `"tws_ui"` | manual cancel observed from TWS desktop UI (multi-client visibility) |
| `"kill_switch"` | the engine cancelled this order as part of kill-switch armament ([INV-4 RC-13](risk_checks.md)) |
| `"venue_purge"` | venue cancelled all open orders (e.g. mass cancel on disconnect) |
| `"reconciliation"` | reconciliation observed the venue had no record of this order |

**For `reject`** (one of the IB error code categories per
[INV-14](ib_error_codes.md), MISSING — full mapping lands at M3):

| Value | Meaning |
|-------|---------|
| `"insufficient_buying_power"` | margin / cash below requirement |
| `"invalid_contract"` | unknown / unsubscribed instrument |
| `"price_outside_band"` | venue price-band check |
| `"throttle"` | IB pacing violation |
| `"market_closed"` | order outside RTH and not RTH-only-bypass |
| `"halted"` | symbol halted |
| `"<other>"` | preserve venue's text |

Reason strings drive analytics; do not let them rot. New canonical values
are added by the M3 IB-adapter author and back-populated to INV-14.

## 6. Idempotency

- **Repeating a fill event** (same `venue_exec_id`): deduplicated by the
  engine; FSM treats as no-op (does not raise). Required because IB can
  re-deliver `execDetails` after a reconnect.
- **Repeating a `wire_ack`** for the same `client_order_id`: the engine
  drops it (the order is already past `SUBMITTED`); FSM raises
  `IllegalTransition` for any state ≠ `SUBMIT_PENDING`. The engine, not the
  FSM, owns the dedup.
- **Repeating a terminal trigger** (`reject` while already `REJECTED`,
  `cancel` while already `CANCELED`): drop with a warning log; do not raise.

## 7. Cross-References

- [DD-1 §1.1, §2.4, §2.5, §2.6](../dd/domain_objects.md) — `OrderState`, `OrderEventKind`, `Order`, `Fill`, `OrderEvent`.
- [REQUIREMENTS §5.3](../../REQUIREMENTS.md) — narrative origin.
- [INV-4 RC-13](risk_checks.md) — kill-switch interaction.
- [INV-5 domain_events](domain_events.md) — non-order event types.
- [INV-14 ib_error_codes](ib_error_codes.md) — MISSING; reject-reason mapping at M3.
- [ADR-007](../decisions/DECISIONS.md#adr-007--in-process-event-bus-for-v1) — durability ordering rule (persist before publish).

## Open Questions

None blocking M0. M3-time questions deferred to INV-14 once we observe
real IB rejects.

## Changelog

- **v0.1 (2026-04-26)** — initial STABLE write at M0.
