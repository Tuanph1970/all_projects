---
tags: [technical-analysis, schwager, continuation-pattern, support-resistance, context, framework]
source: "Schwager - Getting Started in Technical Analysis, Ch.4 pp.52-70; Ch.5 pp.92-93; Ch.11 pp.165-171; Ch.17 Rules 49,52,57"
related: ["[[Flags]]", "[[Pennants]]", "[[Flags-Pennants as Trend Pauses]]", "[[Breakout Confirmation]]"]
---

# Flags/Pennants Near Support/Resistance Boundaries

## The Core Idea

A flag or pennant on its own is a standard continuation signal. But *where* it forms relative to major support/resistance boundaries can amplify, invert, or completely change the meaning. This note maps the five spatial scenarios Schwager identifies and explains the behavioral logic behind each.

> The more extended the trading range, the greater the potential significance of a flag or pennant that forms near or above its top. — Ch. 5

This is the context-multiplier principle: the same pattern, in different positions, tells you fundamentally different things about buyer/seller behavior.

## The Five Scenarios

### 1. Near the top of a trading range → Very bullish

**What you see**: Price has been oscillating in a range for weeks or months. A flag/pennant forms near the *upper boundary* of that range.

**What it means**: The market has reached a level that has previously turned it back (resistance). Instead of retreating, it pauses in a tight consolidation. This is not what sellers want to see — if they had the strength to push price back down, the consolidation would be broader and more volatile. The narrow pause near resistance means the selling pressure is being absorbed.

**Analogy**: A rock climber reaches a difficult overhang (resistance). Instead of falling back, they hang there, resting their grip, gathering strength. The fact that they can hold on at all at this difficult point suggests they're strong enough to push through.

**Schwager examples**: Figs 5.26 (soybeans), 5.27 (soybean meal) — both were precursors of "explosive advances."

**Rule #49**: *"Narrow market consolidations near the upper end of broader trading ranges are bullish patterns."*

### 2. Above a trading range → Breakout confirmation

**What you see**: Price has broken above a trading range. Instead of reversing (which is common — false breakouts are frequent), it pauses in a flag/pennant *above* the former range boundary.

**What it means**: The breakout is real. Price is holding above the level that was resistance and is now support. The flag is the market digesting the breakout before the next leg up. This is one of the strongest continuation setups in Schwager's framework.

**Analogy**: The climber has cleared the overhang. Instead of sliding back, they're resting on the ledge above it. That ledge (the former resistance, now support) is holding their weight. The next move is further up.

**Rule #52**: *"Flags or pennants forming right above or below prior extended and broad trading ranges tend to be fairly reliable continuation patterns."*

**Connection to Chapter 4**: Once prices break above a trading range, the upper boundary becomes support (the S/R inversion principle). A flag forming just above this inverted level is the market testing and confirming this inversion.

### 3. Pullback into range after breakout → Reversal signal (NOT continuation!)

**What you see**: Price broke above a trading range, but then pulled back and formed a flag/pennant *inside* the former range.

**What it means**: The breakout failed. Price couldn't hold above resistance and retreated back into the range. The flag forming inside the range is not a continuation pattern — it's a sign that the breakout was false and a top may be forming.

**Analogy**: The climber cleared the overhang, stood on the ledge for a moment, then slid back below it. They're now hanging below the overhang again, resting. That's not preparation for another attempt — that's exhaustion. The next move is likely back down.

**Rule #57**: *"If the market breaks out to a new high or low and then pulls back to form a flag or pennant in the prebreakout trading range, assume that a top or bottom is in place."*

This is the **one scenario where a flag/pennant is NOT a continuation signal**. It's the odd one out — and it's critical to recognize because the trading logic is inverted: you'd trade *against* the original breakout direction.

### 4. Near the bottom of a trading range → Very bearish

The mirror image of scenario 1. A flag/pennant near the *lower boundary* of a range means the market is not bouncing off support despite reaching a level that has previously turned it back. The buying pressure is failing to absorb the selling.

**Schwager examples**: Figs 5.28 (Eurodollar), 5.29 (natural gas) — both were "harbingers of steep price declines."

**Rule #49**: *"...Similarly, narrow consolidations near the low end of trading ranges are bearish."*

### 5. Below a trading range → Breakdown confirmation

The mirror image of scenario 2. Price has broken below a range and is pausing in a flag/pennant below the former support. The breakdown is being confirmed — price is holding below the level that was support and is now resistance.

## The Behavioral Framework

What unifies all five scenarios is a question about **supply and demand at critical levels**:

```
At a resistance level:
  └── Market pauses tightly (flag/pennant)
       ├── Near or above resistance → Sellers can't push it back
       │    → Bullish: strength at resistance
       └── Pulled back below after breakout → Buyers couldn't hold
            → Bearish: failed breakout (Rule #57)

At a support level:
  └── Market pauses tightly (flag/pennant)
       ├── Near or below support → Buyers can't push it back
       │    → Bearish: weakness at support
       └── Pulled back above after breakdown → Sellers couldn't hold
            → Bullish: failed breakdown (Rule #57)
```

