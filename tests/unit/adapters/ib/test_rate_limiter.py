"""Tests for :data:`blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS`.

The default table values are sourced from [KB-3 §9](../../../../../docs/kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults)
adapter budget defaults; these tests pin the numbers so unintentional drift
during refactoring is caught at CI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.rate_limiter import IB_DEFAULT_RATE_LIMITS
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter


def test_global_bucket_capacity_is_20() -> None:
    """KB-3 §1 + §9: 20 msg/sec ceiling = 60% headroom under IB's 50 msg/sec
    hard cap (3 violations terminate the API session)."""
    bucket = IB_DEFAULT_RATE_LIMITS.buckets["global"]
    assert bucket.capacity == 20
    assert bucket.refill_per_second == Decimal(20)


def test_historical_bucket_capacity_is_50() -> None:
    """KB-3 §2 + §9: ≤ 60 reqHistoricalData calls per 10-minute window;
    we ship 50 with 17% headroom."""
    bucket = IB_DEFAULT_RATE_LIMITS.buckets["historical"]
    assert bucket.capacity == 50
    # Refill: 50 tokens per 600 seconds.
    assert bucket.refill_per_second == Decimal(50) / Decimal(600)


def test_buckets_match_kb3_section_9() -> None:
    """KB-3 §9 table entries the M2-IB.2 adapter ships with."""
    assert set(IB_DEFAULT_RATE_LIMITS.buckets) == {"global", "historical"}


async def test_global_bucket_throttles_burst() -> None:
    """The G3-IB throttle test (TASK_REGISTRY M2-IB §"Exit criteria"): a
    burst of 60 calls/sec must throttle below the 20 msg/sec ceiling.

    With SimClock advancing only on ``sleep(...)`` calls, a burst that
    exhausts the bucket forces awaits — the limiter advances time and
    refills. After 60 acquires we should have crossed at least 2 seconds
    of simulated time (40 deficit tokens / 20 per second = 2 s minimum).
    """
    clock = SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))
    limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)

    start = clock.now()
    for _ in range(60):
        await limiter.acquire("global")
    elapsed = (clock.now() - start).total_seconds()

    # 20 tokens come "free" from the initial capacity; the remaining 40
    # require waiting 40 / 20 = 2 seconds at minimum.
    assert elapsed >= 2.0


async def test_historical_bucket_blocks_after_initial_capacity() -> None:
    """50 historical requests come "free"; the 51st must await ≥ 12 seconds
    (1 token / (50/600 per second) = 12 s)."""
    clock = SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))
    limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)

    # Drain the bucket.
    for _ in range(50):
        await limiter.acquire("historical")

    start = clock.now()
    await limiter.acquire("historical")
    elapsed = (clock.now() - start).total_seconds()
    assert elapsed >= 12.0
