---
tags: [technical-analysis, schwager, chapter-7, fundamental-analysis, synthesis, directional-filter]
chapter: 7
concept: 4
title: "Fundamental-Technical Synthesis"
related: [multi-timeframe, confirmation-conditions, signal-filtering, failed-signals]
---

# Fundamental-Technical Synthesis

## Definition

Chart analysis can be combined with fundamental projections to create a **more effective approach** than either method alone. The fundamental forecast serves as a **directional filter** on chart signals:

- Fundamentals bullish → Accept only **buy** chart signals
- Fundamentals bearish → Accept only **sell** chart signals
- Fundamentals neutral → Accept **both** directions

This gives the chart analyst who is also a competent fundamental analyst a **"decided edge"** over traders relying on either method alone.

**Critical prerequisite:** Schwager specifies this requires "better than 50-50 accuracy rate" in fundamental forecasting. A wrong filter actively inverts results.

## Schwager's Exact Words

> *"Assuming some skill in fundamental forecasting (i.e., a better than 50-50 accuracy rate), chart analysis can be combined with fundamental projections to provide a more effective approach."*  
> — Chapter 7, p.124

> *"Combining fundamental analysis with technical analysis can provide a particularly effective approach and is indeed descriptive of the general methodology used by some of the world's most successful traders."*  
> — Introduction, p.4

> *"Fundamental analysis is concerned with the why of market behavior, while technical analysis is more concerned with the when."*  
> — Introduction, p.4

> *"The breakout will fail unless there are solid fundamental reasons and underlying buying to sustain the trend."*  
> — Chapter 4, p.55 (why fundamentals matter for breakout sustainability)

> *"The failure of a market to follow through on significant bullish or bearish news is often a harbinger of an imminent trend reversal."*  
> — Chapter 17, Rule 77 (the reverse application — fundamental-chart disagreement as warning)

## Analogy — Product Strategy + A/B Testing

In software product development:
- **Product strategy** = fundamental analysis (which direction the market is going)
- **A/B testing** = technical analysis (which specific move to make and when)

Running A/B tests without a strategy means optimizing random metrics. Having a strategy without testing means guessing at implementation. The synthesis: strategy tells you **which direction to invest in**, tests tell you **when and how to execute**.

You don't A/B test features that contradict your product vision, just as you don't take sell signals when fundamentals say bullish.

## The Filter Logic

| Fundamental View | Chart Buy Signal | Chart Sell Signal |
|---|---|---|
| **Bullish** | ACCEPT (high conviction) | REJECT |
| **Neutral** | Accept (normal) | Accept (normal) |
| **Bearish** | REJECT | ACCEPT (high conviction) |

## Worked Example: The Asymmetry of Right vs Wrong

### Scenario: 6 chart signals in a bullish market

| Signal | Type | Raw Result |
|--------|------|-----------|
| 1 | Sell breakout | Loss -$400 |
| 2 | Buy breakout | Loss -$300 (false) |
| 3 | Sell breakout | Loss -$350 |
| 4 | Buy breakout | **Win +$2,500** |
| 5 | Sell breakout | Loss -$200 |
| 6 | Buy continuation | **Win +$1,800** |

### Results by fundamental filter

| Filter | Trades | Win Rate | Net P&L | vs. Baseline |
|--------|--------|----------|---------|-------------|
| None (raw) | 6 | 33% | +$3,050 | Baseline |
| **Bullish (correct)** | 3 | 67% | **+$4,000** | **+31%** |
| Neutral | 6 | 33% | +$3,050 | No change |
| **Bearish (WRONG)** | 3 | 0% | **-$950** | **-131%** |

### The critical insight

A correct filter improves P&L by +31%. A wrong filter **flips profit to loss**. This asymmetry is why "better than 50-50" is a hard prerequisite, not a soft suggestion.

## The Three-Layer Filter Stack

This concept forms a natural stack with Concepts 2 and 3:

```
Layer 1: FUNDAMENTALS (broadest, slowest filter)
  "What is the economic / earnings / supply-demand direction?"
  → Stays constant for weeks/months
    ↓
Layer 2: WEEKLY CHART (multi-timeframe context)
  "What is the price structure on the weekly chart?"
  → Confirms or challenges the fundamental view
    ↓
Layer 3: DAILY SIGNALS + CONFIRMATION CONDITIONS
  "Is there a specific entry trigger with confirmation?"
  → The actual trade entry
    ↓
Result: Highest-conviction trades pass all three layers
```

