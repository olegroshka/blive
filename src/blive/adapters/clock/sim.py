"""Simulated :class:`ClockPort` adapter.

Time is held by the adapter and advanced explicitly via :meth:`tick` or
implicitly via :meth:`sleep`. ``sleep`` does **not** yield to the event
loop — this is intentional so deterministic tests can run synchronously.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class SimClock:
    """Controllable clock for tests. Implements ``ClockPort``."""

    def __init__(self, start: datetime | None = None) -> None:
        if start is None:
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        if start.tzinfo is None:
            raise ValueError("SimClock start must be timezone-aware")
        self._now = start

    def now(self) -> datetime:
        return self._now

    async def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("sleep seconds must be non-negative")
        self._now += timedelta(seconds=seconds)

    def tick(self, seconds: float) -> None:
        """Advance the clock without an ``await`` ceremony."""
        if seconds < 0:
            raise ValueError("tick seconds must be non-negative")
        self._now += timedelta(seconds=seconds)


__all__ = ["SimClock"]
