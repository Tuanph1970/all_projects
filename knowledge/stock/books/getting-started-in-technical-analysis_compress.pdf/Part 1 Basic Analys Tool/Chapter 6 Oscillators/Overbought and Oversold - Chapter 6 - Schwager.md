# Overbought and Oversold Levels
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 111–112, 116–119), Chapter 10 (pp. 148–149)
**Tags:** #technical-analysis #overbought #oversold #oscillators #momentum #schwager #countertrend #indicators
**Related:** [[Oscillators]] · [[Momentum]] · [[Equilibrium Line]] · [[Divergence]] · [[RSI]] · [[Stochastics]] · [[MACD]] · [[Failed Signals]] · [[Trading Ranges]] · [[Trends]]

---

## Definition

**Overbought:** when prices have risen too far, too fast and are ripe for a downward correction.

**Oversold:** when prices have fallen too far, too fast and are ripe for an upward correction.

These are **momentum extremes** — not predictions, but probability statements. They indicate that the pace of the current move is historically unusual and such extremes *tend* to resolve with at least a partial reversal. The keyword is "tend to" — not "always," not "will."

---

## Simple Analogy: The Rubber Band

Think of price as a **rubber band** stretched around a moving average (or equilibrium line).

- **Normal stretch:** the band is taut but comfortable — momentum is positive or negative but not extreme. No signal.
- **Overbought:** the band is stretched far above — the further it stretches, the greater the *potential* snapback force. But a strong enough hand (trend) can hold it stretched for a long time.
- **Oversold:** the band is stretched far below — same snapback potential in reverse.
- **Snap:** when the force holding the stretch (trend momentum) weakens, the band snaps back toward the center.

The critical insight: **how strong the hand is matters more than how stretched the band is.** In a range, there's no hand — the band snaps back reliably. In a strong trend, the hand holds firm — and the band stays stretched far longer than you'd expect.

This is why the same OB/OS reading means different things in different market contexts.

---

## Relationship to Equilibrium Line

The [[Equilibrium Line]] and OB/OS levels form a **complete reading system**:

| Component | What It Tells You | Sea Level Analogy |
|---|---|---|
| **Equilibrium Line** | Which **side of neutral** you're on (positive vs. negative momentum) | Sea level — are you above or below water? |
| **OB/OS Levels** | How **far from neutral** you've gone (extreme vs. moderate) | Flood/drought markers — are you at dangerous extremes? |

Together: direction (above/below the line) + extremity (distance from the line) = full momentum context.

---

## How Levels Are Set — Two Systems

### For Unbounded Oscillators (Momentum, ROC, Price Oscillator, MACD)

These have **no fixed upper or lower limits** — the oscillator can theoretically go to infinity.

**Method:** Review historical readings and pick levels that isolate the most extreme values.

**Schwager's guideline:** Capture roughly the highest and lowest **10%** of oscillator readings. Review past peaks and troughs to find where extreme readings cluster.

**The problem:** "There is no guarantee that overbought or oversold levels set today will be appropriate for market conditions a month from now." Market volatility changes, and the oscillator's range shifts with it. What was extreme in a calm market may be normal in a volatile one.

### For Normalized (Bounded) Oscillators (RSI, Stochastics)

These have **fixed boundaries** (0 to 100), making level-setting simpler.

| Oscillator | Common OB Level | Common OS Level |
|---|---|---|
| **RSI** | 70 | 30 |
| **Stochastics** | 80 | 20 |

These are conventions, not laws. Alternative choices: 75/25, 80/20 for RSI, depending on market context.

### The Threshold Tradeoff (Precision vs. Recall)

> The more extreme the selected threshold levels, the closer the OB/OS signals will be to actual market turning points, but the greater the number of such points that will be missed. — Schwager

| Threshold Choice | Precision | Recall | Example |
|---|---|---|---|
| **Wider (e.g., 70/30)** | Lower — more false signals | Higher — catches more turning points | RSI 70/30 |
| **Tighter (e.g., 80/20)** | Higher — signals closer to actual turns | Lower — misses some turns entirely | RSI 80/20 |