## Rule 77: The Reverse Test

Ch17 Rule 77 provides the inverse application: *"The failure of a market to follow through on significant bullish or bearish news is often a harbinger of an imminent trend reversal."*

When fundamentals say "up" but the chart fails to respond, that **disagreement** is itself a signal. The synthesis works both ways:
- **Agreement** (fundamentals bullish + chart breakout up) → Strengthens signal
- **Disagreement** (fundamentals bullish + chart fails on good news) → Warning of reversal

This connects directly to [[Ch7 - Using Failed Signals as Trading Indicators]].

## Python Implementation

```python
import pandas as pd
from typing import Literal, Optional
from dataclasses import dataclass


@dataclass
class FundamentalView:
    """The fundamental analyst's directional forecast."""
    direction: Literal['bullish', 'bearish', 'neutral']
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""


def apply_fundamental_filter(
    df: pd.DataFrame,
    view: FundamentalView,
    signal_col: str = 'chart_signal',
    confidence_threshold: float = 0.6
) -> pd.DataFrame:
    """
    Filter chart signals using a fundamental directional view.
    
    Low confidence (< threshold) → treat as neutral.
    
    Parameters
    ----------
    df : pd.DataFrame with signal column (1=buy, -1=sell, 0=none)
    view : FundamentalView with direction and confidence
    confidence_threshold : float, below this treat as neutral
    
    Returns
    -------
    DataFrame with 'filtered_signal' and 'signal_quality' columns
    """
    df = df.copy()
    df['filtered_signal'] = 0
    df['signal_quality'] = 'none'
    
    direction = view.direction
    if view.confidence < confidence_threshold:
        direction = 'neutral'
    
    for i in range(len(df)):
        sig = df[signal_col].iloc[i]
        if sig == 0:
            continue
        
        if direction == 'neutral':
            df.iloc[i, df.columns.get_loc('filtered_signal')] = sig
            df.iloc[i, df.columns.get_loc('signal_quality')] = 'normal'
        elif direction == 'bullish' and sig == 1:
            df.iloc[i, df.columns.get_loc('filtered_signal')] = sig
            df.iloc[i, df.columns.get_loc('signal_quality')] = 'high_conviction'
        elif direction == 'bearish' and sig == -1:
            df.iloc[i, df.columns.get_loc('filtered_signal')] = sig
            df.iloc[i, df.columns.get_loc('signal_quality')] = 'high_conviction'
        # else: signal rejected (stays 0)
    
    return df


def detect_news_failure(
    df: pd.DataFrame,
    news_date_col: str = 'news_date',
    news_direction_col: str = 'news_direction',
    close_col: str = 'Close',
    lookforward_days: int = 5,
    min_move_pct: float = 0.02
) -> pd.DataFrame:
    """
    Ch17 Rule 77: Detect when market fails to follow
    through on significant news.
    
    If bullish news doesn't produce min_move_pct up move
    within lookforward_days → potential reversal warning.
    
    Parameters
    ----------
    df : pd.DataFrame with news event columns
    lookforward_days : int, days to check for follow-through
    min_move_pct : float, minimum expected move as fraction
    
    Returns
    -------
    DataFrame with 'news_failure' column (1=failure detected)
    """
    df = df.copy()
    df['news_failure'] = 0
    
    news_rows = df[df[news_date_col].notna()].index
    
    for idx in news_rows:
        pos = df.index.get_loc(idx)
        direction = df.loc[idx, news_direction_col]
        entry_price = df.loc[idx, close_col]
        
        end_pos = min(pos + lookforward_days, len(df) - 1)
        future_close = df.iloc[end_pos][close_col]
        
        actual_move = (future_close - entry_price) / entry_price
        
        if direction == 'bullish' and actual_move < min_move_pct:
            df.iloc[end_pos, df.columns.get_loc('news_failure')] = 1
        elif direction == 'bearish' and actual_move > -min_move_pct:
            df.iloc[end_pos, df.columns.get_loc('news_failure')] = 1
    
    return df


def full_synthesis_pipeline(
    daily_df: pd.DataFrame,
    weekly_bias: dict,
    fundamental_view: FundamentalView,
    signal_col: str = 'signal'
) -> dict:
    """
    Complete three-layer synthesis pipeline.
    
    Layer 1: Fundamental filter
    Layer 2: Weekly bias filter (from multi-timeframe)
    Layer 3: Accept only signals passing both
    
    Returns summary with trade counts and quality breakdown.
    """
    # Layer 1: Fundamental
    after_fund = apply_fundamental_filter(
        daily_df, fundamental_view, signal_col
    )
    
    # Layer 2: Weekly bias (from Ch7 Concept 3)
    from typing import Literal
    bias = weekly_bias.get('bias', 'neutral')
    
    df = after_fund.copy()
    df['final_signal'] = df['filtered_signal']
    
    if bias == 'bullish':
        df.loc[df['final_signal'] == -1, 'final_signal'] = 0
    elif bias == 'bearish':
        df.loc[df['final_signal'] == 1, 'final_signal'] = 0
    
    raw = (daily_df[signal_col] != 0).sum()
    after_f = (after_fund['filtered_signal'] != 0).sum()
    final = (df['final_signal'] != 0).sum()
    
    return {
        'raw_signals': int(raw),
        'after_fundamental_filter': int(after_f),
        'after_both_filters': int(final),
        'rejected_by_fundamentals': int(raw - after_f),
        'rejected_by_weekly': int(after_f - final),
        'total_rejected': int(raw - final),
        'fundamental_view': fundamental_view.direction,
        'weekly_bias': bias,
        'df': df
    }
```

