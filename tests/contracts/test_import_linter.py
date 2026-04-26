"""Negative test: a deliberately-violating package triggers the import-linter contract.

Verifies that the rule shape used in ``pyproject.toml`` (``forbidden`` contract,
domain depending on adapters) actually fires when a domain module imports an
adapters module. Hermetic — runs against a temp package, not the live tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

# In-process equivalent of the ``lint-imports`` CLI: take the config path
# from sys.argv[1], invoke the API, exit non-zero if any contract is broken.
# Avoids depending on the script entry point being on PATH.
_LINT_IMPORTS_RUNNER = textwrap.dedent("""\
    import sys
    from importlinter.cli import lint_imports
    sys.exit(lint_imports(config_filename=sys.argv[1], no_cache=True))
    """)


def test_violation_is_caught(tmp_path: Path) -> None:
    """Construct a tiny `proj.{domain,adapters}` package with a deliberate
    domain → adapters import. Run import-linter against it and assert it
    reports the contract broken with non-zero exit.
    """
    proj = tmp_path / "proj"
    domain = proj / "domain"
    adapters = proj / "adapters"
    domain.mkdir(parents=True)
    adapters.mkdir(parents=True)

    (proj / "__init__.py").write_text("")
    (domain / "__init__.py").write_text("")
    (adapters / "__init__.py").write_text("")
    (adapters / "thing.py").write_text("VALUE = 42\n")
    # The deliberate violation:
    (domain / "violation.py").write_text("from proj.adapters.thing import VALUE\n")

    config = tmp_path / ".importlinter"
    config.write_text(textwrap.dedent("""\
            [importlinter]
            root_packages =
                proj

            [importlinter:contract:domain-vs-adapters]
            name = Domain must not import adapters
            type = forbidden
            source_modules =
                proj.domain
            forbidden_modules =
                proj.adapters
            """))

    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", _LINT_IMPORTS_RUNNER, str(config)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0, (
        "expected import-linter to fail on violation; "
        f"stdout=\n{result.stdout}\nstderr=\n{result.stderr}"
    )
    # The CLI prints "BROKEN" (uppercase) for failed contracts.
    assert "BROKEN" in result.stdout, f"expected 'BROKEN' in output; got:\n{result.stdout}"


def test_clean_package_passes(tmp_path: Path) -> None:
    """Sanity check: same shape WITHOUT the violation passes (no false positives)."""
    proj = tmp_path / "proj"
    domain = proj / "domain"
    adapters = proj / "adapters"
    domain.mkdir(parents=True)
    adapters.mkdir(parents=True)

    (proj / "__init__.py").write_text("")
    (domain / "__init__.py").write_text("")
    (adapters / "__init__.py").write_text("")
    (adapters / "thing.py").write_text("VALUE = 42\n")
    (domain / "ok.py").write_text("VALUE = 1\n")  # no cross-layer import

    config = tmp_path / ".importlinter"
    config.write_text(textwrap.dedent("""\
            [importlinter]
            root_packages =
                proj

            [importlinter:contract:domain-vs-adapters]
            name = Domain must not import adapters
            type = forbidden
            source_modules =
                proj.domain
            forbidden_modules =
                proj.adapters
            """))

    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", _LINT_IMPORTS_RUNNER, str(config)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, (
        "expected import-linter to pass on clean package; "
        f"stdout=\n{result.stdout}\nstderr=\n{result.stderr}"
    )
    assert "KEPT" in result.stdout, result.stdout
