"""RiskEngine — M1 subset.

Implements RC-08 / RC-09 / RC-12 / RC-13 from
:doc:`../../docs/inv/risk_checks.md` (INV-4). Other RCs land at M4 when the
full RiskEngine is fleshed out.

Order of evaluation (per INV-4 §"Order of evaluation"): RC-13 (kill-switch)
→ RC-08 (stale data) → RC-09 (market hours) → RC-12 (model artefact age).
Higher RCs short-circuit; the first failure produces a ``RiskBreach`` and
the order is not approved.

The engine is **pure** in the sense that ``approve()`` produces decisions
deterministically from its inputs — but it owns one mutable dependency,
the ``KillSwitch``, which is the system-wide latch armed by external
events (manual UI, IB disconnect, etc.). The latch is observed via a
trivial accessor; no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping

from blive.domain.events import RiskBreach, RiskBreachSeverity, RiskCheckCode
from blive.domain.types import Bar, Instrument, Order

# --- Topic name (INV-5 row `risk.breach`) -----------------------------------

BREACH_TOPIC = "risk.breach"


# --- Kill-switch latch -------------------------------------------------------


@dataclass
class KillSwitch:
    """System-wide latch (RC-13).

    Armed by external sources (manual UI, IB disconnect, etc.) per
    :doc:`../../REQUIREMENTS.md` §5.5. Once armed, every order is blocked
    until cleared by an explicit human action (``M4`` adds the resume flow;
    M1 keeps the latch + accessor only).
    """

    _armed: bool = False
    _armed_reason: str = ""

    @property
    def armed(self) -> bool:
        return self._armed

    @property
    def reason(self) -> str:
        return self._armed_reason

    def arm(self, reason: str) -> None:
        if not reason:
            raise ValueError("KillSwitch.arm requires a non-empty reason")
        self._armed = True
        self._armed_reason = reason

    def clear(self) -> None:
        # M4 will guard this with a confirmation token; M1 keeps the simplest
        # mechanism so tests can exercise it.
        self._armed = False
        self._armed_reason = ""


# --- RiskEngine config + inputs ----------------------------------------------


@dataclass(frozen=True, slots=True)
class RiskEngineConfig:
    """Per-strategy thresholds; sourced from
    ``LiveStrategyConfig.risk_overrides`` (DD-3 §7).
    """

    max_data_staleness_intraday_sec: int = 300
    max_data_staleness_daily_sec: int = 86400
    outside_rth_allowed: bool = False
    max_model_artefact_age_days: int = 30
    model_artefact_warning_age_days: int = 21
    # Whether the strategy currently rebalances on intraday or EOD bars; set
    # at strategy load time from the btest ``DataConfig.frequency``.
    is_intraday: bool = False


@dataclass(frozen=True, slots=True)
class RiskInputs:
    """Per-decision inputs."""

    last_bar: Bar | None  # most recent bar for the relevant instrument; None ⇒ no data
    is_market_open: bool  # provided by the engine's calendar (M1: caller wires this in)
    artefact_paths: Mapping[str, Path] = field(default_factory=dict)


# --- The engine ---------------------------------------------------------------


class RiskEngine:
    """M1 RiskEngine.

    ADR-008 no-bypass: callers feed orders through ``approve()``; the
    return is either the input order (approved, possibly with a non-block
    warning ``RiskBreach``) or a single ``RiskBreach`` with severity ==
    ``BLOCK`` and the order is dropped.
    """

    def __init__(
        self,
        *,
        config: RiskEngineConfig,
        kill_switch: KillSwitch,
        strategy_id: str,
    ) -> None:
        self._config = config
        self._kill_switch = kill_switch
        self._strategy_id = strategy_id

    @property
    def config(self) -> RiskEngineConfig:
        return self._config

    def approve(
        self,
        order: Order,
        *,
        inputs: RiskInputs,
        now: datetime,
    ) -> tuple[Order | None, list[RiskBreach]]:
        """Apply RC-13, RC-08, RC-09, RC-12 in order.

        Returns ``(order, breaches)`` where:

        - ``order is None`` iff a ``BLOCK`` breach fired; the caller drops it.
        - ``order`` is the original (M1: never scaled) when no ``BLOCK`` fired.
        - ``breaches`` is the full list (warns and any blocks); always at most
          one ``BLOCK`` because checks short-circuit.
        """
        breaches: list[RiskBreach] = []

        # RC-13 — kill-switch armed
        if self._kill_switch.armed:
            breaches.append(
                RiskBreach(
                    strategy_id=self._strategy_id,
                    check=RiskCheckCode.RC_13,
                    severity=RiskBreachSeverity.BLOCK,
                    detail=f"kill-switch armed: {self._kill_switch.reason}",
                    time_utc=now,
                )
            )
            return None, breaches

        # RC-08 — stale data
        staleness_breach = self._check_stale_data(inputs.last_bar, order.instrument, now)
        if staleness_breach is not None:
            breaches.append(staleness_breach)
            return None, breaches

        # RC-09 — market hours
        if not inputs.is_market_open and not self._config.outside_rth_allowed:
            breaches.append(
                RiskBreach(
                    strategy_id=self._strategy_id,
                    check=RiskCheckCode.RC_09,
                    severity=RiskBreachSeverity.BLOCK,
                    detail=(
                        f"market closed for {order.instrument.symbol} on "
                        f"{order.instrument.venue}; outside_rth not allowed"
                    ),
                    time_utc=now,
                )
            )
            return None, breaches

        # RC-12 — model-artefact freshness
        artefact_block, artefact_warn = self._check_artefact_freshness(inputs.artefact_paths, now)
        if artefact_warn is not None:
            breaches.append(artefact_warn)
        if artefact_block is not None:
            breaches.append(artefact_block)
            return None, breaches

        return order, breaches

    # --- internals ----------------------------------------------------------

    def _check_stale_data(
        self,
        last_bar: Bar | None,
        instrument: Instrument,
        now: datetime,
    ) -> RiskBreach | None:
        if last_bar is None:
            return RiskBreach(
                strategy_id=self._strategy_id,
                check=RiskCheckCode.RC_08,
                severity=RiskBreachSeverity.BLOCK,
                detail=f"no bar received for {instrument.symbol}",
                time_utc=now,
            )
        threshold_sec = (
            self._config.max_data_staleness_intraday_sec
            if self._config.is_intraday
            else self._config.max_data_staleness_daily_sec
        )
        delta = now - last_bar.close_time_utc
        if delta > timedelta(seconds=threshold_sec):
            return RiskBreach(
                strategy_id=self._strategy_id,
                check=RiskCheckCode.RC_08,
                severity=RiskBreachSeverity.BLOCK,
                detail=(
                    f"bar for {instrument.symbol} is stale: {int(delta.total_seconds())}s "
                    f"old > threshold {threshold_sec}s"
                ),
                time_utc=now,
            )
        return None

    def _check_artefact_freshness(
        self,
        artefact_paths: Mapping[str, Path],
        now: datetime,
    ) -> tuple[RiskBreach | None, RiskBreach | None]:
        """Return ``(block, warn)`` per ADR-022."""
        if not artefact_paths:
            return None, None

        oldest_age_days: float = 0.0
        oldest_name = ""
        for name, path in artefact_paths.items():
            if not path.is_file():
                # No artefact on disk ⇒ block: a strategy that requires an
                # artefact path cannot be sized without it.
                return (
                    RiskBreach(
                        strategy_id=self._strategy_id,
                        check=RiskCheckCode.RC_12,
                        severity=RiskBreachSeverity.BLOCK,
                        detail=f"model artefact {name!r} missing at {path}",
                        time_utc=now,
                    ),
                    None,
                )
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=now.tzinfo)
            age_days = (now - mtime).total_seconds() / 86400.0
            if age_days > oldest_age_days:
                oldest_age_days = age_days
                oldest_name = name

        if oldest_age_days >= self._config.max_model_artefact_age_days:
            return (
                RiskBreach(
                    strategy_id=self._strategy_id,
                    check=RiskCheckCode.RC_12,
                    severity=RiskBreachSeverity.BLOCK,
                    detail=(
                        f"model artefact {oldest_name!r} is {oldest_age_days:.1f}d old; "
                        f"hard threshold {self._config.max_model_artefact_age_days}d "
                        f"(ADR-022)"
                    ),
                    time_utc=now,
                ),
                None,
            )
        if oldest_age_days >= self._config.model_artefact_warning_age_days:
            return (
                None,
                RiskBreach(
                    strategy_id=self._strategy_id,
                    check=RiskCheckCode.RC_12,
                    severity=RiskBreachSeverity.WARN,
                    detail=(
                        f"model artefact {oldest_name!r} is {oldest_age_days:.1f}d old; "
                        f"warning threshold {self._config.model_artefact_warning_age_days}d "
                        f"(ADR-022)"
                    ),
                    time_utc=now,
                ),
            )
        return None, None


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
