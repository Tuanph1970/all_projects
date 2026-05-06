---
chapter: 17
title: "Eighty-Two Trading Rules and Market Observations"
type: index
tags: [chapter-17, MOC, index, trading-rules]
---

# Chapter 17 — Eighty-Two Trading Rules and Market Observations

> *"Live long enough and you will eventually be wrong about everything."* — Russell Baker (chapter epigraph)

## Chapter Overview

Chapter 17 distills decades of personal trading experience into 82 specific, opinionated rules organized by the book into seven thematic sections. The chapter's central tension: most of these rules are widely known clichés that traders nonetheless **systematically violate** until they have lost real money rediscovering them. Schwager presents the rules with the explicit acknowledgment that *the only way they sink in is through the painful experience of breaking them* — but writing them down provides a reference that can shorten the cycle of repetition.

This MOC organizes the 82 rules into **seven concept notes** (one per thematic section), each treated as a distinct concept with its own definition, illustration, analogy, numeric example, code, and cross-references.

## The Seven Concepts (Sections of the Chapter)

| # | Concept | Section | Rules | Note |
|---:|---|---|---|---|
| 1 | Entering Trades | Entering Trades | 1–12 | [[01_Entering_Trades]] |
| 2 | Exiting Trades & Risk Control | Exiting Trades and Risk Control | 13–23 | [[02_Exiting_Risk_Control]] |
| 3 | Money Management | Other Risk-Control Rules | 24–30 | [[03_Money_Management]] |
| 4 | Holding & Exiting Winners | Holding and Exiting Winning Trades | 31–38 | [[04_Holding_Winners]] |
| 5 | Trading Psychology | Miscellaneous Principles and Rules | 39–47 | [[05_Trading_Psychology]] |
| 6 | Market Patterns | Market Patterns | 48–77 | [[06_Market_Patterns]] |
| 7 | Analysis & Review | Analysis and Review | 78–82 | [[07_Analysis_Review]] |

## Conceptual Architecture

The seven concepts form a **trading life-cycle** with feedback:

```
   ┌─────────────────────────────────────────────────────┐
   │                                                     │
   ▼                                                     │
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐
│ Patterns│ →  │  Entry   │ →  │  Hold   │ →  │   Exit   │ →  │  Review  │
│  (#6)   │    │   (#1)   │    │  (#4)   │    │  (#2)    │    │   (#7)   │
└─────────┘    └──────────┘    └─────────┘    └──────────┘    └──────────┘
                    ▲               ▲               ▲              │
                    │               │               │              │
                    └───────────────┴───────────────┘              │
                                    │                              │
                            ┌──────────────┐                       │
                            │  Money Mgmt  │ ←─────────────────────┘
                            │     (#3)     │
                            └──────────────┘
                                    ▲
                            ┌──────────────┐
                            │  Psychology  │
                            │     (#5)     │   (overlay on all)
                            └──────────────┘
```

**Money Management (#3)** sits in the middle because it sets the size of every entry, the dollar definition of every exit, and the ammunition for every future trade.

**Psychology (#5)** is an overlay that applies to all the others — it's *how* the trader executes the other concepts.

**Review (#7)** closes the loop: data flows from completed trades back into pattern recognition and rule refinement.

## Pattern Index — Cross-Concept Themes

These themes recur across multiple concepts:

### The Failed-Signal Master Principle
> A failed signal is more reliable than the original signal.

- Manifests as bull/bear traps in [[06_Market_Patterns]]
- Triggers reverse positions in [[02_Exiting_Risk_Control]]
- Validated by patterns chart book in [[07_Analysis_Review]]

### Cut Losers, Keep Winners
- Position-level: liquidate losing positions first ([[03_Money_Management]])
- Trade-level: never average down on a loser ([[02_Exiting_Risk_Control]])
- Within a trade: trailing stops on winners ([[04_Holding_Winners]])

### Plan, Don't React
- Entries planned in advance ([[01_Entering_Trades]])
- Stops defined at entry ([[02_Exiting_Risk_Control]])
- End-of-day decisions, not intraday ([[05_Trading_Psychology]])
- Reviews on a schedule, not on whim ([[07_Analysis_Review]])

### Discipline as a State, Not a Trait
- Bad habits are never cured, only kept latent ([[05_Trading_Psychology]])
- Risk rules don't relax after a winning streak ([[03_Money_Management]])
- Reviews especially matter when busy ([[07_Analysis_Review]])

## Connections to Other Chapters

| External Chapter | Used By |
|---|---|
| Ch 3: Trends | #1 (entry context), #6 (pattern interpretation) |
| Ch 4: Trading Ranges & Support/Resistance | #1 (stop placement), #6 (range structure) |
| Ch 5: Chart Patterns | #1 (confirming patterns), #6 (pattern catalog) |
| Ch 8: Midtrend Entry & Pyramiding | #1 (entry timing), #4 (adding to winners) |
| Ch 9: Choosing Stop-Loss Points | #2 (the canonical methodology) |
| Ch 10: Setting Objectives | #4 (counterpart for winning-trade exits) |
| Ch 11: The Most Important Rule | #6 (failed-signal principle) |
| Ch 12: Real-World Chart Analysis | All — case studies of all decisions |
| Ch 14: Trend-Following Systems | #2, #4 — mechanical exit rules |
| Ch 16: Planned Trading Approach | All — the framework these rules live in |
| Ch 18: Market Wiz(ar)dom | #5, #7 — broader principles from successful traders |

## How to Use This Chapter

1. **First read:** Skim all seven concepts. Don't try to memorize.
2. **After your first 20 trades:** Re-read with your own diary in hand. Mark which rules you've already broken.
3. **After your first significant loss:** Re-read concepts #2 and #3. The pain makes the lessons land.
4. **Quarterly:** Re-read one concept per quarter. Update your own rules document.
5. **After every winning streak:** Re-read concept #5. That's when bad habits return.

## Files in This Set

```
chapter17/
├── notes/
│   ├── 00_INDEX.md                  ← this file
│   ├── 01_Entering_Trades.md
│   ├── 02_Exiting_Risk_Control.md
│   ├── 03_Money_Management.md
│   ├── 04_Holding_Winners.md
│   ├── 05_Trading_Psychology.md
│   ├── 06_Market_Patterns.md
│   └── 07_Analysis_Review.md
├── images/
│   ├── 01_entering_trades.svg
│   ├── 02_exiting_risk_control.svg
│   ├── 03_money_management.svg
│   ├── 04_holding_winners.svg
│   ├── 05_trading_psychology.svg
│   ├── 06_market_patterns.svg
│   └── 07_analysis_review.svg
└── code/
    ├── 01_entering_trades.py
    ├── 02_exiting_risk_control.py
    ├── 03_money_management.py
    ├── 04_holding_winners.py
    ├── 05_trading_psychology.py
    ├── 06_market_patterns.py
    └── 07_analysis_review.py
```

## Source

- Schwager, Jack D. *Getting Started in Technical Analysis*. Wiley, 1999.
- Chapter 17: Eighty-Two Trading Rules and Market Observations (pp. 288–298)
- Adjacent: Chapter 16 (Planned Trading Approach), Chapter 18 (Market Wiz(ar)dom)
