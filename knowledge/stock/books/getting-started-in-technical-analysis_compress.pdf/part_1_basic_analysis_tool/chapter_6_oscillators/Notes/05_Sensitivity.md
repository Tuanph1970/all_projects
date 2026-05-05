# Sensitivity (Look-back Period)

> Schwager, Ch. 6, pp. 112–113

## Definition

The **look-back period** *n* is the parameter that controls how reactive an oscillator is to recent price movement. Short look-backs (e.g. 5 days) react quickly to small swings; long look-backs (e.g. 20+ days) ignore noise and only register significant turning points.

There is no universally correct value — it is a deliberate trade-off between responsiveness and noise.

## Illustration

![[12_sensitivity.png]]

The middle panel (5-day) flips sign frequently and tracks every wiggle; the bottom panel (20-day) is much smoother and only signals on larger swings.

## Easy analogy

Think of the look-back period as the **shutter speed of a camera**. A fast shutter (small *n*) freezes every twitch — including blur from your shaky hand. A slow shutter (large *n*) averages over time and only captures the major motion. The fast camera shows more detail; the slow camera shows the underlying truth more reliably.

Or: weighing yourself once a day vs once a month. Daily weight bounces wildly with hydration and meals; monthly weight reveals the actual diet trend.

## Numeric example

For these closes:

```
Day:  ...  16  17  18  19  20  21  22
       ...  60  58  62  64  61  63  65
```

5-day momentum at day 22:  $65 - 61 = +4$ (a clear up-thrust over the last week)
20-day momentum at day 22 (using day 2's close ≈ 51): $65 - 51 = +14$ (much larger, reflecting a bigger picture trend)

The two indicators tell **different stories** about the same data:

- The 5-day says "modest recent push of +4 → expect a small reversal at the upper boundary."
- The 20-day says "$+14 over a month → still riding a major trend."

## Python code

```python
import pandas as pd
from oscillators_master import momentum

closes = pd.Series([...])  # your data
m5  = momentum(closes, 5)
m20 = momentum(closes, 20)

# Heuristic: react if 5-day shows reversal AND 20-day still confirms trend
buy_signal = (m5 < 0) & (m5.diff() > 0) & (m20 > 0)
```

Full code: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Same concept across every oscillator — affects [[02_Momentum]], [[03_Rate_of_Change]], [[06_MA_Oscillator]], [[11_RSI]] (default 14), [[12_Stochastics]] (default 14, smoothed by 3).
- Reversal magnitude scales with look-back: a 5-day momentum overshoot predicts a small bounce; a 20-day overshoot predicts a larger one.
- Determines where reasonable [[09_Overbought_Oversold]] thresholds will fall.

### Outside the chapter

- Same trade-off as moving-average length in [[Chapter_3_Trends]] — a fast MA whipsaws, a slow MA lags.
- Maps directly to short-vs-long parameters in [[Chapter_14_Trading_Systems]].
- The optimization of *n* is the central topic of [[Chapter_15_Testing_Optimizing]] — and Schwager warns there about over-fitting.

## Decision rule of thumb

| Holding period | Suggested *n* (days) |
|----------------|----------------------|
| Day / swing (1–5 days)  | 5–10 |
| Position trading (weeks) | 14–20 |
| Long-term (months)       | 50–100 |
