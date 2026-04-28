"""Multi-broker registry — the single dispatch site for `BrokerPort` and `MarketDataPort`.

Per [ADR-034](../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004):
this module is the **only** place outside ``blive.adapters.*`` allowed to
import from broker-specific adapter packages (``blive.adapters.{paper,ig,ib}``).
Strategy code, the Sizer, and the RiskEngine resolve a broker via
:func:`get_broker` / :func:`get_market_data` rather than importing adapters
directly. The discipline is enforced by the import-linter contract
"Broker registry isolation (ADR-034)" in ``pyproject.toml``.

The registry does **not** itself manage credentials or rate limits — those
are the broker adapter's concern (per [ADR-035](../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets)
the credentials live at ``~/.blive/secrets/{broker}.env`` and are loaded by
the adapter; per [ADR-031](../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) /
[ADR-038](../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)
the rate limiter is at ``blive.adapters.shared.rate_limiter``).

For M2-IG.2 the registry knows about ``"paper"``. ``"ig"`` is registered when
M2-IG.3 lands the IG adapter; ``"ib"`` resumes from the
``M2-substrate-IB.checkpoint`` when the IB Paper account reopens.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from blive.domain.ports import BrokerPort, MarketDataPort

# --- Adapter imports (the load-bearing isolation point) ---------------------
# Per ADR-034, these are the imports the import-linter contract whitelists.
# Other broker adapters (`ig`, `ib`) join here as their packages land.
from blive.adapters.ig import create_ig_broker, create_ig_market_data
from blive.adapters.paper.broker import PaperBroker
from blive.adapters.paper.market_data import PaperMarketData


# --- Public types -----------------------------------------------------------

BrokerFactory = Callable[..., BrokerPort]
MarketDataFactory = Callable[..., MarketDataPort]


class UnknownBroker(KeyError):
    """Raised when :func:`get_broker` / :func:`get_market_data` is called
    with a name that has no registered factory."""

    def __init__(self, name: str, *, kind: str = "broker") -> None:
        self.name = name
        self.kind = kind
        super().__init__(
            f"unknown {kind} {name!r}; registered: "
            f"{sorted(_BROKER_FACTORIES if kind == 'broker' else _MARKET_DATA_FACTORIES)}"
        )


# --- Registry tables --------------------------------------------------------

_BROKER_FACTORIES: dict[str, BrokerFactory] = {
    # PaperBroker is its own factory — its constructor accepts the
    # injection kwargs (clock, price_lookup, …) that the caller supplies.
    "paper": PaperBroker,
    # IG uses a higher-level factory that builds IGClient + IGInstrumentResolver
    # internally (the IGBroker constructor takes the wired-up dependency tree
    # rather than the raw config inputs the caller has).
    "ig": create_ig_broker,
}

_MARKET_DATA_FACTORIES: dict[str, MarketDataFactory] = {
    "paper": PaperMarketData,
    # IG market-data: REST historical_bars works today; subscribe_bars /
    # subscribe_trades raise NotImplementedError pending the Lightstreamer
    # integration at M2-IG.3 follow-up.
    "ig": create_ig_market_data,
}

_BOOTSTRAP_BROKER_FACTORIES = dict(_BROKER_FACTORIES)
_BOOTSTRAP_MARKET_DATA_FACTORIES = dict(_MARKET_DATA_FACTORIES)


# --- Public dispatch surface ------------------------------------------------


def get_broker(name: str, *args: Any, **kwargs: Any) -> BrokerPort:
    """Return a `BrokerPort` instance for the named broker.

    ``*args`` and ``**kwargs`` pass through to the registered factory; each
    broker adapter declares its own injection shape (e.g. PaperBroker takes
    ``clock`` + ``price_lookup``; IGBroker will take ``client`` +
    ``rate_limiter`` at M2-IG.3). The registry does no per-broker shape
    munging — it's a name-to-callable dispatcher.
    """
    if name not in _BROKER_FACTORIES:
        raise UnknownBroker(name, kind="broker")
    return _BROKER_FACTORIES[name](*args, **kwargs)


def get_market_data(name: str, *args: Any, **kwargs: Any) -> MarketDataPort:
    """Return a `MarketDataPort` instance for the named broker."""
    if name not in _MARKET_DATA_FACTORIES:
        raise UnknownBroker(name, kind="market_data")
    return _MARKET_DATA_FACTORIES[name](*args, **kwargs)


# --- Registration --------------------------------------------------------------


def register_broker(name: str, factory: BrokerFactory) -> None:
    """Register a broker factory.

    Used by IG / IB adapter packages at their landing milestone (M2-IG.3 for
    IG; M2-IB resumption for IB) to wire their factory into the registry.
    Tests use this to inject mock factories.

    Re-registering an existing name **overwrites** silently — call sites are
    expected to know what they're doing.
    """
    _BROKER_FACTORIES[name] = factory


def register_market_data(name: str, factory: MarketDataFactory) -> None:
    """Register a market-data factory."""
    _MARKET_DATA_FACTORIES[name] = factory


def known_brokers() -> tuple[str, ...]:
    """Return the sorted tuple of broker names with a registered factory."""
    return tuple(sorted(_BROKER_FACTORIES))


def known_market_data() -> tuple[str, ...]:
    """Return the sorted tuple of market-data names with a registered factory."""
    return tuple(sorted(_MARKET_DATA_FACTORIES))


def reset_registries() -> None:
    """Restore the bootstrap factory tables.

    Test helper: lets a test register a mock factory, do its work, then put
    the registry back. Only the bootstrap-time entries (currently ``paper``)
    survive the reset; later-registered entries are dropped.
    """
    global _BROKER_FACTORIES, _MARKET_DATA_FACTORIES
    _BROKER_FACTORIES.clear()
    _BROKER_FACTORIES.update(_BOOTSTRAP_BROKER_FACTORIES)
    _MARKET_DATA_FACTORIES.clear()
    _MARKET_DATA_FACTORIES.update(_BOOTSTRAP_MARKET_DATA_FACTORIES)


__all__ = [
    "BrokerFactory",
    "MarketDataFactory",
    "UnknownBroker",
    "get_broker",
    "get_market_data",
    "register_broker",
    "register_market_data",
    "known_brokers",
    "known_market_data",
    "reset_registries",
]
