"""
Database utilities for microservices.

Provides:
- Async database connection management
- Repository base class
- Transaction management
"""

from stock_common.database.connection import (
    DatabaseManager,
    get_db_manager,
    get_async_session,
    install_stale_connection_guard,
)
from stock_common.database.repository import BaseRepository

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "get_async_session",
    "install_stale_connection_guard",
    "BaseRepository",
]
