# Concept 6 — Testing vs Fitting

**Tags:** #ch15 #pitfall #methodology

## Definition

The single most consequential distinction in the chapter:

- **Testing** = evaluating a system on data the parameter selection process never saw.
- **Fitting** (or *curve-fitting*) = adjusting parameters so the system's past performance is maximized, then claiming that performance is meaningful.

Schwager's central warning: *"the question of which parameter sets will perform best during any given period is largely a matter of chance."* If you test enough parameter sets on enough data, even a meaningless system will produce some sets with stellar past records. Choosing those is **fitting** — and it tells you nothing about the future.

## Illustration

![[06_testing_vs_fitting.png]]

Left: in-sample period — the curve-fit system looks like a money machine. Right: out-of-sample — same parameters, performance collapses. The "honest" system looks unimpressive in both, but at least its in-sample and out-of-sample results agree.

## Analogy

Imagine you "predicted" the World Cup winner by listing every possible bracket outcome ahead of time, then *after* the tournament, holding up the one bracket that happened to be correct. Did you predict the winner? Technically yes. Do you have any forecasting skill? Of course not. Curve-fitting is exactly this trick on price data.

## Numeric example

From `code/concept_06_testing_vs_fitting.py` — the input data is **pure random noise**:

```
Best in-sample lookback : 37
In-sample P&L           : +0.1759
Out-of-sample P&L       : +0.1557

Average across all 50 lookbacks (a more honest estimator):
  In-sample mean        : -0.1546
  Out-of-sample mean    : +0.0871
```

The "best" lookback shows a positive number on data that has *no signal whatsoever*. If we'd looked at the average across all lookbacks (the honest answer), we'd see ~zero, which is the truth. Run the script with a different seed and the "best" lookback will be a totally different number.

## Source code

[[code/concept_06_testing_vs_fitting.py]]

## Relationships

### Within the chapter
- The trap that everything else in this chapter is designed to avoid.
- Cured by [[07_Blind_Simulation]] (separate selection from evaluation in time) and [[08_Average_Parameter_Set_Performance]] (average instead of pick a winner).
- Almost identical mechanism as [[01_Well_Chosen_Example]] — both use after-the-fact selection to manufacture a result.

### When does this trap close on you?
Any time you (a) tested >1 parameter set, (b) chose the best, and (c) reported its performance as the system's expected return. The more parameter sets you tested, the worse the bias.

A useful sanity check: how many "things you could have varied" went into the final model? Lookback length, smoothing constant, threshold, exit rule, position-sizing, market filter… each one is another opportunity to fit noise.

### Outside the chapter
- [[Chapter_14_Trend_Following_Systems]] — problem #8 ("Systems that work well in testing but bomb") is fitting in disguise.
- [[Appendix_Concepts_Formulas]] — many indicator formulas have parameters; the same trap applies.
- General ML/statistics — this is *exactly* the train/test-split discipline from supervised learning, just applied to time series. Schwager was preaching it for trading systems before it was a buzzword.
