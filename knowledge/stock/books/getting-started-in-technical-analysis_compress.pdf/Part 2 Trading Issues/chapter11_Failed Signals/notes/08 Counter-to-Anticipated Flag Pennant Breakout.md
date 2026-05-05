# 08 Counter-to-Anticipated Flag Pennant Breakout

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #flag #pennant

## Definition

Flags and pennants are short-term consolidation patterns (one to three weeks) that form **inside** an existing trend. The textbook expectation is that they resolve in the *same direction* as the prior trend — so a flag that forms after a strong up-leg should break upward, and a flag after a sharp down-leg should break downward.

A **counter-to-anticipated breakout** is a flag or pennant that resolves the **wrong way** — breaking opposite to the preceding trend. Schwager finds this kind of failure to be among the highest-quality reversal signals on a chart, often providing extraordinarily timely warnings of major trend turns.

**Confirmation rule:** wait for a *close* beyond the relevant boundary (not just an intraday touch). The reversal interpretation stays in force as long as price doesn't later close back beyond the *opposite* end of the flag.

## Illustration

![[08_counter_anticipated_flag.png]]

The book's **Figures 11.19–11.23** show this on July 1992 cotton, December 1994 soybean oil, March 1994 cotton, March 1992 cocoa, and March 1993 cotton. Several of these called major trend reversals to within a few days.

## Common-life analogy

A jogger has been running uphill for ten minutes (the strong prior trend). They pause at a landing to catch their breath (the flag). The expected next move is to keep running uphill. If instead they sit down and start walking *back down* the hill, the pause wasn't a recovery — it was the moment they decided to abandon the hike. The change of direction during what looked like a "rest" is the most informative possible signal about how the rest of the hike will go.

## Numeric example

Stock has rallied from $40 to $58 over four weeks (strong uptrend). It then forms a pennant for ten trading days with a converging triangle bounded by:

- Upper boundary at $58.50 (sloping down to ~$57.80)
- Lower boundary at $56.40 (sloping up to ~$57.20)

**Day 11**: closes at $55.90 — *below* the lower pennant boundary. This is the counter-to-anticipated breakout. Schwager-confirmation is satisfied because it's a close, not an intraday wick.

Trade plan: short on Day 11 close at $55.90, stop at $58.60 (just above the pennant high). Risk = $2.70. The "remains-in-force" rule keeps the bearish bias as long as no future close pierces $58.50. Pennant size is roughly $2; counter-trend extensions of 3–5× pattern height are common, so a $46–48 target is reasonable.

## Python sketch

```python
def counter_anticipated_flag(df, flag_start, flag_end, upper, lower, prior_trend,
                             lookahead=20):
    """
    prior_trend: 'up' if a strong rally preceded the flag, 'down' if a slide.
    Yields the index of the first close that breaks the flag in the OPPOSITE
    direction to the prior trend.
    """
    expected = "up" if prior_trend == "up" else "down"
    for j in range(flag_end + 1, min(flag_end + 1 + lookahead, len(df))):
        c = df["close"].iloc[j]
        if expected == "up" and c < lower:
            yield j; return
        if expected == "down" and c > upper:
            yield j; return
```

Full version: `code/chapter11_detectors.py` → `detect_flag_failures()`.

## Relationships within the chapter

- **Direct sibling** of [[09 Opposite-Direction Breakout After Normal Breakout]] — both involve flags/pennants and both fail through closes beyond the opposite boundary; the difference is *when* the failure happens (immediately, vs. after a normal-direction break first).
- Uses [[03 Confirmation Conditions]] (close-beyond-boundary form, similar to [[02 Bull and Bear Traps]]).
- A counter-to-anticipated flag failure that occurs near a multi-month spike or WRD strengthens the read of [[06 Return to Spike Extremes]] / [[07 Return to Wide-Ranging Day Extremes]].

## When the concept works best

- **After a long, strong prior trend.** The longer the up- (or down-) leg, the more meaningful a "wrong-way" flag break.
- **Near an obvious target zone** (round number, prior major high/low). The market is more likely to fail-flip when it's already encroached on a structural barrier.
- **Tight, well-formed flags.** A clear, narrow pennant with two parallel touches per side gives a clean break level; a sloppy "maybe-flag" generates whipsaws.

## Relationships outside the chapter

- Flag/pennant geometry, plus the standard "continuation" reading: [[Chapter 5 - Chart Patterns]].
- Schwager's **Rule #62** in [[Chapter 17 - Eighty-Two Trading Rules]] explicitly cites a flag breaking against the prior trend as a major reversal candidate.
- Multiple worked examples of flag and pennant failures appear inside the chart-by-chart commentary of [[Chapter 12 - Real World Chart Analysis]].
