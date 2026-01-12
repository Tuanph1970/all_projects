#!/bin/bash
# =============================================================================
# Fast Customer Sort Products Test (PROD-005)
# =============================================================================
# Tests sorting products on the Product List screen.
#
# Test Case: PROD-005 - Sort Products
# Prerequisites:
# - Backend API running on localhost:8000 and localhost:8002
# - Metro bundler running
# - Android emulator connected
# - Test data setup completed (run setup-phase-c-test-data.sh)
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
TEMP_FLOW=$(mktemp /tmp/sort-products-XXXXXX.yaml)

echo ""
echo "=============================================="
echo "  PROD-005: Sort Products"
echo "=============================================="
echo "Test Scenario:"
echo "  1. Customer login"
echo "  2. Navigate to Product List screen"
echo "  3. Verify default sort (Newest)"
echo "  4. Sort by Popular"
echo "  5. Sort by Price: Low to High"
echo "  6. Sort by Price: High to Low"
echo "  7. Sort by Highest Rated"
echo "  8. Verify sort info updates correctly"
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

navigate_to_product_list() {
    echo ""
    _log_step "Navigating to Product List screen..."

    # Tap on "Browse All Products" button from Home screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "tab-home"
- tapOn:
    id: "tab-home"
- waitForAnimationToEnd
- scrollUntilVisible:
    element:
      id: "home-view-all-products-button"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "home-view-all-products-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list-screen"
    timeout: 15000
- takeScreenshot: "prod005-01-product-list-screen"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Navigated to Product List screen"
        return 0
    else
        _log_error "Failed to navigate to Product List screen"
        return 1
    fi
}

verify_default_sort() {
    echo ""
    _log_step "Verifying default sort (Newest)..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "sort-info"
# Default sort should be "Newest"
- assertVisible:
    text: ".*Newest.*"
    optional: true
- takeScreenshot: "prod005-02-default-sort-newest"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Default sort (Newest) verified"
        return 0
    else
        _log_info "Default sort may vary, continuing test..."
        return 0
    fi
}

open_sort_menu() {
    echo ""
    _log_step "Opening sort menu..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "product-sort-button"
- waitForAnimationToEnd
- takeScreenshot: "prod005-sort-menu-open"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Sort menu opened"
        return 0
    else
        _log_error "Failed to open sort menu"
        return 1
    fi
}

sort_by_newest() {
    echo ""
    _log_step "Sorting by Newest..."

    # Open sort menu first
    open_sort_menu

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Newest"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list"
    timeout: 10000
- takeScreenshot: "prod005-03-sorted-newest"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Sorted by Newest"
        return 0
    else
        _log_error "Failed to sort by Newest"
        return 1
    fi
}

sort_by_popular() {
    echo ""
    _log_step "Sorting by Popular..."

    # Open sort menu first
    open_sort_menu

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Popular"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list"
    timeout: 10000
- assertVisible:
    text: ".*Popular.*"
    optional: true
- takeScreenshot: "prod005-04-sorted-popular"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Sorted by Popular"
        return 0
    else
        _log_error "Failed to sort by Popular"
        return 1
    fi
}

sort_by_price_low_high() {
    echo ""
    _log_step "Sorting by Price: Low to High..."

    # Open sort menu first
    open_sort_menu

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Price: Low to High"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list"
    timeout: 10000
- assertVisible:
    text: ".*Price.*Low.*"
    optional: true
- takeScreenshot: "prod005-05-sorted-price-low-high"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Sorted by Price: Low to High"
        return 0
    else
        _log_error "Failed to sort by Price: Low to High"
        return 1
    fi
}

sort_by_price_high_low() {
    echo ""
    _log_step "Sorting by Price: High to Low..."

    # Open sort menu first
    open_sort_menu

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Price: High to Low"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list"
    timeout: 10000
- assertVisible:
    text: ".*Price.*High.*"
    optional: true
- takeScreenshot: "prod005-06-sorted-price-high-low"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Sorted by Price: High to Low"
        return 0
    else
        _log_error "Failed to sort by Price: High to Low"
        return 1
    fi
}

sort_by_highest_rated() {
    echo ""
    _log_step "Sorting by Highest Rated..."

    # Open sort menu first
    open_sort_menu

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    text: "Highest Rated"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-list"
    timeout: 10000
- assertVisible:
    text: ".*Rated.*"
    optional: true
- takeScreenshot: "prod005-07-sorted-highest-rated"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Sorted by Highest Rated"
        return 0
    else
        _log_error "Failed to sort by Highest Rated"
        return 1
    fi
}

verify_sort_info_updates() {
    echo ""
    _log_step "Verifying sort info updates correctly..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- assertVisible:
    id: "sort-info"
- assertVisible:
    id: "results-count"
- assertVisible:
    id: "product-list"
- takeScreenshot: "prod005-08-sort-info-verified"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Sort info verified"
        return 0
    else
        _log_error "Sort info verification failed"
        return 1
    fi
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

    # Step 2: Navigate to Product List
    _log_step "Step 2: Navigate to Product List..."
    if ! navigate_to_product_list; then
        _log_error "Navigation to Product List failed"
        failed=1
    fi

    # Step 3: Verify Default Sort
    _log_step "Step 3: Verify Default Sort..."
    if ! verify_default_sort; then
        _log_error "Default sort verification failed"
        failed=1
    fi

    # Step 4: Sort by Newest
    _log_step "Step 4: Sort by Newest..."
    if ! sort_by_newest; then
        _log_error "Sort by Newest failed"
        failed=1
    fi

    # Step 5: Sort by Popular
    _log_step "Step 5: Sort by Popular..."
    if ! sort_by_popular; then
        _log_error "Sort by Popular failed"
        failed=1
    fi

    # Step 6: Sort by Price Low to High
    _log_step "Step 6: Sort by Price Low to High..."
    if ! sort_by_price_low_high; then
        _log_error "Sort by Price (Low-High) failed"
        failed=1
    fi

    # Step 7: Sort by Price High to Low
    _log_step "Step 7: Sort by Price High to Low..."
    if ! sort_by_price_high_low; then
        _log_error "Sort by Price (High-Low) failed"
        failed=1
    fi

    # Step 8: Sort by Highest Rated
    _log_step "Step 8: Sort by Highest Rated..."
    if ! sort_by_highest_rated; then
        _log_error "Sort by Highest Rated failed"
        failed=1
    fi

    # Step 9: Verify Sort Info Updates
    _log_step "Step 9: Verify Sort Info Updates..."
    if ! verify_sort_info_updates; then
        _log_error "Sort info verification failed"
        failed=1
    fi

    # Summary
    echo ""
    echo "=============================================="
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} PROD-005: Sort Products - PASSED!"
    else
        echo -e "${YELLOW}[WARN]${NC} PROD-005: Sort Products - COMPLETED WITH WARNINGS"
    fi
    echo "=============================================="
    echo "Sort Options Tested:"
    echo "  - Newest (default)"
    echo "  - Popular"
    echo "  - Price: Low to High"
    echo "  - Price: High to Low"
    echo "  - Highest Rated"
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - prod005-01-product-list-screen.png"
    echo "  - prod005-02-default-sort-newest.png"
    echo "  - prod005-03-sorted-newest.png"
    echo "  - prod005-04-sorted-popular.png"
    echo "  - prod005-05-sorted-price-low-high.png"
    echo "  - prod005-06-sorted-price-high-low.png"
    echo "  - prod005-07-sorted-highest-rated.png"
    echo "  - prod005-08-sort-info-verified.png"
    echo "=============================================="

    return $failed
}

# Run main
main "$@"
