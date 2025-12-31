#!/bin/bash
set -e

echo "=========================================="
echo "Ceramic Marketplace API - Starting"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for MySQL database..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if python << END
import sys
from sqlalchemy import create_engine
from app.core.config import settings

try:
    engine = create_engine(
        f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
        pool_pre_ping=True
    )
    conn = engine.connect()
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"Database not ready: {e}")
    sys.exit(1)
END
    then
        echo "✓ Database is ready!"
        break
    fi

    retry_count=$((retry_count + 1))
    echo "Database not ready yet. Retry $retry_count/$max_retries..."
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "✗ Failed to connect to database after $max_retries attempts"
    exit 1
fi

# Run database initialization (create tables)
echo ""
echo "Initializing database tables..."
python << END
from app.utils.database_init import create_tables
try:
    create_tables()
    print("✓ Database tables created successfully")
except Exception as e:
    print(f"Note: {e}")
    print("Tables may already exist, continuing...")
END

# Seed initial data if SEED_DATA environment variable is set
if [ "$SEED_DATA" = "true" ] || [ "$SEED_DATA" = "1" ]; then
    echo ""
    echo "Seeding database with initial data..."
    python << END
from app.utils.seed_data import seed_database
try:
    seed_database()
    print("✓ Database seeded successfully")
except Exception as e:
    print(f"Note: {e}")
    print("Seed data may already exist, continuing...")
END
fi

# Run Alembic migrations if available
if [ -d "migrations/versions" ] && [ "$(ls -A migrations/versions/*.py 2>/dev/null)" ]; then
    echo ""
    echo "Running Alembic migrations..."
    alembic upgrade head
    echo "✓ Migrations completed"
else
    echo ""
    echo "Note: No Alembic migrations found, skipping..."
fi

echo ""
echo "=========================================="
echo "Starting FastAPI application..."
echo "=========================================="

# Start the application
exec "$@"
