"""Loader tests — YAML parse + module import + spec id determinism."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from textwrap import dedent

import pytest

from blive.strategy.loader import load_live_strategy


@pytest.fixture
def fake_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create a tiny module exposing ``build_strategy()`` returning a stub strategy.

    Uses a unique module name per test to avoid leftover ``sys.modules`` state.
    """
    import sys
    import textwrap
    import uuid

    module_name = f"_blive_test_strategy_{uuid.uuid4().hex}"
    module_path = tmp_path / "_strategy_pkg"
    module_path.mkdir()
    (module_path / "__init__.py").write_text("")
    (module_path / f"{module_name}.py").write_text(textwrap.dedent("""
            from dataclasses import dataclass

            @dataclass(frozen=True)
            class _StubFactor:
                name: str
                path: str = ""

            @dataclass(frozen=True)
            class _StubPortfolio:
                instrument: str
                target_leverage: float

            @dataclass(frozen=True)
            class _StubStrategy:
                factors: dict
                portfolio: _StubPortfolio

            def build_strategy(theta=0.08):
                return _StubStrategy(
                    factors={
                        "f1": _StubFactor(name="f1", path="/dev/null"),
                    },
                    portfolio=_StubPortfolio(instrument="X", target_leverage=1.0),
                )
            """))
    monkeypatch.syspath_prepend(str(tmp_path))
    full_dotted = f"_strategy_pkg.{module_name}"
    yield full_dotted
    sys.modules.pop(full_dotted, None)
    sys.modules.pop("_strategy_pkg", None)


def _write_yaml(strategy_id: str, dirpath: Path, dotted: str, **extra) -> Path:
    sd = dirpath / strategy_id
    sd.mkdir()
    body = f"strategy_id: {strategy_id}\n" f"strategy_module: {dotted}\n" f"nav_slice: '0.05'\n"
    for k, v in extra.items():
        body += f"{k}: {v}\n"
    p = sd / "live.yaml"
    p.write_text(body)
    return p


def test_load_live_strategy_basic_path(tmp_path: Path, fake_module: str) -> None:
    yaml_path = _write_yaml("x_strategy", tmp_path, fake_module)
    live = load_live_strategy(yaml_path)
    assert live.live_config.strategy_id == "x_strategy"
    assert live.live_config.nav_slice == Decimal("0.05")
    assert live.spec_id and len(live.spec_id) == 64  # sha256 hex
    # No artefacts on disk in fake_module ⇒ empty hash map
    assert live.artefact_sha256_by_factor == {}


def test_strategy_id_must_match_parent_dir(tmp_path: Path, fake_module: str) -> None:
    sd = tmp_path / "actual_dir"
    sd.mkdir()
    p = sd / "live.yaml"
    p.write_text(f"strategy_id: claimed_id\nstrategy_module: {fake_module}\nnav_slice: '0.05'\n")
    with pytest.raises(ValueError, match="strategy_id mismatch"):
        load_live_strategy(p)


def test_missing_yaml_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="live strategy YAML"):
        load_live_strategy(tmp_path / "no_such_file.yaml")


def test_module_without_build_strategy_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import textwrap

    pkg = tmp_path / "_lib"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "no_builder.py").write_text(textwrap.dedent("X = 1\n"))
    monkeypatch.syspath_prepend(str(tmp_path))

    yaml_path = _write_yaml("y_strategy", tmp_path, "_lib.no_builder")
    with pytest.raises(AttributeError, match="build_strategy"):
        load_live_strategy(yaml_path)


def test_spec_id_deterministic(tmp_path: Path, fake_module: str) -> None:
    yaml_path = _write_yaml("z_strategy", tmp_path, fake_module)
    live_a = load_live_strategy(yaml_path)
    live_b = load_live_strategy(yaml_path)
    assert live_a.spec_id == live_b.spec_id


def test_spec_id_changes_with_yaml(tmp_path: Path, fake_module: str) -> None:
    yaml_a = _write_yaml("a_strategy", tmp_path, fake_module)
    live_a = load_live_strategy(yaml_a)

    sd2 = tmp_path / "b_strategy"
    sd2.mkdir()
    p2 = sd2 / "live.yaml"
    p2.write_text(f"strategy_id: b_strategy\nstrategy_module: {fake_module}\nnav_slice: '0.07'\n")
    live_b = load_live_strategy(p2)
    assert live_a.spec_id != live_b.spec_id


def test_artefact_paths_unknown_factor_rejected(tmp_path: Path, fake_module: str) -> None:
    artefact_file = tmp_path / "fake_artefact.bin"
    artefact_file.write_bytes(b"hello")
    sd = tmp_path / "v_strategy"
    sd.mkdir()
    p = sd / "live.yaml"
    p.write_text(dedent(f"""
            strategy_id: v_strategy
            strategy_module: {fake_module}
            nav_slice: '0.05'
            artefact_paths:
              paths:
                does_not_exist_factor: {artefact_file.as_posix()}
            """).strip())
    with pytest.raises(ValueError, match="unknown factor"):
        load_live_strategy(p)
