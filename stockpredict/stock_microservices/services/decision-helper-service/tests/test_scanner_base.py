"""S-2 — FR-SCAN-BASE / SQUEEZE / MA / LEVEL, plus VT-3 and VT-4.

VT-3 (planted pattern) and VT-4 (null false-positive rate) are the phase's exit
criteria. VT-4 in particular is not a diagnostic: C4 and EC-S5 require the null
rate to be reported beside every candidate list, because a funnel that fires as
often on noise as on data has no content however plausible its output reads.
"""
from __future__ import annotations

import math
import random
from dataclasses import replace
from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.scanner.base import (
    DEFAULT_BASE_MAX_BARS,
    SHAPE_FLAG,
    SHAPE_FLAT,
    MAProximity,
    SqueezeMetrics,
    assess_base,
    detect_flag_base,
    detect_base,
    find_pivot,
    measure_ma_proximity,
    measure_squeeze,
    true_ranges,
)
from app.services.scanner.null_model import (
    VN_DAILY_LOG_SD,
    estimate_null_fpr,
    random_walk,
)
from app.services.scanner.screen import ScanConfig, run_scan
from app.services.signal.base import OHLCVBar

START = date(2022, 1, 3)


def bar(i: int, close: float, *, half_range: float, volume: float) -> OHLCVBar:
    return OHLCVBar(
        date=START + timedelta(days=i),
        open=close, high=close + half_range, low=max(0.01, close - half_range),
        close=close, volume=volume,
    )


def advance_then_base(
    *,
    run_bars: int = 260,
    base_bars: int = 30,
    start: float = 20.0,
    run_step: float = 0.25,
    base_half_range_start: float = 1.2,
    base_half_range_end: float = 0.2,
    run_volume: float = 2_000_000,
    base_volume_start: float = 2_000_000,
    base_volume_end: float = 400_000,
    wobble: float = 0.0,
) -> List[OHLCVBar]:
    """A planted Qullamaggie setup: an advance, then a flat base whose range and
    volume contract toward the right edge.

    Both the range and the volume taper LINEARLY to their end values, which is
    what makes the last third measurably quieter than the first — the thing
    FR-SCAN-SQUEEZE is defined to detect.
    """
    bars: List[OHLCVBar] = []
    price = start
    for i in range(run_bars):
        price = start + run_step * i
        bars.append(bar(i, price, half_range=price * 0.02, volume=run_volume))

    top = price
    for j in range(base_bars):
        frac = j / max(1, base_bars - 1)
        hr = base_half_range_start + (base_half_range_end - base_half_range_start) * frac
        vol = base_volume_start + (base_volume_end - base_volume_start) * frac
        drift = wobble * math.sin(j * 1.3)
        bars.append(bar(run_bars + j, top + drift, half_range=hr, volume=vol))
    return bars


# ---------------------------------------------------------------------------
# true_ranges
# ---------------------------------------------------------------------------

def test_first_bar_has_no_true_range():
    tr = true_ranges([bar(0, 10, half_range=1, volume=1), bar(1, 11, half_range=1, volume=1)])
    assert tr[0] is None and tr[1] is not None


def test_true_range_spans_the_gap_to_the_previous_close():
    b = [bar(0, 10, half_range=0.1, volume=1), bar(1, 20, half_range=0.1, volume=1)]
    assert true_ranges(b)[1] == pytest.approx(20.1 - 10)


# ---------------------------------------------------------------------------
# FR-SCAN-BASE
# ---------------------------------------------------------------------------

def test_a_planted_base_is_found_with_the_right_boundaries():
    """VT-3's core assertion: the boundary recovered must be the planted one,
    not whatever the thresholds happen to allow."""
    bars = advance_then_base(run_bars=260, base_bars=30)
    w = detect_base(bars)
    assert w is not None
    assert w.end_index == len(bars) - 1, "a base that ended last month is history, not a setup"
    assert abs(w.start_index - 260) <= 2, f"base start {w.start_index}, planted at 260"
    assert abs(w.length - 30) <= 2, f"found {w.length} bars of a 30-bar base"
    assert w.depth_pct < 25.0


