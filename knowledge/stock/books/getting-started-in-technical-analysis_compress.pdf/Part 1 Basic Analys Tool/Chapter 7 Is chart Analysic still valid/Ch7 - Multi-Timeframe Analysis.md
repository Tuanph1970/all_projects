---
tags: [technical-analysis, schwager, chapter-7, multi-timeframe, context, weekly-chart, art]
chapter: 7
concept: 3
title: "Multi-Timeframe Analysis (Putting Chart Patterns in Context)"
related: [confirmation-conditions, trend-analysis, chart-art, signal-filtering]
---

# Multi-Timeframe Analysis (Putting Chart Patterns in Context)

## Definition

Chart analysis is **more than recognizing individual patterns in isolation**. The successful chart trader synthesizes multiple components of the overall picture by examining patterns across different timeframes. A pattern on a daily chart takes on completely different meaning when viewed against the backdrop of the weekly or monthly chart.

This concept is the **centerpiece** of Schwager's "chart analysis is an art" argument.

## Schwager's Exact Words

> *"Chart analysis is more than just the recognition and interpretation of individual patterns. One of the earmarks of the successful chart trader is an ability to synthesize the various components of the overall picture."*  
> — Chapter 7, p.123

> *"The skill and subjectivity implied in this approach place chart analysis in the realm of an art that cannot be mimicked by merely following a set of textbook rules. This is a crucial point in understanding how the chartist approach can remain valid despite widespread publicity."*  
> — Chapter 7, p.124

> *"Never go counter to your own opinion of the long-term trend of the market. In other words, don't try to dance between the raindrops."*  
> — Chapter 17, Rule 41

> *"Periodically review long-term charts (e.g., every two to four weeks)."*  
> — Chapter 17, Rule 79

## Analogy — The Git Log vs. The Commit Diff

Looking at a single daily chart pattern is like reading one `git diff` without context:

| Git Concept | Trading Equivalent |
|---|---|
| `git diff HEAD~1` | Today's daily chart pattern |
| `git log --oneline -20` | Weekly chart (recent history) |
| `git log --all --graph` | Monthly chart (full project history) |
| A revert in today's diff | A daily sell signal |
| ...but the log shows a 6-month refactor | ...but the weekly chart shows a strong uptrend |
| **Interpretation:** noise, not a real reversal | **Interpretation:** false signal, reject the sell |

The zoom level determines the interpretation.

## Schwager's Eurodollar Example (Figures 7.1-7.4)

### Step 1: Daily Chart View (Narrow Context)

The naive trader sees a **trading range** on the daily September 1992 Eurodollar chart. They treat upside and downside breakouts **equivalently** — no directional bias.

Result: They take the March sell signal (loss), the May sell signal (loss), and the buy signal (big win). Net: modest profit with unnecessary losses.

### Step 2: Weekly Chart View (Broad Context)

The experienced trader examines the **long-term weekly continuous futures chart** and sees:
- A **flag pattern** near the **top of a five-year trading range**
- This is an **extremely bullish** long-term picture

### Step 3: The Synthesis

With weekly context:
- **Sell signals on the daily chart should be rejected** (they contradict the bullish weekly picture)
- **Buy signals should be traded more aggressively** than a neutral trading range would warrant
- The false March sell signal could have been **avoided entirely**

### The Decision Matrix

| Weekly Bias | Daily Buy Signal | Daily Sell Signal | Position Sizing |
|-------------|-----------------|------------------|-----------------|
| **Bullish** | ACCEPT aggressively | REJECT or reduce | Larger on buys |
| **Bearish** | REJECT or reduce | ACCEPT aggressively | Larger on sells |
| **Neutral** | Accept normally | Accept normally | Standard size |

## The River Current Metaphor

Think of the weekly chart as the **direction of a river's current**. The daily chart shows the ripples and eddies on the surface.

- **Daily signal aligned with weekly trend** = catching an eddy that launches you downstream faster
- **Daily signal against weekly trend** = paddling upstream — you might make progress briefly, but the current usually wins

## Worked Example: Tech Stock XYZ

### Setup
- Weekly chart: 12-month uptrend, higher highs and higher lows → **BULLISH bias**
- Daily chart: 5 breakout signals over 2 months

### Results

| Signal | Direction | Weekly Alignment | Naive Action | Context Action | Outcome |
|--------|-----------|-----------------|-------------|----------------|---------|
| #1 | SELL | Against weekly | Take trade | **REJECT** | -$3.50 |
| #2 | BUY | With weekly | Take trade | **ACCEPT** | +$6.00 |
| #3 | SELL | Against weekly | Take trade | **REJECT** | -$2.80 |
| #4 | BUY | With weekly | Take trade | **ACCEPT** | +$12.00 |
| #5 | SELL | Against weekly | Take trade | **REJECT** | -$4.00 |

