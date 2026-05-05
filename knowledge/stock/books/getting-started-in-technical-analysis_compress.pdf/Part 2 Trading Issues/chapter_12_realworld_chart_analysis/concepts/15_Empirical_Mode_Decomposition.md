# 15 — Empirical Mode Decomposition (EMD)

> Extension to Chapter 12. EMD asks the most ambitious question of any decomposition method: *"what if we let the data tell us what its components are, instead of imposing a basis?"*

## The Core Idea

[[14_Wavelet_Decomposition|Wavelets]] impose a basis: pick `db4` and the algorithm projects your signal onto db4-shaped wiggles. EMD has no fixed basis. It decomposes a signal into **Intrinsic Mode Functions (IMFs)** — components that emerge from the data itself.

Each IMF satisfies two properties:

1. **The number of extrema and the number of zero crossings differ by at most one.** Clean oscillation, not a trend.
2. **At any point, the mean of the upper and lower envelopes is zero.** Locally symmetric around zero.

That's the definition. Different signals produce different IMFs at different scales. A calm market produces few IMFs at long periods; a volatile one produces more IMFs at varied periods.

## The Sifting Algorithm

EMD extracts one IMF at a time using "sifting":

```
Input: signal s(t)

Loop until s(t) has fewer than 2 extrema (it's monotonic):
    h(t) = s(t)
    Repeat until h(t) is an IMF:
        1. Find local maxima and local minima of h(t)
        2. Cubic-spline upper envelope through maxima
        3. Cubic-spline lower envelope through minima
        4. m(t) = (upper + lower) / 2
        5. h(t) = h(t) - m(t)
    Accept h(t) as the next IMF
    s(t) = s(t) - h(t)        # extract the IMF, recurse on residual

Output: signal = IMF_1 + IMF_2 + ... + IMF_N + residual
```

IMF_1 is the highest-frequency component. The residual is the underlying trend — whatever's left after all the oscillations have been peeled off.

## Illustration

![[15a_emd_decomposition.png]]

A 252-bar synthetic series with embedded 5-bar, 21-bar, and 80-bar cycles plus two engineered shocks. EMD recovered exactly the structure I built in:

- **IMF1** at ~3 bars — daily noise; visibly bulges around the shock dates (mid-2023, late-2023)
- **IMF2** at ~8 bars
- **IMF3** at ~20 bars — matches the embedded 21-bar cycle
- **IMF4** at ~72 bars — matches the embedded 80-bar cycle
- **Residual** — clean smooth trend, holds 45.5% of variance

Reconstruction is exact to ~10⁻¹⁴. No basis was specified. The decomposition is what *the data* contains.

## Numeric Example — Output of `emd_decompose`

```
Number of IMFs extracted: 4
Reconstruction max error: 2.84e-14

Energy fractions:
       IMF1   3.78%      noise band
       IMF2   3.09%      ~8-bar cycles
       IMF3   6.31%      ~21-bar cycles  ← detected the embedded monthly cycle
       IMF4  41.35%      ~80-bar cycles  ← detected the embedded major cycle
   residual  45.48%      slow drift / trend

Estimated dominant periods:
       IMF1   3.3 bars
       IMF2   8.3 bars
       IMF3  20.2 bars
       IMF4  72.0 bars
```

The energy distribution and period estimates together give you a regime fingerprint. If a stock has 70% energy in the residual, it is drift-dominated. If 60% sits in IMF2-IMF3, it has strong swing-trade-horizon structure.

## EEMD — Mitigating Mode Mixing

A real problem with vanilla EMD is **mode mixing**: a single IMF can contain components of very different scales when the signal switches regimes or has intermittent transients. The shock at index 120 in the demo, for instance, leaks across IMF1, IMF2, and IMF3 instead of being cleanly assigned to one.

The standard fix is **Ensemble EMD (EEMD)**:

1. Add Gaussian noise of small amplitude to the signal.
2. Run EMD on the noisy signal.
3. Repeat 100 times with different noise realizations.
4. Average the IMFs across all trials.

The noise pushes the algorithm to consistent scales across trials, and averaging cancels the noise. Cost: ~100× slower than plain EMD, plus two new tunable parameters (noise std, number of trials).

![[15b_emd_vs_eemd.png]]

EMD (left) vs EEMD (right) on the same series. EEMD's IMF1 looks more uniformly noisy; the cycle structure in IMF3 and IMF4 is similar. On clean synthetic data the difference is modest; on real stock data with regime shifts, EEMD's separation is meaningfully cleaner.

