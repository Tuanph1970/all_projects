---
tags: [technical-analysis, schwager, chapter-7, confirmation, signal-filtering, whipsaw]
chapter: 7
concept: 2
title: "Confirmation Conditions"
related: [risk-control, false-signals, breakouts, trend-following, thrust-days]
---

# Confirmation Conditions

## Definition

Confirmation conditions are **additional criteria that must be met** before a chart signal is acted upon, rather than blindly following every technical signal. They serve as a quality gate to reduce false signals at the cost of slightly delayed entry on valid signals.

There is **no single "best" set of confirmation conditions** — the optimal choice varies by market and over time. The specific choice of confirmation rules is one of the **pivotal ways in which chart analysis is individualized**.

## Schwager's Exact Words

> *"Chart analysis can be made much more effective by requiring confirmation conditions for trade entry, rather than blindly following all technical signals."*  
> — Chapter 7, p.122

> *"There is no such thing as a best set of confirmation conditions. In any list of tested alternatives, the indicated best strategy will vary from market to market as well as over time."*  
> — Chapter 7, p.122

> *"The use of confirmation rules is one of the primary means of transforming classical chart concepts into a more powerful trading approach."*  
> — Chapter 7, p.123

> *"The increased use of technical analysis seems to have resulted in an increased frequency of false breakouts."*  
> — Chapter 4, p.58 (1998 observation strengthening the case for confirmation)

## Analogy — The CI/CD Pipeline

Think of confirmation conditions like **quality gates in a deployment pipeline**:

| Pipeline Stage | Trading Equivalent | What It Tests |
|---|---|---|
| Code commit | Raw breakout signal | Pattern detected |
| Unit tests | Time delay | Does signal persist after N days? |
| Integration tests | Min penetration | Has price moved enough beyond level? |
| Canary deployment | Thrust day confirmation | Is momentum continuing in the signal direction? |
| Production deploy | Confirmed trade entry | Signal validated, position taken |

Each gate slows down good deploys slightly but prevents shipping broken code. The tradeoff is identical.

## The Core Tradeoff

```
Less restrictive → More false signals → More whipsaw losses
                 → Better entry fills on valid signals

More restrictive → Fewer false signals → Fewer whipsaw losses
                 → Worse entry fills (delayed entry) on valid signals
```

**The confirmation condition is beneficial as long as reduced profits due to delayed entry are more than offset by avoided losses.**

## Three Methods

### 1. Time Delay

Wait N days after signal, then re-evaluate.

**Schwager's Ch7 rule:**
- Wait 3 days after signal
- Buy: enter if close > highest high since signal
- Sell: enter if close < lowest low since signal

**Eurodollar result:** Filtered out both false sell signals (March, May), only modestly delayed the winning buy entry.

**Ch14 example:** 6-day delay on N=12 cocoa breakout system eliminated 6 of 7 false signals.

### 2. Minimum Percent Penetration

Accept signal only if price penetrates breakout level by ≥ N%.

**Ch14 example:** 2% penetration requirement on N=12 cocoa breakout eliminated all 7 false signals.

### 3. Pattern (Thrust Days)

Require N thrust days in the signal direction after the breakout.

**Thrust day definition (from Ch5):**
- Up thrust: close > previous day's high
- Down thrust: close < previous day's low

**Ch14 example:** 3 thrust day requirement on N=12 cocoa breakout eliminated all 7 false signals.

## Comparison Table

| Attribute | Time Delay | Min Penetration | Thrust Days |
|-----------|-----------|-----------------|-------------|
| Parameter | N days | Min % | N thrust days |
| Measures | Persistence | Magnitude | Directional momentum |
| Entry delay | Fixed | Variable (price) | Variable (pattern) |
| Best for | Choppy markets | Volatile markets | Trending markets |
| SW analogy | `sleep()` + retry | Threshold check | Health check probe |

All three eliminated all 7 false signals in Schwager's Ch14 cocoa example. They can be combined for even stronger filtering.

