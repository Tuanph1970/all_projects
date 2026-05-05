# Concentrations of Relative Highs and Lows

**Source:** Schwager, *Getting Started in Technical Analysis*, Ch. 4, pp. 67–69
**Parent:** [[Chapter 4 - Trading Ranges and Support and Resistance]]

## Definition

A **concentration of relative highs and lows** is a narrow price band that contains *multiple* prior relative extremes — minor peaks and troughs that may individually look unremarkable, but collectively define a meaningful price zone. When this clustered band lies *above* the current price, it acts as a **resistance zone**; when it lies *below* the current price, it acts as a **support zone**.

The intuition contrasts directly with the previous concept ([[Prior Major Highs and Lows]]):

- A single, dramatic peak/trough is one data point. It can be cleanly defined but it is statistically just one observation.
- A *cluster* of less-extreme relative peaks/troughs all sitting in roughly the same price band is many data points pointing at the same level — stronger statistical evidence.

The chapter notes this method is especially useful on **long-term charts** (weekly bars, or daily charts with at least ~2 years of history) where enough relative extremes have accumulated.

## Illustration

![[05_concentrations.png]]

*Red ▼ marks every relative high (the bar is the max within ±5 bars); green ▲ marks every relative low. The shaded red band shows where many relative highs have piled up — a resistance zone. Notice it's a band, not a single line: clusters define **zones** rather than precise points.*

## Analogy

Picture a busy parking lot. There's no painted line saying "park here", but cars repeatedly end up clustered at one end — maybe because that end is closer to the entrance, or it's shaded. After a week of watching, you notice that even though no single car is special, the cluster defines a "preferred zone" where parking activity concentrates.

A new driver arriving doesn't need to know why; they just need to know cars *will* tend to slow down and stop in that band. That's exactly how a concentration of relative highs/lows works on a chart — many small individual decisions ("I'll take profits here", "I'll start selling here") aggregate at a price level for reasons no one needs to articulate, and the collective behavior creates a zone where future activity will keep clustering.

## Numeric example

Stock JKL has these relative highs over the past 18 months (using a 5-bar definition: a bar's high is greater than the highs of the 5 bars before and after):

| Relative high # | Date    | Price  |
|----------------:|:--------|-------:|
| 1               | Mar '24 | 71.20  |
| 2               | May '24 | 70.85  |
| 3               | Jul '24 | 71.50  |
| 4               | Sep '24 | 70.40  |
| 5               | Dec '24 | 71.10  |

All five highs sit between 70.40 and 71.50 — a band roughly 1.1 wide on a ~71 base, or about **1.5%**. Five distinct rejections in a 1.5%-wide band is a strong concentration.

- Current price = 65.00
- **Resistance zone**: 70.40 – 71.50

A trader long from 65 should:

- Expect price action to slow down approaching 70.40
- Consider taking partial profits as the band is reached
- Only believe in a true breakout once a confirmed close occurs above 71.50 + a buffer (say, 72.20 = +1%)

## Code

See [[code/concentration_zones.py]] — it identifies all relative extremes, then greedily clusters them by price proximity. Clusters with at least N members become zones.

```python
from concentration_zones import find_zones

zones = find_zones(
    prices,
    current_day=290,
    n=5,                  # 5-bar definition of relative high/low
    bandwidth_pct=0.025,  # cluster all extremes within 2.5% of each other
    min_members=3,        # need at least 3 extremes to call it a zone
)
for z in zones:
    print(z)
# Zone(resistance 70.40-71.50, 5 members)
# Zone(support 60.20-61.10, 4 members)
```

The clustering is one-dimensional and greedy: sort the extremes by price, then walk the sorted list grouping any value within `bandwidth_pct` of the cluster's anchor.

## Within-chapter relationships

- **vs. [[Prior Major Highs and Lows]]** — the dial here is "single point vs. zone". Major highs/lows give you precise but solitary signals; concentrations give you fuzzier but multiply-confirmed signals. The two work best in combination: trade *toward* major highs/lows, but use zones to gauge how much hesitation to expect along the way.
- **vs. [[Trading Range]]** — a long-running trading range will *itself* produce concentrations of relative highs near its top and relative lows near its bottom. So the concept is partly a generalization of "the range produces S/R at its boundaries".
- **vs. [[Price Envelope Bands]]** — both define **zones** rather than points, but concentrations are *historical and static* (the band is rooted in actual past price extremes), whereas envelope bands are *current and dynamic* (the band is recomputed each day from a moving average).

When does this work well?

- Long-history charts (weekly or daily over 2+ years)
- Markets without major regime changes (the historical extremes still reflect the current "world")
- After identifying 3+ relative extremes in a tight band — the more, the stronger

When is it less useful?

- Short charts (a single futures contract, recently listed stock) — too few extremes to cluster
- Markets with a strong trending bias — relative highs/lows keep walking up or down, no clustering
- After major fundamental changes that reset the price context

## Cross-chapter relationships

- [[Chapter 3 - Trends]] — the relative-high/relative-low concept comes directly from Ch. 3's definition of trend (uptrend = succession of higher highs and higher lows). Once you have those points, you can either trace trend lines through them (Ch. 3) or cluster them (this concept).
- [[Chapter 5 - Chart Patterns]] — a "rectangle" (a special case of trading range) is essentially a particularly clean concentration of relative highs at one level and relative lows at another.
- [[Chapter 6 - Oscillators]] — oscillator divergences taken *at a known concentration zone* are stronger signals than isolated divergences.

## Tags

#technical-analysis #chapter-4 #zones #clusters #relative-extremes
