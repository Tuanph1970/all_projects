"""Account Service — Business Logic for Journal Accounts & Trading Rules"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account_repository import AccountRepository
from app.models.domain import Account, TradingRule
from app.models.schemas import AccountCreate, AccountUpdate, TradingRuleCreate, TradingRuleUpdate


class AccountService:
    def __init__(self, session: AsyncSession):
        self.repo = AccountRepository(session)

    # =========================================================================
    # Account Operations
    # =========================================================================

    async def create_account(self, user_id: int, data: AccountCreate) -> Account:
        return await self.repo.create_account(
            user_id=user_id,
            account_name=data.account_name,
            starting_equity=data.starting_equity,
            currency=data.currency,
            max_risk_per_trade=data.max_risk_per_trade,
            max_cumulative_risk=data.max_cumulative_risk
        )

    async def get_accounts(self, user_id: int) -> List[Account]:
        return await self.repo.get_accounts_by_user(user_id)

    async def get_account(self, account_id: int, user_id: int) -> Optional[Account]:
        return await self.repo.get_account_by_id(account_id, user_id)

    async def update_account(self, account_id: int, user_id: int, data: AccountUpdate) -> Optional[Account]:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.repo.get_account_by_id(account_id, user_id)
        return await self.repo.update_account(account_id, user_id, **update_data)

    async def delete_account(self, account_id: int, user_id: int) -> bool:
        return await self.repo.delete_account(account_id, user_id)

    # =========================================================================
    # Trading Rules Operations
    # =========================================================================

    async def create_rule(self, account_id: int, user_id: int, data: TradingRuleCreate) -> Optional[TradingRule]:
        # Verify account ownership
        account = await self.repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        return await self.repo.create_rule(
            account_id=account_id,
            rule_text=data.rule_text,
            category=data.category,
            sort_order=data.sort_order
        )

    async def get_rules(self, account_id: int, user_id: int, active_only: bool = False) -> Optional[List[TradingRule]]:
        account = await self.repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        return await self.repo.get_rules_by_account(account_id, active_only)

    async def update_rule(self, account_id: int, user_id: int,
                          rule_id: int, data: TradingRuleUpdate) -> Optional[TradingRule]:
        account = await self.repo.get_account_by_id(account_id, user_id)
        if not account:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.repo.get_rule_by_id(rule_id, account_id)
        return await self.repo.update_rule(rule_id, account_id, **update_data)

    async def delete_rule(self, account_id: int, user_id: int, rule_id: int) -> bool:
        account = await self.repo.get_account_by_id(account_id, user_id)
        if not account:
            return False
        return await self.repo.delete_rule(rule_id, account_id)
