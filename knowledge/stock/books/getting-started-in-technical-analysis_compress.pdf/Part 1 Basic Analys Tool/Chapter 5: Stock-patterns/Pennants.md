---
tags: [technical-analysis, schwager, continuation-pattern, pennants]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.87-93; Chapter 11 pp.165-171; Chapter 12 pp.202-206"
related: ["[[Flags]]", "[[Triangles]]", "[[Continuation Patterns MOC]]"]
---

# Pennants

## Definition

A **pennant** is a narrow-band, short-duration (1-3 weeks) congestion phase within a trend, enclosed by **converging lines**. It is the converging-boundary sibling of the [[Flags|flag]].

> Pennants may appear to be similar to triangles, but they differ in terms of time: the triangle has a longer duration. — Schwager

## The One Structural Difference From Flags

| | Flag | Pennant |
|---|---|---|
| Upper boundary | Parallel to lower | Converges toward lower |
| Lower boundary | Parallel to upper | Converges toward upper |
| Shape | Parallelogram / channel | Small triangle / wedge |

That's it. Everything else — duration, trading logic, entry strategy, stop placement, failed signals, context significance — is **identical**. Schwager consistently writes "flags and pennants" as a single unit throughout the book.

## Analogy

If a flag is a runner pausing to tie their shoe (a flat pause), a pennant is the runner slowing to a walk, taking shorter and shorter steps, then suddenly sprinting again. The energy is compressing — each oscillation gets smaller until the pattern can't contain it anymore and the trend erupts.

## Why Schwager Doesn't Separate Them

Schwager never gives a pennant its own section. Every rule, every trading principle, every failed-signal type applies equally to both. His reasoning is practical: the distinction between parallel and converging lines is often ambiguous on real charts, and **flags can morph into pennants as they evolve** (Trade 12.11, copper). If your boundaries start parallel and then converge over the next few days, was it a flag or a pennant? The answer doesn't change what you do.

## The Shape-Shift Problem

This is Schwager's most practical insight about the flag/pennant distinction:

> Flag and pennant consolidations frequently change their shape as they evolve. It is also quite common for such consolidations to be interrupted by one-day spikes.

**Implication for detection code**: Don't classify too early. A pattern that looks like a flag on day 5 may look like a pennant by day 10. For algorithmic detection, the better approach is to detect "narrow short-duration consolidation within a trend" as a single category, then optionally classify the boundary geometry (parallel vs. converging) as a secondary attribute — not as the primary filter.

**Implication for stop placement**: Don't anchor stops to the *original* boundary. The pattern may widen, narrow, or tilt as it evolves. Use a margin beyond the *current* boundary, and update it as the pattern develops.

## Everything That Carries Over From [[Flags]]

All of these apply identically to pennants:

