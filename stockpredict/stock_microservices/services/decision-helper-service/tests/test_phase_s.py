"""Tests for Phase S — Risk dashboard (F-180..F-183)."""
from __future__ import annotations

import pytest
from datetime import date, datetime
from typing import Optional

from app.models.schemas import PositionRiskItem, RiskOverviewResponse


# ---------------------------------------------------------------------------
# F-180 — PositionRiskItem schema
# ---------------------------------------------------------------------------

class TestPositionRiskItem:
    def _item(self, **kw):
        defaults = dict(
            ticker="VIC",
            direction="LONG",
            entry_price=50.0,
            current_stop=47.0,
            position_size=100,
            risk_per_share=3.0,
            risk_amount=300.0,
            risk_pct_equity=0.3,
            days_held=5,
            entry_bar_date=date(2025, 5, 1),
        )
        defaults.update(kw)
        return PositionRiskItem(**defaults)

    def test_long_position(self):
        item = self._item(direction="LONG")
        assert item.direction == "LONG"
        assert item.risk_per_share == 3.0

    def test_short_position(self):
        item = self._item(direction="SHORT", entry_price=50.0, current_stop=53.0, risk_per_share=3.0)
        assert item.direction == "SHORT"

    def test_optional_fields_none(self):
        item = PositionRiskItem(ticker="VIC", direction="LONG", entry_price=50.0, position_size=100)
        assert item.current_stop is None
        assert item.risk_per_share is None
        assert item.risk_amount is None
        assert item.risk_pct_equity is None

    def test_days_held(self):
        item = self._item(days_held=10)
        assert item.days_held == 10

    def test_entry_bar_date(self):
        item = self._item(entry_bar_date=date(2025, 4, 1))
        assert item.entry_bar_date == date(2025, 4, 1)

    def test_risk_amount_computed(self):
        # risk_per_share × position_size
        item = self._item(risk_per_share=3.0, position_size=200, risk_amount=600.0)
        assert item.risk_amount == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# F-181 — RiskOverviewResponse schema
# ---------------------------------------------------------------------------

class TestRiskOverviewResponse:
    def _item(self, ticker="VIC", direction="LONG", pct=0.5):
        return PositionRiskItem(
            ticker=ticker, direction=direction,
            entry_price=50.0, position_size=100,
            risk_per_share=2.5, risk_amount=250.0,
            risk_pct_equity=pct,
        )

    def _resp(self, **kw):
        defaults = dict(
            user_id=1,
            computed_at=datetime(2025, 5, 1),
            account_equity=100000.0,
            total_positions=1,
            long_count=1,
            short_count=0,
            total_risk_amount=250.0,
            total_risk_pct=0.25,
            long_risk_pct=0.25,
            short_risk_pct=0.0,
            net_exposure_pct=0.25,
            max_drawdown_scenario=250.0,
            max_drawdown_pct=0.25,
            positions=[self._item()],
        )
        defaults.update(kw)
        return RiskOverviewResponse(**defaults)

    def test_basic_response(self):
        resp = self._resp()
        assert resp.total_positions == 1
        assert resp.long_count == 1
        assert resp.short_count == 0

    def test_empty_positions(self):
        resp = self._resp(total_positions=0, long_count=0, short_count=0,
                          total_risk_amount=0.0, total_risk_pct=0.0,
                          long_risk_pct=0.0, short_risk_pct=0.0,
                          net_exposure_pct=0.0, max_drawdown_scenario=0.0,
                          max_drawdown_pct=0.0, positions=[])
        assert resp.positions == []

    def test_mixed_positions(self):
        resp = self._resp(
            total_positions=2, long_count=1, short_count=1,
            positions=[self._item("VIC", "LONG"), self._item("VCB", "SHORT")],
        )
        assert len(resp.positions) == 2

    def test_no_equity(self):
        resp = self._resp(account_equity=None)
        assert resp.account_equity is None

    def test_net_exposure_long_biased(self):
        resp = self._resp(long_risk_pct=2.0, short_risk_pct=0.5, net_exposure_pct=1.5)
        assert resp.net_exposure_pct == pytest.approx(1.5)

    def test_net_exposure_short_biased(self):
        resp = self._resp(long_risk_pct=0.5, short_risk_pct=2.0, net_exposure_pct=-1.5)
        assert resp.net_exposure_pct == pytest.approx(-1.5)


# ---------------------------------------------------------------------------
# F-182 — Risk calculation logic (mirrors backend _compute_risk and frontend)
# ---------------------------------------------------------------------------

