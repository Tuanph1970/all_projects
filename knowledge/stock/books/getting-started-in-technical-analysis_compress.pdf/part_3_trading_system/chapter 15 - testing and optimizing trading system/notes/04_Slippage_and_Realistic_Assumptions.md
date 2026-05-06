# Concept 4 — Slippage & Realistic Assumptions

**Tags:** #ch15 #execution #pitfall

## Definition

**Slippage** = the gap between the price at which a backtest *says* you traded and the price you'd *actually* fill at in real markets. It's the catch-all term for the friction that turns a paper-profitable system into a real-money loser.

Schwager identifies two sources of unrealistic backtest assumptions:

1. **Transaction costs.** Commissions are only part of it. The bigger hidden cost is the difference between theoretical execution and real fill prices on stop, market, open, and close orders. Rule of thumb: assume far more than just commissions (e.g., $100/trade in his era).
2. **Limit days.** A computerized backtest assumes you fill on every signal. In reality, when a market locks at the daily limit, no execution is possible. Paper profit can become a real loss after a multi-day limit-locked move.

## Illustration

![[04_slippage.png]]

Signal generated near 107; fill not possible until day 9 at 122 because the market gapped through the limit. The paper trade is profitable; the real trade isn't.

## Analogy

You see a flash sale online: $50 sneakers, retail $200. By the time you check out, your size has sold out and the only ones left are $180. Your "savings" only existed in the listing price — your *fill price* is what your wallet actually pays.

## Numeric example

From `code/concept_04_slippage.py`, same signals across friction scenarios:

```
Scenario                            Net P&L ($)   # trades
Paper (no friction)                  +1,847.21        148
+ commission $5/trade                +1,107.21        148
+ 0.05% slippage                       +396.50        148
+ realistic ($25 + 0.10%)            -1,820.99        148
+ pessimistic ($50 + 0.25%)          -5,891.10        148
```

Same exact strategy, friction alone flips it from **+$1,847 to −$5,891**. Active systems get punished disproportionately because trade count multiplies friction.

## Source code

[[code/concept_04_slippage.py]]

## Relationships

### Within the chapter
- One of the headline reasons for problems #8 and #10 in Ch. 14's "ten common problems" (systems that bomb live, slippage).
- **Closely linked to [[09_Schwagers_Corollary]]** — distortion method #6 is "unrealistic transaction costs."

### When does this matter most?
For **active systems** (many trades per year). A slow trend-follower trading a few times a year barely notices slippage; a fast intraday system can be entirely consumed by it. Before evaluating any system, calculate: *trades-per-year × estimated cost-per-trade*. If that number rivals expected gross profit, you don't have a system, you have a vendor for your broker.

### Outside the chapter
- [[Chapter_9_Stop_Loss_Points]] — stops that cluster at obvious levels suffer worst slippage.
- [[Chapter_13_Charting_Software]] — most testing software lets you set a slippage assumption; many traders leave it at zero.
- [[Chapter_16_Planned_Trading_Approach]] — execution discipline is itself a step in the planned approach.
