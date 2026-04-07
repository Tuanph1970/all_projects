# Price Oscillator
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 113–116), Chapter 14 (pp. 230–234)
**Tags:** #technical-analysis #price-oscillator #oscillators #momentum #schwager #moving-average #crossover #indicators
**Related:** [[Oscillators]] · [[Moving Average-Based Oscillator]] · [[MACD]] · [[Momentum Indicator]] · [[Moving Averages]] · [[Equilibrium Line]] · [[Overbought and Oversold]] · [[Oscillator Sensitivity]]

---

## Definition

The Price Oscillator measures the **difference between two moving averages** of different lengths:

```
Price Oscillator = Short-term MA − Long-term MA
```

Schwager illustrates this with Figure 6.5: 10-day and 20-day MAs on the 3Com price chart, with the oscillator below.

> "The price oscillator is essentially an alternate depiction of the basic moving average crossover system described in Chapter 14." — Schwager

---

## Simple Analogy: Two Runners

Think of two runners on the same track:
- **Fast runner** = short-term MA (responds quickly to recent pace changes)
- **Slow runner** = long-term MA (maintains steady, averaged pace)

| Runner Behavior | Oscillator Reading | What It Means |
|---|---|---|
| Fast runner pulls ahead, gap widening | Positive and **rising** | Bullish momentum increasing — short-term trend accelerating away from long-term |
| Fast runner still ahead, gap shrinking | Positive but **falling** | Momentum decelerating — fast runner is tiring |
| Side by side (crossing) | **Zero** | Crossover — relationship between timeframes is flipping |
| Slow runner takes lead, gap widening | Negative and **falling** | Bearish momentum increasing |
| Slow runner ahead, gap shrinking | Negative but **rising** | Bearish momentum decelerating |

> The oscillator doesn't track either runner's absolute position. It tracks the **distance between them**. That distance is the momentum.

---

## Position on the Smoothing Ladder

```
Momentum         = Price − Price(N)         ← raw vs. raw      (noisiest, fastest)
MA Oscillator    = Price − MA(N)            ← raw vs. smoothed
Price Oscillator = MA(short) − MA(long)     ← smoothed vs. smoothed (smoothest, laggiest)
  └→ MACD        = EMA(12) − EMA(26) + signal line  (specific Price Oscillator + extra smoothing)
```

Each step replaces a noisy input with a smoothed one:
- **Momentum:** both inputs are raw single prices → maximum noise, maximum speed
- **MA Oscillator:** one input smoothed → less noise, some lag
- **Price Oscillator:** both inputs smoothed → least noise, most lag

> The cost of double smoothing: the Price Oscillator requires **both** the short-term and long-term trends to shift before it signals. This produces fewer false signals but slower reactions.

---

## The Key Equivalence: Price Oscillator = MA Crossover

| Event on Price Chart | Event on Oscillator Panel | Same bar? |
|---|---|---|
| Short MA crosses above Long MA | Price Oscillator crosses above 0 | ✅ Yes |
| Short MA crosses below Long MA | Price Oscillator crosses below 0 | ✅ Yes |
| Short MA far above Long MA | Large positive oscillator value | ✅ Direct mapping |
| Short MA far below Long MA | Large negative oscillator value | ✅ Direct mapping |

**The algebra:**
```
Short MA > Long MA
  ↕ identical to
Short MA − Long MA > 0
  ↕ identical to
Price Oscillator > 0
```

⚠️ **These are NOT independent confirmations.** A moving average crossover on the price chart and a Price Oscillator zero-line crossover are the **same event** in different visual formats. Don't double-count them.

**What the oscillator adds:** the *magnitude* of the gap between the two MAs, displayed as a single line. This makes it easy to see convergence, divergence, and overbought/oversold conditions — all of which are hard to eyeball on the price chart where two MA lines curve through price action.

---

## What the Price Oscillator Tells You

The two MAs represent **two timeframes of trend**:

