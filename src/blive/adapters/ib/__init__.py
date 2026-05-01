"""Interactive Brokers adapter package.

Per [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)
the IB adapter family lives under ``blive.adapters.ib``. Modules:

- :mod:`blive.adapters.ib.credentials` — :data:`IB_SCHEMA` and the typed
  :class:`IBCredentials` dataclass per [ADR-035](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).
- :mod:`blive.adapters.ib.rate_limiter` — :data:`IB_DEFAULT_RATE_LIMITS`
  per [ADR-031](../../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters)
  + [ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031).
- :mod:`blive.adapters.ib.client` — :class:`IBClient` (TCP socket +
  callback model wrapping ``ib_async.IB``) plus the typed exception
  hierarchy (M2-IB.2).
- :mod:`blive.adapters.ib.instrument_resolver` — :class:`Instrument` ↔ IB
  ``Contract`` per [DD-7](../../../../docs/dd/instrument_dictionary.md)
  + Yahoo-suffix translation per [ADR-041](../../../../docs/decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver)
  (M2-IB.3a).
- :mod:`blive.adapters.ib.broker` — :class:`IBBroker` read methods +
  AccountUpdate emission timer (M2-IB.3b-i / .3b-i-timer); write
  methods at M2-IB.4.
- :mod:`blive.adapters.ib.market_data` — :class:`IBMarketData` —
  ``historical_bars`` shipped at M2-IB.3b-ii; streaming ``subscribe_*``
  methods raise :class:`NotImplementedError` pending M2-IB.5.
"""

from typing import Any

from blive.adapters.ib.broker import IBBroker
from blive.adapters.ib.client import (
    IBClient,
    IBConnectionError,
    IBError,
)
from blive.adapters.ib.credentials import IB_SCHEMA, IBCredentials
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.ib.market_data import IBMarketData
from blive.adapters.ib.rate_limiter import IB_DEFAULT_RATE_LIMITS
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.ports import ClockPort


def create_ib_broker(
    *,
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: ClockPort,
    account_update_interval_seconds: float = 30.0,
    **_unused: Any,
) -> IBBroker:
    """Factory wired into :mod:`blive.runtime.broker_registry`
    per [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004).

    Builds the dependency tree the live caller would otherwise have to
    construct manually: :class:`IBClient` (wraps :class:`ib_async.IB`),
    :class:`IBInstrumentResolver` (Instrument ↔ Contract cache), and
    the :class:`IBBroker` itself. The ``rate_limiter`` should be
    configured with :data:`IB_DEFAULT_RATE_LIMITS` (or an override
    supplied by the operator).

    The ``**_unused`` kwarg absorbs registry-style configuration noise
    (e.g. ``ib_config`` from :class:`blive.strategy.config.LiveStrategyConfig`)
    that callers may pass through without intending it for the IB adapter
    specifically.
    """
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    return IBBroker(
        client=client,
        resolver=resolver,
        clock=clock,
        account_update_interval_seconds=account_update_interval_seconds,
    )


def create_ib_market_data(
    *,
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: ClockPort,
    **_unused: Any,
) -> IBMarketData:
    """Factory paired with :func:`create_ib_broker` for the multi-broker registry.

    Creates an independent :class:`IBClient` so a strategy that uses
    only :meth:`IBMarketData.historical_bars` doesn't need a full
    :class:`IBBroker`. For the **paired** broker + market-data case
    (typical M2-IB.5 strategy run), the caller can either: (a) build
    both via these factories and accept the second :class:`IBClient`
    instance, or (b) construct :class:`IBBroker` and :class:`IBMarketData`
    directly with a shared :class:`IBClient` to avoid duplicate auth
    state. The registry uses (a) for simplicity.

    The :meth:`IBMarketData.subscribe_bars` / :meth:`subscribe_trades`
    methods raise :class:`NotImplementedError` until pipeline integration
    lands at M2-IB.5; ``historical_bars`` works today.
    """
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    return IBMarketData(client=client, resolver=resolver, clock=clock)


__all__ = [
    "IB_SCHEMA",
    "IB_DEFAULT_RATE_LIMITS",
    "IBBroker",
    "IBClient",
    "IBConnectionError",
    "IBCredentials",
    "IBError",
    "IBInstrumentResolver",
    "IBMarketData",
    "create_ib_broker",
    "create_ib_market_data",
]
