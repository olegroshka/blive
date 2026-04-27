"""In-process paper-trading :class:`BrokerPort` adapter.

Deterministic in-process matcher for development and unit tests. Honours
the order FSM (INV-13) by emitting ``OrderEvent``s in the canonical
sequence; never touches a wire.

M0 / M1 scope:

- Only ``MKT`` orders are matched (fill at the price returned by the
  ``price_lookup`` callable). ``LMT`` and stop variants are held in the
  open-orders book until canceled — partial fills are a later milestone.
- Position tracking is **not** done here; the engine derives positions
  from observed fills via :func:`blive.domain.positions.apply_fill`.
- ``account_snapshot`` returns a fixed stub.
- ``replace`` (M1) is in-place mutation of the open order's fields. INV-13
  does not currently include a replace trigger; the order keeps its FSM
  state and ``client_order_id`` and future fills evaluate against the new
  fields. This matches IB-side semantics: ``modifyOrder`` does not transition
  the venue's order status.
"""

from __future__ import annotations

import asyncio
import dataclasses
from decimal import Decimal
from typing import AsyncIterator, Callable
from uuid import UUID

from blive.domain.events import ConnectionStatus, OrderEvent
from blive.domain.ports import BrokerEvent, ClockPort
from blive.domain.types import (
    AccountSnapshot,
    ClientOrderId,
    Fill,
    Instrument,
    Order,
    OrderEventKind,
    OrderType,
    OrderUpdate,
    Position,
)


