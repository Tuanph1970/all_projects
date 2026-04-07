# RSI (Relative Strength Index)
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 110–111, 117–119), Chapter 10 (pp. 148–149), Appendix (pp. 316–317)
**Tags:** #technical-analysis #RSI #oscillators #momentum #schwager #normalized #overbought #oversold #divergence #indicators
**Related:** [[Oscillators]] · [[Momentum]] · [[Unbounded vs Normalized Oscillators]] · [[Overbought and Oversold]] · [[Divergence]] · [[Stochastics]] · [[MACD]] · [[Oscillator Sensitivity]]

---

## Definition

RSI is a **normalized momentum oscillator** that measures the balance of up-close pressure vs. down-close pressure over a lookback period, scaled to a fixed 0–100 range.

Developed by **Welles Wilder Jr.** in his 1978 book *New Concepts in Technical Trading Systems*.

```
RSI = 100 − (100 / (1 + RS))

RS = Average Gain over N periods / Average Loss over N periods
     (default N = 14)
```

> "Relative strength (RS) is the key calculation in the formula. The rest of the math simply normalizes the scale of the RSI to a constant range of zero to 100." — Schwager

---

## Simple Analogy: Win-Loss Record

Think of RSI as a sports team's **adjusted win-loss record** over the last 14 games:

- It doesn't just count wins and losses (that would be a simple ratio)
- It weights them by **margin of victory** — winning by 10 gets more credit than winning by 1
- The result is scaled to 0–100 so you can compare any team regardless of league

| RSI Reading | Win-Loss Analogy | Market Meaning |
|---|---|---|
| **100** | Won every game by huge margins | All closes up — 100% bullish (unsustainable) |
| **70** | Winning decisively, dominant streak | Up-pressure significantly dominates. Overbought territory. |
| **50** | Even record, no clear edge | Up and down pressure balanced. Neutral. |
| **30** | Losing badly, on a slide | Down-pressure significantly dominates. Oversold territory. |
| **0** | Lost every game by huge margins | All closes down — 100% bearish (unsustainable) |

The reading changes daily as new "games" (closes) enter the window and old ones drop out.

---

## Formula Walkthrough (Developer Perspective)

### Step 1: Classify each day
```python
delta = close_today - close_yesterday
if delta > 0:
    gain = delta      # "up day"
    loss = 0
else:
    gain = 0
    loss = abs(delta)  # "down day"
```

### Step 2: Average gains and losses over N days
```python
avg_gain = sum(gains_over_N_days) / N    # divide by N, not by count of up days
avg_loss = sum(losses_over_N_days) / N   # zeros included in the average
```
> Important: dividing by N (total days), not by the count of up or down days. Days with zero contribution still count. This is what makes "14 up days out of 14" produce RSI = 100, not just RSI = "high."

### Step 3: Calculate RS (Relative Strength)
```python
RS = avg_gain / avg_loss
```
RS = 2.0 means gains have been twice as large as losses. RS = 0.5 means losses have been twice as large as gains.

### Step 4: Normalize to 0–100
```python
RSI = 100 - (100 / (1 + RS))
```

| RS Value | RSI Value | Meaning |
|---|---|---|
| ∞ (no losses) | 100 | Pure buying pressure |
| 2.0 | 66.7 | Gains 2x losses |
| 1.0 | 50.0 | Gains = losses (balanced) |
| 0.5 | 33.3 | Losses 2x gains |
| 0 (no gains) | 0 | Pure selling pressure |

The normalization formula is a **sigmoid-like compression** — it maps the 0-to-infinity RS ratio into a bounded 0–100 scale. It's the same kind of transformation you'd see in logistic regression.

---

## Wilder's Smoothing (Subsequent Calculations)

After the initial N-period average, Wilder uses exponential-style smoothing:

```python
new_avg_gain = (prev_avg_gain * (N - 1) + current_gain) / N
new_avg_loss = (prev_avg_loss * (N - 1) + current_loss) / N
```

This means:
- Older data has diminishing but **non-zero** influence
- RSI has a longer "memory" than a pure rolling window
- The indicator is smoother than a recalculated-from-scratch version
- Equivalent to an EMA with smoothing constant `1/N`

---

## Properties

