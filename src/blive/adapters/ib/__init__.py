"""Interactive Brokers adapter package.

Per [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)
the IB adapter family lives under ``blive.adapters.ib``. M2-IB.2 ships
the connection layer:

- :mod:`blive.adapters.ib.credentials` — :data:`IB_SCHEMA` and the typed
  :class:`IBCredentials` dataclass per [ADR-035](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).
- :mod:`blive.adapters.ib.rate_limiter` — :data:`IB_DEFAULT_RATE_LIMITS`
  per [ADR-031](../../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters)
  + [ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031).
- :mod:`blive.adapters.ib.client` — :class:`IBClient` (TCP socket +
  callback model wrapping ``ib_async.IB``) plus the typed exception
  hierarchy.

Coming at M2-IB.3:

- :mod:`blive.adapters.ib.instrument_resolver` — :class:`Instrument` ↔ IB
  ``Contract`` per [DD-7](../../../../docs/dd/instrument_dictionary.md).
- :mod:`blive.adapters.ib.broker` — :class:`IBBroker` read methods (full
  read+write at M2-IB.4).
- :mod:`blive.adapters.ib.market_data` — :class:`IBMarketData`.
- ``create_ib_broker`` / ``create_ib_market_data`` factories registered
  into :mod:`blive.runtime.broker_registry`.
"""

from blive.adapters.ib.client import (
    IBClient,
    IBConnectionError,
    IBError,
)
from blive.adapters.ib.credentials import IB_SCHEMA, IBCredentials
from blive.adapters.ib.rate_limiter import IB_DEFAULT_RATE_LIMITS

__all__ = [
    "IB_SCHEMA",
    "IB_DEFAULT_RATE_LIMITS",
    "IBClient",
    "IBConnectionError",
    "IBCredentials",
    "IBError",
]
