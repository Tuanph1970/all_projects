"""Shared data types and default parameters (SRS §4.1, Appendix A).

Result objects are frozen dataclasses; the wire/data-frame contracts (events, prices,
odds) are pandas and documented in CLAUDE.md, not modelled as classes here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# A window is a pair of integer index bounds (start, end_exclusive) into a price series.
Window = tuple[int, int]


@dataclass(frozen=True)
class Params:
    """Pipeline defaults (SRS Appendix A). Magnitudes are defaults, not test targets."""

    L: int = 120                 # estimation-window length (trading days)
    g: int = 5                   # gap: estimation ends g days before t0 (EC1)
    k1: int = 1                  # event window pre-days
    k2: int = 1                  # event window post-days
    jump_local_window: int = 21  # trailing daily-return window for local vol (EC5)
    jump_level: float = 0.01     # Lee-Mykland test level
    n_surrogates: int = 1000     # random-walk null replications (EC4)
    seed: int = 0                # reproducibility (EC7)


DEFAULTS = Params()


@dataclass(frozen=True)
class AlignedEvent:
    """Resolved event day and windows on the daily price grid (FR-ALIGN)."""

    event_id: str
    t0_index: int                # index of event day t0 in the price series
    est_window: Window           # [t0-(L+g), t0-g); end strictly < t0
    event_window: Window         # [t0-k1, t0+k2]  (inclusive of t0+k2)
    coverage: str = "full"       # "full" | "partial:<reason>"


@dataclass(frozen=True)
class Surprise:
    """Observed, standardised surprise (FR-SURP)."""

    method: str                  # "consensus" | "futures" | "odds"
    s_raw: float                 # actual - expected
    s: float                     # standardised: s_raw / scale
    expected: float              # the pre-event expectation used
    scale: float                 # sigma_kind (pre-event dispersion)
    sign: int                    # sign of s_raw: +1 / 0 / -1


@dataclass(frozen=True)
class AbnormalReturns:
    """Market-model abnormal returns over the event window (FR-AR)."""

    ar: np.ndarray               # abnormal returns over the event window
    car: float                   # cumulative abnormal return = sum(ar)
    alpha: float
    beta: float
    sigma_ar: float              # estimation-window residual std
    est_window: Window
    event_window: Window
    placebo_car: np.ndarray      # CAR distribution from non-event placebo windows (EC4)


@dataclass(frozen=True)
class JumpTest:
    """Lee-Mykland daily jump-test result (FR-JUMP)."""

    statistic: float             # L = r_t0 / sigma_local
    threshold: float             # extreme-value threshold at `level`
    is_jump: bool
    sigma_local: float           # local diffusive vol (pre-t0)
    null_fpr: float              # empirical FPR on the random-walk null (EC4)


@dataclass(frozen=True)
class CrossSectionExposure:
    """Cross-sectional exposure of CAR on surprise (FR-XS)."""

    gamma0: float                # intercept
    gamma1: float                # exposure: reaction per unit surprise
    se_gamma1: float             # robust standard error of gamma1
    cluster: str                 # inference method used (e.g. "event_date")
    n_assets: int
    n_event_dates: int
    r_squared: float


@dataclass(frozen=True)
class EventReaction:
    """Bundled single-event result (SRS §4.1)."""

    aligned: AlignedEvent
    surprise: Surprise
    abnormal: AbnormalReturns
    jump: JumpTest
