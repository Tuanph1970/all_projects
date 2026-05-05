# Normalized vs Unbounded Oscillators

> Schwager, Ch. 6, pp. 116–117

## Definition

Oscillators come in two structural flavors:

| Type | Range | Examples |
|------|-------|----------|
| **Unbounded** | No fixed ceiling/floor | [[02_Momentum]], [[03_Rate_of_Change]], [[06_MA_Oscillator]], [[07_Price_Oscillator]], [[08_MACD]] |
| **Normalized** | Fixed bounds, usually 0–100 | [[11_RSI]], [[12_Stochastics]] |

The practical consequence: normalized oscillators allow **fixed numerical thresholds** (RSI 70/30, Stoch 80/20) that work across stocks and time. Unbounded oscillators need their thresholds calibrated to each market and parameter set.

## Illustration

Compare the y-axis of [[06_macd.png]] (unbounded — varies in absolute price units) with [[08_rsi.png]] (always between 0 and 100).

## Easy analogy

Imagine measuring temperature two ways:

- **Unbounded (Celsius reading)**: actual numeric value depends on the climate. "−5 °C" is freezing in London, normal in Antarctica. You need local context to know what it means.
- **Normalized (a 0–100 weather "comfort index")**: 80+ is uncomfortably hot, 20− is uncomfortably cold — *anywhere on Earth*. The scale is the same regardless of the underlying physical units.

Normalized oscillators give you that universal-comfort-index advantage.

## Numeric example

For a $10 stock and a $1000 stock, both rising 5 % over 10 days:

| Stock | Close 10d ago | Close today | Momentum | RSI(14) |
|-------|--------------|-------------|----------|---------|
| Cheap | $10.00 | $10.50 | +$0.50 | 67 |
| Expensive | $1,000 | $1,050 | +$50 | 67 |

Momentum readings (+0.50 vs +50) are not comparable between stocks. RSI readings (both ~67) are directly comparable: in both cases the stock is *moderately strong but not yet overbought*.

## Python code

```python
import pandas as pd

def is_overbought_normalized(indicator, level=70):
    """For RSI/Stoch with fixed [0,100] range."""
    return indicator > level

def is_overbought_unbounded(indicator, lookback=200, pct=0.90):
    """For Momentum/MACD: dynamic threshold from rolling history."""
    threshold = indicator.rolling(lookback).quantile(pct)
    return indicator > threshold
```

Full code: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Determines the right approach in [[09_Overbought_Oversold]] (fixed vs dynamic thresholds).
- All normalized oscillators ([[11_RSI]], [[12_Stochastics]]) wrap an underlying momentum calculation in a `100 − 100/(1 + …)` or "% within recent range" transformation.
- Both types display [[13_Divergence]] equally well — divergence cares about pivot direction, not absolute value.

### Outside the chapter

- The normalization idea also appears in **volatility ratios** and **standardized z-scores** — see [[Appendix_Formulas]].
- Position-sizing systems in [[Chapter_14_Trading_Systems]] and [[Chapter_16_Planned_Trading]] benefit from normalized inputs because they generalize across markets without re-tuning.

## Practical guideline

| Need | Pick |
|------|------|
| Cross-market scan / many stocks at once | **Normalized** (RSI / Stoch) |
| Fine-grained study of one specific market | Either; unbounded shows raw force more directly |
| Fixed parameter set deployable everywhere | **Normalized** |
