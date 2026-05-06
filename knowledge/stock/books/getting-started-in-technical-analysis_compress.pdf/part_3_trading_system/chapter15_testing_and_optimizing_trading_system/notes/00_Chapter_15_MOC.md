# Chapter 15 — Testing and Optimizing Trading Systems

> **Source:** Schwager, J. — *Getting Started in Technical Analysis*, Ch. 15 (pp. 253–273)
> **Theme:** *How* to evaluate a trading system honestly, and the many ways the process gets corrupted.

## TL;DR

> *"Every decade has its characteristic folly… people persist in believing that what has happened in the recent past will go on happening into the indefinite future."* — George J. Church (epigraph)

Backtest results are wildly easier to fake (often unintentionally) than to make rigorous. Chapter 15 is essentially an anti-self-deception manual: the methods, vocabulary, and red flags every system tester needs.

## Concept Map

```
                       Trading System (rules)
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
            Parameter                Choosing data
                │                  ┌────────┴────────┐
                ▼                  ▼                 ▼
         Parameter Set       Price series       Time period
                │                                    │
                ▼                                    ▼
       Realistic Assumptions ◀── Slippage      Time Stability
                │
                ▼
        Optimization ──┐
                │      ├─▶ Parameter Stability
                │      │
                ▼      ▼
        Testing vs Fitting (the trap)
                │
        ┌───────┴───────┐
        ▼               ▼
 Blind Simulation   Average Parameter
 (walk-forward)     Set Performance
                │
                ▼
       Schwager's Corollary
       ("bad simulations drive out good")
                │
                ▼
       Multimarket Testing  ──▶  System Construction Steps
```

## Concepts

| # | Concept | Note |
|---|---|---|
| 1 | The Well-Chosen Example | [[01_Well_Chosen_Example]] |
| 2 | Parameter & Parameter Set | [[02_Parameter_and_Parameter_Set]] |
| 3 | Time Stability | [[03_Time_Stability]] |
| 4 | Slippage & Realistic Assumptions | [[04_Slippage_and_Realistic_Assumptions]] |
| 5 | Optimization (incl. Parameter Stability) | [[05_Optimization]] |
| 6 | Testing vs Fitting | [[06_Testing_vs_Fitting]] |
| 7 | Blind Simulation (Walk-Forward) | [[07_Blind_Simulation]] |
| 8 | Average Parameter Set Performance | [[08_Average_Parameter_Set_Performance]] |
| 9 | Schwager's Corollary | [[09_Schwagers_Corollary]] |
| 10 | Multimarket System Testing | [[10_Multimarket_Testing]] |

## Chapter-level takeaways (Schwager's own list, paraphrased)

1. The way you *identify* trends matters less than the modifications around the system (filters, exits, sizing).
2. Complexity for its own sake is a vice. Use the simplest version that doesn't lose performance.
3. Diversify markets — both for risk control and to avoid missing the rare giant move.
4. Diversify systems too if capital allows (trend + countertrend + pattern).
5. Trade several diversified parameter sets, not just one optimum.
6. Optimization is overrated.
7. Optimized in-sample results are useless for evaluation — use blind simulation or average-set performance.
8. "Simulated" in advertising usually means "optimized." Treat it as marketing fiction.
9. Successful systems share one trait: lots of big winning years, very few big losing ones — i.e. *let profits run, cut losses short*.

## Related chapters

- [[Chapter_13_Software]] — what testing tools to use
- [[Chapter_14_Trend_Following_Systems]] — the systems that get tested here
- [[Chapter_16_Planned_Trading_Approach]] — once a system passes ch. 15, deploy it via ch. 16

## Files

- Illustrations: `images/01_..png` through `images/10_..png`
- Source code: `code/concept_01_..py` through `code/concept_10_..py`
- Master generator: `code/00_generate_illustrations.py`