## Filter vs. Confirmation (Ch14 Distinction)

| Type | When Applied | Example |
|------|-------------|---------|
| **Filter** | At time of signal receipt | "Only accept signals aligned with fundamental outlook" |
| **Confirmation** | After signal, during validation period | "Wait 3 days, check if signal still valid" |

A system can include **both**. Only signals that pass the filter AND are subsequently confirmed result in trades.

## Python Implementation

```python
import pandas as pd
import numpy as np


def apply_time_delay_confirmation(
    df: pd.DataFrame,
    signal_col: str = 'raw_signal',
    delay_days: int = 3,
    close_col: str = 'Close',
    high_col: str = 'High',
    low_col: str = 'Low'
) -> pd.DataFrame:
    """
    Schwager Ch7 confirmation: wait N days, then check
    if close is above/below the high/low since signal.

    Parameters
    ----------
    df : pd.DataFrame with OHLC + signal column
    delay_days : int, days to wait before confirming

    Returns
    -------
    DataFrame with 'confirmed_signal' column added
    """
    df = df.copy()
    df['confirmed_signal'] = 0

    pending = None

    for i in range(len(df)):
        raw = df[signal_col].iloc[i]

        if raw != 0 and pending is None:
            pending = {
                'dir': raw, 'idx': i,
                'hi': df[high_col].iloc[i],
                'lo': df[low_col].iloc[i]
            }
            continue

        if pending is not None:
            pending['hi'] = max(pending['hi'], df[high_col].iloc[i])
            pending['lo'] = min(pending['lo'], df[low_col].iloc[i])

            if i - pending['idx'] >= delay_days:
                c = df[close_col].iloc[i]
                if pending['dir'] == 1 and c > pending['hi']:
                    df.iloc[i, df.columns.get_loc('confirmed_signal')] = 1
                    pending = None
                elif pending['dir'] == -1 and c < pending['lo']:
                    df.iloc[i, df.columns.get_loc('confirmed_signal')] = -1
                    pending = None

            if raw != 0 and raw != pending.get('dir'):
                pending = {
                    'dir': raw, 'idx': i,
                    'hi': df[high_col].iloc[i],
                    'lo': df[low_col].iloc[i]
                }

    return df


def apply_penetration_confirmation(
    df: pd.DataFrame,
    signal_col: str = 'raw_signal',
    min_pct: float = 0.02,
    close_col: str = 'Close',
    level_col: str = 'breakout_level'
) -> pd.DataFrame:
    """
    Ch14 confirmation: accept only if close penetrates
    the breakout level by at least min_pct.
    """
    df = df.copy()
    df['confirmed_signal'] = 0

    for i in range(len(df)):
        sig = df[signal_col].iloc[i]
        if sig == 0:
            continue
        level = df[level_col].iloc[i]
        if pd.isna(level) or level == 0:
            continue
        pct = (df[close_col].iloc[i] - level) / level

        if sig == 1 and pct >= min_pct:
            df.iloc[i, df.columns.get_loc('confirmed_signal')] = 1
        elif sig == -1 and pct <= -min_pct:
            df.iloc[i, df.columns.get_loc('confirmed_signal')] = -1

    return df


def apply_thrust_day_confirmation(
    df: pd.DataFrame,
    signal_col: str = 'raw_signal',
    required_thrusts: int = 3,
    high_col: str = 'High',
    low_col: str = 'Low',
    close_col: str = 'Close'
) -> pd.DataFrame:
    """
    Ch14 confirmation: require N thrust days in signal
    direction after breakout.

    Thrust day: close > prev high (up) or close < prev low (down).
    """
    df = df.copy()
    df['confirmed_signal'] = 0

    pending_dir = None
    thrust_count = 0

    for i in range(1, len(df)):
        raw = df[signal_col].iloc[i]
        if raw != 0:
            pending_dir = raw
            thrust_count = 0
            continue

        if pending_dir is not None:
            c = df[close_col].iloc[i]
            prev_h = df[high_col].iloc[i-1]
            prev_l = df[low_col].iloc[i-1]

            if pending_dir == 1 and c > prev_h:
                thrust_count += 1
            elif pending_dir == -1 and c < prev_l:
                thrust_count += 1

            if thrust_count >= required_thrusts:
                df.iloc[i, df.columns.get_loc('confirmed_signal')] = pending_dir
                pending_dir = None
                thrust_count = 0

    return df


def confirmation_pipeline(
    df: pd.DataFrame,
    signal_col: str = 'raw_signal',
    delay_days: int = 3,
    min_penetration: float = 0.02,
    required_thrusts: int = 2
) -> pd.DataFrame:
    """
    Chain multiple confirmation methods into a pipeline.
    
    Applies time delay first, then thrust day confirmation
    on the surviving signals.
    """
    # Stage 1: Time delay
    stage1 = apply_time_delay_confirmation(
        df, signal_col=signal_col, delay_days=delay_days
    )
    
    # Stage 2: Thrust days on confirmed signals
    stage2 = apply_thrust_day_confirmation(
        stage1, signal_col='confirmed_signal',
        required_thrusts=required_thrusts
    )
    stage2.rename(
        columns={'confirmed_signal': 'pipeline_signal'}, inplace=True
    )
    
    return stage2
```

