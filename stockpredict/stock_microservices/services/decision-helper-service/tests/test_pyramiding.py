"""F-043 — Pyramiding guard rails (Schwager Ch 8, 14).

Additive entries to a *winning* position are allowed only under three guards:
  1. cumulative pyramid shares ≤ 50 % of the initial entry,
  2. each add tightens (never widens) the position stop,
  3. no adds after N consecutive losses.
"""
from __future__ import annotations

import pytest

from app.services.risk.pyramiding import PyramidDecision, evaluate_pyramid


def _long(**over):
    base = dict(
        direction="LONG",
        entry_price=100.0,
        current_close=110.0,        # in profit
        current_stop=95.0,
        initial_shares=100,
        pyramided_shares=0,
        proposed_add_shares=40,
        proposed_add_stop=104.0,    # tighter than current 95
        recent_losses=0,
        loss_streak_threshold=3,
    )
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_winning_long_add_allowed_and_tightens_stop():
    d = evaluate_pyramid(**_long())
    assert d.allowed is True
    assert d.add_shares == 40
    assert d.new_stop == 104.0           # tightened up toward price
    assert d.new_stop >= 95.0            # never widens


def test_winning_short_add_allowed_and_tightens_stop():
    d = evaluate_pyramid(
        direction="SHORT", entry_price=100.0, current_close=90.0,
        current_stop=105.0, initial_shares=100, pyramided_shares=0,
        proposed_add_shares=30, proposed_add_stop=96.0,  # tighter (lower) than 105
        recent_losses=0, loss_streak_threshold=3,
    )
    assert d.allowed is True
    assert d.add_shares == 30
    assert d.new_stop == 96.0            # tightened down toward price
    assert d.new_stop <= 105.0           # never widens


# ---------------------------------------------------------------------------
# Guard 1 — 50 % pyramid cap
# ---------------------------------------------------------------------------

def test_pyramid_cap_blocks_when_exhausted():
    d = evaluate_pyramid(**_long(pyramided_shares=50))  # already at 50% of 100
    assert d.allowed is False
    assert "max_pyramid" in d.guards_triggered


def test_pyramid_cap_clamps_oversized_add():
    # 30 already added (cap=50), proposed 40 → only 20 may be added.
    d = evaluate_pyramid(**_long(pyramided_shares=30, proposed_add_shares=40))
    assert d.allowed is True
    assert d.add_shares == 20
    assert "max_pyramid" in d.guards_triggered


# ---------------------------------------------------------------------------
# Guard 2 — never widen the stop
# ---------------------------------------------------------------------------

def test_stop_never_widens_long():
    # proposed add stop is LOWER (wider) than current → keep current stop.
    d = evaluate_pyramid(**_long(proposed_add_stop=90.0))
    assert d.allowed is True
    assert d.new_stop == 95.0            # unchanged, not widened to 90


def test_stop_never_widens_short():
    d = evaluate_pyramid(
        direction="SHORT", entry_price=100.0, current_close=90.0,
        current_stop=105.0, initial_shares=100, pyramided_shares=0,
        proposed_add_shares=30, proposed_add_stop=110.0,  # wider (higher)
        recent_losses=0, loss_streak_threshold=3,
    )
    assert d.allowed is True
    assert d.new_stop == 105.0           # unchanged, not widened to 110


# ---------------------------------------------------------------------------
# Guard 3 — no adds after a losing streak
# ---------------------------------------------------------------------------

def test_loss_streak_blocks_add():
    d = evaluate_pyramid(**_long(recent_losses=3, loss_streak_threshold=3))
    assert d.allowed is False
    assert "loss_streak" in d.guards_triggered


# ---------------------------------------------------------------------------
# Precondition — only add to winners
# ---------------------------------------------------------------------------

def test_long_not_in_profit_rejected():
    d = evaluate_pyramid(**_long(current_close=99.0))  # below entry
    assert d.allowed is False
    assert "not_winning" in d.guards_triggered


def test_short_not_in_profit_rejected():
    d = evaluate_pyramid(
        direction="SHORT", entry_price=100.0, current_close=101.0,  # above entry
        current_stop=105.0, initial_shares=100, pyramided_shares=0,
        proposed_add_shares=30, proposed_add_stop=99.0,
        recent_losses=0, loss_streak_threshold=3,
    )
    assert d.allowed is False
    assert "not_winning" in d.guards_triggered


