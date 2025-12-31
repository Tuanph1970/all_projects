from typing import Dict, List, Optional
import pandas as pd
import json
import os
import logging
from datetime import date
from vnstock import Vnstock
# Use VCI as primary source (more stable), with TCBS as fallback
from vnstock.explorer.vci.company import Company as VCICompany
from vnstock.explorer.vci.financial import Finance
from core.exceptions import ExternalServiceException
from core.decorators import validate_input, cache_result

# Try to import TCBS Company as fallback
try:
    from vnstock.explorer.tcbs.company import Company as TCBSCompany
    TCBS_AVAILABLE = True
except ImportError:
    TCBS_AVAILABLE = False

# Try to import gold price functions
try:
    from vnstock.explorer.misc.gold_price import sjc_gold_price, btmc_goldprice
    GOLD_PRICE_AVAILABLE = True
except ImportError:
    GOLD_PRICE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Set environment variable for vnstock
if "ACCEPT_TC" not in os.environ:
    os.environ["ACCEPT_TC"] = "tôi đồng ý"

DATA_FILE_NAME = "./stock_data/company_list.xlsx"


class StockEntity:
    def __init__(self, symbol: str, source: str):
        self.symbol = symbol
        self.source = source
    
    def dump_json(self, df: pd.DataFrame) -> List[Dict]:
        json_str = df.to_json(orient='records', force_ascii=False, date_format='iso')
        return json.loads(json_str)


