# Rate of Change (ROC)

> Schwager, Ch. 6, pp. 111–112

## Definition

**Rate of Change** is the multiplicative cousin of momentum. Instead of subtracting prices, you divide them:

$$ \text{ROC}(n) = \frac{\text{Close}_t}{\text{Close}_{t-n}} $$

Or, more commonly expressed as a percentage:

$$ \text{ROC\%}(n) = \frac{\text{Close}_t - \text{Close}_{t-n}}{\text{Close}_{t-n}} \times 100 $$

Other than scale, ROC and Momentum behave virtually identically — they peak, trough, and cross their equilibrium at the same moments. ROC's advantage is that it normalizes for price level: a $5 move in a $50 stock is very different from a $5 move in a $500 stock.

## Illustration

![[02_roc.png]]

## Easy analogy

Momentum tells you "the marathon runner is 10 km ahead of where she was an hour ago." ROC tells you "she has covered **24 % more distance** than an hour ago." If you're comparing runners of very different speeds (or stocks of very different prices), the percentage version is the fair comparison.

## Numeric example

Same closes as the [[02_Momentum]] note: 50 → 62 over 10 days.

$$ \text{ROC ratio} = \frac{62}{50} = 1.24 $$
$$ \text{ROC \%} = \frac{62 - 50}{50} \times 100 = 24\% $$

A reading of 1.0 (or 0 %) is the equilibrium — price unchanged. A reading of 1.24 means today's close is 24 % above the close 10 days ago.

## Python code

```python
def rate_of_change(close, n=10):
    """ROC ratio: close[t] / close[t-n]."""
    return close / close.shift(n)

def rate_of_change_pct(close, n=10):
    """ROC percentage form."""
    return ((close - close.shift(n)) / close.shift(n)) * 100
```

Full file: [[oscillators_master.py]]

## Relationships

### Within Chapter 6

- Mathematically equivalent to [[02_Momentum]] (just division vs subtraction). Schwager explicitly notes "the indicators are virtually identical" except for scale.
- Same [[04_Equilibrium_Line]] interpretation (1.0 for ratio form, 0 for percentage form).
- Same overbought/oversold logic — see [[09_Overbought_Oversold]].
- Like Momentum, sensitivity depends on **n**; see [[05_Sensitivity]].

### Outside the chapter

- The "%" form is what most traders mean colloquially when they say "the stock is up 24 % this month."
- Used as a screening tool in [[Chapter_12_Real_World_Chart_Analysis]].
- Comparing ROC across stocks helps with relative-strength-style ranking — a different concept from [[11_RSI]] despite the similar name.

## When ROC is preferred over plain Momentum

| Situation | Prefer |
|-----------|--------|
| Comparing two stocks at very different price levels | **ROC %** |
| Working in a single market across many years | **ROC %** (price level drifts a lot) |
| Quick visual reading on a single chart | Either — they look the same |
| Setting fixed numeric overbought/oversold lines that should remain valid as the stock grows | **ROC %** |
