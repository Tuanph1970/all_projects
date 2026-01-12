#!/bin/bash
# =============================================================================
# Run Phase C Tests - Customer Product Browsing (Extended)
# =============================================================================
# Runs all Phase C E2E tests:
# - PROD-003: Filter Products by Category
# - PROD-004: Filter Products by Price Range
# - PROD-005: Sort Products
#
# Usage:
#   ./run-phase-c-tests.sh           # Run all Phase C tests
#   ./run-phase-c-tests.sh --setup   # Run setup script before tests
#   ./run-phase-c-tests.sh --quick   # Run only PROD-003 (quick test)
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
RUN_SETUP=false
QUICK_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --setup)
            RUN_SETUP=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo ""
echo "=============================================="
echo "  Phase C: Customer Product Browsing Tests"
echo "=============================================="
echo "Time: $(date)"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
RESULTS=()

run_test() {
    local test_name="$1"
    local test_script="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if "$SCRIPT_DIR/$test_script"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        RESULTS+=("✅ $test_name")
        echo -e "${GREEN}[PASS]${NC} $test_name"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        RESULTS+=("❌ $test_name")
        echo -e "${RED}[FAIL]${NC} $test_name"
    fi
}

# Run setup if requested
if [[ "$RUN_SETUP" == "true" ]]; then
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running Test Data Setup${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if "$SCRIPT_DIR/setup-phase-c-test-data.sh"; then
        echo -e "${GREEN}[PASS]${NC} Test data setup complete"
    else
        echo -e "${RED}[FAIL]${NC} Test data setup failed"
        exit 1
    fi
fi

# Run tests
echo ""
echo "Running Phase C Tests..."
echo ""

# Test 1: Filter by Category (PROD-003)
run_test "PROD-003: Filter Products by Category" "fast-customer-filter-category-test.sh"

# If not quick mode, run all tests
if [[ "$QUICK_MODE" != "true" ]]; then
    # Test 2: Filter by Price Range (PROD-004)
    run_test "PROD-004: Filter Products by Price Range" "fast-customer-filter-price-test.sh"

    # Test 3: Sort Products (PROD-005)
    run_test "PROD-005: Sort Products" "fast-customer-sort-products-test.sh"
fi

# Summary
echo ""
echo "=============================================="
echo "  Phase C Test Results Summary"
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

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}🎉 All Phase C tests passed!${NC}"
    echo ""
    exit 0
else
    echo ""
    echo -e "${YELLOW}⚠️  Some tests failed. Check logs above for details.${NC}"
    echo ""
    exit 1
fi
