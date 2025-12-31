"""
Redis Cache Utility for Ceramic Marketplace
Provides caching layer for improved performance
"""
import redis
import json
import hashlib
import logging
from typing import Optional, Any, Callable, Union
from functools import wraps
from datetime import timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client with connection pooling and utilities"""

    _instance: Optional['RedisCache'] = None
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """Initialize Redis connection pool"""
        try:
            self._pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                max_connections=20,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            self._client = redis.Redis(connection_pool=self._pool)
            # Test connection
            self._client.ping()
            logger.info(f"Redis connected successfully to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
            self._client = None
        except Exception as e:
            logger.warning(f"Redis initialization error: {e}. Caching will be disabled.")
            self._client = None

    @property
    def client(self) -> Optional[redis.Redis]:
        """Get Redis client"""
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.is_available:
            return None
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            return value
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
        """
        if not self.is_available:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if nx:
                return self._client.setnx(key, serialized)
            if ttl:
                return self._client.setex(key, ttl, serialized)
            return self._client.set(key, serialized)
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.is_available:
            return False
        try:
            return self._client.delete(key) > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.is_available:
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.is_available:
            return False
        try:
            return self._client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self.is_available:
            return None
        try:
            return self._client.incr(key, amount)
        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key"""
        if not self.is_available:
            return False
        try:
            return self._client.expire(key, ttl)
        except Exception as e:
            logger.warning(f"Cache expire error for key {key}: {e}")
            return False

    def ttl(self, key: str) -> int:
        """Get remaining TTL for a key"""
        if not self.is_available:
            return -2
        try:
            return self._client.ttl(key)
        except Exception as e:
            logger.warning(f"Cache ttl error for key {key}: {e}")
            return -2

    def flush_all(self) -> bool:
        """Flush all keys (use with caution)"""
        if not self.is_available:
            return False
        try:
            self._client.flushdb()
            return True
        except Exception as e:
            logger.warning(f"Cache flush error: {e}")
            return False

    def health_check(self) -> dict:
        """Get cache health status"""
        if not self.is_available:
            return {"status": "unavailable", "message": "Redis not connected"}
        try:
            info = self._client.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "total_keys": self._client.dbsize()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Singleton cache instance
cache = RedisCache()


# Cache key generators
class CacheKeys:
    """Cache key generators for different entities"""

    PREFIX = "ceramic"

    @staticmethod
    def products_list(skip: int, limit: int, **filters) -> str:
        """Generate cache key for product listings"""
        filter_hash = hashlib.md5(
            json.dumps(filters, sort_keys=True, default=str).encode()
        ).hexdigest()[:8]
        return f"{CacheKeys.PREFIX}:products:list:{skip}:{limit}:{filter_hash}"

    @staticmethod
    def product_detail(product_id: int) -> str:
        """Generate cache key for product detail"""
        return f"{CacheKeys.PREFIX}:products:detail:{product_id}"

    @staticmethod
    def categories() -> str:
        """Generate cache key for categories"""
        return f"{CacheKeys.PREFIX}:categories:all"

    @staticmethod
    def category_tree() -> str:
        """Generate cache key for category tree"""
        return f"{CacheKeys.PREFIX}:categories:tree"

    @staticmethod
    def featured_products(category_id: Optional[int] = None) -> str:
        """Generate cache key for featured products"""
        if category_id:
            return f"{CacheKeys.PREFIX}:products:featured:{category_id}"
        return f"{CacheKeys.PREFIX}:products:featured:all"

    @staticmethod
    def trending_products(days: int) -> str:
        """Generate cache key for trending products"""
        return f"{CacheKeys.PREFIX}:products:trending:{days}"

    @staticmethod
    def home_featured() -> str:
        """Generate cache key for home featured data"""
        return f"{CacheKeys.PREFIX}:home:featured"

    @staticmethod
    def catalog_stats() -> str:
        """Generate cache key for catalog stats"""
        return f"{CacheKeys.PREFIX}:stats:catalog"

    @staticmethod
    def filter_options(category_id: Optional[int] = None) -> str:
        """Generate cache key for filter options"""
        if category_id:
            return f"{CacheKeys.PREFIX}:filters:options:{category_id}"
        return f"{CacheKeys.PREFIX}:filters:options:all"

    @staticmethod
    def category_showcase(category_id: int) -> str:
        """Generate cache key for category showcase"""
        return f"{CacheKeys.PREFIX}:categories:showcase:{category_id}"

    @staticmethod
    def similar_products(product_id: int) -> str:
        """Generate cache key for similar products"""
        return f"{CacheKeys.PREFIX}:products:similar:{product_id}"

    @staticmethod
    def related_products(product_id: int) -> str:
        """Generate cache key for related products"""
        return f"{CacheKeys.PREFIX}:products:related:{product_id}"


# Cache invalidation helpers
class CacheInvalidation:
    """Cache invalidation utilities"""

    @staticmethod
    def invalidate_product(product_id: int):
        """Invalidate all caches related to a product"""
        cache.delete(CacheKeys.product_detail(product_id))
        cache.delete(CacheKeys.similar_products(product_id))
        cache.delete(CacheKeys.related_products(product_id))
        # Invalidate list caches
        cache.delete_pattern(f"{CacheKeys.PREFIX}:products:list:*")
        cache.delete_pattern(f"{CacheKeys.PREFIX}:products:featured:*")
        cache.delete_pattern(f"{CacheKeys.PREFIX}:products:trending:*")
        cache.delete(CacheKeys.home_featured())
        cache.delete(CacheKeys.catalog_stats())

    @staticmethod
    def invalidate_category(category_id: int):
        """Invalidate all caches related to a category"""
        cache.delete(CacheKeys.categories())
        cache.delete(CacheKeys.category_tree())
        cache.delete(CacheKeys.category_showcase(category_id))
        cache.delete(CacheKeys.filter_options(category_id))
        cache.delete(CacheKeys.featured_products(category_id))
        cache.delete(CacheKeys.home_featured())

    @staticmethod
    def invalidate_all_products():
        """Invalidate all product-related caches"""
        cache.delete_pattern(f"{CacheKeys.PREFIX}:products:*")
        cache.delete(CacheKeys.home_featured())
        cache.delete(CacheKeys.catalog_stats())

    @staticmethod
    def invalidate_all():
        """Invalidate entire cache"""
        cache.delete_pattern(f"{CacheKeys.PREFIX}:*")


def cached(
    ttl: int = 300,
    key_func: Optional[Callable] = None,
    prefix: str = ""
):
    """
    Decorator for caching function results

    Args:
        ttl: Cache TTL in seconds
        key_func: Function to generate cache key from args/kwargs
        prefix: Additional prefix for cache key

    Usage:
        @cached(ttl=300, prefix="products")
        def get_products(skip, limit):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip cache if Redis not available
            if not cache.is_available:
                return func(*args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [CacheKeys.PREFIX, prefix or func.__name__]
                key_parts.extend(str(arg) for arg in args if not hasattr(arg, '__dict__'))
                key_parts.append(
                    hashlib.md5(
                        json.dumps(kwargs, sort_keys=True, default=str).encode()
                    ).hexdigest()[:8]
                )
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            # Execute function and cache result
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            if result is not None:
                cache.set(cache_key, result, ttl=ttl)

            return result

        # Add cache control methods to wrapper
        wrapper.cache_clear = lambda: cache.delete_pattern(f"{CacheKeys.PREFIX}:{prefix or func.__name__}:*")

        return wrapper
    return decorator


# Rate limiting helper
class RateLimiter:
    """Simple rate limiter using Redis"""

    def __init__(self, key_prefix: str = "ratelimit"):
        self.key_prefix = f"{CacheKeys.PREFIX}:{key_prefix}"

    def is_allowed(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit

        Returns:
            (is_allowed, remaining_requests)
        """
        if not cache.is_available:
            return True, max_requests

        key = f"{self.key_prefix}:{identifier}"

        try:
            current = cache.increment(key)
            if current == 1:
                cache.expire(key, window_seconds)

            remaining = max(0, max_requests - current)
            return current <= max_requests, remaining
        except:
            return True, max_requests

    def get_retry_after(self, identifier: str) -> int:
        """Get seconds until rate limit resets"""
        if not cache.is_available:
            return 0
        key = f"{self.key_prefix}:{identifier}"
        return max(0, cache.ttl(key))


# Default rate limiter instance
rate_limiter = RateLimiter()
