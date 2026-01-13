#!/bin/bash
# =============================================================================
# Phase F Test Runner - Seller Order Fulfillment Extended Tests
# =============================================================================
# Runs all Phase F seller order fulfillment tests
#
# Test Cases:
#   - FUL-003: Reject Order
#   - FUL-005: Add Tracking Information
#   - FUL-006: Mark Order as Delivered
#
# Usage:
#   ./run-phase-f-tests.sh          # Run all tests
#   ./run-phase-f-tests.sh --quick  # Run only FUL-006 (fastest test)
#
# Prerequisites:
#   - Backend API running
#   - Android emulator connected
#   - test_seller_user account exists
#   - Orders in various states exist (tests will try to create via API)
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
echo "  Phase F: Seller Order Fulfillment Extended"
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
SKIPPED=0
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
        local exit_code=$?
        if [[ $exit_code -eq 0 ]]; then
            # Test completed but was skipped (no orders found)
            echo -e "${YELLOW}[SKIP]${NC} $test_name"
            ((SKIPPED++))
        else
            echo -e "${RED}[FAIL]${NC} $test_name"
            ((FAILED++))
        fi
        return 1
    fi
}

# Run tests
echo -e "${YELLOW}[INFO]${NC} Starting Phase F tests..."

if [[ "$QUICK_MODE" == "false" ]]; then
    # Test 1: FUL-003 - Reject Order
    run_test "FUL-003: Reject Order" "fast-seller-reject-order-test.sh" || true

    # Test 2: FUL-005 - Add Tracking Information
    run_test "FUL-005: Add Tracking Information" "fast-seller-add-tracking-test.sh" || true
fi

# Test 3: FUL-006 - Mark Order as Delivered (always run)
run_test "FUL-006: Mark Order as Delivered" "fast-seller-deliver-order-test.sh" || true

# Summary
echo ""
echo "=============================================="
echo "  Phase F Test Summary"
echo "=============================================="
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    if [[ $SKIPPED -gt 0 ]]; then
        echo -e "${YELLOW}=============================================="
        echo -e "  PHASE F TESTS COMPLETED (some skipped)"
        echo -e "==============================================${NC}"
        echo ""
        echo "Note: Some tests were skipped because required orders"
        echo "were not available. Create orders in various states"
        echo "to fully test all scenarios."
    else
        echo -e "${GREEN}=============================================="
        echo -e "  ALL PHASE F TESTS PASSED!"
        echo -e "==============================================${NC}"
    fi
    exit 0
else
    echo -e "${RED}=============================================="
    echo -e "  SOME TESTS FAILED"
    echo -e "==============================================${NC}"
    exit 1
fi
