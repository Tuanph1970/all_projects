# MACD + Volume Confirmation
---
**Source:** Practical application combining Schwager's Chapter 6 (Oscillators) with volume analysis principles
**Tags:** #technical-analysis #MACD #volume #confirmation #oscillators #momentum #conviction #indicators
**Related:** [[MACD]] · [[Oscillators]] · [[Overbought and Oversold]] · [[Divergence]] · [[Moving Averages]] · [[Failed Signals]]

---

## Why Combine MACD with Volume?

MACD and volume answer **different questions**:

| Dimension | Tool | Question |
|---|---|---|
| **Momentum** | MACD | "How fast is price changing?" |
| **Conviction** | Volume | "How many participants are behind this change?" |

A move with strong momentum AND strong conviction is the highest-quality signal. A move with strong momentum but weak conviction is suspect.

> Using both together is more robust than using either alone — because you're cross-checking two **independent** dimensions of market behavior. MACD and RSI, by contrast, both measure momentum — their "agreement" is partially redundant. MACD and volume are genuinely independent.

---

## Simple Analogy: The Crowd and the Shout

Think of MACD as hearing someone shout from a distance:
- **Direction** of the shout = bullish or bearish (which side of zero)
- **Loudness** of the shout = momentum strength (how far from zero)

Volume tells you **how many people are shouting the same thing**:
- One person shouting = noise. The move lacks support.
- A crowd shouting = signal. Many participants agree on the direction.

The strongest signals come when a loud shout (strong MACD) is backed by a large crowd (high volume). A loud shout from one person in an empty room (strong MACD on thin volume) should make you suspicious.

---

## Three Practical Combinations

### 1. Volume Confirmation of MACD Crossovers

The simplest combination. When MACD generates a signal line crossover, check volume relative to its average:

| MACD Signal | Volume Condition | Signal Quality | Action |
|---|---|---|---|
| Bullish crossover | Volume **above** average | Strong — many participants supporting the move | Enter with confidence |
| Bullish crossover | Volume **below** average | Weak — momentum shift on thin participation | Wait for volume to confirm, or skip |
| Bearish crossover | Volume **above** average | Strong — heavy selling pressure | Respect the signal |
| Bearish crossover | Volume **below** average | Weak — may be temporary thin selling | Could be a dip-buy if trend is intact |

This maps to Schwager's "confirmation condition" concept from Chapter 14 — requiring a second independent condition before acting on the primary signal.

### 2. Volume-Weighted MACD

Instead of computing MACD on raw closing prices, compute it on a **volume-weighted price** (e.g., typical price × volume, then normalize). This embeds volume directly into the oscillator so the MACD line reflects not just price change but *how much conviction* was behind each change.

**The idea:** A $1 move on 10 million shares should register differently than a $1 move on 100,000 shares. Standard MACD treats them identically. Volume-weighted MACD weights the high-volume move more heavily.

**Tradeoff:** More complex to compute and interpret. The standard MACD is a pure price-momentum tool; adding volume changes what it measures. Use this as an experimental supplement, not a replacement.

### 3. MACD + OBV Divergence

OBV (On-Balance Volume) is a cumulative indicator: adds volume on up-close days, subtracts volume on down-close days. It tracks whether volume is flowing *into* or *out of* a security.

Comparing OBV's direction with MACD's direction creates a **two-dimensional divergence check**:

| MACD Peaks | OBV Peaks | Interpretation |
|---|---|---|
| Higher highs | Higher highs | Full confirmation — momentum AND participation both growing |
| Higher highs | **Lower highs** | Warning — price rising but volume drying up. Move lacks conviction. |
| Lower highs | Higher highs | Volume is flowing in despite weakening momentum — potential accumulation |
| Lower highs | Lower highs | Both weakening — trend likely exhausted |

> The MACD-vs-OBV divergence is especially powerful because it's a divergence on the *volume* dimension — independent of the price-vs-momentum divergence from [[Divergence]]. When both types of divergence appear simultaneously (price making new highs, MACD making lower highs, AND OBV making lower highs), the warning is significantly stronger.

---

## The Complete Decision Matrix

| MACD Signal | Volume Condition | OBV Direction | Confidence | Recommended Action |
|---|---|---|---|---|
| Bullish cross | High volume | OBV rising | Highest | Full position entry |
| Bullish cross | High volume | OBV flat/falling | Moderate | Partial entry, watch for follow-through |
| Bullish cross | Low volume | OBV rising | Moderate | Wait for volume confirmation bar |
| Bullish cross | Low volume | OBV flat/falling | Lowest | Skip or very small position |
| MACD divergence | — | OBV also diverging | Strong warning | Tighten stops, take partial profits |
| MACD divergence | — | OBV still healthy | Mild warning | Watch but don't panic |

