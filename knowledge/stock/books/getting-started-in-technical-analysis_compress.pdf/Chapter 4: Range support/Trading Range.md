# Trading Range

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

A **trading range** is a horizontal price corridor that contains price fluctuations over an extended period. Price moves sideways — bouncing between an upper boundary ([[Support and Resistance|resistance]]) and a lower boundary ([[Support and Resistance|support]]) — without establishing a sustained uptrend or downtrend.

**Key characteristics:**
- **Horizontal**: Price direction is flat (low slope), not trending up or down.
- **Extended duration**: Ranges persist for weeks, months, or even years.
- **Range-bound**: Price oscillates between identifiable upper and lower boundaries.
- **Pattern-neutral**: Most chart patterns (gaps, flags, pennants) are relatively meaningless when they occur inside a trading range.

Schwager emphasizes that markets spend **most of their time** in trading ranges. Unfortunately, they are very difficult to trade profitably. His blunt advice: most technical traders should **minimize participation** in range-bound markets.

---

## How to Detect

### Visual Detection
1. Look for a period where price moves sideways with no consistent higher highs or lower lows.
2. Draw horizontal lines at the highest highs and lowest lows of the period.
3. If price has bounced between these boundaries multiple times over at least 1–2 months, a trading range is established.

### Quantitative Detection
Combine two indicators:
- **ADX (Average Directional Index)**: Measures trend strength (not direction). ADX below 20–25 indicates a non-trending, ranging market.
- **Linear Regression Slope**: A rolling slope near zero confirms the price corridor is horizontal, not angled.

### The Detection Problem
- **In hindsight**: Ranges are easy to identify after they have occurred.
- **In real-time**: They are "nearly impossible to predict." What looks like a range might become a trend, and vice versa.
- **Lookback dependency**: Any algorithmic detection requires a lookback period (5, 10, 30 days), and there is no single "correct" number.

---

## Analogy

### The Tennis Ball in a Hallway

Imagine a tennis ball bouncing back and forth inside a narrow hallway.

| Element | Analogy |
|---------|---------|
| **Price** | The tennis ball |
| **Trading Range** | The hallway itself |
| **Upper Boundary (Resistance)** | The right wall |
| **Lower Boundary (Support)** | The left wall |
| **Breakout** | The ball smashing through one of the walls |

For most of the time, the ball just bounces harmlessly between the walls. Trying to bet on which wall it hits next is chaotic and dangerous. The smart strategy is to **wait outside the hallway** for the ball to break through a wall — that is when the real move happens.

---

## Use Case / Example

### Figure 4.7 — Copper Nearest Futures (1983–1988)

**The Setup:** From mid-1984 to early 1987, copper traded in a horizontal range between approximately 55 and 70. For nearly **three years**, the market went nowhere.

**The Trap:** Traders trying to buy and sell inside this range would have been whipsawed repeatedly. Each rally to 70 was met with selling, each dip to 55 was met with buying, but no sustained move developed.

**The Resolution:** In early 1987, copper finally broke above 70 (the upper boundary). The price then skyrocketed from ~70 to ~140 in a short time.

**The Lesson:** The three years of consolidation built up enormous "potential energy." When the range finally broke, the resulting move was violent and highly profitable — but only for traders who waited for the breakout rather than trying to trade the bounces inside the range.

### Figure 4.2 — Dow Jones Industrial Average

A multi-year trading range in the Dow preceded the historic bull market of the 1980s and 1990s, demonstrating that even major indices can be trapped in ranges for years before a breakout triggers a massive trend.

---

## Python Code

```python
import pandas as pd
import numpy as np


def calculate_adx(df, period=14):
    """
    Calculate Average Directional Index (ADX) to measure trend strength.
    ADX < 25 typically indicates a ranging market.
    """
    high = df['High']
    low = df['Low']
    close = df['Close']

    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

    # Smoothed averages (Wilder's smoothing)
    atr = pd.Series(tr).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, min_periods=period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, min_periods=period).mean() / atr

    # DX and ADX
    dx = 100 * np.abs(plus_di - minus_di) / (np.abs(plus_di + minus_di))
    adx = dx.ewm(alpha=1/period, min_periods=period).mean()
    return adx


def calculate_rolling_slope(df, price_col='Close', window=20):
    """
    Calculate the slope of a linear regression over a rolling window.
    Slope near 0 indicates horizontal movement.
    """
    slopes = [np.nan] * (window - 1)
    prices = df[price_col].values
    x = np.arange(window)

    for i in range(window - 1, len(prices)):
        y = prices[i - window + 1: i + 1]
        if np.any(np.isnan(y)):
            slopes.append(np.nan)
        else:
            m, _ = np.polyfit(x, y, 1)
            slopes.append(m)
    return pd.Series(slopes, index=df.index)


def detect_trading_range(df, adx_thresh=25, slope_thresh=0.05, min_duration=10):
    """
    Identify trading ranges using ADX + Slope.
    
    Parameters:
        adx_thresh: ADX below this = no trend (default 25)
        slope_thresh: Normalized slope below this = horizontal (default 0.05)
        min_duration: Minimum consecutive days to qualify as a range
    
    Returns:
        DataFrame with 'Is_Range' boolean column
    """
    df = df.copy()
    df['ADX'] = calculate_adx(df)
    df['Slope'] = calculate_rolling_slope(df, window=20)
    df['Slope_Pct'] = df['Slope'] / df['Close']

    # Conditions
    cond_adx = df['ADX'] < adx_thresh
    cond_slope = np.abs(df['Slope_Pct']) < slope_thresh
    df['Range_Signal'] = (cond_adx & cond_slope).astype(int)

    # Filter by minimum duration
    df['Group'] = (df['Range_Signal'] != df['Range_Signal'].shift()).cumsum()
    group_counts = df.groupby('Group')['Range_Signal'].transform('sum')
    df['Is_Range'] = (df['Range_Signal'] == 1) & (group_counts >= min_duration)

    return df
```

### Usage

```python
import yfinance as yf

df = yf.download("AAPL", period="2y")
result = detect_trading_range(df, adx_thresh=25, slope_thresh=0.0005, min_duration=10)

range_pct = result['Is_Range'].sum() / len(result) * 100
print(f"Time in trading range: {range_pct:.1f}%")
```

### Important Caveats
- **Lagging**: Detects ranges after they have established, not before.
- **Parameter sensitivity**: `adx_thresh` and `slope_thresh` must be tuned per asset class.
- **Schwager's advice**: If the detection requires too much parameter tweaking to look "clean," the ambiguity itself is a signal to stay in cash.

---

## Practical Trading Rules

1. **Minimize participation**: Don't try to trade the bounces inside the range.
2. **Switch strategies**: If you must trade, use oscillator-based approaches (RSI, Stochastic) — but know they will be disastrous when the trend starts.
3. **Strict stop-losses**: If fading minor trends within a range, liquidate if price penetrates the range boundary by a specified amount or stays beyond for a minimum number of days.
4. **Wait for the breakout**: The real money is made when price escapes the range. See [[Trading Range Breakout]].

---

## Related Concepts
- [[Trading Range Breakout]]
- [[Support and Resistance]]
- [[False Breakout (Stop Run)]]
- [[Price Envelope Bands]]

---

## Tags
#technical-analysis #schwager #trading-range #sideways-market #ADX