class MarketStockEntity(StockEntity):
    def __init__(self, symbol: str, source: str):
        super().__init__(symbol=symbol, source=source)
        self._stock = None
        self._vci_stock = None

    @property
    def stock(self):
        """Lazy initialization of stock with preferred source."""
        if self._stock is None:
            try:
                self._stock = Vnstock().stock(symbol=self.symbol, source=self.source)
            except Exception as e:
                logger.warning(f"Failed to init stock with {self.source}: {e}, trying VCI")
                self._stock = Vnstock().stock(symbol=self.symbol, source='VCI')
        return self._stock

    @property
    def vci_stock(self):
        """VCI stock instance for fallback."""
        if self._vci_stock is None:
            self._vci_stock = Vnstock().stock(symbol=self.symbol, source='VCI')
        return self._vci_stock

    def get_stock_by_group(self, group: str) -> List[str]:
        try:
            if group != 'all':
                df = self.stock.listing.symbols_by_group(group)
            else:
                df = self.stock.listing.all_symbols()['ticker']
            return list(df)
        except Exception as e:
            logger.error(f"Error getting stocks by group {group}: {e}")
            return []

    def get_price_board(self, group: str) -> pd.DataFrame:
        try:
            lst_symbol = self.get_stock_by_group(group)
            return self.stock.trading.price_board(lst_symbol)
        except Exception as e:
            logger.error(f"Error getting price board for group {group}: {e}")
            return pd.DataFrame()

    def get_price_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Get price history with VCI fallback."""
        # Try primary source first
        try:
            result = self.stock.quote.history(symbol=symbol, start=start, end=end)
            if result is not None and not result.empty:
                return result
        except Exception as e:
            logger.warning(f"Primary source failed for price history: {e}")

        # Fallback to VCI
        try:
            result = self.vci_stock.quote.history(symbol=symbol, start=start, end=end)
            if result is not None and not result.empty:
                return result
        except Exception as e:
            logger.error(f"VCI fallback also failed for price history: {e}")

        return pd.DataFrame()
    
    def get_companies_info(self, group: str) -> pd.DataFrame:
        df = pd.read_excel(DATA_FILE_NAME)
        df_group = df[df[group] == True]
        return df_group
    
    def get_all_companies(self) -> pd.DataFrame:
        df = pd.read_excel(DATA_FILE_NAME)
        df = df.rename(columns={
            "Market Capital": "MarketCap",
            "Outstanding Share": "OutstandingShare",
            "P/B": "PB",
            "P/S": "PS",
            "P/E": "PE",
            "P/Cash Flow": "PC",
            "Gross Profit Margin": "Gross_Profit",
            "Net Profit Margin": "Net_Profit",
            "Dividend yield": "Dividend_Yield",
            "Current Ratio": "Current_Ratio"
        })
        return df
    
    def get_companies_by_industry(self, industry_id: int) -> pd.DataFrame:
        df = self.get_all_companies()
        df_industry = df[df['industry_id'] == industry_id]
        return df_industry
    
    def get_top_gainers(self) -> pd.DataFrame:
        df = self.get_all_companies()
        df['variation'] = df['close'] - df['open']
        df = df.sort_values('variation', ascending=False)
        return df.head(10)
    
    def get_top_losers(self) -> pd.DataFrame:
        df = self.get_all_companies()
        df['variation'] = df['close'] - df['open']
        df = df.sort_values('variation')
        return df.head(10)
    
    def get_top_actives(self) -> pd.DataFrame:
        df = self.get_all_companies()
        df = df.sort_values('volume', ascending=False)
        return df.head(10)
    
    def get_main_industries(self) -> pd.DataFrame:
        df = self.get_all_companies()
        df = df[['industry_id_v2', 'industry']]
        df = df.drop_duplicates(subset=['industry_id_v2'])
        return df


class CompanyStockEntity(StockEntity):
    """Entity for company data with VCI/TCBS fallback and column standardization."""

    # Column mapping from VCI format to standard/frontend format
    OVERVIEW_COLUMN_MAP = {
        'symbol': 'ticker',
        'issue_share': 'issueShare',
        'company_profile': 'companyProfile',
        # VCI uses icb_name2, icb_name3, icb_name4 (no underscore before number)
        'icb_name2': 'industry',
        'icb_name3': 'industryL2',
        'icb_name4': 'industryL3',
        'charter_capital': 'charterCapital',
        'no_employees': 'noEmployees',
        'no_shareholders': 'noShareholders',
        'foreign_percent': 'foreignPercent',
        'outstanding_share': 'outstandingShare',
        'free_float_rate': 'freeFloatRate',
        'history': 'history',
    }

    NEWS_COLUMN_MAP = {
        'ticker': 'symbol',
        'news_title': 'title',
        'news_short_content': 'description',
        'news_full_content': 'content',
        'news_source_link': 'source',
        'news_image_url': 'imageUrl',
        'public_date': 'publishDate',
        'created_at': 'createdAt',
        # Price-related fields from VCI API
        'close_price': 'price',
        'ref_price': 'referencePrice',
        'price_change_pct': 'changePercent',
        'floor': 'floorPrice',
        'ceiling': 'ceilingPrice',
    }

    EVENTS_COLUMN_MAP = {
        'ticker': 'symbol',
        'event_title': 'title',
        'event_list_name': 'eventType',
        'en__event_list_name': 'eventTypeEn',
        'public_date': 'publishDate',
        'issue_date': 'issueDate',
        'record_date': 'recordDate',
        'exright_date': 'exrightDate',
        'source_url': 'source',
        'ratio': 'ratio',
        'value': 'value',
    }

    def __init__(self, symbol: str, source: str):
        super().__init__(symbol=symbol, source=source)
        self.symbol = symbol
        self.source = source
        self._vci_company = None
        self._tcbs_company = None

    @property
    def vci_company(self):
        """Lazy initialization of VCI Company"""
        if self._vci_company is None:
            self._vci_company = VCICompany(symbol=self.symbol)
        return self._vci_company

    @property
    def tcbs_company(self):
        """Lazy initialization of TCBS Company (fallback)"""
        if self._tcbs_company is None and TCBS_AVAILABLE:
            self._tcbs_company = TCBSCompany(symbol=self.symbol)
        return self._tcbs_company

    def _convert_timestamp_to_iso(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Convert millisecond timestamp column to ISO date format."""
        if column not in df.columns:
            return df

        try:
            # VCI returns timestamps in milliseconds (e.g., 1765819507000)
            # Convert to datetime and then to ISO string
            df[column] = pd.to_datetime(df[column], unit='ms', errors='coerce')
            df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"Failed to convert timestamp column {column}: {e}")

        return df

    def _standardize_columns(self, df: pd.DataFrame, column_map: Dict[str, str], convert_dates: bool = False) -> pd.DataFrame:
        """Standardize column names for frontend compatibility."""
        if df is None or df.empty:
            return df

        # Convert timestamp columns to ISO date format if needed
        if convert_dates:
            for col in ['public_date', 'created_at', 'updated_at']:
                if col in df.columns:
                    df = self._convert_timestamp_to_iso(df, col)

        # Rename columns that exist in the DataFrame
        rename_map = {old: new for old, new in column_map.items() if old in df.columns}
        if rename_map:
            df = df.rename(columns=rename_map)

        return df

    def _call_with_fallback(self, method_name: str, vci_fallback_method: str = None, *args, **kwargs) -> pd.DataFrame:
        """
        Try VCI first, fallback to TCBS if VCI fails.

        Args:
            method_name: The method name to call (e.g., 'overview', 'profile')
            vci_fallback_method: Alternative method name to try on VCI if primary doesn't exist

        Returns:
            DataFrame with company data
        """
        # Try VCI first (primary source)
        try:
            vci_method = getattr(self.vci_company, method_name, None)
            if vci_method:
                result = vci_method(*args, **kwargs)
                if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                    return result
            # Try VCI fallback method if primary doesn't exist
            elif vci_fallback_method:
                vci_method = getattr(self.vci_company, vci_fallback_method, None)
                if vci_method:
                    result = vci_method(*args, **kwargs)
                    if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                        logger.info(f"VCI: Using {vci_fallback_method} as fallback for {method_name}")
                        return result
        except Exception as vci_error:
            logger.warning(f"VCI {method_name} failed for {self.symbol}: {vci_error}")

        # Fallback to TCBS (may not work due to API changes)
        if TCBS_AVAILABLE and self.tcbs_company:
            try:
                tcbs_method = getattr(self.tcbs_company, method_name, None)
                if tcbs_method:
                    result = tcbs_method(*args, **kwargs)
                    if result is not None:
                        return result
            except Exception as tcbs_error:
                logger.debug(f"TCBS {method_name} unavailable for {self.symbol}: {tcbs_error}")

        # Return empty DataFrame if both fail (not an error for unsupported methods)
        logger.info(f"Method {method_name} not available for {self.symbol}")
        return pd.DataFrame()

    def overview_company(self) -> pd.DataFrame:
        df = self._call_with_fallback('overview')
        return self._standardize_columns(df, self.OVERVIEW_COLUMN_MAP)

    def get_company_profile(self) -> pd.DataFrame:
        """Get company profile - uses overview() as VCI doesn't have profile method"""
        df = self._call_with_fallback('profile', vci_fallback_method='overview')
        return self._standardize_columns(df, self.OVERVIEW_COLUMN_MAP)

    def get_company_events(self) -> pd.DataFrame:
        df = self._call_with_fallback('events')
        return self._standardize_columns(df, self.EVENTS_COLUMN_MAP)

    def get_company_news(self) -> pd.DataFrame:
        df = self._call_with_fallback('news')
        # News has timestamp fields that need conversion to ISO date format
        df = self._standardize_columns(df, self.NEWS_COLUMN_MAP, convert_dates=True)

        # Calculate absolute price change if price columns exist
        if 'price' in df.columns and 'referencePrice' in df.columns:
            try:
                df['change'] = df['price'] - df['referencePrice']
            except Exception as e:
                logger.warning(f"Failed to calculate price change: {e}")

        return df

    def get_company_dividends(self) -> pd.DataFrame:
        """
        Get company dividends.
        Note: VCI doesn't have dividends method, TCBS API may be unavailable.
        Returns empty DataFrame if data is not available.
        """
        # Try to get dividend data - this may not be available in current API
        result = self._call_with_fallback('dividends')
        if result.empty:
            logger.info(f"Dividend data not available for {self.symbol} - API limitation")
        return result

    def get_company_shareholders(self) -> pd.DataFrame:
        """Get company shareholders"""
        return self._call_with_fallback('shareholders')

    def get_company_officers(self, filter_by: str = 'working') -> pd.DataFrame:
        """Get company officers/management"""
        return self._call_with_fallback('officers', filter_by=filter_by)

    def get_company_subsidiaries(self) -> pd.DataFrame:
        """Get company subsidiaries"""
        return self._call_with_fallback('subsidiaries')

    def get_trading_stats(self) -> pd.DataFrame:
        """Get trading statistics"""
        return self._call_with_fallback('trading_stats')

    def get_ratio_summary(self) -> pd.DataFrame:
        """Get financial ratio summary"""
        return self._call_with_fallback('ratio_summary')


