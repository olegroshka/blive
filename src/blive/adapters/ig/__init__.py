"""IG Markets adapter package.

Per [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)
the IG adapter family lives under ``blive.adapters.ig``. Modules:

- :mod:`blive.adapters.ig.credentials` — :data:`IG_SCHEMA` and the typed
  :class:`IGCredentials` dataclass per [ADR-035](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).
- :mod:`blive.adapters.ig.client` — REST + Lightstreamer driver per
  [ADR-036](../../../../docs/decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)
  (M2-IG.3 adds REST core; Lightstreamer subscriptions land alongside
  :mod:`blive.adapters.ig.market_data`).
- :mod:`blive.adapters.ig.instrument_resolver` — ``Instrument`` ↔ IG epic
  per [DD-8](../../../../docs/dd/ig_instrument_dictionary.md) (M2-IG.3).
- :mod:`blive.adapters.ig.broker` — :class:`IGBroker` per [INV-6 §1.1](../../../../docs/inv/ports_adapters.md#11-brokerport)
  (read methods M2-IG.3; write methods M2-IG.4).
- :mod:`blive.adapters.ig.market_data` — :class:`IGMarketData` (M2-IG.3
  follow-up).
"""

from typing import Any

import httpx

from blive.adapters.ig.broker import IGBroker
from blive.adapters.ig.client import IGClient
from blive.adapters.ig.credentials import IG_SCHEMA, IGCredentials
from blive.adapters.ig.instrument_resolver import IGInstrumentResolver
from blive.adapters.ig.market_data import IGMarketData
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.ports import ClockPort


def create_ig_broker(
    *,
    credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: ClockPort,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = 30.0,
    **_unused: Any,
) -> IGBroker:
    """Factory wired into [`broker_registry`](../../runtime/broker_registry.py)
    per [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004).

    Builds the dependency tree the live caller would otherwise have to
    construct manually: :class:`IGClient` (REST transport),
    :class:`IGInstrumentResolver` (epic ↔ Instrument cache), and the
    :class:`IGBroker` itself. ``transport=None`` (the default) lets
    httpx pick its own AsyncHTTPTransport; tests inject
    :class:`httpx.MockTransport`.

    The ``**_unused`` kwarg absorbs registry-style configuration noise
    (e.g. ``ig_config`` from :class:`blive.strategy.config.LiveStrategyConfig`)
    that callers may pass through without intending it for the IG adapter
    specifically. Concrete ``ig_config`` keys land at M2-IG.4 / .5.
    """
    client = IGClient(
        credentials=credentials,
        rate_limiter=rate_limiter,
        clock=clock,
        transport=transport,
        timeout_seconds=timeout_seconds,
    )
    resolver = IGInstrumentResolver(client)
    return IGBroker(
        client=client,
        resolver=resolver,
        credentials=credentials,
        clock=clock,
    )


def create_ig_market_data(
    *,
    credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: ClockPort,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = 30.0,
    **_unused: Any,
) -> IGMarketData:
    """Factory paired with :func:`create_ig_broker` for the multi-broker registry.

    Creates an independent :class:`IGClient` so a strategy that uses
    only :meth:`IGMarketData.historical_bars` doesn't need a full
    :class:`IGBroker` (e.g. backtest replay against IG-fetched
    historicals). The IGClient still authenticates + rate-limits the
    same way; tests inject ``transport``.

    For the **paired** broker + market-data case (typical M2-IG.5 strategy
    run), the caller can either: (a) build both via these factories and
    accept the second :class:`IGClient` instance, or (b) construct
    :class:`IGBroker` and :class:`IGMarketData` directly with a shared
    :class:`IGClient` to avoid duplicate auth state. The registry uses
    (a) for simplicity; M2-IG.5 may swap to (b) when the strategy
    pipeline lands.

    The :meth:`IGMarketData.subscribe_bars` / :meth:`subscribe_trades`
    methods raise :class:`NotImplementedError` until the Lightstreamer
    integration lands at M2-IG.3 follow-up; the historical_bars REST
    path works today.
    """
    client = IGClient(
        credentials=credentials,
        rate_limiter=rate_limiter,
        clock=clock,
        transport=transport,
        timeout_seconds=timeout_seconds,
    )
    resolver = IGInstrumentResolver(client)
    return IGMarketData(
        client=client,
        resolver=resolver,
        clock=clock,
    )


__all__ = [
    "IG_SCHEMA",
    "IGCredentials",
    "IGBroker",
    "IGClient",
    "IGInstrumentResolver",
    "IGMarketData",
    "create_ig_broker",
    "create_ig_market_data",
]
