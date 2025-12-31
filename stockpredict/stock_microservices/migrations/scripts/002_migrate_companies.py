#!/usr/bin/env python3
"""
Company Data Migration Script
Migrates company and industry data from Django to stock-data-service

Migration Order: 2 (Before portfolios which reference companies)

Usage:
    python 002_migrate_companies.py --mode dry_run
    python 002_migrate_companies.py --mode initial
"""
import argparse
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

import sys
sys.path.append('..')
from config.settings import DJANGO_DB, STOCK_DATA_DB, MigrationMode
from base_migrator import BaseMigrator, MigrationResult


class IndustryMigrator(BaseMigrator):
    """Migrates industries from Django to stock-data-service"""

    @property
    def table_name(self) -> str:
        return "stock_industry"

    @property
    def target_table_name(self) -> str:
        return "industries"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "legacy_id": record["id"],
            "name": record["name"],
            "sector": record.get("sector", "Unknown"),
            "description": record.get("description", ""),
            "created_at": record.get("created_at") or datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO industries (
                legacy_id, name, sector, description,
                created_at, updated_at
            ) VALUES (
                :legacy_id, :name, :sector, :description,
                :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                updated_at = VALUES(updated_at)
        """


class CompanyMigrator(BaseMigrator):
    """Migrates companies from Django to stock-data-service"""

    def __init__(self, *args, industry_id_map: Dict[int, int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.industry_id_map = industry_id_map or {}

    @property
    def table_name(self) -> str:
        return "stock_company"

    @property
    def target_table_name(self) -> str:
        return "companies"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        # Map legacy industry_id to new industry_id
        legacy_industry_id = record.get("industry_id")
        new_industry_id = self.industry_id_map.get(legacy_industry_id) if legacy_industry_id else None

        return {
            "legacy_id": record["id"],
            "symbol": record["symbol"].upper(),
            "name": record["name"],
            "industry_id": new_industry_id,
            "exchange": record.get("exchange", "UNKNOWN"),
            "market_cap": record.get("market_cap"),
            "website": record.get("website"),
            "description": record.get("description", ""),
            "ceo": record.get("ceo"),
            "employees": record.get("employees"),
            "founded": record.get("founded"),
            "headquarters": record.get("headquarters"),
            "is_active": bool(record.get("is_active", True)),
            "created_at": record.get("created_at") or datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO companies (
                legacy_id, symbol, name, industry_id, exchange,
                market_cap, website, description, ceo, employees,
                founded, headquarters, is_active, created_at, updated_at
            ) VALUES (
                :legacy_id, :symbol, :name, :industry_id, :exchange,
                :market_cap, :website, :description, :ceo, :employees,
                :founded, :headquarters, :is_active, :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                market_cap = VALUES(market_cap),
                is_active = VALUES(is_active),
                updated_at = VALUES(updated_at)
        """


class HistoricalPriceMigrator(BaseMigrator):
    """Migrates historical prices from Django to stock-data-service"""

    def __init__(self, *args, company_id_map: Dict[int, int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_id_map = company_id_map or {}

    @property
    def table_name(self) -> str:
        return "stock_historicalprice"

    @property
    def target_table_name(self) -> str:
        return "historical_prices"

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        legacy_company_id = record.get("company_id")
        new_company_id = self.company_id_map.get(legacy_company_id) if legacy_company_id else None

        return {
            "legacy_id": record["id"],
            "company_id": new_company_id,
            "date": record["date"],
            "open_price": record.get("open") or record.get("open_price"),
            "high_price": record.get("high") or record.get("high_price"),
            "low_price": record.get("low") or record.get("low_price"),
            "close_price": record.get("close") or record.get("close_price"),
            "adj_close": record.get("adj_close") or record.get("adjusted_close"),
            "volume": record.get("volume", 0),
            "created_at": datetime.utcnow(),
        }

    def get_insert_query(self) -> str:
        return """
            INSERT INTO historical_prices (
                legacy_id, company_id, date, open_price, high_price,
                low_price, close_price, adj_close, volume, created_at
            ) VALUES (
                :legacy_id, :company_id, :date, :open_price, :high_price,
                :low_price, :close_price, :adj_close, :volume, :created_at
            )
            ON DUPLICATE KEY UPDATE
                close_price = VALUES(close_price),
                volume = VALUES(volume)
        """


def build_id_mapping(
    source_engine,
    target_engine,
    source_table: str,
    target_table: str
) -> Dict[int, int]:
    """Build mapping from legacy IDs to new IDs"""
    from sqlalchemy import text

    mapping = {}
    with target_engine.connect() as conn:
        result = conn.execute(text(
            f"SELECT id, legacy_id FROM {target_table} WHERE legacy_id IS NOT NULL"
        ))
        for row in result:
            mapping[row.legacy_id] = row.id

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Migrate company data from Django")
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
        "--skip-prices",
        action="store_true",
        help="Skip historical prices migration (can be very large)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    mode_map = {
        "dry_run": MigrationMode.DRY_RUN,
        "initial": MigrationMode.INITIAL,
        "incremental": MigrationMode.INCREMENTAL,
        "verify": MigrationMode.VERIFY,
    }
    mode = mode_map[args.mode]

    results = []

    # Step 1: Migrate Industries
    print("\n=== Step 1: Migrating Industries ===")
    industry_migrator = IndustryMigrator(
        source_db=DJANGO_DB,
        target_db=STOCK_DATA_DB,
        mode=mode,
        batch_size=args.batch_size
    )
    result = industry_migrator.run()
    results.append(result)
    print(f"Industries: {result.records_migrated} migrated, {result.records_failed} failed")

    # Build industry ID mapping
    from sqlalchemy import create_engine
    if mode != MigrationMode.DRY_RUN:
        target_engine = create_engine(STOCK_DATA_DB.connection_string)
        industry_id_map = build_id_mapping(
            industry_migrator.source_engine,
            target_engine,
            "stock_industry",
            "industries"
        )
        target_engine.dispose()
    else:
        industry_id_map = {}

    # Step 2: Migrate Companies
    print("\n=== Step 2: Migrating Companies ===")
    company_migrator = CompanyMigrator(
        source_db=DJANGO_DB,
        target_db=STOCK_DATA_DB,
        mode=mode,
        batch_size=args.batch_size,
        industry_id_map=industry_id_map
    )
    result = company_migrator.run()
    results.append(result)
    print(f"Companies: {result.records_migrated} migrated, {result.records_failed} failed")

    # Build company ID mapping
    if mode != MigrationMode.DRY_RUN:
        target_engine = create_engine(STOCK_DATA_DB.connection_string)
        company_id_map = build_id_mapping(
            company_migrator.source_engine,
            target_engine,
            "stock_company",
            "companies"
        )
        target_engine.dispose()
    else:
        company_id_map = {}

    # Step 3: Migrate Historical Prices (optional)
    if not args.skip_prices:
        print("\n=== Step 3: Migrating Historical Prices ===")
        print("WARNING: This may take a long time for large datasets")
        price_migrator = HistoricalPriceMigrator(
            source_db=DJANGO_DB,
            target_db=STOCK_DATA_DB,
            mode=mode,
            batch_size=args.batch_size * 10,  # Larger batches for prices
            company_id_map=company_id_map
        )
        result = price_migrator.run()
        results.append(result)
        print(f"Prices: {result.records_migrated} migrated, {result.records_failed} failed")

    # Summary
    print("\n=== Migration Summary ===")
    for r in results:
        status_icon = "✓" if r.status.value == "completed" else "✗"
        print(f"  {status_icon} {r.table_name}: {r.records_migrated}/{r.records_processed} records")


if __name__ == "__main__":
    main()
