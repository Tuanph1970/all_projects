"""Backlog #118 — chart patterns, graded against the random-walk null.

THIS IS THE PART OF THE NARRATOR MOST LIKELY TO MISLEAD, so it is the part most
constrained. `chart-decomp-service` detects eleven formations; measured on real
FPT bars it found six and NOT ONE was noteworthy -- Head & Shoulders scored at
the 6.1st percentile of what the same detector produces on random walks.

"Head & Shoulders detected" on that evidence is a confident sentence with
nothing behind it. These tests exist to make that sentence impossible.
"""
from __future__ import annotations

import pytest

from app.services.narrative import (
    NOTEWORTHY_PERCENTILE,
    PATTERN_DIRECTION,
    chart_pattern_findings,
    pattern_direction,
)


def _det(pattern, *, end_index=300, score=0.6, pct=50.0, noteworthy=False, bias=None):
    return {
        "pattern": pattern, "end_index": end_index, "score": score,
        "null_percentile": pct, "noteworthy": noteworthy,
        "directional_bias": bias, "start_index": max(0, end_index - 40),
    }


def _codes(fs):
    return [f.code for f in fs]


def _one(fs, code):
    hits = [f for f in fs if f.code == code]
    assert hits, f"{code} not in {_codes(fs)}"
    return hits[0]


# ---------------------------------------------------------------------------
# The central rule: an unremarkable shape is never a signal
# ---------------------------------------------------------------------------

def test_the_real_fpt_reading_does_not_announce_a_head_and_shoulders():
    """The measured case, with the service's own numbers.

    Six detections on FPT, none noteworthy, Head & Shoulders at the 6.1st
    percentile. The output must be ONE "no stronger than chance" finding -- not
    a list of five formations that reads like five signals.
    """
    dets = [
        _det("Bear Flag", end_index=195, score=0.597, pct=13.2),
        _det("Descending Triangle", end_index=244, score=0.207, pct=24.0),
        _det("Head & Shoulders", end_index=348, score=0.550, pct=6.1),
        _det("Inverse Head & Shoulders", end_index=244, score=0.778, pct=77.9),
        _det("Double Top", end_index=267, score=0.634, pct=38.6),
    ]
    rates = {"Head & Shoulders": 0.49, "Inverse Head & Shoulders": 0.497,
             "Double Top": 0.277, "Bear Flag": 0.367, "Descending Triangle": 1.25}
    # 454 bars is what the live FPT call actually sent, and a 180-bar display
    # window is the shipped default -- so the recency cutoff is index 274 and
    # the Bear Flag (195) and Descending Triangle (244) fall outside it. Using
    # bars_total=354 here, as the first version of this test did, silently
    # moved the cutoff and left only ONE detection in scope, which made the
    # "best of a bad bunch" assertion test nothing.
    out = chart_pattern_findings(dets, rates, bars_total=454, recent_bars=180)

    assert "narrative.pattern.noteworthy" not in _codes(out), (
        "an unremarkable shape was promoted to a signal")
    f = _one(out, "narrative.pattern.not_noteworthy")
    assert f.severity == "info", "a chance-level shape must not carry a direction"
    # The best of a bad bunch is named with its percentile, so the reader can
    # see HOW far short it fell rather than just being told it fell short.
    # ARITHMETIC, stated because I got it wrong first: 454 bars with a 180-bar
    # display puts the cutoff at index 274, so of the six real detections only
    # the Head & Shoulders at 348 is on the chart. The others end at 195, 244,
    # 244 and 267 -- all scrolled off.
    #
    # Which makes this the sharpest form of the rule: the ONE formation an FPT
    # reader can actually see is a Head & Shoulders, the most famous reversal
    # pattern there is, and it scores at the 6.1st percentile of what the same
    # detector finds in random noise. It must not be announced.
    assert f.params["count"] == 1, f.params
    assert f.params["best_name"] == "Head & Shoulders"
    assert f.params["best_percentile"] == 6.1
    assert f.params["expected_in_noise"] == 0.49
    assert "Bear Flag" not in f.params["names"], "an out-of-view formation was narrated"


def test_the_strongest_of_several_in_view_is_the_one_named():
    """The "best of a bad bunch" branch, with every detection inside the window
    so the selection is actually exercised rather than being a sample of one."""
    dets = [
        _det("Head & Shoulders", end_index=348, score=0.550, pct=6.1),
        _det("Double Top", end_index=340, score=0.634, pct=38.6),
        _det("Inverse Head & Shoulders", end_index=330, score=0.778, pct=77.9),
    ]
    out = chart_pattern_findings(dets, {"Inverse Head & Shoulders": 0.497},
                                 bars_total=354, recent_bars=180)
    f = _one(out, "narrative.pattern.not_noteworthy")
    assert f.params["count"] == 3
    assert f.params["best_name"] == "Inverse Head & Shoulders"
    assert f.params["best_percentile"] == 77.9
    assert f.params["expected_in_noise"] == 0.5
    assert f.params["threshold"] == NOTEWORTHY_PERCENTILE


def test_a_noteworthy_pattern_is_narrated_with_its_direction():
    """Non-vacuity for the test above: the gate must not suppress everything."""
    out = chart_pattern_findings(
        [_det("Inverse Head & Shoulders", end_index=350, score=0.91,
              pct=98.4, noteworthy=True)],
        {"Inverse Head & Shoulders": 0.497}, bars_total=354)
    f = _one(out, "narrative.pattern.noteworthy")
    assert f.severity == "bullish"
    assert f.params["percentile"] == 98.4
    assert f.params["expected_in_noise"] == 0.5


