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
    CompanyListingResponse,
    StockPriceResponse,
    HistoricalDataResponse,
    TopMoverResponse,
    SearchResult,
    MarketIndexResponse,
    IndustryResponse,
    PaginatedResponse,
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

        # If database is empty, fallback to live data from vnstock
        if total == 0 and not exchange and not industry_id:
            logger.info("Database empty, fetching live company data from vnstock")
            live_companies = await self.get_all_companies_live()
            total = len(live_companies)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            # Paginate live data
            paginated = live_companies[skip:skip + page_size]

            responses = [
                CompanyResponse(
                    id=0,
                    symbol=c.symbol,
                    name=c.name,
                    name_en=None,
                    exchange=c.exchange,
                    industry_id=None,
                    industry_name=None,
                    listing_date=None,
                    outstanding_shares=None,
                    market_cap=None,
                    website=None,
                    description=None,
                    is_active=True,
                    is_tradeable=True,
                )
                for c in paginated
            ]
            return responses, total, total_pages

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

    # ==================== Live Company Data from VNStock ====================

    async def get_all_companies_live(self) -> List[CompanyListingResponse]:
        """
        Get all companies from vnstock (live data).
        This fetches directly from vnstock API, not from database.
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)
            df = stock.listing.all_symbols()

            if df is None or df.empty:
                logger.warning("No companies returned from vnstock")
                return []

            companies = [
                CompanyListingResponse(
                    symbol=row["symbol"],
                    name=row.get("organ_name", row.get("organName", "")),
                    exchange=None,  # all_symbols doesn't provide exchange
                )
                for _, row in df.iterrows()
            ]

            logger.info(f"Fetched {len(companies)} companies from vnstock")
            return companies

        except Exception as e:
            logger.error(f"Error fetching companies from vnstock: {e}")
            return []

    async def get_companies_by_group_live(self, group: str = "VN30") -> List[CompanyListingResponse]:
        """
        Get companies by stock group from vnstock (live data).

        Args:
            group: Stock group (VN30, VN100, HOSE, HNX, UPCOM, etc.)
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)

            # symbols_by_group returns a Series, not DataFrame
            symbols = stock.listing.symbols_by_group(group.upper())

            if symbols is None or len(symbols) == 0:
                logger.warning(f"No companies returned for group {group}")
                return []

            # Convert Series to list of CompanyListingResponse
            companies = [
                CompanyListingResponse(
                    symbol=symbol,
                    name="",  # symbols_by_group only returns symbols, not names
                    exchange=group.upper() if group.upper() in ["HOSE", "HNX", "UPCOM"] else None,
                )
                for symbol in symbols
            ]

            logger.info(f"Fetched {len(companies)} companies for group {group}")
            return companies

        except Exception as e:
            logger.error(f"Error fetching companies by group {group}: {e}")
            return []

    async def search_companies_live(self, query: str, limit: int = 20) -> List[CompanyListingResponse]:
        """
        Search companies from vnstock (live data).
        Searches through all listed companies by symbol or name.
        """
        try:
            # Get all companies first
            all_companies = await self.get_all_companies_live()

            if not all_companies:
                return []

            query_upper = query.upper()
            query_lower = query.lower()

            # Filter by symbol or name match
            matched = []
            for company in all_companies:
                symbol_match = query_upper in company.symbol.upper()
                name_match = query_lower in company.name.lower() if company.name else False

                if symbol_match or name_match:
                    matched.append(company)

                if len(matched) >= limit:
                    break

            return matched

        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []

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

        # If database is empty, fallback to live data
        if not results:
            logger.info("Database empty, fetching live top gainers from price board")
            return await self._get_top_movers_live(limit=limit, sort_by="gainers")

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

        # If database is empty, fallback to live data
        if not results:
            logger.info("Database empty, fetching live top losers from price board")
            return await self._get_top_movers_live(limit=limit, sort_by="losers")

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

        # If database is empty, fallback to live data
        if not results:
            logger.info("Database empty, fetching live most active from price board")
            return await self._get_top_movers_live(limit=limit, sort_by="volume")

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

    async def _get_top_movers_live(self, limit: int = 10, sort_by: str = "gainers") -> List[TopMoverResponse]:
        """
        Get top movers from live price board data.

        Args:
            limit: Number of results to return
            sort_by: "gainers" for top gainers, "losers" for top losers, "volume" for most active
        """
        try:
            # Fetch price board for VN100 to get a broader market view
            price_data = await self.get_price_board(group="VN100")

            if not price_data:
                # Fallback to VN30 if VN100 fails
                price_data = await self.get_price_board(group="VN30")

            if not price_data:
                logger.warning("No price board data available")
                return []

            # Get company names for enrichment
            company_names = {}
            try:
                stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)
                all_symbols_df = stock.listing.all_symbols()
                if all_symbols_df is not None and not all_symbols_df.empty:
                    for _, row in all_symbols_df.iterrows():
                        symbol = row.get("symbol", "")
                        name = row.get("organ_name", row.get("organName", ""))
                        if symbol and name:
                            company_names[symbol] = name
            except Exception as e:
                logger.warning(f"Could not load company names: {e}")

            # Filter out entries without valid price data
            valid_data = [
                item for item in price_data
                if item.get("matchPrice") and item.get("changePercent") is not None
            ]

            # Sort based on criteria
            if sort_by == "gainers":
                # Sort by change percent descending, filter positive changes
                sorted_data = sorted(
                    [d for d in valid_data if (d.get("changePercent") or 0) > 0],
                    key=lambda x: x.get("changePercent", 0),
                    reverse=True
                )
            elif sort_by == "losers":
                # Sort by change percent ascending, filter negative changes
                sorted_data = sorted(
                    [d for d in valid_data if (d.get("changePercent") or 0) < 0],
                    key=lambda x: x.get("changePercent", 0),
                    reverse=False
                )
            else:  # volume
                # Sort by total volume descending
                sorted_data = sorted(
                    valid_data,
                    key=lambda x: x.get("totalQty", 0) or 0,
                    reverse=True
                )

            # Take top N results
            top_results = sorted_data[:limit]

            # Convert to TopMoverResponse
            movers = []
            for item in top_results:
                symbol = item.get("symbol", "")
                movers.append(TopMoverResponse(
                    symbol=symbol,
                    name=company_names.get(symbol, symbol),
                    exchange=item.get("exchange", "HOSE"),
                    close=item.get("matchPrice", 0),
                    change=item.get("change", 0) or 0,
                    change_percent=item.get("changePercent", 0) or 0,
                    volume=item.get("totalQty", 0) or 0,
                ))

            logger.info(f"Fetched {len(movers)} {sort_by} from live price board")
            return movers

        except Exception as e:
            logger.error(f"Error fetching top movers from live data: {e}")
            return []

    # ==================== Industry Operations ====================

    async def get_all_industries(self) -> List[IndustryResponse]:
        """Get all industries"""
        industries = await self.repository.get_all_industries()

        # If database is empty, fallback to live data from vnstock
        if not industries:
            logger.info("Database empty, fetching live industry data from vnstock")
            return await self.get_all_industries_live()

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

    async def get_all_industries_live(self) -> List[IndustryResponse]:
        """
        Get all industries from vnstock (live data).
        Uses symbols_by_industries() to extract unique industries since
        industries_icb() is not available for all data sources.
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)

            # Try industries_icb() first, fallback to symbols_by_industries()
            try:
                df = stock.listing.industries_icb()
                if df is not None and not df.empty:
                    industries = []
                    for idx, row in df.iterrows():
                        industry = IndustryResponse(
                            id=idx + 1,
                            code=str(row.get("icb_code", row.get("icbCode", ""))),
                            name=row.get("icb_name", row.get("icbName", "")),
                            name_en=row.get("en_icb_name", row.get("enIcbName", None)),
                            description=None,
                            level=int(row.get("level", 1)) if row.get("level") is not None else 1,
                        )
                        industries.append(industry)
                    logger.info(f"Fetched {len(industries)} industries from industries_icb()")
                    return industries
            except Exception as icb_error:
                logger.warning(f"industries_icb() not available: {icb_error}, trying symbols_by_industries()")

            # Fallback: Use symbols_by_industries() and extract unique industries
            df = stock.listing.symbols_by_industries()

            if df is None or df.empty:
                logger.warning("No data returned from vnstock symbols_by_industries")
                return []

            # Log columns for debugging
            logger.info(f"symbols_by_industries columns: {df.columns.tolist()}")

            # Extract unique industries from the data
            # Look for icb_code2/icb_name2 (level 2 industries) as they are broader categories
            industries = []
            seen_codes = set()

            # Determine which columns to use for industry extraction
            code_col = None
            name_col = None
            name_en_col = None

            for col in ['industry_code', 'icb_code2', 'icb_code3', 'icb_code']:
                if col in df.columns:
                    code_col = col
                    break

            for col in ['industry_name', 'icb_name2', 'icb_name3', 'icb_name']:
                if col in df.columns:
                    name_col = col
                    break

            for col in ['industry_name_en', 'en_icb_name2', 'en_icb_name3', 'en_icb_name']:
                if col in df.columns:
                    name_en_col = col
                    break

            if code_col is None or name_col is None:
                logger.warning(f"Could not find industry columns. Available: {df.columns.tolist()}")
                return []

            idx = 1
            for _, row in df.iterrows():
                code = str(row.get(code_col, ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    industry = IndustryResponse(
                        id=idx,
                        code=code,
                        name=row.get(name_col, ""),
                        name_en=row.get(name_en_col, None) if name_en_col else None,
                        description=None,
                        level=2 if 'icb_code2' in code_col else 3,
                    )
                    industries.append(industry)
                    idx += 1

            # Sort by code
            industries.sort(key=lambda x: x.code)

            logger.info(f"Extracted {len(industries)} unique industries from symbols_by_industries()")
            return industries

        except Exception as e:
            logger.error(f"Error fetching industries from vnstock: {e}")
            return []

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

    async def get_companies_by_industry_code(
        self,
        industry_code: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[CompanyResponse]:
        """
        Get companies in an industry by ICB code.
        Falls back to vnstock live data when database is empty.
        """
        # First try to get from database
        skip = (page - 1) * page_size

        # Try to find industry by code in database
        industry = await self.repository.get_industry_by_code(industry_code)

        if industry:
            companies = await self.repository.get_companies_by_industry(
                industry_id=industry.id,
                skip=skip,
                limit=page_size,
            )
            total = len(companies)  # This is simplified, ideally get count from repo
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            items = [
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

            return PaginatedResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        # Fallback to live data from vnstock
        logger.info(f"Database empty for industry {industry_code}, fetching live data from vnstock")
        return await self.get_companies_by_industry_code_live(
            industry_code=industry_code,
            page=page,
            page_size=page_size,
        )

    async def get_companies_by_industry_code_live(
        self,
        industry_code: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[CompanyResponse]:
        """
        Get companies by industry code from vnstock (live data).
        Uses symbols_by_industries() method and enriches with company names from all_symbols().
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)
            df = stock.listing.symbols_by_industries()

            if df is None or df.empty:
                logger.warning("No data returned from vnstock symbols_by_industries")
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                )

            # Log columns for debugging
            logger.info(f"get_companies_by_industry_code_live columns: {df.columns.tolist()}")

            # Filter by industry code - check various possible column names
            icb_col = None
            for col in ['industry_code', 'icb_code', 'icbCode', 'icb_code3', 'icb_code2', 'icb_code4']:
                if col in df.columns:
                    icb_col = col
                    break

            if icb_col is None:
                logger.warning(f"Could not find ICB code column in dataframe. Columns: {df.columns.tolist()}")
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                )

            # Filter by industry code (match start of code for hierarchical matching)
            filtered_df = df[df[icb_col].astype(str).str.startswith(str(industry_code))]

            if filtered_df.empty:
                logger.warning(f"No companies found for industry code: {industry_code}")
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                )

            total = len(filtered_df)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            # Paginate
            skip = (page - 1) * page_size
            paginated_df = filtered_df.iloc[skip:skip + page_size]

            # Try to get company names from all_symbols() for enrichment
            company_names = {}
            try:
                all_symbols_df = stock.listing.all_symbols()
                if all_symbols_df is not None and not all_symbols_df.empty:
                    for _, sym_row in all_symbols_df.iterrows():
                        symbol = sym_row.get("symbol", "")
                        name = sym_row.get("organ_name", sym_row.get("organName", ""))
                        if symbol and name:
                            company_names[symbol] = name
                    logger.info(f"Loaded {len(company_names)} company names for enrichment")
            except Exception as e:
                logger.warning(f"Could not load company names for enrichment: {e}")

            # Determine column names for industry data
            name_col = None
            for col in ['industry_name', 'icb_name', 'icb_name2', 'icb_name3']:
                if col in df.columns:
                    name_col = col
                    break

            companies = []
            for idx, row in paginated_df.iterrows():
                symbol = row.get("symbol", row.get("ticker", ""))

                # Get industry name from the available column
                industry_name = row.get(name_col, "") if name_col else ""

                # Get industry code value
                ind_code = str(row.get(icb_col, "")) if icb_col else ""

                # Get company name from enrichment data or use symbol
                company_name = company_names.get(symbol, symbol)

                company = CompanyResponse(
                    id=0,
                    symbol=symbol,
                    name=company_name,
                    name_en=None,
                    exchange=row.get("exchange", None),
                    industry_id=None,
                    industry_name=industry_name,
                    icb_name2=industry_name,  # Use same industry name for display
                    icb_name3=ind_code,  # Show industry code in level 3
                    icb_name4=None,
                    com_type_code=row.get("com_type_code", None),
                    listing_date=None,
                    outstanding_shares=None,
                    market_cap=None,
                    website=None,
                    description=None,
                    is_active=True,
                    is_tradeable=True,
                )
                companies.append(company)

            logger.info(f"Fetched {len(companies)} companies for industry {industry_code} from vnstock")

            return PaginatedResponse(
                items=companies,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"Error fetching companies by industry from vnstock: {e}")
            return PaginatedResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

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

    # Stock group symbol mappings
    STOCK_GROUPS = {
        "VN30": ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
                 "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
                 "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"],
        "VN100": ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
                  "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
                  "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
                  "AGG", "ANV", "ASM", "BWE", "CII", "CMG", "DBC", "DCM", "DGC", "DGW",
                  "DIG", "DPM", "DXG", "ELC", "EVF", "FRT", "GEX", "HAG", "HCM", "HDC",
                  "HDG", "HHV", "HSG", "HT1", "IDC", "KBC", "KDC", "KDH", "LPB", "MIG",
                  "MSH", "NLG", "NT2", "NVL", "OCB", "PAN", "PC1", "PDR", "PHR", "PNJ",
                  "PPC", "PTB", "PVD", "PVS", "PVT", "REE", "SBT", "SCS", "SIP", "SJS",
                  "SZC", "TCH", "TLG", "TNH", "VCI", "VGC", "VHC", "VIX", "VND", "VOS",
                  "VPI", "VTP"],
    }

    # Browser-like headers for Vietcap API
    VIETCAP_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://trading.vietcap.com.vn',
        'Referer': 'https://trading.vietcap.com.vn/'
    }

    async def get_price_board(self, group: str = "VN30") -> List[dict]:
        """
        Get real-time price board data for a stock group.

        Args:
            group: Stock group (VN30, VN100, HOSE, HNX, etc.)

        Returns:
            List of price board data with bid/ask, match prices, etc.
        """
        import httpx

        try:
            # Get symbols for the group
            symbols = self.STOCK_GROUPS.get(group.upper(), self.STOCK_GROUPS.get("VN30"))

            # Call Vietcap API directly with browser headers
            url = "https://trading.vietcap.com.vn/api/price/symbols/getList"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={"symbols": symbols},
                    headers=self.VIETCAP_HEADERS
                )

                if response.status_code != 200:
                    logger.warning(f"Vietcap API returned {response.status_code} for group: {group}")
                    return []

                data = response.json()

                if not data:
                    logger.warning(f"No price board data for group: {group}")
                    return []

                # Transform response to simplified format
                records = []
                for item in data:
                    listing = item.get("listingInfo", {})
                    match_price = item.get("matchPrice", {})
                    bid_ask = item.get("bidAsk", {})

                    # Get bid prices (3 levels) - API returns 'volume' not 'qty'
                    bid_prices = bid_ask.get("bidPrices", [])
                    ask_prices = bid_ask.get("askPrices", [])

                    # Calculate change and changePercent if not provided
                    current_price = match_price.get("matchPrice")
                    ref_price = listing.get("refPrice")
                    change = None
                    change_percent = None
                    if current_price and ref_price and ref_price > 0:
                        change = current_price - ref_price
                        change_percent = round((change / ref_price) * 100, 2)

                    record = {
                        "symbol": listing.get("symbol"),
                        "refPrice": ref_price,
                        "ceiling": listing.get("ceiling"),
                        "floor": listing.get("floor"),
                        # Match price data - updated field names
                        "matchPrice": current_price,
                        "matchQty": match_price.get("matchVol"),
                        "matchValue": match_price.get("accumulatedValue"),
                        "change": change,
                        "changePercent": change_percent,
                        "totalQty": match_price.get("accumulatedVolume"),
                        "totalValue": match_price.get("accumulatedValue"),
                        "highest": match_price.get("highest"),
                        "lowest": match_price.get("lowest"),
                        "openPrice": match_price.get("openPrice"),
                        "averagePrice": match_price.get("avgMatchPrice"),
                        # Bid prices (3 levels) - 'volume' is the correct field name
                        "buyPrice1": bid_prices[0].get("price") if len(bid_prices) > 0 else None,
                        "buyQty1": bid_prices[0].get("volume") if len(bid_prices) > 0 else None,
                        "buyPrice2": bid_prices[1].get("price") if len(bid_prices) > 1 else None,
                        "buyQty2": bid_prices[1].get("volume") if len(bid_prices) > 1 else None,
                        "buyPrice3": bid_prices[2].get("price") if len(bid_prices) > 2 else None,
                        "buyQty3": bid_prices[2].get("volume") if len(bid_prices) > 2 else None,
                        # Ask/Sell prices (3 levels)
                        "sellPrice1": ask_prices[0].get("price") if len(ask_prices) > 0 else None,
                        "sellQty1": ask_prices[0].get("volume") if len(ask_prices) > 0 else None,
                        "sellPrice2": ask_prices[1].get("price") if len(ask_prices) > 1 else None,
                        "sellQty2": ask_prices[1].get("volume") if len(ask_prices) > 1 else None,
                        "sellPrice3": ask_prices[2].get("price") if len(ask_prices) > 2 else None,
                        "sellQty3": ask_prices[2].get("volume") if len(ask_prices) > 2 else None,
                        "exchange": listing.get("board"),
                        "tradingStatus": listing.get("tradingStatus"),
                    }
                    records.append(record)

                logger.info(f"Fetched price board for {len(records)} symbols in group {group}")
                return records

        except Exception as e:
            logger.error(f"Error fetching price board for group {group}: {e}")
            return []
