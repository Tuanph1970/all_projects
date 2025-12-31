from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import EntityNotFoundException
from decimal import Decimal
from services.stock_market_service import StockMarketService


class PortfolioRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_portfolio"
    
    def get_user_portfolio(self, user_id: int) -> List[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE user_id = %s ORDER BY symbol"
        return self.execute_query(query, (user_id,))
    
    def get_portfolio_item(self, user_id: int, symbol: str) -> Optional[Dict]:
        query = f"SELECT * FROM {self.table_name()} WHERE user_id = %s AND symbol = %s"
        result = self.execute_query(query, (user_id, symbol))
        return result[0] if result else None
    
    def add_stock_to_portfolio(self, user_id: int, symbol: str, company_name: str, shares: Decimal, price: Decimal) -> bool:
        try:
            existing = self.get_portfolio_item(user_id, symbol)
            
            if existing:
                old_shares = Decimal(str(existing['shares']))
                old_avg_price = Decimal(str(existing['avg_price']))
                new_shares = old_shares + shares
                new_avg_price = ((old_shares * old_avg_price) + (shares * price)) / new_shares
                
                query = f"UPDATE {self.table_name()} SET shares = %s, avg_price = %s, updated_at = NOW() WHERE user_id = %s AND symbol = %s"
                return self.execute_non_query(query, (new_shares, new_avg_price, user_id, symbol)) > 0
            else:
                query = f"INSERT INTO {self.table_name()} (user_id, symbol, company_name, shares, avg_price) VALUES (%s, %s, %s, %s, %s)"
                return self.execute_non_query(query, (user_id, symbol, company_name, shares, price)) > 0
        except Exception as e:
            print(f"Error adding stock to portfolio: {e}")
            return False
    
    def sell_stock_from_portfolio(self, user_id: int, symbol: str, shares_to_sell: Decimal) -> bool:
        try:
            existing = self.get_portfolio_item(user_id, symbol)
            
            if not existing:
                return False
            
            current_shares = Decimal(str(existing['shares']))
            
            if current_shares < shares_to_sell:
                return False
            
            new_shares = current_shares - shares_to_sell
            
            if new_shares == 0:
                query = f"DELETE FROM {self.table_name()} WHERE user_id = %s AND symbol = %s"
                return self.execute_non_query(query, (user_id, symbol)) > 0
            else:
                query = f"UPDATE {self.table_name()} SET shares = %s, updated_at = NOW() WHERE user_id = %s AND symbol = %s"
                return self.execute_non_query(query, (new_shares, user_id, symbol)) > 0
        except Exception as e:
            print(f"Error selling stock from portfolio: {e}")
            return False
    
    def remove_stock_from_portfolio(self, user_id: int, symbol: str) -> bool:
        try:
            query = f"DELETE FROM {self.table_name()} WHERE user_id = %s AND symbol = %s"
            return self.execute_non_query(query, (user_id, symbol)) > 0
        except Exception as e:
            print(f"Error removing stock from portfolio: {e}")
            return False
    
    def get_portfolio_summary(self, user_id: int) -> Dict:
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_stocks,
                    SUM(shares * avg_price) as total_value
                FROM {self.table_name()}
                WHERE user_id = %s
            """
            result = self.execute_query(query, (user_id,))
            return result[0] if result else {"total_stocks": 0, "total_value": 0}
        except Exception as e:
            print(f"Error getting portfolio summary: {e}")
            return {"total_stocks": 0, "total_value": 0}

    def get_user_portfolio_symbols(self, user_id: int) -> List[str]:
        """
        Get just the stock symbols from user's portfolio.

        Args:
            user_id: User ID

        Returns:
            List of ticker symbols (uppercase)
        """
        query = f"SELECT DISTINCT symbol FROM {self.table_name()} WHERE user_id = %s ORDER BY symbol"
        result = self.execute_query(query, (user_id,))
        return [row['symbol'].upper() for row in result if row.get('symbol')]

    def get_portfolio_with_sync_status(self, user_id: int) -> List[Dict]:
        """
        Get user's portfolio items with sync status information.

        Args:
            user_id: User ID

        Returns:
            List of portfolio items with sync status
        """
        query = f"""
            SELECT
                p.*,
                s.sync_status,
                s.last_sync_date,
                s.total_records,
                s.earliest_data_date,
                s.latest_data_date
            FROM {self.table_name()} p
            LEFT JOIN tbl_stock_sync_status s ON p.symbol = s.ticker
            WHERE p.user_id = %s
            ORDER BY p.symbol
        """
        return self.execute_query(query, (user_id,))
