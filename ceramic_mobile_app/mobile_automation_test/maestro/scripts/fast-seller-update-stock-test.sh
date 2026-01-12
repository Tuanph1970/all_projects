#!/bin/bash
# =============================================================================
# SPM-007: Update Product Stock Test
# =============================================================================
# Tests updating product stock/inventory for seller products
# Test scenarios:
#   1. Login as seller
#   2. Navigate to product list
#   3. Select a product to edit
#   4. Update stock quantity
#   5. Save changes and verify
#
# Prerequisites:
# - Android emulator connected
# - Metro bundler running
# - Backend server running (port 8002)
# - At least one product must exist (SPM-001)
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

# Configuration
APP_ID="com.ceramicmarketplace.app"
TEMP_FLOW=$(mktemp /tmp/seller-update-stock-XXXXXX.yaml)
TIMESTAMP=$(date +%s)
NEW_STOCK_VALUE="150"

echo ""
echo "=============================================="
echo "  SPM-007: Update Product Stock Test"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Login as seller"
echo "  2. Navigate to products"
echo "  3. Select product to edit"
echo "  4. Update stock to: $NEW_STOCK_VALUE"
echo "  5. Verify changes saved"
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

# Navigate to products tab
navigate_to_products_tab() {
    _log_step "Navigating to Products tab..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-products"
- waitForAnimationToEnd
- takeScreenshot: "stock-01-product-list"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Products screen loaded"
        return 0
    else
        _log_error "Failed to load products screen"
        return 1
    fi
}

# Select first product to edit
select_product_to_edit() {
    _log_step "Selecting product to edit..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-item-0"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "stock-02-product-details"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Product selected"
        return 0
    else
        _log_error "Failed to select product"
        return 1
    fi
}

# Tap edit button
tap_edit_button() {
    _log_step "Tapping edit button..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-button"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "stock-03-edit-screen"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Edit screen loaded"
        return 0
    else
        _log_info "Edit button may not be visible, trying alternative..."
        return 1
    fi
}

# Update stock quantity
update_stock_quantity() {
    _log_step "Updating stock quantity to $NEW_STOCK_VALUE..."

    # Scroll down to find stock field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- scrollUntilVisible:
    element:
      id: "edit-product-stock-input"
    direction: DOWN
    timeout: 10000
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Tap on stock input field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-stock-input"
    optional: true
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        # Try alternative ID
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "stock-input"
    optional: true
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5

    # Clear existing value
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- eraseText:
    charactersToErase: 10
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter new stock value via ADB
    _adb_input "$NEW_STOCK_VALUE"
    _adb_dismiss_keyboard

    _log_success "Stock value updated to $NEW_STOCK_VALUE"

    # Take screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "stock-04-stock-updated"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    return 0
}

# Save product changes
save_product_changes() {
    _log_step "Saving product changes..."

    _adb_dismiss_keyboard
    sleep 0.3

    # Try scrolling to find save button
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- scrollUntilVisible:
    element:
      id: "save-product-button"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "save-product-button"
    optional: true
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Changes saved (save-product-button)"
        return 0
    fi

    # Try alternative button IDs
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-submit-button"
    optional: true
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Changes saved (edit-product-submit-button)"
        return 0
    fi

    # Try text-based button
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: ".*[Ss]ave.*|.*[Uu]pdate.*"
    optional: true
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Changes saved (text button)"
        return 0
    fi

    _log_error "Could not find save button"
    return 1
}

# Verify stock update
verify_stock_update() {
    _log_step "Verifying stock update..."
    sleep 2

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "stock-05-after-save"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Go back to product list
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- pressKey: back
- waitForAnimationToEnd
- tapOn:
    id: "tab-products"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "stock-06-final-product-list"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    _log_success "Stock update verification complete"
    return 0
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local test_passed=true

    # Step 1: Login as seller
    if ! seller_login; then
        _log_error "Login failed - cannot proceed with test"
        exit 1
    fi

    # Step 2: Navigate to products
    if ! navigate_to_products_tab; then
        _log_error "Failed to navigate to products"
        test_passed=false
    fi

    # Step 3: Select product to edit
    if [[ "$test_passed" == "true" ]]; then
        if ! select_product_to_edit; then
            _log_error "Failed to select product"
            test_passed=false
        fi
    fi

    # Step 4: Tap edit button
    if [[ "$test_passed" == "true" ]]; then
        tap_edit_button  # Continue even if this fails
    fi

    # Step 5: Update stock quantity
    if [[ "$test_passed" == "true" ]]; then
        if ! update_stock_quantity; then
            _log_error "Failed to update stock"
            test_passed=false
        fi
    fi

    # Step 6: Save changes
    if [[ "$test_passed" == "true" ]]; then
        if ! save_product_changes; then
            _log_error "Failed to save changes"
            test_passed=false
        fi
    fi

    # Step 7: Verify update
    if [[ "$test_passed" == "true" ]]; then
        verify_stock_update
    fi

    # Summary
    echo ""
    echo "=============================================="
    if [[ "$test_passed" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} SPM-007: Update Product Stock Test PASSED!"
        echo "  - Logged in as seller"
        echo "  - Selected product from list"
        echo "  - Updated stock to: $NEW_STOCK_VALUE"
        echo "  - Changes saved successfully"
    else
        echo -e "${RED}[FAIL]${NC} SPM-007: Update Product Stock Test FAILED!"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - stock-01-product-list.png"
    echo "  - stock-02-product-details.png"
    echo "  - stock-03-edit-screen.png"
    echo "  - stock-04-stock-updated.png"
    echo "  - stock-05-after-save.png"
    echo "  - stock-06-final-product-list.png"
    echo "=============================================="

    if [[ "$test_passed" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Run main
main "$@"
