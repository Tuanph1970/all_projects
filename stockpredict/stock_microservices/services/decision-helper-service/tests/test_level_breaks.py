"""EM-7 T1 — levels that remember being broken (`FR-EM-T1`).

E&M Ch 13 is the mechanism EM-7 is built on:

> **Pattern resistance** — *the mechanism explains the patterns*: a broken
> descending-triangle demand line becomes resistance; a broken H&S neckline
> becomes resistance; a rectangle's supply line becomes support once
> decisively exceeded.

So a level has a **role**, and breaking it **reverses** that role. The
alternation is the whole of the mechanic, and EM-2's `S5` already got it wrong
once in `analysis-service`: without alternation a *support* reads as "broken
upward" on every ordinary rally, which is meaningless and numerous enough to
swamp the real breaks. That bug was caught there only by building a genuinely
**quiet** fixture instead of trusting an oscillating one, so this file starts
with the quiet fixture too.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from datetime import date, timedelta
from typing import List, Optional, Sequence

import pytest

from app.services.backtest import market_features as mf
from app.services.backtest.market_features import (
    BREAK_ATR_MULTIPLE,
    atr_series,
    compute_sr_levels,
    detect_level_breaks,
    effective_level_type,
)
from app.services.signal.base import OHLCVBar

ANALYSIS_SERVICE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "analysis-service")


def _bars(closes: Sequence[float], pad: float = 0.5) -> List[OHLCVBar]:
    day = date(2020, 1, 1)
    out = []
    for c in closes:
        out.append(OHLCVBar(date=day, open=c, high=c + pad, low=c - pad,
                            close=c, volume=1_000_000))
        day += timedelta(days=1)
    return out


#: Price oscillates between ~98.8 and ~102.4 and so stays ENTIRELY ABOVE a
#: support at 97. It rallies away from that support repeatedly and never
#: closes decisively below it, so the correct answer is **zero** breaks.
#:
#: The level has to sit below the whole range for this to be the scenario at
#: all. The first draft of this fixture put the level at 100 — inside the
#: oscillation — where price genuinely does break down through it, so the test
#: failed against correct code. A quiet fixture has to be quiet *relative to
#: the level*, which is the detail EM-2's S5 fixture turned on.
QUIET_LEVEL = 97.0
QUIET_ABOVE = _bars([100.6 + 1.8 * math.sin(i / 3.0) for i in range(80)])


# ---------------------------------------------------------------------------
# H-T4 — the alternation, which is the point
# ---------------------------------------------------------------------------

class TestRoleAlternation:

    def test_a_support_price_merely_rallies_above_is_never_broken(self):
        """The EM-2 S5 bug, as a test. Zero, not 'a few'."""
        breaks = detect_level_breaks(QUIET_ABOVE, QUIET_LEVEL, role="support")
        assert breaks == []

    def test_the_fixture_would_catch_a_both_directions_rule(self):
        """Proof the test above can fail — the guard that makes it a guard.

        A rule that counted penetrations in EITHER direction (EM-2 S5's
        shipped bug) would fire on these rallies, because every close clears
        `QUIET_LEVEL` upward by far more than the band. Asserted here so the
        quiet fixture cannot quietly become vacuous.
        """
        series = atr_series(QUIET_ABOVE)
        fired = 0
        for i, bar in enumerate(QUIET_ABOVE):
            a = series[i]
            if a is None or a <= 0:
                continue
            if bar.close >= QUIET_LEVEL + a * BREAK_ATR_MULTIPLE:
                fired += 1
        assert fired > 20, (
            "the fixture no longer rallies clear of the level, so the "
            "alternation test above has stopped discriminating"
        )

    def test_a_support_closed_decisively_below_is_broken_once(self):
        bars = _bars([105.0] * 30 + [95.0] * 20)
        breaks = detect_level_breaks(bars, 100.0, role="support")
        assert len(breaks) == 1
        assert breaks[0]["direction"] == "down"

    def test_staying_beyond_records_one_break_and_not_one_per_bar(self):
        """Otherwise a level's history is a function of how long the frame is."""
        short = detect_level_breaks(_bars([105.0] * 30 + [95.0] * 5), 100.0, role="support")
        long = detect_level_breaks(_bars([105.0] * 30 + [95.0] * 60), 100.0, role="support")
        assert len(short) == len(long) == 1

    def test_the_role_reverses_so_a_recovery_is_the_next_break(self):
        bars = _bars([105.0] * 30 + [95.0] * 20 + [106.0] * 20)
        breaks = detect_level_breaks(bars, 100.0, role="support")
        assert [b["direction"] for b in breaks] == ["down", "up"]

    def test_a_resistance_mirrors_it(self):
        bars = _bars([95.0] * 30 + [106.0] * 20 + [94.0] * 20)
        breaks = detect_level_breaks(bars, 100.0, role="resistance")
        assert [b["direction"] for b in breaks] == ["up", "down"]

    def test_an_oscillation_through_the_level_alternates_rather_than_repeats(self):
        bars = _bars([105.0] * 20 + [95.0] * 20 + [105.0] * 20 + [95.0] * 20)
        dirs = [b["direction"] for b in detect_level_breaks(bars, 100.0, role="support")]
        assert dirs == ["down", "up", "down"]
        assert all(a != b for a, b in zip(dirs, dirs[1:])), "directions must alternate"


