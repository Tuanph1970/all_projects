"""Unit tests for the journal-service business-logic modules.

Targets edge cases in trade_service (pure-function calculators +
service-level error paths), diary_service, planning_service,
dependencies, and a few repository methods that the route tests
don't routinely exercise.

The conftest test_db fixture gives us real SQLite execution, so most
of these talk to the actual SQLAlchemy stack rather than mocks.
"""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import (
    get_current_user,
    validate_token_with_auth_service,
)
from app.config import get_settings
from app.models.domain import Trade, TradeDirection, TradeStatus
from app.repositories.account_repository import AccountRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.planning_repository import PlanningRepository
from app.repositories.trade_repository import TradeRepository
from app.services.diary_service import DiaryService
from app.services.planning_service import PlanningService
from app.services.trade_service import TradeService


settings = get_settings()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade(
    *,
    entry_price=100.0,
    initial_stop=95.0,
    position_size=1000,
    direction=TradeDirection.LONG,
    commission=50.0,
    exit_price=None,
    exit_date=None,
    entry_date=None,
    revised_stop=None,
) -> Trade:
    t = Trade(
        account_id=1,
        trade_number=1,
        entry_date=entry_date or date(2026, 1, 1),
        market_ticker="FPT",
        direction=direction,
        entry_price=entry_price,
        entry_type="Market",
        initial_stop=initial_stop,
        revised_stop=revised_stop,
        position_size=position_size,
        commission=commission,
        exit_date=exit_date,
        exit_price=exit_price,
        status=TradeStatus.OPEN,
    )
    return t


async def _create_account(test_db, *, equity=100_000_000, max_per=2.0, max_cum=25.0):
    repo = AccountRepository(test_db)
    return await repo.create_account(
        user_id=1,
        account_name="Test",
        starting_equity=equity,
        currency="VND",
        max_risk_per_trade=max_per,
        max_cumulative_risk=max_cum,
    )


# ---------------------------------------------------------------------------
# TradeService — pure calculators
# ---------------------------------------------------------------------------

class TestTradeCalculators:
    def test_calc_risk_amount(self):
        # |100 - 95| * 1000 = 5000
        assert TradeService.calc_risk_amount(_trade()) == 5000.0

    def test_calc_risk_percent_zero_equity_returns_zero(self):
        """Avoids divide-by-zero when an account has no equity yet."""
        assert TradeService.calc_risk_percent(_trade(), equity=0) == 0.0

    def test_calc_risk_percent_normal(self):
        # 5000 / 100000 = 5%
        assert TradeService.calc_risk_percent(_trade(), equity=100_000) == 5.0

    def test_calc_net_pnl_open_trade_returns_none(self):
        assert TradeService.calc_net_pnl(_trade()) is None

    def test_calc_net_pnl_long_winning(self):
        # (110 - 100) * 1000 - 50 = 9950
        assert TradeService.calc_net_pnl(_trade(exit_price=110.0)) == pytest.approx(9950.0)

    def test_calc_net_pnl_short_winning(self):
        # Short: (entry - exit) * size - commission = (100 - 90) * 1000 - 50 = 9950
        t = _trade(direction=TradeDirection.SHORT, exit_price=90.0)
        assert TradeService.calc_net_pnl(t) == pytest.approx(9950.0)

    def test_calc_r_multiple_returns_none_for_open_trade(self):
        assert TradeService.calc_r_multiple(_trade()) is None

    def test_calc_r_multiple_zero_risk_returns_none(self):
        """Entry == initial_stop → risk = 0 → r-multiple undefined."""
        t = _trade(entry_price=100.0, initial_stop=100.0, exit_price=110.0)
        assert TradeService.calc_r_multiple(t) is None

    def test_calc_r_multiple_long_2R_win(self):
        # PnL = (110 - 100) * 1000 - 50 = 9950, Risk = 5000, R = 1.99
        t = _trade(exit_price=110.0)
        assert TradeService.calc_r_multiple(t) == pytest.approx(1.99, rel=1e-3)

    def test_calc_duration_open_trade_returns_none(self):
        assert TradeService.calc_duration(_trade()) is None

    def test_calc_duration_days(self):
        t = _trade(entry_date=date(2026, 1, 1), exit_date=date(2026, 1, 8))
        assert TradeService.calc_duration(t) == 7


class TestStopRevisionValidation:
    def test_long_stop_cannot_be_loosened(self):
        # Long: new stop must be >= current stop; widening (90 < 95) blocked.
        t = _trade()
        msg = TradeService.validate_stop_revision(t, new_stop=90.0)
        assert msg is not None
        assert "Long" in msg

    def test_long_stop_can_be_tightened(self):
        t = _trade()
        assert TradeService.validate_stop_revision(t, new_stop=97.0) is None

    def test_short_stop_cannot_be_loosened(self):
        # Short: new stop must be <= current stop; widening (105 > 100) blocked.
        t = _trade(direction=TradeDirection.SHORT, entry_price=100.0, initial_stop=105.0)
        msg = TradeService.validate_stop_revision(t, new_stop=110.0)
        assert msg is not None
        assert "Short" in msg

    def test_short_stop_can_be_tightened(self):
        t = _trade(direction=TradeDirection.SHORT, entry_price=100.0, initial_stop=105.0)
        assert TradeService.validate_stop_revision(t, new_stop=102.0) is None

    def test_uses_revised_stop_when_present(self):
        """When a prior revision exists, the next revision is compared
        against that, not the initial_stop."""
        t = _trade(revised_stop=97.0)
        # 95 < 97 → would loosen → blocked even though 95 >= initial_stop=95.
        msg = TradeService.validate_stop_revision(t, new_stop=95.0)
        assert msg is not None