def test_the_boundary_is_chosen_by_flatness_not_by_the_threshold():
    """THE REGRESSION THIS FILE EXISTS TO HOLD. Greedy longest-admissible
    returned 43 bars at drift/depth 0.49 — 13 bars of the preceding advance,
    stopped by the 0.50 cap rather than by the data, and three unrelated fixture
    shapes all produced exactly that. A window chosen by flatness sits far below
    the cap because the planted base really is flat."""
    for base_bars in (20, 30, 45):
        w = detect_base(advance_then_base(base_bars=base_bars))
        assert w is not None
        assert w.drift_over_depth < 0.2, \
            f"{base_bars}-bar fixture chose a window at the cap ({w.drift_over_depth:.2f})"
        assert abs(w.length - base_bars) <= 2


def test_a_longer_window_wins_only_when_flatness_ties():
    """Inside a perfectly flat stretch every window scores 0, so the tie-break
    decides — and it must prefer the longer base, which has absorbed more supply."""
    bars = [bar(i, 50.0, half_range=0.5, volume=1_000_000) for i in range(300)]
    w = detect_base(bars, min_bars=10, max_bars=40)
    assert w is not None and w.length == 40


def test_a_stock_still_running_has_no_base():
    """What rejects an extended name — the drift limit, not a separate test."""
    bars = advance_then_base(run_bars=300, base_bars=0) if False else [
        bar(i, 20.0 + 0.5 * i, half_range=0.4, volume=1_000_000) for i in range(300)
    ]
    # 60 bars of a 0.5/bar ramp from ~130 is a +23% drift — over the 15% limit.
    assert detect_base(bars) is None


def test_a_deep_drawdown_is_not_a_base():
    bars = [bar(i, 100.0, half_range=0.5, volume=1_000_000) for i in range(260)]
    bars += [bar(260 + j, 100.0 - 1.4 * j, half_range=0.5, volume=1_000_000) for j in range(30)]
    w = detect_base(bars)
    assert w is None or w.length < 25, "a 40% slide is a correction, not a consolidation"


def test_drift_is_symmetric_because_both_directions_disqualify():
    up = [bar(i, 100.0 + 0.9 * i, half_range=0.3, volume=1_000_000) for i in range(40)]
    down = [bar(i, 100.0 - 0.9 * i, half_range=0.3, volume=1_000_000) for i in range(40)]
    assert detect_base(up, min_bars=30, max_bars=40) is None
    assert detect_base(down, min_bars=30, max_bars=40) is None


def test_a_base_shorter_than_three_bars_is_refused():
    with pytest.raises(ValueError, match="at least 3"):
        detect_base(advance_then_base(), min_bars=2)


def test_max_below_min_is_refused():
    with pytest.raises(ValueError, match="below min_bars"):
        detect_base(advance_then_base(), min_bars=20, max_bars=10)


# ---------------------------------------------------------------------------
# FR-SCAN-SQUEEZE
# ---------------------------------------------------------------------------

def test_the_squeeze_reports_ratios_not_just_booleans():
    bars = advance_then_base()
    w = detect_base(bars)
    s = measure_squeeze(bars, w)
    assert s.range_ratio is not None and s.volume_ratio is not None
    assert s.range_ratio < 1.0, "a tapering base must read as contraction"
    assert s.volume_ratio < 1.0, "a tapering base must read as dry-up"
    assert s.first_third_tr and s.last_third_tr and s.base_mean_volume


def test_a_constant_range_base_reads_as_no_contraction():
    """A flat, quiet stretch is not a squeeze. The ratio must sit at 1.0."""
    bars = [bar(i, 50.0, half_range=0.5, volume=1_000_000) for i in range(300)]
    w = detect_base(bars)
    s = measure_squeeze(bars, w)
    assert s.range_ratio == pytest.approx(1.0, abs=0.02)
    assert s.volume_ratio == pytest.approx(1.0, abs=0.02)


