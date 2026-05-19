"""Tests for Phase M — Multi-ticker scanner (F-120..F-123)."""
from __future__ import annotations

import pytest
from app.models.schemas import ScanRequest, ScanResultItem, ScanResponse
from datetime import date


# ---------------------------------------------------------------------------
# F-120 — ScanRequest schema
# ---------------------------------------------------------------------------

class TestScanRequest:
    def test_no_date_defaults_to_none(self):
        req = ScanRequest()
        assert req.bar_date is None

    def test_explicit_date(self):
        req = ScanRequest(bar_date=date(2025, 5, 19))
        assert req.bar_date == date(2025, 5, 19)


# ---------------------------------------------------------------------------
# F-121 — ScanResultItem schema
# ---------------------------------------------------------------------------

class TestScanResultItem:
    def _item(self, **kw):
        defaults = dict(
            ticker="VIC", action="BUY", regime="TREND_UP",
            confidence=0.82, is_actionable=True,
        )
        return ScanResultItem(**{**defaults, **kw})

    def test_required_fields(self):
        item = self._item()
        assert item.ticker == "VIC"
        assert item.action == "BUY"
        assert item.regime == "TREND_UP"
        assert item.confidence == 0.82
        assert item.is_actionable is True

    def test_optional_prices_default_none(self):
        item = self._item()
        assert item.entry_price is None
        assert item.stop_price is None
        assert item.target_price is None
        assert item.position_size is None

    def test_optional_signal_fields(self):
        item = self._item()
        assert item.signal_kind is None
        assert item.signal_confirmed is False

    def test_error_field_optional(self):
        item = self._item()
        assert item.error is None

    def test_error_field_set(self):
        item = self._item(error="No OHLCV data for TICKER")
        assert "No OHLCV data" in item.error

    def test_actionable_true_for_buy(self):
        item = self._item(action="BUY", is_actionable=True)
        assert item.is_actionable is True

    def test_actionable_false_for_wait(self):
        item = self._item(action="WAIT", is_actionable=False)
        assert item.is_actionable is False

    def test_full_item(self):
        item = ScanResultItem(
            ticker="VCB",
            action="SELL_SHORT",
            regime="TREND_DOWN",
            confidence=0.75,
            entry_price=85.5,
            stop_price=90.0,
            target_price=76.0,
            position_size=100,
            signal_kind="MA_CROSS",
            signal_confirmed=True,
            is_actionable=True,
        )
        assert item.ticker == "VCB"
        assert item.stop_price == 90.0
        assert item.signal_confirmed is True


# ---------------------------------------------------------------------------
# F-121 — ScanResponse schema
# ---------------------------------------------------------------------------

class TestScanResponse:
    def _make(self, results=None):
        results = results or []
        actionable = sum(1 for r in results if r.is_actionable)
        return ScanResponse(
            bar_date=date(2025, 5, 19),
            ticker_count=len(results),
            actionable_count=actionable,
            results=results,
            latency_ms=420,
        )

    def test_empty_scan(self):
        resp = self._make()
        assert resp.ticker_count == 0
        assert resp.actionable_count == 0
        assert resp.results == []

    def test_scan_with_results(self):
        items = [
            ScanResultItem(ticker="VIC", action="BUY", regime="TREND_UP",
                           confidence=0.82, is_actionable=True),
            ScanResultItem(ticker="VCB", action="WAIT", regime="RANGE",
                           confidence=0.3, is_actionable=False),
        ]
        resp = self._make(items)
        assert resp.ticker_count == 2
        assert resp.actionable_count == 1
        assert resp.results[0].ticker == "VIC"

    def test_bar_date_preserved(self):
        resp = self._make()
        assert resp.bar_date == date(2025, 5, 19)

    def test_latency_ms_field(self):
        resp = self._make()
        assert resp.latency_ms == 420


# ---------------------------------------------------------------------------
# F-122 — Ranking logic (mirrors backend sort key)
# ---------------------------------------------------------------------------

class TestScannerRanking:
    """Validate the ranking rule: BUY/SELL_SHORT first, then confidence desc."""

    _ACTION_RANK = {
        "BUY": 0, "SELL_SHORT": 1, "COVER": 2,
        "REVERSE": 3, "HOLD": 4, "WAIT": 5,
    }

    def _sort(self, items):
        return sorted(items, key=lambda r: (self._ACTION_RANK.get(r["action"], 9), -r["confidence"]))

    def test_buy_before_wait(self):
        items = [
            {"action": "WAIT", "confidence": 0.9},
            {"action": "BUY", "confidence": 0.7},
        ]
        ranked = self._sort(items)
        assert ranked[0]["action"] == "BUY"

    def test_buy_before_sell_short(self):
        items = [
            {"action": "SELL_SHORT", "confidence": 0.8},
            {"action": "BUY", "confidence": 0.6},
        ]
        ranked = self._sort(items)
        assert ranked[0]["action"] == "BUY"

    def test_higher_confidence_first_within_same_action(self):
        items = [
            {"action": "BUY", "confidence": 0.6},
            {"action": "BUY", "confidence": 0.9},
        ]
        ranked = self._sort(items)
        assert ranked[0]["confidence"] == 0.9

    def test_full_ranking_order(self):
        items = [
            {"action": "WAIT",       "confidence": 0.1},
            {"action": "HOLD",       "confidence": 0.5},
            {"action": "SELL_SHORT", "confidence": 0.8},
            {"action": "BUY",        "confidence": 0.7},
        ]
        ranked = self._sort(items)
        actions = [r["action"] for r in ranked]
        assert actions == ["BUY", "SELL_SHORT", "HOLD", "WAIT"]


# ---------------------------------------------------------------------------
# F-123 — Frontend filter logic (mirrors ScannerPage filter)
# ---------------------------------------------------------------------------

class TestScannerFilter:
    def _items(self):
        return [
            {"action": "BUY",        "is_actionable": True},
            {"action": "SELL_SHORT", "is_actionable": True},
            {"action": "HOLD",       "is_actionable": False},
            {"action": "WAIT",       "is_actionable": False},
        ]

    def _apply(self, items, f):
        if f == "All":
            return items
        if f == "Actionable":
            return [i for i in items if i["is_actionable"]]
        return [i for i in items if i["action"] == f]

    def test_filter_all(self):
        assert len(self._apply(self._items(), "All")) == 4

    def test_filter_actionable(self):
        result = self._apply(self._items(), "Actionable")
        assert len(result) == 2
        assert all(r["is_actionable"] for r in result)

    def test_filter_buy(self):
        result = self._apply(self._items(), "BUY")
        assert len(result) == 1
        assert result[0]["action"] == "BUY"

    def test_filter_sell_short(self):
        result = self._apply(self._items(), "SELL_SHORT")
        assert len(result) == 1

    def test_filter_hold(self):
        result = self._apply(self._items(), "HOLD")
        assert len(result) == 1
        assert result[0]["action"] == "HOLD"
