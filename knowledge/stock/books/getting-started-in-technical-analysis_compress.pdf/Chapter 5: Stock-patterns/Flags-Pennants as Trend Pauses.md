---
tags: [technical-analysis, schwager, continuation-pattern, trend-pause, framework]
source: "Schwager - Getting Started in Technical Analysis, Ch.5 pp.87-93; Ch.8 pp.132-134; Ch.9 p.138; Ch.11 pp.165-171; Ch.12 pp.196-210; Ch.17 Rules 49-52,57,61-62,73"
related: ["[[Flags]]", "[[Pennants]]", "[[Triangles]]", "[[Breakout Confirmation]]", "[[Signal Frequency vs Reliability Trade-off]]"]
---

# Flags/Pennants as Trend Pauses

## The Core Idea

This note isn't about a new pattern — it's about the **unifying framework** beneath [[Flags]] and [[Pennants]]. Schwager never uses the phrase "trend pause" explicitly, but the concept runs through everything he writes about these patterns across six chapters. The insight is:

> A flag or pennant is not primarily a shape on a chart. It is a **behavioral event** — a moment when a trending market temporarily stops advancing (or declining), absorbs the counter-pressure, and then resumes.

Understanding this reframes flags and pennants from "things to detect" into "phases of a trend's lifecycle."

## Analogy: The Three-Phase Breathing Cycle

Think of a trend as breathing:

1. **Inhale** (impulse move) — a strong directional move, the trend advancing with momentum
2. **Hold** (the pause) — lungs full, no motion, gathering energy for the next breath. This is the flag/pennant.
3. **Exhale** (continuation) — the trend resumes, energy releases in the same direction

The pause is not random — it's structurally necessary. A trend that never pauses is climactic (exhaustion gaps, spikes). A trend that pauses *healthily* is sustainable. The pause itself is evidence of trend health.

## Why Pauses Happen — The Market Mechanics

Schwager doesn't spell out the microstructure, but the logic is implicit:

### 1. Supply absorption
After an advance, some participants take profits. The selling pressure from profit-takers creates a brief counter-move or consolidation. If the trend is healthy, this selling is *absorbed* — new buyers step in at the lower prices within the flag, and the trend resumes.

### 2. No reversal pressure
The narrow range of the flag/pennant tells you something important: sellers aren't aggressively pressing. If they were, the range would widen, the duration would extend, and you'd see a trading range or reversal pattern instead of a tight pause.

### 3. Volatility contraction precedes expansion
This is a well-documented market phenomenon. Periods of compressed volatility tend to be followed by volatility expansions. The flag/pennant is the compression phase; the breakout is the expansion. The direction of the expansion is probabilistically biased toward the prior trend.

## The Tactical Framework

### Phase 1: Recognize the pause forming

A flag/pennant is forming when you observe:
- Price oscillates in a **narrow band** relative to recent [[True Range and ADTR|ADTR]]
- Duration is short (5-15 bars, roughly 1-3 weeks)
- There was a **substantive prior move** (impulse leg) of at least 3× ADTR
- Boundaries are roughly parallel ([[Flags|flag]]) or converging ([[Pennants|pennant]])

### Phase 2: Enter during the pause (Schwager's preference)

This is the key tactical distinction. Most textbooks say "wait for breakout." Schwager says enter *during* the formation:

> I prefer to enter positions during the formation of the flag or pennant, anticipating the probable direction of the breakout. — Ch. 5

