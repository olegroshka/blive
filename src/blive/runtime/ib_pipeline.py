"""IB-mode end-to-end pipeline.

Sibling of :mod:`blive.runtime.paper_pipeline` for the M2-IB.5 strategy
run: the rebalance-loop machinery is the same shape (factor → signal →
portfolio → sizer → risk → broker), but the broker is :class:`blive.adapters.ib.broker.IBBroker`
talking to IB Paper, and the data feed is :class:`blive.adapters.paper.market_data.PaperMarketData`
backed by an EODHD parquet (per [ADR-017](../../../docs/decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing)
hybrid routing — data from EODHD, execution on IB).

Decoupled from the signal source: the caller passes a pre-computed
``position_series`` (a pandas Series indexed by bar close timestamps,
values in ``{0, 1}`` for the M2-IB.5 single-leg long/flat case). The
TKAN stub for end-to-end paper testing (M2-IB.5 prereq #3) and any
future btest interpreter (per [OQ-030](../../../docs/decisions/OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes)
/ [ADR-030](../../../docs/decisions/DECISIONS.md#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010))
both produce a ``position_series`` matching this shape.

Compared to ``run_paper_pipeline``:

- **Broker is injected** (caller constructs and connects). The pipeline
  uses :class:`blive.adapters.ib.broker.IBBroker` directly only for the
  IB-specific event drain (``IBBroker._events`` queue access matches the
  pattern from ``scripts/probe_ib_submit.py``); switching to a different
  ``BrokerPort`` impl is a small refactor when the third-broker case
  arrives.
- **No price_lookup injection** — the broker fills at the venue's real
  market, so the pipeline doesn't simulate fills. The ``Fill.price`` and
  ``Fill.commission`` from the broker drive the local cash ledger.
- **No btest integration in this module.** The position_series is the
  signal contract.
- **Order type defaults to LMT** at the bar's close price ± a small
  aggressive offset — for paper testing, this exercises the full FSM
  (SUBMITTED → ACCEPTED → CANCELED if the order doesn't fill, or →
  FILLED if it crosses). MARKET orders are also supported; choose via
  ``order_type``.

Out of scope (M5+ work): real-time live mode (waiting for the next
session close); reconciliation drift; intraday tick handling;
multi-instrument rebalances.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from blive.adapters.alert.log import LogAlert
from blive.adapters.ib.broker import IBBroker
from blive.adapters.paper.market_data import PaperMarketData
from blive.domain.events import OrderEvent
from blive.domain.positions import apply_fill
from blive.domain.types import (
    TERMINAL_ORDER_STATES,
    Bar,
    ClientOrderId,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderState,
    OrderType,
    Position,
    TimeInForce,
)
from blive.risk import (
    BREACH_TOPIC,
    KillSwitch,
    RiskBreach,
    RiskEngine,
    RiskEngineConfig,
    RiskInputs,
)
from blive.sizing import SizerInput, size_orders
from blive.strategy.loader import LiveStrategy

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IBEquityPoint:
    """One row of the equity curve at a rebalance close."""

    time_utc: datetime
    cash: Decimal
    position_qty: Decimal
    mark_price: Decimal
    equity: Decimal


@dataclass
class IBRunResult:
    """Outcome of an IB-paper run."""

    equity_curve: list[IBEquityPoint] = field(default_factory=list)
    breaches: list[RiskBreach] = field(default_factory=list)
    fills_count: int = 0
    submitted_count: int = 0
    canceled_count: int = 0
    rejected_count: int = 0
    final_equity: Decimal = Decimal("0")


# --- Public entry point ------------------------------------------------------


async def run_ib_pipeline(
    *,
    live_strategy: LiveStrategy,
    broker: IBBroker,
    market_data: PaperMarketData,
    instrument: Instrument,
    position_series: pd.Series,
    starting_cash: Decimal = Decimal("1000000"),
    base_currency: str = "EUR",
    target_leverage: Decimal = Decimal("1"),
    order_type: OrderType = OrderType.LMT,
    limit_price_offset_bps: Decimal = Decimal("50"),
    event_wait_seconds: float = 10.0,
    kill_switch: KillSwitch | None = None,
) -> IBRunResult:
    """Run the M2-IB.5 IB-paper pipeline end-to-end against IB Paper.

    The caller must:

    1. Construct an :class:`IBBroker` and call :meth:`IBBroker.connect`.
    2. Provide a :class:`PaperMarketData` whose fixture covers
       ``position_series.index``.
    3. Provide ``position_series`` aligned with the market_data bars'
       close timestamps; values in ``{0, 1}``.

    The pipeline:

    1. Walks the historical bars in ``market_data.bars(instrument)``.
    2. For each bar whose timestamp is in ``position_series.index``,
       computes ``target_weight = position * target_leverage``.
    3. Sizes via :func:`blive.sizing.size_orders`, runs each candidate
       through the M1 :class:`blive.risk.RiskEngine` subset (RC-08 /
       RC-09 / RC-12 / RC-13), submits approved orders to IB.
    4. Drains the broker's event queue until the order reaches a
       terminal state (FILLED / CANCELED / REJECTED / EXPIRED), then
       cancels any non-terminal orders before moving to the next bar.
    5. Updates a local cash + position view from observed fills (the
       broker remains authoritative on its own ``account_snapshot``;
       this local view is the per-strategy attribution view).

    Returns an :class:`IBRunResult` summarising the run; the broker
    stays connected on return (caller manages disconnect).
    """
    if not broker.is_connected:
        raise RuntimeError("run_ib_pipeline expects an already-connected IBBroker")

    bars = market_data.bars(instrument)
    if not bars:
        raise ValueError(f"no bars in fixture for {instrument}")

    risk_engine = RiskEngine(
        config=_risk_config_from_live(live_strategy),
        kill_switch=kill_switch if kill_switch is not None else KillSwitch(),
        strategy_id=live_strategy.live_config.strategy_id,
    )
    alert = LogAlert()

    # Drain any startup events (ConnectionStatus, initial AccountUpdate)
    # off the broker's queue before the loop begins.
    await _drain_startup_events(broker)

    instrument_key = instrument.symbol
    cash = starting_cash
    positions: dict[str, Position] = {}
    result = IBRunResult()

    for bar in bars:
        t = bar.close_time_utc
        ts_key = pd.Timestamp(t)
        if ts_key not in position_series.index:
            continue

        position_int = int(position_series.loc[ts_key])
        target_weight = Decimal(position_int) * target_leverage

        def _resolve_instrument(_key: str, _i: Instrument = instrument) -> Instrument:
            return _i

        def _price_lookup(_inst: Instrument, _p: Decimal = bar.close) -> Decimal:
            return _p

        sizer_in = SizerInput(
            target_weights={instrument_key: target_weight},
            equity=_compute_equity(cash, positions, bar.close),
            nav_slice=live_strategy.live_config.nav_slice,
            current_positions=positions,
            instrument_resolver=_resolve_instrument,
            price_lookup=_price_lookup,
            strategy_id=live_strategy.live_config.strategy_id,
            now=t,
        )
        candidate_orders = size_orders(sizer_in)

        for desired in candidate_orders:
            risk_inputs = RiskInputs(
                last_bar=bar,
                is_market_open=True,  # paper-test runs against historical bars
                artefact_paths=dict(live_strategy.live_config.artefact_paths.paths),
            )
            approved, breaches = risk_engine.approve(desired, inputs=risk_inputs, now=t)
            if breaches:
                result.breaches.extend(breaches)
                for b in breaches:
                    await alert.send(
                        b.alert_severity(),
                        f"{BREACH_TOPIC}/{b.check.value}",
                        b.detail,
                    )
            if approved is None:
                continue

            # Promote to LMT at the bar's close (± offset) so IB Paper has
            # a price to work with; MARKET orders for a daily-frequency
            # paper test would fill at unrelated current-market prices.
            order_for_ib = _ib_order_from_desired(
                desired=approved,
                bar=bar,
                order_type=order_type,
                limit_price_offset_bps=limit_price_offset_bps,
            )

            await broker.submit(order_for_ib)
            result.submitted_count += 1
            terminal_state, fill_event = await _drain_order_lifecycle(
                broker=broker,
                target_id=ClientOrderId(order_for_ib.client_order_id),
                timeout_s=event_wait_seconds,
            )

            if (
                terminal_state == OrderState.FILLED
                and fill_event is not None
                and fill_event.fill is not None
            ):
                fill = fill_event.fill
                prior = positions.get(instrument_key)
                positions[instrument_key] = apply_fill(
                    prior,
                    fill,
                    strategy_id=live_strategy.live_config.strategy_id,
                    now=t,
                )
                signed = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
                cash -= signed * fill.price + fill.commission
                result.fills_count += 1
            elif terminal_state == OrderState.CANCELED:
                result.canceled_count += 1
            elif terminal_state == OrderState.REJECTED:
                result.rejected_count += 1
            else:
                # Non-terminal after timeout — engine-cancel before moving on.
                try:
                    await broker.cancel(ClientOrderId(order_for_ib.client_order_id))
                except KeyError:
                    pass
                # Drain any final event after the cancel; ignore outcome.
                await _drain_order_lifecycle(
                    broker=broker,
                    target_id=ClientOrderId(order_for_ib.client_order_id),
                    timeout_s=event_wait_seconds,
                )
                result.canceled_count += 1

        equity = _compute_equity(cash, positions, bar.close)
        qty = positions[instrument_key].quantity if instrument_key in positions else Decimal("0")
        result.equity_curve.append(
            IBEquityPoint(
                time_utc=t,
                cash=cash,
                position_qty=qty,
                mark_price=bar.close,
                equity=equity,
            )
        )

    result.final_equity = result.equity_curve[-1].equity if result.equity_curve else starting_cash
    return result


# --- Helpers -----------------------------------------------------------------


def _ib_order_from_desired(
    *,
    desired: Order,
    bar: Bar,
    order_type: OrderType,
    limit_price_offset_bps: Decimal,
) -> Order:
    """Build the order to send to IB.

    For MARKET, return ``desired`` with ``order_type=MKT`` and no price.
    For LIMIT, set the limit at the bar's close ± an aggressive offset
    (BUY: close * (1 + bps/10000); SELL: close * (1 - bps/10000)) so
    crossing orders are likely to fill in normal venue conditions while
    away-of-market ones exercise the SUBMITTED → ACCEPTED → CANCELED
    path on the engine's bar-end cancel.
    """
    base = desired
    if order_type == OrderType.MKT:
        return Order(
            client_order_id=ClientOrderId(uuid4()),
            strategy_id=base.strategy_id,
            instrument=base.instrument,
            side=base.side,
            quantity=base.quantity,
            order_type=OrderType.MKT,
            time_in_force=base.time_in_force,
            limit_price=None,
            stop_price=None,
            parent_id=None,
            tags={**base.tags, "pipeline": "m2-ib.5"},
            created_at=base.created_at,
        )
    if order_type == OrderType.LMT:
        scale = limit_price_offset_bps / Decimal("10000")
        if base.side == OrderSide.BUY:
            limit_price = bar.close * (Decimal("1") + scale)
        else:
            limit_price = bar.close * (Decimal("1") - scale)
        return Order(
            client_order_id=ClientOrderId(uuid4()),
            strategy_id=base.strategy_id,
            instrument=base.instrument,
            side=base.side,
            quantity=base.quantity,
            order_type=OrderType.LMT,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price.quantize(Decimal("0.01")),
            stop_price=None,
            parent_id=None,
            tags={**base.tags, "pipeline": "m2-ib.5"},
            created_at=base.created_at,
        )
    raise ValueError(f"run_ib_pipeline supports MKT or LMT order_type only; got {order_type!r}")


async def _drain_startup_events(broker: IBBroker) -> None:
    """Pull any ConnectionStatus / AccountUpdate sitting in the queue at
    pipeline entry. We don't want them to confuse per-order drain loops."""
    queue = broker._events  # noqa: SLF001 — pipeline-internal access
    drained = 0
    while not queue.empty():
        await queue.get()
        drained += 1
    if drained:
        log.debug("drained %d startup event(s) from broker queue", drained)


