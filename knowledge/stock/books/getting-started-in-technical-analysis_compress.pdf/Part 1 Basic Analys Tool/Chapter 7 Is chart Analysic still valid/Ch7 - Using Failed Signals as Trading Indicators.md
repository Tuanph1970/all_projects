---
tags: [technical-analysis, schwager, chapter-7, chapter-11, failed-signals, bull-trap, bear-trap, contrarian]
chapter: 7
concept: 5
title: "Using Failed Signals as Trading Indicators"
related: [risk-control, confirmation-conditions, breakouts, chart-patterns]
---

# Using Failed Signals as Trading Indicators

## Definition

When a market **fails to follow through** in the direction of a key chart signal, this failure is **among the most reliable of all chart signals**, strongly suggesting a significant move in the **opposite direction**. Schwager considers this so important he devoted all of Chapter 11 — titled "The Most Important Rule in Chart Analysis" — to it.

The mechanical explanation: price pushes above resistance, triggering stops. After stops clear, **no new buying appears**. The market rose just enough to activate orders but couldn't sustain the move. This absence of follow-through reveals the underlying picture is far weaker than the breakout suggested.

## Schwager's Exact Words

> *"A failed signal is among the most reliable of all chart signals."*  
> — Chapter 11, p.152

> *"In my experience, this type of counter-to-anticipated price action is among the most reliable indicators of major tops and bottoms."*  
> — Chapter 11, p.153 (on bull/bear traps)

> *"I find failed signals considerably more reliable than conventional chart patterns."*  
> — Chapter 11, p.176

> *"A failed signal is more reliable than the original signal. Go the other way."*  
> — Chapter 17, Rule 76

> *"It takes great discipline to capitalize on failed signals, but such flexibility is essential to the effective synthesis of chart analysis and trading."*  
> — Chapter 11, p.177

## Analogy — The Canary Release That Crashes

A canary release pushes a change to 5% of traffic. If the canary crashes immediately, that's not just "the canary failed" — it's **strong evidence of a fundamental bug** that would have destroyed the full deployment.

A breakout is the market's canary release. Price "deploys" above the range. If it immediately crashes back, there was **no genuine demand above that level**. The stops fired but no real buyers showed up. That absence of follow-through is the strongest sell signal you'll get — stronger than any pattern that initiated the original position.

## The Three Levels of Trader Response (Ch11 Conclusion)

| Level | Trader | Response to Failed Signal | Typical Result |
|-------|--------|--------------------------|----------------|
| 1 | **Novice** | Ignores it, holds position, hopes for recovery | Large loss (-$8) |
| 2 | **Experienced** | Exits quickly once failure is apparent | Small loss (-$2), missed opportunity |
| 3 | **Truly Skilled** | Does a 180° turn — reverses position at a loss | Loss on original + profit on reversal (net +$4) |

The $12 swing between novice and skilled comes entirely from **how you respond to failure** — not from the initial market call.

## The Eight Types of Failed Signals (Ch11 Taxonomy)

### 1. Bull and Bear Traps
Major breakouts immediately followed by sharp reversals. **Most reliable** type per Schwager.

**Confirmation conditions:**
- **Initial price:** Retrace to median of the pre-breakout consolidation
- **Strong price:** Retrace to far boundary of the range (lower for bull trap, upper for bear trap)
- **Time:** Market fails to return to breakout extreme within ~4 weeks

**Invalidation:** Bull trap cancelled if price returns to breakout high. Bear trap cancelled if price returns to breakout low.

### 2. False Trend Line Breakouts
Schwager: "False trend breakout signals are **considerably more reliable** than conventional trend breakout signals." Confirmed by N closes back on the original side of the trend line.

### 3. Filled Gaps
Gaps normally indicate trend continuation. When a gap gets filled, the original gap becomes a failed signal. Significance enhanced if: gap was wide, gap was a breakaway gap, or multiple consecutive gaps are filled.

