# Chapter 14 — Technical Trading Systems: Structure and Design

> *"There are only two types of trend-following systems: fast and slow."* — Jim Orcutt

## What this chapter is about

Schwager moves from chart reading (Parts 1–2) to **mechanical, rule-based systems**. The chapter gives a practical anatomy of a working system and walks through the modifications that turn a textbook formula into something tradable.

The chapter does **not** hand you a "money machine." Its goal is to show the building blocks — and the failure modes — so you can engineer your own.

## Concept map

The chapter splits into three logical layers:

```
Trend-Following Systems  →  Modifications  →  Diversification
        │                        │
   ┌────┴────┐              ┌────┴───────────────────┐
   │         │              │                        │
  MA       Breakout       Confirmation, Filter,    Multiple markets
 systems   systems        Market adjustments,      Multiple systems
                          Buy/sell asymmetry,       Multiple parameter sets
                          Pyramiding, Trade exit
```

Plus a separate, complementary track: **countertrend systems** (work where trend systems fail).

## Concept index

| # | Concept | Note |
|---|---------|------|
| 1 | [[01_Trend_Following_Systems\|Trend-Following Systems (fast vs slow)]] | Architecture and the speed trade-off |
| 2 | [[02_Moving_Average_Systems\|Simple Moving Average System]] | Price vs MA crossover |
| 3 | [[03_Weighted_Moving_Averages\|Weighted Moving Averages]] | LWMA and EWMA variants |
| 4 | [[04_Crossover_Moving_Average_System\|Crossover MA System]] | Two MAs against each other |
| 5 | [[05_Breakout_Systems\|Breakout Systems]] | N-day high/low |
| 6 | [[06_Confirmation_Conditions\|Confirmation Conditions]] | Penetration / Time delay / Pattern |
| 7 | [[07_Filter\|Filter Rules]] | Reject low-probability trades up front |
| 8 | [[08_Market_Characteristic_Adjustments\|Market Characteristic Adjustments]] | Adapt parameters to volatility |
| 9 | [[09_Buy_Sell_Differentiation\|Buy/Sell Asymmetry]] | Different rules for longs vs shorts |
| 10 | [[10_Pyramiding\|Pyramiding]] | Add to winning positions |
| 11 | [[11_Trade_Exit\|Trade Exit + Re-entry]] | Liquidate before opposite signal |
| 12 | [[12_Countertrend_Systems\|Countertrend Systems]] | Fade moves / Oscillators / Sentiment |
| 13 | [[13_Diversification\|Diversification (markets, systems, SMSVs)]] | Three levels of diversification |

## How everything connects

A typical Schwager-style trend-following system, fully assembled:

```
        ┌──────────────────┐
        │ Base trend system│   ← Trend-Following (1)
        │  (MA or Breakout)│     Moving Avg (2,3,4) or Breakout (5)
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │   Filter (7)     │   ← reject before signal
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ Confirmation (6) │   ← validate after signal
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │ Market adj. (8)  │   ← adapt N to volatility
        │ Buy/sell diff (9)│
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │  Pyramiding (10) │   ← bet bigger on real trends
        │  Trade exit (11) │   ← cap losses, re-enter
        └────────┬─────────┘
                 │
        ┌────────▼─────────┐
        │Diversification(13)│  ← smooth across markets/systems
        └──────────────────┘
```

Countertrend systems (12) sit in parallel — best deployed alongside, not instead of, trend-following.

## Cross-chapter links

- **Ch. 6 — Oscillators** → input to countertrend systems (Concept 12)
- **Ch. 8 — Midtrend Entry & Pyramiding** → directly extended in Concept 10
- **Ch. 9 — Stop-Loss Points** → trade-exit/stop logic (Concept 11)
- **Ch. 15 — Testing & Optimization** → all parameters here become test variables
- **Ch. 16 — Planned Trading Approach** → reuses diversification (Concept 13)

## Schwager's 10 standard problems with simple trend-following systems

The chapter ends with a problem→solution table — a useful checklist:

1. Too many losing trades → **filter** + **confirmation**
2. Big open-profit give-back → **trade exit** rule
3. Constant unit size misses big trends → **pyramiding**
4. Buy/sell symmetry not realistic → **buy/sell differentiation**
5. Same N for all markets → **market characteristic adjustment**
6. System whipsaws in ranges → countertrend overlay or filter
7. No risk control → stop rules
8. Single-system fragility → trade **multiple systems**
9. Parameter-shift risk → **multiple parameter sets** (SMSVs)
10. Slippage/cost overstate paper P&L → realistic backtest assumptions (Ch. 15)
