# Concept 8 — Average Parameter Set Performance

**Tags:** #ch15 #methodology #solution

## Definition

An honest alternative to walk-forward: define your complete list of parameter sets to test **before** running any simulation, then report the **average** result across **all** of them — not just the profitable ones.

The discipline is in the up-front commitment. You can't run the sweep, see the results, and then "decide which sets are worth averaging." Every set you considered counts, including the losers.

## Illustration

![[08_avg_parameter_set.png]]

Blue bars: in-sample returns (sorted, best on the left). Orange bars: same parameter sets evaluated out-of-sample. The red dashed line shows what you'd have realized by trading the in-sample winner — usually disappointing. The green dashed line shows the honest mean across all sets.

## Analogy

You want to know if a coin is fair. You flip it 100 times and split the flips into 10 groups of 10. *One* group came up 9 heads. If you only report that group, the coin looks rigged. The honest answer is the average of all 10 groups, which is ~50%.

Same idea: pre-commit to your parameter list, then trust the mean.

## Numeric example

From `code/concept_08_avg_parameter_set.py`, on synthetic data:

```
Number of parameter sets : 24
Best (cherry-picked)     : (50, 0.0) -> +0.0481
Worst                    : -0.0237
AVERAGE across all sets  : +0.0089   <-- honest estimate
% of sets profitable     : 71%
```

The cherry-picked set looks like 5x the average. Trade the average — that's what you should expect over time. (And note the "% profitable" — if it's barely above 50%, the system has no edge regardless of how good the best set looks.)

## Source code

[[code/concept_08_avg_parameter_set.py]]

## Relationships

### Within the chapter
- The simpler sibling of [[07_Blind_Simulation]]. Both are endorsed by Schwager; this one needs less compute and less coding.
- Directly disarms [[06_Testing_vs_Fitting]] — averaging removes the act of selection.
- An empirical justification for Schwager's chapter takeaway #5: *"trade a number of diversified parameter sets rather than a single optimized set."* If the best set isn't reliably better than the average, why bet on it?

### When to use which
| Situation | Pick |
|---|---|
| Need a fast first cut on whether a system has edge | Average parameter set |
| Need a defensible final estimate before committing capital | Blind simulation |
| Limited data (can't afford to split it many ways) | Average parameter set |
| Long history available (10+ years) | Either, walk-forward preferred |

### Outside the chapter
- [[Chapter_14_Trend_Following_Systems]] — solution to "parameter shift" (problem #9): trade several sets, not one.
- General quant practice — this is **ensembling** along the parameter dimension. Same intuition as bagging in ML, applied to one model with many hyperparameter values.