### 4. Return to Spike Extremes
Spikes mark reversals. When price returns to a prior spike extreme, the spike is negated. More significant if: the spike was extreme in magnitude, and if weeks/months have elapsed since the original spike.

### 5. Return to Wide-Ranging Day Extremes
Close beyond the opposite extreme of a significant wide-ranging day = that day's signal has failed.

### 6. Counter-to-Anticipated Flag/Pennant Breakout
Flags/pennants are expected to resolve in the direction of the preceding trend. When they break the "wrong" way, it's a high-reliability reversal signal.

### 7. Penetration of Top/Bottom Formations
Double tops that get broken upward, H&S patterns whose neckline holds — these failed reversal patterns signal powerful continuation.

### 8. Breaking of Curvature
Rounding patterns that get broken in the direction opposite to the curve pathway.

## The Meta-Argument: Why Failed Signals Stay Reliable

Schwager's most intellectually fascinating argument:

```
Breakouts become popular (1980s-90s)
    → More traders use them
        → More false breakouts occur (efficiency degrades)
            → More failed signals available
                → Failed signals become MORE reliable
                    → But failed signals are NOT yet popular
                        → Edge preserved
```

> *"There is an inverse relationship between the popularity of an indicator and its efficiency."*

**The dynamic principle:** The concept can be "made dynamic by pegging it to the conventional wisdom." Whatever pattern is currently popular, its failure is more significant than the pattern itself. If a new pattern becomes the next breakout, the failure of that pattern becomes the new high-reliability signal.

> *"In this more general sense, the concept of failed signals could prove timeless."*

## Real-World Example: The Crude Oil Reversal (Ch12, Trades 12.12-12.13)

Schwager's most dramatic demonstration:

1. **Trade 12.12:** Goes SHORT crude oil at the bottom of a trading range. Reasoning: pennant + downside gap (perfectly logical bearish setup).
2. **The failure:** Crude rebounds to the top of the range. The pennant low looks like a bear trap. Original premise completely violated.
3. **Trade 12.13 (the next day!):** Reverses to LONG. Reasoning: confirmed bear trap + wide-ranging up day near the low.
4. **Result:** Started by going short at the virtual market bottom, reversed, and captured a large rally.

Schwager's commentary: *"Flexibility in recognizing a trade was wrong and reversing (not merely liquidating) the original position made it possible to capture a large gain in a trade sequence that began by going short at the virtual market bottom!"*

**Key lesson:** *"The ability to decisively respond to the market's constantly changing price action is a far more important attribute than skill in making market calls."*

## Connection to Concept 4 (Fundamental-Technical Synthesis)

Ch17 Rule 77 provides a fundamental version of failed signals: *"The failure of a market to follow through on significant bullish or bearish news is often a harbinger of an imminent trend reversal."*

When fundamentals say "up" (great earnings report) and the chart fails to respond, that fundamental-chart disagreement IS a failed signal — applied to news rather than chart patterns.

## Python Implementation

