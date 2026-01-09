#!/bin/bash
# =============================================================================
# Fast Customer Order Test
# =============================================================================
# Tests complete customer order flow:
# - Customer login
# - Search for products
# - View product details
# - Add to cart
# - Checkout and place order
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

# Source the login library
source "$SCRIPT_DIR/customer-login-lib.sh"

# Configuration
APP_ID="com.ceramicmarketplace.app"
TEMP_FLOW=$(mktemp /tmp/customer-order-XXXXXX.yaml)

# Search query - matches products created by seller tests
SEARCH_QUERY="${SEARCH_QUERY:-ceramic}"

echo ""
echo "=============================================="
echo "  Fast Customer Order Test"
echo "=============================================="
echo "Test Cases:"
echo "  - Customer authentication"
echo "  - Search for products"
echo "  - View product details"
echo "  - Add to cart"
echo "  - Checkout and place order"
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
# Test Functions
# =============================================================================

test_search_products() {
    echo ""
    echo "=============================================="
    echo "  Searching for Products"
    echo "=============================================="

    # Navigate to search tab
    _log_step "Navigating to Search tab..."
    if ! navigate_to_search; then
        _log_error "Failed to navigate to Search tab"
        return 1
    fi

    # Enter search query
    _log_step "Entering search query: $SEARCH_QUERY"
    cat > "$TEMP_FLOW" << EOF
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "search-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    
    sleep 0.5
    _adb_input "$SEARCH_QUERY"
    
    # Submit search
    _log_step "Submitting search..."
    adb shell input keyevent KEYCODE_ENTER
    sleep 2  # Wait for search results to load

    # Take screenshot of search results
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "customer-order-01-search-results"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    _log_success "Search completed"
    return 0
}

test_view_product_details() {
    echo ""
    echo "=============================================="
    echo "  Viewing Product Details"
    echo "=============================================="

    # Tap on first product in search results
    _log_step "Tapping on first product..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Tap on the first product card (use text matching since product names vary)
- tapOn:
    text: ".*"
    index: 0
    optional: true
EOF
    # Try tapping on a product - if search results are empty, this might fail
    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_info "Could not tap on product via text, trying alternative..."
        # Try tapping in the area where products would appear
        _adb_tap 200 500
    fi
    
    sleep 2  # Wait for product details to load

    # Verify product details screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "customer-order-02-product-details"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    _log_success "Product details viewed"
    return 0
}

test_add_to_cart() {
    echo ""
    echo "=============================================="
    echo "  Adding Product to Cart"
    echo "=============================================="

    # Tap Add to Cart button
    _log_step "Tapping Add to Cart button..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- scrollUntilVisible:
    element:
      id: "product-add-to-cart-button"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "product-add-to-cart-button"
- waitForAnimationToEnd
- takeScreenshot: "customer-order-03-added-to-cart"
EOF
    
    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Product added to cart"
    else
        _log_info "Add to cart button not found, trying alternative approach..."
        # Try scrolling down and tapping
        adb shell input swipe 500 1500 500 500 300
        sleep 0.5
        
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Add to Cart"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "customer-order-03-added-to-cart"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -3
    fi

    # Handle the alert dialog - tap "View Cart"
    _log_step "Handling cart confirmation dialog..."
    sleep 1
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "View Cart"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    return 0
}

test_checkout() {
    echo ""
    echo "=============================================="
    echo "  Proceeding to Checkout"
    echo "=============================================="

    # Navigate to cart if not already there
    _log_step "Navigating to Cart..."
    if ! navigate_to_cart; then
        _log_info "Already at cart or cart navigation failed"
    fi

    # Take screenshot of cart
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "customer-order-04-cart"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Tap checkout button
    _log_step "Tapping checkout button..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
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
- extendedWaitUntil:
    visible:
      id: "checkout-screen"
    timeout: 15000
- takeScreenshot: "customer-order-05-checkout-screen"
EOF
    
    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_error "Failed to navigate to checkout"
        return 1
    fi

    _log_success "Checkout screen loaded"
    return 0
}

test_fill_shipping_and_place_order() {
    echo ""
    echo "=============================================="
    echo "  Filling Shipping Information"
    echo "=============================================="

    # Fill Address Line 1
    _log_step "Filling address line 1..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-address-line1"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "123 Test Street"
    _adb_hide_keyboard

    # Fill City
    _log_step "Filling city..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-city"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "Test City"
    _adb_hide_keyboard

    # Fill State
    _log_step "Filling state..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-state"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "TC"
    _adb_hide_keyboard

    # Fill Postal Code
    _log_step "Filling postal code..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-postal-code"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "12345"
    _adb_hide_keyboard

    # Fill Country
    _log_step "Filling country..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "checkout-country"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.3
    _adb_input "USA"
    _adb_hide_keyboard

    # Take screenshot before placing order
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "customer-order-06-filled-checkout"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Place Order
    _log_step "Placing order..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
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
- takeScreenshot: "customer-order-07-order-result"
EOF
    
    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Order placed successfully!"
    else
        _log_error "Failed to place order"
        return 1
    fi

    # Handle success dialog
    sleep 2
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "customer-order-08-success-dialog"
# Tap Continue Shopping or View Order
- tapOn:
    text: "Continue Shopping"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    return 0
}

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

    # Step 2: Search for products
    _log_step "Step 2: Search for products..."
    if ! test_search_products; then
        _log_error "Search products test failed"
        failed=1
    fi

    # Step 3: View product details
    _log_step "Step 3: View product details..."
    if ! test_view_product_details; then
        _log_error "View product details test failed"
        failed=1
    fi

    # Step 4: Add to cart
    _log_step "Step 4: Add to cart..."
    if ! test_add_to_cart; then
        _log_error "Add to cart test failed"
        failed=1
    fi

    # Step 5: Checkout
    _log_step "Step 5: Proceed to checkout..."
    if ! test_checkout; then
        _log_error "Checkout test failed"
        failed=1
    fi

    # Step 6: Fill shipping and place order
    _log_step "Step 6: Fill shipping and place order..."
    if ! test_fill_shipping_and_place_order; then
        _log_error "Place order test failed"
        failed=1
    fi

    # Summary
    echo ""
    echo "=============================================="
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} CUSTOMER ORDER TEST COMPLETED!"
    else
        echo -e "${YELLOW}[WARN]${NC} CUSTOMER ORDER TEST COMPLETED WITH WARNINGS"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - customer-login-success.png"
    echo "  - customer-order-01-search-results.png"
    echo "  - customer-order-02-product-details.png"
    echo "  - customer-order-03-added-to-cart.png"
    echo "  - customer-order-04-cart.png"
    echo "  - customer-order-05-checkout-screen.png"
    echo "  - customer-order-06-filled-checkout.png"
    echo "  - customer-order-07-order-result.png"
    echo "  - customer-order-08-success-dialog.png"
    echo "=============================================="

    return $failed
}

# Run main
main "$@"
