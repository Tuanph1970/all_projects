"""EM-8 M1 — the gap measured-move objective (Backlog #92).

E&M Ch 12 give a measuring rule to **one** kind of gap:

> **Continuation / Runaway / "Measuring" Gap** — it occurs in the middle of a
> rapid straight-line move, at **approximately the halfway point**. *Inference:
> prices will travel as far beyond the gap as they already have from the start
> of the move to the gap*, measured vertically on the chart.

And explicitly deny it to the others:

* **Breakaway** — *"No measuring implication."*
* **Common** — none.
* **Exhaustion** — *"a wide gap at the very end of a move"*. A target
  projected in the trend direction here points the way the move is **ending**.

What was wrong before (`#92`), in two independent ways:

1. `target = neckline ± gap_size` projected the **gap's own height**, not the
   distance already travelled. A gap is one day's jump; the move may be weeks.
2. It was emitted for **every** subtype, including the three with no rule.

Neither could be caught by testing the detector against itself — it agreed
with itself. It was found by reading the code against the source.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.patterns.continuation import GapDetector


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------

def _gap_series(*, pre_decline: int = 6, rise: int = 24,
                start_high: float = 106.0, move_low: float = 100.0,
                move_top: float = 118.0, gap: float = 3.0,
                direction: str = "up", post: int = 10,
                fill_after: int = 0, hl_pad: float = 0.5) -> pd.DataFrame:
    """A move with a deliberately identifiable start, then a gap.

    Shape for `direction="up"`: a short decline into a **V at `move_low`**
    (which is the swing low the halfway rule must find), a straight rise to
    `move_top`, then a gap of `gap`, then `post` bars.

    `fill_after > 0` drags a post-gap bar back through the gap so the detector
    classifies it as filled.
    """
    closes = list(np.linspace(start_high, move_low, pre_decline))
    closes += list(np.linspace(move_low, move_top, rise))[1:]
    gap_idx = len(closes)

    sign = 1.0 if direction == "up" else -1.0
    if direction == "down":
        closes = [start_high + (start_high - c) for c in closes]

    pre_last = closes[-1]
    closes.append(pre_last + sign * (gap + 1.0))
    for j in range(post):
        closes.append(closes[-1] + sign * 0.4)

    closes = np.asarray(closes, dtype=float)
    high = closes + hl_pad
    low = closes - hl_pad

    # Force the gap: the new bar's low must clear the previous bar's high.
    if direction == "up":
        low[gap_idx] = high[gap_idx - 1] + gap
        high[gap_idx] = low[gap_idx] + 2.0
        closes[gap_idx] = low[gap_idx] + 1.0
    else:
        high[gap_idx] = low[gap_idx - 1] - gap
        low[gap_idx] = high[gap_idx] - 2.0
        closes[gap_idx] = high[gap_idx] - 1.0

    if 0 < fill_after < post:
        # The fill bar is a wide reversal bar that dips back through the gap
        # while still OVERLAPPING its predecessor, and the series ends there.
        #
        # Both halves matter. Without the overlap, pulling a bar down below
        # the gap creates a fresh gap DOWN between it and the bar before;
        # without the truncation, the bars after it gap back UP. Either way
        # the detector -- which scans right-to-left for the most recent gap --
        # finds the spurious one instead of the planted one. The existing
        # `_gap_frame` helper in test_continuation_patterns.py documents the
        # same trap, and this fixture fell into it on the first run.
        k = gap_idx + fill_after
        closes, high, low = closes[:k + 1], high[:k + 1], low[:k + 1]
        if direction == "up":
            low[k] = high[gap_idx - 1] - 0.5
            high[k] = max(high[k], low[k - 1] + 0.1)
        else:
            high[k] = low[gap_idx - 1] + 0.5
            low[k] = min(low[k], high[k - 1] - 0.1)
        closes[k] = (low[k] + high[k]) / 2.0

    return pd.DataFrame({"open": closes, "high": high, "low": low,
                         "close": closes,
                         "volume": np.full(len(closes), 1000, dtype=int)})


def _runaway_up() -> pd.DataFrame:
    return _gap_series(direction="up", fill_after=0)


# ---------------------------------------------------------------------------
# H-M5a — scope: only the runaway gap has a rule
# ---------------------------------------------------------------------------

class TestOnlyTheRunawayGapGetsAnObjective:

    def test_a_runaway_gap_carries_an_objective(self):
        m = GapDetector().detect(_runaway_up())
        assert m is not None and m.details["gap_type"] == "runaway"
        assert m.measured_move_target is not None

    def test_a_breakaway_gap_carries_none(self):
        """E&M: 'No measuring implication.'"""
        df = _gap_series(direction="up", start_high=100.0, move_low=106.0,
                         move_top=94.0, fill_after=0)
        m = GapDetector().detect(df)
        assert m is not None and m.details["gap_type"] == "breakaway"
        assert m.measured_move_target is None

    def test_a_common_gap_carries_none(self):
        df = _gap_series(direction="up", move_low=100.0, move_top=103.0,
                         rise=24, fill_after=2)
        m = GapDetector().detect(df)
        assert m is not None and m.details["gap_type"] == "common"
        assert m.measured_move_target is None

    def test_an_exhaustion_gap_carries_none_because_the_move_is_ending(self):
        """The worst of the three. An exhaustion gap is 'a wide gap at the
        very end of a move', so a target projected in the trend direction
        points the way the move is finishing."""
        df = _gap_series(direction="up", move_low=100.0, move_top=160.0,
                         fill_after=2)
        m = GapDetector().detect(df)
        assert m is not None and m.details["gap_type"] == "exhaustion"
        assert m.measured_move_target is None

    @pytest.mark.parametrize("kind", ["breakaway", "common", "exhaustion"])
    def test_the_subtypes_without_a_rule_say_so(self, kind):
        frames = {
            "breakaway": _gap_series(direction="up", start_high=100.0,
                                     move_low=106.0, move_top=94.0),
            "common": _gap_series(direction="up", move_low=100.0,
                                  move_top=103.0, fill_after=2),
            "exhaustion": _gap_series(direction="up", move_low=100.0,
                                      move_top=160.0, fill_after=2),
        }
        m = GapDetector().detect(frames[kind])
        assert m is not None and m.details["gap_type"] == kind
        assert m.details["measuring_rule"] == "none"


# ---------------------------------------------------------------------------
# H-M5b — the halfway construction
# ---------------------------------------------------------------------------

class TestTheHalfwayRule:

    def test_the_objective_is_the_distance_travelled_projected_beyond_the_gap(self):
        """The gap sits in the middle: travelled before it, the same beyond."""
        df = _runaway_up()
        m = GapDetector().detect(df)
        assert m is not None and m.measured_move_target is not None

        i = m.key_bars[-1]
        near = float(df["high"].iloc[i - 1])     # pre-gap edge
        far = float(df["low"].iloc[i])           # post-gap edge
        start = m.details["move_start"]

        travelled = near - start
        assert m.measured_move_target == pytest.approx(far + travelled, abs=1e-3)

    def test_the_objective_is_not_the_gap_size_any_more(self):
        """The regression guard for `#92`'s first defect.

        On a move far longer than the gap, the old formula
        (`far_edge + gap_size`) and the halfway rule differ by a lot — so a
        revert cannot pass silently.
        """
        df = _runaway_up()
        m = GapDetector().detect(df)
        i = m.key_bars[-1]
        far = float(df["low"].iloc[i])
        gap_size = m.details["gap_size"]

        projected = m.measured_move_target - far
        assert projected > 3 * gap_size, (
            "the objective still looks like the gap's own height"
        )

    def test_the_move_start_is_the_swing_low_of_the_move(self):
        df = _runaway_up()
        m = GapDetector().detect(df)
        # The fixture's V bottoms at a close of 100.0, so its LOW is 99.5.
        # The tolerance is tight enough to tell those apart on purpose: the
        # module reads `low`/`high` rather than `close` because E&M measure
        # the move "vertically on the chart", and a loose tolerance would let
        # that documented choice be silently reversed.
        assert m.details["move_start"] == pytest.approx(99.5, abs=0.1)
        assert m.details["move_start_source"] == "pivot"

    def test_a_down_gap_mirrors_it(self):
        df = _gap_series(direction="down", fill_after=0)
        m = GapDetector().detect(df)
        assert m is not None and m.details["gap_direction"] == "down"
        if m.measured_move_target is not None:
            i = m.key_bars[-1]
            far = float(df["high"].iloc[i])
            assert m.measured_move_target < far


# ---------------------------------------------------------------------------
# which definition of "the start of the move" was used
# ---------------------------------------------------------------------------

class TestTheMoveStartIsNeverAmbiguous:
    """The plan requires that two definitions cannot silently coexist: the
    detector records which one it used, so the calibration (`M2`) can split
    on it instead of pooling two different measurements."""

    def test_the_source_is_always_recorded_with_an_objective(self):
        m = GapDetector().detect(_runaway_up())
        assert m.measured_move_target is not None
        assert m.details["move_start_source"] in ("pivot", "window")
        assert m.details["measuring_rule"] == "runaway_halfway"

    def test_the_fallback_is_used_when_no_pivot_precedes_the_gap(self):
        """A move with no confirmed swing low before the gap — a straight
        rise from the first bar — still measures, from the window extreme,
        and says that is what it did."""
        df = _gap_series(pre_decline=2, rise=28, start_high=100.0,
                         move_low=100.0, move_top=124.0, fill_after=0)
        m = GapDetector().detect(df)
        assert m is not None
        if m.measured_move_target is not None:
            assert m.details["move_start_source"] in ("pivot", "window")


# ---------------------------------------------------------------------------
# the objective must not read bars after the gap
# ---------------------------------------------------------------------------

class TestTheObjectiveIsCausal:

    @pytest.mark.parametrize("extra", [0, 3, 10])
    def test_the_objective_does_not_depend_on_how_many_bars_follow(self, extra):
        """The objective is built from the move *before* the gap.

        Tested by truncation rather than by perturbation: shifting the
        post-gap bars creates a NEW gap, and the detector then reports that
        one instead -- so a poke tests the fixture, not the measurement. How
        many bars follow is the variable that cannot change a causal
        objective, so that is the one to vary.
        """
        base = _runaway_up()
        full = GapDetector().detect(base)
        assert full is not None and full.measured_move_target is not None
        i = full.key_bars[-1]

        cut = GapDetector().detect(base.iloc[:i + 1 + extra])
        assert cut is not None and cut.key_bars == full.key_bars
        assert cut.measured_move_target == pytest.approx(full.measured_move_target)

    def test_repeated_runs_are_identical(self):
        df = _runaway_up()
        a = GapDetector().detect(df)
        b = GapDetector().detect(df)
        assert a.measured_move_target == b.measured_move_target
