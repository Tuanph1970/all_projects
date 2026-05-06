# Reversal Days

> Part of: [[Chapter_05_Chart_Patterns]] → One-Day Patterns

## Definition

**Standard definition**: A reversal high day is a bar that prints a new high in an uptrend, then closes *below* the prior day's close. A reversal low day is the mirror image: a new low in a downtrend that closes *above* the prior day's close.

Schwager argues this standard is too weak — far too many false signals. He proposes a stronger rule:

> **Stronger reversal high day**: new high, then closes *below the prior day's low* (and optionally below the low of the prior two days).

The stronger rule misses some real tops but cuts out most of the noise.

## Illustration

![[reversal_days_illustration.svg]]

## Analogy — The Marathon Runner Who Suddenly Trips

Imagine a runner who's been leading a race for ten miles. She crosses the next mile-marker still in front — a new "high" for her position. But by the time the next checkpoint reads out, she's not just behind her recent pace — she's behind where she was *yesterday at the same checkpoint*.

The standard reversal day is like noticing she fell *a little* behind yesterday's pace. That happens often and rarely means much.

The stronger version is "she's fallen behind even her *worst* time from yesterday's leg." That's a real change — something gave way.

## Numeric Example

A stock in an uptrend:

| Day | High | Low | Close |
|---|---|---|---|
| T−1 | 75.20 | 74.50 | **75.00** |
| **T (reversal high)** | **76.40** | 73.80 | 74.10 |

- New high (76.40 > 75.20) ✓
- Close (74.10) below prior close (75.00) → **standard** reversal day ✓
- Close (74.10) below prior low (74.50) → **stronger** reversal day ✓ — significant signal

## Python Code

```python
import pandas as pd

def reversal_high_days(df: pd.DataFrame, strong: bool = True) -> pd.Series:
    """
    Detect reversal high days.

    strong=False : standard definition (close < prior close)
    strong=True  : Schwager's restrictive definition (close < prior low)
    """
    new_high = df["high"] > df["high"].shift(1)
    if strong:
        condition_close = df["close"] < df["low"].shift(1)
    else:
        condition_close = df["close"] < df["close"].shift(1)
    return new_high & condition_close


def reversal_low_days(df: pd.DataFrame, strong: bool = True) -> pd.Series:
    new_low = df["low"] < df["low"].shift(1)
    if strong:
        condition_close = df["close"] > df["high"].shift(1)
    else:
        condition_close = df["close"] > df["close"].shift(1)
    return new_low & condition_close


def reversal_and_spike(df: pd.DataFrame) -> pd.Series:
    """
    The most significant case: bar is BOTH a reversal day AND a spike day.
    Far rarer; far higher conviction.
    """
    from_spikes = __import__("spikes_module")        # see Spikes.md
    return reversal_high_days(df, strong=False) & from_spikes.detect_spike_highs(df)
```

## Relationships

### Within Chapter 5

- **Versus [[Spikes]]**: distinct concepts — a spike is about *how the bar sticks out* from neighbors; a reversal day is about *closing through* the prior bar. Their intersection is the strongest signal.
- **Versus [[Thrust Days]]**: an upthrust day is a *bullish* close above prior high, a reversal high day is a *bearish* close below prior close (or low). They are opposing single-bar signals at trend extremes.
- **Component of [[V Tops and Bottoms]]**: reversal days frequently mark the apex of a V.

### Outside Chapter 5

- **[[Chapter 03 - Trends]]** — the *interpretive context* (uptrend or downtrend?) determines whether the bar is meaningful at all.
- **[[Chapter 11 - The Most Important Rule]]** — a reversal day that gets quickly negated (price closes back above the new high within a few days) becomes a "failed reversal" and signals continuation.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — when a reversal high day forms, place a stop just above its high; if violated, the signal failed.

### When does this concept work well?

- **Best**: stronger definition + occurs after a long, mature trend + bar is also a [[Spikes|spike]] or [[Wide-Ranging Days|wide-ranging day]].
- **Worst**: standard definition alone in choppy markets — produces too many false signals to act on mechanically.

#chart-patterns #one-day-pattern #reversal-days
