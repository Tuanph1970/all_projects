#!/bin/bash
# =============================================================================
# Test Configuration File
# =============================================================================
# This file contains shared test credentials and configuration used by all
# E2E test scripts. Source this file in your test scripts.
#
# Usage: source "$(dirname "$0")/test_config.sh"
#
# Created: 2026-01-21
# =============================================================================

# =============================================================================
# API Configuration
# =============================================================================
export API_BASE_URL="${API_BASE_URL:-http://localhost:8002}"
export APP_ID="com.ceramicmarketplace.app"

# =============================================================================
# Customer Account
# =============================================================================
export CUSTOMER_USERNAME="test_customer"
export CUSTOMER_EMAIL="test_customer@test.com"
export CUSTOMER_PASSWORD="Test@123456"
export CUSTOMER_FULL_NAME="Test Customer"

# =============================================================================
# Seller Account
# =============================================================================
export SELLER_USERNAME="test_seller"
export SELLER_EMAIL="test_seller@test.com"
export SELLER_PASSWORD="Test@123456"
export SELLER_FULL_NAME="Test Seller"
export SELLER_SHOP_NAME="Test Ceramic Shop"

# =============================================================================
# Common Test Password (same for all test accounts)
# =============================================================================
export TEST_PASSWORD="Test@123456"

# =============================================================================
# Helper Functions
# =============================================================================

# Get customer auth token
get_customer_token() {
    local response=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$CUSTOMER_USERNAME\", \"password\": \"$CUSTOMER_PASSWORD\"}")

    echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4
}

# Get seller auth token
get_seller_token() {
    local response=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$SELLER_USERNAME\", \"password\": \"$SELLER_PASSWORD\"}")

    echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4
}

# Verify API is accessible
verify_api() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/api/v1/health" 2>/dev/null || echo "000")
    if [[ "$response" == "200" ]] || [[ "$response" == "404" ]]; then
        return 0
    fi
    return 1
}

# Log functions with colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

_log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

_log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

_log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

_log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

_log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# =============================================================================
# Print Configuration (for debugging)
# =============================================================================
print_config() {
    echo "=============================================="
    echo "  Test Configuration"
    echo "=============================================="
    echo "API Base URL: $API_BASE_URL"
    echo "App ID: $APP_ID"
    echo ""
    echo "Customer Account:"
    echo "  Username: $CUSTOMER_USERNAME"
    echo "  Email: $CUSTOMER_EMAIL"
    echo "  Password: $CUSTOMER_PASSWORD"
    echo ""
    echo "Seller Account:"
    echo "  Username: $SELLER_USERNAME"
    echo "  Email: $SELLER_EMAIL"
    echo "  Password: $SELLER_PASSWORD"
    echo "  Shop Name: $SELLER_SHOP_NAME"
    echo "=============================================="
}

# Auto-print config if running directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    print_config
fi
