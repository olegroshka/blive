"""CI smoke-import contract — ADR-010.

Asserts every canonical btest engine + DSL surface that blive depends on
imports cleanly. Catches version drift between btest and blive at CI time
rather than in production.

Listed surfaces are the ones blive actively uses (M1 wiring + M2 stub
import paths). When blive grows new btest dependencies, update this test
**and** the ADR-010 surface enumeration in KB-1 in the same commit.
"""

from __future__ import annotations


def test_btest_engine_classes() -> None:
    from quantdsl_backtest.engine.backtest_runner import run_backtest
    from quantdsl_backtest.engine.factor_engine import FactorEngine
    from quantdsl_backtest.engine.portfolio_engine import compute_target_weights_for_date
    from quantdsl_backtest.engine.results import BacktestResult
    from quantdsl_backtest.engine.signal_engine import SignalEngine

    assert FactorEngine.__name__ == "FactorEngine"
    assert SignalEngine.__name__ == "SignalEngine"
    assert callable(compute_target_weights_for_date)
    assert callable(run_backtest)
    assert BacktestResult.__name__ == "BacktestResult"


def test_btest_dsl_surface() -> None:
    from quantdsl_backtest.dsl.backtest_config import (
        BacktestConfig,
        DrawdownPolicy,
        MarginConfig,
        Reporting,
        RiskChecks,
    )
    from quantdsl_backtest.dsl.costs import (
        BorrowCost,
        Commission,
        Costs,
        FinancingCost,
        StaticFees,
    )
    from quantdsl_backtest.dsl.data_config import DataConfig
    from quantdsl_backtest.dsl.execution import (
        Execution,
        LatencyModel,
        OrderPolicy,
        PowerLawSlippageModel,
        VolumeParticipation,
    )
    from quantdsl_backtest.dsl.factors import (
        ExternalFactor,
        FactorNode,
        ReturnFactor,
    )
    from quantdsl_backtest.dsl.portfolio import (
        LongShortPortfolio,
        TimingPortfolio,
    )
    from quantdsl_backtest.dsl.signals import (
        And,
        GreaterEqual,
        MaskFromBoolean,
        SignalNode,
    )
    from quantdsl_backtest.dsl.strategy import Strategy
    from quantdsl_backtest.dsl.universe import Universe

    # Just exercise the names so a removed/renamed symbol is caught.
    assert Strategy.__name__ == "Strategy"
    assert TimingPortfolio.__name__ == "TimingPortfolio"
    assert LongShortPortfolio.__name__ == "LongShortPortfolio"
    assert ExternalFactor.__name__ == "ExternalFactor"
    assert MaskFromBoolean.__name__ == "MaskFromBoolean"
    assert OrderPolicy.__name__ == "OrderPolicy"
    assert Commission.__name__ == "Commission"
    assert BacktestConfig.__name__ == "BacktestConfig"
    assert DataConfig.__name__ == "DataConfig"
    assert Universe.__name__ == "Universe"


def test_btest_data_sources_registry() -> None:
    from quantdsl_backtest.data.bundles import DataBundle
    from quantdsl_backtest.data.requests import DataRequest
    from quantdsl_backtest.data.sources.base import CacheStore, DataSource
    from quantdsl_backtest.data.sources.registry import DataSourceRegistry

    assert DataSourceRegistry.__name__ == "DataSourceRegistry"
    assert DataSource.__name__ == "DataSource"
    assert CacheStore.__name__ == "CacheStore"
    assert DataRequest.__name__ == "DataRequest"
    assert DataBundle.__name__ == "DataBundle"


def test_btest_singleasset_runner_for_timing_portfolio() -> None:
    """Per OQ-030: TimingPortfolio strategies dispatch via SingleAssetRunner."""
    from quantdsl_backtest.runners.single_asset import SingleAssetRunner

    assert hasattr(SingleAssetRunner, "run")
