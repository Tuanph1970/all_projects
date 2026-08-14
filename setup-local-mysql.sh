#!/bin/bash
# =============================================================================
# MySQL Database Setup Script for All Projects
# =============================================================================
# This script creates all required databases and users for local development
# Run this script once to set up your local MySQL server
#
# Usage:
#   chmod +x setup-local-mysql.sh
#   ./setup-local-mysql.sh
#
# Prerequisites:
#   - MySQL server running locally
#   - Root access to MySQL
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-Mysql_2025}"
DEFAULT_USER_PASSWORD="${DEFAULT_USER_PASSWORD:-Mysql_2025}"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  MySQL Database Setup for All Projects${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# Check if MySQL is running
check_mysql() {
    echo -e "${YELLOW}Checking MySQL service...${NC}"
    if command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mariadb 2>/dev/null; then
            echo -e "${GREEN}✓ MySQL service is running${NC}"
            return 0
        fi
    fi

    # Try to connect directly
    if mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" &>/dev/null; then
        echo -e "${GREEN}✓ MySQL is accessible${NC}"
        return 0
    fi

    echo -e "${RED}✗ MySQL is not running or not accessible${NC}"
    echo -e "${YELLOW}Please start MySQL: sudo systemctl start mysql${NC}"
    exit 1
}

# Function to run MySQL command
run_mysql() {
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "$1" 2>/dev/null
}

# Function to check if database exists
db_exists() {
    result=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -N -e "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='$1'" 2>/dev/null)
    [ -n "$result" ]
}

# Function to check if user exists
user_exists() {
    result=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -N -e "SELECT User FROM mysql.user WHERE User='$1'" 2>/dev/null)
    [ -n "$result" ]
}

# Function to create database if not exists
create_database() {
    local db_name=$1
    local charset=${2:-utf8mb4}
    local collation=${3:-utf8mb4_unicode_ci}

    if db_exists "$db_name"; then
        echo -e "${YELLOW}  ⚡ Database '$db_name' already exists${NC}"
    else
        run_mysql "CREATE DATABASE IF NOT EXISTS \`$db_name\` CHARACTER SET $charset COLLATE $collation;"
        echo -e "${GREEN}  ✓ Created database '$db_name'${NC}"
    fi
}

# Function to create user and grant permissions
create_user() {
    local username=$1
    local password=$2
    local database=$3

    if user_exists "$username"; then
        echo -e "${YELLOW}  ⚡ User '$username' already exists - updating permissions${NC}"
    else
        run_mysql "CREATE USER IF NOT EXISTS '$username'@'localhost' IDENTIFIED BY '$password';"
        run_mysql "CREATE USER IF NOT EXISTS '$username'@'%' IDENTIFIED BY '$password';"
        echo -e "${GREEN}  ✓ Created user '$username'${NC}"
    fi

    # Grant permissions
    run_mysql "GRANT ALL PRIVILEGES ON \`$database\`.* TO '$username'@'localhost';"
    run_mysql "GRANT ALL PRIVILEGES ON \`$database\`.* TO '$username'@'%';"
    echo -e "${GREEN}  ✓ Granted permissions on '$database' to '$username'${NC}"
}

# Check MySQL
check_mysql

echo ""
echo -e "${BLUE}Creating databases and users...${NC}"
echo ""

# =============================================================================
# 1. MERCAI MOBILE APP
# =============================================================================
echo -e "${YELLOW}[1/4] Setting up Mercai database...${NC}"
create_database "mercai"
create_user "mercai_user" "$DEFAULT_USER_PASSWORD" "mercai"
echo ""

# =============================================================================
# 2. STOCK PREDICT - WebAPI
# =============================================================================
echo -e "${YELLOW}[2/4] Setting up Stock Predict WebAPI database...${NC}"
create_database "stockpredict"
create_user "stockapi" "$DEFAULT_USER_PASSWORD" "stockpredict"
echo ""

# =============================================================================
# 3. STOCK PREDICT - Microservices
# =============================================================================
echo -e "${YELLOW}[3/4] Setting up Stock Microservices database...${NC}"
create_database "defaultdb"
create_database "stock_auth"
create_database "stock_data"
create_database "stock_portfolio"
create_database "stock_prediction"
create_database "stock_analysis"
create_database "stock_ai_insights"
create_database "stock_chatbot"

# Create stockuser for microservices
create_user "stockuser" "$DEFAULT_USER_PASSWORD" "defaultdb"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_auth\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_auth\`.* TO 'stockuser'@'%';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_data\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_data\`.* TO 'stockuser'@'%';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_portfolio\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_portfolio\`.* TO 'stockuser'@'%';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_prediction\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_prediction\`.* TO 'stockuser'@'%';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_analysis\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_analysis\`.* TO 'stockuser'@'%';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_ai_insights\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_ai_insights\`.* TO 'stockuser'@'%';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_chatbot\`.* TO 'stockuser'@'localhost';"
run_mysql "GRANT ALL PRIVILEGES ON \`stock_chatbot\`.* TO 'stockuser'@'%';"
echo -e "${GREEN}  ✓ Granted permissions on all stock databases to 'stockuser'${NC}"
echo ""

# =============================================================================
# 4. MATHEMATIC MOBILE
# =============================================================================
echo -e "${YELLOW}[4/4] Setting up Mathematic Mobile database...${NC}"
create_database "MathematicsSolverDb"
create_user "mathematic_user" "$DEFAULT_USER_PASSWORD" "MathematicsSolverDb"
echo ""

# =============================================================================
# FLUSH PRIVILEGES
# =============================================================================
echo -e "${YELLOW}Flushing privileges...${NC}"
run_mysql "FLUSH PRIVILEGES;"
echo -e "${GREEN}✓ Privileges flushed${NC}"

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""
echo -e "${YELLOW}Created Databases:${NC}"
echo "  - mercai (Mercai)"
echo "  - stockpredict (Stock Predict WebAPI)"
echo "  - defaultdb, stock_* (Stock Microservices)"
echo "  - MathematicsSolverDb (Mathematic Mobile)"
echo ""
echo -e "${YELLOW}Created Users:${NC}"
echo "  - mercai_user (password: $DEFAULT_USER_PASSWORD)"
echo "  - stockapi (password: $DEFAULT_USER_PASSWORD)"
echo "  - stockuser (password: $DEFAULT_USER_PASSWORD)"
echo "  - mathematic_user (password: $DEFAULT_USER_PASSWORD)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Copy .env.local files to .env in each project"
echo "  2. Run: docker-compose -f docker-compose.local.yml up -d"
echo ""
echo -e "${GREEN}Your local MySQL is ready for all projects!${NC}"
