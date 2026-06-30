# Archived scripts

One-off wire-validation probes and superseded run drivers from the M2-IB ladder.
Kept for traceability (they're cited by name in `TASK_REGISTRY.md`, the M2-IB
retro, and `INV-14`), but no longer part of the active execution path. Moved here
2026-06-29 during a declutter; restore to `scripts/` if a probe is needed again.

- `probe_ib_*.py` — M2-IB.2/.3/.4 handshake / read / resolve / market-data / submit wire probes.
- `probe_qql3_*.py`, `probe_tqqq_*.py` — M2-IB.6 PRIIPs / PMA-cap / unit-of-quote investigations.
- `run_m2ib5_paper.py` — M2-IB.5 single-instrument CAC.PA driver (closed-early per registry).
- `run_today_sfera_signal.py` — superseded by `scripts/execute_sfera_strategy.py` (generalized, S-code, DB+file sources, MOO).

Active drivers remain in `scripts/`: `execute_sfera_strategy.py`, `list_positions.py`,
`run_m2ib6_ib_paper.py` (UK-listed QQL3/IBTL/IBTM path), `refresh_eodhd_*.py`.
