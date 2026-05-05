# 14 — Wavelet Decomposition for Chart Analysis

> Extension to Chapter 12, deeper than [[13_Multi_Timeframe_Decomposition]]. Wavelets formalize what timeframe-stacking does manually: decompose a price series into bands of different scales, each localized in time.

## Why Wavelets, Not Fourier

Fourier asks *"what frequencies are present?"* — and assumes those frequencies exist *everywhere* in the signal. A flag pattern in March is not present in November, so Fourier components can't represent it cleanly. They smear local features across all frequencies.

Wavelets ask *"what patterns of what size are present, and where?"* Each wavelet is a small wiggle that exists only in a finite window. Slide it across the signal, dilate it to different sizes, and you get a 2D map: **scale × time**. Big scales catch slow features (trends); small scales catch fast features (single-day spikes); each detection is anchored to a date.

| Property | Fourier | Wavelet |
|---|---|---|
| Basis function | Sine waves (infinite extent) | Localized wiggles (finite support) |
| Asks | What frequencies? | What patterns of what size, where? |
| Time localization | None (global) | Yes (local) |
| Scale localization | Yes (frequency bins) | Yes (scale axis) |
| Signal class assumption | Stationary | Non-stationary OK |
| Output | 1D spectrum | 2D scale-time map |

## The Three Ingredients

A wavelet transform has three components:

**Mother wavelet ψ(t).** A small wiggle that integrates to zero. Different mothers detect different things:

- **Haar** — step function. Detects abrupt level changes (gaps, breakouts).
- **Daubechies (db4, db8)** — smooth, asymmetric. General-purpose default for noisy financial series.
- **Symlet (sym4)** — like Daubechies but more symmetric.
- **Morlet** — Gaussian-windowed sine. Best for CWT scalograms.
- **Mexican Hat (Ricker)** — second derivative of a Gaussian. Detects peaks/troughs cleanly.

**Scale a.** Dilation factor. Small a = narrow window = high-frequency. Large a = wide window = low-frequency. Schwager's D/W/M timeframes are a coarse three-scale version.

**Translation b.** Where in time to center the wavelet — what makes the transform local.

The continuous wavelet transform:

> W(a, b) = (1/√a) · ∫ x(t) · ψ\*((t − b) / a) dt

In English: at each (scale, time) cell, measure how strongly the signal resembles a wavelet of size a centered at time b.

## CWT vs DWT — Two Flavors

**Continuous Wavelet Transform (CWT).** Computes W(a, b) on a fine grid of scales × times. Output is dense, redundant, oversampled. Best for **visualization**: where is energy concentrated in scale-time space? PyWavelets: `pywt.cwt`.

**Discrete Wavelet Transform (DWT).** Uses dyadic scales (1, 2, 4, 8, 16…) and downsamples at each level. Output is sparse and reconstructs the original exactly. Best for **decomposition + filtering**. PyWavelets: `pywt.wavedec`/`waverec`.

A J-level DWT splits a price series into:

> x(t) = A_J(t) + D_J(t) + D_{J−1}(t) + ... + D_1(t)

where A_J is the smooth "approximation" (trend) and each D_j is the detail at scale 2^j.

## What Wavelets Give You for Chart Analysis

### A. Multi-Resolution Decomposition (MRA)

![[14a_mra_decomposition.png]]

A 5-level db4 decomposition of a synthetic series with two engineered shocks. The reconstruction property holds: trend + D1 + D2 + D3 + D4 + D5 equals the original to machine precision (~10⁻¹³).

What to read in the image:
- **D1 and D2** spike sharply at the two shock dates — wavelets localize transient events to the right band and right time.
- **D4 (~16-day band)** shows the cleanest oscillation, picking up the synthetic 20-bar cycle.
- **D5 (~32-day band)** captures the slower 80-bar undulation.
- **Trend (A_5)** holds 81% of the variance — the genuine low-frequency component, *not* a moving average.

