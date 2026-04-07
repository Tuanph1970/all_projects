# Oscillator Sensitivity
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 112–113), Chapter 14 (pp. 229–230)
**Tags:** #technical-analysis #oscillator-sensitivity #N-parameter #lookback #schwager #tradeoff #indicators
**Related:** [[Oscillators]] · [[Momentum Indicator]] · [[Rate of Change (ROC)]] · [[RSI]] · [[Stochastics]] · [[MACD]] · [[Moving Averages]] · [[Overbought and Oversold]]

---

## Definition

Oscillator sensitivity is controlled by the **lookback period (N)** — the number of days the oscillator looks back to compute its value. This single parameter determines how quickly the oscillator reacts, how much noise it contains, and what size of price move it's calibrated to detect.

> "As with moving averages, the number of days used in an oscillator calculation determines how sensitive the indicator will be." — Schwager

---

## Simple Analogy: Microscope Zoom Levels

Think of the N parameter as the **zoom level on a microscope**.

| Zoom Level | N Value | What You See | Tradeoff |
|---|---|---|---|
| **High magnification** | Short (5 days) | Every cell, every tiny movement. Incredible detail. | Lose context — can't tell signal from noise. Overreact to every twitch. |
| **Medium magnification** | Mid (10-14 days) | Medium-scale patterns. Significant enough to trade, timely enough to act. | Compromise — miss some small moves, catch most big ones. |
| **Low magnification** | Long (20-40 days) | Big structures, major movements. | Miss fine detail, but not distracted by noise. When you see movement, it matters. |

> There's no "correct" zoom level. It depends on **what you're trying to see** — which means it depends on your trading timeframe.

---

## The Core Tradeoff: Signal vs. Noise

This is fundamentally a **signal-to-noise ratio** problem:

```
Short N → More signals + More noise  → Earlier entry, more false signals
Long N  → Fewer signals + Less noise → Later entry, fewer false signals
```

There is **no free lunch**. You cannot simultaneously have early signals and low false signal rates. Every oscillator parameter choice is a position on this spectrum.

### Schwager's 5-Day vs. 20-Day Comparison (Figure 6.3)

| Property | 5-Day Momentum | 20-Day Momentum |
|---|---|---|
| **Tracks** | Short-term fluctuations | Major turning points |
| **Signal frequency** | High — catches every minor swing | Low — only signals on significant moves |
| **Noise level** | High — many signals don't lead to tradeable reversals | Low — signals tend to correspond to real moves |
| **Lag** | Minimal — reacts almost immediately | Significant — signals arrive after move is underway |
| **Reversal size signaled** | Small — 1-3 day corrections | Large — weeks/months reversals |

---

## The Proportionality Rule

> "The reversal portended by a 5-day oscillator will generally be proportionally smaller to that portended by a 20-day oscillator." — Schwager

This is often overlooked: N doesn't just control *how many* signals you get — it controls **what size of reversal** those signals correspond to.

- **5-day momentum peak** → signals a minor pullback (days)
- **10-day momentum peak** → signals a moderate correction (1-2 weeks)
- **20-day momentum peak** → signals a potential trend reversal (weeks to months)

They're not catching the same fish with different nets — they're **fishing in different waters**. A short-period oscillator and a long-period oscillator are measuring fundamentally different market phenomena.

---

## How N Maps Across All Oscillator Types

The tradeoff is universal — every oscillator has this same tension:

| Oscillator | What N Controls | Short N Effect | Long N Effect |
|---|---|---|---|
| **Momentum** | Days ago to compare | Catches minor swings, noisy | Catches major turns, laggy |
| **ROC** | Same as Momentum | Same | Same |
| **RSI** | Averaging period (up/down closes) | Volatile RSI, frequent OB/OS | Smooth RSI, rare but reliable OB/OS |
| **Stochastics** | %K range period | Rapid oscillation (fast stochastics) | Smoother oscillation |
| **MA-based oscillator** | Moving average length | Tight tracking, many crossovers | Loose tracking, few crossovers |
| **Price oscillator** | Short and long MA lengths | Responsive to minor trend shifts | Only responds to major trend changes |
| **MACD** | EMA lengths (12/26 default) | Not typically varied — Appel chose specific defaults | — |