In ML terms: this is the classic **precision-recall tradeoff**. Wider thresholds maximize recall (don't miss reversals) at the cost of precision (more false positives). Tighter thresholds maximize precision at the cost of recall.

---

## What To Do When OB/OS Is Triggered

Schwager presents a **graduated response spectrum** from most to least aggressive:

### When Overbought Is Triggered (mirror for oversold):

| Response | Aggressiveness | What It Means |
|---|---|---|
| **1. Go short** | Most aggressive | Pure countertrend bet — "I think it reverses here" |
| **2. Liquidate entire long position** | Defensive | "I'm getting out to protect gains" |
| **3. Liquidate part of long position** | Partially defensive | "I'll reduce exposure but keep some upside" |
| **4. Tighten stop order** | Least aggressive | "I'll stay in but protect myself if it turns" |

> The appropriate response depends on whether you've identified the market as **range-bound** (options 1-2 are reasonable) or **trending** (options 3-4 are safer). This maps directly to the four use cases in [[Oscillators]].

---

## Timing the Response — Four Approaches

Even after deciding *what* to do, *when* to do it matters:

### From Most Aggressive to Most Conservative:

**1. When the oscillator first penetrates the extreme level**
- Act immediately on entry into the zone
- Earliest signal, but highest false signal rate
- Risk: oscillator can stay in extreme territory for extended periods in trends

**2. After it penetrates and reverses by a specified amount**
- Wait for the oscillator to pull back from its extreme by X points
- Slightly later entry, fewer false signals
- Risk: what counts as "enough" reversal is subjective

**3. Only after it exits the extreme zone entirely**
- Wait for the oscillator to cross back below OB (or above OS)
- More confirmation, later entry
- Risk: in choppy markets, oscillator may exit and re-enter repeatedly

**4. Only when a price pattern confirms a reversal**
- Wait for the chart itself to show a reversal pattern (e.g., double top, failed breakout)
- Most conservative, fewest false signals, but worst entry price when correct
- **Schwager says this is "probably the most prudent"**

> In trending markets, the oscillator can stay overbought for weeks or months. Approaches 1–3 would have you acting repeatedly while the trend continues. Approach 4 keeps you out until the market **actually confirms** what the oscillator is suggesting.

---

## The Critical Problem: Oscillator Skew in Trends

In trending markets, OB/OS levels become **systematically skewed** in the direction of the trend:

### In an Uptrend:
- Oscillator keeps hitting overbought → generates **repeated false sell signals**
- Oscillator rarely/never hits oversold → **misses useful buy-the-dip signals**
- Result: all the signals you get are wrong; all the signals you need don't appear

### In a Downtrend:
- Oscillator keeps hitting oversold → generates **repeated false buy signals**
- Oscillator rarely/never hits overbought → **misses useful sell-the-rally signals**
- Same problem in reverse

### Schwager's Citicorp Example (Figure 6.8):
> "The oscillator posted repeated and sustained overbought signals without registering a single oversold signal. As a result, the oscillator produced many false sell signals without producing any buy signals, although the latter would have been more useful for traders seeking entry points to the existing trend."

This is the single most important warning in the chapter.

---

## The Solution: Adjusting Levels for Trend Direction

Schwager explicitly recommends **shifting OB/OS thresholds** based on the prevailing trend:

| Market Context | OB Level | OS Level | Logic |
|---|---|---|---|
| **No clear trend (range)** | 70 | 30 | Symmetric — both sides equally useful |
| **Uptrend** | 80 | 40 | Harder to trigger sell signals; easier to trigger buy-the-dip signals |
| **Downtrend** | 60 | 20 | Harder to trigger buy signals; easier to trigger sell-the-rally signals |

**The logic:** In a trend, you want the oscillator to help you trade **with** the trend:
- In an uptrend → oversold (buy-the-dip) signals are useful; overbought signals are noise → raise both levels
- In a downtrend → overbought (sell-the-rally) signals are useful; oversold signals are noise → lower both levels

---

## Effectiveness by Market Context

| | **Range Market** | **Trending Market** |
|---|---|---|
| **Standard OB/OS as trade trigger** | ✅ Works well — extremes snap back | ❌ Disaster — repeated false signals against the trend |
| **Adjusted OB/OS for trend-direction entries** | ⚪ Unnecessary — standard levels suffice | ✅ Useful — helps time entries with the trend |
| **OB/OS as diagnostic (alert only)** | ✅ Useful — flags range boundaries | ✅ Useful — but requires price confirmation before action |

> "While the traditional countertrend approach of selling when the oscillator is overbought and buying when the oscillator is oversold may provide excellent entry points in trading ranges, it is a recipe for disaster in trending markets." — Schwager

---

## The Deeper Lesson

> **Overbought does NOT mean "will go down." Oversold does NOT mean "will go up."**

They mean: "momentum has reached a historically extreme level." What happens next depends entirely on market context:
- **Range:** extremes snap back → OB/OS signals are reliable trade triggers
- **Trend:** extremes are the new normal → OB/OS signals are noise unless adjusted and confirmed

This is why Schwager concludes that OB/OS readings should be used as **"trading alerts"** — hypothesis generators, not trade triggers:
1. The alert says: "conditions are extreme"
2. The confirmation from price action says: "and the market is actually turning"
3. You need **both**

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional


# ── RSI Calculation ────────────────────────────────────────────
def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.
    Normalized oscillator with fixed 0-100 range.
    Default OB/OS levels: 70/30.
    """
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()

    # Use Wilder's smoothing for subsequent values
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1)
                            + gains.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1)
                            + losses.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ── Momentum Oscillator ───────────────────────────────────────
def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """Momentum = Today's close − Close N days ago."""
    return prices - prices.shift(n)


# ── OB/OS Level Detection ─────────────────────────────────────
def detect_ob_os_signals(oscillator: pd.Series,
                          ob_level: float,
                          os_level: float) -> pd.DataFrame:
    """
    Detect overbought and oversold conditions.

    Returns DataFrame with columns:
      - 'zone': 'overbought', 'oversold', or 'neutral'
      - 'entry': True on the bar the oscillator first enters the zone
      - 'exit': True on the bar the oscillator exits the zone
    """
    zone = pd.Series('neutral', index=oscillator.index)
    zone[oscillator >= ob_level] = 'overbought'
    zone[oscillator <= os_level] = 'oversold'

    prev_zone = zone.shift(1).fillna('neutral')

    entry = zone != prev_zone
    exit_signal = (prev_zone != 'neutral') & (zone == 'neutral')

    return pd.DataFrame({
        'zone': zone,
        'entry': entry & (zone != 'neutral'),  # entered OB or OS
        'exit': exit_signal,                     # exited back to neutral
    }, index=oscillator.index)


# ── Adaptive OB/OS for Trend Context ──────────────────────────
def adaptive_ob_os_levels(prices: pd.Series,
                           ma_period: int = 50,
                           base_ob: float = 70,
                           base_os: float = 30,
                           shift_amount: float = 10
                           ) -> pd.DataFrame:
    """
    Adjust OB/OS levels based on trend direction.

    Uses a moving average to determine trend:
      - Uptrend (price > MA):   raise both levels by shift_amount
      - Downtrend (price < MA): lower both levels by shift_amount
      - No trend (near MA):     use base levels

    Schwager's logic:
      - In uptrend: make sell signals harder, buy-the-dip signals easier
      - In downtrend: make buy signals harder, sell-the-rally signals easier

    Returns DataFrame with columns: 'ob_level', 'os_level', 'trend'
    """
    ma = prices.rolling(window=ma_period).mean()

    trend = pd.Series('neutral', index=prices.index)
    trend[prices > ma] = 'uptrend'
    trend[prices < ma] = 'downtrend'

    ob_level = pd.Series(base_ob, index=prices.index)
    os_level = pd.Series(base_os, index=prices.index)

    # Uptrend: raise both → harder to sell, easier to buy dips
    ob_level[trend == 'uptrend'] = base_ob + shift_amount
    os_level[trend == 'uptrend'] = base_os + shift_amount

    # Downtrend: lower both → harder to buy, easier to sell rallies
    ob_level[trend == 'downtrend'] = base_ob - shift_amount
    os_level[trend == 'downtrend'] = base_os - shift_amount

    return pd.DataFrame({
        'ob_level': ob_level,
        'os_level': os_level,
        'trend': trend,
    }, index=prices.index)


# ── OB/OS for Unbounded Oscillators (Percentile Method) ───────
def percentile_ob_os(oscillator: pd.Series,
                      lookback: int = 100,
                      upper_pct: float = 90,
                      lower_pct: float = 10) -> pd.DataFrame:
    """
    Set OB/OS levels for unbounded oscillators using rolling percentiles.

    Schwager's guideline: isolate the highest and lowest ~10% of readings.
    This implementation uses a rolling window so levels adapt to
    changing volatility conditions.

    Returns DataFrame with columns: 'ob_level', 'os_level'
    """
    ob = oscillator.rolling(window=lookback).quantile(upper_pct / 100)
    os = oscillator.rolling(window=lookback).quantile(lower_pct / 100)

    return pd.DataFrame({
        'ob_level': ob,
        'os_level': os,
    }, index=oscillator.index)


# ── Timing Approaches ─────────────────────────────────────────
def timing_approach_signals(oscillator: pd.Series,
                             ob_level: float,
                             os_level: float,
                             reversal_amount: float = 5.0
                             ) -> pd.DataFrame:
    """
    Implement Schwager's four timing approaches for OB/OS signals.

    Returns DataFrame with boolean columns for each approach:
      - 'approach_1': signal on first penetration of extreme zone
      - 'approach_2': signal after penetration + reversal by specified amount
      - 'approach_3': signal on exit from extreme zone
      - 'approach_4': placeholder (requires external price pattern confirmation)

    Note: Approach 4 cannot be fully automated here because it requires
    chart pattern recognition. The column is set to the same as approach_3
    as a baseline — in practice, you'd add your own pattern confirmation
    filter on top.
    """
    signals = detect_ob_os_signals(oscillator, ob_level, os_level)

    # Approach 1: first penetration
    app1_sell = signals['entry'] & (signals['zone'] == 'overbought')
    app1_buy = signals['entry'] & (signals['zone'] == 'oversold')

    # Approach 2: penetration + reversal by specified amount
    # Track peak reading within each OB/OS zone, signal when
    # oscillator pulls back from that peak by reversal_amount
    peak_in_zone = oscillator.copy()
    trough_in_zone = oscillator.copy()
    app2_sell = pd.Series(False, index=oscillator.index)
    app2_buy = pd.Series(False, index=oscillator.index)

    in_ob = False
    in_os = False
    ob_peak = -np.inf
    os_trough = np.inf

    for i in range(1, len(oscillator)):
        val = oscillator.iloc[i]

        # Track overbought zone
        if val >= ob_level:
            in_ob = True
            ob_peak = max(ob_peak, val)
        elif in_ob:
            if ob_peak - val >= reversal_amount:
                app2_sell.iloc[i] = True
            if val < ob_level:
                in_ob = False
                ob_peak = -np.inf

        # Track oversold zone
        if val <= os_level:
            in_os = True
            os_trough = min(os_trough, val)
        elif in_os:
            if val - os_trough >= reversal_amount:
                app2_buy.iloc[i] = True
            if val > os_level:
                in_os = False
                os_trough = np.inf

    # Approach 3: exit from extreme zone
    app3_sell = signals['exit'] & (signals['zone'].shift(1) == 'overbought')
    app3_buy = signals['exit'] & (signals['zone'].shift(1) == 'oversold')

    # Approach 4: price pattern confirmation (placeholder)
    # In practice: combine approach 3 with your own pattern detection
    app4_sell = app3_sell.copy()
    app4_buy = app3_buy.copy()

    return pd.DataFrame({
        'app1_sell': app1_sell, 'app1_buy': app1_buy,
        'app2_sell': app2_sell, 'app2_buy': app2_buy,
        'app3_sell': app3_sell, 'app3_buy': app3_buy,
        'app4_sell': app4_sell, 'app4_buy': app4_buy,
    }, index=oscillator.index)


# ── Visualization ─────────────────────────────────────────────
def plot_ob_os(prices: pd.Series,
               oscillator: pd.Series,
               ob_level: float = 70,
               os_level: float = 30,
               adaptive_levels: Optional[pd.DataFrame] = None,
               title: str = 'OB/OS Analysis'):
    """
    Dual-panel chart:
      Top: Price with background shading for OB/OS zones
      Bottom: Oscillator with OB/OS levels, zone shading, and entry markers

    If adaptive_levels is provided, uses dynamic OB/OS levels
    instead of fixed ones.
    """
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 9), sharex=True,
        gridspec_kw={'height_ratios': [2, 1]}
    )

    # ── Price chart ──
    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title(f'{title} — Price', fontsize=12)
    ax1.set_ylabel('Price')
    ax1.grid(True, alpha=0.3)

    # ── Oscillator chart ──
    ax2.plot(oscillator.index, oscillator.values,
             color='#1a73e8', linewidth=1.0, label='Oscillator')

    if adaptive_levels is not None:
        # Dynamic OB/OS levels
        ax2.plot(adaptive_levels.index, adaptive_levels['ob_level'],
                 color='red', linewidth=0.8, linestyle='--',
                 label='OB Level (adaptive)')
        ax2.plot(adaptive_levels.index, adaptive_levels['os_level'],
                 color='green', linewidth=0.8, linestyle='--',
                 label='OS Level (adaptive)')
        ax2.fill_between(oscillator.index,
                         adaptive_levels['ob_level'], 100,
                         color='red', alpha=0.08)
        ax2.fill_between(oscillator.index,
                         0, adaptive_levels['os_level'],
                         color='green', alpha=0.08)
    else:
        # Fixed OB/OS levels
        ax2.axhline(y=ob_level, color='red', linewidth=0.8,
                     linestyle='--', label=f'Overbought ({ob_level})')
        ax2.axhline(y=os_level, color='green', linewidth=0.8,
                     linestyle='--', label=f'Oversold ({os_level})')
        ax2.fill_between(oscillator.index,
                         ob_level, 100,
                         where=(oscillator >= ob_level),
                         color='red', alpha=0.2)
        ax2.fill_between(oscillator.index,
                         0, os_level,
                         where=(oscillator <= os_level),
                         color='green', alpha=0.2)

    # Midline
    ax2.axhline(y=50, color='gray', linewidth=0.5, linestyle=':')

    # Mark entry points into OB/OS zones
    signals = detect_ob_os_signals(oscillator, ob_level, os_level)
    ob_entries = signals['entry'] & (signals['zone'] == 'overbought')
    os_entries = signals['entry'] & (signals['zone'] == 'oversold')

    if ob_entries.any():
        ax2.scatter(oscillator.index[ob_entries],
                    oscillator.values[ob_entries],
                    color='red', marker='v', s=60, zorder=5,
                    label='Entered OB')
    if os_entries.any():
        ax2.scatter(oscillator.index[os_entries],
                    oscillator.values[os_entries],
                    color='green', marker='^', s=60, zorder=5,
                    label='Entered OS')

    # Shade price chart background during OB/OS periods
    for i in range(len(signals)):
        if signals['zone'].iloc[i] == 'overbought':
            ax1.axvspan(prices.index[i],
                        prices.index[min(i + 1, len(prices) - 1)],
                        color='red', alpha=0.04)
        elif signals['zone'].iloc[i] == 'oversold':
            ax1.axvspan(prices.index[i],
                        prices.index[min(i + 1, len(prices) - 1)],
                        color='green', alpha=0.04)

    ax2.set_title(f'{title} — Oscillator', fontsize=12)
    ax2.set_ylabel('Oscillator Value')
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    np.random.seed(42)
    n_days = 250

    # ── Scenario 1: Range-bound market (OB/OS works well) ──
    range_noise = np.random.normal(0, 1.5, n_days)
    range_cycle = 5 * np.sin(np.linspace(0, 8 * np.pi, n_days))
    range_prices = pd.Series(
        100 + range_cycle + range_noise,
        index=pd.date_range('2024-01-01', periods=n_days, freq='B'),
        name='Close'
    )

    rsi_range = compute_rsi(range_prices, period=14)
    print("=== Range Market: RSI OB/OS Signals ===")
    signals_range = detect_ob_os_signals(rsi_range, 70, 30)
    ob_count = (signals_range['entry'] & (signals_range['zone'] == 'overbought')).sum()
    os_count = (signals_range['entry'] & (signals_range['zone'] == 'oversold')).sum()
    print(f"Overbought entries: {ob_count}")
    print(f"Oversold entries:   {os_count}")
    print(f"Ratio (OB/OS):      {ob_count/max(os_count,1):.1f}")
    print("(In a range, OB and OS signals should be roughly balanced)\n")

    plot_ob_os(range_prices, rsi_range, title='Range Market — RSI OB/OS')

    # ── Scenario 2: Trending market (OB/OS fails) ──
    trend_up = np.linspace(0, 40, n_days)
    trend_noise = np.random.normal(0, 1.5, n_days)
    trend_prices = pd.Series(
        100 + trend_up + trend_noise,
        index=pd.date_range('2024-01-01', periods=n_days, freq='B'),
        name='Close'
    )

    rsi_trend = compute_rsi(trend_prices, period=14)
    print("=== Trending Market: RSI OB/OS Signals (Fixed Levels) ===")
    signals_trend = detect_ob_os_signals(rsi_trend, 70, 30)
    ob_count_t = (signals_trend['entry'] & (signals_trend['zone'] == 'overbought')).sum()
    os_count_t = (signals_trend['entry'] & (signals_trend['zone'] == 'oversold')).sum()
    print(f"Overbought entries: {ob_count_t}")
    print(f"Oversold entries:   {os_count_t}")
    print(f"Skew: {ob_count_t} sell signals vs {os_count_t} buy signals")
    print("(Demonstrates oscillator skew — many false sells, no useful buys)\n")

    plot_ob_os(trend_prices, rsi_trend, title='Trending Market — Fixed OB/OS (Skew Problem)')

    # ── Scenario 3: Adaptive levels fix the skew ──
    adaptive = adaptive_ob_os_levels(trend_prices, ma_period=50,
                                      base_ob=70, base_os=30,
                                      shift_amount=10)
    print("=== Trending Market: RSI OB/OS Signals (Adaptive Levels) ===")
    print(f"Uptrend levels: OB={adaptive['ob_level'].mode().iloc[0]}, "
          f"OS={adaptive['os_level'].mode().iloc[0]}")
    print("(Raised levels → fewer false sell signals, more useful buy-dip signals)\n")

    plot_ob_os(trend_prices, rsi_trend,
               adaptive_levels=adaptive,
               title='Trending Market — Adaptive OB/OS (Schwager Fix)')

    # ── Scenario 4: Unbounded oscillator with percentile-based levels ──
    mom = compute_momentum(trend_prices, n=10)
    pct_levels = percentile_ob_os(mom, lookback=100,
                                   upper_pct=90, lower_pct=10)
    print("=== Unbounded Oscillator: Percentile-Based OB/OS ===")
    print(f"Current OB level: {pct_levels['ob_level'].iloc[-1]:.2f}")
    print(f"Current OS level: {pct_levels['os_level'].iloc[-1]:.2f}")
    print("(Levels adapt to changing volatility conditions)\n")

    # ── Scenario 5: Compare four timing approaches ──
    timing = timing_approach_signals(rsi_range, ob_level=70, os_level=30,
                                      reversal_amount=5)
    print("=== Four Timing Approaches (Range Market) ===")
    for app in range(1, 4):
        sell_count = timing[f'app{app}_sell'].sum()
        buy_count = timing[f'app{app}_buy'].sum()
        print(f"Approach {app}: {sell_count} sell signals, {buy_count} buy signals")
    print("(Approach 1 = most signals, Approach 3 = fewest but higher quality)")
    print("(Approach 4 = same as 3 + manual price pattern confirmation)")
