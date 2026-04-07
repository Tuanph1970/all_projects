# MACD (Moving Average Convergence-Divergence)
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 114–116)
**Tags:** #technical-analysis #MACD #oscillators #momentum #schwager #moving-average #crossover #signal-line #indicators
**Related:** [[Oscillators]] · [[Price Oscillator]] · [[Moving Average-Based Oscillator]] · [[Momentum]] · [[Equilibrium Line]] · [[Overbought and Oversold]] · [[Divergence]] · [[Moving Averages]]

---

## Definition

MACD is a **specific, named configuration** of the [[Price Oscillator]] developed by Gerald Appel. It consists of three components:

```
MACD Line    = 12-day EMA − 26-day EMA        (the core oscillator)
Signal Line  = 9-day EMA of the MACD Line     (smoothed oscillator)
Histogram    = MACD Line − Signal Line         (gap between them)
```

> "The well-known moving average convergence-divergence (MACD) indicator is a unique version of the price oscillator." — Schwager

---

## Simple Analogy: Speedometer + Smoothed Average + Dashboard Gauge

Think of MACD as three layers of your car's speed monitoring:

- **MACD line** = your current speed reading (how far short-term momentum has pulled away from long-term)
- **Signal line** = the 9-second average of your speed (smoothed speed — doesn't jump around as much)
- **Histogram** = the gap between your current speed and the average (are you speeding up or slowing down *relative to your recent pattern*?)

When your current speed rises above your recent average speed → histogram goes positive → you're accelerating. When it falls below → histogram goes negative → you're decelerating. The crossover moment (histogram = 0) is when your speed equals your recent average — the transition point.

---

## Deconstructing the Name

"Moving Average **Convergence-Divergence**" describes the behavior of the two underlying EMAs:

| EMA Behavior | MACD Line | Name Origin |
|---|---|---|
| 12-EMA and 26-EMA **spreading apart** | Moving away from zero | **Divergence** — the MAs are diverging |
| 12-EMA and 26-EMA **coming together** | Moving toward zero | **Convergence** — the MAs are converging |

⚠️ This is **not** the same as the "divergence" concept (price vs. oscillator disagreement) covered in [[Divergence]]. Same word, different meaning. The MACD name describes MA behavior; the divergence signal describes price-vs-momentum disagreement.

---

## Position on the Smoothing Ladder

```
Momentum         = Price − Price(N)            ← raw vs. raw
MA Oscillator    = Price − MA(N)               ← raw vs. smoothed
Price Oscillator = MA(short) − MA(long)        ← smoothed vs. smoothed
MACD             = EMA(12) − EMA(26)           ← smoothed vs. smoothed (EMA)
                   + 9-day signal line          ← oscillator itself smoothed
                   + histogram                  ← rate of change of oscillator
```

MACD sits at the top of the ladder — maximum smoothing, most lag, but cleanest signals.

---

## The Three Components

### Component 1: MACD Line (EMA12 − EMA26)

A [[Price Oscillator]] with exponential moving averages. Measures the **gap between short-term and long-term trend**.

| MACD Line Position | Meaning |
|---|---|
| Above zero | 12-EMA above 26-EMA — short-term trend is bullish |
| At zero | 12-EMA equals 26-EMA — the EMAs are crossing |
| Below zero | 12-EMA below 26-EMA — short-term trend is bearish |
| Far from zero | Large gap between EMAs — strong momentum |
| Near zero | Small gap — weak momentum or transition |

**Why EMA instead of SMA?** Exponential averages give more weight to recent prices, making the oscillator slightly more responsive without shortening the lookback period (which would add noise).

> "A price oscillator that used 12- and 26-day moving averages would look much the same as the MACD except for the presence of the 9-day signal line." — Schwager

### Component 2: Signal Line (9-day EMA of MACD)

The key addition that distinguishes MACD from a plain Price Oscillator. It's a **moving average of the oscillator itself** — smoothing applied to the already-smoothed MACD line.

**How it generates signals:** Buy when MACD line crosses above the signal line; sell when it crosses below. This works "in much the same fashion as a moving average crossover" — because it IS one. The MACD line is the "price" and the signal line is its "moving average."

**Why it matters:** The signal line crossover fires **before** the zero-line crossover, giving earlier entries. The signal line stays close to the MACD line and turns when momentum shifts, often well before the MACD line reaches zero.

### Component 3: Histogram (MACD − Signal Line)

> "Simply the difference between the primary MACD line and the signal line, and is included to highlight crossovers of the two." — Schwager

| Histogram | Meaning |
|---|---|
| > 0 | MACD above signal line — bullish momentum |
| = 0 | MACD crossing signal line — crossover moment |
| < 0 | MACD below signal line — bearish momentum |
| Bars growing | Momentum accelerating |
| Bars shrinking | Momentum decelerating |

The histogram is the **momentum of the momentum** — the rate of change of the MACD line. When histogram bars peak and start shrinking (while still positive), it's the earliest signal that bullish momentum is losing energy. This maps to the **State 1 → State 2 transition** from [[Momentum]].

---

## Two Types of Crossover Signals

| Signal Type | What Crosses | Speed | Reliability | When to Use |
|---|---|---|---|---|
| **Signal line crossover** | MACD crosses above/below signal line | Faster — fires earlier | Lower — more false signals | Swing trading, earlier entries |
| **Zero-line crossover** | MACD crosses above/below zero | Slower — fires later | Higher — fewer false signals | Position trading, trend confirmation |

### The OB/OS Filter

Schwager mentions a third approach: establish overbought/oversold levels on MACD and only use crossovers that occur in extreme zones, to "filter out low-probability trades." This combines:
- The crossover signal (timing)
- The OB/OS framework (confirmation of extreme conditions)

Only acting on crossovers in extreme zones reduces false signals at the cost of missing crossovers in the neutral zone.

---

## Why MACD Became Popular — The Multi-Tool

MACD packages multiple readings into one panel:

| Reading | How to Get It |
|---|---|
| Trend direction | Which side of zero is the MACD line? |
| Momentum magnitude | How far from zero? |
| Momentum rate of change | Histogram bars growing or shrinking? |
| Fast crossover signal | MACD crossing signal line |
| Slow crossover signal | MACD crossing zero line |
| Trend health / divergence | Compare MACD peaks to price peaks |

### Schwager's Deflationary Framing

Despite MACD's popularity, Schwager deliberately presents it as **just another variation**:

> "One of the most significant aspects of Figures 6.1–6.5 is the similarity between the different oscillators despite the variety of calculations used to construct them... almost all popular oscillators are variations on these simple themes."

MACD is not magic. It measures momentum — the same thing every other oscillator in this chapter measures. Its advantage is packaging multiple readings conveniently. Its limitations (oscillator skew in trends, false signals, OB/OS problems) are identical to every other oscillator's.

---

## Properties

| Property | Value |
|---|---|
| **Type** | Unbounded oscillator |
| **Equilibrium line** | 0 (MACD line) |
| **Parameters** | 12 (fast EMA), 26 (slow EMA), 9 (signal line EMA) |
| **MA type** | Exponential (EMA) |
| **Components** | MACD line, signal line, histogram |
| **Signal types** | Signal line crossover (fast), zero-line crossover (slow) |
| **Inventor** | Gerald Appel |

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_macd(prices: pd.Series,
                  fast: int = 12,
                  slow: int = 26,
                  signal: int = 9) -> pd.DataFrame:
    """
    Complete MACD calculation.

    Parameters:
      prices: closing price series
      fast: fast EMA period (default 12)
      slow: slow EMA period (default 26)
      signal: signal line EMA period (default 9)

    Returns:
      DataFrame with columns: 'macd', 'signal', 'histogram'
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram,
    }, index=prices.index)


def detect_macd_signals(macd_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect both types of MACD crossover signals.

    Returns DataFrame with columns:
      - 'signal_cross': 'bullish' / 'bearish' / None
      - 'zero_cross': 'bullish' / 'bearish' / None
    """
    macd = macd_df['macd']
    sig = macd_df['signal']

    # Signal line crossovers
    prev_above_sig = (macd.shift(1) > sig.shift(1))
    curr_above_sig = (macd > sig)
    sig_bull = (~prev_above_sig) & curr_above_sig
    sig_bear = prev_above_sig & (~curr_above_sig)

    signal_cross = pd.Series(None, index=macd.index, dtype=object)
    signal_cross[sig_bull] = 'bullish'
    signal_cross[sig_bear] = 'bearish'

    # Zero-line crossovers
    prev_above_zero = (macd.shift(1) > 0)
    curr_above_zero = (macd > 0)
    zero_bull = (~prev_above_zero) & curr_above_zero
    zero_bear = prev_above_zero & (~curr_above_zero)

    zero_cross = pd.Series(None, index=macd.index, dtype=object)
    zero_cross[zero_bull] = 'bullish'
    zero_cross[zero_bear] = 'bearish'

    return pd.DataFrame({
        'signal_cross': signal_cross,
        'zero_cross': zero_cross,
    }, index=macd.index)


def detect_histogram_momentum(macd_df: pd.DataFrame) -> pd.Series:
    """
    Classify histogram behavior — the "momentum of momentum."

    Returns Series with:
      'accelerating_bullish' — histogram positive and growing
      'decelerating_bullish' — histogram positive but shrinking (early warning)
      'accelerating_bearish' — histogram negative and growing (more negative)
      'decelerating_bearish' — histogram negative but shrinking (early warning)
    """
    hist = macd_df['histogram']
    hist_change = hist.diff()

    state = pd.Series('neutral', index=hist.index)
    state[(hist > 0) & (hist_change > 0)] = 'accelerating_bullish'
    state[(hist > 0) & (hist_change <= 0)] = 'decelerating_bullish'
    state[(hist <= 0) & (hist_change < 0)] = 'accelerating_bearish'
    state[(hist <= 0) & (hist_change >= 0)] = 'decelerating_bearish'

    return state


def plot_macd_full(prices: pd.Series,
                    fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Complete MACD visualization: price + EMAs, MACD + signal + histogram.
    Shows both crossover types with markers.
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_df = compute_macd(prices, fast, slow, signal)
    signals = detect_macd_signals(macd_df)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1.2]})

    # ── Price + EMAs ──
    ax1.plot(prices.index, prices.values, color='#333333',
             linewidth=0.8, alpha=0.7, label='Price')
    ax1.plot(ema_fast.index, ema_fast.values, color='#E24B4A',
             linewidth=1.2, label=f'{fast}-EMA')
    ax1.plot(ema_slow.index, ema_slow.values, color='#378ADD',
             linewidth=1.2, label=f'{slow}-EMA')
    ax1.set_title(f'Price with {fast}/{slow}-day EMAs', fontsize=12)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── MACD panel ──
    ax2.plot(macd_df.index, macd_df['macd'].values,
             color='#534AB7', linewidth=1.2, label='MACD line')
    ax2.plot(macd_df.index, macd_df['signal'].values,
             color='#EF9F27', linewidth=1.2, linestyle='--',
             label='Signal line')
    ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='--', alpha=0.4)

    # Histogram as bars
    hist = macd_df['histogram']
    colors = ['#1D9E75' if v >= 0 else '#E24B4A' for v in hist.values]
    ax2.bar(macd_df.index, hist.values, color=colors, alpha=0.35, width=1.5)

    # Signal line crossover markers
    sig_bull = signals['signal_cross'] == 'bullish'
    sig_bear = signals['signal_cross'] == 'bearish'
    if sig_bull.any():
        ax2.scatter(macd_df.index[sig_bull],
                    macd_df['macd'].values[sig_bull],
                    color='#1D9E75', marker='^', s=60, zorder=5,
                    label='Signal cross (buy)')
    if sig_bear.any():
        ax2.scatter(macd_df.index[sig_bear],
                    macd_df['macd'].values[sig_bear],
                    color='#E24B4A', marker='v', s=60, zorder=5,
                    label='Signal cross (sell)')

    # Zero-line crossover markers
    zero_bull = signals['zero_cross'] == 'bullish'
    zero_bear = signals['zero_cross'] == 'bearish'
    if zero_bull.any():
        ax2.scatter(macd_df.index[zero_bull],
                    [0] * zero_bull.sum(),
                    color='#1D9E75', marker='D', s=50, zorder=5,
                    label='Zero cross (buy)')
    if zero_bear.any():
        ax2.scatter(macd_df.index[zero_bear],
                    [0] * zero_bear.sum(),
                    color='#E24B4A', marker='D', s=50, zorder=5,
                    label='Zero cross (sell)')

    ax2.set_title('MACD (line + signal + histogram)', fontsize=12)
    ax2.legend(fontsize=8, loc='upper left')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    # Print signal summary
    print(f"=== MACD Signal Summary ===")
    print(f"Signal line crossovers: "
          f"{sig_bull.sum()} bullish, {sig_bear.sum()} bearish")
    print(f"Zero-line crossovers:   "
          f"{zero_bull.sum()} bullish, {zero_bear.sum()} bearish")
    print(f"Signal line fires ~{(sig_bull.sum()+sig_bear.sum()) / max(zero_bull.sum()+zero_bear.sum(),1):.1f}x "
          f"more often than zero-line")


