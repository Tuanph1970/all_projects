# 03 — Weighted Moving Averages (LWMA, EWMA)

## Definition

The simple moving average treats every day in its window equally — yesterday's close has the same weight as the close from N days ago. Many practitioners argue more recent prices should matter more. **Weighted moving averages** apply unequal weights to address this.

**Linearly Weighted Moving Average (LWMA):** weights increase linearly from oldest to newest.

$$\text{LWMA}_t(N) = \frac{\sum_{k=1}^{N} k \cdot \text{Close}_{t-N+k}}{\sum_{k=1}^{N} k}$$

**Exponentially Weighted Moving Average (EWMA):** weights decay geometrically; recent days dominate.

$$\text{EWMA}_t = \alpha \cdot \text{Close}_t + (1-\alpha) \cdot \text{EWMA}_{t-1}, \quad \alpha = \frac{2}{N+1}$$

Schwager's empirical view: there is no strong evidence that LWMA or EWMA consistently outperforms the plain SMA. Sometimes one wins, sometimes another. Don't burn time chasing the "right" weighting scheme — work on filters, confirmations, and pyramiding instead.

## Illustration

![[03_weighted_ma.png]]

All three moving averages on the same price series. The EWMA hugs price most closely (most recent-weighted), the LWMA sits in the middle, and the SMA lags the most. They look meaningfully different — but the *trading performance* differences across them are mostly noise.

## Analogy

Three friends try to estimate "how heavy the traffic has been this month."

- **SMA friend:** counts the cars seen each day in the last 30 days, divides by 30. Treats day 1 the same as day 30.
- **LWMA friend:** counts the same days, but weights the count by which day it was — yesterday gets weight 30, the day before 29, ..., day 1 gets weight 1.
- **EWMA friend:** keeps a single rolling number and updates it each day: "new estimate = a bit of today + most of yesterday's estimate."

All three friends are trying to summarize the same reality. They'll usually agree on the broad picture and disagree on exactly when traffic "started getting bad." None of them is consistently more right — they just emphasize different things.

## Numeric example

10-day weighted moving average over a rising series:

| Day | Price | SMA(10) | LWMA(10) | EWMA(10) |
|-----|-------|---------|----------|----------|
| 9   | 104.52 | 101.59 | 102.21 | 102.10 |
| 14  | 103.59 | 103.08 | 103.48 | 103.03 |
| 19  | 103.77 | 103.70 | 103.76 | 103.54 |
| 34  | 106.05 | 104.69 | 105.27 | 105.04 |
| 39  | 109.35 | 107.36 | 108.20 | 107.59 |

When the trend accelerates (day 39: price jumps from 106 → 109), the LWMA tracks fastest (108.20), then EWMA (107.59), then SMA (107.36). That responsiveness is the appeal — but a faster MA also turns more sharply on noise.

## Code

[[../codes/03_weighted_ma.py]]

```python
def lwma(prices, n):
    weights = np.arange(1, n+1)
    out = np.full(len(prices), np.nan)
    for i in range(n-1, len(prices)):
        out[i] = np.dot(prices[i-n+1:i+1], weights) / weights.sum()
    return out

def ewma(prices, n):
    a = 2.0 / (n + 1)
    out = np.zeros(len(prices))
    out[0] = prices[0]
    for i in range(1, len(prices)):
        out[i] = a * prices[i] + (1 - a) * out[i-1]
    return out
```

## Relationships

### Within the chapter

- **Variant of:** [[02_Moving_Average_Systems]] — same trading rule, different smoothing.
- **Often combined with:** [[04_Crossover_Moving_Average_System]] — many real-world systems use EWMAs in a crossover (e.g., MACD's 12/26 EWMA pair).
- **Doesn't fix what really matters:** the overhauls that actually improve performance live in [[06_Confirmation_Conditions]], [[07_Filter]], [[08_Market_Characteristic_Adjustments]], and [[10_Pyramiding]].

### Beyond the chapter

- **Appendix:** explicit LWMA / EWMA formulas.
- **Ch. 6 (Oscillators):** EWMAs underlie indicators like MACD and the smoothed RSI.
- **Ch. 15 (Optimization):** more weighting schemes = more parameters = more overfitting risk; this is exactly the kind of "complexity for its own sake" the chapter cautions against.

### When weighted MAs help

- Mostly when noise structure makes recent data genuinely more informative — for example, after a regime change.
- Inside indicators where the *combination* with other signals matters more than the smoother alone (e.g., MACD).
- They rarely help simply by being weighted; they help when their faster reaction is paired with stronger filters.