The key insight: the *same shape* (a tight pause) means **opposite things** depending on whether it's at a level where the market is *testing* resistance/support (scenarios 1,2,4,5) or *retreating from* a failed test (scenario 3).

## The Amplifier: Prior Range Duration

Schwager is explicit that the significance of these setups scales with the duration of the prior trading range. A flag near the top of a 2-week range is modestly bullish. A flag near the top of a 6-month range is potentially explosive. The longer price has been capped at a level, the more stored energy is released when it finally breaks through.

## Python Detection

```python
import pandas as pd
import numpy as np


def find_trading_range(df: pd.DataFrame,
                       min_duration: int = 20,
                       max_width_pct: float = 0.15) -> list[dict]:
    """
    Identify trading ranges in the price history.

    A trading range is a period where price oscillates between
    a high and low boundary without a sustained breakout.

    Parameters
    ----------
    min_duration : int
        Minimum bars to qualify as a range (20 ~ 1 month)
    max_width_pct : float
        Maximum range width as % of midpoint price (0.15 = 15%)
    """
    ranges = []

    for end_i in range(min_duration, len(df)):
        for dur in [60, 40, 30, 20]:  # Try longer ranges first
            if end_i - dur < 0:
                continue
            window = df.iloc[end_i - dur:end_i]
            high = window['high'].max()
            low = window['low'].min()
            mid = (high + low) / 2
            width_pct = (high - low) / mid if mid > 0 else 0

            if width_pct <= max_width_pct:
                ranges.append({
                    'start_date': df.index[end_i - dur],
                    'end_date': df.index[end_i],
                    'range_high': high,
                    'range_low': low,
                    'duration_bars': dur,
                    'width_pct': width_pct,
                })
                break  # Take the longest qualifying range at this endpoint

    return ranges


def classify_flag_near_sr(flag: dict,
                          ranges: list[dict],
                          proximity_pct: float = 0.15) -> dict:
    """
    Classify a flag/pennant's position relative to the nearest
    trading range.

    Returns a dict with:
    - scenario: one of the five scenarios
    - range: the relevant trading range (if any)
    - significance: qualitative assessment
    - trading_implication: what to do

    Parameters
    ----------
    flag : dict
        Output from detect_flag_or_pennant()
    ranges : list[dict]
        Output from find_trading_range()
    proximity_pct : float
        How close to the boundary counts as "near" (% of range width)
    """
    flag_mid = (flag['upper_boundary'] + flag['lower_boundary']) / 2

    # Find the most recent range that ended before the flag started
    relevant_ranges = [
        r for r in ranges
        if r['end_date'] <= flag['start_date']
    ]

    if not relevant_ranges:
        return {
            'scenario': 'no_range_context',
            'range': None,
            'significance': 'standard',
            'trading_implication': 'Treat as standard continuation pause',
        }

    # Take the most recent range
    rng = max(relevant_ranges, key=lambda r: r['end_date'])
    range_width = rng['range_high'] - rng['range_low']
    proximity_threshold = proximity_pct * range_width

    # Determine position relative to range
    above_top = flag_mid > rng['range_high']
    below_bottom = flag_mid < rng['range_low']
    near_top = (not above_top and
                flag_mid > rng['range_high'] - proximity_threshold)
    near_bottom = (not below_bottom and
                   flag_mid < rng['range_low'] + proximity_threshold)

    # Check if there was a breakout from this range before the flag
    # (needed to distinguish scenarios 2 vs 1, and 3)
    breakout_bars = df_between_dates(flag['start_date'], rng['end_date'])

    if above_top:
        # Was there a recent breakout attempt that pulled back?
        # Scenario 2: above range, holding
        # Scenario 3: pulled back into range (checked separately)
        return {
            'scenario': 'above_range',
            'range': rng,
            'significance': 'very_high',
            'trading_implication': (
                'Breakout confirmation. Price holding above former '
                'resistance (now support). Strong continuation setup. '
                f'Prior range duration: {rng["duration_bars"]} bars.'
            ),
            'schwager_rule': 'Rule #52',
        }

    elif below_bottom:
        return {
            'scenario': 'below_range',
            'range': rng,
            'significance': 'very_high',
            'trading_implication': (
                'Breakdown confirmation. Price holding below former '
                'support (now resistance). Strong bearish continuation. '
                f'Prior range duration: {rng["duration_bars"]} bars.'
            ),
            'schwager_rule': 'Rule #52',
        }

    elif near_top:
        return {
            'scenario': 'near_range_top',
            'range': rng,
            'significance': 'high',
            'trading_implication': (
                'Bullish: not backing off at resistance. Gathering '
                'strength for upside breakout. The longer the prior '
                f'range ({rng["duration_bars"]} bars), the more '
                'significant.'
            ),
            'schwager_rule': 'Rule #49',
        }

    elif near_bottom:
        return {
            'scenario': 'near_range_bottom',
            'range': rng,
            'significance': 'high',
            'trading_implication': (
                'Bearish: not bouncing at support. Selling pressure '
                'overwhelming buying. Expect downside breakout. '
                f'Prior range: {rng["duration_bars"]} bars.'
            ),
            'schwager_rule': 'Rule #49',
        }

    else:
        return {
            'scenario': 'mid_range',
            'range': rng,
            'significance': 'low',
            'trading_implication': (
                'Flag inside the range, away from boundaries. '
                'Standard continuation — no enhanced significance.'
            ),
        }


def detect_pullback_into_range(df: pd.DataFrame,
                                flag: dict,
                                ranges: list[dict]) -> dict | None:
    """
    Detect Scenario 3: a breakout from a range followed by a
    pullback, with the flag forming INSIDE the prior range.

    This is the reversal scenario (Rule #57) — the one case where
    a flag is NOT a continuation signal.

    Returns dict with reversal signal info, or None.
    """
    flag_mid = (flag['upper_boundary'] + flag['lower_boundary']) / 2

    relevant_ranges = [
        r for r in ranges
        if r['end_date'] <= flag['start_date']
    ]

    if not relevant_ranges:
        return None

    rng = max(relevant_ranges, key=lambda r: r['end_date'])

    # Is the flag inside the range?
    inside = rng['range_low'] <= flag_mid <= rng['range_high']
    if not inside:
        return None

    # Was there a breakout between the range end and the flag start?
    range_end_idx = df.index.get_loc(rng['end_date'])
    flag_start_idx = df.index.get_loc(flag['start_date'])
    between = df.iloc[range_end_idx:flag_start_idx]

    if len(between) == 0:
        return None

    max_high = between['high'].max()
    min_low = between['low'].min()

    upside_breakout = max_high > rng['range_high']
    downside_breakout = min_low < rng['range_low']

    if upside_breakout:
        return {
            'scenario': 'pullback_into_range',
            'failed_breakout_direction': 'up',
            'implied_signal': 'bearish',
            'range': rng,
            'note': (
                'Rule #57: Upside breakout failed, flag formed back '
                'inside range. Assume TOP is in place. Stop: above '
                'flag/pennant boundary.'
            ),
        }
    elif downside_breakout:
        return {
            'scenario': 'pullback_into_range',
            'failed_breakout_direction': 'down',
            'implied_signal': 'bullish',
            'range': rng,
            'note': (
                'Rule #57: Downside breakout failed, flag formed back '
                'inside range. Assume BOTTOM is in place. Stop: below '
                'flag/pennant boundary.'
            ),
        }

    return None


def full_sr_analysis(df: pd.DataFrame,
                     flag: dict,
                     range_lookback: int = 60,
                     max_width_pct: float = 0.15) -> dict:
    """
    Complete support/resistance context analysis for a flag/pennant.

    Pipeline:
    1. Find trading ranges in the history
    2. Check for pullback-into-range (Rule #57) first — this overrides
    3. If no pullback, classify normal position

    The pullback check runs first because it inverts the signal:
    a flag that looks like it's "near the top of a range" could
    actually be a failed breakout that retreated.
    """
    ranges = find_trading_range(
        df.iloc[:df.index.get_loc(flag['start_date'])],
        min_duration=20,
        max_width_pct=max_width_pct,
    )

    # Priority check: is this a pullback scenario (Rule #57)?
    pullback = detect_pullback_into_range(df, flag, ranges)
    if pullback:
        return pullback

    # Normal classification
    return classify_flag_near_sr(flag, ranges)
```

