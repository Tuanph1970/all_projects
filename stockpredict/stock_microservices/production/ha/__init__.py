"""
High Availability Configuration Module

This module provides high availability configurations and utilities
for production deployment of the microservices.
"""

from .health_checks import (
    HealthCheckConfig,
    HealthStatus,
    ServiceHealth,
    check_service_health,
)
from .load_balancer import (
    LoadBalancerConfig,
    HealthCheckPolicy,
)
from .failover import (
    FailoverConfig,
    CircuitBreakerConfig,
    RetryConfig,
)
from .replication import (
    ReplicationConfig,
    DatabaseReplicationConfig,
    CacheReplicationConfig,
)

__all__ = [
    "HealthCheckConfig",
    "HealthStatus",
    "ServiceHealth",
    "check_service_health",
    "LoadBalancerConfig",
    "HealthCheckPolicy",
    "FailoverConfig",
    "CircuitBreakerConfig",
    "RetryConfig",
    "ReplicationConfig",
    "DatabaseReplicationConfig",
    "CacheReplicationConfig",
]
