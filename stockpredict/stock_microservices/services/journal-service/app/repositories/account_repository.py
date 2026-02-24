"""Account Repository — Database Operations for Journal Accounts & Trading Rules"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Account, TradingRule


class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Account Operations
    # =========================================================================

    async def create_account(self, user_id: int, account_name: str,
                             starting_equity: float, currency: str = "VND",
                             max_risk_per_trade: float = 2.0,
                             max_cumulative_risk: float = 25.0) -> Account:
        account = Account(
            user_id=user_id,
            account_name=account_name,
            starting_equity=starting_equity,
            current_equity=starting_equity,
            max_risk_per_trade=max_risk_per_trade,
            max_cumulative_risk=max_cumulative_risk,
            currency=currency
        )
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def get_account_by_id(self, account_id: int, user_id: int) -> Optional[Account]:
        result = await self.session.execute(
            select(Account)
            .where(and_(Account.id == account_id, Account.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_accounts_by_user(self, user_id: int) -> List[Account]:
        result = await self.session.execute(
            select(Account)
            .where(Account.user_id == user_id)
            .order_by(Account.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_account(self, account_id: int, user_id: int, **kwargs) -> Optional[Account]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(Account)
            .where(and_(Account.id == account_id, Account.user_id == user_id))
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_account_by_id(account_id, user_id)

    async def delete_account(self, account_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            delete(Account)
            .where(and_(Account.id == account_id, Account.user_id == user_id))
        )
        await self.session.commit()
        return result.rowcount > 0

    # =========================================================================
    # Trading Rules Operations
    # =========================================================================

    async def create_rule(self, account_id: int, rule_text: str,
                          category: str, sort_order: int = 0) -> TradingRule:
        rule = TradingRule(
            account_id=account_id,
            rule_text=rule_text,
            category=category,
            sort_order=sort_order
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def get_rules_by_account(self, account_id: int, active_only: bool = False) -> List[TradingRule]:
        query = select(TradingRule).where(TradingRule.account_id == account_id)
        if active_only:
            query = query.where(TradingRule.is_active == True)
        result = await self.session.execute(query.order_by(TradingRule.sort_order))
        return list(result.scalars().all())

    async def get_rule_by_id(self, rule_id: int, account_id: int) -> Optional[TradingRule]:
        result = await self.session.execute(
            select(TradingRule)
            .where(and_(TradingRule.id == rule_id, TradingRule.account_id == account_id))
        )
        return result.scalar_one_or_none()

    async def update_rule(self, rule_id: int, account_id: int, **kwargs) -> Optional[TradingRule]:
        await self.session.execute(
            update(TradingRule)
            .where(and_(TradingRule.id == rule_id, TradingRule.account_id == account_id))
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_rule_by_id(rule_id, account_id)

    async def delete_rule(self, rule_id: int, account_id: int) -> bool:
        result = await self.session.execute(
            delete(TradingRule)
            .where(and_(TradingRule.id == rule_id, TradingRule.account_id == account_id))
        )
        await self.session.commit()
        return result.rowcount > 0
