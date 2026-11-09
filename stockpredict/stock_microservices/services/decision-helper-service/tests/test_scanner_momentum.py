"""FR-SCAN-MOM — multi-horizon momentum and its cross-sectional ranking."""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.scanner.momentum import (
    DEFAULT_HORIZONS,
    MomentumProfile,
    MomentumRank,
    horizon_return,
    profile_momentum,
    order_key,
    rank_cross_section,
    _percentiles,
)
from app.services.signal.base import OHLCVBar


def bars_from(closes: Sequence[float], start: date = date(2024, 1, 1)) -> List[OHLCVBar]:
    return [
        OHLCVBar(date=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1_000)
        for i, c in enumerate(closes)
    ]


# ---------------------------------------------------------------------------
# horizon_return
# ---------------------------------------------------------------------------

def test_horizon_return_is_measured_over_bars_not_positions():
    # 11 bars; a 10-bar lookback compares the last close to the FIRST.
    b = bars_from([100.0] + [0.0] * 9 + [150.0])
    b = bars_from([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 150])
    assert horizon_return(b, 10) == pytest.approx(50.0)


def test_horizon_return_needs_lookback_plus_one_bars():
    b = bars_from([100, 110, 120])
    assert horizon_return(b, 2) == pytest.approx(20.0)
    assert horizon_return(b, 3) is None, "a 3-bar lookback needs 4 bars, not 3"


def test_non_positive_reference_close_yields_none_not_a_huge_return():
    """A zero reference would manufacture an enormous return that would then
    sit at the TOP of the ranking — the worst place for a data fault to land."""
    b = bars_from([0.0, 10.0, 20.0])
    assert horizon_return(b, 2) is None


def test_zero_or_negative_lookback_is_a_programming_error():
    with pytest.raises(ValueError):
        horizon_return(bars_from([1, 2, 3]), 0)


# ---------------------------------------------------------------------------
# profile_momentum
# ---------------------------------------------------------------------------

def test_profile_is_incomplete_when_any_horizon_is_short():
    b = bars_from(list(range(1, 80)))          # 79 bars: 21 and 63 fit, 126 does not
    p = profile_momentum("X", b, DEFAULT_HORIZONS)
    assert p.returns[21] is not None and p.returns[63] is not None
    assert p.returns[126] is None
    assert p.complete is False


# ---------------------------------------------------------------------------
# percentiles
# ---------------------------------------------------------------------------

def test_percentile_spans_zero_to_one_strongest_last():
    pct = _percentiles({"A": 1.0, "B": 2.0, "C": 3.0})
    assert pct["A"] == pytest.approx(0.0)
    assert pct["B"] == pytest.approx(0.5)
    assert pct["C"] == pytest.approx(1.0)


def test_ties_share_the_average_rank():
    """Identical returns MUST score identically, or the composite would order
    them by whatever the sort happened to do and determinism would be luck."""
    pct = _percentiles({"A": 5.0, "B": 5.0, "C": 9.0})
    assert pct["A"] == pct["B"] == pytest.approx(0.25)
    assert pct["C"] == pytest.approx(1.0)


def test_single_symbol_universe_scores_neutral_not_strongest():
    assert _percentiles({"ONLY": 42.0}) == {"ONLY": 0.5}


# ---------------------------------------------------------------------------
# rank_cross_section
# ---------------------------------------------------------------------------

def _profile(sym: str, r21: float, r63: float, r126: float) -> MomentumProfile:
    return MomentumProfile(sym, {21: r21, 63: r63, 126: r126}, 300, True)


def test_ranking_is_strongest_first_and_carries_the_population_size():
    ranked = rank_cross_section([
        _profile("LOW", 1, 1, 1),
        _profile("MID", 5, 5, 5),
        _profile("TOP", 9, 9, 9),
    ])
    assert [r.symbol for r in ranked] == ["TOP", "MID", "LOW"]
    assert all(r.ranked_universe == 3 for r in ranked)