def test_zero_initial_shares_rejected():
    d = evaluate_pyramid(**_long(initial_shares=0))
    assert d.allowed is False


# ---------------------------------------------------------------------------
# Harness wiring — _maybe_pyramid grows a winning position under guards
# ---------------------------------------------------------------------------

from datetime import date

import app.services.backtest.harness as H
from app.services.backtest.harness import BacktestConfig, _Position, _maybe_pyramid
from app.services.signal.base import OHLCVBar, RawSignal


def _cfg(**over):
    base = dict(ticker="VCB", start_date=date(2023, 1, 1), end_date=date(2023, 12, 31),
                allow_pyramiding=True)
    base.update(over)
    return BacktestConfig(**base)


def _winning_long_pos():
    return _Position(
        state="LONG", direction="LONG", entry_date=date(2023, 1, 2),
        entry_price=100.0, stop=95.0, target=130.0, shares=100, initial_shares=100,
    )


def _stub_signal_layer(monkeypatch, direction="LONG", accept=True, add_stop=104.0, add_shares=40):
    """Force a confirmed same-direction continuation signal and a fixed add size/stop."""
    sig = RawSignal(kind="N_DAY_BREAKOUT", direction=direction, confidence=0.8,
                    bar_date=date(2023, 6, 1), trigger_price=110.0, evidence={})
    monkeypatch.setattr(H, "_run_signals", lambda *a, **k: [sig])

    class _Conf:
        def __init__(self):
            self.signal = sig
            self.accepted = accept
            self.final_confidence = 0.8
    monkeypatch.setattr(H, "_best_confirmed", lambda *a, **k: _Conf() if accept else None)

    class _StopRes:
        stop_price = add_stop
    monkeypatch.setattr(H, "compute_initial_stop", lambda **k: _StopRes())

    class _SizeRes:
        shares = add_shares
    monkeypatch.setattr(H, "compute_size", lambda **k: _SizeRes())


def test_maybe_pyramid_adds_to_winner(monkeypatch):
    _stub_signal_layer(monkeypatch, add_stop=104.0, add_shares=40)
    pos = _winning_long_pos()
    bar = OHLCVBar(date=date(2023, 6, 1), open=110, high=112, low=109, close=110, volume=1_000_000)

    delta = _maybe_pyramid(pos, [bar], bar, "TREND_UP", atr=2.0, swings=None,
                           sr_data=None, rsi=60.0, equity=100_000.0, config=_cfg())

    assert pos.shares == 140                 # 100 + 40 add
    assert pos.pyramided_shares == 40
    assert pos.pyramided_shares <= 0.5 * pos.initial_shares  # 50% cap respected
    assert pos.stop == 104.0                 # tightened up toward price
    assert 100.0 < pos.entry_price < 110.0   # blended entry between old and add fill
    assert delta == -_cfg().commission


def test_maybe_pyramid_respects_cap(monkeypatch):
    # propose 80 but only 50 (50% of 100) allowed, and 10 already pyramided → 40 more.
    _stub_signal_layer(monkeypatch, add_shares=80)
    pos = _winning_long_pos()
    pos.pyramided_shares = 10
    pos.shares = 110
    bar = OHLCVBar(date=date(2023, 6, 1), open=110, high=112, low=109, close=110, volume=1_000_000)

    _maybe_pyramid(pos, [bar], bar, "TREND_UP", atr=2.0, swings=None,
                   sr_data=None, rsi=60.0, equity=100_000.0, config=_cfg())

    assert pos.pyramided_shares == 50        # 10 + 40 = the 50% cap
    assert pos.shares == 150


def test_maybe_pyramid_skipped_without_signal(monkeypatch):
    _stub_signal_layer(monkeypatch, accept=False)
    pos = _winning_long_pos()
    bar = OHLCVBar(date=date(2023, 6, 1), open=110, high=112, low=109, close=110, volume=1_000_000)

    delta = _maybe_pyramid(pos, [bar], bar, "TREND_UP", atr=2.0, swings=None,
                           sr_data=None, rsi=60.0, equity=100_000.0, config=_cfg())
    assert pos.shares == 100                 # unchanged
    assert delta == 0.0
