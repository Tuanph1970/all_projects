# 09 — Differentiation Between Buy and Sell Signals

## Definition

Basic trend-following systems use **symmetric** rules — the same lookback for buys and sells (e.g., buy on 20-day high, sell on 20-day low). Schwager argues this symmetry is unjustified: bull and bear markets often behave very differently.

The empirical observation: price breaks from major **tops** tend to be sharper and faster than rallies from major **bottoms**. Tops form quickly (panic, liquidation); bottoms form slowly (accumulation, capitulation followed by basing).

The implication: it can make sense to use **more sensitive conditions for sell signals than for buy signals**. For example, in a breakout system, *N=30* for buys but *N=10* for sells.

But there's a major caveat — every additional asymmetry adds parameters, and parameters compound overfitting risk (Chapter 15). Don't introduce buy/sell asymmetry just because you can; introduce it only if there's a robust empirical case for it.

## Illustration

![[09_buy_sell_diff.png]]

A market that rises slowly, then crashes. A symmetric system would either be too late on the rise (large N) or too jumpy on the rise (small N). With buy=30 and sell=10, the system enters cleanly during the slow rise and exits decisively when the crash starts.

## Analogy

You're hiring people for your team and you're about to fire someone who is underperforming.

- **Hiring** is a slow process. You take 30 days of interviews, references, trial work — you want to be very sure before bringing someone on.
- **Firing** can be much faster. If someone is causing serious damage to the team, you don't take 30 days to confirm — you act on shorter, sharper signals.

You're not being inconsistent. You're recognizing that the *underlying processes* are asymmetric: building takes longer than breaking. Markets are similar — bull markets are built; bear markets break.

## Numeric example

Same simulated bull-then-bust series:

| Configuration | Signals fired |
|--------------|--------------|
| Symmetric (N=20 / N=20) | 1 BUY @ 106.66 (day 20), 1 SELL @ 124.04 (day 107) |
| Asymmetric (Nb=30, Ns=10) | 1 BUY @ 108.23 (day 32) — sell still pending |

The sample is small but the mechanism is visible: the asymmetric system enters slightly later (more conservative buy), and would have exited the long faster on any sharper turn down.

## Code

[[../codes/09_buy_sell_diff.py]]

```python
def asymmetric_breakout(prices, N_buy, N_sell):
    p = np.asarray(prices, dtype=float)
    sigs, pos = [], 0
    start = max(N_buy, N_sell)
    for i in range(start, len(p)):
        hi_buy = p[i-N_buy:i].max()
        lo_sell = p[i-N_sell:i].min()
        if p[i] > hi_buy and pos != 1:
            sigs.append({'day': i, 'price': p[i], 'side': 'BUY'}); pos = 1
        elif p[i] < lo_sell and pos != -1:
            sigs.append({'day': i, 'price': p[i], 'side': 'SELL'}); pos = -1
    return sigs
```

## Relationships

### Within the chapter

- **Sibling of:** [[08_Market_Characteristic_Adjustments]] — both inject asymmetry into a previously symmetric system.
- **Modification of:** [[05_Breakout_Systems]] and [[04_Crossover_Moving_Average_System]] (different MA lengths for long-cross vs short-cross).
- **Cross-references:** the chapter explicitly flags the danger of overfitting — also see [[06_Confirmation_Conditions]] and [[07_Filter]] which add fewer parameters per unit of improvement.

### Beyond the chapter

- **Ch. 5 (Chart Patterns):** top-formation patterns (head-and-shoulders, double tops) and bottom-formation patterns are visually different — confirming that the underlying processes really are asymmetric.
- **Ch. 9 (Stop-Loss Points):** stop placement also tends to be asymmetric — wider in calm uptrends, tighter in fast downtrends.
- **Ch. 15 (Testing):** every parameter you add this way must be validated by *blind simulation*, not in-sample fitting.

### When buy/sell asymmetry helps most

- Equities and equity indices, which historically show this top-vs-bottom asymmetry strongly.
- After major panics where the bottom is well-known to be a slow process.
- When you can support the asymmetry with a multi-decade backtest, not just a few cherry-picked years.

It hurts when applied in symmetric markets (some FX pairs, some commodity inversions where bottoms are sharp too) — there's nothing principled to anchor the asymmetry to.
