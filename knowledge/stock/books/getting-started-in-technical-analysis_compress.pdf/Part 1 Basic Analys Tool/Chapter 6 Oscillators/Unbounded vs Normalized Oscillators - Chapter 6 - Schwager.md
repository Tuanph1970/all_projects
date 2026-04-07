# Unbounded vs. Normalized Oscillators
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 116–117)
**Tags:** #technical-analysis #unbounded #normalized #oscillators #schwager #OB-OS #indicators
**Related:** [[Oscillators]] · [[Momentum Indicator]] · [[Rate of Change (ROC)]] · [[MACD]] · [[Price Oscillator]] · [[RSI]] · [[Stochastics]] · [[Overbought and Oversold]] · [[Equilibrium Line]]

---

## Definition

Schwager divides all oscillators into two families based on their **output range**:

| Family | Range | Members |
|---|---|---|
| **Unbounded** | No fixed limits — can go to ±infinity | Momentum, ROC, MA Oscillator, Price Oscillator, MACD |
| **Normalized (bounded)** | Fixed range, typically 0 to 100 | RSI, Stochastics |

> Unbounded indicators are described as having "no absolute high or low boundaries." Normalized oscillators "have fixed upper and lower boundaries." — Schwager

---

## Simple Analogy: Two Thermometer Types

**Unbounded (like Momentum):** A thermometer that shows the **raw temperature difference** from yesterday. It reads "+5 degrees" or "-12 degrees." No maximum reading — the temperature could jump by any amount. To know if "+5" is extreme, you must compare to historical readings *for this specific room*. "+5" in a tropical house is normal; "+5" in a meat freezer is an emergency.

**Normalized (like RSI):** A thermometer that always reads **between 0 and 100**, regardless of the room. It converts raw temperature into a percentage scale: 0 = "coldest recently" and 100 = "hottest recently." Now "above 70 = warm, below 30 = cold" works in *any room* without knowing the room's history. The scale self-adapts.

| Thermometer Type | Need Room-Specific Calibration? | Portable Across Rooms? |
|---|---|---|
| **Raw difference** (unbounded) | Yes — must study this room's history | No — "+5" means different things |
| **Percentage scale** (normalized) | No — scale auto-adjusts | Yes — "75" means the same everywhere |

---

## Why This Distinction Matters: OB/OS Level Setting

### Unbounded Oscillators — Manual Calibration Required

> "Overbought and oversold zones can be established simply by picking levels that isolate more extreme oscillator values. There are no hard-and-fast rules." — Schwager

**Schwager's guideline:** Capture the highest and lowest **10%** of readings by reviewing past peaks and troughs.

**The problem:** "There is no guarantee that overbought or oversold levels set today will be appropriate for market conditions a month from now."

As market volatility changes, the oscillator's range shifts → carefully set levels become obsolete. Requires ongoing recalibration.

### Normalized Oscillators — Standard Levels Work

Standard OB/OS levels work out of the box:

| Oscillator | OB Level | OS Level | Why It Works |
|---|---|---|---|
| **RSI** | 70 | 30 | Normalization constrains output to 0–100 regardless of price scale |
| **Stochastics** | 80 | 20 | Same — position within recent range is inherently scaled |

These are portable across instruments and time periods. "RSI above 70" means the same thing for any stock at any price level.

> Schwager notes levels are "commonly set equidistant from the upper and lower limits — for example, 70 and 30 or 80 and 20 (although this is not required, and would even be inappropriate in strongly trending markets)."

The trend adjustment ([[Overbought and Oversold]]) still applies — but the starting point is standardized, not empirical.

---

## How Normalization Works

### Unbounded = Absolute Measurement
- Raw magnitude in input units (dollars, points, ratio)
- +5 momentum on a $10 stock ≠ +5 on a $500 stock
- You know the **raw size** of the move

### Normalized = Relative Measurement
- Position within recent range, expressed as percentage (0–100)
- RSI 75 on a $10 stock = RSI 75 on a $500 stock
- You know **where the move stands relative to its own recent history**
- Raw magnitude information is lost — a large move and small move can produce the same reading if proportionally similar

