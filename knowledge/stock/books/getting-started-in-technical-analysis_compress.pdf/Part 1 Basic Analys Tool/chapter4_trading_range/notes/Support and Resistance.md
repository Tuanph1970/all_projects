# Support and Resistance

**Source:** Schwager, *Getting Started in Technical Analysis*, Ch. 4, pp. 58–67
**Parent:** [[Chapter 4 - Trading Ranges and Support and Resistance]]

## Definition

**Support** is a price level (or zone) at which buying interest has historically been strong enough to halt declines and push prices back up — a metaphorical *floor*. **Resistance** is a price level (or zone) at which selling pressure has historically been strong enough to halt rallies and push prices back down — a metaphorical *ceiling*.

Two key behavioral observations from the chapter:

- These levels should always be treated as **approximate zones, not precise points**. Markets do not turn on the penny.
- After a level is decisively broken, **its role flips**. A ceiling that gets pierced becomes a floor on the next pullback; a floor that gets pierced becomes a ceiling on the next rally. This is one of the most useful (and reliably observed) phenomena in technical analysis.

## Illustration

![[03_sr_flip.png]]

*Prices oscillate in a range with 105 acting as resistance (the gray box). Once that ceiling is decisively broken (around day 95), prices trend up. When prices later pull back, they bounce off the same 105 level — now acting as **support**. Same line, opposite role.*

## Analogy

Think of the ceiling above your head while you stand in a basement with a glass ceiling. Throw a ball up: it bounces off the ceiling. That ceiling is *resistance*. One day, someone breaks the glass and you climb up to the ground floor. You are now standing **on top of** the same glass — it is now a *floor*. If you slip, you'll bump into it from above. The physical object hasn't moved; your relationship to it has.

That's why the same price level keeps showing up as both support and resistance over time, depending on which side of it the market is currently sitting.

## Numeric example

Stock DEF trades sideways between **$45 and $50** for 4 months, hitting $50 four separate times without breaking through.

- $50 is acting as resistance.
- A trader who shorts at $50 with a stop at $50.75 has roughly $0.75 of risk; if price falls back to $45, the reward is $5. Reward/risk ≈ 6.7×.

In month 5, prices break out to $54 and stay above $50 for two weeks.

- $50 is now expected to act as support.
- A trader who buys on a pullback to $50.20 with a stop at $48.50 has $1.70 of risk; if the new uptrend reaches $58, reward is $7.80. Reward/risk ≈ 4.6×.

The same level produced two different but equally clean trade setups, six months apart, just by changing roles.

## Code

See [[code/support_resistance.py]] — `levels_at_now()` returns prior major highs and lows classified as either support or resistance from the perspective of the current price (handling the role-reversal rule automatically).

```python
from support_resistance import levels_at_now

# For each prior major high/low, classify it relative to today's price
for lvl in levels_at_now(prices, current_day=180, n=5):
    print(lvl)
# SRLevel(support @ 87.80 from day 49 [prior_low])
# SRLevel(resistance @ 101.56 from day 14 [prior_high])
```

The classification logic:

```python
if prior_high > current_price:
    role = 'resistance'             # not yet broken — it's a ceiling above us
else:
    role = 'support'                # we broke above it — flipped to floor
```

## Within-chapter relationships

- **Foundation for the chapter** — every other concept in Ch. 4 is a *method* for finding support and resistance:
  - [[Trading Range]] boundaries → S/R
  - [[Prior Major Highs and Lows]] → S/R
  - [[Concentrations of Relative Highs and Lows]] → S/R *zones*
  - [[Price Envelope Bands]] → *dynamic* S/R derived from a moving average
- **vs. [[Trading Range Breakout]]** — a breakout is exactly the moment when an S/R level fails, which is also the moment that level is about to flip its role.

When does S/R analysis work well?

- Markets watched by many participants (where memory of past prices is collective)
- Liquid markets with clear historical reference points
- After clean, well-defined prior peaks or troughs

When is it less reliable?

- Highly news-driven markets where fundamentals overwhelm chart memory
- Newly listed instruments without much history
- During rapid regime changes (e.g., post-merger, post-earnings shock)

## Cross-chapter relationships

- [[Chapter 5 - Chart Patterns]] — head-and-shoulders, double tops, triangles all derive their meaning from S/R: the "neckline" of a head-and-shoulders is precisely a support level whose break confirms the pattern.
- [[Chapter 9 - Stop-Loss Points]] — a logical stop sits *just beyond* a support or resistance level, because if the level breaks, your trading premise is invalidated.
- [[Chapter 10 - Setting Objectives]] — a logical profit target sits *just before* the next overhead resistance (for longs) or next underlying support (for shorts).
- [[Chapter 6 - Oscillators]] — overbought/oversold readings near known resistance/support are stronger signals than oscillator readings in mid-range.

## Tags

#technical-analysis #chapter-4 #support #resistance #role-reversal
