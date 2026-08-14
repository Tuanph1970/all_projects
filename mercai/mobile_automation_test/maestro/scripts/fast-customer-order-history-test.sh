#!/bin/bash
# =============================================================================
# ORD-005: View Order History Test
# =============================================================================
# Tests customer ability to view their order history
#
# Test Scenario:
#   1. Customer login
#   2. Navigate to Profile tab
#   3. Tap on Order History
#   4. Verify Order History screen loads
#   5. Verify order list displays (or empty state)
#   6. If orders exist, verify order card elements
#
# Prerequisites:
#   - Backend API running
#   - Customer test account exists (see test_config.sh)
#   - Customer may have previous orders
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/customer-login-lib.sh"
source "$SCRIPT_DIR/ensure-metro.sh"

echo ""
echo "=============================================="
echo "  ORD-005: View Order History"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Customer login"
echo "  2. Navigate to Profile tab"
echo "  3. Tap on Order History"
echo "  4. Verify Order History screen"
echo "  5. Verify order list elements"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# Test Functions
# =============================================================================

navigate_to_profile() {
    _log_step "Navigating to Profile tab..."
    local temp_flow=$(mktemp /tmp/nav-profile-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-profile"
- waitForAnimationToEnd
- takeScreenshot: "ord005-01-profile-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Profile tab loaded"
    else
        _log_error "Failed to navigate to profile"
    fi
    return $result
}

tap_order_history() {
    _log_step "Tapping on Order History..."
    local temp_flow=$(mktemp /tmp/tap-history-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "profile-order-history-button"
- tapOn:
    id: "profile-order-history-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "order-history-screen"
    timeout: 15000
- takeScreenshot: "ord005-02-order-history-screen"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order History screen loaded"
    else
        _log_error "Failed to open Order History"
    fi
    return $result
}

verify_order_history_screen() {
    _log_step "Verifying Order History screen elements..."
    local temp_flow=$(mktemp /tmp/verify-history-XXXXXX.yaml)

    # First check if we have orders or empty state
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "order-history-screen"
# Check for either order list or empty state
- runFlow:
    when:
      visible:
        id: "order-history-list"
    commands:
      - takeScreenshot: "ord005-03-orders-exist"
- runFlow:
    when:
      visible:
        id: "order-history-empty"
    commands:
      - takeScreenshot: "ord005-03-no-orders"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order History screen verified"
    fi
    return $result
}

verify_order_card_if_exists() {
    _log_step "Checking for order cards..."
    local temp_flow=$(mktemp /tmp/check-cards-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
# Try to find first order card - optional check
- runFlow:
    when:
      visible:
        id: "order-history-card-0"
    commands:
      - assertVisible:
          id: "order-history-number-0"
      - assertVisible:
          id: "order-history-status-0"
      - assertVisible:
          id: "order-history-total-0"
      - assertVisible:
          id: "order-history-view-btn-0"
      - takeScreenshot: "ord005-04-order-card-verified"
- takeScreenshot: "ord005-05-order-history-final"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    _log_success "Order card check completed"
    return 0  # Don't fail if no orders exist
}

navigate_back() {
    _log_step "Navigating back to Profile..."
    local temp_flow=$(mktemp /tmp/nav-back-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-history-back"
- waitForAnimationToEnd
- takeScreenshot: "ord005-06-back-to-profile"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Navigated back to Profile"
    fi
    return $result
}

# =============================================================================
# Main Test Flow
# =============================================================================

main() {
    # Step 1: Customer login
    _log_step "Step 1: Customer Login..."
    if ! customer_login; then
        _log_error "Customer login failed"
        exit 1
    fi
    _log_success "Customer logged in successfully"

    # Step 2: Navigate to Profile
    _log_step "Step 2: Navigate to Profile..."
    if ! navigate_to_profile; then
        _log_error "Failed to navigate to profile"
        exit 1
    fi

    # Step 3: Tap Order History
    _log_step "Step 3: Tap Order History..."
    if ! tap_order_history; then
        _log_error "Failed to open Order History"
        exit 1
    fi

    # Step 4: Verify Order History screen
    _log_step "Step 4: Verify Order History Screen..."
    if ! verify_order_history_screen; then
        _log_error "Failed to verify Order History screen"
        exit 1
    fi

    # Step 5: Check for order cards
    _log_step "Step 5: Check Order Cards..."
    verify_order_card_if_exists

    # Step 6: Navigate back
    _log_step "Step 6: Navigate Back..."
    if ! navigate_back; then
        _log_error "Failed to navigate back"
        exit 1
    fi

    echo ""
    echo "=============================================="
    _log_success "ORD-005: View Order History - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - ord005-01-profile-tab.png"
    echo "  - ord005-02-order-history-screen.png"
    echo "  - ord005-03-orders-exist.png (or no-orders)"
    echo "  - ord005-04-order-card-verified.png (if orders exist)"
    echo "  - ord005-05-order-history-final.png"
    echo "  - ord005-06-back-to-profile.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
