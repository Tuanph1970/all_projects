"""Domain entities — immutable result dataclasses (SRS §4.1).

All arrays are plain numpy ndarrays stored in the entity.  Entities are
produced by use-cases and consumed by the API / frontend serialisation layer.
They must never hold mutable references to algorithm internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class MODWTResult:
    """Maximal Overlap Discrete Wavelet Transform result (FR-DECOMP-MODWT).

    approximation : A_J — the coarsest-scale smooth signal, shape (N,)
    details       : [D_1, D_2, ..., D_J] finest → coarsest, each shape (N,)
    coi_widths    : COI half-width in samples per detail level.
                    coi_widths[j] = (2^(j+1) - 1) * (filter_len - 1)

    Round-trip guarantee: approximation + sum(details) ≈ x within 1e-10.
    """
    approximation: np.ndarray
    details: list[np.ndarray]
    wavelet: str
    level: int
    coi_widths: list[int]

    @property
    def n_levels(self) -> int:
        return self.level

    def reconstruct(self) -> np.ndarray:
        """Sum all components; should match the original series to ~1e-10."""
        result = self.approximation.copy()
        for d in self.details:
            result = result + d
        return result


@dataclass
class EMDResult:
    """Empirical Mode Decomposition result (FR-DECOMP-EMD).

    imfs             : shape (K, N); last row is the monotonic residue.
    dominant_periods : period estimate per IMF via zero-crossing; length K-1
                       (residue has no meaningful period).
    n_sift_iters     : number of sifting iterations per IMF; length K.
    """
    imfs: np.ndarray
    dominant_periods: list[float]
    n_sift_iters: list[int]

    @property
    def n_imfs(self) -> int:
        return self.imfs.shape[0]

    @property
    def residue(self) -> np.ndarray:
        return self.imfs[-1]

    def reconstruct(self) -> np.ndarray:
        return self.imfs.sum(axis=0)


@dataclass
class VMDResult:
    """Variational Mode Decomposition result (FR-DECOMP-VMD).

    modes               : shape (K, N), sorted by ascending center_frequency.
    center_frequencies  : shape (K,) in cycles/sample, ascending.
    series_mean         : mean subtracted before decomposition; add back for
                          exact reconstruction together with modes.
    reconstruction_error: relative L2 error = ||x - (mean + sum(modes))||/||x||

    Trap B4: VMD is NOT exact reconstruction. Do not interpret variance shares
    as summing to 100%.
    """
    modes: np.ndarray
    center_frequencies: np.ndarray
    series_mean: float
    reconstruction_error: float

    @property
    def K(self) -> int:
        return self.modes.shape[0]

    def reconstruct(self) -> np.ndarray:
        return self.modes.sum(axis=0) + self.series_mean


@dataclass
class TimeFreqResult:
    """Time-frequency representation (CWT scalogram or Hilbert spectrum).

    power       : shape (n_freqs, N) — energy density |W|² or A(t)²
    frequencies : shape (n_freqs,) — frequency values (Hz or cycles/sample)
    periods     : shape (n_freqs,) — 1/frequencies
    coi         : shape (N,) — maximum RELIABLE period at each time step.
                  Values outside coi are edge-contaminated (Trap B7: mandatory).
    phase       : shape (n_freqs, N) or None — phase angle(W) if requested.
    """
    power: np.ndarray
    frequencies: np.ndarray
    periods: np.ndarray
    coi: np.ndarray
    phase: Optional[np.ndarray] = None


@dataclass
class HurstResult:
    """Hurst exponent estimate via wavelet variance (FR-HURST).

    H            : point estimate Ĥ = (slope + 2) / 2
    slope        : regression slope of log2(Var(d_j)) on j
    intercept    : regression intercept
    variances    : Var(d_j) for all levels j = 1..J_max
    scale_mask   : boolean mask of included scales (j_lo..j_hi)
    """
    H: float
    slope: float
    intercept: float
    variances: np.ndarray
    scale_mask: np.ndarray


@dataclass
class CoherenceResult:
    """Wavelet coherence between two series (FR-COH).

    r_squared   : shape (n_scales, N), bounded [0, 1]
    phase       : shape (n_scales, N), angle of smoothed cross-wavelet
    frequencies : shape (n_scales,)
    coi         : shape (N,) — max reliable period at each time (Trap B7)
    """
    r_squared: np.ndarray
    phase: np.ndarray
    frequencies: np.ndarray
    coi: np.ndarray


@dataclass
class ForecastResult:
    """Walk-forward volatility forecast result (FR-FCST-HAR / FR-FCST-VMD-HAR).

    timestamps  : integer indices (0..N-1) for which predictions are available
    predictions : log-RV predictions
    actuals     : actual log-RV values at the same timestamps
    metrics     : dict with keys rmse, mae, r2, qlike, dm_vs_har (may be None
                  for the baseline model itself)
    features_used : descriptive list of feature names
    """
    timestamps: np.ndarray
    predictions: np.ndarray
    actuals: np.ndarray
    metrics: dict
    features_used: list[str]

    @property
    def n_oos(self) -> int:
        return int(np.sum(~np.isnan(self.predictions)))


@dataclass
class BacktestResult:
    """Vol-targeting backtest result (FR-BT-*).

    pnl_gross  : daily gross P&L array
    pnl_net    : daily net P&L (gross minus transaction costs)
    positions  : daily position weights w[t]
    turnover   : daily turnover |w[t] - w[t-1]|
    metrics    : dict with keys ann_ret, ann_vol, sharpe, maxdd,
                 avg_leverage, ann_turnover, cost_drag
    """
    pnl_gross: np.ndarray
    pnl_net: np.ndarray
    positions: np.ndarray
    turnover: np.ndarray
    metrics: dict


# ── Part II — Pattern detection entities (SRS §II.4) ─────────────────────────


@dataclass
class Swing:
    """A single significant pivot anchoring pattern geometry (SRS §II.4).

    index : position in the (denoised) series
    price : value at that position
    kind  : 'H' (high) or 'L' (low) — see SwingSkeleton for the alternation
            guarantee enforced by the swing extractor (FR-SW-2).
    """
    index: int
    price: float
    kind: str  # 'H' | 'L'


@dataclass
class SwingSkeleton:
    """The piecewise-linear skeleton connecting consecutive swings (FR-SW-2).

    `swings` is the ordered, strictly-alternating H/L pivot list produced by the
    swing extractor.  The view properties give detectors cheap array access
    without copying the dataclass list each time.
    """
    swings: list[Swing]

    def __len__(self) -> int:
        return len(self.swings)

    @property
    def indices(self) -> np.ndarray:
        return np.array([s.index for s in self.swings], dtype=int)

    @property
    def prices(self) -> np.ndarray:
        return np.array([s.price for s in self.swings], dtype=np.float64)

    @property
    def kinds(self) -> list[str]:
        return [s.kind for s in self.swings]


@dataclass
class Detection:
    """One detected chart pattern (SRS §II.4 / FR-PAT-*, FR-SCORE-1, FR-FPR-2).

    pattern         : human-readable name, e.g. 'Head & Shoulders', 'Bull Flag'
    start_index     : first series index covered by the pattern
    end_index       : last series index covered by the pattern
    pivots          : constituent swing indices
    score           : [0, 1] geometric quality (FR-SCORE-1)
    null_percentile : where this score sits vs the random-walk null for the same
                      pattern (FR-FPR-2); None until null comparison is run.
    confirmed       : False when the pattern touches the right-edge cone of
                      influence and may still change as new data arrives
                      (Part II Trap B6 / Part I Constraint C2).
    details         : pattern-specific extras (prices, projected target, ...).
    """
    pattern: str
    start_index: int
    end_index: int
    pivots: list[int]
    score: float
    null_percentile: Optional[float] = None
    confirmed: bool = True
    details: dict = field(default_factory=dict)


@dataclass
class PatternPipelineResult:
    """End-to-end pattern pipeline output (SRS §II.4 `PipelineResult`).

    Renamed `PatternPipelineResult` to avoid colliding with any future Part I
    pipeline result entity.

    raw            : original input series
    denoised       : Layer-1 wavelet-denoised series (FR-DN-1)
    swings         : extracted swing pivots (FR-SW-*)
    detections     : aggregated detections across all detectors (FR-PAT-EXT)
    fpr_by_pattern : per-pattern false-positive rate vs the null (FR-FPR-1);
                     empty dict when compute_fpr is False.
    """
    raw: np.ndarray
    denoised: np.ndarray
    swings: list[Swing]
    detections: list[Detection]
    fpr_by_pattern: dict
