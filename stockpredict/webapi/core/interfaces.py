from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar('T')


class Repository(ABC, Generic[T]):
    @abstractmethod
    def find_by_id(self, id: Any) -> Optional[T]:
        pass
    
    @abstractmethod
    def find_all(self) -> List[T]:
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        pass
    
    @abstractmethod
    def delete(self, id: Any) -> bool:
        pass


class StockDataRepository(ABC):
    @abstractmethod
    def get_stock_history(self, ticker: str, start_date: str, end_date: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        pass


class StockMarketService(ABC):
    @abstractmethod
    def get_companies_by_group(self, group: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_top_gainers(self) -> List[Dict]:
        pass


class ModelService(ABC):
    @abstractmethod
    def create_model(self, model_data: Dict) -> Dict:
        pass
    
    @abstractmethod
    def get_model_by_id(self, model_id: int) -> Optional[Dict]:
        pass


class DataSource(ABC):
    @abstractmethod
    def fetch_data(self, **kwargs) -> Any:
        pass