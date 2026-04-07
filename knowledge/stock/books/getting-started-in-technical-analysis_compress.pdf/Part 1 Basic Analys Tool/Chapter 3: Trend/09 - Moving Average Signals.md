# Moving Average Signals

## Description

Schwager's signal method from Figures 3.20/3.21: generate buy/sell signals based on the **direction change** of the [[08 - Moving Averages|moving average]] with a minimum threshold reversal to prevent whipsaws.

This is different from the common "price crosses MA" method — the signal comes from the MA *itself* changing direction, not from price crossing the MA line. The threshold creates a "dead band" where small MA oscillations don't trigger signals.

**Three components:**
1. The MA (parameter N) — the smoothing engine
2. The peak/trough tracker — running max/min since last signal
3. The threshold (parameter T) — minimum MA reversal to trigger

## Simple Analogy

Think of a thermostat with a **dead band**. A normal thermostat turns the heater on at 68°F and off at 72°F — the 4°F gap prevents the system from flipping on/off every second. The MA threshold works the same way: the MA must reverse by a meaningful amount before the system acknowledges the direction change. Without the dead band, you'd get constant flipping (whipsaws) every time the MA wiggles.

## Signal Logic

```
Track: ma_running_high (since last sell), ma_running_low (since last buy)

BUY when:  MA[today] - ma_running_low  >= threshold
SELL when: ma_running_high - MA[today]  >= threshold

After BUY:  reset ma_running_high = MA[today]
After SELL: reset ma_running_low = MA[today]
```

## The Two Faces (Schwager's Matched Pair)

**Figure 3.20 — Trending market (Natural Gas):** "This extremely simple technique generated superb trading signals... three signals... You can't ask for much more than that."

**Figure 3.21 — Sideways market (Cocoa):** "The same method... proves to be a disastrous strategy in this market, yielding six consecutive losses and one break-even trade."

Same method, same parameters, opposite results. This leads directly to [[12 - Trending vs Sideways Markets]].

## Illustration

**Interactive simulation:** `assets/simulations/ma_signal_interactive.jsx`
- Switch between trending / sideways / mixed regimes
- Adjust MA period and threshold with sliders
- Live signal generation with win/loss statistics
- Shows how no parameter combination works in both regimes

## Python Code

**File:** `assets/code/trend_lines.py` → function `moving_average_trend()`

The signal generation logic with threshold tracking is fully implemented, including the running high/low state machine.

## Parameter Interactions

| N (MA period) | T (threshold) | Effect |
|---|---|---|
| Short (10) | Low (0.5) | Whipsaw machine — catches everything, most false |
| Short (10) | High (2.0) | Fast but selective — can work well |
| Long (40) | Low (0.5) | Smooth and selective — most signals genuine |
| Long (40) | High (3.0) | Misses almost everything |

## Connections

- **Depends on:** [[08 - Moving Averages]]
- **Failure mode leads to:** [[12 - Trending vs Sideways Markets]]
- **Improved by:** Ch.14 MA direction filter, crossover systems, confirmation conditions
- **Complementary:** Ch.8 Midtrend entry at MA (use MA for reentry, not reversal)
- **Source:** Schwager pp.49-50, Figures 3.20-3.21

---
*Tags: #signals #schwager-ch3 #codeable #parametric #regime-dependent*