---

## Matching N to Trading Timeframe

| Trader Type | Holding Period | Recommended N Range | Logic |
|---|---|---|---|
| **Day trader** | Hours | 5-7 (daily) or sub-daily bars | Need fast signals; accept noise; can cut losses quickly |
| **Swing trader** | Days to weeks | 10-14 | Classic defaults (RSI 14, MACD 12/26) designed for this timeframe |
| **Position trader** | Weeks to months | 20-40 (or weekly data) | Filter everything except major trend changes; accept late signals |

> **The N parameter should match the size of the moves you're trying to trade**, not just your personal patience level. A day trader using 40-day RSI will miss every intraday opportunity. A position trader using 5-day momentum will drown in noise.

---

## The Smoothing Alternative

Instead of increasing N (which adds lag), some oscillators add **smoothing layers** to reduce noise while keeping a shorter lookback:

| Oscillator | Raw (Noisy) Version | Smoothed Version | Smoothing Method |
|---|---|---|---|
| **Stochastics** | Fast stochastics (%K, %D, typically 5-day) | Slow stochastics (smoothed %K, smoothed %D) | Extra 3-day MA applied to each line |
| **MACD** | Raw MACD line (12-EMA − 26-EMA) | MACD with signal line | 9-day MA of MACD line |

**The tradeoff shifts but doesn't disappear:** smoothing reduces noise but adds its own lag. It's a partial escape from the sensitivity tradeoff, not a full one. You're trading noise for latency in a different ratio than N alone would give you.

---

## The Parallel to Moving Average Length (Chapter 3)

The sensitivity tradeoff for oscillators is **identical** to the moving average length tradeoff from Chapter 3:

| Moving Averages (Ch. 3) | Oscillators (Ch. 6) |
|---|---|
| Short MA (5-day): responsive, many false crossovers | Short N: sensitive, many false signals |
| Long MA (40-day): smooth, few false crossovers, late | Long N: smooth, few false signals, late |
| No "correct" MA length | No "correct" N value |
| Depends on market context and trading style | Depends on market context and trading style |

This is not a coincidence — it's the same math. The direction of an N-day MA is equivalent to the sign of N-day Momentum (proven in [[Momentum Indicator]]). Changing N in the oscillator and changing the MA length are the same operation viewed from different angles.

---

## The Overfitting Warning

Endlessly optimizing N to fit historical data is a form of **overfitting** — Schwager's term from Chapter 15. The N that worked best on the last 12 months may not work at all on the next 12 months because:

1. Market volatility changes → the optimal sensitivity changes
2. Trending vs. ranging periods shift → what signals matter changes
3. A perfectly-fitted N captures past noise as if it were signal

> The goal is to choose an N that makes **conceptual sense** for your trading timeframe, not one that maximizes historical backtest returns. A robust N works reasonably well across conditions; a perfect-fit N works spectacularly on history and breaks on live data.

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List


