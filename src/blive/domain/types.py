"""Domain value types.

SSOT is :doc:`../../docs/dd/domain_objects.md` (DD-1). Any change to fields,
invariants, or enum members is a multi-artefact edit per
``CONTEXT_PROTOCOL §3``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Mapping, NewType
from uuid import UUID

# --- Opaque ID aliases -------------------------------------------------------

ClientOrderId = NewType("ClientOrderId", UUID)


# --- Tradability (DD-1 §2.1; ADR-037) ----------------------------------------

# How an instrument is held — discriminates spot ownership from derivative
# wrappers. Forwards to the Sizer's quantize step (integer-share rule for
# "spot" per ADR-027; per-instrument fractional precision for "cfd" / "spread_bet").
Tradability = Literal["spot", "cfd", "spread_bet"]
_TRADABILITY_VALUES: frozenset[str] = frozenset({"spot", "cfd", "spread_bet"})


# --- Enums (DD-1 §1.1) -------------------------------------------------------


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MKT = "MKT"
    LMT = "LMT"
    MOC = "MOC"
    LOC = "LOC"
    STP = "STP"
    STP_LMT = "STP_LMT"
    # IB-specific algorithmic Market order variant routed via IBALGO Adaptive
    # ("smart agency" routing). Bypasses IB's regulatory disruptive-orders
    # price-cap (warning 2161) for volatile / leveraged products on LSEETF
    # and other venues where raw MKT gets auto-converted to a capped LMT —
    # observed at M2-IB.6.2b (2026-05-06) on QQL3, where the raw-MKT cap
    # bound structurally even at a 60-second event-wait. Strategies opt in
    # per-instrument; not a default. Adapter-side (IBBroker) sets
    # ``algoStrategy="Adaptive"`` + ``algoParams=[("adaptivePriority","Normal")]``
    # on the underlying ib_async.MarketOrder. Other adapters that do not
    # support algorithmic order routing (paper, mock, or future brokers
    # without an equivalent) raise on submit per the registry contract.
    ADAPTIVE_MKT = "ADAPTIVE_MKT"


class TimeInForce(StrEnum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    OPG = "OPG"


class OrderState(StrEnum):
    INITIALIZED = "INITIALIZED"
    SUBMIT_PENDING = "SUBMIT_PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


TERMINAL_ORDER_STATES: frozenset[OrderState] = frozenset(
    {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED, OrderState.EXPIRED}
)


class OrderEventKind(StrEnum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    FX = "FX"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# --- Validators --------------------------------------------------------------


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC, got {value!r}")


def _require_iso_currency(value: str, field_name: str) -> None:
    if not (len(value) == 3 and value.isascii() and value.isupper() and value.isalpha()):
        raise ValueError(f"{field_name} must be a 3-letter uppercase ISO 4217 code, got {value!r}")


# --- Instrument (DD-1 §2.1) --------------------------------------------------


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    venue: str
    currency: str
    asset_class: AssetClass
    multiplier: Decimal = Decimal("1")
    tradability: Tradability = "spot"

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.strip() or " " in self.symbol:
            raise ValueError(
                f"Instrument.symbol must be non-empty and whitespace-free, got {self.symbol!r}"
            )
        if not self.venue or not self.venue.isupper():
            raise ValueError(f"Instrument.venue must be uppercase non-empty, got {self.venue!r}")
        _require_iso_currency(self.currency, "Instrument.currency")
        if self.multiplier <= 0:
            raise ValueError(f"Instrument.multiplier must be positive, got {self.multiplier!r}")
        if self.tradability not in _TRADABILITY_VALUES:
            raise ValueError(
                f"Instrument.tradability must be one of {sorted(_TRADABILITY_VALUES)}, "
                f"got {self.tradability!r}"
            )


# --- Bar (DD-1 §2.2) ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Bar:
    instrument: Instrument
    open_time_utc: datetime
    close_time_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None = None

    def __post_init__(self) -> None:
        _require_utc(self.open_time_utc, "Bar.open_time_utc")
        _require_utc(self.close_time_utc, "Bar.close_time_utc")
        if self.close_time_utc <= self.open_time_utc:
            raise ValueError("Bar.close_time_utc must be > open_time_utc")
        if self.open <= 0 or self.close <= 0:
            raise ValueError("Bar prices must be strictly positive")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("Bar OHLC ordering invariant violated (low ≤ open/close ≤ high)")
        if self.volume < 0:
            raise ValueError("Bar.volume must be non-negative")
        if self.vwap is not None and not (self.low <= self.vwap <= self.high):
            raise ValueError("Bar.vwap, when set, must lie in [low, high]")


# --- Trade (DD-1 §2.3) -------------------------------------------------------


TradeAggressor = Literal["BUY", "SELL", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class Trade:
    instrument: Instrument
    time_utc: datetime
    price: Decimal
    quantity: Decimal
    aggressor: TradeAggressor

    def __post_init__(self) -> None:
        _require_utc(self.time_utc, "Trade.time_utc")
        if self.price <= 0 or self.quantity <= 0:
            raise ValueError("Trade.price and quantity must be strictly positive")
        if self.aggressor not in ("BUY", "SELL", "UNKNOWN"):
            raise ValueError(f"Trade.aggressor must be BUY/SELL/UNKNOWN, got {self.aggressor!r}")


# --- Order (DD-1 §2.4) -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Order:
    client_order_id: UUID
    strategy_id: str
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    time_in_force: TimeInForce
    limit_price: Decimal | None
    stop_price: Decimal | None
    parent_id: UUID | None
    tags: Mapping[str, str]
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("Order.strategy_id must be non-empty")
        if self.quantity <= 0:
            raise ValueError("Order.quantity must be strictly positive")
        # limit_price discipline
        needs_limit = self.order_type in (OrderType.LMT, OrderType.STP_LMT)
        if needs_limit and (self.limit_price is None or self.limit_price <= 0):
            raise ValueError(
                f"Order.limit_price required and positive for order_type={self.order_type}"
            )
        if not needs_limit and self.limit_price is not None:
            raise ValueError(f"Order.limit_price must be None for order_type={self.order_type}")
        # stop_price discipline
        needs_stop = self.order_type in (OrderType.STP, OrderType.STP_LMT)
        if needs_stop and (self.stop_price is None or self.stop_price <= 0):
            raise ValueError(
                f"Order.stop_price required and positive for order_type={self.order_type}"
            )
        if not needs_stop and self.stop_price is not None:
            raise ValueError(f"Order.stop_price must be None for order_type={self.order_type}")
        _require_utc(self.created_at, "Order.created_at")
        for k in self.tags:
            if not k:
                raise ValueError("Order.tags keys must be non-empty")


# --- Fill (DD-1 §2.5) --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Fill:
    client_order_id: UUID
    venue_order_id: str
    venue_exec_id: str
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    price: Decimal
    commission: Decimal
    currency: str
    time_utc: datetime

    def __post_init__(self) -> None:
        if not self.venue_exec_id:
            raise ValueError("Fill.venue_exec_id must be non-empty (idempotency key)")
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("Fill.quantity and price must be strictly positive")
        if self.commission < 0:
            raise ValueError("Fill.commission must be non-negative")
        _require_iso_currency(self.currency, "Fill.currency")
        _require_utc(self.time_utc, "Fill.time_utc")


# --- Position (DD-1 §2.7) ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Position:
    instrument: Instrument
    strategy_id: str
    quantity: Decimal
    avg_cost: Decimal
    currency: str
    opened_at: datetime | None
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("Position.strategy_id must be non-empty")
        _require_iso_currency(self.currency, "Position.currency")
        if self.currency != self.instrument.currency:
            raise ValueError(
                f"Position.currency ({self.currency!r}) must match instrument.currency "
                f"({self.instrument.currency!r})"
            )
        if self.quantity == 0:
            if self.opened_at is not None:
                raise ValueError("Position.opened_at must be None when quantity == 0")
        else:
            if self.opened_at is None:
                raise ValueError("Position.opened_at required when quantity != 0")
            _require_utc(self.opened_at, "Position.opened_at")
            if self.avg_cost <= 0:
                raise ValueError("Position.avg_cost must be positive when quantity != 0")
        _require_utc(self.updated_at, "Position.updated_at")


# --- AccountSnapshot (DD-1 §2.8) --------------------------------------------


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    equity: Decimal
    cash_by_ccy: Mapping[str, Decimal]
    buying_power: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    leverage: Decimal
    margin_used: Decimal
    base_currency: str
    taken_at: datetime

    def __post_init__(self) -> None:
        _require_iso_currency(self.base_currency, "AccountSnapshot.base_currency")
        for ccy in self.cash_by_ccy:
            _require_iso_currency(ccy, "AccountSnapshot.cash_by_ccy key")
        for v, name in (
            (self.buying_power, "buying_power"),
            (self.gross_exposure, "gross_exposure"),
            (self.margin_used, "margin_used"),
            (self.leverage, "leverage"),
        ):
            if v < 0:
                raise ValueError(f"AccountSnapshot.{name} must be non-negative, got {v!r}")
        _require_utc(self.taken_at, "AccountSnapshot.taken_at")


# --- OrderUpdate (DD-1 §2.9) -------------------------------------------------


@dataclass(frozen=True, slots=True)
class OrderUpdate:
    quantity: Decimal | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None

    def __post_init__(self) -> None:
        if all(v is None for v in (self.quantity, self.limit_price, self.stop_price)):
            raise ValueError("OrderUpdate must change at least one field")
        for v, name in (
            (self.quantity, "quantity"),
            (self.limit_price, "limit_price"),
            (self.stop_price, "stop_price"),
        ):
            if v is not None and v <= 0:
                raise ValueError(f"OrderUpdate.{name}, when set, must be strictly positive")


# --- BarFreq alias (used by MarketDataPort signatures) -----------------------

BarFreq = Literal["1m", "5m", "15m", "1h", "1d"]


__all__ = [
    # Aliases
    "ClientOrderId",
    "BarFreq",
    "Tradability",
    "TradeAggressor",
    "TERMINAL_ORDER_STATES",
    # Enums
    "OrderSide",
    "OrderType",
    "TimeInForce",
    "OrderState",
    "OrderEventKind",
    "AssetClass",
    "Severity",
    # Value types
    "Instrument",
    "Bar",
    "Trade",
    "Order",
    "Fill",
    "Position",
    "AccountSnapshot",
    "OrderUpdate",
]
