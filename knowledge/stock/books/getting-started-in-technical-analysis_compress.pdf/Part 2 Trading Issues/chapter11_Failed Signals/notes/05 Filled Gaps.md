# 05 Filled Gaps

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #gap

## Definition

A **gap** is a price discontinuity (today's low above yesterday's high, or today's high below yesterday's low). Gaps are normally read as *continuation* signals — the market expects the trend in the direction of the gap to keep going. A **filled gap** therefore qualifies the original gap as a **failed signal**: price has retraced through the empty space, contradicting the gap's continuation message and often presaging a meaningful reversal.

Schwager prefers a **strict fill definition**: the close must move *beyond the close of the day prior to the gap day* (an upside gap is filled when a later close sinks below the pre-gap close; a downside gap is filled when a later close exceeds it). This is more restrictive than the common "intraday touch" definition and produces fewer false calls.

**The gap fail is more potent when:**
- the filled gap is wide,
- it was a **breakaway gap** (out of consolidation),
- two or more consecutive gaps are filled.

## Illustration

![[05_filled_gaps.png]]

The book's **Figures 11.8–11.12** show real fills on sugar, cotton, crude oil, and Apple Computer — including the case (Fig 11.10) where a huge upside gap took **two months** of sideways drift before completing the fill.

## Common-life analogy

A friend leaps over a puddle in the path. Normally that means they're committed to crossing — they're going forward. But if a few minutes later you see them step *back* across the puddle and through the spot where they leapt from, the leap meant nothing; whatever they were chasing was on the original side after all. The wider the puddle they leapt, the more meaningful it is when they walk back across it.

## Numeric example

Stock closes Monday at **$48.00** (the prior close).
Tuesday opens at **$50.20** (gap up — Monday's high was $48.50, Tuesday's low is $50.20). Stock rallies to $52 over the next three days.

- **Day 8** — closes $49.10. By the *intraday-touch* definition the gap is filled (we touched $48.50). Schwager's stricter rule says: not yet.
- **Day 11** — closes $47.85. **Below the pre-gap close of $48.00** → confirmed filled gap.

Trade plan: short on Day 11 close, stop above the gap-day high ($50.50). The "remains-in-force" rule keeps the bearish bias as long as price doesn't close back **above** the gap.

## Python sketch

```python
def detect_filled_gaps(df, lookahead=30):
    """Schwager-strict definition: a fill requires close beyond the pre-gap close."""
    out = []
    for i in range(1, len(df) - 1):
        prev_close = df["close"].iloc[i - 1]
        prev_high  = df["high"].iloc[i - 1]
        prev_low   = df["low"].iloc[i - 1]
        # upside gap
        if df["low"].iloc[i] > prev_high:
            for j in range(i + 1, min(i + lookahead + 1, len(df))):
                if df["close"].iloc[j] < prev_close:
                    out.append(("up", df.index[i], df.index[j])); break
        # downside gap
        elif df["high"].iloc[i] < prev_low:
            for j in range(i + 1, min(i + lookahead + 1, len(df))):
                if df["close"].iloc[j] > prev_close:
                    out.append(("down", df.index[i], df.index[j])); break
    return out
```

Full version in `code/chapter11_detectors.py`.

## Relationships within the chapter

- Filled gaps are the **gap-class** member of the [[01 Failed Signals]] family.
- Uses [[03 Confirmation Conditions]] in the form of "close beyond the pre-gap close."
- Often co-occurs with [[07 Return to Wide-Ranging Day Extremes]] — Schwager notes that the fill-day is itself often a wide-ranging bar (a double-strength signal).
- A filled gap that occurs together with [[06 Return to Spike Extremes]] or [[10 Penetration of Top and Bottom Formations]] strengthens the case for a major reversal.

## When the concept works best

- **Breakaway gaps** at the start of a move: their failure is the strongest of the four gap subtypes.
- **Two consecutive gaps in the same direction, both filled** — interpreted as a near-certain trend transition.
- **Long sideways fills** (Schwager's two-month sugar example): patience after the gap is rewarded; you don't have to act on intraday wicks.

## Relationships outside the chapter

- Gap taxonomy (common, breakaway, runaway, exhaustion): [[Chapter 5 - Chart Patterns]].
- Island reversals (a special two-gap structure) connect to this concept and to [[10 Penetration of Top and Bottom Formations]].
- Rule #69 in [[Chapter 17 - Eighty-Two Trading Rules]] echoes the same idea.
- Where to place the protective stop after a filled-gap entry: [[Chapter 9 - Stop Loss Points]].
