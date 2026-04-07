# Trading Range Breakout

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

A **trading range breakout** occurs when price escapes the horizontal corridor of a [[Trading Range]], signaling an impending move in the breakout direction. Breakouts are the primary way technical traders capitalize on the energy stored during consolidation periods.

However, **not all breakouts are real**. Many are [[False Breakout (Stop Run)|false breakouts]] where price briefly escapes and then falls back. Schwager identifies **three factors** that enhance breakout reliability:

1. **Duration** — How long the range lasted
2. **Narrowness** — How tight the price corridor was
3. **Confirmation** — Whether the breakout is sustained

---

## How to Detect

### The Three Reliability Factors

#### 1. Duration (Time = Stored Energy)

The longer a trading range persists, the more significant the eventual breakout.

- **Why it works**: During a range, institutional investors may be slowly accumulating (buying) or distributing (selling) without moving price. The longer this lasts, the more "potential energy" builds up. When price finally escapes, the backlog of orders drives a violent move.
- **Practical rule**: A breakout from a 3-month range is generally more trustworthy than one from a 3-day range.

#### 2. Narrowness (Tight Range = Low Risk)

Breakouts from narrow (tight) ranges tend to be more reliable and more attractive trades.

- **Why it works**: Markets cycle between low and high volatility. A narrow range represents volatility compression. Historically, low volatility periods are followed by explosive moves.
- **Risk/reward advantage**: If the range is narrow, the stop-loss (placed back inside the range) is close to entry. This means low dollar risk per trade and a favorable reward-to-risk ratio.
- **Visual cue**: Look for converging lower highs and higher lows within the range (the range "tightens" before breaking).

#### 3. Confirmation (Proof the Breakout Is Real)

Wait for evidence that the breakout is sustained before entering.

- **Why it matters**: Stop orders cluster just beyond range boundaries. A slight penetration triggers a cascade of stops, temporarily pushing price further in the breakout direction. Once those orders are filled, price often falls back unless real buying/selling sustains it.
- **Confirmation methods**:
  - **Time filter**: Price stays beyond the range for N days (e.g., 3–5 consecutive closes beyond the boundary).
  - **Percent filter**: Price penetrates the boundary by a minimum percentage (e.g., 2–3%).
  - **Thrust days**: Strong candles with firm closes beyond the range.
  - **Combined**: Both time AND percent conditions are met.
- **The trade-off**: Confirmation means worse entry prices on valid signals, but avoids many [[False Breakout (Stop Run)|false breakouts]]. Schwager argues this trade-off is worth it.

---

## Analogy

### The Rubber Band in a Shoebox

| Element | Analogy |
|---------|---------|
| **Trading Range** | A rubber band stuck inside a shoebox |
| **Duration** | How long you hold the rubber band under tension — 5 minutes vs. 5 days |
| **Narrowness** | How tight the box is — a matchbox vs. a moving box |
| **False Breakout** | The lid lifts a crack, people rush in, but it slams shut |
| **Confirmation** | The rubber band sitting on top of the box for several days |

**Duration**: The longer you stretch a rubber band and hold it, the more energy stores up. When released, it flies further.

**Narrowness**: A tiny matchbox makes it obvious when the band escapes (it only needs to move an inch). A giant box makes it ambiguous — the band might travel 6 inches and still be inside.

**Confirmation**: Don't bet the band has escaped just because the lid lifts a crack. Wait until the band is clearly sitting on top of the box for several days. You miss the first inch of movement, but you avoid the trap of the lid slamming shut.

---

## Use Case / Example

### Figure 4.7 — Copper Futures: Duration Example

**Setup**: Copper traded between ~55 and ~70 for nearly **3 years** (1984–1987).

**Breakout**: In early 1987, price broke above 70.

**Result**: Price rocketed from ~70 to ~140 in a short time.

**Lesson**: Three years of consolidation = massive stored energy. The long duration made this breakout extremely significant.

### Figure 4.9 — British Pound: Narrowness Example

**Setup**: The chart shows **two narrow ranges** during an uptrend (a "stair-step" pattern):
- Box 1: ~157.5 to ~161 (March–April)
- Box 2: ~165 to ~167.5 (May)

**Breakout**: Each narrow range broke upward, continuing the trend.

**Lesson**: You don't need multi-year ranges. Short, tight pauses offer reliable breakouts with very tight stop-losses and low risk.

### Figure 4.8 — Soybean Meal: Combined Example

**Setup**: 10-month range between ~180 and ~195 (Aug 1992–May 1993).

**Breakout**: In June/July 1993, price smashed through 195.

**Result**: Sharp rally from ~195 to ~235.

**Lesson**: Even at "only" 10 months, the range was long enough to build significant pressure. The breakout was powerful.

