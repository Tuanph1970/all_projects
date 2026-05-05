"""
emd_stl_decomposer.py
=====================
Two more decomposition approaches for price series:

    1. Empirical Mode Decomposition (EMD)
       - Adaptive, data-driven
       - Output: IMFs (oscillations) + residual (trend)
       - Output count varies per signal — that's the point
       - Plus EEMD (ensemble) variant that mitigates mode-mixing

    2. STL — Seasonal-Trend decomposition using Loess
       - Three components: trend + seasonal + remainder
       - Fixed user-specified period
       - Designed for genuinely periodic data; on stocks, useful
         mainly for removing calendar effects

Both feed back into the Chapter 12 pipeline as pre-processing.

Algorithmic notes:

    EMD sifting (per IMF):
        1. Find local maxima and minima of signal s(t)
        2. Cubic-spline upper envelope through maxima
        3. Cubic-spline lower envelope through minima
        4. m(t) = (upper + lower) / 2
        5. h(t) = s(t) - m(t)
        6. If h(t) is an IMF, accept it. Else repeat with h(t) as s(t).
        7. Subtract IMF from original; recurse on residual.

    STL:
        Iterates inner loop:
            (a) detrend by subtracting current trend estimate
            (b) cycle-subseries smoothing → seasonal estimate
            (c) low-pass filter the seasonal to remove low-freq leakage
            (d) seasonal adjustment of the original
            (e) LOESS smooth the seasonally-adjusted → new trend
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from PyEMD import EMD, EEMD
from statsmodels.tsa.seasonal import STL


# ==================================================================
# 1. EMD — Empirical Mode Decomposition
# ==================================================================
@dataclass
class EMDDecomposition:
    imfs: list[pd.Series]           # IMF_1 (highest freq) → IMF_N
    residual: pd.Series              # the trend
    method: str                      # 'EMD' or 'EEMD'

    def reconstruct(self) -> pd.Series:
        s = self.residual.copy()
        for imf in self.imfs:
            s = s + imf
        return s

    def n_imfs(self) -> int:
        return len(self.imfs)

    def energy_per_imf(self) -> dict[str, float]:
        total = sum(imf.var() for imf in self.imfs) + self.residual.var()
        out = {f"IMF{i+1}": float(imf.var() / total)
               for i, imf in enumerate(self.imfs)}
        out["residual"] = float(self.residual.var() / total)
        return out

    def dominant_period_per_imf(self) -> dict[str, float]:
        """
        Estimate the average period of each IMF by counting zero crossings.
        Two zero crossings ≈ one full cycle, so period ≈ 2N / n_zero_crossings.
        """
        out = {}
        for i, imf in enumerate(self.imfs):
            sign_changes = np.sum(np.diff(np.sign(imf.values)) != 0)
            if sign_changes < 2:
                out[f"IMF{i+1}"] = float("inf")
            else:
                out[f"IMF{i+1}"] = 2.0 * len(imf) / sign_changes
        return out


def emd_decompose(
    close: pd.Series,
    max_imfs: Optional[int] = None,
    method: str = "EMD",
    eemd_trials: int = 100,
    noise_std: float = 0.2,
    seed: int = 0,
) -> EMDDecomposition:
    """
    Decompose a price series into IMFs + residual using EMD or EEMD.

    Parameters
    ----------
    close : pd.Series
        Price series indexed by date.
    max_imfs : int, optional
        Cap on number of IMFs to extract. None = unlimited.
    method : 'EMD' or 'EEMD'
        EEMD adds noise across trials and averages, mitigating mode-mixing
        but ~100× slower.
    eemd_trials : int
        Number of noisy trials for EEMD. Ignored for plain EMD.
    noise_std : float
        Standard deviation of the noise added in EEMD trials, expressed
        as a fraction of the input series' std.
    seed : int
        Random seed (EEMD only).
    """
    x = close.values.astype(float)

    if method == "EMD":
        emd = EMD()
        imfs_array = emd.emd(x, max_imf=max_imfs if max_imfs else -1)
    elif method == "EEMD":
        eemd = EEMD(trials=eemd_trials, noise_width=noise_std)
        eemd.noise_seed(seed)
        imfs_array = eemd.eemd(x, max_imf=max_imfs if max_imfs else -1)
    else:
        raise ValueError("method must be 'EMD' or 'EEMD'")

    # imfs_array shape: (n_imfs, n_samples)
    # PyEMD returns IMFs from highest frequency to lowest. The LAST row
    # is typically the slowest, near-monotonic component — effectively
    # the trend. We separate it out so the dataclass matches the standard
    # textbook formulation: signal = sum(IMFs) + residual.
    n_rows = imfs_array.shape[0]
    if n_rows >= 2:
        # Treat the last row (slowest oscillation / monotonic) as the trend.
        trend = imfs_array[-1]
        oscillation_imfs = imfs_array[:-1]
    else:
        trend = np.zeros_like(x)
        oscillation_imfs = imfs_array

    # Any tiny machine-precision residual goes into trend so reconstruction stays exact.
    reconstructed = oscillation_imfs.sum(axis=0) + trend
    leftover = x - reconstructed
    trend = trend + leftover

    imf_series = [
        pd.Series(oscillation_imfs[i], index=close.index, name=f"IMF{i+1}")
        for i in range(oscillation_imfs.shape[0])
    ]
    residual_series = pd.Series(trend, index=close.index, name="residual")

    return EMDDecomposition(imfs=imf_series, residual=residual_series,
                            method=method)


# ==================================================================
# 2. STL — Seasonal-Trend decomposition using Loess
# ==================================================================
@dataclass
class STLDecomposition:
    trend: pd.Series
    seasonal: pd.Series
    remainder: pd.Series
    period: int

    def reconstruct(self) -> pd.Series:
        return self.trend + self.seasonal + self.remainder

    def strength_of_trend(self) -> float:
        """
        Hyndman's measure: 1 - Var(remainder) / Var(remainder + trend).
        Range [0, 1]. Closer to 1 means trend dominates.
        """
        denom = (self.remainder + self.trend).var()
        if denom == 0:
            return 0.0
        return float(max(0.0, 1.0 - self.remainder.var() / denom))

    def strength_of_seasonality(self) -> float:
        """
        1 - Var(remainder) / Var(remainder + seasonal).
        Closer to 1 means seasonality dominates.
        """
        denom = (self.remainder + self.seasonal).var()
        if denom == 0:
            return 0.0
        return float(max(0.0, 1.0 - self.remainder.var() / denom))


def stl_decompose(
    close: pd.Series,
    period: int = 21,
    seasonal: int = 7,
    robust: bool = True,
) -> STLDecomposition:
    """
    Decompose a price series with STL.

    Parameters
    ----------
    close : pd.Series
        Price series indexed by date.
    period : int
        Length of the seasonal cycle in bars. For daily stock data:
            5   → weekly (day-of-week effects)
            21  → monthly (turn-of-month effects)
            63  → quarterly
            252 → annual (commodity seasonality)
    seasonal : int
        Length of the seasonal smoother (must be odd, ≥ 7).
        Smaller values let the seasonal pattern change more rapidly
        across periods.
    robust : bool
        If True, downweight outliers in trend/seasonal estimation.
        Recommended for noisy financial data.
    """
    if period < 2:
        raise ValueError("period must be >= 2")
    if seasonal % 2 == 0 or seasonal < 7:
        raise ValueError("seasonal must be odd and >= 7")

    result = STL(close, period=period, seasonal=seasonal,
                 robust=robust).fit()

    return STLDecomposition(
        trend=result.trend,
        seasonal=result.seasonal,
        remainder=result.resid,
        period=period,
    )


# ==================================================================
# 3. Cross-method denoising — feed clean prices to Chapter 12 detectors
# ==================================================================
def emd_denoise(
    close: pd.Series,
    drop_first_n: int = 1,
) -> pd.Series:
    """
    Denoise by removing the highest-frequency IMF(s) and reconstructing.
    drop_first_n=1 removes the noisiest IMF; drop_first_n=2 also removes
    the next-noisiest.

    EMD-based denoising is genuinely different from wavelet denoising:
    the highest-frequency IMF adapts to whatever "noise" looks like in
    *this* series, rather than assuming Gaussian white noise at fine scales.
    """
    decomp = emd_decompose(close)
    if drop_first_n >= len(decomp.imfs):
        raise ValueError(
            f"drop_first_n={drop_first_n} >= number of IMFs "
            f"({len(decomp.imfs)})"
        )
    out = decomp.residual.copy()
    for i, imf in enumerate(decomp.imfs):
        if i >= drop_first_n:
            out = out + imf
    out.name = "emd_denoised"
    return out


def stl_detrend(
    close: pd.Series,
    period: int = 21,
) -> pd.Series:
    """
    Return close minus the STL trend — useful for examining cyclic and
    residual structure without trend dominance.
    """
    d = stl_decompose(close, period=period)
    return (close - d.trend).rename("detrended")


# ==================================================================
# Demo
# ==================================================================
if __name__ == "__main__":
    np.random.seed(42)
    n = 252                                    # one trading year
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    t = np.arange(n)

    signal = (
        100
        + 0.04 * t
        + 4.0 * np.sin(2 * np.pi * t / 80)        # 80-bar cycle
        + 1.5 * np.sin(2 * np.pi * t / 21)        # ~monthly cycle
        + 0.5 * np.sin(2 * np.pi * t / 5)         # weekly cycle
        + np.random.normal(0, 0.6, n)
    )
    signal[120] += 6.0
    signal[200] -= 5.0
    close = pd.Series(signal, index=dates, name="close")

    # ----- EMD -----
    print("=" * 60)
    print("EMD")
    print("=" * 60)
    emd_result = emd_decompose(close)
    print(f"  Number of IMFs extracted: {emd_result.n_imfs()}")
    print(f"  Reconstruction max error: "
          f"{(emd_result.reconstruct() - close).abs().max():.3e}")
    print("  Energy fractions:")
    for k, v in emd_result.energy_per_imf().items():
        print(f"    {k:>9}  {v:.3%}")
    print("  Estimated dominant periods:")
    for k, v in emd_result.dominant_period_per_imf().items():
        period_str = "monotonic" if v == float("inf") else f"{v:.1f} bars"
        print(f"    {k:>9}  {period_str}")

    # ----- EEMD (ensemble) -----
    print("\n" + "=" * 60)
    print("EEMD (ensemble, mitigates mode mixing)")
    print("=" * 60)
    eemd_result = emd_decompose(close, method="EEMD",
                                eemd_trials=30, seed=7)
    print(f"  Number of IMFs extracted: {eemd_result.n_imfs()}")
    print(f"  Reconstruction max error: "
          f"{(eemd_result.reconstruct() - close).abs().max():.3e}")

    # ----- STL -----
    print("\n" + "=" * 60)
    print("STL with period=21 (monthly)")
    print("=" * 60)
    stl_result = stl_decompose(close, period=21, seasonal=7)
    print(f"  Strength of trend:       {stl_result.strength_of_trend():.3f}")
    print(f"  Strength of seasonality: "
          f"{stl_result.strength_of_seasonality():.3f}")
    print(f"  Reconstruction max error: "
          f"{(stl_result.reconstruct() - close).abs().max():.3e}")

    # ----- STL with period=5 (weekly) -----
    stl_weekly = stl_decompose(close, period=5, seasonal=7)
    print(f"\n  STL with period=5 (weekly):")
    print(f"    Strength of seasonality: "
          f"{stl_weekly.strength_of_seasonality():.3f}")
    print(f"    Strength of trend:       "
          f"{stl_weekly.strength_of_trend():.3f}")
