# Chapter 12 — Real-World Chart Analysis

> *"Knowing what can go wrong in a trade is often more important than knowing what can go right."*  
> — Jack D. Schwager

## Overview

Chapter 12 is unlike the rest of the book. Instead of teaching new patterns, Schwager walks through **19 actual trades** he recommended at Prudential Securities (Figures 12.1–12.19) — both winners and losers. The chapter teaches the *application* and *discipline* layer: when to enter, when to bail, when to reverse, and what mistakes look like in real time.

The chapter is best read **interactively**: cover the right-hand "exit" page, study the entry chart, decide your strategy, then turn the page to compare.

## Concepts Captured

The 19 trades repeatedly invoke 12 underlying concepts. Each note below contains a definition, an illustration, an analogy, a numeric example, runnable Python, and links to related concepts.

| # | Concept | Source figure(s) |
|---|---|---|
| 1 | [[01_Primary_Premise_Violation]] — exit when the trade idea is invalidated | 12.1, 12.5, 12.6, 12.15 |
| 2 | [[02_Market_vs_Limit_Orders]] — the cost of waiting for a better price | 12.2 |
| 3 | [[03_Stop_Placement_Quality]] — stops too tight cause premature exits | 12.3, 12.11, 12.16 |
| 4 | [[04_Measured_Move_Objective]] — projecting prior swings onto pullbacks | 12.4, 12.7, 12.8, 12.14 |
| 5 | [[05_Bull_Trap]] — failed upside breakouts as top signals | 12.2, 12.8 |
| 6 | [[06_Bear_Trap]] — failed downside breakouts as bottom signals | 12.5, 12.10, 12.13 |
| 7 | [[07_Flag_and_Pennant_Continuation]] — brief pause inside a trend | 12.5, 12.10, 12.11, 12.14, 12.18, 12.19 |
| 8 | [[08_Counter_to_Anticipated_Breakout]] — failure becomes the new signal | 12.6, 12.7, 12.9, 12.15, 12.18 |
| 9 | [[09_Wide_Ranging_Day]] — outsized bar as reversal warning | 12.7, 12.13, 12.17 |
| 10 | [[10_Trailing_Stop]] — let the trend run, lock in gains | 12.13, 12.16 |
| 11 | [[11_Island_Reversal_and_Spike_High]] — multi-pattern top signals | 12.17, 12.18 |
| 12 | [[12_Expected_Gain_per_Trade]] — why win-rate alone is misleading | 12.9 |
| **13** | [[13_Multi_Timeframe_Decomposition]] — *extension*: decompose a chart into a list of overlapping patterns across timeframes | (synthesis) |
| **14** | [[14_Wavelet_Decomposition]] — *extension*: continuous-scale decomposition (DWT/CWT, denoising, matched-filter detection) | (synthesis) |
| **15** | [[15_Empirical_Mode_Decomposition]] — *extension*: adaptive, basis-free decomposition into IMFs + residual | (synthesis) |
| **16** | [[16_STL_Decomposition]] — *extension*: trend + seasonal + remainder via LOESS, useful for calendar-effect removal | (synthesis) |

## Decomposition Methods Compared

The four decomposition approaches in extensions 13–16, side by side:

| Method | Basis | Multi-scale | Adapts to data | Best chart use |
|---|---|---|---|---|
| Multi-timeframe | Fixed (D/W/M) | Discrete | No | Match Schwager's vocabulary |
| Wavelets (DWT/CWT) | Fixed (db4, morl, …) | Continuous (dyadic) | Time-localized | Denoising, scalogram features |
| EMD / EEMD | None | Adaptive | Fully | Cycle extraction, regime detection |
| STL | LOESS + fixed period | Single-period | Slowly | Calendar-effect removal, baseline |

## Master Themes

Three lessons run through every trade:

1. **Premise discipline.** Every position should rest on a clearly stated technical premise. The moment that premise is violated, the trade is over — regardless of P&L.
2. **Flexibility beats prediction.** Skill in *responding* to changing price action matters more than skill in market calls. The crude-oil sequence (12.12 → 12.13) shows a trader going short at the bottom, recognizing the failure, reversing, and capturing a large gain.
3. **Asymmetry is the edge.** A pattern need not win 50% of the time. What matters is `E = p·avg_win − (1−p)·avg_loss`. Flags near range extremes, bull/bear traps, and counter-to-anticipated breakouts all produce small, fast losses and large, slow wins.

## Source

- **Book:** *Getting Started in Technical Analysis* — Jack D. Schwager (Wiley, 1998)
- **Chapter 12** — Real-World Chart Analysis (pp. 178–218)
- **Code:** [`chapter12_concepts.py`](code/chapter12_concepts.py)
- **Charts:** [`generate_charts.py`](code/generate_charts.py)
