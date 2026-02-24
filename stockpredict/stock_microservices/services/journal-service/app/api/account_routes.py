"""Account & Trading Rules API Routes"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.account_service import AccountService
from app.models.schemas import (
    AccountCreate, AccountUpdate, AccountResponse,
    TradingRuleCreate, TradingRuleUpdate, TradingRuleResponse
)

router = APIRouter()


# =============================================================================
# Account Endpoints
# =============================================================================

@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new journal account"""
    service = AccountService(db)
    return await service.create_account(current_user["user_id"], data)


@router.get("/accounts", response_model=List[AccountResponse])
async def get_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all journal accounts for current user"""
    service = AccountService(db)
    return await service.get_accounts(current_user["user_id"])


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific journal account"""
    service = AccountService(db)
    account = await service.get_account(account_id, current_user["user_id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update journal account settings"""
    service = AccountService(db)
    account = await service.update_account(account_id, current_user["user_id"], data)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a journal account and all its data"""
    service = AccountService(db)
    deleted = await service.delete_account(account_id, current_user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")


# =============================================================================
# Trading Rules Endpoints
# =============================================================================

@router.post("/accounts/{account_id}/rules", response_model=TradingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    account_id: int,
    data: TradingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a trading rule to account"""
    service = AccountService(db)
    rule = await service.create_rule(account_id, current_user["user_id"], data)
    if not rule:
        raise HTTPException(status_code=404, detail="Account not found")
    return rule


@router.get("/accounts/{account_id}/rules", response_model=List[TradingRuleResponse])
async def get_rules(
    account_id: int,
    active_only: bool = Query(False, description="Show only active rules"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all trading rules for an account"""
    service = AccountService(db)
    rules = await service.get_rules(account_id, current_user["user_id"], active_only)
    if rules is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return rules


@router.put("/accounts/{account_id}/rules/{rule_id}", response_model=TradingRuleResponse)
async def update_rule(
    account_id: int,
    rule_id: int,
    data: TradingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a trading rule"""
    service = AccountService(db)
    rule = await service.update_rule(account_id, current_user["user_id"], rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="Account or rule not found")
    return rule


@router.delete("/accounts/{account_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    account_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a trading rule"""
    service = AccountService(db)
    deleted = await service.delete_rule(account_id, current_user["user_id"], rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account or rule not found")
