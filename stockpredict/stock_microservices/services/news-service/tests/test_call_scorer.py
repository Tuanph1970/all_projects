"""Forward-return scoring of TCBS calls (FR-BM-SCORE, FR-BM-RECORD, EC-B7).

The three properties these exist to hold down:

  * horizons count **trading sessions**, taken from the price series' own dates;
  * a horizon that has not elapsed stays NULL — never a partial or extrapolated fill;
  * the index-relative return spans the **same two dates** as the absolute one.

Fixtures are hand-computed, per SRS §5.4 — no magic numbers copied out of the code.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.ingest.price_history import PriceSeries
from app.services.call_scorer import (
    CallScorer,
    build_record,
    score_call,
)

CALL_DATE = date(2026, 9, 21)


def series(closes, *, start=CALL_DATE, symbol="NTP", adjusted=False, skip=()):
    """A synthetic daily series starting at `start`, one bar per weekday.

    `skip` names offsets to omit, which simulates a halted stock — the case that
    separates "N sessions later" from "N calendar days later".
    """
    dates, values, d, i = [], [], start, 0
    while len(dates) < len(closes):
        if d.weekday() < 5:
            if i not in skip:
                dates.append(d)
                values.append(closes[len(dates) - 1])
            i += 1
        d += timedelta(days=1)
    return PriceSeries(symbol=symbol, dates=tuple(dates), closes=tuple(values),
                       adjusted=adjusted)


# ---------------------------------------------------------------------------
# Absolute returns
# ---------------------------------------------------------------------------

def test_returns_are_hand_computable_at_each_horizon():
    # ref = 100 at the call session; +1%, +5%, +20%, +60% at the four horizons.
    closes = [100.0] + [100.0] * 60
    closes[1] = 101.0     # 1 session later
    closes[5] = 105.0     # 5 sessions later
    closes[20] = 120.0
    closes[60] = 160.0
    score = score_call(session_date=CALL_DATE, prices=series(closes))

    assert score.ref_close == 100.0
    assert score.ref_date == CALL_DATE
    assert score.returns[1] == pytest.approx(0.01)
    assert score.returns[5] == pytest.approx(0.05)
    assert score.returns[20] == pytest.approx(0.20)
    assert score.returns[60] == pytest.approx(0.60)
    assert score.complete


def test_a_losing_call_scores_negative():
    closes = [100.0] + [90.0] * 60
    score = score_call(session_date=CALL_DATE, prices=series(closes))
    assert score.returns[1] == pytest.approx(-0.10)
    assert score.returns[60] == pytest.approx(-0.10)


# ---------------------------------------------------------------------------
# Rule 2 — no forward-looking fill
# ---------------------------------------------------------------------------

def test_an_unelapsed_horizon_stays_none():
    """Only 6 sessions exist: 1d and 5d fill, 20d and 60d must stay NULL."""
    score = score_call(session_date=CALL_DATE, prices=series([100.0, 101, 102, 103, 104, 105]))
    assert score.returns[1] == pytest.approx(0.01)
    assert score.returns[5] == pytest.approx(0.05)
    assert score.returns[20] is None
    assert score.returns[60] is None
    assert not score.complete
    assert score.any_scored


def test_the_last_available_bar_is_never_used_as_a_proxy_for_a_later_horizon():
    """The failure mode this rule exists for: 10 sessions of data must not let a 20- or
    60-session horizon quietly report the 10-session move as if the horizon had run."""
    closes = [100.0] + [130.0] * 9        # a big move, 10 bars total
    score = score_call(session_date=CALL_DATE, prices=series(closes))
    assert score.returns[5] == pytest.approx(0.30)
    assert score.returns[20] is None and score.returns[60] is None


def test_exactly_enough_bars_fills_the_horizon_and_not_one_less():
    """Boundary: ref + 5 must be the 6th bar, so 6 bars fill 5d and 5 bars do not."""
    assert score_call(session_date=CALL_DATE,
                      prices=series([100.0] * 6)).returns[5] is not None
    assert score_call(session_date=CALL_DATE,
                      prices=series([100.0] * 5)).returns[5] is None


def test_no_price_history_at_or_before_the_call_scores_nothing():
    later = series([100.0] * 60, start=CALL_DATE + timedelta(days=30))
    score = score_call(session_date=CALL_DATE, prices=later)
    assert score.ref_close is None
    assert all(v is None for v in score.returns.values())


# ---------------------------------------------------------------------------
# Rule 1 — sessions, not calendar days
# ---------------------------------------------------------------------------

def test_horizons_count_sessions_so_weekends_do_not_shorten_them():
    """The 5th session after a Monday call is the following Monday, not that Saturday."""
    score = score_call(session_date=CALL_DATE, prices=series([100.0] + [110.0] * 10))
    assert CALL_DATE.weekday() == 0                       # the call lands on a Monday
    assert score.returns[5] == pytest.approx(0.10)


def test_a_halted_stock_counts_its_own_sessions():
    """Bars 1-3 are missing (halt). The '5 sessions later' bar is therefore the 5th bar
    that actually traded, not the calendar day five sessions out."""
    closes = [100.0] + [100.0] * 20
    halted = series(closes, skip=(1, 2, 3))
    score = score_call(session_date=CALL_DATE, prices=halted)
    assert score.returns[5] is not None
    assert halted.dates[5] > CALL_DATE + timedelta(days=7)


def test_reference_falls_back_to_the_last_close_before_the_call():
    """If the symbol did not trade on the session the mail describes, the honest
    reference is the last price actually known when the mail was published."""
    # Bars on the two sessions before the call, then a gap over the call date itself.
    gapped = PriceSeries(
        symbol="NTP",
        dates=(CALL_DATE - timedelta(days=4), CALL_DATE - timedelta(days=3),
               CALL_DATE + timedelta(days=2), CALL_DATE + timedelta(days=3)),
        closes=(99.0, 100.0, 110.0, 120.0),
        adjusted=False,
    )
    score = score_call(session_date=CALL_DATE, prices=gapped)
    assert score.ref_date == CALL_DATE - timedelta(days=3)
    assert score.ref_close == 100.0
    assert score.returns[1] == pytest.approx(0.10)   # next bar that actually traded


# ---------------------------------------------------------------------------
# Rule 3 — index-relative over the same window
# ---------------------------------------------------------------------------

def test_excess_return_is_stock_minus_index_over_the_same_dates():
    stock = series([100.0] + [110.0] * 60)                       # +10%
    index = series([1000.0] + [1040.0] * 60, symbol="VNINDEX")   # +4%
    score = score_call(session_date=CALL_DATE, prices=stock, index=index)
    assert score.returns[1] == pytest.approx(0.10)
    assert score.excess[1] == pytest.approx(0.06)
    assert score.excess[60] == pytest.approx(0.06)


def test_a_stock_that_rose_less_than_the_index_has_negative_excess():
    stock = series([100.0] + [102.0] * 30)
    index = series([1000.0] + [1050.0] * 30, symbol="VNINDEX")
    score = score_call(session_date=CALL_DATE, prices=stock, index=index)
    assert score.returns[20] > 0
    assert score.excess[20] == pytest.approx(0.02 - 0.05)


def test_excess_uses_the_halted_stocks_dates_not_its_positions():
    """The stock is halted for 3 sessions, so its 5th bar is the index's 8th. The excess
    must compare the index across the stock's two *dates* — using the index's own 5th
    position instead would silently measure a shorter window for the benchmark."""
    stock = series([100.0] + [110.0] * 20, skip=(1, 2, 3))
    index_closes = [1000.0] + [1000.0 + 10 * i for i in range(1, 21)]
    index = series(index_closes, symbol="VNINDEX")
    score = score_call(session_date=CALL_DATE, prices=stock, index=index)

    end_date = stock.dates[5]
    j = index.dates.index(end_date)
    expected_index_move = index.closes[j] / index.closes[0] - 1
    assert score.excess[5] == pytest.approx(0.10 - expected_index_move)
    # And that really is a longer window than the index's own 5th bar.
    assert j > 5


def test_excess_is_none_when_the_index_is_unavailable():
    score = score_call(session_date=CALL_DATE, prices=series([100.0] * 61), index=None)
    assert all(v is None for v in score.excess.values())
    assert score.returns[1] is not None      # absolute scoring still happens


def test_excess_is_none_for_a_horizon_the_index_cannot_cover():
    stock = series([100.0] + [110.0] * 60)
    short_index = series([1000.0] * 3, symbol="VNINDEX")
    score = score_call(session_date=CALL_DATE, prices=stock, index=short_index)
    assert score.returns[60] is not None
    assert score.excess[60] is None          # no index bar that far out — not faked


# ---------------------------------------------------------------------------
# The scheduled job
# ---------------------------------------------------------------------------

class FakeReco:
    def __init__(self, reco_id, symbol):
        self.id = reco_id
        self.symbol = symbol


class FakeRepo:
    def __init__(self, pending):
        self._pending = pending
        self.saved = {}
        self.retired = []

    def list_unscored(self, limit=500):
        return self._pending

    def save_score(self, reco_id, score, *, scoring_done=False):
        self.saved[reco_id] = (score, scoring_done)

    def mark_scoring_done(self, reco_id):
        self.retired.append(reco_id)


class FakePrices:
    def __init__(self, by_symbol):
        self._by_symbol = by_symbol
        self.requested = []

    def history(self, symbol, start, end):
        self.requested.append((symbol, start, end))
        from app.ingest.price_history import PriceUnavailableError
        if symbol not in self._by_symbol:
            raise PriceUnavailableError(f"no data for {symbol}")
        return self._by_symbol[symbol]


@pytest.mark.asyncio
async def test_tick_scores_pending_calls():
    repo = FakeRepo([(FakeReco(1, "NTP"), CALL_DATE)])
    prices = FakePrices({
        "NTP": series([100.0] + [110.0] * 60),
        "VNINDEX": series([1000.0] + [1000.0] * 60, symbol="VNINDEX"),
    })
    result = await CallScorer(repo, prices).tick(today=CALL_DATE + timedelta(days=200))

    assert result["considered"] == 1 and result["scored"] == 1 and result["completed"] == 1
    score, done = repo.saved[1]
    assert score.returns[20] == pytest.approx(0.10)
    assert done is True                       # every horizon filled -> stop revisiting


@pytest.mark.asyncio
async def test_a_partially_scored_call_is_not_retired():
    repo = FakeRepo([(FakeReco(1, "NTP"), CALL_DATE)])
    prices = FakePrices({"NTP": series([100.0] + [101.0] * 5)})
    result = await CallScorer(repo, prices).tick(today=CALL_DATE + timedelta(days=7))

    score, done = repo.saved[1]
    assert score.returns[5] is not None and score.returns[20] is None
    assert done is False                      # 20d/60d still to come
    assert result["completed"] == 0 and result["scored"] == 1


@pytest.mark.asyncio
async def test_one_index_fetch_serves_the_whole_batch():
    pending = [(FakeReco(i, s), CALL_DATE) for i, s in enumerate(["NTP", "MSN", "OIL"], 1)]
    repo = FakeRepo(pending)
    prices = FakePrices({s: series([100.0] * 61, symbol=s)
                         for s in ("NTP", "MSN", "OIL", "VNINDEX")})
    await CallScorer(repo, prices).tick(today=CALL_DATE + timedelta(days=120))

    assert [s for s, _, _ in prices.requested].count("VNINDEX") == 1


@pytest.mark.asyncio
async def test_a_price_outage_defers_and_never_raises():
    repo = FakeRepo([(FakeReco(1, "GONE"), CALL_DATE)])
    result = await CallScorer(repo, FakePrices({})).tick(today=CALL_DATE + timedelta(days=5))

    assert result["unavailable"] == ["GONE"]
    assert repo.saved == {}
    assert repo.retired == []            # recent call — a transient outage must not retire it


@pytest.mark.asyncio
async def test_an_unpriceable_call_is_retired_only_once_its_window_has_long_closed():
    repo = FakeRepo([(FakeReco(1, "DELISTED"), CALL_DATE)])
    result = await CallScorer(repo, FakePrices({})).tick(today=CALL_DATE + timedelta(days=500))

    assert repo.retired == [1] and result["gave_up"] == 1


@pytest.mark.asyncio
async def test_a_stale_call_that_can_never_complete_stops_being_revisited():
    """A symbol whose series simply stops — scored as far as it goes, then retired."""
    repo = FakeRepo([(FakeReco(1, "THIN"), CALL_DATE)])
    prices = FakePrices({"THIN": series([100.0] + [105.0] * 5)})
    await CallScorer(repo, prices).tick(today=CALL_DATE + timedelta(days=500))

    score, done = repo.saved[1]
    assert score.returns[5] is not None and score.returns[60] is None
    assert done is True


@pytest.mark.asyncio
async def test_scoring_still_runs_when_the_index_is_unavailable():
    repo = FakeRepo([(FakeReco(1, "NTP"), CALL_DATE)])
    prices = FakePrices({"NTP": series([100.0] + [110.0] * 60)})   # no VNINDEX
    result = await CallScorer(repo, prices).tick(today=CALL_DATE + timedelta(days=120))

    score, _ = repo.saved[1]
    assert score.returns[20] is not None
    assert score.excess[20] is None
    assert result["scored"] == 1


@pytest.mark.asyncio
async def test_an_empty_queue_is_a_cheap_noop():
    prices = FakePrices({})
    result = await CallScorer(FakeRepo([]), prices).tick(today=CALL_DATE)
    assert result["considered"] == 0
    assert prices.requested == []       # not even the index is fetched


# ---------------------------------------------------------------------------
# The track record (FR-BM-RECORD, EC-B7)
# ---------------------------------------------------------------------------

def _row(action, ret, excess=None):
    return (action, {1: ret, 5: ret, 20: ret, 60: ret},
            {1: excess, 5: excess, 20: excess, 60: excess})


def test_record_refuses_to_report_below_the_minimum():
    record = build_record([_row("BUY", 0.05) for _ in range(29)], min_calls=30)
    assert record["reportable"] is False
    assert record["scored_calls"] == 29
    assert record["horizons"] == {}      # nothing is published, not even partially


def test_record_reports_at_the_minimum():
    record = build_record([_row("BUY", 0.05) for _ in range(30)], min_calls=30)
    assert record["reportable"] is True
    assert record["horizons"]["20d"]["n"] == 30


def test_unscored_calls_do_not_count_towards_the_minimum():
    rows = [_row("BUY", 0.05) for _ in range(20)] + [_row("BUY", None) for _ in range(20)]
    record = build_record(rows, min_calls=30)
    assert record["total_calls"] == 40
    assert record["scored_calls"] == 20
    assert record["reportable"] is False


def test_hit_rate_counts_direction_per_action():
    rows = ([_row("BUY", 0.05) for _ in range(20)]      # right
            + [_row("BUY", -0.05) for _ in range(10)]   # wrong
            + [_row("SELL", -0.05) for _ in range(10)])  # right: a fall is a good SELL
    record = build_record(rows, min_calls=30)
    assert record["horizons"]["20d"]["directional_n"] == 40
    assert record["horizons"]["20d"]["hit_rate"] == pytest.approx(30 / 40)


def test_hold_and_watch_are_excluded_from_the_hit_rate():
    """They assert no direction, so scoring them as right or wrong would invent a
    prediction the desk never made — but their returns are still reported."""
    rows = [_row("BUY", 0.05) for _ in range(30)] + [_row("WATCH", -0.20) for _ in range(10)]
    record = build_record(rows, min_calls=30)
    assert record["horizons"]["20d"]["directional_n"] == 30
    assert record["horizons"]["20d"]["hit_rate"] == pytest.approx(1.0)
    assert record["by_action"]["WATCH"]["n"] == 10
    assert record["by_action"]["WATCH"]["horizons"]["20d"]["mean_return"] == pytest.approx(-0.20)


def test_the_benchmark_travels_beside_the_hit_rate():
    """EC-B7 / C4: a hit rate alone is not evidence. Here TCB is right 100% of the time,
    but so was simply buying the index — excess is zero, so there is no skill shown."""
    rows = [_row("BUY", 0.05, excess=0.0) for _ in range(30)]
    h = build_record(rows, min_calls=30)["horizons"]["20d"]
    assert h["hit_rate"] == pytest.approx(1.0)
    assert h["benchmark_hit_rate"] == pytest.approx(1.0)
    assert h["mean_excess_return"] == pytest.approx(0.0)


def test_a_call_that_beat_the_index_shows_positive_excess_and_a_losing_benchmark():
    """TCB's BUYs rose 5% while the index fell 2% — right call, benchmark wrong."""
    rows = [_row("BUY", 0.05, excess=0.07) for _ in range(30)]
    h = build_record(rows, min_calls=30)["horizons"]["20d"]
    assert h["hit_rate"] == pytest.approx(1.0)
    assert h["benchmark_hit_rate"] == pytest.approx(0.0)
    assert h["mean_excess_return"] == pytest.approx(0.07)


