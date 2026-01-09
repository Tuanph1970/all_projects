#!/bin/bash
# =============================================================================
# Seller Add 5 Products - Fast ADB input with app focus control
# =============================================================================
# Uses the reusable login library for seller authentication
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

APP_ID="com.ceramicmarketplace.app"

# Function to ensure app is in focus before typing
ensure_app_focus() {
    adb shell "am start -n $APP_ID/.MainActivity" > /dev/null 2>&1
    sleep 0.2
}

# Function for fast text input with app focus
fast_input() {
    local text="$1"
    ensure_app_focus
    _adb_input "$text"
}

echo "=============================================="
echo "  Seller Add 5 Products (Fast ADB Input)"
echo "=============================================="

TEMP_FLOW=$(mktemp /tmp/add5-fast-XXXXXX.yaml)
TIMESTAMP=$(date +%s)
PRODUCTS_ADDED=0

# ===== LOGIN =====
_log_step "Logging in..."

if ! seller_login; then
    _log_error "Login failed"
    rm -f "$TEMP_FLOW"
    exit 1
fi
_log_success "Login done"

# ===== GO TO PRODUCTS TAB =====
_log_step "Going to Products tab..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
- waitForAnimationToEnd
- takeScreenshot: "fast-add5-02-products"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# ===== ADD 5 PRODUCTS =====
add_one_product() {
    local NUM=$1
    local TITLE=$2
    local DESC=$3
    local PRICE=$4

    _log_info "Adding product $NUM: $TITLE"

    # Click FAB to add
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-management-fab-add"
    optional: true
- tapOn:
    id: "fab-add"
    optional: true
- waitForAnimationToEnd
- tapOn:
    id: "add-product-title-input"
    optional: true
- tapOn:
    id: "product-title-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    fast_input "$TITLE"

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
    optional: true
- tapOn:
    id: "product-description-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    fast_input "$DESC"

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
    optional: true
- tapOn:
    id: "product-price-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    fast_input "$PRICE"

    cat > "$TEMP_FLOW" << EOF
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- takeScreenshot: "fast-add5-product${NUM}-filled"
- tapOn:
    id: "add-product-submit-button"
    optional: true
- tapOn:
    id: "submit-button"
    optional: true
- tapOn:
    text: "Save"
    optional: true
- tapOn:
    text: "Add"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "fast-add5-product${NUM}-done"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        PRODUCTS_ADDED=$((PRODUCTS_ADDED + 1))
        _log_success "Product $NUM added"
    fi

    # Go back to products list
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
    optional: true
- tapOn:
    id: "tab-products"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 1
}

add_one_product "1" "Vase_$TIMESTAMP" "Ceramic_vase" "49.99"
add_one_product "2" "Bowl_$TIMESTAMP" "Clay_bowl" "29.99"
add_one_product "3" "Plate_$TIMESTAMP" "Dinner_plate" "19.99"
add_one_product "4" "Mug_$TIMESTAMP" "Coffee_mug" "14.99"
add_one_product "5" "Sculpture_$TIMESTAMP" "Art_piece" "99.99"

# Final screenshot
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "fast-add5-final"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
echo "Products added: $PRODUCTS_ADDED / 5"
if [ $PRODUCTS_ADDED -ge 3 ]; then
    _log_success "TEST PASSED!"
    exit 0
else
    _log_error "TEST NEEDS REVIEW"
    exit 1
fi
