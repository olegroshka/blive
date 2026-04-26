# Methodology Amendments Log

This file records material amendments to the **Cognitive Cartography** discipline as articulated in [`CONTEXT_PROTOCOL.md`](../../CONTEXT_PROTOCOL.md). Each entry captures the amendment, motivation, ADRs introduced, artefacts changed, and the implications for the next iteration of the methodology paper at [`docs/method/paper/cognitive_cartography.tex`](paper/cognitive_cartography.tex).

The paper is updated separately when amendments accumulate enough to warrant a new edition; this log is the staging ground for that update.

## Convention

Each entry has:

- Heading: `## Amendment v{N}.{N} — {short title}`
- Date
- Motivation
- ADR(s) introduced
- Substrate artefacts changed
- Paper sections affected (for next paper iteration)
- Cross-references

Append-only. Resolved amendments are not edited; if a later amendment partly reverses or modifies an earlier one, the new entry references the prior with a "supersedes" note.

---

## Amendment v0.2 — Agentic-Execution Layer

**Date:** 2026-04-26

**ADR:** [ADR-026 — Adopt agentic-execution layer; reduce human action surface](../decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface)

### Motivation

The discipline as articulated in `CONTEXT_PROTOCOL` v0.2 placed substantial manual burden on the human operator: warm-up reading, edit-protocol enforcement, cross-reference tracking, ADR / OQ writing, retrospective drafting, NEXT_PROMPT updating, status-lifecycle management. The Gemini research plan ([`Research_Plan_for_Paper_Iteration_Gemini.md`](Research_Plan_for_Paper_Iteration_Gemini.md)) catalogued the rapid maturation of agentic memory architectures (MemGPT, Agentic Memory / Zettelkasten, Multi-Layer Memory, Sculptor / ARC, graph-native context, Recursive Language Models), demonstrating that both human practitioners (via the discipline) and AI researchers (via these architectures) had arrived at structurally similar substrate solutions.

The discipline's posture should reflect this convergence by repositioning itself as the **human-governance schema** over agentic execution rather than as a manual alternative to it. Without this repositioning, the methodology risks two failure modes: (a) being seen as obsolete once autonomous memory systems handle substrate execution natively, and (b) imposing manual burden that doesn't scale to projects of meaningful complexity.

### What the amendment changes

- The discipline's *content* is unchanged — six artefact categories, stable IDs, status lifecycle, edit protocol, propagation rules, anti-patterns all stand.
- The discipline's *execution model* shifts from "human-driven manual" to "human-governed, agent-executed".
- A **five-layer adoption stack** is codified:
  - **L0** — Substrate-aware warm-up agent (replaces manual file-list reading).
  - **L1** — Continuous integrity watchdog (background drift / orphan / staleness scans).
  - **L2** — In-situ ADR auto-drafting (capture decisions at the moment of decision).
  - **L3** — Auto-drafted retros and NEXT_PROMPTs (populate from observable state).
  - **L4** — Graph-native substrate (markdown views over a knowledge graph).
- **Adoption order:** L0 + L1 first (low cost, immediate utility, layer-independent); L2 + L3 after L0 / L1 prove reliable; L4 at discipline v2.0.
- The human's residual surface area refines to: intent declaration, decision approval, scope governance, voice authority on substantive prose.
- Implementation deferred: ADR-026 locks the *direction* and *posture*; concrete tooling and timing decisions live in OQ-028 (framework choice) and OQ-029 (timing).

### Substrate artefacts changed

- **`CONTEXT_PROTOCOL.md`** v0.2 → v0.3: new §11 specifies the division of labour and the layer stack; existing §11 (Self-Critique) renumbers to §12.
- **`docs/decisions/DECISIONS.md`** v0.3 → v0.4: ADR-026 added.
- **`docs/decisions/OPEN_QUESTIONS.md`** v0.1.3 → v0.1.4: OQ-028 (memory framework choice) and OQ-029 (implementation timing) added.
- **`CONTEXT_INVENTORY.md`**: row updates — KB-10 to v0.4 (26 ADRs); CONTEXT_PROTOCOL row to v0.3; KB-11 row reflecting OQ-028 / OQ-029; this file added to the file layout.
- **NEW** — `docs/method/Amendments_Log.md` (this file).

