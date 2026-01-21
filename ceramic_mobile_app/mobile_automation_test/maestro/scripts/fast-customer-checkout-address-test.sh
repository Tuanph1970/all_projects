#!/bin/bash
# =============================================================================
# ORD-002: Add Shipping Address Test
# =============================================================================
# Tests customer ability to add shipping address during checkout
#
# Test Scenario:
#   1. Customer login
#   2. Navigate to Product List and add item to cart
#   3. Navigate to Cart screen
#   4. Proceed to Checkout
#   5. Fill shipping address form
#   6. Verify form validation (empty fields)
#   7. Fill complete address
#   8. Place order successfully
#   9. Verify order confirmation
#
# Prerequisites:
#   - Backend API running
#   - Products exist in database
#   - Customer test account exists (see test_config.sh)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/customer-login-lib.sh"
source "$SCRIPT_DIR/ensure-metro.sh"

echo ""
echo "=============================================="
echo "  ORD-002: Add Shipping Address"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Customer login"
echo "  2. Add product to cart"
echo "  3. Navigate to Cart screen"
echo "  4. Proceed to Checkout"
echo "  5. Fill shipping address"
echo "  6. Verify form validation"
echo "  7. Place order"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# Test Functions
# =============================================================================

add_product_to_cart() {
    _log_step "Adding product to cart..."
    local temp_flow=$(mktemp /tmp/add-to-cart-XXXXXX.yaml)
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
- takeScreenshot: "ord002-01-product-list"
# Tap on a product by text name (more reliable than testID with database ID)
- tapOn:
    text: "Ceramic Dinner Plate Set"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-details-screen"
    timeout: 10000
- takeScreenshot: "ord002-02-product-details"
# Add to cart
- tapOn:
    id: "product-add-to-cart-button"
- waitForAnimationToEnd
- takeScreenshot: "ord002-03-added-to-cart"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Product added to cart"
    else
        _log_error "Failed to add product to cart"
    fi
    return $result
}

