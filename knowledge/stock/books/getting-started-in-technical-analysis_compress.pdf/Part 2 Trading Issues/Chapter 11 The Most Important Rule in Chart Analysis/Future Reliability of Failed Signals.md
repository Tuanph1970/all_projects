---
title: "Future Reliability of Failed Signals"
chapter: 11
concept: 13
tags:
  - failed-signals
  - inverse-popularity
  - meta-principle
  - market-efficiency
  - schwager
  - chapter-11
aliases:
  - Inverse Popularity Effect
  - Failed Signal Reliability
  - Popularity vs Efficiency
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Bull Traps]]"
  - "[[Bear Traps]]"
  - "[[False Trend Line Breakouts]]"
  - "[[Ch7 — Is Chart Analysis Still Valid?]]"
---

# Future Reliability of Failed Signals

## Definition

Schwager's meta-observation closing Chapter 11: there is an **inverse relationship** between the popularity of an indicator and its efficiency. Failed signals are currently reliable precisely because they are underused. If their usage became widespread, their reliability would degrade — but the *concept* can be made timeless by pegging it to whatever the conventional wisdom happens to be.

> *"There is an inverse relationship between the popularity of an indicator and its efficiency."*
> — Schwager, Ch. 11

---

## Simple Analogy: The Secret Fishing Spot

You know a secret fishing spot where you always catch fish (the failed signal strategy). It works because few other people fish there — the fish aren't scared.

But imagine you publish the coordinates online. Thousands of people show up. The fish get spooked by all the boats. Your secret spot stops working — not because the fish left, but because the crowd changed the dynamics.

However, you notice something: wherever the *crowd* is fishing (the popular spot), fish actually gather just *outside* that area, where the crowd's noise pushes them. So you start fishing wherever the crowd *isn't*. Your strategy adapts: you don't need a fixed location. You just need to go where the crowd isn't. That's Schwager's "timeless" version of failed signals — peg to wherever the conventional wisdom is, and trade its failure.

---

## The Breakout Example

Schwager provides a concrete historical illustration:

| Era | Breakout Usage | Breakout Efficiency |
|---|---|---|
| **Pre-1980s** | Few practitioners | Worked well — many excellent signals, few false signals |
| **Post-1980s** | Widely popular | Deteriorated — "price reversals following breakouts are more often the rule than the exception" |

The mechanism: as more traders placed stops above/below trading ranges and more algorithms bought breakouts, the market adapted. Breakouts became *stop-hunting events* rather than genuine trend signals — which is precisely why bull and bear traps became so prevalent and reliable.

---

## Three Key Claims

### 1. Failed signals are currently more reliable than conventional patterns

> *"I find failed signals considerably more reliable than conventional chart patterns."*

Schwager stakes his professional reputation on this — it's the strongest claim in the book.

### 2. Low adoption is the source of their edge

