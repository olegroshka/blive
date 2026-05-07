"""EODHD adapter package.

The first non-script EODHD module; precursor to the eventual
``EODHDDataSource`` (per [ADR-014](../../../../docs/decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction)).
At v0.1 it ships only the per-instrument convention catalogue +
sizing-time price-conversion helper introduced at M3.1 per
[ADR-050 PROPOSED](../../../../docs/decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only).
"""

from blive.adapters.eodhd.conventions import (
    CONVENTIONS_BY_IB_SYMBOL,
    Convention,
    ConventionKind,
    eodhd_to_ib_price,
)

__all__ = [
    "CONVENTIONS_BY_IB_SYMBOL",
    "Convention",
    "ConventionKind",
    "eodhd_to_ib_price",
]
