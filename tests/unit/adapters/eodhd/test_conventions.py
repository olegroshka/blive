"""Tests for the per-instrument EODHD-vs-IB convention catalogue.

Operationalises [ADR-050 PROPOSED](../../../../docs/decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from blive.adapters.eodhd.conventions import (
    CONVENTIONS_BY_IB_SYMBOL,
    Convention,
    ConventionKind,
    eodhd_to_ib_price,
)


def test_identity_convention_for_unlisted_symbol_is_a_no_op() -> None:
    """Symbols absent from the catalogue fall through to IDENTITY (no
    conversion). Most Phase 1 instruments use this convention (IBTL /
    IBTM / QQQ / TLT) — this is the load-bearing default."""
    out = eodhd_to_ib_price(ib_symbol="IBTL", eodhd_price=Decimal("420.5"))
    assert out == Decimal("420.5")


def test_qql3_manual_scale_divides_by_ten() -> None:
    """QQL3 catalogue entry per ADR-050 — divisor 10 against IB live
    reference. EODHD close $412.94 → IB-equivalent $41.294."""
    out = eodhd_to_ib_price(ib_symbol="QQL3", eodhd_price=Decimal("412.94"))
    assert out == Decimal("41.294")


def test_qql3_manual_scale_preserves_decimal_precision() -> None:
    """No float conversion — Decimal arithmetic only, per ADR-027 sizer
    purity."""
    out = eodhd_to_ib_price(ib_symbol="QQL3", eodhd_price=Decimal("383.20"))
    assert out == Decimal("38.320")
    assert isinstance(out, Decimal)


def test_zero_or_negative_price_rejected() -> None:
    """Defensive — a non-positive EODHD price is nonsensical."""
    with pytest.raises(ValueError, match="must be > 0"):
        eodhd_to_ib_price(ib_symbol="QQL3", eodhd_price=Decimal("0"))
    with pytest.raises(ValueError, match="must be > 0"):
        eodhd_to_ib_price(ib_symbol="QQL3", eodhd_price=Decimal("-1"))


def test_manual_scale_requires_positive_divisor() -> None:
    with pytest.raises(ValueError, match="requires a divisor"):
        Convention(kind=ConventionKind.MANUAL_SCALE)
    with pytest.raises(ValueError, match="must be > 0"):
        Convention(kind=ConventionKind.MANUAL_SCALE, divisor=Decimal("0"))
    with pytest.raises(ValueError, match="must be > 0"):
        Convention(kind=ConventionKind.MANUAL_SCALE, divisor=Decimal("-1"))


def test_identity_convention_must_not_specify_divisor() -> None:
    """Field hygiene — IDENTITY + divisor is a contradiction."""
    with pytest.raises(ValueError, match="must not specify a divisor"):
        Convention(kind=ConventionKind.IDENTITY, divisor=Decimal("10"))


def test_qql3_catalogue_entry_documented() -> None:
    """The QQL3 entry must carry source + notes for audit per ADR-050.

    Operator-curated catalogue entries are useless without provenance —
    this test enforces that the canonical entry stays documented.
    """
    qql3 = CONVENTIONS_BY_IB_SYMBOL["QQL3"]
    assert qql3.kind == ConventionKind.MANUAL_SCALE
    assert qql3.divisor == Decimal("10")
    assert "IB live reference" in qql3.source
    assert qql3.notes  # non-empty notes


def test_phase1_non_qql3_tradables_not_in_catalogue() -> None:
    """IBTL / IBTM / QQQ / TLT use IDENTITY (no entry needed) per ADR-050.

    A premature entry for these would mask catalogue-miss errors and
    add maintenance burden. Their absence is load-bearing.
    """
    for symbol in ("IBTL", "IBTM", "QQQ", "TLT"):
        assert symbol not in CONVENTIONS_BY_IB_SYMBOL
