# Concept 2 — Parameter & Parameter Set

**Tags:** #ch15 #vocabulary #foundations

## Definition

- **Trading system:** a complete set of rules for generating buy and sell signals.
- **Parameter:** any value within those rules that you can freely change to alter the *timing* of signals (without changing the rules themselves). Example: in a breakout system, `N` (the lookback length).
- **Parameter set:** one specific combination of all parameter values. In a crossover-MA system, `{short_MA = 10, long_MA = 40}` is one parameter set; `{15, 50}` is another. (Schwager notes this term is identical to "system variation" used in Ch. 14.)

A 1-parameter system has parameter sets of 1 element. A 2-parameter system has 2-element sets, and so on.

## Illustration

![[02_parameter_set.png]]

Same breakout rules, two different parameter sets (N=7, N=40). The signals fire on completely different days.

## Analogy

A recipe (the system) says "bake until golden." The oven temperature is a parameter. 350°F and 425°F give you the same dish in concept, but the timing — and the result — are nothing alike. The combination of temperature + time + rack position is your parameter set.

## Numeric example

Crossover-MA system, sweep over 16 parameter sets (`code/concept_02_parameter_set.py`):

```
short_MA  long_MA  P&L ($/share)
       5       30     -8.42
       5       50     +12.05
       5       80     +33.91
      10       50     +28.74
      10      120     +18.66
      20       30      0.00      <-- invalid (long < short+10)
      20      120     +24.13
```

The *rules* didn't change once. Only knob settings did. Yet performance ranges from −$8 to +$34 per share. This is exactly why the next concept — optimization — is so tempting and so dangerous.

## Source code

[[code/concept_02_parameter_set.py]]

## Relationships

### Within the chapter
- The unit of analysis for [[05_Optimization]], [[07_Blind_Simulation]], and [[08_Average_Parameter_Set_Performance]] — every method in this chapter manipulates parameter sets.
- **Parameter shift** (Ch. 14, problem #9) is what happens when last year's best parameter set becomes this year's worst — i.e. parameter-set performance isn't stable across time.

### When to use few vs. many parameters?
Schwager: prefer the simplest form that doesn't materially hurt performance. Each new parameter multiplies the parameter-set space and the room for [[06_Testing_vs_Fitting|curve fitting]]. Treat parameters like dependencies in a project — only add one when you've justified the cost.

### Outside the chapter
- [[Chapter_14_Trend_Following_Systems]] — defines the canonical systems (breakout, crossover MA) whose parameters this chapter dissects.
- [[Chapter_13_Charting_Software]] — testing software is what lets you sweep parameter sets at scale.
