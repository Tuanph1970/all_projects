---
tags: [technical-analysis, schwager, continuation-pattern, flags]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.87-93; Chapter 9 p.138; Chapter 11 pp.165-171; Chapter 12 pp.196-210; Chapter 17 Rules 49-52,57,61-62"
related: ["[[Continuation Patterns MOC]]", "[[Triangles]]", "[[Pennants]]", "[[Signal Frequency vs Reliability Trade-off]]"]
---

# Flags

## Definition

A **flag** is a narrow-band, short-duration (1-3 weeks) congestion phase within a trend, enclosed by **parallel lines**. It represents a temporary pause — the trend catches its breath before resuming.

### Flag vs. Pennant vs. Triangle

| Feature | Flag | Pennant | Triangle |
|---------|------|---------|----------|
| Boundary lines | Parallel | Converging | Converging |
| Duration | 1-3 weeks | 1-3 weeks | Weeks to months |
| Role | Almost always continuation | Almost always continuation | Continuation or reversal |

The pennant is the converging-lines cousin of the flag — same duration, same logic, just a different shape. The triangle looks similar to a pennant but takes much longer to form.

## Analogy

Think of a flag as a runner pausing to tie their shoe mid-race. They're still in the race, still pointed in the same direction, and as soon as the lace is fixed they take off running again. The shoe-tying is the pause (the flag body), the sprint before was the prior trend, and the sprint after is the continuation.

A counter-to-anticipated breakout from a flag is like the runner pausing to tie their shoe and then suddenly turning around and running the opposite way. Something fundamental changed.

## Slope Direction

Flags typically slope **against** the main trend — a flag in an uptrend usually tilts slightly downward, and vice versa. However, Schwager found no significant reliability difference between same-direction and opposite-direction slopes.

## Schwager's Entry Strategy (Unique and Important)

This is where flags get tactically interesting. Most textbooks say "wait for the breakout." Schwager disagrees:

> I prefer to enter positions **during the formation** of the flag or pennant, anticipating the probable direction of the breakout. This approach allows for more advantageous trade entries without a significant deterioration in the percentage of correct trades, since reversals following breakouts from flags and pennants are about as common as breakouts in the counter-to-anticipated direction.

### Why this works

The probability already favors continuation. By entering during the formation rather than waiting for the breakout, you get a better price. The stop is the same either way (opposite extreme of the flag), so the risk/reward improves.

### Stop placement

After entry (whether during formation or after breakout), the **opposite extreme of the flag** serves as the stop-loss point. This is one of flags' key advantages — the stop is close and technically meaningful.

> Tight flag and pennant consolidations tend to be reliable continuation patterns and allow entry into an existing trend, with a reasonably close, yet meaningful, stop point. — Rule #61

### Stop placement warning (from Chapter 12)

Don't place stops **too close** to the flag boundary. Schwager made this mistake himself (Trade 12.11, March 1995 copper):

> Flag and pennant consolidations frequently change their shape as they evolve. It is also quite common for such consolidations to be interrupted by one-day spikes. Consequently, it is important that stops allow for a meaningful margin beyond the existing boundary of the pattern.

## Flags Near Support/Resistance (Power Moves)

### Flag near top of trading range = very bullish

When a flag forms near the top of a long trading range, it means the market is **not backing off** despite reaching major resistance. It's gathering strength for an upside breakout. The longer the prior trading range, the more significant this signal (Figs 5.26, 5.27).

### Flag above trading range = breakout confirmation

When a flag forms **above** the boundary of a prior trading range, prices are holding above the breakout point — very strong confirmation that the breakout is real.

### Mirror images for bearish

Flags near the bottom of or below trading ranges are particularly bearish (Figs 5.28, 5.29).

> Flags or pennants forming right above or below prior extended and broad trading ranges tend to be fairly reliable continuation patterns. — Rule #52

### Flag after breakout that pulls back into range = top/bottom signal

> If the market breaks out to a new high or low and then pulls back to form a flag in the prebreakout trading range, assume that a top or bottom is in place. — Rule #57

## Failed Flag Signals (Chapter 11)

