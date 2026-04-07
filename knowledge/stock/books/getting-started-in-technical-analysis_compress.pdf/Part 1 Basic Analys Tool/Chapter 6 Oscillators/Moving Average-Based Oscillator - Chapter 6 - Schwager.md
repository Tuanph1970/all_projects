# Moving Average-Based Oscillator
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 113–114)
**Tags:** #technical-analysis #ma-oscillator #oscillators #momentum #schwager #moving-average #indicators
**Related:** [[Oscillators]] · [[Momentum Indicator]] · [[Equilibrium Line]] · [[Moving Averages]] · [[Price Oscillator]] · [[MACD]] · [[Overbought and Oversold]] · [[Oscillator Sensitivity]]

---

## Definition

The Moving Average-Based Oscillator measures the **distance between price and its moving average**:

```
MA Oscillator = Today's Close − N-day Moving Average
```

It captures how far price has strayed from its "normal" level — how extended or compressed the current move is relative to recent history.

---

## Simple Analogy: Dog on a Leash

Think of a person walking a dog on a leash down a path.

- The **person** is the moving average — walking steadily along the trend
- The **dog** is the price — running ahead, lagging behind, darting left and right
- The **leash** is the MA oscillator — it measures **how far the dog is from the person** at any moment

| Dog Behavior | Oscillator Reading | Meaning |
|---|---|---|
| Dog runs far ahead | Large positive value | Price extended above MA — overbought territory |
| Dog walks beside person | Near zero | Price close to MA — neutral |
| Dog falls far behind | Large negative value | Price extended below MA — oversold territory |
| Leash goes taut | Extreme reading | The distance is unsustainable — dog will get pulled back (or person will get pulled forward) |

The leash has a maximum length (the rubber band from [[Overbought and Oversold]]) — but in a strong trend, the person (MA) speeds up to follow the dog, keeping the leash from snapping.

---

## The Bridge Between Two Worlds

This oscillator connects **trend-following** (Chapter 3) with **countertrend** analysis (Chapter 6):

| World | Tool | Question Asked |
|---|---|---|
| **Trend-following** (Ch. 3) | Price chart + MA | "Is price above or below the average?" (direction) |
| **Countertrend** (Ch. 6) | MA Oscillator | "How *far* above or below?" (magnitude) |

Both come from the same data. The oscillator is an alternate visualization that makes the **distance dimension** easier to read.

---

## How It Works — Three Zones

| Oscillator Value | Price vs. MA | Meaning |
|---|---|---|
| **> 0** (positive) | Price above MA | Price advancing faster than average — bullish momentum |
| **= 0** (at line) | Price equals MA | The MA crossover point — direction is changing |
| **< 0** (negative) | Price below MA | Price declining faster than average — bearish momentum |

The further the oscillator is from zero, the more **extended** the move. Extreme positive readings = overbought; extreme negative readings = oversold.

---

## The Key Equivalence

> "The equilibrium line ('0') represents identical price and moving average values. When the oscillator crosses above and below this line, it is **equivalent to price crossing above and below the moving average**." — Schwager

| Event on Price Chart | Event on Oscillator Panel | Same bar? |
|---|---|---|
| Price crosses above MA | Oscillator crosses above 0 | ✅ Yes — identical event |
| Price crosses below MA | Oscillator crosses below 0 | ✅ Yes — identical event |

⚠️ **These are NOT independent confirmations.** They're the same signal displayed two ways. Don't double-count them.

**What the oscillator adds beyond the crossover:** a clearer view of the *magnitude* of the deviation. On the price chart, the distance between price and MA is hard to eyeball — it varies with chart scale, price level, and time. The oscillator panel normalizes this into a single line oscillating around zero, making overbought/oversold readings and divergences much easier to spot.

---

## MA Oscillator vs. Momentum Indicator

Both are subtraction-based, unbounded, with equilibrium at zero. The difference is in the **reference point**:

| Property | Momentum Indicator | MA Oscillator |
|---|---|---|
| **Formula** | Close − Close(N) | Close − MA(N) |
| **Reference point** | A single price N days ago | Average of last N prices |
| **Reference stability** | Jumpy — that one price may be an anomaly | Smooth — the average absorbs noise |
| **Oscillator smoothness** | Noisier | Inherently smoother |
| **Analogy** | "How far from that specific checkpoint?" | "How far from home?" |
| **Best for** | Raw speed measurement, immediate reaction | Measuring deviation from trend, OB/OS |

