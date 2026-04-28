"""IB rate-limit defaults.

Provides :data:`IB_DEFAULT_RATE_LIMITS` — the
:class:`blive.adapters.shared.rate_limiter.RateLimitConfig` that the IB
adapter ships with, parameterised per [ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)
(which generalised [ADR-031](../../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters)
to per-bucket configuration). Numerical values lifted from [KB-3 §9](../../../../docs/kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults)
adapter budget defaults table.

Buckets:

- ``global`` — 20 tokens capacity, refill 20/s. Matches IB's 50 msg/s hard
  cap with 60% headroom (3 violations terminate the API session per
  [KB-3 §1](../../../../docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle));
  outbound IB calls draw from this bucket.
- ``historical`` — 50 tokens capacity, refill ≈ 0.0833/s (= 50 per 10
  minutes). Matches the [KB-3 §2](../../../../docs/kb/ib_pacing_spec.md#2-historical-data-pacing)
  60-per-10-minute hard cap with 17% headroom; ``reqHistoricalData``
  warm-up requests draw from this bucket.

Per-strategy sub-bucket enforcement ([INV-4 RC-05](../../../../docs/inv/risk_checks.md))
is forward-compat-ignored at M2; lands at M4 alongside the full RiskEngine
through the [DD-3 §7 RiskOverrides](../../../../docs/dd/config_schemas.md#7-riskoverrides)
surface. Until M4, callers that need per-strategy throttling can register
dynamic buckets keyed by ``f"strategy_{strategy_id}"`` if needed.

Sub-rules that the token-bucket algorithm cannot represent (per
[KB-3 §2](../../../../docs/kb/ib_pacing_spec.md#2-historical-data-pacing)):

- "≤ 1 per 15 seconds for identical request" — per-request dedup;
  enforce inside ``IBMarketData.historical_bars`` at M2-IB.3 if needed.
- "BID_ASK whatToShow counts double" — per-call multiplier; enforce by
  acquiring 2 tokens (``rate_limiter.acquire("historical", tokens=2)``)
  for BID_ASK requests at M2-IB.3.

These are per-call concerns, not bucket-level concerns; the bucket structure
above remains canonical.
"""

from __future__ import annotations

from decimal import Decimal

from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
)

# Refill rate for the historical bucket: 50 tokens per 600 seconds (10 minutes).
# Stored as a Decimal so the rate-limiter's clock arithmetic stays exact.
_HISTORICAL_REFILL_PER_SECOND: Decimal = Decimal(50) / Decimal(600)


IB_DEFAULT_RATE_LIMITS: RateLimitConfig = RateLimitConfig(
    buckets={
        "global": RateLimitBucket(
            capacity=20,
            refill_per_second=Decimal(20),
        ),
        "historical": RateLimitBucket(
            capacity=50,
            refill_per_second=_HISTORICAL_REFILL_PER_SECOND,
        ),
    },
)


__all__ = [
    "IB_DEFAULT_RATE_LIMITS",
]