### Bottom Line

| Approach | Trades | Winners | Losers | Net P&L |
|----------|--------|---------|--------|---------|
| Naive (all signals) | 5 | 2 | 3 | +$7.70 |
| With weekly context | 2 | 2 | 0 | +$18.00 |

All three sell signals — which contradicted the weekly uptrend — were losers. By simply filtering against the weekly bias, we eliminated all losing trades and more than doubled net profit.

## How Multi-Timeframe Fits in the Signal Pipeline

```
Weekly chart → Determines directional bias (broadest filter)
    ↓
Fundamentals → Additional directional confirmation (Concept 4)
    ↓
Daily signal → Pattern detected (Concept 2 raw signal)
    ↓
Confirmation → Time delay / penetration / thrust days (Concept 2)
    ↓
Trade entry or → If signal fails → Use as reversal signal (Concept 5)
    ↓
Risk control → Stop placement + let winners run (Concept 1)
```

Multi-timeframe is the first and broadest filter — applied before confirmation conditions.

## Python Implementation

```python
import pandas as pd
import numpy as np
from typing import Literal


def determine_weekly_bias(
    weekly_df: pd.DataFrame,
    lookback_weeks: int = 52,
    close_col: str = 'Close',
    high_col: str = 'High',
    low_col: str = 'Low'
) -> dict:
    """
    Determine directional bias from weekly chart.
    
    Uses position within long-term range + recent trend
    direction to classify bias as bullish, bearish, or neutral.
    
    Parameters
    ----------
    weekly_df : pd.DataFrame
        Weekly OHLC data
    lookback_weeks : int
        Number of weeks to define the range
    
    Returns
    -------
    dict with bias, position_in_range, and quarter_change
    """
    if len(weekly_df) < lookback_weeks:
        return {'bias': 'neutral', 'position_in_range': 0.5, 'quarter_change': 0}
    
    recent = weekly_df.tail(lookback_weeks)
    range_high = recent[high_col].max()
    range_low = recent[low_col].min()
    range_size = range_high - range_low
    
    if range_size == 0:
        return {'bias': 'neutral', 'position_in_range': 0.5, 'quarter_change': 0}
    
    current = weekly_df[close_col].iloc[-1]
    position = (current - range_low) / range_size
    
    # Recent trend (13 weeks = ~1 quarter)
    quarter = weekly_df.tail(min(13, len(weekly_df)))
    q_change = (quarter[close_col].iloc[-1] - quarter[close_col].iloc[0]) / quarter[close_col].iloc[0]
    
    if position > 0.67 and q_change > 0.02:
        bias = 'bullish'
    elif position < 0.33 and q_change < -0.02:
        bias = 'bearish'
    else:
        bias = 'neutral'
    
    return {
        'bias': bias,
        'position_in_range': round(position, 3),
        'quarter_change': round(q_change, 4)
    }


def filter_daily_signals_by_weekly(
    daily_df: pd.DataFrame,
    weekly_bias: str,
    signal_col: str = 'signal'
) -> pd.DataFrame:
    """
    Filter daily trading signals based on weekly bias.
    
    Bullish bias: only accept buy signals (1)
    Bearish bias: only accept sell signals (-1)
    Neutral: accept both
    
    Parameters
    ----------
    daily_df : pd.DataFrame
        Daily data with signal column (1=buy, -1=sell, 0=none)
    weekly_bias : str
        'bullish', 'bearish', or 'neutral'
    
    Returns
    -------
    pd.DataFrame with 'filtered_signal' column
    """
    df = daily_df.copy()
    df['filtered_signal'] = df[signal_col].copy()
    df['filter_reason'] = ''
    
    if weekly_bias == 'bullish':
        mask = df['filtered_signal'] == -1
        df.loc[mask, 'filtered_signal'] = 0
        df.loc[mask, 'filter_reason'] = 'Rejected: sell vs bullish weekly'
    elif weekly_bias == 'bearish':
        mask = df['filtered_signal'] == 1
        df.loc[mask, 'filtered_signal'] = 0
        df.loc[mask, 'filter_reason'] = 'Rejected: buy vs bearish weekly'
    
    return df


def multi_timeframe_backtest(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    signal_col: str = 'signal',
    pnl_col: str = 'trade_pnl',
    lookback_weeks: int = 52
) -> dict:
    """
    Compare naive (all signals) vs multi-timeframe filtered trading.
    
    Parameters
    ----------
    daily_df : pd.DataFrame
        Daily data with signal and P&L columns
    weekly_df : pd.DataFrame
        Weekly OHLC for bias determination
    
    Returns
    -------
    dict with naive_stats, filtered_stats, and improvement metrics
    """
    # Determine weekly bias
    wb = determine_weekly_bias(weekly_df, lookback_weeks)
    
    # Naive: trade all signals
    naive_trades = daily_df[daily_df[signal_col] != 0]
    naive_pnl = naive_trades[pnl_col].sum()
    naive_wins = (naive_trades[pnl_col] > 0).sum()
    naive_n = len(naive_trades)
    
    # Filtered: only aligned signals
    filtered = filter_daily_signals_by_weekly(daily_df, wb['bias'], signal_col)
    filt_trades = filtered[filtered['filtered_signal'] != 0]
    filt_pnl = daily_df.loc[filt_trades.index, pnl_col].sum()
    filt_wins = (daily_df.loc[filt_trades.index, pnl_col] > 0).sum()
    filt_n = len(filt_trades)
    
    # Rejected signals analysis
    rejected = filtered[filtered['filter_reason'] != '']
    rejected_pnl = daily_df.loc[rejected.index, pnl_col].sum()
    
    return {
        'weekly_bias': wb,
        'naive': {
            'trades': naive_n,
            'wins': naive_wins,
            'win_rate': round(naive_wins / naive_n, 3) if naive_n > 0 else 0,
            'net_pnl': round(naive_pnl, 2)
        },
        'filtered': {
            'trades': filt_n,
            'wins': filt_wins,
            'win_rate': round(filt_wins / filt_n, 3) if filt_n > 0 else 0,
            'net_pnl': round(filt_pnl, 2)
        },
        'rejected_signals': len(rejected),
        'rejected_pnl': round(rejected_pnl, 2),
        'pnl_improvement': round(filt_pnl - naive_pnl, 2)
    }
```

