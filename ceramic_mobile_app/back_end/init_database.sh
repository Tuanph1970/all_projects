#!/bin/bash

# Database Initialization Script for Ceramic Marketplace
# This script creates the database and initializes tables

set -e

echo "========================================"
echo "Database Initialization"
echo "========================================"
echo ""

# Database configuration
DB_HOST="112.213.91.103"
DB_PORT="3306"
DB_NAME="ceramic_marketplace"
DB_USER="root"
DB_PASS="MySql_2025"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if MySQL is accessible
echo "Checking MySQL connection..."
if mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MySQL connection successful${NC}"
else
    echo -e "${RED}✗ MySQL connection failed${NC}"
    echo "Please check your MySQL credentials and ensure MySQL is running"
    exit 1
fi

# Create database if not exists
echo ""
echo "Creating database..."
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
echo -e "${GREEN}✓ Database created/verified${NC}"

# Grant permissions
echo ""
echo "Granting permissions..."
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%'; FLUSH PRIVILEGES;" 2>/dev/null
echo -e "${GREEN}✓ Permissions granted${NC}"

# Show databases
echo ""
echo "Current databases:"
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e "SHOW DATABASES;" 2>/dev/null | grep -v "information_schema\|performance_schema\|mysql\|sys"

# Initialize tables (run this after application is deployed)
echo ""
echo -e "${YELLOW}Note: Tables will be created when you run:${NC}"
echo "  docker exec ceramic_api_prod python -m app.utils.database_init"

echo ""
echo -e "${GREEN}========================================"
echo "Database initialization complete!"
echo "========================================${NC}"
