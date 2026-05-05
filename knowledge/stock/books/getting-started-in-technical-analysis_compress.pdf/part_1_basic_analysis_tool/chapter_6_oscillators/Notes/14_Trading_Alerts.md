# Oscillators as Trading Alerts

> Schwager, Ch. 6, p. 119 (the chapter's conclusion)

## Definition

Schwager's central practical recommendation: rather than treating oscillator signals (overbought, oversold, divergence) as **direct trade entries**, treat them as **alerts** — warnings that a market may be overextended — and only act once *price itself* confirms the implied reversal.

A clean alert-and-confirm workflow:

1. **Alert** — oscillator enters its extreme zone (e.g. RSI > 70).
2. **Watch** — monitor price; do not enter yet.
3. **Confirm** — wait for an actual price-based reversal signal (e.g. close below prior day's low, break of a short-term trend line, completion of a reversal pattern).
4. **Enter** — only now establish the position.
5. **Stop** — place a stop-loss using the most recent swing extreme as a reference.

## Illustration

![[11_trading_alerts.png]]

Orange dotted lines = alerts (RSI crossed above 70). Red downward triangles = confirmed entries (price actually fell after the alert, validating the signal).

## Easy analogy

A smoke detector. When it beeps, you don't immediately call the fire department. You **investigate** — look around, sniff the air, check the kitchen. If you actually see flames or smell something burning, you act. False alarms are common; using the alarm as your *trigger to investigate* (not your trigger to act) is the difference between a sensible household and one that constantly evacuates over burnt toast.

The same is true for an oscillator: an overbought reading is the smoke detector. It tells you to look harder at price, not to flip your position blindly.

## Numeric example

Suppose a stock has been rallying and reaches RSI = 73 on Monday with a close of $58.

- **Naive approach:** sell short Monday at $58. Stock keeps climbing to $63 over two weeks → −$5 loss.
- **Alert approach:**
  - Monday: RSI > 70 → **alert** (no trade).
  - Tuesday–Thursday: stock keeps climbing to $61. RSI now at 78. Still no trade.
  - Friday: stock closes at $59, below prior day's low of $59.50 → **price confirmation**.
  - **Enter short** at the open Monday at $58.50, with a stop just above the recent high of $61.50.
  - Risk: $3 on entry. Reward potential: as far as the next support area.

The alert approach skipped the false move and let the trader risk a defined $3 instead of suffering an open-ended loss.

## Python code

```python
import pandas as pd
from oscillators_master import rsi

def alert_and_confirm(close: pd.Series, ob: int = 70, os_: int = 30):
    """
    Generate alert dates (oscillator extreme) and confirmation dates
    (subsequent close that breaks the prior day's low/high).
    """
    r = rsi(close, 14)
    overbought = r > ob
    oversold   = r < os_

    sell_alerts = close.index[overbought]
    buy_alerts  = close.index[oversold]

    sell_confirmed, buy_confirmed = [], []

    for d in sell_alerts:
        i = close.index.get_loc(d)
        # confirm: close in the next 5 days breaks below this day's low
        for j in range(i + 1, min(i + 6, len(close))):
            if close.iloc[j] < close.iloc[i]:
                sell_confirmed.append(close.index[j])
                break

    for d in buy_alerts:
        i = close.index.get_loc(d)
        for j in range(i + 1, min(i + 6, len(close))):
            if close.iloc[j] > close.iloc[i]:
                buy_confirmed.append(close.index[j])
                break

    return buy_alerts, buy_confirmed, sell_alerts, sell_confirmed
```

Full implementation: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- The proper way to act on every other concept in the chapter — [[02_Momentum]], [[06_MA_Oscillator]], [[08_MACD]], [[09_Overbought_Oversold]], [[11_RSI]], [[12_Stochastics]], and especially [[13_Divergence]] (which produces the most false signals).
- The natural antidote to the "signals fail in trending markets" problem highlighted throughout the chapter.

### Outside the chapter

- Price confirmation step is exactly the **breakout / reversal pattern** logic of [[Chapter_5_Chart_Patterns]].
- The required stop-loss step links directly to [[Chapter_9_Stop_Loss]].
- The wait-for-price idea is a central rule among Schwager's [[Chapter_17_Trading_Rules]].
- This pattern is built into the design of the countertrend systems in [[Chapter_14_Trading_Systems]] (oscillator + confirmation).
- The patience required is the trader-psychology theme of [[Chapter_18_Market_Wizdom]].

## Why this matters: the chapter's bottom line

> The conventional countertrend reading of an oscillator — "sell at overbought, buy at oversold" — works wonderfully in a trading range and **disastrously in a trend**. Because you cannot reliably know in advance which regime is coming, treat oscillator signals as alerts and let price be the arbiter.

This single principle is, in Schwager's view, more valuable than any specific oscillator formula in the chapter.
