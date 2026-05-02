"""IB-mode pipeline tests.

Covers the M2-IB.5 prereq #2 deliverable (broker-agnostic pipeline at
``src/blive/runtime/ib_pipeline.py``). The wire-level validation of the
underlying IBBroker happy + REJECTED-disambiguation paths is in
``test_broker.py`` + the ``probe_ib_submit.py`` wire probe; this file
tests the pipeline orchestration above the broker.

Mocking strategy: a small ``_FakeIBBroker`` class implements the surface
``run_ib_pipeline`` consumes (``is_connected``, ``submit``, ``cancel``,
``_events`` queue). The fake's submit() enqueues a configurable event
sequence so we can drive happy / cancel / reject paths without touching
real IB.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd
import pytest

from blive.adapters.paper.market_data import PaperMarketData
from blive.domain.events import OrderEvent
from blive.domain.ports import BrokerEvent
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Fill,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
)
from blive.risk import KillSwitch
from blive.runtime.ib_pipeline import IBRunResult, run_ib_pipeline
from blive.strategy.config import (
    ArtefactPaths,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)
from blive.strategy.loader import LiveStrategy

# --- Fake IBBroker -----------------------------------------------------------


@dataclass
class _FakeIBBroker:
    """Minimal fake matching the IBBroker surface that run_ib_pipeline uses."""

    is_connected: bool = True
    submitted_orders: list[Order] = None  # type: ignore[assignment]
    canceled_ids: list[ClientOrderId] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._events: asyncio.Queue[BrokerEvent] = asyncio.Queue()
        self.submitted_orders = []
        self.canceled_ids = []
        self._on_submit: Callable[[Order], list[OrderEvent]] = self._default_on_submit
        self._on_cancel: Callable[[ClientOrderId], list[OrderEvent]] = self._default_on_cancel

    def configure_submit(self, fn: Callable[[Order], list[OrderEvent]]) -> None:
        self._on_submit = fn

    def configure_cancel(self, fn: Callable[[ClientOrderId], list[OrderEvent]]) -> None:
        self._on_cancel = fn

    @staticmethod
    def _default_on_submit(order: Order) -> list[OrderEvent]:
        # Default: SUBMITTED → ACCEPTED → FILLED at the order's reference price
        # for the full quantity, no commission.
        cid = ClientOrderId(order.client_order_id)
        ref_price = order.limit_price if order.limit_price is not None else Decimal("100")
        fill = Fill(
            client_order_id=cid,
            venue_order_id="42",
            venue_exec_id=str(uuid4()),
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            price=ref_price,
            commission=Decimal("0"),
            currency=order.instrument.currency,
            time_utc=order.created_at,
        )
        now = order.created_at
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.ACCEPTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.FILLED,
                reason=None,
                time_utc=now,
                fill=fill,
            ),
        ]

    @staticmethod
    def _default_on_cancel(cid: ClientOrderId) -> list[OrderEvent]:
        now = datetime.now(tz=timezone.utc)
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.CANCELED,
                reason="engine",
                time_utc=now,
            )
        ]

    async def submit(self, order: Order) -> ClientOrderId:
        self.submitted_orders.append(order)
        for event in self._on_submit(order):
            await self._events.put(event)
        return ClientOrderId(order.client_order_id)

    async def cancel(self, client_order_id: ClientOrderId) -> None:
        self.canceled_ids.append(client_order_id)
        for event in self._on_cancel(client_order_id):
            await self._events.put(event)


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def fixture_path(tmp_path: Path) -> Path:
    """20-day CAC.PA-like parquet."""
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    rows = []
    for i in range(20):
        t = base + timedelta(days=i)
        rows.append(
            dict(
                open_time_utc=t - timedelta(hours=8),
                close_time_utc=t,
                open=78.0 + i * 0.1,
                high=79.0 + i * 0.1,
                low=77.0 + i * 0.1,
                close=78.5 + i * 0.1,
                volume=1000.0,
            )
        )
    df = pd.DataFrame(rows)
    p = tmp_path / "cac_pa_20d.parquet"
    df.to_parquet(p)
    return p


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )


def _make_live_strategy(
    nav_slice: Decimal = Decimal("0.05"),
    risk_overrides: RiskOverrides | None = None,
    artefact_paths: ArtefactPaths | None = None,
) -> LiveStrategy:
    cfg = LiveStrategyConfig(
        strategy_id="fake_strategy",
        strategy_module="dummy",
        nav_slice=nav_slice,
        live_overrides=LiveOverrides(),
        risk_overrides=risk_overrides or RiskOverrides(),
        artefact_paths=artefact_paths or ArtefactPaths(),
    )
    return LiveStrategy(
        strategy=object(),  # not used by run_ib_pipeline (signal injected)
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )


def _always_long(bar_times: list[datetime]) -> pd.Series:
    return pd.Series(
        data=[1] * len(bar_times),
        index=pd.to_datetime(bar_times, utc=True),
    )


# --- Tests ------------------------------------------------------------------


def test_run_ib_pipeline_requires_connected_broker(
    fixture_path: Path, instrument: Instrument
) -> None:
    md = PaperMarketData(fixtures={instrument: fixture_path})
    broker = _FakeIBBroker(is_connected=False)
    live = _make_live_strategy()
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)
    with pytest.raises(RuntimeError, match="already-connected"):
        asyncio.run(
            run_ib_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=md,
                instrument=instrument,
                position_series=position,
            )
        )


def test_run_ib_pipeline_empty_bars_raises(tmp_path: Path, instrument: Instrument) -> None:
    """Empty fixture → ValueError; pipeline can't size against zero bars."""
    df = pd.DataFrame(
        {
            "open_time_utc": pd.to_datetime([], utc=True),
            "close_time_utc": pd.to_datetime([], utc=True),
            "open": pd.Series([], dtype=float),
            "high": pd.Series([], dtype=float),
            "low": pd.Series([], dtype=float),
            "close": pd.Series([], dtype=float),
            "volume": pd.Series([], dtype=float),
        }
    )
    p = tmp_path / "empty.parquet"
    df.to_parquet(p)
    md = PaperMarketData(fixtures={instrument: p})
    broker = _FakeIBBroker()
    live = _make_live_strategy()
    with pytest.raises(ValueError, match="no bars"):
        asyncio.run(
            run_ib_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=md,
                instrument=instrument,
                position_series=pd.Series(dtype=int),
            )
        )