class TestRiskWarnings:
    def test_warning_when_single_trade_risk_exceeds_limit(self):
        svc = TradeService(session=MagicMock())
        warnings = svc.get_risk_warnings(
            risk_percent=3.0, cumulative_percent=10.0,
            max_per_trade=2.0, max_cumulative=25.0,
        )
        assert any(w["level"] == "warning" for w in warnings)

    def test_danger_when_cumulative_exceeds_limit(self):
        svc = TradeService(session=MagicMock())
        warnings = svc.get_risk_warnings(
            risk_percent=1.0, cumulative_percent=30.0,
            max_per_trade=2.0, max_cumulative=25.0,
        )
        assert any(w["level"] == "danger" for w in warnings)

    def test_caution_when_cumulative_at_70_percent_of_limit(self):
        """Cumulative > 70% × max → 'caution' but not 'danger' yet."""
        svc = TradeService(session=MagicMock())
        warnings = svc.get_risk_warnings(
            risk_percent=1.0, cumulative_percent=20.0,  # 20 > 25*0.7=17.5
            max_per_trade=2.0, max_cumulative=25.0,
        )
        assert any(w["level"] == "caution" for w in warnings)

    def test_no_warnings_for_safe_trade(self):
        svc = TradeService(session=MagicMock())
        warnings = svc.get_risk_warnings(
            risk_percent=1.0, cumulative_percent=5.0,
            max_per_trade=2.0, max_cumulative=25.0,
        )
        assert warnings == []


# ---------------------------------------------------------------------------
# TradeService — DB-backed branches not hit by route tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_cumulative_risk_with_no_open_trades(test_db):
    """No open trades → zero cumulative."""
    acct = await _create_account(test_db)
    svc = TradeService(test_db)
    cum = await svc.get_cumulative_risk(acct.id, acct.current_equity)
    assert cum["open_trade_count"] == 0
    assert cum["total_risk_amount"] == 0.0
    assert cum["cumulative_risk_percent"] == 0.0


@pytest.mark.asyncio
async def test_get_cumulative_risk_zero_equity_returns_zero_percent(test_db):
    """Zero-equity account → cumulative percent is 0 (no div-by-zero)."""
    svc = TradeService(test_db)
    cum = await svc.get_cumulative_risk(account_id=999, equity=0)
    assert cum["cumulative_risk_percent"] == 0.0


@pytest.mark.asyncio
async def test_create_trade_returns_none_for_unknown_account(test_db):
    from app.models.schemas import TradeCreate
    svc = TradeService(test_db)
    payload = TradeCreate(
        entry_date=date(2026, 1, 1),
        market_ticker="FPT",
        direction=TradeDirection.LONG,
        entry_price=100.0,
        entry_type="Market",
        initial_stop=95.0,
        position_size=1000,
        commission=0,
    )
    out = await svc.create_trade(account_id=999_999, user_id=1, data=payload)
    assert out is None


@pytest.mark.asyncio
async def test_get_trade_returns_none_for_unknown_account(test_db):
    svc = TradeService(test_db)
    assert (await svc.get_trade(account_id=999, user_id=1, trade_id=1)) is None


@pytest.mark.asyncio
async def test_get_trade_returns_none_for_unknown_trade(test_db):
    acct = await _create_account(test_db)
    svc = TradeService(test_db)
    assert (await svc.get_trade(account_id=acct.id, user_id=1, trade_id=999)) is None


@pytest.mark.asyncio
async def test_update_trade_returns_none_for_unknown_account(test_db):
    from app.models.schemas import TradeUpdate
    svc = TradeService(test_db)
    out = await svc.update_trade(
        account_id=999, user_id=1, trade_id=1, data=TradeUpdate()
    )
    assert out is None


@pytest.mark.asyncio
async def test_update_trade_empty_payload_returns_unmodified_or_none(test_db):
    """Empty update_data + missing trade → None (early return path)."""
    acct = await _create_account(test_db)
    from app.models.schemas import TradeUpdate
    svc = TradeService(test_db)
    out = await svc.update_trade(
        account_id=acct.id, user_id=1, trade_id=999, data=TradeUpdate()
    )
    assert out is None


@pytest.mark.asyncio
async def test_close_trade_returns_none_for_unknown_account(test_db):
    svc = TradeService(test_db)
    assert (await svc.close_trade(account_id=999, user_id=1, trade_id=1,
                                  exit_price=110.0)) is None


@pytest.mark.asyncio
async def test_close_trade_returns_error_for_already_closed_trade(test_db):
    """Repository surfaces a closed trade — service returns the error dict."""
    acct = await _create_account(test_db)
    repo = TradeRepository(test_db)
    t = await repo.create_trade(
        account_id=acct.id, trade_number=1,
        entry_date=date(2026, 1, 1), market_ticker="FPT",
        direction=TradeDirection.LONG, entry_price=100.0,
        entry_type="Market", initial_stop=95.0,
        position_size=1000, commission=0,
    )
    # Close it directly via the repo so the service sees CLOSED status.
    await repo.update_trade(t.id, acct.id, status=TradeStatus.CLOSED,
                            exit_price=110.0, exit_date=date(2026, 1, 2))

    svc = TradeService(test_db)
    out = await svc.close_trade(
        account_id=acct.id, user_id=1, trade_id=t.id, exit_price=120.0
    )
    assert out["error"] is True
    assert "đóng" in out["message"]


