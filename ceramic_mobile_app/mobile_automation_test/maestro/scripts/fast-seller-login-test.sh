#!/bin/bash
# =============================================================================
# Fast Seller Login Test
# =============================================================================
# Tests seller login functionality using the reusable login library
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

echo ""
echo "=============================================="
echo "  Fast Seller Login Test"
echo "=============================================="
echo "Using credentials:"
echo "  Username: $SELLER_USERNAME"
echo "  Password: ${SELLER_PASSWORD:0:4}****"
echo "Time: $(date)"
echo ""

# Run the login function
if seller_login; then
    echo ""
    echo "=============================================="
    echo -e "${GREEN}[PASS]${NC} SELLER LOGIN TEST PASSED!"
    echo "=============================================="
    exit 0
else
    echo ""
    echo "=============================================="
    echo -e "${RED}[FAIL]${NC} SELLER LOGIN TEST FAILED!"
    echo "=============================================="
    exit 1
fi
