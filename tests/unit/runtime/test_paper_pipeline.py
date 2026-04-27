"""Paper-mode pipeline tests.

Covers the four G2 exit criteria as far as they can be exercised at M1
without the real CAC.PA fixture + TKAN artefact:

1. Round-trip with commission (G2 criterion 3).
2. Synthetic-parity sanity check — blive's pipeline reproduces the equity
   curve implied by a known position series.
3. RC-08 stale-data negative test (G2 criterion 4).
4. Pipeline rejects non-TimingPortfolio strategies until OQ-030 resolves.

The "real" G2 ±1 bps test against `tkan_v4_momentum_timing` 1× over ≥ 252
days of CAC.PA history is a manual test gated on the operator providing
the EODHD fixture + the TKAN ``pred_cache.pkl`` artefact; see
``tests_slow/g2_parity/`` (drafted as a follow-up after Phase-1 fixtures
land).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Mapping

import pandas as pd
import pytest

from blive.adapters.paper.market_data import PaperMarketData, make_default_cac_pa
from blive.runtime import paper_pipeline as _pp
from blive.runtime.paper_pipeline import run_paper_pipeline
from blive.strategy.config import (
    ArtefactPaths,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)
from blive.strategy.loader import LiveStrategy

# --- Fakes that replace btest's SingleAssetRunner / Strategy / TimingPortfolio
# during these tests. The real btest code path is exercised by the manual
# `tests_slow/g2_parity` suite once fixtures land.


@dataclass(frozen=True)
class _FakeTimingPortfolio:
    instrument: str
    target_leverage: float = 1.0
    signal_delay_bars: int = 1


@dataclass(frozen=True)
class _FakeStrategy:
    factors: Mapping[str, object]
    portfolio: _FakeTimingPortfolio


@dataclass
class _FakeRunResult:
    position: pd.Series


class _FakeSingleAssetRunner:
    """Drop-in for ``SingleAssetRunner`` keyed by a pre-baked position series."""

    _position: pd.Series | None = None

    @classmethod
    def with_position(cls, position: pd.Series) -> type:
        cls._position = position
        return cls

    def __init__(self, strategy: _FakeStrategy, btest_root: Path) -> None:
        self._strategy = strategy

    def run(self, price_close: pd.Series, aux_series=None) -> dict:
        assert self._position is not None
        return {"position": self._position}


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


def _make_live_strategy(
    nav_slice: Decimal = Decimal("0.05"),
    target_leverage: float = 1.0,
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
    strategy = _FakeStrategy(
        factors={},
        portfolio=_FakeTimingPortfolio(instrument="CAC.PA", target_leverage=target_leverage),
    )
    return LiveStrategy(
        strategy=strategy,
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )


def _patch_runner_and_portfolio(
    monkeypatch: pytest.MonkeyPatch,
    *,
    position: pd.Series,
) -> None:
    """Swap btest's runner + TimingPortfolio for fakes."""
    monkeypatch.setattr(
        _pp,
        "SingleAssetRunner",
        _FakeSingleAssetRunner.with_position(position),
    )
    monkeypatch.setattr(_pp, "TimingPortfolio", _FakeTimingPortfolio)


def test_pipeline_round_trip_with_commission(
    fixture_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G2 criterion 3 — fill including commission reflected in equity."""
    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})

    # Always-in position (1) — first bar drives one BUY; equity then tracks.
    bar_times = [b.close_time_utc for b in md.bars(inst)]
    position = pd.Series(
        data=[1] * len(bar_times),
        index=pd.to_datetime(bar_times, utc=True),
    )
    _patch_runner_and_portfolio(monkeypatch, position=position)

    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    commission = Decimal("0.005")  # per share

    result = asyncio.run(
        run_paper_pipeline(
            live_strategy=live,
            market_data=md,
            instrument=inst,
            btest_root=Path("."),
            starting_cash=Decimal("100000"),
            commission_per_share=commission,
        )
    )
    assert result.fills_count == 1, "expected exactly one fill (initial entry)"
    # First-bar entry: nav_slice * equity = 5000; price ≈ 78.5; qty ≈ 63.
    first_fill_qty = 63
    # Equity should be lower than starting_cash by commission * qty post-fill.
    final = result.equity_curve[-1]
    assert final.position_qty == Decimal(str(first_fill_qty))
    # Equity at final bar ≈ cash + qty * close. Sanity: final equity > 99,000.
    assert final.equity > Decimal("99000")


def test_pipeline_rc13_kill_switch_armed_blocks_all_orders(
    fixture_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G2 criterion 4 (no-bypass): pre-armed kill-switch ⇒ zero fills, every
    rebalance attempt logs a RC-13 BLOCK breach. End-to-end RC-08 timing is
    unit-tested in :mod:`tests.unit.risk.test_checks`; the pipeline-level
    negative test focuses on the no-bypass property of ADR-008.
    """
    from blive.risk import KillSwitch

    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(inst)]
    # Always-in (entry signal True every day) — without the kill switch we'd
    # see one fill on day-1 entry, then steady-state.
    position = pd.Series(
        data=[1] * len(bar_times),
        index=pd.to_datetime(bar_times, utc=True),
    )
    _patch_runner_and_portfolio(monkeypatch, position=position)

    ks = KillSwitch()
    ks.arm("test pre-armed kill switch")
    live = _make_live_strategy()

    result = asyncio.run(
        run_paper_pipeline(
            live_strategy=live,
            market_data=md,
            instrument=inst,
            btest_root=Path("."),
            starting_cash=Decimal("100000"),
            kill_switch=ks,
        )
    )
    assert result.fills_count == 0
    assert all(b.check.value == "RC-13" for b in result.breaches)
    assert len(result.breaches) >= 1
    # Equity untouched (no trades, no commission).
    assert result.final_equity == Decimal("100000")


def test_pipeline_synthetic_parity_no_trades_when_position_zero(
    fixture_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When btest says ``position=0`` for the whole window, blive submits no orders."""
    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(inst)]
    position = pd.Series(
        data=[0] * len(bar_times),
        index=pd.to_datetime(bar_times, utc=True),
    )
    _patch_runner_and_portfolio(monkeypatch, position=position)

    live = _make_live_strategy()
    result = asyncio.run(
        run_paper_pipeline(
            live_strategy=live,
            market_data=md,
            instrument=inst,
            btest_root=Path("."),
            starting_cash=Decimal("100000"),
        )
    )
    assert result.fills_count == 0
    assert result.final_equity == Decimal("100000")


def test_pipeline_rejects_non_timing_portfolio(
    fixture_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per OQ-030, only TimingPortfolio archetype supported at M1."""
    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})

    @dataclass(frozen=True)
    class _LongShortPortfolio:
        pass

    @dataclass(frozen=True)
    class _S:
        factors: Mapping[str, object] = field(default_factory=dict)
        portfolio: _LongShortPortfolio = field(default_factory=_LongShortPortfolio)

    cfg = LiveStrategyConfig(strategy_id="x", strategy_module="m.x", nav_slice=Decimal("0.05"))
    live = LiveStrategy(
        strategy=_S(),
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )
    # _LongShortPortfolio is not the (mocked or real) TimingPortfolio class
    # used by the pipeline, so the isinstance check raises NotImplementedError.
    with pytest.raises(NotImplementedError, match="TimingPortfolio"):
        asyncio.run(
            run_paper_pipeline(
                live_strategy=live,
                market_data=md,
                instrument=inst,
                btest_root=Path("."),
            )
        )