@pytest.mark.asyncio
async def test_revise_stop_returns_none_for_unknown_account(test_db):
    from app.models.schemas import StopRevisionCreate
    svc = TradeService(test_db)
    out = await svc.revise_stop(
        account_id=999, user_id=1, trade_id=1,
        data=StopRevisionCreate(new_stop=97.0, reason="trail"),
    )
    assert out is None


@pytest.mark.asyncio
async def test_revise_stop_rejects_widening(test_db):
    """Long: new_stop < current_stop is blocked by validate_stop_revision."""
    from app.models.schemas import StopRevisionCreate
    acct = await _create_account(test_db)
    repo = TradeRepository(test_db)
    t = await repo.create_trade(
        account_id=acct.id, trade_number=1,
        entry_date=date(2026, 1, 1), market_ticker="FPT",
        direction=TradeDirection.LONG, entry_price=100.0,
        entry_type="Market", initial_stop=95.0,
        position_size=1000, commission=0,
    )
    svc = TradeService(test_db)
    out = await svc.revise_stop(
        account_id=acct.id, user_id=1, trade_id=t.id,
        data=StopRevisionCreate(new_stop=90.0, reason="loosen"),
    )
    assert out["error"] is True


@pytest.mark.asyncio
async def test_revise_stop_rejects_closed_trade(test_db):
    from app.models.schemas import StopRevisionCreate
    acct = await _create_account(test_db)
    repo = TradeRepository(test_db)
    t = await repo.create_trade(
        account_id=acct.id, trade_number=1,
        entry_date=date(2026, 1, 1), market_ticker="FPT",
        direction=TradeDirection.LONG, entry_price=100.0,
        entry_type="Market", initial_stop=95.0,
        position_size=1000, commission=0,
    )
    await repo.update_trade(t.id, acct.id, status=TradeStatus.CLOSED,
                            exit_price=110.0, exit_date=date(2026, 1, 2))
    svc = TradeService(test_db)
    out = await svc.revise_stop(
        account_id=acct.id, user_id=1, trade_id=t.id,
        data=StopRevisionCreate(new_stop=97.0, reason="trail"),
    )
    assert out["error"] is True


@pytest.mark.asyncio
async def test_delete_trade_returns_false_for_unknown_account(test_db):
    svc = TradeService(test_db)
    assert (await svc.delete_trade(account_id=999, user_id=1, trade_id=1)) is False


