---
id: KB-6
title: Cost & Margin Dictionary
status: DRAFT
owner: Claude
last_reviewed: 2026-04-26
version: 0.1
sources:
  - btest/src/quantdsl_backtest/dsl/costs.py            # accessed 2026-04-26
  - btest/src/quantdsl_backtest/dsl/backtest_config.py  # accessed 2026-04-26
  - https://www.interactivebrokers.com/en/index.php?f=commission     # accessed 2026-04-26
  - https://www.interactivebrokers.com/en/index.php?f=marginnew      # accessed 2026-04-26
depends_on:
  - KB-1 btest_dsl_inventory
referenced_by:
  - REQUIREMENTS.md §8 (parity contract envelopes)
  - ADR-016 (both leverage paths)
---

# KB-6 — Cost & Margin Dictionary

## Purpose

For every cost and margin component in `btest`'s DSL, document the formula, what `btest` computes today, what the live equivalent must compute, and the parity envelope between them. This KB is the SSOT for the parity contract numerics in [REQUIREMENTS §8](../../REQUIREMENTS.md).

## Scope

In scope: `Costs.Commission`, `BorrowCost`, `FinancingCost`, `StaticFees`, plus `BacktestConfig.MarginConfig`, `RiskChecks`, `DrawdownPolicy`. Each entry includes the field shape (lifted from [KB-1](btest_dsl_inventory.md)), the backtest semantic, the live equivalent, and the parity tolerance.

Out of scope: pacing limits (KB-3); IB account types (KB-2 §9); strategy-specific risk thresholds (INV-4).

## Verdict legend

- **Pure formula** — same code path used in btest and blive; zero divergence by construction.
- **Live override needed** — the live engine queries the broker for an actual rate; the btest static value is a placeholder used in research.
- **Structural** — backtest model is a calibration target, not a contract; live divergence is expected and bounded.

---

## 1. Commission

### Source: `btest/src/quantdsl_backtest/dsl/costs.py:9-16`

```python
@dataclass
class Commission:
    type: Literal["per_share", "bps_notional"]
    amount: float
```

### Backtest semantic
- `per_share`: `amount × |qty|` per fill.
- `bps_notional`: `amount × 1e-4 × |notional|` per fill.

### Live equivalent
IB returns `Commission` per fill in `commissionReport` callback (the actual cents charged). blive uses **IB-reported commission** as ground truth; `Commission` model is the parity reference.

### Parity envelope
- US equities, IBKR Pro tier: typical `per_share=0.005` (half-cent per share, min $1, max 1% of trade value). Backtest model with `per_share=0.005` should match within **±0.5 bps** of IB's actual on liquid US equities.
- European equities: tiered fee + exchange + clearing fees that vary; backtest `bps_notional` model is a coarse proxy. Expect **±2 bps** envelope.

### Verdict: **pure formula** for the model itself; **structural** divergence in live (we use IB ground truth, model is a parity reference).

---

## 2. BorrowCost

### Source: `btest/src/quantdsl_backtest/dsl/costs.py:19-26`

```python
@dataclass
class BorrowCost:
    default_annual_rate: float
    curve_name: Optional[str] = None
```

### Backtest semantic
For each short position held overnight, accrue `default_annual_rate × |notional| × (days / 365)`. If `curve_name` is set, lookup a per-symbol curve (typically `stock_loan_rates` parquet) and use that instead of `default_annual_rate`.

### Live equivalent
IB exposes per-symbol borrow rates via `reqMktData` with generic-tick `47` (`Shortable_Shares`) and `48` (`Shortable_Reason`); the **actual borrow charge** is debited in IB account activity at end of day. blive uses **IB-reported borrow** as ground truth; `BorrowCost.default_annual_rate` becomes the parity reference (typically conservative).

### Parity envelope
- General-collateral US equity: IB rate typically 0.5–2% above benchmark; backtest static rate of 2.0% is **conservative** for most general-collateral names but **insufficient** for hard-to-borrow.
- Hard-to-borrow: IB rates can spike to 50%+ annualised; backtest cannot model this without per-symbol curve.
- Envelope: **±25 bps annualised** for general-collateral; **structural** for hard-to-borrow (no static envelope).