Flags produce two types of failed signals. Both connect to the Chapter 11 framework where a failed signal is MORE reliable than the original.

### Type 1: Counter-to-anticipated breakout

A flag in a downtrend normally continues down. If it breaks **up** instead, that's a counter-to-anticipated breakout — a potent reversal signal (Figs 11.19-11.23).

The failed signal remains valid as long as prices don't close beyond the **opposite end** of the flag. A pullback after the counter breakout doesn't invalidate it — only a close past the other side does (Fig 11.21).

> If a tight flag or pennant consolidation leads to a breakout in the wrong direction (i.e., a reversal instead of a continuation), expect the move to continue in the direction of the breakout. — Rule #62

### Type 2: Opposite direction breakout after normal breakout

A flag breaks out in the expected direction (continuation), but instead of following through, prices reverse and close beyond the **opposite extreme** of the flag. The initial breakout was a trap (Figs 11.24-11.26).

Key: requires a **close** beyond the opposite end, not just an intraday penetration. Schwager prefers this stricter definition.

## Real-World Trading Lessons (Chapter 12)

| Trade | Instrument | Entry | Outcome | Lesson |
|-------|-----------|-------|---------|--------|
| 12.10 | Dec 1994 silver | Flag after bear trap | Loss ($500) | Counter-to-anticipated downside penetration = get out immediately |
| 12.11 | Mar 1995 copper | Flag in new high ground | Loss (stop too tight) | Flags change shape; allow margin beyond boundary for stops |
| 12.12 | Crude oil | Pennant near range low + wide gap | Loss (bear trap) | Failed pennant led to reversal and next trade |
| 12.13 | Crude oil | Reversed from 12.12 on failure signals | Large gain | Flexibility to reverse position is more valuable than calling direction right |
| 12.14 | Sep 1994 unleaded gas | Flag in uptrend, buy near lower boundary | Win | Expected gain per trade matters more than win percentage |

### The Expected Gain Insight (from Trade 12.14)

> It is a mistake to focus on the percentage of winning trades. The key factor is the **expected gain per trade** = (% wins × avg win) - (% losses × avg loss).

Flags naturally produce favorable expected gain because: when right, the continuation can be very large; when wrong, the stop at the opposite extreme limits the loss. The pattern can be profitable even with significantly more losses than gains.

## Python Detection

