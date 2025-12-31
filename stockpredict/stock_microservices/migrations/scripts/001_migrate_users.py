#!/usr/bin/env python3
"""
User Migration Script
Migrates user accounts from Django auth_user table to auth-service users table

Migration Order: 1 (First - users are referenced by other tables)

Usage:
    python 001_migrate_users.py --mode dry_run
    python 001_migrate_users.py --mode initial
    python 001_migrate_users.py --mode verify
"""
import argparse
import logging
from typing import Dict, Any
from datetime import datetime

import sys
sys.path.append('..')
from config.settings import DJANGO_DB, AUTH_DB, MigrationMode
from base_migrator import BaseMigrator, MigrationResult


class UserMigrator(BaseMigrator):
    """Migrates users from Django to auth-service"""

    @property
    def table_name(self) -> str:
        return "auth_user"

    @property
    def target_table_name(self) -> str:
        return "users"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Django user to auth-service user format"""
        return {
            "legacy_id": record["id"],
            "username": record["username"],
            "email": record["email"],
            "password_hash": record["password"],  # Already hashed by Django
            "first_name": record.get("first_name", ""),
            "last_name": record.get("last_name", ""),
            "is_active": bool(record.get("is_active", True)),
            "is_staff": bool(record.get("is_staff", False)),
            "is_superuser": bool(record.get("is_superuser", False)),
            "created_at": record.get("date_joined") or datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login_at": record.get("last_login"),
            "email_verified": True,  # Assume verified for migrated users
            "migration_source": "django_auth_user",
            "migrated_at": datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        """Get INSERT query for users table"""
        return """
            INSERT INTO users (
                legacy_id, username, email, password_hash,
                first_name, last_name, is_active, is_staff, is_superuser,
                created_at, updated_at, last_login_at, email_verified,
                migration_source, migrated_at
            ) VALUES (
                :legacy_id, :username, :email, :password_hash,
                :first_name, :last_name, :is_active, :is_staff, :is_superuser,
                :created_at, :updated_at, :last_login_at, :email_verified,
                :migration_source, :migrated_at
            )
            ON DUPLICATE KEY UPDATE
                last_login_at = VALUES(last_login_at),
                updated_at = VALUES(updated_at)
        """

    def pre_migration_check(self) -> bool:
        """Verify target table structure exists"""
        if not self.target_engine:
            self.logger.error("Target database not configured")
            return False

        try:
            with self.target_engine.connect() as conn:
                result = conn.execute(
                    "SHOW TABLES LIKE 'users'"
                )
                if not result.fetchone():
                    self.logger.error("Target 'users' table does not exist")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Pre-migration check failed: {e}")
            return False

    def post_migration_verify(self) -> Dict[str, Any]:
        """Verify migration data integrity"""
        verification = self.verify()

        # Additional checks
        with self.source_engine.connect() as src_conn:
            # Check specific users migrated correctly
            from sqlalchemy import text
            sample_users = src_conn.execute(
                text("SELECT id, username, email FROM auth_user ORDER BY id LIMIT 5")
            ).fetchall()

        if self.target_engine:
            with self.target_engine.connect() as tgt_conn:
                from sqlalchemy import text
                for user in sample_users:
                    result = tgt_conn.execute(
                        text("SELECT id, username, email FROM users WHERE legacy_id = :lid"),
                        {"lid": user.id}
                    ).fetchone()

                    if not result:
                        verification["sample_check_failed"] = True
                        verification["missing_user"] = user.username
                        break
                    elif result.username != user.username or result.email != user.email:
                        verification["sample_check_failed"] = True
                        verification["data_mismatch"] = user.username
                        break
                else:
                    verification["sample_check_passed"] = True

        return verification


def main():
    parser = argparse.ArgumentParser(description="Migrate users from Django to auth-service")
    parser.add_argument(
        "--mode",
        choices=["dry_run", "initial", "incremental", "verify"],
        default="dry_run",
        help="Migration mode"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for processing"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint"
    )
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("migration.users")

    # Parse mode
    mode_map = {
        "dry_run": MigrationMode.DRY_RUN,
        "initial": MigrationMode.INITIAL,
        "incremental": MigrationMode.INCREMENTAL,
        "verify": MigrationMode.VERIFY,
    }
    mode = mode_map[args.mode]

    # Create migrator
    migrator = UserMigrator(
        source_db=DJANGO_DB,
        target_db=AUTH_DB,
        mode=mode,
        batch_size=args.batch_size,
        logger=logger
    )

    if args.mode == "verify":
        # Just verify
        result = migrator.post_migration_verify()
        print("\n=== Migration Verification ===")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return

    # Run migration
    result = migrator.run(resume=args.resume)

    # Print results
    print("\n=== Migration Results ===")
    print(f"  Table: {result.table_name}")
    print(f"  Status: {result.status.value}")
    print(f"  Records Processed: {result.records_processed}")
    print(f"  Records Migrated: {result.records_migrated}")
    print(f"  Records Skipped: {result.records_skipped}")
    print(f"  Records Failed: {result.records_failed}")
    print(f"  Duration: {result.duration_seconds:.2f} seconds")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for error in result.errors[:10]:
            print(f"    - {error}")


if __name__ == "__main__":
    main()
