"""
Backup Configuration

Provides comprehensive backup configurations for disaster recovery.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, time


class BackupType(Enum):
    """Types of backups"""
    FULL = "full"              # Complete backup of all data
    INCREMENTAL = "incremental"  # Changes since last backup
    DIFFERENTIAL = "differential"  # Changes since last full backup
    SNAPSHOT = "snapshot"      # Point-in-time snapshot


class BackupDestination(Enum):
    """Backup storage destinations"""
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    LOCAL = "local"
    NFS = "nfs"


class RetentionPolicy(Enum):
    """Backup retention policies"""
    DAILY_WEEKLY_MONTHLY = "daily_weekly_monthly"
    GRANDFATHER_FATHER_SON = "gfs"
    SIMPLE_DAYS = "simple_days"


@dataclass
class BackupSchedule:
    """Backup schedule configuration"""

    # Daily backup
    daily_enabled: bool = True
    daily_time: time = time(2, 0)  # 2 AM
    daily_type: BackupType = BackupType.INCREMENTAL

    # Weekly backup
    weekly_enabled: bool = True
    weekly_day: int = 0  # Sunday
    weekly_time: time = time(3, 0)  # 3 AM
    weekly_type: BackupType = BackupType.FULL

    # Monthly backup
    monthly_enabled: bool = True
    monthly_day: int = 1  # First day of month
    monthly_time: time = time(4, 0)  # 4 AM
    monthly_type: BackupType = BackupType.FULL


@dataclass
class RetentionConfig:
    """Backup retention configuration"""

    policy: RetentionPolicy = RetentionPolicy.GRANDFATHER_FATHER_SON

    # Simple retention
    retain_days: int = 30

    # GFS retention
    retain_daily: int = 7      # Keep daily backups for 7 days
    retain_weekly: int = 4     # Keep weekly backups for 4 weeks
    retain_monthly: int = 12   # Keep monthly backups for 12 months
    retain_yearly: int = 7     # Keep yearly backups for 7 years


@dataclass
class DatabaseBackupConfig:
    """Database backup configuration"""

    # Connection
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "stockhelper")
    username: str = os.getenv("DB_BACKUP_USER", "backup_user")

    # Backup options
    backup_type: BackupType = BackupType.FULL
    compression: bool = True
    compression_level: int = 6  # 1-9
    parallel_jobs: int = 4

    # WAL archiving
    enable_wal_archiving: bool = True
    wal_archive_path: str = "/var/lib/postgresql/archive"

    # Point-in-time recovery
    enable_pitr: bool = True
    pitr_target_time: Optional[datetime] = None

    # Tables to exclude (if any)
    exclude_tables: List[str] = field(default_factory=list)

    # Include schema only (no data) for specific schemas
    schema_only: List[str] = field(default_factory=list)


@dataclass
class RedisBackupConfig:
    """Redis backup configuration"""

    # Connection
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))

    # Backup options
    backup_type: str = "rdb"  # rdb, aof, or both

    # RDB settings
    rdb_save_seconds: int = 900  # Save if N seconds have passed
    rdb_save_changes: int = 1    # And at least N changes

    # AOF settings
    aof_enabled: bool = True
    aof_fsync: str = "everysec"  # always, everysec, no

    # Compression
    rdb_compression: bool = True


@dataclass
class FileBackupConfig:
    """File/object storage backup configuration"""

    # Paths to backup
    backup_paths: List[str] = field(default_factory=lambda: [
        "/app/uploads",
        "/app/logs",
        "/app/config",
    ])

    # Exclude patterns
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp",
        "*.log",
        "__pycache__",
        ".git",
    ])

    # Compression
    compression: str = "gzip"  # gzip, bzip2, lz4, none


@dataclass
class BackupDestinationConfig:
    """Backup destination configuration"""

    # Primary destination
    destination: BackupDestination = BackupDestination.S3

    # S3 configuration
    s3_bucket: str = os.getenv("BACKUP_S3_BUCKET", "")
    s3_prefix: str = os.getenv("BACKUP_S3_PREFIX", "backups/")
    s3_region: str = os.getenv("BACKUP_S3_REGION", "us-east-1")
    s3_storage_class: str = "STANDARD_IA"  # STANDARD, STANDARD_IA, GLACIER

    # GCS configuration
    gcs_bucket: str = os.getenv("BACKUP_GCS_BUCKET", "")
    gcs_prefix: str = os.getenv("BACKUP_GCS_PREFIX", "backups/")

    # Azure configuration
    azure_container: str = os.getenv("BACKUP_AZURE_CONTAINER", "")
    azure_connection_string: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")

    # Local/NFS configuration
    local_path: str = os.getenv("BACKUP_LOCAL_PATH", "/backups")

    # Encryption
    encrypt_at_rest: bool = True
    encryption_key_id: str = os.getenv("BACKUP_ENCRYPTION_KEY_ID", "")


@dataclass
class BackupConfig:
    """Main backup configuration"""

    # Enable/disable backups
    enabled: bool = True

    # Schedule
    schedule: BackupSchedule = field(default_factory=BackupSchedule)

    # Retention
    retention: RetentionConfig = field(default_factory=RetentionConfig)

    # Component configurations
    database: DatabaseBackupConfig = field(default_factory=DatabaseBackupConfig)
    redis: RedisBackupConfig = field(default_factory=RedisBackupConfig)
    files: FileBackupConfig = field(default_factory=FileBackupConfig)

    # Destination
    destination: BackupDestinationConfig = field(default_factory=BackupDestinationConfig)

    # Verification
    verify_backup: bool = True
    verification_sample_percent: int = 10

    # Notifications
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ["slack", "email"])


def get_backup_config() -> BackupConfig:
    """Get backup configuration"""
    return BackupConfig()


# Backup script generators
def generate_pg_backup_command(
    config: Optional[DatabaseBackupConfig] = None,
    output_path: str = "/tmp/backup.sql"
) -> str:
    """Generate PostgreSQL backup command"""
    config = config or DatabaseBackupConfig()

    cmd_parts = [
        "pg_dump",
        f"--host={config.host}",
        f"--port={config.port}",
        f"--username={config.username}",
        f"--dbname={config.database}",
        "--format=custom",
        f"--jobs={config.parallel_jobs}",
    ]

    if config.compression:
        cmd_parts.append(f"--compress={config.compression_level}")

    for table in config.exclude_tables:
        cmd_parts.append(f"--exclude-table={table}")

    for schema in config.schema_only:
        cmd_parts.append(f"--schema-only --schema={schema}")

    cmd_parts.append(f"--file={output_path}")

    return " ".join(cmd_parts)


def generate_pg_restore_command(
    backup_path: str,
    config: Optional[DatabaseBackupConfig] = None
) -> str:
    """Generate PostgreSQL restore command"""
    config = config or DatabaseBackupConfig()

    cmd_parts = [
        "pg_restore",
        f"--host={config.host}",
        f"--port={config.port}",
        f"--username={config.username}",
        f"--dbname={config.database}",
        f"--jobs={config.parallel_jobs}",
        "--clean",  # Drop objects before recreating
        "--if-exists",  # Don't error if objects don't exist
        backup_path,
    ]

    return " ".join(cmd_parts)


def generate_redis_backup_command(
    config: Optional[RedisBackupConfig] = None,
    output_path: str = "/tmp/dump.rdb"
) -> str:
    """Generate Redis backup command"""
    config = config or RedisBackupConfig()

    if config.backup_type == "rdb":
        return f"redis-cli -h {config.host} -p {config.port} --rdb {output_path}"
    else:
        return f"redis-cli -h {config.host} -p {config.port} BGREWRITEAOF"


def generate_s3_upload_command(
    local_path: str,
    config: Optional[BackupDestinationConfig] = None
) -> str:
    """Generate S3 upload command"""
    config = config or BackupDestinationConfig()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(local_path)
    s3_path = f"s3://{config.s3_bucket}/{config.s3_prefix}{timestamp}/{filename}"

    cmd_parts = [
        "aws s3 cp",
        local_path,
        s3_path,
        f"--storage-class {config.s3_storage_class}",
    ]

    if config.encrypt_at_rest:
        cmd_parts.append("--sse aws:kms")
        if config.encryption_key_id:
            cmd_parts.append(f"--sse-kms-key-id {config.encryption_key_id}")

    return " ".join(cmd_parts)


# Backup verification utilities
async def verify_postgres_backup(
    backup_path: str,
    config: Optional[DatabaseBackupConfig] = None
) -> Dict[str, Any]:
    """
    Verify PostgreSQL backup integrity

    Args:
        backup_path: Path to backup file
        config: Database backup configuration

    Returns:
        Verification result dict
    """
    import subprocess
    import os

    result = {
        "valid": False,
        "file_exists": os.path.exists(backup_path),
        "file_size": 0,
        "table_count": 0,
        "errors": [],
    }

    if not result["file_exists"]:
        result["errors"].append("Backup file not found")
        return result

    result["file_size"] = os.path.getsize(backup_path)

    # Verify backup format
    try:
        verify_cmd = f"pg_restore --list {backup_path}"
        output = subprocess.check_output(verify_cmd, shell=True, stderr=subprocess.STDOUT)
        lines = output.decode().strip().split("\n")
        result["table_count"] = sum(1 for line in lines if "TABLE DATA" in line)
        result["valid"] = True
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Backup verification failed: {e.output.decode()}")

    return result


def calculate_retention_date(
    backup_date: datetime,
    backup_type: str,
    config: Optional[RetentionConfig] = None
) -> datetime:
    """
    Calculate when a backup should be deleted based on retention policy

    Args:
        backup_date: When the backup was created
        backup_type: Type of backup (daily, weekly, monthly, yearly)
        config: Retention configuration

    Returns:
        Datetime when backup can be deleted
    """
    from datetime import timedelta

    config = config or RetentionConfig()

    retention_days = {
        "daily": config.retain_daily,
        "weekly": config.retain_weekly * 7,
        "monthly": config.retain_monthly * 30,
        "yearly": config.retain_yearly * 365,
    }

    days = retention_days.get(backup_type, config.retain_days)
    return backup_date + timedelta(days=days)


# Backup manifest
@dataclass
class BackupManifest:
    """Backup manifest for tracking backups"""
    backup_id: str
    backup_type: BackupType
    timestamp: datetime
    components: List[str]  # database, redis, files
    size_bytes: int
    checksum: str
    destination: str
    retention_until: datetime
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "backup_type": self.backup_type.value,
            "timestamp": self.timestamp.isoformat(),
            "components": self.components,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "destination": self.destination,
            "retention_until": self.retention_until.isoformat(),
            "verified": self.verified,
            "metadata": self.metadata,
        }
