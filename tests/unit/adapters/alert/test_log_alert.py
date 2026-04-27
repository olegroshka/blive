"""LogAlert tests."""

from __future__ import annotations

import logging

import pytest

from blive.adapters.alert.log import LogAlert
from blive.domain.types import Severity


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "severity,expected_level",
    [
        (Severity.LOW, logging.INFO),
        (Severity.MEDIUM, logging.WARNING),
        (Severity.HIGH, logging.ERROR),
        (Severity.CRITICAL, logging.CRITICAL),
    ],
)
async def test_log_alert_level_mapping(
    severity: Severity, expected_level: int, caplog: pytest.LogCaptureFixture
) -> None:
    alert = LogAlert(logger=logging.getLogger("blive.alert.test"))
    with caplog.at_level(logging.DEBUG, logger="blive.alert.test"):
        await alert.send(severity, subject="test", body="body")
    assert any(rec.levelno == expected_level for rec in caplog.records)
    assert any("test" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test_log_alert_empty_subject_raises() -> None:
    alert = LogAlert()
    with pytest.raises(ValueError, match="subject"):
        await alert.send(Severity.LOW, subject="", body="body")