| Property | Value |
|---|---|
| **Type** | Normalized (bounded) oscillator |
| **Range** | 0 to 100 |
| **Equilibrium** | 50 (balanced up/down pressure) |
| **Default period** | 14 days (Wilder's recommendation) |
| **OB/OS levels** | 70 / 30 (standard), adjustable |
| **Smoothing** | Wilder's exponential smoothing |
| **Inventor** | Welles Wilder Jr. (1978) |

---

## Standard OB/OS Levels and the Trend Adjustment

### Standard Levels
| Level | RSI Value | Meaning |
|---|---|---|
| **Overbought** | 70 | Up-pressure has been dominant — potentially overextended |
| **Neutral** | 50 | Balanced |
| **Oversold** | 30 | Down-pressure has been dominant — potentially overextended |

Alternative conventions: 75/25 or 80/20 (more extreme thresholds, fewer but higher-quality signals).

### Trend Adjustment (from [[Overbought and Oversold]])

| Market Context | OB Level | OS Level | Logic |
|---|---|---|---|
| **Range** | 70 | 30 | Symmetric — both signals equally useful |
| **Uptrend** | 80 | 40 | Harder to trigger sell; easier to trigger buy-the-dip |
| **Downtrend** | 60 | 20 | Harder to trigger buy; easier to trigger sell-the-rally |

> "This is not required, and would even be inappropriate in strongly trending markets." — Schwager

---

## RSI in Schwager's Examples

### Soybean Oil — Range Market (Figure 10.6, Chapter 10)
RSI OB/OS signals provide "reasonably good position liquidation signals" because the market stays in a trading range. OB signals near range tops, OS signals near range bottoms — the classic use case where RSI excels.

### Citicorp — Trending Market (Figure 6.8, Chapter 6)
10-day RSI "posted repeated and sustained overbought signals without registering a single oversold signal." Many false sell signals, zero buy signals. The definitive illustration of why RSI (and all oscillators) require trend context and price confirmation.

### 3Com Corp (Figures 6.1–6.7, Chapter 6)
RSI shown alongside multiple other oscillators on the same price data. Schwager's point: despite different formulas, "the fundamental information they convey is identical." RSI divergence between February and April 1997 lows is visible in nearly all the oscillators.

---

## Strengths and Limitations

### Strengths ✅
| Strength | Why It Matters |
|---|---|
| **Portability** | RSI 75 means the same on a $5 stock and a $500 stock. Universal screening rules work. |
| **Stable OB/OS levels** | 70/30 stays meaningful regardless of price level or volatility changes |
| **Divergence detection** | Most commonly used oscillator for price-vs-momentum divergence |
| **Intuitive reading** | "The balance of up vs. down pressure" is easy to grasp conceptually |
| **Cross-instrument comparability** | Can rank a universe of stocks by RSI and the ranking is meaningful |

### Limitations ❌
| Limitation | Why It Matters |
|---|---|
| **Trend skew** | Same problem as all oscillators — sustained overbought in uptrends, sustained oversold in downtrends |
| **Loss of magnitude** | A stock rising $0.10/day and one rising $10/day can produce similar RSI readings |
| **Period sensitivity** | 5-day RSI hits 70/30 frequently; 21-day RSI barely reaches those levels. Period choice fundamentally affects signal rate. |
| **Not a trend tool** | RSI is designed for countertrend (OB/OS) and diagnostic (divergence) use, not trend identification |

---

## RSI vs. Other Oscillators

| Property | RSI | Stochastics | MACD | Momentum |
|---|---|---|---|---|
| **Range** | 0–100 | 0–100 | Unbounded | Unbounded |
| **What it measures** | Gain/loss balance | Close position in N-day range | EMA gap | Raw price change |
| **OB/OS levels** | 70/30 | 80/20 | Empirical | Empirical |
| **Best for** | OB/OS in ranges, divergence | OB/OS in ranges, crossover | Trend crossovers | Raw speed, diagnostics |
| **Smoothing** | Wilder's EMA | 3-day MA (slow version) | 9-day signal line | None |

> Despite these differences: "the fundamental information they convey is identical." — Schwager

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI with Wilder's smoothing.

    Step 1: Calculate daily changes (gains and losses)
    Step 2: Initial average = simple mean over first N days
    Step 3: Subsequent averages use Wilder's smoothing:
            new_avg = (prev_avg * (N-1) + current_value) / N

    Parameters:
      prices: closing price series
      period: lookback period (default 14, Wilder's recommendation)

    Returns:
      Series of RSI values (0 to 100)
    """
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    # Initial averages (simple mean)
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()

    # Wilder's smoothing for subsequent values
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1)
                            + gains.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1)
                            + losses.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_rsi_simple(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI without Wilder's smoothing — pure rolling window.
    Included for comparison to show the smoothing effect.
    """
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi_decomposition(prices: pd.Series, period: int = 14):
    """
    Show the internal components of RSI at each step:
    gains/losses → averages → RS → RSI.
    Helps demystify the formula.
    """
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1]*(period-1) + gains.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1]*(period-1) + losses.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    print(f"=== RSI Decomposition ({period}-day, last 5 bars) ===")
    print(pd.DataFrame({
        'Close': prices.round(2),
        'Change': delta.round(2),
        'Gain': gains.round(2),
        'Loss': losses.round(2),
        'Avg Gain': avg_gain.round(4),
        'Avg Loss': avg_loss.round(4),
        'RS': rs.round(4),
        'RSI': rsi.round(1),
    }).tail(5).to_string())


