"""Chart-pattern detectors (Schwager Ch 5, 11, 12).

F-005 ships in three daily slices:
  - Day 1 (this commit): reversal patterns — H&S, Inverse H&S, Double Top,
    Double Bottom.
  - Day 2: continuation + bar patterns (flag, pennant, triangle, gap, WRD).
  - Day 3: aggregated /insights/patterns/{symbol} endpoint + integration
    tests.

Each detector returns a uniform `PatternMatch` (or None) so the eventual
aggregated endpoint can iterate them generically. See base.py.
"""
from app.services.patterns.base import PatternDetector, PatternMatch
from app.services.patterns.reversal import (
    HeadAndShouldersDetector,
    InverseHeadAndShouldersDetector,
    DoubleTopDetector,
    DoubleBottomDetector,
)

__all__ = [
    "PatternDetector",
    "PatternMatch",
    "HeadAndShouldersDetector",
    "InverseHeadAndShouldersDetector",
    "DoubleTopDetector",
    "DoubleBottomDetector",
]
