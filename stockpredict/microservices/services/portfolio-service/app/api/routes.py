"""Portfolio Service API Routes"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.portfolio_service import PortfolioService
from app.models.schemas import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse, PortfolioWithHoldings, PortfolioSummary,
    HoldingCreate, HoldingUpdate, HoldingResponse,
    TransactionCreate, TransactionResponse,
    AlertCreate, AlertUpdate, AlertResponse,
    BulkTransactionCreate, BulkTransactionResponse,
    WatchlistAdd
)

router = APIRouter()


# Portfolio Endpoints
@router.post("/portfolios", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new portfolio"""
    service = PortfolioService(db)
    return await service.create_portfolio(current_user["user_id"], data)


@router.get("/portfolios", response_model=List[PortfolioResponse])
async def get_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all portfolios for current user"""
    service = PortfolioService(db)
    return await service.get_user_portfolios(current_user["user_id"])


@router.get("/portfolios/default", response_model=PortfolioResponse)
async def get_default_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get or create default portfolio"""
    service = PortfolioService(db)
    return await service.get_or_create_default_portfolio(current_user["user_id"])


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioWithHoldings)
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get portfolio with holdings and transactions"""
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id, current_user["user_id"])
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/portfolios/{portfolio_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get portfolio summary with statistics"""
    service = PortfolioService(db)
    summary = await service.get_portfolio_summary(portfolio_id, current_user["user_id"])
    if not summary:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return summary


