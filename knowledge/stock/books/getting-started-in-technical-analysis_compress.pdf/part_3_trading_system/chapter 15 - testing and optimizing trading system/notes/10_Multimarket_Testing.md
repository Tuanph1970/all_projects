# Concept 10 — Multimarket System Testing

**Tags:** #ch15 #robustness #methodology

## Definition

A trustworthy system should perform across a **broad portfolio of markets** — not just the one you tuned it on. Schwager's rule of thumb:

- For futures: a good system should be profitable in **~85% or more** of actively traded markets.
- For stocks (long-only): a good system should beat buy-and-hold's return/risk on a **majority** of tested stocks.

Exceptions exist (e.g., a system that uses fundamental data is by definition single-market; stock indexes behave atypically), but the core principle stands: **edge that doesn't generalize is probably edge that doesn't exist.**

A second wrinkle: when running a multimarket test, you can't naively trade "one contract per market" — markets have different volatilities and correlations. Pre-determine your **percentage capital allocation** per market before starting the test. Otherwise the result is dominated by whichever market happens to have the biggest dollar swings.

## Illustration

![[10_multimarket.png]]

The same system run across 10 synthetic markets. Each dot is one market: x = max drawdown, y = annual return, color = return/risk ratio. A system worth trading should have most dots in the upper-left quadrant (high return, low drawdown).

## Analogy

You taste-test a new coffee blend at one café and love it. Before claiming it's the best blend ever, try it at five more cafés with five different baristas, brewed five different ways. If it tastes great everywhere, it's a great blend. If it only works on the first café's specific machine — you didn't find a great blend, you found a great machine.

## Numeric example

From `code/concept_10_multimarket.py`, the same MA-crossover system on 10 synthetic markets:

```
Market     Total P&L ($/share)
Coffee                  +28.42
Sugar                   +12.91
Crude                   +47.02
Gold                     -3.18
Corn                    +18.66
Wheat                    +9.13
Cocoa                   -10.07
Soy                     +21.55
Cotton                   +5.99
Lumber                   +0.82

% profitable markets : 80%   (target: ~85%+)
```

80% means just below Schwager's bar — borderline. If only 30–40% were profitable, the system is curve-fit to its origin market and shouldn't be deployed.

## Source code

[[code/concept_10_multimarket.py]]

## Relationships

### Within the chapter
- The portfolio-level corollary to [[07_Blind_Simulation]]: blind simulation is robustness across **time**, multimarket testing is robustness across **markets**. Both are forms of cross-validation.
- A test of [[06_Testing_vs_Fitting]] in disguise: a curve-fit system rarely generalizes across markets.
- The motivation behind chapter takeaway #3: trade many markets both for risk control *and* to avoid missing the rare giant move.

### Comparison: stocks vs. futures multimarket testing
| Dimension | Stocks | Futures |
|---|---|---|
| Number of names | hundreds-thousands | dozens |
| Long/short typical? | long-only common | both |
| Correlation structure | sectors cluster heavily | low cross-asset corr if diversified |
| Bench mark | beat buy-and-hold | absolute return (no buy-and-hold for futures) |
| Position-sizing concern | shares per stock | volatility-equalize across contracts |

### When can you skip it?
- **Single-market by design** — e.g., a system with fundamental input that only applies to one market (Schwager calls this out explicitly).
- **Atypical market** — e.g., stock-index systems that wouldn't work on grains.

But for any general technical system, you should not skip this step.

### Outside the chapter
- [[Chapter_14_Trend_Following_Systems]] — diversification (problems #1, #2c, #6, #7) is intrinsic to the multimarket discipline.
- [[Chapter_16_Planned_Trading_Approach]] — Step 2 of the planned approach is selecting markets to trade; the multimarket test result tells you which.
- Modern portfolio theory — multimarket testing is essentially measuring whether your "alpha" survives diversification.