### Verdict: **live override needed**. blive's `costs.live_borrow_provider` hook ([REQUIREMENTS §5.1](../../REQUIREMENTS.md)) queries IB at run time; backtest static is a parity reference only for general-collateral.

---

## 3. FinancingCost

### Source: `btest/src/quantdsl_backtest/dsl/costs.py:29-36`

```python
@dataclass
class FinancingCost:
    base_rate_curve: Optional[str] = None  # "SOFR", "ESTER", etc.
    spread_bps: float = 50.0
```

### Backtest semantic
For margin-financed positions: `(base_rate(t) + spread_bps × 1e-4) × |financed_notional| × (days / 365)`. The base rate curve loaded from a parquet (e.g. `data/rates/SOFR.parquet`).

### Live equivalent
IB charges a tiered financing rate based on `EquityWithLoanValue` size (the larger the account, the lower the spread). blive uses **IB-reported margin interest** as ground truth; the model is the parity reference.

### Parity envelope
- IBKR Pro Reg-T account, USD financing on $100k: roughly Fed Funds + 1.5% currently; backtest `SOFR + 50 bps` is **too aggressive** (will under-cost financing). Use `SOFR + 150 bps` as a conservative default.
- Tier breaks (above $1M, $10M, etc.) reduce spread further; not modelled in backtest.
- Envelope: **±15 bps annualised** within a tier; **structural** across tier boundaries.

### Verdict: **live override needed**. blive's `costs.live_financing_provider` hook queries IB tier rate at run time; backtest static is a parity reference per tier.

---

## 4. StaticFees

### Source: `btest/src/quantdsl_backtest/dsl/costs.py:39-46`

```python
@dataclass
class StaticFees:
    nav_fee_annual: float = 0.0
    perf_fee_fraction: float = 0.0
```

### Backtest semantic
- `nav_fee_annual`: charged daily as `nav × annual / 252`.
- `perf_fee_fraction`: charged on positive monthly NAV deltas above high-water-mark.

### Live equivalent
**Same formula in live.** These are not broker fees; they're investor-facing fees the strategy operator is responsible for. blive applies them as account-level charges to the equity curve.

### Parity envelope
**Zero** — pure formula on both sides. **Verdict: pure formula.**

---

## 5. MarginConfig

### Source: `btest/src/quantdsl_backtest/dsl/backtest_config.py:15-23`

```python
@dataclass
class MarginConfig:
    long_initial: float = 0.5
    short_initial: float = 0.5
    maintenance: float = 0.3
```

### Backtest semantic
Global initial-margin and maintenance-margin requirements applied uniformly across all positions:
- A long $100k position requires `100k × long_initial = $50k` initial margin.
- A short $100k position requires `100k × short_initial = $50k` initial margin.
- Maintenance margin call triggers if equity falls below `(longs + shorts) × maintenance`.

### Live equivalent
IB applies **per-instrument** margin requirements that depend on instrument class (Reg-T equities, leveraged ETFs, futures, options), volatility, and account type (Reg-T vs. Portfolio Margin). blive queries `BrokerPort.account_snapshot()` for the actual `BuyingPower` / `MaintMarginReq` values.

### Parity envelope
- Reg-T US equities: IB initial typically 50%, maintenance 25–30%. Backtest `0.5 / 0.3` matches.
- Leveraged ETFs (TQQQ, TMF): IB initial often 75–100% (higher than 50%); backtest under-margins. **Strategy spec must declare per-instrument margin overrides** for A3 strategies, or the engine will refuse to size.
- Portfolio Margin: substantially lower than Reg-T; per-position values queried at run time.
- **Structural** — backtest is global; live is per-instrument.

### Verdict: **live override needed**. blive's Sizer queries IB margin per instrument; `MarginConfig` is the parity reference for back-of-envelope NAV planning, not a live contract.

---

## 6. RiskChecks

### Source: `btest/src/quantdsl_backtest/dsl/backtest_config.py:26-X`

```python
@dataclass
class RiskChecks:
    max_drawdown: float = 0.25
    max_gross_leverage: float = 3.0
    max_daily_loss: Optional[float] = None
    # ... extras
```

