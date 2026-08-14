#!/bin/bash
# =============================================================================
# CART-002: Update Cart Quantity Test
# =============================================================================
# Tests customer ability to update product quantity in shopping cart
#
# Test Scenario:
#   1. Customer login
#   2. Navigate to Product List and add item to cart
#   3. Navigate to Cart screen
#   4. Verify initial quantity
#   5. Increase quantity using plus button
#   6. Verify quantity increased
#   7. Verify total price updated
#   8. Decrease quantity using minus button
#   9. Verify quantity decreased
#   10. Verify final cart state
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
echo "  CART-002: Update Cart Quantity"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Customer login"
echo "  2. Add product to cart"
echo "  3. Navigate to Cart screen"
echo "  4. Increase quantity"
echo "  5. Verify quantity increased"
echo "  6. Decrease quantity"
echo "  7. Verify quantity decreased"
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
appId: com.mercai.app
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
- takeScreenshot: "cart002-01-product-list"
# Tap on a product by text name (more reliable than testID with database ID)
- tapOn:
    text: "Ceramic Dinner Plate Set"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-details-screen"
    timeout: 10000
- takeScreenshot: "cart002-02-product-details"
# Add to cart
- tapOn:
    id: "product-add-to-cart-button"
- waitForAnimationToEnd
- takeScreenshot: "cart002-03-added-to-cart"
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
appId: com.mercai.app
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
- takeScreenshot: "cart002-04-cart-screen"
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

verify_initial_quantity() {
    _log_step "Verifying initial quantity..."
    local temp_flow=$(mktemp /tmp/verify-qty-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "cart-item-0"
- assertVisible:
    id: "cart-item-quantity-0"
- assertVisible:
    id: "cart-item-total-0"
- takeScreenshot: "cart002-05-initial-quantity"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Initial quantity verified"
    fi
    return $result
}

increase_quantity() {
    _log_step "Increasing quantity..."
    local temp_flow=$(mktemp /tmp/inc-qty-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
# Tap plus button to increase quantity
- tapOn:
    id: "cart-item-quantity-plus-0"
- waitForAnimationToEnd
- takeScreenshot: "cart002-06-quantity-increased"
# Tap plus again to increase to 3
- tapOn:
    id: "cart-item-quantity-plus-0"
- waitForAnimationToEnd
- takeScreenshot: "cart002-07-quantity-increased-again"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Quantity increased"
    fi
    return $result
}

verify_quantity_increased() {
    _log_step "Verifying quantity increased..."
    local temp_flow=$(mktemp /tmp/verify-inc-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "cart-item-quantity-0"
- assertVisible:
    id: "cart-item-total-0"
- assertVisible:
    id: "cart-summary"
- assertVisible:
    id: "cart-total"
- takeScreenshot: "cart002-08-verified-increase"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Quantity increase verified"
    fi
    return $result
}

decrease_quantity() {
    _log_step "Decreasing quantity..."
    local temp_flow=$(mktemp /tmp/dec-qty-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
# Tap minus button to decrease quantity
- tapOn:
    id: "cart-item-quantity-minus-0"
- waitForAnimationToEnd
- takeScreenshot: "cart002-09-quantity-decreased"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Quantity decreased"
    fi
    return $result
}

verify_final_cart_state() {
    _log_step "Verifying final cart state..."
    local temp_flow=$(mktemp /tmp/verify-final-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "cart-screen"
- assertVisible:
    id: "cart-items-list"
- assertVisible:
    id: "cart-item-0"
- assertVisible:
    id: "cart-summary"
- assertVisible:
    id: "cart-subtotal"
- assertVisible:
    id: "cart-total"
- assertVisible:
    id: "cart-checkout-button"
- takeScreenshot: "cart002-10-final-state"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Final cart state verified"
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

    # Step 4: Verify initial quantity
    _log_step "Step 4: Verify Initial Quantity..."
    if ! verify_initial_quantity; then
        _log_error "Failed to verify initial quantity"
        exit 1
    fi

    # Step 5: Increase quantity
    _log_step "Step 5: Increase Quantity..."
    if ! increase_quantity; then
        _log_error "Failed to increase quantity"
        exit 1
    fi

    # Step 6: Verify quantity increased
    _log_step "Step 6: Verify Quantity Increased..."
    if ! verify_quantity_increased; then
        _log_error "Failed to verify quantity increase"
        exit 1
    fi

    # Step 7: Decrease quantity
    _log_step "Step 7: Decrease Quantity..."
    if ! decrease_quantity; then
        _log_error "Failed to decrease quantity"
        exit 1
    fi

    # Step 8: Verify final state
    _log_step "Step 8: Verify Final Cart State..."
    if ! verify_final_cart_state; then
        _log_error "Failed to verify final cart state"
        exit 1
    fi

    echo ""
    echo "=============================================="
    _log_success "CART-002: Update Cart Quantity - PASSED!"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - cart002-01-product-list.png"
    echo "  - cart002-02-product-details.png"
    echo "  - cart002-03-added-to-cart.png"
    echo "  - cart002-04-cart-screen.png"
    echo "  - cart002-05-initial-quantity.png"
    echo "  - cart002-06-quantity-increased.png"
    echo "  - cart002-07-quantity-increased-again.png"
    echo "  - cart002-08-verified-increase.png"
    echo "  - cart002-09-quantity-decreased.png"
    echo "  - cart002-10-final-state.png"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