```python
import numpy as np
import pandas as pd


def detect_flags(df: pd.DataFrame,
                 min_duration: int = 5,
                 max_duration: int = 15,
                 max_width_atr: float = 2.0,
                 min_prior_move_atr: float = 3.0,
                 prior_move_lookback: int = 20,
                 atr_period: int = 14,
                 parallelism_tolerance: float = 0.3) -> list[dict]:
    """
    Detect flag patterns in OHLC data.

    A flag is:
    1. Short duration (5-15 bars, ~1-3 weeks)
    2. Narrow range (width < max_width_atr × ADTR)
    3. Bounded by approximately parallel lines
    4. Preceded by a substantive price move

    Parameters
    ----------
    min_duration, max_duration : int
        Acceptable flag length in bars
    max_width_atr : float
        Maximum flag width as multiple of ADTR
    min_prior_move_atr : float
        Minimum preceding move (in ATR multiples) to qualify
    parallelism_tolerance : float
        How different upper/lower slopes can be (0 = perfectly parallel,
        1 = very loose). Ratio of slope difference to average slope.
    """
    from breakout_confirmation import compute_true_range

    tr = compute_true_range(df)
    adtr = tr.rolling(atr_period).mean()

    flags = []

    for end_i in range(prior_move_lookback + max_duration, len(df)):
        curr_adtr = adtr.iloc[end_i]
        if pd.isna(curr_adtr) or curr_adtr == 0:
            continue

        for dur in range(min_duration, max_duration + 1):
            start_i = end_i - dur

            window = df.iloc[start_i:end_i + 1]
            window_highs = window['high'].values
            window_lows = window['low'].values

            # 1. Check width (narrow band)
            flag_width = window_highs.max() - window_lows.min()
            if flag_width > max_width_atr * curr_adtr:
                continue

            # 2. Fit upper and lower trendlines
            x = np.arange(len(window), dtype=float)

            # Upper line through highs
            upper_coeffs = np.polyfit(x, window_highs, 1)
            upper_slope = upper_coeffs[0]

            # Lower line through lows
            lower_coeffs = np.polyfit(x, window_lows, 1)
            lower_slope = lower_coeffs[0]

            # 3. Check parallelism
            avg_slope = (abs(upper_slope) + abs(lower_slope)) / 2
            if avg_slope > 0:
                slope_diff_ratio = abs(upper_slope - lower_slope) / avg_slope
            else:
                slope_diff_ratio = abs(upper_slope - lower_slope)

            if slope_diff_ratio > parallelism_tolerance:
                continue  # Lines converge/diverge too much → not a flag

            # 4. Check preceding move
            prior_window = df.iloc[start_i - prior_move_lookback:start_i]
            prior_move = prior_window['close'].iloc[-1] - prior_window['close'].iloc[0]
            prior_move_atr = abs(prior_move) / curr_adtr

            if prior_move_atr < min_prior_move_atr:
                continue  # Not enough preceding move

            prior_direction = 'up' if prior_move > 0 else 'down'

            # 5. Check flag slope (typically against the main trend)
            flag_slope = (upper_slope + lower_slope) / 2
            slopes_against = ((prior_direction == 'up' and flag_slope < 0) or
                              (prior_direction == 'down' and flag_slope > 0))

            flags.append({
                'start_date': df.index[start_i],
                'end_date': df.index[end_i],
                'duration_bars': dur,
                'width': flag_width,
                'width_atr': flag_width / curr_adtr,
                'upper_slope': upper_slope,
                'lower_slope': lower_slope,
                'upper_boundary': upper_coeffs[0] * dur + upper_coeffs[1],
                'lower_boundary': lower_coeffs[0] * dur + lower_coeffs[1],
                'prior_direction': prior_direction,
                'prior_move_atr': prior_move_atr,
                'slopes_against_trend': slopes_against,
                'expected_breakout': prior_direction,  # continuation
            })

    # Deduplicate overlapping flags (keep longest)
    flags.sort(key=lambda f: f['duration_bars'], reverse=True)
    used_dates = set()
    unique_flags = []
    for f in flags:
        dates = set(pd.date_range(f['start_date'], f['end_date']))
        if not dates & used_dates:
            unique_flags.append(f)
            used_dates |= dates

    return unique_flags


def classify_flag_context(df: pd.DataFrame, flag: dict,
                          range_lookback: int = 60) -> str:
    """
    Classify flag context for enhanced significance.

    Returns one of:
    - 'near_range_top'    → very bullish (Ch.5 p.92)
    - 'above_range'       → breakout confirmation (Ch.5 p.92)
    - 'near_range_bottom' → very bearish
    - 'below_range'       → breakdown confirmation
    - 'pullback_into_range' → top/bottom signal (Rule #57)
    - 'mid_trend'         → standard continuation
    """
    start_idx = df.index.get_loc(flag['start_date'])
    range_window = df.iloc[max(0, start_idx - range_lookback):start_idx]

    if len(range_window) < 10:
        return 'mid_trend'

    range_high = range_window['high'].max()
    range_low = range_window['low'].min()
    range_size = range_high - range_low

    if range_size == 0:
        return 'mid_trend'

    flag_mid = (flag['upper_boundary'] + flag['lower_boundary']) / 2

    # Flag position relative to the range
    position = (flag_mid - range_low) / range_size

    if flag_mid > range_high:
        return 'above_range'
    elif flag_mid < range_low:
        return 'below_range'
    elif position > 0.85:
        return 'near_range_top'
    elif position < 0.15:
        return 'near_range_bottom'
    else:
        return 'mid_trend'


def check_flag_failed_signal(df: pd.DataFrame, flag: dict,
                              lookforward: int = 15) -> dict | None:
    """
    Check for two types of failed flag signals (Chapter 11):

    Type 1: Counter-to-anticipated breakout
      Flag breaks in the opposite direction of the prior trend.

    Type 2: Opposite direction breakout after normal breakout
      Flag breaks in expected direction, then reverses past the
      opposite boundary (close beyond opposite extreme).

    Returns dict with failure info or None.
    """
    end_idx = df.index.get_loc(flag['end_date'])
    upper = flag['upper_boundary']
    lower = flag['lower_boundary']

    for i in range(end_idx + 1, min(end_idx + 1 + lookforward, len(df))):
        curr_close = df.iloc[i]['close']

        # Type 1: Counter-to-anticipated breakout
        if flag['prior_direction'] == 'up' and curr_close < lower:
            return {
                'type': 'counter_to_anticipated',
                'date': df.index[i],
                'close': curr_close,
                'breakout_direction': 'down',
                'note': ('Flag in uptrend broke DOWN. '
                         'More reliable than original signal. '
                         'Remains valid unless close > upper boundary.'),
            }
        elif flag['prior_direction'] == 'down' and curr_close > upper:
            return {
                'type': 'counter_to_anticipated',
                'date': df.index[i],
                'close': curr_close,
                'breakout_direction': 'up',
                'note': ('Flag in downtrend broke UP. '
                         'More reliable than original signal. '
                         'Remains valid unless close < lower boundary.'),
            }

    # Type 2: Check for normal breakout followed by reversal
    normal_breakout_seen = False
    for i in range(end_idx + 1, min(end_idx + 1 + lookforward, len(df))):
        curr_close = df.iloc[i]['close']

        if not normal_breakout_seen:
            if flag['prior_direction'] == 'up' and curr_close > upper:
                normal_breakout_seen = True
            elif flag['prior_direction'] == 'down' and curr_close < lower:
                normal_breakout_seen = True
        else:
            # After normal breakout, check for reversal past opposite end
            if flag['prior_direction'] == 'up' and curr_close < lower:
                return {
                    'type': 'opposite_after_normal',
                    'date': df.index[i],
                    'close': curr_close,
                    'breakout_direction': 'down',
                    'note': ('Flag broke up (normal), then reversed below lower '
                             'boundary. Original breakout was a trap.'),
                }
            elif flag['prior_direction'] == 'down' and curr_close > upper:
                return {
                    'type': 'opposite_after_normal',
                    'date': df.index[i],
                    'close': curr_close,
                    'breakout_direction': 'up',
                    'note': ('Flag broke down (normal), then reversed above upper '
                             'boundary. Original breakout was a trap.'),
                }

    return None
```