# ---------------------------------------------------------------------------
# the effective type
# ---------------------------------------------------------------------------

class TestEffectiveType:

    def test_broken_downward_the_level_now_acts_as_resistance(self):
        assert effective_level_type("support", [{"direction": "down", "bar_index": 5}]) == "resistance"

    def test_broken_upward_the_level_now_acts_as_support(self):
        assert effective_level_type("resistance", [{"direction": "up", "bar_index": 5}]) == "support"

    def test_the_most_recent_break_decides(self):
        hist = [{"direction": "down", "bar_index": 5}, {"direction": "up", "bar_index": 9}]
        assert effective_level_type("support", hist) == "support"

    def test_with_no_breaks_the_declared_type_stands(self):
        assert effective_level_type("support", []) == "support"
        assert effective_level_type("resistance", []) == "resistance"


# ---------------------------------------------------------------------------
# H-T1 causality
# ---------------------------------------------------------------------------

class TestCausality:

    def test_appending_future_bars_moves_no_past_break(self):
        bars = _bars([105.0] * 30 + [95.0] * 20)
        before = detect_level_breaks(bars, 100.0, role="support")
        after = detect_level_breaks(bars + _bars([110.0] * 25), 100.0, role="support")
        assert after[:len(before)] == before

    @pytest.mark.parametrize("cut", [40, 45, 50])
    def test_a_truncated_frame_matches_the_prefix(self, cut):
        bars = _bars([105.0] * 30 + [95.0] * 20 + [106.0] * 20)
        full = detect_level_breaks(bars, 100.0, role="support")
        part = detect_level_breaks(bars[:cut], 100.0, role="support")
        assert part == [b for b in full if b["bar_index"] < cut]

    def test_the_atr_series_never_reads_forward(self):
        bars = _bars([100.0 + i * 0.3 for i in range(60)])
        full = atr_series(bars)
        part = atr_series(bars[:40])
        assert part == pytest.approx([v for v in full[:40]], nan_ok=True)


# ---------------------------------------------------------------------------
# thin and degenerate data
# ---------------------------------------------------------------------------

class TestThinData:

    def test_a_frame_too_short_for_an_atr_reports_no_breaks(self):
        """A zero or NaN ATR would make every crossing look infinitely
        decisive, so the band must be unavailable rather than zero."""
        assert detect_level_breaks(_bars([105.0] * 5 + [95.0] * 3), 100.0,
                                   role="support") == []

    def test_a_non_positive_level_reports_no_breaks(self):
        assert detect_level_breaks(_bars([105.0] * 40), 0.0, role="support") == []
        assert detect_level_breaks(_bars([105.0] * 40), -3.0, role="support") == []

    def test_an_empty_frame_is_inert(self):
        assert detect_level_breaks([], 100.0, role="support") == []
        assert atr_series([]) == []

    def test_a_flat_series_has_a_zero_band_and_so_no_breaks(self):
        """Zero ATR must disable the band, not divide by it."""
        assert detect_level_breaks(_bars([100.0] * 60, pad=0.0), 100.0,
                                   role="support") == []