def test_the_composite_ranks_percentiles_so_a_wide_horizon_cannot_dominate():
    """THE POINT OF THE DESIGN. WIDE is best on the 126-bar horizon by a huge
    raw margin but worst on the other two. A mean of RAW returns would crown it
    (300+1+1)/3 = 100.7 against TIGHT's 10; ranking percentiles first puts it
    below, because it wins one horizon of three."""
    ranked = rank_cross_section([
        _profile("WIDE", 1.0, 1.0, 300.0),
        _profile("TIGHT", 10.0, 10.0, 10.0),
        _profile("MID", 5.0, 5.0, 50.0),
    ])
    assert [r.symbol for r in ranked] == ["TIGHT", "MID", "WIDE"]
    assert sum(_profile("WIDE", 1.0, 1.0, 300.0).returns.values()) / 3 > 10.0


def test_weights_shift_the_order_in_the_direction_they_name():
    profiles = [
        _profile("SHORT_TERM", 9.0, 1.0, 1.0),
        _profile("LONG_TERM", 1.0, 1.0, 9.0),
    ]
    fast = rank_cross_section(profiles, {21: 10.0, 63: 1.0, 126: 1.0})
    slow = rank_cross_section(profiles, {21: 1.0, 63: 1.0, 126: 10.0})
    assert fast[0].symbol == "SHORT_TERM"
    assert slow[0].symbol == "LONG_TERM"


def test_incomplete_profiles_are_dropped_and_do_not_inflate_the_population():
    ranked = rank_cross_section([
        _profile("OK1", 1, 1, 1),
        _profile("OK2", 2, 2, 2),
        MomentumProfile("SHORT", {21: 5.0, 63: 5.0, 126: None}, 80, False),
    ])
    assert {r.symbol for r in ranked} == {"OK1", "OK2"}
    assert all(r.ranked_universe == 2 for r in ranked), \
        "ranked_universe must describe the population the percentiles were computed over"


def test_mixing_horizon_sets_is_refused_rather_than_silently_compared():
    with pytest.raises(ValueError, match="not comparable"):
        rank_cross_section([
            _profile("A", 1, 1, 1),
            MomentumProfile("B", {21: 1.0, 63: 1.0}, 300, True),
        ])


def test_a_missing_weight_is_refused():
    with pytest.raises(ValueError, match="no weight"):
        rank_cross_section([_profile("A", 1, 1, 1)], {21: 1.0})


def test_empty_universe_ranks_to_nothing():
    assert rank_cross_section([]) == []


def _rank(symbol: str, composite: float) -> MomentumRank:
    return MomentumRank(symbol, {21: 0.0}, {21: 0.0}, composite, 88)


def test_a_one_ulp_difference_cannot_reorder_the_ranking():
    """REGRESSION, from live data at 2024-03-31. DPG and VHC both scored
    0.74329501915708..., differing only in the last place. The funnel reading a
    TSV ranked DPG 8th; the same funnel reading the same bars as JSON over HTTP
    ranked VHC 8th. The candidate SET was identical; only the order moved.

    The two composites below are the REAL measured pair, and they are distinct
    floats — asserting that is the point, because an earlier version of this
    test used `1.0 + 1e-16`, which is exactly 1.0 in float64, so it passed
    without ever exercising the rounding."""
    dpg, vhc = 0.7432950191570881, 0.7432950191570882
    assert dpg != vhc, "the fixture must be two genuinely different floats"
    ordered = sorted([_rank("VHC", vhc), _rank("DPG", dpg)], key=order_key)
    assert [r.symbol for r in ordered] == ["DPG", "VHC"], \
        "float noise decided the order instead of the symbol"


def test_rounding_does_not_merge_genuinely_different_scores():
    """The tolerance must stay far below the finest real distinction a
    percentile can draw — 1/(n-1), about 0.0115 at n = 88."""
    ordered = sorted(
        [_rank("B", 0.50), _rank("A", 0.50 + 1.0 / 87), _rank("C", 0.50 - 1.0 / 87)],
        key=order_key,
    )
    assert [r.symbol for r in ordered] == ["A", "B", "C"]


def test_the_full_ranking_uses_the_same_key():
    ranked = rank_cross_section([
        _profile("A", 3.0, 3.0, 3.0),
        _profile("B", 2.0, 2.0, 2.0),
        _profile("C", 1.0, 1.0, 1.0),
    ])
    assert [r.symbol for r in ranked] == ["A", "B", "C"]
    assert len({r.composite for r in ranked}) == 3