---

## Connection to Schwager's Framework

### Volume as a Confirmation Condition
Schwager discusses confirmation conditions extensively in Chapters 7 and 14 — secondary conditions that must be met before acting on a primary signal. Volume confirmation fits this framework perfectly:
- **Primary signal:** MACD crossover (price momentum)
- **Confirmation condition:** above-average volume (market conviction)

### Independent vs. Redundant Confirmation
Schwager's confirmation conditions work best when they measure **something different** from the primary signal. Volume is ideal because it's an independent data stream — not derived from price. Contrast with using RSI to confirm MACD: both measure price momentum, so their "agreement" is partially circular.

### Link to [[Oscillators]] — Use Case 4 (Trend-Direction Entry Timing)
Volume-confirmed MACD crossovers are particularly useful for the trend-direction entry timing use case. In an uptrend, you want to buy pullbacks. A bullish MACD signal-line crossover on above-average volume during a pullback = strong signal that the pullback is ending and the trend is resuming.

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional


def compute_macd(prices: pd.Series,
                  fast: int = 12, slow: int = 26,
                  signal: int = 9) -> pd.DataFrame:
    """Standard MACD: EMA(fast) - EMA(slow) + signal line."""
    ema_f = prices.ewm(span=fast, adjust=False).mean()
    ema_s = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_f - ema_s
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return pd.DataFrame({
        'macd': macd, 'signal': sig, 'histogram': hist
    }, index=prices.index)


