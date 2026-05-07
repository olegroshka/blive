---
id: KB-15
title: Parity Methodology
status: DRAFT
owner: Claude
last_reviewed: 2026-05-06
version: 0.1
sources:
  - ADR-050 (EODHD-vs-IB unit-of-quote conversion at sizing time)
  - RETRO-M2-IB §"Surprises" #7 (EODHD-vs-IB QQL3 price 10× discrepancy)
  - INV-14 v0.7 (error 110 / 2161; QQL3 PMA-cap investigation)
  - INV-4 v0.2 (RC-10 row promoted to implemented)
  - scripts/probe_qql3_unit_of_quote.py (2026-05-06 EODHD-side investigation)
depends_on:
  - ADR-050 (operationalises this stub)
  - ADR-014 (data-source abstraction)
  - ADR-017 (hybrid EODHD + IB streaming routing)
  - ADR-027 (Sizer purity contract preserved by sizing-time conversion)
  - ADR-029 (PaperMarketData parquet — kept vendor-pristine)
  - ADR-047 (PRIIPs-compliant Phase 1 universe — surfaced QQL3)
referenced_by:
  - INV-4 v0.2 RC-10 row
  - ADR-050 §"Cross-References"
  - TASK_REGISTRY M3.1 substrate transitions
---

# KB-15 — Parity Methodology

## Purpose

Captures the methodological discipline for keeping `blive`'s execution coherent with its data inputs as the strategy operates across multiple data vendors (EODHD historical, IB live wire) and one execution venue (IB Paper / IB Live). At v0.1 (M3.1 stub-DRAFT) this KB owns the **unit-of-quote / reverse-split section only**; the full M7 parity envelope (commission deltas, financing residuals, slippage characterisation, regime-adjusted CAGR / Sharpe / MDD comparison against backtest) extends from this stub at M7.

## Scope

**In scope at v0.1 (M3.1):**

- §1 The unit-of-quote problem and its M3.1 narrow fix.
- §2 The per-instrument convention catalogue at `src/blive/adapters/eodhd/conventions.py`.
- §3 RC-10 (price sanity) as the auto-detection layer per [INV-4 v0.2](../inv/risk_checks.md).
- §4 The catalogue-curation workflow (operator updates when EODHD propagates a missing event).
- §5 Worked example: QQL3.

**Out of scope at v0.1 (defers to M7):**

