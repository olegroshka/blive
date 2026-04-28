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
- :mod:`blive.adapters.ig.market_data` — :class:`IGMarketData` (M2-IG.3).
"""

from blive.adapters.ig.credentials import IG_SCHEMA, IGCredentials

__all__ = [
    "IG_SCHEMA",
    "IGCredentials",
]