### Backtest semantic
- `max_drawdown`: hard stop; position sizing scales to zero if drawdown threshold breached.
- `max_gross_leverage`: cap on `(long_notional + short_notional) / equity`.
- `max_daily_loss`: optional cap on intraday P&L drop from session-start equity.

### Live equivalent
**Same formulas in live.** blive's `RiskEngine` ([ADR-008](../decisions/DECISIONS.md#adr-008--riskengine-no-bypass-enforced-architecturally)) applies these checks against live equity / leverage / P&L every time an order is proposed.

### Parity envelope
**Zero** — pure formulas on both sides. **Verdict: pure formula.**

The **defaults** are conservative starting points; per-strategy overrides via YAML (REQUIREMENTS §5.5, INV-4).

---

## 7. DrawdownPolicy

### Source: `btest/src/quantdsl_backtest/dsl/backtest_config.py:X-X`

```python
@dataclass
class DrawdownPolicy:
    mode: Literal["none", "hard_kill", "soft_scale"] = "none"
    threshold: float = 0.15
    # soft_scale specific:
    start: float = 0.05  # begin scaling
    full: float = 0.15   # fully scaled to zero
```

### Backtest semantic
- `none`: no drawdown action.
- `hard_kill`: at `drawdown >= threshold`, scale all positions to zero; stay flat.
- `soft_scale`: linearly scale position sizing from 1.0 (at drawdown ≤ start) to 0.0 (at drawdown ≥ full).

### Live equivalent
**Same formulas in live.** blive's `RiskEngine` consults `DrawdownPolicy` on every rebalance; the resulting scale factor multiplies target weights before submission.

### Parity envelope
**Zero** — pure formulas. **Verdict: pure formula.**

The kill-switch (REQUIREMENTS §5.5) is distinct: it is a **system-wide** halt triggered by operational conditions (disconnect, parity breach, etc.), not by strategy P&L. `DrawdownPolicy` is per-strategy and continues to operate even with kill-switch armed (the kill-switch overrides toward zero exposure regardless).

---

## 8. Cost Aggregation Pipeline

### How costs assemble in btest

```
For each fill (instrument, side, qty, price):
    cost = 0
    cost += commission.compute(qty, price * qty)
    if side == "SELL_SHORT" and held_overnight:
        cost += borrow.compute(qty * price, days)
    if held_with_leverage and held_overnight:
        cost += financing.compute(financed_notional, days)
    fees_daily = static_fees.compute(nav, days)
```

### How costs assemble in blive

```
For each fill (from broker callback):
    cost = ib_reported_commission     # from commissionReport callback
    # borrow accrues at IB's daily settlement; blive records but does not compute
    # financing accrues at IB's daily settlement; blive records but does not compute
fees_daily = static_fees.compute(nav, days)  # pure formula, same as backtest
```

### Parity diagnostic

Daily ([ADR-012](../decisions/DECISIONS.md#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)):
- `realized_pnl` = sum of fills' (price - prior_close) × qty × side - cost
- `simulated_pnl` = btest replay of the day's fills with the strategy's cost models
- `residual_bps` = (realized - simulated) / |realized| × 1e4

Residual decomposition (M7+):
- `commission_residual` = ib_reported_commission - model_commission
- `borrow_residual` = ib_reported_borrow - model_borrow (most variable)
- `financing_residual` = ib_reported_financing - model_financing
- `slippage_residual` = (realized_fill_price - simulated_fill_price) (largest typically)

Aggregate envelope: REQUIREMENTS §8 — ±15 bps over 5 trading days. Provisional, calibrated at M7 ([OQ-012](../decisions/OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right)).

---

## 9. Cross-References

- [KB-1 §8](btest_dsl_inventory.md) — costs section of DSL inventory.
- [REQUIREMENTS §8](../../REQUIREMENTS.md) — parity contract.
- [ADR-016 leverage paths](../decisions/DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments).
- [INV-4 risk_checks](../inv/risk_checks.md) — derived risk-check inventory.
- [OQ-012 parity tolerance bands](../decisions/OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right).

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from `btest/src/quantdsl_backtest/dsl/costs.py` and `backtest_config.py`.