def test_the_expected_in_noise_rate_is_reported_because_it_is_a_rate():
    """`fpr_by_pattern` is detections PER random-walk series, not a probability.

    Measured at 1.25 for Descending Triangle -- an average coin-flip chart of
    this length contains more than one. A reader told only "triangle detected"
    cannot know that; told the rate, they can.
    """
    out = chart_pattern_findings(
        [_det("Descending Triangle", end_index=350, pct=30.0)],
        {"Descending Triangle": 1.2533}, bars_total=354)
    f = _one(out, "narrative.pattern.not_noteworthy")
    assert f.params["expected_in_noise"] == 1.25


def test_a_mixed_bag_separates_the_signal_from_the_noise():
    out = chart_pattern_findings([
        _det("Double Bottom", end_index=350, score=0.95, pct=97.0, noteworthy=True),
        _det("Bear Flag", end_index=340, score=0.4, pct=20.0, noteworthy=False),
        _det("Symmetric Triangle", end_index=345, score=0.3, pct=10.0, noteworthy=False),
    ], {}, bars_total=354)
    assert _one(out, "narrative.pattern.noteworthy").severity == "bullish"
    nn = _one(out, "narrative.pattern.not_noteworthy")
    assert nn.params["count"] == 2
    assert "Bear Flag" in nn.params["names"] and "Symmetric Triangle" in nn.params["names"]
    assert "Double Bottom" not in nn.params["names"], "a signal was also listed as noise"


# ---------------------------------------------------------------------------
# Missing benchmark: unmeasured, not promoted
# ---------------------------------------------------------------------------

def test_without_the_null_benchmark_patterns_are_unvalidated_not_signals():
    """`noteworthy=None` means the benchmark did not run.

    The tempting fallback is to show the shapes anyway and let the user judge.
    That silently promotes them: a formation on screen beside real indicator
    readings IS a signal to most readers.
    """
    out = chart_pattern_findings(
        [_det("Head & Shoulders", end_index=350, noteworthy=None)], {}, bars_total=354)
    f = _one(out, "narrative.pattern.unvalidated")
    assert f.severity == "warning"
    assert "Head & Shoulders" in f.params["names"]
    assert "narrative.pattern.noteworthy" not in _codes(out)


def test_an_empty_detection_list_says_nothing_was_found():
    assert _codes(chart_pattern_findings([], {}, bars_total=300)) == ["narrative.pattern.none"]


@pytest.mark.parametrize("junk", [None, [None, 3, "x"]])
def test_malformed_payloads_do_not_raise(junk):
    out = chart_pattern_findings(junk, {}, bars_total=300)
    assert out and all(hasattr(f, "code") for f in out)


# ---------------------------------------------------------------------------
# Recency: a formation from a year ago is not about today
# ---------------------------------------------------------------------------

def test_an_old_formation_is_not_narrated_beside_todays_reading():
    out = chart_pattern_findings(
        [_det("Head & Shoulders", end_index=50, score=0.99, pct=99.0, noteworthy=True)],
        {}, bars_total=400, recent_bars=60)
    assert _codes(out) == ["narrative.pattern.none_recent"]
    assert "narrative.pattern.noteworthy" not in _codes(out)


def test_the_same_formation_at_the_right_edge_IS_narrated():
    """Guards the guard: proves the suppression above is the recency window and
    not a broken detector path."""
    out = chart_pattern_findings(
        [_det("Head & Shoulders", end_index=395, score=0.99, pct=99.0, noteworthy=True)],
        {}, bars_total=400, recent_bars=60)
    f = _one(out, "narrative.pattern.noteworthy")
    assert f.params["bars_ago"] == 4


def test_bars_ago_counts_from_the_right_edge():
    out = chart_pattern_findings(
        [_det("Double Top", end_index=380, score=0.9, pct=99.0, noteworthy=True)],
        {}, bars_total=400)
    assert _one(out, "narrative.pattern.noteworthy").params["bars_ago"] == 19


# ---------------------------------------------------------------------------
# Direction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("Head & Shoulders", "bearish"),
    ("Inverse Head & Shoulders", "bullish"),
    ("Double Top", "bearish"),
    ("Double Bottom", "bullish"),
    ("Bear Flag", "bearish"),
    ("Bull Flag", "bullish"),
    ("Ascending Triangle", "bullish"),
    ("Descending Triangle", "bearish"),
])
def test_the_conventional_direction_of_each_formation(name, expected):
    assert pattern_direction(name) == expected


def test_a_symmetric_triangle_is_neutral_because_the_book_says_it_resolves_either_way():
    assert pattern_direction("Symmetric Triangle") == "info"


def test_the_services_own_bias_wins_over_our_mapping():
    """chart-decomp reports `directional_bias` at multi-scale. Where it speaks,
    it is the authority -- our table is the fallback, not an override."""
    assert pattern_direction("Head & Shoulders", "bullish") == "bullish"
    assert pattern_direction("Double Bottom", "bearish") == "bearish"


def test_an_unknown_formation_is_neutral_rather_than_guessed():
    assert pattern_direction("Three Drives To A Teacup") == "info"


def test_every_mapped_direction_is_a_severity_the_finding_accepts():
    from app.services.narrative import SEVERITIES
    assert set(PATTERN_DIRECTION.values()) <= set(SEVERITIES)


def test_the_noteworthy_threshold_matches_the_detectors_own_default():
    """If chart-decomp changed `noteworthy_pct`, the number we PRINT would lie
    even though the flag stayed correct, because the flag comes from them and
    the threshold text comes from us."""
    assert NOTEWORTHY_PERCENTILE == 95.0
