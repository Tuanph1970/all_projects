"""
Stock Service - Business logic for stock data operations
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
import json
import pandas as pd

from vnstock import Vnstock

from app.config import get_settings
from app.models.domain import Company, StockPrice, Industry
from app.models.schemas import (
    CompanyResponse,
    CompanyDetailResponse,
    StockPriceResponse,
    HistoricalDataResponse,
    TopMoverResponse,
    SearchResult,
    MarketIndexResponse,
    IndustryResponse,
)
from app.repositories.stock_repository import StockRepository


settings = get_settings()
logger = logging.getLogger(__name__)


class StockService:
    """Service for stock data operations"""

    def __init__(self, repository: StockRepository):
        self.repository = repository
        self._vnstock = None

    @property
    def vnstock(self) -> Vnstock:
        """Lazy load VNStock client"""
        if self._vnstock is None:
            self._vnstock = Vnstock(source=settings.VNSTOCK_DATA_SOURCE)
        return self._vnstock

    # ==================== Company Operations ====================

    async def get_all_companies(
        self,
        page: int = 1,
        page_size: int = 50,
        exchange: Optional[str] = None,
        industry_id: Optional[int] = None,
    ) -> Tuple[List[CompanyResponse], int, int]:
        """Get all companies with pagination"""
        skip = (page - 1) * page_size
        companies, total = await self.repository.get_all_companies(
            skip=skip,
            limit=page_size,
            exchange=exchange,
            industry_id=industry_id,
        )

        total_pages = (total + page_size - 1) // page_size

        responses = [
            CompanyResponse(
                id=c.id,
                symbol=c.symbol,
                name=c.name,
                name_en=c.name_en,
                exchange=c.exchange,
                industry_id=c.industry_id,
                industry_name=c.industry.name if c.industry else None,
                listing_date=c.listing_date,
                outstanding_shares=c.outstanding_shares,
                market_cap=c.market_cap,
                website=c.website,
                description=c.description,
                is_active=c.is_active,
                is_tradeable=c.is_tradeable,
            )
            for c in companies
        ]

        return responses, total, total_pages

    async def get_company_detail(self, symbol: str) -> Optional[CompanyDetailResponse]:
        """Get detailed company information"""
        company = await self.repository.get_company_by_symbol(symbol)
        if not company:
            return None

        # Get latest price
        latest_price = await self.repository.get_latest_price(company.id)

        industry_response = None
        if company.industry:
            industry_response = IndustryResponse(
                id=company.industry.id,
                code=company.industry.code,
                name=company.industry.name,
                name_en=company.industry.name_en,
                description=company.industry.description,
                level=company.industry.level,
            )

        return CompanyDetailResponse(
            id=company.id,
            symbol=company.symbol,
            name=company.name,
            name_en=company.name_en,
            exchange=company.exchange,
            industry=industry_response,
            listing_date=company.listing_date,
            outstanding_shares=company.outstanding_shares,
            market_cap=company.market_cap,
            website=company.website,
            description=company.description,
            current_price=latest_price.close if latest_price else None,
            change=latest_price.change if latest_price else None,
            change_percent=latest_price.change_percent if latest_price else None,
            volume=latest_price.volume if latest_price else None,
        )

    async def search_companies(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search companies by symbol or name"""
        companies = await self.repository.search_companies(query, limit)

        return [
            SearchResult(
                symbol=c.symbol,
                name=c.name,
                exchange=c.exchange,
                industry_name=c.industry.name if c.industry else None,
                match_score=1.0 if c.symbol.upper() == query.upper() else 0.5,
            )
            for c in companies
        ]

    # ==================== Historical Data Operations ====================

    async def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[HistoricalDataResponse]:
        """Get historical price data for a symbol"""
        company = await self.repository.get_company_by_symbol(symbol)
        if not company:
            return None

        # Default to last 1 year
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        prices = await self.repository.get_historical_prices(
            company_id=company.id,
            start_date=start_date,
            end_date=end_date,
        )

        # Sort by date ascending
        prices.sort(key=lambda x: x.date)

        price_responses = [
            StockPriceResponse(
                date=p.date,
                open=p.open,
                high=p.high,
                low=p.low,
                close=p.close,
                volume=p.volume,
                value=p.value,
                adj_close=p.adj_close,
                change=p.change,
                change_percent=p.change_percent,
            )
            for p in prices
        ]

        return HistoricalDataResponse(
            symbol=company.symbol,
            name=company.name,
            exchange=company.exchange,
            data=price_responses,
            count=len(price_responses),
        )

    async def fetch_and_save_historical_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """Fetch historical data from VNStock and save to database"""
        company = await self.repository.get_company_by_symbol(symbol)
        if not company:
            raise ValueError(f"Company not found: {symbol}")

        # Default dates
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        try:
            # Fetch from VNStock
            stock = self.vnstock.stock(symbol=symbol, source=settings.VNSTOCK_DATA_SOURCE)
            df = stock.quote.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
            )

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return 0

            # Convert to StockPrice objects
            prices = []
            for _, row in df.iterrows():
                price = StockPrice(
                    company_id=company.id,
                    date=row.get("time", row.name).date() if hasattr(row.get("time", row.name), "date") else row.get("time", row.name),
                    open=row.get("open"),
                    high=row.get("high"),
                    low=row.get("low"),
                    close=row.get("close"),
                    volume=int(row.get("volume", 0)),
                )
                prices.append(price)

            # Save to database
            count = await self.repository.save_prices(prices)

            # Update company sync timestamp
            await self.repository.update_company(
                company.id,
                last_synced_at=datetime.utcnow()
            )

            return count

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            raise

    # ==================== Top Movers ====================

    async def get_top_gainers(self, limit: int = 10) -> List[TopMoverResponse]:
        """Get top gaining stocks"""
        results = await self.repository.get_top_gainers(limit)

        return [
            TopMoverResponse(
                symbol=company.symbol,
                name=company.name,
                exchange=company.exchange,
                close=price.close,
                change=price.change or 0,
                change_percent=price.change_percent or 0,
                volume=price.volume or 0,
            )
            for company, price in results
        ]

    async def get_top_losers(self, limit: int = 10) -> List[TopMoverResponse]:
        """Get top losing stocks"""
        results = await self.repository.get_top_losers(limit)

        return [
            TopMoverResponse(
                symbol=company.symbol,
                name=company.name,
                exchange=company.exchange,
                close=price.close,
                change=price.change or 0,
                change_percent=price.change_percent or 0,
                volume=price.volume or 0,
            )
            for company, price in results
        ]

    async def get_most_active(self, limit: int = 10) -> List[TopMoverResponse]:
        """Get most active stocks by volume"""
        results = await self.repository.get_top_volume(limit)

        return [
            TopMoverResponse(
                symbol=company.symbol,
                name=company.name,
                exchange=company.exchange,
                close=price.close,
                change=price.change or 0,
                change_percent=price.change_percent or 0,
                volume=price.volume or 0,
            )
            for company, price in results
        ]

    # ==================== Industry Operations ====================

    async def get_all_industries(self) -> List[IndustryResponse]:
        """Get all industries"""
        industries = await self.repository.get_all_industries()

        return [
            IndustryResponse(
                id=i.id,
                code=i.code,
                name=i.name,
                name_en=i.name_en,
                description=i.description,
                level=i.level,
            )
            for i in industries
        ]

    async def get_companies_by_industry(
        self,
        industry_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> List[CompanyResponse]:
        """Get companies in an industry"""
        skip = (page - 1) * page_size
        companies = await self.repository.get_companies_by_industry(
            industry_id=industry_id,
            skip=skip,
            limit=page_size,
        )

        return [
            CompanyResponse(
                id=c.id,
                symbol=c.symbol,
                name=c.name,
                name_en=c.name_en,
                exchange=c.exchange,
                industry_id=c.industry_id,
                listing_date=c.listing_date,
                outstanding_shares=c.outstanding_shares,
                market_cap=c.market_cap,
                website=c.website,
                description=c.description,
                is_active=c.is_active,
                is_tradeable=c.is_tradeable,
            )
            for c in companies
        ]

    # ==================== Market Index Operations ====================

    async def get_market_indices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[MarketIndexResponse]:
        """Get market index data"""
        indices = await self.repository.get_market_indices(start_date, end_date)

        return [
            MarketIndexResponse(
                code=i.code,
                name=i.name,
                date=i.date,
                open=i.open,
                high=i.high,
                low=i.low,
                close=i.close,
                volume=i.volume,
                value=i.value,
                change=i.change,
                change_percent=i.change_percent,
            )
            for i in indices
        ]

    async def get_latest_indices(self) -> List[MarketIndexResponse]:
        """Get latest market index values"""
        indices = await self.repository.get_latest_indices()

        return [
            MarketIndexResponse(
                code=i.code,
                name=i.name,
                date=i.date,
                open=i.open,
                high=i.high,
                low=i.low,
                close=i.close,
                volume=i.volume,
                value=i.value,
                change=i.change,
                change_percent=i.change_percent,
            )
            for i in indices
        ]

    # ==================== Price Board Operations ====================

    async def get_price_board(self, group: str = "VN30") -> List[dict]:
        """
        Get real-time price board data for a stock group.

        Args:
            group: Stock group (VN30, VN100, HOSE, HNX, etc.)

        Returns:
            List of price board data with bid/ask, match prices, etc.
        """
        try:
            # Use VNStock to get price board data
            stock = self.vnstock.stock(symbol="VN30F1M", source=settings.VNSTOCK_DATA_SOURCE)
            df = stock.trading.price_board(symbols_list=group)

            if df.empty:
                logger.warning(f"No price board data for group: {group}")
                return []

            # Flatten multi-level columns if they exist
            if isinstance(df.columns, pd.MultiIndex):
                new_columns = []
                for column in df.columns:
                    if column[1] == 'symbol':
                        new_column = 'symbol'
                    else:
                        new_column = column[0] + column[1]
                    new_columns.append(new_column)
                df.columns = new_columns

            # Convert to list of dictionaries
            records = df.to_dict(orient='records')
            return records

        except Exception as e:
            logger.error(f"Error fetching price board for group {group}: {e}")
            return []
