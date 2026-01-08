#!/bin/bash
# Fast Seller Add 5 Products Test - Hybrid approach
# Adds 5 products to test bulk product creation

set -e

# Configuration
USERNAME="${TEST_SELLER_USERNAME:-test_seller_user}"
PASSWORD="${TEST_PASSWORD:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Add Maestro to PATH
export PATH="$PATH:$HOME/.maestro/bin"

echo "=============================================="
echo "  Fast Seller Add 5 Products Test (Hybrid)"
echo "=============================================="
echo "Username: $USERNAME"
echo "Time: $(date)"
echo ""

# Check device
if ! adb devices | grep -q "device$"; then
    print_error "No Android device connected"
    exit 1
fi
print_success "Device connected"

TEMP_FLOW=$(mktemp /tmp/seller-add-5-products-XXXXXX.yaml)
TIMESTAMP=$(date +%s)

# Product data
declare -a PRODUCTS=(
    "Ceramic_Vase_${TIMESTAMP}|Beautiful_handmade_ceramic_vase|49.99|25"
    "Clay_Bowl_${TIMESTAMP}|Artisan_clay_bowl_for_decoration|29.99|50"
    "Pottery_Plate_${TIMESTAMP}|Traditional_pottery_dinner_plate|19.99|100"
    "Ceramic_Mug_${TIMESTAMP}|Handcrafted_ceramic_coffee_mug|14.99|75"
    "Art_Sculpture_${TIMESTAMP}|Unique_ceramic_art_sculpture|99.99|10"
)

# ===== PHASE 1: Fast Login =====
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

print_step "Launching app..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Login screen ready"

print_step "Entering credentials (fast ADB input)..."
adb shell input text "$USERNAME"
sleep 0.3

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-password-input"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-submit-button"

- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-dashboard"
    timeout: 20000
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Login successful"

# ===== PHASE 2: Add 5 Products =====
PRODUCTS_ADDED=0

for i in {0..4}; do
    PRODUCT_DATA="${PRODUCTS[$i]}"
    IFS='|' read -r TITLE DESC PRICE STOCK <<< "$PRODUCT_DATA"

    PRODUCT_NUM=$((i + 1))
    print_info "Adding product $PRODUCT_NUM of 5: $TITLE"

    # Navigate to Add Product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
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
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-management-fab-add"
    optional: true

- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Fill product title
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-title-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    adb shell input text "$TITLE"
    sleep 0.3

    # Fill description
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    adb shell input text "$DESC"
    sleep 0.3

    # Fill price
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    adb shell input text "$PRICE"
    sleep 0.3

    # Scroll and fill stock
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- scroll
- tapOn:
    id: "add-product-stock-input"
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    adb shell input text "$STOCK"
    sleep 0.3

    # Submit product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-submit-button"
    optional: true

- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        PRODUCTS_ADDED=$((PRODUCTS_ADDED + 1))
        print_success "Product $PRODUCT_NUM added: $TITLE"
    else
        print_error "Failed to add product $PRODUCT_NUM"
    fi

    # Small delay between products
    sleep 1

    # Navigate back to dashboard for next product
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
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
appId: com.ceramicmarketplace.app
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
    print_success "ALL 5 PRODUCTS ADDED SUCCESSFULLY!"
    echo "=============================================="
    exit 0
else
    print_info "Products added: $PRODUCTS_ADDED of 5"
    echo "=============================================="
    exit 1
fi
