from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from services.stock_entity_service import MarketStockEntity, CompanyStockEntity, StockFinanceEntity


class DataSourceStrategy(ABC):
    @abstractmethod
    def get_market_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_company_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_financial_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        pass


class VCIDataSourceStrategy(DataSourceStrategy):
    def get_market_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        market_stock = MarketStockEntity(symbol=symbol, source="VCI")
        return market_stock.get_all_companies()
    
    def get_company_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        company_stock = CompanyStockEntity(symbol=symbol, source="VCI")
        return company_stock.overview_company()
    
    def get_financial_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        period = kwargs.get('period', 'quarter')
        language = kwargs.get('language', 'en')
        financial = StockFinanceEntity(symbol, "VCI", period, language)
        return financial.get_income_statement()


class TCBSDataSourceStrategy(DataSourceStrategy):
    def get_market_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        market_stock = MarketStockEntity(symbol=symbol, source="TCBS")
        return market_stock.get_all_companies()
    
    def get_company_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        company_stock = CompanyStockEntity(symbol=symbol, source="TCBS")
        return company_stock.overview_company()
    
    def get_financial_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        period = kwargs.get('period', 'quarter')
        language = kwargs.get('language', 'en')
        financial = StockFinanceEntity(symbol, "TCBS", period, language)
        return financial.get_income_statement()


class DataSourceContext:
    def __init__(self, strategy: DataSourceStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: DataSourceStrategy):
        self._strategy = strategy
    
    def get_market_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        return self._strategy.get_market_data(symbol, **kwargs)
    
    def get_company_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        return self._strategy.get_company_data(symbol, **kwargs)
    
    def get_financial_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        return self._strategy.get_financial_data(symbol, **kwargs)


class DataSourceStrategyFactory:
    _strategies = {
        'VCI': VCIDataSourceStrategy(),
        'TCBS': TCBSDataSourceStrategy()
    }
    
    @classmethod
    def get_strategy(cls, source_type: str) -> DataSourceStrategy:
        strategy = cls._strategies.get(source_type)
        if not strategy:
            raise ValueError(f"Unsupported data source strategy: {source_type}")
        return strategy
    
    @classmethod
    def create_context(cls, source_type: str) -> DataSourceContext:
        strategy = cls.get_strategy(source_type)
        return DataSourceContext(strategy)