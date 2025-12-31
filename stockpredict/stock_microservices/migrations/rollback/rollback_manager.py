"""Rollback Manager for Migrations"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import pymysql
from pymysql.cursors import DictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RollbackCheckpoint:
    """Represents a rollback checkpoint"""
    id: str
    created_at: datetime
    tables_affected: List[str] = field(default_factory=list)
    record_counts: Dict[str, int] = field(default_factory=dict)
    backup_file: Optional[str] = None
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'tables_affected': self.tables_affected,
            'record_counts': self.record_counts,
            'backup_file': self.backup_file,
            'status': self.status
        }


class RollbackManager:
    """Manages rollback operations for migrations"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        checkpoint_dir: str = None
    ):
        self.db_config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'cursorclass': DictCursor,
            'charset': 'utf8mb4'
        }
        self.checkpoint_dir = checkpoint_dir or os.path.join(
            os.path.dirname(__file__), '..', 'checkpoints'
        )
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.conn = None

    def connect(self):
        """Connect to database"""
        self.conn = pymysql.connect(**self.db_config)
        logger.info(f"Connected to database: {self.db_config['host']}:{self.db_config['database']}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Closed database connection")

    def create_checkpoint(
        self,
        tables: List[str],
        checkpoint_id: Optional[str] = None
    ) -> RollbackCheckpoint:
        """Create a rollback checkpoint"""
        checkpoint_id = checkpoint_id or datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            self.connect()

            # Get current record counts for each table
            record_counts = {}
            for table in tables:
                with self.conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    record_counts[table] = result['count'] if result else 0

            checkpoint = RollbackCheckpoint(
                id=checkpoint_id,
                created_at=datetime.utcnow(),
                tables_affected=tables,
                record_counts=record_counts,
                status="active"
            )

            # Save checkpoint to file
            checkpoint_file = os.path.join(
                self.checkpoint_dir,
                f'checkpoint_{checkpoint_id}.json'
            )
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

            logger.info(f"Created checkpoint: {checkpoint_id}")
            return checkpoint

        finally:
            self.close()

    def load_checkpoint(self, checkpoint_id: str) -> Optional[RollbackCheckpoint]:
        """Load a checkpoint from file"""
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f'checkpoint_{checkpoint_id}.json'
        )

        if not os.path.exists(checkpoint_file):
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return None

        with open(checkpoint_file, 'r') as f:
            data = json.load(f)

        return RollbackCheckpoint(
            id=data['id'],
            created_at=datetime.fromisoformat(data['created_at']),
            tables_affected=data.get('tables_affected', []),
            record_counts=data.get('record_counts', {}),
            backup_file=data.get('backup_file'),
            status=data.get('status', 'active')
        )

    def list_checkpoints(self) -> List[RollbackCheckpoint]:
        """List all available checkpoints"""
        checkpoints = []

        for filename in os.listdir(self.checkpoint_dir):
            if filename.startswith('checkpoint_') and filename.endswith('.json'):
                checkpoint_id = filename[11:-5]  # Remove 'checkpoint_' and '.json'
                checkpoint = self.load_checkpoint(checkpoint_id)
                if checkpoint:
                    checkpoints.append(checkpoint)

        # Sort by creation date (newest first)
        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints

    def rollback_table(
        self,
        table_name: str,
        target_count: int,
        strategy: str = "truncate_excess"
    ) -> Dict[str, Any]:
        """Rollback a single table to target state"""
        result = {
            'table': table_name,
            'strategy': strategy,
            'success': False,
            'before_count': 0,
            'after_count': 0,
            'records_removed': 0
        }

        try:
            self.connect()

            # Get current count
            with self.conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                current_count = cursor.fetchone()['count']
                result['before_count'] = current_count

            if current_count <= target_count:
                logger.info(f"Table {table_name} already at or below target count")
                result['after_count'] = current_count
                result['success'] = True
                return result

            # Rollback strategy
            if strategy == "truncate_excess":
                # Remove records added after checkpoint
                excess = current_count - target_count
                with self.conn.cursor() as cursor:
                    # Delete newest records
                    cursor.execute(f"""
                        DELETE FROM {table_name}
                        ORDER BY id DESC
                        LIMIT %s
                    """, (excess,))
                    self.conn.commit()
                    result['records_removed'] = cursor.rowcount

            elif strategy == "restore_backup":
                # This would restore from a backup file
                # Not implemented here - requires database-specific logic
                logger.warning("Backup restore not implemented")
                pass

            # Verify
            with self.conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                result['after_count'] = cursor.fetchone()['count']

            result['success'] = True
            logger.info(f"Rolled back {table_name}: {result['before_count']} -> {result['after_count']}")

        except Exception as e:
            logger.error(f"Rollback failed for {table_name}: {e}")
            result['error'] = str(e)

        finally:
            self.close()

        return result

    def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Rollback all tables to a checkpoint"""
        checkpoint = self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return {'success': False, 'error': 'Checkpoint not found'}

        logger.info(f"Rolling back to checkpoint: {checkpoint_id}")
        if dry_run:
            logger.info("DRY RUN - No changes will be made")

        results = {
            'checkpoint_id': checkpoint_id,
            'dry_run': dry_run,
            'tables': [],
            'success': True
        }

        for table in checkpoint.tables_affected:
            target_count = checkpoint.record_counts.get(table, 0)

            if dry_run:
                # Just simulate
                try:
                    self.connect()
                    with self.conn.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        current_count = cursor.fetchone()['count']

                    results['tables'].append({
                        'table': table,
                        'current_count': current_count,
                        'target_count': target_count,
                        'would_remove': max(0, current_count - target_count)
                    })
                finally:
                    self.close()
            else:
                # Actually rollback
                table_result = self.rollback_table(table, target_count)
                results['tables'].append(table_result)

                if not table_result['success']:
                    results['success'] = False

        # Mark checkpoint as used
        if not dry_run and results['success']:
            checkpoint.status = "rolled_back"
            checkpoint_file = os.path.join(
                self.checkpoint_dir,
                f'checkpoint_{checkpoint_id}.json'
            )
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

        return results


def main():
    """CLI for rollback manager"""
    import argparse

    parser = argparse.ArgumentParser(description='Migration Rollback Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List checkpoints
    subparsers.add_parser('list', help='List available checkpoints')

    # Create checkpoint
    create_parser = subparsers.add_parser('create', help='Create a checkpoint')
    create_parser.add_argument('--tables', nargs='+', required=True,
                              help='Tables to include in checkpoint')

    # Rollback
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to checkpoint')
    rollback_parser.add_argument('checkpoint_id', help='Checkpoint ID to rollback to')
    rollback_parser.add_argument('--execute', action='store_true',
                                help='Actually execute rollback (not dry run)')

    args = parser.parse_args()

    manager = RollbackManager(
        host=os.getenv('DB_HOST', '112.213.91.103'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'Mysql_2025'),
        database=os.getenv('DB_NAME', 'defaultdb')
    )

    if args.command == 'list':
        checkpoints = manager.list_checkpoints()
        print(f"\nFound {len(checkpoints)} checkpoints:\n")
        for cp in checkpoints:
            print(f"  ID: {cp.id}")
            print(f"  Created: {cp.created_at}")
            print(f"  Tables: {', '.join(cp.tables_affected)}")
            print(f"  Status: {cp.status}")
            print()

    elif args.command == 'create':
        checkpoint = manager.create_checkpoint(args.tables)
        print(f"\nCreated checkpoint: {checkpoint.id}")
        print(f"Tables: {', '.join(checkpoint.tables_affected)}")
        print(f"Record counts: {checkpoint.record_counts}")

    elif args.command == 'rollback':
        dry_run = not args.execute
        result = manager.rollback_to_checkpoint(args.checkpoint_id, dry_run=dry_run)
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