Compare with a moving average: an SMA of length L is one specific low-pass filter with a fixed lag. The wavelet trend is a different filter with no group delay across the relevant band, and it gives you the discarded high-frequency bands as separate, inspectable signals.

### B. CWT Scalograms

![[14b_scalogram.png]]

The continuous wavelet transform of the same series. The bright band at the bottom (large scales, ~80-bar) shows the dominant cycle. Vertical streaks at shock dates extend upward through multiple scales — that's how a wavelet "sees" a transient event.

The white dashed line and shaded region mark the **cone of influence** — the boundary zone where the wavelet partially extends beyond the data and results are unreliable. **Live trading happens at the right edge of the chart, exactly where the wavelet is least trustworthy.** This is the single most important caveat for using wavelets in real time.

### C. Wavelet Denoising

![[14c_denoising.png]]

Soft-thresholding the highest-frequency detail bands and reconstructing produces a smoothed series that:
- Has **no lag** at turning points (compare with the blue 20-bar SMA, which arrives 5–10 bars late).
- **Preserves localized shocks** as features (yellow bands), where the SMA smears them across many bars.

The threshold uses Donoho-Johnstone's universal rule: λ = σ · √(2 ln N), where σ is estimated from the median absolute deviation of D1.

### D. Wavelet as Matched Filter (Multi-Scale Pattern Detection)

![[14d_multiscale_spikes.png]]

The Mexican Hat wavelet at scale a is itself a "peak of width a" template. Convolving it across price flags peaks of matching width. Run it at multiple scales and you get a multi-scale spike detector — **the wavelet equivalent of confluence**.

This image is also instructive in what it *doesn't* show. The two engineered shocks at June 2023 and October 2023 are visible in the price line but mostly missed by the detector. Why? The threshold is computed against the standard deviation of all coefficients — and at large scales, the coefficient series is dominated by the strong cyclical signal, which inflates σ and effectively raises the bar for "spike" classification. **This is calibration failure, not a method failure.** Lowering the threshold would surface those shocks but also produce more false positives. Real-world calibration requires per-instrument, regime-aware tuning.

## Numeric Example — What `multi_resolution_decompose` Returns

```
Energy fractions per band (synthetic 256-bar series):
  trend  81.1%        # A_5 — slowest component, holds the drift
     D1   1.3%        # ~2-day wiggles (mostly noise)
     D2   0.7%        # ~4-day wiggles
     D3   1.6%        # ~8-day wiggles
     D4   5.0%        # ~16-day wiggles (catches 20-bar embedded cycle)
     D5  10.2%        # ~32-day wiggles
  reconstruction max error: 1.14e-13   # machine precision
```

The energy distribution tells you *what scales matter for this series*. If 90% of energy is in the trend, the instrument is dominated by drift; intraday strategies will struggle. If energy is spread across D2–D4, there is meaningful structure at swing-trade horizons.

## Python Usage

```python
from wavelet_decomposer import (
    multi_resolution_decompose,    # x → trend + details
    scalogram,                     # x → 2D (scale × time) map
    wavelet_denoise,               # x → smoothed x with shocks preserved
    multi_scale_spikes,            # x → per-scale ±1 detections
    coincident_spikes,             # combine scales → confluence
)

# Multi-resolution decomposition
mra = multi_resolution_decompose(close, wavelet="db4", levels=5)
print(mra.energy_per_band())      # which scales hold the variance
mra.reconstruct()                  # equals close, to machine precision

# Plug a denoised series back into the Chapter 12 detectors
from chapter12_concepts import detect_flag, wide_ranging_day
clean = wavelet_denoise(close, levels=4, threshold_levels=2)
clean_df = pd.DataFrame({
    "open": opens, "high": highs, "low": lows, "close": clean
})
flag = detect_flag(clean_df.tail(16))   # noise-free flag detection
```

## How Wavelets Plug Into the Chapter 12 Pipeline

