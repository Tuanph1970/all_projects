"""
Stock Repository - Data access layer for stock operations
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import Company, StockPrice, Industry, MarketIndex, CompanyProfile, FinancialStatement


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
        """Save multiple prices (upsert on (company_id, date)).

        Daily re-syncs re-fetch a window that overlaps what is already
        stored, so a plain INSERT collides on idx_price_company_date and the
        whole batch (including the genuinely new days) is lost.
        """
        if not prices:
            return 0
        rows = [
            {
                "company_id": p.company_id,
                "date": p.date,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
                "value": p.value,
                "adj_close": p.adj_close,
                "change": p.change,
                "change_percent": p.change_percent,
            }
            for p in prices
        ]
        stmt = mysql_insert(StockPrice).values(rows)
        stmt = stmt.on_duplicate_key_update(
            {col: stmt.inserted[col] for col in ("open", "high", "low", "close", "volume", "value", "adj_close", "change", "change_percent")}
        )
        await self.session.execute(stmt)
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

    # ==================== Company Profile Cache Operations ====================

    async def get_company_profile(self, symbol: str) -> Optional[CompanyProfile]:
        """Get cached company profile by ticker"""
        result = await self.session.execute(
            select(CompanyProfile).where(CompanyProfile.ticker == symbol.upper())
        )
        return result.scalar_one_or_none()

    async def upsert_company_profile(self, symbol: str, **kwargs) -> CompanyProfile:
        """Insert or update a company profile"""
        existing = await self.get_company_profile(symbol)
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            existing.synced_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        profile = CompanyProfile(ticker=symbol.upper(), **kwargs)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def count_company_profiles(self) -> int:
        """Count total cached company profiles"""
        result = await self.session.execute(
            select(func.count(CompanyProfile.id))
        )
        return result.scalar() or 0

    async def get_oldest_profile_sync(self) -> Optional[datetime]:
        """Get the oldest synced_at among all profiles"""
        result = await self.session.execute(
            select(func.min(CompanyProfile.synced_at))
        )
        return result.scalar()

    # ==================== Financial Statement Cache Operations ====================

    async def get_financial_statements(
        self, symbol: str, statement_type: str, period: str
    ) -> List[FinancialStatement]:
        """Get cached financial statements"""
        result = await self.session.execute(
            select(FinancialStatement)
            .where(
                and_(
                    FinancialStatement.symbol == symbol.upper(),
                    FinancialStatement.statement_type == statement_type,
                    FinancialStatement.period == period,
                )
            )
            .order_by(FinancialStatement.report_year.desc())
        )
        return list(result.scalars().all())

    async def bulk_upsert_market_indices(self, records: List[dict]) -> int:
        """Replace the stored rows for each (code, date) in `records`.

        Backlog #91: `market_indices` had a reader and two public endpoints
        but NO WRITER anywhere, so both endpoints returned empty forever.
        This is that writer.

        Delete-then-insert per code, bounded to the date span being written,
        mirroring `bulk_upsert_financial_statements`. The model has a UNIQUE
        index on (code, date), so a plain insert would raise on the overlap
        every refresh produces.
        """
        if not records:
            return 0

        by_code: dict = {}
        for rec in records:
            by_code.setdefault(rec["code"], []).append(rec)

        written = 0
        for code, rows in by_code.items():
            days = [r["date"] for r in rows]
            await self.session.execute(
                delete(MarketIndex).where(
                    and_(
                        MarketIndex.code == code,
                        MarketIndex.date >= min(days),
                        MarketIndex.date <= max(days),
                    )
                )
            )
            for r in rows:
                self.session.add(MarketIndex(
                    code=code,
                    name=r.get("name") or code,
                    date=r["date"],
                    open=r.get("open"),
                    high=r.get("high"),
                    low=r.get("low"),
                    close=r["close"],
                    volume=r.get("volume"),
                    value=r.get("value"),
                    change=r.get("change"),
                    change_percent=r.get("change_percent"),
                ))
                written += 1

        await self.session.commit()
        return written

    async def bulk_upsert_financial_statements(
        self, symbol: str, statement_type: str, period: str, records: List[dict]
    ) -> int:
        """Delete old rows for this (symbol, type, period) and insert fresh ones."""
        await self.session.execute(
            delete(FinancialStatement).where(
                and_(
                    FinancialStatement.symbol == symbol.upper(),
                    FinancialStatement.statement_type == statement_type,
                    FinancialStatement.period == period,
                )
            )
        )
        now = datetime.utcnow()
        for rec in records:
            row = FinancialStatement(
                symbol=symbol.upper(),
                statement_type=statement_type,
                period=period,
                report_year=rec.get("report_year"),
                data=rec["data"],
                synced_at=now,
            )
            self.session.add(row)
        await self.session.commit()
        return len(records)