```

### What Each Function Does

| Function | Purpose | Key Concept |
|---|---|---|
| `compute_rsi()` | RSI with Wilder's smoothing | Normalized oscillator, fixed 0–100 range |
| `compute_momentum()` | Simple momentum | Unbounded oscillator, equilibrium at 0 |
| `detect_ob_os_signals()` | Flag OB/OS zone entries and exits | Core signal detection for any oscillator |
| `adaptive_ob_os_levels()` | Shift OB/OS levels based on trend direction | **Schwager's solution to oscillator skew** |
| `percentile_ob_os()` | Rolling percentile levels for unbounded oscillators | Schwager's "isolate top/bottom 10%" guideline |
| `timing_approach_signals()` | Implement all four timing methods | Compares aggressive vs. conservative timing |
| `plot_ob_os()` | Dual-panel visualization with zone shading | Visual mapping of OB/OS onto price action |

### Key Implementation Notes

1. **`adaptive_ob_os_levels()`** is the most important function conceptually — it implements Schwager's explicit recommendation to shift levels with the trend. It uses a simple MA to determine trend direction, then raises both levels in uptrends and lowers both in downtrends. The `shift_amount` parameter controls how much adjustment to apply.

2. **`percentile_ob_os()`** uses a rolling window, so the OB/OS levels **adapt to changing market volatility**. This addresses Schwager's concern that "levels set today may not be appropriate a month from now." Fixed percentile thresholds, rolling application.

3. **`timing_approach_signals()`** implements approaches 1–3 mechanically. Approach 4 (price pattern confirmation) is left as a placeholder because it requires chart pattern recognition that can't be fully automated in a simple function — in practice, you'd layer your own confirmation logic on top of approach 3.

4. **The example scenarios demonstrate the skew problem directly:** run the range-market scenario and you'll see balanced OB/OS signals. Run the trending-market scenario with fixed levels and you'll see the skew Schwager describes. Run it again with adaptive levels and watch the skew correct.

---

## Connection to Broader Framework

### Link to [[Oscillators]] — The Four Use Cases
OB/OS levels are the primary mechanism through which oscillators generate countertrend signals. Their effectiveness maps directly to the four-use-case framework:
- **Use Case 1 (range, trade trigger):** OB/OS signals work well ✅
- **Use Case 2 (trend, trade trigger):** OB/OS signals fail badly ❌
- **Use Case 3 (trend, diagnostic):** OB/OS as alert, not trigger ✅
- **Use Case 4 (trend, entry timing):** Adjusted OB/OS for dip-buying ✅

### Link to [[Equilibrium Line]]
- Equilibrium line = which side of neutral (direction)
- OB/OS levels = how far from neutral (extremity)
- Together they form the complete oscillator reading system

### Link to [[Divergence]]
Divergence is the *other* major countertrend signal besides OB/OS. They can reinforce each other: an overbought reading combined with a bearish divergence is a stronger alert than either alone. But both still require price confirmation.

### Link to [[Failed Signals]] (Chapter 11)
An OB/OS signal that doesn't produce a reversal is itself a type of failed signal — and per Schwager's framework, a failed signal suggests strength in the opposite direction. If the market stays overbought without reversing, that persistence is evidence of trend strength, not a reason to keep fighting it.

### Link to Decision Support Framework
OB/OS readings answer: "Is this move at a historically extreme pace?"
They do NOT answer: "Will this move reverse?"
The first is a **fact about momentum**. The second is a **prediction about future price**. Schwager's entire framework is built on using the first to inform decisions, while never confusing it for the second.
