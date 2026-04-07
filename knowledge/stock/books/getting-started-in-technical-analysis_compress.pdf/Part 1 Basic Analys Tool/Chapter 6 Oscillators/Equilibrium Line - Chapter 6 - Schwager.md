# Equilibrium Line
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 112–114)
**Tags:** #technical-analysis #equilibrium-line #oscillators #momentum #schwager #indicators
**Related:** [[Momentum]] · [[Oscillators]] · [[Overbought and Oversold]] · [[Rate of Change (ROC)]] · [[MACD]] · [[RSI]] · [[Price Oscillator]] · [[Moving Averages]]

---

## Definition

The equilibrium line is the **horizontal median** on an oscillator chart that represents **neutral momentum** — the point where the rate of price change is exactly zero. It is the reference point that gives all oscillator readings their meaning.

Without the equilibrium line, oscillator values are just floating numbers. It establishes the **coordinate system** that makes oscillator readings interpretable.

---

## Simple Analogy: The Sea Level

Think of the equilibrium line as **sea level**.

- **Above sea level** (oscillator above the line) = the tide is in, water is rising. Price has been gaining over the measurement period.
- **At sea level** (oscillator at the line) = the waterline. Perfectly neutral. Price today equals the reference price.
- **Below sea level** (oscillator below the line) = the tide is out, water is receding. Price has been falling over the measurement period.

Now extend the analogy:
- **How far above sea level** you are tells you how extreme the tide is → this maps to [[Overbought and Oversold]] levels
- **Whether the water is still rising or starting to fall back** while above sea level → this maps to the four momentum states (accelerating vs. decelerating)
- **Crossing sea level** = the tide is turning, net direction has flipped

The overbought/oversold thresholds are like flood markers and drought markers — they tell you when the water is at extreme levels that historically don't sustain for long.

---

## What the Equilibrium Line Represents — By Oscillator Type

| Oscillator | Equilibrium Line Value | What It Means at the Line |
|---|---|---|
| **Momentum** (price − price N days ago) | **0** | Today's close = close N days ago. Zero net change. |
| **Rate of Change** (price ÷ price N days ago) | **1.0** (or 100%) | Today's close equals the close N days ago. Ratio = 1. |
| **MA-based oscillator** (price − MA) | **0** | Price = moving average exactly. Price is crossing the MA. |
| **Price oscillator** (short MA − long MA) | **0** | Short MA = long MA. The two averages are crossing. |
| **MACD** | **0** | 12-day EMA = 26-day EMA. The EMAs are crossing. |
| **RSI** (normalized) | **50** | Up closes and down closes are balanced. |
| **Stochastics** (normalized) | **50** | Close is at the midpoint of the N-day range. |

---

## The Three Zones

### Above the Equilibrium Line
- Current price is **higher** than the reference price (N days ago, or the MA)
- Net positive momentum — price has been rising over the measurement period

### At the Equilibrium Line
- Current price **equals** the reference price
- Zero net momentum — perfectly neutral

### Below the Equilibrium Line
- Current price is **lower** than the reference price
- Net negative momentum — price has been falling over the measurement period

---

## Four Momentum States (Position + Direction)

Combining *where* the oscillator is relative to the line with *which direction* it's moving:

| State | Position | Direction | Meaning | Analogy |
|---|---|---|---|---|
| **1** | Above | Rising ↗ | Advancing with increasing momentum | Tide rising and accelerating |
| **2** | Above | Falling ↘ | Still positive but pace is slowing | Tide still high but starting to recede |
| **3** | Below | Falling ↘ | Declining with increasing downward momentum | Tide falling and accelerating out |
| **4** | Below | Rising ↗ | Still negative but decline is slowing | Tide still out but starting to come back |

> ⚠️ The transition from **State 1 → State 2** is often the **first warning** that a rally is losing steam — even though the oscillator hasn't crossed below zero yet. The deceleration happens *before* the reversal.

---

## Crossover Signals — What They Really Mean

When the oscillator crosses the equilibrium line, it has specific meaning depending on the type:

### Momentum / ROC Crossover
- Today's close has moved from being above to below (or vice versa) the close N days ago
- The **net direction** of price change over the measurement period has flipped

### MA-Based Oscillator Crossover
- Mathematically equivalent to **price crossing the moving average** on the price chart
- The oscillator is just an alternate visualization of the same event

### Price Oscillator / MACD Crossover
- Equivalent to the **short-term MA crossing the long-term MA**
- The classic moving average crossover signal from Chapter 14

> ⚠️ **Critical insight:** Moving average crossover systems and price oscillator zero-line crossovers are **the same signal displayed differently**. One is on the price chart, the other is on the oscillator panel below. They are NOT independent confirmations — they're one signal, not two.

---

## Normalized Oscillators — Different Scale, Same Concept

Normalized (bounded) oscillators like RSI and stochastics range between fixed limits (0 to 100). Their neutral midpoint is **50**, not 0, but the conceptual role is the same:

