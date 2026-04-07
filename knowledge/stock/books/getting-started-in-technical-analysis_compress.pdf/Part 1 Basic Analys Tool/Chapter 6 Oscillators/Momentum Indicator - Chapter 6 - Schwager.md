# Momentum Indicator
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 111–113), Chapter 3 (p. 48)
**Tags:** #technical-analysis #momentum-indicator #oscillators #schwager #basic-oscillator #indicators
**Related:** [[Momentum]] · [[Oscillators]] · [[Equilibrium Line]] · [[Rate of Change (ROC)]] · [[Overbought and Oversold]] · [[Oscillator Sensitivity]] · [[Moving Averages]] · [[Divergence]]

---

## Definition

The Momentum indicator is the **simplest, most direct oscillator** — the concept of momentum expressed as the most minimal possible formula:

```
Momentum = Today's Close − Close N days ago
```

No smoothing, no normalization, no weighting. It got the name "Momentum" because it's the **purest, most unfiltered** measurement of the concept. Every other oscillator is this idea with extra processing layers on top.

---

## Simple Analogy: The Speedometer

The Momentum indicator is a **raw speedometer** bolted directly to the engine.

- It tells you **exactly how fast** you're going right now — no smoothing, no averaging, no delay
- The reading is in **raw units** (mph, not "percentage of max speed") — so a reading of 60 means very different things in a car vs. an airplane
- It **reacts instantly** to acceleration or braking — you feel every bump
- The tradeoff: it's **jumpy on rough roads** — every pothole shows up as a speed change, making it hard to distinguish real acceleration from road noise

Compare to the RSI (a normalized oscillator), which is more like a smoothed, calibrated gauge that always reads between 0 and 100 regardless of the vehicle. Cleaner to read, but you lose the raw, immediate responsiveness.

---

## Properties

| Property | Value |
|---|---|
| **Type** | Unbounded oscillator (no fixed limits) |
| **Equilibrium line** | 0 (zero net price change over N days) |
| **Scale** | Price units (dollars, points) |
| **Inputs** | Closing prices, lookback period N |
| **Smoothing** | None — raw, unfiltered |
| **Speed** | Fastest oscillator — zero lag |

---

## The Hidden Connection to Moving Averages

Schwager reveals in Chapter 3 that **the direction of a moving average is mathematically equivalent to the sign of the Momentum indicator:**

> A rising N-day moving average means today's close is higher than the close N days ago — which is exactly the condition for positive N-day Momentum.

| Event on Price Chart | Equivalent Oscillator Event |
|---|---|
| N-day MA turns upward | N-day Momentum crosses above 0 |
| N-day MA turns downward | N-day Momentum crosses below 0 |
| N-day MA is flat | N-day Momentum is at 0 |

**Why this matters:** These are the **same signal displayed two different ways**. A 20-day moving average upturn and a 20-day Momentum zero-line crossover happen at the exact same bar. Don't treat them as two independent confirmations — they're one event.

---

## Reading the Momentum Indicator

### The Four States (from [[Equilibrium Line]])

| State | Position | Direction | Meaning | Speedometer Analogy |
|---|---|---|---|---|
| **1** | Above 0 | Rising ↗ | Accelerating advance | Pedal to the floor, speed increasing |
| **2** | Above 0 | Falling ↘ | Still positive but decelerating | Foot off the gas, coasting but still moving forward |
| **3** | Below 0 | Falling ↘ | Accelerating decline | Braking hard, speed increasing in reverse |
| **4** | Below 0 | Rising ↗ | Still negative but decelerating | Easing off the brakes, still in reverse but slowing |

> The **State 1 → State 2 transition** is the earliest warning signal: the advance continues but the engine is straining. This happens before the zero-line crossover (which signals the actual direction change).

### Crossover Signal
When Momentum crosses 0:
- **From below to above:** price has shifted from net-declining to net-advancing over the past N days
- **From above to below:** price has shifted from net-advancing to net-declining

---

## Sensitivity: The N-Day Tradeoff

Schwager compares 5-day vs. 20-day momentum on the same price series (3Com, Figure 6.3):

| Parameter | Behavior | Signal Size | Use Case |
|---|---|---|---|
| **Short (e.g., 5-day)** | Tracks every minor swing. Noisy. | Small, frequent reversals | Short-term / day trading |
| **Long (e.g., 20-day)** | Filters minor swings. Smooth but laggy. | Large, significant reversals | Position / swing trading |

> "The reversal portended by a 5-day oscillator will generally be proportionally smaller to that portended by a 20-day oscillator." — Schwager