def test_an_expanding_base_reads_above_one():
    bars = advance_then_base(base_half_range_start=0.2, base_half_range_end=1.2,
                             base_volume_start=400_000, base_volume_end=2_000_000)
    w = detect_base(bars)
    s = measure_squeeze(bars, w)
    assert s.range_ratio > 1.0 and s.volume_ratio > 1.0


# ---------------------------------------------------------------------------
# FR-SCAN-MA
# ---------------------------------------------------------------------------

def test_moving_averages_hug_from_below_in_a_settled_base():
    m = measure_ma_proximity(advance_then_base())
    assert m.ma_fast is not None and m.ma_medium is not None
    assert m.hugging, (m.dist_fast_pct, m.dist_medium_pct)
    assert 0.0 <= m.dist_fast_pct <= 8.0


def test_a_stock_far_above_its_averages_is_not_hugging():
    """It takes an ACCELERATING move to pull price away from its MA10, which a
    failing test made obvious: on a LINEAR ramp the MA lags by a constant
    absolute amount, so as price rises the percentage gap shrinks. A 1.5/bar
    ramp reaching 468 sits 1.4% over its MA10 — textbook hugging. Only a
    blow-off opens a real gap."""
    bars = [bar(i, 20.0 * (1.012 ** i), half_range=0.3, volume=1_000_000) for i in range(300)]
    m = measure_ma_proximity(bars)
    assert not m.hugging
    assert m.dist_fast_pct > 0, "the MA is below price — just far below"


def test_an_average_above_price_is_not_hugging_either():
    bars = [bar(i, 200.0 - 0.5 * i, half_range=0.3, volume=1_000_000) for i in range(300)]
    m = measure_ma_proximity(bars)
    assert not m.hugging and m.dist_fast_pct < 0


# ---------------------------------------------------------------------------
# FR-SCAN-LEVEL
# ---------------------------------------------------------------------------

def test_the_pivot_is_the_base_high_and_sits_at_or_above_price():
    bars = advance_then_base(wobble=0.6)
    w = detect_base(bars)
    p = find_pivot(bars, w)
    assert p.level == pytest.approx(w.high)
    assert p.distance_pct >= 0.0
    assert p.distance_atr is None or p.distance_atr >= 0.0


def test_price_at_the_pivot_is_a_trigger_not_a_rejection():
    """A flat base leaves price just under its own high — a small positive
    distance, never a rejection. The tolerance is 3% rather than the base's own
    half-range because the recovered window may include one bar of the preceding
    advance, whose high is the widest in the window."""
    bars = advance_then_base(wobble=0.0)
    w = detect_base(bars)
    p = find_pivot(bars, w)
    assert 0.0 <= p.distance_pct < 3.0, f"pivot {p.distance_pct:.2f}% above close"


# ---------------------------------------------------------------------------
# VT-3 — the planted setup survives the whole funnel (MANDATORY)
# ---------------------------------------------------------------------------

def test_vt3_a_planted_setup_passes_every_clause():
    a = assess_base("PLANT", advance_then_base())
    assert a.passed, a.failed_clauses()
    assert a.window and a.squeeze and a.moving_averages and a.pivot
    assert len(a.clauses) == 4


def test_vt3_the_planted_setup_survives_the_full_scan():
    bars = advance_then_base()
    r = run_scan({"PLANT": bars}, bars[-1].date, ScanConfig())
    assert [c.symbol for c in r.candidates] == ["PLANT"], r.accounting()
    c = r.candidates[0]
    assert c.base is not None and c.base.passed
    assert c.base.pivot.level >= c.trend.close


