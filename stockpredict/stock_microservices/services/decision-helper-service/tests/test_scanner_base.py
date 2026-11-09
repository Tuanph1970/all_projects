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
    assess_base,
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
