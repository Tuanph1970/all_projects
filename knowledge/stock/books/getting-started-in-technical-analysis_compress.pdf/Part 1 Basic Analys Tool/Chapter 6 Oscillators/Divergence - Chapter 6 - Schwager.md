# Divergence
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 117–119)
**Tags:** #technical-analysis #divergence #oscillators #momentum #schwager #bearish-divergence #bullish-divergence #trend-health #indicators
**Related:** [[Oscillators]] · [[Momentum]] · [[RSI]] · [[Stochastics]] · [[MACD]] · [[Overbought and Oversold]] · [[Failed Signals]] · [[Trends]]

---

## Definition

Divergence is "the phenomenon of price and momentum moving in opposite directions." — Schwager (Glossary)

It is the second major oscillator signal alongside [[Overbought and Oversold]]:
- **OB/OS** measures *how extreme* the current momentum is
- **Divergence** measures whether momentum is *confirming or contradicting* what price is doing

### The Core Pattern
```
Price makes a new extreme → oscillator does NOT confirm with its own new extreme → trend is vulnerable
```

---

## Simple Analogy: A Runner's Lap Times

Think of a runner doing consecutive laps:

| Lap | Time | Interpretation |
|---|---|---|
| 1 | 60 sec | Strong start |
| 2 | 58 sec | Accelerating — healthy momentum |
| 3 | 62 sec | Slower — still running, but pace is fading |
| 4 | 67 sec | Even slower — fatigue setting in |

The runner has completed four laps (price keeps making "new highs" — further around the track). But each lap takes longer (momentum is declining).

- If you only look at **total distance** (price) → things look fine, still advancing
- If you look at **lap times** (oscillator) → the runner is fading

**That's divergence:** the distance keeps increasing, but the pace is deteriorating. The runner hasn't stopped — but the deterioration suggests they might.

> The divergence only becomes actionable when the runner **actually stops or stumbles** (price confirmation). Fading lap times alone don't guarantee a collapse — marathon runners routinely slow down without stopping.

---

## Bearish Divergence (in uptrends)

Called "bearish" because it portends a potential **downturn in prices**:

```
Price:      High ──→ Higher High         (new price high ✅)
Oscillator: Peak ──→ Lower Peak          (no new momentum high ❌)
                      ↑ DIVERGENCE
```

> "A higher price high accompanied by a lower oscillator high... the market has posted a new high, but momentum, by failing to confirm the price move with a new high of its own, is revealing trend vulnerability." — Schwager

### Schwager's Citicorp Example (Figure 6.8)
- Price posts consecutive higher highs from Nov 1996 to Oct 1997
- RSI peaks are **progressively lower** at each price high (points A, B, C, D)
- "Momentum has diverged from price, suggesting the uptrend is losing steam"

### Traditional Response
- Establish a short position anticipating a reversal, OR
- Liquidate / reduce an existing long position as protection

---

## Bullish Divergence (in downtrends)

Called "bullish" because it portends a potential **upturn in prices**:

```
Price:      Low ──→ Lower Low            (new price low ✅)
Oscillator: Trough → Higher Trough       (no new momentum low ❌)
                      ↑ DIVERGENCE
```

The decline is losing force — each push down is weaker than the last.

### Schwager's 3Com Example (Figures 6.1–6.7)
- Price makes a lower low from February to April 1997
- Oscillator lows in April are **higher** than February lows
- Visible across Momentum, ROC, MA oscillator, price oscillator, MACD, RSI
- "Every indicator... shows a classic divergence" — confirming it's a property of momentum itself, not a specific formula

---

## The Critical Warning: Multiple Divergences

This is Schwager's most important practical point about divergence:

> "Unfortunately, divergences rarely occur only between the penultimate and final peaks in an advance, or the last two lows in a downtrend."

### The Problem
Divergences can appear **multiple times** during a trend, long before the actual reversal.

### Schwager's Citicorp Evidence (Figure 6.8)
The chart shows divergences at:
- Points X → Y (early in the uptrend)
- Points Y → Z (still early)
- Points A → B
- Points B → C
- Points C → D

**Five separate bearish divergences** during a sustained uptrend. A trader who shorted at the first divergence (X→Y) would have entered "even more prematurely" and watched the trend continue for another year+.