**The tradeoff is identical to the moving average length tradeoff** from Chapter 3: shorter = more sensitive but noisier, longer = smoother but laggier. No "correct" N value — it depends on your trading timeframe.

---

## Strengths and Weaknesses

### Strengths ✅
| Strength | Why It Matters |
|---|---|
| **Transparency** | No black box — you always know exactly what the number means |
| **Speed** | Zero lag — reacts instantly to price changes (fastest oscillator) |
| **Diagnostic clarity** | Four momentum states are clean and easy to interpret |
| **Simplicity** | One subtraction. Trivial to compute and debug. |

### Weaknesses ❌
| Weakness | Why It Matters |
|---|---|
| **Noise** | No smoothing means every minor fluctuation shows up. Many false signals in choppy markets. |
| **Scale dependence** | +5 means very different things on a $10 stock vs. $500 stock. Can't compare across instruments. |
| **No fixed boundaries** | Unbounded → can't use standard OB/OS levels (70/30). Must set levels empirically, and they may not hold. |

---

## Momentum vs. Rate of Change — Siblings, Not Rivals

Schwager shows both side by side (Figure 6.2) and says they're "virtually identical" except for scale:

| | Momentum | Rate of Change (ROC) |
|---|---|---|
| **Formula** | `Close − Close(N)` | `Close ÷ Close(N)` |
| **Operation** | Subtraction | Division |
| **Equilibrium line** | 0 | 1.0 (or 100%) |
| **Units** | Price units (dollars, points) | Ratio (dimensionless) or percent |
| **Scale dependent?** | ✅ Yes — $5 move means different things at different price levels | ❌ No — 5% is 5% regardless of price level |
| **Shape** | Identical to ROC | Identical to Momentum |
| **Comparable across instruments?** | ❌ No | ✅ Yes |

They produce the **same peaks, troughs, crossovers, and divergences**. The only practical difference: ROC is comparable across instruments with different price scales. For analysis of a single instrument, they're interchangeable.

> **Analogy:** Momentum is like measuring speed in "meters traveled since 10 seconds ago." ROC is like measuring speed in "percentage of distance covered since 10 seconds ago." Same motion, different ruler.

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """
    Momentum Indicator: Today's close − Close N days ago.

    Properties:
      - Unbounded (no fixed limits)
      - Equilibrium line at 0
      - Scale: price units (dollars/points)
      - No smoothing — fastest oscillator, most noise

    Parameters:
      prices: Series of closing prices
      n: lookback period (days)

    Returns:
      Series of momentum values
    """
    return prices - prices.shift(n)


def compute_roc(prices: pd.Series, n: int = 10) -> pd.Series:
    """
    Rate of Change: Today's close / Close N days ago.

    Equivalent to Momentum but scale-independent.
    Equilibrium line at 1.0.
    Multiply by 100 for percentage scale (equilibrium at 100).
    """
    return prices / prices.shift(n)


def momentum_direction(momentum: pd.Series) -> pd.Series:
    """
    Classify the direction of momentum change:
      'accelerating' — momentum is increasing (moving away from 0)
      'decelerating' — momentum is decreasing (moving toward 0)

    This is essentially the second derivative of price.
    """
    delta = momentum.diff()
    # Accelerating if momentum and its change have the same sign
    # (positive momentum getting more positive, or negative getting more negative)
    same_sign = (momentum > 0) & (delta > 0) | (momentum < 0) & (delta < 0)

    result = pd.Series('decelerating', index=momentum.index)
    result[same_sign] = 'accelerating'
    result[momentum.isna() | delta.isna()] = np.nan
    return result


