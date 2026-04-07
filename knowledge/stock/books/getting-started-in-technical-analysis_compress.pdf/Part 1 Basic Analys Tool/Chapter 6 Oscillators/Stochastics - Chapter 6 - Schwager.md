# Stochastics
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 110–111, 117), Appendix (pp. 321–322)
**Tags:** #technical-analysis #stochastics #oscillators #momentum #schwager #normalized #overbought #oversold #indicators
**Related:** [[Oscillators]] · [[RSI]] · [[Unbounded vs Normalized Oscillators]] · [[Overbought and Oversold]] · [[Divergence]] · [[MACD]] · [[Oscillator Sensitivity]] · [[Momentum]]

---

## Definition

Stochastics measures momentum by comparing **today's close to the high-low range** of the past N days. It answers: "Where is the close positioned within the recent range?"

### %K Formula
```
%K = ((Close − Lowest Low of N days) / (Highest High of N days − Lowest Low of N days)) × 100
```

### %D Formula
```
%D = 3-day moving average of %K
```

> "Stochastics measures momentum by comparing the recent close to the absolute price range (high of the range minus low of the range) over an N-day period." — Schwager

---

## Simple Analogy: Elevator Position in a Building

Think of the N-day price range as a building:

| Component | Building Analogy |
|---|---|
| **Lowest low** (N days) | Ground floor |
| **Highest high** (N days) | Top floor |
| **Today's close** | The elevator |
| **%K value** | What floor the elevator is on (as % of total floors) |

| %K Reading | Elevator Position | Market Meaning |
|---|---|---|
| **90-100** | Near the top floor | Close at the top of recent range — overbought |
| **50** | Middle floor | Close in the middle of recent range — neutral |
| **0-10** | Near the ground floor | Close at the bottom of recent range — oversold |

**Key difference from RSI:** RSI asks "how strong has the engine been?" (gain/loss pressure). Stochastics asks "what floor are we on?" (position in the range). Different questions about the same market.

---

## The Four Lines: Fast vs. Slow

Schwager explains the progression from noisy to usable:

### Fast Stochastics (raw — typically too noisy to trade)

```
Fast %K = raw formula (typically 5-day period)
Fast %D = 3-day MA of Fast %K
```

> "Because of the noisiness of the raw %K and %D lines (commonly calculated over a five-day period, and referred to as 'fast stochastics')..." — Schwager

### Slow Stochastics (smoothed — what everyone actually uses)

```
Slow %K = Fast %D          (the smoothed line becomes the new main line)
Slow %D = 3-day MA of Slow %K   (smoothing the already-smoothed line)
```

> "An additionally smoothed version of stochastics called 'slow stochastics' is usually used by most software programs, and is most frequently referred to simply as 'stochastics.'" — Schwager

### The Smoothing Progression

```
Raw price data
  → Fast %K (raw formula — very jittery)
    → Fast %D = 3-day MA of Fast %K (first smoothing)
      → Slow %K = Fast %D (reuse the smoothed line)
        → Slow %D = 3-day MA of Slow %K (second smoothing)
```

This is the same layered-smoothing pattern as MACD: raw oscillator → smoothed with a signal line → the signal line itself gets smoothed.

---

## How It Generates Signals

### 1. OB/OS Zone Signals (primary use)

| Level | Standard Value | Meaning |
|---|---|---|
| **Overbought** | 80 | Close consistently near the top of the recent range |
| **Oversold** | 20 | Close consistently near the bottom of the recent range |
| **Neutral** | 50 | Close in the middle of the range |

All the same principles from [[Overbought and Oversold]] apply: four timing approaches, trend adjustment, oscillator skew in trends, "trading alert" framework.

### 2. %K/%D Crossover Signals

| Signal | Condition | Meaning |
|---|---|---|
| **Bullish** | %K crosses above %D | Faster line overtaking slower — upward momentum shift |
| **Bearish** | %K crosses below %D | Faster line dropping below slower — downward momentum shift |

> "The additional line on the stochastic is a 3-day moving average of the basic stochastic, similar to the signal line of the MACD." — Schwager

**Best practice:** Crossovers are most meaningful when they occur **within** the OB/OS zones. A bullish %K/%D crossover in the oversold zone (below 20) is a much stronger buy signal than one in the neutral zone (40-60).