### Why Multiple Divergences Happen
In a strong trend, the **initial momentum burst is almost always the strongest**. Every subsequent rally within the trend tends to have slightly less momentum — because the early, easy gains have already been captured.

This means divergence is **normal in healthy trends**, not necessarily a sign the trend is about to end.

> **Marathon analogy:** A marathon runner's fastest lap is almost always early in the race. Every subsequent lap tends to be slightly slower. That doesn't mean the runner is about to collapse — it means they've settled into a sustainable pace. The divergence between early and later lap times is *expected*, not alarming.

### The Implication
Divergence without price confirmation is a **hypothesis** ("the trend may be weakening"), not a **conclusion** ("the trend is reversing"). The confirmation must come from price: a support/resistance break, a chart pattern reversal, a failed signal.

---

## Divergence Across All Oscillators

Schwager demonstrates divergence across every oscillator on the same price data (3Com, Figures 6.1–6.7):

| Oscillator | Shows Feb/Apr 1997 Divergence? |
|---|---|
| RSI | Yes |
| Momentum | Yes |
| ROC | Yes |
| MA Oscillator | Yes |
| Price Oscillator | Yes |
| MACD | Yes |
| Stochastics | No (exception in this case) |

> This reinforces that divergence is a property of **momentum itself**, not of any specific formula. All oscillators see it because they all measure the same underlying phenomenon.

---

## Divergence vs. OB/OS: Two Different Warnings

| Property | OB/OS Signal | Divergence Signal |
|---|---|---|
| **What it measures** | Absolute momentum level (how extreme) | Relative momentum direction (confirming or not) |
| **When it fires** | When oscillator reaches a threshold | When oscillator peak/trough fails to match price peak/trough |
| **What it tells you** | "Momentum is at an extreme level" | "Momentum is not confirming price's new extreme" |
| **False signal risk** | High in trends (oscillator stays extreme) | High in trends (multiple divergences before reversal) |
| **Requires** | Fixed or empirical thresholds | Comparison of two successive peaks or troughs |
| **Best used as** | Trading alert with price confirmation | Trading alert with price confirmation |

Both require the same treatment: treat as an alert, wait for price confirmation, don't act on the oscillator signal alone.

---

## Properties

| Property | Value |
|---|---|
| **Type** | Oscillator-to-price comparison signal |
| **Variants** | Bearish (uptrend: higher price high, lower oscillator high) and Bullish (downtrend: lower price low, higher oscillator low) |
| **Applicable oscillators** | All — RSI, MACD, Momentum, ROC, Stochastics, Price Oscillator |
| **Reliability** | Moderate — can produce multiple false signals in trends |
| **Best confirmation** | Price pattern reversal, support/resistance break, failed signal |

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI with Wilder's smoothing."""
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1]*(period-1) + gains.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1]*(period-1) + losses.iloc[i]) / period
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def find_local_peaks(series: pd.Series, order: int = 5) -> pd.Series:
    """
    Find local maxima: points higher than 'order' neighbors on each side.
    Returns boolean Series (True at peak locations).
    """
    peaks = pd.Series(False, index=series.index)
    for i in range(order, len(series) - order):
        window = series.iloc[i - order:i + order + 1]
        if series.iloc[i] == window.max() and not window.duplicated().all():
            peaks.iloc[i] = True
    return peaks


def find_local_troughs(series: pd.Series, order: int = 5) -> pd.Series:
    """
    Find local minima: points lower than 'order' neighbors on each side.
    Returns boolean Series (True at trough locations).
    """
    troughs = pd.Series(False, index=series.index)
    for i in range(order, len(series) - order):
        window = series.iloc[i - order:i + order + 1]
        if series.iloc[i] == window.min() and not window.duplicated().all():
            troughs.iloc[i] = True
    return troughs