def test_vt3_a_ramp_with_no_base_is_rejected_by_the_base_stage_not_the_trend_one():
    """The two stages must fail for different reasons, or one is redundant."""
    bars = [bar(i, 20.0 + 0.5 * i, half_range=0.4, volume=1_000_000) for i in range(400)]
    r = run_scan({"RAMP": bars}, bars[-1].date, ScanConfig())
    assert r.candidates == ()
    assert r.failed_trend == ()
    assert [b.symbol for b in r.failed_base] == ["RAMP"]


def test_vt3_every_symbol_still_accounts_for_with_the_base_stage_on():
    bars = advance_then_base()
    ramp = [bar(i, 20.0 + 0.5 * i, half_range=0.4, volume=1_000_000) for i in range(400)]
    r = run_scan({"PLANT": bars, "RAMP": ramp}, bars[-1].date, ScanConfig())
    acc = r.accounting()
    assert acc["accounted"] == acc["universe_total"] == 2


def test_require_base_false_reproduces_the_s1_funnel():
    """The two phases must stay comparable on the same data."""
    ramp = [bar(i, 20.0 + 0.5 * i, half_range=0.4, volume=1_000_000) for i in range(400)]
    s1 = run_scan({"RAMP": ramp}, ramp[-1].date, ScanConfig(require_base=False))
    assert [c.symbol for c in s1.candidates] == ["RAMP"]
    assert s1.candidates[0].base is None


# ---------------------------------------------------------------------------
# VT-4 — null false-positive rate (MANDATORY)
# ---------------------------------------------------------------------------

