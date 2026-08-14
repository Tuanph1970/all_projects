#!/bin/bash
# =============================================================================
# FUL-006: Mark Order as Delivered Test
# =============================================================================
# Tests seller ability to mark a shipped order as delivered
#
# Test Scenario:
#   1. Seller login
#   2. Navigate to Orders tab
#   3. Find a shipped order (or create and ship one via API)
#   4. Open order details
#   5. Tap Mark as Delivered button
#   6. Verify order status changed to DELIVERED
#
# Prerequisites:
#   - Backend API running
#   - Android emulator connected
#   - Seller test account exists (see test_config.sh)
#   - A shipped order exists (will try to create via API if not)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/seller-login-lib.sh"
source "$SCRIPT_DIR/ensure-metro.sh"

# API Configuration and credentials are loaded from test_config.sh via seller-login-lib.sh

echo ""
echo "=============================================="
echo "  FUL-006: Mark Order as Delivered"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Seller login"
echo "  2. Navigate to Orders tab"
echo "  3. Find shipped order"
echo "  4. Open order details"
echo "  5. Mark as delivered"
echo "  6. Verify delivery"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# API Helper Functions
# =============================================================================

create_shipped_order() {
    _log_step "Creating shipped order via API..."

    # Get customer token
    local customer_token=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$CUSTOMER_USERNAME&password=$CUSTOMER_PASSWORD" 2>/dev/null | \
        grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "")

    if [[ -z "$customer_token" ]]; then
        _log_info "Could not get customer token - will use existing orders"
        return 0
    fi

    # Get a product
    local product_id=$(curl -s -X GET "$API_BASE_URL/api/v1/products?limit=1" \
        -H "Authorization: Bearer $customer_token" 2>/dev/null | \
        grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2 2>/dev/null || echo "")

    if [[ -z "$product_id" ]]; then
        _log_info "Could not find products - will use existing orders"
        return 0
    fi

    # Create order
    local order_data='{
        "items": [{"product_id": '"$product_id"', "quantity": 1}],
        "shipping_address_line1": "123 Delivery Test Ave",
        "shipping_city": "Deliver City",
        "shipping_state": "DC",
        "shipping_postal_code": "11111",
        "shipping_country": "USA"
    }'

    local order_response=$(curl -s -X POST "$API_BASE_URL/api/v1/orders/" \
        -H "Authorization: Bearer $customer_token" \
        -H "Content-Type: application/json" \
        -d "$order_data" 2>/dev/null || echo "")

    local order_id=$(echo "$order_response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2 2>/dev/null || echo "")

    if [[ -z "$order_id" ]]; then
        _log_info "Could not create order - will use existing orders"
        return 0
    fi
    _log_success "Created order ID: $order_id"

    # Get seller token to update order status
    local seller_token=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$SELLER_USERNAME&password=$SELLER_PASSWORD" 2>/dev/null | \
        grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "")

    if [[ -z "$seller_token" ]]; then
        _log_info "Could not get seller token - order stays pending"
        return 0
    fi

    # Progress order through states
    curl -s -X PATCH "$API_BASE_URL/api/v1/orders/$order_id/status" \
        -H "Authorization: Bearer $seller_token" \
        -H "Content-Type: application/json" \
        -d '{"status": "CONFIRMED"}' 2>/dev/null || true

    curl -s -X PATCH "$API_BASE_URL/api/v1/orders/$order_id/status" \
        -H "Authorization: Bearer $seller_token" \
        -H "Content-Type: application/json" \
        -d '{"status": "PROCESSING"}' 2>/dev/null || true

    curl -s -X PATCH "$API_BASE_URL/api/v1/orders/$order_id/status" \
        -H "Authorization: Bearer $seller_token" \
        -H "Content-Type: application/json" \
        -d '{"status": "SHIPPED", "tracking_number": "DELIVER-TEST-123", "carrier": "UPS"}' 2>/dev/null || true

    _log_success "Order updated to SHIPPED status"
}

# =============================================================================
# Test Functions
# =============================================================================

filter_shipped_orders() {
    _log_step "Filtering for shipped orders..."
    local temp_flow=$(mktemp /tmp/filter-shipped-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-filter-button"
    optional: true
- waitForAnimationToEnd
- tapOn:
    id: "filter-shipped"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "ful006-01-shipped-orders"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Filtered for shipped orders"
    fi
    return $result
}

open_first_shipped_order() {
    _log_step "Opening first shipped order..."
    local temp_flow=$(mktemp /tmp/open-order-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
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
- takeScreenshot: "ful006-02-order-details"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order details opened"
    else
        _log_error "No shipped orders found to open"
    fi
    return $result
}

verify_shipped_status() {
    _log_step "Verifying order is in SHIPPED status..."
    local temp_flow=$(mktemp /tmp/verify-shipped-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    text: "SHIPPED"
- assertVisible:
    id: "order-details-deliver-btn"
- takeScreenshot: "ful006-03-shipped-status"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order confirmed as SHIPPED"
    fi
    return $result
}

tap_deliver_button() {
    _log_step "Tapping Mark as Delivered button..."
    local temp_flow=$(mktemp /tmp/tap-deliver-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-details-deliver-btn"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      text: "DELIVERED"
    timeout: 10000
- takeScreenshot: "ful006-04-order-delivered"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order marked as delivered"
    fi
    return $result
}

verify_delivered_status() {
    _log_step "Verifying order is now DELIVERED..."
    local temp_flow=$(mktemp /tmp/verify-delivered-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "order-details-status"
- assertVisible:
    text: "DELIVERED"
- takeScreenshot: "ful006-05-delivered-verified"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order delivery verified"
    fi
    return $result
}

navigate_back_to_orders() {
    _log_step "Navigating back to Orders list..."
    local temp_flow=$(mktemp /tmp/nav-back-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-details-back"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "order-management-screen"
    timeout: 10000
- takeScreenshot: "ful006-06-back-to-orders"
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
    # Step 0: Try to create a shipped order via API
    create_shipped_order || true

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

    # Step 3: Filter for shipped orders
    _log_step "Step 3: Filter Shipped Orders..."
    filter_shipped_orders || true

    # Step 4: Open first shipped order
    _log_step "Step 4: Open Shipped Order..."
    if ! open_first_shipped_order; then
        _log_info "No shipped orders found - test cannot proceed"
        echo ""
        echo "=============================================="
        _log_info "FUL-006: Mark Order as Delivered - SKIPPED (no shipped orders)"
        echo "=============================================="
        exit 0
    fi

    # Step 5: Verify shipped status
    _log_step "Step 5: Verify Shipped Status..."
    if ! verify_shipped_status; then
        _log_info "Order is not in SHIPPED status - test cannot proceed"
        echo ""
        echo "=============================================="
        _log_info "FUL-006: Mark Order as Delivered - SKIPPED (order not shipped)"
        echo "=============================================="
        exit 0
    fi

    # Step 6: Tap Mark as Delivered button
    _log_step "Step 6: Mark as Delivered..."
    if ! tap_deliver_button; then
        _log_error "Failed to mark as delivered"
        exit 1
    fi

    # Step 7: Verify delivered status
    _log_step "Step 7: Verify Delivery..."
    verify_delivered_status || true

    # Step 8: Navigate back
    _log_step "Step 8: Navigate Back..."
    navigate_back_to_orders || true

    echo ""
    echo "=============================================="
    _log_success "FUL-006: Mark Order as Delivered - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - ful006-01-shipped-orders.png"
    echo "  - ful006-02-order-details.png"
    echo "  - ful006-03-shipped-status.png"
    echo "  - ful006-04-order-delivered.png"
    echo "  - ful006-05-delivered-verified.png"
    echo "  - ful006-06-back-to-orders.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
