"""S-1 funnel — accounting, the seam gate, and the two mandatory harnesses.

VT-1 (no-leakage) and VT-2 (determinism) are the phase's exit criteria, not
extras: a scanner that reads the future produces a beautiful backtest and no
trades, and one that is not reproducible makes VT-5's forward evaluation
unfalsifiable.
"""
from __future__ import annotations

import random
from dataclasses import replace
from datetime import date, timedelta
from typing import Dict, List, Sequence

import pytest

from app.services.scanner.screen import ScanConfig, run_scan
from app.services.signal.base import OHLCVBar

START = date(2022, 1, 3)


def series(closes: Sequence[float], volume: float = 1_000_000) -> List[OHLCVBar]:
    return [
        OHLCVBar(date=START + timedelta(days=i), open=c, high=c, low=c, close=c,
                 volume=volume)
        for i, c in enumerate(closes)
    ]


def rising(n: int = 400, start: float = 20.0, step: float = 0.3, **kw) -> List[OHLCVBar]:
    """A ramp steep enough to clear the 30% prior-advance floor.

    The slope is load-bearing, which is easy to miss: the floor is measured over
    the last 126 bars, so on a LINEAR ramp from 20.0 the advance is
    (20+399s)/(20+273s)-1, and anything under s = 0.136 fails `prior_advance`
    while still being a textbook uptrend. At s = 0.1 every fixture here lands in
    `failed_trend` and the accounting assertions go green for the wrong reason.
    """
    return series([start + step * i for i in range(n)], **kw)


def falling(n: int = 400, start: float = 80.0, step: float = 0.1, **kw) -> List[OHLCVBar]:
    return series([start - step * i for i in range(n)], **kw)


#: Prices here are in the stored unit (thousands of VND), as the real series is:
#: a 20.0 close is 20,000 VND, so 1,000,000 shares is 20 tỷ/phiên — comfortably
#: over the 5 tỷ floor. `volume=1` is the illiquid case at 20,000 VND/phiên.
#:
#: `require_base=False` PINS THE S-1 FUNNEL, which is this file's subject. The
#: fixtures here are linear ramps: constant true range, so `range_contraction`
#: reads exactly 1.00 and S-2 rejects every one of them — correctly, since a
#: ramp is a stock going straight up, which is the opposite of resting. Turning
#: the base stage off here keeps these tests testing what they were written to
#: test, and keeps S-1 reproducible on the same data once S-2 exists.
#: S-2's own behaviour is pinned in `test_scanner_base.py`.
LIQUID_CONFIG = ScanConfig(require_base=False)


def last_date(bars: Sequence[OHLCVBar]) -> date:
    return bars[-1].date


# ---------------------------------------------------------------------------
# Accounting (FR-SCAN-UNIV)
# ---------------------------------------------------------------------------

def test_every_symbol_lands_in_exactly_one_bucket():
    universe = {
        "UP": rising(),
        "DOWN": falling(),
        "SHORT": rising(n=40),
        "THIN": rising(volume=1),
        "EMPTY": [],
    }
    r = run_scan(universe, last_date(universe["UP"]), LIQUID_CONFIG)
    acc = r.accounting()
    assert acc["accounted"] == acc["universe_total"] == 5
    assert r.excluded_no_bars == ("EMPTY",)
    assert r.excluded_insufficient_history == ("SHORT",)
    assert [l.ticker for l in r.excluded_illiquid] == ["THIN"]
    assert [t.symbol for t in r.failed_trend] == ["DOWN"]
    assert [c.symbol for c in r.candidates] == ["UP"]


def test_the_cut_keeps_qualified_names_in_the_accounting():
    """`max_candidates` truncates the SHOWN list; the names it cuts are still
    qualified and must not vanish from the totals."""
    universe = {f"S{i:02d}": rising(start=20.0 + i) for i in range(5)}
    r = run_scan(universe, last_date(universe["S00"]), replace(LIQUID_CONFIG, max_candidates=2))
    assert len(r.candidates) == 2
    assert len(r.excess_qualified) == 3
    acc = r.accounting()
    assert acc["accounted"] == acc["universe_total"] == 5