class StockFinanceEntity(StockEntity):
    def __init__(self, symbol: str, source: str, period: str, language: str):
        super().__init__(symbol=symbol, source=source)
        self.period = period
        self.lang = language
        self._report = None

    @property
    def report(self):
        """Lazy initialization of Finance report."""
        if self._report is None:
            try:
                self._report = Finance(symbol=self.symbol, period=self.period)
            except Exception as e:
                logger.error(f"Failed to initialize Finance for {self.symbol}: {e}")
                raise
        return self._report

    def _safe_call(self, method_name: str, *args, **kwargs) -> pd.DataFrame:
        """Safely call a report method with error handling."""
        try:
            method = getattr(self.report, method_name, None)
            if method:
                result = method(*args, **kwargs)
                return result if result is not None else pd.DataFrame()
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error calling {method_name} for {self.symbol}: {e}")
            return pd.DataFrame()

    def get_company_balance_sheet(self) -> pd.DataFrame:
        return self._safe_call('balance_sheet', lang=self.lang)

    def get_income_statement(self) -> pd.DataFrame:
        return self._safe_call('income_statement', lang=self.lang)

    def get_cash_flow(self) -> pd.DataFrame:
        return self._safe_call('cash_flow', lang=self.lang)

    def get_ratio(self) -> pd.DataFrame:
        return self._safe_call('ratio', lang=self.lang)


