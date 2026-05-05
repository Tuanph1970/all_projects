# MACD (Moving Average Convergence-Divergence)

> Schwager, Ch. 6, pp. 114–116

## Definition

**MACD** is a specific price oscillator built from three components:

1. **MACD line** = EMA(12) − EMA(26) of close
2. **Signal line** = EMA(9) of the MACD line
3. **Histogram** = MACD line − Signal line

Two important note: MACD uses **exponential** moving averages (which weight recent data more heavily) rather than simple ones, and the signal line provides an additional smoothing layer used for crossover signals.

## Illustration

![[06_macd.png]]

Blue = MACD line, red = signal line, bars = histogram. Histogram bars rise above zero when MACD crosses above its signal (buy zone) and fall below zero when MACD crosses below (sell zone).

## Easy analogy

Picture two people running a long race:
- The **fast runner** (12-EMA) reacts quickly to changes in pace.
- The **slow runner** (26-EMA) maintains a steadier pace.

The MACD line is the **gap between them**. When the fast runner is pulling ahead, MACD is positive and growing. The signal line is then a **stop-watch averaging the recent gap** — when the current gap exceeds the recent average gap, that's a buy signal. The histogram is just the **height of today's gap above (or below) the stop-watch average**, drawn as bars so you can see momentum changes at a glance.

## Numeric example

A simplified scenario (illustrative values):

| Day | EMA12 | EMA26 | MACD | EMA9(MACD) | Histogram |
|-----|-------|-------|------|------------|-----------|
| 1   | 50.10 | 49.90 | +0.20 | 0.10 | +0.10 |
| 2   | 50.40 | 50.05 | +0.35 | 0.15 | +0.20 |
| 3   | 50.70 | 50.20 | +0.50 | 0.22 | +0.28 |
| 4   | 50.90 | 50.40 | +0.50 | 0.28 | +0.22 |
| 5   | 50.95 | 50.55 | +0.40 | 0.31 | +0.09 |

In day 3, the histogram peaks at +0.28 — momentum is at its strongest. By day 5, even though MACD is still positive, the histogram is shrinking — momentum is weakening, an early warning that the trend may be tiring.

## Python code

```python
import pandas as pd

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Standard MACD: returns (macd_line, signal_line, histogram)."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# Trade signals
def macd_signals(close):
    m, s, _ = macd(close)
    above = m > s
    buy  = above & (~above.shift(1).fillna(False))
    sell = (~above) & (above.shift(1).fillna(False))
    return buy, sell
```

Full implementation: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- A specific case of [[07_Price_Oscillator]] using exponential MAs of length 12 and 26.
- The signal-line cross is a smoothed version of an [[04_Equilibrium_Line]] crossing.
- MACD's slope and divergence with price form the basis for [[13_Divergence]] signals.
- Optional [[09_Overbought_Oversold]] thresholds can be added on top to filter trades.

### Outside the chapter

- Two-EMA structure echoes the dual-MA crossover system in [[Chapter_14_Trading_Systems]].
- A buy/sell signal-line crossover is mathematically the same as a fast/slow MA crossover from [[Chapter_3_Trends]].
- Used as a confirmation filter for chart pattern breakouts — see [[Chapter_5_Chart_Patterns]].
- The exponential weighting trick is detailed in the formulas appendix → [[Appendix_Formulas]].

## When MACD shines vs struggles

| Condition | MACD behavior |
|-----------|---------------|
| Steady trend | Stays clearly above (or below) zero — confirms direction; few whipsaws |
| Volatile range | Many shallow signal-line crossings — frequent whipsaws |
| Slow-moving stock | Histogram barely separates from zero — signals weak |
| Sharp news event | EMAs are slow to react — late signal |
