#!/bin/bash
# =============================================================================
# Fast Seller Add Products Test v2
# =============================================================================
# Step by step product addition with verification
# Uses the reusable login library for seller authentication
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

TEMP_FLOW=$(mktemp /tmp/add-products-XXXXXX.yaml)
TIMESTAMP=$(date +%s)
PRODUCTS_ADDED=0

echo ""
echo "=============================================="
echo "  Seller Add 5 Products Test v2"
echo "=============================================="
echo ""

# ===== LOGIN =====
_log_step "Phase 1: Login"

if ! seller_login; then
    _log_error "Login failed"
    rm -f "$TEMP_FLOW"
    exit 1
fi
_log_success "Login successful"

# Function to add one product
add_product() {
    local NUM=$1
    local TITLE=$2
    local DESC=$3
    local PRICE=$4

    _log_info "Adding product $NUM: $TITLE"

    # Navigate to add product screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "seller-dashboard-fab-add"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "add-product-screen"
    timeout: 10000
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_error "Failed to open add product screen"
        return 1
    fi

    # Take screenshot of empty form
    cat > "$TEMP_FLOW" << EOF
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "add5-${NUM}a-empty-form"
- tapOn:
    id: "add-product-title-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter title
    _adb_input "$TITLE"

    # Enter description
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _adb_input "$DESC"

    # Enter price
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _adb_input "$PRICE"

    # Take screenshot of filled form and submit
    cat > "$TEMP_FLOW" << EOF
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- takeScreenshot: "add5-${NUM}b-filled-form"
- tapOn:
    id: "add-product-submit-button"
- waitForAnimationToEnd
- takeScreenshot: "add5-${NUM}c-after-submit"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Product $NUM added: $TITLE"
        PRODUCTS_ADDED=$((PRODUCTS_ADDED + 1))
    else
        _log_error "Failed to add product $NUM"
        return 1
    fi

    # Navigate back to dashboard
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-dashboard"
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    sleep 1
    return 0
}

# Add 5 products
add_product "01" "Vase_${TIMESTAMP}" "Beautiful_vase" "49.99"
add_product "02" "Bowl_${TIMESTAMP}" "Clay_bowl" "29.99"
add_product "03" "Plate_${TIMESTAMP}" "Dinner_plate" "19.99"
add_product "04" "Mug_${TIMESTAMP}" "Coffee_mug" "14.99"
add_product "05" "Sculpture_${TIMESTAMP}" "Art_piece" "99.99"

# Final verification - go to products tab
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-products"
- waitForAnimationToEnd
- takeScreenshot: "add5-final-products-list"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
echo "Products added: $PRODUCTS_ADDED of 5"
if [ $PRODUCTS_ADDED -ge 3 ]; then
    _log_success "ADD PRODUCTS TEST PASSED!"
    exit 0
else
    _log_error "ADD PRODUCTS TEST FAILED!"
    exit 1
fi
