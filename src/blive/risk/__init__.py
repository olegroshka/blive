"""Risk engine.

M1 subset implementing checks RC-08 (stale data), RC-09 (market hours),
RC-12 (model artefact freshness), RC-13 (kill-switch armed) per
:doc:`../../docs/inv/risk_checks.md` (INV-4). Other RCs land at M4.

Architecturally enforces ADR-008 no-bypass: blive's pipeline composes the
Sizer → ``RiskEngine.approve()`` → broker; there is no path for
``Strategy``/``Sizer`` code to reach the broker without traversing this
gate.
"""

from blive.domain.events import RiskBreach, RiskBreachSeverity, RiskCheckCode
from blive.risk.checks import (
    BREACH_TOPIC,
    KillSwitch,
    RiskEngine,
    RiskEngineConfig,
    RiskInputs,
)

__all__ = [
    "BREACH_TOPIC",
    "KillSwitch",
    "RiskBreach",
    "RiskBreachSeverity",
    "RiskCheckCode",
    "RiskEngine",
    "RiskEngineConfig",
    "RiskInputs",
]
