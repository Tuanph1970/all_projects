# Concept 7 — Blind Simulation (Walk-Forward Testing)

**Tags:** #ch15 #methodology #solution

## Definition

A **blind simulation** chooses the parameter set using only data from a *prior* time window, then evaluates performance on a *subsequent* window the selection process never saw. Repeat the process by sliding the windows forward — also called **walk-forward testing**.

The non-negotiable rule: **simulation and optimization periods must never overlap.** If they do, you're not testing — you're peeking at the answers.

## Illustration

![[07_blind_simulation.png]]

Three folds. Each blue bar is the "optimize on this window" period; each red bar is the locked-in test period that follows. Parameter set chosen from each blue is then evaluated on its red. No overlap, ever.

## Analogy

You're tutoring a student for a math exam. You give them practice problems on Monday (in-sample), then a *different* set of problems on Tuesday (out-of-sample). If they ace Tuesday, you know they learned. If you'd given them Monday's problems again on Tuesday, you'd know nothing.

In ML/data-science vocabulary: blind simulation **is** the train/validation/test split — applied along the time axis instead of randomly.

## Numeric example

From `code/concept_07_blind_simulation.py`, three rolling folds on synthetic price data:

```
Fold       Best N (in-sample)       OOS P&L
1985-1992                  18         +18.42
1987-1994                  41         +12.07
1989-1996                  29          -3.11
```

Notice that the "best N" is **different in every fold** (18, 41, 29). This is parameter shift in action. The walk-forward results show what you'd realistically have made — a mix of wins and losses, with the OOS numbers usually much smaller than the in-sample optimization implied.

## Source code

[[code/concept_07_blind_simulation.py]]

## Relationships

### Within the chapter
- One of the **two** methods Schwager endorses for honest system evaluation. The other is [[08_Average_Parameter_Set_Performance]].
- Directly counters [[01_Well_Chosen_Example]] (no cherry-picking possible because future data is locked) and [[06_Testing_vs_Fitting]] (selection and evaluation are separated in time).
- Reveals **parameter shift** (Ch. 14, problem #9) as a structural feature, not a bug — different folds choose different "best" parameters.

### Comparison: blind simulation vs. average parameter set
| Dimension | Blind simulation | [[08_Average_Parameter_Set_Performance|Average param set]] |
|---|---|---|
| Realism | Closer to actual trading | Conservative |
| Compute cost | Higher (re-optimize per fold) | Lower (single sweep) |
| Best for | Final go/no-go evaluation | Quick robustness check |
| Risk of self-deception | Low | Lowest |

Schwager: "**Both** are valid procedures."

### Outside the chapter
- [[Chapter_13_Charting_Software]] — software that doesn't support walk-forward should be replaced.
- ML practice — this is **time-series cross-validation**, identical in spirit. Use `TimeSeriesSplit` from sklearn for similar workflows.
