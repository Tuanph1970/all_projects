"""
Measured Move (MM):

Premise: markets tend to move in approximately equal-size price swings.
After an initial swing of magnitude S followed by a partial retracement to R,
the next swing in the original direction is projected to reach R + S
(uptrend) or R - S (downtrend).

Reliability is enhanced when several measured-move targets cluster
in the same price area (a "concentration" of MM targets).
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Swing:
    start_price: float
    end_price: float
    label: str = ""

    @property
    def magnitude(self) -> float:
        return abs(self.end_price - self.start_price)

    @property
    def direction(self) -> int:
        return 1 if self.end_price > self.start_price else -1


def measured_move_target(initial_swing: Swing, retracement_low: float) -> float:
    """Project the next swing target from the retracement point."""
    if initial_swing.direction == 1:
        return retracement_low + initial_swing.magnitude
    return retracement_low - initial_swing.magnitude


def cluster_targets(targets: List[float], tolerance_pct: float = 0.02
                    ) -> List[Tuple[float, int]]:
    """Group targets that fall within `tolerance_pct` of each other.
    Returns list of (cluster_center, count) sorted by count desc."""
    sorted_t = sorted(targets)
    clusters: List[List[float]] = []
    for t in sorted_t:
        if clusters and abs(t - clusters[-1][-1]) / clusters[-1][-1] <= tolerance_pct:
            clusters[-1].append(t)
        else:
            clusters.append([t])
    summary = [(sum(c) / len(c), len(c)) for c in clusters]
    summary.sort(key=lambda x: -x[1])
    return summary


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    # Numeric example based on a hypothetical stock:
    #   Swing A: rallies from 30.00 to 50.00  (+20)
    #   Pullback to 42.00
    #   Swing B (projected): 42 + 20 = 62
    initial = Swing(30.00, 50.00, "Initial rally")
    retrace = 42.00
    target = measured_move_target(initial, retrace)
    print(f"Initial swing magnitude: {initial.magnitude:.2f}")
    print(f"Retracement low: {retrace:.2f}")
    print(f"Measured move target: {target:.2f}")

    # Multiple swings in the same trend often produce overlapping targets
    # which raises confidence in the projected zone.
    multiple = [
        measured_move_target(Swing(30.0, 50.0), 42.0),  # 62.00
        measured_move_target(Swing(35.0, 52.0), 45.0),  # 62.00
        measured_move_target(Swing(40.0, 55.5), 47.0),  # 62.50
        measured_move_target(Swing(20.0, 40.0), 50.0),  # 70.00 (outlier)
    ]
    clusters = cluster_targets(multiple, tolerance_pct=0.02)
    print("\nMM target clusters (center, count):")
    for center, count in clusters:
        marker = "  *** strong" if count >= 2 else ""
        print(f"  {center:6.2f}  x{count}{marker}")
    # Expected:
    #   Initial swing magnitude: 20.00
    #   Retracement low: 42.00
    #   Measured move target: 62.00
    #   MM target clusters (center, count):
    #     62.17  x3  *** strong
    #     70.00  x1
