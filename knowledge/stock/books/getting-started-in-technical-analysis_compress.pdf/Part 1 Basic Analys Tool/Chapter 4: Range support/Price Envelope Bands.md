# Price Envelope Bands

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

**Price Envelope Bands** are dynamic [[Support and Resistance|support and resistance]] levels derived from a moving average. Unlike static horizontal lines drawn at [[Prior Major Highs and Lows|prior highs/lows]] or [[Concentrations of Relative Highs and Lows|cluster zones]], envelope bands **move with the price**, providing adaptive overbought/oversold boundaries.

### Construction

- **Middle Line**: A Moving Average (e.g., 20-day SMA)
- **Upper Band**: Moving Average + (Moving Average × Percentage)
- **Lower Band**: Moving Average − (Moving Average × Percentage)

**Example**: If the 20-day MA = 100 and the percentage = 2.5%:
- Upper Band = 100 + 2.5% = **102.50** (resistance / overbought)
- Lower Band = 100 − 2.5% = **97.50** (support / oversold)

### Bollinger Bands

**Bollinger Bands** are a well-known variant of price envelope bands. Instead of adding/subtracting a fixed percentage, they add/subtract a **standard deviation** calculation from the moving average.

| Feature | Price Envelope | Bollinger Bands |
|---------|---------------|-----------------|
| **Band width** | Fixed percentage (e.g., ±2.5%) | Standard deviation (adapts to volatility) |
| **Behavior** | Constant width relative to MA | Expands when volatility is high, contracts when low |
| **Use case** | Simpler, consistent boundaries | Responsive to market conditions |

### Schwager's Assessment

Schwager is candid about the limitations: the price envelope provides a **reasonably good** indication of when the market may be nearing a turning point, but it is **"not as effective a tool as it might appear to be."** During extended trends, prices can continue to hug one band without reversing — the envelope repeatedly suggests the market is overbought/oversold while price keeps trending.

---

## How to Detect

### What the Bands Tell You

| Price Position | Signal | Interpretation |
|----------------|--------|----------------|
| Price touches/exceeds **Upper Band** | Overbought | Market may be stretched too far above average — potential resistance |
| Price touches/exceeds **Lower Band** | Oversold | Market may be stretched too far below average — potential support |
| Price bounces **between** bands | Ranging | Bands are working as expected — mean reversion is likely |
| Price **hugs** one band | Trending | Bands are failing — strong trend is overriding the mean-reversion signal |

### Choosing Parameters

| Parameter | Description | Tuning Guidance |
|-----------|-------------|-----------------|
| **MA Period** | Length of the moving average | Longer = smoother but more lagging. Typical: 20 days |
| **Envelope %** | Width of the bands | Higher = wider bands, fewer signals. Must be tuned per asset |

**Rules of thumb for envelope percentage:**

| Asset Class | Typical Envelope % | Rationale |
|------------|-------------------|-----------|
| Stocks | 2.0–3.0% | Moderate volatility |
| Forex | 1.0–1.5% | Low volatility |
| Commodities | 2.5–4.0% | Higher volatility |
| Crypto | 5.0–10.0% | Very high volatility |
| Intraday (90-min bars) | 1.0–1.5% | Shorter timeframe = tighter bands |

### The Selection Criterion

Choose the percentage so that the envelope **encompasses most of the price activity**, with:
- The upper boundary approximately coinciding with relative highs.
- The lower boundary approximately coinciding with relative lows.

If price constantly breaks the bands, the percentage is too tight. If price never reaches the bands, the percentage is too wide.

---

## Analogy

### The Rubber Leash

Imagine a dog (price) attached to its owner (the moving average) by a rubber leash (the envelope band).

| Element | Analogy |
|---------|---------|
| **The owner** | The moving average — walks at a steady pace in the general direction |
| **The dog** | The price — runs ahead, falls behind, but stays tethered |
| **The leash** | The envelope bands — stretches but pulls the dog back toward the owner |
| **Upper band** | The dog running too far ahead (overbought) — the leash pulls it back |
| **Lower band** | The dog falling too far behind (oversold) — the leash pulls it forward |
| **Strong trend** | The dog sees a squirrel and drags the owner along — the leash stretches but the dog keeps pulling (price hugs the band) |

**In a range**: The dog runs forward, the leash pulls it back. It falls behind, the leash pulls it forward. Mean reversion works.

**In a trend**: The dog sees a squirrel and keeps running. The leash is fully stretched (overbought), but the dog doesn't come back — it just drags the owner (moving average) along with it. Selling because the leash is stretched would be a mistake.

---

## Use Case / Example

### Figure 4.29 — March 1995 T-Bond (Daily Chart)

**Parameters**: 20-day moving average with 2.5% envelope bands.

**What the chart shows**:

**Ranging period (middle of chart)**: Price bounces cleanly between the upper and lower bands. It touches the top band → falls. Touches the bottom band → rises. This is the ideal scenario where the envelope works as advertised.

**Downtrend (left side)**: Price "hugs" the lower band for an extended period. The envelope keeps saying "oversold," but price keeps sliding lower. A trader who bought every time price hit the lower band would have lost money.

**Uptrend (right side)**: Price "hugs" the upper band. The envelope keeps saying "overbought," but price keeps climbing. A trader who sold every time price hit the upper band would have missed a major rally.

**The Lesson**: Envelope bands are a useful tool for gauging **potential** turning points, but they must be combined with other analysis. In trending markets, they generate repeated false signals.

### Figure 4.30 — March 1995 T-Bond (90-Minute Bars)

Same market as Fig 4.29, but using intraday data with a smaller envelope (1.2%). Demonstrates that the concept scales across timeframes — you just need to adjust the percentage.

---

## Python Code