## When This Concept Works Best

- **Breakout trading** with frequent whipsaws
- **Choppy / range-bound markets** with high false signal rate
- **Systematic/algorithmic trading** — confirmation rules are easily codified and backtested
- **Markets with increased TA participation** — Schwager notes false breakouts have become more common since technical analysis went mainstream (Ch4, p.58)
- **Bridging discretionary and systematic approaches** — the easiest Ch7 concept to automate

## When It Doesn't Work

- **Fast gap-and-go breakouts** — any delay means you miss the move entirely
- **Very tight ranges** where confirmation eats most of the potential profit
- **Over-optimization** — fitting confirmation rules too precisely to historical data creates brittle systems
- Schwager explicitly notes: *"one could also construct examples in which the use of confirmation conditions is detrimental"*

## The Individualization Insight

This is central to Schwager's defense of chart analysis as an art. Two traders looking at the same chart can use different confirmation rules and get different results — neither is wrong. This **irreducible subjectivity** is precisely what prevents chart analysis from being arbitraged away by widespread knowledge of patterns.

## Cross-References Across the Book

| Location | What It Says |
|----------|-------------|
| Ch 4, p.58 | Breakout confirmation methods + false breakouts increasing |
| Ch 5 | Thrust days defined (used as confirmation pattern) |
| Ch 7, p.122-123 | Core statement + Eurodollar example |
| Ch 14, p.240-243 | Three detailed examples with cocoa (penetration, time delay, pattern) |
| Ch 14, p.244-245 | Filter vs. confirmation distinction |
| Ch 14, Table 14.2 | Problem #2 (Whipsaws) → Solution: confirmation conditions |

## Links

### Inside This Chapter
- [[Ch7 - Is Chart Analysis Still Valid (MOC)]]
- [[Ch7 - Risk Control and Win Rate vs Profitability]] — Confirmation improves win/loss ratio
- [[Ch7 - Multi-Timeframe Analysis]] — Weekly context acts as macro-level filter
- [[Ch7 - Fundamental-Technical Synthesis]] — Fundamentals as directional filter (applied before confirmation)
- [[Ch7 - Using Failed Signals as Trading Indicators]] — What happens when confirmed signals still fail

### Inside the Book
- [[Ch4 - Trading Ranges and Support and Resistance]] — Breakout confirmation at trading range boundaries
- [[Ch5 - Chart Patterns]] — Thrust days (the building block for pattern confirmation)
- [[Ch6 - Oscillators]] — Overbought/oversold as additional confirmation input
- Chapter 14 — Confirmation Conditions (detailed systematic treatment with figures)
- Chapter 14, Table 14.2 — Problem #2 (Whipsaws) and solution
