# 05 — Breakout Systems

## Definition

A **breakout system** trades on the principle that a market's ability to push to a new extreme indicates the move has further to run. The simplest formulation:

- **Buy** (cover any short, go long) when today's close exceeds the highest close of the prior *N* days.
- **Sell** (cover any long, go short) when today's close is below the lowest close of the prior *N* days.

It has only **one parameter** — *N* — which is what makes it so attractive: small surface area for overfitting, easy to test, easy to reason about.

The choice of *N* is the same speed/sensitivity trade-off as everywhere else:

- **Small *N* (e.g., 7):** signals fire early on real reversals — and on every minor squiggle.
- **Large *N* (e.g., 40):** very few signals; large per-trade losses if you happen to be on the wrong side; cleaner trends.

## Illustration

![[05_breakout.png]]

Green dashed line = rolling 20-day high. Red dashed line = rolling 20-day low. The system flips long whenever the close breaks above the upper line and short when it breaks below the lower line. Notice how the system stays cleanly long during the strong rising phase.

## Analogy

You're tracking the tallest building on a city's skyline. As long as no new building has been taller than every building from the last 20 years, you assume the era of skyscraper-building has paused. The moment a new building goes taller than anything in 20 years, you take it as a sign that a new building boom is underway and you act on it.

The bigger the comparison window (20 years vs 1 year), the more meaningful any new record is — but you also wait much longer to react.

## Numeric example

```
Test: 150-day synthetic price series

N    Signals    Closed-trade P&L
 7      16          +$10.16
20       7          – $7.55
40       1            $0.00
```

The N=7 system happened to win on this particular series, but it took 16 trades' worth of commission and slippage to do so. The N=40 system rarely fired, so it neither won nor lost much. In real life, the right answer depends on the market and the cost of trading — it has to be tested.

## Code

[[../codes/05_breakout.py]]

```python
def breakout_system(prices, n):
    p = np.asarray(prices, dtype=float)
    pos = np.zeros(len(p), dtype=int)
    signals = []
    cur = 0
    for i in range(n, len(p)):
        prior_high = p[i-n:i].max()
        prior_low  = p[i-n:i].min()
        if p[i] > prior_high and cur != 1:
            signals.append({'day': i, 'price': p[i], 'side': 'BUY'})
            cur = 1
        elif p[i] < prior_low and cur != -1:
            signals.append({'day': i, 'price': p[i], 'side': 'SELL'})
            cur = -1
        pos[i] = cur
    return pd.DataFrame(signals), pos
```

## Relationships

### Within the chapter

- **Sibling of:** [[02_Moving_Average_Systems]] / [[04_Crossover_Moving_Average_System]] — these are the two main families Schwager focuses on.
- **One-parameter advantage:** unlike the crossover MA system, breakout has only one knob. Less expressive, but also harder to overfit.
- **Most modifications work especially naturally with breakouts:**
    - [[06_Confirmation_Conditions]] (penetration, time delay, thrust days) — most of the chapter's confirmation examples are illustrated on breakouts.
    - [[08_Market_Characteristic_Adjustments]] — a great fit; *N* can be made volatility-dependent.
    - [[10_Pyramiding]] — Schwager's example pyramid scheme uses 10-day high/low logic on top of an N-day breakout base.

### Beyond the chapter

- **Ch. 4 (Trading Ranges and Support/Resistance):** breakouts of trading ranges are the chart-pattern equivalent — an explicit visual case the system tries to mechanize.
- **Ch. 5 (Chart Patterns):** continuation-pattern breakouts; the system is essentially a generalized chart pattern detector.
- **Ch. 7 (Is Chart Analysis Still Valid?):** the same breakout idea works manually with a discretionary trader's eye — chart-reading and rule-based are the same in spirit.
- **Ch. 17 (82 Trading Rules):** several of the rules concern fading vs following breakouts.
- **Famous example:** the original "Turtle Trading" system used by Richard Dennis was effectively a 20-day / 55-day breakout system.

### When breakout systems work best

- Markets prone to long, sustained moves once a level is decisively broken (commodities, currencies during regime shifts).
- Markets with clear range-and-break behaviour rather than constant noise.
- When combined with a regime/volatility filter so you don't take 20-day-high signals during a sideways grind.