def detect_divergence(prices: pd.Series,
                       oscillator: pd.Series,
                       peak_order: int = 5) -> pd.DataFrame:
    """
    Detect classic divergences between price and oscillator.

    Bearish divergence: price higher high + oscillator lower high
    Bullish divergence: price lower low + oscillator higher low

    Parameters:
      prices: closing price series
      oscillator: any oscillator series (RSI, MACD, Momentum, etc.)
      peak_order: number of bars on each side to define a local peak/trough

    Returns:
      DataFrame with divergence events:
        'date', 'type', 'price_prev', 'price_curr',
        'osc_prev', 'osc_curr', 'price_prev_date', 'price_curr_date'
    """
    results = []

    # ── Bearish divergence (compare peaks) ──
    price_peaks = find_local_peaks(prices, peak_order)
    osc_peaks = find_local_peaks(oscillator, peak_order)

    price_peak_dates = prices.index[price_peaks]
    price_peak_vals = prices[price_peaks]

    for i in range(1, len(price_peak_dates)):
        curr_date = price_peak_dates[i]
        prev_date = price_peak_dates[i - 1]

        # Price made a higher high
        if price_peak_vals.iloc[i] > price_peak_vals.iloc[i - 1]:
            # Find nearest oscillator peak to each price peak
            osc_near_prev = oscillator.iloc[
                max(0, prices.index.get_loc(prev_date) - peak_order):
                prices.index.get_loc(prev_date) + peak_order + 1
            ]
            osc_near_curr = oscillator.iloc[
                max(0, prices.index.get_loc(curr_date) - peak_order):
                min(len(oscillator), prices.index.get_loc(curr_date) + peak_order + 1)
            ]

            osc_prev_val = osc_near_prev.max()
            osc_curr_val = osc_near_curr.max()

            # Oscillator made a lower high → bearish divergence
            if osc_curr_val < osc_prev_val:
                results.append({
                    'date': curr_date,
                    'type': 'bearish',
                    'price_prev': round(price_peak_vals.iloc[i - 1], 2),
                    'price_curr': round(price_peak_vals.iloc[i], 2),
                    'osc_prev': round(osc_prev_val, 2),
                    'osc_curr': round(osc_curr_val, 2),
                    'prev_date': prev_date,
                })

    # ── Bullish divergence (compare troughs) ──
    price_troughs = find_local_troughs(prices, peak_order)
    price_trough_dates = prices.index[price_troughs]
    price_trough_vals = prices[price_troughs]

    for i in range(1, len(price_trough_dates)):
        curr_date = price_trough_dates[i]
        prev_date = price_trough_dates[i - 1]

        # Price made a lower low
        if price_trough_vals.iloc[i] < price_trough_vals.iloc[i - 1]:
            osc_near_prev = oscillator.iloc[
                max(0, prices.index.get_loc(prev_date) - peak_order):
                prices.index.get_loc(prev_date) + peak_order + 1
            ]
            osc_near_curr = oscillator.iloc[
                max(0, prices.index.get_loc(curr_date) - peak_order):
                min(len(oscillator), prices.index.get_loc(curr_date) + peak_order + 1)
            ]

            osc_prev_val = osc_near_prev.min()
            osc_curr_val = osc_near_curr.min()

            # Oscillator made a higher low → bullish divergence
            if osc_curr_val > osc_prev_val:
                results.append({
                    'date': curr_date,
                    'type': 'bullish',
                    'price_prev': round(price_trough_vals.iloc[i - 1], 2),
                    'price_curr': round(price_trough_vals.iloc[i], 2),
                    'osc_prev': round(osc_prev_val, 2),
                    'osc_curr': round(osc_curr_val, 2),
                    'prev_date': prev_date,
                })

    return pd.DataFrame(results)


