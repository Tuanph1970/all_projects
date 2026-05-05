# 11 — Island Reversal and Spike High (Multi-Pattern Confluence)

## Definition

An **island reversal** is a chart pattern in which a cluster of bars (sometimes a single bar) sits **isolated by gaps on both sides** — a gap *up* into the cluster and a gap *down* out of it (top island), or the mirror at bottoms. Visually, the cluster looks marooned above (or below) the surrounding price action. A **spike high** (or low) is a single bar with an unusually long upper (or lower) tail that pierces well above the surrounding bars before closing back, often signalling exhaustion at the end of an extended move.

The point of grouping these in Chapter 12 is **confluence**: in Figure 12.17 (July 1994 soybeans), Schwager notes that **four bearish patterns occurred on a single day** — bull trap, island reversal, spike high, and wide-ranging day. When multiple independent reversal signals stack on the same bar, the probability of an actual top is dramatically higher than any one signal alone.

## Illustration

![[11_island_spike.png]]

The price gaps up to a high cluster, then gaps down — the cluster is left "stranded" above the rest of the chart. A spike high marks the same exhaustion in single-bar form.

## Analogy

A rocket fired straight up appears to hover at apogee for a long moment before falling — that hover is the island. The gap up is the final burn; the gap down is gravity reasserting itself; the bars in between are the moment of motionlessness when all the fuel is spent. A single rocket might hover briefly by chance, but if you watch it cough out a final puff of smoke (spike high), stall in mid-air (wide-ranging top), and then drop straight down through where it just was, you know the engine is done — not just "maybe done."

## Numeric Example

July 1994 soybeans (Figure 12.17), idealized values:

| Bar | Open | High | Low | Close | Pattern role |
|---|---|---|---|---|---|
| t−1 | 760 | 770 | 758 | 768 | normal up bar |
| t (gap-up) | **790** | 802 | 786 | 800 | gap above prior high (768) — start of island |
| t+1 (top) | 798 | **810** | 795 | 800 | spike high; wide-ranging in context |
| t+2 (gap-down) | 780 | 788 | **775** | 778 | gap below the cluster — island sealed |

Read together: **bull trap** (failed breakout above prior range), **island reversal** (gap-isolated cluster), **spike high** (810 well above closes), **wide-ranging day** (range 786–810 vs. typical ~10). The result was a sustained downtrend.

## Python

```python
from chapter12_concepts import detect_island_reversal, spike_high, wide_ranging_day
import pandas as pd

# Construct a tiny bar series with a deliberate island top.
df = pd.DataFrame({
    "open":  [760, 765, 768, 790, 798, 780, 770, 760],
    "high":  [770, 772, 775, 802, 810, 788, 775, 765],
    "low":   [758, 760, 765, 786, 795, 775, 763, 753],
    "close": [768, 770, 773, 800, 800, 778, 765, 755],
})

islands = detect_island_reversal(df)
spikes  = spike_high(df, lookback=3, k=1.5)
wide    = wide_ranging_day(df, lookback=3, k=1.5)

confluence = pd.DataFrame({"island": islands, "spike": spikes, "wide": wide})
confluence["count"] = confluence.sum(axis=1)
print(confluence)
# The island bar(s) typically register multiple True flags simultaneously.
```

## Relationships

### Within Chapter 12

- **[[05_Bull_Trap]]** — Figure 12.17 explicitly enumerates the bull trap as one of the four overlapping signals; islands and traps reinforce each other.
- **[[09_Wide_Ranging_Day]]** — wide-ranging bars often *form the spike* itself, so the two patterns commonly coincide.
- **[[01_Primary_Premise_Violation]]** — multiple coincident reversal signals provide an unambiguous premise for liquidating any long position.
- **The general lesson — confluence:** a chart pattern's reliability scales nonlinearly with the number of *independent* signals confirming it.

### When does it work best?

Strongest at **the end of extended advances** (or declines for bottom islands), where exhaustion is plausible. The more patterns that line up on the same bar, the higher the conviction. A lone island in the middle of a young trend is much less reliable than the same shape after a months-long extended advance.

The chapter explicitly notes another condition where exit makes sense even before classical confirmation: when there has been a **very quick, pronounced move** *and* **proximity of major support/resistance** — these are setups particularly prone to abrupt pullbacks, so partial profit-taking near major levels is reasonable.

### Outside the chapter

- **Chapter 5 — Chart Patterns.** Spike highs/lows and island reversals are introduced as one-day reversal patterns.
- **Chapter 11 — Failed Signals.** Many of the patterns that compose a Figure-12.17-style confluence are themselves "failed signal" events (the bull trap especially).
- **Chapter 17 — Trading Rules** (rule 56): a breakout to new highs followed within a week or two by a gap back into the range is one of the most reliable bull-trap variants — exactly the geometry of an island top.
- **Chapter 18 — Market Wizardry.** The principle that *multiple independent confirmations* dramatically improve trade quality recurs throughout the Wizards interviews.

## Source

- Schwager, *Getting Started in Technical Analysis*, Ch. 12, Figures 12.17, 12.18
- Background: Ch. 5 — Chart Patterns (spikes, islands, one-day reversals)
- Code: [`chapter12_concepts.py → detect_island_reversal(), spike_high()`](code/chapter12_concepts.py)
- Image: [`11_island_spike.png`](images/11_island_spike.png)
