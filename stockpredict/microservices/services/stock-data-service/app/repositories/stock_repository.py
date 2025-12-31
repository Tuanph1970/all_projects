"""
Stock Repository - Data access layer for stock operations
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import Company, StockPrice, Industry, MarketIndex


class StockRepository:
    """Repository for stock-related database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Company Operations ====================

    async def get_all_companies(
        self,
        skip: int = 0,
        limit: int = 100,
        exchange: Optional[str] = None,
        industry_id: Optional[int] = None,
        is_active: bool = True,
    ) -> Tuple[List[Company], int]:
        """Get all companies with optional filters"""
        query = select(Company).options(selectinload(Company.industry))

        if is_active:
            query = query.where(Company.is_active == True)
        if exchange:
            query = query.where(Company.exchange == exchange.upper())
        if industry_id:
            query = query.where(Company.industry_id == industry_id)

        # Count total
        count_query = select(func.count(Company.id))
        if is_active:
            count_query = count_query.where(Company.is_active == True)
        if exchange:
            count_query = count_query.where(Company.exchange == exchange.upper())
        if industry_id:
            count_query = count_query.where(Company.industry_id == industry_id)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Get paginated results
        query = query.order_by(Company.symbol).offset(skip).limit(limit)
        result = await self.session.execute(query)
        companies = list(result.scalars().all())

        return companies, total

    async def get_company_by_symbol(self, symbol: str) -> Optional[Company]:
        """Get company by symbol"""
        result = await self.session.execute(
            select(Company)
            .options(selectinload(Company.industry))
            .where(Company.symbol == symbol.upper())
        )
        return result.scalar_one_or_none()

    async def get_company_by_id(self, company_id: int) -> Optional[Company]:
        """Get company by ID"""
        result = await self.session.execute(
            select(Company)
            .options(selectinload(Company.industry))
            .where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def search_companies(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Company]:
        """Search companies by symbol or name"""
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(Company)
            .options(selectinload(Company.industry))
            .where(
                or_(
                    Company.symbol.ilike(search_pattern),
                    Company.name.ilike(search_pattern),
                    Company.name_en.ilike(search_pattern),
                )
            )
            .where(Company.is_active == True)
            .order_by(
                # Prioritize exact symbol match
                Company.symbol.ilike(query).desc(),
                Company.symbol
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_company(self, **kwargs) -> Company:
        """Create a new company"""
        company = Company(**kwargs)
        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def update_company(self, company_id: int, **kwargs) -> Optional[Company]:
        """Update company"""
        await self.session.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**kwargs, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return await self.get_company_by_id(company_id)

    # ==================== Stock Price Operations ====================

    async def get_historical_prices(
        self,
        company_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 1000,
    ) -> List[StockPrice]:
        """Get historical prices for a company"""
        query = select(StockPrice).where(StockPrice.company_id == company_id)

        if start_date:
            query = query.where(StockPrice.date >= start_date)
        if end_date:
            query = query.where(StockPrice.date <= end_date)

        query = query.order_by(StockPrice.date.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_price(self, company_id: int) -> Optional[StockPrice]:
        """Get latest price for a company"""
        result = await self.session.execute(
            select(StockPrice)
            .where(StockPrice.company_id == company_id)
            .order_by(StockPrice.date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_prices_by_date(self, trade_date: date) -> List[StockPrice]:
        """Get all prices for a specific date"""
        result = await self.session.execute(
            select(StockPrice)
            .options(selectinload(StockPrice.company))
            .where(StockPrice.date == trade_date)
        )
        return list(result.scalars().all())

    async def save_prices(self, prices: List[StockPrice]) -> int:
        """Save multiple prices (upsert)"""
        for price in prices:
            self.session.add(price)
        await self.session.commit()
        return len(prices)

    async def get_top_gainers(self, limit: int = 10) -> List[Tuple[Company, StockPrice]]:
        """Get top gaining stocks"""
        # Get latest date with prices
        latest_date_result = await self.session.execute(
            select(func.max(StockPrice.date))
        )
        latest_date = latest_date_result.scalar()

        if not latest_date:
            return []

        result = await self.session.execute(
            select(Company, StockPrice)
            .join(StockPrice, Company.id == StockPrice.company_id)
            .where(StockPrice.date == latest_date)
            .where(StockPrice.change_percent > 0)
            .where(Company.is_active == True)
            .order_by(StockPrice.change_percent.desc())
            .limit(limit)
        )
        return list(result.all())

    async def get_top_losers(self, limit: int = 10) -> List[Tuple[Company, StockPrice]]:
        """Get top losing stocks"""
        latest_date_result = await self.session.execute(
            select(func.max(StockPrice.date))
        )
        latest_date = latest_date_result.scalar()

        if not latest_date:
            return []

        result = await self.session.execute(
            select(Company, StockPrice)
            .join(StockPrice, Company.id == StockPrice.company_id)
            .where(StockPrice.date == latest_date)
            .where(StockPrice.change_percent < 0)
            .where(Company.is_active == True)
            .order_by(StockPrice.change_percent.asc())
            .limit(limit)
        )
        return list(result.all())

    async def get_top_volume(self, limit: int = 10) -> List[Tuple[Company, StockPrice]]:
        """Get most active stocks by volume"""
        latest_date_result = await self.session.execute(
            select(func.max(StockPrice.date))
        )
        latest_date = latest_date_result.scalar()

        if not latest_date:
            return []

        result = await self.session.execute(
            select(Company, StockPrice)
            .join(StockPrice, Company.id == StockPrice.company_id)
            .where(StockPrice.date == latest_date)
            .where(Company.is_active == True)
            .order_by(StockPrice.volume.desc())
            .limit(limit)
        )
        return list(result.all())

    # ==================== Industry Operations ====================

    async def get_all_industries(self) -> List[Industry]:
        """Get all industries"""
        result = await self.session.execute(
            select(Industry).order_by(Industry.name)
        )
        return list(result.scalars().all())

    async def get_industry_by_code(self, code: str) -> Optional[Industry]:
        """Get industry by code"""
        result = await self.session.execute(
            select(Industry).where(Industry.code == code)
        )
        return result.scalar_one_or_none()

    async def get_companies_by_industry(
        self,
        industry_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Company]:
        """Get companies in an industry"""
        result = await self.session.execute(
            select(Company)
            .where(Company.industry_id == industry_id)
            .where(Company.is_active == True)
            .order_by(Company.symbol)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== Market Index Operations ====================

    async def get_market_indices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[MarketIndex]:
        """Get market index data"""
        query = select(MarketIndex)

        if start_date:
            query = query.where(MarketIndex.date >= start_date)
        if end_date:
            query = query.where(MarketIndex.date <= end_date)

        query = query.order_by(MarketIndex.date.desc(), MarketIndex.code)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_indices(self) -> List[MarketIndex]:
        """Get latest market index values"""
        # Get latest date
        latest_date_result = await self.session.execute(
            select(func.max(MarketIndex.date))
        )
        latest_date = latest_date_result.scalar()

        if not latest_date:
            return []

        result = await self.session.execute(
            select(MarketIndex)
            .where(MarketIndex.date == latest_date)
            .order_by(MarketIndex.code)
        )
        return list(result.scalars().all())
