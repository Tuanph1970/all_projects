"""Backlog #118 — the narrator's four new readings, and the gate that stops it lying.

Every test here drives a PURE function over a constructed frame. That is the
point of the module's shape: the narrator's correctness is the whole feature, so
it has to be checkable without a broker, a database, or a live market.

Constructions are built to kill the specific mutation each one is about. The
session that produced this file has been burned repeatedly by fixtures that
cannot distinguish a correct implementation from a broken one — a flat `[10]*40`
volume series where mean equals median, a source assertion that matched the
test's own comment, a guard that could not fire on what compose injected. So the
numbers below are chosen, not typed.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
import pytest

from app.services.narrative import (
    DOJI_BODY_RATIO,
    MAX_BELIEVABLE_DAILY_MOVE_PCT,
    Finding,
    detect_candles,
    detect_rsi_divergence,
    find_corporate_action_gaps,
    gap_findings,
    price_channel,
)


def _frame(rows):
    """rows: iterable of (date, open, high, low, close[, volume])."""
    recs = []
    for i, r in enumerate(rows):
        d, o, h, l, c = r[:5]
        v = r[5] if len(r) > 5 else 1_000_000
        recs.append({"date": d, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return pd.DataFrame(recs)


def _flat(n, price=50.0, start="2026-01-01"):
    dates = pd.bdate_range(start, periods=n).strftime("%Y-%m-%d")
    return _frame([(d, price, price + 0.5, price - 0.5, price) for d in dates])


# ===========================================================================
# 1. The honesty gate (#119)
# ===========================================================================

def test_the_real_tcb_stock_dividend_is_caught():
    """The gap that motivated the gate, with the database's own numbers.

    TCB closed 33.80 on 2026-10-26 and 22.37 on 2026-10-27. HOSE caps a session
    at +/-7%, so -33.8% is arithmetically impossible as trading.
    """
    df = _frame([
        ("2026-10-23", 34.0, 34.4, 34.0, 34.20),
        ("2026-10-26", 34.2, 34.3, 33.7, 33.80),
        ("2026-10-27", 22.4, 22.5, 22.2, 22.37),
        ("2026-10-28", 22.3, 22.5, 22.2, 22.33),
    ])
    gaps = find_corporate_action_gaps(df)
    assert len(gaps) == 1, gaps
    g = gaps[0]
    assert g["date"] == "2026-10-27"
    assert g["move_pct"] == pytest.approx(-33.81, abs=0.02)
    # ~1.51 reads as roughly a 3-for-2 issue, which is the useful fact.
    assert g["ratio"] == pytest.approx(1.511, abs=0.01)


def test_a_legitimate_limit_move_is_not_called_a_corporate_action():
    """The false positive that would make the gate worthless.

    A UPCoM board allows +/-15%. If the gate fired on that, it would cry "stock
    dividend" on real trading and be tuned out — which costs more than a miss.
    Exactly 15.0% must pass, because the comparison is strictly greater-than.
    """
    df = _frame([
        ("2026-01-02", 10.0, 10.0, 10.0, 10.00),
        ("2026-01-05", 11.5, 11.5, 11.5, 11.50),   # exactly +15.00%
    ])
    assert find_corporate_action_gaps(df) == []


def test_just_past_the_ceiling_is_caught():
    """Guards the guard above: the boundary must be a boundary, not a floor."""
    df = _frame([
        ("2026-01-02", 10.0, 10.0, 10.0, 10.00),
        ("2026-01-05", 11.6, 11.6, 11.6, 11.60),   # +16.0%
    ])
    gaps = find_corporate_action_gaps(df)
    assert len(gaps) == 1
    assert gaps[0]["move_pct"] == pytest.approx(16.0, abs=0.01)


def test_a_clean_series_yields_nothing():
    """Non-vacuity in the other direction: the common case is no gaps at all.

    Only four such gaps exist in five years of this database, so a gate that
    fired on ordinary bars would be useless.
    """
    rng = np.random.default_rng(118)
    price = 50.0
    rows = []
    for i, d in enumerate(pd.bdate_range("2026-01-01", periods=120).strftime("%Y-%m-%d")):
        price *= 1 + rng.normal(0, 0.015)   # ~1.5% daily vol, never near 15%
        rows.append((d, price, price * 1.01, price * 0.99, price))
    assert find_corporate_action_gaps(_frame(rows)) == []


def test_the_threshold_is_the_loosest_vn_board_not_the_tightest():
    """Pins the chosen default and the reason for it.

    HOSE is 7%, HNX 10%, UPCoM 15%. The board is unknown here, so the default
    must be the loosest or legitimate limit days get flagged.
    """
    assert MAX_BELIEVABLE_DAILY_MOVE_PCT == 15.0


def test_the_ceiling_is_a_parameter_that_actually_changes_the_answer():
    """A configurable that is never read is decorative. This proves it is read."""
    df = _frame([
        ("2026-01-02", 10.0, 10.0, 10.0, 10.0),
        ("2026-01-05", 11.2, 11.2, 11.2, 11.2),   # +12%
    ])
    assert find_corporate_action_gaps(df) == []                        # under 15
    assert len(find_corporate_action_gaps(df, max_move_pct=10.0)) == 1  # over 10


def test_a_gap_is_reported_as_a_warning_and_never_as_bearish():
    """The specific error the gate exists to prevent, asserted directly.

    A -34% stock dividend is not bad news. If severity were derived from the
    sign of the move, the narrator would be right back to calling it a crash.
    """
    df = _frame([
        ("2026-10-26", 34.2, 34.3, 33.7, 33.80),
        ("2026-10-27", 22.4, 22.5, 22.2, 22.37),
    ])
    findings = gap_findings(find_corporate_action_gaps(df))
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].code == "narrative.data.corporate_action_gap"


def test_the_worst_gap_is_the_one_reported_when_several_exist():
    df = _frame([
        ("2021-07-01", 21.7, 21.8, 21.6, 21.71),
        ("2021-07-02", 17.9, 18.0, 17.8, 17.91),   # -17.5%
        ("2021-07-05", 17.9, 18.0, 17.8, 17.90),
        ("2021-07-06", 11.9, 12.0, 11.8, 11.90),   # -33.5%, the worst
    ])
    gaps = find_corporate_action_gaps(df)
    assert len(gaps) == 2
    f = gap_findings(gaps)[0]
    assert f.params["count"] == 2
    assert f.params["move_pct"] == pytest.approx(-33.52, abs=0.05)


def test_no_gaps_means_no_finding_rather_than_an_all_clear_sentence():
    assert gap_findings([]) == []


@pytest.mark.parametrize("bad", [
    pd.DataFrame(),
    pd.DataFrame({"close": [10.0]}),              # a single bar has no overnight
    pd.DataFrame({"open": [1.0, 2.0]}),           # no close column at all
])
def test_degenerate_input_is_empty_not_an_exception(bad):
    assert find_corporate_action_gaps(bad) == []


def test_a_zero_or_negative_prior_close_cannot_divide_by_zero():
    df = _frame([
        ("2026-01-02", 0.0, 0.0, 0.0, 0.0),
        ("2026-01-05", 10.0, 10.0, 10.0, 10.0),
    ])
    assert find_corporate_action_gaps(df) == []


# ===========================================================================
# 2. Candlesticks
# ===========================================================================

def _codes(findings):
    return {f.code for f in findings}


def test_a_doji_is_recognised():
    df = _frame([
        ("2026-01-02", 50.0, 51.0, 49.0, 50.0),
        ("2026-01-05", 50.0, 52.0, 48.0, 50.1),   # body 0.1 of range 4.0 = 2.5%
    ])
    assert "narrative.candle.doji" in _codes(detect_candles(df))


def test_a_wide_bodied_bar_is_not_a_doji():
    """Non-vacuity: the detector must distinguish, not just fire."""
    df = _frame([
        ("2026-01-02", 50.0, 51.0, 49.0, 50.0),
        ("2026-01-05", 48.0, 52.0, 48.0, 52.0),   # body == range
    ])
    assert "narrative.candle.doji" not in _codes(detect_candles(df))


def test_the_doji_ratio_is_the_published_tenth():
    assert DOJI_BODY_RATIO == 0.10


def test_a_hammer_is_recognised_and_is_bullish():
    # body 0.5 (49.5->50.0), lower shadow 4.5, upper shadow 0.2
    df = _frame([
        ("2026-01-02", 55.0, 55.5, 54.5, 55.0),
        ("2026-01-05", 49.5, 50.2, 45.0, 50.0),
    ])
    found = [f for f in detect_candles(df) if f.code == "narrative.candle.hammer"]
    assert found, _codes(detect_candles(df))
    assert found[0].severity == "bullish"


def test_a_shooting_star_is_recognised_and_is_bearish():
    # body 0.5 (50.0->49.5), upper shadow 4.8, lower shadow 0.2
    df = _frame([
        ("2026-01-02", 45.0, 45.5, 44.5, 45.0),
        ("2026-01-05", 50.0, 54.8, 49.3, 49.5),
    ])
    found = [f for f in detect_candles(df) if f.code == "narrative.candle.shooting_star"]
    assert found, _codes(detect_candles(df))
    assert found[0].severity == "bearish"


def test_a_hammer_and_a_shooting_star_are_not_the_same_shape():
    """They are mirrors, so a detector that ignored which shadow is long would
    emit both for either bar. This asserts the asymmetry is real."""
    hammer = _frame([
        ("2026-01-02", 55.0, 55.5, 54.5, 55.0),
        ("2026-01-05", 49.5, 50.2, 45.0, 50.0),
    ])
    codes = _codes(detect_candles(hammer))
    assert "narrative.candle.hammer" in codes
    assert "narrative.candle.shooting_star" not in codes


def test_bullish_engulfing_requires_the_body_to_cover_the_previous_body():
    df = _frame([
        ("2026-01-02", 52.0, 52.2, 49.8, 50.0),   # down bar, body 52.0 -> 50.0
        ("2026-01-05", 49.5, 53.0, 49.4, 52.5),   # up bar swallowing it
    ])
    found = [f for f in detect_candles(df) if f.code == "narrative.candle.bullish_engulfing"]
    assert found
    assert found[0].severity == "bullish"


def test_an_up_bar_that_does_not_cover_the_previous_body_is_not_engulfing():
    """The near-miss. Without the open<=prev_close and close>=prev_open checks,
    any up bar after a down bar would read as engulfing."""
    df = _frame([
        ("2026-01-02", 52.0, 52.2, 49.8, 50.0),
        ("2026-01-05", 50.5, 51.5, 50.4, 51.0),   # inside the previous body
    ])
    assert "narrative.candle.bullish_engulfing" not in _codes(detect_candles(df))


def test_bearish_engulfing_is_the_mirror():
    df = _frame([
        ("2026-01-02", 50.0, 52.2, 49.8, 52.0),   # up bar
        ("2026-01-05", 52.5, 52.9, 49.4, 49.5),   # down bar swallowing it
    ])
    found = [f for f in detect_candles(df) if f.code == "narrative.candle.bearish_engulfing"]
    assert found
    assert found[0].severity == "bearish"


def test_only_the_recent_edge_is_narrated():
    """A hammer forty bars back is history. The lookback must actually bound."""
    rows = [("2026-01-02", 55.0, 55.5, 54.5, 55.0),
            ("2026-01-05", 49.5, 50.2, 45.0, 50.0)]   # the hammer
    tail = pd.bdate_range("2026-01-06", periods=30).strftime("%Y-%m-%d")
    rows += [(d, 50.0, 50.6, 49.4, 50.2) for d in tail]
    df = _frame(rows)
    assert "narrative.candle.hammer" not in _codes(detect_candles(df, lookback=3))
    # ...and it IS found when the window reaches back far enough, which proves
    # the absence above is the lookback and not a broken detector.
    assert "narrative.candle.hammer" in _codes(detect_candles(df, lookback=40))


def test_a_zero_range_bar_has_no_shape_and_is_skipped():
    """A limit-locked or untraded bar would otherwise divide by zero."""
    df = _frame([
        ("2026-01-02", 50.0, 51.0, 49.0, 50.0),
        ("2026-01-05", 50.0, 50.0, 50.0, 50.0),
    ])
    assert detect_candles(df) is not None   # no exception
    assert "narrative.candle.doji" not in _codes(detect_candles(df))


def test_candles_report_how_long_ago_so_today_is_distinguishable():
    df = _frame([
        ("2026-01-02", 55.0, 55.5, 54.5, 55.0),
        ("2026-01-05", 49.5, 50.2, 45.0, 50.0),
    ])
    f = [x for x in detect_candles(df) if x.code == "narrative.candle.hammer"][0]
    assert f.params["bars_ago"] == 0
    assert f.params["date"] == "2026-01-05"


# ===========================================================================
# 3. RSI divergence
# ===========================================================================

def _diverging_frame(kind: str):
    """Two clean swings, with RSI moving the opposite way to price."""
    n = 40
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    base = np.full(n, 50.0)
    rsi = np.full(n, 50.0)
    if kind == "bearish":
        base[10] = 55.0          # first high
        base[30] = 58.0          # HIGHER high
        rsi[10], rsi[30] = 75.0, 62.0   # LOWER momentum
        rows = [(d, 50.0, b + 0.2, 49.0, 50.0) for d, b in zip(dates, base)]
    else:
        base[10] = 45.0          # first low
        base[30] = 42.0          # LOWER low
        rsi[10], rsi[30] = 25.0, 38.0   # HIGHER momentum
        rows = [(d, 50.0, 51.0, b - 0.2, 50.0) for d, b in zip(dates, base)]
    return _frame(rows), rsi


def test_bearish_divergence_is_found_when_price_rises_on_less_force():
    df, rsi = _diverging_frame("bearish")
    found = [f for f in detect_rsi_divergence(df, rsi)
             if f.code == "narrative.divergence.bearish_rsi"]
    assert found, [f.code for f in detect_rsi_divergence(df, rsi)]
    f = found[0]
    assert f.severity == "bearish"
    assert f.params["from_price"] < f.params["to_price"]
    assert f.params["from_rsi"] > f.params["to_rsi"]


def test_bullish_divergence_is_the_mirror():
    df, rsi = _diverging_frame("bullish")
    found = [f for f in detect_rsi_divergence(df, rsi)
             if f.code == "narrative.divergence.bullish_rsi"]
    assert found
    assert found[0].severity == "bullish"
    assert found[0].params["from_price"] > found[0].params["to_price"]
    assert found[0].params["from_rsi"] < found[0].params["to_rsi"]


def test_agreement_is_not_divergence():
    """The central non-vacuity test. Price up AND momentum up must be silent."""
    n = 40
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    base = np.full(n, 50.0)
    base[10], base[30] = 55.0, 58.0
    rsi = np.full(n, 50.0)
    rsi[10], rsi[30] = 62.0, 75.0      # momentum CONFIRMS the higher high
    df = _frame([(d, 50.0, b + 0.2, 49.0, 50.0) for d, b in zip(dates, base)])
    assert [f for f in detect_rsi_divergence(df, rsi)
            if f.code == "narrative.divergence.bearish_rsi"] == []


def test_a_misaligned_rsi_series_is_refused_rather_than_compared():
    """Silently comparing a price pivot to an unrelated momentum reading is the
    worst outcome here, because it produces confident nonsense."""
    df, rsi = _diverging_frame("bearish")
    assert detect_rsi_divergence(df, rsi[:-5]) == []
    assert detect_rsi_divergence(df, np.append(rsi, [50.0, 50.0])) == []


def test_two_pivots_too_close_together_are_not_two_swings():
    n = 40
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    base = np.full(n, 50.0)
    base[28], base[30] = 55.0, 58.0      # 2 bars apart
    rsi = np.full(n, 50.0)
    rsi[28], rsi[30] = 75.0, 62.0
    df = _frame([(d, 50.0, b + 0.2, 49.0, 50.0) for d, b in zip(dates, base)])
    assert detect_rsi_divergence(df, rsi, min_separation=5) == []


def test_a_short_series_is_empty_not_an_exception():
    df = _flat(6)
    assert detect_rsi_divergence(df, np.full(6, 50.0)) == []


# ===========================================================================
# 4. Price channel
# ===========================================================================

def test_a_channel_needs_two_pivots_on_each_rail():
    """One high does not make a trendline. The narrator must be able to say
    nothing rather than draw a line through a single point."""
    assert price_channel(_flat(60)) is None     # no swings at all in a flat series


def test_a_rising_channel_has_two_rising_rails():
    n = 80
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(dates):
        mid = 40.0 + 0.2 * i                 # steady advance
        osc = 2.0 * np.sin(i / 4.0)          # swings inside it
        c = mid + osc
        rows.append((d, c, c + 1.0, c - 1.0, c))
    ch = price_channel(_frame(rows))
    assert ch is not None
    assert ch.upper_slope > 0 and ch.lower_slope > 0
    assert ch.upper_now > ch.lower_now
    assert 0.0 <= ch.position_pct <= 100.0
    assert ch.pivots_used >= 4


def test_a_falling_channel_has_two_falling_rails():
    n = 80
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(dates):
        c = 70.0 - 0.2 * i + 2.0 * np.sin(i / 4.0)
        rows.append((d, c, c + 1.0, c - 1.0, c))
    ch = price_channel(_frame(rows))
    assert ch is not None
    assert ch.upper_slope < 0 and ch.lower_slope < 0


def test_position_says_where_in_the_channel_price_sits():
    """Built so the last bar closes near the TOP rail, and asserts the number
    reflects that rather than defaulting to the middle."""
    n = 81
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(dates):
        c = 50.0 + 2.0 * np.sin(i / 4.0)
        rows.append((d, c, c + 1.0, c - 1.0, c))
    # Force the final close onto the upper rail.
    rows[-1] = (dates[-1], 52.0, 53.0, 51.0, 53.0)
    ch = price_channel(_frame(rows))
    assert ch is not None
    assert ch.position_pct > 70.0, ch.as_dict()


def test_a_crossed_wedge_clamps_rather_than_reporting_a_wild_number():
    n = 80
    dates = pd.bdate_range("2026-01-01", periods=n).strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(dates):
        amp = max(0.2, 6.0 - 0.07 * i)      # converging
        c = 50.0 + amp * np.sin(i / 4.0)
        rows.append((d, c, c + amp / 2, c - amp / 2, c))
    ch = price_channel(_frame(rows))
    if ch is not None:
        assert 0.0 <= ch.position_pct <= 100.0


def test_min_pivots_cannot_be_satisfied_by_one_swing():
    """Guards the guard: `min_pivots=1` would make the None above unreachable,
    so the default must be above one."""
    import inspect
    sig = inspect.signature(price_channel)
    assert sig.parameters["min_pivots"].default >= 2


# ===========================================================================
# 5. Findings are well-formed, and BOTH locales can render them
# ===========================================================================

def test_an_unknown_severity_is_refused_at_construction():
    with pytest.raises(ValueError):
        Finding("narrative.x", {}, "catastrophic")


def test_a_finding_serialises_to_code_params_severity():
    d = Finding("narrative.x", {"a": 1}, "bullish").as_dict()
    assert d == {"code": "narrative.x", "params": {"a": 1}, "severity": "bullish"}


def _locale(name):
    root = pathlib.Path(__file__).resolve().parents[4]
    p = root / "stock_react_javascript/stock-react-app/src/i18n" / name
    if not p.exists():
        for cand in root.rglob(f"src/**/{name}"):
            p = cand
            break
    if not p.exists():
        pytest.skip(f"{name} not found from {root}")
    return json.loads(p.read_text(encoding="utf-8"))


def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


#: Every code this module can emit. Hardcoded rather than discovered, so that
#: ADDING a code without a translation breaks the test instead of silently
#: shrinking the thing being checked.
ALL_CODES = [
    "narrative.data.corporate_action_gap",
    "narrative.candle.doji",
    "narrative.candle.hammer",
    "narrative.candle.shooting_star",
    "narrative.candle.bullish_engulfing",
    "narrative.candle.bearish_engulfing",
    "narrative.divergence.bearish_rsi",
    "narrative.divergence.bullish_rsi",
    "narrative.channel.broken_below",
    "narrative.channel.broken_above",
    "narrative.pattern.noteworthy",
    "narrative.pattern.not_noteworthy",
    "narrative.pattern.unvalidated",
    "narrative.pattern.none",
    "narrative.pattern.none_recent",
    "narrative.pattern.unavailable",
]


@pytest.mark.parametrize("lang", ["en.json", "vi.json"])
def test_every_finding_code_has_a_string_in_both_locales(lang):
    """A finding with no translation reaches the user as a raw dotted key.

    The owner's #118 requirements were written in Vietnamese, so an
    English-only narrator would be the wrong half of the feature.
    """
    flat = _flatten(_locale(lang))
    missing = [c for c in ALL_CODES if c not in flat]
    assert not missing, f"{lang} is missing: {missing}"


@pytest.mark.parametrize("lang", ["en.json", "vi.json"])
def test_no_translation_is_left_as_an_empty_string(lang):
    flat = _flatten(_locale(lang))
    blank = [c for c in ALL_CODES if c in flat and not str(flat[c]).strip()]
    assert not blank, f"{lang} has blank strings for: {blank}"


def test_the_vietnamese_narration_is_not_just_the_english_copied():
    """Pasting the English in to make the test above pass would be the obvious
    shortcut, and it would ship an untranslated screen that looks translated."""
    en, vi = _flatten(_locale("en.json")), _flatten(_locale("vi.json"))
    shared = [c for c in ALL_CODES if c in en and c in vi]
    assert shared, "no codes present in both locales yet"
    identical = [c for c in shared if en[c] == vi[c]]
    assert len(identical) <= len(shared) // 4, (
        f"{len(identical)}/{len(shared)} Vietnamese strings are byte-identical "
        f"to the English: {identical}")
