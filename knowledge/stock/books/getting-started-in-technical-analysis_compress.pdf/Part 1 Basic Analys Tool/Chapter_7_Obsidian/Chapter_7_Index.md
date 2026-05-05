---
chapter: 7
title: "Chapter 7 — Is Chart Analysis Still Valid?"
tags: [technical-analysis, chart-analysis, chapter-7, moc]
source: "Schwager, J. D., Getting Started in Technical Analysis (Wiley, 1999), pp. 120–126"
---

# Chapter 7 — Is Chart Analysis Still Valid? (Map of Content)

> "I always laugh at people who say, 'I've never met a rich technician.' I love that! It is such an arrogant, nonsensical response. I used fundamentals for nine years and got rich as a technician."
> — Marty Schwartz (epigraph to Chapter 7)

## What this chapter is about

Chapters 1–6 taught us **how** to read charts. Chapter 7 stops and answers the harder question: **does chart analysis still work?** Skeptics raise three objections — it's too simple, key levels are easy to game, and the methods are too well publicized. Schwager concedes the points are basically valid, then gives **five reasons** chart analysis remains effective in skilled hands.

The whole chapter pivots on a single running example: the **September 1992 Eurodollar contract**, which generated **two false breakouts** followed by **one big winning breakout** in 1991 (Figures 7.1–7.4). Two losses out of three trades — yet the strategy was **net profitable**. That single fact is the chapter's thesis.

## Concepts in this chapter

| # | Concept | Note |
|---|---------|------|
| 1 | The Skepticism Problem (the chapter's framing) | [[01_Skepticism_Problem]] |
| 2 | Risk Control — win rate < 50% can still be profitable | [[02_Risk_Control]] |
| 3 | Confirmation Conditions | [[03_Confirmation_Conditions]] |
| 4 | Putting Chart Patterns in Context (Multi-Timeframe) | [[04_Patterns_In_Context]] |
| 5 | Knowledge of Fundamentals (Filtered Signals) | [[05_Knowledge_Of_Fundamentals]] |
| 6 | Using Failed Signals | [[06_Failed_Signals]] |
| 7 | Chart Analysis as an Art (vs. Mechanical Science) | [[07_Art_Vs_Science]] |

## Concept relationship map

```
                  ┌──────────────────────────────┐
                  │ THE SKEPTICISM PROBLEM (#1)  │
                  │  "Charts are too well known" │
                  └──────────────┬───────────────┘
                                 │ answered by
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
  ┌──────────┐            ┌──────────────┐         ┌──────────────┐
  │  Risk    │            │ Confirmation │         │ Multi-frame  │
  │ Control  │            │  Conditions  │         │   Context    │
  │   (#2)   │◄──pairs───►│     (#3)     │◄──with──│     (#4)     │
  └────┬─────┘            └──────┬───────┘         └──────┬───────┘
       │                         │                        │
       └──────────┬──────────────┴────────────┬───────────┘
                  ▼                           ▼
        ┌──────────────────┐       ┌──────────────────┐
        │  Fundamentals    │       │   Failed Signals │
        │  Filter (#5)     │       │       (#6)       │
        └────────┬─────────┘       └────────┬─────────┘
                 │                          │
                 └──────────┬───────────────┘
                            ▼
                  ┌──────────────────┐
                  │ Chart = ART (#7) │
                  │  not mechanical  │
                  └──────────────────┘
```

**Reading order:** the concepts build on each other. #2–#6 are the five concrete answers to #1, and #7 is the conclusion that ties them together: skill, judgement, and synthesis are what survives publicity — and those cannot be commoditised.

## Cross-chapter relationships

| Where it points | Why it matters |
|---|---|
| [[Chapter_3_Trends]] | Trend lines/MAs are inputs the chartist must put "in context" (#4) |
| [[Chapter_4_Trading_Ranges]] | The Eurodollar example IS a trading range; breakout mechanics from Ch. 4 |
| [[Chapter_5_Chart_Patterns]] | The patterns whose failures become signals in #6 (flag, H&S, double top) |
| [[Chapter_6_Oscillators]] | Oscillator signals as **alerts** parallels confirmation logic in #3 |
| [[Chapter_9_Stop_Loss]] | Risk control (#2) needs concrete stop placement — Ch. 9 fills in the how |
| [[Chapter_11_Most_Important_Rule]] | "Failed signals" (#6) is the central idea of Ch. 11 — Ch. 7 introduces it |
| [[Chapter_12_Real_World_Charts]] | Chapter 12's 19 trade case studies *are* the synthesis of #2–#6 in practice |
| [[Chapter_14_Trading_Systems]] | Confirmation conditions (#3) reappear as filter rules in system design |

## Key chapter takeaway

> **Publicity erodes mechanical signals, not synthesis.** Anyone can be told where the breakout level is. Almost no-one has the discipline to (a) take the loss when it fails, (b) wait for confirmation, (c) read the long-term chart, (d) check fundamentals, and (e) reverse on a failed signal — *all at once*. The five-factor synthesis is the moat.

## Source code

All Eurodollar simulations and chart generation: [[ch7_master.py]]
Run-time numeric output: 3 trades / 1 winner / **net +$2,913 per contract** (no confirmation), and 5 failed-signal events identified.

---
**Tags:** #technical-analysis #chart-analysis #risk-control #confirmation #multi-timeframe #failed-signals #chapter-7 #moc
