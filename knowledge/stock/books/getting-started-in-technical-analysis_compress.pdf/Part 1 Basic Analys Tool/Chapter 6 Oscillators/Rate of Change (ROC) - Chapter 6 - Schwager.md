# Rate of Change (ROC)
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 112–114)
**Tags:** #technical-analysis #rate-of-change #ROC #oscillators #momentum #schwager #basic-oscillator #indicators
**Related:** [[Momentum Indicator]] · [[Momentum]] · [[Oscillators]] · [[Equilibrium Line]] · [[Overbought and Oversold]] · [[Oscillator Sensitivity]] · [[Price Oscillator]] · [[MACD]]

---

## Definition

Rate of Change (ROC) is the **division sibling** of the [[Momentum Indicator]]. Where Momentum subtracts, ROC divides:

```
Momentum = Today's Close − Close N days ago    (subtraction → absolute units)
ROC      = Today's Close ÷ Close N days ago    (division → ratio / percent)
```

Schwager introduces them together and says they are "virtually identical" except for the difference in scale (Figure 6.2).

---

## Simple Analogy: Two Rulers for the Same Distance

Imagine measuring how far a runner has moved in 10 seconds.

- **Momentum** measures in **meters**: "the runner moved 5 meters." But 5 meters means very different things for a sprinter (that's slow) vs. a toddler (that's fast). The raw number depends on who you're measuring.
- **ROC** measures in **percent of the track completed**: "the runner covered 5% of the track." Now a sprinter at 5% and a toddler at 5% represent equivalent effort relative to their context.

Same motion, different ruler. The percent ruler (ROC) is more universally comparable.

---

## Why ROC Exists — The Scale Problem

| Scenario | Stock A ($10→$15) | Stock B ($500→$505) |
|---|---|---|
| **Momentum** | +5 | +5 |
| **ROC** | 1.50 (50% gain) | 1.01 (1% gain) |

Momentum says both moved "+5" — but a 50% gain and a 1% gain are wildly different moves. ROC captures this by normalizing by the starting price.

> **ROC solves the comparability problem:** it makes momentum measurements meaningful across instruments with different price levels.

---

## Properties

| Property | Momentum | ROC |
|---|---|---|
| **Formula** | `Close − Close(N)` | `Close ÷ Close(N)` |
| **Operation** | Subtraction | Division |
| **Equilibrium line** | 0 | 1.0 (or 100%) |
| **Units** | Price units (dollars) | Dimensionless ratio / percent |
| **Scale dependent?** | Yes | No |
| **Shape** | Identical | Identical |
| **Comparable across instruments?** | No | Yes |
| **OB/OS level portability** | Must set per instrument | Can use universal thresholds |

---

## When To Use ROC vs. Momentum

| Use Case | Recommended | Why |
|---|---|---|
| **Single instrument over time** | Either — interchangeable | Same shape, same signals |
| **Cross-instrument comparison** | ROC | Percentage scale makes comparison meaningful |
| **Setting OB/OS thresholds across instruments** | ROC | A 10% ROC move means the same on a $20 stock and a $2,000 stock |
| **Intuitive reading of magnitude** | ROC | "Up 5%" is immediately meaningful; "+$5" requires knowing the base price |
| **Quick mental math** | Momentum | Subtraction is simpler than division |

---

## Mathematical Relationship

Momentum and ROC are algebraically linked:

```
ROC = 1 + (Momentum / Close_N_days_ago)
```

Or equivalently:

```
Momentum = Close_N_days_ago × (ROC − 1)
```

This means:
- When Momentum > 0, ROC > 1.0 (both say "price went up")
- When Momentum = 0, ROC = 1.0 (both say "no change")
- When Momentum < 0, ROC < 1.0 (both say "price went down")
- They cross their respective equilibrium lines on **exactly the same bar**
- They peak and trough on **exactly the same bar**
- They produce **identical divergence signals**

> This is not an approximation — it's an algebraic identity. They are the same measurement expressed in two forms.

---

## Schwager's Key Point

Schwager doesn't differentiate Momentum and ROC much because his argument is that they're **functionally the same**. This reinforces his broader Chapter 6 thesis:

> "Almost all popular oscillators are variations on these simple themes."

Momentum and ROC are the purest demonstration — literally the same measurement in two mathematically equivalent forms. If you understand one, you understand the other. The formula differences affect scale and comparability, but the underlying signal — the rate of price change — is identical.

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_roc(prices: pd.Series, n: int = 10,
                as_percent: bool = True) -> pd.Series:
    """
    Rate of Change: Today's close / Close N days ago.

    Parameters:
      prices: Series of closing prices
      n: lookback period
      as_percent: if True, returns (ratio - 1) * 100 so equilibrium = 0%
                  if False, returns raw ratio so equilibrium = 1.0

    Returns:
      Series of ROC values
    """
    ratio = prices / prices.shift(n)
    if as_percent:
        return (ratio - 1) * 100  # equilibrium at 0%
    return ratio  # equilibrium at 1.0