## When This Concept Works Best

- **Longer-term position trading** (weeks to months) where fundamentals have time to play out
- **Markets with clear fundamental drivers** — interest rates for bonds, earnings for stocks, crop reports for grains
- **Traders who monitor both fundamentals and charts** — the "hybrid" approach Schwager attributes to many top traders
- **Combining with multi-timeframe analysis** — fundamentals as Layer 1, weekly chart as Layer 2
- **Reducing overtrading** — the filter eliminates many marginal signals

## When It Doesn't Work

- **Short-term / day trading** — fundamentals change too slowly to be useful intraday
- **Fundamental accuracy ≤ 50%** — the filter actively inverts results (see worked example)
- **Markets with opaque fundamentals** — some markets lack reliable fundamental models
- **Regime changes** — fundamentals lag during structural shifts (the same weakness as multi-timeframe)
- **If fundamental and technical views always agree** — then the filter adds no value (it never rejects anything)

## Cross-References

| Location | What It Says |
|----------|-------------|
| Introduction, p.4 | Combining approaches = "particularly effective", used by top traders |
| Ch 1, p.12 | Chart = "unambiguous summary of net impact of all fundamental factors" |
| Ch 1, p.15 | Charts as timing tool for fundamentally-driven traders |
| Ch 4, p.55 | Breakouts need "solid fundamental reasons" to sustain |
| Ch 7, p.124 | Core concept: fundamental filter on chart signals |
| Ch 14, p.243 | Systematic filter: fundamental model classifying market as bullish/bearish/neutral |
| Ch 16, p.277 | Trading philosophy: "synthesis of fundamental and chart analyses" |
| Ch 17, Rule 41 | "Never go counter to the long-term trend" |
| Ch 17, Rule 77 | Market failing on fundamental news = reversal warning |
| Ch 18, p.299 | Market Wizards: methods include "pure fundamentalists, pure technicians, hybrids" |

## Links

### Inside This Chapter
- [[Ch7 - Is Chart Analysis Still Valid (MOC)]]
- [[Ch7 - Multi-Timeframe Analysis]] — Both provide directional context; can be layered (weekly chart = Layer 2)
- [[Ch7 - Confirmation Conditions]] — Fundamentals as the broadest filter, confirmation as the narrowest
- [[Ch7 - Risk Control and Win Rate vs Profitability]] — Correct fundamental filter improves win rate
- [[Ch7 - Using Failed Signals as Trading Indicators]] — Rule 77 connects fundamental-chart disagreement to failed signals

### Inside the Book
- Introduction — The Great Fundamental vs Technical Analysis Debate
- Chapter 1 — Charts: Forecasting Tool or Folklore? (chart as summary of fundamentals)
- [[Ch4 - Trading Ranges and Support and Resistance]] — Breakouts need fundamental support
- Chapter 14 — Filter section: systematic fundamental model integration
- Chapter 16 — Planned Trading Approach (defining a philosophy)
- Chapter 17 — Rules 41 and 77
- Chapter 18 — Market Wiz(ar)dom (hybrid traders among the best)
