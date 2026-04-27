"""Order sizing.

Pure-function conversion from ``target_weights`` (one entry per instrument
key, value in ``[-1, 1]``) into a list of broker-neutral ``Order`` objects,
applying the rounding policy from
:doc:`../../docs/decisions/DECISIONS.md` (ADR-027) and the NAV-slice cap
from ADR-020 (validated upstream by ``LiveStrategyConfig.nav_slice``).
"""

from blive.sizing.sizer import (
    SizerInput,
    quantize_share_qty,
    size_orders,
)

__all__ = [
    "SizerInput",
    "quantize_share_qty",
    "size_orders",
]
