"""EM-2 / S2 — `H-S1`: the three-arm hit-rate study, and the BEFORE numbers.

`tests/baselines/em2_hitrate_touchcount.json` is the *before*-half of EM-2's
C4 benchmark: the forward hit rate of the **shipped** touch-count levels, and
of the matched-distance random null, captured while `_find_sr_levels` still
scores a level by ``len(cluster)``. Task `S4` changes that model; without these
recorded first, "volume-weighted levels are better" would be unfalsifiable.

That is the lesson EM-1 paid for, and the reason this task lands before `S4`
rather than after it.

The controls come first
-----------------------
A study that reports "no edge" is only worth reading if it could have detected
an edge that was there. `TestSensitivityControls` plants a level a synthetic
series genuinely bounces off and asserts the rule finds it, then marches price
straight through a level and asserts the rule calls it a penetration. Without
those two, a null result is indistinguishable from a broken harness — so they
are asserted here, not assumed.
"""
from __future__ import annotations

import functools
import json
import math
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from tests.sr_hitrate_harness import (
    ARMS,
    HORIZON,
    MAX_SYMBOLS,
    PROXIMITY_PCT,
    STEP,
    WINDOW,
    _classify,
    _null_levels,
    _shipped_levels,
    run_study,
    source_bars,
)

BASELINE_PATH = Path(__file__).parent / "baselines" / "em2_hitrate_touchcount.json"

#: True when the harness is running with the parameters the committed baseline
#: describes. Any override means the numbers are not comparable, so the
#: baseline guard steps aside rather than failing misleadingly.
DEFAULT_CONFIG = (
    int(os.environ.get("EM2_MAX_SYMBOLS", str(MAX_SYMBOLS))) == MAX_SYMBOLS
    and not os.environ.get("EM2_BARS_TSV")
)


@functools.lru_cache(maxsize=4)
def _study(max_symbols: int | None = None):
    """Cached — the study is cheap but not free, and several tests read it."""
    return run_study(max_symbols=max_symbols)


# ---------------------------------------------------------------------------
# Sensitivity controls — these gate the credibility of everything below
# ---------------------------------------------------------------------------