def wilder_vs_simple_comparison(prices: pd.Series, period: int = 14):
    """
    Compare RSI with Wilder's smoothing vs. simple rolling window.
    Shows the smoothing effect.
    """
    rsi_wilder = compute_rsi(prices, period)
    rsi_simple = compute_rsi_simple(prices, period)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                    gridspec_kw={'height_ratios': [1.5, 1]})

    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    ax2.plot(rsi_wilder.index, rsi_wilder.values, color='#534AB7',
             linewidth=1.0, label="RSI (Wilder's smoothing)")
    ax2.plot(rsi_simple.index, rsi_simple.values, color='#E24B4A',
             linewidth=0.8, alpha=0.6, label='RSI (simple rolling)')
    ax2.axhline(y=70, color='red', linewidth=0.7, linestyle=':')
    ax2.axhline(y=30, color='green', linewidth=0.7, linestyle=':')
    ax2.axhline(y=50, color='black', linewidth=0.5, linestyle='--')
    ax2.set_ylim(0, 100)
    ax2.set_title(f'{period}-day RSI: Wilder vs Simple', fontsize=12)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    # Count OB/OS triggers
    wilder_ob = (rsi_wilder >= 70).sum()
    simple_ob = (rsi_simple >= 70).sum()
    print(f"Wilder RSI bars above 70: {wilder_ob}")
    print(f"Simple RSI bars above 70: {simple_ob}")
    print(f"Wilder's smoothing produces {'fewer' if wilder_ob < simple_ob else 'more'} "
          f"OB readings (smoother)")