def compute_obv(prices: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume: cumulative volume, adding on up-close days
    and subtracting on down-close days.
    """
    direction = np.sign(prices.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


def volume_confirmed_macd_signals(prices: pd.Series,
                                    volume: pd.Series,
                                    vol_avg_period: int = 20,
                                    vol_threshold: float = 1.0
                                    ) -> pd.DataFrame:
    """
    Detect MACD crossovers and classify by volume confirmation.

    Parameters:
      prices: closing prices
      volume: daily volume
      vol_avg_period: period for volume moving average
      vol_threshold: volume must be this multiple of avg to confirm
                     (1.0 = at average, 1.5 = 50% above average)

    Returns:
      DataFrame with columns:
        'signal': 'bullish' / 'bearish' / None
        'volume_ratio': current volume / average volume
        'confirmed': True if volume ratio >= threshold
        'quality': 'strong' / 'weak' / None
    """
    macd_df = compute_macd(prices)
    macd_line = macd_df['macd']
    sig_line = macd_df['signal']

    vol_avg = volume.rolling(window=vol_avg_period).mean()
    vol_ratio = volume / vol_avg

    # Detect signal-line crossovers
    prev_above = macd_line.shift(1) > sig_line.shift(1)
    curr_above = macd_line > sig_line
    bull_cross = (~prev_above) & curr_above
    bear_cross = prev_above & (~curr_above)

    signal = pd.Series(None, index=prices.index, dtype=object)
    signal[bull_cross] = 'bullish'
    signal[bear_cross] = 'bearish'

    confirmed = vol_ratio >= vol_threshold
    quality = pd.Series(None, index=prices.index, dtype=object)
    quality[(signal.notna()) & confirmed] = 'strong'
    quality[(signal.notna()) & (~confirmed)] = 'weak'

    return pd.DataFrame({
        'signal': signal,
        'volume_ratio': vol_ratio.round(2),
        'confirmed': confirmed,
        'quality': quality,
    }, index=prices.index)


def macd_obv_divergence(prices: pd.Series,
                         volume: pd.Series,
                         lookback: int = 5) -> pd.DataFrame:
    """
    Detect double divergence: MACD divergence + OBV divergence.

    Checks if the most recent MACD peak is lower than the prior peak
    AND the most recent OBV peak is lower than the prior peak,
    while price made a higher high.

    Parameters:
      prices: closing prices
      volume: daily volume
      lookback: minimum bars between peaks

    Returns:
      DataFrame with columns:
        'price_higher_high': bool
        'macd_lower_high': bool
        'obv_lower_high': bool
        'double_divergence': bool (both MACD and OBV diverging)
    """
    macd_df = compute_macd(prices)
    obv = compute_obv(prices, volume)

    # Find local peaks (simplified: higher than N neighbors on each side)
    def find_peaks(series, n=lookback):
        peaks = pd.Series(False, index=series.index)
        for i in range(n, len(series) - n):
            window = series.iloc[i - n:i + n + 1]
            if series.iloc[i] == window.max():
                peaks.iloc[i] = True
        return peaks

    price_peaks = find_peaks(prices)
    macd_peaks = find_peaks(macd_df['macd'])
    obv_peaks = find_peaks(obv)

    # Get the two most recent peaks for each
    def last_two_peaks(series, peak_mask):
        peak_vals = series[peak_mask]
        if len(peak_vals) < 2:
            return None, None
        return peak_vals.iloc[-2], peak_vals.iloc[-1]

    p_prev, p_last = last_two_peaks(prices, price_peaks)
    m_prev, m_last = last_two_peaks(macd_df['macd'], macd_peaks)
    o_prev, o_last = last_two_peaks(obv, obv_peaks)

    result = {
        'price_higher_high': p_last > p_prev if p_prev and p_last else None,
        'macd_lower_high': m_last < m_prev if m_prev and m_last else None,
        'obv_lower_high': o_last < o_prev if o_prev and o_last else None,
    }
    result['double_divergence'] = (
        result['price_higher_high'] is True and
        result['macd_lower_high'] is True and
        result['obv_lower_high'] is True
    )

    return result


def compute_volume_weighted_macd(prices: pd.Series,
                                   volume: pd.Series,
                                   fast: int = 12,
                                   slow: int = 26,
                                   signal: int = 9) -> pd.DataFrame:
    """
    Volume-Weighted MACD: apply MACD to VWAP-like prices
    instead of raw closes.

    Method: Use volume-weighted close as input.
    vw_price = cumulative(price * volume) / cumulative(volume)
    computed on a rolling basis.
    """
    vw_price = (prices * volume).rolling(window=fast).sum() / \
               volume.rolling(window=fast).sum()

    return compute_macd(vw_price, fast, slow, signal)


def plot_macd_volume(prices: pd.Series,
                      volume: pd.Series,
                      vol_avg_period: int = 20):
    """
    Three-panel chart:
      Top: Price
      Middle: Volume bars (colored by MACD crossover confirmation)
      Bottom: MACD with signal line + histogram

    Volume bars are green/red based on close direction,
    with opacity indicating above/below average volume.
    """
    macd_df = compute_macd(prices)
    obv = compute_obv(prices, volume)
    vol_avg = volume.rolling(window=vol_avg_period).mean()
    vol_signals = volume_confirmed_macd_signals(prices, volume, vol_avg_period)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(
        4, 1, figsize=(14, 14), sharex=True,
        gridspec_kw={'height_ratios': [2.5, 1, 1, 1.5]}
    )

    # ── Price ──
    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    ax1.set_title('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)

    # Mark confirmed vs weak signals on price chart
    for i, row in vol_signals.iterrows():
        if row['signal'] == 'bullish':
            color = '#1D9E75' if row['quality'] == 'strong' else '#9FE1CB'
            marker = '^'
            ax1.scatter(i, prices[i], color=color, marker=marker,
                       s=80, zorder=5, edgecolors='black', linewidths=0.3)
        elif row['signal'] == 'bearish':
            color = '#E24B4A' if row['quality'] == 'strong' else '#F7C1C1'
            marker = 'v'
            ax1.scatter(i, prices[i], color=color, marker=marker,
                       s=80, zorder=5, edgecolors='black', linewidths=0.3)

    ax1.set_ylabel('Price')

    # ── Volume bars ──
    close_direction = prices.diff()
    vol_colors = ['#1D9E75' if d >= 0 else '#E24B4A'
                  for d in close_direction.values]
    vol_alphas = [0.8 if v >= a else 0.3
                  for v, a in zip(volume.values, vol_avg.values)]

    for i in range(len(volume)):
        ax2.bar(volume.index[i], volume.values[i],
                color=vol_colors[i], alpha=vol_alphas[i], width=1.5)

    ax2.plot(vol_avg.index, vol_avg.values, color='#534AB7',
             linewidth=1.0, linestyle='--', label=f'{vol_avg_period}-day avg')
    ax2.set_title('Volume (bright = above avg, faded = below avg)', fontsize=12)
    ax2.set_ylabel('Volume')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── OBV ──
    ax3.plot(obv.index, obv.values, color='#534AB7', linewidth=1.0)
    ax3.set_title('On-Balance Volume (OBV)', fontsize=12)
    ax3.set_ylabel('OBV')
    ax3.grid(True, alpha=0.3)

    # ── MACD ──
    ax4.plot(macd_df.index, macd_df['macd'].values,
             color='#534AB7', linewidth=1.2, label='MACD')
    ax4.plot(macd_df.index, macd_df['signal'].values,
             color='#EF9F27', linewidth=1.2, linestyle='--',
             label='Signal line')
    ax4.axhline(y=0, color='black', linewidth=0.5, linestyle='--', alpha=0.4)

    hist = macd_df['histogram']
    hist_colors = ['#1D9E75' if v >= 0 else '#E24B4A' for v in hist.values]
    ax4.bar(macd_df.index, hist.values, color=hist_colors, alpha=0.35, width=1.5)

    ax4.set_title('MACD + Signal Line + Histogram', fontsize=12)
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    # ── Print signal summary ──
    sig_df = vol_signals[vol_signals['signal'].notna()]
    if len(sig_df) > 0:
        strong = (sig_df['quality'] == 'strong').sum()
        weak = (sig_df['quality'] == 'weak').sum()
        print(f"=== Volume-Confirmed MACD Signals ===")
        print(f"Total crossovers: {len(sig_df)}")
        print(f"  Strong (volume confirmed): {strong}")
        print(f"  Weak (low volume):         {weak}")
        print(f"  Confirmation rate:         {strong/len(sig_df)*100:.0f}%")


# ── Example Usage ──────────────────────────────────────────────
if __name__ == '__main__':

    np.random.seed(42)
    n_days = 250

    # Simulate price
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

    # Simulate volume (higher on trend days, lower on range days)
    base_vol = 1_000_000
    vol_noise = np.random.lognormal(0, 0.5, n_days)
    price_change = np.abs(np.diff(np.concatenate([[0], trend])))
    volume = pd.Series(
        (base_vol * (1 + price_change * 2) * vol_noise).astype(int),
        index=prices.index,
        name='Volume'
    )

    # ── Full visualization ──
    plot_macd_volume(prices, volume)

    # ── Volume-confirmed signals ──
    signals = volume_confirmed_macd_signals(prices, volume)
    confirmed_signals = signals[signals['signal'].notna()]
    print("\n=== Recent Signals ===")
    print(confirmed_signals.tail(10).to_string())

    # ── Double divergence check ──
    print("\n=== Double Divergence Analysis ===")
    div_result = macd_obv_divergence(prices, volume)
    for key, val in div_result.items():
        print(f"  {key}: {val}")
    if div_result['double_divergence']:
        print("  *** DOUBLE DIVERGENCE DETECTED — strong warning ***")
    else:
        print("  No double divergence at this time")

    # ── OBV trend ──
    obv = compute_obv(prices, volume)
    obv_trend = 'rising' if obv.iloc[-1] > obv.iloc[-20] else 'falling'
    print(f"\n=== OBV 20-day trend: {obv_trend} ===")
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_macd()` | Standard MACD calculation | Reused from [[MACD]] note |
| `compute_obv()` | On-Balance Volume — cumulative volume direction | Independent volume momentum indicator |
| `volume_confirmed_macd_signals()` | Classify MACD crossovers as "strong" (volume-confirmed) or "weak" | The core combination — volume as confirmation condition |
| `macd_obv_divergence()` | Detect double divergence (both MACD and OBV diverging from price) | Strongest warning signal — two independent dimensions both fading |
| `compute_volume_weighted_macd()` | MACD on volume-weighted prices | Experimental — embeds volume into the oscillator itself |
| `plot_macd_volume()` | Four-panel chart: price, volume, OBV, MACD | Full visual with signal quality markers on price chart |

### Key Implementation Notes

1. **`volume_confirmed_macd_signals()`** is the workhorse. It detects MACD signal-line crossovers, then checks whether volume on the crossover bar exceeds its 20-day average. The `vol_threshold` parameter (default 1.0 = at average) can be raised to 1.5 for stricter confirmation. Signals are labeled "strong" or "weak" based on this check.

2. **The four-panel visualization** maps the story top to bottom: price (with signal quality markers — bright colors for strong, faded for weak), volume bars (bright if above average, faded if below), OBV line (cumulative volume direction), and MACD (standard display). This lets you see at a glance whether momentum and conviction are aligned.

3. **`macd_obv_divergence()`** checks for the most dangerous condition: price making higher highs while BOTH MACD and OBV make lower highs. This "double divergence" means momentum is fading AND participation is drying up — two independent warnings converging on the same conclusion.

4. **Volume simulation** in the example uses log-normal noise (volume is always positive and right-skewed) with higher values during trending phases and lower values during the range. This mimics real market behavior where volume tends to expand during trends and contract during consolidations.

---

## Important Caveats

### Not in Schwager Chapter 6
Volume indicators are not covered in Chapter 6. This note extends Schwager's oscillator framework with volume concepts from broader technical analysis. The combination is well-established in practice but treat it as a practical supplement, not as Schwager's teaching.

### Volume Data Availability
- **Stocks:** volume data is readily available and reliable
- **Futures:** volume data exists but may be less straightforward (exchange volume, total open interest)
- **Forex:** no centralized volume data — tick volume is used as a proxy but is less reliable

### The Independence Principle
The reason MACD + volume is a strong combination is that they measure **different things** (price momentum vs. participation). This is more valuable than combining two price-based oscillators (e.g., MACD + RSI), which partly duplicate each other's information. When choosing confirmation tools, prioritize independence of the data source.
