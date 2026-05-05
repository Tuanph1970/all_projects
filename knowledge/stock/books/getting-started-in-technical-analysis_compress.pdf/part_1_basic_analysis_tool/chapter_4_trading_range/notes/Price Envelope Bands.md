# Price Envelope Bands

**Source:** Schwager, *Getting Started in Technical Analysis*, Ch. 4, pp. 69–72
**Parent:** [[Chapter 4 - Trading Ranges and Support and Resistance]]

## Definition

A **price envelope band** is a pair of curves drawn around a moving average that tries to contain most of the price action. The upper curve is the moving average plus a fixed percentage; the lower curve is the moving average minus the same percentage:

$$
\text{upper} = \text{MA} \times (1 + p) \qquad \text{lower} = \text{MA} \times (1 - p)
$$

By choosing an appropriate percentage `p` for the market, the band is calibrated so that relative highs land near the upper boundary and relative lows land near the lower boundary. Touching the upper band suggests **overbought**; touching the lower band suggests **oversold**.

**Bollinger Bands** are a well-known variant that uses a rolling standard deviation instead of a fixed percentage:

$$
\text{upper} = \text{MA} + k\sigma \qquad \text{lower} = \text{MA} - k\sigma
$$

with `k` typically set to 2. The advantage of Bollinger Bands is that they automatically widen during high-volatility periods and narrow during quiet periods.

**Important caveat from the chapter**: envelope bands are *not infallible*. During strong, sustained trends, prices can hug one band for weeks while the band drifts along with the trend — i.e., "overbought" or "oversold" can persist far longer than the trader's patience. Envelope bands are most useful in ranging markets and least useful in trending ones.

## Illustration

![[06_envelope_bands.png]]

*Top panel: a 2.5% percent envelope around a 20-day moving average. The dashed lines walk up and down with the MA, defining a dynamic corridor. Bottom panel: Bollinger Bands (MA ± 2σ) on the same data — notice how the bands automatically widen and narrow with volatility, while the percent envelope keeps a constant relative width.*

## Analogy

Imagine walking a dog on a long elastic leash. The dog drifts side to side as it walks but mostly stays within leash length of you. As you walk forward, the area the dog can reach moves with you — it's not a fixed fence in one place, it walks with the walker.

The moving average is *you*. The envelope band is the *reach of the leash*. The percentage version is a leash of constant length. Bollinger Bands are a leash that gets longer when the dog is excited and shorter when calm.

When the dog is at the end of the leash, you predict it'll snap back toward you soon — that's overbought/oversold. But if you're walking briskly downhill and the dog is sprinting just ahead of you, the dog can stay at the end of the leash for a long time without snapping back. That's the trending-market failure mode.

## Numeric example

Stock MNO daily closes over the last 20 days average to **MA = $100.00**. Standard deviation of those closes is **σ = $1.50**.

| Method                         | Upper          | Lower          |
|:-------------------------------|---------------:|---------------:|
| Percent envelope (2.5%)        | 100 × 1.025 = **102.50** | 100 × 0.975 = **97.50** |
| Bollinger Bands (k = 2)        | 100 + 2(1.50) = **103.00** | 100 − 2(1.50) = **97.00** |

If today's close is **102.80**, both bands flag the same thing: prices are at or beyond the upper band → overbought.

Now suppose the next day closes at **104.20**, with the new MA at $100.50 and σ rising to $1.80:

| Method                         | Upper          | Lower          |
|:-------------------------------|---------------:|---------------:|
| Percent envelope (2.5%)        | 100.5 × 1.025 = **103.01** | 100.5 × 0.975 = **97.99** |
| Bollinger Bands (k = 2)        | 100.5 + 3.60 = **104.10**  | 100.5 − 3.60 = **96.90** |

The percent envelope still flags overbought (104.20 > 103.01). The Bollinger Band has widened with volatility (104.20 ≈ 104.10) — barely overbought. This is exactly the trend-hugging case the chapter warns about.

## Code

See [[code/price_envelope.py]] — implements both `percent_envelope()` and `bollinger_bands()` with a common `EnvelopeResult` return type, plus an `envelope_signals()` helper that flags overbought/oversold bars.

```python
from price_envelope import percent_envelope, bollinger_bands, envelope_signals

env = percent_envelope(prices, window=20, pct=0.025)
bb  = bollinger_bands(prices,  window=20, num_std=2.0)

flags = envelope_signals(prices, env)
print(f"Overbought touches: {flags['overbought'].sum()}")
print(f"Oversold touches:   {flags['oversold'].sum()}")

# Last bar diagnostic
print(f"Price={prices[-1]:.2f}, "
      f"MA={env.ma[-1]:.2f}, "
      f"Env=[{env.lower[-1]:.2f},{env.upper[-1]:.2f}], "
      f"BB=[{bb.lower[-1]:.2f},{bb.upper[-1]:.2f}]")
```

The two band types share the same MA computation; the only difference is what gets added/subtracted (a percentage of the MA vs. a multiple of the rolling standard deviation).

## Within-chapter relationships

- **vs. [[Trading Range]] boundaries** — both contain price action between two horizontal-ish lines. Range boundaries are *fixed and only valid while the range holds*. Envelope bands are *dynamic and always defined* — they keep working as the market drifts. The trade-off: range boundaries are more decisive when valid; envelope bands are always available but noisier.
- **vs. [[Prior Major Highs and Lows]]** — these give you S/R at fixed historical price levels; envelopes give you S/R as a moving target. Strongest signals occur when an envelope band coincides with a historical level.
- **vs. [[Concentrations of Relative Highs and Lows]]** — both produce **zones** rather than points. Concentrations are static and historical; envelopes are dynamic and statistical.

When does this work well?

- Sideways/ranging markets without strong trend
- Mean-reverting markets (some currency pairs, some equity indices in low-vol regimes)
- Combined with another signal (e.g. oscillator divergence at the band)

When does it fail?

- Strong trending markets — prices ride one band for weeks. Repeatedly fading into the band produces a string of losses.
- Volatility expansions — Bollinger Bands widen, but the percent envelope doesn't, leading to many false signals on percent-based bands during volatile periods.
- Right at the start of a new trend — the band captures the prior regime, not the new one.

## Cross-chapter relationships

- [[Chapter 3 - Trends]] — the moving average that powers the envelope is itself a trend-following tool from Ch. 3. Envelope bands are essentially "S/R thinking grafted onto a trend tool".
- [[Chapter 6 - Oscillators]] — both envelope bands and oscillators (RSI, stochastics) try to identify overbought/oversold conditions, and both share the same failure mode in trending markets. They work best as cross-confirmation tools.
- [[Chapter 14 - Trend-Following Systems]] — the same MA used for an envelope band can drive trend-following signals (price crosses above MA = buy). Combining: only fade the upper band when the MA is *flat*, not when it's *rising* — the latter is a trend signal, not a reversal signal.
- [[Chapter 9 - Stop-Loss Points]] — a band-touch stop is a *volatility-adaptive* stop: in quiet markets it is tight, in noisy markets it widens. This is structurally similar to ATR-based stops introduced later.
- [[Chapter 8 - Midtrend Entry]] — a touch of the *lower* band during an established uptrend (a pullback that doesn't break the trend) can be used as a midtrend entry trigger.

## Tags

#technical-analysis #chapter-4 #envelope #bollinger-bands #moving-average #overbought #oversold
