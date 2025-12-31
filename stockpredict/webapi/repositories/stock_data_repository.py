from typing import Dict, List, Optional
import datetime as dt
import pandas as pd
from repositories.base_repository import BaseRepository


class StockDataRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_stock_history"
    
    def get_latest_trading_date(self, ticker: str) -> Optional[str]:
        query = f"""
        SELECT tradingdate FROM {self.table_name()} 
        WHERE ticker = %s 
        ORDER BY tradingdate DESC 
        LIMIT 1
        """
        result = self.execute_query(query, (ticker,))
        return result[0]['tradingdate'].strftime('%Y-%m-%d') if result else None
    
    def insert_stock_data(self, ticker: str, open_price: float, high: float, 
                         low: float, close: float, volume: int, trading_date: str) -> bool:
        query = f"""
        INSERT INTO {self.table_name()} 
        (ticker, open, high, low, close, volume, tradingdate) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (ticker, open_price, high, low, close, volume, trading_date)
        return self.execute_non_query(query, params) > 0
    
    def get_stock_history(self, ticker: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE ticker = %s"
        params = [ticker]
        
        if start_date:
            query += " AND tradingdate >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND tradingdate <= %s"
            params.append(end_date)
        
        query += " ORDER BY tradingdate ASC"
        
        return self.execute_query(query, tuple(params))
    
    def get_stock_history_df(self, ticker: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        query = f"SELECT * FROM {self.table_name()} WHERE ticker = %s"
        params = [ticker]
        
        if start_date:
            query += " AND tradingdate >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND tradingdate <= %s"
            params.append(end_date)
        
        query += " ORDER BY tradingdate ASC"
        
        return self.fetch_dataframe(query, tuple(params))


class TopStockRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_top_stock"
    
    def get_top_stock_tickers(self) -> List[str]:
        query = f"SELECT ticker FROM {self.table_name()}"
        result = self.execute_query(query)
        return [row['ticker'] for row in result]
    
    def get_all_top_stocks(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)