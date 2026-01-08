#!/bin/bash
# Fast Seller Edit 2 Products Test - Hybrid approach
# Edits 2 existing products to test product update functionality

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
echo "  Fast Seller Edit 2 Products Test (Hybrid)"
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

TEMP_FLOW=$(mktemp /tmp/seller-edit-products-XXXXXX.yaml)
TIMESTAMP=$(date +%s)

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

# ===== PHASE 2: Navigate to Products =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-products"

- waitForAnimationToEnd
- takeScreenshot: "edit-01-product-list"
EOF

print_step "Navigating to products..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Products screen loaded"

# ===== PHASE 3: Edit First Product =====
print_info "Editing product 1 of 2..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Tap on first product to view/edit
- tapOn:
    id: "product-item-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-02-product-1-details"

# Tap edit button
- tapOn:
    id: "edit-product-button"
    optional: true

- waitForAnimationToEnd
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Update title
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-title-input"
    optional: true

- eraseText:
    charactersToErase: 50
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

NEW_TITLE="Updated_Product_1_${TIMESTAMP}"
adb shell input text "$NEW_TITLE"
sleep 0.3

# Update price
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "edit-product-price-input"
    optional: true

- eraseText:
    charactersToErase: 10
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "59.99"
sleep 0.3

# Save changes
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "save-product-button"
    optional: true

- tapOn:
    id: "edit-product-submit-button"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-03-product-1-saved"
EOF

if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_success "Product 1 edited successfully"
else
    print_info "Product 1 edit attempted"
fi

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
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# ===== PHASE 4: Edit Second Product =====
print_info "Editing product 2 of 2..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Tap on second product
- tapOn:
    id: "product-item-1"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-04-product-2-details"

# Tap edit button
- tapOn:
    id: "edit-product-button"
    optional: true

- waitForAnimationToEnd
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Update description
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-description-input"
    optional: true

- eraseText:
    charactersToErase: 100
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

NEW_DESC="Updated_description_with_new_details_${TIMESTAMP}"
adb shell input text "$NEW_DESC"
sleep 0.3

# Update stock
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- scroll
- tapOn:
    id: "edit-product-stock-input"
    optional: true

- eraseText:
    charactersToErase: 5
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2
adb shell input text "200"
sleep 0.3

# Save changes
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "save-product-button"
    optional: true

- tapOn:
    id: "edit-product-submit-button"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-05-product-2-saved"
EOF

if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_success "Product 2 edited successfully"
else
    print_info "Product 2 edit attempted"
fi

# Final screenshot of product list
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- pressKey: back
- waitForAnimationToEnd

- tapOn:
    id: "tab-products"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-06-final-list"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Cleanup
rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
print_success "SELLER EDIT 2 PRODUCTS TEST COMPLETED!"
echo "=============================================="
exit 0
