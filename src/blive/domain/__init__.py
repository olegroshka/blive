"""Domain layer — broker-neutral core (ADR-004).

This package may not import from ``blive.adapters`` or third-party broker
SDKs (e.g. ``ib_async``). The contract is enforced by import-linter; see
``pyproject.toml`` ``[tool.importlinter]``.
"""
