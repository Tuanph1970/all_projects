"""User Data Migration Script"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import BaseMigration, MigrationConfig, MigrationResult

logger = logging.getLogger(__name__)


class UserMigration(BaseMigration):
    """Migration for user-related tables"""

    # Table mapping from Django to Microservices
    TABLE_MAPPINGS = {
        'stock_helper_user': {
            'target_table': 'stock_helper_user',
            'field_mappings': {
                # source_field: target_field (None means same name)
                'id': None,
                'username': None,
                'email': None,
                'password': None,
                'first_name': None,
                'last_name': None,
                'is_active': None,
                'is_staff': None,
                'is_superuser': None,
                'date_joined': None,
                'last_login': None,
            },
            'transformations': {
                # field: transformation function
            }
        },
        'stock_helper_userprofile': {
            'target_table': 'stock_helper_userprofile',
            'field_mappings': {
                'id': None,
                'user_id': None,
                'phone': None,
                'avatar': None,
                'bio': None,
                'preferences': None,
            }
        },
        'stock_helper_usersession': {
            'target_table': 'stock_helper_usersession',
            'field_mappings': {
                'id': None,
                'user_id': None,
                'session_key': None,
                'ip_address': None,
                'user_agent': None,
                'created_at': None,
                'expires_at': None,
                'is_active': None,
            }
        }
    }

    def get_source_tables(self) -> List[str]:
        """Get list of user-related tables to migrate"""
        return list(self.TABLE_MAPPINGS.keys())

    def migrate_table(self, table_name: str) -> MigrationResult:
        """Migrate a single table"""
        result = MigrationResult(table_name=table_name)

        try:
            mapping = self.TABLE_MAPPINGS.get(table_name)
            if not mapping:
                result.errors.append(f"No mapping found for table: {table_name}")
                result.finalize()
                return result

            # Get source data
            source_count = self.get_table_count(self.source_conn, table_name)
            logger.info(f"  Found {source_count} records in source table")

            if self.config.validate_only:
                result.records_processed = source_count
                result.records_migrated = source_count
                result.finalize()
                return result

            # Compare schemas
            schema_comparison = self.compare_schemas(table_name)
            if not schema_comparison['compatible']:
                if schema_comparison['missing_in_target']:
                    result.warnings.append(
                        f"Fields missing in target: {schema_comparison['missing_in_target']}"
                    )
                if schema_comparison['type_differences']:
                    result.warnings.append(
                        f"Type differences: {schema_comparison['type_differences']}"
                    )

            # Migrate in batches
            offset = 0
            while offset < source_count:
                batch = self._fetch_batch(table_name, offset, self.config.batch_size)
                result.records_processed += len(batch)

                if not self.config.dry_run:
                    migrated, failed = self._insert_batch(
                        mapping['target_table'],
                        batch,
                        mapping.get('field_mappings', {}),
                        mapping.get('transformations', {})
                    )
                    result.records_migrated += migrated
                    result.records_failed += failed
                else:
                    result.records_migrated += len(batch)
                    logger.debug(f"  [DRY RUN] Would migrate {len(batch)} records")

                offset += self.config.batch_size

            result.finalize()

        except Exception as e:
            result.errors.append(str(e))
            result.finalize()
            logger.error(f"Error migrating table {table_name}: {e}")

        return result

    def _fetch_batch(
        self,
        table_name: str,
        offset: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of records from source"""
        with self.source_conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {table_name} ORDER BY id LIMIT %s OFFSET %s",
                (limit, offset)
            )
            return cursor.fetchall()

    def _insert_batch(
        self,
        target_table: str,
        records: List[Dict[str, Any]],
        field_mappings: Dict[str, Optional[str]],
        transformations: Dict[str, callable]
    ) -> tuple:
        """Insert a batch of records into target"""
        if not records:
            return 0, 0

        migrated = 0
        failed = 0

        with self.target_conn.cursor() as cursor:
            for record in records:
                try:
                    # Apply field mappings and transformations
                    transformed = self._transform_record(
                        record, field_mappings, transformations
                    )

                    # Build insert query
                    fields = list(transformed.keys())
                    placeholders = ', '.join(['%s'] * len(fields))
                    field_names = ', '.join(fields)

                    sql = f"""
                        INSERT INTO {target_table} ({field_names})
                        VALUES ({placeholders})
                        ON DUPLICATE KEY UPDATE
                        {', '.join([f'{f}=VALUES({f})' for f in fields if f != 'id'])}
                    """

                    cursor.execute(sql, list(transformed.values()))
                    migrated += 1

                except Exception as e:
                    logger.error(f"Failed to insert record {record.get('id')}: {e}")
                    failed += 1

            self.target_conn.commit()

        return migrated, failed

    def _transform_record(
        self,
        record: Dict[str, Any],
        field_mappings: Dict[str, Optional[str]],
        transformations: Dict[str, callable]
    ) -> Dict[str, Any]:
        """Transform a record according to mappings and transformations"""
        result = {}

        for source_field, target_field in field_mappings.items():
            if source_field in record:
                target_name = target_field if target_field else source_field
                value = record[source_field]

                # Apply transformation if exists
                if source_field in transformations:
                    value = transformations[source_field](value)

                result[target_name] = value

        return result

    def validate_migration(self) -> Dict[str, Any]:
        """Validate migration by comparing source and target"""
        validation_results = {}

        for table in self.get_source_tables():
            mapping = self.TABLE_MAPPINGS[table]
            target_table = mapping['target_table']

            source_count = self.get_table_count(self.source_conn, table)
            target_count = self.get_table_count(self.target_conn, target_table)

            validation_results[table] = {
                'source_count': source_count,
                'target_count': target_count,
                'match': source_count == target_count,
                'difference': source_count - target_count
            }

        return validation_results


def run_user_migration(
    dry_run: bool = True,
    validate_only: bool = False,
    batch_size: int = 1000
):
    """Run user migration"""
    config = MigrationConfig(
        dry_run=dry_run,
        validate_only=validate_only,
        batch_size=batch_size
    )

    migration = UserMigration(config)
    results = migration.run()

    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    migration.save_report(f'user_migration_report_{timestamp}.json')

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='User Data Migration')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Run in dry-run mode (no actual changes)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute the migration (not dry-run)')
    parser.add_argument('--validate', action='store_true',
                        help='Only validate, do not migrate')
    parser.add_argument('--batch-size', type=int, default=1000,
                        help='Batch size for migration')

    args = parser.parse_args()

    dry_run = not args.execute
    run_user_migration(
        dry_run=dry_run,
        validate_only=args.validate,
        batch_size=args.batch_size
    )
