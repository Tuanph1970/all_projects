"""The shared relative-volume primitive (Backlog #117).

Reproduces ai-insights' FR-EM-V1 algorithm so stock-data-service can publish an
unusual-volume reading with each price event. The agreement test that keeps the
two honest lives in ai-insights-service (it can import both); these pin the
behaviour that matters on its own terms.
"""
from __future__ import annotations

import pytest

from stock_common.analytics.volume import (
    DEFAULT_BASELINE_WINDOW,
    MIN_BASELINE_BARS,
    relative_volume,
)


def _flat(n=60, level=100):
    return [level] * n


# --- the measure ------------------------------------------------------------

def test_a_spike_reads_as_its_multiple_of_the_median():
    rv = relative_volume(_flat() + [420], 60)
    assert rv.known and rv.value == pytest.approx(4.2)
    assert rv.baseline == pytest.approx(100.0)


def test_a_quiet_bar_reads_below_one():
    assert relative_volume(_flat() + [50], 60).value == pytest.approx(0.5)


def test_the_baseline_is_a_MEDIAN_so_one_climax_day_cannot_mask_the_next():
    """The decision inherited from EM-1. A mean baseline absorbs an extreme day
    and understates the following one; a median does not move."""
    history = _flat(60, 100)
    history[30] = 10_000                      # one enormous day inside the window
    rv = relative_volume(history + [300], 60)
    assert rv.baseline == pytest.approx(100.0), "the outlier moved the baseline"
    assert rv.value == pytest.approx(3.0)


# --- causality --------------------------------------------------------------

def test_the_reading_cannot_see_its_own_bar_or_the_future():
    """The baseline is strictly [index-window, index). Appending later bars must
    not change any earlier reading."""
    past = [100 + (i % 7) for i in range(80)]
    future = [99_999] * 25
    before = [relative_volume(past, i).value for i in range(len(past))]
    after = [relative_volume(past + future, i).value for i in range(len(past))]
    assert before == after


def test_a_bar_is_not_part_of_its_own_baseline():
    """A single huge bar must read high, which it cannot do if it is averaged
    into its own denominator."""
    rv = relative_volume(_flat(40, 10) + [1000], 40)
    assert rv.value == pytest.approx(100.0)


# --- unavailability is explicit, never a 0 or a 1 ---------------------------

@pytest.mark.parametrize("index", [-1, 0, 99])
def test_an_unusable_index_is_unknown_with_a_reason(index):
    rv = relative_volume(_flat(10), index)
    assert not rv.known and rv.reason


def test_too_little_history_is_unknown_not_neutral():
    """A caller must fall back to neutral deliberately; it must not be handed a
    1.0 that looks like a measurement."""
    rv = relative_volume([10] * 5 + [500], 5)
    assert not rv.known
    assert rv.reason == "insufficient_history"


@pytest.mark.parametrize("cell", [None, "abc", float("nan"), -5])
def test_a_missing_or_impossible_volume_is_unknown(cell):
    rv = relative_volume(_flat() + [cell], 60)
    assert not rv.known and rv.reason == "missing_volume"


def test_missing_cells_inside_the_window_are_skipped_not_zeroed():
    history = _flat(60, 100)
    history[10] = None
    history[11] = "n/a"
    rv = relative_volume(history + [200], 60)
    assert rv.known and rv.baseline == pytest.approx(100.0)


# --- zero is data, but cannot be a denominator (EC-V2) ----------------------

def test_a_zero_volume_bar_is_kept_as_data():
    """Dropping zeros would turn a dormant stretch into a normal one."""
    rv = relative_volume(_flat(60, 0) + [0], 60)
    assert not rv.known
    assert rv.reason == "dormant_no_baseline"


def test_a_dormant_window_widens_to_the_last_real_trading_level():
    """E&M's Dormant Bottom: weeks of no sales ending in a flurry. The widened
    baseline counts only trading bars, so the reading does not drift with how
    LONG the dormancy was — that would be arithmetic, not evidence."""
    traded = [200] * 15
    dormant = [0] * 105
    rv = relative_volume(traded + dormant + [600], len(traded) + len(dormant))
    assert rv.known, rv.reason
    assert rv.baseline == pytest.approx(200.0)
    assert rv.value == pytest.approx(3.0)


def test_the_widened_reading_does_not_drift_with_the_length_of_the_dormancy():
    """The property the nonzero_only widening exists to protect."""
    traded = [200] * 15
    values = []
    for dead in (60, 90, 110):
        v = traded + [0] * dead + [600]
        values.append(relative_volume(v, len(v) - 1).value)
    assert len({round(x, 9) for x in values if x is not None}) == 1, values


# --- defaults ---------------------------------------------------------------

def test_the_window_and_floor_match_em1():
    assert DEFAULT_BASELINE_WINDOW == 100
    assert MIN_BASELINE_BARS == 10