def test_mean_return_ignores_unfilled_horizons():
    rows = [("BUY", {1: 0.10, 5: 0.10, 20: None, 60: None}, {1: None, 5: None, 20: None, 60: None})
            for _ in range(30)]
    record = build_record(rows, min_calls=30)
    assert record["horizons"]["1d"]["n"] == 30
    assert record["horizons"]["20d"]["n"] == 0
    assert record["horizons"]["20d"]["mean_return"] is None
    assert record["horizons"]["20d"]["hit_rate"] is None


# ---------------------------------------------------------------------------
# End to end against the real repository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scorer_drives_the_real_repository_end_to_end():
    """FakeRepo above could drift from TcbRepository's actual interface, so run one
    pass against the real thing: parse a real email, store it, score it, read it back."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from pathlib import Path

    from app.ingest.tcb_mail_parser import parse_tcb_mail
    from app.repositories.tcb_repository import TcbRepository

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    repo = TcbRepository(engine)
    repo.ensure_schema()

    raw = (Path(__file__).parent / "fixtures" / "tcb_mail_1.txt").read_text(encoding="utf-8")
    repo.save(parse_tcb_mail(raw, reference_date=CALL_DATE), raw=raw, session_date=CALL_DATE)

    assert [r.symbol for r, _ in repo.list_unscored()] == ["NTP"]

    prices = FakePrices({
        "NTP": series([100.0] + [110.0] * 60),
        "VNINDEX": series([1000.0] + [1020.0] * 60, symbol="VNINDEX"),
    })
    result = await CallScorer(repo, prices).tick(today=CALL_DATE + timedelta(days=120))
    assert result == {"considered": 1, "scored": 1, "completed": 1,
                      "gave_up": 0, "unavailable": []}

    (reco, _), = repo.list_recos(symbol="NTP")
    assert reco.ref_close == pytest.approx(100.0)
    assert reco.ret_20d == pytest.approx(0.10)
    assert reco.ret_20d_vs_index == pytest.approx(0.08)   # 10% stock - 2% index
    assert reco.scoring_done is True and reco.scored_at is not None

    # Completed calls leave the queue, so the next tick is free.
    assert repo.list_unscored() == []
    assert (await CallScorer(repo, prices).tick(today=CALL_DATE))["considered"] == 0
