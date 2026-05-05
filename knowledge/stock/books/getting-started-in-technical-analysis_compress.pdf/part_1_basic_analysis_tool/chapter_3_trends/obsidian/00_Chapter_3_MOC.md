---
chapter: 3
title: "Chapter 3 - Trends (MOC)"
tags: [technical-analysis, trends, chapter-3, moc]
source: "Schwager, Getting Started in Technical Analysis (Wiley, 1999)"
---

# Chapter 3 — Trends (Map of Content)

> "The trend is your friend except at the end when it bends."
> — Ed Seykota (epigraph to Chapter 3)

The basic goal of chart analysis is to **define and identify price trends**, because trends offer the best profit opportunities. Chapter 3 introduces three different families of tools that all answer the same underlying question: *what direction is this market going, and is it still going there?*

## Concept map

```
                            How do we identify the trend?
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
   Discrete pivots             Geometric lines                    Smoothing
        │                              │                              │
   ┌────┴────┐                ┌────────┼────────┐                     │
[01_Uptrend] [02_Downtrend]  [03_Uptr_Line]  [04_Downtr_Line]    [09_Moving_Average]
                              [05_Trend_Channel]
                              [06_Trend_Line_Rules]
                              [07_TD_Line]
                              [08_Internal_Trend_Line]
```

## Notes

| # | Concept | Key idea |
|--:|---------|----------|
| 1 | [[01_Uptrend]] | Higher highs + higher lows |
| 2 | [[02_Downtrend]] | Lower lows + lower highs |
| 3 | [[03_Uptrend_Line]] | Straight line through higher lows |
| 4 | [[04_Downtrend_Line]] | Straight line through lower highs |
| 5 | [[05_Trend_Channel]] | Trend line + parallel return line |
| 6 | [[06_Trend_Line_Rules]] | Pullback entry, penetration reversal, channel exit |
| 7 | [[07_TD_Line]] | DeMark's objective two-pivot rule |
| 8 | [[08_Internal_Trend_Line]] | Best-fit through majority, ignores extreme spikes |
| 9 | [[09_Moving_Average]] | Smoothed average; trends well, whipsaws when choppy |

## Cross-cutting themes

**Three views of the same animal.** The chapter shows three different lenses on "the trend":
- *Pivot-based*: discrete swing highs and lows ([[01_Uptrend]], [[02_Downtrend]]).
- *Line-based*: geometric boundaries ([[03_Uptrend_Line]], [[04_Downtrend_Line]], [[05_Trend_Channel]], [[07_TD_Line]], [[08_Internal_Trend_Line]]).
- *Smoothing-based*: averaging away noise ([[09_Moving_Average]]).

**Subjective vs. objective.** Conventional trend lines are subjective. The chapter offers two answers:
- [[07_TD_Line]] — make the rule deterministic by always using the most recent qualifying pivots.
- [[09_Moving_Average]] — sidestep pivot selection entirely with a rolling mean.

**Extreme vs. typical pivots.** Two opposite philosophies of which points should anchor the trend:
- [[07_TD_Line]] anchors on extreme pivots (most recent qualifying low/high).
- [[08_Internal_Trend_Line]] deliberately *excludes* extreme pivots as emotional excesses.

**Trade-off: smoothness vs. lag.** Every method that filters noise pays for it with delayed signals. The N parameter shows up everywhere — in pivot detection, in TD lines, in moving averages — and always governs the same trade-off.

**Trends in hindsight vs. real time.** A repeated caution in the chapter: trend lines look much better in hindsight than in real time. Penetrations are common; most are redraws, not reversals. This sets up the "false signals" theme that runs through the rest of the book (Ch. 11).

## Source code

All Python implementations live in `code/`:
- [[01_trend_pivots.py]] — pivot detection + trend classification
- [[02_trend_lines.py]] — uptrend/downtrend lines + channel + rules
- [[03_td_lines.py]] — DeMark TD lines
- [[04_internal_trend_line.py]] — regression-based internal line with outlier trimming
- [[05_moving_average.py]] — SMA + reversal signals + backtest helper
- `generate_charts.py` — produces every illustration in this folder

## Charts

All illustrations live in `images/`:
1. `01_uptrend_highs_lows.png`
2. `02_downtrend_highs_lows.png`
3. `03_uptrend_line.png`
4. `04_downtrend_line.png`
5. `05_trend_channel.png`
6. `06_trend_line_rules.png`
7. `07_td_line.png`
8. `08_internal_trend_line.png`
9. `09_moving_average_trending.png`
10. `10_moving_average_sideways.png`

## Forward links to other chapters

| Concept from Ch. 3 | Connects to |
|---|---|
| Reaction lows/highs | Ch. 4: Trading Ranges and Support and Resistance |
| Trend-line breaks | Ch. 5: Chart Patterns |
| MA lag | Ch. 6: Oscillators (designed to lead, not lag) |
| False trend-line signals | Ch. 7: Is Chart Analysis Still Valid?, Ch. 11 |
| Pullback entry rule | Ch. 8: Midtrend Entry and Pyramiding |
| Latest RL/RH | Ch. 9: Choosing Stop-Loss Points |
| Channel exit rule | Ch. 10: Setting Objectives and Other Position Exit Criteria |
| Variations of MA | Ch. 14 and Appendix |

## Source

Schwager, Jack D. *Getting Started in Technical Analysis*. New York: John Wiley & Sons, 1999. Chapter 3 ("Trends"), pp. 33-50.