def rsi_period_sensitivity(prices: pd.Series,
                            periods: list = [5, 9, 14, 21]):
    """
    Compare RSI at different periods to show the sensitivity tradeoff.
    Shorter period = more volatile, reaches OB/OS more often.
    """
    n = len(periods)
    fig, axes = plt.subplots(n + 1, 1, figsize=(14, 3 * (n + 1)), sharex=True,
                              gridspec_kw={'height_ratios': [2] + [1] * n})

    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].grid(True, alpha=0.3)

    colors = ['#E24B4A', '#EF9F27', '#534AB7', '#1D9E75']
    for i, period in enumerate(periods):
        rsi = compute_rsi(prices, period)
        ax = axes[i + 1]
        ax.plot(rsi.index, rsi.values, color=colors[i % len(colors)],
                linewidth=0.9)
        ax.axhline(y=70, color='red', linewidth=0.5, linestyle=':')
        ax.axhline(y=30, color='green', linewidth=0.5, linestyle=':')
        ax.axhline(y=50, color='black', linewidth=0.4, linestyle='--')
        ax.set_ylim(0, 100)

        ob_count = (rsi >= 70).sum()
        os_count = (rsi <= 30).sum()
        ax.set_title(f'{period}-day RSI  |  OB bars: {ob_count}  |  '
                     f'OS bars: {os_count}', fontsize=11)
        ax.grid(True, alpha=0.3)

    plt.suptitle('RSI period sensitivity: shorter = more volatile, '
                 'more OB/OS triggers', fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


def rsi_range_vs_trend(n_days: int = 200):
    """
    Side-by-side demonstration: RSI works well in ranges,
    fails in trends (Schwager's key examples).
    """
    np.random.seed(42)

    # Range market
    range_noise = np.random.normal(0, 1.5, n_days)
    range_cycle = 5 * np.sin(np.linspace(0, 6 * np.pi, n_days))
    range_prices = pd.Series(100 + range_cycle + range_noise)

    # Trending market
    trend_noise = np.random.normal(0, 1.0, n_days)
    trend_line = np.linspace(0, 40, n_days)
    trend_prices = pd.Series(100 + trend_line + trend_noise)

    rsi_range = compute_rsi(range_prices, 14)
    rsi_trend = compute_rsi(trend_prices, 14)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Range market
    axes[0, 0].plot(range_prices.values, color='#333333', linewidth=1)
    axes[0, 0].set_title('Range market: price', fontsize=11)
    axes[0, 0].grid(True, alpha=0.3)

    axes[1, 0].plot(rsi_range.values, color='#534AB7', linewidth=0.9)
    axes[1, 0].axhline(y=70, color='red', linewidth=0.7, linestyle=':')
    axes[1, 0].axhline(y=30, color='green', linewidth=0.7, linestyle=':')
    axes[1, 0].set_ylim(0, 100)
    ob_r = (rsi_range >= 70).sum()
    os_r = (rsi_range <= 30).sum()
    axes[1, 0].set_title(f'RSI: OB={ob_r}, OS={os_r} '
                          f'(ratio: {ob_r/max(os_r,1):.1f})', fontsize=11)
    axes[1, 0].grid(True, alpha=0.3)

    # Trending market
    axes[0, 1].plot(trend_prices.values, color='#333333', linewidth=1)
    axes[0, 1].set_title('Trending market: price', fontsize=11)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 1].plot(rsi_trend.values, color='#534AB7', linewidth=0.9)
    axes[1, 1].axhline(y=70, color='red', linewidth=0.7, linestyle=':')
    axes[1, 1].axhline(y=30, color='green', linewidth=0.7, linestyle=':')
    axes[1, 1].set_ylim(0, 100)
    ob_t = (rsi_trend >= 70).sum()
    os_t = (rsi_trend <= 30).sum()
    axes[1, 1].set_title(f'RSI: OB={ob_t}, OS={os_t} '
                          f'(skew: {ob_t}:{os_t})', fontsize=11)
    axes[1, 1].grid(True, alpha=0.3)

    plt.suptitle('RSI: works in ranges (balanced signals), '
                 'fails in trends (skewed signals)',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()

    print(f"Range market — OB/OS ratio: {ob_r/max(os_r,1):.1f} "
          f"(near 1.0 = balanced)")
    print(f"Trend market — OB/OS ratio: {ob_t/max(os_t,1):.1f} "
          f"(>>1.0 = skewed, many false sell signals)")


def plot_rsi_full(prices: pd.Series, period: int = 14,
                   ob: float = 70, os: float = 30):
    """
    Complete RSI visualization with OB/OS zones, midline, and zone shading.
    """
    rsi = compute_rsi(prices, period)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})

    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # RSI
    ax2.plot(rsi.index, rsi.values, color='#534AB7', linewidth=1.0)
    ax2.axhline(y=ob, color='red', linewidth=0.8, linestyle='--',
                 label=f'Overbought ({ob})')
    ax2.axhline(y=os, color='green', linewidth=0.8, linestyle='--',
                 label=f'Oversold ({os})')
    ax2.axhline(y=50, color='gray', linewidth=0.5, linestyle=':')
    ax2.fill_between(rsi.index, ob, 100,
                     where=(rsi >= ob), color='red', alpha=0.15)
    ax2.fill_between(rsi.index, 0, os,
                     where=(rsi <= os), color='green', alpha=0.15)
    ax2.set_ylim(0, 100)
    ax2.set_title(f'{period}-day RSI', fontsize=12)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

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

    # ── Full RSI visualization ──
    plot_rsi_full(prices)

    # ── Formula decomposition ──
    print()
    rsi_decomposition(prices)

    # ── Wilder vs simple comparison ──
    print()
    wilder_vs_simple_comparison(prices)

    # ── Period sensitivity ──
    print()
    rsi_period_sensitivity(prices, periods=[5, 9, 14, 21])

    # ── Range vs trend demonstration ──
    print()
    rsi_range_vs_trend()
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_rsi()` | Full RSI with Wilder's smoothing | The standard implementation — matches charting software |
| `compute_rsi_simple()` | RSI with pure rolling window (no Wilder smoothing) | For comparison — shows the smoothing effect |
| `rsi_decomposition()` | Prints every step: change → gain/loss → avg → RS → RSI | Demystifies the formula for developers |
| `wilder_vs_simple_comparison()` | Visual: Wilder RSI vs. simple RSI | Wilder's version is smoother, fewer false OB/OS triggers |
| `rsi_period_sensitivity()` | 5/9/14/21-day RSI side by side | Shorter period = more volatile, reaches OB/OS far more often |
| `rsi_range_vs_trend()` | Same RSI in range vs. trend market | Balanced OB/OS in range; heavily skewed in trend |
| `plot_rsi_full()` | Clean dual-panel price + RSI with zone shading | The standard chart layout |

### Key Implementation Notes

1. **`compute_rsi()`** implements Wilder's smoothing exactly: initial average is a simple mean over the first N bars, then each subsequent bar uses `(prev * (N-1) + current) / N`. This matches what professional charting software produces. The `compute_rsi_simple()` variant uses a pure rolling window — run both side by side to see how Wilder's smoothing produces a smoother, less reactive RSI.

2. **`rsi_decomposition()`** is designed for learning. It prints every internal variable at each step, so you can trace a specific RSI reading back to its component gains/losses. This is the "show your work" function — essential for building trust that the formula does what you think it does.

3. **`rsi_range_vs_trend()`** is the visual proof of the range-vs-trend problem. In the range market, OB and OS signal counts are roughly balanced. In the trend market, OB signals vastly outnumber OS signals (or vice versa). The ratio between them quantifies the skew.

4. **`rsi_period_sensitivity()`** shows that a 5-day RSI might spend 40% of its time in OB/OS zones, while a 21-day RSI might only reach those zones 5% of the time. Same market, same thresholds — the period choice fundamentally changes the signal rate. This is the [[Oscillator Sensitivity]] tradeoff in concrete numbers.

---

## Connection to Broader Framework

### Link to [[Unbounded vs Normalized Oscillators]]
RSI is the primary example of a normalized oscillator. Its 0–100 range and standard 70/30 levels are the key practical advantage over unbounded oscillators like Momentum and MACD. The tradeoff: RSI loses raw magnitude information.

### Link to [[Overbought and Oversold]]
RSI is the oscillator most commonly used for OB/OS analysis. The standard 70/30 levels, the trend adjustment (80/40 in uptrends, 60/20 in downtrends), the four timing approaches, and the "trading alert" framework from that note all apply directly to RSI.

### Link to [[Divergence]]
RSI is Schwager's primary tool for demonstrating divergence. The 3Com and Citicorp examples both use RSI to show bearish divergence (price higher high, RSI lower high). RSI's normalization makes divergences visually clearer — you're comparing peaks on the same 0–100 scale.

### Link to [[Stochastics]]
RSI and stochastics are both normalized to 0–100 but measure different things: RSI measures the gain/loss balance (close-to-close changes), while stochastics measures the close's position within the N-day high/low range. They often give similar signals but can diverge — and when they disagree, it's informative.

### Link to [[MACD]] — Complementary Use
RSI (normalized, countertrend) and MACD (unbounded, trend-following) are **complementary**:
- RSI excels in ranges (OB/OS mean-reversion)
- MACD excels in trends (crossover signals)
- Using one from each family provides broader market coverage
- They succeed where the other fails

### Link to [[Oscillator Sensitivity]]
RSI's 14-day default is Wilder's recommendation — not a universal constant. Changing the period dramatically affects signal rate (5-day RSI triggers OB/OS constantly; 21-day RSI barely reaches those levels). The period should match your trading timeframe, following the same principles from the Oscillator Sensitivity note.