@router.put("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update portfolio details"""
    service = PortfolioService(db)
    portfolio = await service.update_portfolio(portfolio_id, current_user["user_id"], data)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.delete("/portfolios/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a portfolio"""
    service = PortfolioService(db)
    deleted = await service.delete_portfolio(portfolio_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Portfolio not found")


# Holdings Endpoints
@router.post("/portfolios/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def add_holding(
    portfolio_id: int,
    data: HoldingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a stock to portfolio"""
    service = PortfolioService(db)
    holding = await service.add_holding(portfolio_id, current_user["user_id"], data)
    if not holding:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return holding


@router.get("/portfolios/{portfolio_id}/holdings", response_model=List[HoldingResponse])
async def get_holdings(
    portfolio_id: int,
    watchlist_only: Optional[bool] = Query(None, description="Filter watchlist items"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all holdings in a portfolio"""
    service = PortfolioService(db)
    return await service.get_holdings(portfolio_id, current_user["user_id"], watchlist_only)


@router.put("/portfolios/{portfolio_id}/holdings/{symbol}", response_model=HoldingResponse)
async def update_holding(
    portfolio_id: int,
    symbol: str,
    data: HoldingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update holding details"""
    service = PortfolioService(db)
    holding = await service.update_holding(portfolio_id, current_user["user_id"], symbol, data)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding


@router.delete("/portfolios/{portfolio_id}/holdings/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_holding(
    portfolio_id: int,
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a stock from portfolio"""
    service = PortfolioService(db)
    removed = await service.remove_holding(portfolio_id, current_user["user_id"], symbol)
    if not removed:
        raise HTTPException(status_code=404, detail="Holding not found")


@router.post("/portfolios/{portfolio_id}/refresh-prices")
async def refresh_prices(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Refresh current prices for all holdings"""
    service = PortfolioService(db)
    updated = await service.refresh_prices(portfolio_id, current_user["user_id"])
    return {"updated": updated, "message": f"Updated prices for {updated} holdings"}


# Transaction Endpoints
@router.post("/portfolios/{portfolio_id}/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def record_transaction(
    portfolio_id: int,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record a buy/sell transaction"""
    service = PortfolioService(db)
    transaction = await service.record_transaction(portfolio_id, current_user["user_id"], data)
    if not transaction:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return transaction


@router.post("/portfolios/{portfolio_id}/transactions/bulk", response_model=BulkTransactionResponse)
async def bulk_record_transactions(
    portfolio_id: int,
    data: BulkTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record multiple transactions at once"""
    service = PortfolioService(db)
    successful = 0
    failed = 0
    transactions = []
    errors = []

    for tx_data in data.transactions:
        try:
            tx = await service.record_transaction(portfolio_id, current_user["user_id"], tx_data)
            if tx:
                transactions.append(tx)
                successful += 1
            else:
                failed += 1
                errors.append(f"Failed to record transaction for {tx_data.symbol}")
        except Exception as e:
            failed += 1
            errors.append(f"Error for {tx_data.symbol}: {str(e)}")

    return BulkTransactionResponse(
        successful=successful,
        failed=failed,
        transactions=transactions,
        errors=errors
    )


@router.get("/portfolios/{portfolio_id}/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    portfolio_id: int,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get transaction history"""
    service = PortfolioService(db)
    return await service.get_transactions(portfolio_id, current_user["user_id"], symbol, limit, offset)


@router.delete("/portfolios/{portfolio_id}/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a transaction"""
    service = PortfolioService(db)
    deleted = await service.delete_transaction(portfolio_id, current_user["user_id"], transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")


# Price Alert Endpoints
@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a price alert"""
    service = PortfolioService(db)
    return await service.create_alert(current_user["user_id"], data)


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    active_only: bool = Query(True, description="Show only active alerts"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all price alerts"""
    service = PortfolioService(db)
    return await service.get_alerts(current_user["user_id"], active_only)


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a price alert"""
    service = PortfolioService(db)
    alert = await service.update_alert(alert_id, current_user["user_id"], data)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a price alert"""
    service = PortfolioService(db)
    deleted = await service.delete_alert(alert_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")


# Watchlist Endpoints (convenience methods)
@router.post("/watchlist/{symbol}", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add symbol to watchlist (default portfolio)"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    holding = await service.add_holding(
        default_portfolio.id,
        current_user["user_id"],
        HoldingCreate(symbol=symbol, is_watchlist_only=True)
    )
    if not holding:
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")
    return holding


@router.get("/watchlist", response_model=List[HoldingResponse])
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get watchlist items from default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    return await service.get_holdings(default_portfolio.id, current_user["user_id"], watchlist_only=True)


@router.delete("/watchlist/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove symbol from watchlist"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    removed = await service.remove_holding(default_portfolio.id, current_user["user_id"], symbol)
    if not removed:
        raise HTTPException(status_code=404, detail="Symbol not in watchlist")


# =============================================================================
# Convenience Routes (use default portfolio)
# =============================================================================

@router.post("/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def add_holding_default(
    data: HoldingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a holding to default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    holding = await service.add_holding(default_portfolio.id, current_user["user_id"], data)
    if not holding:
        raise HTTPException(status_code=500, detail="Failed to add holding")
    return holding


@router.get("/holdings", response_model=List[HoldingResponse])
async def get_holdings_default(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get holdings from default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    return await service.get_holdings(default_portfolio.id, current_user["user_id"])


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def record_transaction_default(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record a transaction in default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    transaction = await service.record_transaction(default_portfolio.id, current_user["user_id"], data)
    if not transaction:
        raise HTTPException(status_code=500, detail="Failed to record transaction")
    return transaction


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions_default(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get transaction history from default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    return await service.get_transactions(default_portfolio.id, current_user["user_id"], symbol, limit, offset)


@router.post("/watchlist", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist_json(
    data: WatchlistAdd,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add symbol to watchlist via JSON body"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    holding = await service.add_holding(
        default_portfolio.id,
        current_user["user_id"],
        HoldingCreate(symbol=data.symbol, is_watchlist_only=True)
    )
    if not holding:
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")
    return holding


# Static routes MUST be defined before dynamic /{portfolio_id} route
@router.get("/summary", response_model=PortfolioSummary)
async def get_summary_default(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get summary for default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    summary = await service.get_portfolio_summary(default_portfolio.id, current_user["user_id"])
    if not summary:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return summary


@router.get("/performance")
async def get_performance_default(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get performance for default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    summary = await service.get_portfolio_summary(default_portfolio.id, current_user["user_id"])
    if not summary:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {
        "portfolio_id": summary.portfolio_id,
        "total_invested": summary.total_invested,
        "current_value": summary.current_value,
        "profit_loss": summary.total_profit_loss,
        "profit_loss_percent": summary.total_profit_loss_percent
    }


@router.get("/metrics")
async def get_metrics_default(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get metrics for default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    summary = await service.get_portfolio_summary(default_portfolio.id, current_user["user_id"])
    if not summary:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {
        "portfolio_id": summary.portfolio_id,
        "total_holdings": summary.total_holdings,
        "total_invested": summary.total_invested,
        "current_value": summary.current_value,
        "profit_loss": summary.total_profit_loss,
        "profit_loss_percent": summary.total_profit_loss_percent
    }


@router.post("/refresh")
async def refresh_default(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Refresh prices for default portfolio"""
    service = PortfolioService(db)
    default_portfolio = await service.get_or_create_default_portfolio(current_user["user_id"])
    updated = await service.refresh_prices(default_portfolio.id, current_user["user_id"])
    return {"updated": updated, "message": f"Updated prices for {updated} holdings"}


# Dynamic route - MUST be LAST to not shadow static routes
@router.get("/{portfolio_id}", response_model=PortfolioWithHoldings)
async def get_portfolio_alias(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get portfolio by ID (alias for /portfolios/{id})"""
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id, current_user["user_id"])
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio
