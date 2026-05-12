"""Unit tests for PortfolioService — service-layer business logic
exercised against a mocked PortfolioRepository.

Each test stubs the repo methods on the service and verifies the
service's branching, validation, and computed-field logic.
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.domain import (
    AlertType,
    Portfolio,
    PortfolioHolding,
    PriceAlert,
    Transaction,
    TransactionType,
)
from app.models.schemas import (
    AlertCreate,
    AlertType as AlertTypeEnum,
    AlertUpdate,
    HoldingCreate,
    HoldingUpdate,
    PortfolioCreate,
    PortfolioUpdate,
    TransactionCreate,
    TransactionType as TransactionTypeEnum,
)
from app.services.portfolio_service import PortfolioService


def _make_service():
    """Build a PortfolioService whose repo is fully mocked."""
    svc = PortfolioService(session=MagicMock())
    svc.repo = MagicMock()
    # Default common methods to None / [] so unhandled branches no-op.
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=None)
    svc.repo.get_default_portfolio = AsyncMock(return_value=None)
    svc.repo.get_portfolios_by_user = AsyncMock(return_value=[])
    svc.repo.get_holdings_by_portfolio = AsyncMock(return_value=[])
    svc.repo.get_alerts_by_user = AsyncMock(return_value=[])
    return svc


def _portfolio(id=1, user_id=1, name="P1", is_default=False) -> Portfolio:
    p = Portfolio(
        id=id, user_id=user_id, name=name,
        description=None, is_default=is_default,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    return p


def _holding(
    id=1, portfolio_id=1, symbol="FPT",
    quantity=10, average_price=100.0, total_cost=1000.0,
    profit_loss_percent=5.0,
) -> PortfolioHolding:
    h = PortfolioHolding(
        id=id, portfolio_id=portfolio_id, symbol=symbol,
        quantity=quantity, average_price=average_price,
        total_cost=total_cost, current_price=None,
        current_value=None, profit_loss=None,
        profit_loss_percent=profit_loss_percent,
        is_watchlist_only=False,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    return h


def _transaction(id=1, portfolio_id=1) -> Transaction:
    return Transaction(
        id=id, portfolio_id=portfolio_id, symbol="FPT",
        transaction_type=TransactionType.BUY,
        quantity=10, price=100.0, total_value=1000.0, fees=5.0,
        notes=None, transaction_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )


def _alert(
    id=1, user_id=1, symbol="FPT",
    alert_type=AlertType.ABOVE, target_price=110.0,
    is_active=True,
) -> PriceAlert:
    return PriceAlert(
        id=id, user_id=user_id, symbol=symbol,
        alert_type=alert_type, target_price=target_price,
        target_percent=None, is_active=is_active, is_triggered=False,
        triggered_at=None, notes=None,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# create_portfolio + get_or_create_default_portfolio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_portfolio_unsets_existing_default_when_marking_new_one_default():
    svc = _make_service()
    existing = _portfolio(id=99, is_default=True)
    svc.repo.get_default_portfolio = AsyncMock(return_value=existing)
    svc.repo.update_portfolio = AsyncMock()
    svc.repo.create_portfolio = AsyncMock(return_value=_portfolio(id=1, is_default=True))

    out = await svc.create_portfolio(
        user_id=1, data=PortfolioCreate(name="New", is_default=True),
    )
    assert out.id == 1
    # Existing default got unset before the new portfolio was created.
    svc.repo.update_portfolio.assert_any_await(99, 1, is_default=False)
    svc.repo.create_portfolio.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_portfolio_skips_default_unset_when_not_default():
    svc = _make_service()
    svc.repo.create_portfolio = AsyncMock(return_value=_portfolio())
    out = await svc.create_portfolio(
        user_id=1, data=PortfolioCreate(name="N", is_default=False),
    )
    # The default-lookup path should not have run.
    svc.repo.get_default_portfolio.assert_not_awaited()
    assert out.id == 1


@pytest.mark.asyncio
async def test_get_portfolio_returns_none_when_missing():
    svc = _make_service()
    assert (await svc.get_portfolio(portfolio_id=1, user_id=1)) is None


@pytest.mark.asyncio
async def test_get_portfolio_returns_with_holdings_when_present():
    svc = _make_service()
    p = _portfolio()
    p.holdings = []
    p.transactions = []
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=p)
    out = await svc.get_portfolio(portfolio_id=1, user_id=1)
    assert out is not None
    assert out.id == 1


@pytest.mark.asyncio
async def test_get_user_portfolios_remaps_rows():
    svc = _make_service()
    svc.repo.get_portfolios_by_user = AsyncMock(
        return_value=[_portfolio(id=1, name="A"), _portfolio(id=2, name="B")]
    )
    out = await svc.get_user_portfolios(user_id=1)
    assert [p.name for p in out] == ["A", "B"]


@pytest.mark.asyncio
async def test_get_or_create_default_portfolio_returns_existing_default():
    svc = _make_service()
    existing = _portfolio(id=7, is_default=True)
    svc.repo.get_default_portfolio = AsyncMock(return_value=existing)
    out = await svc.get_or_create_default_portfolio(user_id=1)
    assert out.id == 7


@pytest.mark.asyncio
async def test_get_or_create_default_portfolio_promotes_first_existing():
    """No default, but some other portfolios exist → promote the first."""
    svc = _make_service()
    svc.repo.get_default_portfolio = AsyncMock(return_value=None)
    first = _portfolio(id=3, is_default=False)
    svc.repo.get_portfolios_by_user = AsyncMock(return_value=[first])
    svc.repo.update_portfolio = AsyncMock()
    out = await svc.get_or_create_default_portfolio(user_id=1)
    assert out.id == 3
    svc.repo.update_portfolio.assert_awaited_once_with(3, 1, is_default=True)


@pytest.mark.asyncio
async def test_get_or_create_default_portfolio_creates_new_when_user_has_none():
    svc = _make_service()
    svc.repo.get_default_portfolio = AsyncMock(return_value=None)
    svc.repo.get_portfolios_by_user = AsyncMock(return_value=[])
    created = _portfolio(id=10, name="Default Portfolio", is_default=True)
    svc.repo.create_portfolio = AsyncMock(return_value=created)
    out = await svc.get_or_create_default_portfolio(user_id=1)
    assert out.id == 10
    svc.repo.create_portfolio.assert_awaited_once()


# ---------------------------------------------------------------------------
# update_portfolio + delete_portfolio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_portfolio_empty_payload_returns_current_or_none():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    out = await svc.update_portfolio(
        portfolio_id=1, user_id=1, data=PortfolioUpdate(),
    )
    assert out is not None and out.id == 1


@pytest.mark.asyncio
async def test_update_portfolio_empty_payload_returns_none_when_portfolio_missing():
    svc = _make_service()
    out = await svc.update_portfolio(
        portfolio_id=99, user_id=1, data=PortfolioUpdate(),
    )
    assert out is None


@pytest.mark.asyncio
async def test_update_portfolio_unsetting_other_default_when_marking_default():
    svc = _make_service()
    existing_default = _portfolio(id=99, is_default=True)
    svc.repo.get_default_portfolio = AsyncMock(return_value=existing_default)
    svc.repo.update_portfolio = AsyncMock(return_value=_portfolio(id=1, is_default=True))
    out = await svc.update_portfolio(
        portfolio_id=1, user_id=1,
        data=PortfolioUpdate(is_default=True),
    )
    assert out is not None
    # The OTHER default got unset.
    svc.repo.update_portfolio.assert_any_await(99, 1, is_default=False)


@pytest.mark.asyncio
async def test_update_portfolio_does_not_unset_when_marking_same_portfolio_default():
    """Marking the already-default portfolio as default shouldn't try
    to unset itself."""
    svc = _make_service()
    existing_default = _portfolio(id=1, is_default=True)
    svc.repo.get_default_portfolio = AsyncMock(return_value=existing_default)
    svc.repo.update_portfolio = AsyncMock(return_value=_portfolio(id=1, is_default=True))
    out = await svc.update_portfolio(
        portfolio_id=1, user_id=1, data=PortfolioUpdate(is_default=True),
    )
    assert out is not None
    # update_portfolio called once (for the actual update), not twice.
    assert svc.repo.update_portfolio.await_count == 1


@pytest.mark.asyncio
async def test_delete_portfolio_delegates_to_repo():
    svc = _make_service()
    svc.repo.delete_portfolio = AsyncMock(return_value=True)
    assert (await svc.delete_portfolio(1, 1)) is True


# ---------------------------------------------------------------------------
# get_portfolio_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_portfolio_summary_returns_none_when_portfolio_missing():
    svc = _make_service()
    assert (await svc.get_portfolio_summary(1, 1)) is None


@pytest.mark.asyncio
async def test_get_portfolio_summary_sorts_holdings_by_pl_for_top_and_worst():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_portfolio_stats = AsyncMock(return_value={
        "total_holdings": 3,
        "total_invested": 30_000.0,
        "current_value": 33_000.0,
        "total_profit_loss": 3_000.0,
        "profit_loss_percent": 10.0,
    })
    holdings = [
        _holding(id=1, symbol="A", profit_loss_percent=15.0),
        _holding(id=2, symbol="B", profit_loss_percent=-5.0),
        _holding(id=3, symbol="C", profit_loss_percent=8.0),
    ]
    svc.repo.get_holdings_by_portfolio = AsyncMock(return_value=holdings)

    out = await svc.get_portfolio_summary(1, 1)
    assert out is not None
    assert out.total_holdings == 3
    # Sorted descending → top = A (15%), worst = B (-5%).
    assert out.top_performers[0].symbol == "A"
    assert out.worst_performers[-1].symbol == "B"


# ---------------------------------------------------------------------------
# add_holding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_holding_returns_none_when_portfolio_missing():
    svc = _make_service()
    out = await svc.add_holding(
        1, 1, HoldingCreate(symbol="FPT", quantity=10, average_price=100.0),
    )
    assert out is None


@pytest.mark.asyncio
async def test_add_holding_creates_new_when_symbol_absent():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holding = AsyncMock(return_value=None)
    svc.repo.add_holding = AsyncMock(return_value=_holding())
    # Stub the fire-and-forget background task.
    with patch.object(svc, "_trigger_ensure_and_sync", AsyncMock()):
        out = await svc.add_holding(
            1, 1, HoldingCreate(symbol="FPT", quantity=10, average_price=100.0),
        )
    assert out is not None
    assert out.symbol == "FPT"
    svc.repo.add_holding.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_holding_merges_into_existing_with_weighted_average():
    """Existing 10 @ 100 + new 10 @ 120 → 20 @ 110 average (weighted)."""
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    existing = _holding(quantity=10, average_price=100.0, total_cost=1000.0)
    svc.repo.get_holding = AsyncMock(return_value=existing)
    svc.repo.update_holding = AsyncMock(side_effect=lambda *_a, **kw: _holding(
        quantity=kw.get("quantity", 0),
        average_price=kw.get("average_price", 0),
        total_cost=kw.get("total_cost", 0),
    ))
    with patch.object(svc, "_trigger_ensure_and_sync", AsyncMock()):
        out = await svc.add_holding(
            1, 1, HoldingCreate(symbol="FPT", quantity=10, average_price=120.0),
        )
    update_kwargs = svc.repo.update_holding.await_args.kwargs
    assert update_kwargs["quantity"] == 20
    assert update_kwargs["average_price"] == pytest.approx(110.0)
    assert update_kwargs["total_cost"] == pytest.approx(2200.0)


# ---------------------------------------------------------------------------
# get_holdings + update_holding + remove_holding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_holdings_returns_empty_list_when_portfolio_missing():
    svc = _make_service()
    assert (await svc.get_holdings(1, 1)) == []


@pytest.mark.asyncio
async def test_get_holdings_returns_remapped_rows_when_portfolio_exists():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holdings_by_portfolio = AsyncMock(
        return_value=[_holding(symbol="A"), _holding(symbol="B")]
    )
    out = await svc.get_holdings(1, 1)
    assert [h.symbol for h in out] == ["A", "B"]


@pytest.mark.asyncio
async def test_update_holding_returns_none_when_portfolio_missing():
    svc = _make_service()
    out = await svc.update_holding(
        1, 1, "FPT", HoldingUpdate(quantity=20),
    )
    assert out is None


@pytest.mark.asyncio
async def test_update_holding_returns_none_when_holding_missing():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holding = AsyncMock(return_value=None)
    out = await svc.update_holding(1, 1, "FPT", HoldingUpdate(quantity=20))
    assert out is None


@pytest.mark.asyncio
async def test_update_holding_recomputes_total_cost_when_both_quantity_and_price_provided():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holding = AsyncMock(return_value=_holding())
    svc.repo.update_holding = AsyncMock(side_effect=lambda *_a, **kw: _holding(**kw))
    await svc.update_holding(
        1, 1, "FPT", HoldingUpdate(quantity=20, average_price=110.0),
    )
    update_kwargs = svc.repo.update_holding.await_args.kwargs
    assert update_kwargs["total_cost"] == pytest.approx(2200.0)


@pytest.mark.asyncio
async def test_update_holding_recomputes_total_cost_when_only_quantity_changes():
    """If only quantity is supplied, total_cost is quantity × existing avg."""
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holding = AsyncMock(return_value=_holding(average_price=100.0))
    svc.repo.update_holding = AsyncMock(side_effect=lambda *_a, **kw: _holding(**kw))
    await svc.update_holding(1, 1, "FPT", HoldingUpdate(quantity=20))
    update_kwargs = svc.repo.update_holding.await_args.kwargs
    assert update_kwargs["total_cost"] == pytest.approx(2000.0)


@pytest.mark.asyncio
async def test_remove_holding_returns_false_when_portfolio_missing():
    svc = _make_service()
    assert (await svc.remove_holding(1, 1, "FPT")) is False


@pytest.mark.asyncio
async def test_remove_holding_returns_false_when_holding_missing():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holding = AsyncMock(return_value=None)
    assert (await svc.remove_holding(1, 1, "FPT")) is False


@pytest.mark.asyncio
async def test_remove_holding_delegates_to_delete_holding():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holding = AsyncMock(return_value=_holding())
    svc.repo.delete_holding = AsyncMock(return_value=True)
    assert (await svc.remove_holding(1, 1, "FPT")) is True


# ---------------------------------------------------------------------------
# refresh_prices — httpx mocked
# ---------------------------------------------------------------------------

class _FakeHttpxClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.post = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_refresh_prices_returns_zero_when_portfolio_missing():
    svc = _make_service()
    assert (await svc.refresh_prices(1, 1)) == 0


@pytest.mark.asyncio
async def test_refresh_prices_returns_zero_when_no_holdings():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holdings_by_portfolio = AsyncMock(return_value=[])
    assert (await svc.refresh_prices(1, 1)) == 0


@pytest.mark.asyncio
async def test_refresh_prices_updates_with_quotes_on_200():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holdings_by_portfolio = AsyncMock(
        return_value=[_holding(symbol="FPT")]
    )
    svc.repo.update_holding_prices = AsyncMock(return_value=1)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"quotes": [{"symbol": "FPT", "price": 110.0}]}

    with patch("app.services.portfolio_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await svc.refresh_prices(1, 1)
    assert out == 1
    svc.repo.update_holding_prices.assert_awaited_once_with(1, {"FPT": 110.0})


@pytest.mark.asyncio
async def test_refresh_prices_returns_zero_on_non_200():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holdings_by_portfolio = AsyncMock(return_value=[_holding()])
    resp = MagicMock()
    resp.status_code = 503
    with patch("app.services.portfolio_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        assert (await svc.refresh_prices(1, 1)) == 0


@pytest.mark.asyncio
async def test_refresh_prices_returns_zero_on_httpx_exception():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_holdings_by_portfolio = AsyncMock(return_value=[_holding()])

    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    with patch("app.services.portfolio_service.httpx.AsyncClient", return_value=Boom()):
        assert (await svc.refresh_prices(1, 1)) == 0


# ---------------------------------------------------------------------------
# record_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_transaction_returns_none_when_portfolio_missing():
    svc = _make_service()
    payload = TransactionCreate(
        symbol="FPT", transaction_type=TransactionTypeEnum.BUY,
        quantity=10, price=100.0, fees=5.0,
    )
    out = await svc.record_transaction(1, 1, payload)
    assert out is None


@pytest.mark.asyncio
async def test_record_transaction_buy_creates_holding_when_absent():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.create_transaction = AsyncMock(return_value=_transaction())
    svc.repo.get_holding = AsyncMock(return_value=None)
    svc.repo.add_holding = AsyncMock()

    payload = TransactionCreate(
        symbol="FPT", transaction_type=TransactionTypeEnum.BUY,
        quantity=10, price=100.0, fees=5.0,
    )
    with patch.object(svc, "_trigger_ensure_and_sync", AsyncMock()):
        out = await svc.record_transaction(1, 1, payload)
    assert out is not None
    svc.repo.add_holding.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_transaction_buy_merges_into_existing_holding():
    """Existing 10 @ 100 + buy 10 @ 120 (+5 fees) → 20 shares, weighted avg."""
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.create_transaction = AsyncMock(return_value=_transaction())
    svc.repo.get_holding = AsyncMock(
        return_value=_holding(quantity=10, average_price=100.0, total_cost=1000.0)
    )
    svc.repo.update_holding = AsyncMock()

    payload = TransactionCreate(
        symbol="FPT", transaction_type=TransactionTypeEnum.BUY,
        quantity=10, price=120.0, fees=5.0,
    )
    with patch.object(svc, "_trigger_ensure_and_sync", AsyncMock()):
        await svc.record_transaction(1, 1, payload)
    update_kwargs = svc.repo.update_holding.await_args.kwargs
    # 10 + 10 = 20 quantity; total_cost = 1000 + (10×120) + 5 = 2205
    assert update_kwargs["quantity"] == 20
    assert update_kwargs["total_cost"] == pytest.approx(2205.0)
    assert update_kwargs["average_price"] == pytest.approx(110.25)


@pytest.mark.asyncio
async def test_record_transaction_sell_deletes_when_fully_liquidated():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.create_transaction = AsyncMock(return_value=_transaction())
    svc.repo.get_holding = AsyncMock(return_value=_holding(quantity=10))
    svc.repo.delete_holding = AsyncMock(return_value=True)

    payload = TransactionCreate(
        symbol="FPT", transaction_type=TransactionTypeEnum.SELL,
        quantity=10, price=110.0, fees=0,
    )
    await svc.record_transaction(1, 1, payload)
    svc.repo.delete_holding.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_transaction_sell_partial_reduces_quantity_and_total_cost():
    """Partial sell: 10 @ avg=100 → sell 4 → 6 left, total_cost=600."""
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.create_transaction = AsyncMock(return_value=_transaction())
    svc.repo.get_holding = AsyncMock(
        return_value=_holding(quantity=10, average_price=100.0, total_cost=1000.0)
    )
    svc.repo.update_holding = AsyncMock()

    payload = TransactionCreate(
        symbol="FPT", transaction_type=TransactionTypeEnum.SELL,
        quantity=4, price=110.0, fees=0,
    )
    await svc.record_transaction(1, 1, payload)
    update_kwargs = svc.repo.update_holding.await_args.kwargs
    assert update_kwargs["quantity"] == 6
    assert update_kwargs["total_cost"] == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# get_transactions + delete_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_transactions_returns_empty_when_portfolio_missing():
    svc = _make_service()
    assert (await svc.get_transactions(1, 1)) == []


@pytest.mark.asyncio
async def test_get_transactions_returns_remapped_rows():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_transactions_by_portfolio = AsyncMock(
        return_value=[_transaction(id=1), _transaction(id=2)]
    )
    out = await svc.get_transactions(1, 1)
    assert [t.id for t in out] == [1, 2]


@pytest.mark.asyncio
async def test_delete_transaction_returns_false_when_portfolio_missing():
    svc = _make_service()
    assert (await svc.delete_transaction(1, 1, 1)) is False


@pytest.mark.asyncio
async def test_delete_transaction_returns_false_when_transaction_missing():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio())
    svc.repo.get_transaction_by_id = AsyncMock(return_value=None)
    assert (await svc.delete_transaction(1, 1, 99)) is False


@pytest.mark.asyncio
async def test_delete_transaction_returns_false_for_different_portfolio():
    """A transaction from another portfolio cannot be deleted via this one."""
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio(id=1))
    svc.repo.get_transaction_by_id = AsyncMock(
        return_value=_transaction(portfolio_id=99)  # different portfolio
    )
    assert (await svc.delete_transaction(1, 1, 1)) is False


@pytest.mark.asyncio
async def test_delete_transaction_delegates_when_authorized():
    svc = _make_service()
    svc.repo.get_portfolio_by_id = AsyncMock(return_value=_portfolio(id=1))
    svc.repo.get_transaction_by_id = AsyncMock(return_value=_transaction(portfolio_id=1))
    svc.repo.delete_transaction = AsyncMock(return_value=True)
    assert (await svc.delete_transaction(1, 1, 1)) is True


# ---------------------------------------------------------------------------
# Alerts: create / get / update / delete / check_alerts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_alert_persists_via_repo():
    svc = _make_service()
    svc.repo.create_alert = AsyncMock(return_value=_alert())
    out = await svc.create_alert(
        user_id=1,
        data=AlertCreate(
            symbol="FPT", alert_type=AlertTypeEnum.ABOVE, target_price=110.0,
        ),
    )
    assert out.symbol == "FPT"
    svc.repo.create_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_alerts_remaps_rows():
    svc = _make_service()
    svc.repo.get_alerts_by_user = AsyncMock(
        return_value=[_alert(id=1), _alert(id=2)]
    )
    out = await svc.get_alerts(user_id=1)
    assert [a.id for a in out] == [1, 2]


@pytest.mark.asyncio
async def test_update_alert_empty_payload_returns_current_or_none():
    svc = _make_service()
    svc.repo.get_alert_by_id = AsyncMock(return_value=_alert())
    out = await svc.update_alert(1, 1, AlertUpdate())
    assert out is not None and out.id == 1


@pytest.mark.asyncio
async def test_update_alert_empty_payload_returns_none_when_missing():
    svc = _make_service()
    svc.repo.get_alert_by_id = AsyncMock(return_value=None)
    out = await svc.update_alert(99, 1, AlertUpdate())
    assert out is None


@pytest.mark.asyncio
async def test_update_alert_applies_changes_via_repo():
    svc = _make_service()
    svc.repo.update_alert = AsyncMock(return_value=_alert(is_active=False))
    out = await svc.update_alert(1, 1, AlertUpdate(is_active=False))
    assert out.is_active is False
    svc.repo.update_alert.assert_awaited_once_with(1, 1, is_active=False)


@pytest.mark.asyncio
async def test_delete_alert_delegates_to_repo():
    svc = _make_service()
    svc.repo.delete_alert = AsyncMock(return_value=True)
    assert (await svc.delete_alert(1, 1)) is True


# ---------------------------------------------------------------------------
# check_alerts (price-based triggering)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_alerts_returns_empty_when_no_active_alerts():
    svc = _make_service()
    svc.repo.get_alerts_by_user = AsyncMock(return_value=[])
    out = await svc.check_alerts(user_id=1, price_data={"FPT": 110.0})
    assert out == []


@pytest.mark.asyncio
async def test_check_alerts_skips_symbols_without_price_data():
    svc = _make_service()
    svc.repo.get_alerts_by_user = AsyncMock(
        return_value=[_alert(symbol="FPT", target_price=110.0)]
    )
    out = await svc.check_alerts(user_id=1, price_data={"VNM": 70.0})
    assert out == []


@pytest.mark.asyncio
async def test_check_alerts_triggers_above_alert_when_price_at_or_above():
    svc = _make_service()
    above_alert = _alert(symbol="FPT", alert_type=AlertType.ABOVE, target_price=110.0)
    svc.repo.get_alerts_by_user = AsyncMock(return_value=[above_alert])
    svc.repo.trigger_alert = AsyncMock(return_value=True)
    svc.repo.update_alert = AsyncMock()

    out = await svc.check_alerts(user_id=1, price_data={"FPT": 115.0})
    assert len(out) == 1
    svc.repo.trigger_alert.assert_awaited_once_with(above_alert.id)
    # Marked inactive after triggering.
    svc.repo.update_alert.assert_awaited_once_with(above_alert.id, 1, is_active=False)


@pytest.mark.asyncio
async def test_check_alerts_does_not_trigger_above_when_price_below_target():
    svc = _make_service()
    above_alert = _alert(symbol="FPT", alert_type=AlertType.ABOVE, target_price=110.0)
    svc.repo.get_alerts_by_user = AsyncMock(return_value=[above_alert])
    svc.repo.trigger_alert = AsyncMock()
    out = await svc.check_alerts(user_id=1, price_data={"FPT": 105.0})
    assert out == []
    svc.repo.trigger_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_alerts_triggers_below_alert_when_price_at_or_below():
    svc = _make_service()
    below_alert = _alert(symbol="FPT", alert_type=AlertType.BELOW, target_price=95.0)
    svc.repo.get_alerts_by_user = AsyncMock(return_value=[below_alert])
    svc.repo.trigger_alert = AsyncMock(return_value=True)
    svc.repo.update_alert = AsyncMock()

    out = await svc.check_alerts(user_id=1, price_data={"FPT": 90.0})
    assert len(out) == 1
    svc.repo.trigger_alert.assert_awaited_once()


# ---------------------------------------------------------------------------
# _trigger_ensure_and_sync — httpx best-effort fire-and-forget
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trigger_ensure_and_sync_swallows_exception():
    """Background task must not propagate — it's purely best-effort."""
    svc = _make_service()

    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    with patch("app.services.portfolio_service.httpx.AsyncClient", return_value=Boom()):
        # Must not raise.
        await svc._trigger_ensure_and_sync("FPT")


@pytest.mark.asyncio
async def test_trigger_ensure_and_sync_calls_stock_data_endpoint():
    svc = _make_service()
    resp = MagicMock()
    resp.status_code = 200

    class Ctx:
        async def __aenter__(self):
            client = MagicMock()
            client.post = AsyncMock(return_value=resp)
            return client

        async def __aexit__(self, *_):
            return False

    captured = {}

    class CapturingCtx(Ctx):
        async def __aenter__(self):
            client = MagicMock()
            async def fake_post(url, **kw):
                captured["url"] = url
                return resp
            client.post = AsyncMock(side_effect=fake_post)
            return client

    with patch("app.services.portfolio_service.httpx.AsyncClient", return_value=CapturingCtx()):
        await svc._trigger_ensure_and_sync("FPT")
    assert "ensure-and-sync" in captured["url"]
    assert "FPT" in captured["url"]
