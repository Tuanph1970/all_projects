#!/usr/bin/env python3
"""
Migration Rollback Script
Emergency rollback procedures for data migration

This script provides capabilities to:
1. Rollback specific tables to pre-migration state
2. Rollback all migrated data
3. Verify rollback completeness

Usage:
    python rollback_migration.py --table users --dry-run
    python rollback_migration.py --all --confirm
"""
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
import json

from sqlalchemy import create_engine, text

import sys
sys.path.append('..')
from config.settings import (
    AUTH_DB, STOCK_DATA_DB, PORTFOLIO_DB,
    PREDICTION_DB, ANALYSIS_DB
)


@dataclass
class RollbackResult:
    """Result of a rollback operation"""
    table: str
    records_deleted: int
    success: bool
    error: str = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.table,
            "records_deleted": self.records_deleted,
            "success": self.success,
            "error": self.error,
            "duration_seconds": self.duration_seconds
        }


class MigrationRollback:
    """Handles rollback of migrated data"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.logger = logging.getLogger("migration.rollback")
        self.results: List[RollbackResult] = []

        # Table configurations: (db_config, table_name, rollback_order)
        # Higher order = rolled back first (to handle foreign keys)
        self.tables = [
            (PORTFOLIO_DB, "transactions", 1),
            (PORTFOLIO_DB, "holdings", 2),
            (PORTFOLIO_DB, "price_alerts", 3),
            (PORTFOLIO_DB, "portfolios", 4),
            (STOCK_DATA_DB, "historical_prices", 5),
            (STOCK_DATA_DB, "companies", 6),
            (STOCK_DATA_DB, "industries", 7),
            (AUTH_DB, "users", 8),
        ]

    def rollback_table(self, db_config, table_name: str) -> RollbackResult:
        """Rollback a single table by deleting migrated records"""
        start_time = datetime.utcnow()
        result = RollbackResult(table=table_name, records_deleted=0, success=False)

        try:
            engine = create_engine(db_config.connection_string)

            with engine.connect() as conn:
                # Count records to delete
                count_query = text(f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE legacy_id IS NOT NULL
                """)
                count = conn.execute(count_query).scalar()
                self.logger.info(f"  Found {count} migrated records in {table_name}")

                if self.dry_run:
                    self.logger.info(f"  [DRY RUN] Would delete {count} records")
                    result.records_deleted = count
                    result.success = True
                else:
                    # Disable foreign key checks temporarily
                    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

                    # Delete migrated records
                    delete_query = text(f"""
                        DELETE FROM {table_name}
                        WHERE legacy_id IS NOT NULL
                    """)
                    delete_result = conn.execute(delete_query)
                    result.records_deleted = delete_result.rowcount

                    # Re-enable foreign key checks
                    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                    conn.commit()

                    self.logger.info(f"  Deleted {result.records_deleted} records")
                    result.success = True

            engine.dispose()

        except Exception as e:
            result.error = str(e)
            self.logger.error(f"  Error rolling back {table_name}: {e}")

        result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        return result

    def rollback_all(self) -> List[RollbackResult]:
        """Rollback all migrated tables in correct order"""
        self.logger.info("Starting full rollback...")

        # Sort by rollback order (descending)
        sorted_tables = sorted(self.tables, key=lambda x: x[2])

        for db_config, table_name, _ in sorted_tables:
            self.logger.info(f"Rolling back: {table_name}")
            result = self.rollback_table(db_config, table_name)
            self.results.append(result)

        return self.results

    def rollback_specific(self, table_names: List[str]) -> List[RollbackResult]:
        """Rollback specific tables"""
        # Find matching tables
        tables_to_rollback = [
            (db, table, order) for db, table, order in self.tables
            if table in table_names
        ]

        if not tables_to_rollback:
            self.logger.error(f"No matching tables found for: {table_names}")
            return []

        # Sort by rollback order
        sorted_tables = sorted(tables_to_rollback, key=lambda x: x[2])

        for db_config, table_name, _ in sorted_tables:
            self.logger.info(f"Rolling back: {table_name}")
            result = self.rollback_table(db_config, table_name)
            self.results.append(result)

        return self.results

    def verify_rollback(self) -> Dict[str, Any]:
        """Verify rollback was successful"""
        verification = {
            "verified_at": datetime.utcnow().isoformat(),
            "tables": {},
            "all_clear": True
        }

        for db_config, table_name, _ in self.tables:
            try:
                engine = create_engine(db_config.connection_string)
                with engine.connect() as conn:
                    count = conn.execute(text(f"""
                        SELECT COUNT(*) FROM {table_name}
                        WHERE legacy_id IS NOT NULL
                    """)).scalar()

                verification["tables"][table_name] = {
                    "remaining_migrated_records": count,
                    "clear": count == 0
                }

                if count > 0:
                    verification["all_clear"] = False

                engine.dispose()

            except Exception as e:
                verification["tables"][table_name] = {
                    "error": str(e),
                    "clear": False
                }
                verification["all_clear"] = False

        return verification

    def generate_report(self) -> Dict[str, Any]:
        """Generate rollback report"""
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "dry_run": self.dry_run,
            "summary": {
                "total_tables": len(self.results),
                "successful": sum(1 for r in self.results if r.success),
                "failed": sum(1 for r in self.results if not r.success),
                "total_records_deleted": sum(r.records_deleted for r in self.results),
                "total_duration_seconds": sum(r.duration_seconds for r in self.results),
            },
            "tables": [r.to_dict() for r in self.results]
        }