---

## RSI vs. Stochastics — Comparison

| Property | RSI | Stochastics |
|---|---|---|
| **Measures** | Gain/loss balance (close-to-close changes) | Close position in N-day high/low range |
| **Input data** | Close only | Close, High, Low (OHLC) |
| **Question answered** | "How dominant has buying pressure been?" | "Where is the close within the recent range?" |
| **Range** | 0–100 | 0–100 |
| **Default OB/OS** | 70 / 30 | 80 / 20 |
| **Default period** | 14 days | 5 days (fast), smoothed to slow |
| **Lines** | Single line | Two lines (%K and %D) with crossover |
| **Smoothing** | Wilder's exponential | MA-based (fast/slow variants) |
| **Raw noisiness** | Moderate | High — fast stochastics is very jittery |

### When They Disagree — That's Interesting

| Condition | Possible Interpretation |
|---|---|
| RSI overbought, stochastics not | Strong gains, but close isn't at top of absolute range (wide range absorbs the move) |
| Stochastics overbought, RSI not | Close near range top, but gains haven't been dominant (drifted up in narrow range) |
| Both overbought | Strong agreement — higher conviction OB signal |
| Both oversold | Strong agreement — higher conviction OS signal |

> When both agree → stronger signal. When they disagree → investigate before acting.

---

## Properties

| Property | Value |
|---|---|
| **Type** | Normalized (bounded) oscillator |
| **Range** | 0 to 100 |
| **Equilibrium** | 50 |
| **Default periods** | %K: 5 or 14 days, %D: 3-day MA |
| **Variants** | Fast (raw + 1 smoothing) and Slow (2 layers of smoothing) |
| **OB/OS levels** | 80 / 20 (standard) |
| **Signal types** | OB/OS zones, %K/%D crossovers |

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_stochastic(high: pd.Series,
                        low: pd.Series,
                        close: pd.Series,
                        k_period: int = 14,
                        d_period: int = 3,
                        variant: str = 'slow') -> pd.DataFrame:
    """
    Stochastic Oscillator.

    Parameters:
      high: daily high prices
      low: daily low prices
      close: daily close prices
      k_period: lookback for %K calculation (default 14)
      d_period: smoothing period for %D (default 3)
      variant: 'fast' or 'slow'

    Returns:
      DataFrame with columns: '%K', '%D'

    Fast stochastics:
      %K = raw formula
      %D = 3-day MA of %K

    Slow stochastics:
      %K = Fast %D (first smoothing becomes the main line)
      %D = 3-day MA of Slow %K (second smoothing)
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    # Raw %K
    fast_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    fast_d = fast_k.rolling(window=d_period).mean()

    if variant == 'fast':
        return pd.DataFrame({
            '%K': fast_k,
            '%D': fast_d,
        }, index=close.index)

    elif variant == 'slow':
        slow_k = fast_d  # Fast %D becomes Slow %K
        slow_d = slow_k.rolling(window=d_period).mean()
        return pd.DataFrame({
            '%K': slow_k,
            '%D': slow_d,
        }, index=close.index)

    else:
        raise ValueError(f"variant must be 'fast' or 'slow', got '{variant}'")


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI with Wilder's smoothing (for comparison)."""
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


