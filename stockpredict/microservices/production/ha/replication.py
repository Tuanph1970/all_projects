"""
Replication Configuration

Provides database and cache replication configurations for high availability.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ReplicationMode(Enum):
    """Replication modes"""
    SYNC = "synchronous"      # Wait for all replicas
    ASYNC = "asynchronous"    # Don't wait for replicas
    SEMI_SYNC = "semi_sync"   # Wait for at least one replica


class FailoverPolicy(Enum):
    """Failover policies"""
    AUTOMATIC = "automatic"   # Automatic failover
    MANUAL = "manual"         # Requires manual intervention
    GUIDED = "guided"         # Automatic with approval


@dataclass
class ReplicaConfig:
    """Individual replica configuration"""
    host: str
    port: int
    priority: int = 100      # Higher = preferred for promotion
    read_only: bool = True
    region: str = "default"
    availability_zone: str = "default"


@dataclass
class DatabaseReplicationConfig:
    """PostgreSQL replication configuration"""

    # Primary settings
    primary_host: str = os.getenv("DB_PRIMARY_HOST", "localhost")
    primary_port: int = int(os.getenv("DB_PRIMARY_PORT", "5432"))

    # Replication mode
    replication_mode: ReplicationMode = ReplicationMode.ASYNC

    # Replica configuration
    replicas: List[ReplicaConfig] = field(default_factory=list)

    # Replication settings
    max_wal_senders: int = 10
    wal_keep_size: str = "1GB"
    max_replication_slots: int = 10

    # Synchronous replication settings (when mode is SYNC or SEMI_SYNC)
    synchronous_commit: str = "on"
    synchronous_standby_names: str = "FIRST 1 (*)"

    # Failover settings
    failover_policy: FailoverPolicy = FailoverPolicy.AUTOMATIC
    failover_timeout_seconds: int = 30
    promotion_timeout_seconds: int = 60

    # Health check
    health_check_interval_seconds: int = 10
    health_check_timeout_seconds: int = 5
    max_lag_bytes: int = 100 * 1024 * 1024  # 100MB max lag

    # Connection pooling for replicas
    replica_pool_size: int = 10
    replica_max_overflow: int = 5


@dataclass
class CacheReplicationConfig:
    """Redis replication configuration"""

    # Master settings
    master_host: str = os.getenv("REDIS_MASTER_HOST", "localhost")
    master_port: int = int(os.getenv("REDIS_MASTER_PORT", "6379"))

    # Sentinel configuration (for automatic failover)
    use_sentinel: bool = os.getenv("REDIS_USE_SENTINEL", "false").lower() == "true"
    sentinel_hosts: List[str] = field(default_factory=lambda: [
        host.strip()
        for host in os.getenv("REDIS_SENTINEL_HOSTS", "").split(",")
        if host.strip()
    ])
    sentinel_master_name: str = os.getenv("REDIS_SENTINEL_MASTER", "mymaster")
    sentinel_password: Optional[str] = os.getenv("REDIS_SENTINEL_PASSWORD")

    # Replica configuration
    replicas: List[ReplicaConfig] = field(default_factory=list)

    # Replication settings
    repl_diskless_sync: bool = True
    repl_diskless_sync_delay: int = 5
    min_replicas_to_write: int = 1
    min_replicas_max_lag: int = 10

    # Cluster mode
    cluster_enabled: bool = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
    cluster_nodes: List[str] = field(default_factory=list)
    cluster_require_full_coverage: bool = True

    # Persistence
    appendonly: bool = True
    appendfsync: str = "everysec"  # everysec, always, no

    # Memory management
    maxmemory_policy: str = "allkeys-lru"


@dataclass
class ReplicationConfig:
    """Combined replication configuration"""
    database: DatabaseReplicationConfig = field(default_factory=DatabaseReplicationConfig)
    cache: CacheReplicationConfig = field(default_factory=CacheReplicationConfig)


def get_replication_config() -> ReplicationConfig:
    """Get replication configuration"""
    return ReplicationConfig()


# PostgreSQL replication configuration generators
def generate_postgres_primary_config(
    config: Optional[DatabaseReplicationConfig] = None
) -> Dict[str, str]:
    """Generate PostgreSQL primary configuration parameters"""
    config = config or DatabaseReplicationConfig()

    params = {
        # Replication
        "wal_level": "replica",
        "max_wal_senders": str(config.max_wal_senders),
        "wal_keep_size": config.wal_keep_size,
        "max_replication_slots": str(config.max_replication_slots),

        # Archiving (for point-in-time recovery)
        "archive_mode": "on",
        "archive_command": "cp %p /var/lib/postgresql/archive/%f",

        # Logging
        "log_replication_commands": "on",
    }

    # Synchronous replication settings
    if config.replication_mode in [ReplicationMode.SYNC, ReplicationMode.SEMI_SYNC]:
        params["synchronous_commit"] = config.synchronous_commit
        params["synchronous_standby_names"] = config.synchronous_standby_names

    return params


def generate_postgres_replica_config(
    primary_host: str,
    primary_port: int,
    config: Optional[DatabaseReplicationConfig] = None
) -> Dict[str, str]:
    """Generate PostgreSQL replica configuration parameters"""
    config = config or DatabaseReplicationConfig()

    return {
        # Recovery settings
        "primary_conninfo": f"host={primary_host} port={primary_port} user=replicator password=$REPLICATION_PASSWORD",
        "hot_standby": "on",
        "hot_standby_feedback": "on",

        # Recovery target (for streaming replication)
        "recovery_target_timeline": "latest",

        # Read-only by default
        "default_transaction_read_only": "on",

        # Promote settings
        "promote_trigger_file": "/tmp/promote_to_primary",
    }


def generate_pg_hba_replication_entries(
    replicas: List[ReplicaConfig]
) -> List[str]:
    """Generate pg_hba.conf entries for replication"""
    entries = [
        "# Replication connections",
        "host replication replicator 0.0.0.0/0 scram-sha-256",
    ]

    for replica in replicas:
        entries.append(
            f"host replication replicator {replica.host}/32 scram-sha-256"
        )

    return entries


# Redis replication configuration generators
def generate_redis_master_config(
    config: Optional[CacheReplicationConfig] = None
) -> Dict[str, str]:
    """Generate Redis master configuration"""
    config = config or CacheReplicationConfig()

    params = {
        # Replication
        "repl-diskless-sync": "yes" if config.repl_diskless_sync else "no",
        "repl-diskless-sync-delay": str(config.repl_diskless_sync_delay),

        # Minimum replicas
        "min-replicas-to-write": str(config.min_replicas_to_write),
        "min-replicas-max-lag": str(config.min_replicas_max_lag),

        # Persistence
        "appendonly": "yes" if config.appendonly else "no",
        "appendfsync": config.appendfsync,

        # Memory
        "maxmemory-policy": config.maxmemory_policy,
    }

    return params


def generate_redis_replica_config(
    master_host: str,
    master_port: int,
    config: Optional[CacheReplicationConfig] = None
) -> Dict[str, str]:
    """Generate Redis replica configuration"""
    config = config or CacheReplicationConfig()

    return {
        "replicaof": f"{master_host} {master_port}",
        "replica-read-only": "yes",
        "replica-serve-stale-data": "yes",

        # Persistence
        "appendonly": "yes" if config.appendonly else "no",
        "appendfsync": config.appendfsync,

        # Memory
        "maxmemory-policy": config.maxmemory_policy,
    }


def generate_redis_sentinel_config(
    master_name: str,
    master_host: str,
    master_port: int,
    quorum: int = 2,
    config: Optional[CacheReplicationConfig] = None
) -> Dict[str, str]:
    """Generate Redis Sentinel configuration"""
    config = config or CacheReplicationConfig()

    return {
        f"sentinel monitor {master_name}": f"{master_host} {master_port} {quorum}",
        f"sentinel down-after-milliseconds {master_name}": "30000",
        f"sentinel parallel-syncs {master_name}": "1",
        f"sentinel failover-timeout {master_name}": "180000",
    }


# Connection string generators
def get_primary_connection_string(
    database: str = "stockhelper",
    config: Optional[DatabaseReplicationConfig] = None
) -> str:
    """Get connection string for primary database"""
    config = config or DatabaseReplicationConfig()
    password = os.getenv("DB_PASSWORD", "")

    return (
        f"postgresql://app:{password}@"
        f"{config.primary_host}:{config.primary_port}/{database}"
    )


def get_replica_connection_strings(
    database: str = "stockhelper",
    config: Optional[DatabaseReplicationConfig] = None
) -> List[str]:
    """Get connection strings for all read replicas"""
    config = config or DatabaseReplicationConfig()
    password = os.getenv("DB_PASSWORD", "")

    return [
        f"postgresql://app:{password}@{replica.host}:{replica.port}/{database}"
        for replica in config.replicas
    ]


def get_redis_connection_url(
    config: Optional[CacheReplicationConfig] = None
) -> str:
    """Get Redis connection URL"""
    config = config or CacheReplicationConfig()
    password = os.getenv("REDIS_PASSWORD", "")

    if config.use_sentinel:
        # Sentinel connection format
        sentinel_hosts = ",".join(config.sentinel_hosts)
        return f"redis+sentinel://{sentinel_hosts}/{config.sentinel_master_name}"

    if config.cluster_enabled:
        # Cluster connection format
        return f"redis://{config.master_host}:{config.master_port}?cluster=true"

    # Standard connection
    if password:
        return f"redis://:{password}@{config.master_host}:{config.master_port}"
    return f"redis://{config.master_host}:{config.master_port}"


# Health monitoring utilities
@dataclass
class ReplicationLag:
    """Replication lag information"""
    replica_host: str
    lag_bytes: int
    lag_seconds: float
    is_healthy: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "replica": self.replica_host,
            "lag_bytes": self.lag_bytes,
            "lag_seconds": self.lag_seconds,
            "healthy": self.is_healthy,
        }


async def check_postgres_replication_lag(
    primary_conn,
    config: Optional[DatabaseReplicationConfig] = None
) -> List[ReplicationLag]:
    """
    Check replication lag for all PostgreSQL replicas

    Args:
        primary_conn: AsyncPG connection to primary
        config: Replication configuration

    Returns:
        List of ReplicationLag objects
    """
    config = config or DatabaseReplicationConfig()

    query = """
        SELECT
            client_addr,
            sent_lsn - replay_lsn AS lag_bytes,
            EXTRACT(EPOCH FROM (now() - replay_lag)) AS lag_seconds
        FROM pg_stat_replication
    """

    rows = await primary_conn.fetch(query)

    return [
        ReplicationLag(
            replica_host=str(row["client_addr"]),
            lag_bytes=row["lag_bytes"] or 0,
            lag_seconds=row["lag_seconds"] or 0,
            is_healthy=(row["lag_bytes"] or 0) < config.max_lag_bytes,
        )
        for row in rows
    ]


async def check_redis_replication_lag(
    redis_client,
    config: Optional[CacheReplicationConfig] = None
) -> List[ReplicationLag]:
    """
    Check replication lag for Redis replicas

    Args:
        redis_client: Redis client connected to master
        config: Replication configuration

    Returns:
        List of ReplicationLag objects
    """
    config = config or CacheReplicationConfig()

    info = await redis_client.info("replication")
    lags = []

    # Parse connected slaves
    for key, value in info.items():
        if key.startswith("slave"):
            parts = value.split(",")
            slave_info = {p.split("=")[0]: p.split("=")[1] for p in parts if "=" in p}

            lag_bytes = int(slave_info.get("lag", 0))
            lags.append(ReplicationLag(
                replica_host=slave_info.get("ip", "unknown"),
                lag_bytes=lag_bytes,
                lag_seconds=lag_bytes / 1000000,  # Approximate
                is_healthy=lag_bytes < config.min_replicas_max_lag * 1000000,
            ))

    return lags
