"""RiskEngine M1 subset tests — RC-08, RC-09, RC-12, RC-13."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from blive.domain.types import (
    AssetClass,
    Bar,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
)
from blive.risk import (
    KillSwitch,
    RiskBreachSeverity,
    RiskCheckCode,
    RiskEngine,
    RiskEngineConfig,
    RiskInputs,
)


def _now() -> datetime:
    return datetime(2026, 4, 27, 15, 30, tzinfo=timezone.utc)


def _instr() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


def _order() -> Order:
    return Order(
        client_order_id=uuid4(),
        strategy_id="s",
        instrument=_instr(),
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MKT,
        time_in_force=TimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=_now(),
    )


def _fresh_bar() -> Bar:
    open_t = _now() - timedelta(seconds=30)
    close_t = _now() - timedelta(seconds=5)
    return Bar(
        instrument=_instr(),
        open_time_utc=open_t,
        close_time_utc=close_t,
        open=Decimal("78"),
        high=Decimal("79"),
        low=Decimal("77"),
        close=Decimal("78.5"),
        volume=Decimal("1000"),
    )


def test_rc13_kill_switch_armed_blocks_all() -> None:
    ks = KillSwitch()
    ks.arm("manual test")
    eng = RiskEngine(config=RiskEngineConfig(), kill_switch=ks, strategy_id="s")
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=_fresh_bar(), is_market_open=True),
        now=_now(),
    )
    assert approved is None
    assert len(breaches) == 1
    assert breaches[0].check == RiskCheckCode.RC_13
    assert breaches[0].severity == RiskBreachSeverity.BLOCK


def test_rc08_stale_data_blocks() -> None:
    """G2 negative test: deliberately stale bar → RC-08 BLOCK + alert."""
    cfg = RiskEngineConfig(max_data_staleness_daily_sec=60, is_intraday=False)
    eng = RiskEngine(config=cfg, kill_switch=KillSwitch(), strategy_id="s")
    stale_bar = Bar(
        instrument=_instr(),
        open_time_utc=_now() - timedelta(minutes=11),
        close_time_utc=_now() - timedelta(minutes=10),  # 600s old, > 60s threshold
        open=Decimal("78"),
        high=Decimal("79"),
        low=Decimal("77"),
        close=Decimal("78.5"),
        volume=Decimal("1000"),
    )
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=stale_bar, is_market_open=True),
        now=_now(),
    )
    assert approved is None
    assert breaches[0].check == RiskCheckCode.RC_08
    assert "stale" in breaches[0].detail


def test_rc08_no_bar_blocks() -> None:
    eng = RiskEngine(config=RiskEngineConfig(), kill_switch=KillSwitch(), strategy_id="s")
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=None, is_market_open=True),
        now=_now(),
    )
    assert approved is None
    assert breaches[0].check == RiskCheckCode.RC_08


def test_rc09_market_closed_blocks_unless_outside_rth_allowed() -> None:
    eng = RiskEngine(
        config=RiskEngineConfig(outside_rth_allowed=False),
        kill_switch=KillSwitch(),
        strategy_id="s",
    )
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=_fresh_bar(), is_market_open=False),
        now=_now(),
    )
    assert approved is None
    assert breaches[0].check == RiskCheckCode.RC_09


def test_rc09_outside_rth_allowed_passes() -> None:
    eng = RiskEngine(
        config=RiskEngineConfig(outside_rth_allowed=True),
        kill_switch=KillSwitch(),
        strategy_id="s",
    )
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=_fresh_bar(), is_market_open=False),
        now=_now(),
    )
    assert approved is not None
    assert breaches == []


def test_rc12_artefact_age_warning_then_block(tmp_path: Path) -> None:
    """ADR-022 freshness window."""
    art = tmp_path / "pred.pkl"
    art.write_bytes(b"x")
    # Age 22 d → warn (between 21 and 30); age 31 d → block.
    eng = RiskEngine(
        config=RiskEngineConfig(max_model_artefact_age_days=30, model_artefact_warning_age_days=21),
        kill_switch=KillSwitch(),
        strategy_id="s",
    )

    # Force mtime to 22 days ago for warn case.
    import os
    import time

    twenty_two_days_ago = (_now() - timedelta(days=22)).timestamp()
    os.utime(art, (twenty_two_days_ago, twenty_two_days_ago))
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=_fresh_bar(), is_market_open=True, artefact_paths={"f": art}),
        now=_now(),
    )
    assert approved is not None
    assert any(
        b.check == RiskCheckCode.RC_12 and b.severity == RiskBreachSeverity.WARN for b in breaches
    )

    # Now block case.
    thirty_one_days_ago = (_now() - timedelta(days=31)).timestamp()
    os.utime(art, (thirty_one_days_ago, thirty_one_days_ago))
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=_fresh_bar(), is_market_open=True, artefact_paths={"f": art}),
        now=_now(),
    )
    assert approved is None
    assert breaches[-1].check == RiskCheckCode.RC_12
    assert breaches[-1].severity == RiskBreachSeverity.BLOCK


def test_rc12_missing_artefact_blocks(tmp_path: Path) -> None:
    eng = RiskEngine(config=RiskEngineConfig(), kill_switch=KillSwitch(), strategy_id="s")
    missing = tmp_path / "nope.pkl"
    approved, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(
            last_bar=_fresh_bar(), is_market_open=True, artefact_paths={"f": missing}
        ),
        now=_now(),
    )
    assert approved is None
    assert breaches[0].check == RiskCheckCode.RC_12
    assert "missing" in breaches[0].detail


def test_eval_order_rc13_short_circuits_rc08() -> None:
    """Order-of-evaluation: RC-13 fires before RC-08."""
    ks = KillSwitch()
    ks.arm("test")
    eng = RiskEngine(config=RiskEngineConfig(), kill_switch=ks, strategy_id="s")
    # Stale data + armed kill-switch → only RC-13 surfaces.
    _, breaches = eng.approve(
        _order(),
        inputs=RiskInputs(last_bar=None, is_market_open=False),
        now=_now(),
    )
    assert len(breaches) == 1
    assert breaches[0].check == RiskCheckCode.RC_13
