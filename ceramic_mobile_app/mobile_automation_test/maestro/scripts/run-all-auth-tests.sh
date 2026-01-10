#!/bin/bash
# =============================================================================
# Run All Authentication Tests
# =============================================================================
# Runs all Phase A authentication tests in sequence:
#   - AUTH-003: Login with Invalid Password
#   - AUTH-004: Login with Non-existent User
#   - AUTH-005: Login with Empty Fields
#   - AUTH-006: Customer Registration
#   - AUTH-007: Seller Registration
#   - AUTH-009: Logout Flow
#
# Usage:
#   ./run-all-auth-tests.sh           # Run all tests
#   ./run-all-auth-tests.sh --quick   # Run only edge case tests (003-005)
#
# Prerequisites:
# - Android emulator connected
# - Metro bundler running
# - Backend server running (port 8002)
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
FAILED_TESTS=()

# Parse arguments
QUICK_MODE=false
if [[ "$1" == "--quick" ]]; then
    QUICK_MODE=true
fi

echo ""
echo "=============================================="
echo "  Authentication Tests Suite"
echo "=============================================="
echo "Mode: $(if $QUICK_MODE; then echo "Quick (edge cases only)"; else echo "Full"; fi)"
echo "Time: $(date)"
echo "=============================================="
echo ""

# =============================================================================
# Test Execution Functions
# =============================================================================

run_test() {
    local test_name="$1"
    local test_script="$2"
    local description="$3"

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Running: $test_name${NC}"
    echo -e "${BLUE}  $description${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ ! -f "$SCRIPT_DIR/$test_script" ]]; then
        echo -e "${YELLOW}[SKIP]${NC} Test script not found: $test_script"
        ((TESTS_SKIPPED++))
        return
    fi

    if "$SCRIPT_DIR/$test_script"; then
        echo -e "${GREEN}[PASS]${NC} $test_name completed successfully"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}[FAIL]${NC} $test_name failed"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
    fi

    # Brief pause between tests
    sleep 2
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    local start_time=$(date +%s)

    # Edge case tests (always run)
    run_test "AUTH-003" "fast-auth-invalid-password-test.sh" "Login with Invalid Password"
    run_test "AUTH-004" "fast-auth-nonexistent-user-test.sh" "Login with Non-existent User"
    run_test "AUTH-005" "fast-auth-empty-fields-test.sh" "Login with Empty Fields"

    # Full tests (skip in quick mode)
    if ! $QUICK_MODE; then
        run_test "AUTH-006" "fast-auth-customer-registration-test.sh" "Customer Registration"
        run_test "AUTH-007" "fast-auth-seller-registration-test.sh" "Seller Registration"
        run_test "AUTH-009" "fast-auth-logout-test.sh" "Logout Flow"
    else
        echo ""
        echo -e "${YELLOW}[INFO]${NC} Skipping registration and logout tests (quick mode)"
        ((TESTS_SKIPPED+=3))
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Summary
    echo ""
    echo "=============================================="
    echo "  Authentication Tests Summary"
    echo "=============================================="
    echo "  Duration: ${duration}s"
    echo "  Tests Passed:  $TESTS_PASSED"
    echo "  Tests Failed:  $TESTS_FAILED"
    echo "  Tests Skipped: $TESTS_SKIPPED"
    echo "=============================================="

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo ""
        echo -e "${RED}Failed Tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
    fi

    echo ""
    if [[ $TESTS_FAILED -eq 0 && $TESTS_PASSED -gt 0 ]]; then
        echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ALL AUTHENTICATION TESTS PASSED!              ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
        exit 0
    elif [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  SOME TESTS FAILED - See details above         ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
        exit 1
    else
        echo -e "${YELLOW}╔════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  NO TESTS EXECUTED                             ║${NC}"
        echo -e "${YELLOW}╚════════════════════════════════════════════════╝${NC}"
        exit 1
    fi
}

# Run main
main "$@"
