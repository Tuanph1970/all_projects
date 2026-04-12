---
title: "Return to Wide-Ranging Day Extremes"
chapter: 11
concept: 8
tags:
  - failed-signals
  - wide-ranging-day
  - WRD
  - penetration
  - reversal
  - schwager
  - chapter-11
aliases:
  - WRD Penetration
  - Wide-Ranging Day Failed Signal
  - WRD Extreme
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Return to Spike Extremes]]"
  - "[[Filled Gaps as Failed Signals]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Return to Wide-Ranging Day Extremes

## Definition

A **wide-ranging day** (WRD) with a particularly strong or weak close normally leads to price extension in the same direction. When a subsequent **close penetrates the opposite extreme** of the WRD, the original day becomes a failed signal:

- Close **above the high** of a downside WRD → **BUY** (bearish continuation failed)
- Close **below the low** of an upside WRD → **SELL** (bullish continuation failed)

> *"Wide-ranging days with particularly strong or weak closes tend to lead to price extensions in the same direction. Consequently, the close above the high price of a downside wide-ranging day or below the low price of an upside wide-ranging day can be viewed as confirming such days as failed signals."*
> — Schwager, Ch. 11

---

## Simple Analogy: The Sledgehammer Blow

A wide-ranging day is like a sledgehammer blow to a nail (the price direction). A massive downside WRD drives the nail deep into "bearish" territory. But what if, weeks later, someone pulls the nail back out and hammers it the other way?

If even a sledgehammer blow couldn't keep the nail in place, that tells you the wood on the other side (the opposite trend) is much harder — much more powerful than the original blow. The bigger the hammer was, the more significant it is that the nail was pulled back out.

---

## What Makes a WRD?

A wide-ranging day has two defining characteristics:

| Characteristic | Description |
|---|---|
| **Unusually large range** | The high-to-low distance significantly exceeds the average range of recent bars (typically 1.5x or more) |
| **Close near an extreme** | Downside WRD: close near the low. Upside WRD: close near the high. A close in the middle is ambiguous and less significant |

The close position is what determines the WRD's directional implication — it's not just the range that matters, but where within that range the market settled.

---

## Trading Rules

### Downside WRD Penetrated Upside → BUY

| Element | Rule |
|---|---|
| **Original signal** | Downside WRD (close near low) → expect bearish continuation |
| **Failed signal trigger** | Subsequent close above the WRD's **high** |
| **Direction** | LONG |
| **Significance** | Enhanced if the penetrating bar is itself a WRD |

### Upside WRD Penetrated Downside → SELL

| Element | Rule |
|---|---|
| **Original signal** | Upside WRD (close near high) → expect bullish continuation |
| **Failed signal trigger** | Subsequent close below the WRD's **low** |
| **Direction** | SHORT |
| **Significance** | Enhanced if the penetrating bar is itself a WRD |

---

## Confluence: The Compounding Effect

Schwager's examples reveal a powerful pattern unique to WRDs — **confluence**, where multiple WRD signals stack together:

### DuPont Example (Figure 11.16)
A pronounced downside WRD in late October → brief consolidation → market reversed with an **upside WRD** → another upside WRD closed **above the October WRD's high** → protracted price advance.

The sequence: downside WRD → upside WRD → penetration = three signals aligned.

### Sugar Example (Figure 11.17)
Two downside WRDs formed in close proximity → each penetrated upside → an **upside WRD materialized between** the two penetrations. This confluence of bullish signals preceded a major rally.

### Eurodollar Example (Figure 11.18)
The closing downside penetration of an upside WRD **was itself a wide-ranging day**. Two failed signals stacking on the same bar — this proved to be an early signal of a massive price decline.

> The key lesson: WRDs don't just produce single failed signals. They can form **chains** where each link reinforces the others. The more WRD failures that point in the same direction, the stronger the conviction.

---

## When This Concept Works Best

- **When the penetrating bar is itself a WRD**: This double-signal (the Eurodollar case) is the strongest form — the market is emphatically rejecting the original WRD's direction
- **Multiple WRDs in proximity, all penetrated**: The sugar example with two downside WRDs both failing is a compounding signal
- **After a sharp directional move**: A WRD that occurs at the end of a strong trend, then gets penetrated, suggests the trend has exhausted itself
- **Combined with other failed signal types**: A WRD penetration that coincides with a [[Filled Gaps as Failed Signals|filled gap]] or [[Return to Spike Extremes|spike penetration]] amplifies reliability

---

## When to Be Cautious

- **WRDs with closes in the middle of the range**: If the close isn't clearly near the high or low, the WRD has no clear directional implication — and therefore no clear "failed signal" when penetrated
- **Very frequent WRDs**: In highly volatile markets, WRDs may be routine rather than exceptional — reducing their individual significance
- **Marginal penetrations**: A close barely beyond the WRD's high or low may be noise. Look for a decisive move through the level
- **Isolated WRDs in a strong trend**: A single WRD penetration against a powerful trend is less reliable than one that comes with confluence

---

## Spike vs. WRD — Sister Concepts Compared

| Attribute | Spike (Concept 7) | WRD (Concept 8) |
|---|---|---|
| Pattern type | Single extreme point (tip) | Extreme range (full bar) |
| What protrudes | The spike high/low vs neighbors | The range width vs average |
| Close position | Often near opposite extreme of spike direction | Always near the extreme in the WRD's direction |
| Penetration trigger | Close beyond the spike price | Close beyond the opposite extreme of the WRD |
| Time factor | Weeks/months preferred (significance enhancer) | No specific minimum, but more time = more significance |
| Compounding | Less common | Central feature — WRD chains and confluence |
| Negation rule | Close beyond opposite extreme of spike day | Not explicitly defined by Schwager for WRDs |

Both are "day-level" failed signals originating from Chapter 5 patterns, sharing the same underlying logic: a dramatic single-day claim that gets contradicted by subsequent price action.

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: WRD penetration is a specific application
- **[[Ch5 — Chart Patterns]]**: Defines wide-ranging days and their significance as continuation signals
- **[[Return to Spike Extremes]]**: Sister concept — same logic applied to spikes instead of WRDs
- **[[Filled Gaps as Failed Signals]]**: Another day-level failed signal; can coincide with WRDs for confluence
- **[[Bull Traps]]** / **[[Bear Traps]]**: WRD penetrations share the "dramatic reversal" quality of traps, but operate at the single-bar level rather than the range level

---

## Python Implementation

See `wrd_penetration_detector.py`:
- `detect_wide_ranging_days()` — finds WRDs using configurable range multiplier and close position threshold
- `detect_wrd_penetration()` — monitors for close beyond the WRD's opposite extreme; also checks whether the penetrating bar is itself a WRD (confluence detection)
- `scan_wrd_confluence()` — finds clusters of same-direction WRD penetrations within a proximity window, with automatic confluence scoring

---

## Key Takeaway

WRD penetrations are the most **confluence-prone** failed signal in Chapter 11. While other failed signals tend to produce a single binary event (confirmed or not), WRDs naturally cluster and chain: a downside WRD gets an upside WRD response, the penetration itself is a WRD, multiple WRDs form in proximity and all fail in the same direction. Schwager's three examples all demonstrate this chaining effect. When WRD failures stack up, the signal quality is exceptional — it's the market saying "I tried my hardest in one direction, and it didn't work. Multiple times."
