# blive

Live algorithmic execution engine for systematic strategies — sibling to [`btest`](../btest).

`blive` runs `btest`-DSL strategies against real brokers behind a hexagonal `BrokerPort`.
Interactive Brokers is the v1 adapter; paper / mock / shadow modes precede it.

## Where to start reading

- [`REQUIREMENTS.md`](REQUIREMENTS.md) — what this project is.
- [`CONTEXT_INVENTORY.md`](CONTEXT_INVENTORY.md) — every knowledge artefact and its status.
- [`CONTEXT_PROTOCOL.md`](CONTEXT_PROTOCOL.md) — the discipline that keeps the substrate coherent. Read **before** any edit.
- [`TASK_REGISTRY.md`](TASK_REGISTRY.md) — Phase 1 plan (M0–M3).
- [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md) — ADRs.

## Setup

Requires Python 3.11.x exactly. Use `uv`.

```bash
uv sync --extra dev
uv run pytest -q
```

## Status

Pre-implementation. M0 (skeleton & domain types) in flight; see `TASK_REGISTRY.md`.
