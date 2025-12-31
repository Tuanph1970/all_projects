"""
Redis Caching Strategy Configuration

Provides comprehensive caching configurations for production services.
"""
import os
import json
import hashlib
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache invalidation strategies"""
    WRITE_THROUGH = "write_through"      # Write to cache and DB simultaneously
    WRITE_BEHIND = "write_behind"        # Write to cache, async write to DB
    WRITE_AROUND = "write_around"        # Write to DB only, invalidate cache
    READ_THROUGH = "read_through"        # Read from cache, fallback to DB
    CACHE_ASIDE = "cache_aside"          # Application manages cache explicitly


@dataclass
class CacheTTLConfig:
    """TTL configurations for different data types"""

    # User-related data
    user_session: int = 1800       # 30 minutes
    user_profile: int = 3600       # 1 hour
    user_preferences: int = 7200   # 2 hours

    # Stock data
    stock_price_realtime: int = 5      # 5 seconds for real-time
    stock_price_delayed: int = 60      # 1 minute for delayed
    stock_history: int = 3600          # 1 hour for historical
    stock_metadata: int = 86400        # 24 hours for company info

    # Portfolio data
    portfolio_summary: int = 300       # 5 minutes
    portfolio_positions: int = 60      # 1 minute
    portfolio_history: int = 3600      # 1 hour

    # Analysis/Predictions
    prediction_results: int = 900      # 15 minutes
    analysis_report: int = 1800        # 30 minutes
    ai_insights: int = 600             # 10 minutes

    # System data
    feature_flags: int = 60            # 1 minute
    config_data: int = 300             # 5 minutes
    rate_limit: int = 60               # 1 minute window


@dataclass
class CacheConfig:
    """Main cache configuration"""

    # Redis connection
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_cluster_mode: bool = os.getenv("REDIS_CLUSTER", "false").lower() == "true"

    # Cluster nodes (if cluster mode enabled)
    redis_cluster_nodes: List[str] = field(default_factory=lambda: [
        node.strip()
        for node in os.getenv("REDIS_CLUSTER_NODES", "").split(",")
        if node.strip()
    ])

    # Connection pool settings
    max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    min_connections: int = int(os.getenv("REDIS_MIN_CONNECTIONS", "10"))
    connection_timeout: int = int(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))
    socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))

    # Retry settings
    retry_on_timeout: bool = True
    max_retries: int = 3
    retry_backoff: float = 0.5

    # TTL configurations
    ttl: CacheTTLConfig = field(default_factory=CacheTTLConfig)

    # Memory management
    max_memory_policy: str = "allkeys-lru"  # Eviction policy
    max_memory_samples: int = 10            # Samples for eviction

    # Compression
    enable_compression: bool = True
    compression_threshold: int = 1024  # Compress values > 1KB

    # Key prefix per service
    service_prefixes: Dict[str, str] = field(default_factory=lambda: {
        "auth": "auth:",
        "stock-data": "stock:",
        "portfolio": "portfolio:",
        "prediction": "pred:",
        "analysis": "analysis:",
        "ai-insights": "ai:",
        "chatbot": "chat:",
        "feature-flags": "ff:",
    })


@dataclass
class RedisCacheStrategy:
    """Cache strategy implementation details"""

    # Primary strategy
    default_strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE

    # Strategy per data type
    data_strategies: Dict[str, CacheStrategy] = field(default_factory=lambda: {
        "user_session": CacheStrategy.WRITE_THROUGH,
        "stock_price": CacheStrategy.READ_THROUGH,
        "portfolio": CacheStrategy.CACHE_ASIDE,
        "prediction": CacheStrategy.CACHE_ASIDE,
        "feature_flags": CacheStrategy.WRITE_THROUGH,
    })

    # Cache warming settings
    enable_cache_warming: bool = True
    warm_on_startup: List[str] = field(default_factory=lambda: [
        "feature_flags",
        "stock_metadata",
        "config_data",
    ])

    # Invalidation settings
    enable_pattern_delete: bool = True
    invalidation_batch_size: int = 1000


def get_cache_config() -> CacheConfig:
    """Get the cache configuration singleton"""
    return CacheConfig()


def generate_cache_key(
    service: str,
    entity_type: str,
    identifier: Union[str, int, Dict],
    version: str = "v1"
) -> str:
    """
    Generate a consistent cache key

    Format: {service_prefix}{entity_type}:{version}:{identifier_hash}
    """
    config = get_cache_config()
    prefix = config.service_prefixes.get(service, f"{service}:")

    # Handle complex identifiers
    if isinstance(identifier, dict):
        # Sort keys for consistent hashing
        id_str = json.dumps(identifier, sort_keys=True)
        identifier = hashlib.md5(id_str.encode()).hexdigest()[:12]

    return f"{prefix}{entity_type}:{version}:{identifier}"


def get_ttl_for_entity(entity_type: str) -> int:
    """Get TTL for a specific entity type"""
    config = get_cache_config()
    return getattr(config.ttl, entity_type, 300)  # Default 5 minutes


# Cache patterns for common operations
class CachePatterns:
    """Common caching patterns implementation"""

    @staticmethod
    def cache_aside_get(
        cache_client,
        key: str,
        fetch_func,
        ttl: Optional[int] = None
    ):
        """
        Cache-aside pattern for reading data

        1. Check cache
        2. If miss, fetch from source
        3. Store in cache
        4. Return data
        """
        # Try cache first
        cached = cache_client.get(key)
        if cached is not None:
            return json.loads(cached) if isinstance(cached, (str, bytes)) else cached

        # Fetch from source
        data = fetch_func()
        if data is not None:
            ttl = ttl or 300
            cache_client.setex(key, ttl, json.dumps(data))

        return data

    @staticmethod
    async def cache_aside_get_async(
        cache_client,
        key: str,
        fetch_func,
        ttl: Optional[int] = None
    ):
        """Async version of cache-aside pattern"""
        cached = await cache_client.get(key)
        if cached is not None:
            return json.loads(cached) if isinstance(cached, (str, bytes)) else cached

        data = await fetch_func()
        if data is not None:
            ttl = ttl or 300
            await cache_client.setex(key, ttl, json.dumps(data))

        return data

    @staticmethod
    def write_through(
        cache_client,
        key: str,
        data: Any,
        write_func,
        ttl: int = 300
    ):
        """
        Write-through pattern

        1. Write to source
        2. Update cache
        """
        # Write to source first
        write_func(data)

        # Update cache
        cache_client.setex(key, ttl, json.dumps(data))

    @staticmethod
    async def invalidate_pattern(
        cache_client,
        pattern: str,
        batch_size: int = 1000
    ) -> int:
        """
        Invalidate all keys matching a pattern

        Returns count of deleted keys
        """
        deleted = 0
        cursor = 0

        while True:
            cursor, keys = await cache_client.scan(
                cursor=cursor,
                match=pattern,
                count=batch_size
            )

            if keys:
                deleted += await cache_client.delete(*keys)

            if cursor == 0:
                break

        return deleted


# Cache health monitoring
@dataclass
class CacheHealthMetrics:
    """Cache health and performance metrics"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    latency_ms: float = 0.0
    memory_used_bytes: int = 0
    connected_clients: int = 0
    evicted_keys: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


