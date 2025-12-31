"""Data Validation for Migration"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pymysql
from pymysql.cursors import DictCursor
import hashlib
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    table_name: str
    check_name: str
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation report"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_db: str = ""
    target_db: str = ""
    results: List[ValidationResult] = field(default_factory=list)
    overall_passed: bool = False
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'source_db': self.source_db,
            'target_db': self.target_db,
            'overall_passed': self.overall_passed,
            'summary': self.summary,
            'results': [
                {
                    'table_name': r.table_name,
                    'check_name': r.check_name,
                    'passed': r.passed,
                    'details': r.details,
                    'errors': r.errors,
                    'warnings': r.warnings
                }
                for r in self.results
            ]
        }


class DataValidator:
    """Validate data migration between source and target databases"""

    def __init__(
        self,
        source_host: str,
        source_port: int,
        source_user: str,
        source_password: str,
        source_database: str,
        target_host: str,
        target_port: int,
        target_user: str,
        target_password: str,
        target_database: str
    ):
        self.source_config = {
            'host': source_host,
            'port': source_port,
            'user': source_user,
            'password': source_password,
            'database': source_database,
            'cursorclass': DictCursor,
            'charset': 'utf8mb4'
        }
        self.target_config = {
            'host': target_host,
            'port': target_port,
            'user': target_user,
            'password': target_password,
            'database': target_database,
            'cursorclass': DictCursor,
            'charset': 'utf8mb4'
        }
        self.source_conn = None
        self.target_conn = None

    def connect(self):
        """Establish database connections"""
        self.source_conn = pymysql.connect(**self.source_config)
        self.target_conn = pymysql.connect(**self.target_config)
        logger.info("Connected to source and target databases")

    def close(self):
        """Close database connections"""
        if self.source_conn:
            self.source_conn.close()
        if self.target_conn:
            self.target_conn.close()
        logger.info("Closed database connections")

    def validate_row_counts(self, table_name: str) -> ValidationResult:
        """Validate that row counts match between source and target"""
        result = ValidationResult(
            table_name=table_name,
            check_name="row_count"
        )

        try:
            with self.source_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                source_count = cursor.fetchone()['count']

            with self.target_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                target_count = cursor.fetchone()['count']

            result.details = {
                'source_count': source_count,
                'target_count': target_count,
                'difference': source_count - target_count
            }

            if source_count == target_count:
                result.passed = True
            else:
                result.errors.append(
                    f"Row count mismatch: source={source_count}, target={target_count}"
                )

        except Exception as e:
            result.errors.append(f"Validation failed: {str(e)}")

        return result

    def validate_primary_keys(self, table_name: str, pk_column: str = 'id') -> ValidationResult:
        """Validate that all primary keys exist in both databases"""
        result = ValidationResult(
            table_name=table_name,
            check_name="primary_key_integrity"
        )

        try:
            # Get source PKs
            with self.source_conn.cursor() as cursor:
                cursor.execute(f"SELECT {pk_column} FROM {table_name} ORDER BY {pk_column}")
                source_pks = set(row[pk_column] for row in cursor.fetchall())

            # Get target PKs
            with self.target_conn.cursor() as cursor:
                cursor.execute(f"SELECT {pk_column} FROM {table_name} ORDER BY {pk_column}")
                target_pks = set(row[pk_column] for row in cursor.fetchall())

            missing_in_target = source_pks - target_pks
            extra_in_target = target_pks - source_pks

            result.details = {
                'source_pk_count': len(source_pks),
                'target_pk_count': len(target_pks),
                'missing_in_target_count': len(missing_in_target),
                'extra_in_target_count': len(extra_in_target)
            }

            if not missing_in_target and not extra_in_target:
                result.passed = True
            else:
                if missing_in_target:
                    sample = list(missing_in_target)[:10]
                    result.errors.append(
                        f"Missing {len(missing_in_target)} PKs in target (sample: {sample})"
                    )
                if extra_in_target:
                    sample = list(extra_in_target)[:10]
                    result.warnings.append(
                        f"Extra {len(extra_in_target)} PKs in target (sample: {sample})"
                    )

        except Exception as e:
            result.errors.append(f"Validation failed: {str(e)}")

        return result

    def validate_data_checksum(
        self,
        table_name: str,
        columns: List[str],
        sample_size: int = 1000
    ) -> ValidationResult:
        """Validate data integrity using checksums"""
        result = ValidationResult(
            table_name=table_name,
            check_name="data_checksum"
        )

        try:
            columns_str = ', '.join(columns)

            # Get sample from source
            with self.source_conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT {columns_str} FROM {table_name} ORDER BY id LIMIT %s",
                    (sample_size,)
                )
                source_rows = cursor.fetchall()

            # Get corresponding rows from target
            with self.target_conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT {columns_str} FROM {table_name} ORDER BY id LIMIT %s",
                    (sample_size,)
                )
                target_rows = cursor.fetchall()

            # Compare checksums
            mismatches = []
            for i, (source_row, target_row) in enumerate(zip(source_rows, target_rows)):
                source_hash = hashlib.md5(
                    json.dumps(source_row, sort_keys=True, default=str).encode()
                ).hexdigest()
                target_hash = hashlib.md5(
                    json.dumps(target_row, sort_keys=True, default=str).encode()
                ).hexdigest()

                if source_hash != target_hash:
                    mismatches.append({
                        'row_index': i,
                        'source_id': source_row.get('id'),
                        'target_id': target_row.get('id')
                    })

            result.details = {
                'sample_size': sample_size,
                'rows_compared': min(len(source_rows), len(target_rows)),
                'mismatches': len(mismatches)
            }

            if not mismatches:
                result.passed = True
            else:
                result.errors.append(
                    f"Found {len(mismatches)} data mismatches (sample: {mismatches[:5]})"
                )

        except Exception as e:
            result.errors.append(f"Validation failed: {str(e)}")

        return result

    def validate_foreign_keys(
        self,
        table_name: str,
        fk_column: str,
        referenced_table: str,
        referenced_column: str = 'id'
    ) -> ValidationResult:
        """Validate foreign key integrity"""
        result = ValidationResult(
            table_name=table_name,
            check_name=f"fk_integrity_{fk_column}"
        )

        try:
            # Check for orphaned FKs in target
            with self.target_conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT t.{fk_column}
                    FROM {table_name} t
                    LEFT JOIN {referenced_table} r ON t.{fk_column} = r.{referenced_column}
                    WHERE t.{fk_column} IS NOT NULL AND r.{referenced_column} IS NULL
                    LIMIT 100
                """)
                orphaned = cursor.fetchall()

            result.details = {
                'orphaned_fks': len(orphaned)
            }

            if not orphaned:
                result.passed = True
            else:
                sample = [row[fk_column] for row in orphaned[:10]]
                result.errors.append(
                    f"Found {len(orphaned)} orphaned FKs (sample: {sample})"
                )

        except Exception as e:
            result.errors.append(f"Validation failed: {str(e)}")

        return result

    def validate_null_constraints(
        self,
        table_name: str,
        not_null_columns: List[str]
    ) -> ValidationResult:
        """Validate NOT NULL constraints are satisfied"""
        result = ValidationResult(
            table_name=table_name,
            check_name="null_constraints"
        )

        try:
            violations = {}

            for column in not_null_columns:
                with self.target_conn.cursor() as cursor:
                    cursor.execute(
                        f"SELECT COUNT(*) as count FROM {table_name} WHERE {column} IS NULL"
                    )
                    null_count = cursor.fetchone()['count']

                    if null_count > 0:
                        violations[column] = null_count

            result.details = {
                'checked_columns': not_null_columns,
                'violations': violations
            }

            if not violations:
                result.passed = True
            else:
                result.errors.append(f"NULL violations found: {violations}")

        except Exception as e:
            result.errors.append(f"Validation failed: {str(e)}")

        return result

    def run_full_validation(
        self,
        tables: List[str],
        fk_definitions: Optional[Dict[str, List[Dict]]] = None
    ) -> ValidationReport:
        """Run full validation on specified tables"""
        report = ValidationReport(
            source_db=f"{self.source_config['host']}:{self.source_config['database']}",
            target_db=f"{self.target_config['host']}:{self.target_config['database']}"
        )

        try:
            self.connect()

            for table in tables:
                logger.info(f"Validating table: {table}")

                # Row count validation
                report.results.append(self.validate_row_counts(table))

                # PK validation
                report.results.append(self.validate_primary_keys(table))

                # FK validation if defined
                if fk_definitions and table in fk_definitions:
                    for fk in fk_definitions[table]:
                        report.results.append(self.validate_foreign_keys(
                            table,
                            fk['column'],
                            fk['referenced_table'],
                            fk.get('referenced_column', 'id')
                        ))

            # Calculate summary
            passed_count = sum(1 for r in report.results if r.passed)
            failed_count = sum(1 for r in report.results if not r.passed)

            report.summary = {
                'total_checks': len(report.results),
                'passed': passed_count,
                'failed': failed_count,
                'pass_rate': passed_count / len(report.results) if report.results else 0
            }

            report.overall_passed = failed_count == 0

        finally:
            self.close()

        return report


