"""Strategy loader.

Reads a blive ``LiveStrategyConfig`` YAML, imports the strategy module, calls
its ``build_strategy()`` to obtain a btest ``Strategy``, applies overrides
per DD-3 §9, computes the spec id per ADR-028, and returns a ``LiveStrategy``
bundle. Pure function modulo I/O.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import importlib.metadata as _metadata
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

# blive's own version (kept in sync with pyproject.toml).
import blive as _blive_pkg
from blive.strategy.config import LiveStrategyConfig


@dataclass(frozen=True, slots=True)
class LiveStrategy:
    """Resolved live-strategy bundle.

    The btest ``Strategy`` is held as ``Any`` to avoid binding blive's domain
    types to btest's DSL surface (which is the whole point of ADR-010 — we
    use btest by import without re-exporting its types as ours).
    """

    strategy: Any  # btest Strategy dataclass; opaque to blive's domain
    live_config: LiveStrategyConfig
    spec_id: str
    artefact_sha256_by_factor: Mapping[str, str]


def load_live_strategy(yaml_path: str | Path) -> LiveStrategy:
    """Load a ``LiveStrategy`` from a YAML config file.

    Steps (DD-3 §9):

    1. Parse YAML via Pydantic (``LiveStrategyConfig``).
    2. Validate ``strategy_id`` matches the parent directory name.
    3. Import the strategy module by dotted path.
    4. Call ``module.build_strategy(**build_strategy_kwargs)`` → btest ``Strategy``.
    5. Apply ``artefact_paths`` overrides via ``dataclasses.replace`` on each
       ``ExternalFactor``.
    6. Compute SHA-256 of every external-artefact file referenced by the
       resolved Strategy.
    7. Compute ``spec_id`` per ADR-028.
    """
    path = Path(yaml_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"live strategy YAML not found: {path}")

    raw = path.read_bytes()
    parsed = yaml.safe_load(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"live strategy YAML at {path} must be a mapping at the top level")

    cfg = LiveStrategyConfig(**parsed)

    # DD-3 §1 validation rule: strategy_id must match parent directory name.
    parent_dir = path.parent.name
    if parent_dir != cfg.strategy_id:
        raise ValueError(
            f"strategy_id mismatch: YAML at {path} has strategy_id={cfg.strategy_id!r} "
            f"but parent directory is {parent_dir!r}"
        )

    module = importlib.import_module(cfg.strategy_module)
    builder = getattr(module, "build_strategy", None)
    if builder is None or not callable(builder):
        raise AttributeError(
            f"strategy module {cfg.strategy_module!r} does not expose a callable "
            f"build_strategy(); see REQUIREMENTS §5.13"
        )
    strategy = builder(**dict(cfg.build_strategy_kwargs))

    strategy = _apply_artefact_overrides(strategy, cfg.artefact_paths.paths)

    artefact_sha256_by_factor = _hash_external_artefacts(strategy)

    spec_id = _compute_spec_id(
        canonical_yaml_bytes=raw,
        strategy_module=cfg.strategy_module,
        btest_version=_pkg_version("quantdsl-backtest"),
        blive_version=getattr(_blive_pkg, "__version__", "unknown"),
        artefact_sha256_by_factor=artefact_sha256_by_factor,
    )

    return LiveStrategy(
        strategy=strategy,
        live_config=cfg,
        spec_id=spec_id,
        artefact_sha256_by_factor=artefact_sha256_by_factor,
    )


def _apply_artefact_overrides(
    strategy: Any,
    overrides: Mapping[str, Path],
) -> Any:
    """Rewrite ``ExternalFactor.path`` for each named factor.

    Returns a new ``Strategy`` with the same identity except for the
    overridden factors. No-op if ``overrides`` is empty. DD-3 §6.
    """
    if not overrides:
        return strategy

    factors = dict(strategy.factors)
    unknown = set(overrides) - set(factors)
    if unknown:
        raise ValueError(
            f"artefact_paths references unknown factor(s): {sorted(unknown)!r}; "
            f"strategy.factors keys are {sorted(factors)!r}"
        )

    for name, new_path in overrides.items():
        if not new_path.exists():
            raise FileNotFoundError(
                f"artefact_paths['{name}'] points to a non-existent file: {new_path}"
            )
        factor = factors[name]
        if not hasattr(factor, "path"):
            raise TypeError(
                f"artefact_paths['{name}'] only valid for factors with a 'path' field "
                f"(e.g. ExternalFactor); factor type is {type(factor).__name__}"
            )
        factors[name] = dataclasses.replace(factor, path=str(new_path))

    return dataclasses.replace(strategy, factors=factors)


def _hash_external_artefacts(strategy: Any) -> dict[str, str]:
    """Compute SHA-256 of every artefact file referenced by an ``ExternalFactor``.

    Skips factors without a ``path`` field. Skips paths that do not point to
    an existing file (logging would be added by the caller in the M2 op flow;
    M1 is permissive so paper-mode tests can run without on-disk artefacts).
    """
    result: dict[str, str] = {}
    for name, factor in strategy.factors.items():
        path_attr = getattr(factor, "path", None)
        if path_attr is None:
            continue
        artefact_path = Path(str(path_attr))
        if not artefact_path.is_file():
            continue
        h = hashlib.sha256()
        with artefact_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        result[name] = h.hexdigest()
    return result


def _compute_spec_id(
    *,
    canonical_yaml_bytes: bytes,
    strategy_module: str,
    btest_version: str,
    blive_version: str,
    artefact_sha256_by_factor: Mapping[str, str],
) -> str:
    """Compute the strategy spec id per ADR-028.

    Inputs are concatenated as a deterministic JSON document then hashed —
    JSON ordering is enforced via ``sort_keys=True`` so the same logical
    inputs always produce the same digest.
    """
    payload = {
        "yaml_sha256": hashlib.sha256(canonical_yaml_bytes).hexdigest(),
        "strategy_module": strategy_module,
        "btest_version": btest_version,
        "blive_version": blive_version,
        "artefact_sha256_by_factor": dict(sorted(artefact_sha256_by_factor.items())),
    }
    serialised = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialised).hexdigest()


def _pkg_version(distribution: str) -> str:
    try:
        return _metadata.version(distribution)
    except _metadata.PackageNotFoundError:
        return "unknown"


__all__ = ["LiveStrategy", "load_live_strategy"]
