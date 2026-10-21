"""EM-8 M2 — the calibration harness's own tests (H-M2, H-M3).

The harness decides whether E&M's measuring rules hold, so its scoring has to
be right before its output means anything. These test the scoring, not the
detectors — and in particular the two ways a completion study flatters itself:

* counting an objective that was **already behind price** as reached (`EC-M1`);
* comparing against a null that is not **matched on distance**, which measures
  how near the targets are rather than what the patterns knew.
"""
from __future__ import annotations

import random

import pandas as pd
import pytest

from tests.em8_calibration import (
    EM_FAMILIES,
    MIN_SYMBOLS,
    OUR_FAMILIES,
    Observation,
    excursion,
    family_of,
    holm,
    non_overlapping,
    null_rate,
    reached,
)


def _frame(closes, pad: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame({
        "open": closes,
        "high": [c + pad for c in closes],
        "low": [c - pad for c in closes],
        "close": closes,
        "volume": [1000] * len(closes),
    })


# ---------------------------------------------------------------------------
# H-M2 — planted completion
# ---------------------------------------------------------------------------

class TestPlantedCompletion:

    def test_an_objective_reached_inside_the_window_is_complete(self):
        df = _frame([100.0] * 5 + [100, 102, 104, 106, 108])
        assert reached(df, bar=4, horizon=5, objective=106.0, up=True) is True

    def test_an_objective_missed_by_a_hair_is_incomplete(self):
        """E&M reject a dead band — 'any penetration, even 0.01, counts' — so
        the boundary must be exact in both directions."""
        df = _frame([100.0] * 5 + [100, 102, 104, 105.99, 105.5])
        assert reached(df, bar=4, horizon=4, objective=106.0, up=True) is False
        assert reached(df, bar=4, horizon=4, objective=105.99, up=True) is True

    def test_reaching_it_after_the_window_does_not_count(self):
        df = _frame([100.0] * 5 + [100, 101, 102, 103, 120])
        assert reached(df, bar=4, horizon=3, objective=110.0, up=True) is False
        assert reached(df, bar=4, horizon=5, objective=110.0, up=True) is True

    def test_a_short_tail_is_unmeasurable_not_a_failure(self):
        """`EC-M2`. Returning False here would score every pattern near the
        end of the data as a miss."""
        df = _frame([100.0] * 10)
        assert reached(df, bar=8, horizon=20, objective=110.0, up=True) is None

    def test_the_down_side_mirrors(self):
        df = _frame([100.0] * 5 + [100, 98, 96, 94, 92])
        assert reached(df, bar=4, horizon=5, objective=94.0, up=False) is True
        assert reached(df, bar=4, horizon=2, objective=94.0, up=False) is False

    def test_the_touch_is_read_on_the_intraday_extreme(self):
        """E&M measure the move on the chart, and the chart shows the high."""
        df = _frame([100.0] * 5 + [100, 101, 102, 102, 102], pad=5.0)
        assert reached(df, bar=4, horizon=5, objective=106.0, up=True) is True


# ---------------------------------------------------------------------------
# H-M3 — the vacuous-objective guard
# ---------------------------------------------------------------------------

class TestVacuousObjectives:

    def test_an_objective_behind_price_is_classified_vacuous(self):
        """`EC-M1`. The sweep excludes these; the definition is here so the
        rule cannot drift from the one the study applies."""
        behind = Observation("X", 10, "f", "p", entry=100.0, objective=95.0)
        assert behind.up is False
        ahead = Observation("X", 10, "f", "p", entry=100.0, objective=105.0)
        assert ahead.up is True

    def test_a_bullish_objective_already_below_price_would_score_free(self):
        """Demonstrates WHY it is excluded rather than merely that it is: at
        bar 4 price is already above 95, so a 'bullish' objective of 95 is
        reached by standing still."""
        df = _frame([100.0] * 10)
        assert reached(df, bar=4, horizon=5, objective=95.0, up=True) is True


# ---------------------------------------------------------------------------
# the overrun, which is what makes "minimum" measurable
# ---------------------------------------------------------------------------

class TestTheOverrun:

    def test_arriving_exactly_at_the_objective_is_one_times(self):
        df = _frame([100.0] * 5 + [100, 102, 104, 106, 106])
        obs = Observation("X", 4, "f", "p", entry=100.0, objective=106.0)
        assert excursion(df, 4, 5, obs) == pytest.approx(1.0)

    def test_running_three_times_as_far_is_three_times(self):
        df = _frame([100.0] * 5 + [100, 105, 110, 115, 118])
        obs = Observation("X", 4, "f", "p", entry=100.0, objective=106.0)
        assert excursion(df, 4, 5, obs) == pytest.approx(3.0, abs=0.01)

    def test_a_zero_distance_objective_has_no_overrun(self):
        df = _frame([100.0] * 12)
        obs = Observation("X", 4, "f", "p", entry=100.0, objective=100.0)
        assert excursion(df, 4, 5, obs) is None


# ---------------------------------------------------------------------------
# the null must be matched on DISTANCE
# ---------------------------------------------------------------------------

class TestTheNullIsMatched:

    def test_a_further_objective_is_harder_for_the_null_too(self):
        """The property that makes the null a control rather than a constant.

        If the null ignored distance it would return the same rate for both,
        and the comparison would reward near targets instead of informative
        patterns.
        """
        random.seed(1)
        closes = [100.0 + (i % 17) * 0.8 for i in range(600)]
        df = _frame(closes, pad=0.5)

        near = Observation("X", 300, "f", "p", entry=100.0, objective=101.0)
        far = Observation("X", 300, "f", "p", entry=100.0, objective=140.0)
        rng = random.Random(7)
        r_near = null_rate(df, near, 20, rng)
        r_far = null_rate(df, far, 20, rng)
        assert r_near is not None and r_far is not None
        assert r_near > r_far

    def test_the_null_declines_when_the_series_is_too_short(self):
        df = _frame([100.0] * 60, pad=0.5)
        obs = Observation("X", 10, "f", "p", entry=100.0, objective=110.0)
        assert null_rate(df, obs, 20, random.Random(1)) is None


# ---------------------------------------------------------------------------
# sampling and bookkeeping
# ---------------------------------------------------------------------------

class TestNonOverlap:

    def test_observations_closer_than_the_horizon_are_dropped(self):
        obs = [Observation("X", b, "f", "p", 100.0, 110.0) for b in (0, 5, 9, 30, 31)]
        kept = [o.bar for o in non_overlapping(obs, 10)]
        assert kept == [0, 30]

    def test_a_longer_horizon_keeps_no_more_than_a_shorter_one(self):
        obs = [Observation("X", b, "f", "p", 100.0, 110.0) for b in range(0, 100, 7)]
        assert len(non_overlapping(obs, 60)) <= len(non_overlapping(obs, 10))


class TestFamilies:

    def test_em_rules_and_ours_are_kept_apart(self):
        assert family_of("Head and Shoulders").startswith("H&S")
        assert family_of("Wide-Ranging Day").startswith("[ours]")
        assert family_of("Bull Trap").startswith("[ours]")

    def test_gap_subtypes_without_a_rule_are_not_a_family(self):
        """Only the runaway gap has a measuring rule (EM-8 M1 / #92)."""
        assert family_of("Gap (runaway)") is not None
        for kind in ("breakaway", "common", "exhaustion"):
            assert family_of(f"Gap ({kind})") is None

    def test_no_pattern_is_in_both_sets(self):
        assert not (set(EM_FAMILIES) & set(OUR_FAMILIES))


class TestHolm:

    def test_a_single_tiny_p_survives(self):
        assert holm({"a": 0.001, "b": 0.9})["a"] is True

    def test_a_family_too_thin_to_judge_cannot_survive(self):
        """Every cell thin leaves p = 1.0, which must not pass."""
        assert holm({"a": 1.0, "b": 1.0}) == {"a": False, "b": False}

    def test_holm_is_stricter_than_uncorrected(self):
        """0.03 alone would pass at 0.05; against four others it must not."""
        out = holm({"a": 0.03, "b": 0.2, "c": 0.3, "d": 0.4, "e": 0.5})
        assert out["a"] is False

    def test_the_minimum_cluster_guard_is_set(self):
        assert MIN_SYMBOLS >= 10
