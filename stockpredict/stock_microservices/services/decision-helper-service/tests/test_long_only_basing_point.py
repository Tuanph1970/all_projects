"""Backlog #86 — the long-only basing-point arm.

E&M's Ch 28 procedure is written for an **advance**: a high is made, prices
recede, a reaction low forms, three days clear it. Bassetti's worked example is
a bull market. Applying the mirror to a short is **our** translation, not a
rule the book validates — so `#86` gives it its own arm instead of assuming it,
and these tests pin the arm's behaviour down independently of any study output.

That independence is the point. `#85` published its regime table as "32
symbols" when it was 12, and nobody noticed for a week, because the study's
behaviour was only ever observed through the numbers it printed. A truth table
asserted directly cannot drift that way.
"""
from __future__ import annotations

import pytest

from app.services.backtest.harness import (
    BacktestConfig,
    basing_point_applies,
    run_backtest_on_bars,
)
from tests.failed_signal_override_study import WARMUP, load_bars

LONG_ONLY = "BASING_POINT_LONG_ONLY"


# ---------------------------------------------------------------------------
# The truth table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("direction", ["LONG", "SHORT", None])
def test_plain_basing_point_governs_both_directions(direction):
    """The shipped mirror: #63/#84 tested this arm, so it must not change."""
    assert basing_point_applies("BASING_POINT", direction) is True


def test_long_only_governs_longs():
    assert basing_point_applies(LONG_ONLY, "LONG") is True


def test_long_only_leaves_a_short_on_the_atr_trail():
    """The whole hypothesis in one assertion."""
    assert basing_point_applies(LONG_ONLY, "SHORT") is False


def test_long_only_does_not_govern_an_unknown_direction():
    assert basing_point_applies(LONG_ONLY, None) is False


@pytest.mark.parametrize("direction", ["LONG", "SHORT", None])
def test_the_atr_default_never_consults_the_basing_point(direction):
    assert basing_point_applies("ATR", direction) is False


@pytest.mark.parametrize("mode", ["", "BASING", "basing_point", "LONG_ONLY",
                                  "BASING_POINT_LONG", "ATR_TRAIL"])
def test_an_unrecognised_mode_falls_back_to_atr_rather_than_guessing(mode):
    """A typo in a config must not silently select E&M's rule.

    Includes the near-misses deliberately — `"basing_point"` lower-case and
    `"BASING_POINT_LONG"` are the two a person would actually mistype, and
    both must read as ATR rather than as a partial match.
    """
    assert basing_point_applies(mode, "LONG") is False
    assert basing_point_applies(mode, "SHORT") is False


# ---------------------------------------------------------------------------
# The wiring: the mode has to reach the replay, not just the helper
# ---------------------------------------------------------------------------

#: A 630-bar slice of REE, not the full ~5,900. The replay recomputes swings
#: per bar, so the whole series costs well over the suite's 30s budget; this
#: slice runs in ~0.5s and still produces 36 trades on BOTH sides, which is
#: all these tests need. REE is in the #86 held-out set, so nothing here
#: touches the symbols #63/#84/#85 measured.
SLICE_BARS = 300


@pytest.fixture(scope="module")
def real_bars():
    try:
        bars = load_bars("/tmp/deep_bars.tsv")
    except OSError:
        pytest.skip("deep dump not present")
    series = bars.get("REE")
    if not series or len(series) < WARMUP + SLICE_BARS:
        pytest.skip("REE not present in the dump with enough bars")
    return "REE", series[: WARMUP + SLICE_BARS]


def _ledger(bars, mode):
    # The mode is ALWAYS passed explicitly, including "ATR".
    #
    # This used to omit it for the ATR arm and lean on the config default. That
    # made the test itself depend on a bound default: #101 probed flipping
    # `trailing_stop_mode` to "BASING_POINT" and this was the ONLY test in 963
    # that broke — not because the codebase objected, but because two of its
    # three arms silently became the same run. A test that asserts three modes
    # differ must not take one of them from a default that can move.
    cfg = BacktestConfig(
        ticker="T", start_date=bars[WARMUP].date, end_date=bars[-1].date,
        trailing_stop_mode=mode,
    )
    return run_backtest_on_bars(cfg, bars).trade_ledger


def test_the_long_only_mode_actually_reaches_the_replay(real_bars):
    """Three arms, three different ledgers — or the flag is decorative.

    Asserted on real held-out bars because a helper that returns the right
    booleans is worthless if the replay never calls it.
    """
    _, bars = real_bars
    atr = _ledger(bars, "ATR")
    both = _ledger(bars, "BASING_POINT")
    longs = _ledger(bars, LONG_ONLY)

    pnl = lambda led: [round(t.gross_pnl or 0.0, 6) for t in led]
    assert pnl(longs) != pnl(atr), "long-only is indistinguishable from ATR"
    assert pnl(longs) != pnl(both), "long-only is indistinguishable from the mirror"


def test_the_mode_is_read_at_call_time_not_frozen_at_import(real_bars):
    """The bound-default guard this project has paid for five times.

    EM-1 S2, #78, W1, #84, and #85's `MAX_SYMBOLS` — the last of which
    published a 12-symbol table as 32 for a week. Two different modes must
    produce two different results through the same code path, or a sweep over
    the mode would read as 'flat, so the mode does not matter'.
    """
    _, bars = real_bars
    seen = {}
    for mode in ("ATR", "BASING_POINT", LONG_ONLY):
        seen[mode] = tuple(round(t.gross_pnl or 0.0, 6) for t in _ledger(bars, mode))
    assert len(set(seen.values())) == 3, seen


def test_shorts_exist_in_the_fixture_or_the_arm_is_untested(real_bars):
    """Guards the guard: if the symbol never shorts, the arms cannot differ
    for the reason #86 is about, and the two tests above would be vacuous."""
    _, bars = real_bars
    directions = {t.direction for t in _ledger(bars, "BASING_POINT")}
    assert "SHORT" in directions, directions
    assert "LONG" in directions, directions


# ---------------------------------------------------------------------------
# The shipped default (Backlog #101)
# ---------------------------------------------------------------------------

def test_the_shipped_backtest_default_is_still_the_ATR_trail():
    """A guard, not a tautology — and #101 is why it exists.

    #101 probed flipping this default to "BASING_POINT" and **all 963 tests
    passed**, which sounds reassuring and is actually the finding: nothing in
    the suite pinned the shipped default, so it could have moved in any commit
    without a single failure. #87 added the same kind of guard to
    `HISTORY_YEARS` after it sat at 5 years for the life of the project
    precisely because it was correct-looking, consumed once, and unasserted.

    The evidence now favours the basing point — #86 measured +12,449 gross and
    #101 +16,383 NET total P&L per symbol on 61 held-out symbols (t = +8.97,
    54/61) — so this default may well change. It must change **deliberately**:
    the live recommendation path consults these verdicts and that is a
    user-visible decision (the #83 gate). Flipping this line should break this
    test and make someone say so out loud.
    """
    from app.services.backtest.harness import BacktestConfig

    assert BacktestConfig(
        ticker="T", start_date=None, end_date=None,
    ).trailing_stop_mode == "ATR"