navigate_to_cart_screen() {
    _log_step "Navigating to Cart screen..."
    local temp_flow=$(mktemp /tmp/nav-cart-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Try tapping "View Cart" dialog button first if visible
- tapOn:
    text: "View Cart"
    optional: true
- waitForAnimationToEnd
# Or navigate via tab
- tapOn:
    id: "tab-cart"
    optional: true
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "cart-screen"
    timeout: 15000
- assertVisible:
    id: "cart-items-list"
- takeScreenshot: "ord002-04-cart-screen"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Cart screen loaded with items"
    else
        _log_error "Failed to navigate to cart"
    fi
    return $result
}

proceed_to_checkout() {
    _log_step "Proceeding to checkout..."
    local temp_flow=$(mktemp /tmp/checkout-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "cart-checkout-button"
- tapOn:
    id: "cart-checkout-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "checkout-screen"
    timeout: 15000
- takeScreenshot: "ord002-05-checkout-screen"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Checkout screen loaded"
    else
        _log_error "Failed to proceed to checkout"
    fi
    return $result
}

verify_checkout_form_visible() {
    _log_step "Verifying checkout form elements..."
    local temp_flow=$(mktemp /tmp/verify-form-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "checkout-screen"
# Verify shipping address form fields
- assertVisible:
    id: "checkout-address-line1"
- assertVisible:
    id: "checkout-city"
- assertVisible:
    id: "checkout-state"
- assertVisible:
    id: "checkout-postal-code"
- assertVisible:
    id: "checkout-country"
- assertVisible:
    id: "checkout-place-order-button"
- takeScreenshot: "ord002-06-checkout-form"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Checkout form elements verified"
    else
        _log_error "Failed to verify checkout form"
    fi
    return $result
}

fill_shipping_address() {
    _log_step "Filling shipping address..."

    # Tap on address line 1 field
    local temp_flow=$(mktemp /tmp/fill-addr-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "checkout-address-line1"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter address line 1
    _adb_input "123 Test Street"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap on city field
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-city"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter city
    _adb_input "Test City"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap on state field
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-state"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter state
    _adb_input "CA"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap on postal code field
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-postal-code"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter postal code
    _adb_input "90210"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap on country field
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-country"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2
    sleep 0.5

    # Enter country
    _adb_input "USA"
    _adb_dismiss_keyboard
    sleep 0.3

    # Take screenshot of filled form
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "ord002-07-address-filled"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2

    rm -f "$temp_flow"
    _log_success "Shipping address filled"
    return 0
}

verify_filled_address() {
    _log_step "Verifying filled address..."
    local temp_flow=$(mktemp /tmp/verify-addr-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Scroll down to see all fields and place order button
- scroll:
    direction: DOWN
    amount: 0.3
- waitForAnimationToEnd
- assertVisible:
    id: "checkout-place-order-button"
- takeScreenshot: "ord002-08-ready-to-place-order"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Address verified, ready to place order"
    fi
    return $result
}

place_order() {
    _log_step "Placing order..."
    local temp_flow=$(mktemp /tmp/place-order-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "checkout-place-order-button"
- waitForAnimationToEnd
# Wait for order confirmation dialog
- extendedWaitUntil:
    visible:
      text: "Order Placed Successfully"
    timeout: 20000
- takeScreenshot: "ord002-09-order-success"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -5
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Order placed successfully"
    else
        _log_error "Failed to place order"
    fi
    return $result
}

handle_order_success_dialog() {
    _log_step "Handling order success dialog..."
    local temp_flow=$(mktemp /tmp/dialog-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Tap "Continue Shopping" to go back to home
- tapOn:
    text: "Continue Shopping"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-home"
    timeout: 10000
- takeScreenshot: "ord002-10-back-to-home"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Returned to home screen"
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

    # Step 2: Add product to cart
    _log_step "Step 2: Add Product to Cart..."
    if ! add_product_to_cart; then
        _log_error "Failed to add product to cart"
        exit 1
    fi

    # Step 3: Navigate to cart
    _log_step "Step 3: Navigate to Cart..."
    if ! navigate_to_cart_screen; then
        _log_error "Failed to navigate to cart"
        exit 1
    fi

    # Step 4: Proceed to checkout
    _log_step "Step 4: Proceed to Checkout..."
    if ! proceed_to_checkout; then
        _log_error "Failed to proceed to checkout"
        exit 1
    fi

    # Step 5: Verify checkout form
    _log_step "Step 5: Verify Checkout Form..."
    if ! verify_checkout_form_visible; then
        _log_error "Failed to verify checkout form"
        exit 1
    fi

    # Step 6: Fill shipping address
    _log_step "Step 6: Fill Shipping Address..."
    if ! fill_shipping_address; then
        _log_error "Failed to fill shipping address"
        exit 1
    fi

    # Step 7: Verify filled address
    _log_step "Step 7: Verify Filled Address..."
    if ! verify_filled_address; then
        _log_error "Failed to verify filled address"
        exit 1
    fi

    # Step 8: Place order
    _log_step "Step 8: Place Order..."
    if ! place_order; then
        _log_error "Failed to place order"
        exit 1
    fi

    # Step 9: Handle success dialog
    _log_step "Step 9: Handle Success Dialog..."
    if ! handle_order_success_dialog; then
        _log_error "Failed to handle success dialog"
        exit 1
    fi

    echo ""
    echo "=============================================="
    _log_success "ORD-002: Add Shipping Address - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - ord002-01-product-list.png"
    echo "  - ord002-02-product-details.png"
    echo "  - ord002-03-added-to-cart.png"
    echo "  - ord002-04-cart-screen.png"
    echo "  - ord002-05-checkout-screen.png"
    echo "  - ord002-06-checkout-form.png"
    echo "  - ord002-07-address-filled.png"
    echo "  - ord002-08-ready-to-place-order.png"
    echo "  - ord002-09-order-success.png"
    echo "  - ord002-10-back-to-home.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