The cleanest workflow is to use wavelets as a **pre-processing layer** before the named-pattern detectors:

```
Raw OHLC
    │
    ▼
wavelet_denoise()        ← suppresses 1-2 day noise spikes
    │
    ▼
chapter12_concepts.*     ← detect flags, traps, wide-range bars
    │
    ▼
chart_decomposer         ← cluster by confluence
```

This is materially better than running pattern detectors on raw closes, because:
1. Random noise spikes won't trip the `wide_ranging_day` detector.
2. Flag boundaries are cleaner once 1-2 day wiggles are gone.
3. The `trend` band gives you a regime tag (uptrend / range / downtrend) for free.

## Caveats That Bite People

**Edge effects (cone of influence).** The most recent ~`scale` bars of the scalogram are unreliable — and that's where you need the answer most. Practical responses: use shorter scales for live decisions; pad the right edge with reasonable forecasts (knowing this introduces its own bias); accept that wavelet methods are intrinsically better for *retrospective analysis* than real-time signal generation.

**Wavelet choice imposes a shape prior.** db4 looks for db4-shaped wiggles. If your real patterns don't resemble the wavelet, coefficients won't fire. Mexican Hat is good for peak-finding, Haar for level changes, Daubechies for general financial series — but none is a free lunch.

**Coefficient magnitude is not probability.** A large W(a, b) says "this signal locally resembles a wavelet of size a." It does not say "a chart pattern is present" or "price will rise." Translating coefficients into trade signals requires the same backtesting discipline as any indicator.

**Non-stationarity.** Volatility regimes shift. A scale that captures meaningful structure in calm markets may capture only noise in volatile ones. Wavelets expose this clearly (energy migrates between bands across regimes); they don't solve it.

## Relationships

### Within the chapter and its extensions

- **[[13_Multi_Timeframe_Decomposition]]** — uses three discrete timeframes (D, W, M); wavelets generalize this to a continuous scale axis. The two are complementary: timeframe-stacking is interpretable and matches Schwager's vocabulary; wavelets are mathematically rigorous but harder to map back to "flag" or "bull trap."
- **[[09_Wide_Ranging_Day]]** — D1 of an MRA is essentially "all the wide-range-day energy." Filtering D1 changes how `wide_ranging_day` fires.
- **[[11_Island_Reversal_and_Spike_High]]** — the multi-scale Mexican Hat detector is a wavelet-native version of spike detection that automatically scans many widths at once.
- **[[03_Stop_Placement_Quality]]** — the wavelet trend gives a noise-free reference for placing stops at structural rather than noise-driven levels.

### Outside the chapter

- **Empirical Mode Decomposition (EMD).** Data-driven alternative to wavelets — splits a series into "intrinsic mode functions" without imposing a basis. More flexible, less standardized, harder to reproduce.
- **Hilbert-Huang Transform.** EMD plus instantaneous-frequency analysis. Used in some quant research for regime detection.
- **Lo, Mamaysky & Wang (2000).** The canonical academic paper applying nonparametric kernel smoothing (a relative of wavelet denoising) to chart pattern recognition.
- **Murtagh, Starck & Renaud (2004).** The à trous wavelet transform applied specifically to financial time series. Worth reading if you want the formal version.

## Source

- Concept: synthesis extending Chapter 12, prompted by user question on Fourier-style decomposition
- Library: PyWavelets (`pywt`)
- Code: [`wavelet_decomposer.py`](code/wavelet_decomposer.py), [`visualize_wavelet.py`](code/visualize_wavelet.py)
- Images:
  - [`14a_mra_decomposition.png`](images/14a_mra_decomposition.png)
  - [`14b_scalogram.png`](images/14b_scalogram.png)
  - [`14c_denoising.png`](images/14c_denoising.png)
  - [`14d_multiscale_spikes.png`](images/14d_multiscale_spikes.png)
- Builds on: [[13_Multi_Timeframe_Decomposition]], [[chapter12_concepts.py]]
