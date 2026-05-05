# 10 — Pyramiding

## Definition

**Pyramiding** is the practice of *adding* units to an already-profitable position when evidence suggests the trend has resumed after a reaction. It addresses a structural weakness of basic trend-following systems: they always trade one constant unit size, no matter how good the trade is going. But because most of the system's lifetime profit comes from a small number of *huge* moves, it makes sense to size up when one of those huge moves appears to be in motion.

A representative pyramid scheme (long version):

1. **Reaction defined** — net position is long and the market closes below the prior 10-day low. (A reaction is a meaningful pullback.)
2. **Pyramid signal** — once a reaction is defined, an additional long is initiated on the next close above the prior 10-day high, *if*:
   - the pyramid signal price is above the price of the most recent buy (i.e., the trend really has resumed at higher prices);
   - the net position size is below the chosen maximum (e.g., 3 units total).

The risk-control half is essential and asymmetric: pyramid units use **tighter** stops than the base position. When you exit a pyramid, you usually liquidate all pyramid units while keeping the original base position unless an opposite trend signal also fires.

## Illustration

![[10_pyramiding.png]]

A strong uptrend with two clear reactions (orange dots). On the resumption of each reaction, a new long unit (lime triangle) is added at a higher price than the prior unit. The base position (green triangle, day 30) was the original entry.

## Analogy

You start jogging at a comfortable pace. After a few minutes, you decide you feel good — so you speed up a little. After a few more minutes of feeling fine, you speed up again. You're not speeding up at random — you only do it after each "checkpoint" where your body confirms it can handle the previous pace. If you ever start to flag, you don't just slow back down to your original speed; you slow much faster than you sped up.

That's pyramiding: incremental commitment in proportion to confirmed strength, with very different rules for going up vs. coming back down.

## Numeric example

```
Day  30 — Base buy   @ 116.22  (unit 1)
Day  65 — Pyramid #1 @ 136.52  (unit 2)
Day  86 — Pyramid #2 @ 142.97  (unit 3)
Final price          @ 160.02

Average cost per unit: 131.90
Open profit at end   : (160.02 – 131.90) × 3  = +$84.36
```

For comparison, the same trade with a single base unit (no pyramid) would have made:
`(160.02 – 116.22) × 1 = +$43.80`.

The pyramid roughly doubled the open profit — by sizing up after the trend confirmed itself rather than betting bigger upfront.

## Code

[[../codes/10_pyramiding.py]]

```python
def pyramid_long_only(prices, base_signal_idx, max_units=3, react_n=10):
    p = np.asarray(prices, dtype=float)
    units = [{'day': base_signal_idx, 'price': p[base_signal_idx], 'unit': 1}]
    in_reaction = False
    last_buy_price = p[base_signal_idx]

    for i in range(base_signal_idx + react_n, len(p)):
        lo_n = p[i-react_n:i].min()
        hi_n = p[i-react_n:i].max()
        if not in_reaction and p[i] < lo_n:
            in_reaction = True
        elif in_reaction and p[i] > hi_n and p[i] > last_buy_price and len(units) < max_units:
            units.append({'day': i, 'price': p[i], 'unit': len(units)+1})
            last_buy_price = p[i]
            in_reaction = False
    return pd.DataFrame(units)
```

## Relationships

### Within the chapter

- **Modification of:** any base trend-following system — [[04_Crossover_Moving_Average_System]], [[05_Breakout_Systems]].
- **Stop-rule sibling:** [[11_Trade_Exit]] — pyramiding is fundamentally about position sizing on the way *up*; trade exit is about how to get *out* (and pyramid units typically use tighter exit conditions than the base).
- **Risk-budget link:** [[13_Diversification]] — Schwager warns to size pyramid lots smaller than the base when total portfolio risk is already high.

### Beyond the chapter

- **Ch. 8 (Midtrend Entry & Pyramiding):** the same rule set is used for midtrend entries — Schwager explicitly notes that midtrend entry and pyramiding are the *same problem* (committing capital after a move has already started).
- **Ch. 9 (Stop-Loss Points):** the tighter pyramid stops are a direct application of the chapter-9 logic.
- **Ch. 16 (Planned Trading Approach):** pyramiding multiplies leverage, so it must be considered alongside the position-sizing framework for the whole account.
- **Famous example:** Jesse Livermore's "buying on the way up" technique described in *Reminiscences of a Stock Operator* — pyramiding before the term existed.

### When pyramiding helps most

- **Strong, sustained, low-noise trends** where reactions are real but the trend resumes cleanly.
- **Markets with low transaction costs** — every pyramid is a new round-trip cost.
- **Diversified portfolios** where the higher leverage on pyramided trades is offset by uncorrelated positions elsewhere.

It hurts in **choppy markets** where every "resumption" turns out to be another whipsaw — you stack losing-side units right at the top.
