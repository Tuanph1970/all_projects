#!/bin/bash
# Fast Seller Add Product Test - Hybrid approach
# Uses Maestro for element detection/tapping, ADB for fast text input

set -e

# Configuration
USERNAME="${TEST_SELLER_USERNAME:-test_seller_user}"
PASSWORD="${TEST_PASSWORD:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"
MAESTRO_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Product details
PRODUCT_TITLE="Test_Product_$(date +%s)"
PRODUCT_DESCRIPTION="This_is_a_test_product_created_by_automated_test"
PRODUCT_PRICE="99.99"
PRODUCT_STOCK="50"
PRODUCT_CATEGORY="Ceramics"
PRODUCT_TAGS="handmade,ceramic,pottery"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

# Add Maestro to PATH
export PATH="$PATH:$HOME/.maestro/bin"

echo "=============================================="
echo "  Fast Seller Add Product Test (Hybrid)"
echo "=============================================="
echo "Username: $USERNAME"
echo "Product: $PRODUCT_TITLE"
echo "Time: $(date)"
echo ""

# Check device
if ! adb devices | grep -q "device$"; then
    print_error "No Android device connected"
    exit 1
fi
print_success "Device connected"

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-add-product-XXXXXX.yaml)

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

print_step "Launching app and waiting for login screen..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Failed to launch app"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Login screen ready"

# Fast username input with ADB
print_step "Entering username (fast ADB input)..."
adb shell input text "$USERNAME"
sleep 0.3
print_success "Username entered"

# Tap password field
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-password-input"
EOF

print_step "Tapping password field..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# Fast password input
print_step "Entering password (fast ADB input)..."
ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3
print_success "Password entered"

# Submit login
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

print_step "Submitting login..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Login failed"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Login successful"

# ===== PHASE 2: Navigate to Add Product =====
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

- takeScreenshot: "add-product-01-empty"
EOF

print_step "Navigating to Add Product screen..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Failed to navigate to Add Product"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Add Product screen loaded"

# ===== PHASE 3: Fill Product Title =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-title-input"
EOF

print_step "Filling product title..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "$PRODUCT_TITLE"
sleep 0.3
print_success "Title entered"

# ===== PHASE 4: Fill Product Description =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-description-input"
EOF

print_step "Filling product description..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "$PRODUCT_DESCRIPTION"
sleep 0.3
print_success "Description entered"

# ===== PHASE 5: Fill Product Price =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-price-input"
EOF

print_step "Filling product price..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "$PRODUCT_PRICE"
sleep 0.3
print_success "Price entered"

# ===== PHASE 6: Scroll and Fill More Fields =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- scroll
- tapOn:
    id: "add-product-category-input"
    optional: true
EOF

print_step "Filling category..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "$PRODUCT_CATEGORY"
sleep 0.3
print_success "Category entered"

# ===== PHASE 7: Fill Stock =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-stock-input"
    optional: true
EOF

print_step "Filling stock quantity..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "$PRODUCT_STOCK"
sleep 0.3
print_success "Stock entered"

# ===== PHASE 8: Fill Tags (Optional) =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "add-product-tags-input"
    optional: true
EOF

print_step "Filling tags..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "$PRODUCT_TAGS"
sleep 0.3
print_success "Tags entered"

# ===== PHASE 9: Take Screenshot of Filled Form =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- takeScreenshot: "add-product-02-filled"
EOF

print_step "Taking screenshot of filled form..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# ===== PHASE 10: Submit Product =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-submit-button"

- waitForAnimationToEnd
- takeScreenshot: "add-product-03-result"
EOF

print_step "Submitting product..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
    echo ""
    echo "=============================================="
    print_success "SELLER ADD PRODUCT TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    print_error "SELLER ADD PRODUCT TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