class PaperBroker:
    """In-process broker for paper mode. Implements ``BrokerPort``."""

    def __init__(
        self,
        clock: ClockPort,
        price_lookup: Callable[[Instrument], Decimal],
        *,
        commission_per_share: Decimal = Decimal("0.005"),
        ack_latency_s: float = 0.0,
        accept_latency_s: float = 0.0,
        fill_latency_s: float = 0.0,
        base_currency: str = "USD",
        starting_cash: Decimal = Decimal("1000000"),
    ) -> None:
        self._clock = clock
        self._price_lookup = price_lookup
        self._commission_per_share = commission_per_share
        self._ack_latency = ack_latency_s
        self._accept_latency = accept_latency_s
        self._fill_latency = fill_latency_s
        self._base_currency = base_currency
        self._starting_cash = starting_cash

        self._connected = False
        self._next_venue_seq = 1
        self._open_orders: dict[UUID, Order] = {}
        self._venue_id_by_order: dict[UUID, str] = {}
        self._events: asyncio.Queue[BrokerEvent] = asyncio.Queue()
        self._lifecycle_tasks: set[asyncio.Task[None]] = set()

    # --- BrokerPort ---------------------------------------------------------

    async def connect(self) -> None:
        self._connected = True
        await self._events.put(
            ConnectionStatus(
                connected=True,
                detail="paper broker connected",
                time_utc=self._clock.now(),
            )
        )

    async def disconnect(self) -> None:
        self._connected = False
        for task in list(self._lifecycle_tasks):
            task.cancel()
        await self._events.put(
            ConnectionStatus(
                connected=False,
                detail="paper broker disconnected",
                time_utc=self._clock.now(),
            )
        )

    async def submit(self, order: Order) -> ClientOrderId:
        if not self._connected:
            raise RuntimeError("PaperBroker.submit called before connect()")
        # Idempotency (REQUIREMENTS §5.3): re-submit with same id is a no-op.
        if order.client_order_id in self._open_orders:
            return ClientOrderId(order.client_order_id)
        self._open_orders[order.client_order_id] = order
        venue_id = self._mint_venue_id()
        self._venue_id_by_order[order.client_order_id] = venue_id

        task = asyncio.create_task(self._simulate_lifecycle(order, venue_id))
        self._lifecycle_tasks.add(task)
        task.add_done_callback(self._lifecycle_tasks.discard)
        return ClientOrderId(order.client_order_id)

    async def cancel(self, client_order_id: ClientOrderId) -> None:
        if client_order_id not in self._open_orders:
            # Idempotent: already filled or already canceled.
            return
        del self._open_orders[client_order_id]
        await self._events.put(
            OrderEvent(
                client_order_id=client_order_id,
                venue_order_id=self._venue_id_by_order.get(client_order_id),
                kind=OrderEventKind.CANCELED,
                reason="engine",
                time_utc=self._clock.now(),
            )
        )

    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None:
        if client_order_id not in self._open_orders:
            # Idempotent like cancel(): if the order has already terminated
            # there is nothing to replace.
            return
        original = self._open_orders[client_order_id]
        # OrderUpdate guarantees at least one field is non-None
        # (validated in DD-1 §2.9 / domain.types). Validate the merged
        # Order via ``dataclasses.replace``; __post_init__ in DD-1 catches
        # limit/stop discipline and the strict-positive rules.
        replaced = dataclasses.replace(
            original,
            quantity=new.quantity if new.quantity is not None else original.quantity,
            limit_price=(new.limit_price if new.limit_price is not None else original.limit_price),
            stop_price=new.stop_price if new.stop_price is not None else original.stop_price,
        )
        self._open_orders[client_order_id] = replaced

    async def open_orders(self) -> list[Order]:
        return list(self._open_orders.values())

    async def positions(self) -> list[Position]:
        # PaperBroker does not track positions; the engine derives them
        # from observed fills via blive.domain.positions.apply_fill.
        return []

    async def account_snapshot(self) -> AccountSnapshot:
        return AccountSnapshot(
            equity=self._starting_cash,
            cash_by_ccy={self._base_currency: self._starting_cash},
            buying_power=self._starting_cash,
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            leverage=Decimal("0"),
            margin_used=Decimal("0"),
            base_currency=self._base_currency,
            taken_at=self._clock.now(),
        )

    def events(self) -> AsyncIterator[BrokerEvent]:
        return self._events_stream()

    # --- Internals ----------------------------------------------------------

    def _mint_venue_id(self) -> str:
        venue_id = f"paper-{self._next_venue_seq:08d}"
        self._next_venue_seq += 1
        return venue_id

    async def _events_stream(self) -> AsyncIterator[BrokerEvent]:
        while True:
            event = await self._events.get()
            yield event

    async def _simulate_lifecycle(self, order: Order, venue_id: str) -> None:
        # The lifecycle re-checks ``_open_orders`` after every sleep; if the
        # order has been canceled in between, the task exits silently and
        # the cancel handler is responsible for emitting CANCELED.
        try:
            if self._ack_latency:
                await self._clock.sleep(self._ack_latency)
            if order.client_order_id not in self._open_orders:
                return
            await self._events.put(
                OrderEvent(
                    client_order_id=order.client_order_id,
                    venue_order_id=venue_id,
                    kind=OrderEventKind.SUBMITTED,
                    reason=None,
                    time_utc=self._clock.now(),
                )
            )

            if self._accept_latency:
                await self._clock.sleep(self._accept_latency)
            if order.client_order_id not in self._open_orders:
                return
            await self._events.put(
                OrderEvent(
                    client_order_id=order.client_order_id,
                    venue_order_id=venue_id,
                    kind=OrderEventKind.ACCEPTED,
                    reason=None,
                    time_utc=self._clock.now(),
                )
            )

            if order.order_type != OrderType.MKT:
                # M0: only MKT auto-fills. LMT / stop variants stay in the
                # open-orders book until cancel().
                return

            if self._fill_latency:
                await self._clock.sleep(self._fill_latency)
            if order.client_order_id not in self._open_orders:
                return
            del self._open_orders[order.client_order_id]

            price = self._price_lookup(order.instrument)
            commission = self._commission_per_share * order.quantity
            fill = Fill(
                client_order_id=order.client_order_id,
                venue_order_id=venue_id,
                venue_exec_id=f"{venue_id}-exec-1",
                instrument=order.instrument,
                side=order.side,
                quantity=order.quantity,
                price=price,
                commission=commission,
                currency=order.instrument.currency,
                time_utc=self._clock.now(),
            )
            await self._events.put(
                OrderEvent(
                    client_order_id=order.client_order_id,
                    venue_order_id=venue_id,
                    kind=OrderEventKind.FILLED,
                    reason=None,
                    time_utc=self._clock.now(),
                    fill=fill,
                )
            )
        except asyncio.CancelledError:
            return


__all__ = ["PaperBroker"]
