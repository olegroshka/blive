"""Wall-clock :class:`ClockPort` adapter."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone


class WallClock:
    """Real-time clock. Implements ``ClockPort``."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


__all__ = ["WallClock"]
