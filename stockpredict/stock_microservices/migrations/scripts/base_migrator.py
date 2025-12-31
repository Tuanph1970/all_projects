"""
Base Migration Class
Provides common functionality for all migration scripts
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker

import sys
sys.path.append('..')
from config.settings import (
    DJANGO_DB, MIGRATION_CONFIG, MigrationMode,
    DatabaseConfig
)


class MigrationStatus(Enum):
    """Status of a migration run"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationResult:
    """Result of a migration operation"""
    table_name: str
    status: MigrationStatus
    records_processed: int = 0
    records_migrated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "status": self.status.value,
            "records_processed": self.records_processed,
            "records_migrated": self.records_migrated,
            "records_skipped": self.records_skipped,
            "records_failed": self.records_failed,
            "errors": self.errors[:10],  # Limit errors in output
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class MigrationCheckpoint:
    """Checkpoint for resumable migrations"""
    migration_id: str
    table_name: str
    last_processed_id: int
    records_processed: int
    created_at: datetime = field(default_factory=datetime.utcnow)


class BaseMigrator(ABC):
    """
    Base class for all migration scripts.
    Provides common functionality for data migration.
    """

    def __init__(
        self,
        source_db: DatabaseConfig = DJANGO_DB,
        target_db: DatabaseConfig = None,
        mode: MigrationMode = MigrationMode.DRY_RUN,
        batch_size: int = None,
        logger: logging.Logger = None
    ):
        self.source_db = source_db
        self.target_db = target_db
        self.mode = mode
        self.batch_size = batch_size or MIGRATION_CONFIG["batch_size"]
        self.logger = logger or self._setup_logger()

        # Engines will be created lazily
        self._source_engine = None
        self._target_engine = None

        # Migration state
        self.result = MigrationResult(
            table_name=self.table_name,
            status=MigrationStatus.PENDING
        )
        self.checkpoints: List[MigrationCheckpoint] = []

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Source table name in Django database"""
        pass

    @property
    @abstractmethod
    def target_table_name(self) -> str:
        """Target table name in microservice database"""
        pass

    @abstractmethod
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a source record to target format"""
        pass

    @abstractmethod
    def get_insert_query(self) -> str:
        """Get the INSERT query for the target table"""
        pass

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for this migrator"""
        logger = logging.getLogger(f"migration.{self.table_name}")
        logger.setLevel(MIGRATION_CONFIG["log_level"])

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    @property
    def source_engine(self):
        """Lazy initialization of source database engine"""
        if self._source_engine is None:
            self._source_engine = create_engine(
                self.source_db.connection_string,
                pool_pre_ping=True,
                pool_size=5
            )
        return self._source_engine

    @property
    def target_engine(self):
        """Lazy initialization of target database engine"""
        if self._target_engine is None and self.target_db:
            self._target_engine = create_engine(
                self.target_db.connection_string,
                pool_pre_ping=True,
                pool_size=5
            )
        return self._target_engine

    def get_source_count(self) -> int:
        """Get total count of records in source table"""
        with self.source_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {self.table_name}"))
            return result.scalar()

    def get_target_count(self) -> int:
        """Get total count of records in target table"""
        if not self.target_engine:
            return 0
        with self.target_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {self.target_table_name}"))
            return result.scalar()

    def fetch_batch(
        self,
        offset: int = 0,
        limit: int = None,
        where_clause: str = None
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of records from the source table"""
        limit = limit or self.batch_size
        query = f"SELECT * FROM {self.table_name}"

        if where_clause:
            query += f" WHERE {where_clause}"

        query += f" ORDER BY id LIMIT {limit} OFFSET {offset}"

        with self.source_engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row._mapping) for row in result]

    def insert_batch(self, records: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """Insert a batch of records into the target table"""
        if self.mode == MigrationMode.DRY_RUN:
            self.logger.info(f"[DRY RUN] Would insert {len(records)} records")
            return len(records), []

        if not self.target_engine:
            raise ValueError("Target database not configured")

        errors = []
        inserted = 0
        insert_query = self.get_insert_query()

        with self.target_engine.connect() as conn:
            for record in records:
                try:
                    transformed = self.transform_record(record)
                    conn.execute(text(insert_query), transformed)
                    inserted += 1
                except Exception as e:
                    errors.append(f"Record {record.get('id', 'unknown')}: {str(e)}")
                    self.logger.warning(f"Failed to insert record: {e}")

            conn.commit()

        return inserted, errors

    def save_checkpoint(self, last_id: int, records_processed: int):
        """Save a checkpoint for resumable migration"""
        if not MIGRATION_CONFIG["checkpoint_enabled"]:
            return

        checkpoint = MigrationCheckpoint(
            migration_id=f"{self.table_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            table_name=self.table_name,
            last_processed_id=last_id,
            records_processed=records_processed
        )
        self.checkpoints.append(checkpoint)

        # Save to file for persistence
        checkpoint_file = f"/tmp/migration_checkpoint_{self.table_name}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({
                "migration_id": checkpoint.migration_id,
                "table_name": checkpoint.table_name,
                "last_processed_id": checkpoint.last_processed_id,
                "records_processed": checkpoint.records_processed,
                "created_at": checkpoint.created_at.isoformat()
            }, f)

        self.logger.debug(f"Checkpoint saved: {checkpoint.migration_id}")

    def load_checkpoint(self) -> Optional[MigrationCheckpoint]:
        """Load the last checkpoint for this table"""
        checkpoint_file = f"/tmp/migration_checkpoint_{self.table_name}.json"
        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
                return MigrationCheckpoint(
                    migration_id=data["migration_id"],
                    table_name=data["table_name"],
                    last_processed_id=data["last_processed_id"],
                    records_processed=data["records_processed"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
        except FileNotFoundError:
            return None

    def run(self, resume: bool = False) -> MigrationResult:
        """Execute the migration"""
        self.result.started_at = datetime.utcnow()
        self.result.status = MigrationStatus.RUNNING

        try:
            self.logger.info(f"Starting migration for {self.table_name}")
            self.logger.info(f"Mode: {self.mode.value}")

            # Get counts
            source_count = self.get_source_count()
            self.logger.info(f"Source records: {source_count}")

            if self.target_db:
                target_count = self.get_target_count()
                self.logger.info(f"Existing target records: {target_count}")

            # Check for resume
            offset = 0
            if resume:
                checkpoint = self.load_checkpoint()
                if checkpoint:
                    offset = checkpoint.records_processed
                    self.logger.info(f"Resuming from checkpoint: {offset} records")

            # Process in batches
            while offset < source_count:
                batch = self.fetch_batch(offset=offset)
                if not batch:
                    break

                self.result.records_processed += len(batch)

                # Insert batch
                inserted, errors = self.insert_batch(batch)
                self.result.records_migrated += inserted
                self.result.records_failed += len(errors)
                self.result.errors.extend(errors)

                offset += len(batch)

                # Save checkpoint
                if batch and offset % (self.batch_size * MIGRATION_CONFIG["checkpoint_interval"]) == 0:
                    last_id = batch[-1].get("id", 0)
                    self.save_checkpoint(last_id, offset)

                self.logger.info(
                    f"Progress: {offset}/{source_count} "
                    f"({(offset/source_count)*100:.1f}%)"
                )

            self.result.status = MigrationStatus.COMPLETED
            self.logger.info(f"Migration completed for {self.table_name}")

        except Exception as e:
            self.result.status = MigrationStatus.FAILED
            self.result.errors.append(str(e))
            self.logger.error(f"Migration failed: {e}", exc_info=True)

        finally:
            self.result.completed_at = datetime.utcnow()
            self.result.duration_seconds = (
                self.result.completed_at - self.result.started_at
            ).total_seconds()

            # Close engines
            if self._source_engine:
                self._source_engine.dispose()
            if self._target_engine:
                self._target_engine.dispose()

        return self.result

    def verify(self) -> Dict[str, Any]:
        """Verify migration completeness"""
        source_count = self.get_source_count()
        target_count = self.get_target_count() if self.target_db else 0

        return {
            "table": self.table_name,
            "source_count": source_count,
            "target_count": target_count,
            "match": source_count == target_count,
            "difference": source_count - target_count,
            "verified_at": datetime.utcnow().isoformat()
        }

    def rollback(self) -> bool:
        """Rollback the migration (delete migrated records)"""
        if self.mode == MigrationMode.DRY_RUN:
            self.logger.info("[DRY RUN] Would rollback migration")
            return True

        if not self.target_engine:
            self.logger.error("Cannot rollback: no target database")
            return False

        try:
            with self.target_engine.connect() as conn:
                # Delete records with legacy_id (migrated records)
                conn.execute(text(
                    f"DELETE FROM {self.target_table_name} WHERE legacy_id IS NOT NULL"
                ))
                conn.commit()

            self.result.status = MigrationStatus.ROLLED_BACK
            self.logger.info(f"Rollback completed for {self.table_name}")
            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
