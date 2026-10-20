"""EM-1 / V1 — unit tests for the volume primitives (FR-EM-V1, FR-EM-V2).

These are written test-first, per `docs/implementation_plan_em1_volume.md` task V1,
and they encode the four harnesses that V1 is responsible for:

  H4  causality (C1)  — the baseline at bar i reads only bars < i, so appending
                        future bars can never move a past value. This is the test
                        that forbids whole-frame normalisation, and it goes in on
                        day one precisely so no later task can violate it quietly.
  H5  thin / missing  — NULL, zero, constant and too-short volume all read as
                        *unknown* (factor exactly 1.0), never as a penalty. E&M's
                        Dormant Bottom (Ch 7) is a real VN small-cap shape.
  H6  determinism     — identical input, identical output, evidence dicts included.
  EC-V5 outliers      — one absurd vendor print is bounded by construction (median
                        baseline + rank-based trend), with no cleaning step.

Every assertion is a *property*. None asserts a magnitude from Edwards & Magee —
`baseline_window` and the factor bounds are defaults pending the S2 sweep
(FR-EM-V11, CLAUDE.md).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pytest

from app.services.patterns.volume import (
    DEFAULT_BASELINE_WINDOW,
    FACTOR_CEILING,
    FACTOR_FLOOR,
    MIN_BASELINE_BARS,
    NEUTRAL_FACTOR,
    VolumeVerdict,
    relative_volume,
    span_relative_volume,
    volume_trend,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _flat(n: int, level: float = 1_000_000.0) -> List[float]:
    return [level] * n


def _rising(n: int, start: float = 100_000.0, step: float = 10_000.0) -> List[float]:
    return [start + i * step for i in range(n)]


def _falling(n: int, start: float = 1_000_000.0, step: float = 10_000.0) -> List[float]:
    return [start - i * step for i in range(n)]


# ===========================================================================
# FR-EM-V1 — relative volume
# ===========================================================================

class TestRelativeVolume:
    """rvol = volume[i] / median(volume[i-window : i])."""

    def test_flat_volume_gives_rvol_of_one(self):
        vol = _flat(80)
        rv = relative_volume(vol, 70)
        assert rv.value == pytest.approx(1.0)
        assert rv.reason == ""

    def test_double_the_baseline_gives_rvol_of_two(self):
        vol = _flat(80)
        vol[70] = 2_000_000.0
        rv = relative_volume(vol, 70)
        assert rv.value == pytest.approx(2.0)

    def test_half_the_baseline_gives_rvol_of_one_half(self):
        vol = _flat(80)
        vol[70] = 500_000.0
        assert relative_volume(vol, 70).value == pytest.approx(0.5)

    def test_baseline_uses_the_median_not_the_mean(self):
        """FR-EM-V1: a single climax day must not inflate the baseline and mask
        the next one. With one huge print in the window, a mean baseline would
        drag rvol well below 1.0; the median leaves it at 1.0."""
        vol = _flat(80, 1_000_000.0)
        vol[60] = 500_000_000.0          # one absurd day inside the window
        rv = relative_volume(vol, 70)
        assert rv.baseline == pytest.approx(1_000_000.0)
        assert rv.value == pytest.approx(1.0)

    def test_baseline_window_is_respected(self):
        """Volume outside the trailing window must not influence the baseline."""
        vol = _flat(200, 1_000_000.0)
        for i in range(0, 100):
            vol[i] = 50_000_000.0        # ancient history, far outside the window
        rv = relative_volume(vol, 199, baseline_window=50)
        assert rv.baseline == pytest.approx(1_000_000.0)
        assert rv.bars_used == 50


# ===========================================================================
# H4 — causality (C1).  The binding constraint.
# ===========================================================================

class TestH4Causality:
    """The baseline at bar i reads only bars strictly before i."""

    def test_appending_future_bars_changes_no_past_value(self):
        """H4: compute over 0..t, append t+1..n, recompute — nothing at or
        before t may move. Any whole-frame normalisation fails this."""
        rng = np.random.default_rng(20261012)
        past = list(rng.integers(100_000, 5_000_000, size=120).astype(float))
        future = list(rng.integers(100_000, 5_000_000, size=80).astype(float))

        before = [relative_volume(past, i).value for i in range(len(past))]
        after = [relative_volume(past + future, i).value for i in range(len(past))]

        assert before == after

    def test_a_volume_spike_in_the_future_cannot_move_a_past_rvol(self):
        """The sharpest form of the same statement: one gigantic future print
        must leave every past reading untouched."""
        vol = _flat(100)
        baseline_reading = relative_volume(vol, 90).value

        extended = vol + [10_000_000_000.0] * 20
        assert relative_volume(extended, 90).value == pytest.approx(baseline_reading)

    def test_the_bar_itself_is_excluded_from_its_own_baseline(self):
        """If bar i were included in its own baseline, a huge print would pull
        its own denominator up and understate the spike."""
        vol = _flat(80, 1_000_000.0)
        vol[70] = 100_000_000.0
        rv = relative_volume(vol, 70)
        assert rv.value == pytest.approx(100.0)

    def test_span_relative_volume_is_causal(self):
        """H4 for the span helper: each bar in the span uses its own trailing
        baseline, so appending bars after the span changes nothing."""
        rng = np.random.default_rng(7)
        vol = list(rng.integers(100_000, 2_000_000, size=150).astype(float))
        before = span_relative_volume(vol, 100, 120).value
        after = span_relative_volume(vol + _flat(50, 9_999_999.0), 100, 120).value
        assert before == pytest.approx(after)


# ===========================================================================
# H5 — thin and missing data (EC-V1, EC-V2, EC-V4, EC-V8)
# ===========================================================================

class TestH5ThinAndMissingData:
    """Unavailable volume reads as *unknown*, never as a penalty."""

    def test_all_none_volume_is_unknown(self):
        """EC-V1: the upstream column is nullable. NULL is not zero."""
        vol: List[Optional[float]] = [None] * 80
        rv = relative_volume(vol, 70)
        assert rv.value is None
        assert rv.reason != ""

    def test_none_at_the_bar_itself_is_unknown(self):
        vol: List[Optional[float]] = _flat(80)
        vol[70] = None
        assert relative_volume(vol, 70).value is None

    def test_nan_is_treated_as_missing_not_as_a_number(self):
        vol = _flat(80)
        vol[70] = float("nan")
        assert relative_volume(vol, 70).value is None

    def test_none_inside_the_window_is_skipped_not_imputed(self):
        """EC-V1: 'never impute zero'. Dropping the holes must leave the
        baseline on the surviving bars."""
        vol: List[Optional[float]] = _flat(80, 1_000_000.0)
        holes = range(40, 50)
        for i in holes:
            vol[i] = None
        index = 70
        rv = relative_volume(vol, index)
        assert rv.baseline == pytest.approx(1_000_000.0)
        # Stated against the window actually in force, not a literal: the
        # default is swept (`FR-EM-V11`, and it moved 50 -> 100 at S2), and the
        # PROPERTY under test is that holes are skipped rather than imputed —
        # which a hardcoded count stops expressing the moment the window moves.
        window_start = max(0, index - DEFAULT_BASELINE_WINDOW)
        expected = (index - window_start) - len([i for i in holes if i >= window_start])
        assert rv.bars_used == expected

    def test_too_few_bars_before_the_index_is_unknown(self):
        """EC-V4: fewer than MIN_BASELINE_BARS usable bars → unknown."""
        vol = _flat(MIN_BASELINE_BARS - 1)
        rv = relative_volume(vol, MIN_BASELINE_BARS - 1)
        assert rv.value is None

    def test_index_zero_is_unknown(self):
        """There is nothing before bar 0, so there is no causal baseline."""
        assert relative_volume(_flat(80), 0).value is None

    def test_zero_volume_run_widens_to_the_nearest_usable_baseline(self):
        """EC-V2: zero is data, not missing — but a zero baseline makes rvol
        undefined, so widen backwards to the nearest usable window."""
        vol = _flat(200, 1_000_000.0)
        for i in range(140, 190):          # a 50-bar dormant stretch
            vol[i] = 0.0
        vol[190] = 3_000_000.0
        rv = relative_volume(vol, 190, baseline_window=50)
        assert rv.value is not None
        assert rv.baseline == pytest.approx(1_000_000.0)
        assert rv.value == pytest.approx(3.0)

    @pytest.mark.parametrize("dormant_bars", [20, 50, 60, 90])
    def test_the_reading_does_not_drift_with_the_length_of_the_dormancy(
        self, dormant_bars: int
    ):
        """EC-V2, and the bug that the previous test caught: a baseline that
        blends dead bars into the median makes rvol a function of how many
        zeros happen to fall inside the widened window. The flurry after a
        20-session sleep and after a 90-session sleep must read the same."""
        vol = _flat(260, 1_000_000.0)
        spike_at = 250
        for i in range(spike_at - dormant_bars, spike_at):
            vol[i] = 0.0
        vol[spike_at] = 3_000_000.0

        rv = relative_volume(vol, spike_at, baseline_window=50)
        assert rv.baseline == pytest.approx(1_000_000.0)
        assert rv.value == pytest.approx(3.0)

    def test_entirely_zero_volume_is_unknown_not_a_penalty(self):
        """A permanently dormant ticker (E&M's Dormant Bottom, Ch 7) must read
        as unknown — never as bearish evidence."""
        vol = _flat(200, 0.0)
        rv = relative_volume(vol, 190)
        assert rv.value is None
        assert rv.reason != ""

    def test_constant_volume_yields_no_trend_verdict(self):
        """A perfectly flat series carries no information about direction."""
        assert volume_trend(_flat(40), 10, 40).value == pytest.approx(0.0)

    def test_unknown_never_produces_a_penalty_factor(self):
        """H5's headline property: the neutral verdict is exactly 1.0, so an
        unknown can never be mistaken for adverse evidence."""
        neutral = VolumeVerdict.neutral("no_volume_data")
        assert neutral.factor == NEUTRAL_FACTOR == 1.0
        assert neutral.score is None
        assert neutral.evidence["status"] == "unknown"
        assert neutral.evidence["reason"] == "no_volume_data"

    def test_thin_volume_is_marked_so_the_ui_can_explain_itself(self):
        """EC-V8: the UI must be able to say *why* there is no verdict."""
        neutral = VolumeVerdict.neutral("thin_volume", thin_volume=True)
        assert neutral.evidence["thin_volume"] is True

    def test_an_empty_series_does_not_raise(self):
        assert relative_volume([], 0).value is None
        assert volume_trend([], 0, 0).value is None

    def test_out_of_range_index_does_not_raise(self):
        assert relative_volume(_flat(20), 99).value is None


# ===========================================================================
# FR-EM-V2 — volume trend
# ===========================================================================

class TestVolumeTrend:
    """A monotone-direction measure in [-1, +1]: negative = drying up."""

    def test_monotonically_falling_volume_is_minus_one(self):
        """'Volume diminishes continuously' (Ch 11) is the flag's condition."""
        assert volume_trend(_falling(40), 0, 40).value == pytest.approx(-1.0)

    def test_monotonically_rising_volume_is_plus_one(self):
        """'Activity must build through the head' (Ch 7)."""
        assert volume_trend(_rising(40), 0, 40).value == pytest.approx(1.0)

    def test_the_measure_is_bounded(self):
        rng = np.random.default_rng(99)
        for seed_shift in range(20):
            vol = list(rng.integers(1, 10_000_000, size=60).astype(float))
            v = volume_trend(vol, 0, 60).value
            assert v is not None
            assert -1.0 <= v <= 1.0

    def test_span_bounds_are_respected(self):
        """Volume outside [start, end) must not affect the verdict."""
        vol = _falling(30) + _rising(30, start=1.0, step=1_000_000.0)
        assert volume_trend(vol, 0, 30).value == pytest.approx(-1.0)
        assert volume_trend(vol, 30, 60).value == pytest.approx(1.0)

    def test_too_short_a_span_is_unknown(self):
        assert volume_trend(_flat(10), 5, 7).value is None

    def test_missing_values_inside_the_span_are_skipped(self):
        vol: List[Optional[float]] = _falling(40)
        for i in (10, 11, 12):
            vol[i] = None
        v = volume_trend(vol, 0, 40).value
        assert v is not None
        assert v < 0


# ===========================================================================
# EC-V5 — one absurd print must be bounded by construction
# ===========================================================================

class TestECV5OutlierRobustness:
    """No outlier-rejection step is specified: robust statistics instead."""

    def test_one_absurd_print_does_not_flip_the_trend_verdict(self):
        """A rank-based measure moves by at most one observation's worth; an
        OLS slope on raw volume would be dragged positive by this print."""
        clean = _falling(40)
        dirty = list(clean)
        dirty[5] = 10_000_000_000.0        # bad vendor row early in the span

        clean_v = volume_trend(clean, 0, 40).value
        dirty_v = volume_trend(dirty, 0, 40).value

        assert dirty_v < 0, "a drying-up span must still read as drying up"
        assert abs(dirty_v - clean_v) < 0.25

    def test_one_absurd_print_does_not_distort_a_later_baseline(self):
        """Already asserted via the median in TestRelativeVolume; restated here
        as the EC-V5 contract so a refactor to a mean baseline fails loudly."""
        vol = _flat(120, 1_000_000.0)
        vol[80] = 10_000_000_000.0
        assert relative_volume(vol, 110).baseline == pytest.approx(1_000_000.0)


# ===========================================================================
# H6 — determinism
# ===========================================================================

class TestH6Determinism:

    def test_repeated_calls_are_identical(self):
        rng = np.random.default_rng(4242)
        vol = list(rng.integers(50_000, 8_000_000, size=180).astype(float))

        first = [relative_volume(vol, i) for i in range(len(vol))]
        second = [relative_volume(vol, i) for i in range(len(vol))]
        assert first == second

        assert volume_trend(vol, 20, 90) == volume_trend(vol, 20, 90)
        assert span_relative_volume(vol, 20, 90) == span_relative_volume(vol, 20, 90)

    def test_evidence_dict_ordering_is_stable(self):
        a = VolumeVerdict.neutral("x", thin_volume=True)
        b = VolumeVerdict.neutral("x", thin_volume=True)
        assert list(a.evidence.keys()) == list(b.evidence.keys())


# ===========================================================================
# Factor bounds (FR-EM-V7) — the constants V4 will compose with
# ===========================================================================

class TestFactorBounds:
    """Volume is corroboration, not the finding: it can neither erase a
    geometrically excellent pattern nor manufacture a poor one."""

    def test_volume_can_only_discredit(self):
        """Backlog #81. The ceiling sits exactly at neutral, measured: a
        ceiling above it never raised detection power at a fixed
        false-positive rate (TPR 69.2% at 1.00, 61.5% at the shipped 1.15,
        30.8% at 1.60) because it lifts the far more numerous noise detections
        along with the signal, so the gate climbs faster than a planted
        pattern's confidence does.

        This replaces an assertion that the bounds *bracket* neutral, which
        was true of `FR-EM-V7`'s original 1.15 and is now deliberately false.
        """
        assert FACTOR_FLOOR < NEUTRAL_FACTOR
        assert FACTOR_CEILING == pytest.approx(NEUTRAL_FACTOR)

    def test_bounds_are_deliberately_asymmetric(self):
        """SRS §8 q2: E&M's volume evidence discredits better than it promotes,
        so the floor is further from neutral than the ceiling. Pending the S2
        sweep (FR-EM-V11) — this test pins the *intent*, not the values."""
        assert (NEUTRAL_FACTOR - FACTOR_FLOOR) > (FACTOR_CEILING - NEUTRAL_FACTOR)

    def test_defaults_are_documented_as_sweepable(self):
        assert DEFAULT_BASELINE_WINDOW > MIN_BASELINE_BARS > 1