> **Momentum** asks: "how far have I traveled since this specific checkpoint?"
> **MA Oscillator** asks: "how far am I from home?"
>
> Home (the average) moves slowly and predictably; the checkpoint (a single past price) can be anywhere.

---

## Sensitivity: MA Length Controls the Zoom

| MA Length | What the Oscillator Tracks | Use Case |
|---|---|---|
| **10-day** | Short-term deviations from recent average | Short-term OB/OS, day/swing trading |
| **50-day** | Medium-term deviations | Swing/position trading |
| **200-day** | Long-term positioning relative to major trend | Market-level assessment ("how extended is the market?") |

> "Longer moving averages will reflect more significant trends; oscillators based on longer averages will reflect longer-term price swings." — Schwager

---

## Division Variant

Like Momentum/ROC, the MA oscillator has a **division sibling**:

```
MA Oscillator (subtraction) = Close − MA(N)     → equilibrium at 0
MA Oscillator (division)    = Close ÷ MA(N)     → equilibrium at 1.0
```

> "Moving average–based oscillators can also be calculated by division instead of subtraction... The resulting indicators are equivalent." — Schwager

The division variant is scale-independent — useful for comparing how extended different instruments are relative to their own averages.

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_ma_oscillator(prices: pd.Series, n: int = 20,
                           method: str = 'subtract') -> pd.Series:
    """
    Moving Average-Based Oscillator.

    Parameters:
      prices: closing price series
      n: moving average period
      method: 'subtract' → Close - MA (equilibrium at 0)
              'divide'   → Close / MA (equilibrium at 1.0)

    Returns:
      Series of oscillator values
    """
    ma = prices.rolling(window=n).mean()
    if method == 'subtract':
        return prices - ma
    elif method == 'divide':
        return prices / ma
    else:
        raise ValueError(f"method must be 'subtract' or 'divide', got '{method}'")


def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """Momentum = Close - Close(N)."""
    return prices - prices.shift(n)


