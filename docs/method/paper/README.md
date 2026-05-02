# Cognitive Cartography paper

LaTeX source for the paper *Cognitive Cartography: A Meta-Methodology for Human–AI Collaboration on Complex Problems*.

## Files

- `cognitive_cartography.tex` — main source (canonical).
- `references.bib` — bibliography.
- `README.md` — this file.

## Build

```bash
latexmk -pdf cognitive_cartography
```

Or manually:

```bash
pdflatex cognitive_cartography
bibtex cognitive_cartography
pdflatex cognitive_cartography
pdflatex cognitive_cartography
```

Required packages: `lmodern`, `geometry`, `microtype`, `tikz` (with libraries `positioning`, `arrows.meta`, `shapes.geometric`, `decorations.pathreplacing`, `calc`, `fit`, `backgrounds`, `matrix`, `shapes.misc`), `booktabs`, `caption`, `natbib`, `xcolor`, `enumitem`, `hyperref`. All in standard TeX Live full installs.

## Status

DRAFT v0.1 — §1 and §2 fully drafted; §3–§10 outlined; eight figures included as TikZ; ~25 references seeded in `references.bib`.

**Frozen in-repo as of 2026-05-02.** The systematic paper-iteration and human / agent substrate emergence research has moved to a separate research project with its own publication trajectory. This folder remains as a historical staging artefact — the LaTeX source above is preserved at DRAFT v0.1 and will not be revised here. Amendments continue to accumulate at [`docs/method/Amendments_Log.md`](../Amendments_Log.md) as raw material the separate project can draw on; see that file's "Scope note (2026-05-02)" preamble.

## Figures

| Id | Label | Width | Status |
|----|-------|-------|--------|
| F1 | `fig:drift` — drift spectrum | 1 col | included |
| F2 | `fig:hierarchy` — hierarchy of maps | 1 col | included |
| F3 | `fig:atlas` — artefact graph | 2 col | included |
| F4 | `fig:status` — status lifecycle | 1 col | included |
| F5 | `fig:editproto` — edit protocol | 1 col | included |
| F6 | `tab:synthesis` — discipline ↔ principle ↔ failure mode | 2 col (table) | included |
| F7 | `fig:session` — session lifecycle | 1 col | included |
| F8 | `fig:substrate` — substrate coverage | 1 col | included |

All figures are TikZ source inline in the `.tex`; they will refine as drafting continues.

## Provenance

The paper documents a discipline the author has practised over years across many domains. AI participation in *writing* the paper is acknowledged in the paper's Acknowledgements section.