def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """Momentum = Today's close − Close N days ago."""
    return prices - prices.shift(n)


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI with Wilder's smoothing."""
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period-1) + gains.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period-1) + losses.iloc[i]) / period
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def sensitivity_comparison(prices: pd.Series,
                            n_values: List[int] = [5, 10, 20, 40],
                            oscillator_type: str = 'momentum'):
    """
    Side-by-side comparison of multiple N values on the same price data.
    Demonstrates the sensitivity tradeoff visually and numerically.

    Parameters:
      prices: closing price series
      n_values: list of lookback periods to compare
      oscillator_type: 'momentum' or 'rsi'
    """
    n_panels = len(n_values)
    fig, axes = plt.subplots(n_panels + 1, 1, figsize=(14, 3 * (n_panels + 1)),
                              sharex=True,
                              gridspec_kw={'height_ratios': [2] + [1] * n_panels})

    # Price panel
    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].set_ylabel('Price')
    axes[0].grid(True, alpha=0.3)

    colors = ['#E24B4A', '#EF9F27', '#378ADD', '#1D9E75']
    stats = []

    for i, n in enumerate(n_values):
        ax = axes[i + 1]
        color = colors[i % len(colors)]

        if oscillator_type == 'momentum':
            osc = compute_momentum(prices, n)
            eq_line = 0
            label = f'{n}-day Momentum'
        elif oscillator_type == 'rsi':
            osc = compute_rsi(prices, n)
            eq_line = 50
            label = f'{n}-day RSI'
        else:
            raise ValueError(f"Unknown type: {oscillator_type}")

        ax.plot(osc.index, osc.values, color=color, linewidth=0.9)
        ax.axhline(y=eq_line, color='black', linewidth=0.5, linestyle='--')
        ax.fill_between(osc.index, eq_line, osc.values,
                        where=(osc > eq_line), color='green', alpha=0.08)
        ax.fill_between(osc.index, eq_line, osc.values,
                        where=(osc <= eq_line), color='red', alpha=0.08)

        # Count zero-line (or 50-line) crossovers
        if oscillator_type == 'momentum':
            crossovers = ((osc.shift(1) * osc) < 0).sum()
        else:
            crossovers = (((osc.shift(1) - 50) * (osc - 50)) < 0).sum()

        # Count peaks (local maxima)
        peaks = ((osc > osc.shift(1)) & (osc > osc.shift(-1))).sum()

        ax.set_title(f'{label}  |  crossovers: {crossovers}  |  peaks: {peaks}',
                     fontsize=11)
        ax.set_ylabel('Value')
        ax.grid(True, alpha=0.3)

        stats.append({
            'N': n,
            'crossovers': crossovers,
            'peaks': peaks,
            'std': osc.std(),
        })

    plt.tight_layout()
    plt.show()

    # Print summary table
    print(f"\n=== Sensitivity Comparison ({oscillator_type}) ===")
    print(f"{'N':>4} {'Crossovers':>12} {'Peaks':>8} {'Std Dev':>10} {'Noise Level':>14}")
    print("-" * 52)
    max_cross = max(s['crossovers'] for s in stats)
    for s in stats:
        noise = 'High' if s['crossovers'] > max_cross * 0.7 else \
                'Medium' if s['crossovers'] > max_cross * 0.4 else 'Low'
        print(f"{s['N']:>4} {s['crossovers']:>12} {s['peaks']:>8} "
              f"{s['std']:>10.2f} {noise:>14}")

    return stats


def proportionality_demo(prices: pd.Series):
    """
    Demonstrate the proportionality rule: short-N peaks correspond
    to small reversals, long-N peaks correspond to large reversals.
    """
    mom_5 = compute_momentum(prices, 5)
    mom_20 = compute_momentum(prices, 20)

    # Find peaks in each
    peaks_5 = (mom_5 > mom_5.shift(1)) & (mom_5 > mom_5.shift(-1)) & (mom_5 > 0)
    peaks_20 = (mom_20 > mom_20.shift(1)) & (mom_20 > mom_20.shift(-1)) & (mom_20 > 0)

    # Measure what happens after each peak (max drawdown in next N days)
    def avg_reversal_after_peaks(prices, peaks, forward_window):
        reversals = []
        peak_indices = peaks[peaks].index
        for idx in peak_indices:
            loc = prices.index.get_loc(idx)
            if loc + forward_window >= len(prices):
                continue
            future = prices.iloc[loc:loc + forward_window]
            peak_price = prices.iloc[loc]
            max_decline = (peak_price - future.min()) / peak_price * 100
            reversals.append(max_decline)
        return np.mean(reversals) if reversals else 0

    rev_5 = avg_reversal_after_peaks(prices, peaks_5, 5)
    rev_20 = avg_reversal_after_peaks(prices, peaks_20, 20)

    print("=== Proportionality Rule ===")
    print(f"5-day momentum peaks → avg reversal in next 5 days:  {rev_5:.2f}%")
    print(f"20-day momentum peaks → avg reversal in next 20 days: {rev_20:.2f}%")
    print(f"Ratio: {rev_20/max(rev_5, 0.01):.1f}x")
    print("(Long-N peaks tend to signal proportionally larger reversals)")


