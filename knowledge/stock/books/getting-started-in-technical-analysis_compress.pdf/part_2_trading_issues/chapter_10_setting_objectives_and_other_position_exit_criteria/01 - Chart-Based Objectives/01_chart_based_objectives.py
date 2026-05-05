"""
Chart-Based Objective: Head-and-Shoulders price target.

The classic projection rule:
    Target = Neckline - (Head - Neckline)   [for a top]
    Target = Neckline + (Neckline - Head)   [for a bottom, inverse H&S]

This file gives a tiny, dependency-light implementation suitable for
plugging into a backtest or screener.
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class HeadShouldersPattern:
    left_shoulder: float
    head: float
    right_shoulder: float
    neckline: float
    pattern_type: Literal["top", "bottom"]


def project_head_shoulders_target(p: HeadShouldersPattern) -> float:
    """Return the projected price target after a neckline break."""
    height = abs(p.head - p.neckline)
    if p.pattern_type == "top":
        return p.neckline - height
    return p.neckline + height


def validate_pattern(p: HeadShouldersPattern,
                     shoulder_tolerance: float = 0.05) -> Optional[str]:
    """Quick sanity check. Returns None if OK, else an error string."""
    if p.pattern_type == "top":
        if not (p.head > p.left_shoulder and p.head > p.right_shoulder):
            return "Head must be the highest point in a top pattern"
        if p.neckline >= min(p.left_shoulder, p.right_shoulder):
            return "Neckline must be below both shoulders"
    else:
        if not (p.head < p.left_shoulder and p.head < p.right_shoulder):
            return "Head must be the lowest point in a bottom pattern"
        if p.neckline <= max(p.left_shoulder, p.right_shoulder):
            return "Neckline must be above both shoulders"

    asymmetry = abs(p.left_shoulder - p.right_shoulder) / max(
        p.left_shoulder, p.right_shoulder)
    if asymmetry > shoulder_tolerance:
        return f"Shoulders differ by {asymmetry:.1%} (>{shoulder_tolerance:.0%})"
    return None


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    # Real-numbers example: a stock peaks at 64, with shoulders at 60 and a
    # neckline at 58. After breakdown, the projected target is 52.
    pattern = HeadShouldersPattern(
        left_shoulder=60.0,
        head=64.0,
        right_shoulder=61.0,
        neckline=58.0,
        pattern_type="top",
    )

    err = validate_pattern(pattern)
    print(f"Validation: {'OK' if err is None else err}")
    target = project_head_shoulders_target(pattern)
    print(f"Head height above neckline: {pattern.head - pattern.neckline:.2f}")
    print(f"Projected downside target after neckline break: {target:.2f}")
    # Sample output:
    #   Validation: OK
    #   Head height above neckline: 6.00
    #   Projected downside target after neckline break: 52.00