class TestSensitivityControls:
    """Can the outcome rule detect a level that is really there?"""

    @staticmethod
    def _bouncing(floor: float = 100.0, n: int = 60) -> pd.DataFrame:
        """A series that repeatedly falls to `floor` and bounces hard."""
        closes = []
        for cycle in range(n // 6):
            closes += [floor + 6, floor + 3, floor + 0.2,
                       floor + 3, floor + 6, floor + 8]
        return pd.DataFrame({
            "high": [c + 0.3 for c in closes],
            "low": [c - 0.3 for c in closes],
            "close": closes,
        })

    @staticmethod
    def _marching(level: float = 100.0, n: int = 40) -> pd.DataFrame:
        """A series that walks straight up through `level` and keeps going."""
        closes = [level - 4 + i * 0.6 for i in range(n)]
        return pd.DataFrame({
            "high": [c + 0.2 for c in closes],
            "low": [c - 0.2 for c in closes],
            "close": closes,
        })

    def test_a_planted_support_is_detected_as_a_reversal(self):
        """POSITIVE control. Price touches 100 and rebounds every cycle; a
        support level at 100 must read as a hit."""
        verdict = _classify(self._bouncing(), level_price=100.0, is_resistance=False)
        assert verdict == "hit"

    def test_a_level_price_marches_through_is_detected_as_a_penetration(self):
        """NEGATIVE control. A resistance in the path of a steady advance must
        read as a miss, not as a reversal."""
        verdict = _classify(self._marching(), level_price=100.0, is_resistance=True)
        assert verdict == "miss"

    def test_a_level_price_never_approaches_is_no_observation(self):
        """Not a hit and not a miss: an untested level must not enter the
        denominator at all, or the rate would reward levels for being far
        away and never challenged."""
        verdict = _classify(self._marching(), level_price=1_000.0, is_resistance=True)
        assert verdict is None

    def test_the_rule_is_not_biased_towards_hits(self):
        """The bias control, stated as a property.

        On a symbol with no S/R structure — a pure random walk — a symmetric
        rule must land near a coin flip. An earlier version of this harness
        required only that the bar's *high* reached the level, which left the
        reversal threshold up to 19x closer than the penetration threshold and
        pushed every arm into the 70s. This test is what would catch that
        again."""
        rng = np.random.default_rng(31337)
        hits = misses = 0
        for trial in range(400):
            steps = rng.normal(0.0, 0.015, size=80)
            close = 100.0 * np.exp(np.cumsum(steps))
            frame = pd.DataFrame({
                "high": close * 1.004,
                "low": close * 0.996,
                "close": close,
            })
            level = float(close[0])
            for is_res in (True, False):
                v = _classify(frame, level_price=level, is_resistance=is_res)
                if v == "hit":
                    hits += 1
                elif v == "miss":
                    misses += 1

        resolved = hits + misses
        assert resolved > 200, "control needs a usable sample"
        rate = hits / resolved
        se = math.sqrt(0.25 / resolved)
        assert abs(rate - 0.5) < 5 * se, (
            f"outcome rule is skewed on a structureless series: {rate:.3f} "
            f"(+/-{se:.3f}); both arms would be inflated and their difference "
            f"compressed"
        )


# ---------------------------------------------------------------------------
# Causality (C1) — the study's own discipline
# ---------------------------------------------------------------------------

class TestCausality:

    def test_levels_are_built_from_a_slice_not_the_whole_series(self):
        """C1, as Backlog #79 established it: appending future bars must not
        change the levels at a past test date. A harness that built levels on
        the full frame and then indexed into it would fail this."""
        from unittest.mock import MagicMock
        from app.services.analysis_service import AnalysisService

        bars, _ = source_bars()
        df = bars[sorted(bars)[0]]
        svc = AnalysisService(session=MagicMock())
        t = WINDOW + 40

        frame = df.iloc[t - WINDOW + 1: t + 1].reset_index(drop=True)
        before = [(lv.price, lv.type, lv.strength) for lv in _shipped_levels(svc, frame)]

        longer = df.iloc[t - WINDOW + 1: t + 200].reset_index(drop=True)
        truncated = longer.iloc[:WINDOW].reset_index(drop=True)
        after = [(lv.price, lv.type, lv.strength) for lv in _shipped_levels(svc, truncated)]

        assert before == after

    def test_the_outcome_window_never_includes_the_approach_bar(self):
        """The approach bar itself cannot decide its own outcome — otherwise a
        bar that closed 1% below a resistance would be scored a reversal by the
        very close that defined the approach."""
        frame = pd.DataFrame({
            "high": [100.5, 100.5, 100.5],
            "low": [99.5, 99.5, 99.5],
            "close": [100.0, 100.0, 100.0],
        })
        # Nothing moves, so nothing resolves: proof the approach bar is excluded.
        assert _classify(frame, 100.0, is_resistance=True) == "unresolved"


# ---------------------------------------------------------------------------
# The null arm's construction
# ---------------------------------------------------------------------------

class TestMatchedDistanceNull:

    def test_the_null_preserves_the_distance_distribution(self):
        """Arm 3 exists to hold the distance-from-spot confound fixed. If its
        distances did not match, a difference between arms could be nothing
        more than the null sitting further from price."""
        from unittest.mock import MagicMock
        from app.services.analysis_service import AnalysisService

        bars, _ = source_bars()
        df = bars[sorted(bars)[0]]
        svc = AnalysisService(session=MagicMock())
        frame = df.iloc[:WINDOW].reset_index(drop=True)
        spot = float(frame["close"].iloc[-1])

        real = _shipped_levels(svc, frame)
        assert real, "fixture produced no levels"
        nulls = _null_levels(real, spot, np.random.default_rng(1))

        real_d = sorted(abs(lv.price - spot) / spot for lv in real)
        null_d = sorted(abs(n["price"] - spot) / spot for n in nulls)
        assert len(null_d) == len(real_d)
        assert null_d == pytest.approx(real_d)

    def test_the_null_moves_the_locations(self):
        """Matched distance must not mean "the same level back again"."""
        from unittest.mock import MagicMock
        from app.services.analysis_service import AnalysisService

        bars, _ = source_bars()
        df = bars[sorted(bars)[0]]
        svc = AnalysisService(session=MagicMock())
        frame = df.iloc[:WINDOW].reset_index(drop=True)
        spot = float(frame["close"].iloc[-1])
        real = _shipped_levels(svc, frame)
        nulls = _null_levels(real, spot, np.random.default_rng(2))

        real_prices = {round(lv.price, 4) for lv in real}
        null_prices = {round(n["price"], 4) for n in nulls}
        assert null_prices - real_prices, "the null reproduced only real levels"

    def test_a_non_positive_null_price_is_dropped_not_clamped(self):
        """Clamping would pile null levels onto one price and give that price
        artificial weight in the rate."""
        from app.models.schemas import SRLevel, SRLevelType, SRTouch, SwingType

        lvl = SRLevel(
            price=0.5, type=SRLevelType.SUPPORT, strength=1, age_bars=0,
            touches=[SRTouch(bar_index=0, date="2026-01-01", price=0.5,
                             pivot_type=SwingType.LOW)],
        )
        # spot 1.0 with a level at 0.5 is a relative distance of 0.5; the
        # mirrored side sits at 1.5, the near side at 0.5 — both positive, so
        # force the degenerate case directly.
        out = _null_levels([lvl], spot=0.4, rng=np.random.default_rng(3))
        for n in out:
            assert n["price"] > 0


# ---------------------------------------------------------------------------
# Regeneration — not a test, but it lives here so there is one source of truth
# ---------------------------------------------------------------------------

def _regenerate() -> Dict[str, Any]:
    """Record the shipped and null arms under every source available."""
    sources: Dict[str, Any] = {}

    os.environ["EM2_FORCE_SYNTHETIC"] = "1"
    _study.cache_clear()
    syn = run_study()
    sources[syn.source_label] = syn.as_dict()
    del os.environ["EM2_FORCE_SYNTHETIC"]
    _study.cache_clear()

    real = run_study()
    if real.source_label != syn.source_label:
        sources[real.source_label] = real.as_dict()

    return {
        "_comment": (
            "EM-2 H-S1 before-numbers: the forward hit rate of the SHIPPED "
            "touch-count S/R levels and of the matched-distance random null, "
            "captured at task S2, before task S4 adds volume_strength. Do not "
            "edit by hand; regenerate with EM2_REGEN_BASELINE=1 pytest "
            "tests/test_sr_hitrate.py and say in the commit message why the "
            "numbers moved."
        ),
        "params": {
            "window": WINDOW,
            "step": STEP,
            "horizon": HORIZON,
            "proximity_pct": PROXIMITY_PCT,
            "max_symbols": MAX_SYMBOLS,
        },
        "sources": sources,
    }


@pytest.mark.skipif(
    not os.environ.get("EM2_REGEN_BASELINE"),
    reason="set EM2_REGEN_BASELINE=1 to rewrite the committed before-numbers",
)
def test_regenerate_baseline():
    payload = _regenerate()

    # The rail that matters, and the precedent EM-1's baseline guard set: this
    # file IS the before-measurement. Regenerating it once `_find_sr_levels`
    # populates volume_strength would overwrite the touch-count record with
    # post-S4 numbers and quietly destroy the C4 benchmark — the exact failure
    # this task exists to prevent.
    from unittest.mock import MagicMock
    from app.services.analysis_service import AnalysisService

    bars, _ = source_bars()
    svc = AnalysisService(session=MagicMock())
    frame = bars[sorted(bars)[0]].iloc[:WINDOW].reset_index(drop=True)
    for lvl in _shipped_levels(svc, frame):
        assert getattr(lvl, "volume_strength", None) is None, (
            "_find_sr_levels already populates volume_strength, so the shipped "
            "arm is no longer the touch-count model. This file is the "
            "BEFORE-numbers of EM-2's C4 benchmark; regenerating it now would "
            "overwrite them. Revert the model first, or edit deliberately and "
            "say why in the commit message."
        )

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"\nrewrote {BASELINE_PATH}")