```python
import pandas as pd
import numpy as np
from typing import Literal


def detect_bull_trap(
    df: pd.DataFrame,
    lookback: int = 20,
    confirmation: Literal['initial', 'strong', 'time'] = 'initial',
    high_col: str = 'High',
    low_col: str = 'Low',
    close_col: str = 'Close'
) -> pd.DataFrame:
    """
    Detect bull traps with Schwager's three confirmation levels.

    Parameters
    ----------
    confirmation : str
        'initial' = retrace to median of range
        'strong'  = retrace to far (low) boundary
        'time'    = fail to return to high within 20 days
    """
    df = df.copy()
    df['bull_trap'] = 0
    df['trap_entry'] = np.nan

    range_high = df[high_col].rolling(lookback).max().shift(1)
    range_low = df[low_col].rolling(lookback).min().shift(1)
    range_mid = (range_high + range_low) / 2

    breakout_idx = None
    breakout_high = None

    for i in range(lookback, len(df)):
        if df[close_col].iloc[i] > range_high.iloc[i] and breakout_idx is None:
            breakout_idx = i
            breakout_high = df[high_col].iloc[i]
            continue

        if breakout_idx is not None:
            if df[high_col].iloc[i] > breakout_high * 1.02:
                breakout_idx = None
                continue

            confirmed = False
            if confirmation == 'initial':
                confirmed = df[close_col].iloc[i] < range_mid.iloc[breakout_idx]
            elif confirmation == 'strong':
                confirmed = df[close_col].iloc[i] < range_low.iloc[breakout_idx]
            elif confirmation == 'time':
                confirmed = (i - breakout_idx >= 20 and
                             df[close_col].iloc[i] < breakout_high)

            if confirmed:
                df.iloc[i, df.columns.get_loc('bull_trap')] = 1
                df.iloc[i, df.columns.get_loc('trap_entry')] = df[close_col].iloc[i]
                breakout_idx = None

    return df


def detect_bear_trap(
    df: pd.DataFrame,
    lookback: int = 20,
    confirmation: Literal['initial', 'strong', 'time'] = 'initial',
    high_col: str = 'High',
    low_col: str = 'Low',
    close_col: str = 'Close'
) -> pd.DataFrame:
    """Detect bear traps. Mirror logic of bull trap detection."""
    df = df.copy()
    df['bear_trap'] = 0
    df['trap_entry'] = np.nan

    range_high = df[high_col].rolling(lookback).max().shift(1)
    range_low = df[low_col].rolling(lookback).min().shift(1)
    range_mid = (range_high + range_low) / 2

    breakout_idx = None
    breakout_low = None

    for i in range(lookback, len(df)):
        if df[close_col].iloc[i] < range_low.iloc[i] and breakout_idx is None:
            breakout_idx = i
            breakout_low = df[low_col].iloc[i]
            continue

        if breakout_idx is not None:
            if df[low_col].iloc[i] < breakout_low * 0.98:
                breakout_idx = None
                continue

            confirmed = False
            if confirmation == 'initial':
                confirmed = df[close_col].iloc[i] > range_mid.iloc[breakout_idx]
            elif confirmation == 'strong':
                confirmed = df[close_col].iloc[i] > range_high.iloc[breakout_idx]
            elif confirmation == 'time':
                confirmed = (i - breakout_idx >= 20 and
                             df[close_col].iloc[i] > breakout_low)

            if confirmed:
                df.iloc[i, df.columns.get_loc('bear_trap')] = 1
                df.iloc[i, df.columns.get_loc('trap_entry')] = df[close_col].iloc[i]
                breakout_idx = None

    return df


def detect_counter_flag_breakout(
    df: pd.DataFrame,
    trend_col: str = 'trend',
    flag_high_col: str = 'flag_high',
    flag_low_col: str = 'flag_low',
    close_col: str = 'Close'
) -> pd.DataFrame:
    """
    Detect counter-to-anticipated flag/pennant breakouts.
    
    If trend is up and flag breaks down (or vice versa),
    that's a failed signal = strong reversal indicator.
    """
    df = df.copy()
    df['counter_flag'] = 0

    for i in range(len(df)):
        trend = df[trend_col].iloc[i]
        fh = df[flag_high_col].iloc[i]
        fl = df[flag_low_col].iloc[i]
        c = df[close_col].iloc[i]

        if pd.isna(fh) or pd.isna(fl):
            continue

        # Uptrend + downside flag breakout = bearish failed signal
        if trend == 1 and c < fl:
            df.iloc[i, df.columns.get_loc('counter_flag')] = -1
        # Downtrend + upside flag breakout = bullish failed signal
        elif trend == -1 and c > fh:
            df.iloc[i, df.columns.get_loc('counter_flag')] = 1

    return df


def trader_response_hierarchy(
    failure_detected: bool,
    current_position: int,
    skill_level: Literal['novice', 'experienced', 'skilled'] = 'skilled'
) -> dict:
    """
    Schwager's three-level hierarchy of trader response.
    """
    if not failure_detected:
        return {'action': 'hold', 'position': current_position,
                'reasoning': 'Signal still valid'}

    responses = {
        'novice': {
            'action': 'hold_and_hope',
            'position': current_position,
            'reasoning': 'Ignoring failure, hoping for recovery (BAD)'
        },
        'experienced': {
            'action': 'exit',
            'position': 0,
            'reasoning': 'Recognized failure, exited to flat'
        },
        'skilled': {
            'action': 'reverse',
            'position': -current_position,
            'reasoning': 'Failed signal = strong opposite signal, reversed'
        }
    }
    return responses.get(skill_level, responses['experienced'])
```