def compare_momentum_sensitivity(prices: pd.Series,
                                   short_n: int = 5,
                                   long_n: int = 20):
    """
    Side-by-side comparison of short vs. long momentum periods.
    Demonstrates the N-day sensitivity tradeoff (Schwager Figure 6.3).
    """
    mom_short = compute_momentum(prices, short_n)
    mom_long = compute_momentum(prices, long_n)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                              gridspec_kw={'height_ratios': [2, 1, 1]})

    # Price
    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].set_ylabel('Price')
    axes[0].grid(True, alpha=0.3)

    # Short momentum
    axes[1].plot(mom_short.index, mom_short.values,
                 color='#e8501a', linewidth=0.9)
    axes[1].axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    axes[1].fill_between(mom_short.index, 0, mom_short.values,
                         where=(mom_short > 0), color='green', alpha=0.1)
    axes[1].fill_between(mom_short.index, 0, mom_short.values,
                         where=(mom_short <= 0), color='red', alpha=0.1)
    axes[1].set_title(f'{short_n}-Day Momentum (sensitive, noisy)', fontsize=11)
    axes[1].set_ylabel('Momentum')
    axes[1].grid(True, alpha=0.3)

    # Long momentum
    axes[2].plot(mom_long.index, mom_long.values,
                 color='#1a73e8', linewidth=0.9)
    axes[2].axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    axes[2].fill_between(mom_long.index, 0, mom_long.values,
                         where=(mom_long > 0), color='green', alpha=0.1)
    axes[2].fill_between(mom_long.index, 0, mom_long.values,
                         where=(mom_long <= 0), color='red', alpha=0.1)
    axes[2].set_title(f'{long_n}-Day Momentum (smooth, laggy)', fontsize=11)
    axes[2].set_ylabel('Momentum')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    # Count zero-line crossovers as proxy for signal frequency
    short_crosses = ((mom_short.shift(1) * mom_short) < 0).sum()
    long_crosses = ((mom_long.shift(1) * mom_long) < 0).sum()
    print(f"{short_n}-day zero-line crossovers: {short_crosses}")
    print(f"{long_n}-day zero-line crossovers: {long_crosses}")
    print(f"Short period produces ~{short_crosses / max(long_crosses, 1):.1f}x "
          f"more signals")


