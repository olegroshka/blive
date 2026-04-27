"""Pure-function Sizer.

Converts ``target_weights`` (per-instrument fractions in ``[-1, 1]``) into
``Order`` objects, deltas-against-current-positions, applying the rounding
policy from :doc:`../../docs/decisions/DECISIONS.md` (ADR-027 — integer
shares, truncate toward zero).

The Sizer is **pure**: no I/O, no clocks beyond what's passed in, no global
state. Tests cover every rounding boundary and the explicit "exit ⇒ flatten
exactly current quantity" invariant from ADR-027.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Callable, Mapping
from uuid import uuid4

from blive.domain.types import (
    Instrument,
    Order,
    OrderSide,
    OrderType,
    Position,
    TimeInForce,
)


@dataclass(frozen=True, slots=True)
class SizerInput:
    """Bundle of inputs for one Sizer invocation."""

    target_weights: Mapping[str, Decimal]  # instrument_key → weight in [-1, 1]
    equity: Decimal  # total account NAV
    nav_slice: Decimal  # 0 < nav_slice ≤ 0.10 per ADR-020
    current_positions: Mapping[str, Position]  # keyed by instrument_key
    instrument_resolver: Callable[[str], Instrument]
    price_lookup: Callable[[Instrument], Decimal]
    strategy_id: str
    now: datetime


def quantize_share_qty(raw: Decimal, *, precision: Decimal = Decimal("1")) -> Decimal:
    """Quantize a desired share quantity per ADR-027.

    Truncate toward zero at the requested precision (default integer).
    Negative inputs round upward (toward zero) so the magnitude shrinks
    rather than grows.
    """
    if precision <= 0:
        raise ValueError(f"precision must be positive, got {precision}")
    if raw == 0:
        return Decimal("0")
    if raw > 0:
        return raw.quantize(precision, rounding=ROUND_DOWN)
    # Negative path: ROUND_DOWN takes |x| toward zero, so -1.7 → -1 not -2.
    return (-((-raw).quantize(precision, rounding=ROUND_DOWN))).quantize(precision)


def size_orders(inp: SizerInput) -> list[Order]:
    """Compute the list of ``Order``s that move the strategy to ``target_weights``.

    For each instrument key in ``target_weights``:

    1. ``effective_capital = equity * nav_slice``.
    2. ``desired_signed_qty = (effective_capital * target_weight) / price``.
    3. ``current_qty = current_positions[key].quantity if present else 0``.
    4. **ADR-027 exit-flatten rule**: if ``target_weight == 0``, set
       ``desired_signed_qty := 0`` (exact, not rounded), so the resulting
       delta closes the entire current position — no leftover one-share drift.
    5. ``delta = quantize_share_qty(desired_signed_qty - current_qty)``.
    6. If ``abs(delta) >= 1``, emit one ``Order`` with side from ``sign(delta)``
       and ``quantity = abs(delta)``.

    Returns the list of orders to submit (possibly empty).
    """
    if inp.nav_slice <= 0:
        raise ValueError(f"nav_slice must be > 0, got {inp.nav_slice}")
    if inp.equity <= 0:
        raise ValueError(f"equity must be > 0, got {inp.equity}")

    effective_capital = inp.equity * inp.nav_slice
    orders: list[Order] = []

    for key, target_weight in inp.target_weights.items():
        if not (Decimal("-1") <= target_weight <= Decimal("1")):
            raise ValueError(f"target_weight for {key!r} must be in [-1, 1], got {target_weight}")

        instrument = inp.instrument_resolver(key)
        price = inp.price_lookup(instrument)
        if price <= 0:
            raise ValueError(f"price for {instrument} must be > 0, got {price}")

        # ADR-027 exit-flatten rule.
        if target_weight == 0:
            desired_signed_qty = Decimal("0")
        else:
            desired_signed_qty = (effective_capital * target_weight) / price

        current_qty = (
            inp.current_positions[key].quantity if key in inp.current_positions else Decimal("0")
        )

        delta = desired_signed_qty - current_qty
        rounded = quantize_share_qty(delta)

        if rounded == 0:
            continue

        side = OrderSide.BUY if rounded > 0 else OrderSide.SELL
        quantity = abs(rounded)
        orders.append(
            Order(
                client_order_id=uuid4(),
                strategy_id=inp.strategy_id,
                instrument=instrument,
                side=side,
                quantity=quantity,
                order_type=OrderType.MKT,
                time_in_force=TimeInForce.DAY,
                limit_price=None,
                stop_price=None,
                parent_id=None,
                tags={"rebalance_at": inp.now.isoformat()},
                created_at=inp.now,
            )
        )

    return orders


__all__ = ["SizerInput", "size_orders", "quantize_share_qty"]
