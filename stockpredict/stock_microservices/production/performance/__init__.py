"""
Performance Optimization Module

This module provides performance optimization configurations and utilities
for production deployment of the microservices.
"""

from .database_config import (
    DatabasePoolConfig,
    get_database_pool_config,
    create_async_engine_with_pool,
)
from .cache_config import (
    CacheConfig,
    RedisCacheStrategy,
    get_cache_config,
)
from .compression_config import (
    CompressionConfig,
    get_compression_middleware,
)
from .resource_config import (
    ResourceLimits,
    AutoScalingConfig,
    get_resource_config,
)

__all__ = [
    "DatabasePoolConfig",
    "get_database_pool_config",
    "create_async_engine_with_pool",
    "CacheConfig",
    "RedisCacheStrategy",
    "get_cache_config",
    "CompressionConfig",
    "get_compression_middleware",
    "ResourceLimits",
    "AutoScalingConfig",
    "get_resource_config",
]
