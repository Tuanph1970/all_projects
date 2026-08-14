#!/bin/bash
# =============================================================================
# Phase E Test Runner - Customer Order Tests
# =============================================================================
# Runs all Phase E customer order tests
#
# Test Cases:
#   - ORD-002: Add Shipping Address (via checkout)
#   - ORD-005: View Order History
#   - ORD-006: View Order Details
#
# Usage:
#   ./run-phase-e-tests.sh          # Run all tests
#   ./run-phase-e-tests.sh --quick  # Run quick version (skip order-details as it overlaps with checkout-address)
#
# Prerequisites:
#   - Backend API running
#   - Android emulator connected
#   - Products exist in database
#   - Customer test account exists (see test_config.sh)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo ""
echo "=============================================="
echo "  Phase E: Customer Order Tests"
echo "=============================================="
echo "Time: $(date)"
echo ""

# Parse arguments
QUICK_MODE=false
if [[ "$1" == "--quick" ]]; then
    QUICK_MODE=true
    echo -e "${YELLOW}[INFO]${NC} Running in quick mode"
fi

# Initialize counters
PASSED=0
FAILED=0
TOTAL=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_script="$2"

    ((TOTAL++))

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running: ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if bash "$SCRIPT_DIR/$test_script"; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $test_name"
        ((FAILED++))
        return 1
    fi
}

# Run tests
echo -e "${YELLOW}[INFO]${NC} Starting Phase E tests..."

# Test 1: ORD-002 - Add Shipping Address
run_test "ORD-002: Add Shipping Address" "fast-customer-checkout-address-test.sh" || true

# Test 2: ORD-005 - View Order History
run_test "ORD-005: View Order History" "fast-customer-order-history-test.sh" || true

# Test 3: ORD-006 - View Order Details (skip in quick mode as it overlaps with ORD-002)
if [[ "$QUICK_MODE" == "false" ]]; then
    run_test "ORD-006: View Order Details" "fast-customer-order-details-test.sh" || true
else
    echo ""
    echo -e "${YELLOW}[SKIP]${NC} ORD-006: View Order Details (quick mode)"
fi

# Summary
echo ""
echo "=============================================="
echo "  Phase E Test Summary"
echo "=============================================="
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}=============================================="
    echo -e "  ALL PHASE E TESTS PASSED!"
    echo -e "==============================================${NC}"
    exit 0
else
    echo -e "${RED}=============================================="
    echo -e "  SOME TESTS FAILED"
    echo -e "==============================================${NC}"
    exit 1
fi
