---
id: KB-9
title: UK Regulatory Inventory (light)
status: DRAFT
owner: Oleg primary, Claude assist
last_reviewed: 2026-05-03
version: 0.2
sources:
  - https://www.fca.org.uk/                               # accessed 2026-04-26
  - https://www.gov.uk/hmrc                               # accessed 2026-04-26
  - https://www.fca.org.uk/markets/market-abuse           # accessed 2026-04-26
  - https://www.gov.uk/government/publications/markets-in-financial-instruments-directive-mifid-ii  # accessed 2026-04-26
depends_on: []
referenced_by:
  - REQUIREMENTS.md §6.3 (security & audit, UK considerations)
  - ADR-018 (UK strategies deferred but in-scope later)
---

# KB-9 — UK Regulatory Inventory

> **WARNING:** This KB is a **non-authoritative orientation** by Claude for an independent UK-based trader running automated systematic strategies on personal capital. **Anything material requires confirmation by a UK accountant / FCA-authorised compliance professional.** This file flags topics, not legal answers.

## Purpose

Survey the UK regulatory and tax landscape relevant to running `blive` from the UK with personal capital, so the engine and operating model don't accidentally violate something. Items needing professional advice are flagged `(Oleg / professional)`.

## Scope

In scope:
- FCA implications for trading personal capital via API.
- HMRC tax record-keeping expectations.
- Audit-trail requirements that affect engine design.
- MiFID II awareness (mostly not applicable to retail personal trading).
- Market-abuse considerations (always applicable).

Out of scope:
- Operating as an authorised firm (raises the entire FCA permissions question).
- Taking external capital (FCA authorisation likely needed).
- Tax planning beyond record-keeping (seek accountant).

---

## 1. FCA / Personal Trading

- **Trading own personal capital** via a regulated broker (IBKR UK Ltd) is **not regulated activity** — no FCA permissions needed.
- The moment the trader **takes external capital** (friends, family, investors, even informal pooling) the activity moves into FCA territory and likely needs authorisation. **(Oleg / professional)**
- Operating as a sole trader vs. a limited company changes tax treatment but not FCA status (provided personal capital).
- FCA's [perimeter guidance](https://www.fca.org.uk/firms/authorisation/when-required) is the canonical reference.

**For blive operating model**: assume personal capital from individual or sole trader; if a limited company is used, accountant confirms. **No FCA permissions tagged in REQUIREMENTS.**

---

## 2. HMRC Tax Record-Keeping

- For self-assessment income tax, **trade-by-trade records** must be retained for **at least 5 years** after the relevant tax year's filing deadline (longer if a company).
- Tax treatment of trading P&L depends on:
  - Whether HMRC classifies the activity as **investment** (CGT) or **trading** (income tax) — this depends on frequency, intent, organisation, and is fact-specific. **(Oleg / professional)**
  - Type of instrument (equities, ETFs, futures all treated differently).
- Multi-currency trading produces realised FX gains/losses that must be tracked separately.
- IBKR provides annual statements; UK-specific reports (CGT-style) are not automatic — Oleg will need to compute or use a third-party tool.

**For blive operating model**: the **daily NDJSON trade tape** ([REQUIREMENTS §6.3](../../REQUIREMENTS.md)) is the system of record for tax purposes. Retention 7 years aligns with HMRC requirements. **No additional tax-engine logic in blive v1.**

---

## 3. Audit Trail Expectations

- For personal trading, HMRC needs trade-by-trade detail; FCA does not require audit trails for personal capital.
- For any **future move to external capital** (post-v1), MiFID II would impose:
  - 5-year record retention of orders, fills, communications.
  - Best execution records.
  - Transaction reporting (RTS 22 / RTS 28).
  - Algorithmic trading notification (RTS 6) if applicable.

**For blive design**: the existing append-only event log + hash-chained audit entries ([REQUIREMENTS §6.3](../../REQUIREMENTS.md)) **already satisfies the data-retention shape** that future MiFID-II compliance would require. No design change needed for v1.

---

## 4. MiFID II — Awareness Only

- **MiFID II does not apply to a UK-based trader using their own capital via a regulated broker.** The broker (IBKR UK) handles the regulated bits.
- It would apply if blive ever:
  - Took external capital and operated as an authorised firm.
  - Acted as a high-frequency algorithmic trading system (HFT, RTS 6) — out of scope per [ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only).
  - Provided MTF / OTF services (definitionally not blive).

**For blive**: not directly applicable. Recorded here so we don't accidentally drift into territory that would require it without realising. **(Oleg / professional)** if status changes.

---

## 5. Market Abuse Regulation (MAR)

UK MAR applies to **everyone**, including personal traders. Relevant to blive:

