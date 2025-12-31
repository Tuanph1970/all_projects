"""
Vietnam Stock Service Module
A comprehensive service class for accessing Vietnam stock market data using vnstock library.
"""

import pandas as pd
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Enum for available data sources"""
    VCI = "VCI"
    TCBS = "TCBS"
    MSN = "MSN"
    VND = "VND"
    CAFEF = "CAFEF"
    VIETSTOCK = "VIETSTOCK"


class Exchange(Enum):
    """Enum for Vietnam stock exchanges"""
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"
    ALL = "HOSE,HNX,UPCOM"


class Period(Enum):
    """Enum for time periods"""
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"


class Interval(Enum):
    """Enum for data intervals"""
    ONE_DAY = "1D"
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    ONE_HOUR = "1H"
    FIFTEEN_MIN = "15m"
    FIVE_MIN = "5m"


@dataclass
class StockConfig:
    """Configuration class for stock service"""
    symbol: str
    source: str = DataSource.VCI.value  # Changed default to VCI (more stable)
    exchange: str = Exchange.HOSE.value


class StockService:
    """
    Main service class for accessing Vietnam stock market data.

    This class provides comprehensive access to:
    - Stock quotes and historical data
    - Company information and profiles
    - Financial statements and ratios
    - Market indices and screening
    - Trading statistics
    - Foreign exchange rates
    - Commodities and bonds
    """

    def __init__(self, symbol: Optional[str] = None, source: str = DataSource.VCI.value):
        """
        Initialize StockService

        Args:
            symbol: Stock ticker symbol (e.g., 'VIC', 'VNM', 'TCB')
            source: Data source to use (VCI, TCBS, MSN, etc.) - VCI is default (more stable)
        """
        try:
            from vnstock import Vnstock, Listing, Screener
            from vnstock.explorer.vci.company import Company as VCICompany
            from vnstock.explorer.vci.financial import Finance as VCIFinance

            self.symbol = symbol
            self.source = source

            # Initialize main Vnstock instance
            if symbol:
                try:
                    self.stock = Vnstock().stock(symbol=symbol, source=source)
                except Exception as e:
                    logger.warning(f"Failed to init stock with {source}: {e}, trying VCI")
                    self.stock = Vnstock().stock(symbol=symbol, source='VCI')
            else:
                self.stock = None

            # Initialize core modules
            self.listing = Listing()

            # Initialize screener with error handling (TCBS screener may be unavailable)
            try:
                self.screener = Screener()
            except Exception as e:
                logger.warning(f"Screener initialization failed: {e}")
                self.screener = None

            # Initialize symbol-specific services only if symbol is provided
            if symbol:
                try:
                    # Use VCI as primary source for company and finance data
                    self.company = VCICompany(symbol=symbol)
                    self.finance = VCIFinance(symbol=symbol)
                except Exception as e:
                    logger.warning(f"VCI Company/Finance init failed: {e}")
                    self.company = None
                    self.finance = None

                # Quote and Trading are initialized via the stock object
                self.quote = self.stock.quote if self.stock else None
                self.trading = self.stock.trading if self.stock else None
            else:
                self.quote = None
                self.company = None
                self.finance = None
                self.trading = None

            # Initialize vnstock instance for general use
            self.vnstock = Vnstock()

            logger.info(f"StockService initialized for {symbol or 'general use'} with source {source}")

        except ImportError as e:
            logger.error("Failed to import vnstock. Please install it using: pip install vnstock")
            raise ImportError("vnstock library not installed") from e

    # ============== LISTING METHODS ==============

    def _fetch_stocks_via_screener(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """
        Internal method to fetch stocks using Screener API.

        Args:
            exchange: Exchange name (HOSE, HNX, UPCOM) or None for all

        Returns:
            DataFrame with stock data from screener
        """
        if exchange and exchange.upper() in ['HOSE', 'HNX', 'UPCOM']:
            params = {"exchangeName": exchange.upper()}
            return self.screener.stock(params=params, limit=500)
        else:
            all_results = []
            for ex in ['HOSE', 'HNX', 'UPCOM']:
                try:
                    params = {"exchangeName": ex}
                    exchange_result = self.screener.stock(params=params, limit=500)
                    if not exchange_result.empty:
                        all_results.append(exchange_result)
                except Exception as ex_error:
                    logger.warning(f"Error fetching from exchange {ex} via screener: {ex_error}")
                    continue

            if all_results:
                return pd.concat(all_results, ignore_index=True)
            return pd.DataFrame()

    def _fetch_stocks_via_listing(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """
        Internal method to fetch stocks using Listing API (fallback).

        Args:
            exchange: Exchange name (HOSE, HNX, UPCOM) or None for all

        Returns:
            DataFrame with stock data from listing
        """
        try:
            if exchange and exchange.upper() in ['HOSE', 'HNX', 'UPCOM']:
                result = self.listing.symbols_by_exchange()
                # Filter by exchange if specified
                if not result.empty and 'exchange' in result.columns:
                    result = result[result['exchange'].str.upper() == exchange.upper()]
                return result
            else:
                return self.listing.all_symbols()
        except Exception as e:
            logger.error(f"Error fetching stocks via listing: {e}")
            return pd.DataFrame()

    def get_all_stocks(self, exchange: Optional[str] = None, include_price_data: bool = True) -> pd.DataFrame:
        """
        Get list of all stocks in the market

        Args:
            exchange: Exchange name (HOSE, HNX, UPCOM) or None for all
            include_price_data: If True, fetch price and volume data using screener

        Returns:
            DataFrame with stock listings including price data
        """
        try:
            result = pd.DataFrame()

            # If include_price_data is True, try screener first, then fallback to listing
            if include_price_data:
                try:
                    # Try screener first for comprehensive data
                    result = self._fetch_stocks_via_screener(exchange)
                except Exception as screener_error:
                    logger.warning(f"Screener API failed, falling back to Listing: {screener_error}")
                    result = pd.DataFrame()

                # If screener failed or returned empty, use listing as fallback
                if result.empty:
                    logger.info("Using Listing API as fallback for stock data")
                    result = self._fetch_stocks_via_listing(exchange)

                # Rename columns to standardize
                if not result.empty:
                    # Map screener columns to standard names
                    column_mapping = {
                        'ticker': 'symbol',
                        'price_near_realtime': 'price',
                        'total_trading_value': 'volume',
                        'prev_1d_growth_pct': 'change_percent',
                        'organ_short_name': 'name',
                        'exchange_name': 'exchange'
                    }

                    # Rename columns if they exist
                    for old_col, new_col in column_mapping.items():
                        if old_col in result.columns and new_col not in result.columns:
                            result.rename(columns={old_col: new_col}, inplace=True)

                return result
            else:
                # Original behavior: just get basic listing
                if exchange:
                    return self.listing.symbols_by_exchange(exchange=exchange)
                return self.listing.all_symbols()
        except Exception as e:
            logger.error(f"Error fetching stock listings: {e}")
            return pd.DataFrame()

    def get_industries(self) -> pd.DataFrame:
        """Get list of all industries using ICB classification"""
        try:
            # Use industries_icb() to get ICB industry hierarchy
            industries_df = self.listing.industries_icb()

            if industries_df.empty:
                logger.warning("No industries data returned from industries_icb()")
                return pd.DataFrame()

            return industries_df
        except Exception as e:
            logger.error(f"Error fetching industries: {e}")
            return pd.DataFrame()

    def get_stocks_by_industry(self, industry_code: str) -> pd.DataFrame:
        """
        Get stocks by industry code using ICB classification

        Args:
            industry_code: ICB industry code to filter by
        """
        try:
            # Use symbols_by_industries() to get stocks grouped by industry
            stocks_df = self.listing.symbols_by_industries()

            if stocks_df.empty:
                logger.warning(f"No stocks data returned for industry {industry_code}")
                return pd.DataFrame()

            # Filter by industry code - check all ICB level columns
            # ICB codes are stored in icb_code1 (level 1), icb_code2 (level 2), icb_code3 (level 3), icb_code4 (level 4)
            for col in ['icb_code3', 'icb_code2', 'icb_code1', 'icb_code4', 'icb_code', 'industry_code']:
                if col in stocks_df.columns:
                    filtered = stocks_df[stocks_df[col] == industry_code]
                    if not filtered.empty:
                        logger.info(f"Filtered {len(filtered)} stocks by {col} = {industry_code}")
                        return filtered

            # Try matching by industry name if code filtering didn't work
            if 'industryEn' in stocks_df.columns:
                filtered = stocks_df[stocks_df['industryEn'] == industry_code]
                if not filtered.empty:
                    return filtered

            # If no matches found, log warning and return empty DataFrame
            logger.warning(f"No stocks found for industry code {industry_code}. Available columns: {stocks_df.columns.tolist()}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching stocks by industry: {e}")
            return pd.DataFrame()

    # ============== QUOTE METHODS ==============

    def get_price_history(
            self,
            symbol: Optional[str] = None,
            start: str = None,
            end: str = None,
            interval: str = Interval.ONE_DAY.value,
            source: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get historical price data for a stock

        Args:
            symbol: Stock symbol (uses instance symbol if None)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval (1D, 1W, 1M, 1H, 15m, 5m)
            source: Data source to use

        Returns:
            DataFrame with historical price data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if not start:
                start = '2020-01-01'
            if not end:
                end = datetime.now().strftime('%Y-%m-%d')

            if self.stock and symbol == self.symbol:
                return self.stock.quote.history(start=start, end=end, interval=interval)
            else:
                # Create temporary stock instance for different symbol
                temp_stock = self.vnstock.stock(symbol=symbol, source=source or self.source)
                return temp_stock.quote.history(start=start, end=end, interval=interval)

        except Exception as e:
            logger.error(f"Error fetching price history for {symbol}: {e}")
            return pd.DataFrame()

    def get_intraday_data(
            self,
            symbol: Optional[str] = None,
            page_size: int = 5000
    ) -> pd.DataFrame:
        """
        Get intraday trading data

        Args:
            symbol: Stock symbol
            page_size: Number of records to fetch

        Returns:
            DataFrame with intraday data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.quote.intraday(page_size=page_size)
            else:
                return self.quote.intraday(symbol=symbol, page_size=page_size)

        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return pd.DataFrame()

    def get_price_board(self, symbols: List[str]) -> pd.DataFrame:
        """
        Get current price board for multiple stocks

        Args:
            symbols: List of stock symbols

        Returns:
            DataFrame with current prices
        """
        try:
            return self.quote.price_board(symbols=symbols)
        except Exception as e:
            logger.error(f"Error fetching price board: {e}")
            return pd.DataFrame()

    # ============== COMPANY METHODS ==============

    def get_company_overview(self, symbol: Optional[str] = None) -> Dict:
        """
        Get company overview information

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with company overview
        """
        try:
            from vnstock.explorer.vci.company import Company as VCICompany

            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            # Always create a new Company instance for the requested symbol
            # Use VCI as primary source (more stable than TCBS)
            company = VCICompany(symbol=symbol)
            result = company.overview()

            # Convert DataFrame to dictionary if needed
            if hasattr(result, 'to_dict'):
                # If it's a DataFrame, convert to dictionary
                if not result.empty:
                    # Get the first row as a dictionary
                    return result.iloc[0].to_dict()
                else:
                    return {}
            elif isinstance(result, dict):
                return result
            else:
                logger.warning(f"Unexpected overview result type: {type(result)}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching company overview for {symbol}: {e}")
            return {}

    def get_company_profile(self, symbol: Optional[str] = None) -> Dict:
        """
        Get detailed company profile

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with company profile
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            # Try to get profile from overview or return empty dict if not available
            # Since profile method doesn't exist, use overview as fallback
            if self.stock and symbol == self.symbol:
                try:
                    # Try to get profile if it exists
                    if hasattr(self.stock.company, 'profile'):
                        return self.stock.company.profile()
                    else:
                        # Fallback to overview or empty dict
                        overview = self.stock.company.overview()
                        # Extract profile-like information from overview
                        return {
                            'website': overview.get('website', ''),
                            'employees': overview.get('employees', 0),
                            'description': overview.get('companyProfile', ''),
                            'founded': overview.get('foundedYear', ''),
                            'headquarters': overview.get('headquarters', '')
                        }
                except AttributeError:
                    return {}
            else:
                # For different symbol, create a temporary Company instance
                from vnstock.explorer.vci.company import Company as VCICompany
                temp_company = VCICompany(symbol=symbol)
                try:
                    if hasattr(temp_company, 'profile'):
                        return temp_company.profile()
                    else:
                        overview = temp_company.overview()
                        return {
                            'website': overview.get('website', ''),
                            'employees': overview.get('employees', 0),
                            'description': overview.get('companyProfile', ''),
                            'founded': overview.get('foundedYear', ''),
                            'headquarters': overview.get('headquarters', '')
                        }
                except AttributeError:
                    return {}

        except Exception as e:
            logger.error(f"Error fetching company profile: {e}")
            return {}

    def get_shareholders(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get major shareholders information

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with shareholders data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.company.shareholders()
            else:
                return self.company.shareholders(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching shareholders: {e}")
            return pd.DataFrame()

    def get_insider_trading(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get insider trading information

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with insider trading data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                # Check if insider_trading method exists
                if hasattr(self.stock.company, 'insider_trading'):
                    return self.stock.company.insider_trading()
                elif hasattr(self.stock.company, 'insiders'):
                    return self.stock.company.insiders()
                else:
                    logger.warning(f"Insider trading data not available for {symbol}")
                    return pd.DataFrame()
            else:
                # For different symbol, create a temporary Company instance
                from vnstock.explorer.vci.company import Company as VCICompany
                temp_company = VCICompany(symbol=symbol)
                if hasattr(temp_company, 'insider_trading'):
                    return temp_company.insider_trading()
                elif hasattr(temp_company, 'insiders'):
                    return temp_company.insiders()
                else:
                    logger.warning(f"Insider trading data not available for {symbol}")
                    return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching insider trading: {e}")
            return pd.DataFrame()

    def get_subsidiaries(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get company subsidiaries information

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with subsidiaries data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.company.subsidiaries()
            else:
                return self.company.subsidiaries(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching subsidiaries: {e}")
            return pd.DataFrame()

    def get_officers(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get company officers and management

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with officers data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.company.officers()
            else:
                return self.company.officers(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching officers: {e}")
            return pd.DataFrame()

    def get_events(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get company events and announcements

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with events data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.company.events()
            else:
                return self.company.events(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return pd.DataFrame()

    def get_news(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get company news

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with news data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.company.news()
            else:
                return self.company.news(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return pd.DataFrame()

    def get_dividends(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get dividend history

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with dividend data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            # Try different approaches to get dividend data
            if self.stock and symbol == self.symbol:
                # Check if dividends method exists
                if hasattr(self.stock.company, 'dividends'):
                    return self.stock.company.dividends()
                elif hasattr(self.stock.company, 'dividend_history'):
                    return self.stock.company.dividend_history()
                elif hasattr(self.stock, 'dividends'):
                    return self.stock.dividends()
                else:
                    logger.warning(f"Dividend data not available for {symbol}")
                    return pd.DataFrame()
            else:
                # For different symbol, try multiple approaches
                from vnstock.explorer.vci.company import Company as VCICompany
                temp_company = VCICompany(symbol=symbol)
                if hasattr(temp_company, 'dividends'):
                    return temp_company.dividends()
                elif hasattr(temp_company, 'dividend_history'):
                    return temp_company.dividend_history()
                else:
                    # Try using Vnstock directly with VCI source
                    temp_stock = self.vnstock.stock(symbol=symbol, source='VCI')
                    if hasattr(temp_stock, 'dividends'):
                        return temp_stock.dividends()
                    else:
                        logger.warning(f"Dividend data not available for {symbol}")
                        return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching dividends: {e}")
            return pd.DataFrame()

    # ============== FINANCIAL METHODS ==============

    def get_balance_sheet(
            self,
            symbol: Optional[str] = None,
            period: str = Period.YEAR.value,
            lang: str = 'en',
            dropna: bool = True
    ) -> pd.DataFrame:
        """
        Get balance sheet data

        Args:
            symbol: Stock symbol
            period: 'year' or 'quarter'
            lang: Language ('en' or 'vi')
            dropna: Drop NaN values

        Returns:
            DataFrame with balance sheet data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.finance.balance_sheet(period=period, lang=lang, dropna=dropna)
            else:
                return self.finance.balance_sheet(symbol=symbol, period=period, lang=lang, dropna=dropna)

        except Exception as e:
            logger.error(f"Error fetching balance sheet: {e}")
            return pd.DataFrame()

    def get_income_statement(
            self,
            symbol: Optional[str] = None,
            period: str = Period.YEAR.value,
            lang: str = 'en',
            dropna: bool = True
    ) -> pd.DataFrame:
        """
        Get income statement data

        Args:
            symbol: Stock symbol
            period: 'year' or 'quarter'
            lang: Language ('en' or 'vi')
            dropna: Drop NaN values

        Returns:
            DataFrame with income statement data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.finance.income_statement(period=period, lang=lang, dropna=dropna)
            else:
                return self.finance.income_statement(symbol=symbol, period=period, lang=lang, dropna=dropna)

        except Exception as e:
            logger.error(f"Error fetching income statement: {e}")
            return pd.DataFrame()

    def get_cash_flow(
            self,
            symbol: Optional[str] = None,
            period: str = Period.YEAR.value,
            lang: str = 'en',
            dropna: bool = True
    ) -> pd.DataFrame:
        """
        Get cash flow statement data

        Args:
            symbol: Stock symbol
            period: 'year' or 'quarter'
            lang: Language ('en' or 'vi')
            dropna: Drop NaN values

        Returns:
            DataFrame with cash flow data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.finance.cash_flow(period=period, lang=lang, dropna=dropna)
            else:
                return self.finance.cash_flow(symbol=symbol, period=period, lang=lang, dropna=dropna)

        except Exception as e:
            logger.error(f"Error fetching cash flow: {e}")
            return pd.DataFrame()

    def get_financial_ratios(
            self,
            symbol: Optional[str] = None,
            period: str = Period.YEAR.value,
            lang: str = 'en',
            dropna: bool = True
    ) -> pd.DataFrame:
        """
        Get financial ratios

        Args:
            symbol: Stock symbol
            period: 'year' or 'quarter'
            lang: Language ('en' or 'vi')
            dropna: Drop NaN values

        Returns:
            DataFrame with financial ratios
        """
        try:
            from vnstock.explorer.vci.financial import Finance as VCIFinance

            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            # Always create a new Finance instance for the requested symbol
            # Use VCI as primary source (more stable than TCBS)
            finance = VCIFinance(symbol=symbol)
            return finance.ratio(period=period, lang=lang, dropna=dropna)

        except Exception as e:
            logger.error(f"Error fetching financial ratios for {symbol}: {e}")
            return pd.DataFrame()

    def compare_financial_ratios(
            self,
            symbol_list: List[str],
            industry_comparison: bool = True,
            frequency: str = Period.YEAR.value,
            start_year: int = 2020
    ) -> pd.DataFrame:
        """
        Compare financial ratios between multiple stocks

        Args:
            symbol_list: List of stock symbols to compare
            industry_comparison: Include industry comparison
            frequency: 'year' or 'quarter'
            start_year: Starting year for comparison

        Returns:
            DataFrame with comparison data
        """
        try:
            return self.finance.ratio_compare(
                symbol_ls=symbol_list,
                industry_comparison=industry_comparison,
                frequency=frequency,
                start_year=start_year
            )
        except Exception as e:
            logger.error(f"Error comparing financial ratios: {e}")
            return pd.DataFrame()

    # ============== TRADING METHODS ==============

    def get_price_depth(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get current price depth (order book)

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with price depth data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.trading.price_depth()
            else:
                return self.trading.price_depth(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching price depth: {e}")
            return pd.DataFrame()

    def get_foreign_trading(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get foreign investor trading data

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with foreign trading data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.trading.foreign()
            else:
                return self.trading.foreign(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching foreign trading: {e}")
            return pd.DataFrame()

    def get_proprietary_trading(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get proprietary trading data

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with proprietary trading data
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            if self.stock and symbol == self.symbol:
                return self.stock.trading.proprietary()
            else:
                return self.trading.proprietary(symbol=symbol)

        except Exception as e:
            logger.error(f"Error fetching proprietary trading: {e}")
            return pd.DataFrame()

    # ============== SCREENING METHODS ==============

    def screen_stocks(
            self,
            exchange: str = Exchange.ALL.value,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            min_volume: Optional[int] = None,
            min_market_cap: Optional[float] = None,
            limit: int = 100
    ) -> pd.DataFrame:
        """
        Screen stocks based on criteria

        Args:
            exchange: Exchange to screen (HOSE, HNX, UPCOM, or ALL)
            min_price: Minimum price filter (in thousands VND)
            max_price: Maximum price filter (in thousands VND)
            min_volume: Minimum volume filter
            min_market_cap: Minimum market cap filter (in billions VND)
            limit: Maximum number of results

        Returns:
            DataFrame with screened stocks
        """
        try:
            all_results = []
            screener_failed = False

            # Handle exchange parameter
            if exchange == 'ALL' or exchange == 'HOSE,HNX,UPCOM':
                exchanges = ['HOSE', 'HNX', 'UPCOM']
            else:
                exchanges = [exchange]

            # Try fetching data from screener first
            for ex in exchanges:
                try:
                    params = {"exchangeName": ex}
                    fetch_limit = limit * 3 if (min_price or max_price or min_volume or min_market_cap) else limit
                    fetch_limit = min(fetch_limit, 500)

                    result = self.screener.stock(params=params, limit=fetch_limit)

                    if not result.empty:
                        all_results.append(result)

                except Exception as ex_error:
                    logger.warning(f"Screener failed for exchange {ex}: {ex_error}")
                    screener_failed = True
                    continue

            # Fallback to Listing API if screener failed for all exchanges
            if not all_results and screener_failed:
                logger.info("Screener API unavailable, falling back to Listing API")
                try:
                    listing_result = self._fetch_stocks_via_listing(exchange if exchange != 'ALL' else None)
                    if not listing_result.empty:
                        all_results.append(listing_result)
                except Exception as listing_error:
                    logger.error(f"Listing fallback also failed: {listing_error}")

            # Combine all results
            if all_results:
                combined_df = pd.concat(all_results, ignore_index=True)

                # Apply filters manually on the fetched data
                # Convert filter values to proper numeric types to avoid dtype comparison errors
                if min_price is not None and 'price_near_realtime' in combined_df.columns:
                    try:
                        min_price_float = float(min_price)
                        combined_df = combined_df[combined_df['price_near_realtime'] >= min_price_float]
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid min_price value: {min_price}")

                if max_price is not None and 'price_near_realtime' in combined_df.columns:
                    try:
                        max_price_float = float(max_price)
                        combined_df = combined_df[combined_df['price_near_realtime'] <= max_price_float]
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid max_price value: {max_price}")

                if min_volume is not None and 'total_trading_value' in combined_df.columns:
                    try:
                        min_volume_float = float(min_volume)
                        combined_df = combined_df[combined_df['total_trading_value'] >= min_volume_float]
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid min_volume value: {min_volume}")

                if min_market_cap is not None and 'market_cap' in combined_df.columns:
                    try:
                        min_market_cap_float = float(min_market_cap)
                        combined_df = combined_df[combined_df['market_cap'] >= min_market_cap_float]
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid min_market_cap value: {min_market_cap}")

                # Sort by market cap (descending) and limit results
                if 'market_cap' in combined_df.columns:
                    combined_df = combined_df.sort_values('market_cap', ascending=False)

                return combined_df.head(limit)
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error screening stocks: {e}")
            return pd.DataFrame()

    # ============== MARKET INDICES METHODS ==============

    def get_market_index(
            self,
            index: str = "VNINDEX",
            start: str = None,
            end: str = None
    ) -> pd.DataFrame:
        """
        Get market index data

        Args:
            index: Index name (VNINDEX, VN30, HNX-INDEX, etc.)
            start: Start date
            end: End date

        Returns:
            DataFrame with index data
        """
        try:
            if not start:
                start = '2020-01-01'
            if not end:
                end = datetime.now().strftime('%Y-%m-%d')

            index_stock = self.vnstock.stock(symbol=index, source='TCBS')
            return index_stock.quote.history(start=start, end=end)

        except Exception as e:
            logger.error(f"Error fetching market index: {e}")
            return pd.DataFrame()

    # ============== FOREX METHODS ==============

    def get_forex_rate(
            self,
            currency_pair: str = "USDVND",
            start: str = None,
            end: str = None,
            interval: str = Interval.ONE_DAY.value
    ) -> pd.DataFrame:
        """
        Get foreign exchange rate data

        Args:
            currency_pair: Currency pair (e.g., USDVND, EURVND)
            start: Start date
            end: End date
            interval: Data interval

        Returns:
            DataFrame with forex data
        """
        try:
            if not start:
                start = '2020-01-01'
            if not end:
                end = datetime.now().strftime('%Y-%m-%d')

            fx = self.vnstock.fx(symbol=currency_pair, source='MSN')
            return fx.quote.history(start=start, end=end, interval=interval)

        except Exception as e:
            logger.error(f"Error fetching forex rate: {e}")
            return pd.DataFrame()

    # ============== COMMODITIES METHODS ==============

    def get_gold_price(self) -> pd.DataFrame:
        """
        Get SJC gold price data

        Returns:
            DataFrame with gold price data
        """
        try:
            from vnstock.explorer.misc import sjc_gold_price
            return sjc_gold_price()
        except Exception as e:
            logger.error(f"Error fetching gold price: {e}")
            return pd.DataFrame()

    def get_vcb_exchange_rate(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        Get Vietcombank exchange rates

        Args:
            date: Date to get rates for (YYYY-MM-DD)

        Returns:
            DataFrame with exchange rates
        """
        try:
            from vnstock.explorer.misc import vcb_exchange_rate
            if date:
                return vcb_exchange_rate(date=date)
            return vcb_exchange_rate()
        except Exception as e:
            logger.error(f"Error fetching VCB exchange rate: {e}")
            return pd.DataFrame()

    # ============== FUND METHODS ==============

    def get_fund_listing(self) -> pd.DataFrame:
        """
        Get list of investment funds

        Returns:
            DataFrame with fund listings
        """
        try:
            from vnstock.explorer.fmarket.fund import Fund
            fund = Fund()
            return fund.listing()
        except Exception as e:
            logger.error(f"Error fetching fund listing: {e}")
            return pd.DataFrame()

    def get_etf_data(self, symbol: str) -> Dict:
        """
        Get ETF information

        Args:
            symbol: ETF symbol

        Returns:
            Dictionary with ETF data
        """
        try:
            from vnstock.explorer.fmarket.fund import Fund
            fund = Fund()
            return fund.details(symbol=symbol)
        except Exception as e:
            logger.error(f"Error fetching ETF data: {e}")
            return {}

    # ============== UTILITY METHODS ==============

    def export_to_excel(self, data: pd.DataFrame, filename: str):
        """
        Export DataFrame to Excel file

        Args:
            data: DataFrame to export
            filename: Output filename
        """
        try:
            data.to_excel(filename, index=False)
            logger.info(f"Data exported to {filename}")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")

    def export_to_csv(self, data: pd.DataFrame, filename: str):
        """
        Export DataFrame to CSV file

        Args:
            data: DataFrame to export
            filename: Output filename
        """
        try:
            data.to_csv(filename, index=False)
            logger.info(f"Data exported to {filename}")
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")

    def analyze_stock(self, symbols: Union[str, List[str]]) -> pd.DataFrame:
        """
        Perform comprehensive analysis on one or more stocks

        Args:
            symbols: Single symbol or list of symbols

        Returns:
            DataFrame with analysis results
        """
        try:
            if isinstance(symbols, str):
                symbols = [symbols]

            analysis_data = []
            for symbol in symbols:
                try:
                    # Get basic data
                    overview = self.get_company_overview(symbol)

                    # Get latest price
                    price_data = self.get_price_history(symbol,
                                                        start=(datetime.now().replace(day=1)).strftime('%Y-%m-%d'))

                    if not price_data.empty:
                        latest_price = price_data['close'].iloc[-1]
                        price_change = ((price_data['close'].iloc[-1] / price_data['close'].iloc[0]) - 1) * 100
                    else:
                        latest_price = 0
                        price_change = 0

                    # Get financial ratios
                    ratios = self.get_financial_ratios(symbol)

                    analysis_data.append({
                        'Symbol': symbol,
                        'Company': overview.get('companyName', ''),
                        'Industry': overview.get('industry', ''),
                        'Price': latest_price,
                        'Change%': round(price_change, 2),
                        'MarketCap': overview.get('marketCap', 0),
                        'P/E': ratios['P/E'].iloc[-1] if not ratios.empty and 'P/E' in ratios else None,
                        'P/B': ratios['P/B'].iloc[-1] if not ratios.empty and 'P/B' in ratios else None,
                        'ROE': ratios['ROE'].iloc[-1] if not ratios.empty and 'ROE' in ratios else None,
                        'ROA': ratios['ROA'].iloc[-1] if not ratios.empty and 'ROA' in ratios else None,
                    })
                except Exception as e:
                    logger.warning(f"Error analyzing {symbol}: {e}")
                    continue

            return pd.DataFrame(analysis_data)

        except Exception as e:
            logger.error(f"Error in stock analysis: {e}")
            return pd.DataFrame()

    def get_technical_indicators(
            self,
            symbol: Optional[str] = None,
            start: str = None,
            end: str = None
    ) -> Dict:
        """
        Calculate basic technical indicators

        Args:
            symbol: Stock symbol
            start: Start date
            end: End date

        Returns:
            Dictionary with technical indicators
        """
        try:
            symbol = symbol or self.symbol
            if not symbol:
                raise ValueError("Symbol must be provided")

            # Get price data
            df = self.get_price_history(symbol, start, end)

            if df.empty:
                return {}

            # Calculate simple moving averages
            df['SMA_20'] = df['close'].rolling(window=20).mean()
            df['SMA_50'] = df['close'].rolling(window=50).mean()
            df['SMA_200'] = df['close'].rolling(window=200).mean()

            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Get latest values
            latest = df.iloc[-1]

            return {
                'current_price': latest['close'],
                'sma_20': latest['SMA_20'],
                'sma_50': latest['SMA_50'],
                'sma_200': latest['SMA_200'],
                'rsi': latest['RSI'],
                'volume': latest['volume'],
                'high_52w': df['high'].tail(252).max() if len(df) > 252 else df['high'].max(),
                'low_52w': df['low'].tail(252).min() if len(df) > 252 else df['low'].min()
            }

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}

    def __str__(self):
        """String representation of the service"""
        return f"StockService(symbol={self.symbol}, source={self.source})"

    def __repr__(self):
        """Representation of the service"""
        return self.__str__()


# Example usage
if __name__ == "__main__":
    # Initialize service for a specific stock
    service = StockService(symbol="VIC", source="VCI")

    # Get historical price data
    price_data = service.get_price_history(start="2024-01-01", end="2024-12-31")
    print("Price History:")
    print(price_data.head())

    # Get company overview
    overview = service.get_company_overview()
    print("\nCompany Overview:")
    print(overview)

    # Get financial statements
    balance_sheet = service.get_balance_sheet(period="year")
    print("\nBalance Sheet:")
    print(balance_sheet.head())

    # Screen stocks
    screened = service.screen_stocks(
        exchange="HOSE",
        min_price=10000,
        max_price=100000,
        limit=10
    )
    print("\nScreened Stocks:")
    print(screened)

    # Analyze multiple stocks
    analysis = service.analyze_stock(["VIC", "VNM", "TCB"])
    print("\nStock Analysis:")
    print(analysis)

    # Get technical indicators
    indicators = service.get_technical_indicators()
    print("\nTechnical Indicators:")
    print(indicators)

    # Export data
    service.export_to_csv(price_data, "vic_price_history.csv")
    service.export_to_excel(balance_sheet, "vic_balance_sheet.xlsx")