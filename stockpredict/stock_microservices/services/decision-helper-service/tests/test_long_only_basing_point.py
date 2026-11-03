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

from datetime import date

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

def test_the_backtest_default_is_the_basing_point_trail():
    """A guard, not a tautology — and #101 is why it exists.

    This default was "ATR" for the life of the harness and moved to
    "BASING_POINT" on 2026-10-27 by owner decision, on the evidence of #86 and
    #101: on 61 symbols no EM-3 study had seen, +12,449 total GROSS P&L per
    symbol (t = +6.60) and +16,383 NET (t = +8.97, 54/61 positive), of which
    76% decomposes to the rule rather than to its 23% lower turnover.

    The guard exists because #101 probed the flip first and found that **all
    963 tests passed either way** — nothing pinned the default, so it could
    have moved in any commit without a single failure. #87 added the same kind
    of guard to `HISTORY_YEARS` after it sat wrong for the life of the project
    for exactly that reason: correct-looking, consumed once, unasserted.

    Changing this line again should break this test and make someone say so
    out loud.
    """
    from app.services.backtest.harness import BacktestConfig

    assert BacktestConfig(
        ticker="T", start_date=None, end_date=None,
    ).trailing_stop_mode == "BASING_POINT"


def test_the_endpoint_and_the_class_now_agree_on_the_basing_point_trail():
    """Backlog #101, both decisions, now taken.

    HISTORY THIS TEST HAS CARRIED, because it is the point of it. It began as
    "the endpoint still pins the ATR trail" and asserted the literal
    `trailing_stop_mode="ATR"` appeared in routes.py — true only while the
    endpoint hardcoded it. On 2026-11-02 the mode became a request field and
    this became a property test: an unflagged request resolved to ATR, so the
    class default could not reach a user-visible response. On 2026-11-03 the
    owner took decision (2) and the request default moved to BASING_POINT too.

    So the two defaults now AGREE, which means the old non-vacuity trick —
    asserting they differ — no longer says anything. What keeps this meaningful
    instead is the pair below: the default is the measured rule, AND the old
    rule is still reachable, so the flip is recoverable rather than final.
    """
    from app.models.schemas import BacktestRequest
    from app.services.backtest.harness import BacktestConfig

    request_default = BacktestRequest(
        ticker="VCB", start_date=date(2026, 1, 1), end_date=date(2026, 3, 1),
    ).trailing_stop_mode
    class_default = BacktestConfig(
        ticker="T", start_date=None, end_date=None).trailing_stop_mode

    assert request_default == "BASING_POINT", (
        "the /backtest default is no longer the basing-point trail; #101 "
        "decision (2) adopted it on 61 held-out symbols at net t=+8.97"
    )
    assert class_default == "BASING_POINT", (
        "the BacktestConfig default diverged from the endpoint; #101 moved both "
        "and they are meant to stay aligned"
    )


def test_the_old_atr_trail_remains_reachable():
    """Adoption is not removal. Every published study pins its control arm
    explicitly so earlier figures reproduce, and a regression stays one request
    field away from being undone."""
    from app.models.schemas import BacktestRequest
    from app.services.backtest.harness import basing_point_applies

    req = BacktestRequest(ticker="VCB", start_date=date(2026, 1, 1),
                          end_date=date(2026, 3, 1), trailing_stop_mode="ATR")
    assert req.trailing_stop_mode == "ATR"
    # And ATR genuinely bypasses the basing-point rule rather than being a label.
    assert basing_point_applies("ATR", "LONG") is False
    assert basing_point_applies("ATR", "SHORT") is False


def test_the_endpoint_lets_a_caller_ask_for_the_basing_point_trail():
    """The other half of the #63 middle ground: the rule is reachable through
    the real endpoint, so it can be compared without flipping anyone's
    baseline. Without this, the only way to see it was to edit the source."""
    from app.models.schemas import BacktestRequest

    for mode in ("BASING_POINT", "BASING_POINT_LONG_ONLY"):
        req = BacktestRequest(ticker="VCB", start_date=date(2026, 1, 1),
                              end_date=date(2026, 3, 1), trailing_stop_mode=mode)
        assert req.trailing_stop_mode == mode
