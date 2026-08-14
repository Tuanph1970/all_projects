#!/bin/bash
# =============================================================================
# Phase D Test Runner - Customer Cart Operations
# =============================================================================
# Runs all Phase D E2E tests for customer cart operations
#
# Tests included:
#   - CART-002: Update Cart Quantity
#   - CART-003: Remove Item from Cart
#
# Usage:
#   ./run-phase-d-tests.sh           # Run all Phase D tests
#   ./run-phase-d-tests.sh --quick   # Run only CART-002 (quick test)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a RESULTS

log_header() { echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
log_test() { echo -e "${BLUE}Running: $1${NC}"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }

run_test() {
    local test_name="$1"
    local test_script="$2"

    log_header
    log_test "$test_name"
    log_header

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if "$SCRIPT_DIR/$test_script"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        RESULTS+=("✅ $test_name")
        log_pass "$test_name"
        return 0
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        RESULTS+=("❌ $test_name")
        log_fail "$test_name"
        return 1
    fi
}

echo ""
echo "=============================================="
echo "  Phase D: Customer Cart Operations Tests"
echo "=============================================="
echo "Time: $(date)"
echo ""

# Parse arguments
QUICK_MODE=false
if [[ "$1" == "--quick" ]]; then
    QUICK_MODE=true
    echo "Running in QUICK mode (CART-002 only)"
    echo ""
fi

echo "Running Phase D Tests..."
echo ""

# Run tests
run_test "CART-002: Update Cart Quantity" "fast-customer-update-cart-quantity-test.sh" || true

if [[ "$QUICK_MODE" == false ]]; then
    run_test "CART-003: Remove Item from Cart" "fast-customer-remove-cart-item-test.sh" || true
fi

# Print summary
echo ""
echo "=============================================="
echo "  Phase D Test Results Summary"
echo "=============================================="
echo ""

for result in "${RESULTS[@]}"; do
    echo "  $result"
done

echo ""
echo "----------------------------------------------"
echo "  Total:  $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"
echo "----------------------------------------------"
echo ""

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All Phase D tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some Phase D tests failed!${NC}"
    exit 1
fi
