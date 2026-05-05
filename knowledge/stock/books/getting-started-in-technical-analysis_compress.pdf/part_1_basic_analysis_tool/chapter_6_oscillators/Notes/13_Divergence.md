# Divergence (Bullish & Bearish)

> Schwager, Ch. 6, pp. 117–119

## Definition

A **divergence** occurs when an oscillator moves in the opposite direction to price at successive pivots — a hint that the visible trend is losing internal force.

| Type | Price action | Oscillator action | Implication |
|------|-------------|-------------------|-------------|
| **Bearish divergence** | Higher high in price | Lower high in oscillator | Uptrend weakening; possible reversal down |
| **Bullish divergence** | Lower low in price | Higher low in oscillator | Downtrend weakening; possible reversal up |

The mechanism: price is making a new extreme but the *force* behind the move is no longer there.

## Illustration

![[10_divergence.png]]

Red arrows mark bearish divergences (price up, RSI lower); green arrows mark bullish divergences (price down, RSI higher).

## Easy analogy

Imagine a sprinter setting personal records every week — but you also notice her **breath getting more labored** each race despite the faster times. The visible result (faster time) keeps improving, but the underlying force (lung capacity) is fading. Sooner or later, she's going to slow down. Divergence is exactly that: **the visible record keeps improving while the underlying engine weakens**.

The reverse is also instructive: a runner who keeps posting slower times, yet whose **breathing is becoming easier** each race. The decline you see is masking a recovering engine — the slowdown is about to reverse.

## Numeric example

| Date | Price high | RSI at that pivot | What it means |
|------|-----------|-------------------|---------------|
| Mar 1 | $52 | 78 | Strong rally; RSI confirms |
| Apr 5 | $55 | 72 | Higher price, lower RSI → divergence #1 (still mild) |
| May 12 | $57 | 65 | Higher price, even lower RSI → divergence #2 (clearer) |
| Jun 8 | $58 | 58 | Higher price, much lower RSI → divergence #3 (strong) |

Three successive bearish divergences. Schwager's caution: the *first* such divergence is rarely the right entry — it often appears mid-trend and the market keeps climbing. Wait for price confirmation.

## Python code

```python
import pandas as pd

def find_pivots(series: pd.Series, window: int = 5):
    """Return index positions of pivot highs and lows."""
    highs, lows = [], []
    for i in range(window, len(series) - window):
        win = series.iloc[i - window: i + window + 1]
        if series.iloc[i] == win.max():
            highs.append(i)
        if series.iloc[i] == win.min():
            lows.append(i)
    return highs, lows

def detect_divergence(price: pd.Series, oscillator: pd.Series, window: int = 5):
    """Return lists of (price_index, oscillator_index) for bearish and bullish divergence."""
    p_h, p_l = find_pivots(price, window)
    o_h, o_l = find_pivots(oscillator, window)
    bearish, bullish = [], []
    for i in range(1, len(p_h)):
        prev, curr = p_h[i - 1], p_h[i]
        if (price.iloc[curr] > price.iloc[prev]
                and oscillator.iloc[curr] < oscillator.iloc[prev]):
            bearish.append((curr, curr))
    for i in range(1, len(p_l)):
        prev, curr = p_l[i - 1], p_l[i]
        if (price.iloc[curr] < price.iloc[prev]
                and oscillator.iloc[curr] > oscillator.iloc[prev]):
            bullish.append((curr, curr))
    return bearish, bullish
```

Full implementation: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Detectable on **every** oscillator: [[02_Momentum]], [[03_Rate_of_Change]], [[06_MA_Oscillator]], [[07_Price_Oscillator]], [[08_MACD]], [[11_RSI]], [[12_Stochastics]].
- Stronger when combined with [[09_Overbought_Oversold]] — divergence forming inside an overbought zone is a classic high-conviction setup.
- Often issued as a [[14_Trading_Alerts]] rather than as an immediate entry, because of the false-signal problem described below.

### Outside the chapter

- Conceptually similar to [[Chapter_5_Chart_Patterns]] reversal patterns (a head-and-shoulders is essentially a price-only divergence).
- Often combined with [[Chapter_4_Trading_Ranges]] resistance to time exits.
- The need to limit losses on premature signals connects directly to [[Chapter_9_Stop_Loss]].
- Discussed in trading-system context in [[Chapter_14_Trading_Systems]].

## The honest weakness of divergence (Schwager's warning)

Trends produce **multiple successive divergences** before they actually turn. A trader who shorts at the first divergence in a strong uptrend can suffer repeated losses while the trend extends through divergence #2, #3, even #4 before finally rolling over.

Practical mitigations:

1. **Wait for price confirmation** — a break of the most recent swing low (after a bearish divergence) or a swing high (after a bullish one).
2. **Use it only at "weighted" locations** — e.g. divergence at major resistance is more credible than divergence in the middle of a range.
3. **Always pair with stop-loss** — see [[Chapter_9_Stop_Loss]].
4. **Adjust thresholds to the trend** — in strong trends, ignore divergences that fail to push the oscillator out of the dominant zone.
