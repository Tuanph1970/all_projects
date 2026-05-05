# 06 — Confirmation Conditions

## Definition

A **confirmation condition** is a secondary requirement that must be satisfied *after* a basic system signal before the trade is actually taken. It's a "show me you mean it" rule.

Three common forms:

1. **Penetration** — the close must move beyond the trigger level by at least X% (or X ticks/points). A 2% penetration rule on a breakout means a marginal break by 0.5% is ignored.
2. **Time delay** — wait *D* days after the signal, then re-check. The trade is taken only if the move is still in force at day *D*.
3. **Pattern** — require a specific subsequent pattern, e.g. *K* thrust days in the signal direction.

The trade-off is fundamental: **fewer false signals, but worse entry prices on the real ones.** A confirmation rule pays off only when avoided losses on bad signals exceed surrendered profits on good ones.

## Illustration

![[06_confirmation.png]]

Three panels showing the same set of basic signals (light green) and which ones survive each confirmation method (dark green). All three approaches drop several would-be losers — at the cost of entering later on the real moves.

## Analogy

You hear someone shout "FIRE!" in the building. You can react three ways:

1. **Penetration:** Wait until you can actually smell smoke (a meaningful, measurable signal beyond the original alarm). Real fires give measurable smoke; pranks usually don't.
2. **Time delay:** Wait 5 minutes. If the alarm is still going, take it seriously. False alarms tend to get cancelled quickly; real ones stay live.
3. **Pattern:** Wait for three corroborating signs — alarm + smoke + people leaving. The combination is much harder to fake.

In all three cases you've slowed down. If it's a real fire, you've lost five precious minutes. If it's a false alarm, you've avoided a panicked evacuation. Whether the "wait" was worth it depends entirely on the base rate of real fires vs. false alarms in your building.

## Numeric example

Same 140-day series, 15-day breakout system:

| Variant | Signals fired |
|---------|--------------|
| Basic breakout (no confirmation) | 4 |
| + 2% penetration confirmation | 1 |
| + 5-day time-delay confirmation | 3 |
| + 3 thrust-day confirmation | 2 |

Penetration is the strictest filter here — only the most decisive breakouts survive. Time delay is the most permissive — most basic signals are still in the money five days later.

## Code

[[../codes/06_confirmation.py]]

```python
def confirm_penetration(prices, n, pct=0.02):
    sigs, pos = [], 0
    for i in range(n, len(prices)):
        hi = prices[i-n:i].max()
        lo = prices[i-n:i].min()
        if prices[i] > hi*(1+pct) and pos != 1:
            sigs.append({'day': i, 'price': prices[i], 'side': 'BUY'}); pos = 1
        elif prices[i] < lo*(1-pct) and pos != -1:
            sigs.append({'day': i, 'price': prices[i], 'side': 'SELL'}); pos = -1
    return sigs

def confirm_time_delay(prices, base_signals, delay=5):
    confirmed = []
    for s in base_signals:
        d = s['day'] + delay
        if d < len(prices):
            if s['side'] == 'BUY' and prices[d] > s['price']:
                confirmed.append({'day': d, 'price': prices[d], 'side': 'BUY'})
            elif s['side'] == 'SELL' and prices[d] < s['price']:
                confirmed.append({'day': d, 'price': prices[d], 'side': 'SELL'})
    return confirmed
```

## Relationships

### Within the chapter

- **Applied to:** all base systems — [[02_Moving_Average_Systems]], [[04_Crossover_Moving_Average_System]], [[05_Breakout_Systems]]. The confirmation rule lives one layer above the base.
- **Sibling concept:** [[07_Filter]]. Both reduce false signals, but they act at different times — filter at signal time, confirmation after.
- **A system can use both at once:** filter rejects up front; confirmation validates what survives the filter.

### Beyond the chapter

- **Ch. 7 (Is Chart Analysis Still Valid?):** introduces confirmation as one of two essential rescues for chart-based trading (the other being risk control).
- **Ch. 11 (Most Important Rule):** confirmation logic helps detect *failed signals* — when a confirmation never arrives, that itself is information.
- **Ch. 15 (Testing):** more confirmation parameters = more curve-fitting risk; the trader has to test honestly.

### When confirmation rules help most

- **Choppy / range-bound markets** where most basic signals are noise.
- **Markets with sharp daily intraday volatility** where end-of-day closes are more reliable than intraday prints.
- **Lower-conviction strategies** where the base signal is acknowledged to be noisy — confirmation adds back some signal-to-noise.

They hurt most in **fast-moving markets where missing the first few days is expensive** (commodity supply shocks, earnings gaps).