## Decision Framework

```
Flag detected in existing trend
     │
     ├─ Where does it sit? (classify_flag_context)
     │     ├─ Near range top/above range → ENHANCED bullish
     │     ├─ Near range bottom/below range → ENHANCED bearish
     │     ├─ Pullback into prior range → TOP/BOTTOM signal
     │     └─ Mid-trend → standard continuation
     │
     ├─ Entry strategy
     │     ├─ Schwager preferred: enter DURING formation
     │     │    • Better price, probability already favors continuation
     │     │    • Stop: opposite extreme of flag + margin
     │     │
     │     └─ Conservative: wait for breakout
     │          • Worse price, slightly more confirmation
     │          • Stop: same — opposite extreme + margin
     │
     ├─ Breakout occurs
     │     ├─ In expected direction → hold, trail stop
     │     │
     │     └─ Counter-to-anticipated → FAILED SIGNAL
     │           • More reliable than original
     │           • Trade in breakout direction
     │           • Valid unless close past opposite boundary
     │
     └─ After normal breakout
           ├─ Follow-through → trend continues
           └─ Reversal past opposite boundary → TRAP
                 • Second type of failed signal
                 • Requires close (not just intraday touch)
```

## Connections

- [[Triangles]] — longer-duration version of similar convergence concept
- [[Pennants]] — converging-lines variant of the flag (same duration, same logic)
- [[Wide-Ranging Days]] — wide-ranging day within or near a flag adds significance
- [[Breakout Confirmation]] — all three confirmation methods apply to flag breakouts
- Chapter 11 failed signals — flags produce two distinct failure types, both high-value
- Chapter 9 (stop placement) — opposite extreme of flag is a natural stop