| RSI Zone | Meaning |
|---|---|
| Above 50 | Bullish momentum dominates (up closes outweigh down closes) |
| At 50 | Balanced — neither side dominant |
| Below 50 | Bearish momentum dominates (down closes outweigh up closes) |

However, for normalized oscillators, traders focus more on the **overbought/oversold thresholds** (70/30 for RSI, 80/20 for stochastics) rather than the midpoint crossover. The equilibrium line concept is most directly relevant for **unbounded oscillators** like Momentum, ROC, Price Oscillator, and MACD.

---

## What the Equilibrium Line Does NOT Tell You

The equilibrium line tells you about **net direction over the measurement period** — but NOT about:
- **Trend strength** — a reading of +1 and +10 are both "above the line" but imply very different conditions
- **Sustainability** — being above the line doesn't mean the move will continue
- **Extremity** — how far from the line determines overbought/oversold, which is a separate concept

> The equilibrium line tells you **which side of neutral** you're on. The overbought/oversold levels tell you **how far from neutral** you've gone.

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """
    Momentum = Today's close − Close N days ago.
    Equilibrium line is at 0.
    """
    return prices - prices.shift(n)


def compute_roc(prices: pd.Series, n: int = 10) -> pd.Series:
    """
    Rate of Change = Today's close / Close N days ago.
    Equilibrium line is at 1.0 (multiply by 100 for percentage scale).
    """
    return prices / prices.shift(n)


def compute_ma_oscillator(prices: pd.Series, n: int = 20) -> pd.Series:
    """
    MA-based oscillator = Price − Moving Average.
    Equilibrium line is at 0.
    Crossover of this line = price crossing the MA on the price chart.
    """
    ma = prices.rolling(window=n).mean()
    return prices - ma


def compute_price_oscillator(prices: pd.Series,
                              short_n: int = 10,
                              long_n: int = 20) -> pd.Series:
    """
    Price Oscillator = Short MA − Long MA.
    Equilibrium line is at 0.
    Crossover of this line = short MA crossing long MA on price chart.
    """
    short_ma = prices.rolling(window=short_n).mean()
    long_ma = prices.rolling(window=long_n).mean()
    return short_ma - long_ma


def classify_momentum_state(oscillator: pd.Series) -> pd.Series:
    """
    Classify each bar into one of four momentum states
    based on position relative to equilibrium line (0)
    and direction of change.

    State 1: Above and Rising  (strongest bullish)
    State 2: Above and Falling (bullish but decelerating)
    State 3: Below and Falling (strongest bearish)
    State 4: Below and Rising  (bearish but decelerating)
    """
    direction = oscillator.diff()  # positive = rising, negative = falling

    conditions = [
        (oscillator > 0) & (direction > 0),   # State 1: above + rising
        (oscillator > 0) & (direction <= 0),   # State 2: above + falling
        (oscillator <= 0) & (direction < 0),   # State 3: below + falling
        (oscillator <= 0) & (direction >= 0),  # State 4: below + rising
    ]
    labels = [
        'State 1: Above & Rising',
        'State 2: Above & Falling',
        'State 3: Below & Falling',
        'State 4: Below & Rising',
    ]

    return pd.Series(
        np.select(conditions, labels, default='Neutral'),
        index=oscillator.index
    )


def detect_equilibrium_crossovers(oscillator: pd.Series) -> pd.Series:
    """
    Detect crossovers of the equilibrium line (0).
    Returns a Series with:
      'bullish_cross' — oscillator crosses from below to above 0
      'bearish_cross' — oscillator crosses from above to below 0
      None            — no crossover
    """
    prev = oscillator.shift(1)

    bullish = (prev <= 0) & (oscillator > 0)
    bearish = (prev > 0) & (oscillator <= 0)

    result = pd.Series(None, index=oscillator.index, dtype=object)
    result[bullish] = 'bullish_cross'
    result[bearish] = 'bearish_cross'
    return result