## When This Concept Works Best

- **Any trend-following approach** — the weekly chart tells you the "wind direction"
- **Breakout trading from trading ranges** — daily breakout direction should align with weekly bias
- **Avoiding false signals** — most false breakouts occur against the larger trend
- **Position sizing decisions** — trade larger when daily and weekly agree, smaller otherwise
- **Combining with confirmation conditions** — multi-timeframe filter first, then confirm surviving signals

## When It Doesn't Work

- **Major trend reversals** — the weekly bias lags; it tells you the old direction when the market is actually turning. The weekly chart is always late at tops and bottoms.
- **Pure mean-reversion strategies** — these intentionally trade against the larger trend
- **Very short-term trading** — daily chart may be too slow to serve as the "macro" view
- **Ambiguous weekly charts** — when the weekly picture is unclear, the filter adds no value

## Why This Makes Chart Analysis an Art

The key judgment calls that require skill, not rules:
1. **How do you determine weekly bias?** Is it "near the top of a 5-year range" (bullish flag) or "forming a double top" (bearish)?
2. **When does the bias change?** No formula tells you when to switch from bullish to neutral.
3. **Which timeframe pair to use?** Daily/weekly? Weekly/monthly? Hourly/daily?

Two experienced traders can look at the same weekly chart and reach opposite conclusions. This irreducible subjectivity is exactly Schwager's point — it's what prevents chart analysis from being arbitraged away.

## Links

### Inside This Chapter
- [[Ch7 - Is Chart Analysis Still Valid (MOC)]]
- [[Ch7 - Confirmation Conditions]] — Multi-timeframe acts as broadest filter; confirmation refines further
- [[Ch7 - Fundamental-Technical Synthesis]] — Fundamentals add another directional layer
- [[Ch7 - Risk Control and Win Rate vs Profitability]] — Filtering by context improves win rate
- [[Ch7 - Using Failed Signals as Trading Indicators]] — Failed signals after multi-timeframe alignment are especially significant

### Inside the Book
- [[Ch3 - Trends]] — Trend identification on different timeframes
- [[Ch5 - Chart Patterns]] — Flag patterns referenced in the weekly Eurodollar example
- Chapter 2 — Types of Charts (weekly/monthly chart construction, continuous futures)
- Chapter 10 — Measured moves use continuous futures for multi-timeframe analysis
- Chapter 12 — Real-World Chart Analysis (Schwager uses multi-timeframe reasoning throughout)
- Chapter 17 — Rule 41: "Never go counter to your own opinion of the long-term trend"
- Chapter 17 — Rule 79: "Periodically review long-term charts"
