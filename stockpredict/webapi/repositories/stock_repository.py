from typing import Dict, List, Optional
import pandas as pd
from repositories.base_repository import BaseRepository
from core.exceptions import EntityNotFoundException


class StockRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_stock_history"
    
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
    
    def insert_stock_data(self, ticker: str, open_price: float, high: float, 
                         low: float, close: float, volume: int, trading_date: str) -> bool:
        query = f"""
        INSERT INTO {self.table_name()} 
        (ticker, open, high, low, close, volume, tradingdate) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (ticker, open_price, high, low, close, volume, trading_date)
        
        return self.execute_non_query(query, params) > 0
    
    def get_latest_trading_date(self, ticker: str) -> Optional[str]:
        query = f"""
        SELECT tradingdate FROM {self.table_name()}
        WHERE ticker = %s
        ORDER BY tradingdate DESC
        LIMIT 1
        """
        result = self.execute_query(query, (ticker,))
        return result[0]['tradingdate'].strftime('%Y-%m-%d') if result else None

    def get_earliest_trading_date(self, ticker: str) -> Optional[str]:
        """Get the earliest trading date for a ticker."""
        query = f"""
        SELECT tradingdate FROM {self.table_name()}
        WHERE ticker = %s
        ORDER BY tradingdate ASC
        LIMIT 1
        """
        result = self.execute_query(query, (ticker,))
        if result and result[0]['tradingdate']:
            date_val = result[0]['tradingdate']
            if hasattr(date_val, 'strftime'):
                return date_val.strftime('%Y-%m-%d')
            return str(date_val)
        return None

    def has_data_for_ticker(self, ticker: str) -> bool:
        """Check if any data exists for a ticker."""
        query = f"SELECT 1 FROM {self.table_name()} WHERE ticker = %s LIMIT 1"
        result = self.execute_query(query, (ticker.upper(),))
        return len(result) > 0

    def get_data_count(self, ticker: str) -> int:
        """Get total record count for a ticker."""
        query = f"SELECT COUNT(*) as cnt FROM {self.table_name()} WHERE ticker = %s"
        result = self.execute_query(query, (ticker.upper(),))
        return result[0]['cnt'] if result else 0

    def get_date_range(self, ticker: str) -> Optional[Dict]:
        """
        Get earliest and latest date for a ticker.

        Returns:
            Dict with 'earliest_date' and 'latest_date' or None if no data
        """
        query = f"""
        SELECT
            MIN(tradingdate) as earliest_date,
            MAX(tradingdate) as latest_date,
            COUNT(*) as total_records
        FROM {self.table_name()}
        WHERE ticker = %s
        """
        result = self.execute_query(query, (ticker.upper(),))
        if result and result[0]['earliest_date']:
            row = result[0]
            earliest = row['earliest_date']
            latest = row['latest_date']
            return {
                'earliest_date': earliest.strftime('%Y-%m-%d') if hasattr(earliest, 'strftime') else str(earliest),
                'latest_date': latest.strftime('%Y-%m-%d') if hasattr(latest, 'strftime') else str(latest),
                'total_records': row['total_records']
            }
        return None

    def bulk_upsert_stock_data(self, records: List[Dict]) -> int:
        """
        Bulk insert/update stock data using INSERT ... ON DUPLICATE KEY UPDATE.

        Args:
            records: List of dicts with keys: ticker, open, high, low, close, volume, tradingdate

        Returns:
            Number of affected rows
        """
        if not records:
            return 0

        # Build the bulk insert query
        query = f"""
        INSERT INTO {self.table_name()}
            (ticker, open, high, low, close, volume, tradingdate)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume)
        """

        # Process records in batches to avoid memory issues
        batch_size = 500
        total_affected = 0
        connection = None
        cursor = None

        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                params_list = [
                    (
                        str(r.get('ticker', '')).upper(),
                        float(r.get('open', 0)),
                        float(r.get('high', 0)),
                        float(r.get('low', 0)),
                        float(r.get('close', 0)),
                        int(r.get('volume', 0)),
                        str(r.get('tradingdate', r.get('time', '')))[:10]  # Handle both tradingdate and time keys
                    )
                    for r in batch
                ]

                cursor.executemany(query, params_list)
                total_affected += cursor.rowcount

            connection.commit()
            return total_affected

        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def bulk_upsert_from_dataframe(self, ticker: str, df: pd.DataFrame) -> int:
        """
        Bulk upsert stock data from a pandas DataFrame.

        Args:
            ticker: Stock symbol
            df: DataFrame with columns: time/date, open, high, low, close, volume

        Returns:
            Number of affected rows
        """
        if df is None or df.empty:
            return 0

        # Normalize column names
        df_copy = df.copy()

        # Handle different date column names
        date_col = None
        for col in ['time', 'date', 'tradingdate', 'trading_date']:
            if col in df_copy.columns:
                date_col = col
                break

        if date_col is None and df_copy.index.name in ['time', 'date', 'tradingdate']:
            df_copy = df_copy.reset_index()
            date_col = df_copy.columns[0]

        if date_col is None:
            raise ValueError("DataFrame must have a date column (time, date, or tradingdate)")

        # Convert to records format
        records = []
        for _, row in df_copy.iterrows():
            date_val = row[date_col]
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val)[:10]

            records.append({
                'ticker': ticker.upper(),
                'open': float(row.get('open', 0)),
                'high': float(row.get('high', 0)),
                'low': float(row.get('low', 0)),
                'close': float(row.get('close', 0)),
                'volume': int(row.get('volume', 0)),
                'tradingdate': date_str
            })

        return self.bulk_upsert_stock_data(records)

    def delete_ticker_data(self, ticker: str) -> int:
        """
        Delete all data for a ticker (for re-sync).

        Args:
            ticker: Stock symbol

        Returns:
            Number of deleted rows
        """
        query = f"DELETE FROM {self.table_name()} WHERE ticker = %s"
        return self.execute_non_query(query, (ticker.upper(),))


class CompanyRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_company"
    
    def get_company_by_ticker(self, ticker: str) -> Optional[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE ticker = %s"
        result = self.execute_query(query, (ticker,))
        return result[0] if result else None
    
    def get_companies_by_industry(self, industry_id: int) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE industryID = %s"
        return self.execute_query(query, (industry_id,))
    
    def get_all_companies(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)
    
    def create_company(self, company_data: Dict) -> bool:
        fields = ', '.join(company_data.keys())
        placeholders = ', '.join(['%s'] * len(company_data))
        query = f"INSERT INTO {self.table_name()} ({fields}) VALUES ({placeholders})"
        
        return self.execute_non_query(query, tuple(company_data.values())) > 0


class TopStockRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_top_stock"
    
    def get_top_stocks(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)
    
    def get_top_stock_tickers(self) -> List[str]:
        query = f"SELECT ticker FROM {self.table_name()}"
        result = self.execute_query(query)
        return [row['ticker'] for row in result]


class MarketIndexRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_market_index_series"
    
    def get_market_index_series(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)


class LatestIndicesRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_market_latest_indices_series"
    
    def get_latest_indices_series(self) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()}"
        return self.execute_query(query)