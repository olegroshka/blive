"""Per-instrument EODHD-vs-IB unit-of-quote conventions.

Operationalises [ADR-050 PROPOSED](../../../../docs/decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) —
the M3.1 narrow-scope sizing fix per
[TASK_REGISTRY M3.1](../../../../TASK_REGISTRY.md). Surfaces a single
helper, :func:`eodhd_to_ib_price`, that callers (the multi-instrument
pipeline's `_price_lookup` closure) route through to convert
EODHD-quoted prices to IB-equivalent prices at sizing time.

The conversion is **per-instrument**, keyed by IB symbol (the same
key the multi-instrument pipeline already uses; matches the
``order_type_by_symbol`` precedent in
:mod:`blive.runtime.ib_pipeline`). Symbols absent from the catalogue
fall through to the IDENTITY convention — most instruments need no
conversion (IBTL / IBTM / QQQ / TLT in the Phase 1 universe per
[ADR-047](../../../../docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)).

The catalogue is operator-curated. RC-10 (price sanity) per
[INV-4 v0.2](../../../../docs/inv/risk_checks.md) is the auto-detection
layer for catalogue-miss / catalogue-stale cases; it trips at sizing
time when an IB-equivalent reference price diverges from the
post-conversion EODHD price beyond the configured threshold (default
±50%; chosen for leveraged-ETP volatility per ADR-050 §"Decision" #4).

Vendor-side promotion path (per ADR-050 alternatives #3, deferred):
when the catalogue grows ≥3-5 entries or operator-side editing
pressure builds, this dict-literal promotes to a YAML-driven catalogue
under ``~/.blive/config/`` paralleling the secrets pattern in
[ADR-035](../../../../docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets).
At M3.1 we ship one entry (QQL3); the dict literal is sufficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ConventionKind(StrEnum):
    """Kind of EODHD-vs-IB unit-of-quote convention.

    Extension policy: add a new variant when M3.2's empirical window
    or a future EODHD refresh surfaces a convention not covered here.
    Each variant pairs with a :class:`Convention` field-set and an
    explicit :func:`eodhd_to_ib_price` branch.
    """

    #: No conversion — EODHD price equals IB price. Default for unlisted
    #: symbols. Most Phase 1 instruments use this convention (IBTL /
    #: IBTM / QQQ / TLT).
    IDENTITY = "IDENTITY"

    #: Operator-confirmed manual scale factor: ``ib_price = eodhd_price /
    #: divisor``. Used when EODHD has lagged a reverse-split that IB has
    #: indexed (the M3.1 QQL3 case per ADR-050). Operator records the
    #: divisor + source + notes; the catalogue entry stays in effect
    #: until EODHD propagates the missing event.
    MANUAL_SCALE = "MANUAL_SCALE"


@dataclass(frozen=True, slots=True)
class Convention:
    """A per-instrument EODHD→IB price conversion convention.

    Fields:

    - ``kind`` — selects the conversion branch in :func:`eodhd_to_ib_price`.
    - ``divisor`` — for :attr:`ConventionKind.MANUAL_SCALE` only;
      ``ib_price = eodhd_price / divisor``. Must be > 0.
    - ``source`` — free-form provenance string (e.g. "IB live reference,
      M2-IB.6.2c"); audit trail for the catalogue entry.
    - ``notes`` — free-form notes (e.g. "EODHD-side recent reverse-split
      lag; revisit when /api/splits/QQQ3.LSE picks up the event").
    """

    kind: ConventionKind
    divisor: Decimal | None = None
    source: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.kind == ConventionKind.MANUAL_SCALE:
            if self.divisor is None:
                raise ValueError("MANUAL_SCALE convention requires a divisor")
            if self.divisor <= 0:
                raise ValueError(f"MANUAL_SCALE divisor must be > 0, got {self.divisor}")
        if self.kind == ConventionKind.IDENTITY and self.divisor is not None:
            raise ValueError("IDENTITY convention must not specify a divisor")


#: Sentinel default for symbols absent from the catalogue.
_IDENTITY_DEFAULT = Convention(kind=ConventionKind.IDENTITY)


#: Per-IB-symbol catalogue.
#:
#: ADR-050 catalogue v0.1 — single entry. Add rows here as the M3.2
#: empirical window or future EODHD refreshes surface conventions.
CONVENTIONS_BY_IB_SYMBOL: dict[str, Convention] = {
    # QQL3 (3× Nasdaq leveraged ETP, LSEETF; per ADR-047). EODHD reports
    # close ~$412 on 2026-05-06; IB live reference ~$39. The
    # 2026-05-06 EODHD-side investigation (scripts/probe_qql3_unit_of_quote.py)
    # refuted the adjusted_close hypothesis (close == adjusted_close;
    # ratio 1.0) and the currency hypothesis (CurrencyCode = USD). The
    # operative cause is a recent reverse-split that EODHD has not yet
    # propagated to its EOD feed (a known EODHD lag failure mode on
    # leveraged ETPs). Operator-confirmed divisor 10.0 against IB live
    # reference. Revisit when EODHD's /api/splits/QQQ3.LSE picks up the
    # event (at which point adjusted_close will diverge from close and
    # this row can either simplify to `use_adjusted_close` or move to
    # IDENTITY if EODHD also corrects close).
    "QQL3": Convention(
        kind=ConventionKind.MANUAL_SCALE,
        divisor=Decimal("10"),
        source="IB live reference, M2-IB.6.2c (2026-05-06)",
        notes=(
            "EODHD-side recent reverse-split lag; "
            "revisit when /api/splits/QQQ3.LSE picks up the event."
        ),
    ),
}


def eodhd_to_ib_price(*, ib_symbol: str, eodhd_price: Decimal) -> Decimal:
    """Convert an EODHD-quoted price to its IB-equivalent for ``ib_symbol``.

    Routes through :data:`CONVENTIONS_BY_IB_SYMBOL`. Symbols absent
    from the catalogue use the IDENTITY convention (no conversion).

    Examples
    --------
    Identity (default for unlisted symbols)::

        >>> eodhd_to_ib_price(ib_symbol="IBTL", eodhd_price=Decimal("420.5"))
        Decimal('420.5')

    Manual scale (QQL3, M3.1)::

        >>> eodhd_to_ib_price(ib_symbol="QQL3", eodhd_price=Decimal("412.94"))
        Decimal('41.294')

    Raises
    ------
    ValueError
        if ``eodhd_price`` is not strictly positive.
    """
    if eodhd_price <= 0:
        raise ValueError(f"eodhd_price must be > 0, got {eodhd_price}")

    convention = CONVENTIONS_BY_IB_SYMBOL.get(ib_symbol, _IDENTITY_DEFAULT)
    if convention.kind == ConventionKind.IDENTITY:
        return eodhd_price
    if convention.kind == ConventionKind.MANUAL_SCALE:
        assert convention.divisor is not None  # invariant from __post_init__
        return eodhd_price / convention.divisor

    raise AssertionError(f"unhandled convention kind {convention.kind!r} for {ib_symbol!r}")


__all__ = [
    "CONVENTIONS_BY_IB_SYMBOL",
    "Convention",
    "ConventionKind",
    "eodhd_to_ib_price",
]