## When This Concept Works Best

- **Breakout-heavy environments** where false breakouts are common
- **Markets with heavy stop-hunting** — algorithms/floor traders push price to trigger stops
- **Reversal trading** — failed signals are the highest-confidence reversal indicators
- **After a confirmed signal from Concept 2** still fails — a "confirmed failure" is even more significant
- **When other layers (fundamentals, weekly chart) align** — a failed signal that agrees with the broader context is extremely reliable

## When It Doesn't Work

- **Genuine breakouts with shallow pullbacks** — not every retracement after a breakout is a failure. Schwager's confirmation conditions exist precisely to distinguish genuine failures from normal pullbacks.
- **Requires very fast reaction** — the skilled trader must reverse immediately, which is psychologically devastating (you're admitting you were wrong AND betting the other way)
- **"Failed failed signals"** — Schwager acknowledges these exist (Ch11, p.164). A spike penetration that reverses back can negate the failed signal. Need clear invalidation rules.
- **If the concept becomes widely popular** — its reliability could degrade (Schwager warns of this but notes the dynamic principle preserves the meta-concept)

## Cross-References Across the Book

| Location | What It Says |
|----------|-------------|
| Ch 7, p.124 | Concept 5 introduction: "crucial item of information often overlooked by novice chartists" |
| Ch 11, p.152-177 | Full chapter: 8 types, confirmation conditions, real examples, future reliability |
| Ch 12, Trades 12.5-12.13 | Real-world examples using failed signals in actual trading decisions |
| Ch 12, Trade 12.12-13 | Crude oil: short at bottom → reverse → capture rally |
| Ch 12, Trade 12.8 | Gold: confirmed bull trap top → short → profit |
| Ch 17, Rule 9 | "Don't fade recent price failure patterns when implementing trades" |
| Ch 17, Rule 76 | "A failed signal is more reliable than the original signal. Go the other way." |
| Ch 17, Rule 77 | Market failing on bullish/bearish news = fundamental version of failed signal |
| Ch 17, Rules 56-58,62 | Specific failed pattern rules (trap formations, flag breakouts) |

## Links

### Inside This Chapter
- [[Ch7 - Is Chart Analysis Still Valid (MOC)]]
- [[Ch7 - Risk Control and Win Rate vs Profitability]] — Accepting the loss on the failed trade requires rigorous risk control
- [[Ch7 - Confirmation Conditions]] — Confirmation filters reduce false signals, but some confirmed signals still fail. Those failures are even more significant.
- [[Ch7 - Multi-Timeframe Analysis]] — Weekly context adds conviction to the failed signal interpretation
- [[Ch7 - Fundamental-Technical Synthesis]] — Rule 77: market failing on news = fundamental version of this concept

### Inside the Book
- [[Ch3 - Trends]] — Trend lines prone to false breakouts (Type 2 failed signals)
- [[Ch4 - Trading Ranges and Support and Resistance]] — Breakouts from ranges that fail = bull/bear traps
- [[Ch5 - Chart Patterns]] — All pattern types (gaps, spikes, flags, WRDs) that can "fail"
- Chapter 9 — Stop placement: the failed breakout high/low becomes the stop for the reverse trade
- Chapter 11 — **"The Most Important Rule in Chart Analysis"** (full chapter treatment)
- Chapter 12 — Real-World Chart Analysis (multiple examples demonstrating this concept)