def plot_divergence(prices: pd.Series,
                     oscillator: pd.Series,
                     divergences: pd.DataFrame,
                     osc_name: str = 'RSI',
                     ob: Optional[float] = 70,
                     os_level: Optional[float] = 30):
    """
    Dual-panel chart with divergence lines drawn between the
    corresponding peaks/troughs on both price and oscillator panels.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1.2]})

    # ── Price ──
    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # ── Oscillator ──
    ax2.plot(oscillator.index, oscillator.values, color='#534AB7', linewidth=1.0)
    if ob is not None:
        ax2.axhline(y=ob, color='red', linewidth=0.5, linestyle=':')
    if os_level is not None:
        ax2.axhline(y=os_level, color='green', linewidth=0.5, linestyle=':')
    ax2.axhline(y=50, color='black', linewidth=0.4, linestyle='--')
    if ob is not None and os_level is not None:
        ax2.set_ylim(0, 100)
    ax2.set_title(f'{osc_name}', fontsize=12)
    ax2.grid(True, alpha=0.3)

    # ── Draw divergence lines ──
    for _, div in divergences.iterrows():
        prev_date = div['prev_date']
        curr_date = div['date']

        if div['type'] == 'bearish':
            color = '#E24B4A'
            # Line on price (higher high)
            ax1.plot([prev_date, curr_date],
                     [div['price_prev'], div['price_curr']],
                     color=color, linewidth=2, linestyle='-', alpha=0.7)
            ax1.scatter([prev_date, curr_date],
                       [div['price_prev'], div['price_curr']],
                       color=color, s=50, zorder=5)
            # Line on oscillator (lower high)
            ax2.plot([prev_date, curr_date],
                     [div['osc_prev'], div['osc_curr']],
                     color=color, linewidth=2, linestyle='-', alpha=0.7)
            ax2.scatter([prev_date, curr_date],
                       [div['osc_prev'], div['osc_curr']],
                       color=color, s=50, zorder=5)

        elif div['type'] == 'bullish':
            color = '#1D9E75'
            ax1.plot([prev_date, curr_date],
                     [div['price_prev'], div['price_curr']],
                     color=color, linewidth=2, linestyle='-', alpha=0.7)
            ax1.scatter([prev_date, curr_date],
                       [div['price_prev'], div['price_curr']],
                       color=color, s=50, zorder=5)
            ax2.plot([prev_date, curr_date],
                     [div['osc_prev'], div['osc_curr']],
                     color=color, linewidth=2, linestyle='-', alpha=0.7)
            ax2.scatter([prev_date, curr_date],
                       [div['osc_prev'], div['osc_curr']],
                       color=color, s=50, zorder=5)

    bear_count = (divergences['type'] == 'bearish').sum()
    bull_count = (divergences['type'] == 'bullish').sum()
    ax1.set_title(f'Price — divergences: {bear_count} bearish (red), '
                  f'{bull_count} bullish (green)', fontsize=12)

    plt.tight_layout()
    plt.show()


def demonstrate_multiple_divergences(n_days: int = 300):
    """
    Create a scenario with multiple bearish divergences during
    a sustained uptrend — Schwager's key warning.
    Shows how divergences can fire repeatedly while the trend continues.
    """
    np.random.seed(42)

    # Strong uptrend with decelerating momentum phases
    trend = np.concatenate([
        np.linspace(0, 15, 80),   # strong initial rally
        np.linspace(15, 17, 30),  # brief pause
        np.linspace(17, 28, 70),  # second rally (less steep)
        np.linspace(28, 30, 30),  # brief pause
        np.linspace(30, 38, 60),  # third rally (even less steep)
        np.linspace(38, 32, 30),  # actual reversal
    ])
    noise = np.random.normal(0, 1.0, n_days)
    prices = pd.Series(
        100 + trend + noise,
        index=pd.date_range('2024-01-01', periods=n_days, freq='B'),
        name='Close'
    )

    rsi = compute_rsi(prices, 14)
    divergences = detect_divergence(prices, rsi, peak_order=8)

    bearish = divergences[divergences['type'] == 'bearish']

    print(f"=== Multiple Divergence Demonstration ===")
    print(f"Uptrend duration: ~{n_days} bars")
    print(f"Bearish divergences detected: {len(bearish)}")
    if len(bearish) > 0:
        print(f"\nEach divergence:")
        for i, (_, d) in enumerate(bearish.iterrows()):
            print(f"  #{i+1} at {d['date'].strftime('%Y-%m-%d')}: "
                  f"Price {d['price_prev']:.0f}→{d['price_curr']:.0f} (higher), "
                  f"RSI {d['osc_prev']:.0f}→{d['osc_curr']:.0f} (lower)")

        print(f"\nA trader shorting at divergence #1 would have lost money")
        print(f"as the trend continued for {(bearish.iloc[-1]['date'] - bearish.iloc[0]['date']).days} "
              f"more days after the first signal.")

    plot_divergence(prices, rsi, divergences, osc_name='14-day RSI')


def divergence_across_oscillators(prices: pd.Series, peak_order: int = 8):
    """
    Show that the same divergence appears across multiple oscillators.
    Schwager's point: divergence is a property of momentum, not a formula.
    """
    mom = prices - prices.shift(10)
    rsi = compute_rsi(prices, 14)
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26

    oscillators = {
        'Momentum (10)': mom,
        'RSI (14)': rsi,
        'MACD': macd,
    }

    print("=== Divergence Across Oscillators ===")
    for name, osc in oscillators.items():
        divs = detect_divergence(prices, osc, peak_order)
        bearish = (divs['type'] == 'bearish').sum() if len(divs) > 0 else 0
        bullish = (divs['type'] == 'bullish').sum() if len(divs) > 0 else 0
        print(f"  {name:<20} bearish: {bearish}  bullish: {bullish}")

    print("\n(Similar counts across oscillators = same phenomenon detected)")


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    # ── Multiple divergence warning demo ──
    demonstrate_multiple_divergences()

    # ── Cross-oscillator detection ──
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
        index=pd.date_range('2024-01-01', periods=n_days, freq='B')
    )
    print()
    divergence_across_oscillators(prices)
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `find_local_peaks()` | Identifies local maxima in any series | Used for both price peaks and oscillator peaks |
| `find_local_troughs()` | Identifies local minima | Used for both price troughs and oscillator troughs |
| `detect_divergence()` | Core detection: finds bearish and bullish divergences | Compares successive price peaks/troughs to oscillator peaks/troughs |
| `plot_divergence()` | Dual-panel chart with divergence lines drawn | Lines slope UP on price (higher high) but DOWN on oscillator (lower high) |
| `demonstrate_multiple_divergences()` | Creates a scenario with repeated false divergences | Schwager's key warning: multiple divergences before actual reversal |
| `divergence_across_oscillators()` | Shows same divergence detected by Momentum, RSI, MACD | Proves divergence is a momentum property, not formula-specific |

### Key Implementation Notes

1. **`detect_divergence()`** works with **any** oscillator — pass in RSI, MACD, Momentum, stochastics %K, or any other series. The function doesn't care about the oscillator type because divergence is a property of momentum itself.

2. **`peak_order`** parameter controls how "significant" a peak must be. Higher values (8-10) find major peaks only; lower values (3-5) find minor peaks too — producing more divergences but of lower quality. This is another instance of the sensitivity tradeoff.

3. **`demonstrate_multiple_divergences()`** deliberately constructs a price series with decelerating rallies — each phase is less steep than the prior one. This guarantees multiple bearish divergences before the actual reversal, mimicking Schwager's Citicorp scenario. The output counts how many divergences fire and how long the trend continues after the first one.

4. **`plot_divergence()`** draws lines connecting the compared peaks/troughs on **both** the price panel and the oscillator panel. The visual signature of bearish divergence: the price line slopes UP (higher high) while the oscillator line slopes DOWN (lower high). This cross-panel comparison is the visual that makes divergence intuitive.

---

## Connection to Broader Framework

### Link to [[Oscillators]] — Use Case 3 (Trend Health Diagnostic)
Divergence is the primary tool for Use Case 3. It doesn't generate trade entries (that would be Use Case 2, which fails in trends). Instead, it provides **diagnostic information** about the trend's internal condition. The correct response to divergence is not "short the market" but "be aware the trend may be weakening and watch for price confirmation."

### Link to [[Overbought and Oversold]]
OB/OS and divergence are the two countertrend signals oscillators produce. They can reinforce each other: an overbought reading combined with bearish divergence is a stronger alert than either alone. But both still require price confirmation — neither is a standalone trigger.

### Link to [[Momentum]] — The Price vs. Momentum Distinction
Divergence is the purest expression of the price vs. momentum distinction from the Momentum note. When price and momentum agree (both making new highs), the trend is healthy. When they diverge, the trend's engine is weakening. The ball analogy from that note applies: deceleration (divergence) happens before the ball stops and reverses.

### Link to [[Failed Signals]] (Chapter 11)
A divergence signal that doesn't produce a reversal is itself a type of failed signal. Per Schwager's framework, a failed signal suggests strength in the opposite direction — if bearish divergence doesn't produce a downturn, the trend may be even more robust than the oscillator suggests.

### Link to [[MACD + Volume Confirmation]]
Combining oscillator divergence with OBV divergence creates a "double divergence" — momentum fading AND participation drying up simultaneously. Two independent dimensions warning of the same thing. This is the strongest warning configuration in our framework.
