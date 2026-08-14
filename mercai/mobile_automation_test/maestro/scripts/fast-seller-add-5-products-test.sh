#!/bin/bash
# =============================================================================
# Fast Seller Add 5 Products Test
# =============================================================================
# Tests bulk product creation using the reusable login library
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

TIMESTAMP=$(date +%s)

# Product data
declare -a PRODUCTS=(
    "Ceramic_Vase_${TIMESTAMP}|Beautiful_handmade_ceramic_vase|49.99|25"
    "Clay_Bowl_${TIMESTAMP}|Artisan_clay_bowl_for_decoration|29.99|50"
    "Pottery_Plate_${TIMESTAMP}|Traditional_pottery_dinner_plate|19.99|100"
    "Ceramic_Mug_${TIMESTAMP}|Handcrafted_ceramic_coffee_mug|14.99|75"
    "Art_Sculpture_${TIMESTAMP}|Unique_ceramic_art_sculpture|99.99|10"
)

echo ""
echo "=============================================="
echo "  Fast Seller Add 5 Products Test"
echo "=============================================="
echo "Time: $(date)"
echo ""

# ===== STEP 1: Login =====
if ! seller_login; then
    _log_error "Login failed - cannot proceed with test"
    exit 1
fi

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-add-5-products-XXXXXX.yaml)

# ===== STEP 2: Add 5 Products =====
PRODUCTS_ADDED=0

for i in {0..4}; do
    PRODUCT_DATA="${PRODUCTS[$i]}"
    IFS='|' read -r TITLE DESC PRICE STOCK <<< "$PRODUCT_DATA"

    PRODUCT_NUM=$((i + 1))
    _log_info "Adding product $PRODUCT_NUM of 5: $TITLE"

    # Navigate to Add Product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "seller-dashboard-fab-add"
    optional: true

- tapOn:
    id: "tab-products"
    optional: true

- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Try FAB from products screen if not on dashboard
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "product-management-fab-add"
    optional: true

- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Fill product title
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "add-product-title-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _adb_input "$TITLE"

    # Fill description
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _adb_input "$DESC"

    # Fill price
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _adb_input "$PRICE"

    # Scroll and fill stock
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- hideKeyboard
- scroll
- tapOn:
    id: "add-product-stock-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    _adb_input "$STOCK"

    # Submit product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- hideKeyboard
- tapOn:
    id: "add-product-submit-button"
    optional: true

- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        PRODUCTS_ADDED=$((PRODUCTS_ADDED + 1))
        _log_success "Product $PRODUCT_NUM added: $TITLE"
    else
        _log_error "Failed to add product $PRODUCT_NUM"
    fi

    # Small delay between products
    sleep 1

    # Navigate back to dashboard for next product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "tab-dashboard"
    optional: true

- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
done

# Take final screenshot
cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "tab-products"

- waitForAnimationToEnd
- takeScreenshot: "add-5-products-final"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Cleanup
rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
if [ $PRODUCTS_ADDED -eq 5 ]; then
    _log_success "ALL 5 PRODUCTS ADDED SUCCESSFULLY!"
    echo "=============================================="
    exit 0
else
    _log_info "Products added: $PRODUCTS_ADDED of 5"
    echo "=============================================="
    exit 1
fi