def run_validation(
    tables: Optional[List[str]] = None,
    output_file: Optional[str] = None
):
    """Run validation with default configuration"""
    import os

    validator = DataValidator(
        source_host=os.getenv('SOURCE_DB_HOST', '112.213.91.103'),
        source_port=int(os.getenv('SOURCE_DB_PORT', '3306')),
        source_user=os.getenv('SOURCE_DB_USER', 'root'),
        source_password=os.getenv('SOURCE_DB_PASSWORD', 'Mysql_2025'),
        source_database=os.getenv('SOURCE_DB_NAME', 'defaultdb'),
        target_host=os.getenv('TARGET_DB_HOST', '112.213.91.103'),
        target_port=int(os.getenv('TARGET_DB_PORT', '3306')),
        target_user=os.getenv('TARGET_DB_USER', 'root'),
        target_password=os.getenv('TARGET_DB_PASSWORD', 'Mysql_2025'),
        target_database=os.getenv('TARGET_DB_NAME', 'defaultdb')
    )

    default_tables = tables or [
        'stock_helper_user',
        'stock_helper_userprofile',
        'stock_helper_company',
        'stock_helper_stockprice',
        'stock_helper_industry',
        'stock_helper_sector',
    ]

    # FK definitions for validation
    fk_definitions = {
        'stock_helper_userprofile': [
            {'column': 'user_id', 'referenced_table': 'stock_helper_user'}
        ],
        'stock_helper_stockprice': [
            {'column': 'company_id', 'referenced_table': 'stock_helper_company'}
        ],
        'stock_helper_company': [
            {'column': 'industry_id', 'referenced_table': 'stock_helper_industry'}
        ],
        'stock_helper_industry': [
            {'column': 'sector_id', 'referenced_table': 'stock_helper_sector'}
        ]
    }

    report = validator.run_full_validation(default_tables, fk_definitions)

    # Output results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Validation report saved to: {output_file}")
    else:
        print(json.dumps(report.to_dict(), indent=2))

    return report


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Data Validation')
    parser.add_argument('--tables', nargs='+', help='Tables to validate')
    parser.add_argument('--output', '-o', help='Output file for report')

    args = parser.parse_args()

    run_validation(
        tables=args.tables,
        output_file=args.output
    )
