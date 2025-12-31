"""
Database Connection Pooling Configuration

Provides optimized database connection pool settings for production.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import QueuePool, NullPool


@dataclass
class DatabasePoolConfig:
    """Database connection pool configuration"""

    # Pool sizing
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "20"))
    max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
    pool_pre_ping: bool = True  # Enable connection health checks

    # Connection settings
    connect_timeout: int = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
    command_timeout: int = int(os.getenv("DB_COMMAND_TIMEOUT", "30"))

    # Query optimization
    echo_pool: bool = os.getenv("DB_ECHO_POOL", "false").lower() == "true"
    query_cache_size: int = int(os.getenv("DB_QUERY_CACHE_SIZE", "500"))

    # Replica settings for read scaling
    use_read_replica: bool = os.getenv("DB_USE_READ_REPLICA", "false").lower() == "true"
    read_replica_url: Optional[str] = os.getenv("DB_READ_REPLICA_URL")

    # Service-specific overrides
    service_pool_sizes: Dict[str, int] = field(default_factory=lambda: {
        "auth": 15,           # Lower - auth is quick
        "stock-data": 30,     # Higher - heavy read operations
        "portfolio": 20,      # Medium - mixed read/write
        "prediction": 25,     # Higher - ML queries can be slow
        "analysis": 25,       # Higher - complex aggregations
        "ai-insights": 15,    # Lower - mostly external API calls
        "chatbot": 10,        # Lower - mostly stateless
    })


@dataclass
class QueryOptimizationConfig:
    """Query optimization settings"""

    # Statement caching
    prepared_statement_cache_size: int = 100

    # Batch settings
    batch_insert_size: int = 1000
    batch_select_size: int = 5000

    # Timeout settings
    statement_timeout_ms: int = 30000  # 30 seconds
    lock_timeout_ms: int = 10000  # 10 seconds

    # Index hints
    enable_index_hints: bool = True

    # Query plan caching (PostgreSQL)
    plan_cache_mode: str = "auto"  # auto, force_generic_plan, force_custom_plan


@dataclass
class PostgresOptimizations:
    """PostgreSQL-specific optimizations"""

    # Connection parameters
    work_mem: str = "64MB"
    maintenance_work_mem: str = "256MB"
    effective_cache_size: str = "4GB"

    # Parallel query settings
    max_parallel_workers_per_gather: int = 2
    parallel_tuple_cost: float = 0.01

    # JIT compilation
    jit: bool = True
    jit_above_cost: int = 100000

    # Logging for slow queries
    log_min_duration_statement: int = 1000  # Log queries > 1s

    def get_connection_args(self) -> Dict[str, Any]:
        """Get connection arguments for SQLAlchemy"""
        return {
            "options": (
                f"-c work_mem={self.work_mem} "
                f"-c maintenance_work_mem={self.maintenance_work_mem} "
                f"-c jit={'on' if self.jit else 'off'}"
            )
        }


@lru_cache()
def get_database_pool_config() -> DatabasePoolConfig:
    """Get the database pool configuration singleton"""
    return DatabasePoolConfig()


def get_pool_size_for_service(service_name: str) -> int:
    """Get optimal pool size for a specific service"""
    config = get_database_pool_config()
    return config.service_pool_sizes.get(
        service_name,
        config.pool_size
    )


def create_async_engine_with_pool(
    database_url: str,
    service_name: Optional[str] = None,
    use_null_pool: bool = False,
) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine with optimized pool settings

    Args:
        database_url: Database connection URL
        service_name: Optional service name for service-specific pool sizes
        use_null_pool: Use NullPool for serverless environments
    """
    config = get_database_pool_config()

    # Get service-specific pool size
    pool_size = (
        get_pool_size_for_service(service_name)
        if service_name
        else config.pool_size
    )

    # Base engine arguments
    engine_args = {
        "echo": config.echo_pool,
        "pool_pre_ping": config.pool_pre_ping,
    }

    if use_null_pool:
        # For serverless environments (Lambda, Cloud Functions)
        engine_args["poolclass"] = NullPool
    else:
        # Standard connection pooling
        engine_args.update({
            "poolclass": QueuePool,
            "pool_size": pool_size,
            "max_overflow": config.max_overflow,
            "pool_timeout": config.pool_timeout,
            "pool_recycle": config.pool_recycle,
        })

    # Convert sync URL to async if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+asyncpg://"
        )

    return create_async_engine(database_url, **engine_args)


def create_read_replica_engine(
    service_name: Optional[str] = None
) -> Optional[AsyncEngine]:
    """Create engine for read replica if configured"""
    config = get_database_pool_config()

    if not config.use_read_replica or not config.read_replica_url:
        return None

    return create_async_engine_with_pool(
        config.read_replica_url,
        service_name=service_name,
    )


# Connection health check utilities
async def check_connection_health(engine: AsyncEngine) -> Dict[str, Any]:
    """Check database connection health and pool status"""
    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0,
        "healthy": pool.checkedout() < pool.size() + pool.overflow(),
    }


# Query optimization utilities
def optimize_bulk_insert_query(
    table_name: str,
    columns: list,
    values_count: int,
    batch_size: int = 1000
) -> list:
    """
    Generate optimized bulk insert queries with batching

    Returns list of (query, batch_start, batch_end) tuples
    """
    batches = []
    for start in range(0, values_count, batch_size):
        end = min(start + batch_size, values_count)
        placeholders = ", ".join(
            f"({', '.join([f'${i*len(columns)+j+1}' for j in range(len(columns))])})"
            for i in range(end - start)
        )
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES {placeholders}"
        batches.append((query, start, end))

    return batches
