"""
Stock Data Sync Service
Synchronizes stock data between vnstock API and local MySQL database.
Implements on-demand sync strategy with graceful fallback.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

from repositories.stock_repository import StockRepository
from repositories.stock_sync_status_repository import StockSyncStatusRepository

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    status: str  # 'success', 'error', 'skipped'
    records_added: int
    message: str
    error_message: Optional[str] = None
    ticker: Optional[str] = None
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None


class StockDataSyncService:
    """
    Service for synchronizing stock data between vnstock API and local MySQL database.
    Implements on-demand sync strategy with graceful fallback.
    """

    DEFAULT_YEARS_HISTORY = 5

    def __init__(self):
        self.stock_repo = StockRepository()
        self.sync_status_repo = StockSyncStatusRepository()
        self._vnstock_service = None

    @property
    def vnstock_service(self):
        """Lazy load vnstock service to avoid circular imports."""
        if self._vnstock_service is None:
            from services.stock_entities import StockService
            self._vnstock_service = StockService()
        return self._vnstock_service

    def sync_stock_data(self, ticker: str, force_full: bool = False) -> SyncResult:
        """
        Main sync method called when user adds stock to portfolio.
        Fetches historical data from vnstock and stores in MySQL.

        Args:
            ticker: Stock symbol to sync
            force_full: If True, resync all history. If False, only update missing dates.

        Returns:
            SyncResult with status, records_added, error_message
        """
        ticker = ticker.upper()
        logger.info(f"Starting sync for {ticker} (force_full={force_full})")

        try:
            # Check if we already have data and it's recent
            if not force_full:
                sync_status = self.sync_status_repo.get_sync_status(ticker)
                if sync_status and sync_status.get('sync_status') == 'complete':
                    # Already have data, just do an incremental update
                    return self.update_latest_data(ticker)

            # Mark as syncing
            self.sync_status_repo.set_syncing(ticker)

            # Calculate date range (5 years back to today)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=self.DEFAULT_YEARS_HISTORY * 365)).strftime('%Y-%m-%d')

            # Fetch data from vnstock
            logger.info(f"Fetching {ticker} data from vnstock: {start_date} to {end_date}")
            df = self._fetch_from_vnstock(ticker, start_date, end_date)

            if df is None or df.empty:
                error_msg = f"No data returned from vnstock for {ticker}"
                logger.warning(error_msg)
                self.sync_status_repo.set_error(ticker, error_msg)
                return SyncResult(
                    status='error',
                    records_added=0,
                    message=error_msg,
                    error_message=error_msg,
                    ticker=ticker
                )

            # Store in database
            records_added = self.stock_repo.bulk_upsert_from_dataframe(ticker, df)
            logger.info(f"Stored {records_added} records for {ticker}")

            # Get date range for metadata
            date_range = self.stock_repo.get_date_range(ticker)
            earliest_date = date_range['earliest_date'] if date_range else start_date
            latest_date = date_range['latest_date'] if date_range else end_date
            total_records = date_range['total_records'] if date_range else records_added

            # Update sync status
            self.sync_status_repo.set_complete(ticker, earliest_date, latest_date, total_records)

            return SyncResult(
                status='success',
                records_added=records_added,
                message=f"Successfully synced {records_added} records for {ticker}",
                ticker=ticker,
                earliest_date=earliest_date,
                latest_date=latest_date
            )

        except Exception as e:
            error_msg = f"Sync failed for {ticker}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.sync_status_repo.set_error(ticker, str(e))
            return SyncResult(
                status='error',
                records_added=0,
                message=error_msg,
                error_message=str(e),
                ticker=ticker
            )

    def update_latest_data(self, ticker: str) -> SyncResult:
        """
        Called before training to update with latest data.
        Fetches from last_sync_date to today.
        Graceful failure: returns success with existing data if vnstock fails.

        Args:
            ticker: Stock symbol

        Returns:
            SyncResult (always returns success status for graceful degradation)
        """
        ticker = ticker.upper()
        logger.info(f"Updating latest data for {ticker}")

        try:
            # Get current sync status
            sync_status = self.sync_status_repo.get_sync_status(ticker)

            # If never synced, do a full sync
            if not sync_status or sync_status.get('sync_status') != 'complete':
                logger.info(f"{ticker} not synced yet, performing full sync")
                return self.sync_stock_data(ticker)

            # Check if we already have today's data
            latest_date_str = sync_status.get('latest_data_date')
            if latest_date_str:
                if hasattr(latest_date_str, 'strftime'):
                    latest_date = latest_date_str
                else:
                    latest_date = datetime.strptime(str(latest_date_str)[:10], '%Y-%m-%d')

                # Skip if already updated today
                if latest_date.date() >= (datetime.now() - timedelta(days=1)).date():
                    logger.info(f"{ticker} already up to date (latest: {latest_date_str})")
                    return SyncResult(
                        status='skipped',
                        records_added=0,
                        message=f"{ticker} already up to date",
                        ticker=ticker,
                        latest_date=str(latest_date_str)[:10]
                    )

                # Calculate incremental date range
                start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                # No latest date, get from last week
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            end_date = datetime.now().strftime('%Y-%m-%d')

            # Try to fetch new data from vnstock
            logger.info(f"Fetching incremental data for {ticker}: {start_date} to {end_date}")
            df = self._fetch_from_vnstock(ticker, start_date, end_date)

            if df is None or df.empty:
                # Graceful degradation: return success with existing data
                logger.warning(f"No new data from vnstock for {ticker}, using existing data")
                return SyncResult(
                    status='success',
                    records_added=0,
                    message=f"No new data available for {ticker}, using existing data",
                    ticker=ticker
                )

            # Store new records
            records_added = self.stock_repo.bulk_upsert_from_dataframe(ticker, df)
            logger.info(f"Added {records_added} new records for {ticker}")

            # Update sync status
            date_range = self.stock_repo.get_date_range(ticker)
            if date_range:
                self.sync_status_repo.set_complete(
                    ticker,
                    date_range['earliest_date'],
                    date_range['latest_date'],
                    date_range['total_records']
                )

            return SyncResult(
                status='success',
                records_added=records_added,
                message=f"Updated {ticker} with {records_added} new records",
                ticker=ticker,
                latest_date=date_range['latest_date'] if date_range else end_date
            )

        except Exception as e:
            # Graceful degradation: log error but return success
            # Training can proceed with existing data
            logger.warning(f"Update failed for {ticker}: {str(e)}. Using existing data.")
            return SyncResult(
                status='success',  # Return success to allow training to continue
                records_added=0,
                message=f"Update failed for {ticker}, using existing data: {str(e)}",
                error_message=str(e),
                ticker=ticker
            )

    def get_sync_status(self, ticker: str) -> Optional[Dict]:
        """
        Get current sync status for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with sync status info or None
        """
        return self.sync_status_repo.get_sync_status(ticker.upper())

    def bulk_sync(self, tickers: List[str]) -> Dict[str, SyncResult]:
        """
        Sync multiple tickers.

        Args:
            tickers: List of stock symbols

        Returns:
            Dict mapping ticker to SyncResult
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.sync_stock_data(ticker)
        return results

    def _fetch_from_vnstock(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Internal method to fetch data from vnstock API.

        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data or None on failure
        """
        try:
            df = self.vnstock_service.get_price_history(
                symbol=ticker,
                start=start_date,
                end=end_date,
                source='VCI'  # Use VCI as default source
            )

            if df is not None and not df.empty:
                logger.info(f"Fetched {len(df)} records for {ticker} from vnstock")
                return df

            return None

        except Exception as e:
            logger.error(f"Error fetching from vnstock for {ticker}: {str(e)}")
            return None

    def is_data_available(self, ticker: str) -> bool:
        """
        Check if local data is available for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            True if local data exists
        """
        return self.stock_repo.has_data_for_ticker(ticker.upper())

    def get_data_coverage(self, ticker: str) -> Optional[Dict]:
        """
        Get data coverage information for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Dict with earliest_date, latest_date, total_records
        """
        return self.stock_repo.get_date_range(ticker.upper())

    def ensure_data_available(self, ticker: str) -> SyncResult:
        """
        Ensure data is available for a ticker, syncing if necessary.
        This is a convenience method for training/prediction.

        Args:
            ticker: Stock symbol

        Returns:
            SyncResult
        """
        ticker = ticker.upper()

        # Check if we have data
        if self.is_data_available(ticker):
            # Update with latest if needed
            return self.update_latest_data(ticker)
        else:
            # No data, do full sync
            return self.sync_stock_data(ticker)
