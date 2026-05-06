# Chapter 16 — The Planned Trading Approach

> _"If making money is a slow process, losing it is quickly done."_ — Ihara Saikaku

![[01_planned_trading_overview.svg]]

## Chapter Summary

Chapter 16 lays out a seven-step blueprint for building a disciplined trading practice. The premise is simple: traders who treat speculation as entertainment can play it by ear, but anyone whose goal is to make money needs a written, systematic plan. The chapter is the practical capstone of the book — it takes everything learned about charts, systems, and risk and packages it into a daily workflow.

## The Seven Steps (Concept Map)

| # | Concept | Note |
|---|---------|------|
| 1 | Trading Philosophy | [[01 Trading Philosophy]] |
| 2 | Market Selection | [[02 Market Selection]] |
| 3 | Risk Control Plan (umbrella) | [[03 Risk Control Plan]] |
| 3a | Maximum Risk Per Trade | [[04 Maximum Risk Per Trade]] |
| 3b | Stop-Loss Strategy | [[05 Stop-Loss Strategy]] |
| 3c | Diversification | [[06 Diversification]] |
| 3d | Reduced Leverage for Correlated Markets | [[07 Reduced Leverage Correlated Markets]] |
| 3e | Market Volatility Adjustments | [[08 Market Volatility Adjustments]] |
| 3f | Adjusting Leverage to Equity Changes | [[09 Adjusting Leverage to Equity]] |
| 3g | Losing Period Adjustments | [[10 Losing Period Adjustments]] |
| 4 | Planning Time Routine | [[11 Planning Time Routine]] |
| 5 | Trader's Notebook | [[12 Traders Notebook]] |
| 6 | Trader's Diary | [[13 Traders Diary]] |
| 7 | Personal Trading Analysis | [[14 Personal Trading Analysis]] |
| 7a | Segmented Trade Analysis | [[15 Segmented Trade Analysis]] |
| 7b | Equity Chart | [[16 Equity Chart]] |

## How the Concepts Connect

```
PHILOSOPHY (1) → defines what kind of edge you're chasing
       ↓
MARKETS (2)    → applies that edge only where it fits
       ↓
RISK PLAN (3)  → caps the damage when the edge fails
       ↓
ROUTINE (4)    → operationalises the plan every day
       ↓
NOTEBOOK (5)   → records what actually happened
       ↓
DIARY (6)      → records WHY it happened
       ↓
ANALYSIS (7)   → feeds insight back into Steps 1-3
```

The whole structure is a feedback loop: Step 7's findings refine Steps 1, 2, and 3, then the cycle repeats.

## Related Chapters

- **Chapter 9 — Choosing Stop-Loss Points** → mechanics behind [[05 Stop-Loss Strategy]]
- **Chapter 10 — Setting Objectives and Other Position Exit Criteria** → exit rules used in [[12 Traders Notebook]]
- **Chapter 14 — Technical Trading Systems: Structure and Design** → diversification benefits expanded
- **Chapter 15 — Testing and Optimizing Trading Systems** → "well-chosen example" trap that motivates honest record keeping
- **Chapter 17 — Eighty-Two Trading Rules** → tactical companion to this strategic blueprint
- **Chapter 18 — Market Wiz(ar)dom** → psychological foundation (discipline, responsibility, independence)

## Source Code Library

All code lives in the `/code/` folder:

- [[01_position_sizing.py]] — fixed-fractional position sizing, total-risk caps
- [[02_volatility_sizing.py]] — ATR-based sizing, equity-adjusted leverage
- [[03_traders_notebook.py]] — persistent CSV-backed trading journal
- [[04_trade_analysis.py]] — segmentation, expectancy, equity curve & drawdown