# ---------------------------------------------------------------------------
# The before-numbers
# ---------------------------------------------------------------------------

def _load_baseline() -> Dict[str, Any]:
    if not BASELINE_PATH.exists():
        pytest.fail(
            f"{BASELINE_PATH.name} is missing. Regenerate with "
            f"EM2_REGEN_BASELINE=1 pytest {Path(__file__).name}"
        )
    return json.loads(BASELINE_PATH.read_text())


@pytest.mark.skipif(not DEFAULT_CONFIG, reason="the baseline describes the committed params only")
class TestTouchCountBaseline:
    """The recorded numbers must still be reproducible.

    Not busywork: these are the figures `S4`'s claim is measured against, so a
    silent change in `_find_sr_levels` — a tolerance nudged, a pivot window
    altered — has to surface here rather than quietly moving the goalposts.
    """

    def test_the_current_source_is_described_by_the_baseline(self):
        baseline = _load_baseline()
        report = _study()
        assert report.source_label in baseline["sources"], (
            f"no committed numbers for source {report.source_label!r}; "
            f"have {sorted(baseline['sources'])}"
        )

    def test_shipped_and_null_arms_match_the_committed_numbers(self):
        baseline = _load_baseline()
        report = _study()
        want = baseline["sources"][report.source_label]["arms"]
        got = report.as_dict()["arms"]

        problems = []
        for arm in ("touch_count", "random_null"):
            for key in ("hit_rate", "hits", "misses", "levels_tested"):
                if got[arm][key] != want[arm][key]:
                    problems.append(
                        f"{arm}.{key}: baseline={want[arm][key]} now={got[arm][key]}"
                    )
        assert not problems, (
            "the before-numbers moved:\n  " + "\n  ".join(problems)
            + "\nIf this is a deliberate model change, S4 is where it belongs, "
              "and the baseline must not simply be regenerated to match."
        )

    def test_every_arm_is_reported(self):
        report = _study()
        assert set(report.arms) == set(ARMS)

    def test_the_source_is_labelled_not_assumed(self):
        """A study that silently substituted synthetic data for market data
        would overstate its own result."""
        report = _study()
        assert report.source_label.startswith(("real:", "synthetic"))


