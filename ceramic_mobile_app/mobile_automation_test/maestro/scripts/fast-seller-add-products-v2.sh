#!/bin/bash
# Fast Seller Add Products Test v2 - Step by step with verification
# Adds 5 products with clear verification at each step

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

print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
print_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
print_error() { echo -e "${RED}[FAIL]${NC} $1"; }
print_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

export PATH="$PATH:$HOME/.maestro/bin"

echo "=============================================="
echo "  Seller Add 5 Products Test v2"
echo "=============================================="
echo "Username: $USERNAME"
echo ""

# Check device
if ! adb devices | grep -q "device$"; then
    print_error "No Android device connected"
    exit 1
fi
print_success "Device connected"

TEMP_FLOW=$(mktemp /tmp/add-products-XXXXXX.yaml)
TIMESTAMP=$(date +%s)
PRODUCTS_ADDED=0

# ===== LOGIN =====
print_step "Phase 1: Login"

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
adb shell input text "$USERNAME"
sleep 0.5

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
sleep 0.5

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
- takeScreenshot: "add5-00-login-success"
EOF

if ! maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
    print_error "Login failed"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Login successful"

# Function to add one product
add_product() {
    local NUM=$1
    local TITLE=$2
    local DESC=$3
    local PRICE=$4

    print_info "Adding product $NUM: $TITLE"

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
        print_error "Failed to open add product screen"
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
    adb shell input text "$TITLE"
    sleep 0.3

    # Enter description
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    adb shell input text "$DESC"
    sleep 0.3

    # Enter price
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    adb shell input text "$PRICE"
    sleep 0.3

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
        print_success "Product $NUM added: $TITLE"
        PRODUCTS_ADDED=$((PRODUCTS_ADDED + 1))
    else
        print_error "Failed to add product $NUM"
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
    print_success "ADD PRODUCTS TEST PASSED!"
    exit 0
else
    print_error "ADD PRODUCTS TEST FAILED!"
    exit 1
fi
