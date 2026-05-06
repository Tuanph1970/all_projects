# Concept 5 — Optimization (and Parameter Stability)

**Tags:** #ch15 #methodology #pitfall

## Definition

**Optimization** is the process of searching for the parameter set(s) that performed best on past data, with the (often unjustified) assumption that those parameters will also perform best in the future.

When ranking candidate parameter sets, Schwager argues you must consider **four factors** — not just total profit:

1. **Percent return** — measured against capital required, not absolute dollars.
2. **Risk measure** — equity-curve volatility, max drawdown, retracements.
3. **Parameter stability** — does performance hold steady across nearby parameter values, or does it cliff-edge?
4. **Time stability** — see [[03_Time_Stability]].

**Parameter stability** specifically: prefer a *broad plateau* of decent performance to an *isolated spike*. A spike that disappears one tick away is almost certainly noise.

## Illustration

![[05_parameter_stability.png]]

Profit landscape across (short_MA, long_MA) combinations. The black-circled spike is a fluke — its neighbors all underperform. The blue-circled plateau is the right place to draw your parameter set from, even though its peak is lower.

## Analogy

You're choosing a campsite. Site A is a single flat patch of ground surrounded by sharp rocks — sleep there, but roll over once in your tent and you're in pain. Site B is a wide grassy field — flat in every direction. The peak comfort might be marginally lower at Site B, but you'll *actually be comfortable* anywhere on it. Pick the field.

## Numeric example

From `code/concept_05_optimization.py`:

```
Strategy 1 — naive peak picker:
  best (short, long) = (5, 25),  in-sample profit = $145

Strategy 2 — neighborhood-aware (robust) picker:
  best (short, long) = (10, 50),  plateau score = $93
```

Strategy 1 picks the dazzling fluke. Strategy 2 picks a slightly less dazzling but reproducible region. Out-of-sample, strategy 2 wins ~80% of the time in this kind of synthetic experiment.

## Schwager's empirical conclusions about optimization

1. **Any** system can be made to look profitable through optimization.
2. Optimization **always overstates** future performance — usually by a wide margin.
3. For most systems, optimization improves future performance only marginally, if at all.
4. Optimization's real value is defining **boundary ranges** to avoid, not pinpointing a winner.
5. Sophisticated optimization adds nothing over simple optimization.

## Source code

[[code/concept_05_optimization.py]]

## Relationships

### Within the chapter
- The setup for [[06_Testing_vs_Fitting]] — most over-fitting failures start with naive optimization.
- Solved by [[07_Blind_Simulation]] (walk-forward) and [[08_Average_Parameter_Set_Performance]] (don't pick a winner — average them all).
- Distortion method #5 in [[09_Schwagers_Corollary]].

### When is optimization legitimately useful?
- Eliminating obviously-bad parameter ranges before testing.
- Sanity-checking that a system has a plausible operating range.
- **Not** for picking the parameter set you'll trade — that should come from a robustness criterion (plateau, walk-forward, average).

### Outside the chapter
- [[Chapter_14_Trend_Following_Systems]] — "parameter shift" (problem #9) is what happens when you optimized too aggressively.
- [[Chapter_13_Charting_Software]] — modern software makes parameter-grid sweeps effortless, which is exactly why this discipline matters more, not less.