def fast_vs_slow_comparison(high: pd.Series,
                              low: pd.Series,
                              close: pd.Series,
                              k_period: int = 14):
    """
    Visual comparison of fast vs. slow stochastics.
    Shows why slow stochastics is preferred — fast version is too noisy.
    """
    fast = compute_stochastic(high, low, close, k_period, variant='fast')
    slow = compute_stochastic(high, low, close, k_period, variant='slow')

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                                         gridspec_kw={'height_ratios': [2, 1, 1]})

    ax1.plot(close.index, close.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # Fast stochastics
    ax2.plot(fast.index, fast['%K'].values, color='#378ADD', linewidth=0.8,
             label='Fast %K')
    ax2.plot(fast.index, fast['%D'].values, color='#EF9F27', linewidth=0.8,
             linestyle='--', label='Fast %D')
    ax2.axhline(y=80, color='red', linewidth=0.5, linestyle=':')
    ax2.axhline(y=20, color='green', linewidth=0.5, linestyle=':')
    ax2.set_ylim(0, 100)
    crosses_fast = (((fast['%K'].shift(1) - fast['%D'].shift(1)) *
                     (fast['%K'] - fast['%D'])) < 0).sum()
    ax2.set_title(f'Fast stochastics (noisy) — crossovers: {crosses_fast}',
                  fontsize=11)
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Slow stochastics
    ax3.plot(slow.index, slow['%K'].values, color='#378ADD', linewidth=1.0,
             label='Slow %K')
    ax3.plot(slow.index, slow['%D'].values, color='#EF9F27', linewidth=1.0,
             linestyle='--', label='Slow %D')
    ax3.axhline(y=80, color='red', linewidth=0.5, linestyle=':')
    ax3.axhline(y=20, color='green', linewidth=0.5, linestyle=':')
    ax3.set_ylim(0, 100)
    crosses_slow = (((slow['%K'].shift(1) - slow['%D'].shift(1)) *
                     (slow['%K'] - slow['%D'])) < 0).sum()
    ax3.set_title(f'Slow stochastics (usable) — crossovers: {crosses_slow}',
                  fontsize=11)
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.suptitle(f'Fast vs Slow stochastics ({k_period}-day): '
                 f'smoothing reduces noise by '
                 f'{(1-crosses_slow/max(crosses_fast,1))*100:.0f}%',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


def rsi_vs_stochastics(high: pd.Series,
                        low: pd.Series,
                        close: pd.Series,
                        period: int = 14):
    """
    Side-by-side RSI and slow stochastics to show where
    they agree and disagree.
    """
    rsi = compute_rsi(close, period)
    stoch = compute_stochastic(high, low, close, period, variant='slow')

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                                         gridspec_kw={'height_ratios': [2, 1, 1]})

    ax1.plot(close.index, close.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # RSI
    ax2.plot(rsi.index, rsi.values, color='#534AB7', linewidth=1.0)
    ax2.axhline(y=70, color='red', linewidth=0.7, linestyle=':')
    ax2.axhline(y=30, color='green', linewidth=0.7, linestyle=':')
    ax2.axhline(y=50, color='black', linewidth=0.4, linestyle='--')
    ax2.fill_between(rsi.index, 70, 100,
                     where=(rsi >= 70), color='red', alpha=0.1)
    ax2.fill_between(rsi.index, 0, 30,
                     where=(rsi <= 30), color='green', alpha=0.1)
    ax2.set_ylim(0, 100)
    rsi_ob = (rsi >= 70).sum()
    rsi_os = (rsi <= 30).sum()
    ax2.set_title(f'RSI (14-day) — OB/OS: 70/30 — OB bars: {rsi_ob}, '
                  f'OS bars: {rsi_os}', fontsize=11)
    ax2.grid(True, alpha=0.3)

    # Stochastics
    ax3.plot(stoch.index, stoch['%K'].values, color='#378ADD', linewidth=1.0,
             label='%K')
    ax3.plot(stoch.index, stoch['%D'].values, color='#EF9F27', linewidth=1.0,
             linestyle='--', label='%D')
    ax3.axhline(y=80, color='red', linewidth=0.7, linestyle=':')
    ax3.axhline(y=20, color='green', linewidth=0.7, linestyle=':')
    ax3.fill_between(stoch.index, 80, 100,
                     where=(stoch['%K'] >= 80), color='red', alpha=0.1)
    ax3.fill_between(stoch.index, 0, 20,
                     where=(stoch['%K'] <= 20), color='green', alpha=0.1)
    ax3.set_ylim(0, 100)
    stoch_ob = (stoch['%K'] >= 80).sum()
    stoch_os = (stoch['%K'] <= 20).sum()
    ax3.set_title(f'Slow stochastics (14-day) — OB/OS: 80/20 — '
                  f'OB bars: {stoch_ob}, OS bars: {stoch_os}', fontsize=11)
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.suptitle('RSI vs Stochastics: same family, different questions',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()

    # Agreement analysis
    both_ob = ((rsi >= 70) & (stoch['%K'] >= 80)).sum()
    both_os = ((rsi <= 30) & (stoch['%K'] <= 20)).sum()
    rsi_ob_only = ((rsi >= 70) & (stoch['%K'] < 80)).sum()
    stoch_ob_only = ((rsi < 70) & (stoch['%K'] >= 80)).sum()

    print(f"=== RSI vs Stochastics Agreement ===")
    print(f"Both overbought:        {both_ob} bars")
    print(f"Both oversold:          {both_os} bars")
    print(f"RSI OB, stoch not:      {rsi_ob_only} bars (disagreement)")
    print(f"Stoch OB, RSI not:      {stoch_ob_only} bars (disagreement)")
    print(f"Agreement rate (OB):    "
          f"{both_ob/max(rsi_ob+stoch_ob_only,1)*100:.0f}%")


def stochastic_crossover_in_zones(high: pd.Series,
                                    low: pd.Series,
                                    close: pd.Series,
                                    k_period: int = 14):
    """
    Detect %K/%D crossovers and classify them by zone.
    Crossovers in OB/OS zones are higher quality than
    crossovers in the neutral zone.
    """
    stoch = compute_stochastic(high, low, close, k_period, variant='slow')
    k, d = stoch['%K'], stoch['%D']

    prev_above = k.shift(1) > d.shift(1)
    curr_above = k > d
    bull_cross = (~prev_above) & curr_above
    bear_cross = prev_above & (~curr_above)

    results = []
    for i in range(len(close)):
        if bull_cross.iloc[i]:
            zone = ('oversold' if k.iloc[i] <= 20 else
                    'overbought' if k.iloc[i] >= 80 else 'neutral')
            results.append({
                'date': close.index[i],
                'type': 'bullish',
                'zone': zone,
                'quality': 'high' if zone == 'oversold' else 'low',
                '%K': round(k.iloc[i], 1),
            })
        elif bear_cross.iloc[i]:
            zone = ('overbought' if k.iloc[i] >= 80 else
                    'oversold' if k.iloc[i] <= 20 else 'neutral')
            results.append({
                'date': close.index[i],
                'type': 'bearish',
                'zone': zone,
                'quality': 'high' if zone == 'overbought' else 'low',
                '%K': round(k.iloc[i], 1),
            })

    df = pd.DataFrame(results)
    if len(df) > 0:
        high_q = (df['quality'] == 'high').sum()
        low_q = (df['quality'] == 'low').sum()
        print(f"=== Stochastic Crossover Quality ===")
        print(f"Total crossovers: {len(df)}")
        print(f"  In OB/OS zone (high quality): {high_q}")
        print(f"  In neutral zone (low quality): {low_q}")
        print(f"\nRecent crossovers:")
        print(df.tail(8).to_string(index=False))

    return df


def plot_stochastics_full(high: pd.Series,
                           low: pd.Series,
                           close: pd.Series,
                           k_period: int = 14):
    """
    Complete stochastics visualization with OB/OS zones,
    %K/%D crossover markers, and zone-quality shading.
    """
    stoch = compute_stochastic(high, low, close, k_period, variant='slow')

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                    gridspec_kw={'height_ratios': [2, 1]})

    ax1.plot(close.index, close.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    k, d = stoch['%K'], stoch['%D']
    ax2.plot(k.index, k.values, color='#378ADD', linewidth=1.0, label='%K')
    ax2.plot(d.index, d.values, color='#EF9F27', linewidth=1.0,
             linestyle='--', label='%D')
    ax2.axhline(y=80, color='red', linewidth=0.8, linestyle='--')
    ax2.axhline(y=20, color='green', linewidth=0.8, linestyle='--')
    ax2.axhline(y=50, color='gray', linewidth=0.4, linestyle=':')
    ax2.fill_between(k.index, 80, 100, where=(k >= 80),
                     color='red', alpha=0.12)
    ax2.fill_between(k.index, 0, 20, where=(k <= 20),
                     color='green', alpha=0.12)
    ax2.set_ylim(0, 100)

    # Mark crossovers in OB/OS zones only (high quality)
    prev_above = k.shift(1) > d.shift(1)
    curr_above = k > d
    bull_in_os = (~prev_above) & curr_above & (k <= 30)
    bear_in_ob = prev_above & (~curr_above) & (k >= 70)

    if bull_in_os.any():
        ax2.scatter(k.index[bull_in_os], k.values[bull_in_os],
                    color='#1D9E75', marker='^', s=70, zorder=5,
                    label='Buy (cross in OS zone)')
    if bear_in_ob.any():
        ax2.scatter(k.index[bear_in_ob], k.values[bear_in_ob],
                    color='#E24B4A', marker='v', s=70, zorder=5,
                    label='Sell (cross in OB zone)')

    ax2.set_title(f'Slow stochastics ({k_period}-day)', fontsize=12)
    ax2.legend(fontsize=8, loc='upper left')
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
    close = pd.Series(
        100 + trend + noise,
        index=pd.date_range('2024-01-01', periods=n_days, freq='B'),
        name='Close'
    )
    high = close + np.abs(np.random.normal(0, 0.8, n_days))
    low = close - np.abs(np.random.normal(0, 0.8, n_days))

    # ── Full stochastics chart ──
    plot_stochastics_full(high, low, close)

    # ── Fast vs slow comparison ──
    fast_vs_slow_comparison(high, low, close)

    # ── RSI vs stochastics ──
    rsi_vs_stochastics(high, low, close)

    # ── Crossover quality analysis ──
    print()
    stochastic_crossover_in_zones(high, low, close)
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_stochastic()` | Core: fast or slow variant with configurable periods | Fast %D becomes Slow %K — the smoothing chain |
| `fast_vs_slow_comparison()` | Side-by-side: fast (noisy) vs. slow (usable) | Counts crossovers to quantify noise reduction |
| `rsi_vs_stochastics()` | RSI and stochastics on same data with agreement analysis | Shows when they agree (strong) and disagree (informative) |
| `stochastic_crossover_in_zones()` | Classifies crossovers by zone (OB/OS vs. neutral) | Crossovers in extreme zones are higher quality |
| `plot_stochastics_full()` | Complete chart with zone shading and quality markers | Only marks crossovers in OB/OS zones (high quality signals) |

### Key Implementation Notes

1. **`compute_stochastic()`** takes OHLC data (high, low, close) — unlike RSI which only needs close. This is a fundamental difference: stochastics uses the full price bar to determine the close's position within the range.

2. **`fast_vs_slow_comparison()`** counts crossovers for both variants. You'll see the fast version produces 2-3x more crossovers — that's the noise Schwager mentions. The smoothing typically reduces crossovers by 40-60%.

3. **`rsi_vs_stochastics()`** includes an agreement analysis that counts bars where both, only RSI, or only stochastics is in OB territory. The disagreement bars are the most interesting — they show when the two indicators diverge, which means the two different questions they ask are giving different answers about the same market.

4. **`stochastic_crossover_in_zones()`** classifies every crossover by whether it occurred in the OB zone, OS zone, or neutral zone. Crossovers in extreme zones are labeled "high quality" — this implements the common practice of only trading stochastic crossovers that happen in the OB/OS territory.

---

## Connection to Broader Framework

### Link to [[RSI]]
RSI and stochastics are both normalized to 0–100 but measure different things:
- **RSI:** gain/loss balance (close-to-close)
- **Stochastics:** close position in N-day range (uses high/low/close)
- They're complementary — agreement strengthens a signal, disagreement warrants investigation.

### Link to [[MACD]]
The %D line is "similar to the signal line of the MACD." Both are smoothed versions of the main oscillator line, generating crossover signals. The pattern: raw oscillator + smoothed version → crossover = signal.

### Link to [[Unbounded vs Normalized Oscillators]]
Stochastics is the second pillar of normalized oscillators (alongside RSI). Its 80/20 OB/OS levels are slightly more extreme than RSI's 70/30, reflecting its greater raw sensitivity (the %K formula is inherently jumpier than RSI's averaged gains/losses).

### Link to [[Overbought and Oversold]]
All the OB/OS principles apply: four timing approaches, trend adjustment, oscillator skew, "trading alert" framework. Stochastics is particularly prone to the trend-skew problem because its raw formula (fast %K) is very sensitive — which is why slow stochastics with its double smoothing became the standard.

### Link to [[Oscillators]] — Same Limitations
> "The fundamental information they convey is identical to that of the other indicators discussed in this chapter: Overbought levels are assumed to represent selling opportunities, and oversold levels are assumed to represent buying opportunities." — Schwager

Stochastics, despite its unique formula, is subject to every limitation discussed in the Oscillators note: works in ranges, fails in trends (unless used diagnostically), requires price confirmation.
