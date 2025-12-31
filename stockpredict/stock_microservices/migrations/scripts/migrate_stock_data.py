"""Stock Data Migration Script"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import BaseMigration, MigrationConfig, MigrationResult

logger = logging.getLogger(__name__)


class StockDataMigration(BaseMigration):
    """Migration for stock data tables"""

    TABLE_MAPPINGS = {
        'stock_helper_company': {
            'target_table': 'stock_helper_company',
            'field_mappings': {
                'id': None,
                'symbol': None,
                'name': None,
                'short_name': None,
                'exchange': None,
                'industry': None,
                'sector': None,
                'market_cap': None,
                'listing_date': None,
                'is_active': None,
                'created_at': None,
                'updated_at': None,
            }
        },
        'stock_helper_stockprice': {
            'target_table': 'stock_helper_stockprice',
            'field_mappings': {
                'id': None,
                'company_id': None,
                'date': None,
                'open': None,
                'high': None,
                'low': None,
                'close': None,
                'volume': None,
                'adjusted_close': None,
            },
            'order_by': 'date DESC',
            'incremental_field': 'date'
        },
        'stock_helper_stockindicator': {
            'target_table': 'stock_helper_stockindicator',
            'field_mappings': {
                'id': None,
                'company_id': None,
                'date': None,
                'indicator_type': None,
                'value': None,
                'period': None,
            },
            'order_by': 'date DESC',
            'incremental_field': 'date'
        },
        'stock_helper_industry': {
            'target_table': 'stock_helper_industry',
            'field_mappings': {
                'id': None,
                'name': None,
                'code': None,
                'sector_id': None,
                'description': None,
            }
        },
        'stock_helper_sector': {
            'target_table': 'stock_helper_sector',
            'field_mappings': {
                'id': None,
                'name': None,
                'code': None,
                'description': None,
            }
        },
        'stock_helper_marketindex': {
            'target_table': 'stock_helper_marketindex',
            'field_mappings': {
                'id': None,
                'name': None,
                'symbol': None,
                'exchange': None,
                'description': None,
            }
        },
        'stock_helper_indexhistory': {
            'target_table': 'stock_helper_indexhistory',
            'field_mappings': {
                'id': None,
                'index_id': None,
                'date': None,
                'open': None,
                'high': None,
                'low': None,
                'close': None,
                'volume': None,
                'change_percent': None,
            },
            'order_by': 'date DESC',
            'incremental_field': 'date'
        }
    }

    def get_source_tables(self) -> List[str]:
        """Get list of stock data tables to migrate"""
        # Order matters for foreign key constraints
        return [
            'stock_helper_sector',
            'stock_helper_industry',
            'stock_helper_company',
            'stock_helper_stockprice',
            'stock_helper_stockindicator',
            'stock_helper_marketindex',
            'stock_helper_indexhistory',
        ]

    def migrate_table(self, table_name: str) -> MigrationResult:
        """Migrate a single table"""
        result = MigrationResult(table_name=table_name)

        try:
            mapping = self.TABLE_MAPPINGS.get(table_name)
            if not mapping:
                result.errors.append(f"No mapping found for table: {table_name}")
                result.finalize()
                return result

            # Get source data count
            source_count = self.get_table_count(self.source_conn, table_name)
            logger.info(f"  Found {source_count} records in source table")

            if self.config.validate_only:
                result.records_processed = source_count
                result.records_migrated = source_count
                result.finalize()
                return result

            # Check for incremental migration
            incremental_field = mapping.get('incremental_field')
            last_migrated = None

            if incremental_field and not self.config.dry_run:
                last_migrated = self._get_last_migrated_value(
                    mapping['target_table'],
                    incremental_field
                )
                if last_migrated:
                    logger.info(f"  Incremental migration from: {last_migrated}")

            # Migrate in batches
            order_by = mapping.get('order_by', 'id')
            offset = 0

            while offset < source_count:
                batch = self._fetch_batch(
                    table_name,
                    offset,
                    self.config.batch_size,
                    order_by,
                    incremental_field,
                    last_migrated
                )

                if not batch:
                    break

                result.records_processed += len(batch)

                if not self.config.dry_run:
                    migrated, failed = self._insert_batch(
                        mapping['target_table'],
                        batch,
                        mapping.get('field_mappings', {})
                    )
                    result.records_migrated += migrated
                    result.records_failed += failed
                else:
                    result.records_migrated += len(batch)
                    logger.debug(f"  [DRY RUN] Would migrate {len(batch)} records")

                offset += self.config.batch_size

                # For large tables, log progress
                if source_count > 10000 and offset % 10000 == 0:
                    logger.info(f"  Progress: {offset}/{source_count} records")

            result.finalize()

        except Exception as e:
            result.errors.append(str(e))
            result.finalize()
            logger.error(f"Error migrating table {table_name}: {e}")

        return result

    def _get_last_migrated_value(
        self,
        table_name: str,
        field_name: str
    ) -> Optional[Any]:
        """Get the last migrated value for incremental migration"""
        try:
            with self.target_conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT MAX({field_name}) as last_value FROM {table_name}"
                )
                result = cursor.fetchone()
                return result['last_value'] if result else None
        except Exception:
            return None

    def _fetch_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        order_by: str = 'id',
        incremental_field: Optional[str] = None,
        last_value: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of records from source"""
        with self.source_conn.cursor() as cursor:
            if incremental_field and last_value:
                cursor.execute(
                    f"""
                    SELECT * FROM {table_name}
                    WHERE {incremental_field} > %s
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s
                    """,
                    (last_value, limit, offset)
                )
            else:
                cursor.execute(
                    f"""
                    SELECT * FROM {table_name}
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset)
                )
            return cursor.fetchall()

    def _insert_batch(
        self,
        target_table: str,
        records: List[Dict[str, Any]],
        field_mappings: Dict[str, Optional[str]]
    ) -> tuple:
        """Insert a batch of records into target"""
        if not records:
            return 0, 0

        migrated = 0
        failed = 0

        with self.target_conn.cursor() as cursor:
            for record in records:
                try:
                    # Apply field mappings
                    transformed = {}
                    for source_field, target_field in field_mappings.items():
                        if source_field in record:
                            target_name = target_field if target_field else source_field
                            transformed[target_name] = record[source_field]

                    if not transformed:
                        continue

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


def run_stock_data_migration(
    dry_run: bool = True,
    validate_only: bool = False,
    batch_size: int = 5000
):
    """Run stock data migration"""
    config = MigrationConfig(
        dry_run=dry_run,
        validate_only=validate_only,
        batch_size=batch_size
    )

    migration = StockDataMigration(config)
    results = migration.run()

    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    migration.save_report(f'stock_data_migration_report_{timestamp}.json')

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Stock Data Migration')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Run in dry-run mode (no actual changes)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute the migration (not dry-run)')
    parser.add_argument('--validate', action='store_true',
                        help='Only validate, do not migrate')
    parser.add_argument('--batch-size', type=int, default=5000,
                        help='Batch size for migration')

    args = parser.parse_args()

    dry_run = not args.execute
    run_stock_data_migration(
        dry_run=dry_run,
        validate_only=args.validate,
        batch_size=args.batch_size
    )
