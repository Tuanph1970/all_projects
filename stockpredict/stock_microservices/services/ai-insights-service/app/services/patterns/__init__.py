"""Chart-pattern detectors (Schwager Ch 5, 11, 12).

F-005 / F-006 pattern catalog:
  - reversal.py  : H&S, Inverse H&S, Double Top, Double Bottom  (Day 1)
  - continuation.py : Flag, Pennant, Triangle ×3, Gap, WRD      (Day 2)
  - trap.py      : Bull Trap, Bear Trap                         (F-006)

Each detector returns a uniform `PatternMatch` (or None).  The aggregated
endpoint iterates all modules generically — see base.py.
"""
from app.services.patterns.base import PatternDetector, PatternMatch
from app.services.patterns.reversal import (
    HeadAndShouldersDetector,
    InverseHeadAndShouldersDetector,
    DoubleTopDetector,
    DoubleBottomDetector,
    run_reversal_detectors,
)
from app.services.patterns.continuation import (
    FlagDetector,
    PennantDetector,
    SymmetricalTriangleDetector,
    AscendingTriangleDetector,
    DescendingTriangleDetector,
    GapDetector,
    WideRangingDayDetector,
    run_continuation_detectors,
)
from app.services.patterns.trap import TrapDetector, run_trap_detectors

__all__ = [
    # base
    "PatternDetector",
    "PatternMatch",
    # reversal
    "HeadAndShouldersDetector",
    "InverseHeadAndShouldersDetector",
    "DoubleTopDetector",
    "DoubleBottomDetector",
    "run_reversal_detectors",
    # continuation / bar
    "FlagDetector",
    "PennantDetector",
    "SymmetricalTriangleDetector",
    "AscendingTriangleDetector",
    "DescendingTriangleDetector",
    "GapDetector",
    "WideRangingDayDetector",
    "run_continuation_detectors",
    # trap
    "TrapDetector",
    "run_trap_detectors",
]