**Why this works:**
- Probability already favors continuation
- Entry price is better (you're buying lower in an uptrend pause)
- Stop is the same either way: opposite extreme of the formation + margin
- Reversals following breakouts are "about as common as breakouts in the counter-to-anticipated direction" — meaning the confirmation from waiting doesn't materially improve accuracy

**Where specifically to enter within the pause:**
- In an uptrend flag: buy near the **lower boundary** of the flag (Trade 12.10, 12.14)
- In a downtrend flag: sell near the **upper boundary** of the flag
- This maximizes the distance to your target and minimizes the distance to your stop

### Phase 3: Manage the outcome

Three scenarios after entry:

#### 3a. Continuation (expected)
The trend resumes in the anticipated direction. Trail stop to lock in profits. The flag/pennant boundary becomes the initial stop, then the trailing stop takes over.

#### 3b. Counter-to-anticipated breakout
The pause resolves in the **wrong** direction. This is a [[Flags|failed signal]] — and Schwager considers it MORE reliable than the original signal (Ch. 11). Exit immediately, and consider reversing.

#### 3c. The pause just... keeps going
The pattern extends beyond the 1-3 week window. At some point it stops being a flag/pennant and becomes a trading range. The longer it lasts, the less the prior trend momentum matters. If the narrow consolidation persists for several weeks without resolution, the original thesis weakens.

## Context Multipliers

The same flag/pennant pause has dramatically different significance depending on *where* it forms. Schwager provides four context scenarios that multiply or alter the signal:

### Near the top of a trading range (bullish)

> The market is not backing off despite having reached a major resistance area — the top of the range. Such price action has bullish implications and suggests that the market is gathering strength for an eventual upside breakout. — Ch. 5

The longer the prior trading range, the more significant this signal (Figs 5.26, 5.27).

### Above a trading range (breakout confirmation)

When a flag forms *above* the boundary of a broken trading range, prices are holding above the breakout point. This is strong confirmation that the breakout is real and not a trap.

### Pullback into a prior range after breakout (reversal signal)

> If the market breaks out to a new high or low and then pulls back to form a flag or pennant in the prebreakout trading range, assume that a top or bottom is in place. — Rule #57

This is the opposite of the "above range" case. The breakout failed to hold, and the retreat back into the range suggests the breakout was false.

### Two successive pauses with little separation (strong continuation)

> Two successive flags with little separation can be viewed as a probable continuation pattern. — Rule #73

Multiple pauses in quick succession are like a runner taking two short breaths instead of one long one — they're still running, just catching breath more frequently. The direction remains the same.

## The Expected Gain Asymmetry

This is Schwager's most important quantitative argument for why flag/pennant pauses are valuable even when wrong more often than right:

> It is a mistake to focus on the percentage of winning trades. The key factor is the **expected gain per trade**.
>
> Expected gain = (% wins × avg win) - (% losses × avg loss)

Flags and pennants naturally produce **asymmetric payoffs**:
- **When right**: The continuation leg can be large (the full next impulse move)
- **When wrong**: The stop at the opposite extreme is close and clearly defined (small loss)

This means a flag/pennant trading strategy can be profitable with significantly fewer wins than losses — as long as the wins are materially larger than the losses.

## Python: Trend Pause Scoring

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class TrendPause:
    """A detected trend pause (flag or pennant) with context scoring."""
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    shape: str                  # 'flag' or 'pennant'
    prior_direction: str        # 'up' or 'down'
    prior_move_atr: float       # Prior impulse in ATR multiples
    width_atr: float            # Pause width in ATR multiples
    duration_bars: int
    upper_boundary: float
    lower_boundary: float
    context: str                # from classify_flag_context
    score: float                # composite quality score
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None


def score_trend_pause(pattern: dict,
                      context: str,
                      successive_count: int = 1) -> float:
    """
    Score a flag/pennant trend pause on a 0-10 scale.

    Components:
    - Prior move strength (bigger impulse = better setup)
    - Tightness (narrower pause = less selling pressure)
    - Duration (shorter = healthier pause, Schwager's 1-3 week sweet spot)
    - Context (where it sits relative to S/R levels)
    - Successive pauses bonus

    Returns
    -------
    float: 0-10 score. Higher = stronger setup.
    """
    score = 0.0

    # 1. Prior impulse strength (0-3 points)
    # Schwager requires a "substantive" move; 3+ ATR is minimum
    move_atr = pattern['prior_move_atr']
    if move_atr >= 6:
        score += 3.0
    elif move_atr >= 4:
        score += 2.0
    elif move_atr >= 3:
        score += 1.0
    # Below 3 ATR: no points — weak impulse

    # 2. Tightness of pause (0-2 points)
    # Narrower = sellers aren't pressing
    width_atr = pattern['width_atr']
    if width_atr <= 0.8:
        score += 2.0
    elif width_atr <= 1.2:
        score += 1.5
    elif width_atr <= 1.5:
        score += 1.0
    elif width_atr <= 2.0:
        score += 0.5

    # 3. Duration (0-2 points)
    # Schwager's sweet spot: 5-15 bars
    dur = pattern['duration_bars']
    if 5 <= dur <= 10:
        score += 2.0   # Tightest, shortest = healthiest
    elif 10 < dur <= 15:
        score += 1.5
    elif dur < 5:
        score += 0.5   # Too short to be meaningful
    # Beyond 15: no points — becoming a trading range

    # 4. Context multiplier (0-3 points)
    context_scores = {
        'above_range': 3.0,       # Breakout confirmation (strongest)
        'near_range_top': 2.5,    # Gathering strength for breakout
        'mid_trend': 1.5,         # Standard continuation
        'near_range_bottom': 2.5, # Bearish equivalent
        'below_range': 3.0,       # Breakdown confirmation
        'pullback_into_range': 0.0,  # Reversal signal — NOT a continuation!
    }
    score += context_scores.get(context, 1.0)

    # 5. Successive pauses bonus (Rule #73)
    if successive_count >= 2:
        score = min(score + 1.0, 10.0)

    return round(min(score, 10.0), 1)


def compute_entry_and_stop(pattern: dict,
                           margin_atr_multiple: float = 0.5,
                           adtr: float = 1.0) -> tuple[float, float]:
    """
    Compute entry price and stop price for a trend pause.

    Entry: near the support boundary (lower for uptrend, upper for downtrend)
    Stop: opposite extreme + margin (to avoid shape-shift stops)

    Parameters
    ----------
    margin_atr_multiple : float
        Extra margin beyond the boundary, in ATR multiples.
        Schwager learned this lesson the hard way (Trade 12.11).
    adtr : float
        Current ADTR value for computing the margin.
    """
    margin = margin_atr_multiple * adtr

    if pattern['prior_direction'] == 'up':
        entry = pattern['lower_boundary']     # Buy near support
        stop = pattern['lower_boundary'] - margin  # Below with margin
    else:
        entry = pattern['upper_boundary']     # Sell near resistance
        stop = pattern['upper_boundary'] + margin  # Above with margin

    return entry, stop


def detect_successive_pauses(patterns: list[dict],
                             max_gap_bars: int = 5) -> list[list[dict]]:
    """
    Find sequences of flags/pennants with little separation (Rule #73).

    Two successive pauses with little gap = strong continuation signal.
    """
    if not patterns:
        return []

    # Sort by start date
    sorted_p = sorted(patterns, key=lambda p: p['start_date'])

    chains = [[sorted_p[0]]]

    for i in range(1, len(sorted_p)):
        prev_end = sorted_p[i - 1]['end_date']
        curr_start = sorted_p[i]['start_date']

        # Count business days between
        gap = len(pd.bdate_range(prev_end, curr_start)) - 1

        # Same direction required
        same_dir = (sorted_p[i]['prior_direction'] ==
                    sorted_p[i - 1]['prior_direction'])

        if gap <= max_gap_bars and same_dir:
            chains[-1].append(sorted_p[i])
        else:
            chains.append([sorted_p[i]])

    # Return only chains with 2+ pauses
    return [c for c in chains if len(c) >= 2]


def build_trend_pause(df: pd.DataFrame,
                      pattern: dict,
                      context: str,
                      successive_count: int = 1,
                      atr_period: int = 14) -> TrendPause:
    """
    Full pipeline: take a detected flag/pennant, add context,
    score it, and compute entry/stop.
    """
    from breakout_confirmation import compute_true_range

    tr = compute_true_range(df)
    adtr = tr.rolling(atr_period).mean()
    end_idx = df.index.get_loc(pattern['end_date'])
    curr_adtr = adtr.iloc[end_idx]

    quality = score_trend_pause(pattern, context, successive_count)
    entry, stop = compute_entry_and_stop(pattern, adtr=curr_adtr)

    return TrendPause(
        start_date=pattern['start_date'],
        end_date=pattern['end_date'],
        shape=pattern.get('shape', 'flag'),
        prior_direction=pattern['prior_direction'],
        prior_move_atr=pattern['prior_move_atr'],
        width_atr=pattern['width_atr'],
        duration_bars=pattern['duration_bars'],
        upper_boundary=pattern['upper_boundary'],
        lower_boundary=pattern['lower_boundary'],
        context=context,
        score=quality,
        entry_price=entry,
        stop_price=stop,
    )
```

## The Lifecycle Summary

```
IMPULSE → PAUSE → RESOLUTION
   │         │         │
   │         │         ├── Continuation (expected)
   │         │         │     Trail stop, ride the next impulse
   │         │         │
   │         │         ├── Counter breakout (failed signal)
   │         │         │     Exit, consider reversing (Ch. 11)
   │         │         │
   │         │         └── Extended pause → becomes trading range
   │         │               Original thesis weakens
   │         │
   │         ├── Enter during pause (Schwager's preference)
   │         │   Near support boundary of the pause
   │         │   Stop: opposite extreme + margin
   │         │
   │         └── Context multiplier:
   │             Near range top → enhanced
   │             Above range → very enhanced
   │             Pullback into range → REVERSAL, not continuation
   │             Two in series → Rule #73 bonus
   │
   └── Must be substantive (3+ ATR)
       Without a real impulse, the pause has no thesis
```

## Connections

- [[Flags]] — parallel-boundary pause
- [[Pennants]] — converging-boundary pause  
- [[Triangles]] — longer-duration pause (different beast mechanically)
- [[Wide-Ranging Days]] — a WRD at the start or end of a pause amplifies significance
- [[Gaps]] — a breakaway gap preceding a pause adds conviction
- [[Breakout Confirmation]] — applies to the resolution phase
- [[Signal Frequency vs Reliability Trade-off]] — the entry-during-formation vs. wait-for-breakout choice maps directly to this