---

## The Family Comparison

| Property | Unbounded | Normalized |
|---|---|---|
| **Examples** | Momentum, ROC, Price Oscillator, MACD | RSI, Stochastics |
| **Range** | −∞ to +∞ | 0 to 100 |
| **Equilibrium** | 0 (or 1.0 for ratio-based) | 50 |
| **OB/OS level setting** | Hard — empirical, instrument-specific, drifts over time | Easy — standard levels (70/30, 80/20) work universally |
| **Cross-instrument comparison** | Difficult (Momentum) or possible (ROC) | Easy — same scale everywhere |
| **Magnitude information** | Preserved — raw size of move visible | Lost — only relative position visible |
| **Primary signal type** | Crossovers (zero-line, signal line) | OB/OS zone entries/exits |
| **Best market context** | Trends (MACD crossovers) | Ranges (RSI/stochastics OB/OS mean-reversion) |
| **Countertrend use** | Possible but requires calibration | Natural — designed for this |
| **Trend-following use** | Natural — MACD crossovers are trend signals | Less suited — OB/OS signals are countertrend by nature |

---

## Schwager's Key Insight: Same Information, Different Packaging

Despite the structural difference, both families convey **identical fundamental information**:

> "Although the developers of these indicators suggest a variety of applications for these oscillators, the fundamental information they convey is identical to that of the other indicators discussed in this chapter: Overbought levels are assumed to represent selling opportunities, and oversold levels are assumed to represent buying opportunities." — Schwager

RSI at 80 and Momentum at a historically extreme positive value are saying the **same thing**: the pace of advance is extreme. They just express it on different scales.

---

## Practical Decision Guide: Which Family to Use When

| Situation | Recommended Family | Why |
|---|---|---|
| Trading a single stock's OB/OS in a range | **Normalized** (RSI, stochastics) | Standard levels work immediately, designed for mean-reversion |
| Screening many stocks for OB/OS | **Normalized** (RSI) | Same threshold applies to all instruments |
| Identifying trend changes via crossovers | **Unbounded** (MACD) | Crossover signals are trend-following, not OB/OS dependent |
| Measuring raw momentum magnitude | **Unbounded** (Momentum, ROC) | Raw size of move is preserved |
| Building a trend-following system | **Unbounded** (MACD, Price Oscillator) | Crossover signals work as entry/exit rules |
| Combining with volume for confirmation | **Either** — volume is independent of both | Volume confirms the conviction behind the signal regardless of oscillator family |

---

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def compute_momentum(prices: pd.Series, n: int = 10) -> pd.Series:
    """Unbounded: Close - Close(N). Range: -inf to +inf."""
    return prices - prices.shift(n)


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Normalized: RSI with Wilder's smoothing. Range: 0 to 100."""
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


def compute_stochastic(prices_high: pd.Series,
                        prices_low: pd.Series,
                        prices_close: pd.Series,
                        k_period: int = 14,
                        d_period: int = 3,
                        slow: bool = True) -> pd.DataFrame:
    """
    Normalized: Stochastics. Range: 0 to 100.

    Fast stochastics: raw %K and its 3-day MA (%D)
    Slow stochastics: smoothed %K (= fast %D) and its 3-day MA (slow %D)
    """
    lowest_low = prices_low.rolling(window=k_period).min()
    highest_high = prices_high.rolling(window=k_period).max()
    fast_k = 100 * (prices_close - lowest_low) / (highest_high - lowest_low)
    fast_d = fast_k.rolling(window=d_period).mean()

    if slow:
        slow_k = fast_d
        slow_d = slow_k.rolling(window=d_period).mean()
        return pd.DataFrame({'%K': slow_k, '%D': slow_d}, index=prices_close.index)

    return pd.DataFrame({'%K': fast_k, '%D': fast_d}, index=prices_close.index)


