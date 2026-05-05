# 16 — STL Decomposition (Seasonal-Trend using LOESS)

> Extension to Chapter 12. STL is the simplest of the decomposition methods we've covered — and the most honestly limited for chart analysis. It's worth knowing precisely *because* of its limitations.

## The Core Idea

STL decomposes a time series into three additive components:

> y(t) = trend(t) + seasonal(t) + remainder(t)

where:
- **Trend** is a smoothed long-term component (LOESS regression).
- **Seasonal** is a periodic component at a *fixed, user-specified* period.
- **Remainder** is whatever's left.

The algorithm alternates between:
- estimating the seasonal pattern (averaging values at the same phase across periods, then smoothing), and
- estimating the trend (LOESS smoothing of the deseasonalized series).

A few iterations of this back-and-forth converge to a stable decomposition.

## Why It's "Crude for Charting"

STL was designed for series with **genuine, fixed-period seasonality** — monthly retail sales, daily electricity demand, hourly traffic patterns. It assumes:

1. **The period is known and fixed.** You tell STL "the cycle is 12 months" or "the cycle is 21 bars." Stock prices generally don't have a fixed seasonal cycle in the same sense.
2. **The seasonality is roughly periodic across the whole series.** STL handles slow drift in the seasonal pattern (its `robust` mode), but not regime changes.

For most stock charts, neither assumption holds cleanly. There *are* weak calendar effects (turn-of-month, January effect, day-of-week patterns) but they're small relative to the dominant non-seasonal variation.

## Why It's Still Worth Knowing

Three legitimate uses on price series:

### 1. Calendar-Effect Removal

If you suspect day-of-week or end-of-month patterns are leaking into your indicators, STL with `period=5` (weekly) or `period=21` (monthly) will pull them out as the "seasonal" component. What's left is cleaner for technical analysis.

### 2. Genuine Annual Cycles

Some commodities really do have annual cycles — natural gas (winter heating), agricultural futures (planting/harvest), certain retail-exposed equities. STL with `period=252` on daily data extracts that cleanly when it exists.

### 3. A Boring Baseline

When evaluating fancier methods like wavelets or EMD, STL is the boring control that often performs surprisingly well. **If your wavelet-based pattern detector doesn't beat STL trend + remainder, the wavelet wasn't doing useful work.** This is a humble but extremely useful function in any quant research workflow.

## Illustration

![[15c_stl_decomposition.png]]

Same synthetic series as in [[15_Empirical_Mode_Decomposition]] decomposed two ways:

**Left (period=21)** — STL extracts the embedded 21-bar cycle as the seasonal component. Trend strength = 0.93 (high — the series is trend-dominated). Seasonal strength = 0.54 (moderate). The remainder shows the two engineered shocks as clean isolated spikes around mid-2023 and late-2023 — STL preserves transient events rather than smearing them.

**Right (period=5)** — STL extracts the much weaker 5-bar cycle. Seasonal strength drops to 0.27 (the synthetic 5-bar cycle was small relative to the others). Trend strength rises to 0.96 because more variance is now lumped into the trend.

The lesson: **the "seasonal" component is whatever you tell STL to look for**. Pick the wrong period and the seasonal component becomes meaningless decoration.

## Numeric Example — Output of `stl_decompose`

```
STL with period=21 (monthly):
  Strength of trend:       0.928       # variance explained by trend
  Strength of seasonality: 0.544       # variance explained by seasonal
  Reconstruction max error: 1.42e-14   # exact

STL with period=5 (weekly):
  Strength of seasonality: 0.271
  Strength of trend:       0.959
```

These two scalars — Hyndman's "strength of trend" and "strength of seasonality" — each take values in [0, 1]:

> strength_of_trend = max(0, 1 − Var(remainder) / Var(remainder + trend))

A trend strength near 1 means the trend explains most of the structured variation; near 0 means the trend is no better than noise. Same idea for seasonality.

## Python Usage

```python
from emd_stl_decomposer import stl_decompose, stl_detrend

# Monthly seasonality
d = stl_decompose(close, period=21, seasonal=7, robust=True)
print(f"Trend strength:        {d.strength_of_trend():.3f}")
print(f"Seasonal strength:     {d.strength_of_seasonality():.3f}")

# Weekly seasonality (day-of-week effects)
d_weekly = stl_decompose(close, period=5, seasonal=7)

# Detrending — useful as a pre-processing step for cycle analysis
detrended = stl_detrend(close, period=21)

# Pass STL-cleaned series back through Chapter 12 detectors
from chapter12_concepts import detect_flag, wide_ranging_day
clean_close = d.trend + d.remainder        # remove seasonal pattern
# ... build OHLC dataframe and run detectors ...
```

