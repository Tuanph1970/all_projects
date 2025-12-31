#!/usr/bin/env python3
"""
Portfolio Migration Script
Migrates portfolios, holdings, and alerts from Django to portfolio-service

Migration Order: 3 (After users and companies)

Usage:
    python 003_migrate_portfolios.py --mode dry_run
    python 003_migrate_portfolios.py --mode initial
"""
import argparse
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

import sys
sys.path.append('..')
from config.settings import (
    DJANGO_DB, PORTFOLIO_DB, AUTH_DB, STOCK_DATA_DB, MigrationMode
)
from base_migrator import BaseMigrator, MigrationResult


class PortfolioMigrator(BaseMigrator):
    """Migrates portfolios from Django to portfolio-service"""

    def __init__(self, *args, user_id_map: Dict[int, int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id_map = user_id_map or {}

    @property
    def table_name(self) -> str:
        return "stock_portfolio"

    @property
    def target_table_name(self) -> str:
        return "portfolios"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        legacy_user_id = record.get("user_id")
        new_user_id = self.user_id_map.get(legacy_user_id) if legacy_user_id else None

        if not new_user_id and self.mode != MigrationMode.DRY_RUN:
            self.logger.warning(
                f"No user mapping for portfolio {record['id']} (user_id={legacy_user_id})"
            )

        return {
            "legacy_id": record["id"],
            "user_id": new_user_id,
            "name": record["name"],
            "description": record.get("description", ""),
            "is_default": bool(record.get("is_default", False)),
            "is_public": bool(record.get("is_public", False)),
            "currency": record.get("currency", "USD"),
            "initial_balance": Decimal(str(record.get("initial_balance", 0))),
            "created_at": record.get("created") or record.get("created_at") or datetime.utcnow(),
            "updated_at": record.get("modified") or record.get("updated_at") or datetime.utcnow(),
            "migration_source": "django_portfolio",
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO portfolios (
                legacy_id, user_id, name, description,
                is_default, is_public, currency, initial_balance,
                created_at, updated_at, migration_source
            ) VALUES (
                :legacy_id, :user_id, :name, :description,
                :is_default, :is_public, :currency, :initial_balance,
                :created_at, :updated_at, :migration_source
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                description = VALUES(description),
                updated_at = VALUES(updated_at)
        """


class HoldingMigrator(BaseMigrator):
    """Migrates holdings from Django to portfolio-service"""

    def __init__(
        self,
        *args,
        portfolio_id_map: Dict[int, int] = None,
        company_id_map: Dict[int, int] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.portfolio_id_map = portfolio_id_map or {}
        self.company_id_map = company_id_map or {}

    @property
    def table_name(self) -> str:
        return "stock_holding"

    @property
    def target_table_name(self) -> str:
        return "holdings"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        legacy_portfolio_id = record.get("portfolio_id")
        new_portfolio_id = self.portfolio_id_map.get(legacy_portfolio_id)

        legacy_company_id = record.get("company_id") or record.get("stock_id")
        new_company_id = self.company_id_map.get(legacy_company_id)

        return {
            "legacy_id": record["id"],
            "portfolio_id": new_portfolio_id,
            "company_id": new_company_id,
            "symbol": record.get("symbol", "").upper(),
            "quantity": Decimal(str(record.get("quantity", 0))),
            "average_cost": Decimal(str(record.get("average_cost", 0))),
            "current_price": Decimal(str(record.get("current_price", 0))),
            "purchase_date": record.get("purchase_date") or record.get("first_purchase_date"),
            "notes": record.get("notes", ""),
            "created_at": record.get("created_at") or datetime.utcnow(),
            "updated_at": record.get("updated_at") or datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO holdings (
                legacy_id, portfolio_id, company_id, symbol,
                quantity, average_cost, current_price, purchase_date,
                notes, created_at, updated_at
            ) VALUES (
                :legacy_id, :portfolio_id, :company_id, :symbol,
                :quantity, :average_cost, :current_price, :purchase_date,
                :notes, :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                quantity = VALUES(quantity),
                current_price = VALUES(current_price),
                updated_at = VALUES(updated_at)
        """


class AlertMigrator(BaseMigrator):
    """Migrates price alerts from Django to portfolio-service"""

    def __init__(
        self,
        *args,
        user_id_map: Dict[int, int] = None,
        company_id_map: Dict[int, int] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.user_id_map = user_id_map or {}
        self.company_id_map = company_id_map or {}

    @property
    def table_name(self) -> str:
        return "stock_pricealert"

    @property
    def target_table_name(self) -> str:
        return "price_alerts"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        legacy_user_id = record.get("user_id")
        new_user_id = self.user_id_map.get(legacy_user_id)

        legacy_company_id = record.get("company_id") or record.get("stock_id")
        new_company_id = self.company_id_map.get(legacy_company_id)

        # Map alert type
        alert_type_mapping = {
            "above": "price_above",
            "below": "price_below",
            "percent_change": "percent_change",
            "volume": "volume_spike",
        }
        alert_type = alert_type_mapping.get(
            record.get("alert_type", "above"),
            "price_above"
        )

        return {
            "legacy_id": record["id"],
            "user_id": new_user_id,
            "company_id": new_company_id,
            "symbol": record.get("symbol", "").upper(),
            "alert_type": alert_type,
            "target_price": Decimal(str(record.get("target_price", 0))),
            "comparison": record.get("comparison", ">="),
            "is_active": bool(record.get("is_active", True)),
            "is_triggered": bool(record.get("is_triggered", False)),
            "triggered_at": record.get("triggered_at"),
            "notification_method": record.get("notification_method", "email"),
            "created_at": record.get("created_at") or datetime.utcnow(),
            "updated_at": record.get("updated_at") or datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO price_alerts (
                legacy_id, user_id, company_id, symbol,
                alert_type, target_price, comparison,
                is_active, is_triggered, triggered_at,
                notification_method, created_at, updated_at
            ) VALUES (
                :legacy_id, :user_id, :company_id, :symbol,
                :alert_type, :target_price, :comparison,
                :is_active, :is_triggered, :triggered_at,
                :notification_method, :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                is_triggered = VALUES(is_triggered),
                triggered_at = VALUES(triggered_at),
                updated_at = VALUES(updated_at)
        """


def load_id_mapping(engine, table: str) -> Dict[int, int]:
    """Load legacy_id -> id mapping from a table"""
    from sqlalchemy import text, create_engine

    if isinstance(engine, str):
        engine = create_engine(engine)

    mapping = {}
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                f"SELECT id, legacy_id FROM {table} WHERE legacy_id IS NOT NULL"
            ))
            for row in result:
                mapping[row.legacy_id] = row.id
    except Exception as e:
        logging.warning(f"Could not load mapping from {table}: {e}")

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Migrate portfolios from Django")
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
        "--skip-alerts",
        action="store_true",
        help="Skip price alerts migration"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("migration.portfolios")

    mode_map = {
        "dry_run": MigrationMode.DRY_RUN,
        "initial": MigrationMode.INITIAL,
        "incremental": MigrationMode.INCREMENTAL,
        "verify": MigrationMode.VERIFY,
    }
    mode = mode_map[args.mode]

    results = []

    # Load ID mappings from previously migrated tables
    from sqlalchemy import create_engine

    logger.info("Loading ID mappings from previous migrations...")

    if mode != MigrationMode.DRY_RUN:
        auth_engine = create_engine(AUTH_DB.connection_string)
        user_id_map = load_id_mapping(auth_engine, "users")
        auth_engine.dispose()
        logger.info(f"Loaded {len(user_id_map)} user mappings")

        stock_engine = create_engine(STOCK_DATA_DB.connection_string)
        company_id_map = load_id_mapping(stock_engine, "companies")
        stock_engine.dispose()
        logger.info(f"Loaded {len(company_id_map)} company mappings")
    else:
        user_id_map = {}
        company_id_map = {}

    # Step 1: Migrate Portfolios
    print("\n=== Step 1: Migrating Portfolios ===")
    portfolio_migrator = PortfolioMigrator(
        source_db=DJANGO_DB,
        target_db=PORTFOLIO_DB,
        mode=mode,
        batch_size=args.batch_size,
        user_id_map=user_id_map
    )
    result = portfolio_migrator.run()
    results.append(result)
    print(f"Portfolios: {result.records_migrated} migrated, {result.records_failed} failed")

    # Build portfolio ID mapping
    if mode != MigrationMode.DRY_RUN:
        portfolio_engine = create_engine(PORTFOLIO_DB.connection_string)
        portfolio_id_map = load_id_mapping(portfolio_engine, "portfolios")
        portfolio_engine.dispose()
    else:
        portfolio_id_map = {}

    # Step 2: Migrate Holdings
    print("\n=== Step 2: Migrating Holdings ===")
    holding_migrator = HoldingMigrator(
        source_db=DJANGO_DB,
        target_db=PORTFOLIO_DB,
        mode=mode,
        batch_size=args.batch_size,
        portfolio_id_map=portfolio_id_map,
        company_id_map=company_id_map
    )
    result = holding_migrator.run()
    results.append(result)
    print(f"Holdings: {result.records_migrated} migrated, {result.records_failed} failed")

    # Step 3: Migrate Price Alerts
    if not args.skip_alerts:
        print("\n=== Step 3: Migrating Price Alerts ===")
        alert_migrator = AlertMigrator(
            source_db=DJANGO_DB,
            target_db=PORTFOLIO_DB,
            mode=mode,
            batch_size=args.batch_size,
            user_id_map=user_id_map,
            company_id_map=company_id_map
        )
        result = alert_migrator.run()
        results.append(result)
        print(f"Alerts: {result.records_migrated} migrated, {result.records_failed} failed")

    # Summary
    print("\n=== Migration Summary ===")
    total_migrated = sum(r.records_migrated for r in results)
    total_failed = sum(r.records_failed for r in results)

    for r in results:
        status_icon = "✓" if r.status.value == "completed" else "✗"
        print(f"  {status_icon} {r.table_name}: {r.records_migrated}/{r.records_processed}")

    print(f"\n  Total: {total_migrated} migrated, {total_failed} failed")


if __name__ == "__main__":
    main()