# ---------------------------------------------------------------------------
# H-T7 — the bound-default guard
# ---------------------------------------------------------------------------

class TestTheBreakThreshold:

    def test_the_multiple_is_read_at_call_time_not_frozen_at_import(self, monkeypatch):
        """Eighth instance of this trap in the project."""
        bars = _bars([105.0] * 30 + [99.0] * 20)
        assert detect_level_breaks(bars, 100.0, role="support") != []
        monkeypatch.setattr(mf, "BREAK_ATR_MULTIPLE", 20.0)
        assert detect_level_breaks(bars, 100.0, role="support") == [], (
            "BREAK_ATR_MULTIPLE is not being read at call time"
        )

    def test_the_default_matches_the_shipped_service(self):
        assert BREAK_ATR_MULTIPLE == 0.5


# ---------------------------------------------------------------------------
# compute_sr_levels stays additive
# ---------------------------------------------------------------------------

class TestComputeSrLevelsIsAdditive:

    def test_the_existing_shape_is_unchanged(self):
        bars = _bars([100.0 + 6 * math.sin(i / 5.0) for i in range(120)])
        out = compute_sr_levels(bars)
        assert set(out) >= {"supports", "resistances"}
        for lvl in out["supports"] + out["resistances"]:
            assert "price" in lvl and "strength" in lvl

    def test_each_level_now_carries_its_break_history(self):
        bars = _bars([100.0 + 6 * math.sin(i / 5.0) for i in range(120)])
        for lvl in compute_sr_levels(bars)["supports"]:
            assert "breaks" in lvl
            assert lvl["effective_type"] in ("support", "resistance")
            assert ("broken_at" in lvl) == bool(lvl["breaks"])


# ---------------------------------------------------------------------------
# H-T8 — the replica must agree with the shipped service
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.isdir(ANALYSIS_SERVICE),
                    reason="analysis-service not present")
class TestReplicaAgreesWithAnalysisService:
    """Two implementations of one rule are tolerated only because the harness
    cannot make per-bar HTTP calls. So the agreement is asserted, not hoped
    for — EM-6 D1 found a study's private copy of the swing rule wrong on 906
    of 5,672 bars, and that is the failure mode this guards.

    The SAME ATR series is handed to both, so this isolates the break and
    alternation logic from any difference in ATR formulation.
    """

    def _reference(self, bars, level_price, role, atr):
        job = {
            "service_path": ANALYSIS_SERVICE,
            "bars": [{"date": str(b.date), "open": b.open, "high": b.high,
                      "low": b.low, "close": b.close, "volume": b.volume}
                     for b in bars],
            "atr": [None if v is None or math.isnan(v) else v for v in atr],
            "level_price": level_price,
            "first_bar": 0,
            "declared_type": role,
        }
        helper = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "em7_reference_breaks.py")
        proc = subprocess.run([sys.executable, helper], input=json.dumps(job),
                              capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            pytest.skip(f"reference helper unavailable: {proc.stderr[-300:]}")
        return json.loads(proc.stdout)

    @pytest.mark.parametrize("closes,role", [
        ([105.0] * 30 + [95.0] * 20, "support"),
        ([105.0] * 30 + [95.0] * 20 + [106.0] * 20, "support"),
        ([95.0] * 30 + [106.0] * 20 + [94.0] * 20, "resistance"),
        ([100.6 + 1.8 * math.sin(i / 3.0) for i in range(80)], "support"),
    ])
    def test_the_break_lists_are_identical(self, closes, role):
        bars = _bars(closes)
        atr = atr_series(bars)
        mine = [{"direction": b["direction"], "bar_index": b["bar_index"]}
                for b in detect_level_breaks(bars, 100.0, role=role, atr=atr)]
        theirs = self._reference(bars, 100.0, role, atr)
        assert mine == theirs

    def test_the_quiet_fixture_agrees_too(self):
        """The case that matters most: both must say zero."""
        atr = atr_series(QUIET_ABOVE)
        mine = detect_level_breaks(QUIET_ABOVE, QUIET_LEVEL, role="support", atr=atr)
        theirs = self._reference(QUIET_ABOVE, QUIET_LEVEL, "support", atr)
        assert mine == [] and theirs == []
