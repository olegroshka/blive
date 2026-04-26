---
id: RETRO-M{N}
title: M{N} Retrospective
status: DRAFT
owner: Oleg
last_reviewed: YYYY-MM-DD
version: 1.0
sources:
  - TASK_REGISTRY.md M{N}
depends_on:
  - TASK_REGISTRY
referenced_by: []
---

# RETRO-M{N} — M{N} Retrospective

> **Frozen record.** This file is `STABLE` on first complete write and not edited thereafter. If a future session needs to add context, append a separate `RETRO-M{N}-addendum.md` rather than modifying this file.

## Date and session(s)

- **Date:** YYYY-MM-DD
- **Sessions involved:** [e.g., 2 sessions on YYYY-MM-DD and YYYY-MM-DD]
- **Closing milestone:** M{N}

## Gate status

**G_{N+1} status:** PASSED · PARTIAL · BLOCKED

| Exit criterion (from TASK_REGISTRY.md M{N}) | Status | Notes |
|---------------------------------------------|--------|-------|
| [criterion 1] | ✓ / ⚠ / ✗ | [evidence or reason for failure] |
| [criterion 2] | ✓ / ⚠ / ✗ | |
| [criterion 3] | ✓ / ⚠ / ✗ | |
| [criterion 4] | ✓ / ⚠ / ✗ | |

## Delivered vs plan

[Brief enumeration of what was actually shipped against the M_{N} deliverables list. Format as a table of plan vs reality.]

| Plan deliverable | Status | Notes |
|------------------|--------|-------|
| 1. [name] | ✓ done / ⚠ partial / ✗ blocked | [if not done, why] |
| 2. [name] | | |
| ... | | |

## Surprises

[3–7 items. What did we expect that turned out different? What did the work actually require that we didn't plan for? What was harder or easier than estimated?]

- 
- 
- 

## ADRs raised this milestone

[List ADRs filed during M_{N} work, with one-line summary of each. Empty list is fine.]

- ADR-NNN — [title]: [one-line rationale]

## OQs raised this milestone

[List OQs filed during M_{N} work, with one-line summary and current status. Empty list is fine.]

- OQ-NNN — [question]: [status, e.g., OPEN with target M_{N+1}]

## Substrate transitions

[Which artefacts changed status during M_{N}.]

| Artefact | Before | After |
|----------|--------|-------|
| DD-X | MISSING | STABLE |
| INV-Y | MISSING | DRAFT |
| ... | | |

## Effort vs estimate

- **Estimated:** [from TASK_REGISTRY M_{N} estimate]
- **Actual:** [hours / sessions]
- **Variance reason** (if > ±50%): [brief]

## Recommendations for NEXT_PROMPT M_{N+1}

[The most important section. What should the next milestone's kickoff prompt emphasise, change, or warn about? What did we learn in M_{N} that the M_{N+1} agent will benefit from?]

- 
- 
- 

## Recommendations for the discipline itself

[If anything in CONTEXT_PROTOCOL or the discipline at large needs amendment based on M_{N} experience, note it here. Prefer ADR-ising significant changes rather than informal accumulation.]

- 

## Cross-References

- [TASK_REGISTRY.md](../../TASK_REGISTRY.md) — M{N} plan and exit criteria.
- [CONTEXT_PROTOCOL.md §8.3.1](../../CONTEXT_PROTOCOL.md) — milestone-close protocol that mandated this retro.
- [ADR-024](../decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) — retro artefact type definition.
- [previous retro: RETRO-M{N-1}](M{N-1}_retrospective.md) — if applicable.

## Changelog

- **v1.0 (YYYY-MM-DD)** — initial (and only) write at M{N} close.
