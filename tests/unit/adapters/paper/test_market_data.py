"""PaperMarketData fixture-loading tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from blive.adapters.paper.market_data import PaperMarketData, make_default_cac_pa
from blive.domain.types import AssetClass, Instrument


def _write_fixture(path: Path, n_days: int = 10) -> None:
    base = datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc)
    rows = []
    for i in range(n_days):
        t = base + timedelta(days=i)
        open_t = t - timedelta(hours=8)
        rows.append(
            dict(
                open_time_utc=open_t,
                close_time_utc=t,
                open=78.0 + i,
                high=79.0 + i,
                low=77.0 + i,
                close=78.5 + i,
                volume=1000.0,
            )
        )
    df = pd.DataFrame(rows)
    df.to_parquet(path)


@pytest.fixture
def fixture_path(tmp_path: Path) -> Path:
    p = tmp_path / "cac_pa.parquet"
    _write_fixture(p)
    return p


def test_market_data_load_and_iterate(fixture_path: Path) -> None:
    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})
    bars = md.bars(inst)
    assert len(bars) == 10
    assert bars[0].open == Decimal("78.0")
    assert bars[-1].close == Decimal("87.5")
    # Monotonic close times
    for a, b in zip(bars, bars[1:]):
        assert a.close_time_utc < b.close_time_utc


def test_latest_returns_correct_bar(fixture_path: Path) -> None:
    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})
    bars = md.bars(inst)
    third = bars[2]
    latest = md.latest(inst, on_or_before=third.close_time_utc)
    assert latest is not None
    assert latest.close_time_utc == third.close_time_utc


@pytest.mark.asyncio
async def test_freq_mismatch_raises(fixture_path: Path) -> None:
    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path}, freq="1d")
    with pytest.raises(ValueError, match="freq"):
        await md.historical_bars(
            inst,
            "1m",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc),
        )


def test_unknown_instrument_raises(fixture_path: Path) -> None:
    """An instrument that wasn't in the constructor's fixture map raises KeyError."""
    md = PaperMarketData(fixtures={make_default_cac_pa(): fixture_path})
    other = Instrument(
        symbol="AAPL",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.EQUITY,
        multiplier=Decimal("1"),
    )
    with pytest.raises(KeyError):
        md.bars(other)


def test_missing_required_columns_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.parquet"
    pd.DataFrame({"close": [1.0, 2.0]}).to_parquet(bad)
    inst = make_default_cac_pa()
    with pytest.raises(ValueError, match="missing required columns"):
        PaperMarketData(fixtures={inst: bad})


def test_subscribe_trades_not_implemented(fixture_path: Path) -> None:
    import asyncio

    inst = make_default_cac_pa()
    md = PaperMarketData(fixtures={inst: fixture_path})
    with pytest.raises(NotImplementedError):
        asyncio.run(md.subscribe_trades(inst))