## Decision Matrix

| Scenario | Signal | Strength | Stop | Schwager Rule |
|----------|--------|----------|------|---------------|
| Near range top | Bullish continuation | High (scales with range duration) | Below flag + margin | #49 |
| Above range | Bullish confirmation | Very high | Below flag (or range top) | #52 |
| Pullback into range | **Reversal** (not continuation!) | High | Beyond flag boundary | #57 |
| Near range bottom | Bearish continuation | High (scales with range duration) | Above flag + margin | #49 |
| Below range | Bearish confirmation | Very high | Above flag (or range bottom) | #52 |

## The S/R Inversion Principle (Chapter 4)

This concept from Chapter 4 is the mechanical foundation for scenarios 2 and 5:

> Once prices witness a sustained breakout above a trading range, the upper boundary of that range becomes a zone of price support.

And the mirror:

> In the case of a sustained breakout below a trading range, the lower boundary of that range becomes a zone of price resistance.

When a flag forms above the range, it sits on this newly created support (former resistance). When a flag forms below the range, it sits below this newly created resistance (former support). This is why these are the strongest setups — the flag is testing the inverted level, and the fact that it holds is powerful confirmation.

## Connections

- [[Flags]] — the base pattern; this note adds the spatial context layer
- [[Pennants]] — same logic applies identically
- [[Flags-Pennants as Trend Pauses]] — the context multiplier section links here
- [[Breakout Confirmation]] — scenarios 2 and 5 are natural extensions of the breakout confirmation framework
- [[Triangles]] — triangles near S/R boundaries carry similar (but less sharp) significance
- Chapter 4 (support and resistance) — the theoretical foundation for all five scenarios
- Chapter 11 (failed signals) — scenario 3 (pullback into range) is a specific type of failed breakout signal
