"""Pydantic v2 models for the live strategy YAML config.

SSOT is :doc:`../../docs/dd/config_schemas.md` (DD-3). Field shape locked by
:doc:`../../docs/decisions/DECISIONS.md` (ADR-028). Any field-shape change
is a multi-artefact edit per ``CONTEXT_PROTOCOL §3``.

All models are ``frozen=True`` so the resolved config is immutable post-load,
matching the crash-only design (ADR-009).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

log = logging.getLogger(__name__)

# DD-3 §1: Phase-1 NAV slice cap per ADR-020.
NAV_SLICE_HARD_CAP = Decimal("0.10")

# DD-3 §7: M4-tier RC keys that the M1 loader admits but ignores (forward-compat).
_M4_RC_OVERRIDE_KEYS = frozenset(
    {
        "max_gross_leverage",
        "target_net_exposure_tolerance",
        "max_abs_weight_per_name",
        "max_daily_loss_warn",
        "max_daily_loss_kill",
        "max_orders_per_sec_strategy",
        "max_orders_per_min_strategy",
        "max_orders_per_sec_global",
        "max_single_name_notional_pct",
        "max_price_deviation_pct",
        "drawdown_policy",
    }
)


class _BliveModel(BaseModel):
    """Shared base: forbid unknown keys, freeze the resolved object."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=False)


class LiveOverrides(_BliveModel):
    """Overlays ``Strategy.execution.live_overrides`` (DD-3 §2)."""

    time_in_force: Literal["DAY", "GTC", "IOC", "FOK", "OPG"] | None = None
    routing: Literal["SMART", "PRIMARY", "DIRECT"] | None = "SMART"
    direct_venue: str | None = None
    ib_algo: Literal["Adaptive", "TWAP", "VWAP", "Arrival Price", "Percentage of Volume"] | None = (
        None
    )
    ib_algo_params: Mapping[str, Any] = Field(default_factory=dict)
    outside_rth: bool = False

    @model_validator(mode="after")
    def _direct_venue_when_direct(self) -> "LiveOverrides":
        if self.routing == "DIRECT" and not self.direct_venue:
            raise ValueError("LiveOverrides.direct_venue required when routing == 'DIRECT'")
        if self.direct_venue is not None and self.routing != "DIRECT":
            raise ValueError("LiveOverrides.direct_venue only valid when routing == 'DIRECT'")
        if self.direct_venue is not None and not self.direct_venue.isupper():
            raise ValueError("LiveOverrides.direct_venue must be uppercase MIC")
        return self


class LiveBorrowProvider(_BliveModel):
    """Overlays ``Strategy.costs.live_borrow_provider`` (DD-3 §3)."""

    kind: Literal["ib", "static"]
    default_annual_rate: Decimal | None = None
    cache_ttl_seconds: int = 3600

    @field_validator("cache_ttl_seconds")
    @classmethod
    def _ttl_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("LiveBorrowProvider.cache_ttl_seconds must be ≥ 0")
        return v

    @model_validator(mode="after")
    def _static_requires_rate(self) -> "LiveBorrowProvider":
        if self.kind == "static" and self.default_annual_rate is None:
            raise ValueError(
                "LiveBorrowProvider.default_annual_rate required when kind == 'static'"
            )
        return self


class LiveFinancingProvider(_BliveModel):
    """Overlays ``Strategy.costs.live_financing_provider`` (DD-3 §4)."""

    kind: Literal["ib", "static"]
    base_rate_curve: Literal["ESTER", "SOFR", "static"] | None = None
    spread_bps: Decimal = Decimal("0")

    @field_validator("spread_bps")
    @classmethod
    def _spread_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("LiveFinancingProvider.spread_bps must be ≥ 0")
        return v


class LiveKillSwitch(_BliveModel):
    """Per-strategy live kill criteria (DD-3 §5)."""

    max_intraday_drawdown_bps: Decimal | None = None
    max_consecutive_rejects: int | None = 5
    max_consecutive_reject_window_seconds: int = 60
    max_position_age_days: int | None = None

    @model_validator(mode="after")
    def _validate_thresholds(self) -> "LiveKillSwitch":
        if self.max_intraday_drawdown_bps is not None and self.max_intraday_drawdown_bps <= 0:
            raise ValueError("LiveKillSwitch.max_intraday_drawdown_bps must be > 0 when set")
        if self.max_consecutive_rejects is not None and self.max_consecutive_rejects < 1:
            raise ValueError("LiveKillSwitch.max_consecutive_rejects must be ≥ 1 when set")
        if self.max_consecutive_reject_window_seconds < 1:
            raise ValueError("LiveKillSwitch.max_consecutive_reject_window_seconds must be ≥ 1")
        if self.max_position_age_days is not None and self.max_position_age_days < 1:
            raise ValueError("LiveKillSwitch.max_position_age_days must be ≥ 1 when set")
        return self


