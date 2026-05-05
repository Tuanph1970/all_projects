# 13 — Multi-Timeframe Chart Decomposition

> Extension to Chapter 12. This concept is not in Schwager's text — it's a synthesis built on top of his pattern vocabulary, motivated by the question: *"can we decompose a chart into a list of patterns the way Fourier decomposes a signal into frequencies?"*

## The Question

A single chart view can simultaneously contain a long-term trend, a medium-term flag, a short-term wide-ranging day, and a bull trap formed by their interaction. Schwager's Figure 12.17 explicitly illustrates this: bull trap + island reversal + spike high + wide-ranging day all on the same bar. **Can we decompose a chart automatically into a list of overlapping patterns?**

## Why It's Not Quite a Fourier Transform

Fourier decomposes a signal into an **orthogonal basis** of sinusoids — every signal has a unique decomposition, and the components don't overlap in meaning. Chart patterns do not work that way:

| Property | Fourier | Chart patterns |
|---|---|---|
| Basis | Orthogonal sinusoids | Named, overlapping shapes |
| Decomposition | Unique | Many valid labelings |
| Components | Independent | Often nested or contradictory |
| Time localization | Global (FT) or local (wavelets) | Always local |
| Multi-scale | Naturally (wavelets) | Yes — same chart, multiple timeframes |

The closer mental model is **multi-scale object detection in computer vision**: the same image contains a face, a smile, two eyes, a nose — all true, all overlapping, no canonical decomposition.

## The Pipeline

```
                    ┌───────────────────┐
   raw OHLC  ─────► │ Layer 1: resample │ ─► daily, weekly, monthly views
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Layer 2: detectors│ ─► one per Chapter 12 concept
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Layer 3: findings │ ─► (pattern, tf, span, conf, dir)
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Layer 4: cluster  │ ─► group findings by time overlap
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Layer 5: score    │ ─► conviction + bullish/bearish bias
                    └───────────────────┘
```

Every detector is a wrapper around a Chapter 12 concept function:

| Detector | Source concept |
|---|---|
| `bull_trap` | [[05_Bull_Trap]] |
| `bear_trap` | [[06_Bear_Trap]] |
| `flag` | [[07_Flag_and_Pennant_Continuation]] |
| `counter_breakout` | [[08_Counter_to_Anticipated_Breakout]] |
| `wide_ranging_day` | [[09_Wide_Ranging_Day]] |
| `island_reversal` | [[11_Island_Reversal_and_Spike_High]] |
| `spike_high` | [[11_Island_Reversal_and_Spike_High]] |
| `trend` | trend slope context |

## Illustration

![[13_decomposer_overlay.png]]

A 250-day synthetic series with an engineered bull-trap top in May–August. The decomposer's strongest confluence zone (dark red shading, 9 stacked signals, very_high conviction, BEAR bias) lands directly on the engineered top, exactly where Schwager's discipline says to be most alert. Smaller, weaker confluence zones appear elsewhere — the system surfaces them honestly, which is what lets a trader filter for the high-conviction setups.

## Numeric Example — What the Output Looks Like

Running on the synthetic series above, the decomposer reports (truncated):

```
Total findings: 27
Confluence groups: 10

[1] 2023-05-26 → 2023-08-25  (9 signals, conviction=very_high, bias=BEAR, net=-4.45)
    ↓ [W] bull_trap            conf=0.70  breakout above 113.49 failed back
    ↓ [D] bull_trap            conf=0.70  breakout above 114.61 failed back
    ↓ [D] island_reversal      conf=0.80  gap up + gap down isolating cluster
    ↓ [D] spike_high           conf=0.45  upper tail >1.5 ATR above prior close
    ↓ [D] wide_ranging_day     conf=0.50  TR 1.53
    ↓ [D] flag_pennant         conf=0.55  bearish pole 5.28
    ...
```

Two things to notice:

1. The **same pattern fires on multiple timeframes** (`[W] bull_trap` + `[D] bull_trap`) — that's the decomposer expressing what Schwager calls "confluence on multiple time scales."
2. The group bias is computed as **net of bullish vs. bearish confidence**, not just count. A lone bullish signal inside an otherwise-bearish cluster pulls the net down but doesn't flip the bias.

## Python Usage

```python
from chart_decomposer import decompose_chart, summarize, to_dataframe
import pandas as pd

df = pd.read_csv("aapl_daily.csv", index_col="date", parse_dates=True)

findings, groups = decompose_chart(df, timeframes=("D", "W", "M"))

# Human-readable summary
print(summarize(findings, groups, top_n=5))

# Tidy DataFrame for further analysis
findings_df = to_dataframe(findings)

# Filter to high-conviction confluence zones only
strong = [g for g in groups if g.conviction in ("high", "very_high")]
for g in strong:
    print(f"{g.span_start.date()} → {g.span_end.date()}: "
          f"{len(g.findings)} signals, "
          f"net={g.net_score:+.2f} ({g.conviction})")
```

## Practical Reality Check

Three things worth knowing before relying on this in a live workflow:

1. **It will over-report.** Eight detectors × multiple timeframes × hundreds of bars = lots of findings, most low-conviction. The useful output is the **top-N confluence groups**, not the full list. Filter aggressively.

2. **Detector confidence values are heuristic.** The `0.70`, `0.55`, `0.45` numbers in each detector are starting points, not calibrated probabilities. To make them meaningful, they need to be backtested against forward-return distributions on the instruments you actually trade.

3. **Confluence is correlation, not magic.** When several patterns fire on the same bar, they often share underlying causes (a sharp price spike triggers wide_ranging_day, spike_high, *and* makes a bull trap visible). Treat the confluence count as a single rough conviction signal, not as N independent confirmations.

4. **Schwager's own framing argues against full automation.** He explicitly calls chart analysis "a very subjective endeavor" and recommends each trader build a personal vocabulary. Use the decomposer as an *attention-direction tool* — it points at zones worth studying — rather than as a signal generator.

## Relationships

### Within Chapter 12

This module is a synthesis of every Chapter 12 concept:

- **[[01_Primary_Premise_Violation]]** — when a confluence group's bias **flips** between two adjacent groups, that's a programmatic premise-violation event.
- **[[12_Expected_Gain_per_Trade]]** — confluence count is a candidate feature for filtering setups by expected gain. High-conviction groups historically tend to produce larger average wins; testing whether they actually do is straightforward with this output.

### Outside the chapter

- **Wavelet decomposition** — the closest mathematical analogue: localized in time, multi-scale, but components are still orthogonal. Charts aren't.
- **Empirical Mode Decomposition (EMD)** — splits price into intrinsic mode functions; useful as a *pre-processing* step before pattern detection if you want to detrend.
- **Computer-vision object detection** — the operational analogue. Same image, multiple overlapping bounding boxes, scored by confidence, deduplicated by non-maximum suppression. The cluster-by-overlap step here is essentially NMS.
- **Lo, Mamaysky & Wang (2000)** — academic baseline for automated chart pattern recognition. Modest but real informational content; unstable across regimes.

## Source

- Concept: extension of Chapter 12, motivated by user question on Fourier-style decomposition
- Code: [`chart_decomposer.py`](code/chart_decomposer.py), [`visualize_decomposer.py`](code/visualize_decomposer.py)
- Image: [`13_decomposer_overlay.png`](images/13_decomposer_overlay.png)
- Built on: all detectors in [`chapter12_concepts.py`](code/chapter12_concepts.py)
