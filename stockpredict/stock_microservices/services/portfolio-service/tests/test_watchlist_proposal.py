"""Watchlist proposal fields — who recommended a symbol and what they said.

These cover `PortfolioService.add_to_watchlist`, the path a confirmed TCB News
recommendation takes to reach the watch screen. The behaviour that matters most is the
negative one: pushing a broker call for a stock the user actually OWNS must not demote
that position to watchlist-only.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.schemas import WatchlistAdd
from app.services.portfolio_service import PortfolioService


def _holding(**overrides):
    """A PortfolioHolding-shaped stub good enough for HoldingResponse.model_validate."""
    base = dict(
        id=1, portfolio_id=1, symbol="NTP", quantity=0, average_price=None,
        total_cost=0.0, current_price=None, current_value=None,
        profit_loss=None, profit_loss_percent=None, is_watchlist_only=True,
        proposal_by=None, proposal_action=None, proposal_label=None,
        proposal_date=None, proposal_note=None,
        created_at=date.today(), updated_at=date.today(),
    )
    base.update(overrides)
    stub = MagicMock()
    for k, v in base.items():
        setattr(stub, k, v)
    return stub


@pytest.fixture
def service():
    svc = PortfolioService(MagicMock())
    svc.repo = MagicMock()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=MagicMock(id=1))
    svc.repo.get_holding = AsyncMock(return_value=None)
    svc.repo.add_holding = AsyncMock(side_effect=lambda **kw: _holding(**{
        k: v for k, v in kw.items() if k != "portfolio_id"}))
    svc.repo.update_holding = AsyncMock(side_effect=lambda hid, **kw: _holding(id=hid, **kw))
    # Don't let the fire-and-forget company sync reach the network in tests.
    svc._trigger_ensure_and_sync = AsyncMock()
    return svc


TCB_CALL = WatchlistAdd(
    symbol="NTP", proposal_by="TCB", proposal_action="WATCH",
    proposal_label="Chờ mua", proposal_date=date(2026, 9, 21),
    proposal_note="Giá PVC tuần 14-18/9 châu Á tăng trên diện rộng…",
)


@pytest.mark.asyncio
async def test_new_symbol_is_added_with_its_proposal(service):
    result = await service.add_to_watchlist(1, 42, TCB_CALL)
    assert result.symbol == "NTP"
    assert result.proposal_by == "TCB"
    assert result.proposal_action == "WATCH"
    assert result.proposal_label == "Chờ mua"      # verbatim, not normalised away
    assert result.proposal_date == date(2026, 9, 21)
    kwargs = service.repo.add_holding.await_args.kwargs
    assert kwargs["is_watchlist_only"] is True
    assert kwargs["quantity"] == 0


@pytest.mark.asyncio
async def test_manual_add_sends_no_proposal_columns(service):
    """The watchlist screen's plain add must not invent a proposal — the column default
    applies instead of a value we made up here."""
    await service.add_to_watchlist(1, 42, WatchlistAdd(symbol="VNM"))
    kwargs = service.repo.add_holding.await_args.kwargs
    assert not any(k.startswith("proposal_") for k in kwargs)


@pytest.mark.asyncio
async def test_existing_row_gets_the_new_proposal(service):
    service.repo.get_holding = AsyncMock(return_value=_holding(
        id=7, proposal_by="TCB", proposal_action="BUY", proposal_label="Mua"))
    result = await service.add_to_watchlist(1, 42, TCB_CALL)
    service.repo.update_holding.assert_awaited_once()
    hid, kwargs = service.repo.update_holding.await_args.args[0], \
        service.repo.update_holding.await_args.kwargs
    assert hid == 7
    assert kwargs["proposal_action"] == "WATCH"     # TCB changed its mind; we follow
    assert result.proposal_label == "Chờ mua"


@pytest.mark.asyncio
async def test_a_call_on_an_owned_position_never_demotes_it_to_watchlist_only(service):
    """The regression this method exists to prevent.

    `add_holding` rewrites is_watchlist_only from its input, so routing a TCB call for
    a stock the user holds through it would flip a real 1,000-share position into a
    watchlist-only row and drop it out of the holdings screen and the P&L summary.
    """
    owned = _holding(id=9, symbol="MSN", quantity=1000, average_price=72.5,
                     total_cost=72500.0, is_watchlist_only=False)
    service.repo.get_holding = AsyncMock(return_value=owned)

    await service.add_to_watchlist(1, 42, WatchlistAdd(
        symbol="MSN", proposal_by="TCB", proposal_action="HOLD", proposal_label="Hold"))

    kwargs = service.repo.update_holding.await_args.kwargs
    assert "is_watchlist_only" not in kwargs   # untouched — still an owned position
    assert "quantity" not in kwargs            # and still 1,000 shares
    assert "total_cost" not in kwargs
    assert kwargs["proposal_action"] == "HOLD"


@pytest.mark.asyncio
async def test_existing_row_with_no_proposal_supplied_is_left_alone(service):
    """Re-adding a symbol already on the watchlist, with nothing new to say, must not
    issue a pointless UPDATE that bumps updated_at."""
    service.repo.get_holding = AsyncMock(return_value=_holding(id=3, symbol="VNM"))
    result = await service.add_to_watchlist(1, 42, WatchlistAdd(symbol="VNM"))
    service.repo.update_holding.assert_not_awaited()
    assert result.symbol == "VNM"


@pytest.mark.asyncio
async def test_unknown_portfolio_returns_none(service):
    service.repo.get_portfolio_by_id = AsyncMock(return_value=None)
    assert await service.add_to_watchlist(999, 42, TCB_CALL) is None
    service.repo.add_holding.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["BUY", "SELL", "HOLD", "WATCH"])
async def test_all_four_actions_are_accepted(service, action):
    """WATCH is ours (TCBS's "Chờ mua"); the other three are the broker's own verbs."""
    result = await service.add_to_watchlist(1, 42, WatchlistAdd(
        symbol="NTP", proposal_by="TCB", proposal_action=action))
    assert result.proposal_action == action


def test_proposal_action_column_is_wide_enough_for_every_action():
    from app.models.domain import PortfolioHolding
    width = PortfolioHolding.__table__.c.proposal_action.type.length
    assert width >= max(len(a) for a in ("BUY", "SELL", "HOLD", "WATCH"))


def test_proposal_by_defaults_to_tcb():
    """The default the user asked for: a watchlist row with no explicit source reads TCB."""
    from app.models.domain import PortfolioHolding
    assert PortfolioHolding.__table__.c.proposal_by.server_default.arg == "TCB"
