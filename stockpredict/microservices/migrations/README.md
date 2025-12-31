# Data Migration Scripts

Migration tools for transferring data from Django monolith to microservices architecture.

## Overview

These scripts handle the one-time migration of data from the Django `defaultdb` database to individual microservice databases, along with continuous sync capabilities during the shadow mode period.

## Directory Structure

```
migrations/
├── config/
│   └── settings.py          # Database configs and mappings
├── scripts/
│   ├── base_migrator.py     # Base migration class
│   ├── 001_migrate_users.py # User account migration
│   ├── 002_migrate_companies.py  # Company/stock data
│   ├── 003_migrate_portfolios.py # Portfolios, holdings, alerts
│   └── 004_migrate_transactions.py # Transaction history
├── verify/
│   └── verify_migration.py  # Verification and validation
├── sync/
│   └── sync_service.py      # Real-time sync during shadow mode
├── rollback/
│   └── rollback_migration.py # Emergency rollback procedures
├── run_migration.py         # Master orchestrator
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
export DJANGO_DB_HOST=mysql
export DJANGO_DB_NAME=defaultdb
export DJANGO_DB_USER=stockuser
export DJANGO_DB_PASSWORD=stockpass
```

### 3. Run Dry Run (Recommended First)

```bash
python run_migration.py --mode dry_run
```

### 4. Run Actual Migration

```bash
python run_migration.py --mode initial --confirm
```

### 5. Verify Migration

```bash
python run_migration.py --verify-only
```

## Migration Scripts

### 001_migrate_users.py

Migrates user accounts from Django `auth_user` to `auth_db.users`.

```bash
python scripts/001_migrate_users.py --mode dry_run
python scripts/001_migrate_users.py --mode initial
python scripts/001_migrate_users.py --mode verify
```

**Field Mappings:**
| Django Field | Microservice Field |
|--------------|-------------------|
| id | legacy_id |
| password | password_hash |
| date_joined | created_at |
| last_login | last_login_at |

### 002_migrate_companies.py

Migrates industries, companies, and historical prices.

```bash
python scripts/002_migrate_companies.py --mode dry_run
python scripts/002_migrate_companies.py --mode initial --skip-prices
```

**Tables Migrated:**
- `stock_industry` → `stockdata_db.industries`
- `stock_company` → `stockdata_db.companies`
- `stock_historicalprice` → `stockdata_db.historical_prices`

### 003_migrate_portfolios.py

Migrates portfolios, holdings, and price alerts.

```bash
python scripts/003_migrate_portfolios.py --mode dry_run
python scripts/003_migrate_portfolios.py --mode initial
```

**Tables Migrated:**
- `stock_portfolio` → `portfolio_db.portfolios`
- `stock_holding` → `portfolio_db.holdings`
- `stock_pricealert` → `portfolio_db.price_alerts`

### 004_migrate_transactions.py

Migrates transaction history (can be large).

```bash
python scripts/004_migrate_transactions.py --mode dry_run
python scripts/004_migrate_transactions.py --mode initial --batch-size 10000
python scripts/004_migrate_transactions.py --mode initial --resume
```

**Features:**
- Checkpoint support for resumable migrations
- Large batch processing
- ID mapping for foreign keys

## Migration Modes

| Mode | Description |
|------|-------------|
| `dry_run` | Simulate migration, no changes made |
| `initial` | Full migration of all records |
| `incremental` | Sync only new/changed records |
| `verify` | Verify migration completeness |

## Verification

The verification script checks:

1. **Record Counts**: Source and target table counts match
2. **Sample Data**: Random samples verified for accuracy
3. **Referential Integrity**: Foreign key relationships intact
4. **Data Integrity Score**: Percentage of correctly migrated records

```bash
# Full verification
python verify/verify_migration.py --full

# Specific table
python verify/verify_migration.py --table users --sample 500

# Save report
python verify/verify_migration.py --full --output report.json
```

## Continuous Sync

During shadow mode, run the sync service to keep data synchronized:

```bash
# Sync all tables
python sync/sync_service.py --all

# Sync specific tables
python sync/sync_service.py --tables users,portfolios
```

The sync service:
- Listens to RabbitMQ for Django change events
- Replicates changes to microservice databases
- Handles INSERT, UPDATE, DELETE operations
- Maintains data consistency during transition

## Rollback

Emergency rollback procedures:

```bash
# Dry run (see what would be deleted)
python rollback/rollback_migration.py --all --dry-run

# Rollback specific table
python rollback/rollback_migration.py --table users --confirm

# Rollback all tables
python rollback/rollback_migration.py --all --confirm

# Verify rollback
python rollback/rollback_migration.py --verify
```

**Warning:** Rollback deletes all records with `legacy_id IS NOT NULL` from target tables.

## ID Mapping

Foreign key relationships are maintained through ID mapping:

1. Each migrated record stores `legacy_id` (original Django ID)
2. Subsequent migrations use legacy_id lookups to map relationships
3. Example: Portfolio migration looks up user's new ID via `SELECT id FROM users WHERE legacy_id = ?`

## Checkpoints

Long-running migrations support checkpoints:

- Checkpoints saved every 100 batches
- Resume with `--resume` flag
- Checkpoint files stored in `/tmp/migration_checkpoint_*.json`

## Best Practices

1. **Always run dry_run first** to verify configuration
2. **Backup databases** before running initial migration
3. **Run during low-traffic periods** to minimize sync conflicts
4. **Monitor verification scores** - target >99% integrity
5. **Keep sync service running** throughout shadow mode
6. **Test rollback procedures** before production migration

## Troubleshooting

### Connection Errors

```bash
# Verify database connectivity
mysql -h $DJANGO_DB_HOST -u $DJANGO_DB_USER -p$DJANGO_DB_PASSWORD -e "SELECT 1"
```

### Missing Records

Check verification output for specific missing records:
```bash
python verify/verify_migration.py --table portfolios --sample 1000 --output debug.json
```

### Foreign Key Failures

Ensure migrations run in order:
1. Users first
2. Companies second
3. Portfolios third
4. Transactions last

### Resume After Failure

```bash
python scripts/004_migrate_transactions.py --mode initial --resume
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_DB_HOST` | mysql | Source database host |
| `DJANGO_DB_NAME` | defaultdb | Source database name |
| `AUTH_DB_HOST` | mysql | Auth service database |
| `STOCK_DATA_DB_HOST` | mysql | Stock data database |
| `PORTFOLIO_DB_HOST` | mysql | Portfolio database |
| `MIGRATION_BATCH_SIZE` | 1000 | Records per batch |
| `MIGRATION_WORKERS` | 4 | Parallel workers |
| `MIGRATION_CHECKPOINT` | true | Enable checkpoints |

## Timeline

| Phase | Activity |
|-------|----------|
| Pre-migration | Backup databases, verify connectivity |
| Initial Load | Run all migration scripts |
| Verification | Verify counts and sample data |
| Shadow Mode | Run sync service, compare responses |
| Cutover | Stop sync, switch to microservices |
| Post-migration | Final verification, archive Django data |