def compare_signal_timing(prices: pd.Series):
    """
    Show that signal line crossovers fire BEFORE zero-line crossovers.
    Measures the average lead time in bars.
    """
    macd_df = compute_macd(prices)
    signals = detect_macd_signals(macd_df)

    sig_bulls = signals.index[signals['signal_cross'] == 'bullish']
    zero_bulls = signals.index[signals['zero_cross'] == 'bullish']

    leads = []
    for zb in zero_bulls:
        # Find the most recent signal-line bullish cross before this zero cross
        prior_sigs = sig_bulls[sig_bulls < zb]
        if len(prior_sigs) > 0:
            last_sig = prior_sigs[-1]
            lead_bars = (zb - last_sig).days
            if lead_bars < 30:  # reasonable range
                leads.append(lead_bars)

    if leads:
        print(f"=== Signal Line Lead Time ===")
        print(f"Avg lead: {np.mean(leads):.1f} trading days before zero-line cross")
        print(f"Min lead: {min(leads)} days")
        print(f"Max lead: {max(leads)} days")
        print(f"(Signal line crossover fires earlier, giving a head start)")
    else:
        print("Insufficient data to measure lead time")


def decompose_macd(prices: pd.Series):
    """
    Show MACD is just a Price Oscillator (EMA version) + signal line.
    Decomposes MACD into its building blocks from the smoothing ladder.
    """
    # Level 1: Momentum
    mom = prices - prices.shift(12)

    # Level 2: MA Oscillator
    ma_osc = prices - prices.rolling(26).mean()

    # Level 3: Price Oscillator (SMA)
    po = prices.rolling(12).mean() - prices.rolling(26).mean()

    # Level 4: MACD (Price Oscillator with EMA)
    macd_df = compute_macd(prices)

    print("=== MACD Decomposition (last value) ===")
    print(f"Momentum (12-day):           {mom.iloc[-1]:.3f}")
    print(f"MA Oscillator (price-SMA26): {ma_osc.iloc[-1]:.3f}")
    print(f"Price Oscillator (SMA12-26): {po.iloc[-1]:.3f}")
    print(f"MACD line (EMA12-26):        {macd_df['macd'].iloc[-1]:.3f}")
    print(f"Signal line:                 {macd_df['signal'].iloc[-1]:.3f}")
    print(f"Histogram:                   {macd_df['histogram'].iloc[-1]:.3f}")
    print()
    print("Each level adds smoothing. MACD is the top of the ladder.")


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

    # ── Full MACD visualization ──
    plot_macd_full(prices)

    # ── Histogram momentum states ──
    macd_df = compute_macd(prices)
    hist_states = detect_histogram_momentum(macd_df)
    print("\n=== Histogram Momentum States (last 10 bars) ===")
    print(pd.DataFrame({
        'MACD': macd_df['macd'].round(3),
        'Signal': macd_df['signal'].round(3),
        'Histogram': macd_df['histogram'].round(3),
        'State': hist_states,
    }).tail(10))

    # ── Signal timing comparison ──
    print()
    compare_signal_timing(prices)

    # ── Decomposition ──
    print()
    decompose_macd(prices)
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_macd()` | Core: EMA(12)−EMA(26), signal line, histogram | Returns all three components in one DataFrame |
| `detect_macd_signals()` | Finds both crossover types | Separates signal-line crosses from zero-line crosses |
| `detect_histogram_momentum()` | Classifies histogram acceleration/deceleration | The "momentum of momentum" — earliest warning signal |
| `plot_macd_full()` | Complete dual-panel visualization with all markers | Shows both signal types visually with signal count comparison |
| `compare_signal_timing()` | Measures how many bars signal-line cross leads zero-line cross | Quantifies the speed advantage of signal-line crossovers |
| `decompose_macd()` | Shows MACD's place on the smoothing ladder | Prints all four oscillator levels side by side |

### Key Implementation Notes

1. **`compute_macd()`** uses `pandas.ewm(span=N, adjust=False)` for EMA calculation. The `adjust=False` parameter uses the recursive EMA formula (each day = price * k + prev_EMA * (1-k)) which is the standard real-time calculation method.

2. **`detect_histogram_momentum()`** captures the State 1→2 transition at the MACD level. When the histogram shifts from `accelerating_bullish` to `decelerating_bullish`, that's the earliest warning the current rally is losing steam — even before any crossover fires.

3. **`compare_signal_timing()`** measures the lead time quantitatively. You'll see that signal-line crossovers typically fire 3-8 bars before the corresponding zero-line crossover. That head start is the signal line's value — and its cost is the additional false signals it produces.

4. **`decompose_macd()`** is the conceptual capstone. It prints the last value from each level of the smoothing ladder (Momentum → MA Oscillator → Price Oscillator → MACD), showing how they're all related measurements of the same underlying phenomenon at different smoothing levels.

---

## Connection to Broader Framework

### Link to [[Price Oscillator]]
MACD IS a Price Oscillator. Specifically: `compute_price_oscillator(prices, 12, 26, ma_type='ema')` produces the MACD line. The signal line and histogram are additions on top. Understanding this means MACD is not a new concept — it's a decorated version of something you already know.

### Link to [[Oscillators]] — Same Limitations Apply
All the warnings from the Oscillators note apply to MACD:
- Skew in trending markets (MACD stays above/below zero for extended periods)
- False signal-line crossovers in choppy markets
- OB/OS levels require empirical calibration (unbounded oscillator)
- Best used as a "trading alert" with price confirmation, not as a standalone trigger

### Link to [[Divergence]]
MACD is one of the most commonly used oscillators for detecting price-vs-momentum divergence. When price makes a new high but the MACD line makes a lower high → bearish divergence → trend health warning. We'll cover this in detail in the Divergence notes.

### Link to [[Momentum]] — Four States at Every Level
The histogram's four states (accelerating/decelerating × bullish/bearish) are the same four momentum states from the Momentum note, applied one level higher. The State 1→2 transition (accelerating → decelerating while still bullish) is the earliest signal at every level — and the histogram captures it for the MACD.

### Link to [[Oscillator Sensitivity]]
MACD's fixed parameters (12/26/9) represent Appel's chosen point on the sensitivity spectrum. These are not universal constants — they can be adjusted. Shorter EMAs (e.g., 8/17/9) produce a more sensitive MACD; longer ones (e.g., 19/39/9) produce a smoother one. The tradeoff is the same as with any N parameter.

### The Complete Smoothing Ladder

```
Momentum         = Price − Price(N)          ← concept 6
MA Oscillator    = Price − MA(N)             ← concept 9
Price Oscillator = MA(short) − MA(long)      ← concept 10
MACD line        = EMA(12) − EMA(26)         ← concept 11 (we are here)
Signal line      = 9-EMA of MACD line        ← smoothing the smoothed
Histogram        = MACD − Signal             ← rate of change of the smoothed
```

Each rung adds processing. The signal quality improves (fewer false signals) but the speed decreases (more lag). There is no free lunch — only choices about where on the spectrum you want to operate.
