#!/bin/bash
# Run All Customer Tests - Master script
# Runs all customer-related tests sequentially

set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running before starting tests
source "$SCRIPT_DIR/ensure-metro.sh"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "       CUSTOMER TEST SUITE"
echo "=============================================="
echo "Time: $(date)"
echo ""

PASSED=0
FAILED=0
TESTS=()
RESULTS=()

run_test() {
    local test_name="$1"
    local test_script="$2"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if "$SCRIPT_DIR/$test_script"; then
        PASSED=$((PASSED + 1))
        RESULTS+=("✅")
    else
        FAILED=$((FAILED + 1))
        RESULTS+=("❌")
    fi
    TESTS+=("$test_name")

    # Small pause between tests
    sleep 2
}

# Run all tests
run_test "Customer Login" "fast-customer-login-test.sh"
run_test "Customer Browse Products" "fast-customer-browse-test.sh"
run_test "Customer Cart" "fast-customer-cart-test.sh"

# Summary
echo ""
echo "=============================================="
echo "           TEST SUITE SUMMARY"
echo "=============================================="
echo ""

for i in "${!TESTS[@]}"; do
    echo -e "${RESULTS[$i]} ${TESTS[$i]}"
done

echo ""
echo "----------------------------------------------"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo "Total:  $((PASSED + FAILED))"
echo "----------------------------------------------"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=============================================="
    echo "       ALL CUSTOMER TESTS PASSED! 🎉"
    echo -e "==============================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=============================================="
    echo "       SOME TESTS FAILED!"
    echo -e "==============================================${NC}"
    exit 1
fi
