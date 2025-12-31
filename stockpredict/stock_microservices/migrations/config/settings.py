"""
Migration Configuration Settings
Defines database connections and migration parameters
"""
import os
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class MigrationMode(Enum):
    """Migration execution modes"""
    DRY_RUN = "dry_run"           # Simulate without changes
    INITIAL = "initial"           # Full initial migration
    INCREMENTAL = "incremental"   # Sync new/changed records
    VERIFY = "verify"             # Verification only


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def connection_string(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_connection_string(self) -> str:
        return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


# Source Database (Django Monolith)
DJANGO_DB = DatabaseConfig(
    host=os.getenv("DJANGO_DB_HOST", "mysql"),
    port=int(os.getenv("DJANGO_DB_PORT", "3306")),
    database=os.getenv("DJANGO_DB_NAME", "defaultdb"),
    user=os.getenv("DJANGO_DB_USER", "stockuser"),
    password=os.getenv("DJANGO_DB_PASSWORD", "stockpass")
)

# Target Databases (Microservices)
AUTH_DB = DatabaseConfig(
    host=os.getenv("AUTH_DB_HOST", "mysql"),
    port=int(os.getenv("AUTH_DB_PORT", "3306")),
    database=os.getenv("AUTH_DB_NAME", "auth_db"),
    user=os.getenv("AUTH_DB_USER", "stockuser"),
    password=os.getenv("AUTH_DB_PASSWORD", "stockpass")
)

STOCK_DATA_DB = DatabaseConfig(
    host=os.getenv("STOCK_DATA_DB_HOST", "mysql"),
    port=int(os.getenv("STOCK_DATA_DB_PORT", "3306")),
    database=os.getenv("STOCK_DATA_DB_NAME", "stockdata_db"),
    user=os.getenv("STOCK_DATA_DB_USER", "stockuser"),
    password=os.getenv("STOCK_DATA_DB_PASSWORD", "stockpass")
)

PORTFOLIO_DB = DatabaseConfig(
    host=os.getenv("PORTFOLIO_DB_HOST", "mysql"),
    port=int(os.getenv("PORTFOLIO_DB_PORT", "3306")),
    database=os.getenv("PORTFOLIO_DB_NAME", "portfolio_db"),
    user=os.getenv("PORTFOLIO_DB_USER", "stockuser"),
    password=os.getenv("PORTFOLIO_DB_PASSWORD", "stockpass")
)

PREDICTION_DB = DatabaseConfig(
    host=os.getenv("PREDICTION_DB_HOST", "mysql"),
    port=int(os.getenv("PREDICTION_DB_PORT", "3306")),
    database=os.getenv("PREDICTION_DB_NAME", "prediction_db"),
    user=os.getenv("PREDICTION_DB_USER", "stockuser"),
    password=os.getenv("PREDICTION_DB_PASSWORD", "stockpass")
)

ANALYSIS_DB = DatabaseConfig(
    host=os.getenv("ANALYSIS_DB_HOST", "mysql"),
    port=int(os.getenv("ANALYSIS_DB_PORT", "3306")),
    database=os.getenv("ANALYSIS_DB_NAME", "analysis_db"),
    user=os.getenv("ANALYSIS_DB_USER", "stockuser"),
    password=os.getenv("ANALYSIS_DB_PASSWORD", "stockpass")
)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# RabbitMQ Configuration
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://stockuser:stockpass@rabbitmq:5672/")

# Migration Settings
MIGRATION_CONFIG: Dict[str, Any] = {
    "batch_size": int(os.getenv("MIGRATION_BATCH_SIZE", "1000")),
    "parallel_workers": int(os.getenv("MIGRATION_WORKERS", "4")),
    "retry_attempts": int(os.getenv("MIGRATION_RETRIES", "3")),
    "retry_delay_seconds": int(os.getenv("MIGRATION_RETRY_DELAY", "5")),
    "log_level": os.getenv("MIGRATION_LOG_LEVEL", "INFO"),
    "checkpoint_enabled": os.getenv("MIGRATION_CHECKPOINT", "true").lower() == "true",
    "checkpoint_interval": int(os.getenv("MIGRATION_CHECKPOINT_INTERVAL", "100")),
}

# Table Mappings: Django table -> (target_db, target_table)
TABLE_MAPPINGS = {
    # Auth tables
    "auth_user": (AUTH_DB, "users"),
    "auth_user_groups": (AUTH_DB, "user_groups"),
    "authtoken_token": (AUTH_DB, "tokens"),

    # Stock data tables
    "stock_company": (STOCK_DATA_DB, "companies"),
    "stock_industry": (STOCK_DATA_DB, "industries"),
    "stock_historicalprice": (STOCK_DATA_DB, "historical_prices"),

    # Portfolio tables
    "stock_portfolio": (PORTFOLIO_DB, "portfolios"),
    "stock_holding": (PORTFOLIO_DB, "holdings"),
    "stock_transaction": (PORTFOLIO_DB, "transactions"),
    "stock_pricealert": (PORTFOLIO_DB, "price_alerts"),

    # Prediction tables
    "ml_model": (PREDICTION_DB, "models"),
    "ml_prediction": (PREDICTION_DB, "predictions"),
    "ml_trainingrun": (PREDICTION_DB, "training_runs"),

    # Analysis tables
    "analysis_report": (ANALYSIS_DB, "reports"),
    "analysis_screenerconfig": (ANALYSIS_DB, "screener_configs"),
}

# Field Mappings: Transformations for specific fields
FIELD_MAPPINGS = {
    "auth_user": {
        "id": "legacy_id",
        "date_joined": "created_at",
        "last_login": "last_login_at",
        "password": "password_hash",
    },
    "stock_portfolio": {
        "id": "legacy_id",
        "user_id": "user_id",  # Will need lookup
        "created": "created_at",
        "modified": "updated_at",
    },
}

# Validation Rules
VALIDATION_RULES = {
    "auth_user": {
        "required_fields": ["username", "email", "password"],
        "unique_fields": ["username", "email"],
        "min_count": 1,  # At least 1 user expected
    },
    "stock_portfolio": {
        "required_fields": ["name", "user_id"],
        "unique_fields": [],
        "min_count": 0,
    },
}
