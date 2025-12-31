"""Base Migration Script for Django to Microservices"""
import os
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import pymysql
from pymysql.cursors import DictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MigrationConfig:
    """Configuration for database migration"""
    # Source database (Django)
    source_host: str = os.getenv('SOURCE_DB_HOST', '112.213.91.103')
    source_port: int = int(os.getenv('SOURCE_DB_PORT', '3306'))
    source_user: str = os.getenv('SOURCE_DB_USER', 'root')
    source_password: str = os.getenv('SOURCE_DB_PASSWORD', 'Mysql_2025')
    source_database: str = os.getenv('SOURCE_DB_NAME', 'defaultdb')

    # Target database (Microservices - can be same or different)
    target_host: str = os.getenv('TARGET_DB_HOST', '112.213.91.103')
    target_port: int = int(os.getenv('TARGET_DB_PORT', '3306'))
    target_user: str = os.getenv('TARGET_DB_USER', 'root')
    target_password: str = os.getenv('TARGET_DB_PASSWORD', 'Mysql_2025')
    target_database: str = os.getenv('TARGET_DB_NAME', 'defaultdb')

    # Migration settings
    batch_size: int = int(os.getenv('MIGRATION_BATCH_SIZE', '1000'))
    dry_run: bool = os.getenv('MIGRATION_DRY_RUN', 'true').lower() == 'true'
    validate_only: bool = os.getenv('MIGRATION_VALIDATE_ONLY', 'false').lower() == 'true'


@dataclass
class MigrationResult:
    """Result of a migration operation"""
    success: bool = False
    table_name: str = ""
    records_processed: int = 0
    records_migrated: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    def finalize(self):
        """Finalize the result with end time and duration"""
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'table_name': self.table_name,
            'records_processed': self.records_processed,
            'records_migrated': self.records_migrated,
            'records_failed': self.records_failed,
            'errors': self.errors,
            'warnings': self.warnings,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds
        }


class BaseMigration(ABC):
    """Base class for data migrations"""

    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or MigrationConfig()
        self.source_conn = None
        self.target_conn = None
        self.results: List[MigrationResult] = []

    def connect_source(self):
        """Connect to source database"""
        self.source_conn = pymysql.connect(
            host=self.config.source_host,
            port=self.config.source_port,
            user=self.config.source_user,
            password=self.config.source_password,
            database=self.config.source_database,
            cursorclass=DictCursor,
            charset='utf8mb4'
        )
        logger.info(f"Connected to source database: {self.config.source_host}:{self.config.source_port}")

    def connect_target(self):
        """Connect to target database"""
        self.target_conn = pymysql.connect(
            host=self.config.target_host,
            port=self.config.target_port,
            user=self.config.target_user,
            password=self.config.target_password,
            database=self.config.target_database,
            cursorclass=DictCursor,
            charset='utf8mb4'
        )
        logger.info(f"Connected to target database: {self.config.target_host}:{self.config.target_port}")

    def close_connections(self):
        """Close database connections"""
        if self.source_conn:
            self.source_conn.close()
            logger.info("Closed source database connection")
        if self.target_conn:
            self.target_conn.close()
            logger.info("Closed target database connection")

    def get_table_count(self, conn, table_name: str) -> int:
        """Get count of records in a table"""
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            result = cursor.fetchone()
            return result['count'] if result else 0

    def get_table_schema(self, conn, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information"""
        with conn.cursor() as cursor:
            cursor.execute(f"DESCRIBE {table_name}")
            return cursor.fetchall()

    def compare_schemas(self, table_name: str) -> Dict[str, Any]:
        """Compare schemas between source and target"""
        source_schema = self.get_table_schema(self.source_conn, table_name)
        target_schema = self.get_table_schema(self.target_conn, table_name)

        source_fields = {s['Field']: s for s in source_schema}
        target_fields = {t['Field']: t for t in target_schema}

        missing_in_target = set(source_fields.keys()) - set(target_fields.keys())
        missing_in_source = set(target_fields.keys()) - set(source_fields.keys())
        common_fields = set(source_fields.keys()) & set(target_fields.keys())

        type_differences = []
        for field in common_fields:
            if source_fields[field]['Type'] != target_fields[field]['Type']:
                type_differences.append({
                    'field': field,
                    'source_type': source_fields[field]['Type'],
                    'target_type': target_fields[field]['Type']
                })

        return {
            'table': table_name,
            'compatible': len(missing_in_target) == 0 and len(type_differences) == 0,
            'missing_in_target': list(missing_in_target),
            'missing_in_source': list(missing_in_source),
            'type_differences': type_differences
        }

    @abstractmethod
    def get_source_tables(self) -> List[str]:
        """Get list of tables to migrate from source"""
        pass

    @abstractmethod
    def migrate_table(self, table_name: str) -> MigrationResult:
        """Migrate a single table"""
        pass

    def run(self) -> List[MigrationResult]:
        """Run the migration"""
        try:
            self.connect_source()
            if not self.config.validate_only:
                self.connect_target()

            tables = self.get_source_tables()
            logger.info(f"Found {len(tables)} tables to migrate")

            for table in tables:
                logger.info(f"Processing table: {table}")
                result = self.migrate_table(table)
                self.results.append(result)

                if result.success:
                    logger.info(
                        f"  Migrated {result.records_migrated}/{result.records_processed} records"
                    )
                else:
                    logger.error(f"  Migration failed: {result.errors}")

            return self.results

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            self.close_connections()

    def save_report(self, filepath: str):
        """Save migration report to file"""
        report = {
            'migration_date': datetime.utcnow().isoformat(),
            'config': {
                'source': f"{self.config.source_host}:{self.config.source_port}/{self.config.source_database}",
                'target': f"{self.config.target_host}:{self.config.target_port}/{self.config.target_database}",
                'batch_size': self.config.batch_size,
                'dry_run': self.config.dry_run
            },
            'results': [r.to_dict() for r in self.results],
            'summary': {
                'total_tables': len(self.results),
                'successful_tables': sum(1 for r in self.results if r.success),
                'failed_tables': sum(1 for r in self.results if not r.success),
                'total_records_processed': sum(r.records_processed for r in self.results),
                'total_records_migrated': sum(r.records_migrated for r in self.results),
                'total_records_failed': sum(r.records_failed for r in self.results)
            }
        }

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Migration report saved to: {filepath}")
