#!/bin/bash
# =============================================================================
# ORD-006: View Order Details Test
# =============================================================================
# Tests customer ability to view details of a specific order
#
# Test Scenario:
#   1. Customer login
#   2. Place an order (to ensure we have an order to view)
#   3. Navigate to Profile > Order History
#   4. Tap on an order card to view details
#   5. Verify Order Details screen elements
#   6. Verify order items, status, address, and totals
#   7. Navigate back
#
# Prerequisites:
#   - Backend API running
#   - Products exist in database
#   - test_customer_user account exists
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/customer-login-lib.sh"
source "$SCRIPT_DIR/ensure-metro.sh"

echo ""
echo "=============================================="
echo "  ORD-006: View Order Details"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Customer login"
echo "  2. Place an order"
echo "  3. Navigate to Order History"
echo "  4. View order details"
echo "  5. Verify order elements"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# Test Functions
# =============================================================================

add_product_and_checkout() {
    _log_step "Adding product and checking out..."
    local temp_flow=$(mktemp /tmp/add-checkout-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Navigate to ProductList from HomeScreen
- scrollUntilVisible:
    element:
      id: "home-view-all-products-button"
    direction: DOWN
    timeout: 5000
- tapOn:
    id: "home-view-all-products-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list-screen"
    timeout: 10000
- takeScreenshot: "ord006-01-product-list"
# Tap on a product by text name
- tapOn:
    text: "Ceramic Dinner Plate Set"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-details-screen"
    timeout: 10000
# Add to cart
- tapOn:
    id: "product-add-to-cart-button"
- waitForAnimationToEnd
- takeScreenshot: "ord006-02-added-to-cart"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Product added to cart"
    else
        _log_error "Failed to add product"
    fi
    return $result
}

navigate_to_cart_and_checkout() {
    _log_step "Navigating to cart and checkout..."
    local temp_flow=$(mktemp /tmp/nav-checkout-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Try View Cart button if visible
- tapOn:
    text: "View Cart"
    optional: true
- waitForAnimationToEnd
- tapOn:
    id: "tab-cart"
    optional: true
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "cart-screen"
    timeout: 15000
- tapOn:
    id: "cart-checkout-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "checkout-screen"
    timeout: 15000
- takeScreenshot: "ord006-03-checkout-screen"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Checkout screen loaded"
    fi
    return $result
}

fill_address_and_place_order() {
    _log_step "Filling address and placing order..."

    # Fill address fields using ADB
    local temp_flow=$(mktemp /tmp/fill-addr-XXXXXX.yaml)

    # Tap address line 1
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-address-line1"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5
    _adb_input "456 Order Test Ave"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap city
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-city"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5
    _adb_input "Order City"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap state
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-state"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5
    _adb_input "NY"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap postal code
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-postal-code"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5
    _adb_input "10001"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap country
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-country"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5
    _adb_input "USA"
    _adb_dismiss_keyboard
    sleep 0.3

    # Scroll and place order
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- scroll:
    direction: DOWN
    amount: 0.3
- tapOn:
    id: "checkout-place-order-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      text: "Order Placed Successfully"
    timeout: 20000
- takeScreenshot: "ord006-04-order-success"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order placed successfully"
    fi
    return $result
}

handle_success_dialog() {
    _log_step "Handling success dialog..."
    local temp_flow=$(mktemp /tmp/dialog-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Continue Shopping"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-home"
    timeout: 10000
- takeScreenshot: "ord006-05-back-to-home"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    return $result
}

navigate_to_order_history() {
    _log_step "Navigating to Order History..."
    local temp_flow=$(mktemp /tmp/nav-history-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-profile"
- waitForAnimationToEnd
- tapOn:
    id: "profile-order-history-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "order-history-screen"
    timeout: 15000
- takeScreenshot: "ord006-06-order-history"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order History loaded"
    fi
    return $result
}

tap_first_order() {
    _log_step "Tapping first order card..."
    local temp_flow=$(mktemp /tmp/tap-order-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "order-history-card-0"
- tapOn:
    id: "order-history-view-btn-0"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "customer-order-details-screen"
    timeout: 15000
- takeScreenshot: "ord006-07-order-details"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order Details screen loaded"
    else
        _log_error "Failed to open Order Details"
    fi
    return $result
}

verify_order_details() {
    _log_step "Verifying Order Details elements..."
    local temp_flow=$(mktemp /tmp/verify-details-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "customer-order-details-screen"
# Verify status card
- assertVisible:
    id: "order-details-status-card"
- assertVisible:
    id: "order-details-status"
- assertVisible:
    id: "order-details-date"
- takeScreenshot: "ord006-08-status-verified"
# Verify items card
- assertVisible:
    id: "order-details-items-card"
- assertVisible:
    id: "order-details-item-0"
- assertVisible:
    id: "order-details-item-name-0"
- takeScreenshot: "ord006-09-items-verified"
# Verify totals
- assertVisible:
    id: "order-details-total"
# Scroll to see address
- scroll:
    direction: DOWN
    amount: 0.3
- waitForAnimationToEnd
- assertVisible:
    id: "order-details-address-card"
- assertVisible:
    id: "order-details-address"
- takeScreenshot: "ord006-10-address-verified"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order Details elements verified"
    fi
    return $result
}

navigate_back_to_history() {
    _log_step "Navigating back to Order History..."
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
      id: "order-history-screen"
    timeout: 10000
- takeScreenshot: "ord006-11-back-to-history"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Back to Order History"
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

    # Step 2: Add product and checkout
    _log_step "Step 2: Add Product to Cart..."
    if ! add_product_and_checkout; then
        _log_error "Failed to add product"
        exit 1
    fi

    # Step 3: Navigate to checkout
    _log_step "Step 3: Navigate to Checkout..."
    if ! navigate_to_cart_and_checkout; then
        _log_error "Failed to navigate to checkout"
        exit 1
    fi

    # Step 4: Fill address and place order
    _log_step "Step 4: Fill Address and Place Order..."
    if ! fill_address_and_place_order; then
        _log_error "Failed to place order"
        exit 1
    fi

    # Step 5: Handle success dialog
    _log_step "Step 5: Handle Success Dialog..."
    if ! handle_success_dialog; then
        _log_error "Failed to handle dialog"
        exit 1
    fi

    # Step 6: Navigate to Order History
    _log_step "Step 6: Navigate to Order History..."
    if ! navigate_to_order_history; then
        _log_error "Failed to navigate to Order History"
        exit 1
    fi

    # Step 7: Tap first order
    _log_step "Step 7: View Order Details..."
    if ! tap_first_order; then
        _log_error "Failed to open order details"
        exit 1
    fi

    # Step 8: Verify order details
    _log_step "Step 8: Verify Order Details..."
    if ! verify_order_details; then
        _log_error "Failed to verify order details"
        exit 1
    fi

    # Step 9: Navigate back
    _log_step "Step 9: Navigate Back..."
    if ! navigate_back_to_history; then
        _log_error "Failed to navigate back"
        exit 1
    fi

    echo ""
    echo "=============================================="
    _log_success "ORD-006: View Order Details - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - ord006-01-product-list.png"
    echo "  - ord006-02-added-to-cart.png"
    echo "  - ord006-03-checkout-screen.png"
    echo "  - ord006-04-order-success.png"
    echo "  - ord006-05-back-to-home.png"
    echo "  - ord006-06-order-history.png"
    echo "  - ord006-07-order-details.png"
    echo "  - ord006-08-status-verified.png"
    echo "  - ord006-09-items-verified.png"
    echo "  - ord006-10-address-verified.png"
    echo "  - ord006-11-back-to-history.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
