# False Breakout (Stop Run)

> *Part of: [[Chapter 4 - Trading Ranges and Support and Resistance MOC]]*

---

## Definition

A **false breakout** (also called a **stop run** or **whipsaw**) occurs when price briefly escapes a [[Trading Range]] boundary, triggers a cluster of stop orders, and then immediately reverses back into the range. Traders who entered on the breakout are "trapped" with losing positions.

Schwager identifies false breakouts as one of the most common pitfalls in technical trading. He notes that the increased popularity of technical analysis (as of 1998) has led to an **increased frequency** of false breakouts — a reflexivity concern where the widespread use of a technique undermines its own effectiveness.

In [[Chapter 11 - Failed Signals]], Schwager develops this into a broader principle: **failed signals are often more reliable than the original signals they negate**. A failed upside breakout (bull trap) becomes a strong sell signal; a failed downside breakout (bear trap) becomes a strong buy signal.

---

## How to Detect

### The Mechanism (Stop-Order Cascade)

1. **Stop clusters form**: Many traders place buy-stop orders just above resistance (or sell-stops just below support). These are "if price reaches X, enter my trade" orders.
2. **Price probes the boundary**: A small move beyond the range triggers the nearest stop orders.
3. **Cascade effect**: The triggered orders push price further, triggering more stops in a chain reaction.
4. **Exhaustion**: Once all the clustered stops are filled, there is no remaining demand/supply to sustain the move.
5. **Reversal**: Price falls back into the range. Traders who bought the breakout are now trapped.

### How to Avoid False Breakouts

Use [[Trading Range Breakout|confirmation conditions]]:

| Method | Description | Example |
|--------|-------------|---------|
| **Time filter** | Wait N days for price to stay outside | 3–5 consecutive closes beyond boundary |
| **Percent filter** | Require minimum penetration | 2–3% beyond the boundary |
| **Thrust days** | Look for strong closes with conviction | Wide-range day closing near its extreme |
| **Combined** | Both time AND percent | 3 closes beyond + 2% penetration |

### Visual Warning Signs of a False Breakout

- Price barely exceeds the range boundary (thin penetration).
- Volume spikes on the breakout day but immediately dries up.
- Price forms a long wick/shadow back into the range on the breakout candle.
- The breakout occurs on a single day with no follow-through.

---

## Analogy

### The Mousetrap

Imagine a mouse (your trading capital) trying to escape through a hole in the wall (the range boundary).

| Element | Analogy |
|---------|---------|
| **The range** | A room where the mouse is trapped |
| **The hole in the wall** | The apparent breakout point |
| **The cheese** | The profit you think you'll make |
| **The trap** | The stop-order cascade that snaps back |

The cheese (apparent breakout) lures the mouse through the hole. But just past the hole, there is a mousetrap. The mouse reaches for the cheese, the trap snaps, and the mouse is pulled back inside — worse off than before.

**The smart mouse** waits. It watches another mouse go through the hole first. If that mouse makes it safely to the other side and **stays there for several days**, then it is safe to follow.

### Alternative Analogy: The Revolving Door

Think of a revolving door at a building entrance. You push through the door (breakout), but the door keeps spinning and pushes you right back inside (false breakout). You only truly "escaped" the building if you push through the door, walk 10 steps away, and **stay outside**.

---

## Use Case / Example

### The Stop-Run Mechanism in Action

**Scenario**: A stock has traded between $95 and $105 for 3 months. Many traders have placed buy-stop orders at $105.50, $106, and $106.50 (just above resistance).

**Day 1 (The Trigger)**: Price rallies to $105.20. The first batch of stops at $105.50 triggers. Their buying pushes price to $106. More stops trigger. Price hits $106.80.

**Day 2 (The Exhaustion)**: All the stop orders are now filled. There are no more automatic buyers above $106.80. Without fundamental demand, price drifts back to $105.

