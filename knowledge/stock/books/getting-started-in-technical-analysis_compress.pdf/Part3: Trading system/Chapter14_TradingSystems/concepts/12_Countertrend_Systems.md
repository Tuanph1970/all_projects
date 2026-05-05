# 12 — Countertrend Systems

## Definition

A **countertrend system** waits for a meaningful price move and then takes a position in the **opposite** direction, on the assumption that the market is due for a correction. It's a deliberate inversion of trend-following.

Three flavors covered in the chapter:

1. **Fading minimum move** — the most direct approach. A sell signal fires whenever the market rallies by some minimum amount above the most recent low (since the last countertrend buy). A buy signal fires symmetrically on a decline below the most recent high. The threshold can be expressed in points, percent, or ATR units.

2. **Oscillator-based** — use an oscillator (RSI, stochastic, Williams %R, etc.) to flag overbought or oversold conditions and trade against the prevailing move. Works adequately in range-bound markets and is **disastrous** in trending markets, where oscillators stay pegged at extremes for weeks.

3. **Contrary opinion** — use sentiment readings (e.g., bullish-percent surveys) as input. When sentiment is extremely bullish, take a short with a confirming technical trigger; when extremely bearish, take a long.

The crucial insight: countertrend systems work *best* exactly where trend-following systems fail (sideways markets), and fail *worst* exactly where trend-following systems shine (sustained trends). This makes them complementary — not replacements.

## Illustration

![[12_countertrend.png]]

A range-bound market that oscillates around 100. Each green up-arrow marks a countertrend buy after a 4% drop from a recent peak; each red down-arrow marks a countertrend sell after a 4% rally from a recent trough. In a sideways market, every signal is profitable. In a strong trend, the same logic would generate ruinous losses.

## Analogy

You're at a beach watching the tide come in and out. The water level keeps oscillating around an average.

- **Trend-following thinking:** "Water is rising fast — let's bet it'll keep rising."
- **Countertrend thinking:** "Water has risen X feet from the recent low — the tide always reverses, let's bet it's about to come down."

In a normal day with regular tides, the countertrend bet wins almost every time. But during a tsunami, betting against the rising water level is catastrophic. The same logic that works in calm conditions destroys you when the system you're betting against (the regular tide) breaks down.

## Numeric example

Same simulation framework, threshold 4%:

| Market type | Countertrend signals | Outcome |
|-------------|----------------------|---------|
| Range-bound (sin wave + noise) | 7 signals | Most profitable — buys near lows, sells near highs |
| Trending (drifting up) | 1 signal | Single sell signal taken right as the trend kept rising — losing |

The signal *count* is similar order of magnitude in both, but the *outcome* is opposite. The decisive factor is regime, not the threshold.

## Code

[[../codes/12_countertrend.py]]

```python
def fade_minimum_move(prices, threshold=0.04):
    p = np.asarray(prices, dtype=float)
    sigs = []
    last_signal_side = None
    peak = p[0]; trough = p[0]
    for i in range(1, len(p)):
        peak = max(peak, p[i])
        trough = min(trough, p[i])
        if last_signal_side != 'BUY' and p[i] <= peak * (1 - threshold):
            sigs.append({'day': i, 'price': p[i], 'side': 'BUY'})
            last_signal_side = 'BUY'
            peak = p[i]; trough = p[i]
        elif last_signal_side != 'SELL' and p[i] >= trough * (1 + threshold):
            sigs.append({'day': i, 'price': p[i], 'side': 'SELL'})
            last_signal_side = 'SELL'
            peak = p[i]; trough = p[i]
    return sigs
```

## Relationships

### Within the chapter

- **Direct opposite of:** [[01_Trend_Following_Systems]] — same chapter, opposite philosophy.
- **Often combined with:** [[06_Confirmation_Conditions]] (a thrust day in the countertrend direction is a popular confirmation).
- **Critical filter need:** must use [[07_Filter]] to detect a trending vs range-bound market, otherwise it gets demolished in trends.
- **Diversification benefit:** [[13_Diversification]] explicitly recommends mixing countertrend systems with trend-following ones for portfolio smoothness.

### Beyond the chapter

- **Ch. 6 (Oscillators):** introduces the indicators that countertrend systems rely on (RSI, stochastic, Williams %R) and explicitly warns about their failure mode in trends.
- **Ch. 4 (Trading Ranges):** trading ranges are the home turf of countertrend systems.
- **Ch. 17 (82 Trading Rules):** several rules concern fading extreme moves — countertrend logic in discretionary form.

### When countertrend systems help most

- **Sideways, range-bound markets** with clear support/resistance.
- **Mean-reverting instruments** like spreads (e.g., calendar spreads in commodity futures) and pair trades.
- **Short-term timeframes** where reversion tends to be reliable.

They fail catastrophically when:
- **Trends become persistent** — the system keeps shorting into a rising market and gets stopped out repeatedly at higher and higher prices.
- **Sudden regime changes** turn a range market into a trending one overnight.

The Schwager prescription: **never use a countertrend system without a regime classifier or a hard stop**. The damage from being wrong about a regime is asymmetric — gains accumulate slowly when right, losses arrive all at once when wrong.