---

## Python Code

```python
import pandas as pd
import numpy as np


def detect_confirmed_breakout(df, lookback=20, confirm_days=5, confirm_pct=0.02):
    """
    Detect trading range breakouts with confirmation.

    Parameters:
        lookback: Period to define range boundaries (Donchian Channel)
        confirm_days: Min consecutive days price must stay outside range
        confirm_pct: Min % penetration beyond boundary (alternative confirmation)

    Returns:
        DataFrame with 'signal_buy' and 'signal_sell' boolean columns
    """
    df = df.copy()

    # 1. Define the trading range boundaries (Donchian Channel)
    df['range_high'] = df['High'].rolling(window=lookback).max()
    df['range_low'] = df['Low'].rolling(window=lookback).min()

    # 2. Detect initial breakout
    df['breakout_up'] = df['Close'] > df['range_high'].shift(1)
    df['breakout_down'] = df['Close'] < df['range_low'].shift(1)

    # 3. Time confirmation: count consecutive days outside the range
    df['up_streak'] = 0
    df['down_streak'] = 0

    for i in range(1, len(df)):
        if df['breakout_up'].iloc[i]:
            df.iloc[i, df.columns.get_loc('up_streak')] = df['up_streak'].iloc[i-1] + 1
        else:
            df.iloc[i, df.columns.get_loc('up_streak')] = 0

        if df['breakout_down'].iloc[i]:
            df.iloc[i, df.columns.get_loc('down_streak')] = df['down_streak'].iloc[i-1] + 1
        else:
            df.iloc[i, df.columns.get_loc('down_streak')] = 0

    # 4. Percentage confirmation
    df['pct_above'] = (df['Close'] - df['range_high'].shift(1)) / df['range_high'].shift(1)
    df['pct_below'] = (df['range_low'].shift(1) - df['Close']) / df['range_low'].shift(1)

    # 5. Generate confirmed signals (time OR percent)
    df['signal_buy'] = (df['up_streak'] >= confirm_days) | (df['pct_above'] >= confirm_pct)
    df['signal_sell'] = (df['down_streak'] >= confirm_days) | (df['pct_below'] >= confirm_pct)

    # Only trigger on the first day of confirmation
    df['signal_buy'] = df['signal_buy'] & ~df['signal_buy'].shift(1).fillna(False)
    df['signal_sell'] = df['signal_sell'] & ~df['signal_sell'].shift(1).fillna(False)

    return df


def measure_range_quality(df, lookback=20):
    """
    Measure Duration and Narrowness of the current range.
    Helps assess breakout reliability.

    Returns columns:
        range_duration: Days the range has persisted
        range_width_pct: Width of range as % of price (narrowness)
    """
    df = df.copy()
    df['range_high'] = df['High'].rolling(window=lookback).max()
    df['range_low'] = df['Low'].rolling(window=lookback).min()

    # Narrowness: width as percentage of price
    df['range_width_pct'] = (df['range_high'] - df['range_low']) / df['Close'] * 100

    # Duration: count consecutive days the range boundaries haven't expanded
    df['range_stable'] = (
        (df['range_high'] == df['range_high'].shift(1)) &
        (df['range_low'] == df['range_low'].shift(1))
    )
    df['range_duration'] = 0
    for i in range(1, len(df)):
        if df['range_stable'].iloc[i]:
            df.iloc[i, df.columns.get_loc('range_duration')] = (
                df['range_duration'].iloc[i-1] + 1
            )
        else:
            df.iloc[i, df.columns.get_loc('range_duration')] = 0

    return df
```

### Usage

```python
import yfinance as yf

df = yf.download("AAPL", period="2y")
result = detect_confirmed_breakout(df, lookback=20, confirm_days=5, confirm_pct=0.03)

buys = result[result['signal_buy']]
sells = result[result['signal_sell']]
print(f"Confirmed Buy signals: {len(buys)}")
print(f"Confirmed Sell signals: {len(sells)}")
```

---

## Reflexivity Warning

Schwager notes (writing in 1998) that the increased popularity of technical analysis led to **more frequent false breakouts**. Because many traders watch the same levels:

- Large players (market makers, institutions) know where retail stop orders cluster.
- They may intentionally push price beyond the boundary to trigger stops and capture liquidity.
- The more obvious a pattern, the higher the risk it is a [[False Breakout (Stop Run)|trap]].

This is consistent with the reflexivity argument explored in [[Chapter 11 - Failed Signals]].

---

## Related Concepts
- [[Trading Range]]
- [[False Breakout (Stop Run)]]
- [[Support and Resistance]]
- [[Role Reversal Principle]]

---

## Tags
#technical-analysis #schwager #breakout #confirmation #duration #narrowness