def test_required_bars_is_raised_above_a_too_low_configured_floor():
    cfg = replace(LIQUID_CONFIG, min_bars=10)
    r = run_scan({"UP": rising()}, last_date(rising()), cfg)
    assert r.required_bars >= 200, "SMA200 binds harder than min_bars=10"


# ---------------------------------------------------------------------------
# FR-SCAN-SEAM
# ---------------------------------------------------------------------------

def _with_seam(bars: List[OHLCVBar]) -> List[OHLCVBar]:
    """Halve every close from the midpoint on — a share-count scale break."""
    out = list(bars)
    for i in range(len(out) // 2, len(out)):
        out[i] = replace(out[i], close=out[i].close / 2.0)
    return out


def test_a_seam_excludes_the_symbol_before_it_can_be_ranked():
    universe = {"CLEAN": rising(), "SEAMED": _with_seam(rising())}
    r = run_scan(universe, last_date(universe["CLEAN"]), LIQUID_CONFIG)
    assert [s.symbol for s in r.excluded_price_seam] == ["SEAMED"]
    assert "SEAMED" not in {c.symbol for c in r.candidates}
    assert r.ranked_universe == 1, \
        "a contaminated symbol must not be in the population the percentiles are taken over"


def test_an_allowlisted_seam_is_classified_not_excluded():
    """SRS 2.4: a seam that survived a full re-pull is provider data, not our
    ingestion artefact (VTP 2022-11-16). The gate drops what the repair path can
    still fix; excluding a real session is the detector crying wolf."""
    universe = {"SEAMED": _with_seam(rising())}
    cfg = replace(LIQUID_CONFIG, seam_allowlist=frozenset({"SEAMED"}))
    r = run_scan(universe, last_date(universe["SEAMED"]), cfg)
    assert r.excluded_price_seam == ()
    assert [s.symbol for s in r.flagged_price_seam] == ["SEAMED"]
    assert r.ranked_universe == 1


# ---------------------------------------------------------------------------
# VT-1 — no-leakage (MANDATORY)
# ---------------------------------------------------------------------------

def test_vt1_future_bars_cannot_change_a_past_scan():
    """Swap every bar AFTER the scan date for noise. The scan for that date must
    be byte-identical. This is the test that catches a full-series computation
    that was later sliced."""
    rng = random.Random(20261109)
    universe: Dict[str, List[OHLCVBar]] = {
        "UP": rising(), "DOWN": falling(), "FLAT": series([30.0] * 400),
    }
    as_of = universe["UP"][299].date

    before = run_scan(universe, as_of, LIQUID_CONFIG)

    perturbed = {}
    for sym, bars in universe.items():
        tail = [
            replace(b, open=rng.uniform(1, 500), high=rng.uniform(1, 500),
                    low=rng.uniform(1, 500), close=rng.uniform(1, 500),
                    volume=rng.randint(0, 10_000_000))
            for b in bars[300:]
        ]
        perturbed[sym] = bars[:300] + tail

    after = run_scan(perturbed, as_of, LIQUID_CONFIG)
    assert before == after, "the scan read bars dated after as_of"


def test_vt1_the_scan_date_itself_is_included_not_excluded():
    """The boundary must be <= as_of. Off-by-one here would silently scan
    yesterday while reporting today."""
    bars = rising()
    r = run_scan({"UP": bars}, bars[299].date, LIQUID_CONFIG)
    assert r.candidates[0].trend.close == pytest.approx(bars[299].close)


def test_vt1_unsorted_input_is_sorted_before_the_cut():
    """An unsorted series would make bars[-1] an arbitrary bar and every return
    in the module silently wrong."""
    bars = rising()
    shuffled = list(bars)
    random.Random(7).shuffle(shuffled)
    assert run_scan({"UP": shuffled}, bars[299].date, LIQUID_CONFIG) == run_scan({"UP": bars}, bars[299].date, LIQUID_CONFIG)


# ---------------------------------------------------------------------------
# VT-2 — determinism (MANDATORY)
# ---------------------------------------------------------------------------

def test_vt2_same_date_same_data_gives_an_identical_report():
    universe = {f"S{i:02d}": rising(start=20.0 + i * 0.1) for i in range(12)}
    as_of = last_date(universe["S00"])
    assert run_scan(universe, as_of, LIQUID_CONFIG) == run_scan(universe, as_of, LIQUID_CONFIG)


def test_vt2_insertion_order_does_not_change_the_output():
    base = {f"S{i:02d}": rising(start=20.0 + i * 0.1) for i in range(12)}
    as_of = last_date(base["S00"])
    reordered = dict(sorted(base.items(), key=lambda kv: kv[0], reverse=True))
    assert run_scan(base, as_of, LIQUID_CONFIG) == run_scan(reordered, as_of, LIQUID_CONFIG)


def test_vt2_tied_symbols_are_ordered_by_name_not_by_dict_order():
    tied = {"BBB": rising(), "AAA": rising(), "CCC": rising()}
    r = run_scan(tied, last_date(tied["AAA"]), LIQUID_CONFIG)
    assert [c.symbol for c in r.candidates] == ["AAA", "BBB", "CCC"]


# ---------------------------------------------------------------------------
# Shape of the result
# ---------------------------------------------------------------------------

def test_candidates_are_ranked_from_one_and_carry_their_evidence():
    universe = {"A": rising(start=20.0), "B": rising(start=20.0, step=0.2)}
    r = run_scan(universe, last_date(universe["A"]), LIQUID_CONFIG)
    assert [c.rank for c in r.candidates] == [1, 2]
    top = r.candidates[0]
    assert top.momentum.ranked_universe == 2
    assert set(top.momentum.percentiles) == set(LIQUID_CONFIG.horizons)
    assert top.trend.passed and top.liquidity.passed


def test_an_empty_universe_is_an_empty_report_not_a_crash():
    r = run_scan({}, date(2026, 11, 6), LIQUID_CONFIG)
    assert r.candidates == () and r.universe_total == 0 and r.ranked_universe == 0


# ---------------------------------------------------------------------------
# EC-S4 — the liquidity floor is in VND, and the stored price unit is not
# ---------------------------------------------------------------------------

def test_the_vnd_floor_is_converted_into_the_unit_liquidity_actually_measures():
    """Prices are stored in THOUSANDS of VND (vnstock/VCI). `assess_liquidity`
    multiplies close by volume, so its avg_daily_value is in thousands too.
    Comparing it straight against a VND threshold is wrong by 1,000x in the
    direction that silently passes everything."""
    cfg = ScanConfig(min_avg_daily_value=5_000_000_000.0, price_unit_vnd=1_000.0)
    assert cfg.min_avg_value_in_price_units() == pytest.approx(5_000_000.0)


def test_a_source_quoting_real_vnd_needs_only_the_unit_changed():
    cfg = ScanConfig(min_avg_daily_value=5_000_000_000.0, price_unit_vnd=1.0)
    assert cfg.min_avg_value_in_price_units() == pytest.approx(5_000_000_000.0)


def test_a_nonsense_price_unit_is_refused_rather_than_dividing_by_zero():
    with pytest.raises(ValueError, match="price_unit_vnd"):
        ScanConfig(price_unit_vnd=0.0).min_avg_value_in_price_units()


def test_the_floor_actually_bites_at_the_right_order_of_magnitude():
    """End to end, on the real stored unit.

    The ramp's last 50 closes average 132.35 (thousand VND) on 1,000,000 shares,
    so `avg_daily_value` reads 132,350,000 stored units = **132.35 tỷ/phiên**.
    A 100 tỷ floor passes it and a 200 tỷ floor rejects it.

    The 1,000x bug would be invisible to a one-sided assertion: 132,350,000
    compared raw is under BOTH VND thresholds, so without the conversion the
    first assertion would fail — and compared the other way round every symbol
    in the universe clears any plausible floor. Both directions are asserted.
    """
    bars = rising()
    as_of = last_date(bars)

    passed = run_scan({"X": bars}, as_of, replace(
        LIQUID_CONFIG, min_avg_daily_value=100_000_000_000.0))
    assert [c.symbol for c in passed.candidates] == ["X"]
    assert passed.candidates[0].liquidity.avg_daily_value == pytest.approx(132_350_000.0)

    rejected = run_scan({"X": bars}, as_of, replace(
        LIQUID_CONFIG, min_avg_daily_value=200_000_000_000.0))
    assert rejected.candidates == ()
    assert [l.ticker for l in rejected.excluded_illiquid] == ["X"]