- **Entry strategy**: Enter during formation, don't wait for breakout (Schwager's preference)
- **Stop placement**: Opposite extreme of formation + meaningful margin
- **Near support/resistance**: Pennant near top of trading range = very bullish (Fig 5.26 — specifically shows a pennant above a trading range as precursor to an explosive advance)
- **Failed signal type 1**: Counter-to-anticipated breakout (Fig 11.23 — pennant in March 1993 cotton)
- **Failed signal type 2**: Opposite direction breakout after normal breakout (Fig 11.25 — pennant in December 1992 coffee)
- **Invalidation rule**: Failed signal remains valid unless close beyond the opposite end of the pennant
- **Two successive patterns**: Two flags/pennants with little separation = probable continuation (Rule #73)

## Real-World Trading Lesson (Chapter 12)

### Trade 12.12: Crude oil — Pennant near range low

- **Setup**: Pennant consolidation near the low end of a trading range + wide downside gap preceding the pennant
- **Entry**: Short, anticipating downside continuation
- **Result**: Loss — the market rebounded, turning the pennant low into a bear trap
- **What happened next (Trade 12.13)**: Schwager reversed position on the failure signals (bear trap + wide-ranging up day), captured a large gain
- **Lesson**: *"Flexibility in recognizing a trade was wrong and reversing the original position made it possible to capture a large gain in a trade sequence that began by going short at the virtual market bottom."*

This is the Chapter 11 failed-signal principle in action — the failure of the pennant signal was more valuable than the original signal would have been if it had worked.

## Python Detection

Since Schwager treats flags and pennants as a single pattern family, the detection code is a unified function that classifies boundary geometry as a secondary attribute.

```python
def detect_flag_or_pennant(df: pd.DataFrame,
                           min_duration: int = 5,
                           max_duration: int = 15,
                           max_width_atr: float = 2.0,
                           min_prior_move_atr: float = 3.0,
                           prior_move_lookback: int = 20,
                           atr_period: int = 14,
                           convergence_threshold: float = 0.3) -> list[dict]:
    """
    Detect flags AND pennants as a single pattern family.

    The only difference is boundary geometry:
    - Flag: upper_slope ≈ lower_slope (parallel)
    - Pennant: slopes converge (difference exceeds threshold)

    This matches Schwager's treatment: same logic, same rules,
    same failed-signal types. Shape classification is a secondary
    attribute, not a primary filter.

    Parameters
    ----------
    convergence_threshold : float
        Ratio of slope difference to average absolute slope.
        Below this → flag (parallel). Above this → pennant (converging).
        Set to 0.3 as default — deliberately loose, because the
        distinction is fuzzy and patterns morph over time.
    """
    import numpy as np
    from breakout_confirmation import compute_true_range

    tr = compute_true_range(df)
    adtr = tr.rolling(atr_period).mean()

    patterns = []

    for end_i in range(prior_move_lookback + max_duration, len(df)):
        curr_adtr = adtr.iloc[end_i]
        if pd.isna(curr_adtr) or curr_adtr == 0:
            continue

        for dur in range(min_duration, max_duration + 1):
            start_i = end_i - dur
            window = df.iloc[start_i:end_i + 1]
            highs = window['high'].values
            lows = window['low'].values

            # Narrow band check
            width = highs.max() - lows.min()
            if width > max_width_atr * curr_adtr:
                continue

            # Fit boundary lines
            x = np.arange(len(window), dtype=float)
            upper_slope = np.polyfit(x, highs, 1)[0]
            lower_slope = np.polyfit(x, lows, 1)[0]

            # Must converge or be roughly parallel (not diverge)
            if upper_slope > lower_slope + 0.01 * curr_adtr:
                continue  # Diverging → not a flag or pennant

            # Prior move check
            prior = df.iloc[start_i - prior_move_lookback:start_i]
            prior_move = prior['close'].iloc[-1] - prior['close'].iloc[0]
            if abs(prior_move) / curr_adtr < min_prior_move_atr:
                continue

            # Classify: flag vs pennant
            avg_abs_slope = (abs(upper_slope) + abs(lower_slope)) / 2
            if avg_abs_slope > 0:
                convergence_ratio = abs(upper_slope - lower_slope) / avg_abs_slope
            else:
                convergence_ratio = abs(upper_slope - lower_slope)

            if convergence_ratio <= convergence_threshold:
                shape = 'flag'
            else:
                # Verify converging (not diverging)
                if upper_slope < lower_slope:
                    shape = 'pennant'
                else:
                    continue

            prior_dir = 'up' if prior_move > 0 else 'down'

            # Compute current boundaries (at end of pattern)
            upper_coeffs = np.polyfit(x, highs, 1)
            lower_coeffs = np.polyfit(x, lows, 1)
            upper_boundary = upper_coeffs[0] * dur + upper_coeffs[1]
            lower_boundary = lower_coeffs[0] * dur + lower_coeffs[1]

            patterns.append({
                'start_date': df.index[start_i],
                'end_date': df.index[end_i],
                'shape': shape,  # 'flag' or 'pennant'
                'duration_bars': dur,
                'width': width,
                'width_atr': width / curr_adtr,
                'upper_slope': upper_slope,
                'lower_slope': lower_slope,
                'convergence_ratio': convergence_ratio,
                'upper_boundary': upper_boundary,
                'lower_boundary': lower_boundary,
                'prior_direction': prior_dir,
                'prior_move_atr': abs(prior_move) / curr_adtr,
                'expected_breakout': prior_dir,
            })

    # Deduplicate overlapping patterns (keep longest)
    patterns.sort(key=lambda p: p['duration_bars'], reverse=True)
    used = set()
    unique = []
    for p in patterns:
        dates = set(pd.date_range(p['start_date'], p['end_date']))
        if not dates & used:
            unique.append(p)
            used |= dates

    return unique
```

## The Context Classifier and Failed-Signal Checker

Both `classify_flag_context()` and `check_flag_failed_signal()` from the [[Flags]] note work identically for pennants — just pass the pennant dict in place of the flag dict. The field names are the same (`upper_boundary`, `lower_boundary`, `prior_direction`, etc.).

## Connections

- [[Flags]] — parallel-boundary sibling; shares ALL trading rules
- [[Triangles]] — longer-duration converging pattern; different significance
- [[Breakout Confirmation]] — all three confirmation methods apply
- Chapter 11 — failed pennant signals: Fig 11.23 (counter-to-anticipated), Fig 11.25 (opposite after normal)
- Chapter 12 — Trade 12.12/12.13: pennant failure → reversal → large gain (the flexibility lesson)