| Oscillator Behavior | Meaning | Convergence/Divergence |
|---|---|---|
| **> 0 and rising** | Short-term trend pulling away above long-term | MAs **diverging** — momentum increasing |
| **> 0 and falling** | Short-term still above, but gap shrinking | MAs **converging** — momentum decreasing |
| **Crossing zero (from below)** | Short-term overtaking long-term | MAs **crossing** — bullish transition |
| **< 0 and falling** | Short-term pulling away below long-term | MAs **diverging** downward — bearish momentum increasing |
| **< 0 and rising** | Short-term still below, but gap shrinking | MAs **converging** — bearish momentum decreasing |
| **Crossing zero (from above)** | Long-term overtaking short-term | MAs **crossing** — bearish transition |

> The convergence/divergence of the two MAs is literally what gives [[MACD]] its name: Moving Average **Convergence-Divergence**.

---

## Price Oscillator → MACD: One Step Away

Schwager explicitly positions the Price Oscillator as the direct precursor to MACD:

> "A price oscillator that used 12- and 26-day moving averages would look much the same as the MACD except for the presence of the 9-day signal line." — Schwager

| Feature | Price Oscillator | MACD |
|---|---|---|
| **Formula** | Short SMA − Long SMA | EMA(12) − EMA(26) |
| **MA type** | Simple (or any) | Exponential (specific) |
| **Periods** | Any choice | 12 and 26 (Appel's defaults) |
| **Signal line** | None | 9-day EMA of MACD |
| **Histogram** | None | MACD − Signal line |

MACD is just a Price Oscillator with three specific modifications:
1. **Exponential** moving averages (more weight on recent prices)
2. Specific lengths: **12 and 26 days**
3. A **9-day signal line** for additional crossover signals

Understanding this makes MACD far less mysterious — it's a dressed-up "short MA minus long MA."

---

## Division Variant

Like all oscillators in this family:

```
Price Oscillator (subtract) = MA(short) − MA(long)    → equilibrium at 0
Price Oscillator (divide)   = MA(short) ÷ MA(long)    → equilibrium at 1.0
```

> "Moving average–based oscillators can also be calculated by division instead of subtraction... The resulting indicators are equivalent." — Schwager

Same shape, scale-independent. Useful for cross-instrument comparison.

---

## Properties

| Property | Value |
|---|---|
| **Type** | Unbounded oscillator |
| **Equilibrium line** | 0 (subtraction) or 1.0 (division) |
| **Inputs** | Two MA lengths (short and long) |
| **Parameters** | Short MA period, Long MA period |
| **Smoothness** | High — both inputs are smoothed |
| **Lag** | Higher than MA Oscillator — requires both MAs to shift |
| **Signal** | Zero-line crossover = MA crossover on price chart |

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_price_oscillator(prices: pd.Series,
                              short_n: int = 10,
                              long_n: int = 20,
                              ma_type: str = 'sma',
                              method: str = 'subtract') -> pd.Series:
    """
    Price Oscillator = Short MA − Long MA (or Short MA / Long MA).

    Parameters:
      prices: closing price series
      short_n: short MA period
      long_n: long MA period
      ma_type: 'sma' for simple, 'ema' for exponential
      method: 'subtract' (equilibrium=0) or 'divide' (equilibrium=1.0)

    Returns:
      Series of Price Oscillator values
    """
    if ma_type == 'sma':
        short_ma = prices.rolling(window=short_n).mean()
        long_ma = prices.rolling(window=long_n).mean()
    elif ma_type == 'ema':
        short_ma = prices.ewm(span=short_n, adjust=False).mean()
        long_ma = prices.ewm(span=long_n, adjust=False).mean()
    else:
        raise ValueError(f"ma_type must be 'sma' or 'ema', got '{ma_type}'")

    if method == 'subtract':
        return short_ma - long_ma
    elif method == 'divide':
        return short_ma / long_ma
    else:
        raise ValueError(f"method must be 'subtract' or 'divide', got '{method}'")


def demonstrate_crossover_equivalence(prices: pd.Series,
                                       short_n: int = 10,
                                       long_n: int = 20):
    """
    Show that MA crossover on the price chart is identical to
    Price Oscillator zero-line crossover.

    Three-panel display:
      Top: Price + both MAs with crossover markers
      Middle: Price Oscillator with zero-line crossover markers
      Bottom: Overlay proving they occur on the same bars
    """
    short_ma = prices.rolling(window=short_n).mean()
    long_ma = prices.rolling(window=long_n).mean()
    osc = short_ma - long_ma

    # Detect crossovers
    above = short_ma > long_ma
    cross_up = (~above.shift(1).fillna(False)) & above
    cross_down = above.shift(1).fillna(False) & (~above)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})

    # ── Price + MAs ──
    ax1.plot(prices.index, prices.values, color='#333333',
             linewidth=0.8, alpha=0.6, label='Price')
    ax1.plot(short_ma.index, short_ma.values, color='#E24B4A',
             linewidth=1.2, label=f'{short_n}-day MA')
    ax1.plot(long_ma.index, long_ma.values, color='#378ADD',
             linewidth=1.2, label=f'{long_n}-day MA')

    # Shade gap between MAs
    ax1.fill_between(prices.index, short_ma.values, long_ma.values,
                     where=(short_ma > long_ma), color='green', alpha=0.06)
    ax1.fill_between(prices.index, short_ma.values, long_ma.values,
                     where=(short_ma <= long_ma), color='red', alpha=0.06)

    # Crossover markers
    ax1.scatter(prices.index[cross_up],
                short_ma.values[cross_up],
                color='green', marker='^', s=100, zorder=5,
                label='Bullish cross')
    ax1.scatter(prices.index[cross_down],
                short_ma.values[cross_down],
                color='red', marker='v', s=100, zorder=5,
                label='Bearish cross')

    ax1.set_title(f'Price chart: {short_n}-day MA vs {long_n}-day MA crossover',
                  fontsize=12)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── Price Oscillator ──
    ax2.plot(osc.index, osc.values, color='#534AB7', linewidth=1.0)
    ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax2.fill_between(osc.index, 0, osc.values,
                     where=(osc > 0), color='green', alpha=0.1)
    ax2.fill_between(osc.index, 0, osc.values,
                     where=(osc <= 0), color='red', alpha=0.1)

    # Same crossover markers on oscillator panel
    osc_cross_up = cross_up & osc.notna()
    osc_cross_down = cross_down & osc.notna()
    ax2.scatter(osc.index[osc_cross_up],
                [0] * osc_cross_up.sum(),
                color='green', marker='^', s=100, zorder=5)
    ax2.scatter(osc.index[osc_cross_down],
                [0] * osc_cross_down.sum(),
                color='red', marker='v', s=100, zorder=5)

    ax2.set_title(f'Price Oscillator ({short_n}-MA − {long_n}-MA)',
                  fontsize=12)
    ax2.set_ylabel('MA Gap')
    ax2.grid(True, alpha=0.3)

    plt.suptitle('MA crossover = Oscillator zero-cross (identical bars)',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()

    # Verify equivalence
    valid = short_ma.notna() & long_ma.notna()
    match = ((short_ma[valid] > long_ma[valid]) ==
             (osc[valid] > 0)).mean() * 100
    print(f"MA crossover matches oscillator zero-cross: {match:.1f}%")


def compare_smoothing_levels(prices: pd.Series, n: int = 20):
    """
    Compare all three levels of smoothing on the same data:
      1. Momentum (raw vs. raw)
      2. MA Oscillator (raw vs. smoothed)
      3. Price Oscillator (smoothed vs. smoothed)
    """
    mom = prices - prices.shift(n)
    ma_osc = prices - prices.rolling(window=n).mean()
    price_osc = compute_price_oscillator(prices, short_n=n // 2, long_n=n)

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True,
                              gridspec_kw={'height_ratios': [2, 1, 1, 1]})

    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].grid(True, alpha=0.3)

    oscs = [
        (mom, '#E24B4A', f'Momentum ({n}-day): raw − raw'),
        (ma_osc, '#378ADD', f'MA Oscillator: price − {n}-MA'),
        (price_osc, '#534AB7', f'Price Oscillator: {n//2}-MA − {n}-MA'),
    ]

    for i, (osc, color, title) in enumerate(oscs):
        ax = axes[i + 1]
        ax.plot(osc.index, osc.values, color=color, linewidth=0.9)
        ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
        crosses = ((osc.shift(1) * osc) < 0).sum()
        ax.set_title(f'{title}  |  zero-crossovers: {crosses}', fontsize=11)
        ax.grid(True, alpha=0.3)

    plt.suptitle('Smoothing ladder: noise decreases, lag increases',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


def convergence_divergence_phases(prices: pd.Series,
                                   short_n: int = 10,
                                   long_n: int = 20):
    """
    Label the four phases of the Price Oscillator to show
    convergence and divergence of the two MAs.

    This is the conceptual foundation of MACD naming.
    """
    osc = compute_price_oscillator(prices, short_n, long_n)
    osc_change = osc.diff()

    phase = pd.Series('', index=prices.index)
    phase[(osc > 0) & (osc_change > 0)] = 'Bullish divergence (MAs spreading apart)'
    phase[(osc > 0) & (osc_change <= 0)] = 'Bullish convergence (MAs coming together)'
    phase[(osc <= 0) & (osc_change < 0)] = 'Bearish divergence (MAs spreading apart)'
    phase[(osc <= 0) & (osc_change >= 0)] = 'Bearish convergence (MAs coming together)'

    print(f"=== Convergence/Divergence Phases ({short_n}/{long_n}) ===")
    print(f"Last 10 bars:\n")
    print(pd.DataFrame({
        'Price': prices.round(2),
        'Oscillator': osc.round(3),
        'Change': osc_change.round(3),
        'Phase': phase,
    }).tail(10).to_string())


def price_osc_to_macd_comparison(prices: pd.Series):
    """
    Show that a Price Oscillator with 12/26 SMA is nearly identical
    in shape to MACD (which uses 12/26 EMA). Demonstrates that
    MACD is just a specific Price Oscillator variant.
    """
    po_sma = compute_price_oscillator(prices, 12, 26, ma_type='sma')
    po_ema = compute_price_oscillator(prices, 12, 26, ma_type='ema')

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9), sharex=True,
                                         gridspec_kw={'height_ratios': [2, 1, 1]})

    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    ax2.plot(po_sma.index, po_sma.values, color='#E24B4A', linewidth=0.9)
    ax2.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    ax2.set_title('Price Oscillator: SMA(12) − SMA(26)', fontsize=11)
    ax2.grid(True, alpha=0.3)

    ax3.plot(po_ema.index, po_ema.values, color='#378ADD', linewidth=0.9)
    ax3.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    ax3.set_title('MACD line: EMA(12) − EMA(26)', fontsize=11)
    ax3.grid(True, alpha=0.3)

    plt.suptitle('Price Oscillator (SMA) vs MACD (EMA) — same concept, slight timing difference',
                 fontsize=12, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


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

    # ── Crossover equivalence ──
    demonstrate_crossover_equivalence(prices, short_n=10, long_n=20)

    # ── Smoothing ladder comparison ──
    compare_smoothing_levels(prices, n=20)

    # ── Convergence/divergence phases ──
    print()
    convergence_divergence_phases(prices, short_n=10, long_n=20)

    # ── Price Oscillator → MACD comparison ──
    print()
    price_osc_to_macd_comparison(prices)

    # ── Division variant ──
    print("\n=== Division Variant ===")
    po_sub = compute_price_oscillator(prices, 10, 20, method='subtract')
    po_div = compute_price_oscillator(prices, 10, 20, method='divide')
    print(f"Subtraction: {po_sub.iloc[-1]:.3f} (equilibrium = 0)")
    print(f"Division:    {po_div.iloc[-1]:.4f} (equilibrium = 1.0)")
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_price_oscillator()` | Core: Short MA − Long MA, with SMA/EMA and subtract/divide options | The versatile building block — MACD is one configuration of this |
| `demonstrate_crossover_equivalence()` | Dual-panel: MA crossover on price chart = zero-cross on oscillator | Crossover markers on same bars, proven numerically |
| `compare_smoothing_levels()` | Momentum vs MA Oscillator vs Price Oscillator side-by-side | Shows noise decreasing and crossover count dropping at each level |
| `convergence_divergence_phases()` | Labels the four convergence/divergence phases | The conceptual foundation of the MACD name |
| `price_osc_to_macd_comparison()` | SMA(12)−SMA(26) vs EMA(12)−EMA(26) | Proves MACD is just a Price Oscillator with EMA |

### Key Implementation Notes

1. **`compute_price_oscillator()`** accepts both `sma` and `ema` for the MA type. When you call it with `ma_type='ema', short_n=12, long_n=26`, you get the MACD line. This makes the relationship explicit in code — MACD is literally `compute_price_oscillator(prices, 12, 26, ma_type='ema')`.

2. **`compare_smoothing_levels()`** is the function that ties concepts 6–10 together. It shows all three oscillators on the same data with crossover counts. You'll see Momentum has the most crossovers (noisiest), the MA Oscillator has fewer, and the Price Oscillator has the fewest (smoothest). The smoothing ladder is visible in actual numbers.

3. **`convergence_divergence_phases()`** labels each bar with its convergence/divergence state. This prepares you for MACD, where these phases are the core of the analysis. The names literally come from what the two MAs are doing: converging (coming together) or diverging (spreading apart).

4. **`price_osc_to_macd_comparison()`** shows that swapping SMA for EMA produces a very similar shape with slightly different timing. The EMA version (MACD) reacts a bit faster because exponential weighting emphasizes recent prices. But the overall character is the same — proving MACD is evolutionary, not revolutionary.

---

## Connection to Broader Framework

### Link to [[Moving Average-Based Oscillator]]
The Price Oscillator is the next step on the smoothing ladder:
- MA Oscillator: `price − MA` → one input smoothed
- Price Oscillator: `short MA − long MA` → both inputs smoothed
- Same family, more filtering, more lag

### Link to [[MACD]]
MACD = Price Oscillator with three specific choices:
1. EMA instead of SMA
2. Periods 12 and 26
3. Added 9-day signal line

A Price Oscillator with `ma_type='ema', short_n=12, long_n=26` IS the MACD line. Understanding this means MACD is not a new concept — it's a specific configuration of something you already know.

### Link to [[Moving Averages]] (Chapter 3) and Chapter 14
The Price Oscillator is the **oscillator representation** of the moving average crossover system. Same signal, different display. Chapter 14 covers MA crossover as a trend-following system; Chapter 6 presents the same mechanics as a countertrend oscillator. Same math, different intent.

### Link to [[Equilibrium Line]]
Price Oscillator equilibrium at zero means: short MA = long MA. This is the most "natural" equilibrium interpretation — it's the exact moment the two trend timeframes agree on the current price level. Any deviation represents a disagreement between timeframes — which is momentum.

### Link to [[Oscillator Sensitivity]]
The Price Oscillator has **two** N parameters (short and long MA lengths), giving you more control over sensitivity than single-parameter oscillators. The gap between them matters:
- Close together (e.g., 8/12): very sensitive, more crossovers
- Far apart (e.g., 5/40): less sensitive, fewer but more significant crossovers
- The ratio between the two periods controls how different the "two runners" are in speed