def timeframe_recommendation(holding_period_days: int) -> dict:
    """
    Suggest appropriate N values based on intended holding period.

    Rule of thumb: N should be roughly 0.5x to 1.5x the holding period
    for momentum/ROC. RSI and stochastics have their own conventions.
    """
    recommendations = {
        'momentum_n': max(3, holding_period_days),
        'roc_n': max(3, holding_period_days),
        'rsi_n': max(5, min(holding_period_days, 21)),
        'stochastics_n': max(5, min(holding_period_days, 14)),
    }

    trader_type = (
        'Day trader' if holding_period_days <= 3 else
        'Swing trader' if holding_period_days <= 15 else
        'Position trader'
    )

    print(f"=== N Recommendations for {trader_type} ===")
    print(f"Holding period: ~{holding_period_days} days")
    print(f"  Momentum / ROC:  N = {recommendations['momentum_n']}")
    print(f"  RSI:             N = {recommendations['rsi_n']}")
    print(f"  Stochastics:     N = {recommendations['stochastics_n']}")
    print(f"  Note: These are starting points, not optimal values.")
    print(f"        Adjust based on the specific instrument's volatility.")

    return recommendations


def noise_vs_lag_quantified(prices: pd.Series,
                             n_values: List[int] = [5, 10, 20, 40]):
    """
    Quantify the sensitivity tradeoff numerically:
      - Noise proxy: number of zero-line crossovers
      - Lag proxy: average delay from price turning point to oscillator signal

    Shows the tradeoff is real and monotonic — you can't escape it.
    """
    print("=== Noise vs Lag Quantification ===")
    print(f"{'N':>4} {'Crossovers':>12} {'Avg Lag (bars)':>15} {'Tradeoff':>20}")
    print("-" * 55)

    for n in n_values:
        mom = compute_momentum(prices, n)
        crossovers = ((mom.shift(1) * mom) < 0).sum()

        # Estimate lag: avg distance from price local min/max to
        # nearest momentum zero-cross
        price_peaks = ((prices > prices.shift(1)) &
                       (prices > prices.shift(-1)))
        mom_crosses = ((mom.shift(1) * mom) < 0)

        lags = []
        for idx in price_peaks[price_peaks].index:
            loc = prices.index.get_loc(idx)
            # Look forward for nearest mom cross
            for j in range(1, min(n * 2, len(prices) - loc)):
                if loc + j < len(mom) and mom_crosses.iloc[loc + j]:
                    lags.append(j)
                    break

        avg_lag = np.mean(lags) if lags else float('nan')
        tradeoff = f"{'Noisy' if crossovers > 20 else 'Clean':>6}, " \
                   f"{'Fast' if avg_lag < 5 else 'Slow':>4}"

        print(f"{n:>4} {crossovers:>12} {avg_lag:>15.1f} {tradeoff:>20}")

    print("\n(More crossovers = more noise. Higher lag = slower reaction.)")
    print("(You can reduce one, but only by increasing the other.)")


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    np.random.seed(42)
    n_days = 250

    # Simulated price with trend + range + trend
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

    # ── Sensitivity comparison: Momentum ──
    sensitivity_comparison(prices, n_values=[5, 10, 20, 40],
                           oscillator_type='momentum')

    # ── Sensitivity comparison: RSI ──
    sensitivity_comparison(prices, n_values=[5, 9, 14, 21],
                           oscillator_type='rsi')

    # ── Proportionality rule ──
    print()
    proportionality_demo(prices)

    # ── Noise vs lag quantification ──
    print()
    noise_vs_lag_quantified(prices, n_values=[5, 10, 20, 40])

    # ── Timeframe recommendations ──
    print()
    timeframe_recommendation(holding_period_days=1)   # Day trader
    print()
    timeframe_recommendation(holding_period_days=7)   # Swing trader
    print()
    timeframe_recommendation(holding_period_days=30)  # Position trader
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `sensitivity_comparison()` | Multi-panel visual + stats for 4 different N values | Shows crossover count and peak count decreasing as N increases |
| `proportionality_demo()` | Measures actual reversal size after short-N vs. long-N peaks | Proves long-N peaks correspond to larger reversals |
| `timeframe_recommendation()` | Maps holding period to suggested N values | Starting-point guidance, not optimization |
| `noise_vs_lag_quantified()` | Numerically shows noise (crossovers) vs. lag (bars) | Proves the tradeoff is real and monotonic — you can't escape it |