# ---------------------------------------------------------------------------
# The EM-2 arm — awaiting S4
# ---------------------------------------------------------------------------

def _z(a, b) -> float:
    """Two-proportion z for the difference between two arms' hit rates."""
    p1, n1 = a.hit_rate, a.hits + a.misses
    p2, n2 = b.hit_rate, b.hits + b.misses
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return (p1 - p2) / se if se else 0.0


class TestEM2Arm:

    def test_the_em2_arm_now_runs(self):
        """`S4` landed, so the arm must actually produce levels. Before it, the
        arm reported unavailable on purpose — a fallback to the shipped levels
        would have made the comparison vacuous while looking like it passed."""
        arm = _study().arms["em2_volume"]
        assert arm.available, arm.reason
        assert arm.levels_tested > 0

    def test_the_em2_arm_differs_from_the_shipped_arm(self):
        """Guards against the arm quietly collapsing back into arm 1 — which
        is what happens if it only re-*orders* levels, since every level in an
        arm gets tested either way."""
        report = _study()
        em2 = report.arms["em2_volume"]
        shipped = report.arms["touch_count"]
        assert em2.levels_tested != shipped.levels_tested

    def test_the_matched_selectivity_control_is_reported(self):
        """The EM-2 arm keeps the stronger half of its levels, so it is scored
        on a subset. Without an arm that keeps the stronger half *by touch
        count*, any difference could be "fewer levels, better average" rather
        than "better selection" — the plan's W1 warning in general form."""
        arm = _study().arms["touch_count_matched"]
        assert arm.available
        assert arm.levels_tested < _study().arms["touch_count"].levels_tested

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "MEASURED AT S4, AT TWO SAMPLE SIZES, AND NOT PROVEN. At the "
            "committed 12-symbol config the EM-2 arm looked promising: 56.3% "
            "vs the null's 55.4% (+0.88pp) and +2.26pp over the "
            "matched-selectivity control. Re-run at 32 symbols / step 5 — "
            "5.4x the sample — it inverts: 54.9% vs the null's 54.4% "
            "(+0.54pp, z=+0.97) and 0.84pp BELOW the matched control "
            "(z=-1.34). The small-sample edge was noise. Nothing here is "
            "significant in either direction, and CLAUDE.md's C4 admits an "
            "improvement only on significance, so this stays red. S5-S7 add "
            "role reversal, attack count and decay; if one clears the bar "
            "this turns XPASS(strict) and forces the marker off. Do NOT relax "
            "the threshold, and do not quote the 12-symbol numbers as "
            "evidence."
        ),
    )
    def test_em2_levels_beat_both_the_shipped_arm_and_the_null_with_significance(self):
        """`H-S1`'s acceptance test: a method improves only if it beats BOTH,
        and only if the margin is real.

        The before-numbers made the bar explicit and it was not where one
        might assume — the random null scores at least as well as the shipped
        touch-count levels, so "better than shipped" is evidence of nothing.
        EM-2 has to clear the null, with significance.
        """
        report = _study()
        em2 = report.arms["em2_volume"]
        null = report.arms["random_null"]
        matched = report.arms["touch_count_matched"]

        assert em2.available, em2.reason
        assert _z(em2, null) > 1.96, f"vs null: z={_z(em2, null):+.2f}"
        assert _z(em2, matched) > 1.96, f"vs matched: z={_z(em2, matched):+.2f}"
