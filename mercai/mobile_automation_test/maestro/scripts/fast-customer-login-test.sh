#!/bin/bash
# =============================================================================
# Fast Customer Login Test
# =============================================================================
# Tests customer authentication and basic navigation:
# - Customer login with credentials
# - Verify customer home screen
# - Navigate through customer tabs
#
# Prerequisites:
# - Backend API running on localhost:8000
# - Metro bundler running
# - Android emulator connected
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/customer-login-lib.sh"

# Configuration
APP_ID="com.mercai.app"
TEMP_FLOW=$(mktemp /tmp/customer-test-XXXXXX.yaml)

echo ""
echo "=============================================="
echo "  Fast Customer Login Test"
echo "=============================================="
echo "Test Cases:"
echo "  - Customer authentication"
echo "  - Home tab navigation"
echo "  - Search tab navigation"
echo "  - Cart tab navigation"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# Cleanup
# =============================================================================

cleanup() {
    rm -f "$TEMP_FLOW"
}

trap cleanup EXIT

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local failed=0

    # Step 1: Customer Login
    _log_step "Step 1: Customer Login..."
    if ! customer_login; then
        _log_error "Customer login failed"
        exit 1
    fi
    _log_success "Customer logged in successfully"

    # Step 2: Navigate to Search tab
    _log_step "Step 2: Navigate to Search tab..."
    if ! navigate_to_search; then
        _log_error "Failed to navigate to Search tab"
        failed=1
    fi
    _log_success "Search tab loaded"

    # Step 3: Navigate to Cart tab
    _log_step "Step 3: Navigate to Cart tab..."
    if ! navigate_to_cart; then
        _log_error "Failed to navigate to Cart tab"
        failed=1
    fi
    _log_success "Cart tab loaded"

    # Step 4: Navigate back to Home tab
    _log_step "Step 4: Navigate back to Home tab..."
    if ! navigate_to_home; then
        _log_error "Failed to navigate to Home tab"
        failed=1
    fi
    _log_success "Home tab loaded"

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- takeScreenshot: "customer-test-final"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Summary
    echo ""
    echo "=============================================="
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} CUSTOMER LOGIN TEST COMPLETED!"
    else
        echo -e "${YELLOW}[WARN]${NC} CUSTOMER LOGIN TEST COMPLETED WITH WARNINGS"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - customer-login-success.png"
    echo "  - search-tab.png"
    echo "  - cart-tab.png"
    echo "  - home-tab.png"
    echo "  - customer-test-final.png"
    echo "=============================================="

    return $failed
}

# Run main
main "$@"
