"""FR-SCAN-* — the daily momentum & base scanner (`docs/SRS_momentum_scanner.md`).

The discovery half of the platform. Every other signal surface here answers
"what should I do with THIS ticker"; this package answers "which tickers belong
on the list at all", by ranking a universe on medium-term relative strength and
keeping only the names a trend template admits.

Phase S-1 covers FR-SCAN-UNIV, FR-SCAN-LIQ, FR-SCAN-MOM, FR-SCAN-TREND and the
FR-SCAN-SEAM gate; S-2 adds FR-SCAN-BASE, FR-SCAN-SQUEEZE, FR-SCAN-MA and
FR-SCAN-LEVEL, plus the VT-4 null model that every candidate list is reported
beside (C4/EC-S5). The service surface (S-3) is not here yet.
"""
from app.services.scanner.base import (
    BaseAssessment,
    BaseWindow,
    MAProximity,
    Pivot,
    SqueezeMetrics,
    assess_base,
    detect_base,
    find_pivot,
    measure_ma_proximity,
    measure_squeeze,
)
from app.services.scanner.null_model import (
    NullFprResult,
    estimate_null_fpr,
    random_walk,
)
from app.services.scanner.momentum import (
    MomentumProfile,
    MomentumRank,
    horizon_return,
    profile_momentum,
    rank_cross_section,
)
from app.services.scanner.trend import TrendClause, TrendTemplate, assess_trend
from app.services.scanner.screen import (
    ScanCandidate,
    ScanConfig,
    ScanReport,
    SeamFinding,
    run_scan,
)

__all__ = [
    "BaseAssessment", "BaseWindow", "MAProximity", "Pivot", "SqueezeMetrics",
    "assess_base", "detect_base", "find_pivot", "measure_ma_proximity",
    "measure_squeeze",
    "NullFprResult", "estimate_null_fpr", "random_walk",
    "MomentumProfile", "MomentumRank", "horizon_return", "profile_momentum",
    "rank_cross_section",
    "TrendClause", "TrendTemplate", "assess_trend",
    "ScanCandidate", "ScanConfig", "ScanReport", "SeamFinding", "run_scan",
]
