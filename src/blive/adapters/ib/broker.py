"""IB broker adapter — :class:`BrokerPort` implementation, read side.

M2-IB.3b-i ships the **read side**: ``connect`` / ``disconnect`` /
``positions`` / ``account_snapshot`` / ``open_orders`` / ``events``,
plus the 30s diff-suppress :class:`AccountUpdate` emission timer per
[ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence).
The write side (``submit`` / ``cancel`` / ``replace``) lands at M2-IB.4
and currently raises :class:`NotImplementedError`.

Connection model (per [KB-2 §1](../../../../docs/kb/ib_capability_matrix.md#1-connectivity-surface)):
the underlying :class:`IBClient` does the TCP handshake at :meth:`connect`,
then this class subscribes to ``ib.accountValueEvent`` so account values
stream in via ``ib_async``'s eventkit and accumulate locally for
:meth:`account_snapshot` to compose. Positions and open orders are
queried on demand via ``reqPositionsAsync`` / ``reqAllOpenOrdersAsync``;
each consumes one ``global`` token from the rate limiter per [KB-3 §1](../../../../docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle).

A background task started in :meth:`connect` (cancelled in :meth:`disconnect`)
ticks every ``account_update_interval_seconds`` (default 30s) and emits
an :class:`AccountUpdate` onto the :meth:`events` iterator if any field
crossed its diff-suppress threshold (currency-unit 0.01 / leverage 0.001
per ADR-033 §"Decision" item 2).

Position-mapping note: IB's view is per-account, not per-strategy. blive's
:class:`Position` requires a ``strategy_id``; this adapter tags positions
with the synthetic id ``f"ib_{account_id}"`` to mark them as
"broker-level positions on this IB account". Engine-side reconciliation
(M5) translates between this broker-level view and per-strategy views.
This mirrors the IGBroker convention.

What this module owns:

- TCP-handshake plumbing via :class:`IBClient`.
- Account-values accumulation (the cache underpinning :meth:`account_snapshot`).
- AccountUpdate emission timer + diff-suppress logic (ADR-033).
- IB ``Position`` / ``Trade`` parsing into broker-neutral
  :class:`blive.domain.types.Position` / :class:`Order` records.
- ConnectionStatus emission on connect/disconnect.

What is **not** here yet:

- Order-event FSM emission via ``orderStatusEvent`` /
  ``execDetailsEvent`` / ``commissionReportEvent`` — M2-IB.4 (write
  side).
- IBMarketData (``subscribe_bars`` / ``historical_bars``) — sibling
  module M2-IB.3b-ii.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator
from uuid import uuid4

import ib_async

from blive.adapters.ib.client import IBClient
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.domain.events import AccountUpdate, ConnectionStatus
from blive.domain.ports import BrokerEvent, ClockPort
from blive.domain.types import (
    AccountSnapshot,
    AssetClass,
    ClientOrderId,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    OrderUpdate,
    Position,
    TimeInForce,
    Tradability,
)

log = logging.getLogger(__name__)


# --- DD-7 §3 reverse map: IB exchange → MIC ---------------------------------
#
# Used by the read side to synthesise broker-neutral :class:`Instrument`
# records from IB ``Contract`` fields. Values are the inverse of
# :data:`blive.adapters.ib.instrument_resolver._MIC_TO_IB_EXCHANGE`.
# A sparse table is fine — unknown IB exchanges fall back to the IB
# exchange string itself, which the M5 reconciliation refines as needed.
_IB_EXCHANGE_TO_MIC: dict[str, str] = {
    "SBF": "XPAR",
    "NASDAQ": "XNAS",
    "ISLAND": "XNAS",  # NASDAQ legacy
    "NYSE": "XNYS",
    "ARCA": "ARCX",
    "BATS": "BATS",
    "LSE": "XLON",
    "IBIS": "XETR",
}


# IB ``secType`` → :class:`AssetClass`. Disambiguation is intentional
# best-effort — IB collapses EQUITY and ETF into "STK", so the reverse
# defaults to EQUITY (more general); strategies that need to distinguish
# (e.g. ADR-027 integer-share rounding scopes) carry the canonical
# :class:`Instrument` with ``asset_class=ETF`` from their original
# construction site, not from this reverse lookup.
_SEC_TYPE_TO_ASSET_CLASS: dict[str, AssetClass] = {
    "STK": AssetClass.EQUITY,
    "IND": AssetClass.INDEX,
    "CASH": AssetClass.FX,
    "FUT": AssetClass.FUTURE,
    "OPT": AssetClass.OPTION,
}


# IB AccountValue tags relevant to :class:`AccountSnapshot`.
#
# IB pushes account state as individual (tag, value, currency) tuples.
# We accumulate on ``accountValuesEvent`` and rebuild the snapshot in
# :meth:`account_snapshot`. The "BASE" pseudo-currency carries the
# account's aggregate values; per-currency rows carry the per-currency
# breakdown (used for ``cash_by_ccy``).
_TAG_NET_LIQUIDATION = "NetLiquidationByCurrency"
_TAG_TOTAL_CASH = "TotalCashBalance"
_TAG_BUYING_POWER = "BuyingPower"
_TAG_GROSS_POSITION = "GrossPositionValue"
_TAG_MAINT_MARGIN = "MaintMarginReq"


# Per-field thresholds for the AccountUpdate diff-suppress timer per
# [ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence)
# §"Decision" item 2. Currency-unit fields (equity, cash_by_ccy[ccy],
# buying_power, gross_exposure, net_exposure, margin_used) use 0.01;
# the dimensionless ``leverage`` ratio uses 0.001 (3 d.p.).
_ACCOUNT_VALUE_THRESHOLD: Decimal = Decimal("0.01")
_LEVERAGE_THRESHOLD: Decimal = Decimal("0.001")


class IBShapeError(Exception):
    """Raised when an IB-side response (positions, account values, orders)
    cannot be parsed into a broker-neutral domain object — typically a
    missing field, unexpected type, or unknown enum value. The fault is
    on the IB side (or in our parser); the connection itself is fine."""


class IBBroker:
    """`BrokerPort` adapter for IB Paper / live, read side.

    Wraps a single :class:`IBClient` (TCP handshake + rate limiter) plus
    an :class:`IBInstrumentResolver` (Instrument↔Contract). Account
    values accumulate on ``ib.accountValuesEvent``; positions and
    open orders are fetched on demand. The events() iterator yields
    :class:`ConnectionStatus` records for M2-IB.3b-i; richer events
    (AccountUpdate, OrderEvent) land at the 3b-i timer follow-up and
    M2-IB.4 respectively.
    """

    def __init__(
        self,
        *,
        client: IBClient,
        resolver: IBInstrumentResolver,
        clock: ClockPort,
        account_update_interval_seconds: float = 30.0,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._clock = clock
        self._account_update_interval_seconds = account_update_interval_seconds
        self._connected = False
        self._events: asyncio.Queue[BrokerEvent] = asyncio.Queue()
        # Latest accumulated AccountValue tuples, keyed by (currency, tag).
        # Currency "" means "BASE" / aggregate. Cleared on disconnect.
        self._account_values: dict[tuple[str, str], str] = {}
        # Cached event handler reference — needed so disconnect can detach
        # via ``-=`` symmetrically with the ``+=`` registration in connect.
        self._account_value_handler = self._on_account_value
        # Last-emitted snapshot for the 30s diff-suppress timer per ADR-033.
        # None until the first tick; reset on disconnect.
        self._last_emitted_snapshot: AccountSnapshot | None = None
        # Background task running :meth:`_account_update_loop`. Cancelled on
        # disconnect; recreated on connect.
        self._account_update_task: asyncio.Task[None] | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def broker_strategy_id(self) -> str:
        """Synthetic strategy id used for IB-side positions read back from
        the broker. Engine-side reconciliation (M5) translates between
        this broker-level view and per-strategy views."""
        return f"ib_{self._client.credentials.account_id}"

    # --- BrokerPort: connect / disconnect -----------------------------------

    async def connect(self) -> None:
        """Open the IB connection and start streaming account values.

        Idempotent: re-calling on a connected broker is a no-op.
        ``ib_async.IB.connectAsync`` (called inside :meth:`IBClient.connect`)
        already triggers ``reqAccountUpdatesAsync(account)`` + ``reqPositionsAsync``
        + ``reqOpenOrdersAsync`` and waits for the initial batch — so by
        the time this returns, ``ib.accountValues(account)`` is populated.
        We copy that initial state into our local cache, then attach
        ``ib.accountValueEvent`` so subsequent IB pushes update us.

        Emits a :class:`ConnectionStatus(connected=True)` event on the
        :meth:`events` iterator.
        """
        if self._connected:
            return
        await self._client.connect()
        ib = self._client.ib
        # Seed local cache from ib_async's internal cache (populated by
        # connectAsync's `reqAccountUpdatesAsync` initial batch).
        for av in ib.accountValues(self._client.credentials.account_id):
            self._on_account_value(av)
        # Subscribe for future updates.
        ib.accountValueEvent += self._account_value_handler
        self._connected = True
        # Start the 30s diff-suppress AccountUpdate emission timer per
        # ADR-033 §"Decision" item 2.
        self._account_update_task = asyncio.create_task(
            self._account_update_loop(),
            name=f"ib-broker-account-update-{self._client.credentials.account_id}",
        )
        await self._events.put(
            ConnectionStatus(
                connected=True,
                detail=(
                    f"IB broker connected (account "
                    f"{self._client.credentials.account_id} via "
                    f"{self._client.credentials.host}:{self._client.credentials.port})"
                ),
                time_utc=self._clock.now(),
            )
        )

    async def disconnect(self) -> None:
        """Close the IB connection and stop streaming account values.

        Idempotent: calling on a disconnected broker is a no-op.
        Best-effort cleanup — any underlying error is logged and
        suppressed (the broker still transitions to disconnected state
        and emits the corresponding :class:`ConnectionStatus`).

        Clears the accumulated account-value cache so a fresh
        :meth:`connect` starts from a clean slate (matches IB's own
        re-subscription behaviour).
        """
        if not self._connected:
            return
        # Cancel the AccountUpdate emission timer first so it doesn't
        # interleave with cache teardown.
        task = self._account_update_task
        self._account_update_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001 — best-effort cleanup
                log.warning("AccountUpdate loop raised on cancel; suppressing: %s", exc)
        ib = self._client.ib
        try:
            ib.accountValueEvent -= self._account_value_handler
        except Exception as exc:  # noqa: BLE001 — best-effort cleanup
            log.warning("Detaching ib.accountValueEvent handler raised; suppressing: %s", exc)
        # Note: no explicit reqAccountUpdates(False, ...) — ib_async's TWS
        # API wrapping doesn't expose an unsubscribe path; the subscription
        # is torn down implicitly when the underlying socket disconnects.
        await self._client.disconnect()
        self._connected = False
        self._account_values.clear()
        self._last_emitted_snapshot = None
        await self._events.put(
            ConnectionStatus(
                connected=False,
                detail=(
                    f"IB broker disconnected (account " f"{self._client.credentials.account_id})"
                ),
                time_utc=self._clock.now(),
            )
        )

    # --- BrokerPort: read methods -------------------------------------------

    async def positions(self) -> list[Position]:
        """Return IB's view of the account's open positions.

        Calls ``ib.reqPositionsAsync`` (consumes one ``global`` token);
        each returned ``ib_async.Position`` is parsed into a broker-neutral
        :class:`Position` tagged with :attr:`broker_strategy_id`.
        """
        self._require_connected()
        await self._client.rate_limiter.acquire("global")
        ib_positions = await self._client.ib.reqPositionsAsync()
        now = self._clock.now()
        out: list[Position] = []
        for ib_pos in ib_positions:
            if ib_pos is None:
                continue
            try:
                position = self._parse_ib_position(ib_pos, updated_at=now)
            except (IBShapeError, ValueError, AttributeError, TypeError) as exc:
                log.warning("IB Position skipped (parse failure): %s", exc)
                continue
            out.append(position)
        return out

    async def account_snapshot(self) -> AccountSnapshot:
        """Compose an :class:`AccountSnapshot` from accumulated account values.

        Reads the cache populated by ``accountValuesEvent`` since
        :meth:`connect`. Raises :class:`IBShapeError` if the cache is
        empty (no values pushed yet — caller should retry after a brief
        wait, or call this method only after the first account-update
        batch has arrived).

        Does **not** issue a wire request — the data is push-streamed.
        Cadence-based emission (30s diff-suppress per [ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence))
        is the M2-IB.3b-i follow-up.
        """
        self._require_connected()
        if not self._account_values:
            raise IBShapeError(
                "IB account values not yet received — accountValuesEvent has "
                "not pushed any values since connect(). The first batch "
                "typically arrives within ~500ms of connect(); retry after a "
                "brief wait."
            )
        return self._build_account_snapshot(taken_at=self._clock.now())

    async def open_orders(self) -> list[Order]:
        """Return IB's view of working orders.

        Calls ``ib.reqAllOpenOrdersAsync`` (consumes one ``global``
        token); each returned ``ib_async.Trade`` is parsed into a
        broker-neutral :class:`Order` tagged with
        :attr:`broker_strategy_id`.
        """
        self._require_connected()
        await self._client.rate_limiter.acquire("global")
        ib_trades = await self._client.ib.reqAllOpenOrdersAsync()
        out: list[Order] = []
        for trade in ib_trades:
            if trade is None:
                continue
            try:
                order = self._parse_ib_trade_to_order(trade)
            except (IBShapeError, ValueError, AttributeError, TypeError) as exc:
                log.warning("IB Trade skipped (parse failure): %s", exc)
                continue
            out.append(order)
        return out

    def events(self) -> AsyncIterator[BrokerEvent]:
        """Async iterator over connection-state + (M2-IB.3b-i timer) account
        update events.

        For M2-IB.3b-i the iterator yields :class:`ConnectionStatus`
        records (connect / disconnect) plus :class:`AccountUpdate` records
        emitted by the 30s diff-suppress timer per [ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence).
        :class:`OrderEvent` events arrive at M2-IB.4 (write side).
        """
        return self._events_stream()

    async def _events_stream(self) -> AsyncIterator[BrokerEvent]:
        while True:
            event = await self._events.get()
            yield event

    # --- BrokerPort: write methods (M2-IB.4) --------------------------------

    async def submit(self, order: Order) -> ClientOrderId:
        raise NotImplementedError(
            "IBBroker.submit lands at M2-IB.4 (write side). The IB Gateway's "
            "'Read-Only API' checkbox must also be unchecked before submit "
            "will work — Configuration > API > Settings."
        )

    async def cancel(self, client_order_id: ClientOrderId) -> None:
        raise NotImplementedError("IBBroker.cancel lands at M2-IB.4 (write side).")

    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None:
        raise NotImplementedError("IBBroker.replace lands at M2-IB.4 (write side).")

    # --- Internals: AccountUpdate emission timer (ADR-033) ------------------

    async def _account_update_loop(self) -> None:
        """Background task: every ``account_update_interval_seconds`` (30s
        wall-clock by default), invoke :meth:`_account_update_tick`.

        Cancelled by :meth:`disconnect`. Uses :func:`asyncio.sleep` rather
        than :meth:`ClockPort.sleep` so the cadence is real-time even
        when tests inject a :class:`SimClock` for timestamps. Tests of
        the tick logic call :meth:`_account_update_tick` directly rather
        than running this loop.
        """
        try:
            while self._connected:
                await asyncio.sleep(self._account_update_interval_seconds)
                if not self._connected:
                    return
                await self._account_update_tick()
        except asyncio.CancelledError:
            raise

    async def _account_update_tick(self) -> None:
        """One iteration of the AccountUpdate emission loop.

        Builds the current snapshot from the accumulated account-values
        cache; if any field has changed beyond its threshold (or this is
        the first tick after connect), emits an
        :class:`AccountUpdate` event and updates :attr:`_last_emitted_snapshot`.
        Empty cache or build failure → silent skip (no event, no error
        propagation; the next tick re-evaluates).
        """
        if not self._account_values:
            return
        try:
            current = self._build_account_snapshot(taken_at=self._clock.now())
        except IBShapeError:
            return
        if not self._should_emit_account_update(current):
            return
        await self._events.put(AccountUpdate(snapshot=current, time_utc=self._clock.now()))
        self._last_emitted_snapshot = current

    def _should_emit_account_update(self, current: AccountSnapshot) -> bool:
        """Per ADR-033 §"Decision" item 2: emit when any field has moved
        beyond its threshold compared to the last emitted snapshot.

        Per-field thresholds (currency-unit values use 0.01; ``leverage``
        uses 0.001 since it is a ratio). On the first tick (no
        ``_last_emitted_snapshot``), always emit — there is no baseline
        to diff against and the consumer (UI / persistence) needs the
        initial state.
        """
        last = self._last_emitted_snapshot
        if last is None:
            return True

        if abs(current.equity - last.equity) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.buying_power - last.buying_power) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.gross_exposure - last.gross_exposure) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.net_exposure - last.net_exposure) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.margin_used - last.margin_used) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.leverage - last.leverage) >= _LEVERAGE_THRESHOLD:
            return True

        # cash_by_ccy: union of currencies; treat absent currency as zero.
        all_ccys = set(current.cash_by_ccy) | set(last.cash_by_ccy)
        for ccy in all_ccys:
            delta = abs(
                current.cash_by_ccy.get(ccy, Decimal("0")) - last.cash_by_ccy.get(ccy, Decimal("0"))
            )
            if delta >= _ACCOUNT_VALUE_THRESHOLD:
                return True
        return False

    # --- Internals: event handlers ------------------------------------------

    def _on_account_value(self, account_value: ib_async.AccountValue) -> None:
        """Accumulate one IB ``AccountValue`` push.

        Called by ``ib.accountValuesEvent``; runs on the asyncio loop
        thread (ib_async dispatches eventkit handlers from the loop).
        Stores the raw string value keyed by (currency, tag); parsing
        deferred to :meth:`_build_account_snapshot`.

        Multiple account values for the same (currency, tag) overwrite —
        the latest push wins, matching IB's "live state" semantics.
        """
        currency = account_value.currency or ""
        tag = account_value.tag or ""
        if not tag:
            return  # malformed push; drop quietly
        # Filter: only the account we subscribed to. ib_async sometimes
        # forwards values for sub-accounts when a master client connects.
        if account_value.account and account_value.account != self._client.credentials.account_id:
            return
        self._account_values[(currency, tag)] = account_value.value

    # --- Internals: parsers -------------------------------------------------

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("IBBroker.connect() must be called before read / write methods")

    def _parse_ib_position(self, ib_pos: ib_async.Position, *, updated_at: datetime) -> Position:
        """Map ``ib_async.Position`` to broker-neutral :class:`Position`."""
        contract = ib_pos.contract
        if contract is None:
            raise IBShapeError("IB Position has no contract")
        instrument = self._instrument_from_contract(contract)
        quantity = Decimal(str(ib_pos.position))
        avg_cost = Decimal(str(ib_pos.avgCost))
        opened_at = updated_at if quantity != 0 else None
        return Position(
            instrument=instrument,
            strategy_id=self.broker_strategy_id,
            quantity=quantity,
            avg_cost=avg_cost if quantity != 0 else Decimal("0"),
            currency=instrument.currency,
            opened_at=opened_at,
            updated_at=updated_at,
        )

    def _parse_ib_trade_to_order(self, trade: ib_async.Trade) -> Order:
        """Map ``ib_async.Trade`` to broker-neutral :class:`Order`."""
        ib_order = getattr(trade, "order", None)
        contract = getattr(trade, "contract", None)
        if ib_order is None or contract is None:
            raise IBShapeError("IB Trade missing order or contract")

        instrument = self._instrument_from_contract(contract)
        side = _parse_order_side(getattr(ib_order, "action", ""))
        order_type = _parse_order_type(getattr(ib_order, "orderType", ""))
        time_in_force = _parse_time_in_force(getattr(ib_order, "tif", ""))

        # Order ids: IB has its own integer orderId; blive uses UUID. For
        # orders that didn't originate in blive (manual TWS orders, leftover
        # working orders from a prior session), synthesise a UUID and tag
        # the original IB orderId for traceability.
        client_order_id = uuid4()
        ib_order_id = getattr(ib_order, "orderId", None)
        tags: dict[str, str] = {}
        if ib_order_id is not None:
            tags["ib_order_id"] = str(ib_order_id)
        ib_perm_id = getattr(ib_order, "permId", None)
        if ib_perm_id is not None:
            tags["ib_perm_id"] = str(ib_perm_id)

        # Limit / stop prices: IB stores 0.0 as "no price" for non-LMT/STP
        # types; we surface ``None`` to match DD-1 §2.4 invariants.
        limit_price = _decimal_or_none(getattr(ib_order, "lmtPrice", None))
        stop_price = _decimal_or_none(getattr(ib_order, "auxPrice", None))
        if order_type not in (OrderType.LMT, OrderType.STP_LMT):
            limit_price = None
        if order_type not in (OrderType.STP, OrderType.STP_LMT):
            stop_price = None

        quantity = Decimal(str(getattr(ib_order, "totalQuantity", "0")))
        if quantity <= 0:
            raise IBShapeError(f"IB order has non-positive totalQuantity {quantity!r}")

        return Order(
            client_order_id=ClientOrderId(client_order_id),
            strategy_id=self.broker_strategy_id,
            instrument=instrument,
            side=side,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            parent_id=None,
            tags=tags,
            created_at=self._clock.now(),
        )

    def _instrument_from_contract(self, contract: ib_async.Contract) -> Instrument:
        """Synthesise an :class:`Instrument` from an IB ``Contract``.

        Best-effort: IB collapses EQUITY/ETF into "STK" so the reverse
        defaults to EQUITY. Multi-Yahoo-suffix re-addition is **not**
        attempted here — the strategy that placed the order owns the
        canonical Instrument; this synthesis is for IB-side bookkeeping
        only (positions / open-orders read-back). M5 reconciliation
        translates between the two views.
        """
        symbol = getattr(contract, "symbol", "") or ""
        if not symbol:
            raise IBShapeError("IB Contract has empty symbol")
        sec_type = getattr(contract, "secType", "") or ""
        exchange = getattr(contract, "exchange", "") or ""
        primary_exchange = getattr(contract, "primaryExchange", "") or ""
        # IB reports the *primary* exchange on positions / open orders;
        # if it's set, prefer it over the routing exchange.
        ib_exchange = primary_exchange or exchange
        currency = getattr(contract, "currency", "") or ""
        if not currency:
            raise IBShapeError("IB Contract has empty currency")
        asset_class = _SEC_TYPE_TO_ASSET_CLASS.get(sec_type, AssetClass.EQUITY)
        venue = _IB_EXCHANGE_TO_MIC.get(ib_exchange, ib_exchange)

        multiplier_str = getattr(contract, "multiplier", "") or ""
        multiplier = Decimal(multiplier_str) if multiplier_str else Decimal("1")

        # Tradability: IB retail is spot-only per ADR-040 + ADR-037; CFDs
        # are an IG-side thing.
        tradability: Tradability = "spot"

        return Instrument(
            symbol=symbol,
            venue=venue,
            currency=currency,
            asset_class=asset_class,
            multiplier=multiplier,
            tradability=tradability,
        )

    def _build_account_snapshot(self, *, taken_at: datetime) -> AccountSnapshot:
        """Compose an :class:`AccountSnapshot` from accumulated account values.

        Identifies the base currency from the "BASE" pseudo-currency
        rows (or falls back to the most-frequent currency in the cache).
        Aggregate fields (equity, buying_power, gross_exposure,
        margin_used) come from the BASE rows; per-currency cash from
        per-currency rows.
        """
        # Identify base currency: IB uses an explicit "BASE" pseudo-currency
        # in the account-value stream for aggregate values. The actual
        # base-currency code is reported via the AccountCode tag with no
        # currency, or via per-currency rows.
        base_currency = self._infer_base_currency()

        equity = self._account_value_decimal(
            (base_currency, _TAG_NET_LIQUIDATION),
            fallback_keys=[("BASE", _TAG_NET_LIQUIDATION)],
        )
        buying_power = self._account_value_decimal(
            (base_currency, _TAG_BUYING_POWER),
            fallback_keys=[("BASE", _TAG_BUYING_POWER)],
        )
        gross_exposure = self._account_value_decimal(
            (base_currency, _TAG_GROSS_POSITION),
            fallback_keys=[("BASE", _TAG_GROSS_POSITION)],
        )
        margin_used = self._account_value_decimal(
            (base_currency, _TAG_MAINT_MARGIN),
            fallback_keys=[("BASE", _TAG_MAINT_MARGIN)],
        )

        # cash_by_ccy: per-currency TotalCashBalance rows (excludes the
        # "BASE" aggregate row).
        cash_by_ccy: dict[str, Decimal] = {}
        for (ccy, tag), value in self._account_values.items():
            if tag == _TAG_TOTAL_CASH and ccy and ccy != "BASE":
                try:
                    cash_by_ccy[ccy] = Decimal(value)
                except (ValueError, ArithmeticError):
                    log.warning(
                        "IB account value %s.%s = %r is not a Decimal; skipping",
                        ccy,
                        tag,
                        value,
                    )

        # net_exposure: IB doesn't push a single "net exposure" tag, so we
        # derive it as gross_exposure for v1. Strategies using long/short
        # need the M4 widening to query per-position net properly.
        net_exposure = gross_exposure

        leverage = (gross_exposure / equity) if equity and equity > 0 else Decimal("0")

        return AccountSnapshot(
            equity=equity,
            cash_by_ccy=cash_by_ccy,
            buying_power=buying_power,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            leverage=leverage,
            margin_used=margin_used,
            base_currency=base_currency,
            taken_at=taken_at,
        )

    def _infer_base_currency(self) -> str:
        """Identify the account's base currency from accumulated values.

        IB reports a "BASE" pseudo-currency for aggregate values; the
        actual currency code lives in per-currency rows. Heuristic:
        prefer the explicit ``AccountCurrency`` tag (rare); else pick
        the currency that appears in the most ``NetLiquidationByCurrency``
        rows that aren't "BASE" — this is the per-account base in
        practice.
        """
        # 1. Explicit AccountCurrency tag (set in some account configs).
        for (ccy, tag), value in self._account_values.items():
            if tag == "AccountCurrency" and value:
                return value

        # 2. The non-BASE currency with a NetLiquidation row. For a
        # single-currency account there's only one; for multi-currency the
        # account base is ambiguous and we pick the highest-equity row.
        best_ccy = ""
        best_equity = Decimal("-Infinity")
        for (ccy, tag), value in self._account_values.items():
            if tag != _TAG_NET_LIQUIDATION:
                continue
            if not ccy or ccy == "BASE":
                continue
            try:
                equity = Decimal(value)
            except (ValueError, ArithmeticError):
                continue
            if equity > best_equity:
                best_equity = equity
                best_ccy = ccy
        if best_ccy:
            return best_ccy

        # 3. Fallback: USD (most common IB account currency).
        return "USD"

    def _account_value_decimal(
        self,
        primary_key: tuple[str, str],
        *,
        fallback_keys: list[tuple[str, str]] | None = None,
    ) -> Decimal:
        """Read an account value as Decimal, with fallback keys.

        Used for the BASE-vs-base-currency duality. Returns ``Decimal("0")``
        if no key is present (an empty cache shouldn't reach here per
        :meth:`account_snapshot`'s upfront check, but defensively zero
        is safer than raising on a single missing tag).
        """
        candidates = [primary_key]
        if fallback_keys:
            candidates.extend(fallback_keys)
        for key in candidates:
            value = self._account_values.get(key)
            if value is None:
                continue
            try:
                return Decimal(value)
            except (ValueError, ArithmeticError):
                log.warning(
                    "IB account value %s = %r is not a Decimal; skipping",
                    key,
                    value,
                )
        return Decimal("0")


def _parse_order_side(action: str) -> OrderSide:
    if action == "BUY":
        return OrderSide.BUY
    if action == "SELL":
        return OrderSide.SELL
    raise IBShapeError(f"Unknown IB order action {action!r}")


# IB ``orderType`` is a string in TWS API. We map only the v1 subset; richer
# types are a future-strategy concern. Unknown types raise (load-bearing —
# we can't silently treat ``MIDPRICE`` as ``LMT``).
_IB_ORDER_TYPE_MAP: dict[str, OrderType] = {
    "MKT": OrderType.MKT,
    "LMT": OrderType.LMT,
    "MOC": OrderType.MOC,
    "LOC": OrderType.LOC,
    "STP": OrderType.STP,
    "STP LMT": OrderType.STP_LMT,
    "STP_LMT": OrderType.STP_LMT,
}


def _parse_order_type(order_type_str: str) -> OrderType:
    mapped = _IB_ORDER_TYPE_MAP.get(order_type_str)
    if mapped is None:
        raise IBShapeError(f"Unsupported IB orderType {order_type_str!r}")
    return mapped


_IB_TIF_MAP: dict[str, TimeInForce] = {
    "DAY": TimeInForce.DAY,
    "GTC": TimeInForce.GTC,
    "IOC": TimeInForce.IOC,
    "FOK": TimeInForce.FOK,
    "OPG": TimeInForce.OPG,
}


def _parse_time_in_force(tif_str: str) -> TimeInForce:
    mapped = _IB_TIF_MAP.get(tif_str)
    if mapped is None:
        raise IBShapeError(f"Unsupported IB tif {tif_str!r}")
    return mapped


def _decimal_or_none(value: Any) -> Decimal | None:
    """Parse an IB-side numeric to Decimal, treating 0 / 0.0 / None / ''
    as None (IB uses 0.0 as a "not set" sentinel for limit / stop fields
    on order types that don't carry that field).
    """
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
    if d == 0:
        return None
    return d


__all__ = [
    "IBBroker",
    "IBShapeError",
]