### Key Implementation Notes

1. **`sensitivity_comparison()`** counts zero-line crossovers as a noise proxy. More crossovers = more signals = more noise. Run it and you'll see: 5-day momentum might have 40+ crossovers while 40-day has 8-10. The ratio is dramatic.

2. **`proportionality_demo()`** actually measures what happens after oscillator peaks — short-N peaks are followed by small pullbacks, long-N peaks by larger ones. This is the quantitative proof of Schwager's proportionality rule.

3. **`noise_vs_lag_quantified()`** is the most important function conceptually. It measures both noise (crossover count) and lag (average bars between price turn and oscillator signal) side by side, showing they move in opposite directions. You can reduce one, but only by increasing the other. There is no parameter that gives you both low noise and low lag.

4. **`timeframe_recommendation()`** is deliberately simple — it gives starting-point suggestions, not "optimal" values. The comment "adjust based on the specific instrument's volatility" is intentional: the function resists the temptation to overfit.

---

## Connection to Broader Framework

### Link to [[Momentum Indicator]] and [[Rate of Change (ROC)]]
N is the primary parameter for both. Same tradeoff applies identically to subtraction (Momentum) and division (ROC) — the scale changes but the sensitivity behavior doesn't.

### Link to [[RSI]] and [[Stochastics]]
These normalized oscillators have their own N parameters (RSI default 14, stochastics default 5 with smoothing). The sensitivity tradeoff applies, but the normalization (0-100 range) means the OB/OS thresholds interact with N: a 5-day RSI reaching 70 is far more common than a 21-day RSI reaching 70. Changing N may require recalibrating OB/OS levels.

### Link to [[Moving Averages]] (Chapter 3)
The sensitivity tradeoff for oscillators is **algebraically identical** to the MA length tradeoff. Direction of N-day MA = sign of N-day Momentum. Changing N in the oscillator = changing the MA length. Same math, same tradeoff, different display.

### Link to [[Overbought and Oversold]]
Shorter N → oscillator reaches OB/OS more frequently → more signals but lower quality. Longer N → oscillator reaches OB/OS rarely → fewer signals but each one carries more weight. The N choice and OB/OS threshold choice interact: you may need to widen or tighten OB/OS levels after changing N.

### Link to Overfitting (Chapter 15)
Endlessly optimizing N on historical data is the definition of overfitting. The N that performed best over the last year captured noise-as-signal. A robust N is one that makes conceptual sense for the trading timeframe and performs reasonably (not perfectly) across varying conditions.

### Link to Decision Support Framework
The N parameter is a **design decision**, not an optimization target. It answers: "What timeframe of price behavior am I trying to read?" That's a question about your trading strategy, not about the data. Choose N from your strategy, then let the oscillator do its job. Don't choose N from the data and then claim you have a strategy.