### Paper sections affected (for the next paper iteration)

The next iteration of [`docs/method/paper/cognitive_cartography.tex`](paper/cognitive_cartography.tex) should reflect this amendment. Specific sections:

- **Abstract.** Reframe the discipline's posture from "manual" to "human-governed, agent-executed". One sentence change in the closing claim.
- **§1 Introduction.** Add a brief preview of the human / agent division of labour as a complement to the substrate-vs-model thesis. The thesis itself stands; the execution model around it is what evolves.
- **§3 What We Inherit (foundations) — agentic-AI subsection.** Expand to discuss the convergence noted in this amendment. Cite Sculptor (Active Context Management), ARC, A-MEM (Agentic Memory / Zettelkasten), the Multi-Layer Memory framework, and graph-native context architectures alongside the existing references to RAG, MemGPT, generative agents, Reflexion, Constitutional AI. Empirical anchors from Gemini research plan to consider: the "17% Gap" study on epistemic decay; the ADR-as-control-mechanism study (10–14% efficiency gains).
- **§4 The Discipline.** Unchanged in content; add a brief "Note on execution" pointing forward to §11 (division of labour). The discipline as written is the layer-0 / fully-manual baseline; subsequent layers automate it without changing its semantics.
- **§7 The Practice in the Hand.** Add discussion of how human burden scales as agentic layers come online. The current §7 estimates the manual burden; the new §7 estimates burden under each layer.
- **§8 What Tooling Could Do.** Substantially expanded — much of what §8 currently sketches as "what tooling could help with" maps directly to L0 / L1 (warm-up bundlers, drift detectors, link checkers). Make the layer mapping explicit.
- **§9 Honest Costs and Limits.** Add the agentic-layer-specific failure modes from CONTEXT_PROTOCOL §11.4: agent confabulation, drafting bias drift, layer coupling, over-delegation, execution disagreement.
- **§10 Closing.** Reposition: discipline survives across model generations not because it must remain manual, but because the *governance schema* is durable while the *execution layer* evolves with the tooling. Substrate-engineering remains the leverage point; what changes is who performs the engineering.
- **§11 NEW (in paper).** A dedicated section on the human-governance / agent-execution division of labour, mirroring CONTEXT_PROTOCOL §11. Five-layer adoption stack figure (proposed visualisation: vertical stack with cost / value annotation per layer). Discussion of the relationship to autonomous memory architectures.
- **§5 Synthesis table (F6).** Consider adding a fourth column to the synthesis: "automated by which layer". Each discipline element maps to (cognitive principle, failure mode addressed, automation layer).
- **F6/F8 figures.** Possible new figure: "Five-layer adoption stack" — vertical stack showing what each layer automates, with current human-burden bars decreasing as layers come online.

### Conversation context (for paper authors / reviewers)

The amendment was triggered by a reflection on the closing paragraph of the Gemini research plan, which proposed positioning the discipline as the human-governance schema for safe interaction with autonomous memory systems. That framing was directionally correct but too conservative: it treated automated systems as something the human *interacts with* while keeping the discipline itself manual. The amendment goes further: the discipline is the governance schema, AND the execution can and should be progressively delegated to substrate-aware tooling and agentic memory.

The amendment is consistent with the empirical findings the Gemini plan cites — particularly the ADR-as-control-mechanism study showing models exhibit higher compliance to *documented rationale* than to *static instruction*. This evidence supports both the discipline's existing emphasis on ADRs *and* the auto-drafting of ADRs at L2 (the model is the ideal participant in maintaining the artefact it best responds to).

### Cross-references

- [ADR-026](../decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) — the codifying decision.
- [`CONTEXT_PROTOCOL.md` §11](../../CONTEXT_PROTOCOL.md) — the division-of-labour specification.
- [`Research_Plan_for_Paper_Iteration_Gemini.md`](Research_Plan_for_Paper_Iteration_Gemini.md) — motivating literature analysis.
- [OQ-028](../decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) — open question on framework.
- [OQ-029](../decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1) — open question on timing.
- ADR-024 (RETRO type) and ADR-025 (milestone-close protocol) — auto-drafting interfaces at L3.

**Status:** ACCEPTED 2026-04-26; implementation deferred to L0 + L1 milestone (pending OQ-029 resolution).

---