- Full parity envelope re-derivation against the substituted Phase 1 universe ([RETRO-M2-IB §"Surprises" #4](../retros/M2-IB_retrospective.md) — 3×/3× → 3×/1× regime profile shift).
- Commission / financing / slippage parity envelopes (referenced by [KB-6](./cost_margin_dictionary.md) but not yet decomposed for the substituted universe).
- Live-IB-MD reference pricing (Route A per [ADR-050](../decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only); bounded to free MD tiers only at M7).
- Backtest-vs-live equity-curve parity (G2 ±1 bps target deferred per RETRO-M1; re-derives at M7).

## §1 The unit-of-quote problem (M3.1 framing)

`blive` consumes EODHD-quoted prices for both:

1. **Sizing**: `effective_capital × target_weight / price → desired_qty` per [ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero).
2. **LMT construction**: `bar.close × (1 ± offset_bps/10000)` per `blive.runtime.ib_pipeline._ib_order_from_desired`.

When EODHD's quoted price diverges from IB's contract reference, both the sized quantity and the constructed LMT land in IB-disagreement units. The empirical surface of this divergence (per [INV-14 v0.7](../inv/ib_error_codes.md) + [RETRO-M2-IB §"Surprises" #7](../retros/M2-IB_retrospective.md)) is:

- **IB error 110** ("price not in allowed range") on LMTs computed from EODHD-units when the divergence is multiplicative (e.g. ~10×).
- **Under-sized positions** in IB-USD-equivalent dollar terms, contaminating the M3.2 empirical window's cap-binding evidence (the OQ-031 decision rests on cap-binding behaviour at correctly-sized positions).
- **Mark-to-market equity drift** on the equity-curve report when held positions are marked at EODHD-units while filled at IB-units.

### 1.1 Hypothesis catalogue

The 2026-05-06 `scripts/probe_qql3_unit_of_quote.py` investigation surfaced four hypotheses for *why* an EODHD-vs-IB divergence exists for a given instrument:

| # | Hypothesis | EODHD-side signal |
|---|---|---|
| H1 | EODHD `close` is unadjusted; `adjusted_close` carries the split factor | `close[-1] / adjusted_close[-1]` ≠ 1.0 across the window AND `/api/splits/{ticker}` lists a recent event |
| H2 | EODHD reports LSE main-book GBp pence vs IB's USD class on LSEETF | `/api/fundamentals.General.CurrencyCode` is `GBX` / `GBp` |
| H3 | Different share-class (USD vs GBP-hedged) | EODHD ISIN ≠ IB conId-resolved ISIN |
| H4 | Vendor-symbol divergence (e.g. EODHD `QQQ3.LSE` vs IB `QQL3`) | Same ISIN check as H3 — if ISINs match, H4 refuted |

For QQL3 the 2026-05-06 probe **refuted H1 + H2** (close == adjusted_close ratio 1.0; CurrencyCode = USD) and left H3+H4 inconclusive. The operative cause is most likely a **recent reverse-split that EODHD has not yet propagated** to its EOD feed — a known EODHD lag failure mode on volatile / leveraged ETPs (issuers commonly do 10:1 reverse-splits on 3× products after drawdowns; vendor splits-history feeds sometimes lag by days to weeks).

### 1.2 The narrow M3.1 fix

Per [ADR-050](../decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only): **Hybrid (B-now / A-later free-MD-only)**.

- **B-now**: per-instrument convention catalogue at `src/blive/adapters/eodhd/conventions.py` applies the conversion at sizing time. The `PaperMarketData` parquet stays vendor-pristine; conversion lives at the pipeline boundary (`run_ib_multi_pipeline._price_lookup`), preserving the [ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) Sizer-purity contract.
- **A-later (free-MD-only)**: at M7 the parity-diagnostic surface optionally adopts live IB market-data references for sizing — but **bounded to free IB MD tiers only**. Operator-stated cost discipline at M3.1 entry (no LSEETF / paid subscription); the resulting blast radius is "Route A handles the easy cases (US-equity SMART feeds), Route B handles the hard cases (LSE-ETF / leveraged ETPs)" rather than full A coverage. Captured in ADR-050 so a future M7 implementor doesn't re-litigate scope.

## §2 Per-instrument convention catalogue

The catalogue is a module-level dict literal at `src/blive/adapters/eodhd/conventions.py`. Two convention kinds at v0.1:

- **`IDENTITY`** — no conversion; EODHD price equals IB price. Default for unlisted symbols. Most Phase 1 instruments (IBTL / IBTM / QQQ / TLT) use this convention.
- **`MANUAL_SCALE`** — operator-confirmed manual scale factor: `ib_price = eodhd_price / divisor`. Each entry carries `divisor: Decimal`, `source: str` (free-form provenance), `notes: str` (free-form notes). Used when EODHD has lagged a reverse-split that IB has indexed.

Future kinds land here when [TASK_REGISTRY M3.2](../../TASK_REGISTRY.md)'s empirical window or future EODHD refreshes surface conventions not covered. Candidates include:

- `USE_ADJUSTED_CLOSE` — when EODHD's `adjusted_close` carries the split factor and `close` is raw historical (per H1).
- `CURRENCY_CONVERT` — when EODHD reports in a different currency unit than IB (per H2).

### 2.1 Promotion path (deferred)

When the catalogue grows ≥3-5 entries OR operator-side editing pressure builds, the dict-literal promotes to a YAML-driven catalogue under `~/.blive/config/` paralleling the secrets pattern in [ADR-035](../decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets). Forward-listed in [TASK_REGISTRY Sketched M4+](../../TASK_REGISTRY.md) (the "vendor-convention catalogue centralisation" line); not scheduled at M3.1.

## §3 RC-10 (price sanity) — the auto-detection layer

Per [INV-4 v0.2](../inv/risk_checks.md): RC-10 trips at sizing time when an order's limit/stop price deviates from `RiskInputs.reference_price` by more than `RiskEngineConfig.max_price_deviation_pct` (default ±50%). The pipeline (`run_ib_multi_pipeline`) wires `reference_price` to the IB-equivalent post-conversion price — same value used by the Sizer's `_price_lookup`.

**What RC-10 catches:**

- LMT-construction bugs in `_ib_order_from_desired` (sign error, wrong scale).
- `limit_price_offset_bps` misconfiguration (e.g. operator passes 5000 instead of 50).
- Operator-entered LMT prices that drift far off the converted reference.

**What RC-10 does NOT catch:**

- Catalogue-miss for an instrument (e.g. QQL3 absent from the catalogue). When the catalogue is missing for a symbol, both the LMT and the reference fall through to IDENTITY; deviation is the same 0.5% offset the LMT was constructed with; RC-10 passes — the order then hits IB error 110. This is the catalogue's own job to detect — operator-curated entries with a documented confirmation source.

**Threshold rationale (±50% vs INV-4 v0.1's ±20%):** leveraged ETPs hit 11.74% max daily range per [INV-14 v0.7](../inv/ib_error_codes.md) (QQL3 60-bar window). ±20% would false-positive on legitimate gap-overnight moves; ±50% still catches the M3.1 ~10× case with comfortable margin. M7 forward-list: per-instrument bands once the M3.2 window characterises volatility profiles per instrument.

## §4 Catalogue-curation workflow

Catalogue entries are operator-curated. The workflow:

1. **Discovery**: M3.2's empirical window (or future paper-mode runs) surfaces an order rejected with IB error 110 ("price not in allowed range"). Or RC-10 fires inside the engine. Or the equity-curve report shows an obviously wrong mark-to-market for an instrument.
2. **Investigation**: run `scripts/probe_qql3_unit_of_quote.py --ticker {EODHD_TICKER} --ib-symbol {IB_SYMBOL}` (parameterised — works for any ticker pair, not just QQL3). The hypothesis-refutation matrix narrows the cause.
3. **Operator confirmation**: the operator records the manually-confirmed scale factor (or other convention) against IB's live reference price during RTH. Records source + date in the `source: str` field.
4. **Catalogue update**: add or amend the row in `CONVENTIONS_BY_IB_SYMBOL`. Update the `notes: str` field to capture *why* the entry exists and *when* to revisit.
5. **Revisit cadence**: at each milestone close per [CONTEXT_PROTOCOL §6.3](../../CONTEXT_PROTOCOL.md), audit catalogue entries — when EODHD propagates the previously-missing event (e.g. `/api/splits/QQQ3.LSE` adds the recent split), the entry can either simplify or move to `IDENTITY`.

## §5 Worked example: QQL3

QQL3 is the 3× Nasdaq leveraged ETP on LSEETF (per [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043), Phase 1 universe). The catalogue v0.1 entry:

```python
"QQL3": Convention(
    kind=ConventionKind.MANUAL_SCALE,
    divisor=Decimal("10"),
    source="IB live reference, M2-IB.6.2c (2026-05-06)",
    notes=(
        "EODHD-side recent reverse-split lag; "
        "revisit when /api/splits/QQQ3.LSE picks up the event."
    ),
),
```

### 5.1 Empirical observations

- **EODHD close (2026-05-06)**: $412.94 (`/api/eod/QQQ3.LSE` against the operator's API key)
- **IB live reference (2026-05-06)**: ~$39 (per [INV-14 v0.7](../inv/ib_error_codes.md) M2-IB.6.2c run-3 `mktCapPrice` observation)
- **Divisor**: `412.94 / 39 ≈ 10.59` → operator-confirmed at 10 (round factor reflecting the canonical 10:1 reverse-split shape)
- **EODHD splits endpoint**: returns one historical event (2020-11-09) — nothing recent
- **EODHD adjusted_close**: equals close (ratio 1.0 across 30-day window) — EODHD considers its data already adjusted (incorrectly)
- **EODHD CurrencyCode**: USD (matches IB; refutes H2)

### 5.2 Behavioural impact pre-M3.1 (no catalogue entry)

| Concern | Pre-fix behaviour | Post-fix behaviour (catalogue v0.1) |
|---|---|---|
| Sizer position size on QQL3 (NAV $5000, weight 1.0) | $5000 / $412 ≈ 12 shares | $5000 / $41.20 ≈ 121 shares |
| LMT BUY @ 50 bps offset | $412 × 1.005 = $414.06 → IB error 110 | $41.20 × 1.005 = $41.41 → ACCEPTED |
| Equity-curve mark-to-market for held position | Marked at $412 (~10× too high) | Marked at $41.20 (correct) |
| M3.2 empirical cap-binding evidence | Contaminated (under-sized positions don't generate cap-binding behaviour) | Clean — full IB-USD-equivalent exposure |

### 5.3 When to revisit

- **EODHD propagates the split**: `/api/splits/QQQ3.LSE` adds a 2026-recent event. At that point `adjusted_close` will diverge from `close`; either simplify the entry to a future `USE_ADJUSTED_CLOSE` convention, or move to `IDENTITY` if EODHD also corrects `close` directly.
- **Issuer does another reverse-split**: the divisor needs updating. Operator-driven catalogue revision.
- **Operator switches to Route A** for QQL3 (unlikely given the free-MD-only constraint per ADR-050 — LSEETF is paid tier): catalogue entry becomes a fallback rather than the primary reference.

## §6 Forward-list (M7 work, captured here for traceability)

Items deferred from M3.1's narrow scope to M7's full parity envelope:

- **Per-instrument volatility bands for RC-10** (replace the global ±50%). Requires the M3.2 window's per-instrument volatility characterisation as input.
- **Full Phase 1 parity envelope re-derivation** against the substituted universe (QQL3 / IBTL / IBTM); regime profile differs from the original notebook's TQQQ / TMF / IEF (3×/3× → 3×/1×) per [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) so backtest CAGR / Sharpe / MDD do not carry forward.
- **Mixed-currency P&L parity** (USD on QQL3 leg, GBP-hedged on IBTL/IBTM legs); informed by M3.4's mixed-currency observation.
- **Commission / financing / slippage parity envelopes** — extends [KB-6](./cost_margin_dictionary.md) §1 / §2 / §3 to the substituted universe.
- **Backtest-vs-live equity-curve parity** — G2 ±1 bps deferred per RETRO-M1; re-derives once the universe / regime issues are resolved.
- **Live-IB-MD reference pricing** (Route A) for the subset of instruments on free IB MD tiers — bounded scope per ADR-050 §"Decision" #2.

## Cross-References

- [ADR-050](../decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) — operationalises this stub; the load-bearing decision.
- [INV-4 v0.2](../inv/risk_checks.md) — RC-10 row promoted to implemented; references this KB for context.
- [INV-14](../inv/ib_error_codes.md) — IB error 110 (the symptom that surfaces when conversion is missing or wrong); 2161 (the PMA-cap surface this M3.1 fix unblocks for evaluation in M3.2).
- [ADR-014](../decisions/DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction) — data-source abstraction; conventions live in `blive.adapters.eodhd` per the layered structure.
- [ADR-017](../decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) — hybrid EODHD + IB routing per-instrument; the Hybrid B-now / A-later split here aligns with the per-instrument routing principle.
- [ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) — Sizer purity contract (preserved by sizing-time conversion at the pipeline boundary).
- [ADR-029](../decisions/DECISIONS.md#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet) — PaperMarketData parquet contract (preserved; vendor-pristine).
- [DD-7 §3.2](../dd/instrument_dictionary.md) — reverse-split convention footnote on the QQL3 row (added at M3.1 alongside this KB).
- [KB-6](./cost_margin_dictionary.md) — cost / margin dictionary; future parity-envelope work extends from there.
- [OQ-031](../decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — Phase 1 deployment trade-off; M3.1 unblocks the M3.2 evidence needed for resolution.
- `scripts/probe_qql3_unit_of_quote.py` — EODHD-side investigation probe; parameterised — usable for any ticker pair.
- `src/blive/adapters/eodhd/conventions.py` — the catalogue.
- [TASK_REGISTRY M3.1 / M7](../../TASK_REGISTRY.md) — milestone scope.
- [PHASE_2_READINESS.md](../PHASE_2_READINESS.md) — surfaced this discrepancy as a Phase 1 deployment-decision dependency.

## Open Questions

- (none specific to this stub at v0.1; OQ-031 is the umbrella decision M3.1 unblocks)

## Changelog

- **v0.1 (2026-05-06 / M3.1)** — initial stub-DRAFT. Captures the unit-of-quote / reverse-split section only; full M7 parity envelope deferred. Operationalises ADR-050 with §1 problem framing + hypothesis catalogue, §2 convention catalogue spec, §3 RC-10 role + non-role, §4 catalogue-curation workflow, §5 QQL3 worked example, §6 M7 forward-list.
