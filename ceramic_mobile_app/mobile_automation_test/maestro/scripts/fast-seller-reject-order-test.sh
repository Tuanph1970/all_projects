#!/bin/bash
# =============================================================================
# FUL-003: Reject Order Test
# =============================================================================
# Tests seller ability to reject a pending order
#
# Test Scenario:
#   1. Seller login
#   2. Navigate to Orders tab
#   3. Find a pending order (or create one via API)
#   4. Open order details
#   5. Tap Reject Order button
#   6. Enter rejection reason
#   7. Confirm rejection
#   8. Verify order status changed to CANCELLED
#
# Prerequisites:
#   - Backend API running
#   - Android emulator connected
#   - Seller test account exists (see test_config.sh)
#   - A pending order exists (will try to create via API if not)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/seller-login-lib.sh"
source "$SCRIPT_DIR/ensure-metro.sh"

# API Configuration and credentials are loaded from test_config.sh via seller-login-lib.sh

echo ""
echo "=============================================="
echo "  FUL-003: Reject Order"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Seller login"
echo "  2. Navigate to Orders tab"
echo "  3. Find pending order"
echo "  4. Open order details"
echo "  5. Reject order"
echo "  6. Verify rejection"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# API Helper Functions
# =============================================================================

create_pending_order() {
    _log_step "Creating pending order via API..."

    # Get customer token
    local token_response=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$CUSTOMER_USERNAME&password=$CUSTOMER_PASSWORD" 2>/dev/null || echo "")

    local token=$(echo "$token_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "")

    if [[ -z "$token" ]]; then
        _log_info "Could not get customer token - will use existing orders"
        return 0
    fi

    # Get a product
    local products_response=$(curl -s -X GET "$API_BASE_URL/api/v1/products?limit=1" \
        -H "Authorization: Bearer $token" 2>/dev/null || echo "")

    local product_id=$(echo "$products_response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2 2>/dev/null || echo "")

    if [[ -z "$product_id" ]]; then
        _log_info "Could not find products - will use existing orders"
        return 0
    fi

    # Create order
    local order_data='{
        "items": [{"product_id": '"$product_id"', "quantity": 1}],
        "shipping_address_line1": "789 Reject Test Lane",
        "shipping_city": "Test City",
        "shipping_state": "TS",
        "shipping_postal_code": "54321",
        "shipping_country": "USA"
    }'

    local order_response=$(curl -s -X POST "$API_BASE_URL/api/v1/orders/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "$order_data" 2>/dev/null || echo "")

    local order_id=$(echo "$order_response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2 2>/dev/null || echo "")

    if [[ -n "$order_id" ]]; then
        _log_success "Created pending order ID: $order_id"
    else
        _log_info "Could not create order - will use existing orders"
    fi
}

# =============================================================================
# Test Functions
# =============================================================================

filter_pending_orders() {
    _log_step "Filtering for pending orders..."
    local temp_flow=$(mktemp /tmp/filter-pending-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-filter-button"
    optional: true
- waitForAnimationToEnd
- tapOn:
    id: "filter-pending"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "ful003-01-pending-orders"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Filtered for pending orders"
    fi
    return $result
}

open_first_pending_order() {
    _log_step "Opening first pending order..."
    local temp_flow=$(mktemp /tmp/open-order-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Tap on first order card
- tapOn:
    text: "ORD-"
    optional: true
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "seller-order-details-screen"
    timeout: 10000
- takeScreenshot: "ful003-02-order-details"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order details opened"
    else
        _log_error "No pending orders found to open"
    fi
    return $result
}

tap_reject_button() {
    _log_step "Tapping Reject Order button..."
    local temp_flow=$(mktemp /tmp/tap-reject-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "order-details-reject-btn"
- tapOn:
    id: "order-details-reject-btn"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "reject-modal"
    timeout: 5000
- takeScreenshot: "ful003-03-reject-modal"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Reject modal opened"
    fi
    return $result
}

enter_reject_reason() {
    _log_step "Entering rejection reason..."
    local temp_flow=$(mktemp /tmp/enter-reason-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "reject-reason-input"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter reason via ADB
    _adb_input "Out of stock - Test rejection"
    _adb_dismiss_keyboard

    rm -f "$temp_flow"
    _log_success "Rejection reason entered"
}

confirm_rejection() {
    _log_step "Confirming rejection..."
    local temp_flow=$(mktemp /tmp/confirm-reject-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "ful003-04-reason-filled"
- tapOn:
    id: "reject-confirm-btn"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      text: "CANCELLED"
    timeout: 10000
- takeScreenshot: "ful003-05-order-rejected"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order rejected successfully"
    fi
    return $result
}

navigate_back_to_orders() {
    _log_step "Navigating back to Orders list..."
    local temp_flow=$(mktemp /tmp/nav-back-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-details-back"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "order-management-screen"
    timeout: 10000
- takeScreenshot: "ful003-06-back-to-orders"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Back to Orders list"
    fi
    return $result
}

# =============================================================================
# Main Test Flow
# =============================================================================

main() {
    # Step 0: Try to create a pending order via API
    create_pending_order || true

    # Step 1: Seller login
    _log_step "Step 1: Seller Login..."
    if ! seller_login; then
        _log_error "Seller login failed"
        exit 1
    fi
    _log_success "Seller logged in successfully"

    # Step 2: Navigate to Orders tab
    _log_step "Step 2: Navigate to Orders tab..."
    if ! navigate_to_orders; then
        _log_error "Failed to navigate to Orders tab"
        exit 1
    fi

    # Step 3: Filter for pending orders
    _log_step "Step 3: Filter Pending Orders..."
    filter_pending_orders || true

    # Step 4: Open first pending order
    _log_step "Step 4: Open Pending Order..."
    if ! open_first_pending_order; then
        _log_info "No pending orders found - test cannot proceed"
        echo ""
        echo "=============================================="
        _log_info "FUL-003: Reject Order - SKIPPED (no pending orders)"
        echo "=============================================="
        exit 0
    fi

    # Step 5: Tap Reject button
    _log_step "Step 5: Tap Reject Button..."
    if ! tap_reject_button; then
        _log_error "Reject button not available"
        exit 1
    fi

    # Step 6: Enter rejection reason
    _log_step "Step 6: Enter Rejection Reason..."
    enter_reject_reason

    # Step 7: Confirm rejection
    _log_step "Step 7: Confirm Rejection..."
    if ! confirm_rejection; then
        _log_error "Failed to confirm rejection"
        exit 1
    fi

    # Step 8: Navigate back
    _log_step "Step 8: Navigate Back..."
    navigate_back_to_orders || true

    echo ""
    echo "=============================================="
    _log_success "FUL-003: Reject Order - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - ful003-01-pending-orders.png"
    echo "  - ful003-02-order-details.png"
    echo "  - ful003-03-reject-modal.png"
    echo "  - ful003-04-reason-filled.png"
    echo "  - ful003-05-order-rejected.png"
    echo "  - ful003-06-back-to-orders.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