class TestRiskCalculation:
    def _compute(self, entry, stop, shares, equity=None):
        risk_per_share = abs(entry - stop) if entry and stop else None
        risk_amount = risk_per_share * shares if risk_per_share else None
        risk_pct = risk_amount / equity * 100 if risk_amount and equity else None
        return dict(
            risk_per_share=risk_per_share,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
        )

    def test_long_risk(self):
        r = self._compute(50.0, 47.0, 100, 100_000)
        assert r["risk_per_share"] == pytest.approx(3.0)
        assert r["risk_amount"] == pytest.approx(300.0)
        assert r["risk_pct"] == pytest.approx(0.3)

    def test_short_risk(self):
        r = self._compute(50.0, 53.0, 100, 100_000)
        assert r["risk_per_share"] == pytest.approx(3.0)  # abs value
        assert r["risk_amount"] == pytest.approx(300.0)

    def test_no_stop_gives_none(self):
        r = self._compute(50.0, None, 100, 100_000)
        assert r["risk_per_share"] is None
        assert r["risk_amount"] is None

    def test_no_equity_gives_none_pct(self):
        r = self._compute(50.0, 47.0, 100, None)
        assert r["risk_amount"] == pytest.approx(300.0)
        assert r["risk_pct"] is None

    def test_large_position(self):
        r = self._compute(100.0, 95.0, 1000, 1_000_000)
        assert r["risk_amount"] == pytest.approx(5000.0)
        assert r["risk_pct"] == pytest.approx(0.5)

    def test_risk_equals_1r(self):
        # If risk_pct == risk_per_trade_pct, position is correctly sized
        r = self._compute(50.0, 49.0, 100, 100_000)
        assert r["risk_pct"] == pytest.approx(0.1)


class TestAggregation:
    """Mirrors backend aggregation logic."""

    def _aggregate(self, items, equity):
        total = sum(it["risk_amount"] for it in items if it["risk_amount"])
        long_risk = sum(it["risk_amount"] for it in items if it.get("direction") == "LONG" and it["risk_amount"])
        short_risk = sum(it["risk_amount"] for it in items if it.get("direction") == "SHORT" and it["risk_amount"])
        pct = lambda x: round(x / equity * 100, 3) if equity else 0.0
        return dict(
            total_risk_pct=pct(total),
            long_risk_pct=pct(long_risk),
            short_risk_pct=pct(short_risk),
            net_exposure_pct=round(pct(long_risk) - pct(short_risk), 3),
            max_drawdown_scenario=round(total, 2),
        )

    def test_single_long(self):
        items = [{"direction": "LONG", "risk_amount": 300.0}]
        r = self._aggregate(items, 100_000)
        assert r["total_risk_pct"] == pytest.approx(0.3)
        assert r["long_risk_pct"] == pytest.approx(0.3)
        assert r["short_risk_pct"] == pytest.approx(0.0)
        assert r["net_exposure_pct"] == pytest.approx(0.3)

    def test_single_short(self):
        items = [{"direction": "SHORT", "risk_amount": 300.0}]
        r = self._aggregate(items, 100_000)
        assert r["net_exposure_pct"] == pytest.approx(-0.3)

    def test_balanced(self):
        items = [
            {"direction": "LONG", "risk_amount": 500.0},
            {"direction": "SHORT", "risk_amount": 500.0},
        ]
        r = self._aggregate(items, 100_000)
        assert r["net_exposure_pct"] == pytest.approx(0.0)

    def test_empty(self):
        r = self._aggregate([], 100_000)
        assert r["total_risk_pct"] == pytest.approx(0.0)
        assert r["max_drawdown_scenario"] == pytest.approx(0.0)

    def test_no_equity(self):
        items = [{"direction": "LONG", "risk_amount": 300.0}]
        r = self._aggregate(items, None)
        assert r["total_risk_pct"] == 0.0

    def test_max_drawdown_equals_total_risk(self):
        items = [
            {"direction": "LONG", "risk_amount": 300.0},
            {"direction": "SHORT", "risk_amount": 200.0},
        ]
        r = self._aggregate(items, 100_000)
        assert r["max_drawdown_scenario"] == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# F-183 — Risk severity thresholds (mirrors frontend pctColor logic)
# ---------------------------------------------------------------------------

class TestRiskSeverity:
    def _color(self, pct):
        if pct is None:
            return "gray"
        if pct >= 5:
            return "red"
        if pct >= 2:
            return "yellow"
        return "green"

    def test_safe_zone(self):
        assert self._color(0.5) == "green"

    def test_warning_zone(self):
        assert self._color(3.0) == "yellow"

    def test_critical_zone(self):
        assert self._color(6.0) == "red"

    def test_boundary_2pct(self):
        assert self._color(2.0) == "yellow"

    def test_boundary_5pct(self):
        assert self._color(5.0) == "red"

    def test_none_is_gray(self):
        assert self._color(None) == "gray"
