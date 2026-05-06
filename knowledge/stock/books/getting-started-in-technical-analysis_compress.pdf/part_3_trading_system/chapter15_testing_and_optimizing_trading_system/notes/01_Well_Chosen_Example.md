# Concept 1 — The Well-Chosen Example

**Tags:** #ch15 #pitfall #methodology

## Definition

A *well-chosen example* is a single historical chart, market, or time window picked specifically because it makes a trading system look brilliant. Schwager's point: you can find one for **any** system, even a worthless one. Drawing conclusions from such an example is one of the most common — and expensive — beginner mistakes.

## Illustration

![[01_well_chosen_example.png]]

Left: the slide a seminar speaker shows you. Right: the same system on a different window. Same rules, same parameters — totally different outcome.

## Analogy

Imagine someone selling you a "miracle" weather-forecasting rock by showing you the three days last summer it predicted sunshine and got it right. They didn't show you the 200 days the rock was wrong. Cherry-picked evidence isn't evidence — it's marketing.

## Numeric example

In `code/concept_01_well_chosen_example.py` we run an identical naive breakout system on 100 random 6-month windows:

```
Best window       : $+44.05    <-- 'seminar slide' material
Worst window      : $-21.07
Mean across all   : $-0.44     <-- the honest answer
% windows > 0     : 37.0%
```

The "best window" is roughly **double-digit dollars** of profit per share. The mean is **slightly negative**. If the seminar showed you the $+44 chart, you'd think you found a money machine.

## Source code

[[code/concept_01_well_chosen_example.py]]

## Relationships

### Within the chapter
- **Connects to [[06_Testing_vs_Fitting]]** — the well-chosen example is the demand-side version of curve-fitting. Curve-fitting is the supply side (creator over-tunes the system); cherry-picking is the display side (creator picks the favorable example to show).
- **Cured by [[07_Blind_Simulation]]** and [[08_Average_Parameter_Set_Performance]] — both eliminate cherry-picking by forcing you to look at the *full* distribution of outcomes.
- **Reappears in [[09_Schwagers_Corollary]]** as one of the seven distortion methods.

### When does relying on examples work?
Almost never for *evaluation*. Examples are fine for **teaching** a concept (e.g., "this is what a head-and-shoulders looks like") but useless for proving a system has edge.

### Outside the chapter
- [[Chapter_12_Real_World_Chart_Analysis]] — explicitly contrasts hindsight chart reading with real-time decisions; the well-chosen example pitfall is its hindsight-bias cousin.
- [[Chapter_18_Market_Wizardom]] — successful traders consistently cite skepticism toward any single great trade as a defining trait.
