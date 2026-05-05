# 09 Opposite-Direction Breakout After Normal Breakout

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #flag #two-stage

## Definition

This is the **two-stage failure** of a flag or pennant. A flag forms inside a trend, prices break out *in the expected direction* (continuation), and then — instead of running — they reverse and **close beyond the opposite end** of the flag. The combined sequence (normal break → reversal → close past opposite extreme) qualifies as a failed signal even though the original breakout looked correct.

The crucial confirmation rule is **close beyond the opposite extreme, not merely an intraday penetration**. This stricter rule sacrifices a few points of timeliness in exchange for far fewer false calls.

## Illustration

![[09_opposite_after_normal.png]]

In the book, **Figure 11.24** (DuPont) and **Figure 11.25** (December 1992 coffee) and **Figure 11.26** (April 1992 heating oil) all show this pattern, with Figure 11.26 containing both a counter-to-anticipated break (concept 8) at the top *and* an opposite-direction-after-normal-break (this concept) at the bottom of the same chart.

## Common-life analogy

Picture a long-distance relay race. The team has been ahead for the whole leg. Their runner takes the baton at the handover (normal continuation breakout — they're sticking with the lead). After fifty meters they stumble, drop the baton, and trip another runner — by the time the chaos clears, they're a hundred meters *behind* where they handed off. That handoff wasn't a continuation of the lead; it was the moment the team's lead actually ended. The first fifty meters confirmed nothing — it was the **closing position past the start line of the leg** that revealed the truth.

## Numeric example

Stock rallies from $40 to $58 (strong uptrend), then forms a flag with:
- Upper boundary $58.50
- Lower boundary $56.40

**Day 11–13** — close $59.20, $59.80, $59.50 → normal upside breakout (looks bullish).
**Day 16** — close $57.10 (back inside the flag).
**Day 19** — close $55.80 → **below the flag's lower boundary**. This is the failed-signal confirmation. The original $59 breakout is now repudiated.

Short entry at $55.80 with stop above the flag high ($58.60). Risk = $2.80. Counter-trend extensions of 3–5× the flag height (~$2) imply targets in the $46–50 zone.

## Python sketch

```python
def opposite_after_normal(df, flag_end, upper, lower, prior_trend, lookahead=30):
    """Return idx of failure or None.

    State machine:
        inside  -> price still inside flag
        normal  -> closed beyond expected boundary (continuation)
        failed  -> from normal, closed beyond opposite boundary
    """
    state = "inside"
    expected_up = (prior_trend == "up")
    for j in range(flag_end + 1, min(flag_end + lookahead + 1, len(df))):
        c = df["close"].iloc[j]
        if state == "inside":
            if expected_up and c > upper:    state = "normal_up"
            elif not expected_up and c < lower: state = "normal_down"
        elif state == "normal_up" and c < lower:
            return j                         # failed!
        elif state == "normal_down" and c > upper:
            return j
    return None
```

## Relationships within the chapter

- The **paired sibling** of [[08 Counter-to-Anticipated Flag Pennant Breakout]]: same pattern (flag), same eventual failure direction, but distinguished by whether the failure shows up *before* or *after* an initial normal breakout.
- Uses [[03 Confirmation Conditions]], specifically the strong-price form (close beyond opposite extreme).
- Conceptually similar to [[10 Penetration of Top and Bottom Formations]] — both reverse a *previously valid* technical signal once the opposite-extreme close comes in.

## When the concept works best

- **At extended trend extremes** where a "last gasp" continuation breakout sucks in the late buyers (or sellers) before the reversal.
- **In markets with frequent micro-breakouts.** The two-stage rule filters out flags that simply break, pull back, and break again — only fully reversing flags trigger.
- **Stop-placement is unusually clean:** the flag high/low is a natural risk reference point.

## Relationships outside the chapter

- Flag and pennant anatomy: [[Chapter 5 - Chart Patterns]].
- The "false breakout" cousin in horizontal ranges is [[02 Bull and Bear Traps]] (Chapter 11) but is also referenced explicitly in [[Chapter 17 - Eighty-Two Trading Rules]] (rule cluster 56–58, 62).
- Schwager treats this as a **timing refinement** for traders who want better-than-counter-anticipated entries; that timing-vs-quality theme threads through [[Chapter 9 - Stop Loss Points]] and [[Chapter 10 - Setting Objectives]].