- **Market manipulation** — placing orders not intended to execute, layering, spoofing. blive's RiskEngine refuses orders > ±20% from last trade ([REQUIREMENTS §5.5](../../REQUIREMENTS.md)) which provides one defence; logs document intent.
- **Insider dealing** — material non-public information. Not an engine problem but an operator behaviour problem; blive can't prevent it but the audit log makes any complaint investigable.
- **Wash trading** — self-trades that artificially inflate volume. Not a typical concern for systematic ETF / index strategies but an A1a strategy that long/shorts the same ETF set could in principle generate cancelling orders; the RiskEngine's per-name net-exposure check makes this hard to do accidentally.

**For blive design**: existing controls suffice. Market-abuse risk is operator-level, not engine-level.

---

## 5.5 PRIIPs / KID restrictions (UK retail clients)

The **Packaged Retail and Insurance-based Investment Products (PRIIPs)** regulation requires a **Key Information Document (KID)** in the consumer's language for any "packaged retail product" sold to retail clients in the EU / UK. UK post-Brexit retains PRIIPs in onshored form. Effect on `blive`'s execution:

- **UK retail accounts cannot trade products without a UK-filed KID.** Most US-domiciled ETFs (e.g. TQQQ, TMF, IEF) do **not** have UK KIDs filed by their issuers and are therefore not tradable from UK retail brokerage accounts.
- The restriction is enforced **at the broker level**: IB UK rejects retail orders on KID-less products at submission, surfacing **error 201** with reason text containing *"This product does not have a KID in English or in a language approved for your country"* (catalogued in [INV-14](../inv/ib_error_codes.md)).
- The restriction does **not** apply to:
  - **UK / Irish-domiciled UCITS ETFs and ETPs** that file KIDs as part of their UCITS / ETP regulatory regime (most LSE-listed iShares / WisdomTree / Lyxor ETPs).
  - **Direct equities** (PRIIPs covers packaged products, not single-name shares).
  - **Professional Client** classification (bypasses retail PRIIPs but requires meeting MiFID II "elective professional" criteria — wealth, experience, transaction frequency).
- For `blive` Phase 1 / M2-IB.6, the strategy universe substituted US ETFs for UK-listed UCITS / ETP analogues per [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043). Trend-signal tickers (QQQ / TLT) are signal-only — never traded — so PRIIPs does not apply to their consumption as factor inputs from EODHD.

**Operational implication for future strategies**: any strategy targeting US ETF universes needs an analogous PRIIPs-compliance check before deployment from a UK retail account. The check is a single-instrument operator-side lookup in IB Trader Workstation: search the symbol; if "trade-restricted: no KID" appears, the product is blocked.

**For blive design**: the engine itself is universe-agnostic; PRIIPs is an instrument-set concern, not an engine concern. Phase 1's universe choice per ADR-047 documents the substitution; future strategies extend the same pattern.

---

## 6. Data Privacy (UK GDPR)

- blive processes **Oleg's own** trading data; no third-party personal data.
- IB Gateway logs may include account number, etc. — store securely, don't share.
- **Not in scope**: blive doesn't need a privacy notice or data-protection register entry for personal use.

---

## 7. Items Needing Professional Advice

The list of things Claude **cannot answer authoritatively** and require a UK accountant / lawyer / compliance professional:

- Trading vs. investment classification for HMRC.
- Sole trader vs. limited company structure choice.
- Treatment of foreign-sourced income (US dividends, foreign-listed ETFs).
- Whether any specific strategy crosses into FCA-regulated activity (e.g. if it's marketed publicly).
- VAT registration thresholds (almost certainly not applicable to personal trading; relevant if any commercial side activities exist).
- IHT planning around the trading account.
- Pension-wrapper opportunities (SIPP can hold IBKR-routed instruments).

---

## 8. Cross-References

- [REQUIREMENTS §6.3](../../REQUIREMENTS.md) — security & audit, UK considerations note.
- [ADR-018](../decisions/DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8) — UK equity strategies deferred but in-scope later.
- [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) — PRIIPs-compliant universe for Phase 1 A3.
- [INV-14](../inv/ib_error_codes.md) — IB error 201 PRIIPs-KID variant.
- [KB-13](companion_projects.md) — ForgeFolio handles personal-finance reporting separately.

## Changelog

- **v0.1 (2026-04-26)** — initial stub. Will be refined when Oleg confirms structure (sole trader vs limited co, etc.).
- **v0.2 (2026-05-03)** — added §5.5 (PRIIPs / KID restrictions for UK retail clients) per the M2-IB.6.1 wire-run finding catalogued in [ADR-047](../decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043). Documents the regulation, the IB error-201 surface, the exemption set (UCITS / ETPs / single-name shares / Professional Client classification), and the design implication that PRIIPs is an instrument-set concern rather than an engine concern.