**Day 3 (The Trap)**: Price falls back to $103. Every trader who bought at $105.50–$106.80 is now losing money. Many panic-sell, driving price even lower.

**Result**: Price ends up at $100 — right in the middle of the range. The "breakout" was an illusion created by clustered stop orders.

### How Confirmation Would Have Saved You

- **Time filter (5 days)**: On Day 2, price fell back inside. Signal rejected. No trade entered.
- **Percent filter (3%)**: $105 × 1.03 = $108.15. Price only reached $106.80. Signal rejected.
- **Outcome**: You avoided the trap entirely.

---

## Python Code

```python
import pandas as pd
import numpy as np


def detect_false_breakouts(df, lookback=20, max_outside_days=3, return_threshold=0.02):
    """
    Detect false breakouts: price breaks the range but returns within N days.

    Parameters:
        lookback: Period to define range boundaries
        max_outside_days: If price returns within this many days, it's a false breakout
        return_threshold: Price must return this % inside range to confirm "false"

    Returns:
        DataFrame with 'false_breakout_up' and 'false_breakout_down' columns
    """
    df = df.copy()

    # Define range boundaries
    df['range_high'] = df['High'].rolling(window=lookback).max().shift(1)
    df['range_low'] = df['Low'].rolling(window=lookback).min().shift(1)

    df['false_breakout_up'] = False
    df['false_breakout_down'] = False

    for i in range(max_outside_days, len(df)):
        # Check for upside false breakout
        # Did price break above range_high within the last N days?
        recent_slice = df.iloc[i - max_outside_days:i + 1]
        broke_above = (recent_slice['High'] > recent_slice['range_high']).any()
        now_inside = df['Close'].iloc[i] < df['range_high'].iloc[i]

        if broke_above and now_inside:
            pct_return = (df['range_high'].iloc[i] - df['Close'].iloc[i]) / df['range_high'].iloc[i]
            if pct_return >= return_threshold:
                df.iloc[i, df.columns.get_loc('false_breakout_up')] = True

        # Check for downside false breakout
        broke_below = (recent_slice['Low'] < recent_slice['range_low']).any()
        now_above = df['Close'].iloc[i] > df['range_low'].iloc[i]

        if broke_below and now_above:
            pct_return = (df['Close'].iloc[i] - df['range_low'].iloc[i]) / df['range_low'].iloc[i]
            if pct_return >= return_threshold:
                df.iloc[i, df.columns.get_loc('false_breakout_down')] = True

    return df
```

### Usage

```python
import yfinance as yf

df = yf.download("AAPL", period="1y")
result = detect_false_breakouts(df, lookback=20, max_outside_days=3)

false_ups = result['false_breakout_up'].sum()
false_downs = result['false_breakout_down'].sum()
print(f"False upside breakouts detected: {false_ups}")
print(f"False downside breakouts detected: {false_downs}")
```

### Trading the Failed Signal

Per Schwager's [[Chapter 11 - Failed Signals]] thesis, a false breakout can itself be a **high-probability trading signal in the opposite direction**:

```python
# After detecting a false upside breakout → consider shorting
# After detecting a false downside breakout → consider buying
# The stop-loss goes at the extreme of the false breakout
```

---

## Key Principles

1. **The more obvious the level, the more likely the trap**: If every trader can see the range boundary, large players will exploit it.
2. **Confirmation is your shield**: Never trade a breakout without waiting for proof (time, percent, or both).
3. **Failed signals are tradeable**: A false breakout in one direction often becomes the most reliable signal in the opposite direction.
4. **Reflexivity**: As more traders use technical analysis, false breakouts become more frequent because the same levels attract both retail stops and institutional exploitation.

---

## Related Concepts
- [[Trading Range Breakout]]
- [[Trading Range]]
- [[Support and Resistance]]
- [[Chapter 11 - Failed Signals]]

---

## Tags
#technical-analysis #schwager #false-breakout #stop-run #bull-trap #bear-trap #reflexivity
