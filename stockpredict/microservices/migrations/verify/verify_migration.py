#!/usr/bin/env python3
"""
Migration Verification Script
Comprehensive verification of data migration completeness and accuracy

Usage:
    python verify_migration.py --full
    python verify_migration.py --table users
    python verify_migration.py --sample 100
"""
import argparse
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
import random

from sqlalchemy import create_engine, text

import sys
sys.path.append('..')
from config.settings import (
    DJANGO_DB, AUTH_DB, STOCK_DATA_DB, PORTFOLIO_DB,
    PREDICTION_DB, ANALYSIS_DB
)


@dataclass
class VerificationResult:
    """Result of a verification check"""
    table: str
    source_count: int = 0
    target_count: int = 0
    count_match: bool = False
    sample_verified: int = 0
    sample_passed: int = 0
    sample_failed: int = 0
    data_integrity_score: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def is_valid(self) -> bool:
        return self.count_match and self.sample_failed == 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MigrationVerifier:
    """Comprehensive migration verification tool"""

    def __init__(self):
        self.logger = logging.getLogger("migration.verify")

        # Table mappings: (source_table, target_db, target_table, key_field)
        self.table_mappings = [
            ("auth_user", AUTH_DB, "users", "username"),
            ("stock_industry", STOCK_DATA_DB, "industries", "name"),
            ("stock_company", STOCK_DATA_DB, "companies", "symbol"),
            ("stock_portfolio", PORTFOLIO_DB, "portfolios", "name"),
            ("stock_holding", PORTFOLIO_DB, "holdings", "symbol"),
            ("stock_transaction", PORTFOLIO_DB, "transactions", "transaction_type"),
            ("stock_pricealert", PORTFOLIO_DB, "price_alerts", "symbol"),
        ]

        self.results: Dict[str, VerificationResult] = {}

    def get_engine(self, db_config):
        """Create database engine"""
        return create_engine(db_config.connection_string)

    def count_records(self, engine, table: str) -> int:
        """Count records in a table"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                return result.scalar()
        except Exception as e:
            self.logger.error(f"Error counting {table}: {e}")
            return -1

    def verify_counts(self) -> Dict[str, VerificationResult]:
        """Verify record counts match between source and target"""
        self.logger.info("Verifying record counts...")

        source_engine = self.get_engine(DJANGO_DB)

        for source_table, target_db, target_table, _ in self.table_mappings:
            result = VerificationResult(table=source_table)

            # Count source
            result.source_count = self.count_records(source_engine, source_table)

            # Count target
            target_engine = self.get_engine(target_db)
            result.target_count = self.count_records(target_engine, target_table)
            target_engine.dispose()

            # Compare
            result.count_match = result.source_count == result.target_count

            if not result.count_match:
                diff = result.source_count - result.target_count
                if diff > 0:
                    result.warnings.append(f"Missing {diff} records in target")
                else:
                    result.warnings.append(f"Extra {abs(diff)} records in target")

            self.results[source_table] = result
            self.logger.info(
                f"  {source_table}: {result.source_count} -> {result.target_count} "
                f"({'✓' if result.count_match else '✗'})"
            )

        source_engine.dispose()
        return self.results

    def verify_sample_data(
        self,
        table: str = None,
        sample_size: int = 100
    ) -> Dict[str, VerificationResult]:
        """Verify sample records match between source and target"""
        self.logger.info(f"Verifying sample data (n={sample_size})...")

        source_engine = self.get_engine(DJANGO_DB)

        tables_to_verify = [
            t for t in self.table_mappings
            if table is None or t[0] == table
        ]

        for source_table, target_db, target_table, key_field in tables_to_verify:
            if source_table not in self.results:
                self.results[source_table] = VerificationResult(table=source_table)

            result = self.results[source_table]
            target_engine = self.get_engine(target_db)

            try:
                # Get sample IDs from source
                with source_engine.connect() as conn:
                    ids_query = text(f"SELECT id FROM {source_table} ORDER BY RAND() LIMIT {sample_size}")
                    sample_ids = [row.id for row in conn.execute(ids_query)]

                result.sample_verified = len(sample_ids)

                # Verify each sample record
                for legacy_id in sample_ids:
                    verified, error = self._verify_record(
                        source_engine, source_table,
                        target_engine, target_table,
                        legacy_id, key_field
                    )
                    if verified:
                        result.sample_passed += 1
                    else:
                        result.sample_failed += 1
                        if error:
                            result.errors.append(error)

                # Calculate integrity score
                if result.sample_verified > 0:
                    result.data_integrity_score = (
                        result.sample_passed / result.sample_verified
                    ) * 100

            except Exception as e:
                result.errors.append(f"Sample verification failed: {str(e)}")
                self.logger.error(f"Error verifying {source_table}: {e}")

            finally:
                target_engine.dispose()

            self.logger.info(
                f"  {source_table}: {result.sample_passed}/{result.sample_verified} passed "
                f"({result.data_integrity_score:.1f}%)"
            )

        source_engine.dispose()
        return self.results

    def _verify_record(
        self,
        source_engine,
        source_table: str,
        target_engine,
        target_table: str,
        legacy_id: int,
        key_field: str
    ) -> Tuple[bool, str]:
        """Verify a single record was migrated correctly"""
        try:
            # Get source record
            with source_engine.connect() as conn:
                source_query = text(f"SELECT * FROM {source_table} WHERE id = :id")
                source_record = conn.execute(source_query, {"id": legacy_id}).fetchone()

            if not source_record:
                return False, f"Source record {legacy_id} not found"

            # Get target record by legacy_id
            with target_engine.connect() as conn:
                target_query = text(f"SELECT * FROM {target_table} WHERE legacy_id = :id")
                target_record = conn.execute(target_query, {"id": legacy_id}).fetchone()

            if not target_record:
                return False, f"Target record for legacy_id {legacy_id} not found"

            # Verify key field matches
            source_value = getattr(source_record, key_field, None)
            target_value = getattr(target_record, key_field, None)

            if source_value != target_value:
                return False, (
                    f"Record {legacy_id}: {key_field} mismatch "
                    f"({source_value} != {target_value})"
                )

            return True, None

        except Exception as e:
            return False, f"Error verifying record {legacy_id}: {str(e)}"

    def verify_referential_integrity(self) -> Dict[str, List[str]]:
        """Verify foreign key relationships are intact"""
        self.logger.info("Verifying referential integrity...")
        issues = {}

        portfolio_engine = self.get_engine(PORTFOLIO_DB)

        # Check holdings -> portfolios
        with portfolio_engine.connect() as conn:
            orphaned = conn.execute(text("""
                SELECT h.id, h.portfolio_id
                FROM holdings h
                LEFT JOIN portfolios p ON h.portfolio_id = p.id
                WHERE p.id IS NULL AND h.portfolio_id IS NOT NULL
                LIMIT 10
            """)).fetchall()

            if orphaned:
                issues["holdings_without_portfolio"] = [
                    f"Holding {row.id} references missing portfolio {row.portfolio_id}"
                    for row in orphaned
                ]

        # Check transactions -> portfolios
        with portfolio_engine.connect() as conn:
            orphaned = conn.execute(text("""
                SELECT t.id, t.portfolio_id
                FROM transactions t
                LEFT JOIN portfolios p ON t.portfolio_id = p.id
                WHERE p.id IS NULL AND t.portfolio_id IS NOT NULL
                LIMIT 10
            """)).fetchall()

            if orphaned:
                issues["transactions_without_portfolio"] = [
                    f"Transaction {row.id} references missing portfolio {row.portfolio_id}"
                    for row in orphaned
                ]

        portfolio_engine.dispose()

        if not issues:
            self.logger.info("  All referential integrity checks passed ✓")
        else:
            for check, problems in issues.items():
                self.logger.warning(f"  {check}: {len(problems)} issues found")

        return issues

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_tables": len(self.results),
                "tables_passed": sum(1 for r in self.results.values() if r.is_valid),
                "tables_failed": sum(1 for r in self.results.values() if not r.is_valid),
                "overall_integrity": 0.0,
            },
            "tables": {},
            "recommendations": []
        }

        # Calculate overall integrity
        if self.results:
            total_score = sum(r.data_integrity_score for r in self.results.values())
            report["summary"]["overall_integrity"] = total_score / len(self.results)

        # Add table results
        for table, result in self.results.items():
            report["tables"][table] = result.to_dict()

        # Generate recommendations
        for table, result in self.results.items():
            if not result.count_match:
                report["recommendations"].append(
                    f"Re-run migration for {table}: count mismatch"
                )
            if result.sample_failed > 0:
                report["recommendations"].append(
                    f"Investigate {result.sample_failed} failed samples in {table}"
                )
            if result.data_integrity_score < 95:
                report["recommendations"].append(
                    f"Data integrity below threshold for {table}: "
                    f"{result.data_integrity_score:.1f}%"
                )

        return report


def main():
    parser = argparse.ArgumentParser(description="Verify migration completeness")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full verification including samples"
    )
    parser.add_argument(
        "--table",
        help="Verify specific table only"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=100,
        help="Sample size for data verification"
    )
    parser.add_argument(
        "--output",
        help="Output report to JSON file"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    verifier = MigrationVerifier()

    # Run verifications
    print("\n=== Migration Verification ===\n")

    # Count verification
    verifier.verify_counts()

    # Sample verification
    if args.full or args.table:
        print()
        verifier.verify_sample_data(table=args.table, sample_size=args.sample)

    # Referential integrity
    if args.full:
        print()
        integrity_issues = verifier.verify_referential_integrity()

    # Generate report
    report = verifier.generate_report()

    # Print summary
    print("\n=== Verification Summary ===")
    print(f"  Tables Verified: {report['summary']['total_tables']}")
    print(f"  Tables Passed: {report['summary']['tables_passed']}")
    print(f"  Tables Failed: {report['summary']['tables_failed']}")
    print(f"  Overall Integrity: {report['summary']['overall_integrity']:.1f}%")

    if report["recommendations"]:
        print("\n  Recommendations:")
        for rec in report["recommendations"]:
            print(f"    - {rec}")

    # Save report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved to: {args.output}")

    # Exit code
    if report["summary"]["tables_failed"] > 0:
        print("\n❌ Verification FAILED")
        exit(1)
    else:
        print("\n✓ Verification PASSED")
        exit(0)


if __name__ == "__main__":
    main()
