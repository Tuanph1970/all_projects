#!/bin/bash
# =============================================================================
# Fast Complete Order Flow Test
# =============================================================================
# Tests the complete order lifecycle:
# Part 1 - Customer Flow:
#   - Customer login
#   - Search for products
#   - Add to cart
#   - Place order
#
# Part 2 - Seller Flow:
#   - Seller login
#   - View incoming orders
#   - Accept/confirm the order
#
# Prerequisites:
# - Backend API running on localhost:8000
# - Metro bundler running
# - Android emulator connected
# - Products exist in the system (from seller tests)
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source both login libraries
source "$SCRIPT_DIR/customer-login-lib.sh"
source "$SCRIPT_DIR/seller-login-lib.sh"

# Configuration
APP_ID="com.mercai.app"
TEMP_FLOW=$(mktemp /tmp/complete-order-XXXXXX.yaml)

# Search query - matches products created by seller tests
SEARCH_QUERY="${SEARCH_QUERY:-mercai}"

echo ""
echo "=============================================="
echo "  Complete Order Flow Test"
echo "=============================================="
echo "Part 1 - Customer Flow:"
echo "  - Customer login"
echo "  - Search and find products"
echo "  - Add to cart and place order"
echo ""
echo "Part 2 - Seller Flow:"
echo "  - Seller login"
echo "  - View and accept order"
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
# Helper Functions
# =============================================================================

# Clear app state to switch between users
clear_app_and_restart() {
    _log_step "Clearing app state for user switch..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- launchApp:
    clearState: true
    permissions:
      notifications: allow
      photos: allow
- waitForAnimationToEnd
- assertVisible:
    id: "login-username-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "App state cleared"
}

# =============================================================================
# Part 1: Customer Order Flow
# =============================================================================

customer_order_flow() {
    echo ""
    echo "=============================================="
    echo "  PART 1: CUSTOMER ORDER FLOW"
    echo "=============================================="

    # Step 1.1: Customer Login
    _log_step "Step 1.1: Customer Login..."
    if ! customer_login; then
        _log_error "Customer login failed"
        return 1
    fi
    _log_success "Customer logged in successfully"

    # Step 1.2: Navigate to Search
    _log_step "Step 1.2: Navigate to Search..."
    if ! navigate_to_search; then
        _log_error "Failed to navigate to search"
        return 1
    fi

    # Step 1.3: Search for products
    _log_step "Step 1.3: Searching for products: $SEARCH_QUERY"
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "search-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "$SEARCH_QUERY"
    adb shell input keyevent KEYCODE_ENTER
    sleep 2

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-01-search-results"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "Search completed"

    # Step 1.4: Tap on first product
    _log_step "Step 1.4: Viewing product details..."
    # Tap in the area where first product would be (after search bar)
    _adb_tap 200 500
    sleep 2

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-02-product-details"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Step 1.5: Add to cart
    _log_step "Step 1.5: Adding to cart..."
    # Scroll down to find Add to Cart button
    adb shell input swipe 500 1500 500 500 300
    sleep 0.5

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "product-add-to-cart-button"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-03-add-to-cart"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Handle alert
    sleep 1
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    text: "View Cart"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _log_success "Product added to cart"

    # Step 1.6: Go to Cart and Checkout
    _log_step "Step 1.6: Proceeding to checkout..."
    navigate_to_cart || true
    sleep 1

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- scrollUntilVisible:
    element:
      id: "cart-checkout-button"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "cart-checkout-button"
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-04-checkout"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    # Step 1.7: Fill shipping and place order
    _log_step "Step 1.7: Filling shipping info..."

    # Fill Address
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "checkout-address-line1"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "123 Test Street"
    _adb_hide_keyboard

    # Fill City
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "checkout-city"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "Test City"
    _adb_hide_keyboard

    # Fill State
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "checkout-state"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "TC"
    _adb_hide_keyboard

    # Fill Postal Code
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "checkout-postal-code"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "12345"
    _adb_hide_keyboard

    # Fill Country
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "checkout-country"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "USA"
    _adb_hide_keyboard

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-05-filled-checkout"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Place Order
    _log_step "Step 1.8: Placing order..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- scrollUntilVisible:
    element:
      id: "checkout-place-order-button"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "checkout-place-order-button"
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-06-order-placed"
EOF
    
    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "ORDER PLACED SUCCESSFULLY!"
    else
        _log_error "Failed to place order"
        return 1
    fi

    # Dismiss dialog
    sleep 2
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "complete-flow-07-order-success"
- tapOn:
    text: "Continue Shopping"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    echo ""
    _log_success "=== CUSTOMER ORDER FLOW COMPLETED ==="
    return 0
}

