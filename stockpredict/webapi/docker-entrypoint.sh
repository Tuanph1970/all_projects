#!/bin/bash
# =============================================================================
# Stock Predict WebAPI - Docker Entrypoint Script
# =============================================================================

set -e

# Wait for database to be ready (optional)
wait_for_db() {
    echo "Waiting for database..."
    while ! python -c "
import os
import pymysql
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'defaultdb'),
        port=int(os.getenv('DB_PORT', 3306))
    )
    conn.close()
    exit(0)
except Exception as e:
    print(f'Database not ready: {e}')
    exit(1)
" 2>/dev/null; do
        echo "Database is unavailable - sleeping 5s"
        sleep 5
    done
    echo "Database is up!"
}

# Run migrations
run_migrations() {
    echo "Running database migrations..."
    python manage.py migrate --noinput
}

# Collect static files (for production)
collect_static() {
    if [ "$DJANGO_DEBUG" = "False" ] || [ "$DJANGO_DEBUG" = "false" ]; then
        echo "Collecting static files..."
        python manage.py collectstatic --noinput
    fi
}

# Main execution
main() {
    # Wait for database if DB_HOST is set
    if [ -n "$DB_HOST" ]; then
        wait_for_db
    fi

    # Run migrations
    run_migrations

    # Collect static files
    collect_static

    # Execute the main command
    echo "Starting application..."
    exec "$@"
}

# Run main function with all arguments
main "$@"