class ForeignExchangeEntity(StockEntity):
    def __init__(self, symbol: str, source: str):
        super().__init__(symbol, source)
        self._fx = None

    @property
    def fx(self):
        """Lazy initialization of FX instance."""
        if self._fx is None:
            try:
                self._fx = Vnstock().fx(symbol=self.symbol, source=self.source)
            except Exception as e:
                logger.error(f"Failed to initialize FX for {self.symbol}: {e}")
                # Try MSN as fallback source for FX
                self._fx = Vnstock().fx(symbol=self.symbol, source='MSN')
        return self._fx

    def get_fx_history(self, start: str, end: str, interval: str) -> pd.DataFrame:
        try:
            return self.fx.quote.history(start=start, end=end, interval=interval)
        except Exception as e:
            logger.error(f"Error getting FX history for {self.symbol}: {e}")
            return pd.DataFrame()


class CryptoEntity(StockEntity):
    def __init__(self, symbol: str, source: str):
        super().__init__(symbol=symbol, source=source)
        self._crypto = None

    @property
    def crypto(self):
        """Lazy initialization of Crypto instance."""
        if self._crypto is None:
            try:
                self._crypto = Vnstock().crypto(symbol=self.symbol, source=self.source)
            except Exception as e:
                logger.error(f"Failed to initialize Crypto for {self.symbol}: {e}")
                raise
        return self._crypto

    def get_crypto_history(self, start: str, end: str, interval: str) -> pd.DataFrame:
        try:
            return self.crypto.quote.history(start=start, end=end, interval=interval)
        except Exception as e:
            logger.error(f"Error getting Crypto history for {self.symbol}: {e}")
            return pd.DataFrame()


class WorldIndexEntity(StockEntity):
    def __init__(self, symbol: str, source: str):
        super().__init__(symbol=symbol, source=source)
        self._index = None

    @property
    def index(self):
        """Lazy initialization of World Index instance."""
        if self._index is None:
            try:
                self._index = Vnstock().world_index(symbol=self.symbol, source=self.source)
            except Exception as e:
                logger.error(f"Failed to initialize World Index for {self.symbol}: {e}")
                raise
        return self._index

    def get_index_history(self, start: str, end: str, interval: str) -> pd.DataFrame:
        try:
            return self.index.quote.history(start=start, end=end, interval=interval)
        except Exception as e:
            logger.error(f"Error getting World Index history for {self.symbol}: {e}")
            return pd.DataFrame()


class GoldService:
    @staticmethod
    @cache_result(ttl=300)
    def get_sjc_price() -> Dict:
        if not GOLD_PRICE_AVAILABLE:
            raise ExternalServiceException("SJC Gold Price", "Gold price module not available")
        try:
            return sjc_gold_price()
        except Exception as e:
            raise ExternalServiceException("SJC Gold Price", str(e))

    @staticmethod
    @cache_result(ttl=300)
    def get_btmc_price() -> Dict:
        if not GOLD_PRICE_AVAILABLE:
            raise ExternalServiceException("BTMC Gold Price", "Gold price module not available")
        try:
            return btmc_goldprice()
        except Exception as e:
            raise ExternalServiceException("BTMC Gold Price", str(e))