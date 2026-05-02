# Methodology Amendments Log

This file records material amendments to the **Cognitive Cartography** discipline as articulated in [`CONTEXT_PROTOCOL.md`](../../CONTEXT_PROTOCOL.md). Each entry captures the amendment, motivation, ADRs introduced, artefacts changed, and the implications for the next iteration of the methodology paper at [`docs/method/paper/cognitive_cartography.tex`](paper/cognitive_cartography.tex).

## Scope note (2026-05-02)

The systematic research and paper-iteration work for Cognitive Cartography — and for the broader human / agent substrate emergence question that Amendment v0.2 raised — is moving to a **separate research project** with its own publication trajectory and proper academic apparatus. `blive` is no longer the home for that paper's revision.

Within `blive`, this log continues to serve as a **raw-material accumulator**: each new amendment captures the operational intuition and substrate evidence that arises naturally from the project's own work, in a form the future systematic research can draw on without losing the context of where it was discovered. The conventions below are unchanged; only the downstream consumer is.

The in-tree paper source ([`paper/cognitive_cartography.tex`](paper/cognitive_cartography.tex)) remains at DRAFT v0.1 as a historical staging artefact — it will not be revised in-repo. The separate research project picks up the staged amendments (v0.2, v0.3, and any future entries here) when it is ready to integrate them.

## Convention

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

The "Paper sections affected" subsection in each amendment is preserved as guidance for the future separate research project; it is not actionable inside this repo.

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

## Amendment v0.3 — Session-Bootstrap Files (manual L0 baseline)

**Date:** 2026-05-02

**ADR:** [ADR-042 — Session-bootstrap files: agent-agnostic pattern for L0 warm-up entry point](../decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point)

### Motivation

Amendment v0.2 ([ADR-026](../decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface)) committed the discipline to a five-layer agentic-execution stack but explicitly deferred concrete tooling under [OQ-028](../decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) and [OQ-029](../decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1). In the interim, every session began with the operator manually pointing the agent at the canonical substrate — pasting `NEXT_PROMPT.md` content into the first message, or reminding the agent to read `CONTEXT_INVENTORY.md` before editing. The friction is small per session but compounds across the M0–M2-IB trajectory and is a known vector for skipped warm-up.

Modern agent harnesses already load a small project-root file at session start (Claude Code reads `CLAUDE.md`; other platforms have analogous conventions — `AGENTS.md`, `.cursorrules`, system-prompt configuration). Treating that file as **substrate** — versioned, edit-protocol-governed, pointing at the canonical artefacts rather than restating them — converts the harness's existing auto-load into a near-zero-friction L0 implementation that does not require any of the agentic frameworks deferred under OQ-028.

The pattern is *agent-agnostic in semantics, platform-specific in filename*. The discipline does not commit to any particular harness, vendor, or model generation; it commits to the bootstrap-file pattern, with concrete instances added as agent platforms come into use. This framing is essential: if the methodology coupled itself to one vendor's loader, it would inherit that vendor's lifecycle. By framing the pattern abstractly, the discipline endures across model swaps and platform churn.

### What the amendment changes

- The discipline's *content* is unchanged (six artefact categories, stable IDs, status lifecycle, edit protocol, propagation rules, anti-patterns all stand).
- The discipline's *L0 surface* gains a manual-baseline implementation: session-bootstrap files at the project root, governed by the same protocol as any other substrate artefact.
- A canonical-name convention emerges: each agent platform's auto-loaded file is the bootstrap instance for that platform. The first instance, [`CLAUDE.md`](../../CLAUDE.md), lands with this amendment; future instances (`AGENTS.md`, `.cursorrules`, etc.) add as needed without re-litigating the pattern.
- The bootstrap file is a *pointer* to canonical substrate, never a restatement. SSOT applies; drift is mitigated by explicit `depends_on`, by the file being structurally a pointer (low restating surface by construction), and by milestone-freeze review.

### Substrate artefacts changed

- **NEW** — [`CLAUDE.md`](../../CLAUDE.md) (root, STABLE v1.0): first instance of the bootstrap-file pattern; Claude Code-specific shim around the canonical pointer set.
- **`CONTEXT_PROTOCOL.md`** v0.3 → v0.4: §11.2 (L0 specification) extended to identify session-bootstrap files as the manual L0 baseline; status banner brought current; cross-references [ADR-042](../decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point).
- **`CONTEXT_INVENTORY.md`**: §1 Representation Hierarchy gains a `0. Bootstrap` row for `CLAUDE.md`; CONTEXT_PROTOCOL row updated to v0.4; §7 file-layout placeholder promoted from comment to indexed entry; status banner v0.7 → v0.8.
- **`docs/decisions/DECISIONS.md`** (KB-10) v0.12 → v0.13: ADR-042 added (ACCEPTED); index updated; changelog entry added.