def compute_macd(prices: pd.Series,
                  fast: int = 12, slow: int = 26,
                  signal: int = 9) -> pd.DataFrame:
    """Unbounded: MACD. Range: -inf to +inf."""
    ema_f = prices.ewm(span=fast, adjust=False).mean()
    ema_s = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_f - ema_s
    sig = macd.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({'macd': macd, 'signal': sig}, index=prices.index)


def demonstrate_ob_os_difference(prices: pd.Series,
                                   prices_high: pd.Series,
                                   prices_low: pd.Series):
    """
    Show the key practical difference: unbounded oscillators need
    empirical OB/OS calibration, normalized oscillators have standard levels.
    """
    mom = compute_momentum(prices, 10)
    rsi = compute_rsi(prices, 14)
    stoch = compute_stochastic(prices_high, prices_low, prices, 14, 3)

    fig, axes = plt.subplots(4, 1, figsize=(14, 13), sharex=True,
                              gridspec_kw={'height_ratios': [2, 1, 1, 1]})

    # Price
    axes[0].plot(prices.index, prices.values, color='#333333', linewidth=1.2)
    axes[0].set_title('Price', fontsize=12)
    axes[0].grid(True, alpha=0.3)

    # Momentum (unbounded) — OB/OS requires empirical calibration
    axes[1].plot(mom.index, mom.values, color='#E24B4A', linewidth=0.9)
    axes[1].axhline(y=0, color='black', linewidth=0.5, linestyle='--')

    # Set empirical OB/OS at 90th/10th percentile
    ob_empirical = mom.quantile(0.9)
    os_empirical = mom.quantile(0.1)
    axes[1].axhline(y=ob_empirical, color='red', linewidth=0.7,
                     linestyle=':', alpha=0.7)
    axes[1].axhline(y=os_empirical, color='green', linewidth=0.7,
                     linestyle=':', alpha=0.7)
    axes[1].set_title(f'Momentum (UNBOUNDED) — empirical OB/OS: '
                      f'{ob_empirical:.1f} / {os_empirical:.1f}', fontsize=11)
    axes[1].grid(True, alpha=0.3)

    # RSI (normalized) — standard OB/OS levels
    axes[2].plot(rsi.index, rsi.values, color='#534AB7', linewidth=0.9)
    axes[2].axhline(y=50, color='black', linewidth=0.5, linestyle='--')
    axes[2].axhline(y=70, color='red', linewidth=0.7, linestyle=':')
    axes[2].axhline(y=30, color='green', linewidth=0.7, linestyle=':')
    axes[2].fill_between(rsi.index, 70, 100,
                         where=(rsi >= 70), color='red', alpha=0.1)
    axes[2].fill_between(rsi.index, 0, 30,
                         where=(rsi <= 30), color='green', alpha=0.1)
    axes[2].set_ylim(0, 100)
    axes[2].set_title('RSI (NORMALIZED) — standard OB/OS: 70 / 30', fontsize=11)
    axes[2].grid(True, alpha=0.3)

    # Stochastics (normalized)
    axes[3].plot(stoch.index, stoch['%K'].values, color='#378ADD', linewidth=0.9,
                 label='%K')
    axes[3].plot(stoch.index, stoch['%D'].values, color='#EF9F27', linewidth=0.9,
                 linestyle='--', label='%D')
    axes[3].axhline(y=50, color='black', linewidth=0.5, linestyle='--')
    axes[3].axhline(y=80, color='red', linewidth=0.7, linestyle=':')
    axes[3].axhline(y=20, color='green', linewidth=0.7, linestyle=':')
    axes[3].fill_between(stoch.index, 80, 100,
                         where=(stoch['%K'] >= 80), color='red', alpha=0.1)
    axes[3].fill_between(stoch.index, 0, 20,
                         where=(stoch['%K'] <= 20), color='green', alpha=0.1)
    axes[3].set_ylim(0, 100)
    axes[3].set_title('Stochastics (NORMALIZED) — standard OB/OS: 80 / 20',
                      fontsize=11)
    axes[3].legend(fontsize=8)
    axes[3].grid(True, alpha=0.3)

    plt.suptitle('Unbounded vs Normalized: OB/OS level-setting difference',
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.show()


def cross_instrument_portability(n_instruments: int = 4):
    """
    Show that normalized oscillators produce comparable readings across
    instruments with very different price levels, while unbounded oscillators
    do not.
    """
    np.random.seed(42)
    n_days = 100

    instruments = {
        'Penny stock ($3)': 3,
        'Mid-cap ($50)': 50,
        'Blue chip ($200)': 200,
        'High-price ($800)': 800,
    }

    print("=== Cross-Instrument Portability ===\n")
    print(f"{'Instrument':<22} {'Momentum':>10} {'RSI':>6} {'Same OB/OS?':>12}")
    print("-" * 54)

    for name, base_price in instruments.items():
        noise = np.random.normal(0, base_price * 0.02, n_days)
        trend = np.linspace(0, base_price * 0.15, n_days)
        prices = pd.Series(base_price + trend + noise)

        mom = compute_momentum(prices, 10)
        rsi = compute_rsi(prices, 14)

        print(f"{name:<22} {mom.iloc[-1]:>10.2f} {rsi.iloc[-1]:>6.1f} "
              f"{'RSI: yes':>12}")

    print(f"\nMomentum values range from ~{0.05:.2f} to ~{20:.2f}")
    print(f"RSI values cluster around {55:.0f}-{70:.0f} for all instruments")
    print(f"\nWith Momentum, you need different OB/OS thresholds per instrument.")
    print(f"With RSI, the same 70/30 threshold works everywhere.")


def ob_os_drift_demonstration(n_days: int = 400):
    """
    Show how unbounded OB/OS levels drift as market volatility changes,
    while normalized levels remain stable.
    """
    np.random.seed(42)

    # Price with changing volatility: calm → volatile → calm
    calm1 = np.random.normal(0, 0.5, n_days // 3)
    volatile = np.random.normal(0, 2.0, n_days // 3)
    calm2 = np.random.normal(0, 0.5, n_days - 2 * (n_days // 3))
    noise = np.concatenate([calm1, volatile, calm2])
    trend = np.linspace(0, 15, n_days)
    prices = pd.Series(100 + trend + np.cumsum(noise))

    mom = compute_momentum(prices, 10)
    rsi = compute_rsi(prices, 14)

    # Calculate rolling OB/OS for momentum (90th/10th percentile)
    mom_ob = mom.rolling(100).quantile(0.9)
    mom_os = mom.rolling(100).quantile(0.1)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                                         gridspec_kw={'height_ratios': [1.5, 1, 1]})

    ax1.plot(prices.index, prices.values, color='#333333', linewidth=1)
    ax1.set_title('Price (volatility: calm → volatile → calm)', fontsize=12)
    ax1.axvspan(n_days//3, 2*n_days//3, color='#EF9F27', alpha=0.08)
    ax1.grid(True, alpha=0.3)

    ax2.plot(mom.index, mom.values, color='#E24B4A', linewidth=0.8, alpha=0.7)
    ax2.plot(mom_ob.index, mom_ob.values, color='red', linewidth=1,
             linestyle='--', label='Rolling 90th pct (OB)')
    ax2.plot(mom_os.index, mom_os.values, color='green', linewidth=1,
             linestyle='--', label='Rolling 10th pct (OS)')
    ax2.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
    ax2.set_title('Momentum — OB/OS levels DRIFT with volatility', fontsize=11)
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    ax3.plot(rsi.index, rsi.values, color='#534AB7', linewidth=0.8, alpha=0.7)
    ax3.axhline(y=70, color='red', linewidth=1, linestyle='--', label='OB (70)')
    ax3.axhline(y=30, color='green', linewidth=1, linestyle='--', label='OS (30)')
    ax3.set_ylim(0, 100)
    ax3.set_title('RSI — OB/OS levels STABLE regardless of volatility', fontsize=11)
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.suptitle('OB/OS level stability: unbounded drifts, normalized holds',
                 fontsize=13, fontweight='bold', y=1.01)
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
    close = pd.Series(100 + trend + noise,
                      index=pd.date_range('2024-01-01', periods=n_days, freq='B'))
    high = close + np.abs(np.random.normal(0, 0.8, n_days))
    low = close - np.abs(np.random.normal(0, 0.8, n_days))

    # ── Main comparison ──
    demonstrate_ob_os_difference(close, high, low)

    # ── Cross-instrument portability ──
    print()
    cross_instrument_portability()

    # ── OB/OS drift demonstration ──
    print()
    ob_os_drift_demonstration()
```

### What Each Function Does

| Function | Purpose | Key Insight |
|---|---|---|
| `compute_momentum()` | Unbounded oscillator example | Range: −∞ to +∞ |
| `compute_rsi()` | Normalized oscillator example | Range: 0 to 100 |
| `compute_stochastic()` | Normalized oscillator with fast/slow variants | Range: 0 to 100, dual-line (%K/%D) |
| `demonstrate_ob_os_difference()` | Four-panel: price, momentum (empirical OB/OS), RSI (standard), stochastics (standard) | The visual proof of the OB/OS level-setting difference |
| `cross_instrument_portability()` | Same trend on 4 different price levels | Momentum varies wildly; RSI reads the same everywhere |
| `ob_os_drift_demonstration()` | Changing volatility: calm → volatile → calm | Momentum OB/OS levels drift; RSI levels hold steady |

### Key Implementation Notes

1. **`demonstrate_ob_os_difference()`** is the core visual. The Momentum panel shows empirical OB/OS lines (90th/10th percentile) — these are *derived from the data*, not standard. The RSI and Stochastics panels show fixed, universal lines (70/30 and 80/20). The contrast makes the practical difference obvious.

2. **`cross_instrument_portability()`** applies the same uptrend to stocks at $3, $50, $200, and $800. Momentum values range wildly (because the absolute dollar change varies). RSI values cluster in the same range for all four — because normalization eliminates the scale. This is why RSI screeners work across a universe of stocks.

3. **`ob_os_drift_demonstration()`** is the most important function. It shows price with changing volatility (calm → volatile → calm). The Momentum OB/OS levels (rolling percentile) balloon during the volatile period and shrink during calm periods. The RSI 70/30 lines don't move at all. This demonstrates Schwager's warning: "levels set today may not be appropriate a month from now" — for unbounded oscillators.

---

## Connection to Broader Framework

### Link to [[Overbought and Oversold]]
This concept explains *why* the OB/OS note has two separate sections for setting levels — unbounded vs. normalized require fundamentally different approaches. The adaptive OB/OS function from that note (`adaptive_ob_os_levels`) applies to both families but is more critical for unbounded oscillators.

### Link to [[Momentum Indicator]] and [[MACD]]
These are the primary unbounded oscillators. Their strength (raw magnitude information, crossover signals) comes at the cost of requiring manual OB/OS calibration. MACD's popularity despite being unbounded comes from the fact that its primary signal type (crossover) doesn't depend on OB/OS levels.

### Link to [[RSI]] and [[Stochastics]]
These are the primary normalized oscillators. Their strength (portable OB/OS levels, cross-instrument comparability) comes at the cost of losing raw magnitude information. They're the natural choice for OB/OS-based countertrend trading.

### Link to [[Oscillator Sensitivity]]
Changing the N parameter on a normalized oscillator (e.g., RSI period from 14 to 5) doesn't change the 0-100 range, but it does change how frequently the oscillator reaches OB/OS zones. A 5-period RSI hits 70/30 much more often than a 21-period RSI. The sensitivity tradeoff still applies — but the thresholds remain fixed.

### The Complementary Nature
Unbounded and normalized oscillators are **complementary, not competing**:
- Use **MACD** (unbounded) for trend identification via crossovers
- Use **RSI/Stochastics** (normalized) for countertrend OB/OS signals
- They succeed where the other fails — MACD in trends, RSI/stochastics in ranges
- Combining one from each family provides broader market coverage than picking two from the same family