class ArtefactPaths(_BliveModel):
    """Per-factor overrides for ``ExternalFactor.path`` (DD-3 §6)."""

    paths: Mapping[str, Path] = Field(default_factory=dict)

    @field_validator("paths", mode="before")
    @classmethod
    def _expand_user(cls, v: Mapping[str, Any]) -> Mapping[str, Path]:
        return {k: Path(str(p)).expanduser() for k, p in v.items()}


class RiskOverrides(_BliveModel):
    """Per-strategy overrides for INV-4 thresholds (DD-3 §7).

    M1 fields-only at M1; M4-tier RC keys are admitted but logged-and-ignored
    (forward-compat per DD-3 §7) so a YAML that pre-populates them today does
    not reject when the rest of the RCs land at M4.
    """

    # Deliberately allow extra keys for the forward-compat behaviour described
    # in DD-3 §7 — the only model in DD-3 that does so.
    model_config = ConfigDict(extra="allow", frozen=True, arbitrary_types_allowed=False)

    max_data_staleness_intraday_sec: int = 300
    max_data_staleness_daily_sec: int = 86400
    outside_rth_allowed: bool = False
    max_model_artefact_age_days: int = 30
    model_artefact_warning_age_days: int = 21

    @model_validator(mode="after")
    def _validate(self) -> "RiskOverrides":
        if self.max_data_staleness_intraday_sec <= 0:
            raise ValueError("RiskOverrides.max_data_staleness_intraday_sec must be > 0")
        if self.max_data_staleness_daily_sec <= 0:
            raise ValueError("RiskOverrides.max_data_staleness_daily_sec must be > 0")
        if self.max_model_artefact_age_days < 1:
            raise ValueError("RiskOverrides.max_model_artefact_age_days must be ≥ 1")
        if self.model_artefact_warning_age_days < 1:
            raise ValueError("RiskOverrides.model_artefact_warning_age_days must be ≥ 1")
        if self.model_artefact_warning_age_days >= self.max_model_artefact_age_days:
            raise ValueError(
                "RiskOverrides.model_artefact_warning_age_days must be < "
                "max_model_artefact_age_days (warn before block)"
            )
        # Forward-compat: log-and-ignore unknown keys that are M4-tier.
        extra: dict[str, Any] = self.__pydantic_extra__ or {}
        for key in extra:
            if key in _M4_RC_OVERRIDE_KEYS:
                log.warning(
                    "RiskOverrides: ignoring forward-compat M4-tier RC override key %r "
                    "(lands at M4 per DD-3 §7)",
                    key,
                )
            else:
                raise ValueError(f"RiskOverrides: unknown key {key!r}")
        return self


class LiveStrategyConfig(_BliveModel):
    """Top-level YAML at ``~/.blive/strategies/{strategy_id}/live.yaml`` (DD-3 §1)."""

    strategy_id: str
    strategy_module: str
    build_strategy_kwargs: Mapping[str, Any] = Field(default_factory=dict)
    nav_slice: Decimal
    live_overrides: LiveOverrides = Field(default_factory=LiveOverrides)
    live_borrow_provider: LiveBorrowProvider | None = None
    live_financing_provider: LiveFinancingProvider | None = None
    live_kill_switch: LiveKillSwitch | None = None
    artefact_paths: ArtefactPaths = Field(default_factory=ArtefactPaths)
    risk_overrides: RiskOverrides = Field(default_factory=RiskOverrides)

    @field_validator("strategy_id")
    @classmethod
    def _validate_strategy_id(cls, v: str) -> str:
        if not v or not all(c.isalnum() or c == "_" for c in v) or not v.islower():
            raise ValueError(
                f"LiveStrategyConfig.strategy_id must be non-empty lowercase "
                f"[a-z0-9_]+, got {v!r}"
            )
        return v

    @field_validator("strategy_module")
    @classmethod
    def _validate_module_dotted(cls, v: str) -> str:
        if not v or " " in v or v.startswith(".") or v.endswith("."):
            raise ValueError(f"LiveStrategyConfig.strategy_module must be a dotted path, got {v!r}")
        for part in v.split("."):
            if not part.isidentifier():
                raise ValueError(
                    f"LiveStrategyConfig.strategy_module part {part!r} is not a valid identifier"
                )
        return v

    @field_validator("nav_slice")
    @classmethod
    def _validate_nav_slice(cls, v: Decimal) -> Decimal:
        # ADR-020: hard cap 10%.
        if v <= 0:
            raise ValueError("LiveStrategyConfig.nav_slice must be > 0")
        if v > NAV_SLICE_HARD_CAP:
            raise ValueError(
                f"LiveStrategyConfig.nav_slice exceeds Phase 1 hard cap of "
                f"{NAV_SLICE_HARD_CAP} (ADR-020), got {v}"
            )
        return v


__all__ = [
    "ArtefactPaths",
    "LiveBorrowProvider",
    "LiveFinancingProvider",
    "LiveKillSwitch",
    "LiveOverrides",
    "LiveStrategyConfig",
    "NAV_SLICE_HARD_CAP",
    "RiskOverrides",
]