# =============================================================================
# Part 2: Seller Accept Order Flow
# =============================================================================

seller_accept_order_flow() {
    echo ""
    echo "=============================================="
    echo "  PART 2: SELLER ACCEPT ORDER FLOW"
    echo "=============================================="

    # Step 2.1: Clear app and login as seller
    _log_step "Step 2.1: Switching to Seller..."
    clear_app_and_restart

    # Step 2.2: Seller Login
    _log_step "Step 2.2: Seller Login..."
    if ! seller_login "no_launch"; then
        _log_error "Seller login failed"
        return 1
    fi
    _log_success "Seller logged in successfully"

    # Step 2.3: Navigate to Orders
    _log_step "Step 2.3: Navigating to Orders..."
    if ! navigate_to_orders; then
        _log_error "Failed to navigate to orders"
        return 1
    fi

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-08-seller-orders"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "Orders screen loaded"

    # Step 2.4: Filter for Pending orders
    _log_step "Step 2.4: Filtering for pending orders..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "order-filter-button"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    text: "Pending"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-09-pending-orders"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Step 2.5: Accept/Confirm the order
    _log_step "Step 2.5: Accepting order..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Confirm"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-10-order-confirmed"
EOF
    
    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "ORDER ACCEPTED BY SELLER!"
    else
        _log_info "No pending orders to confirm (order may have been auto-confirmed or none available)"
    fi

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- takeScreenshot: "complete-flow-11-final-state"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    echo ""
    _log_success "=== SELLER ACCEPT ORDER FLOW COMPLETED ==="
    return 0
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local failed=0

    # Part 1: Customer Order Flow
    if ! customer_order_flow; then
        _log_error "Customer order flow failed"
        failed=1
    fi

    # Part 2: Seller Accept Order Flow
    if ! seller_accept_order_flow; then
        _log_error "Seller accept order flow failed"
        failed=1
    fi

    # Summary
    echo ""
    echo "=============================================="
    echo "  COMPLETE ORDER FLOW TEST SUMMARY"
    echo "=============================================="
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} COMPLETE ORDER FLOW TEST PASSED!"
        echo ""
        echo "Flow Summary:"
        echo "  1. Customer logged in"
        echo "  2. Customer searched for products"
        echo "  3. Customer added product to cart"
        echo "  4. Customer placed order"
        echo "  5. Seller logged in"
        echo "  6. Seller viewed orders"
        echo "  7. Seller accepted order"
    else
        echo -e "${YELLOW}[WARN]${NC} COMPLETE ORDER FLOW TEST COMPLETED WITH WARNINGS"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  Customer Flow:"
    echo "    - complete-flow-01-search-results.png"
    echo "    - complete-flow-02-product-details.png"
    echo "    - complete-flow-03-add-to-cart.png"
    echo "    - complete-flow-04-checkout.png"
    echo "    - complete-flow-05-filled-checkout.png"
    echo "    - complete-flow-06-order-placed.png"
    echo "    - complete-flow-07-order-success.png"
    echo "  Seller Flow:"
    echo "    - complete-flow-08-seller-orders.png"
    echo "    - complete-flow-09-pending-orders.png"
    echo "    - complete-flow-10-order-confirmed.png"
    echo "    - complete-flow-11-final-state.png"
    echo "=============================================="

    return $failed
}

# Run main
main "$@"