def momentum_vs_roc(prices: pd.Series, n: int = 10):
    """
    Visual comparison showing Momentum and ROC are the same
    shape on different scales (Schwager Figure 6.2).
    """
    mom = compute_momentum(prices, n)
    roc = compute_roc(prices, n)

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True,
                              gridspec_kw={'height_ratios': [2, 1, 1]})

    # Price
    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].grid(True, alpha=0.3)

    # Momentum
    axes[1].plot(mom.index, mom.values, color='#e8501a', linewidth=0.9)
    axes[1].axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    axes[1].set_title(f'{n}-Day Momentum (equilibrium = 0)', fontsize=11)
    axes[1].set_ylabel('Price units')
    axes[1].grid(True, alpha=0.3)

    # ROC
    axes[2].plot(roc.index, roc.values, color='#1a73e8', linewidth=0.9)
    axes[2].axhline(y=1.0, color='black', linewidth=0.8, linestyle='--')
    axes[2].set_title(f'{n}-Day ROC (equilibrium = 1.0)', fontsize=11)
    axes[2].set_ylabel('Ratio')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def momentum_ma_equivalence(prices: pd.Series, n: int = 20):
    """
    Demonstrate that Momentum zero-line crossover is equivalent
    to Moving Average direction change.

    Schwager's insight from Chapter 3: a rising N-day MA means
    today's close > close N days ago, which is the same as
    positive N-day Momentum.
    """
    ma = prices.rolling(window=n).mean()
    mom = compute_momentum(prices, n)

    ma_rising = ma.diff() > 0       # MA turned up
    mom_positive = mom > 0           # Momentum above zero

    # These should be identical (after warmup period)
    agreement = (ma_rising == mom_positive).iloc[n + 1:]
    pct_match = agreement.mean() * 100

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                              gridspec_kw={'height_ratios': [2, 1, 1]})

    # Price + MA
    axes[0].plot(prices.index, prices.values, color='#333333',
                 linewidth=1.0, alpha=0.7, label='Price')
    axes[0].plot(ma.index, ma.values, color='#1a73e8',
                 linewidth=1.5, label=f'{n}-day MA')
    axes[0].set_title(f'Price with {n}-Day Moving Average', fontsize=12)
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # MA direction
    ma_dir = ma.diff()
    axes[1].bar(ma_dir.index, ma_dir.values,
                color=np.where(ma_dir > 0, 'green', 'red'),
                width=1.5, alpha=0.6)
    axes[1].axhline(y=0, color='black', linewidth=0.8)
    axes[1].set_title('MA Direction (daily change in MA)', fontsize=11)
    axes[1].grid(True, alpha=0.3)

    # Momentum
    axes[2].plot(mom.index, mom.values, color='#e8501a', linewidth=0.9)
    axes[2].axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    axes[2].fill_between(mom.index, 0, mom.values,
                         where=(mom > 0), color='green', alpha=0.1)
    axes[2].fill_between(mom.index, 0, mom.values,
                         where=(mom <= 0), color='red', alpha=0.1)
    axes[2].set_title(f'{n}-Day Momentum', fontsize=11)
    axes[2].grid(True, alpha=0.3)

    plt.suptitle(f'MA Direction ↔ Momentum Equivalence ({pct_match:.1f}% match)',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()

    print(f"MA direction matches Momentum sign: {pct_match:.1f}% of bars")
    print("(100% expected — they are algebraically identical)")


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    np.random.seed(42)
    n_days = 200

    # Simulated price: uptrend → range → downtrend
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

    # ── Basic momentum ──
    mom = compute_momentum(prices, n=10)
    direction = momentum_direction(mom)
    print("=== 10-Day Momentum (last 10 bars) ===")
    print(pd.DataFrame({
        'Price': prices,
        'Momentum': mom.round(2),
        'Direction': direction,
    }).tail(10))
    print()

    # ── Sensitivity comparison (Figure 6.3 equivalent) ──
    print("=== Sensitivity: 5-Day vs 20-Day ===")
    compare_momentum_sensitivity(prices, short_n=5, long_n=20)
    print()

    # ── Momentum vs ROC (Figure 6.2 equivalent) ──
    print("=== Momentum vs ROC: Same Shape, Different Scale ===")
    momentum_vs_roc(prices, n=10)

    # ── MA direction equivalence (Chapter 3 insight) ──
    print("\n=== MA Direction ↔ Momentum Equivalence ===")
    momentum_ma_equivalence(prices, n=20)
```

### What Each Function Does

| Function | Purpose | Key Concept |
|---|---|---|
| `compute_momentum()` | Core formula: `close − close(N)` | The simplest oscillator |
| `compute_roc()` | Division equivalent: `close / close(N)` | Scale-independent sibling |
| `momentum_direction()` | Classifies accelerating vs. decelerating | Second derivative of price |
| `compare_momentum_sensitivity()` | 5-day vs. 20-day side-by-side | N-day tradeoff (Schwager Fig. 6.3) |
| `momentum_vs_roc()` | Shows identical shape, different scale | Subtraction vs. division equivalence (Fig. 6.2) |
| `momentum_ma_equivalence()` | Proves MA direction = Momentum sign | Chapter 3 algebraic identity |

### Key Implementation Notes

1. **`momentum_direction()`** detects whether momentum is accelerating or decelerating by checking whether momentum and its own `diff()` have the same sign. This is the **second derivative of price** — when it flips, the advance/decline is losing energy even before the zero-line crossover.

2. **`compare_momentum_sensitivity()`** counts zero-line crossovers to quantify the noise difference. You'll see the 5-day version produces ~2-4x more crossovers than the 20-day version on the same data — more signals, but proportionally more of them are noise.

3. **`momentum_ma_equivalence()`** is the most conceptually important function. It demonstrates the algebraic identity from Chapter 3: MA direction and Momentum sign agree on 100% of bars (after warmup). This proof prevents you from treating them as independent confirmations.

---

## Connection to Broader Framework

### Link to [[Momentum]] (Concept)
The Momentum indicator is the **simplest implementation** of the momentum concept. It's the "reference implementation" — all other oscillators can be understood as the Momentum indicator with additional processing (smoothing, normalization, ratio conversion, etc.).

### Link to [[Rate of Change (ROC)]]
Momentum and ROC are siblings:
- Same peaks, troughs, crossovers, divergences
- Momentum = subtraction → price units (scale dependent)
- ROC = division → ratio/percent (scale independent)
- For single-instrument analysis, interchangeable. For cross-instrument comparison, use ROC.

### Link to [[Equilibrium Line]]
The Momentum indicator's equilibrium line at 0 is the simplest case: `close − close(N) = 0` means exactly zero net price change. All other oscillator equilibrium lines are transformations of this same concept.

### Link to [[Moving Averages]] (Chapter 3)
The algebraic identity: **MA direction = Momentum sign**. A rising 20-day MA and a positive 20-day Momentum are the same mathematical event. Critical for avoiding redundant confirmations.

### Link to [[Oscillator Sensitivity]]
The N-day parameter in the Momentum indicator is the purest demonstration of the sensitivity tradeoff — no smoothing to complicate the picture. Short N = sensitive/noisy, Long N = smooth/laggy. This tradeoff applies to every oscillator, but it's easiest to see in raw Momentum.

### Link to [[Overbought and Oversold]]
Because the Momentum indicator is unbounded, OB/OS levels must be set empirically (Schwager's "isolate top/bottom 10%" guideline). This is harder than with normalized oscillators like RSI (fixed 70/30), which is one of the practical reasons normalized oscillators became more popular.
