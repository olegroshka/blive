"""Logger-backed :class:`AlertPort` adapter.

Writes alert records to the standard library logger. The intended use is
M1's RiskEngine breach surface; richer adapters (Slack / email) land at M7.
"""

from __future__ import annotations

import logging

from blive.domain.types import Severity


class LogAlert:
    """Implements ``AlertPort``. Maps blive ``Severity`` to log levels."""

    _LEVEL_MAP = {
        Severity.LOW: logging.INFO,
        Severity.MEDIUM: logging.WARNING,
        Severity.HIGH: logging.ERROR,
        Severity.CRITICAL: logging.CRITICAL,
    }

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("blive.alert")

    async def send(self, severity: Severity, subject: str, body: str) -> None:
        if not subject:
            raise ValueError("LogAlert.send: subject must be non-empty")
        level = self._LEVEL_MAP[severity]
        self._logger.log(level, "[%s] %s — %s", severity.value, subject, body)


__all__ = ["LogAlert"]
