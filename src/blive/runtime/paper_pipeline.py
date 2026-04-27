"""Paper-mode end-to-end pipeline.

Composes the M1 deliverables:

1. ``LiveStrategy`` from :mod:`blive.strategy.loader`.
2. btest interpreter for ``TimingPortfolio`` strategies — the per-OQ-030
   dispatch chooses :class:`quantdsl_backtest.runners.single_asset.SingleAssetRunner`.
3. :func:`blive.sizing.size_orders` for the per-rebalance order computation.
4. :class:`blive.risk.RiskEngine` (M1 subset RC-08/RC-09/RC-12/RC-13).
5. :class:`blive.adapters.paper.broker.PaperBroker` for simulated fills.
6. :class:`blive.adapters.paper.market_data.PaperMarketData` for the bar tape.

The pipeline is asynchronous because the broker emits events on an
asyncio queue; the public entry point is the ``async`` function
:func:`run_paper_pipeline`.

Out of M1 scope: cancel-replace flows, partial fills, slippage modelling,
multi-instrument rebalances, intraday tick handling.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Sequence

import pandas as pd

# btest reuse per ADR-010 + OQ-030 dispatch.
from quantdsl_backtest.dsl.portfolio import TimingPortfolio
from quantdsl_backtest.runners.single_asset import SingleAssetRunner

from blive.adapters.alert.log import LogAlert
from blive.adapters.clock.sim import SimClock
from blive.adapters.paper.broker import PaperBroker
from blive.adapters.paper.market_data import PaperMarketData
from blive.domain.events import ConnectionStatus, OrderEvent
from blive.domain.positions import apply_fill
from blive.domain.types import (
    TERMINAL_ORDER_STATES,
    Bar,
    Instrument,
    OrderEventKind,
    OrderState,
    Position,
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
class EquityPoint:
    """One row of the equity curve at a rebalance close."""

    time_utc: datetime
    cash: Decimal
    position_qty: Decimal
    mark_price: Decimal
    equity: Decimal


@dataclass
class PaperRunResult:
    """Outcome of a paper run."""

    equity_curve: list[EquityPoint] = field(default_factory=list)
    breaches: list[RiskBreach] = field(default_factory=list)
    fills_count: int = 0
    final_equity: Decimal = Decimal("0")


# --- Public entry point ------------------------------------------------------


async def run_paper_pipeline(
    *,
    live_strategy: LiveStrategy,
    market_data: PaperMarketData,
    instrument: Instrument,
    btest_root: pathlib.Path,
    starting_cash: Decimal = Decimal("1000000"),
    base_currency: str = "EUR",
    commission_per_share: Decimal = Decimal("0"),
    rebalance_close_time: time = time(15, 30, tzinfo=timezone.utc),
    kill_switch: KillSwitch | None = None,
) -> PaperRunResult:
    """Run the M1 paper-mode pipeline end-to-end.

    The strategy is required to use ``TimingPortfolio`` (the only archetype
    M1 supports per the Phase 1 plan in
    :doc:`../../TASK_REGISTRY.md`). Other archetypes raise.
    """
    strategy = live_strategy.strategy
    if not isinstance(strategy.portfolio, TimingPortfolio):
        raise NotImplementedError(
            "M1 paper pipeline only supports TimingPortfolio strategies; "
            f"got {type(strategy.portfolio).__name__}. See OQ-030."
        )

    # 1. Pull the bar tape and run btest's SingleAssetRunner over it.
    bars = market_data.bars(instrument)
    if not bars:
        raise ValueError(f"no bars in fixture for {instrument}")
    price_close = pd.Series(
        data=[float(b.close) for b in bars],
        index=pd.to_datetime([b.close_time_utc for b in bars], utc=True),
        name="close",
    )

    runner = SingleAssetRunner(strategy, btest_root=btest_root)
    btest_result = runner.run(price_close=price_close)
    position_series = btest_result["position"]

    # 2. Build the blive runtime.
    clock = SimClock(start=bars[0].close_time_utc.replace(tzinfo=timezone.utc))
    bar_by_time: dict[datetime, Bar] = {b.close_time_utc: b for b in bars}

    def _price_lookup(_inst: Instrument) -> Decimal:
        # During the rebalance loop we keep ``current_bar`` updated and the
        # broker fills at its close price.
        return _current_price[0]

    _current_price: list[Decimal] = [bars[0].close]

    broker = PaperBroker(
        clock=clock,
        price_lookup=_price_lookup,
        commission_per_share=commission_per_share,
        base_currency=base_currency,
        starting_cash=starting_cash,
    )
    await broker.connect()
    event_iter = broker.events()
    # Drain the initial connect event so it doesn't appear in the loop below.
    first_event = await event_iter.__anext__()
    assert isinstance(first_event, ConnectionStatus) and first_event.connected

    risk_engine = RiskEngine(
        config=_risk_config_from_live(live_strategy),
        kill_switch=kill_switch if kill_switch is not None else KillSwitch(),
        strategy_id=live_strategy.live_config.strategy_id,
    )
    alert = LogAlert()

    # 3. Rebalance loop.
    instrument_key = strategy.portfolio.instrument
    target_leverage = Decimal(str(strategy.portfolio.target_leverage))

    cash = starting_cash
    positions: dict[str, Position] = {}
    result = PaperRunResult()

    for bar in bars:
        # SimClock tracks the rebalance close moment.
        t = bar.close_time_utc
        clock.tick((t - clock.now()).total_seconds())
        _current_price[0] = bar.close

        # Look up btest's signed target (0 or 1 here for TimingPortfolio).
        ts_key = pd.Timestamp(t)
        if ts_key not in position_series.index:
            continue
        position_int = int(position_series.loc[ts_key])
        target_weight = Decimal(position_int) * target_leverage

        # Build the Sizer inputs.
        def _resolve_instrument(_key: str, _i: Instrument = instrument) -> Instrument:
            return _i

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
        orders = size_orders(sizer_in)

        # Submit each order through the RiskEngine first (ADR-008 no-bypass).
        for order in orders:
            risk_inputs = RiskInputs(
                last_bar=bar,
                is_market_open=True,  # M1 tape replay is always RTH-equivalent
                artefact_paths=dict(live_strategy.live_config.artefact_paths.paths),
            )
            approved, breaches = risk_engine.approve(order, inputs=risk_inputs, now=t)
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

            await broker.submit(approved)
            # Drain events for THIS order until terminal.
            terminal_state, fill_event = await _drain_order_lifecycle(
                event_iter, approved.client_order_id
            )
            if fill_event is not None and fill_event.fill is not None:
                fill = fill_event.fill
                prior = positions.get(instrument_key)
                positions[instrument_key] = apply_fill(
                    prior, fill, strategy_id=live_strategy.live_config.strategy_id, now=t
                )
                # Cash ledger update: BUY lowers cash; SELL raises it.
                signed = fill.quantity if fill.side.value == "BUY" else -fill.quantity
                cash -= signed * fill.price + fill.commission
                result.fills_count += 1
            # If terminal_state is REJECTED / CANCELED / EXPIRED we just skip.

        # Mark equity at this bar's close.
        equity = _compute_equity(cash, positions, bar.close)
        qty = positions[instrument_key].quantity if instrument_key in positions else Decimal("0")
        result.equity_curve.append(
            EquityPoint(
                time_utc=t,
                cash=cash,
                position_qty=qty,
                mark_price=bar.close,
                equity=equity,
            )
        )

    await broker.disconnect()
    result.final_equity = result.equity_curve[-1].equity if result.equity_curve else starting_cash
    return result


# --- Helpers -----------------------------------------------------------------


def _risk_config_from_live(live: LiveStrategy) -> RiskEngineConfig:
    """Translate ``LiveStrategyConfig.risk_overrides`` into ``RiskEngineConfig``."""
    overrides = live.live_config.risk_overrides
    # M1 tape replay is daily (F0); ``is_intraday`` False means the daily
    # staleness threshold applies.
    is_intraday = False
    return RiskEngineConfig(
        max_data_staleness_intraday_sec=overrides.max_data_staleness_intraday_sec,
        max_data_staleness_daily_sec=overrides.max_data_staleness_daily_sec,
        outside_rth_allowed=overrides.outside_rth_allowed,
        max_model_artefact_age_days=overrides.max_model_artefact_age_days,
        model_artefact_warning_age_days=overrides.model_artefact_warning_age_days,
        is_intraday=is_intraday,
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


async def _drain_order_lifecycle(
    events: object,
    target_id: object,
) -> tuple[OrderState, OrderEvent | None]:
    """Pull events from the broker until ``target_id`` reaches a terminal state.

    Returns the final state plus the (optional) fill-bearing event that
    decided it.
    """
    fill_event: OrderEvent | None = None
    state = OrderState.SUBMIT_PENDING

    # The PaperBroker lifecycle task may not have scheduled yet; the first
    # await yields control so it can run.
    await asyncio.sleep(0)
    while True:
        event = await events.__anext__()  # type: ignore[attr-defined]
        if isinstance(event, ConnectionStatus):
            continue
        if not isinstance(event, OrderEvent):
            continue
        if event.client_order_id != target_id:
            # Multi-order events from another submission would land here in a
            # multi-instrument pipeline; M1 is single-instrument so this is
            # paranoia rather than necessity.
            continue
        if event.kind == OrderEventKind.SUBMITTED:
            state = OrderState.SUBMITTED
        elif event.kind == OrderEventKind.ACCEPTED:
            state = OrderState.ACCEPTED
        elif event.kind == OrderEventKind.PARTIAL_FILL:
            state = OrderState.PARTIALLY_FILLED
            # M1 PaperBroker fires only one fill per MKT order; keep the last
            # observed fill so the caller sees it as the FILLED payload below.
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


__all__ = ["EquityPoint", "PaperRunResult", "run_paper_pipeline"]
