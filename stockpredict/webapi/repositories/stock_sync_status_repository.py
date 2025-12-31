"""
Stock Sync Status Repository
Manages sync status tracking for stock data synchronization between vnstock and local MySQL.
"""

from typing import Dict, List, Optional
from datetime import datetime
from repositories.base_repository import BaseRepository


class StockSyncStatusRepository(BaseRepository):
    """Repository for managing stock sync status records."""

    def table_name(self) -> str:
        return "tbl_stock_sync_status"

    def get_sync_status(self, ticker: str) -> Optional[Dict]:
        """
        Get sync status for a specific ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with sync status info or None if not found
        """
        query = f"SELECT * FROM {self.table_name()} WHERE ticker = %s"
        result = self.execute_query(query, (ticker.upper(),))
        return result[0] if result else None

    def get_all_sync_statuses(self) -> List[Dict]:
        """Get sync status for all tracked tickers."""
        query = f"SELECT * FROM {self.table_name()} ORDER BY ticker"
        return self.execute_query(query)

    def get_sync_statuses_for_tickers(self, tickers: List[str]) -> List[Dict]:
        """
        Get sync statuses for a list of tickers.

        Args:
            tickers: List of stock symbols

        Returns:
            List of sync status records
        """
        if not tickers:
            return []

        placeholders = ', '.join(['%s'] * len(tickers))
        query = f"SELECT * FROM {self.table_name()} WHERE ticker IN ({placeholders})"
        return self.execute_query(query, tuple(t.upper() for t in tickers))

    def create_sync_status(self, ticker: str, status: str = 'pending') -> bool:
        """
        Create initial sync status record for a ticker.

        Args:
            ticker: Stock symbol
            status: Initial status (pending, syncing, complete, error)

        Returns:
            True if created successfully
        """
        query = f"""
        INSERT INTO {self.table_name()} (ticker, sync_status, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        ON DUPLICATE KEY UPDATE updated_at = NOW()
        """
        return self.execute_non_query(query, (ticker.upper(), status)) > 0

    def set_syncing(self, ticker: str) -> bool:
        """
        Mark ticker as currently syncing.

        Args:
            ticker: Stock symbol

        Returns:
            True if updated successfully
        """
        query = f"""
        INSERT INTO {self.table_name()} (ticker, sync_status, updated_at)
        VALUES (%s, 'syncing', NOW())
        ON DUPLICATE KEY UPDATE
            sync_status = 'syncing',
            error_message = NULL,
            updated_at = NOW()
        """
        return self.execute_non_query(query, (ticker.upper(),)) > 0

    def set_complete(
        self,
        ticker: str,
        earliest_date: str,
        latest_date: str,
        total_records: int
    ) -> bool:
        """
        Mark sync as complete with metadata.

        Args:
            ticker: Stock symbol
            earliest_date: Earliest data date (YYYY-MM-DD)
            latest_date: Latest data date (YYYY-MM-DD)
            total_records: Total number of records stored

        Returns:
            True if updated successfully
        """
        query = f"""
        INSERT INTO {self.table_name()}
            (ticker, sync_status, last_sync_date, earliest_data_date,
             latest_data_date, total_records, error_message, updated_at)
        VALUES (%s, 'complete', NOW(), %s, %s, %s, NULL, NOW())
        ON DUPLICATE KEY UPDATE
            sync_status = 'complete',
            last_sync_date = NOW(),
            earliest_data_date = VALUES(earliest_data_date),
            latest_data_date = VALUES(latest_data_date),
            total_records = VALUES(total_records),
            error_message = NULL,
            updated_at = NOW()
        """
        return self.execute_non_query(
            query,
            (ticker.upper(), earliest_date, latest_date, total_records)
        ) > 0

    def set_error(self, ticker: str, error_message: str) -> bool:
        """
        Mark sync as failed with error message.

        Args:
            ticker: Stock symbol
            error_message: Description of the error

        Returns:
            True if updated successfully
        """
        query = f"""
        INSERT INTO {self.table_name()}
            (ticker, sync_status, error_message, updated_at)
        VALUES (%s, 'error', %s, NOW())
        ON DUPLICATE KEY UPDATE
            sync_status = 'error',
            error_message = VALUES(error_message),
            updated_at = NOW()
        """
        return self.execute_non_query(query, (ticker.upper(), error_message)) > 0

    def get_tickers_needing_sync(self) -> List[str]:
        """
        Get tickers that have never been synced or have pending status.

        Returns:
            List of ticker symbols
        """
        query = f"""
        SELECT ticker FROM {self.table_name()}
        WHERE sync_status IN ('pending', 'error')
        ORDER BY ticker
        """
        result = self.execute_query(query)
        return [row['ticker'] for row in result]

    def get_tickers_needing_update(self, days_threshold: int = 1) -> List[str]:
        """
        Get tickers that haven't been updated recently.

        Args:
            days_threshold: Number of days since last sync to consider stale

        Returns:
            List of ticker symbols needing update
        """
        query = f"""
        SELECT ticker FROM {self.table_name()}
        WHERE sync_status = 'complete'
          AND (last_sync_date IS NULL
               OR last_sync_date < DATE_SUB(NOW(), INTERVAL %s DAY))
        ORDER BY last_sync_date ASC
        """
        result = self.execute_query(query, (days_threshold,))
        return [row['ticker'] for row in result]

    def delete_sync_status(self, ticker: str) -> bool:
        """
        Delete sync status record for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            True if deleted successfully
        """
        query = f"DELETE FROM {self.table_name()} WHERE ticker = %s"
        return self.execute_non_query(query, (ticker.upper(),)) > 0

    def has_sync_status(self, ticker: str) -> bool:
        """
        Check if a ticker has sync status record.

        Args:
            ticker: Stock symbol

        Returns:
            True if record exists
        """
        query = f"SELECT 1 FROM {self.table_name()} WHERE ticker = %s LIMIT 1"
        result = self.execute_query(query, (ticker.upper(),))
        return len(result) > 0

    def is_sync_complete(self, ticker: str) -> bool:
        """
        Check if a ticker has completed sync.

        Args:
            ticker: Stock symbol

        Returns:
            True if sync is complete
        """
        status = self.get_sync_status(ticker)
        return status is not None and status.get('sync_status') == 'complete'

    def get_latest_data_date(self, ticker: str) -> Optional[str]:
        """
        Get the latest data date for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Date string (YYYY-MM-DD) or None
        """
        status = self.get_sync_status(ticker)
        if status and status.get('latest_data_date'):
            date_val = status['latest_data_date']
            if hasattr(date_val, 'strftime'):
                return date_val.strftime('%Y-%m-%d')
            return str(date_val)
        return None
