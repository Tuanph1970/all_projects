# Overbought / Oversold

> Schwager, Ch. 6, pp. 116–117

## Definition

**Overbought** and **oversold** refer to extreme oscillator readings that are unlikely to be sustained — moments when a market has moved up (or down) too fast over too short a span, suggesting that a corrective reaction may follow.

- **Overbought**: indicator is in its top range → market may be due for a pullback.
- **Oversold**: indicator is in its bottom range → market may be due for a bounce.

There is **no universally correct threshold**. A common rough rule is to pick levels that isolate the highest and lowest ~10 % of historical readings. Reviewing past peaks and troughs of the indicator is the most practical calibration method.

## Illustration

![[07_overbought_oversold.png]]

Red dashed = overbought; green dashed = oversold. Red shaded patches above the line and green patches below mark moments where the market is "stretched."

## Easy analogy

Stretching a rubber band: the further you pull, the more it wants to snap back. A rubber band stretched only a little can still be pulled further (no real signal). One pulled to its visible limit is *strongly biased toward snapping back* — but it can still be pulled a bit further before it actually does (or breaks). That's why traders treat overbought/oversold as a **warning, not a guarantee**.

## Numeric example

Suppose RSI(14) readings over a month sit in the range 35–75, with one excursion to 82.

- 82 is well above the conventional 70 threshold → **overbought** signal.
- A trader watching the position might:
  - Tighten stops on a long position (moving from $48 to $51 on a $52 stock)
  - Liquidate part of the position (sell 50 of 100 shares)
  - Or simply *prepare* to sell once price actually confirms the reversal

If price then closes below the prior day's low at $51.50, that's the price-confirmation step (see [[14_Trading_Alerts]]).

## Python code

```python
import pandas as pd

def overbought_oversold(indicator: pd.Series,
                        upper_pct: float = 0.90,
                        lower_pct: float = 0.10):
    """
    Calibrate dynamic OB/OS levels from historical quantiles.
    Returns (ob_level, os_level, ob_mask, os_mask)
    """
    ob = indicator.quantile(upper_pct)
    os_ = indicator.quantile(lower_pct)
    return ob, os_, indicator > ob, indicator < os_

# Fixed-threshold version for normalized oscillators (RSI/Stoch)
def fixed_thresholds(indicator, ob=70, os_=30):
    return indicator > ob, indicator < os_
```

Full code: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Applies to **every** oscillator: [[02_Momentum]], [[03_Rate_of_Change]], [[06_MA_Oscillator]], [[07_Price_Oscillator]], [[08_MACD]], [[11_RSI]], [[12_Stochastics]].
- Levels differ by oscillator family — see [[10_Normalized_Unbounded]] for the bounded vs unbounded distinction.
- Often used together with [[13_Divergence]] for stronger signals.
- Schwager's recommendation: use as input to [[14_Trading_Alerts]] rather than blind entries.

### Outside the chapter

- Functionally similar to a **support/resistance bounce** at a chart level, but in oscillator-space — see [[Chapter_4_Trading_Ranges]].
- Frequently used as a trade-exit cue in [[Chapter_10_Setting_Objectives]].
- In trending markets, this signal class is one of the most common sources of losses — see [[Chapter_14_Trading_Systems]] discussion of countertrend system pitfalls.

## Critical caveat (the chapter's main warning)

Overbought/oversold thresholds **systematically fail in trending markets** — the oscillator stays pinned at one extreme for weeks while price keeps going. Signals must be adapted to market regime:

| Regime | Suggested OB / OS |
|--------|-------------------|
| Trading range | 70 / 30 (RSI) |
| Strong uptrend | Raise both → 80 / 50 (rare oversold reads become buyable) |
| Strong downtrend | Lower both → 50 / 20 (rare overbought reads become sellable) |