async def get_cache_health(cache_client) -> CacheHealthMetrics:
    """Get cache health metrics"""
    try:
        info = await cache_client.info()
        stats = await cache_client.info("stats")

        return CacheHealthMetrics(
            hits=int(stats.get("keyspace_hits", 0)),
            misses=int(stats.get("keyspace_misses", 0)),
            memory_used_bytes=int(info.get("used_memory", 0)),
            connected_clients=int(info.get("connected_clients", 0)),
            evicted_keys=int(stats.get("evicted_keys", 0)),
        )
    except Exception as e:
        logger.error(f"Failed to get cache health: {e}")
        return CacheHealthMetrics(errors=1)


# Cache warming utilities
async def warm_cache(
    cache_client,
    fetch_funcs: Dict[str, tuple],  # {key: (fetch_func, ttl)}
) -> Dict[str, bool]:
    """
    Warm cache with initial data

    Args:
        cache_client: Redis client
        fetch_funcs: Dict mapping cache keys to (fetch_func, ttl) tuples

    Returns:
        Dict mapping keys to success status
    """
    results = {}

    for key, (fetch_func, ttl) in fetch_funcs.items():
        try:
            data = await fetch_func()
            if data is not None:
                await cache_client.setex(key, ttl, json.dumps(data))
                results[key] = True
            else:
                results[key] = False
        except Exception as e:
            logger.error(f"Failed to warm cache for {key}: {e}")
            results[key] = False

    return results
