# 07 — Filter

## Definition

A **filter** is a screening rule applied *at the time the basic signal fires* to eliminate trades judged to have a low probability of success. The trade either passes the filter and is taken, or it fails the filter and is rejected outright (not delayed — rejected).

Filters can be technical or fundamental:

- **Technical filter:** "only take buy signals if the moving average itself is rising."
- **Trend-context filter:** "skip signals that occur inside what looks like a trading-range market."
- **Fundamental filter:** "only take signals that align with a separate fundamental classification of the market as bullish, bearish, or neutral."

The system designer is essentially trying to find a common feature shared by most *losing* trades and reject anything matching that feature.

**Key distinction from confirmation:** a filter rejects at signal time. A confirmation rule waits and re-evaluates later. A system can use both — filter first, then confirmation on what survives.

## Illustration

![[07_filter.png]]

Top panel: simple MA crossover system without a filter. Many small whipsaw losses where the MA itself is flat or wrong-direction. Bottom panel: same data, same MA, but only signals that align with the slope of the MA are accepted. Far fewer trades, and only ones with directional context.

## Analogy

You're job-hunting and you set up email alerts for "new software jobs." Without a filter, you get every job posted with the word "software" — including listings in cities you'd never move to, salaries below your floor, and roles you have no skills for.

A **filter** is the rule "only show me jobs in my city, at or above my salary, in my technology stack." Most postings get rejected at the inbox. The filter is applied at the moment each new job hits the inbox — not five days later. You never bother reading them at all.

A **confirmation rule** would instead say "after the alert fires, wait a week and check whether the listing is still open and the salary range is still posted." You still read every alert; you just delay your response.

## Numeric example

Same 180-day synthetic series, 20-day SMA crossover:

| Configuration | Signals | Closed-trade P&L |
|--------------|---------|------------------|
| Without filter | 20 | –$0.28 |
| With slope filter | 3 | **+$5.87** |

The filter cut signals 6× and turned a flat result into a profitable one — by avoiding the cluster of whipsaws in the choppy zones.

## Code

[[../codes/07_filter.py]]

```python
def ma_signals_with_filter(prices, n, use_filter=True):
    ma = pd.Series(prices).rolling(n).mean().values
    sigs, pos = [], 0
    for i in range(n+1, len(prices)):
        ma_rising = ma[i] > ma[i-1]
        cross_up = prices[i] > ma[i] and prices[i-1] <= ma[i-1]
        cross_dn = prices[i] < ma[i] and prices[i-1] >= ma[i-1]
        if cross_up and pos != 1:
            if not use_filter or ma_rising:
                sigs.append({'day': i, 'price': prices[i], 'side': 'BUY'}); pos = 1
        elif cross_dn and pos != -1:
            if not use_filter or not ma_rising:
                sigs.append({'day': i, 'price': prices[i], 'side': 'SELL'}); pos = -1
    return sigs
```

## Relationships

### Within the chapter

- **Sister concept to:** [[06_Confirmation_Conditions]] — same goal (kill false signals), different timing.
- **Most useful with:** [[02_Moving_Average_Systems]], where the slope-of-MA filter is the canonical example.
- **Layered above:** any base trend system — [[02_Moving_Average_Systems]], [[04_Crossover_Moving_Average_System]], [[05_Breakout_Systems]].
- **Compatible with:** [[08_Market_Characteristic_Adjustments]] (a regime classification can act as a filter), [[10_Pyramiding]] (filter pyramid signals more strictly than base signals).

### Beyond the chapter

- **Ch. 4 (Trading Ranges):** identifying a trading range is exactly the regime classification that becomes a filter input.
- **Ch. 6 (Oscillators):** an overbought reading can be used as a filter rejecting further buy signals near a peak.
- **Ch. 11 (Most Important Rule):** failed-signal logic itself is a kind of filter — repeated failures reclassify the market.
- **Ch. 15 (Testing):** filter parameters increase parameter-set count; honest testing must include the filter cost.

### When filters help most

- **Range-bound or whipsaw-prone markets** — the slope filter alone often turns a losing trend system into a flat or modestly profitable one.
- **Multi-system or ensemble setups** where you want only your highest-conviction trades to fire.
- **Lower-volatility, well-behaved instruments** (large-cap stocks, major currencies) where regime context is reasonably stable.

They hurt when the filter is too restrictive — at some point you've filtered away most of the real moves too.