```python
import pandas as pd
import numpy as np


def calculate_price_envelope(df, ma_period=20, envelope_pct=2.5, price_col='Close'):
    """
    Calculate Price Envelope Bands.

    Parameters:
        ma_period: Moving average period (default 20)
        envelope_pct: Percentage for the envelope (default 2.5%)
        price_col: Column to use for calculation

    Returns:
        DataFrame with 'MA', 'Upper_Band', 'Lower_Band', 'Position' columns
    """
    df = df.copy()

    # Moving Average
    df['MA'] = df[price_col].rolling(window=ma_period).mean()

    # Envelope Bands
    df['Upper_Band'] = df['MA'] * (1 + envelope_pct / 100)
    df['Lower_Band'] = df['MA'] * (1 - envelope_pct / 100)

    # Position relative to bands
    df['Pct_From_MA'] = (df[price_col] - df['MA']) / df['MA'] * 100

    conditions = [
        df[price_col] >= df['Upper_Band'],
        df[price_col] <= df['Lower_Band']
    ]
    choices = ['OVERBOUGHT', 'OVERSOLD']
    df['Position'] = np.select(conditions, choices, default='NEUTRAL')

    return df


def calculate_bollinger_bands(df, ma_period=20, num_std=2.0, price_col='Close'):
    """
    Calculate Bollinger Bands (standard deviation variant of envelope bands).

    Parameters:
        ma_period: Moving average period (default 20)
        num_std: Number of standard deviations (default 2.0)
        price_col: Column to use for calculation

    Returns:
        DataFrame with 'BB_MA', 'BB_Upper', 'BB_Lower', 'BB_Width' columns
    """
    df = df.copy()

    df['BB_MA'] = df[price_col].rolling(window=ma_period).mean()
    df['BB_Std'] = df[price_col].rolling(window=ma_period).std()

    df['BB_Upper'] = df['BB_MA'] + (df['BB_Std'] * num_std)
    df['BB_Lower'] = df['BB_MA'] - (df['BB_Std'] * num_std)

    # Bandwidth: indicates volatility (narrow = squeeze, wide = expansion)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_MA'] * 100

    return df


def envelope_signals(df, ma_period=20, envelope_pct=2.5):
    """
    Generate trading signals from envelope bands.

    Note Schwager's warning: these work well in ranges but fail in trends.
    Always combine with trend detection (e.g., ADX) before acting on signals.
    """
    df = calculate_price_envelope(df, ma_period, envelope_pct)

    # Signal: price crosses from outside to inside (potential reversal)
    df['prev_position'] = df['Position'].shift(1)

    # Buy signal: was oversold, now returning to neutral
    df['envelope_buy'] = (df['prev_position'] == 'OVERSOLD') & (df['Position'] == 'NEUTRAL')

    # Sell signal: was overbought, now returning to neutral
    df['envelope_sell'] = (df['prev_position'] == 'OVERBOUGHT') & (df['Position'] == 'NEUTRAL')

    return df
```

### Usage

```python
import yfinance as yf
import matplotlib.pyplot as plt

df = yf.download("AAPL", period="1y")

# Price Envelope
df = calculate_price_envelope(df, ma_period=20, envelope_pct=2.5)

# Plot
fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(df.index, df['Close'], label='Close', color='black', linewidth=1.5)
ax.plot(df.index, df['MA'], label='20-Day MA', color='blue', linewidth=1.5)
ax.plot(df.index, df['Upper_Band'], label='Upper Band (+2.5%)', color='red', linestyle='--')
ax.plot(df.index, df['Lower_Band'], label='Lower Band (-2.5%)', color='green', linestyle='--')
ax.fill_between(df.index, df['Upper_Band'], df['Lower_Band'], alpha=0.08, color='gray')
ax.legend()
ax.set_title('Price Envelope Bands')
plt.show()

# Current status
latest = df.dropna().iloc[-1]
print(f"Price: ${latest['Close']:.2f}")
print(f"MA:    ${latest['MA']:.2f}")
print(f"Upper: ${latest['Upper_Band']:.2f}")
print(f"Lower: ${latest['Lower_Band']:.2f}")
print(f"Status: {latest['Position']}")
```

---

## Comparison: Static vs. Dynamic S/R

| Feature | Static S/R (Prior Highs/Lows, Clusters) | Dynamic S/R (Envelope Bands) |
|---------|----------------------------------------|------------------------------|
| **Movement** | Fixed horizontal lines | Moves with price |
| **Based on** | Historical price peaks/valleys | Moving average + percentage |
| **Best use** | Long-term S/R identification | Short-term overbought/oversold |
| **Weakness** | Can be permanently broken | Fails during extended trends |
| **Timeframe** | Weeks to years | Days to weeks |

---

## Critical Limitation

> *"During extended trends prices can continue to hug one end of the price envelope."* — Schwager

**The trap**: The envelope says "overbought" → you sell → price keeps climbing and you lose money.

**The solution**: Combine envelope bands with:
- [[Trading Range]] detection (ADX < 25) to confirm you are in a ranging market.
- [[Prior Major Highs and Lows]] and [[Concentrations of Relative Highs and Lows|cluster zones]] for additional confirmation.
- Trend-following indicators to avoid fighting a strong trend.

**Rule of thumb**: Envelope bands work best when the market is in a confirmed [[Trading Range]]. If ADX > 25 (trending), ignore the bands.

---

## Related Concepts
- [[Support and Resistance]]
- [[Trading Range]]
- [[Concentrations of Relative Highs and Lows]]
- [[Prior Major Highs and Lows]]

---

## Tags
#technical-analysis #schwager #envelope-bands #bollinger-bands #overbought #oversold #moving-average #dynamic-support-resistance
