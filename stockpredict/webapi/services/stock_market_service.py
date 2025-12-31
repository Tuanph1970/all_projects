from typing import Dict, List, Optional
import logging
import pandas as pd
from repositories.stock_repository import StockRepository, CompanyRepository
from services.stock_entity_service import MarketStockEntity, CompanyStockEntity, StockFinanceEntity
from core.exceptions import EntityNotFoundException, ExternalServiceException
from core.factories import DataSourceFactory
from core.decorators import cache_result, validate_input, retry, validate_ticker, validate_date_string
from core.config import get_config

logger = logging.getLogger(__name__)


class StockMarketService:
    def __init__(self):
        self.stock_repo = StockRepository()
        self.company_repo = CompanyRepository()
        self.config = get_config()
    
    @cache_result(ttl=300)
    @retry(max_attempts=3)
    def get_companies_by_group(self, group: str, symbol: str = "VN30F1M", 
                              source: str = None) -> List[Dict]:
        try:
            source = source or self.config.stock_data.default_source
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_companies_info(group=group)
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_all_companies(self, symbol: str = "VN30F1M", source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_all_companies()
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_companies_by_industry(self, industry_id: int, symbol: str = "VN30F1M", 
                                 source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_companies_by_industry(industry_id)
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_top_gainers(self, symbol: str = "VN30F1M", source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_top_gainers()
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_top_losers(self, symbol: str = "VN30F1M", source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_top_losers()
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_top_actives(self, symbol: str = "VN30F1M", source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_top_actives()
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_price_boards(self, group: str, symbol: str = "VN30F1M", 
                        source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_price_board(group)
            
            new_columns = []
            for column in df.columns:
                if column[1] == 'symbol':
                    new_column = 'symbol'
                else:
                    new_column = column[0] + column[1]
                new_columns.append(new_column)
            df.columns = new_columns
            
            df_all = market_stock.get_all_companies()
            df_all = df_all[['open', 'ticker']]
            df = df.merge(df_all, how='left', left_on="symbol", right_on="ticker")
            
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_industries(self, symbol: str = "VN30F1M", source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_main_industries()
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    @cache_result(ttl=60)  # Cache for 1 minute due to real-time price data
    def get_symbol_and_price(self, source: str = "VCI") -> List[Dict]:
        """
        Get list of all stocks with their symbols and current prices
        
        Args:
            source: Data source (default: VCI)
            
        Returns:
            List of dictionaries containing symbol and current_price
        """
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol="VN30F1M", source=validated_source)
            
            # Get all companies to get the symbols
            df = market_stock.get_all_companies()
            
            # Extract symbol and current price columns
            # Based on the stock entities structure, we need to identify the correct column names
            if 'ticker' in df.columns and 'close' in df.columns:
                result_df = df[['ticker','short_name', 'close']].copy()
                result_df.columns = ['symbol','name','price']
            elif 'symbol' in df.columns and 'close' in df.columns:
                result_df = df[['symbol','short_name', 'close']].copy()
                result_df.columns = ['symbol','name', 'price']
            elif 'ticker' in df.columns and 'price' in df.columns:
                result_df = df[['ticker','short_name', 'price']].copy()
                result_df.columns = ['symbol','name', 'current_price']
            else:
                # Fallback: try to find any price-related column
                symbol_col = 'ticker' if 'ticker' in df.columns else 'symbol'
                price_cols = [col for col in df.columns if any(price_term in col.lower() 
                             for price_term in ['close', 'price', 'last', 'current'])]
                if price_cols:
                    result_df = df[[symbol_col, price_cols[0]]].copy()
                    result_df.columns = ['symbol', 'price']
                else:
                    # If no price column found, set current_price to 0
                    result_df = df[[symbol_col]].copy()
                    result_df.columns = ['symbol']
                    result_df['price'] = 0.0
            
            # Clean and format the data
            result_df = result_df.dropna(subset=['symbol'])
            result_df['symbol'] = result_df['symbol'].astype(str)
            result_df['name'] = result_df['name'].astype(str)
            price_series = pd.to_numeric(result_df['price'], errors='coerce')
            result_df['price'] = price_series.infer_objects(copy=False).fillna(0.0)
            
            return market_stock.dump_json(result_df)
            
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))


class CompanyService:
    def __init__(self):
        self.company_repo = CompanyRepository()
        self.config = get_config()
    
    @cache_result(ttl=600)
    @validate_input(symbol=validate_ticker)
    def get_company_overview(self, symbol: str, source: str = None) -> List[Dict]:
        try:
            source = source or self.config.stock_data.default_source
            validated_source = DataSourceFactory.get_data_source(source)
            company_obj = CompanyStockEntity(symbol=symbol, source=validated_source)
            df = company_obj.overview_company()
            return company_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("CompanyStock", str(e))
    
    def get_company_profile(self, symbol: str, source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            company_obj = CompanyStockEntity(symbol=symbol, source=validated_source)
            df = company_obj.get_company_profile()
            return company_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("CompanyStock", str(e))
    
    def get_company_events(self, symbol: str, source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            company_obj = CompanyStockEntity(symbol=symbol, source=validated_source)
            df = company_obj.get_company_events()
            return company_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("CompanyStock", str(e))
    
    def get_company_news(self, symbol: str, source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            company_obj = CompanyStockEntity(symbol=symbol, source=validated_source)
            df = company_obj.get_company_news()
            return company_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("CompanyStock", str(e))
    
    def get_company_dividends(self, symbol: str, source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            company_obj = CompanyStockEntity(symbol=symbol, source=validated_source)
            df = company_obj.get_company_dividends()
            return company_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("CompanyStock", str(e))
    
    def get_price_history(self, symbol: str, start: str, end: str, 
                         source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_price_history(symbol=symbol, start=start, end=end)
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_price_history_df(self, symbol: str, source: str = "VCI",
                           start: str = '2000-01-01', end: str = '2100-01-01') -> pd.DataFrame:
        """
        Get price history with database-first strategy.
        For training/prediction, always tries local DB first, then falls back to vnstock.

        Args:
            symbol: Stock ticker symbol
            source: Data source (default: VCI)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Try local database first
            stock_repo = StockRepository()
            df = stock_repo.get_stock_history_df(symbol.upper(), start, end)

            if df is not None and not df.empty:
                logger.info(f"Retrieved {len(df)} records for {symbol} from local database")
                # Normalize column names to match vnstock format
                if 'tradingdate' in df.columns:
                    df = df.rename(columns={'tradingdate': 'time'})
                return df

            # Fallback to vnstock
            logger.warning(f"No local data for {symbol} in range {start} to {end}, falling back to vnstock")
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            return market_stock.get_price_history(symbol=symbol, start=start, end=end)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))
    
    def get_all_history_data(self, symbol: str, source: str = "VCI") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            market_stock = MarketStockEntity(symbol=symbol, source=validated_source)
            df = market_stock.get_price_history(symbol=symbol, start='2000-01-01', end='2100-01-01')
            return market_stock.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("MarketStock", str(e))


class FinancialService:
    def get_financial_income_statement(self, symbol: str, source: str = "VCI",
                                      period: str = "quarter", language: str = "en") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            financial_obj = StockFinanceEntity(symbol, validated_source, period, language)
            df = financial_obj.get_income_statement()

            # Select columns by name (more robust than positional indexing)
            desired_columns = [
                "ticker", "yearReport", "Minority Interest", "Net Profit/Loss before tax",
                "Dividends received", "Provision for credit losses", "Revenue YoY (%)",
                "Revenue (Bn. VND)", "Financial Income", "Interest Expenses", "Net Sales",
                "Gross Profit", "Financial Expenses", "General & Admin Expenses",
                "Operating Profit/Loss", "Other Income/Expenses", "Selling Expenses", "Sales",
                "Sales deductions", "Gain/(loss) from joint ventures", "Other income",
                "Net Interest Income", "Total operating revenue", "Profit before tax",
                "Business income tax - current", "Net Profit For the Year", "EPS_basis"
            ]
            # Only select columns that exist in the DataFrame
            available_columns = [col for col in desired_columns if col in df.columns]
            df = df[available_columns]
            df = self._rename_income_statement_columns(df)

            return financial_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("StockFinance", str(e))
    
    def _rename_income_statement_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            "ticker": "symbol", "yearReport": "report_year",
            "Minority Interest": "minor_interest", "Net Profit/Loss before tax": "net_profit",
            "Dividends received": "dividend_receive", "Provision for credit losses": "provision_credit_lost",
            "Revenue YoY (%)": "revenue_percent", "Revenue (Bn. VND)": "revenue",
            "Financial Income": "finance_income", "Interest Expenses": "interest_expense",
            "Net Sales": "net_sales", "Gross Profit": "gross_profit",
            "Financial Expenses": "financial_expenses", "General & Admin Expenses": "general_admin_expenses",
            "Operating Profit/Loss": "operating_profit", "Other Income/Expenses": "other_income_expenses",
            "Selling Expenses": "selling_expenses", "Sales": "sales",
            "Sales deductions": "sales_deductions", "Gain/(loss) from joint ventures": "gain_from_joint_ventures",
            "Other income": "other_income", "Net Interest Income": "net_interest_income",
            "Total operating revenue": "total_operating_revenue", "Profit before tax": "profit_before_tax",
            "Business income tax - current": "income_tax_current", "Net Profit For the Year": "net_profit_for_the_year",
            "EPS_basis": "eps_basis"
        }
        return df.rename(columns=column_mapping)
    
    def get_financial_cash_flow(self, symbol: str, source: str = "VCI",
                               period: str = "quarter", language: str = "en") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            financial_obj = StockFinanceEntity(symbol, validated_source, period, language)
            df = financial_obj.get_cash_flow()

            # Select columns by name (more robust than positional indexing)
            desired_columns = [
                "ticker", "yearReport", "Cash and cash equivalents",
                "Profit/Loss from disposal of fixed assets", "Profit/Loss from investing activities",
                "Interest Expense", "Interest income and dividends",
                "Increase/Decrease in receivables", "Increase/Decrease in inventories",
                "Increase/Decrease in payables", "Interest paid",
                "Net cash inflows/outflows from operating activities"
            ]
            # Only select columns that exist in the DataFrame
            available_columns = [col for col in desired_columns if col in df.columns]
            df = df[available_columns]
            df = self._rename_cash_flow_columns(df)

            return financial_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("StockFinance", str(e))
    
    def _rename_cash_flow_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            "ticker": "symbol", "yearReport": "report_year",
            "Cash and cash equivalents": "cash",
            "Profit/Loss from disposal of fixed assets": "profit_disposal_fixed_assets",
            "Profit/Loss from investing activities": "profit_investing_activities",
            "Interest Expense": "interest_expense",
            "Interest income and dividends": "interest_income_and_dividends",
            "Increase/Decrease in receivables": "increase_decrease_in_receivables",
            "Increase/Decrease in inventories": "increase_decrease_in_inventories",
            "Increase/Decrease in payables": "increase_decrease in payables",
            "Interest paid": "interest_paid",
            "Net cash inflows/outflows from operating activities": "cash_from_operating_activities"
        }
        return df.rename(columns=column_mapping)

    def get_company_balance_sheet(self, symbol: str, source: str = "VCI",
                                  period: str = "quarter", language: str = "en") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            financial_obj = StockFinanceEntity(symbol, validated_source, period, language)
            df = financial_obj.get_company_balance_sheet()
            return financial_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("StockFinance", str(e))

    def get_company_financial_ratio(self, symbol: str, source: str = "VCI",
                                    period: str = "quarter", language: str = "en") -> List[Dict]:
        try:
            validated_source = DataSourceFactory.get_data_source(source)
            financial_obj = StockFinanceEntity(symbol, validated_source, period, language)
            df = financial_obj.get_ratio()
            return financial_obj.dump_json(df)
        except Exception as e:
            raise ExternalServiceException("StockFinance", str(e))