def plot_oscillator_with_equilibrium(prices: pd.Series,
                                      oscillator: pd.Series,
                                      title: str = 'Oscillator',
                                      eq_value: float = 0.0):
    """
    Plot price chart above and oscillator below,
    with equilibrium line, color-coded zones, and crossover markers.
    """
    crossovers = detect_equilibrium_crossovers(
        oscillator if eq_value == 0 else oscillator - eq_value
    )

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 8), sharex=True,
        gridspec_kw={'height_ratios': [2, 1]}
    )

    # --- Price chart ---
    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.set_ylabel('Price')
    ax1.grid(True, alpha=0.3)

    # --- Oscillator chart ---
    ax2.plot(oscillator.index, oscillator.values,
             color='#1a73e8', linewidth=1.0)
    ax2.axhline(y=eq_value, color='black', linewidth=1.0,
                linestyle='--', label='Equilibrium Line')

    # Color-code above/below zones
    ax2.fill_between(oscillator.index, eq_value, oscillator.values,
                     where=(oscillator > eq_value),
                     color='green', alpha=0.15, label='Above (positive momentum)')
    ax2.fill_between(oscillator.index, eq_value, oscillator.values,
                     where=(oscillator <= eq_value),
                     color='red', alpha=0.15, label='Below (negative momentum)')

    # Mark crossovers
    bull_cross = crossovers == 'bullish_cross'
    bear_cross = crossovers == 'bearish_cross'

    if bull_cross.any():
        ax2.scatter(oscillator.index[bull_cross],
                    oscillator.values[bull_cross],
                    color='green', marker='^', s=80, zorder=5,
                    label='Bullish crossover')
    if bear_cross.any():
        ax2.scatter(oscillator.index[bear_cross],
                    oscillator.values[bear_cross],
                    color='red', marker='v', s=80, zorder=5,
                    label='Bearish crossover')

    ax2.set_title(title, fontsize=12)
    ax2.set_ylabel('Oscillator Value')
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    # Generate sample price data (simulated uptrend → range → downtrend)
    np.random.seed(42)
    n_days = 200
    trend = np.concatenate([
        np.linspace(0, 15, 70),          # uptrend
        np.linspace(15, 16, 60),         # range
        np.linspace(16, 5, 70),          # downtrend
    ])
    noise = np.random.normal(0, 1.0, n_days)
    price_data = 100 + trend + noise

    dates = pd.date_range('2024-01-01', periods=n_days, freq='B')
    prices = pd.Series(price_data, index=dates, name='Close')

    # ── Momentum oscillator ──
    mom = compute_momentum(prices, n=10)
    states = classify_momentum_state(mom)
    crossovers = detect_equilibrium_crossovers(mom)

    print("=== Momentum States (last 10 days) ===")
    print(states.tail(10))
    print()
    print("=== Equilibrium Crossovers ===")
    print(crossovers.dropna())

    # ── Visualize ──
    plot_oscillator_with_equilibrium(prices, mom,
                                     title='10-Day Momentum with Equilibrium Line')

    # ── MA-based oscillator ──
    ma_osc = compute_ma_oscillator(prices, n=20)
    plot_oscillator_with_equilibrium(prices, ma_osc,
                                     title='Price − 20-Day MA Oscillator')

    # ── Price oscillator ──
    price_osc = compute_price_oscillator(prices, short_n=10, long_n=20)
    plot_oscillator_with_equilibrium(prices, price_osc,
                                     title='Price Oscillator (10-MA − 20-MA)')
```

### What Each Function Does

| Function | Purpose |
|---|---|
| `compute_momentum()` | Simplest oscillator: `close − close N days ago`. Equilibrium at 0. |
| `compute_roc()` | Same idea as ratio: `close / close N days ago`. Equilibrium at 1.0. |
| `compute_ma_oscillator()` | `price − moving average`. Crossover of 0 = price crossing the MA. |
| `compute_price_oscillator()` | `short MA − long MA`. Crossover of 0 = MA crossover on price chart. |
| `classify_momentum_state()` | Maps each bar to one of the four states (above/below × rising/falling). |
| `detect_equilibrium_crossovers()` | Finds the exact bars where the oscillator crosses the equilibrium line. |
| `plot_oscillator_with_equilibrium()` | Dual-panel chart with color-coded zones and crossover markers. |

### Key Implementation Notes

1. **The equilibrium line is just a constant** — 0 for subtraction-based oscillators, 1.0 for ratio-based, 50 for RSI. The math is trivial. The *interpretive framework* around it is what matters.

2. **`classify_momentum_state()`** uses `oscillator.diff()` to detect direction. This is essentially taking the derivative of the oscillator — the second derivative of price. When this flips from positive to negative while the oscillator is still above zero, that's the State 1 → State 2 transition (deceleration warning).

3. **Crossover detection** compares current vs. previous bar's position relative to the line. Simple sign-change logic. In practice, you'd add filters to avoid whipsaws (multiple rapid crossovers in choppy markets).

4. **The MA-based oscillator crossover is mathematically identical to a price/MA crossover** — this is not an approximation, it's an algebraic identity. The code makes this explicit: `prices - ma` crossing 0 is the same event as `prices` crossing `ma`.

---

## Connection to Broader Framework

### Link to [[Momentum]]
The equilibrium line is the **reference point** that makes momentum readings interpretable. Momentum without an equilibrium line is like altitude without sea level — you have a number but no context for what it means.

### Link to [[Overbought and Oversold]]
- The equilibrium line tells you **which side of neutral** you're on
- The overbought/oversold levels tell you **how far from neutral** you've gone
- Together they form a complete reading: direction (above/below the line) + extremity (distance from the line)

### Link to [[MACD]]
The MACD zero-line crossover is one of the most-watched signals in technical analysis. Understanding that it's equivalent to the 12-day and 26-day EMA crossing on the price chart prevents double-counting it as a separate confirmation.

### Link to [[Price Oscillator]] and [[Moving Averages]]
Price oscillator crossing zero = short MA crossing long MA. Same signal, different display. Understanding this equivalence is key to not treating redundant information as independent confirmation.
