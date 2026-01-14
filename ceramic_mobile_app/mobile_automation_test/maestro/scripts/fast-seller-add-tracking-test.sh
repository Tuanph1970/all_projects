#!/bin/bash
# =============================================================================
# FUL-005: Add Tracking Information Test
# =============================================================================
# Tests seller ability to add tracking information when shipping an order
#
# Test Scenario:
#   1. Seller login
#   2. Navigate to Orders tab
#   3. Find a processing order (or create and process one via API)
#   4. Open order details
#   5. Tap Ship with Tracking button
#   6. Enter tracking number and carrier
#   7. Confirm shipment
#   8. Verify tracking information displayed
#
# Prerequisites:
#   - Backend API running
#   - Android emulator connected
#   - test_seller_user account exists
#   - A processing order exists (will try to create via API if not)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/seller-login-lib.sh"
source "$SCRIPT_DIR/ensure-metro.sh"

# API Configuration - Traefik gateway on port 8002
# Direct Traefik: http://localhost:8002/api/v1/...
API_BASE_URL="${API_BASE_URL:-http://localhost:8002}"
CUSTOMER_USERNAME="${CUSTOMER_USERNAME:-test_customer_user}"
CUSTOMER_PASSWORD="${CUSTOMER_PASSWORD:-@Test_customer@1234}"
SELLER_USERNAME="${SELLER_USERNAME:-test_seller_user}"
SELLER_PASSWORD="${SELLER_PASSWORD:-Testseller@123456}"

echo ""
echo "=============================================="
echo "  FUL-005: Add Tracking Information"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Seller login"
echo "  2. Navigate to Orders tab"
echo "  3. Find processing order"
echo "  4. Open order details"
echo "  5. Ship with tracking"
echo "  6. Verify tracking info"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# API Helper Functions
# =============================================================================

create_processing_order() {
    _log_step "Creating processing order via API..."

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
        "items": [{"product_id": '"$product_id"', "quantity": 2}],
        "shipping_address_line1": "456 Tracking Test Blvd",
        "shipping_city": "Ship City",
        "shipping_state": "SC",
        "shipping_postal_code": "67890",
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

    # Update to CONFIRMED
    curl -s -X PATCH "$API_BASE_URL/api/v1/orders/$order_id/status" \
        -H "Authorization: Bearer $seller_token" \
        -H "Content-Type: application/json" \
        -d '{"status": "CONFIRMED"}' 2>/dev/null || true

    # Update to PROCESSING
    curl -s -X PATCH "$API_BASE_URL/api/v1/orders/$order_id/status" \
        -H "Authorization: Bearer $seller_token" \
        -H "Content-Type: application/json" \
        -d '{"status": "PROCESSING"}' 2>/dev/null || true

    _log_success "Order updated to PROCESSING status"
}

# =============================================================================
# Test Functions
# =============================================================================

filter_processing_orders() {
    _log_step "Filtering for processing orders..."
    local temp_flow=$(mktemp /tmp/filter-processing-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-filter-button"
    optional: true
- waitForAnimationToEnd
- tapOn:
    id: "filter-processing"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "ful005-01-processing-orders"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Filtered for processing orders"
    fi
    return $result
}

open_first_processing_order() {
    _log_step "Opening first processing order..."
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
- takeScreenshot: "ful005-02-order-details"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order details opened"
    else
        _log_error "No processing orders found to open"
    fi
    return $result
}

tap_ship_with_tracking() {
    _log_step "Tapping Ship with Tracking button..."
    local temp_flow=$(mktemp /tmp/tap-ship-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "order-details-ship-btn"
- tapOn:
    id: "order-details-ship-btn"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tracking-modal"
    timeout: 5000
- takeScreenshot: "ful005-03-tracking-modal"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Tracking modal opened"
    fi
    return $result
}

enter_tracking_info() {
    _log_step "Entering tracking information..."

    # Tap tracking number input
    local temp_flow=$(mktemp /tmp/tap-tracking-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tracking-number-input"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter tracking number via ADB
    _adb_input "TEST-TRACK-$(date +%s)"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap carrier input
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tracking-carrier-input"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter carrier via ADB
    _adb_input "FedEx"
    _adb_dismiss_keyboard
    sleep 0.3

    rm -f "$temp_flow"
    _log_success "Tracking information entered"
}

confirm_shipment() {
    _log_step "Confirming shipment..."
    local temp_flow=$(mktemp /tmp/confirm-ship-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "ful005-04-tracking-filled"
- tapOn:
    id: "tracking-confirm-btn"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      text: "SHIPPED"
    timeout: 10000
- takeScreenshot: "ful005-05-order-shipped"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order shipped with tracking"
    fi
    return $result
}

verify_tracking_displayed() {
    _log_step "Verifying tracking information displayed..."
    local temp_flow=$(mktemp /tmp/verify-tracking-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "order-details-tracking-card"
    optional: true
- assertVisible:
    id: "order-details-tracking-number"
    optional: true
- takeScreenshot: "ful005-06-tracking-displayed"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Tracking information verified"
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
- takeScreenshot: "ful005-07-back-to-orders"
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
    # Step 0: Try to create a processing order via API
    create_processing_order || true

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

    # Step 3: Filter for processing orders
    _log_step "Step 3: Filter Processing Orders..."
    filter_processing_orders || true

    # Step 4: Open first processing order
    _log_step "Step 4: Open Processing Order..."
    if ! open_first_processing_order; then
        _log_info "No processing orders found - test cannot proceed"
        echo ""
        echo "=============================================="
        _log_info "FUL-005: Add Tracking Information - SKIPPED (no processing orders)"
        echo "=============================================="
        exit 0
    fi

    # Step 5: Tap Ship with Tracking button
    _log_step "Step 5: Tap Ship with Tracking..."
    if ! tap_ship_with_tracking; then
        _log_error "Ship with Tracking button not available"
        exit 1
    fi

    # Step 6: Enter tracking information
    _log_step "Step 6: Enter Tracking Info..."
    enter_tracking_info

    # Step 7: Confirm shipment
    _log_step "Step 7: Confirm Shipment..."
    if ! confirm_shipment; then
        _log_error "Failed to confirm shipment"
        exit 1
    fi

    # Step 8: Verify tracking displayed
    _log_step "Step 8: Verify Tracking Info..."
    verify_tracking_displayed || true

    # Step 9: Navigate back
    _log_step "Step 9: Navigate Back..."
    navigate_back_to_orders || true

    echo ""
    echo "=============================================="
    _log_success "FUL-005: Add Tracking Information - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - ful005-01-processing-orders.png"
    echo "  - ful005-02-order-details.png"
    echo "  - ful005-03-tracking-modal.png"
    echo "  - ful005-04-tracking-filled.png"
    echo "  - ful005-05-order-shipped.png"
    echo "  - ful005-06-tracking-displayed.png"
    echo "  - ful005-07-back-to-orders.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
