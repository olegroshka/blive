---
id: INV-6
title: Ports & Adapters
status: STABLE
owner: Claude
last_reviewed: 2026-04-27
version: 0.2
sources:
  - REQUIREMENTS.md §7.2 (Port signatures)
  - DD-1 §1, §2 (types referenced in signatures)
depends_on:
  - DD-1
  - REQUIREMENTS
  - INV-13
referenced_by:
  - src/blive/domain/ports.py (Protocol implementations)
  - src/blive/adapters/* (concrete adapters)
  - INV-5 domain_events (event types crossing the bus)
---

# INV-6 — Ports & Adapters

## Purpose

Lists every domain `Port` (the interface the domain depends on) and every
known adapter (the concrete implementation an adapter package provides).
Status per adapter tracks where in the milestone ladder it lands.

The `Port` Protocols themselves are the contract; signatures live here in
canonical form. The `src/blive/domain/ports.py` file is the implementation
of these Protocols and stays in sync with this inventory (see
[CONTEXT_PROTOCOL §7.2](../../CONTEXT_PROTOCOL.md) — checked at CI from M5).

## Scope

**In:** the six v1 ports listed in §1; the adapters per port with status
tracker.

**Out:** richer ports that may emerge later (e.g. `MetricsPort` if we move
Prometheus integration behind an adapter); REST-edge ports for the web UI
(M6).

## 1. Port catalogue

### 1.1 `BrokerPort`

The single point of contact between the domain and the broker. **All
order-write paths and account-read paths go through this port.**

```python
class BrokerPort(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def submit(self, order: Order) -> ClientOrderId: ...
    async def cancel(self, client_order_id: ClientOrderId) -> None: ...
    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None: ...
    async def open_orders(self) -> list[Order]: ...
    async def positions(self) -> list[Position]: ...
    async def account_snapshot(self) -> AccountSnapshot: ...
    def events(self) -> AsyncIterator[BrokerEvent]: ...
```

Where `ClientOrderId = uuid.UUID`. Types referenced are
[DD-1 §2](../dd/domain_objects.md).

### 1.2 `MarketDataPort`

```python
class MarketDataPort(Protocol):
    async def subscribe_bars(self, instrument: Instrument, freq: BarFreq) -> AsyncIterator[Bar]: ...
    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]: ...
    async def unsubscribe(self, instrument: Instrument) -> None: ...
    async def historical_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
        start: datetime,
        end: datetime,
    ) -> list[Bar]: ...
```

`BarFreq` is a `Literal["1m", "5m", "15m", "1h", "1d"]`. Live-routing
across providers (EODHD vs IB streaming) per [ADR-017](../decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing).

### 1.3 `ClockPort`

```python
class ClockPort(Protocol):
    def now(self) -> datetime: ...
    async def sleep(self, seconds: float) -> None: ...
```

`now()` returns timezone-aware UTC. Domain code must never call
`datetime.now()` directly — enforced as an import-linter rule from M5
([CONTEXT_PROTOCOL §7.3](../../CONTEXT_PROTOCOL.md)).

### 1.4 `PersistencePort`

```python
class PersistencePort(Protocol):
    async def append(self, event: DomainEvent) -> EventOffset: ...
    async def read_from(self, offset: EventOffset) -> AsyncIterator[DomainEvent]: ...
    async def snapshot(self, key: str, blob: bytes) -> None: ...
    async def load_snapshot(self, key: str) -> bytes | None: ...
```

`DomainEvent` is the union of all event types per
[INV-5](domain_events.md) (DRAFT). `EventOffset` is an opaque `int`-like
monotonic-ascending key (the implementation chooses the encoding —
SQLite's `rowid` at M4 per [ADR-006](../decisions/DECISIONS.md#adr-006--sqlite-for-persistence-in-v1)).

### 1.5 `AlertPort`

```python
class AlertPort(Protocol):
    async def send(self, severity: Severity, subject: str, body: str) -> None: ...
```

`Severity` is an enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. Channel
routing (Slack / email / SMS) is the adapter's concern.

### 1.6 `EventBusPort`

```python
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]

class EventBusPort(Protocol):
    def publish(self, topic: str, event: DomainEvent) -> None: ...
    def subscribe(self, topic: str, handler: EventHandler) -> SubscriptionId: ...
```

`SubscriptionId` is an opaque token returned by `subscribe()` and accepted
by a future `unsubscribe()`. In-process asyncio-queue implementation at
v1 per [ADR-007](../decisions/DECISIONS.md#adr-007--in-process-event-bus-for-v1); Redis Streams as opt-in adapter post-M8. Handler type narrows to
`Coroutine` (rather than `Awaitable`) because the in-process bus uses
`asyncio.create_task`, which only accepts coroutines.

## 2. Adapter status tracker

Per port, the adapters that exist or are planned, with the milestone they
land in.

### 2.1 `BrokerPort` adapters

| Adapter | Module | Status | Milestone | Notes |
|---------|--------|--------|-----------|-------|
| `PaperBroker` | `blive.adapters.paper.broker` | M0 in flight | M0 | in-process matcher; deterministic fills; no IB wire |
| `IBBroker` (read) | `blive.adapters.ib.broker` | MISSING | M2 | `connect`, `disconnect`, `positions`, `open_orders`, `account_snapshot`, `events` |
| `IBBroker` (write) | `blive.adapters.ib.broker` | MISSING | M3 | `submit`, `cancel`, `replace`; full FSM via callbacks |
| `MockBroker` (test-only) | `tests/conftest.py` | M0 | M0 | minimal stub for unit tests not exercising round-trip |

### 2.2 `MarketDataPort` adapters

| Adapter | Module | Status | Milestone |
|---------|--------|--------|-----------|
| `PaperMarketData` (deterministic-fixture) | `blive.adapters.paper.market_data` | M1 implemented | M1 |
| `IBMarketData` | `blive.adapters.ib.market_data` | MISSING | M2 |
| `EODHDMarketData` | `blive.adapters.eodhd.market_data` | MISSING | M2 |

### 2.3 `ClockPort` adapters

| Adapter | Module | Status | Milestone |
|---------|--------|--------|-----------|
| `WallClock` | `blive.adapters.clock.wall` | M0 | M0 |
| `SimClock` | `blive.adapters.clock.sim` | M0 in flight | M0 |

### 2.4 `PersistencePort` adapters

| Adapter | Module | Status | Milestone |
|---------|--------|--------|-----------|
| `InMemoryPersistence` | `blive.adapters.memory.persistence` | M0 in flight | M0 |
| `SQLitePersistence` | `blive.adapters.sqlite.persistence` | MISSING | M4 (per [ADR-006](../decisions/DECISIONS.md#adr-006--sqlite-for-persistence-in-v1)) |

### 2.5 `AlertPort` adapters

| Adapter | Module | Status | Milestone |
|---------|--------|--------|-----------|
| `LogAlert` (writes to logger) | `blive.adapters.alert.log` | M1 implemented | M1 |
| `SlackAlert` | `blive.adapters.alert.slack` | MISSING | M7 |
| `EmailAlert` | `blive.adapters.alert.email` | MISSING | M7 |

### 2.6 `EventBusPort` adapters

| Adapter | Module | Status | Milestone |
|---------|--------|--------|-----------|
| `InMemoryEventBus` | `blive.adapters.memory.bus` | M0 in flight | M0 |
| `RedisStreamsEventBus` | `blive.adapters.redis.bus` | MISSING | post-M8 (opt-in per [ADR-007](../decisions/DECISIONS.md#adr-007--in-process-event-bus-for-v1)) |

## 3. The hexagonal contract (ADR-004)

The domain does not import from adapters. Enforced by the import-linter
contract `Domain layer is broker-neutral` in `pyproject.toml` (added at M0).

**Adapters depend on the domain via Protocols.** Each adapter's tests
verify it implements the Port contract and behaves correctly under chaos
fixtures (the chaos fixtures themselves arrive in KB-7, MISSING, drafted at
M3 from observed behaviour).

## 4. Cross-References

- [REQUIREMENTS §4 principle 1, §7.1, §7.2](../../REQUIREMENTS.md) — narrative origin.
- [DD-1 §2](../dd/domain_objects.md) — types referenced in signatures.
- [INV-5 domain_events](domain_events.md) — `DomainEvent` union.
- [INV-13 order_state_transitions](order_state_transitions.md) — FSM driven by `BrokerEvent`s.
- [ADR-004](../decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — hexagonal enforcement.
- [ADR-007](../decisions/DECISIONS.md#adr-007--in-process-event-bus-for-v1) — bus implementation choice.

## Open Questions

None blocking M0; richer signatures will be needed when M2/M3 adapters land.

## Changelog

- **v0.1 (2026-04-26)** — initial DRAFT at M0. Ports lifted from REQUIREMENTS §7.2; adapter status reflects M0 plan.
- **v0.2 (2026-04-27)** — promoted to STABLE at M1 close. `PaperMarketData` (§2.2) and `LogAlert` (§2.5) landed; `PaperBroker.replace()` (§2.1) now in-place per ADR-029-paired follow-up. M2-tier adapters remain MISSING. Port Protocol surfaces unchanged from v0.1.
