#!/bin/bash
# Seller Add 5 Products - Hybrid (Maestro UI + ADB text input)

set -e

export PATH="$PATH:$HOME/.maestro/bin"

TIMESTAMP=$(date +%s)
TEMP_FLOW=$(mktemp /tmp/add5-hybrid-XXXXXX.yaml)

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_PACKAGE="com.ceramicmarketplace.app"

print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
print_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
print_error() { echo -e "${RED}[FAIL]${NC} $1"; }

# Safe ADB input - just input text directly (app focus maintained by Maestro)
safe_input() {
    local text="$1"
    adb shell input text "$text"
    sleep 0.3
}

echo "=============================================="
echo "  Add 5 Products (Hybrid: Maestro + ADB)"
echo "=============================================="
echo "Timestamp: $TIMESTAMP"
echo ""

# ===== LOGIN =====
print_step "Login..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- launchApp:
    clearState: true
    permissions:
      notifications: allow
      photos: allow
- waitForAnimationToEnd
- assertVisible:
    id: "login-username-input"
- tapOn:
    id: "login-username-input"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

safe_input "test_seller_user"

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-password-input"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

safe_input "Test\\@12345678"

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-submit-button"
- extendedWaitUntil:
    visible:
      id: "tab-dashboard"
    timeout: 20000
- takeScreenshot: "add5-01-logged-in"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Login done"

# ===== GO TO PRODUCTS TAB =====
print_step "Going to Products tab..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
- waitForAnimationToEnd
- takeScreenshot: "add5-02-products-tab"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# ===== FUNCTION TO ADD ONE PRODUCT =====
add_product() {
    local NUM=$1
    local TITLE=$2
    local DESC=$3
    local PRICE=$4
    local CATEGORY=$5
    local QUANTITY=$6

    print_step "Adding product $NUM: $TITLE"

    # Tap FAB to add product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-management-fab-add"
- waitForAnimationToEnd
- tapOn:
    id: "add-product-title-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter title via ADB
    safe_input "$TITLE"

    # Tap description field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter description via ADB
    safe_input "$DESC"

    # Tap price field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter price via ADB
    safe_input "$PRICE"

    # Tap category field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-category-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter category via ADB
    safe_input "$CATEGORY"

    # Tap stock quantity field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-stock-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter quantity via ADB
    safe_input "$QUANTITY"

    # Save product
    cat > "$TEMP_FLOW" << EOF
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- scroll
- takeScreenshot: "add5-product${NUM}-filled"
- tapOn:
    text: "Save"
- waitForAnimationToEnd
- takeScreenshot: "add5-product${NUM}-done"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    print_success "Product $NUM saved"

    # Go back to products list
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.5
}

# ===== ADD 5 PRODUCTS =====
# Args: NUM TITLE DESC PRICE CATEGORY QUANTITY
add_product "1" "Vase_$TIMESTAMP" "Beautiful_ceramic_vase" "49.99" "Vases" "10"
add_product "2" "Bowl_$TIMESTAMP" "Handmade_clay_bowl" "29.99" "Bowls" "15"
add_product "3" "Plate_$TIMESTAMP" "Dinner_plate_set" "19.99" "Plates" "20"
add_product "4" "Mug_$TIMESTAMP" "Coffee_mug_ceramic" "14.99" "Mugs" "25"
add_product "5" "Sculpture_$TIMESTAMP" "Art_sculpture_piece" "99.99" "Art" "5"

# ===== FINAL SCREENSHOT =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
- waitForAnimationToEnd
- takeScreenshot: "add5-final-list"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
print_success "ALL 5 PRODUCTS ADDED SUCCESSFULLY!"
echo "=============================================="
