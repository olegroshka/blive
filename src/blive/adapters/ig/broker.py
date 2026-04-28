"""IG broker adapter — :class:`BrokerPort` implementation.

M2-IG.3 ships the **read side**: ``connect``, ``disconnect``,
``positions``, ``account_snapshot``, ``open_orders``, ``events``. The
write side (``submit`` / ``cancel`` / ``replace``) lands at M2-IG.4 and
currently raises :class:`NotImplementedError`.

Connection model (per [KB-16 §1](../../../../docs/kb/ig_capability_matrix.md#1-connectivity-surface)):
the underlying :class:`IGClient` does the 3-step REST auth at
:meth:`connect`, then this class issues ``PUT /session`` to select the
``IGCredentials.account_id`` as active. All subsequent ``/positions`` /
``/accounts`` / ``/workingorders`` calls return data scoped to that
account.

Position mapping note: IG's view ([KB-16 §2](../../../../docs/kb/ig_capability_matrix.md#2-account-types-and-trading-modes))
is per-account, not per-strategy. blive's :class:`Position` requires a
``strategy_id``; this adapter tags positions with the synthetic id
``f"ig_{account_id}"`` to mark them as "broker-level positions on this
IG account". Engine-side reconciliation (M2-IG.5) translates between
this broker-level view and per-strategy views.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Mapping
from uuid import UUID, uuid4

from blive.adapters.ig.client import IGClient
from blive.adapters.ig.credentials import IGCredentials
from blive.adapters.ig.instrument_resolver import IGInstrumentResolver
from blive.domain.events import ConnectionStatus
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
)

log = logging.getLogger(__name__)


class IGBroker:
    """`BrokerPort` adapter for IG demo / live.

    Wraps a single :class:`IGClient` (REST half of ADR-036) plus an
    :class:`IGInstrumentResolver` for epic ↔ Instrument mapping. The
    Lightstreamer half of order events is wired in M2-IG.4 (write side);
    M2-IG.3 emits only the connection-state events through :meth:`events`.
    """

    def __init__(
        self,
        *,
        client: IGClient,
        resolver: IGInstrumentResolver,
        credentials: IGCredentials,
        clock: ClockPort,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._credentials = credentials
        self._clock = clock
        self._events: asyncio.Queue[BrokerEvent] = asyncio.Queue()
        self._connected = False

    # --- BrokerPort: connect / disconnect -----------------------------------

    async def connect(self) -> None:
        """Authenticate via :class:`IGClient` and switch active account."""
        if self._connected:
            return
        await self._client.connect()
        # Switch active account so /positions, /accounts, /workingorders
        # return data scoped to credentials.account_id.
        await self._client.put(
            "/session",
            version=1,
            json={"accountId": self._credentials.account_id},
            bucket="general",
        )
        self._connected = True
        await self._events.put(
            ConnectionStatus(
                connected=True,
                detail=(
                    f"IG broker connected ({self._credentials.environment} "
                    f"account {self._credentials.account_id})"
                ),
                time_utc=self._clock.now(),
            )
        )

    async def disconnect(self) -> None:
        """Best-effort logout + close transport. Idempotent."""
        if not self._connected:
            return
        try:
            await self._client.disconnect()
        finally:
            self._connected = False
            await self._events.put(
                ConnectionStatus(
                    connected=False,
                    detail=f"IG broker disconnected (account {self._credentials.account_id})",
                    time_utc=self._clock.now(),
                )
            )

    # --- BrokerPort: read methods -------------------------------------------

    async def positions(self) -> list[Position]:
        """Return the IG account's open positions as :class:`Position` records.

        Per [KB-16 §3](../../../../docs/kb/ig_capability_matrix.md#3-asset-classes),
        IG's /positions endpoint returns the active account's positions.
        Each entry's ``market.epic`` is reverse-mapped to a synthesised
        :class:`Instrument` (CFD; the resolver's reverse map is implicit
        in the mapping shape — for v1 we only round-trip what we can).
        """
        self._require_connected()
        body = await self._client.get("/positions", version=2, bucket="general")
        if not isinstance(body, dict):
            return []
        raw_positions = body.get("positions", [])
        if not isinstance(raw_positions, list):
            return []

        out: list[Position] = []
        now = self._clock.now()
        broker_strategy_id = self._broker_strategy_id()
        for entry in raw_positions:
            if not isinstance(entry, dict):
                continue
            position_obj = entry.get("position")
            market_obj = entry.get("market")
            if not isinstance(position_obj, dict) or not isinstance(market_obj, dict):
                continue
            try:
                position = _parse_position(
                    position_obj=position_obj,
                    market_obj=market_obj,
                    strategy_id=broker_strategy_id,
                    updated_at=now,
                )
            except (KeyError, ValueError, TypeError) as exc:
                log.warning("IG /positions entry skipped (parse failure): %s", exc)
                continue
            out.append(position)
        return out

    async def account_snapshot(self) -> AccountSnapshot:
        """Return the IG account-level snapshot.

        Maps IG's per-account ``balance`` payload to :class:`AccountSnapshot`.
        IG returns multiple accounts when the user has them; we filter to
        ``credentials.account_id``.
        """
        self._require_connected()
        body = await self._client.get("/accounts", version=1, bucket="general")
        if not isinstance(body, dict):
            raise _IGShapeError(f"IG /accounts returned non-dict: {type(body).__name__}")
        accounts = body.get("accounts")
        if not isinstance(accounts, list) or not accounts:
            raise _IGShapeError("IG /accounts returned no accounts")

        target = None
        for acc in accounts:
            if isinstance(acc, dict) and acc.get("accountId") == self._credentials.account_id:
                target = acc
                break
        if target is None:
            raise _IGShapeError(
                f"IG account {self._credentials.account_id!r} not found in "
                f"/accounts response (found: "
                f"{[a.get('accountId') for a in accounts if isinstance(a, dict)]})"
            )
        return _parse_account_snapshot(target, taken_at=self._clock.now())

    async def open_orders(self) -> list[Order]:
        """Return IG's working-orders list as :class:`Order` records.

        IG ``/workingorders`` returns LIMIT / STOP orders that haven't
        filled. Market orders execute immediately at IG so they're not
        in the working-orders list.
        """
        self._require_connected()
        body = await self._client.get("/workingorders", version=2, bucket="general")
        if not isinstance(body, dict):
            return []
        raw_orders = body.get("workingOrders", [])
        if not isinstance(raw_orders, list):
            return []

        out: list[Order] = []
        broker_strategy_id = self._broker_strategy_id()
        for entry in raw_orders:
            if not isinstance(entry, dict):
                continue
            order_obj = entry.get("workingOrderData")
            market_obj = entry.get("marketData")
            if not isinstance(order_obj, dict) or not isinstance(market_obj, dict):
                continue
            try:
                order = _parse_working_order(
                    order_obj=order_obj,
                    market_obj=market_obj,
                    strategy_id=broker_strategy_id,
                )
            except (KeyError, ValueError, TypeError) as exc:
                log.warning("IG /workingorders entry skipped (parse failure): %s", exc)
                continue
            out.append(order)
        return out

    def events(self) -> AsyncIterator[BrokerEvent]:
        """Async iterator over connection-state + (M2-IG.4) order events.

        For M2-IG.3 only :class:`ConnectionStatus` events flow here —
        emitted from :meth:`connect` and :meth:`disconnect`. Order events
        require Lightstreamer subscription (M2-IG.4).
        """
        return self._events_stream()

    # --- BrokerPort: write methods (M2-IG.4 stubs) --------------------------

    async def submit(self, order: Order) -> ClientOrderId:
        raise NotImplementedError(
            "IGBroker.submit lands at M2-IG.4; M2-IG.3 ships read-side only"
        )

    async def cancel(self, client_order_id: ClientOrderId) -> None:
        raise NotImplementedError(
            "IGBroker.cancel lands at M2-IG.4; M2-IG.3 ships read-side only"
        )

    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None:
        raise NotImplementedError(
            "IGBroker.replace lands at M2-IG.4; M2-IG.3 ships read-side only"
        )

    # --- Internals ----------------------------------------------------------

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("IGBroker.<read> called before connect()")

    def _broker_strategy_id(self) -> str:
        """The synthetic broker-level strategy_id used to tag IG-side
        positions / orders. Engine-side reconciliation translates."""
        return f"ig_{self._credentials.account_id}"

    async def _events_stream(self) -> AsyncIterator[BrokerEvent]:
        while True:
            event = await self._events.get()
            yield event


# --- IG response parsers (module-level, unit-testable) ----------------------


class _IGShapeError(ValueError):
    """The IG response had a shape the parser doesn't recognise. Bubbles up
    as a regular ValueError but with a distinct class for tests / logs."""


def _parse_position(
    *,
    position_obj: Mapping[str, Any],
    market_obj: Mapping[str, Any],
    strategy_id: str,
    updated_at: datetime,
) -> Position:
    """Translate one IG /positions entry to a :class:`Position`.

    IG fields used:
    - ``position.size`` — absolute size; sign comes from ``direction``.
    - ``position.direction`` — ``"BUY"`` or ``"SELL"``; signs ``size``.
    - ``position.level`` — entry price (avg cost for a single-fill position).
    - ``position.currency`` — ISO 4217 currency.
    - ``position.createdDate`` — ISO timestamp; opened_at.
    - ``market.epic`` — IG instrument id; reverse-mapped to a synthesised
      :class:`Instrument` (CFD in v1).
    - ``market.instrumentName`` — informational; not required.
    """
    epic = str(market_obj.get("epic", ""))
    if not epic:
        raise _IGShapeError("IG position market entry missing 'epic'")

    direction = str(position_obj.get("direction", ""))
    if direction not in ("BUY", "SELL"):
        raise _IGShapeError(f"IG position direction must be BUY/SELL, got {direction!r}")
    size_raw = position_obj.get("size")
    if size_raw is None:
        raise _IGShapeError("IG position missing 'size'")
    size = Decimal(str(size_raw))
    signed_qty = size if direction == "BUY" else -size

    level_raw = position_obj.get("level")
    if level_raw is None:
        raise _IGShapeError("IG position missing 'level'")
    avg_cost = Decimal(str(level_raw))

    currency = str(position_obj.get("currency", ""))
    if not currency:
        raise _IGShapeError("IG position missing 'currency'")

    created = position_obj.get("createdDate") or position_obj.get("createdDateUTC")
    opened_at: datetime | None = None
    if isinstance(created, str) and created:
        try:
            opened_at = _parse_ig_timestamp(created)
        except ValueError:
            opened_at = None
    # blive's Position requires opened_at when quantity != 0 (DD-1 §2.7).
    # If IG didn't include a creation date for a non-zero position, fall back
    # to the snapshot time — we know we observed the position at `updated_at`,
    # which is a strict upper bound on when it actually opened.
    if opened_at is None and signed_qty != Decimal("0"):
        opened_at = updated_at

    instrument = Instrument(
        symbol=_epic_to_symbol(epic),
        venue="IG",
        currency=currency,
        asset_class=_epic_to_asset_class(epic),
        tradability="cfd",
    )
    return Position(
        instrument=instrument,
        strategy_id=strategy_id,
        quantity=signed_qty,
        avg_cost=avg_cost,
        currency=currency,
        opened_at=opened_at,
        updated_at=updated_at,
    )


def _parse_account_snapshot(
    account_obj: Mapping[str, Any],
    *,
    taken_at: datetime,
) -> AccountSnapshot:
    """Translate one IG /accounts entry to :class:`AccountSnapshot`."""
    balance = account_obj.get("balance")
    if not isinstance(balance, dict):
        raise _IGShapeError("IG account entry missing 'balance' object")
    base_currency = str(account_obj.get("currency", ""))
    if not base_currency:
        raise _IGShapeError("IG account entry missing 'currency'")

    available = Decimal(str(balance.get("available", "0")))
    balance_amount = Decimal(str(balance.get("balance", "0")))
    profit_loss = Decimal(str(balance.get("profitLoss", "0")))
    deposit = Decimal(str(balance.get("deposit", "0")))

    equity = balance_amount + profit_loss
    cash_by_ccy = {base_currency: available}
    # IG doesn't surface margin / exposure breakdown in /accounts — fill with
    # zeros and let the engine's continuous-reconciliation tick (M5) populate
    # exposure from the per-position view.
    return AccountSnapshot(
        equity=equity,
        cash_by_ccy=cash_by_ccy,
        buying_power=available,
        gross_exposure=Decimal("0"),
        net_exposure=Decimal("0"),
        leverage=Decimal("0"),
        margin_used=deposit,
        base_currency=base_currency,
        taken_at=taken_at,
    )


def _parse_working_order(
    *,
    order_obj: Mapping[str, Any],
    market_obj: Mapping[str, Any],
    strategy_id: str,
) -> Order:
    """Translate one IG /workingorders entry to :class:`Order`."""
    epic = str(market_obj.get("epic", ""))
    if not epic:
        raise _IGShapeError("IG working order market entry missing 'epic'")

    direction = str(order_obj.get("direction", ""))
    if direction not in ("BUY", "SELL"):
        raise _IGShapeError(f"IG working order direction must be BUY/SELL, got {direction!r}")
    size_raw = order_obj.get("orderSize")
    if size_raw is None:
        raise _IGShapeError("IG working order missing 'orderSize'")
    quantity = Decimal(str(size_raw))

    level_raw = order_obj.get("orderLevel")
    if level_raw is None:
        raise _IGShapeError("IG working order missing 'orderLevel'")
    limit_price = Decimal(str(level_raw))

    order_type_raw = str(order_obj.get("orderType", ""))
    blive_order_type, ig_to_blive_limit, ig_to_blive_stop = _ig_order_type_to_blive(order_type_raw)
    tif_raw = str(order_obj.get("timeInForce", "GOOD_TILL_CANCELLED"))
    blive_tif = _ig_tif_to_blive(tif_raw)

    created = order_obj.get("createdDate") or order_obj.get("createdDateUTC")
    if isinstance(created, str) and created:
        try:
            created_at = _parse_ig_timestamp(created)
        except ValueError:
            created_at = datetime.now(timezone.utc)
    else:
        created_at = datetime.now(timezone.utc)

    deal_id = str(order_obj.get("dealId", ""))
    deal_reference = str(order_obj.get("dealReference", ""))

    instrument = Instrument(
        symbol=_epic_to_symbol(epic),
        venue="IG",
        currency=str(market_obj.get("currencies", [{}])[0].get("code", "EUR"))
        if isinstance(market_obj.get("currencies"), list) and market_obj.get("currencies")
        else "EUR",
        asset_class=_epic_to_asset_class(epic),
        tradability="cfd",
    )

    # blive's Order requires a UUID client_order_id; IG's working orders
    # have no blive UUID (they were placed externally). Synthesise a
    # deterministic UUID from the dealId so reconciliation across
    # restarts is stable.
    client_order_id = (
        UUID(int=int(deal_id, 16) & ((1 << 128) - 1)) if _hex_like(deal_id) else uuid4()
    )

    return Order(
        client_order_id=client_order_id,
        strategy_id=strategy_id,
        instrument=instrument,
        side=OrderSide.BUY if direction == "BUY" else OrderSide.SELL,
        quantity=quantity,
        order_type=blive_order_type,
        time_in_force=blive_tif,
        limit_price=limit_price if ig_to_blive_limit else None,
        stop_price=limit_price if ig_to_blive_stop else None,
        parent_id=None,
        tags={
            "ig_deal_id": deal_id,
            "ig_deal_reference": deal_reference,
            "ig_order_type_raw": order_type_raw,
        },
        created_at=created_at,
    )


# --- Helpers ----------------------------------------------------------------


def _epic_to_symbol(epic: str) -> str:
    """Extract the symbol segment from an IG epic.

    Epic format per [DD-8 §1](../../../../docs/dd/ig_instrument_dictionary.md#1-the-ig-epic-taxonomy):
    ``{family}.{type}.{symbol}.{mode}.{settlement}``. Phase 1 case:
    ``IX.D.CAC40.CASH.IP`` → ``"CAC40"``.

    Returns the epic itself if the format doesn't match — callers see a
    weird but non-empty symbol rather than an error.
    """
    parts = epic.split(".")
    if len(parts) >= 5:
        return parts[2]
    return epic


def _epic_to_asset_class(epic: str) -> AssetClass:
    """Map the epic family code to a blive `AssetClass`."""
    family = epic.split(".", 1)[0] if "." in epic else epic
    if family == "IX":
        return AssetClass.INDEX
    if family in ("KC", "KX"):
        return AssetClass.EQUITY
    if family == "CS":
        return AssetClass.FX
    if family == "CC":
        # Commodities don't have a blive AssetClass member yet; fall back to FUTURE.
        return AssetClass.FUTURE
    if family == "IR":
        return AssetClass.FUTURE
    if family in ("KA", "KB"):
        return AssetClass.OPTION
    return AssetClass.INDEX  # default for unknown families — informational only


def _ig_order_type_to_blive(ig_order_type: str) -> tuple[OrderType, bool, bool]:
    """Map IG order type string to (blive type, has-limit-price, has-stop-price)."""
    if ig_order_type == "LIMIT":
        return OrderType.LMT, True, False
    if ig_order_type == "STOP":
        return OrderType.STP, False, True
    if ig_order_type == "MARKET":
        return OrderType.MKT, False, False
    # Unrecognised — treat as LIMIT to keep the round-trip safe; tags carry the raw value.
    return OrderType.LMT, True, False


def _ig_tif_to_blive(ig_tif: str) -> TimeInForce:
    """Map IG TIF string to blive `TimeInForce` per [KB-16 §5](../../../../docs/kb/ig_capability_matrix.md#5-time-in-force)."""
    if ig_tif == "GOOD_TILL_CANCELLED":
        return TimeInForce.GTC
    if ig_tif == "EXECUTE_AND_ELIMINATE":
        return TimeInForce.IOC
    if ig_tif == "FILL_OR_KILL":
        return TimeInForce.FOK
    if ig_tif == "GOOD_TILL_DATE":
        return TimeInForce.GTC  # closest analogue; goodTillDate carried in tags
    return TimeInForce.GTC


def _parse_ig_timestamp(s: str) -> datetime:
    """Parse an IG timestamp.

    IG uses two formats interchangeably: ``"YYYY/MM/DD HH:MM:SS"`` (local
    server time, no tz) and ISO-8601 with Z. We return UTC-aware datetimes;
    naive timestamps assumed UTC (caller-side imprecision is acceptable
    since the engine's clock is the authoritative source for live).
    """
    s = s.strip()
    # Try ISO 8601 first.
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    # IG's slash format.
    try:
        return datetime.strptime(s, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"unrecognised IG timestamp: {s!r}") from exc


def _hex_like(s: str) -> bool:
    """True when `s` looks like a hex string we can fold into a UUID."""
    if not s:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


__all__ = [
    "IGBroker",
]