async def _drain_order_lifecycle(
    *,
    broker: IBBroker,
    target_id: ClientOrderId,
    timeout_s: float,
) -> tuple[OrderState, OrderEvent | None]:
    """Pull events from the broker until ``target_id`` reaches a terminal state.

    Returns the final state plus the (optional) fill-bearing event that
    decided it. On timeout (terminal not reached within ``timeout_s``),
    returns the latest non-terminal state seen — the caller decides
    whether to cancel.

    Reads :attr:`IBBroker._events` directly to avoid the async-generator
    cancellation hazard documented in ``scripts/probe_ib_submit.py``.
    """
    queue = broker._events  # noqa: SLF001 — pipeline-internal access
    fill_event: OrderEvent | None = None
    state = OrderState.SUBMIT_PENDING
    deadline = asyncio.get_event_loop().time() + timeout_s

    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return state, fill_event
        try:
            event = await asyncio.wait_for(queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            return state, fill_event
        if not isinstance(event, OrderEvent):
            continue
        if event.client_order_id != target_id:
            continue
        if event.kind == OrderEventKind.SUBMITTED:
            state = OrderState.SUBMITTED
        elif event.kind == OrderEventKind.ACCEPTED:
            state = OrderState.ACCEPTED
        elif event.kind == OrderEventKind.PARTIAL_FILL:
            state = OrderState.PARTIALLY_FILLED
            fill_event = event
        elif event.kind == OrderEventKind.FILLED:
            state = OrderState.FILLED
            fill_event = event
            break
        elif event.kind == OrderEventKind.CANCELED:
            state = OrderState.CANCELED
            break
        elif event.kind == OrderEventKind.REJECTED:
            state = OrderState.REJECTED
            break
        elif event.kind == OrderEventKind.EXPIRED:
            state = OrderState.EXPIRED
            break

    assert state in TERMINAL_ORDER_STATES
    return state, fill_event


def _risk_config_from_live(live: LiveStrategy) -> RiskEngineConfig:
    """Translate ``LiveStrategyConfig.risk_overrides`` into ``RiskEngineConfig``.

    Daily-frequency Phase 1 → ``is_intraday=False``. M5+ widening adds
    intraday awareness when the engine grows real-time clock support.
    """
    overrides = live.live_config.risk_overrides
    return RiskEngineConfig(
        max_data_staleness_intraday_sec=overrides.max_data_staleness_intraday_sec,
        max_data_staleness_daily_sec=overrides.max_data_staleness_daily_sec,
        outside_rth_allowed=overrides.outside_rth_allowed,
        max_model_artefact_age_days=overrides.max_model_artefact_age_days,
        model_artefact_warning_age_days=overrides.model_artefact_warning_age_days,
        is_intraday=False,
    )


def _compute_equity(
    cash: Decimal,
    positions: dict[str, Position],
    mark_price: Decimal,
) -> Decimal:
    notional = sum(
        (p.quantity * mark_price for p in positions.values()),
        start=Decimal("0"),
    )
    return cash + notional


__all__ = ["IBEquityPoint", "IBRunResult", "run_ib_pipeline"]