def main():
    parser = argparse.ArgumentParser(description="Rollback migration data")
    parser.add_argument(
        "--table",
        help="Specific table to rollback"
    )
    parser.add_argument(
        "--tables",
        help="Comma-separated list of tables to rollback"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rollback all migrated tables"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate rollback without deleting (default)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually perform the rollback (removes --dry-run)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify rollback completeness"
    )
    parser.add_argument(
        "--output",
        help="Save report to JSON file"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    dry_run = not args.confirm
    rollback = MigrationRollback(dry_run=dry_run)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be deleted")
        print("    Use --confirm to actually perform rollback\n")
    else:
        print("\n🚨 LIVE MODE - Data WILL be deleted!")
        input("Press Enter to continue or Ctrl+C to abort...")
        print()

    # Perform rollback
    if args.verify:
        print("=== Verification Only ===\n")
        verification = rollback.verify_rollback()
        print(json.dumps(verification, indent=2))

    elif args.all:
        print("=== Rolling Back All Tables ===\n")
        rollback.rollback_all()

    elif args.table:
        print(f"=== Rolling Back Table: {args.table} ===\n")
        rollback.rollback_specific([args.table])

    elif args.tables:
        tables = [t.strip() for t in args.tables.split(",")]
        print(f"=== Rolling Back Tables: {tables} ===\n")
        rollback.rollback_specific(tables)

    else:
        parser.print_help()
        return

    # Generate and print report
    if rollback.results:
        report = rollback.generate_report()

        print("\n=== Rollback Summary ===")
        print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"  Tables Processed: {report['summary']['total_tables']}")
        print(f"  Successful: {report['summary']['successful']}")
        print(f"  Failed: {report['summary']['failed']}")
        print(f"  Records {'Would Delete' if dry_run else 'Deleted'}: "
              f"{report['summary']['total_records_deleted']}")
        print(f"  Duration: {report['summary']['total_duration_seconds']:.2f}s")

        # Show per-table results
        print("\n  Per-Table Results:")
        for result in rollback.results:
            status = "✓" if result.success else "✗"
            print(f"    {status} {result.table}: {result.records_deleted} records")
            if result.error:
                print(f"      Error: {result.error}")

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n  Report saved to: {args.output}")


if __name__ == "__main__":
    main()
