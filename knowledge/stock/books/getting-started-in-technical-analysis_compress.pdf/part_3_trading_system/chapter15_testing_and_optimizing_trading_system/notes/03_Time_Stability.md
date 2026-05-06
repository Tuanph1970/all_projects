# Concept 3 — Time Stability

**Tags:** #ch15 #performance-evaluation #risk

## Definition

**Time stability** is how *consistent* a system's performance is across sub-periods within the test window. A system that earned a 15-year average return because of three spectacular years and 12 mediocre years has poor time stability. A system that was profitable in 14 of 15 years has high time stability — and is far more trustworthy.

It's distinct from *parameter stability* (consistency across parameter sets at a single point in time). Time stability asks: **does the same parameter set work next year that worked last year?**

## Illustration

![[03_time_stability.png]]

Both systems produce roughly the same cumulative return over 15 years. System A is "lumpy" (3 hero years carry the rest); System B is steady. Most traders rationally prefer B — and Schwager argues you should too, because you can't pick when to start.

## Analogy

Two restaurants both average 4 stars over a year. One has 200 reviews of {5, 5, 5, 1, 5, 5, 1, …} (every now and then somebody gets food poisoning). The other has 200 reviews of {4, 4, 4, 4, 4, …}. Same average, dramatically different reliability. Which one do you bring your in-laws to?

## Numeric example

From `code/concept_03_time_stability.py`:

```
System A (3 hero years carry the rest)
  cumulative return   :  175.5%
  % positive years    :   60.0%
  worst single year   :   -5.4%
  coef. of variation  :   1.85   (lower = more time-stable)

System B (steady winner)
  cumulative return   :  159.0%
  % positive years    :   93.3%
  worst single year   :   -3.0%
  coef. of variation  :   0.43
```

Same ballpark cumulative return; the standard error per year (coefficient of variation) for A is **4× higher**. Start B at any point in the 15 years and you'd likely be happy. Start A right before its 12-year flat stretch and you'd quit.

## Source code

[[code/concept_03_time_stability.py]]

## Relationships

### Within the chapter
- One of the four [[05_Optimization|performance comparison factors]] (alongside Percent Return, Risk Measure, and Parameter Stability).
- Schwager's recommendation: test on 10–20 years and explicitly evaluate sub-periods (e.g., individual years). This is why test windows shorter than ~5 years should be suspect.
- **Linked to [[07_Blind_Simulation]]** — walk-forward inherently checks time stability because each fold tests a different period.

### When does this matter most?
For systems you'll deploy with real money. For research/exploration it's fine to skip. But once you're sizing a position, time stability tells you the **psychological survivability** of the system — the worst single year is what you'll actually have to live through.

### Outside the chapter
- [[Chapter_14_Trend_Following_Systems]] — "temporary large losses" (problem #6) are essentially time-stability failures.
- [[Chapter_16_Planned_Trading_Approach]] — capital allocation depends on knowing the worst expected drawdown.
- [[Chapter_18_Market_Wizardom]] — top traders almost universally cite "consistency over flash" as critical.