def test_run_ib_pipeline_happy_path_records_fill(
    fixture_path: Path, instrument: Instrument
) -> None:
    """Position=1 every day, broker fills at LMT price → one entry fill;
    subsequent days are flat (target unchanged) so no further submits."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)

    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))

    result: IBRunResult = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
        )
    )

    assert result.fills_count == 1, "always-long → only the entry submits"
    assert result.canceled_count == 0
    assert result.rejected_count == 0
    # First-bar entry: nav_slice=0.05 * 100k = 5k; price ~78.5 LMT crossed +50bps
    # → ~78.89; qty ≈ 63.
    final = result.equity_curve[-1]
    assert final.position_qty == Decimal("63")
    # Equity tracks: cash debited by qty * fill_price; final mark uses last bar close.
    assert final.equity > Decimal("99000")
    # Submitted exactly once.
    assert len(broker.submitted_orders) == 1
    submitted = broker.submitted_orders[0]
    assert submitted.side == OrderSide.BUY


def test_run_ib_pipeline_position_flip_triggers_exit(
    fixture_path: Path, instrument: Instrument
) -> None:
    """Position 1 then 0 mid-series → entry fill, then exit fill on flip."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    half = len(bar_times) // 2
    values = [1] * half + [0] * (len(bar_times) - half)
    position = pd.Series(data=values, index=pd.to_datetime(bar_times, utc=True))

    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))

    result = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
        )
    )

    assert result.fills_count == 2, "expected entry fill + exit fill on the position flip"
    sides = [o.side for o in broker.submitted_orders]
    assert sides == [OrderSide.BUY, OrderSide.SELL]


def test_run_ib_pipeline_kill_switch_armed_blocks_submits(
    fixture_path: Path, instrument: Instrument
) -> None:
    """RC-13 kill switch armed pre-run → zero submits, breaches recorded."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)

    broker = _FakeIBBroker()
    live = _make_live_strategy()
    ks = KillSwitch()
    ks.arm("test pre-armed kill switch")

    result = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
            kill_switch=ks,
        )
    )

    assert result.fills_count == 0
    assert result.submitted_count == 0
    assert len(broker.submitted_orders) == 0
    assert len(result.breaches) >= 1, "expected at least one RC-13 breach logged"


def test_run_ib_pipeline_canceled_when_no_terminal_within_timeout(
    fixture_path: Path, instrument: Instrument
) -> None:
    """If submit() emits only SUBMITTED + ACCEPTED (no fill, no terminal),
    the pipeline times out and engine-cancels the order; cancel emits
    CANCELED → counted in result.canceled_count."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)

    broker = _FakeIBBroker()

    def _on_submit_no_terminal(order: Order) -> list[OrderEvent]:
        cid = ClientOrderId(order.client_order_id)
        now = order.created_at
        # No FILLED / CANCELED / REJECTED — pipeline must time out and cancel.
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.ACCEPTED,
                reason=None,
                time_utc=now,
            ),
        ]

    broker.configure_submit(_on_submit_no_terminal)

    live = _make_live_strategy()

    result = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
            event_wait_seconds=0.05,  # short for fast test
        )
    )

    assert result.fills_count == 0
    # Always-long with no fills → every bar attempts entry, every one cancels.
    # The fake's cancel() emits CANCELED so count grows per attempt.
    assert result.canceled_count >= 1
    assert len(broker.canceled_ids) >= 1
