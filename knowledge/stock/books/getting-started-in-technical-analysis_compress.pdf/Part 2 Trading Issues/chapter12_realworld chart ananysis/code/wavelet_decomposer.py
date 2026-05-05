"""
wavelet_decomposer.py
=====================
Wavelet-based decomposition of OHLC price series.

Three workflows:

    1. multi_resolution_decompose(close)
       Discrete Wavelet Transform → trend + detail bands.
       Each band is a 1-D series the same length as the input.
       Sum of all bands == original series (reconstruction property).

    2. scalogram(close)
       Continuous Wavelet Transform → 2-D (scale × time) energy map.
       Shows where pattern-energy is concentrated at what scale.

    3. wavelet_denoise(close, level=2)
       Soft-threshold the highest-frequency detail bands and reconstruct.
       A principled alternative to moving-average smoothing.

These three feed back into the Chapter 12 decomposer:
    - Run pattern detectors on `wavelet_denoise(close)` to suppress noise spikes.
    - Use CWT modulus maxima as native multi-scale "spike" / "edge" detectors.

The math:
    Continuous: W(a, b) = (1/sqrt(a)) ∫ x(t) ψ*((t-b)/a) dt
    Discrete:   x(t) = A_J(t) + Σ_{j=1..J} D_j(t)
        where  A_J = approximation at coarsest scale J
               D_j = detail band at scale 2^j

Beware:
    - Edge effects ("cone of influence"). The rightmost coefficients
      are the least reliable — and they're the ones you'd most want
      for live trading decisions.
    - Wavelet choice imposes a shape prior. db4/sym4 are reasonable
      defaults for noisy financial series; Mexican Hat for peak-finding.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import pywt


# ==================================================================
# 1. DISCRETE WAVELET TRANSFORM (multi-resolution decomposition)
# ==================================================================
@dataclass
class MRADecomposition:
    """Result of a multi-resolution analysis."""
    trend: pd.Series                  # final approximation (smoothest band)
    details: list[pd.Series]          # D_1 (highest freq) → D_J (lowest)
    wavelet: str
    levels: int

    def reconstruct(self) -> pd.Series:
        """Sum of trend + all details should equal the original series."""
        s = self.trend.copy()
        for d in self.details:
            s = s + d
        return s

    def energy_per_band(self) -> dict[str, float]:
        """L2 energy in each detail band — fraction of total variance per scale."""
        total_var = self.trend.var() + sum(d.var() for d in self.details)
        out = {"trend": float(self.trend.var() / total_var)}
        for j, d in enumerate(self.details, start=1):
            out[f"D{j}"] = float(d.var() / total_var)
        return out


def multi_resolution_decompose(
    close: pd.Series,
    wavelet: str = "db4",
    levels: int = 4,
) -> MRADecomposition:
    """
    Decompose a price series into trend + detail bands using the
    Stationary (à trous) Wavelet Transform — same length per band,
    no downsampling, additive reconstruction.

    Parameters
    ----------
    close : pd.Series
        Price series indexed by date.
    wavelet : str
        Mother wavelet name ('db4', 'db8', 'sym4', 'haar', ...).
    levels : int
        Number of decomposition levels. Each level captures wiggles
        roughly twice as slow as the previous level. With daily data:
            D_1 ≈ 2-day wiggles, D_2 ≈ 4-day, D_3 ≈ 8-day, D_4 ≈ 16-day, ...
    """
    x = close.values.astype(float)
    n = len(x)

    # wavedec requires length compatibility — pad with edge value and trim back.
    pad = (-n) % (2 ** levels)
    if pad:
        x = np.concatenate([x, np.full(pad, x[-1])])

    # Standard multilevel DWT: returns [cA_J, cD_J, cD_{J-1}, ..., cD_1]
    coeffs = pywt.wavedec(x, wavelet, level=levels)

    # To get each band as a same-length time series, we reconstruct from
    # only that level's coefficients (zeroing out all the others) — the
    # "multi-resolution analysis" trick.  Sum of all bands == original.
    def isolate(idx: int) -> np.ndarray:
        zeroed = [np.zeros_like(c) for c in coeffs]
        zeroed[idx] = coeffs[idx]
        rec = pywt.waverec(zeroed, wavelet)
        return rec[:n]

    trend_arr = isolate(0)
    detail_arrays = [isolate(i) for i in range(len(coeffs) - 1, 0, -1)]
    # Reversed so detail_arrays[0] = D_1 (finest), [-1] = D_J (coarsest)

    trend = pd.Series(trend_arr, index=close.index, name="trend")
    detail_series = [
        pd.Series(d, index=close.index, name=f"D{j}")
        for j, d in enumerate(detail_arrays, start=1)
    ]

    return MRADecomposition(trend=trend, details=detail_series,
                            wavelet=wavelet, levels=levels)


# ==================================================================
# 2. CONTINUOUS WAVELET TRANSFORM (scalogram)
# ==================================================================
@dataclass
class Scalogram:
    """Result of a CWT — 2D energy map plus the axes."""
    coefficients: np.ndarray          # shape (n_scales, n_times)
    scales: np.ndarray
    times: pd.DatetimeIndex
    wavelet: str

    def power(self) -> np.ndarray:
        """|W(a,b)|^2 — what most papers actually plot."""
        return np.abs(self.coefficients) ** 2

    def cone_of_influence(self) -> np.ndarray:
        """
        Approximate boundary of the trustworthy region.
        For a Morlet wavelet, COI extends sqrt(2)*scale from each edge.
        Returns an array of length n_times giving the max trustworthy scale.
        """
        n = len(self.times)
        t = np.arange(n)
        edge_dist = np.minimum(t, n - 1 - t)
        return edge_dist / np.sqrt(2)


def scalogram(
    close: pd.Series,
    wavelet: str = "morl",
    n_scales: int = 64,
    min_scale: float = 2.0,
    max_scale: Optional[float] = None,
) -> Scalogram:
    """
    Compute a CWT scalogram. Default uses the complex Morlet wavelet
    (good time-frequency localization).

    Returns
    -------
    Scalogram with `coefficients` shape (n_scales, n_times).
    """
    x = close.values.astype(float)
    if max_scale is None:
        max_scale = len(x) / 4
    scales = np.geomspace(min_scale, max_scale, n_scales)

    coeffs, _ = pywt.cwt(x, scales, wavelet)
    return Scalogram(coefficients=coeffs, scales=scales,
                     times=close.index, wavelet=wavelet)


# ==================================================================
# 3. WAVELET DENOISING
# ==================================================================
def wavelet_denoise(
    close: pd.Series,
    wavelet: str = "db4",
    levels: int = 4,
    threshold_levels: int = 2,
    mode: str = "soft",
) -> pd.Series:
    """
    Denoise a price series by soft-thresholding the highest-frequency
    detail bands, then reconstructing.

    `threshold_levels` controls how many of the finest bands get zeroed
    out — 1 removes day-to-day noise, 2 also removes 2-4 day wiggles,
    etc. A more principled alternative to a moving average: the trend
    that remains is the genuine low-frequency component.

    Threshold is set by the universal rule (Donoho-Johnstone):
        λ = σ * sqrt(2 * ln(N))
    where σ is estimated from the median absolute deviation of D_1.
    """
    x = close.values.astype(float)
    n = len(x)
    pad = (-n) % (2 ** levels)
    if pad:
        x = np.concatenate([x, np.full(pad, x[-1])])

    coeffs = pywt.wavedec(x, wavelet, level=levels)
    # coeffs = [A_J, D_J, D_{J-1}, ..., D_1]

    # Estimate noise σ from the finest detail band
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    universal_threshold = sigma * np.sqrt(2 * np.log(len(x)))

    # Threshold the `threshold_levels` finest bands
    new_coeffs = list(coeffs)
    for k in range(1, threshold_levels + 1):
        new_coeffs[-k] = pywt.threshold(coeffs[-k], universal_threshold, mode=mode)

    reconstructed = pywt.waverec(new_coeffs, wavelet)[:n]
    return pd.Series(reconstructed, index=close.index, name="denoised")


# ==================================================================
# 4. WAVELET-BASED PATTERN DETECTION
#    Treat the wavelet itself as a matched filter.
# ==================================================================
def detect_spikes_via_wavelet(
    close: pd.Series,
    scale: float = 4.0,
    threshold_sigmas: float = 3.0,
    wavelet: str = "mexh",
    mask_edges: bool = True,
) -> pd.Series:
    """
    Detect peaks and troughs at a given scale using the Mexican Hat
    wavelet (a.k.a. Ricker, second derivative of a Gaussian).

    Mexican Hat coefficients are large and positive over peaks of
    matching width, large and negative over troughs.

    With mask_edges=True (default), detections inside the cone of
    influence are suppressed — the wavelet is unreliable at distances
    less than `scale` from either end of the series.

    Returns a Series with values:
        +1  → peak detected at this scale
        -1  → trough detected at this scale
         0  → no detection (or masked edge)
    """
    x = close.values.astype(float)
    coeffs, _ = pywt.cwt(x, [scale], wavelet)
    w = coeffs[0]
    threshold = threshold_sigmas * np.std(w)

    out = np.zeros(len(x), dtype=int)
    out[w >  threshold] = +1
    out[w < -threshold] = -1

    if mask_edges:
        # The cone of influence for the Mexican Hat extends ~scale bars from each end.
        edge = int(np.ceil(scale))
        out[:edge] = 0
        out[-edge:] = 0

    return pd.Series(out, index=close.index, name=f"spikes_scale{scale:g}")


def multi_scale_spikes(
    close: pd.Series,
    scales: tuple[float, ...] = (4, 8, 16, 32),
    threshold_sigmas: float = 3.0,
) -> pd.DataFrame:
    """Run `detect_spikes_via_wavelet` at multiple scales, return as DataFrame."""
    cols = {}
    for s in scales:
        cols[f"scale_{s:g}"] = detect_spikes_via_wavelet(
            close, scale=float(s), threshold_sigmas=threshold_sigmas
        )
    return pd.DataFrame(cols, index=close.index)


def coincident_spikes(spike_df: pd.DataFrame, min_scales: int = 2) -> pd.Series:
    """
    A high-confidence spike fires at multiple scales simultaneously —
    the same logic as Schwager's confluence concept, but applied to
    wavelet detections instead of named patterns.
    """
    pos = (spike_df > 0).sum(axis=1)
    neg = (spike_df < 0).sum(axis=1)
    out = pd.Series(0, index=spike_df.index, dtype=int)
    out[pos >= min_scales] = +1
    out[neg >= min_scales] = -1
    return out


# ==================================================================
# Demo
# ==================================================================
if __name__ == "__main__":
    np.random.seed(7)
    n = 256
    dates = pd.date_range("2023-01-02", periods=n, freq="B")

    # Synthetic series: trend + slow oscillation + fast noise + one shock
    t = np.arange(n)
    signal = (
        100
        + 0.05 * t                                  # slow trend
        + 4.0 * np.sin(2 * np.pi * t / 60)          # 60-bar cycle
        + 1.5 * np.sin(2 * np.pi * t / 12)          # 12-bar cycle
        + np.random.normal(0, 0.6, n)               # noise
    )
    signal[180] += 8.0                              # one big shock
    close = pd.Series(signal, index=dates, name="close")

    # 1. Multi-resolution decomposition
    mra = multi_resolution_decompose(close, wavelet="db4", levels=5)
    print("Energy fractions per band:")
    for k, v in mra.energy_per_band().items():
        print(f"  {k:>5}  {v:.3%}")
    err = (mra.reconstruct() - close).abs().max()
    print(f"  reconstruction max error: {err:.3e}")

    # 2. Denoising
    denoised = wavelet_denoise(close, levels=4, threshold_levels=2)
    print(f"\nNoise removed (RMS): "
          f"{(close - denoised).pow(2).mean() ** 0.5:.3f}")

    # 3. Multi-scale spike detection
    spikes = multi_scale_spikes(close, scales=(4, 8, 16, 32))
    coinc = coincident_spikes(spikes, min_scales=2)
    n_pos = int((coinc > 0).sum())
    n_neg = int((coinc < 0).sum())
    print(f"\nCoincident spikes (≥2 scales): {n_pos} peaks, {n_neg} troughs")
    print(f"Sample peak indices: "
          f"{coinc[coinc > 0].index[:5].strftime('%Y-%m-%d').tolist()}")

    # 4. Scalogram dimensions
    sg = scalogram(close, n_scales=48)
    print(f"\nScalogram shape (scales × time): {sg.coefficients.shape}")
    print(f"Scale range: {sg.scales.min():.1f} → {sg.scales.max():.1f}")
