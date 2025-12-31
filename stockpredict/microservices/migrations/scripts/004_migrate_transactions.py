#!/usr/bin/env python3
"""
Transaction History Migration Script
Migrates stock transactions from Django to portfolio-service

Migration Order: 4 (After portfolios and holdings)

Usage:
    python 004_migrate_transactions.py --mode dry_run
    python 004_migrate_transactions.py --mode initial
"""
import argparse
import logging
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal

import sys
sys.path.append('..')
from config.settings import (
    DJANGO_DB, PORTFOLIO_DB, AUTH_DB, STOCK_DATA_DB, MigrationMode
)
from base_migrator import BaseMigrator, MigrationResult


class TransactionMigrator(BaseMigrator):
    """Migrates stock transactions from Django to portfolio-service"""

    def __init__(
        self,
        *args,
        portfolio_id_map: Dict[int, int] = None,
        holding_id_map: Dict[int, int] = None,
        company_id_map: Dict[int, int] = None,
        user_id_map: Dict[int, int] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.portfolio_id_map = portfolio_id_map or {}
        self.holding_id_map = holding_id_map or {}
        self.company_id_map = company_id_map or {}
        self.user_id_map = user_id_map or {}

    @property
    def table_name(self) -> str:
        return "stock_transaction"

    @property
    def target_table_name(self) -> str:
        return "transactions"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        # Map IDs
        legacy_portfolio_id = record.get("portfolio_id")
        new_portfolio_id = self.portfolio_id_map.get(legacy_portfolio_id)

        legacy_holding_id = record.get("holding_id")
        new_holding_id = self.holding_id_map.get(legacy_holding_id) if legacy_holding_id else None

        legacy_company_id = record.get("company_id") or record.get("stock_id")
        new_company_id = self.company_id_map.get(legacy_company_id)

        legacy_user_id = record.get("user_id")
        new_user_id = self.user_id_map.get(legacy_user_id)

        # Map transaction type
        tx_type_mapping = {
            "buy": "BUY",
            "sell": "SELL",
            "dividend": "DIVIDEND",
            "split": "SPLIT",
            "transfer_in": "TRANSFER_IN",
            "transfer_out": "TRANSFER_OUT",
            "deposit": "DEPOSIT",
            "withdrawal": "WITHDRAWAL",
        }
        tx_type = tx_type_mapping.get(
            record.get("transaction_type", "buy").lower(),
            "BUY"
        )

        # Calculate total amount
        quantity = Decimal(str(record.get("quantity", 0)))
        price = Decimal(str(record.get("price", 0)))
        fees = Decimal(str(record.get("fees", 0) or record.get("commission", 0)))
        total_amount = (quantity * price) + fees

        return {
            "legacy_id": record["id"],
            "portfolio_id": new_portfolio_id,
            "holding_id": new_holding_id,
            "company_id": new_company_id,
            "user_id": new_user_id,
            "symbol": record.get("symbol", "").upper(),
            "transaction_type": tx_type,
            "quantity": quantity,
            "price": price,
            "total_amount": total_amount,
            "fees": fees,
            "currency": record.get("currency", "USD"),
            "exchange_rate": Decimal(str(record.get("exchange_rate", 1))),
            "transaction_date": record.get("transaction_date") or record.get("date"),
            "settlement_date": record.get("settlement_date"),
            "notes": record.get("notes", ""),
            "external_id": record.get("external_id") or record.get("broker_transaction_id"),
            "source": record.get("source", "manual"),
            "created_at": record.get("created_at") or datetime.utcnow(),
            "updated_at": record.get("updated_at") or datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO transactions (
                legacy_id, portfolio_id, holding_id, company_id, user_id,
                symbol, transaction_type, quantity, price, total_amount,
                fees, currency, exchange_rate, transaction_date, settlement_date,
                notes, external_id, source, created_at, updated_at
            ) VALUES (
                :legacy_id, :portfolio_id, :holding_id, :company_id, :user_id,
                :symbol, :transaction_type, :quantity, :price, :total_amount,
                :fees, :currency, :exchange_rate, :transaction_date, :settlement_date,
                :notes, :external_id, :source, :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                notes = VALUES(notes),
                updated_at = VALUES(updated_at)
        """


def load_id_mapping(connection_string: str, table: str) -> Dict[int, int]:
    """Load legacy_id -> id mapping from a table"""
    from sqlalchemy import text, create_engine

    engine = create_engine(connection_string)
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
    finally:
        engine.dispose()

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Migrate transactions from Django")
    parser.add_argument(
        "--mode",
        choices=["dry_run", "initial", "incremental", "verify"],
        default="dry_run",
        help="Migration mode"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Batch size for processing (larger for transactions)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("migration.transactions")

    mode_map = {
        "dry_run": MigrationMode.DRY_RUN,
        "initial": MigrationMode.INITIAL,
        "incremental": MigrationMode.INCREMENTAL,
        "verify": MigrationMode.VERIFY,
    }
    mode = mode_map[args.mode]

    # Load ID mappings from previously migrated tables
    logger.info("Loading ID mappings from previous migrations...")

    if mode != MigrationMode.DRY_RUN:
        user_id_map = load_id_mapping(AUTH_DB.connection_string, "users")
        logger.info(f"Loaded {len(user_id_map)} user mappings")

        company_id_map = load_id_mapping(STOCK_DATA_DB.connection_string, "companies")
        logger.info(f"Loaded {len(company_id_map)} company mappings")

        portfolio_id_map = load_id_mapping(PORTFOLIO_DB.connection_string, "portfolios")
        logger.info(f"Loaded {len(portfolio_id_map)} portfolio mappings")

        holding_id_map = load_id_mapping(PORTFOLIO_DB.connection_string, "holdings")
        logger.info(f"Loaded {len(holding_id_map)} holding mappings")
    else:
        user_id_map = {}
        company_id_map = {}
        portfolio_id_map = {}
        holding_id_map = {}

    # Migrate Transactions
    print("\n=== Migrating Transactions ===")
    print("Note: This may take a while for large transaction histories")

    migrator = TransactionMigrator(
        source_db=DJANGO_DB,
        target_db=PORTFOLIO_DB,
        mode=mode,
        batch_size=args.batch_size,
        portfolio_id_map=portfolio_id_map,
        holding_id_map=holding_id_map,
        company_id_map=company_id_map,
        user_id_map=user_id_map
    )

    result = migrator.run(resume=args.resume)

    # Print results
    print("\n=== Migration Results ===")
    print(f"  Table: {result.table_name}")
    print(f"  Status: {result.status.value}")
    print(f"  Records Processed: {result.records_processed}")
    print(f"  Records Migrated: {result.records_migrated}")
    print(f"  Records Failed: {result.records_failed}")
    print(f"  Duration: {result.duration_seconds:.2f} seconds")

    if result.records_processed > 0:
        rate = result.records_processed / result.duration_seconds
        print(f"  Processing Rate: {rate:.0f} records/second")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)} total, showing first 10):")
        for error in result.errors[:10]:
            print(f"    - {error}")


if __name__ == "__main__":
    main()