## Python Usage

```python
from emd_stl_decomposer import emd_decompose, emd_denoise

# Basic EMD
result = emd_decompose(close)
print(result.energy_per_imf())
print(result.dominant_period_per_imf())

# EEMD for cleaner separation (slower)
result_e = emd_decompose(close, method="EEMD",
                         eemd_trials=100, noise_std=0.2)

# Use EMD for denoising — drop the highest-frequency IMF(s)
clean = emd_denoise(close, drop_first_n=1)
```

## Caveats — EMD Is More Controversial Than Wavelets

**Mode mixing.** Already discussed. EEMD helps but adds parameters of its own, plus a slowdown.

**No theoretical foundation.** Wavelets have a complete mathematical theory — convergence, uniqueness, frame bounds, fast inversion. EMD has a procedure. It works empirically; you can't prove much about it. Some critics call it "a fancy interpolation scheme" rather than a transform.

**Edge effects are worse than wavelets.** Cubic-spline envelope fitting at the boundaries is unstable. The first and last few bars of every IMF are unreliable, and there's no clean cone-of-influence formula. For live trading, this is a real obstacle.

**Stopping criterion is ad hoc.** "When is h(t) close enough to an IMF to stop sifting?" There are several common rules (Cauchy-type, S-number, energy difference); they give different decompositions. The library hides this; the choice still matters.

**Output count is non-deterministic.** Two similar signals can produce different numbers of IMFs. This makes EMD awkward as a feature extractor for ML pipelines — you can't even fix the output dimensionality.

## When EMD Beats Wavelets

In one-line summary: **when the data has well-separated, locally narrowband oscillations whose frequencies aren't on dyadic scales.**

Concrete examples:

- A stock with a real ~17-bar cycle. Wavelets force this into D4 (~16 bars) or D5 (~32 bars), splitting the energy. EMD captures it as a single IMF.
- A market with regime shifts (calm → volatile). EMD adapts; wavelets project the regime change onto fixed bands.
- Detrending where the trend isn't well-modeled by low-frequency wavelet bands. EMD's residual is genuinely the *slowest* component, not "everything below 32 bars."

## When Wavelets Beat EMD

- Live decision-making (edge effects matter).
- ML feature engineering (need fixed-dimensional output).
- Reproducibility and testing (need deterministic output).
- Multi-instrument analysis (need same components across series for comparison).

## Relationships

### Within the chapter and its extensions

- **[[14_Wavelet_Decomposition]]** — direct alternative. Wavelets impose a basis; EMD doesn't. The trade-off is rigor vs adaptivity.
- **[[13_Multi_Timeframe_Decomposition]]** — both EMD and wavelets are continuous-scale generalizations of timeframe stacking.
- **[[09_Wide_Ranging_Day]]** — IMF1 of an EMD typically holds the wide-ranging-day energy; filtering it changes how the detector fires.
- **[[03_Stop_Placement_Quality]]** — the EMD residual is a candidate "noise-free reference" for placing structural stops.

### Outside the chapter

- **Hilbert-Huang Transform.** EMD plus the Hilbert transform of each IMF, yielding instantaneous amplitude and frequency at every (scale, time) point. Conceptually similar to a CWT scalogram but data-adaptive. Used in some quant research for regime detection.
- **Variational Mode Decomposition (VMD).** A more recent alternative to EMD with a stronger mathematical foundation — solves a constrained optimization problem to extract modes simultaneously rather than iteratively. Avoids mode mixing by construction.
- **Singular Spectrum Analysis (SSA).** Yet another adaptive decomposition — embed the series as a trajectory matrix, SVD it, group the components. Different machinery, similar goal.
- **Huang et al. (1998)** is the foundational EMD paper if you want the formal version.

## Source

- Concept: synthesis extending Chapter 12, prompted by user question
- Library: `EMD-signal` (PyEMD module)
- Code: [`emd_stl_decomposer.py`](code/emd_stl_decomposer.py), [`visualize_emd_stl.py`](code/visualize_emd_stl.py)
- Images:
  - [`15a_emd_decomposition.png`](images/15a_emd_decomposition.png)
  - [`15b_emd_vs_eemd.png`](images/15b_emd_vs_eemd.png)
  - [`15d_trend_comparison.png`](images/15d_trend_comparison.png) — cross-method trend comparison
- Builds on: [[14_Wavelet_Decomposition]], [[13_Multi_Timeframe_Decomposition]], [[chapter12_concepts.py]]