## STL vs Wavelet vs EMD — Trend Extraction

![[15d_trend_comparison.png]]

This is the single most useful image to internalize. Same series, four different "trends":

- **Red (EMD residual)** is the smoothest — almost a smooth curve. EMD claims the underlying drift is monotonic-ish.
- **Blue (wavelet trend, db4 A_5)** captures more low-frequency oscillation — it includes the ~80-bar cycle as part of "trend" because that cycle lives in the lowest-frequency band that wasn't classified as a detail.
- **Green (STL trend, P=21)** sits between EMD and wavelet — captures cycles slower than 21 bars but treats faster ones as seasonal.
- **Gray dashed (50-bar SMA)** lags noticeably at every turning point.

**There is no single right answer.** Each method has a different cutoff between "what counts as drift" and "what counts as a cycle." The right choice depends on what you want to do with the trend.

If you want a stop-placement reference that responds slowly to short-term noise, the EMD residual or STL trend is appropriate.

If you want an indicator that turns at intermediate-cycle pivots, the wavelet trend (or `wavelet_denoise`) is more responsive.

If you're doing classical breakout analysis, the SMA may be fine — its lag is a feature, not a bug, because confirmation requires waiting.

## Caveats

**Period must be specified.** Unlike EMD, STL cannot find the period for you. If you don't already know what cycle you want to extract, STL is the wrong tool.

**Multiplicative seasonality not supported.** STL is purely additive. For series where the seasonal amplitude scales with the trend level (very common in financial data), you have to log-transform first, decompose, then exponentiate.

**Outliers can dominate without `robust=True`.** A single shock can deform the seasonal estimate for many periods. Always use `robust=True` on financial data.

**No multi-scale decomposition.** STL extracts *one* seasonal period. If your series has both weekly and quarterly structure, you need to run STL twice (or use MSTL — multi-seasonal STL — also in `statsmodels`).

## When STL Is the Right Tool

- You suspect a specific calendar effect (day-of-week, monthly, annual) is contaminating an indicator. STL extracts and removes it cleanly.
- You're working with a commodity that has a known seasonal cycle.
- You need a quick, deterministic, reproducible decomposition for a baseline comparison.
- You want to communicate "trend + cycle + noise" to a non-technical audience — the three components map onto intuitive language.

## When STL Is the Wrong Tool

- You don't know what period to look for. (Use EMD instead.)
- The cyclic structure isn't fixed across the whole series. (Use wavelets, which are time-localized; or EMD, which is adaptive.)
- You need multi-scale analysis. (Use wavelets or EMD.)
- The signal has strong transient events you want to study separately. (STL's remainder catches them, but it's not designed for transient analysis.)

## Relationships

### Within the chapter and its extensions

- **[[14_Wavelet_Decomposition]]** — wavelets give multi-scale decomposition; STL gives one-scale-at-a-time. STL is to wavelets what a single bandpass filter is to a filter bank.
- **[[15_Empirical_Mode_Decomposition]]** — EMD finds periods adaptively; STL requires the period as input. They are essentially opposite philosophies on the same problem.
- **[[13_Multi_Timeframe_Decomposition]]** — using STL with `period=5/21/63/252` is a kind of "multi-period stacking" but each pass loses information about the others.
- **[[03_Stop_Placement_Quality]]** — the STL trend can serve as a noise-free reference for placing structural stops, similar to the EMD residual.

### Outside the chapter

- **Cleveland et al. (1990)** — the original STL paper. Surprisingly readable, with clear motivation.
- **MSTL (Multi-seasonal STL)** — extension that handles multiple seasonal periods simultaneously. Available as `statsmodels.tsa.seasonal.MSTL`.
- **X-13ARIMA-SEATS** — the U.S. Census Bureau's industrial-strength seasonal adjustment package. Overkill for financial data but the gold standard for economic time series.
- **Prophet (Facebook)** — Bayesian time series model with explicit trend + seasonal + holiday components. Conceptual descendant of STL, popular for business forecasting; rarely used in trading because it doesn't handle the noise/regime structure of asset prices well.

## Source

- Concept: synthesis extending Chapter 12, prompted by user question
- Library: `statsmodels.tsa.seasonal.STL`
- Code: [`emd_stl_decomposer.py`](code/emd_stl_decomposer.py), [`visualize_emd_stl.py`](code/visualize_emd_stl.py)
- Images:
  - [`15c_stl_decomposition.png`](images/15c_stl_decomposition.png)
  - [`15d_trend_comparison.png`](images/15d_trend_comparison.png)
- Builds on: [[14_Wavelet_Decomposition]], [[15_Empirical_Mode_Decomposition]]