def demonstrate_bridge(prices: pd.Series, n: int = 20):
    """
    Show the bridge between trend-following (price + MA on price chart)
    and countertrend (MA oscillator below).

    Demonstrates the zero-line crossover equivalence:
    oscillator crossing 0 = price crossing MA.
    """
    ma = prices.rolling(window=n).mean()
    osc = compute_ma_oscillator(prices, n)

    # Find crossover points
    price_above = prices > ma
    cross_up = (~price_above.shift(1).fillna(False)) & price_above
    cross_down = price_above.shift(1).fillna(False) & (~price_above)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})

    # ── Price + MA (trend-following view) ──
    ax1.plot(prices.index, prices.values, color='#333333',
             linewidth=1.0, alpha=0.8, label='Price')
    ax1.plot(ma.index, ma.values, color='#378ADD',
             linewidth=1.5, label=f'{n}-day MA')

    # Shade distance between price and MA
    ax1.fill_between(prices.index, ma.values, prices.values,
                     where=(prices > ma), color='green', alpha=0.08,
                     label='Price > MA')
    ax1.fill_between(prices.index, ma.values, prices.values,
                     where=(prices <= ma), color='red', alpha=0.08,
                     label='Price < MA')

    # Mark crossovers on price chart
    ax1.scatter(prices.index[cross_up], prices.values[cross_up],
                color='green', marker='^', s=80, zorder=5)
    ax1.scatter(prices.index[cross_down], prices.values[cross_down],
                color='red', marker='v', s=80, zorder=5)

    ax1.set_title(f'Trend-following view: Price + {n}-day MA', fontsize=12)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── MA Oscillator (countertrend view) ──
    ax2.plot(osc.index, osc.values, color='#1a73e8', linewidth=0.9)
    ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax2.fill_between(osc.index, 0, osc.values,
                     where=(osc > 0), color='green', alpha=0.1)
    ax2.fill_between(osc.index, 0, osc.values,
                     where=(osc <= 0), color='red', alpha=0.1)

    # Mark crossovers on oscillator (same bars!)
    osc_cross_up = cross_up & osc.notna()
    osc_cross_down = cross_down & osc.notna()
    ax2.scatter(osc.index[osc_cross_up], [0] * osc_cross_up.sum(),
                color='green', marker='^', s=80, zorder=5)
    ax2.scatter(osc.index[osc_cross_down], [0] * osc_cross_down.sum(),
                color='red', marker='v', s=80, zorder=5)

    ax2.set_title(f'Countertrend view: MA Oscillator (Close − {n}-day MA)',
                  fontsize=12)
    ax2.set_ylabel('Distance from MA')
    ax2.grid(True, alpha=0.3)

    plt.suptitle('Same data, two views — crossovers occur on identical bars',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


def compare_momentum_vs_ma_osc(prices: pd.Series, n: int = 20):
    """
    Side-by-side comparison showing how the MA oscillator is inherently
    smoother than raw Momentum because the reference point (MA) is smoothed.
    """
    mom = compute_momentum(prices, n)
    ma_osc = compute_ma_oscillator(prices, n)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                                         gridspec_kw={'height_ratios': [2, 1, 1]})

    # Price
    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # Momentum
    ax2.plot(mom.index, mom.values, color='#E24B4A', linewidth=0.9)
    ax2.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    mom_crosses = ((mom.shift(1) * mom) < 0).sum()
    ax2.set_title(f'{n}-day Momentum (Close − Close[{n}]) | '
                  f'crossovers: {mom_crosses}', fontsize=11)
    ax2.grid(True, alpha=0.3)

    # MA Oscillator
    ax3.plot(ma_osc.index, ma_osc.values, color='#378ADD', linewidth=0.9)
    ax3.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    ma_crosses = ((ma_osc.shift(1) * ma_osc) < 0).sum()
    ax3.set_title(f'{n}-day MA Oscillator (Close − MA[{n}]) | '
                  f'crossovers: {ma_crosses}', fontsize=11)
    ax3.grid(True, alpha=0.3)

    plt.suptitle('Momentum (noisy reference) vs MA Oscillator (smooth reference)',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()

    print(f"Momentum zero-crossovers:     {mom_crosses}")
    print(f"MA Oscillator zero-crossovers: {ma_crosses}")
    print(f"MA Oscillator produces ~{mom_crosses / max(ma_crosses, 1):.1f}x "
          f"fewer crossovers (smoother)")


def multi_ma_length_comparison(prices: pd.Series,
                                ma_lengths: list = [10, 50, 200]):
    """
    Compare MA oscillators at different MA lengths to show
    how the MA length controls what level of deviation is captured.
    """
    n_panels = len(ma_lengths)
    fig, axes = plt.subplots(n_panels + 1, 1, figsize=(14, 3 * (n_panels + 1)),
                              sharex=True,
                              gridspec_kw={'height_ratios': [2] + [1] * n_panels})

    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].grid(True, alpha=0.3)

    colors = ['#E24B4A', '#378ADD', '#1D9E75']

    for i, n in enumerate(ma_lengths):
        osc = compute_ma_oscillator(prices, n)
        ax = axes[i + 1]
        ax.plot(osc.index, osc.values, color=colors[i % len(colors)],
                linewidth=0.9)
        ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
        ax.fill_between(osc.index, 0, osc.values,
                        where=(osc > 0), color='green', alpha=0.08)
        ax.fill_between(osc.index, 0, osc.values,
                        where=(osc <= 0), color='red', alpha=0.08)
        ax.set_title(f'Close − {n}-day MA', fontsize=11)
        ax.grid(True, alpha=0.3)

    plt.suptitle('MA length controls what level of deviation is measured',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


def verify_crossover_equivalence(prices: pd.Series, n: int = 20):
    """
    Prove that MA oscillator zero-crossover is identical to
    price/MA crossover on the price chart.
    """
    ma = prices.rolling(window=n).mean()
    osc = compute_ma_oscillator(prices, n)

    price_above_ma = prices > ma
    osc_above_zero = osc > 0

    valid = ma.notna() & osc.notna()
    agreement = (price_above_ma[valid] == osc_above_zero[valid]).mean() * 100

    print(f"=== Crossover Equivalence Proof ({n}-day) ===")
    print(f"Price > MA  matches  Oscillator > 0:  {agreement:.1f}%")
    print("(100% expected — algebraically identical)")

    return agreement


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    np.random.seed(42)
    n_days = 250

    trend = np.concatenate([
        np.linspace(0, 20, 80),
        np.linspace(20, 22, 90),
        np.linspace(22, 5, 80),
    ])
    noise = np.random.normal(0, 1.2, n_days)
    prices = pd.Series(
        100 + trend + noise,
        index=pd.date_range('2024-01-01', periods=n_days, freq='B'),
        name='Close'
    )

    # ── Bridge demonstration ──
    demonstrate_bridge(prices, n=20)

    # ── Momentum vs MA Oscillator smoothness ──
    compare_momentum_vs_ma_osc(prices, n=20)

    # ── MA length comparison ──
    multi_ma_length_comparison(prices, ma_lengths=[10, 50, 200])

    # ── Crossover equivalence proof ──
    print()
    verify_crossover_equivalence(prices, n=20)

    # ── Division variant ──
    print("\n=== Division Variant ===")
    osc_sub = compute_ma_oscillator(prices, 20, method='subtract')
    osc_div = compute_ma_oscillator(prices, 20, method='divide')
    print(f"Subtraction: last value = {osc_sub.iloc[-1]:.2f} "
          f"(equilibrium = 0)")
    print(f"Division:    last value = {osc_div.iloc[-1]:.4f} "
          f"(equilibrium = 1.0)")
    print("Same shape, different scale — just like Momentum vs ROC")
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_ma_oscillator()` | Core formula with subtract/divide option | The bridge oscillator — connects Chapter 3 and Chapter 6 |
| `demonstrate_bridge()` | Dual-panel showing price+MA above, oscillator below | Crossover markers appear on **same bars** in both panels |
| `compare_momentum_vs_ma_osc()` | Side-by-side: Momentum vs MA Oscillator | MA oscillator is smoother because reference point is smoothed |
| `multi_ma_length_comparison()` | 10/50/200-day MA oscillators stacked | Shows how MA length controls the "zoom level" of deviation |
| `verify_crossover_equivalence()` | Mathematical proof: price/MA cross = oscillator zero-cross | 100% match — algebraic identity |

### Key Implementation Notes

1. **`demonstrate_bridge()`** is the most important function. It places crossover markers (triangles) on both the price chart and the oscillator panel, and they appear on the **same bars**. The shaded area between price and MA on the upper panel directly maps to the oscillator's distance from zero on the lower panel. This visual makes the "same signal, different display" insight impossible to miss.

2. **`compare_momentum_vs_ma_osc()`** counts crossovers for both and shows the MA oscillator typically produces fewer. The smoothed reference (MA) absorbs noise that the raw reference (single past price) doesn't.

3. **The division variant** in the example output shows that it parallels the Momentum/ROC relationship exactly. Same shape, different scale. This pattern (subtract vs. divide) recurs across the entire oscillator family.

---

## Connection to Broader Framework

### Link to [[Moving Averages]] (Chapter 3)
The MA oscillator uses the MA from Chapter 3 as its reference point. This creates a direct bridge: the same MA that identifies trend direction (Chapter 3) also measures momentum deviation (Chapter 6). Understanding this connection means you see moving averages and oscillators as two views of the same data, not separate tools.

### Link to [[Momentum Indicator]]
Both subtract something from today's close. Momentum subtracts a single past price (noisy reference); MA oscillator subtracts a smoothed average (stable reference). The MA oscillator is the **smoothed evolution** of the Momentum indicator.

### Link to [[Price Oscillator]] and [[MACD]]
The Price Oscillator extends this concept one step further: instead of `price − MA`, it uses `short MA − long MA`. The MACD is a specific version of the Price Oscillator with EMA(12) − EMA(26). The progression is:
```
Momentum (price − past price)
  → MA Oscillator (price − MA)
    → Price Oscillator (short MA − long MA)
      → MACD (EMA12 − EMA26 + signal line)
```
Each step adds smoothing. The MA oscillator is the second rung on this ladder.

### Link to [[Equilibrium Line]]
The MA oscillator's equilibrium at zero has the clearest physical meaning: price = moving average exactly. This is more intuitive than Momentum's equilibrium (price = one specific past price) because the average represents the "center of gravity" of recent price action.

### Link to [[Overbought and Oversold]]
The MA oscillator's distance from zero is a direct measure of extension. This is conceptually identical to [[Price Envelope Bands]] from Chapter 4 — which define OB/OS as price being a certain percentage above/below the MA. The MA oscillator just displays this distance on a separate panel rather than as bands on the price chart.
