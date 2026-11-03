"""Backlog #118 — `get_narrative` assembled end to end, with bars injected.

`_fetch_historical_data` is patched so these tests never touch
stock-data-service. What is under test is the ASSEMBLY: that the sections are
built from one frame, that the chart agrees with the text, and that the two
helper return-orders this file has already been bitten by stay fixed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from app.services.analysis_service import AnalysisService


def _bars(n=320, start=50.0, drift=0.0, seed=118, last_close=None, gap_at=None,
          noise=0.3):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    price, rows = start, []
    for i in range(n):
        price = max(1.0, price * (1 + drift) + rng.normal(0, noise))
        if gap_at is not None and i == gap_at:
            price = price / 1.5          # a 3-for-2 stock dividend
        rows.append({
            "date": dates[i], "open": price, "high": price * 1.02,
            "low": price * 0.98, "close": price,
            "volume": float(rng.integers(500_000, 2_000_000)),
        })
    df = pd.DataFrame(rows)
    if last_close is not None:
        df.loc[df.index[-1], ["open", "high", "low", "close"]] = [
            last_close, last_close * 1.01, last_close * 0.99, last_close]
    return df


def _svc(df):
    svc = AnalysisService(AsyncMock())
    svc._fetch_historical_data = AsyncMock(return_value=df)
    return svc


def _find(resp, code):
    for s in resp.sections:
        for f in s.findings:
            if f.code == code:
                return f
    return None


def _codes(resp):
    return {f.code for s in resp.sections for f in s.findings}


# ---------------------------------------------------------------------------
# The two return-order traps
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_lower_bollinger_reading_is_the_lower_band_not_the_middle():
    """_calculate_bollinger returns (upper, LOWER, middle).

    Unpacked in the natural visual order -- upper, middle, lower -- the SMA
    binds to the lower band and every "price is at the lower band" reading
    fires at the middle band instead. That mistake does NOT raise, so only an
    assertion on the number can catch it.
    """
    # The bands must be computed from the FINAL frame, not from one before the
    # last close is moved: the last bar is INSIDE the 20-bar window, so
    # changing it shifts both the mean and the standard deviation. My first
    # version of this test pre-computed the band, then moved the close, and
    # then asserted against a band that no longer existed -- the test failed
    # while the code was right.
    probe = _bars(n=320, start=50.0)
    rough = float(probe["close"].astype(float).rolling(20).mean().iloc[-1])
    df = _bars(n=320, start=50.0, last_close=rough * 0.85)

    closes = df["close"].astype(float)
    sma = float(closes.rolling(20).mean().iloc[-1])
    std = float(closes.rolling(20).std().iloc[-1])
    lower = sma - 2 * std

    resp = await _svc(df).get_narrative("TEST")
    f = _find(resp, "narrative.indicator.bb_lower")
    assert f is not None, f"no lower-band reading; got {_codes(resp)}"
    assert f.params["lower"] == pytest.approx(round(lower, 2), abs=0.05), (
        f"the reported band {f.params['lower']} is not the lower band "
        f"{lower:.2f} (middle is {sma:.2f})")
    # The assertion that actually kills the mix-up: the reported figure must be
    # a long way below the middle band, which the SMA by definition is not.
    assert f.params["lower"] < sma - std, (
        f"reported {f.params['lower']} looks like the middle band {sma:.2f}, "
        f"not the lower band {lower:.2f}")


@pytest.mark.asyncio
async def test_the_macd_reading_carries_both_a_value_and_its_signal():
    """_calculate_macd returns exactly two values. Unpacking three raises, so
    this would have been caught — but it pins the contract either way."""
    resp = await _svc(_bars()).get_narrative("TEST")
    f = next((_find(resp, c) for c in ("narrative.indicator.macd_bullish",
                                       "narrative.indicator.macd_bearish")
              if _find(resp, c)), None)
    assert f is not None, _codes(resp)
    assert "value" in f.params and "signal" in f.params
    assert f.params["value"] != f.params["signal"]


# ---------------------------------------------------------------------------
# The honesty gate, end to end
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_unadjusted_corporate_action_blocks_the_plan():
    """#119 reaching all the way to the user-visible output.

    The narrator must not build entry/stop/target on levels that a stock
    dividend moved. It says so instead.
    """
    resp = await _svc(_bars(gap_at=250)).get_narrative("TEST")
    assert resp.data_ok is False
    assert _find(resp, "narrative.data.corporate_action_gap") is not None
    assert _find(resp, "narrative.strategy.contaminated") is not None
    # ...and emphatically does NOT offer a trade.
    for code in ("narrative.strategy.long_pullback", "narrative.strategy.sizing"):
        assert _find(resp, code) is None, f"{code} was offered on contaminated data"


@pytest.mark.asyncio
async def test_a_clean_window_says_so_and_is_allowed_a_plan():
    """Non-vacuity for the test above: the gate must not block everything."""
    resp = await _svc(_bars()).get_narrative("TEST")
    assert resp.data_ok is True
    assert _find(resp, "narrative.data.clean") is not None
    assert _find(resp, "narrative.strategy.contaminated") is None


@pytest.mark.asyncio
async def test_the_gap_is_caught_even_when_it_sits_in_the_warmup():
    """SMA 200 reaches back past the displayed window, so a corporate action
    off-chart still contaminates today's reading. The gate must look at the
    whole fetched frame, not just the bars the user can see."""
    df = _bars(n=320, gap_at=10)          # far outside a 180-bar display window
    resp = await _svc(df).get_narrative("TEST", period=180)
    assert resp.bars == 180
    assert resp.data_ok is False, "a gap in the warmup was not noticed"


# ---------------------------------------------------------------------------
# Internal consistency: the text and the chart describe the same bars
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_bars_are_fetched_exactly_once():
    """The reason this method exists instead of composing four endpoints.

    Four fetches can land on four different windows, and then the trend
    section and the levels section describe different last prices in the same
    paragraph.
    """
    svc = _svc(_bars())
    await svc.get_narrative("TEST")
    assert svc._fetch_historical_data.await_count == 1


@pytest.mark.asyncio
async def test_every_level_named_in_the_text_is_also_drawn_on_the_chart():
    """A narrator that talks about support at 50.1 while the chart draws 51.5
    is worse than one that draws nothing."""
    resp = await _svc(_bars()).get_narrative("TEST")
    drawn = {round(l.price, 2) for l in resp.levels}
    for code in ("narrative.levels.nearest_support", "narrative.levels.nearest_resistance"):
        f = _find(resp, code)
        if f is not None:
            assert round(f.params["price"], 2) in drawn, (
                f"{code} names {f.params['price']} which is not in {drawn}")


@pytest.mark.asyncio
async def test_the_chart_ends_on_the_as_of_date():
    resp = await _svc(_bars()).get_narrative("TEST")
    assert resp.chart[-1].date == resp.as_of


@pytest.mark.asyncio
async def test_the_requested_period_bounds_the_chart_not_the_calculation():
    """A shorter chart must not shorten MA200 — the warmup is separate."""
    short = await _svc(_bars()).get_narrative("TEST", period=60)
    assert short.bars == 60
    assert short.chart[-1].ma200 is not None, "MA200 went missing on a short chart"


@pytest.mark.asyncio
async def test_too_little_history_returns_none_rather_than_a_thin_reading():
    assert await _svc(_bars(n=20)).get_narrative("TEST") is None
    assert await _svc(None).get_narrative("TEST") is None


@pytest.mark.asyncio
async def test_every_section_is_present_even_when_it_has_nothing_to_say():
    """A missing section would render as a gap in the page; an explicit
    "nothing here" is the honest version."""
    resp = await _svc(_bars()).get_narrative("TEST")
    assert [s.key for s in resp.sections] == [
        "data", "trend", "levels", "indicators", "patterns", "channel", "strategy"]
    for s in resp.sections:
        assert s.findings, f"section {s.key} is empty"


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_position_size_scales_with_the_risk_budget():
    """Sizing that ignores its own parameter is decorative."""
    # seed=1/drift=0 is chosen because it actually PRODUCES a plan (rr 2.15).
    # The first version of this test skipped itself when no plan appeared,
    # which meant it could pass for ever without once exercising sizing -- a
    # conditionally-skipped assertion is not an assertion.
    df = _bars(drift=0.0, seed=1)
    one = await _svc(df).get_narrative("TEST", capital=100_000_000, risk_pct=1.0)
    two = await _svc(df).get_narrative("TEST", capital=100_000_000, risk_pct=2.0)
    f1, f2 = _find(one, "narrative.strategy.sizing"), _find(two, "narrative.strategy.sizing")
    assert f1 is not None and f2 is not None, (
        f"the fixture stopped producing a plan: {_codes(one)}")
    assert f2.params["shares"] > f1.params["shares"], (
        f"doubling the risk budget did not change the size: "
        f"{f1.params['shares']} vs {f2.params['shares']}")
    # Doubling the budget doubles the size, within integer truncation.
    assert f2.params["shares"] == pytest.approx(2 * f1.params["shares"], rel=0.01)


@pytest.mark.asyncio
async def test_a_bigger_account_buys_more_of_the_same_setup():
    df = _bars(drift=0.0, seed=1)
    small = await _svc(df).get_narrative("TEST", capital=50_000_000, risk_pct=1.0)
    big = await _svc(df).get_narrative("TEST", capital=200_000_000, risk_pct=1.0)
    fs, fb = _find(small, "narrative.strategy.sizing"), _find(big, "narrative.strategy.sizing")
    assert fs and fb
    assert fb.params["shares"] > fs.params["shares"]
    # ...but the SHARE OF THE ACCOUNT committed is the same, because the risk
    # budget is a percentage. If this drifted, sizing would be reading capital
    # twice.
    assert fb.params["capital_pct"] == pytest.approx(fs.params["capital_pct"], rel=0.02)


@pytest.mark.asyncio
async def test_a_reported_plan_always_clears_the_minimum_reward_to_risk():
    """Either a plan is offered AND pays for its risk, or it is refused."""
    for seed in range(12):
        resp = await _svc(_bars(seed=seed, drift=0.001)).get_narrative("TEST")
        plan = _find(resp, "narrative.strategy.long_pullback")
        if plan is not None:
            assert plan.params["rr"] >= AnalysisService.NARRATIVE_MIN_RR, (
                f"seed {seed} offered a plan at {plan.params['rr']}:1")


@pytest.mark.asyncio
async def test_a_downtrend_is_flagged_as_trading_against_the_trend():
    """A FULL bearish stack needs the decline to dominate the noise.

    At drift=-0.002 with noise=0.3 the series ends on an up-tick, so price sat
    just ABOVE MA20 and the reading was correctly `below_200_mixed` rather than
    `down_full_stack`. The code was right and the fixture was not a downtrend
    by the definition being asserted.
    """
    resp = await _svc(_bars(drift=-0.004, seed=3, noise=0.05)).get_narrative("TEST")
    assert _find(resp, "narrative.trend.down_full_stack") is not None, _codes(resp)
    assert _find(resp, "narrative.strategy.against_trend") is not None


@pytest.mark.asyncio
async def test_a_pullback_above_the_200_is_not_called_a_downtrend():
    """The distinction the test above leans on, asserted from the other side."""
    resp = await _svc(_bars(drift=0.0015, seed=11, noise=0.05)).get_narrative("TEST")
    assert _find(resp, "narrative.trend.down_full_stack") is None, _codes(resp)


# ---------------------------------------------------------------------------
# The date window the owner asked for on the screen
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_end_date_truncates_before_the_indicators_are_computed():
    """C1 causality, and the easy way to get this wrong.

    Slicing only the CHART while leaving the indicators on the full series
    produces a reading of March that quietly knows how April turned out. The
    numbers must be identical to what the same request would have returned on
    end_date itself.
    """
    df = _bars(n=400, drift=0.001, seed=5, noise=0.05)
    cutoff = df["date"].iloc[300].strftime("%Y-%m-%d")

    as_of = await _svc(df).get_narrative("TEST", end_date=cutoff)
    # The same bars, with the future physically absent.
    truncated = df[df["date"] <= pd.Timestamp(cutoff)].reset_index(drop=True)
    honest = await _svc(truncated).get_narrative("TEST")

    assert as_of is not None and honest is not None
    assert as_of.as_of == honest.as_of == cutoff
    assert as_of.chart[-1].close == honest.chart[-1].close
    assert as_of.chart[-1].ma200 == honest.chart[-1].ma200, (
        "MA200 differs, so the truncated request saw bars past end_date")
    assert _codes(as_of) == _codes(honest), (
        "the readings differ, so something downstream saw the future")


@pytest.mark.asyncio
async def test_the_window_cannot_report_a_bar_after_its_end_date():
    df = _bars(n=400, seed=5)
    cutoff = df["date"].iloc[250].strftime("%Y-%m-%d")
    resp = await _svc(df).get_narrative("TEST", end_date=cutoff)
    assert all(b.date <= cutoff for b in resp.chart)


@pytest.mark.asyncio
async def test_start_date_moves_the_left_edge_of_the_chart():
    df = _bars(n=400, seed=5)
    begin = df["date"].iloc[300].strftime("%Y-%m-%d")
    resp = await _svc(df).get_narrative("TEST", start_date=begin)
    assert resp.chart[0].date >= begin
    assert all(b.date >= begin for b in resp.chart)


@pytest.mark.asyncio
async def test_a_short_window_still_has_a_real_ma200():
    """The warmup is not the window. `start_date` trims the DISPLAY; the 200
    bars before it are still fetched and still feed MA200. If they were not,
    a one-month window would render a blank long-term average -- which looks
    like 'no trend' rather than 'not asked for'."""
    df = _bars(n=400, seed=5)
    begin = df["date"].iloc[380].strftime("%Y-%m-%d")
    resp = await _svc(df).get_narrative("TEST", start_date=begin)
    assert len(resp.chart) <= 20
    assert resp.chart[0].ma200 is not None, "MA200 was lost on a short window"


@pytest.mark.asyncio
async def test_both_edges_together_bound_the_window():
    df = _bars(n=400, seed=5)
    begin = df["date"].iloc[200].strftime("%Y-%m-%d")
    cutoff = df["date"].iloc[300].strftime("%Y-%m-%d")
    resp = await _svc(df).get_narrative("TEST", start_date=begin, end_date=cutoff)
    assert resp.chart[0].date >= begin
    assert resp.chart[-1].date == cutoff


@pytest.mark.asyncio
async def test_a_malformed_date_is_ignored_rather_than_crashing():
    """A date picker can emit an empty string or a partial value mid-edit."""
    df = _bars(n=320, seed=5)
    for bad in ("", "not-a-date", "2026-13-99", "20260101"):
        resp = await _svc(df).get_narrative("TEST", start_date=bad, end_date=bad)
        assert resp is not None, f"{bad!r} broke the endpoint"


@pytest.mark.asyncio
async def test_a_window_with_too_few_bars_returns_none():
    df = _bars(n=400, seed=5)
    cutoff = df["date"].iloc[10].strftime("%Y-%m-%d")
    assert await _svc(df).get_narrative("TEST", end_date=cutoff) is None


@pytest.mark.asyncio
async def test_price_outside_the_channel_is_said_out_loud():
    """`position_pct` is clamped to 0..100, so a stock trading well BELOW its
    lower rail reports "0% of the way up" -- which reads as "at the bottom of
    the channel" when the truth is "out of the channel". Seen live on FPT and
    TCB before this finding existed."""
    # THE FIXTURE HAS TO SATISFY TWO CONSTRAINTS AT ONCE, and my first attempt
    # satisfied neither. Collapsing the last bar outright created an -82%
    # move, so the #119 gap gate fired instead (correctly) and the plan was
    # refused before the channel was read. And a near-noiseless drift has no
    # interior swing pivots, so `price_channel` returned None -- there was no
    # channel to break out of. So: oscillate enough to FORM pivots, then walk
    # the last stretch down in legal daily steps.
    n = 400
    dates = pd.bdate_range("2024-01-01", periods=n)
    rows, price = [], 60.0
    for i in range(n):
        if i < n - 40:
            price = 60.0 + 0.05 * i + 3.0 * np.sin(i / 5.0)   # rising, swinging
        else:
            price *= 0.97                                      # -3%/day: legal
        rows.append({"date": dates[i], "open": price, "high": price * 1.01,
                     "low": price * 0.99, "close": price,
                     "volume": 1_000_000.0})
    df = pd.DataFrame(rows)
    resp = await _svc(df).get_narrative("TEST")
    assert resp.data_ok is True, "the fixture tripped the gap gate; steps too big"
    assert _find(resp, "narrative.channel.none") is None, (
        "the fixture produced no channel, so there is nothing to break out of")
    f = _find(resp, "narrative.channel.broken_below")
    assert f is not None, _codes(resp)
    assert f.severity == "bearish"
    assert f.params["distance_pct"] > 0


@pytest.mark.asyncio
async def test_a_price_inside_the_channel_is_not_reported_as_broken():
    """Non-vacuity: the finding must distinguish, not just fire."""
    resp = await _svc(_bars(n=400, seed=4, noise=0.05)).get_narrative("TEST")
    codes = _codes(resp)
    inside = not {"narrative.channel.broken_below",
                  "narrative.channel.broken_above"} & codes
    if "narrative.channel.none" not in codes:
        ch = _find(resp, "narrative.channel.rising") or \
             _find(resp, "narrative.channel.falling") or \
             _find(resp, "narrative.channel.flat")
        if ch and 0 < ch.params["position_pct"] < 100:
            assert inside, "a price inside the rails was called a break"
