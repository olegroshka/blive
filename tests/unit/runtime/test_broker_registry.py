"""Tests for :mod:`blive.runtime.broker_registry`.

Covers [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)
dispatch surface: paper bootstrap; unknown raises; registration adds
factories; reset restores bootstrap; known_* enumeration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.paper.broker import PaperBroker
from blive.adapters.paper.market_data import PaperMarketData
from blive.domain.types import AssetClass, Instrument
from blive.runtime.broker_registry import (
    UnknownBroker,
    get_broker,
    get_market_data,
    known_brokers,
    known_market_data,
    register_broker,
    register_market_data,
    reset_registries,
)


@pytest.fixture(autouse=True)
def _reset_registries_after_each_test() -> Any:
    """Every test starts and ends with the bootstrap registry state."""
    reset_registries()
    yield
    reset_registries()


# --- Bootstrap state --------------------------------------------------------


def test_paper_is_bootstrapped() -> None:
    """`paper` is registered out of the box — pre-dates the multi-broker
    registry (M0 / M1)."""
    assert "paper" in known_brokers()
    assert "paper" in known_market_data()


def test_ig_broker_is_bootstrapped() -> None:
    """`ig` broker + market-data factories registered at M2-IG.3 close."""
    assert "ig" in known_brokers()
    assert "ig" in known_market_data()


def test_ig_get_broker_returns_ig_broker() -> None:
    """get_broker('ig', ...) wires up IGClient + IGInstrumentResolver +
    IGBroker via the create_ig_broker factory. We only verify the
    return type — full transport-level testing lives in the IG-adapter
    test files."""
    from datetime import datetime, timezone
    from decimal import Decimal as _Decimal

    import httpx

    from blive.adapters.clock.sim import SimClock
    from blive.adapters.ig import IGBroker, IGCredentials
    from blive.adapters.shared.rate_limiter import (
        RateLimitBucket,
        RateLimitConfig,
        TokenBucketRateLimiter,
    )

    clock = SimClock(start=datetime(2026, 4, 28, tzinfo=timezone.utc))
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "general": RateLimitBucket(capacity=10, refill_per_second=_Decimal("1")),
                "trading": RateLimitBucket(capacity=10, refill_per_second=_Decimal("1")),
            }
        ),
    )
    creds = IGCredentials(
        api_key="k", username="u", password="p", account_id="ACC", environment="demo"
    )
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={}))

    broker = get_broker(
        "ig",
        credentials=creds,
        rate_limiter=rate_limiter,
        clock=clock,
        transport=transport,
    )
    assert isinstance(broker, IGBroker)


def test_known_brokers_returns_sorted_tuple() -> None:
    register_broker("zzz", lambda **_: None)  # type: ignore[arg-type,return-value]
    register_broker("aaa", lambda **_: None)  # type: ignore[arg-type,return-value]
    names = known_brokers()
    assert names == tuple(sorted(names))
    assert "aaa" in names
    assert "zzz" in names
    assert "paper" in names


# --- Dispatch ---------------------------------------------------------------


def test_get_broker_paper_returns_paper_broker() -> None:
    """`get_broker("paper", ...)` constructs a real PaperBroker via its
    constructor signature (clock + price_lookup + optional kwargs)."""
    clock = SimClock(start=datetime(2026, 4, 27, tzinfo=timezone.utc))
    instrument = Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
    )

    def price_lookup(_: Instrument) -> Decimal:
        return Decimal("78.42")

    broker = get_broker("paper", clock=clock, price_lookup=price_lookup)
    assert isinstance(broker, PaperBroker)


def test_get_market_data_paper_returns_paper_market_data(tmp_path: Any) -> None:
    """`get_market_data("paper", ...)` constructs a PaperMarketData. We don't
    actually load fixtures here — empty mapping is enough to verify dispatch."""
    md = get_market_data("paper", fixtures={})
    assert isinstance(md, PaperMarketData)


def test_get_broker_unknown_raises() -> None:
    with pytest.raises(UnknownBroker) as excinfo:
        get_broker("nonexistent")
    assert excinfo.value.name == "nonexistent"
    assert excinfo.value.kind == "broker"


def test_get_market_data_unknown_raises() -> None:
    with pytest.raises(UnknownBroker) as excinfo:
        get_market_data("nonexistent")
    assert excinfo.value.name == "nonexistent"
    assert excinfo.value.kind == "market_data"


# --- Registration -----------------------------------------------------------


def test_register_broker_adds_factory_callable() -> None:
    sentinel = object()

    def fake_factory(**_kwargs: Any) -> Any:
        return sentinel

    register_broker("fake", fake_factory)  # type: ignore[arg-type]
    assert "fake" in known_brokers()
    assert get_broker("fake") is sentinel


def test_register_market_data_adds_factory_callable() -> None:
    sentinel = object()

    def fake_factory(**_kwargs: Any) -> Any:
        return sentinel

    register_market_data("fake", fake_factory)  # type: ignore[arg-type]
    assert "fake" in known_market_data()
    assert get_market_data("fake") is sentinel


def test_register_overwrites_existing_silently() -> None:
    """Re-registering an existing name overwrites — no error, no warning.
    Documented behaviour per the docstring."""

    def first(**_kwargs: Any) -> str:
        return "first"

    def second(**_kwargs: Any) -> str:
        return "second"

    register_broker("twice", first)  # type: ignore[arg-type]
    register_broker("twice", second)  # type: ignore[arg-type]
    assert get_broker("twice") == "second"


# --- Reset -----------------------------------------------------------------


def test_reset_registries_drops_post_bootstrap_entries() -> None:
    register_broker("ephemeral_broker", lambda **_: None)  # type: ignore[arg-type,return-value]
    register_market_data("ephemeral_md", lambda **_: None)  # type: ignore[arg-type,return-value]
    assert "ephemeral_broker" in known_brokers()
    assert "ephemeral_md" in known_market_data()

    reset_registries()
    assert "ephemeral_broker" not in known_brokers()
    assert "ephemeral_md" not in known_market_data()
    # Bootstrap entries persist.
    assert "paper" in known_brokers()
    assert "paper" in known_market_data()


def test_reset_registries_restores_bootstrap_factory() -> None:
    """Resetting restores `paper` to the actual PaperBroker factory, not
    a stale one from an earlier register_broker overwrite."""

    def imposter(**_kwargs: Any) -> str:
        return "imposter"

    register_broker("paper", imposter)  # type: ignore[arg-type]
    assert get_broker("paper") == "imposter"

    reset_registries()
    clock = SimClock(start=datetime(2026, 4, 27, tzinfo=timezone.utc))

    def price_lookup(_: Instrument) -> Decimal:
        return Decimal("78.42")

    broker = get_broker("paper", clock=clock, price_lookup=price_lookup)
    assert isinstance(broker, PaperBroker), "reset should restore the original PaperBroker factory"
