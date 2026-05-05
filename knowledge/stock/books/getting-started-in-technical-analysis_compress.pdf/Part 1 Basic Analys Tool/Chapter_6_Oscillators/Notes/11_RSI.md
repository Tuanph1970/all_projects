# RSI (Relative Strength Index)

> Schwager, Ch. 6, p. 116; Appendix pp. 316–317. Originator: J. Welles Wilder Jr., 1978.

## Definition

The **Relative Strength Index** measures the ratio of average up-moves to average down-moves over an *n*-day window, then squashes the result into a 0–100 range.

$$ RS = \frac{\text{average gain over } n}{\text{average loss over } n} $$

$$ RSI = 100 - \frac{100}{1 + RS} $$

Standard parameters:
- *n* = 14
- Overbought = 70, Oversold = 30 (some traders use 80/20 for stricter signals)

The "Relative Strength" here refers to the stock's strength **relative to itself** (up-days vs down-days). It is *not* relative to another stock or index — that is a different concept also called "relative strength."

## Illustration

![[08_rsi.png]]

## Easy analogy

Picture a tug-of-war happening over a fortnight (14 days). Each day either the "bulls" or the "bears" gain a bit of rope. RSI is the **scoreboard**, scaled from 0 to 100:

- 50 = perfect tie
- 70+ = bulls have been winning so dominantly that they're tiring, opponents about to push back
- 30− = bears have been winning so dominantly that they're tiring, opponents about to push back

The closer to 100 or 0, the more lopsided the recent contest — and the more likely a momentum reversal.

## Numeric example

14 daily closes:

```
51, 52, 51, 53, 54, 53, 55, 56, 55, 57, 58, 57, 59, 60
```

Day-to-day changes: `+1, −1, +2, +1, −1, +2, +1, −1, +2, +1, −1, +2, +1`

- 8 up moves, sum of gains = 13 → average gain = 13 / 13 ≈ **1.00**
- 5 down moves, sum of losses = 5 → average loss = 5 / 13 ≈ **0.385**
- RS = 1.00 / 0.385 ≈ **2.60**
- RSI = 100 − 100 / (1 + 2.60) = 100 − 27.78 ≈ **72.2**

72 > 70 → **overbought** by the standard interpretation.

(Real-world implementations use Wilder's smoothing — an EMA with α = 1/n — for stability across days; the simple-average version above is the one-shot textbook calculation.)

## Python code

```python
import pandas as pd

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI with Wilder's smoothing (EMA, alpha = 1/n)."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Generate trade signals
def rsi_signals(close, ob=70, os_=30):
    r = rsi(close)
    sell_alert = (r.shift(1) <= ob) & (r > ob)
    buy_alert  = (r.shift(1) >= os_) & (r < os_)
    return buy_alert, sell_alert
```

Full implementation: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Normalized version of the [[02_Momentum]] / [[03_Rate_of_Change]] family — see [[10_Normalized_Unbounded]].
- Equilibrium = 50, see [[04_Equilibrium_Line]].
- Default thresholds 70/30 are special cases of [[09_Overbought_Oversold]] applied to a [0, 100]-bounded indicator.
- Often paired with [[12_Stochastics]] on the same chart for confirmation (Schwager's Figure 6.1).
- Frequently used to spot [[13_Divergence]].
- Best deployed as a [[14_Trading_Alerts]] tool, especially in trending environments.

### Outside the chapter

- One of the named overbought/oversold tools in [[Chapter_10_Setting_Objectives]] for trade-exit decisions.
- Detailed formula derivation in [[Appendix_Formulas]].
- Used as a filter inside countertrend systems in [[Chapter_14_Trading_Systems]].
- Shows up as part of "Eighty-Two Trading Rules" guidance in [[Chapter_17_Trading_Rules]].

## When RSI works well — and when it lies

| Condition | RSI behavior |
|-----------|--------------|
| Trading range | Extremely useful — bounces off 70 and 30 cleanly |
| Strong uptrend | Pinned in 60–90 zone for weeks; the standard "30" oversold reading **never appears**, so buy signals are missing |
| Strong downtrend | Pinned in 10–40 zone; standard "70" overbought reading is missing |
| Choppy / sideways | Frequent, often false, threshold crossings — needs price confirmation |

Schwager's central caution applies particularly to RSI: overbought does not mean "sell now"; it means "be alert and watch price for a reversal signal." See [[14_Trading_Alerts]].