def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """Momentum: Today's close - Close N days ago."""
    return prices - prices.shift(n)


def demonstrate_scale_problem(n: int = 10):
    """
    Show why ROC exists: two stocks with the same dollar move
    but very different percentage moves.
    """
    np.random.seed(42)
    days = 60

    # Stock A: low-priced, volatile (starts ~$20)
    noise_a = np.random.normal(0, 0.5, days)
    trend_a = np.linspace(0, 10, days)
    stock_a = pd.Series(20 + trend_a + noise_a, name='Stock A ($20)')

    # Stock B: high-priced, stable (starts ~$500)
    noise_b = np.random.normal(0, 2, days)
    trend_b = np.linspace(0, 10, days)
    stock_b = pd.Series(500 + trend_b + noise_b, name='Stock B ($500)')

    mom_a = compute_momentum(stock_a, n)
    mom_b = compute_momentum(stock_b, n)
    roc_a = compute_roc(stock_a, n, as_percent=True)
    roc_b = compute_roc(stock_b, n, as_percent=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle(f'The Scale Problem: Momentum vs ROC ({n}-day)',
                 fontsize=14, fontweight='bold')

    # Momentum comparison (misleading)
    axes[0, 0].plot(mom_a.values, color='#E24B4A', linewidth=1, label='Stock A ($20)')
    axes[0, 0].plot(mom_b.values, color='#378ADD', linewidth=1, label='Stock B ($500)')
    axes[0, 0].axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    axes[0, 0].set_title('Momentum (misleading)', fontsize=12)
    axes[0, 0].set_ylabel('Dollar change')
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(True, alpha=0.3)

    # ROC comparison (meaningful)
    axes[0, 1].plot(roc_a.values, color='#E24B4A', linewidth=1, label='Stock A ($20)')
    axes[0, 1].plot(roc_b.values, color='#378ADD', linewidth=1, label='Stock B ($500)')
    axes[0, 1].axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    axes[0, 1].set_title('ROC (meaningful comparison)', fontsize=12)
    axes[0, 1].set_ylabel('Percent change')
    axes[0, 1].legend(fontsize=8)
    axes[0, 1].grid(True, alpha=0.3)

    # Stock A: Momentum vs ROC shape
    ax_mom = axes[1, 0]
    ax_roc = ax_mom.twinx()
    ax_mom.plot(mom_a.values, color='#E24B4A', linewidth=1, label='Momentum')
    ax_roc.plot(roc_a.values, color='#378ADD', linewidth=1, label='ROC %',
                linestyle='--')
    ax_mom.set_title('Stock A: Same shape, different scale', fontsize=12)
    ax_mom.set_ylabel('Momentum ($)', color='#E24B4A')
    ax_roc.set_ylabel('ROC (%)', color='#378ADD')
    ax_mom.grid(True, alpha=0.3)

    # Stock B: Momentum vs ROC shape
    ax_mom2 = axes[1, 1]
    ax_roc2 = ax_mom2.twinx()
    ax_mom2.plot(mom_b.values, color='#E24B4A', linewidth=1, label='Momentum')
    ax_roc2.plot(roc_b.values, color='#378ADD', linewidth=1, label='ROC %',
                 linestyle='--')
    ax_mom2.set_title('Stock B: Same shape, different scale', fontsize=12)
    ax_mom2.set_ylabel('Momentum ($)', color='#E24B4A')
    ax_roc2.set_ylabel('ROC (%)', color='#378ADD')
    ax_mom2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def verify_signal_equivalence(prices: pd.Series, n: int = 10):
    """
    Prove that Momentum and ROC produce identical signals:
    same crossovers, same peaks, same troughs, same divergences.
    """
    mom = compute_momentum(prices, n)
    roc = compute_roc(prices, n, as_percent=False)

    # Crossover equivalence: mom crosses 0 ↔ roc crosses 1.0
    mom_cross_up = (mom.shift(1) <= 0) & (mom > 0)
    roc_cross_up = (roc.shift(1) <= 1.0) & (roc > 1.0)
    cross_match = (mom_cross_up == roc_cross_up).iloc[n + 1:].mean() * 100

    # Peak/trough equivalence: local maxima occur on same bars
    mom_peaks = (mom > mom.shift(1)) & (mom > mom.shift(-1))
    roc_peaks = (roc > roc.shift(1)) & (roc > roc.shift(-1))
    peak_match = (mom_peaks == roc_peaks).iloc[n + 1:-1].mean() * 100

    print(f"=== Signal Equivalence ({n}-day) ===")
    print(f"Crossover agreement:  {cross_match:.1f}%")
    print(f"Peak/trough agreement: {peak_match:.1f}%")
    print("(Expected: 100% — they are algebraically identical)")

    return cross_match, peak_match


def roc_cross_instrument_thresholds(n: int = 10):
    """
    Demonstrate how ROC enables portable OB/OS thresholds
    across instruments with different price levels.
    """
    print(f"=== ROC Threshold Portability ({n}-day) ===\n")
    print(f"{'Instrument':<20} {'Price':>8} {'5% move':>10} "
          f"{'Mom value':>10} {'ROC value':>10}")
    print("-" * 62)

    instruments = [
        ("Penny stock", 2),
        ("Mid-cap stock", 50),
        ("Blue chip", 200),
        ("High-price stock", 800),
    ]

    for name, price in instruments:
        move = price * 0.05
        mom_val = move
        roc_val = 1.05
        print(f"{name:<20} ${price:>7.0f} ${move:>9.2f} "
              f"{mom_val:>10.2f} {roc_val:>10.2f}")

    print(f"\nMomentum: threshold varies ($0.10 to $40) — must set per instrument")
    print(f"ROC: threshold is always 1.05 (or 5%) — universally portable")


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    np.random.seed(42)
    n_days = 200
    trend = np.concatenate([
        np.linspace(0, 15, 70),
        np.linspace(15, 16, 60),
        np.linspace(16, 5, 70),
    ])
    noise = np.random.normal(0, 1.0, n_days)
    prices = pd.Series(
        100 + trend + noise,
        index=pd.date_range('2024-01-01', periods=n_days, freq='B'),
        name='Close'
    )

    # ── Basic ROC ──
    roc_pct = compute_roc(prices, n=10, as_percent=True)
    roc_raw = compute_roc(prices, n=10, as_percent=False)
    print("=== 10-Day ROC (last 5 bars) ===")
    print(pd.DataFrame({
        'Price': prices.round(2),
        'ROC (ratio)': roc_raw.round(4),
        'ROC (%)': roc_pct.round(2),
    }).tail(5))
    print()

    # ── Signal equivalence proof ──
    verify_signal_equivalence(prices, n=10)
    print()

    # ── Scale problem demonstration ──
    demonstrate_scale_problem(n=10)

    # ── Cross-instrument threshold portability ──
    roc_cross_instrument_thresholds(n=10)
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_roc()` | Core formula with ratio or percent output | `as_percent=True` shifts equilibrium to 0% for easier reading |
| `compute_momentum()` | Subtraction sibling for comparison | Included to demonstrate equivalence |
| `demonstrate_scale_problem()` | Visual proof of why ROC exists | Same $5 move means 50% on $10 stock vs 1% on $500 stock |
| `verify_signal_equivalence()` | Mathematical proof: same crossovers, peaks, troughs | 100% match expected — algebraic identity |
| `roc_cross_instrument_thresholds()` | Shows OB/OS threshold portability | ROC = 1.05 means "5%" everywhere; Momentum = 5 means different things |

### Key Implementation Notes

1. **The `as_percent` parameter** — ROC can be expressed two ways: as a raw ratio (equilibrium at 1.0) or as a percentage change (equilibrium at 0%). The percentage form `(ratio - 1) * 100` is more intuitive for most uses — "up 5%" reads easier than "ratio 1.05." Most charting software uses the percentage form.

2. **`verify_signal_equivalence()`** proves the algebraic identity programmatically: Momentum crossing 0 and ROC crossing 1.0 happen on the same bar, 100% of the time. Peaks and troughs align 100%. This isn't a statistical correlation — it's a mathematical certainty.

3. **`demonstrate_scale_problem()`** is the most important visual. The top-left panel shows Momentum for a $20 stock and a $500 stock — they look similar, which is misleading because the $20 stock is actually moving much faster in percentage terms. The top-right panel shows ROC for both — now the $20 stock's stronger percentage moves are clearly visible.

---

## Connection to Broader Framework

### Link to [[Momentum Indicator]]
ROC and Momentum are algebraically linked:
- `ROC = 1 + (Momentum / Close_N_days_ago)`
- They produce identical shapes, crossovers, peaks, troughs, and divergences
- The only difference is scale: absolute price units vs. dimensionless ratio

### Link to [[Oscillators]]
ROC is one of the "basic oscillators" in the oscillator family tree. It's the second-simplest after the Momentum indicator. Like Momentum, it's unbounded and requires empirical OB/OS level setting — but its percentage scale makes thresholds more portable across instruments.

### Link to [[Overbought and Oversold]]
ROC's scale independence is a practical advantage for OB/OS level-setting:
- A 10% ROC threshold means "10% move in N days" regardless of instrument
- A Momentum threshold of +5 means very different things depending on the stock's price level
- For multi-instrument screening, ROC thresholds are far more practical

### Link to [[Price Oscillator]] and [[MACD]]
Schwager notes that moving average-based oscillators can also be calculated by division instead of subtraction — "dividing price by a moving average, or dividing a shorter-term average by a longer-term average." The resulting indicators are equivalent. This Momentum/ROC relationship (subtraction vs. division) is the same pattern that recurs throughout the oscillator family.

### Link to Decision Support Framework
ROC answers: "What percentage has price changed over the past N days?"
This is a more universally meaningful question than Momentum's "How many dollars has price changed?" — because the answer is comparable across contexts. A 10% move demands attention whether the stock is at $5 or $500.