### Paper sections affected (for the next paper iteration)

The next iteration of [`docs/method/paper/cognitive_cartography.tex`](paper/cognitive_cartography.tex) should reflect this amendment. Specific sections:

- **§3 What We Inherit (foundations).** Add a subsection (or footnote) noting that mainstream agent harnesses had independently converged on auto-loaded project-root instruction files (Claude Code's `CLAUDE.md`, similar in other tools). The convergence echoes the broader pattern noted in Amendment v0.2: practitioners and tooling vendors arriving at structurally similar substrate solutions independently. Empirical anchor: nearly every commercially-shipping AI coding harness in 2025–26 defaulted to a small project-root markdown file for project-specific instruction; the discipline adopts the channel without coupling to a specific vendor.
- **§8 What Tooling Could Do.** Mark "session-bootstrap file" as the simplest L0 implementation realisable today **without bespoke tooling** — the *zero-cost* point on the L0 cost / value curve. Useful as the leftmost anchor on the layer-adoption stack figure (F8 candidate annotation).
- **§11 Human-governance / agent-execution.** Refine the L0 description to distinguish between (a) *static bootstrap files* (manual baseline; always available; vendor-incidental, discipline-essential) and (b) *substrate-aware warm-up agents* (richer L0; framework-dependent per OQ-028). The two coexist: an agent that reads `CLAUDE.md` and follows its pointers is performing static L0; an agent that walks `depends_on` closures from a task description is performing dynamic L0. The static instance is the durable fallback when the dynamic one is unavailable.
- **F8 (substrate coverage) figure.** Optional small annotation on the L0 layer indicating both the static and dynamic variants, with the static variant labelled as the manual-baseline / always-available implementation.
- **Abstract / closing.** No change to the thesis; one possible sentence to consider for the closing: *"The discipline's lowest-cost realisation is a small agent-agnostic pointer file at the project root — itself substrate — that any harness loads at session start. The methodology is not bound to any AI vendor or model generation; only the loader filename varies."*

### A note on framing — why agent-agnostic matters

A natural temptation is to describe the amendment as "Claude Code support" or "an instruction file for the Claude AI". That framing is wrong, both technically and methodologically:

- **Technically**, the pattern is whatever-harness-you-have. Cursor, Aider, OpenAI Codex, Gemini CLI, Continue, IDE assistants, and unreleased future tools all converge on the same channel: a project-root file the harness loads automatically. Naming the discipline after one product would mis-state the surface.
- **Methodologically**, Cognitive Cartography deliberately positions itself as the **governance schema over substrate execution**, agnostic to the executing layer (Amendment v0.2). Coupling to one vendor would contradict that posture and inherit that vendor's churn.

The amendment therefore frames the pattern abstractly (session-bootstrap files; manual L0 baseline) and treats specific instances (`CLAUDE.md` here; potentially `AGENTS.md` elsewhere later) as platform-incidental shims around the same pointer set. The methodological commitment is to the **pattern**, not the **filename**.

### Conversation context (for paper authors / reviewers)

The amendment was triggered by the realisation that during the M0–M2-IB sessions the operator was repeatedly pasting variants of `NEXT_PROMPT.md` into fresh sessions to bootstrap the agent into the discipline. The cost was small per session but visible across the trajectory; meanwhile, Claude Code natively auto-loads `CLAUDE.md`, providing a zero-friction implementation channel that was unused. Recognising the same property exists in other harnesses generalised the pattern away from being Claude-specific.

This amendment is consistent with the v0.2 framing: the *governance* (warm-up sequence, stable IDs, ADR discipline) is unchanged; the *execution surface* gains a new lowest-friction entry point. As agentic memory tooling matures (per OQ-028), bootstrap files remain the durable fallback for environments where richer tooling is unavailable.

### Cross-references

- [ADR-042](../decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point) — codifying decision.
- [ADR-026](../decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) — agentic-execution stack this amendment extends at L0.
- [`CONTEXT_PROTOCOL.md` §11.2](../../CONTEXT_PROTOCOL.md) — L0 specification (amended).
- [`CLAUDE.md`](../../CLAUDE.md) — first instance.
- [OQ-028](../decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) — open question on richer-L0 tooling; bootstrap files do not displace this work.
- [OQ-029](../decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1) — open question on richer-L0 timing.

**Status:** ACCEPTED 2026-05-02; first instance (`CLAUDE.md`) lands in the same commit batch as this amendment.

---
