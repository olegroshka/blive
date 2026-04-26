"""Position arithmetic — pure functions over :class:`Position` and :class:`Fill`.

Lives in the domain layer because the rules are broker-neutral. Adapters
do not call this; the engine (or a test) does, after observing a fill
event from the BrokerPort.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from blive.domain.types import Fill, OrderSide, Position


def apply_fill(
    position: Position | None,
    fill: Fill,
    *,
    strategy_id: str,
    now: datetime,
) -> Position:
    """Return the new :class:`Position` after applying ``fill``.

    Pure function. Handles five cases:

    1. **flat → open**: ``position is None`` or ``position.quantity == 0``.
    2. **same-side add**: weighted-average avg_cost.
    3. **partial close** (opposite side, smaller magnitude): avg_cost preserved.
    4. **full close** (opposite side, exactly cancelling): quantity → 0, avg_cost → 0, opened_at → None.
    5. **flip** (opposite side, larger magnitude): treated as close + open at fill price.
    """
    signed_qty = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity

    if position is None or position.quantity == 0:
        return Position(
            instrument=fill.instrument,
            strategy_id=strategy_id,
            quantity=signed_qty,
            avg_cost=fill.price,
            currency=fill.instrument.currency,
            opened_at=fill.time_utc,
            updated_at=now,
        )

    if position.strategy_id != strategy_id:
        raise ValueError(
            f"strategy_id mismatch: position has {position.strategy_id!r}, "
            f"caller provided {strategy_id!r}"
        )
    if position.instrument != fill.instrument:
        raise ValueError(
            f"instrument mismatch: position has {position.instrument}, "
            f"fill has {fill.instrument}"
        )

    same_side = (position.quantity > 0 and signed_qty > 0) or (
        position.quantity < 0 and signed_qty < 0
    )
    new_qty = position.quantity + signed_qty

    if same_side:
        # Weighted-average. Both terms have the same sign so the result is signed
        # consistently with new_qty; we take abs to get the (always-positive) avg_cost.
        notional_existing = position.quantity * position.avg_cost
        notional_added = signed_qty * fill.price
        new_avg = (notional_existing + notional_added) / new_qty
        return Position(
            instrument=position.instrument,
            strategy_id=position.strategy_id,
            quantity=new_qty,
            avg_cost=abs(new_avg),
            currency=position.currency,
            opened_at=position.opened_at,
            updated_at=now,
        )

    if new_qty == 0:
        return Position(
            instrument=position.instrument,
            strategy_id=position.strategy_id,
            quantity=Decimal("0"),
            avg_cost=Decimal("0"),
            currency=position.currency,
            opened_at=None,
            updated_at=now,
        )

    if (position.quantity > 0) != (new_qty > 0):
        # Flip: realise prior leg, open new at fill price.
        return Position(
            instrument=position.instrument,
            strategy_id=position.strategy_id,
            quantity=new_qty,
            avg_cost=fill.price,
            currency=position.currency,
            opened_at=fill.time_utc,
            updated_at=now,
        )

    # Partial close (same direction, smaller magnitude). avg_cost preserved.
    return Position(
        instrument=position.instrument,
        strategy_id=position.strategy_id,
        quantity=new_qty,
        avg_cost=position.avg_cost,
        currency=position.currency,
        opened_at=position.opened_at,
        updated_at=now,
    )


__all__ = ["apply_fill"]
