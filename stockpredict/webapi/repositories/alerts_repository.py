from typing import Dict, List, Optional
from repositories.base_repository import BaseRepository
from core.exceptions import EntityNotFoundException
from decimal import Decimal
from datetime import datetime


class AlertsRepository(BaseRepository):
    def table_name(self) -> str:
        return "tbl_price_alerts"
    
    def get_user_alerts(self, user_id: int) -> List[Dict]:
        """Get all alerts for a specific user"""
        query = f"""
            SELECT id, user_id, symbol, company_name, alert_type, 
                   target_price, is_active, triggered, notes, created_at, updated_at
            FROM {self.table_name()} 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))
    
    def get_alert_by_id(self, alert_id: int, user_id: int) -> Optional[Dict]:
        """Get a specific alert by ID and user ID"""
        query = f"""
            SELECT id, user_id, symbol, company_name, alert_type, 
                   target_price, is_active, triggered, notes, created_at, updated_at
            FROM {self.table_name()} 
            WHERE id = %s AND user_id = %s
        """
        result = self.execute_query(query, (alert_id, user_id))
        return result[0] if result else None
    
    def create_alert(self, user_id: int, symbol: str, company_name: str, 
                    alert_type: str, target_price: Decimal, 
                    is_active: bool = True, notes: str = '') -> bool:
        """Create a new price alert"""
        try:
            query = f"""
                INSERT INTO {self.table_name()} 
                (user_id, symbol, company_name, alert_type, target_price, is_active, notes, triggered, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            return self.execute_non_query(
                query, 
                (user_id, symbol, company_name, alert_type, target_price, is_active, notes, False)
            ) > 0
        except Exception as e:
            print(f"Error creating alert: {e}")
            return False
    
    def update_alert(self, alert_id: int, user_id: int, symbol: str, 
                    company_name: str, alert_type: str, target_price: Decimal,
                    is_active: bool = True, notes: str = '') -> bool:
        """Update an existing alert"""
        try:
            # Reset triggered status when updating
            query = f"""
                UPDATE {self.table_name()} 
                SET symbol = %s, company_name = %s, alert_type = %s, 
                    target_price = %s, is_active = %s, notes = %s, 
                    triggered = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """
            return self.execute_non_query(
                query,
                (symbol, company_name, alert_type, target_price, is_active, notes, False, alert_id, user_id)
            ) > 0
        except Exception as e:
            print(f"Error updating alert: {e}")
            return False
    
    def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete an alert"""
        try:
            query = f"DELETE FROM {self.table_name()} WHERE id = %s AND user_id = %s"
            return self.execute_non_query(query, (alert_id, user_id)) > 0
        except Exception as e:
            print(f"Error deleting alert: {e}")
            return False
    
    def toggle_alert_status(self, alert_id: int, user_id: int) -> bool:
        """Toggle the active status of an alert"""
        try:
            # First get the current status
            alert = self.get_alert_by_id(alert_id, user_id)
            if not alert:
                return False
            
            new_status = not alert['is_active']
            
            query = f"""
                UPDATE {self.table_name()} 
                SET is_active = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """
            return self.execute_non_query(query, (new_status, alert_id, user_id)) > 0
        except Exception as e:
            print(f"Error toggling alert status: {e}")
            return False
    
    def update_triggered_alerts(self, symbol: str, current_price: Decimal) -> int:
        """Update alerts that have been triggered by current price"""
        try:
            # Update alerts that should be triggered based on current price
            query_above = f"""
                UPDATE {self.table_name()} 
                SET triggered = TRUE, updated_at = NOW()
                WHERE symbol = %s 
                    AND is_active = TRUE 
                    AND triggered = FALSE
                    AND alert_type = 'price_above' 
                    AND %s >= target_price
            """
            count_above = self.execute_non_query(query_above, (symbol, current_price))
            
            query_below = f"""
                UPDATE {self.table_name()} 
                SET triggered = TRUE, updated_at = NOW()
                WHERE symbol = %s 
                    AND is_active = TRUE 
                    AND triggered = FALSE
                    AND alert_type = 'price_below' 
                    AND %s <= target_price
            """
            count_below = self.execute_non_query(query_below, (symbol, current_price))
            
            return count_above + count_below
        except Exception as e:
            print(f"Error updating triggered alerts: {e}")
            return 0
    
    def get_active_alerts_for_symbol(self, symbol: str) -> List[Dict]:
        """Get all active alerts for a specific symbol"""
        query = f"""
            SELECT id, user_id, symbol, company_name, alert_type, 
                   target_price, is_active, triggered, notes, created_at, updated_at
            FROM {self.table_name()} 
            WHERE symbol = %s AND is_active = TRUE AND triggered = FALSE
            ORDER BY target_price
        """
        return self.execute_query(query, (symbol,))
    
    def reset_triggered_alert(self, alert_id: int, user_id: int) -> bool:
        """Reset a triggered alert to allow it to trigger again"""
        try:
            query = f"""
                UPDATE {self.table_name()} 
                SET triggered = FALSE, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """
            return self.execute_non_query(query, (alert_id, user_id)) > 0
        except Exception as e:
            print(f"Error resetting triggered alert: {e}")
            return False