The concept is "certainly not new" (Schwager's own 1984 book covered it), but he is "not aware of its usage being strongly emphasized elsewhere." This obscurity is the edge. The fewer traders watching for traps, the better traps work as signals.

### 3. Widespread adoption would erode the edge

> *"If the use of failed signals were to become significantly more widespread, their long-term reliability could be adversely affected."*

This is an honest, self-aware admission: by writing about failed signals, Schwager risks degrading the very edge he's describing. It's the observer effect applied to trading.

---

## The Timeless Escape: Dynamic Pegging

Schwager's most profound insight — how the concept survives its own popularity:

> *"The concept of failed signals can be made dynamic by pegging it to the conventional wisdom. In other words, if a new chart pattern became popular as a technical signal in the future, a failure of the pattern could be viewed as more significant than the pattern itself. In this more general sense, the concept of failed signals could prove timeless."*

The logic:

1. **Today**: Breakouts are popular → failed breakouts (traps) are informative
2. **Tomorrow**: If "Pattern X" becomes popular → failed Pattern X signals become informative
3. **Always**: The failure of whatever is popular carries more information than the popular signal itself

This makes the failed signal concept a **meta-principle** — it operates one level above any specific pattern. Specific patterns rise and fall in popularity; the principle that their failure is informative persists.

---

## The Chapter's Bookend: Three Trader Levels

Schwager closes the chapter with the same hierarchy from Concept 1, framing the entire chapter as a journey in one's **relationship to failure**:

| Level | Relationship to Failure | Action |
|---|---|---|
| **Novice** | Ignores failure | Rides into large loss while hoping |
| **Experienced** | Accepts failure | Exits quickly, limits damage |
| **Skilled** | Exploits failure | Does a 180° turn, reverses position |

> *"It takes great discipline to capitalize on failed signals, but such flexibility is essential to the effective synthesis of chart analysis and trading."*
> — Schwager, Ch. 11, Conclusion

---

## When This Concept Matters Most

- **When adopting any popular strategy**: Before using a widely-taught technique, consider whether its popularity has already degraded its edge. The more popular it is, the more valuable its *failure* may be
- **When evaluating new indicators or systems**: Ask not "does this signal work?" but "how many other people are using this signal?" The crowd factor matters as much as the pattern itself
- **When the market environment changes**: If a signal type that used to work stops working, that's not just bad luck — it may be the inverse popularity effect. Adapt by watching for its failure instead
- **When reading trading books (including this one)**: Every technique published becomes slightly less effective. The edge is in the *second-order* thinking — what happens when the technique fails

---

## Connection to Chapter 7

This concept directly extends Chapter 7's discussion of whether chart analysis is still valid despite widespread publicity. Schwager's answer in Ch 7 included five factors, the fifth being: *"Using Failed Signals — the failure of a market to follow through in the direction of a key chart signal is a crucial item of information often overlooked by novice chartists."*

Chapter 11 is the full elaboration of that fifth factor, and Concept 13 addresses the same validity question at the meta-level: will failed signals themselves become invalid if widely known?

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: This concept is the meta-commentary on Concept 1's thesis
- **[[Ch7 — Is Chart Analysis Still Valid?]]**: The same popularity-vs-efficiency question applied to chart analysis broadly; failed signals are Schwager's answer
- **[[Bull Traps]]** / **[[Bear Traps]]**: The most direct example of inverse popularity — breakouts degraded → traps became reliable
- **[[False Trend Line Breakouts]]**: Another example — Schwager says false trend breakouts are "considerably more reliable than conventional trend breakout signals"

---

## Python Implementation

See `inverse_popularity_analyzer.py`:
- `measure_breakout_efficiency()` — measures traditional breakout win rate, profit factor, and average P&L over a period
- `measure_failed_breakout_efficiency()` — measures the same metrics for failed breakout signals (breakout → retreat → trade opposite)
- `compare_signal_efficiency()` — splits data into early/late halves and checks for the inverse popularity pattern: breakout efficiency declining while failed breakout efficiency holds steady
- Returns `inverse_popularity_observed` flag when the pattern matches Schwager's thesis

---

## Key Takeaway

Concept 13 elevates the entire chapter from a catalog of specific patterns into a **philosophy of trading**. The specific failed signals (bull traps, filled gaps, spike penetrations, etc.) are the tools. The inverse popularity principle is the wisdom that tells you *when and why* those tools work — and warns you when they might stop working. Schwager's genius is in the escape clause: by making the concept dynamic (peg to conventional wisdom), he creates something that can outlive any specific market era. The failure of whatever is popular is always informative. That's as close to a timeless trading principle as you'll find.

---

## Chapter 11 — Complete

All 13 concepts covered:

1. [[Failed Signals — The Overarching Principle]]
2. [[Bull Traps]]
3. [[Bear Traps]]
4. [[Confirmation Conditions for Bull-Bear Traps]]
5. [[False Trend Line Breakouts]]
6. [[Filled Gaps as Failed Signals]]
7. [[Return to Spike Extremes]]
8. [[Return to Wide-Ranging Day Extremes]]
9. [[Counter-to-Anticipated Flag Pennant Breakout]]
10. [[Opposite Direction Breakout After Normal Breakout]]
11. [[Penetration of Top and Bottom Formations]]
12. [[Breaking of Curvature]]
13. [[Future Reliability of Failed Signals]] ← you are here
