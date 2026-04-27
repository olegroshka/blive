"""DD-3 schema tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from blive.strategy.config import (
    NAV_SLICE_HARD_CAP,
    ArtefactPaths,
    LiveBorrowProvider,
    LiveFinancingProvider,
    LiveKillSwitch,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)


def test_default_nav_slice_in_range_accepts() -> None:
    cfg = LiveStrategyConfig(
        strategy_id="tkan_v4_momentum_timing_1x",
        strategy_module="btest.strategies.tkan_v4_momentum_timing",
        nav_slice=Decimal("0.05"),
    )
    assert cfg.nav_slice == Decimal("0.05")
    assert cfg.live_overrides == LiveOverrides()
    assert cfg.risk_overrides.max_model_artefact_age_days == 30


def test_nav_slice_above_cap_rejected() -> None:
    with pytest.raises(ValidationError, match="hard cap"):
        LiveStrategyConfig(
            strategy_id="x",
            strategy_module="m.x",
            nav_slice=NAV_SLICE_HARD_CAP + Decimal("0.01"),
        )


def test_nav_slice_zero_rejected() -> None:
    with pytest.raises(ValidationError, match="> 0"):
        LiveStrategyConfig(strategy_id="x", strategy_module="m.x", nav_slice=Decimal("0"))


def test_strategy_id_uppercase_rejected() -> None:
    with pytest.raises(ValidationError, match="lowercase"):
        LiveStrategyConfig(strategy_id="ABC", strategy_module="m.x", nav_slice=Decimal("0.05"))


def test_strategy_id_dash_rejected() -> None:
    with pytest.raises(ValidationError, match="lowercase"):
        LiveStrategyConfig(strategy_id="bad-name", strategy_module="m.x", nav_slice=Decimal("0.05"))


def test_strategy_module_dotted_path_validates() -> None:
    with pytest.raises(ValidationError, match="dotted path"):
        LiveStrategyConfig(strategy_id="x", strategy_module=".bad", nav_slice=Decimal("0.05"))


def test_strategy_module_invalid_identifier_part_rejected() -> None:
    with pytest.raises(ValidationError, match="not a valid identifier"):
        LiveStrategyConfig(strategy_id="x", strategy_module="a.123bad", nav_slice=Decimal("0.05"))


def test_unknown_top_level_key_rejected() -> None:
    with pytest.raises(ValidationError, match="extra"):
        LiveStrategyConfig.model_validate(
            {
                "strategy_id": "x",
                "strategy_module": "m.x",
                "nav_slice": Decimal("0.05"),
                "factors": {},  # forbidden topology key
            }
        )


def test_live_overrides_direct_routing_requires_venue() -> None:
    with pytest.raises(ValidationError, match="direct_venue"):
        LiveOverrides(routing="DIRECT")


def test_live_overrides_direct_venue_only_when_routing_direct() -> None:
    with pytest.raises(ValidationError, match="only valid when routing"):
        LiveOverrides(routing="SMART", direct_venue="XPAR")


def test_live_borrow_provider_static_requires_rate() -> None:
    with pytest.raises(ValidationError, match="default_annual_rate"):
        LiveBorrowProvider(kind="static")


def test_live_borrow_provider_ib_no_rate_required() -> None:
    p = LiveBorrowProvider(kind="ib")
    assert p.default_annual_rate is None
    assert p.cache_ttl_seconds == 3600


def test_live_financing_spread_negative_rejected() -> None:
    with pytest.raises(ValidationError, match="≥ 0"):
        LiveFinancingProvider(kind="ib", spread_bps=Decimal("-1"))


def test_live_kill_switch_thresholds_invalid_rejected() -> None:
    with pytest.raises(ValidationError, match="max_intraday_drawdown_bps"):
        LiveKillSwitch(max_intraday_drawdown_bps=Decimal("0"))


def test_risk_overrides_warn_must_be_below_block() -> None:
    with pytest.raises(ValidationError, match="warn before block"):
        RiskOverrides(
            max_model_artefact_age_days=10,
            model_artefact_warning_age_days=10,
        )


def test_risk_overrides_m4_tier_key_forward_compat(caplog: pytest.LogCaptureFixture) -> None:
    """M4-tier RC keys should be admitted with a warning — DD-3 §7."""
    import logging

    with caplog.at_level(logging.WARNING):
        ro = RiskOverrides(max_gross_leverage=Decimal("2.0"))
    assert ro.max_data_staleness_intraday_sec == 300  # default still applied
    assert any("forward-compat" in rec.getMessage() for rec in caplog.records)


def test_risk_overrides_unknown_key_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown key"):
        RiskOverrides(definitely_not_a_real_key=42)  # type: ignore[arg-type]


def test_artefact_paths_expand_user_handles_tilde() -> None:
    ap = ArtefactPaths(paths={"f1": "~/somewhere/file.pkl"})
    assert "~" not in str(ap.paths["f1"])
