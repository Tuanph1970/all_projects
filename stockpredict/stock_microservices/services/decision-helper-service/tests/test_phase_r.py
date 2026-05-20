"""Tests for Phase R — Journal sync (F-170..F-173)."""
from __future__ import annotations

import pytest
from datetime import date, datetime
from typing import Optional

from app.models.schemas import (
    JournalSyncStatus,
    UserRiskPrefsRequest,
    UserRiskPrefsResponse,
    RecommendationResponse,
)


# ---------------------------------------------------------------------------
# F-170 — JournalSyncStatus schema
# ---------------------------------------------------------------------------

class TestJournalSyncStatus:
    def test_open_pending(self):
        s = JournalSyncStatus(synced=False, action="open")
        assert s.synced is False
        assert s.action == "open"
        assert s.journal_trade_id is None

    def test_open_success(self):
        s = JournalSyncStatus(synced=True, action="open", journal_trade_id=42)
        assert s.synced is True
        assert s.journal_trade_id == 42

    def test_close_pending(self):
        s = JournalSyncStatus(synced=False, action="close", journal_trade_id=7)
        assert s.action == "close"
        assert s.journal_trade_id == 7

    def test_none_action(self):
        s = JournalSyncStatus(synced=False, action="none")
        assert s.action == "none"

    def test_error_field(self):
        s = JournalSyncStatus(synced=False, action="open", error="Connection refused")
        assert "Connection refused" in s.error


# ---------------------------------------------------------------------------
# F-171 — UserRiskPrefs journal_account_id field
# ---------------------------------------------------------------------------

class TestUserRiskPrefsJournalField:
    def test_request_accepts_journal_account_id(self):
        req = UserRiskPrefsRequest(
            account_equity=100000,
            journal_account_id=5,
        )
        assert req.journal_account_id == 5

    def test_request_journal_account_id_optional(self):
        req = UserRiskPrefsRequest(account_equity=100000)
        assert req.journal_account_id is None

    def test_response_includes_journal_account_id(self):
        resp = UserRiskPrefsResponse(
            user_id=1,
            account_equity=100000,
            risk_per_trade_pct=1.0,
            max_concurrent_positions=5,
            max_correlation=0.7,
            loss_streak_size_cut=0.5,
            loss_streak_threshold=3,
            journal_account_id=3,
            updated_at=datetime(2025, 5, 1),
        )
        assert resp.journal_account_id == 3

    def test_response_journal_account_id_nullable(self):
        resp = UserRiskPrefsResponse(
            user_id=1,
            account_equity=100000,
            risk_per_trade_pct=1.0,
            max_concurrent_positions=5,
            max_correlation=0.7,
            loss_streak_size_cut=0.5,
            loss_streak_threshold=3,
            updated_at=datetime(2025, 5, 1),
        )
        assert resp.journal_account_id is None


# ---------------------------------------------------------------------------
# F-172 — RecommendationResponse journal_sync field
# ---------------------------------------------------------------------------

class TestRecommendationJournalSync:
    def _rec(self, action="WAIT", state_before="FLAT", state_after="FLAT", **kw):
        return RecommendationResponse(
            user_id=1, ticker="VIC",
            bar_date=date(2025, 5, 1),
            trigger="ON_DEMAND",
            regime="TREND_UP",
            action=action,
            state_before=state_before,
            state_after=state_after,
            confidence=0.0,
            **kw,
        )

    def test_no_journal_sync_by_default(self):
        rec = self._rec()
        assert rec.journal_sync is None

    def test_journal_sync_populated_for_buy(self):
        rec = self._rec(
            action="BUY",
            state_after="LONG",
            entry_price=50.0,
            stop_price=47.0,
            journal_sync=JournalSyncStatus(synced=False, action="open"),
        )
        assert rec.journal_sync is not None
        assert rec.journal_sync.action == "open"

    def test_journal_sync_populated_for_sell(self):
        rec = self._rec(
            action="SELL",
            state_before="LONG",
            state_after="FLAT",
            journal_sync=JournalSyncStatus(
                synced=False, action="close", journal_trade_id=99
            ),
        )
        assert rec.journal_sync.journal_trade_id == 99

    def test_journal_sync_none_for_hold(self):
        rec = self._rec(action="HOLD", journal_sync=None)
        assert rec.journal_sync is None


# ---------------------------------------------------------------------------
# F-173 — Journal sync payload construction logic
# ---------------------------------------------------------------------------

class TestJournalPayloadConstruction:
    """Mirrors the payload built in open_journal_trade()."""

    def _payload(self, action, ticker, entry_date, entry_price, initial_stop,
                 position_size, signal_kind=None):
        direction = "Long" if action == "BUY" else "Short"
        return {
            "entry_date": str(entry_date),
            "market_ticker": ticker,
            "direction": direction,
            "entry_price": entry_price,
            "entry_type": "Market",
            "initial_stop": initial_stop,
            "position_size": float(position_size),
            "commission": 0.0,
            "entry_reason": f"Auto-sync from decision-helper ({signal_kind or 'signal'})",
        }

    def test_buy_produces_long(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 100)
        assert p["direction"] == "Long"

    def test_sell_short_produces_short(self):
        p = self._payload("SELL_SHORT", "VIC", date(2025, 5, 1), 50.0, 53.0, 100)
        assert p["direction"] == "Short"

    def test_entry_price_and_stop(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 200)
        assert p["entry_price"] == 50.0
        assert p["initial_stop"] == 47.0

    def test_position_size_is_float(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 150)
        assert isinstance(p["position_size"], float)
        assert p["position_size"] == 150.0

    def test_commission_default_zero(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 100)
        assert p["commission"] == 0.0

    def test_signal_kind_in_entry_reason(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 100, signal_kind="MA_CROSS")
        assert "MA_CROSS" in p["entry_reason"]

    def test_no_signal_kind_fallback(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 100)
        assert "signal" in p["entry_reason"]

    def test_date_is_string(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 100)
        assert p["entry_date"] == "2025-05-01"

    def test_entry_type_market(self):
        p = self._payload("BUY", "VIC", date(2025, 5, 1), 50.0, 47.0, 100)
        assert p["entry_type"] == "Market"


class TestJournalCloseParams:
    """Mirrors close_journal_trade() query-param construction."""

    def _close_params(self, exit_price, exit_date, outcome=None):
        reason = f"Auto-sync: {outcome}" if outcome else "Auto-sync: position closed"
        return {
            "exit_price": exit_price,
            "exit_date": str(exit_date),
            "exit_reason": reason,
        }

    def test_win_outcome_in_reason(self):
        p = self._close_params(56.0, date(2025, 5, 10), outcome="WIN")
        assert "WIN" in p["exit_reason"]

    def test_loss_outcome_in_reason(self):
        p = self._close_params(47.0, date(2025, 5, 10), outcome="LOSS")
        assert "LOSS" in p["exit_reason"]

    def test_no_outcome_fallback(self):
        p = self._close_params(50.0, date(2025, 5, 10))
        assert p["exit_reason"] == "Auto-sync: position closed"

    def test_exit_price_preserved(self):
        p = self._close_params(56.25, date(2025, 5, 10))
        assert p["exit_price"] == 56.25

    def test_exit_date_is_string(self):
        p = self._close_params(50.0, date(2025, 6, 1))
        assert p["exit_date"] == "2025-06-01"