# ---------------------------------------------------------------------------
# DiaryService — error / not-found paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_diary_returns_none_when_trade_does_not_exist(test_db):
    svc = DiaryService(test_db)
    out = await svc.get_diary(trade_id=999_999, user_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_update_diary_returns_none_when_trade_does_not_exist(test_db):
    from app.models.schemas import TradeDiaryUpdate
    svc = DiaryService(test_db)
    out = await svc.update_diary(
        trade_id=999_999, user_id=1, data=TradeDiaryUpdate(decision_quality="good"),
    )
    assert out is None


@pytest.mark.asyncio
async def test_delete_diary_returns_none_when_trade_does_not_exist(test_db):
    svc = DiaryService(test_db)
    out = await svc.delete_diary(trade_id=999_999, user_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_get_charts_returns_none_when_diary_does_not_exist(test_db):
    svc = DiaryService(test_db)
    out = await svc.get_charts(diary_id=999_999, user_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_delete_chart_returns_none_when_chart_missing(test_db):
    svc = DiaryService(test_db)
    out = await svc.delete_chart(chart_id=999_999, user_id=1)
    assert out is None


# DiaryService happy paths — exercise via the test_db pipeline with a
# real account + trade + diary, so the full ownership-verification +
# CRUD path executes against SQLite.

async def _make_trade_with_account(test_db) -> tuple:
    acct = await _create_account(test_db)
    trade_repo = TradeRepository(test_db)
    trade = await trade_repo.create_trade(
        account_id=acct.id, trade_number=1,
        entry_date=date(2026, 1, 1), market_ticker="FPT",
        direction=TradeDirection.LONG, entry_price=100.0,
        entry_type="Market", initial_stop=95.0,
        position_size=1000, commission=0,
    )
    return acct, trade


@pytest.mark.asyncio
async def test_get_or_create_diary_creates_when_missing(test_db):
    from app.models.schemas import TradeDiaryCreate
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    out = await svc.get_or_create_diary(
        trade_id=trade.id, user_id=1,
        data=TradeDiaryCreate(reasons_for_trade="bull setup"),
    )
    assert out is not None
    assert out["reasons_for_trade"] == "bull setup"


@pytest.mark.asyncio
async def test_get_or_create_diary_returns_existing_on_second_call(test_db):
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    first = await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    second = await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    assert first["id"] == second["id"]


@pytest.mark.asyncio
async def test_get_diary_returns_not_found_marker_when_no_diary(test_db):
    """Trade exists but no diary → the service returns a sentinel dict
    instead of None so the route can distinguish missing-diary from
    missing-trade."""
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    out = await svc.get_diary(trade_id=trade.id, user_id=1)
    assert out is not None
    assert out.get("not_found") is True


@pytest.mark.asyncio
async def test_update_diary_rejects_outcome_fields_while_trade_open(test_db):
    """Schwager rule: 'how_it_turned_out' / 'lessons_and_mistakes' /
    'emotional_state_exit' can only be filled after the trade closes.
    An attempt to set them on an open trade should return an error."""
    from app.models.schemas import TradeDiaryUpdate
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    out = await svc.update_diary(
        trade_id=trade.id, user_id=1,
        data=TradeDiaryUpdate(how_it_turned_out="won 2R"),
    )
    assert out["error"] is True
    assert "đóng lệnh" in out["message"]


@pytest.mark.asyncio
async def test_update_diary_allows_outcome_fields_after_trade_closes(test_db):
    """Closed trade → outcome/lessons fields are accepted."""
    from app.models.schemas import TradeDiaryUpdate
    acct, trade = await _make_trade_with_account(test_db)

    trade_repo = TradeRepository(test_db)
    await trade_repo.update_trade(
        trade.id, acct.id,
        status=TradeStatus.CLOSED,
        exit_price=110.0, exit_date=date(2026, 1, 5),
    )

    svc = DiaryService(test_db)
    await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    out = await svc.update_diary(
        trade_id=trade.id, user_id=1,
        data=TradeDiaryUpdate(how_it_turned_out="won 2R"),
    )
    assert "error" not in out
    assert out["how_it_turned_out"] == "won 2R"


@pytest.mark.asyncio
async def test_update_diary_returns_error_when_diary_missing(test_db):
    """Trade exists, no diary yet → error pointing at create-first."""
    from app.models.schemas import TradeDiaryUpdate
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    out = await svc.update_diary(
        trade_id=trade.id, user_id=1,
        data=TradeDiaryUpdate(reasons_for_trade="late notes"),
    )
    assert out["error"] is True


@pytest.mark.asyncio
async def test_update_diary_with_empty_payload_returns_current_diary(test_db):
    from app.models.schemas import TradeDiaryUpdate
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    # Empty update body → returns the current diary unchanged.
    out = await svc.update_diary(
        trade_id=trade.id, user_id=1, data=TradeDiaryUpdate(),
    )
    assert "id" in out
    assert "error" not in out


@pytest.mark.asyncio
async def test_delete_diary_returns_false_when_diary_missing(test_db):
    """Trade exists, no diary → returns False rather than None
    (distinguishes from missing-trade)."""
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    out = await svc.delete_diary(trade_id=trade.id, user_id=1)
    assert out is False


@pytest.mark.asyncio
async def test_delete_diary_succeeds_when_diary_exists(test_db):
    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    ok = await svc.delete_diary(trade_id=trade.id, user_id=1)
    assert ok is True
    # Second delete: now no diary → False.
    again = await svc.delete_diary(trade_id=trade.id, user_id=1)
    assert again is False


# ---------------------------------------------------------------------------
# Chart upload / get / delete — exercise the full ownership + filesystem
# round trip with a tmp UPLOAD_DIR.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_chart_writes_file_and_returns_metadata(test_db, tmp_path, monkeypatch):
    """Upload writes the file under UPLOAD_DIR and returns the chart row."""
    from app.services import diary_service as ds_mod
    monkeypatch.setattr(ds_mod.settings, "UPLOAD_DIR", str(tmp_path))

    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    diary = await svc.get_or_create_diary(trade_id=trade.id, user_id=1)

    chart = await svc.upload_chart(
        diary_id=diary["id"], user_id=1,
        file_content=b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
        filename="entry.png",
        caption="Entry chart",
    )
    assert chart is not None
    assert chart["caption"] == "Entry chart"
    # File ended up on disk.
    import os
    assert os.path.exists(chart["image_path"])


@pytest.mark.asyncio
async def test_upload_chart_returns_none_for_unknown_diary(test_db):
    svc = DiaryService(test_db)
    out = await svc.upload_chart(
        diary_id=999_999, user_id=1,
        file_content=b"x", filename="a.png",
    )
    assert out is None


@pytest.mark.asyncio
async def test_get_charts_returns_list_for_known_diary(test_db, tmp_path, monkeypatch):
    from app.services import diary_service as ds_mod
    monkeypatch.setattr(ds_mod.settings, "UPLOAD_DIR", str(tmp_path))

    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    diary = await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    await svc.upload_chart(
        diary_id=diary["id"], user_id=1,
        file_content=b"\x89PNG", filename="a.png",
    )
    charts = await svc.get_charts(diary_id=diary["id"], user_id=1)
    assert charts is not None
    assert len(charts) == 1


@pytest.mark.asyncio
async def test_delete_chart_removes_file_and_row(test_db, tmp_path, monkeypatch):
    import os
    from app.services import diary_service as ds_mod
    monkeypatch.setattr(ds_mod.settings, "UPLOAD_DIR", str(tmp_path))

    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    diary = await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    chart = await svc.upload_chart(
        diary_id=diary["id"], user_id=1,
        file_content=b"\x89PNG", filename="a.png",
    )
    assert os.path.exists(chart["image_path"])

    ok = await svc.delete_chart(chart_id=chart["id"], user_id=1)
    assert ok is True
    # File scrubbed from disk.
    assert not os.path.exists(chart["image_path"])


@pytest.mark.asyncio
async def test_delete_chart_handles_missing_file_gracefully(test_db, tmp_path, monkeypatch):
    """If the file was already removed out-of-band, delete still returns True."""
    import os
    from app.services import diary_service as ds_mod
    monkeypatch.setattr(ds_mod.settings, "UPLOAD_DIR", str(tmp_path))

    acct, trade = await _make_trade_with_account(test_db)
    svc = DiaryService(test_db)
    diary = await svc.get_or_create_diary(trade_id=trade.id, user_id=1)
    chart = await svc.upload_chart(
        diary_id=diary["id"], user_id=1,
        file_content=b"\x89PNG", filename="a.png",
    )
    # Manually remove the file so delete_chart's os.path.exists path
    # exercises the missing-file branch.
    os.remove(chart["image_path"])
    ok = await svc.delete_chart(chart_id=chart["id"], user_id=1)
    assert ok is True


# ---------------------------------------------------------------------------
# More TradeService DB-backed paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_trade_blocks_close_without_exit_price(test_db):
    """Trying to set status=Closed without supplying an exit_price (and
    none on the existing trade) returns the validation error message."""
    from app.models.schemas import TradeUpdate
    acct, trade = await _make_trade_with_account(test_db)
    svc = TradeService(test_db)
    out = await svc.update_trade(
        account_id=acct.id, user_id=1, trade_id=trade.id,
        data=TradeUpdate(status=TradeStatus.CLOSED),
    )
    assert out["error"] is True
    assert "giá thoát" in out["message"]


@pytest.mark.asyncio
async def test_update_trade_autofills_exit_date_when_closing(test_db):
    """Setting status=Closed + exit_price (without exit_date) auto-fills
    exit_date with today."""
    from app.models.schemas import TradeUpdate
    acct, trade = await _make_trade_with_account(test_db)
    svc = TradeService(test_db)
    out = await svc.update_trade(
        account_id=acct.id, user_id=1, trade_id=trade.id,
        data=TradeUpdate(status=TradeStatus.CLOSED, exit_price=110.0),
    )
    # enrich_trade returns the SQLAlchemy-side TradeStatus enum, whose
    # `value` is "Closed". Reading the value side keeps the test
    # robust against enum-identity quirks in test_db.
    assert getattr(out["status"], "value", out["status"]) == "Closed"
    assert out["exit_price"] == 110.0
    # exit_date auto-set to today.
    assert out["exit_date"] == date.today()


@pytest.mark.asyncio
async def test_close_trade_happy_path(test_db):
    acct, trade = await _make_trade_with_account(test_db)
    svc = TradeService(test_db)
    out = await svc.close_trade(
        account_id=acct.id, user_id=1, trade_id=trade.id,
        exit_price=110.0, exit_reason="Hit target",
    )
    assert out is not None
    assert getattr(out["status"], "value", out["status"]) == "Closed"
    assert out["exit_price"] == 110.0
    # R-multiple is computed: (110-100)*1000 - 0 = 10000; risk = 5000 → 2R
    assert out["r_multiple"] == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_revise_stop_happy_path_persists_revision_history(test_db):
    from app.models.schemas import StopRevisionCreate
    acct, trade = await _make_trade_with_account(test_db)
    svc = TradeService(test_db)
    out = await svc.revise_stop(
        account_id=acct.id, user_id=1, trade_id=trade.id,
        data=StopRevisionCreate(new_stop=97.0, reason="trailing"),
    )
    assert "error" not in out
    assert out["revised_stop"] == 97.0
    # Audit row recorded.
    assert any(r["new_stop"] == 97.0 for r in out["stop_revisions"])


@pytest.mark.asyncio
async def test_delete_trade_happy_path(test_db):
    acct, trade = await _make_trade_with_account(test_db)
    svc = TradeService(test_db)
    assert (await svc.delete_trade(acct.id, user_id=1, trade_id=trade.id)) is True
    # Second delete: row gone → False.
    assert (await svc.delete_trade(acct.id, user_id=1, trade_id=trade.id)) is False


# ---------------------------------------------------------------------------
# PlanningService additional paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_daily_plans_returns_list_for_known_account(test_db):
    from app.models.schemas import DailyPlanCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    # Seed a plan.
    await svc.get_or_create_daily_plan(
        account_id=acct.id, user_id=1,
        data=DailyPlanCreate(plan_date=date(2026, 1, 15)),
    )
    plans = await svc.get_daily_plans(account_id=acct.id, user_id=1)
    assert plans is not None
    assert len(plans) >= 1


@pytest.mark.asyncio
async def test_get_daily_plan_returns_dict_for_known_plan(test_db):
    from app.models.schemas import DailyPlanCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    created = await svc.get_or_create_daily_plan(
        account_id=acct.id, user_id=1,
        data=DailyPlanCreate(plan_date=date(2026, 1, 15)),
    )
    out = await svc.get_daily_plan(
        account_id=acct.id, user_id=1, plan_id=created["id"],
    )
    assert out is not None
    assert out["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_daily_plan_returns_none_for_unknown_account(test_db):
    svc = PlanningService(test_db)
    out = await svc.get_daily_plan(account_id=999, user_id=1, plan_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_get_weekly_review_returns_none_for_unknown_account(test_db):
    svc = PlanningService(test_db)
    out = await svc.get_weekly_review(account_id=999, user_id=1, review_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_get_weekly_reviews_returns_list_for_known_account(test_db):
    from app.models.schemas import WeeklyReviewCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    await svc.create_weekly_review(
        account_id=acct.id, user_id=1,
        data=WeeklyReviewCreate(week_start=date(2026, 1, 12)),
    )
    rows = await svc.get_weekly_reviews(account_id=acct.id, user_id=1)
    assert rows is not None
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_update_weekly_review_happy_path(test_db):
    from app.models.schemas import WeeklyReviewCreate, WeeklyReviewUpdate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    created = await svc.create_weekly_review(
        account_id=acct.id, user_id=1,
        data=WeeklyReviewCreate(week_start=date(2026, 1, 12)),
    )
    out = await svc.update_weekly_review(
        account_id=acct.id, user_id=1, review_id=created["id"],
        data=WeeklyReviewUpdate(what_went_well="Solid discipline"),
    )
    assert out["what_went_well"] == "Solid discipline"


@pytest.mark.asyncio
async def test_recalculate_weekly_stats_returns_none_for_unknown_review(test_db):
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    out = await svc.recalculate_weekly_stats(
        account_id=acct.id, user_id=1, review_id=999,
    )
    assert out is None


@pytest.mark.asyncio
async def test_recalculate_weekly_stats_recomputes_for_existing_review(test_db):
    from app.models.schemas import WeeklyReviewCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    created = await svc.create_weekly_review(
        account_id=acct.id, user_id=1,
        data=WeeklyReviewCreate(week_start=date(2026, 1, 12)),
    )
    out = await svc.recalculate_weekly_stats(
        account_id=acct.id, user_id=1, review_id=created["id"],
    )
    assert out is not None
    assert "trades_taken" in out


@pytest.mark.asyncio
async def test_delete_weekly_review_happy_path(test_db):
    from app.models.schemas import WeeklyReviewCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    created = await svc.create_weekly_review(
        account_id=acct.id, user_id=1,
        data=WeeklyReviewCreate(week_start=date(2026, 1, 12)),
    )
    ok = await svc.delete_weekly_review(
        account_id=acct.id, user_id=1, review_id=created["id"],
    )
    assert ok is True


# ---------------------------------------------------------------------------
# PlanningService — DB-backed paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_daily_plans_returns_none_for_unknown_account(test_db):
    svc = PlanningService(test_db)
    out = await svc.get_daily_plans(account_id=999, user_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_get_or_create_daily_plan_creates_new_when_missing(test_db):
    from app.models.schemas import DailyPlanCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    out = await svc.get_or_create_daily_plan(
        account_id=acct.id, user_id=1,
        data=DailyPlanCreate(plan_date=date(2026, 1, 15)),
    )
    assert out is not None
    assert "plan_date" in out


@pytest.mark.asyncio
async def test_get_or_create_daily_plan_returns_existing_on_second_call(test_db):
    from app.models.schemas import DailyPlanCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    first = await svc.get_or_create_daily_plan(
        account_id=acct.id, user_id=1,
        data=DailyPlanCreate(plan_date=date(2026, 1, 15)),
    )
    second = await svc.get_or_create_daily_plan(
        account_id=acct.id, user_id=1,
        data=DailyPlanCreate(plan_date=date(2026, 1, 15)),
    )
    assert first["id"] == second["id"]


@pytest.mark.asyncio
async def test_update_daily_plan_returns_none_for_unknown_account(test_db):
    from app.models.schemas import DailyPlanUpdate
    svc = PlanningService(test_db)
    out = await svc.update_daily_plan(
        account_id=999, user_id=1, plan_id=1,
        data=DailyPlanUpdate(market_review="bullish"),
    )
    assert out is None


@pytest.mark.asyncio
async def test_update_daily_plan_returns_none_for_unknown_plan(test_db):
    from app.models.schemas import DailyPlanUpdate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    out = await svc.update_daily_plan(
        account_id=acct.id, user_id=1, plan_id=999,
        data=DailyPlanUpdate(market_review="bullish"),
    )
    assert out is None


@pytest.mark.asyncio
async def test_delete_daily_plan_returns_false_for_unknown_account(test_db):
    svc = PlanningService(test_db)
    out = await svc.delete_daily_plan(account_id=999, user_id=1, plan_id=1)
    assert out is False


@pytest.mark.asyncio
async def test_get_weekly_reviews_returns_none_for_unknown_account(test_db):
    svc = PlanningService(test_db)
    out = await svc.get_weekly_reviews(account_id=999, user_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_create_weekly_review_returns_none_for_unknown_account(test_db):
    from app.models.schemas import WeeklyReviewCreate
    svc = PlanningService(test_db)
    payload = WeeklyReviewCreate(week_start=date(2026, 1, 12))
    out = await svc.create_weekly_review(account_id=999, user_id=1, data=payload)
    assert out is None


@pytest.mark.asyncio
async def test_create_weekly_review_populates_stats(test_db):
    """Happy path: creating a weekly review computes stats from trades."""
    from app.models.schemas import WeeklyReviewCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    payload = WeeklyReviewCreate(week_start=date(2026, 1, 12))
    out = await svc.create_weekly_review(account_id=acct.id, user_id=1, data=payload)
    assert out is not None
    assert "id" in out
    # Stats are computed even with no trades in the window.
    assert "trades_taken" in out


@pytest.mark.asyncio
async def test_create_weekly_review_rejects_duplicate_week(test_db):
    """Second create for the same week returns an error dict."""
    from app.models.schemas import WeeklyReviewCreate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    payload = WeeklyReviewCreate(week_start=date(2026, 1, 12))
    first = await svc.create_weekly_review(account_id=acct.id, user_id=1, data=payload)
    assert "id" in first
    second = await svc.create_weekly_review(account_id=acct.id, user_id=1, data=payload)
    assert second.get("error") is True


@pytest.mark.asyncio
async def test_update_weekly_review_returns_none_for_unknown_review(test_db):
    from app.models.schemas import WeeklyReviewUpdate
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    out = await svc.update_weekly_review(
        account_id=acct.id, user_id=1, review_id=999,
        data=WeeklyReviewUpdate(),
    )
    assert out is None


@pytest.mark.asyncio
async def test_delete_weekly_review_returns_false_for_unknown_review(test_db):
    acct = await _create_account(test_db)
    svc = PlanningService(test_db)
    out = await svc.delete_weekly_review(
        account_id=acct.id, user_id=1, review_id=999,
    )
    assert out is False


# ---------------------------------------------------------------------------
# Repository edge cases (DiaryRepository / PlanningRepository)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_diary_repository_get_returns_none_for_unknown_trade(test_db):
    repo = DiaryRepository(test_db)
    out = await repo.get_diary_by_trade_id(999_999)
    assert out is None


@pytest.mark.asyncio
async def test_planning_repository_get_daily_plans_empty(test_db):
    repo = PlanningRepository(test_db)
    rows = await repo.get_daily_plans(account_id=999)
    assert rows == []


@pytest.mark.asyncio
async def test_planning_repository_get_weekly_reviews_empty(test_db):
    repo = PlanningRepository(test_db)
    rows = await repo.get_weekly_reviews(account_id=999)
    assert rows == []


# ---------------------------------------------------------------------------
# Dependencies — get_current_user / validate_token_with_auth_service
# ---------------------------------------------------------------------------

def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _token(payload_overrides=None) -> str:
    payload = {
        "sub": "42",
        "email": "alice@example.com",
        "role": "user",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=10),
        "type": "access",
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_get_current_user_returns_dict_on_valid_token():
    user = await get_current_user(credentials=_creds(_token()))
    assert user == {"user_id": 42, "email": "alice@example.com", "role": "user"}


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_sub_field():
    """A token where the `sub` claim is None (or not a string) is rejected
    — pyjwt's strict mode flags 'Subject must be a string'."""
    token = _token({"sub": None})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token))
    assert exc.value.status_code == 401
    assert "subject" in exc.value.detail.lower() or "missing" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_expired_token():
    payload = {
        "sub": "42", "email": "x@y.com",
        "iat": datetime.utcnow() - timedelta(minutes=20),
        "exp": datetime.utcnow() - timedelta(minutes=1),
        "type": "access",
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token))
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_garbage_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds("not.a.jwt"))
    assert exc.value.status_code == 401


# validate_token_with_auth_service is a fallback that the routes don't
# actually wire up — but it's part of the public surface and easy to
# exercise here.

class _FakeHttpxClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_validate_token_with_auth_service_returns_payload_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"user_id": 7, "email": "x@y.com"}
    with patch("app.api.dependencies.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await validate_token_with_auth_service("any.jwt")
    assert out == {"user_id": 7, "email": "x@y.com"}


@pytest.mark.asyncio
async def test_validate_token_with_auth_service_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    with patch("app.api.dependencies.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await validate_token_with_auth_service("any.jwt")
    assert out is None


@pytest.mark.asyncio
async def test_validate_token_with_auth_service_returns_none_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    with patch("app.api.dependencies.httpx.AsyncClient", return_value=Boom()):
        out = await validate_token_with_auth_service("any.jwt")
    assert out is None


# ---------------------------------------------------------------------------
# Route-level 404 paths — each handler's "service returned None → 404"
# branch. Existing route tests cover the happy path; these pin the error
# arm.
# ---------------------------------------------------------------------------

from tests.conftest import API_PREFIX  # noqa: E402


@pytest.mark.asyncio
async def test_diary_create_or_get_404_for_unknown_trade(client, headers):
    r = await client.post(
        f"{API_PREFIX}/trades/999999/diary", json={}, headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diary_get_404_for_unknown_trade(client, headers):
    r = await client.get(f"{API_PREFIX}/trades/999999/diary", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diary_update_404_for_unknown_trade(client, headers):
    r = await client.put(
        f"{API_PREFIX}/trades/999999/diary",
        json={"reasons_for_trade": "test"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diary_delete_404_for_unknown_trade(client, headers):
    r = await client.delete(f"{API_PREFIX}/trades/999999/diary", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diary_get_charts_404_for_unknown_diary(client, headers):
    r = await client.get(f"{API_PREFIX}/diary/999999/charts", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_diary_delete_chart_404_for_unknown_chart(client, headers):
    r = await client.delete(f"{API_PREFIX}/diary/charts/999999", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_get_daily_plans_404_for_unknown_account(client, headers):
    r = await client.get(f"{API_PREFIX}/accounts/999999/plans", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_get_daily_plan_404_for_unknown_account(client, headers):
    r = await client.get(
        f"{API_PREFIX}/accounts/999999/plans/1", headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_create_or_get_daily_plan_404_for_unknown_account(client, headers):
    r = await client.post(
        f"{API_PREFIX}/accounts/999999/plans",
        json={"plan_date": "2026-01-15"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_update_daily_plan_404_for_unknown_account(client, headers):
    r = await client.put(
        f"{API_PREFIX}/accounts/999999/plans/1",
        json={"market_review": "bullish"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_delete_daily_plan_404_for_unknown_account(client, headers):
    r = await client.delete(
        f"{API_PREFIX}/accounts/999999/plans/1", headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_get_weekly_reviews_404_for_unknown_account(client, headers):
    r = await client.get(
        f"{API_PREFIX}/accounts/999999/reviews", headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_create_weekly_review_404_for_unknown_account(client, headers):
    r = await client.post(
        f"{API_PREFIX}/accounts/999999/reviews",
        json={"week_start": "2026-01-12"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planning_get_weekly_review_404_for_unknown_review(client, headers, account):
    r = await client.get(
        f"{API_PREFIX}/accounts/{account['id']}/reviews/999",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_get_404_for_unknown_account(client, headers):
    r = await client.get(f"{API_PREFIX}/accounts/999999/trades", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_get_one_404_for_unknown_trade(client, headers, account):
    r = await client.get(
        f"{API_PREFIX}/accounts/{account['id']}/trades/999", headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_close_404_for_unknown_trade(client, headers, account):
    """close_trade takes exit_price as a query param, not in the body."""
    r = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/trades/999/close?exit_price=110.0",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_revise_stop_404_for_unknown_trade(client, headers, account):
    """Revise-stop endpoint is at /stop, not /revise-stop."""
    r = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/trades/999/stop",
        json={"new_stop": 97.0, "reason": "trail"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_delete_404_for_unknown_trade(client, headers, account):
    r = await client.delete(
        f"{API_PREFIX}/accounts/{account['id']}/trades/999",
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_update_404_for_unknown_trade(client, headers, account):
    r = await client.put(
        f"{API_PREFIX}/accounts/{account['id']}/trades/999",
        json={"market_ticker": "X"},
        headers=headers,
    )
    assert r.status_code == 404


# Account routes — 404 paths for missing accounts
@pytest.mark.asyncio
async def test_account_get_404_for_unknown_account(client, headers):
    r = await client.get(f"{API_PREFIX}/accounts/999999", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_account_update_404_for_unknown_account(client, headers):
    r = await client.put(
        f"{API_PREFIX}/accounts/999999",
        json={"account_name": "renamed"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_account_delete_404_for_unknown_account(client, headers):
    r = await client.delete(f"{API_PREFIX}/accounts/999999", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_account_create_rule_404_for_unknown_account(client, headers):
    r = await client.post(
        f"{API_PREFIX}/accounts/999999/rules",
        json={"rule_text": "Test rule", "category": "General"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_account_get_rules_404_for_unknown_account(client, headers):
    r = await client.get(f"{API_PREFIX}/accounts/999999/rules", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_account_update_rule_404_for_unknown_account(client, headers):
    r = await client.put(
        f"{API_PREFIX}/accounts/999999/rules/1",
        json={"rule_text": "renamed"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_account_delete_rule_404_for_unknown_account(client, headers):
    r = await client.delete(
        f"{API_PREFIX}/accounts/999999/rules/1", headers=headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trade_get_risk_info_happy_path(client, headers, account):
    """Exercise the cumulative-risk endpoint with no open trades."""
    r = await client.get(
        f"{API_PREFIX}/accounts/{account['id']}/risk", headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert "open_trade_count" in body
    assert "max_risk_per_trade" in body
    assert body["current_equity"] == account["current_equity"]


@pytest.mark.asyncio
async def test_trade_get_risk_info_404_for_unknown_account(client, headers):
    r = await client.get(
        f"{API_PREFIX}/accounts/999999/risk", headers=headers
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DashboardService — get_equity_snapshots / create_equity_snapshot
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_get_equity_snapshots_returns_empty_for_fresh_account(test_db):
    from app.services.dashboard_service import DashboardService
    acct = await _create_account(test_db)
    svc = DashboardService(test_db)
    out = await svc.get_equity_snapshots(account_id=acct.id, user_id=1)
    assert out == []


@pytest.mark.asyncio
async def test_dashboard_get_equity_snapshots_returns_none_for_unknown_account(test_db):
    from app.services.dashboard_service import DashboardService
    svc = DashboardService(test_db)
    out = await svc.get_equity_snapshots(account_id=999, user_id=1)
    assert out is None


@pytest.mark.asyncio
async def test_dashboard_create_equity_snapshot_persists_and_returns_dict(test_db):
    from app.services.dashboard_service import DashboardService
    acct = await _create_account(test_db)
    svc = DashboardService(test_db)
    out = await svc.create_equity_snapshot(
        account_id=acct.id, user_id=1,
        snapshot_date=date(2026, 1, 15),
        equity_value=100_000_000.0,
        open_trade_equity=5_000_000.0,
    )
    assert out is not None
    assert out["equity"] == 100_000_000.0
    assert out["open_trade_equity"] == 5_000_000.0
    # total = equity + open_trade_equity (set in domain model)
    assert "total" in out


@pytest.mark.asyncio
async def test_dashboard_create_equity_snapshot_returns_none_for_unknown_account(test_db):
    from app.services.dashboard_service import DashboardService
    svc = DashboardService(test_db)
    out = await svc.create_equity_snapshot(
        account_id=999, user_id=1,
        snapshot_date=date(2026, 1, 15),
        equity_value=100_000.0,
    )
    assert out is None