def test_random_walk_is_calibrated_to_vn_daily_volatility():
    rng = random.Random(1)
    bars = random_walk(rng, 4000)
    rets = [math.log(bars[i].close / bars[i - 1].close) for i in range(1, len(bars))]
    sd = (sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5
    assert sd == pytest.approx(VN_DAILY_LOG_SD, rel=0.15)


def test_random_walk_bars_are_not_degenerate():
    """high == low == close would hand the squeeze test a free pass."""
    bars = random_walk(random.Random(2), 200)
    assert all(b.high > b.low for b in bars)
    assert all(b.high >= b.close >= b.low for b in bars)


def test_vt4_the_null_fpr_is_measurable_and_reproducible():
    cfg = ScanConfig()
    a = estimate_null_fpr(run_scan, cfg, trials=4, universe_size=12, bars_per_symbol=320)
    b = estimate_null_fpr(run_scan, cfg, trials=4, universe_size=12, bars_per_symbol=320)
    assert a == b, "the reported null rate must be reproducible (NFR-S2)"
    assert 0.0 <= a.symbol_fpr <= 1.0 and 0.0 <= a.trial_fpr <= 1.0
    assert a.symbols_tested > 0, "the null universe must survive as far as the ranking"


def test_vt4_the_full_funnel_is_more_selective_against_noise_than_s1_alone():
    """The S-2 stages have to EARN their place: adding base, squeeze and MA
    proximity must cut the noise pass-rate, not merely rearrange it."""
    s1 = estimate_null_fpr(run_scan, ScanConfig(require_base=False),
                           trials=4, universe_size=12, bars_per_symbol=320)
    s2 = estimate_null_fpr(run_scan, ScanConfig(),
                           trials=4, universe_size=12, bars_per_symbol=320)
    assert s2.total_candidates <= s1.total_candidates


# ---------------------------------------------------------------------------
# FR-SCAN-BASE, flag shape — "lá cờ"
# ---------------------------------------------------------------------------

def pole_then_flag(
    *,
    run_bars: int = 260,
    pole_bars: int = 8,
    flag_bars: int = 4,
    start: float = 20.0,
    drift_step: float = 0.05,
    pole_step: float = 3.0,
    pullback_step: float = 0.4,
    bearish: bool = False,
) -> List[OHLCVBar]:
    """A planted bull flag: quiet drift, a SHARP pole, then a TIGHT pullback.

    THE DEFAULTS ARE CALIBRATED TO THE CASE THE FLAT-BASE TEST GENUINELY MISSES,
    which is narrower than it first appears. A 4-bar pullback of 0.4 against an
    8-bar pole of 3.0 retraces ~7%, so no window straddling the pole top and the
    pullback reads flat — the pole dominates any such window and drift/depth
    lands near 0.9. Make the pullback DEEPER (8 bars x 0.6, ~20% retrace) and
    `detect_base` finds a straddling 11-bar FLAT window on its own, which is why
    only 9% of real names fail `base_found` at all.

    `bearish=True` inverts the pole and the pullback to plant a bear flag, which
    this long-side funnel must refuse.
    """
    sign = -1.0 if bearish else 1.0
    bars: List[OHLCVBar] = []
    price = start
    for i in range(run_bars):
        price = start + drift_step * i
        bars.append(bar(i, price, half_range=price * 0.01, volume=1_000_000))
    for j in range(pole_bars):
        price += sign * pole_step
        bars.append(bar(run_bars + j, price, half_range=abs(pole_step) * 0.4,
                        volume=3_000_000))
    for k in range(flag_bars):
        price -= sign * pullback_step
        bars.append(bar(run_bars + pole_bars + k, price,
                        half_range=pullback_step * 0.5, volume=900_000))
    return bars


def test_a_planted_bull_flag_is_found():
    bars = pole_then_flag()
    assert detect_base(bars) is None, \
        "fixture invalid: the flat-base test must NOT already cover this"
    w = detect_flag_base(bars)
    assert w is not None
    assert w.shape == SHAPE_FLAG
    assert w.end_index == len(bars) - 1
    assert w.drift_pct < 0, "a bull flag finishes below where the pullback began"


def test_the_flag_is_why_drift_over_depth_cannot_gate_it():
    """The point of adding a second shape at all."""
    w = detect_flag_base(pole_then_flag())
    assert w.drift_over_depth > 0.5, \
        "if a flag scored under the flat-base gate, no second shape was needed"


def test_a_bear_flag_is_refused():
    """Long-side funnel: a bear flag is a real pattern and an irrelevant one,
    and admitting it would put falling stocks on a list headed 'candidates'."""
    assert detect_flag_base(pole_then_flag(bearish=True)) is None


def test_a_pole_too_small_against_atr_is_not_a_flag():
    assert detect_flag_base(pole_then_flag(pole_step=0.06)) is None


def test_a_pullback_deeper_than_half_the_pole_is_not_a_flag():
    # Pole 8 x 3.0 = 24; a 4 x 3.2 = 12.8 pullback retraces 53% of it.
    assert detect_flag_base(pole_then_flag(pullback_step=3.2)) is None


def test_a_deep_pullback_is_already_covered_by_the_flat_shape():
    """Why the flag only adds 9%: a deep enough pullback leaves a straddling
    window that reads flat on its own, so the flat shape was already finding it."""
    bars = pole_then_flag(flag_bars=8, pullback_step=0.6)
    flat = detect_base(bars)
    assert flat is not None and flat.shape == SHAPE_FLAT


def test_a_rising_pullback_is_not_a_flag():
    """Highs and lows must BOTH slope counter to the pole — a pullback that
    keeps making highs is the move continuing, not a pause in it."""
    assert detect_flag_base(pole_then_flag(pullback_step=-0.4)) is None


def test_a_flag_shorter_than_three_bars_is_refused():
    with pytest.raises(ValueError, match="at least 3"):
        detect_flag_base(pole_then_flag(), flag_min_bars=2)


# ── the flag must only ADD candidates, never change existing ones ──────────

def test_a_flat_base_is_still_classified_flat_when_flags_are_enabled():
    a = assess_base("PLANT", advance_then_base())
    assert a.window.shape == SHAPE_FLAT, "flag-first search would reclassify this"


def test_enabling_flags_does_not_remove_a_flat_base_candidate():
    bars = advance_then_base()
    on = run_scan({"PLANT": bars}, bars[-1].date, ScanConfig(allow_flag_base=True))
    off = run_scan({"PLANT": bars}, bars[-1].date, ScanConfig(allow_flag_base=False))
    assert [c.symbol for c in on.candidates] == [c.symbol for c in off.candidates] == ["PLANT"]


def test_disabling_flags_reproduces_the_flat_only_funnel():
    """How the flag's contribution stays measurable instead of assumed."""
    bars = pole_then_flag()
    off = run_scan({"FLAG": bars}, bars[-1].date, ScanConfig(allow_flag_base=False))
    assert [b.symbol for b in off.failed_base] == ["FLAG"]
    assert "base_found" in off.failed_base[0].failed_clauses()


def test_the_rejection_message_says_a_flag_was_looked_for():
    bars = [bar(i, 20.0 + 0.5 * i, half_range=0.4, volume=1_000_000) for i in range(300)]
    a = assess_base("RAMP", bars, allow_flag=True)
    assert "no bull flag either" in a.clauses[0].detail


def test_the_shape_is_reported_in_the_clause_detail():
    a = assess_base("PLANT", advance_then_base())
    assert a.clauses[0].detail.startswith(SHAPE_FLAT)


# ── EC-S3: the two implementations must not drift apart ───────────────────

def test_cross_check_against_ai_insights_flag_detector():
    """Same geometry, two codebases (see the note in base.py). Skipped where
    ai-insights is not importable, exactly as `tests/test_phase_k.py` does — but
    present so a container run catches divergence instead of nobody catching it."""
    pd = pytest.importorskip("pandas")
    try:
        import sys
        sys.path.insert(0, "../ai-insights-service")
        from app.services.patterns.continuation import FlagDetector  # type: ignore
    except Exception:                                   # noqa: BLE001
        pytest.skip("ai-insights-service pattern package not importable here")

    bars = pole_then_flag()
    ours = detect_flag_base(bars)
    theirs = FlagDetector().detect(pd.DataFrame([
        {"open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ]))
    assert (ours is not None) == (theirs is not None and theirs.found), \
        "the two flag implementations disagree on a planted flag"
    if ours and theirs:
        # Their `neckline` is the breakout level; ours is the window high. Same thing.
        assert ours.high == pytest.approx(theirs.neckline, rel=1e-6)


def test_the_retrace_cap_admits_just_under_and_refuses_just_over():
    """The 50% line, from both sides. 4 x 2.4 = 9.6 against a 24 pole is 40% and
    is a legitimate flag; 4 x 3.2 = 12.8 is 53% and is a failed move."""
    assert detect_flag_base(pole_then_flag(pullback_step=2.4)) is not None
    assert detect_flag_base(pole_then_flag(pullback_step=3.2)) is None


def test_a_pole_that_already_turned_down_is_not_a_pole():
    """The cap is otherwise evadable by SHORTENING the flag, which pushes the
    pole window over the pullback's first bars and inflates pole_move."""
    bars = pole_then_flag(pullback_step=3.2)
    assert detect_flag_base(bars, flag_min_bars=3, flag_max_bars=3) is None


# ---------------------------------------------------------------------------
# Backlog #141 — shape-specific clause settings for FLAG windows
#
# Every test here asserts from BOTH sides. The property that matters is not
# "flags pass more often" — it is that the two shapes are judged by DISJOINT
# rule sets, because the whole risk of #141 was a loosened flag clause leaking
# into the flat path and quietly widening the screen.
# ---------------------------------------------------------------------------

def test_a_flag_window_carries_its_pole_bounds():
    """The instrumentation #141 needs; a flat base must not have it."""
    w = detect_flag_base(pole_then_flag())
    assert w is not None and w.shape == SHAPE_FLAG
    assert w.pole_start_index is not None and w.pole_end_index is not None
    assert w.pole_end_index == w.start_index - 1          # the pole abuts the flag


def test_a_flat_base_has_no_pole_bounds_so_flag_clauses_cannot_reach_it():
    w = detect_base(advance_then_base())
    assert w is not None and w.shape == SHAPE_FLAT
    assert w.pole_start_index is None and w.pole_end_index is None
    sq = measure_squeeze(advance_then_base(), w)
    assert sq.pole_range_ratio is None and sq.pole_volume_ratio is None


def test_the_pole_denominator_is_the_stricter_comparison():
    """§4.2 as a test. The flag's own mean is a WEAK denominator: it is computed
    over the same few quiet bars being measured, so it cannot express "quiet
    relative to the thrust" at all. Against the pole the same window reads 0.30
    where against itself it reads 0.68 — the pole comparison is both stricter
    here and the one that means what the clause says.

    Note what this fixture also shows: the detected window's first third picks up
    the last POLE bar (`first_third_tr == pole_mean_tr`), so on a 4-bar planted
    flag the flat range denominator is not merely weak, it is partly measuring
    the pole it was supposed to be compared against.
    """
    bars = pole_then_flag()
    w = detect_flag_base(bars)
    sq = measure_squeeze(bars, w)
    assert sq.volume_ratio is not None and sq.pole_volume_ratio is not None
    assert sq.pole_volume_ratio < sq.volume_ratio
    assert sq.pole_mean_volume is not None and sq.base_mean_volume is not None
    assert sq.pole_mean_volume > sq.base_mean_volume


def test_extension_beyond_the_atr_bound_fails_the_flag_clause():
    """From the far side: ATR-bounded is a BOUND, not an open door."""
    bars = pole_then_flag()
    assert measure_ma_proximity(bars, max_atr=99.0).hugging_flag is True
    assert measure_ma_proximity(bars, max_atr=0.01).hugging_flag is False


def test_trend_intact_is_still_non_negotiable_for_a_flag():
    """Dropping the percentage ceiling did not drop the requirement that both
    averages sit BELOW price."""
    bars = pole_then_flag(pole_step=0.06, pullback_step=3.0, flag_bars=8)
    mas = measure_ma_proximity(bars, max_atr=99.0)
    if mas.dist_medium_pct is not None and mas.dist_medium_pct < 0:
        assert mas.hugging_flag is False


def test_assess_base_judges_a_flag_by_pole_relative_clauses():
    a = assess_base("FLAGGED", pole_then_flag())
    names = {c.name: c for c in a.clauses}
    assert names["base_found"].passed
    assert "mean pole TR" in names["range_contraction"].detail
    assert "mean pole volume" in names["volume_dryup"].detail
    assert "ATR" in names["ma_hugging"].detail


def test_assess_base_still_judges_a_flat_base_by_production_clauses():
    """The regression that would matter: flag wording — or a flag threshold —
    leaking onto a flat base."""
    a = assess_base("PLANT", advance_then_base())
    names = {c.name: c for c in a.clauses}
    assert names["base_found"].passed
    assert "first third TR" in names["range_contraction"].detail
    assert "base mean" in names["volume_dryup"].detail
    assert "ATR" not in names["ma_hugging"].detail
    assert "0..8%" in names["ma_hugging"].detail


def test_a_missing_denominator_fails_rather_than_passes():
    """Production's rule, preserved across the new clause forms."""
    assert MAProximity(None, None, None, None, False).hugging_flag is False
    sq = SqueezeMetrics(None, None, None, None, None, None)
    assert sq.pole_range_ratio is None and sq.pole_volume_ratio is None


def test_the_flat_candidate_set_is_unchanged_by_the_flag_clauses():
    """§7's claim, at unit scale: with flags off, nothing about this changed."""
    bars = advance_then_base()
    on = run_scan({"PLANT": bars}, bars[-1].date, ScanConfig(allow_flag_base=True))
    off = run_scan({"PLANT": bars}, bars[-1].date, ScanConfig(allow_flag_base=False))
    assert [c.symbol for c in on.candidates] == [c.symbol for c in off.candidates] == ["PLANT"]
    a, b = on.candidates[0].base, off.candidates[0].base
    assert [(c.name, c.passed, c.detail) for c in a.clauses] == \
           [(c.name, c.passed, c.detail) for c in b.clauses]
